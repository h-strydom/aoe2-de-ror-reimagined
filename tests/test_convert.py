"""The converter: terrain clean-up, converted files read back, campaign files and screens, committed maps up to date."""
from __future__ import annotations

import json
from collections import Counter

import pytest
from aoe2ed import games
from aoe2ed.campaign import Campaign as RorCampaign
from aoe2ed.screens import game_campaign_dir
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

from reimagined import layout
from reimagined.aoede.scenario import load_scenario
from reimagined.conversion import load
from reimagined.convert import (
    ROR_CIVS,
    campaign_path,
    convert_campaign,
    convert_mission,
    placements,
    ror_terrain,
    scenario_path,
)
from reimagined.terrain import clean_terrain

CAMPAIGNS = layout.campaigns()


def _ror_installed() -> bool:
    try:
        return game_campaign_dir("ror").is_dir()
    except RuntimeError:
        return False


SET_UP = all(m.scenario_path.is_file() for c in CAMPAIGNS for m in c.missions)
needs_setup = pytest.mark.skipif(not SET_UP, reason="run `reimagined setup` first")
# Campaign files come with RoR's campaign screens, read from the RoR install.
needs_ror = pytest.mark.skipif(not (SET_UP and _ror_installed()), reason="needs `reimagined setup` and RoR installed")
ROAD = 32


def test_stray_roads_take_the_terrain_around_them():
    w = h = 12
    terrain = [0] * (w * h)
    terrain[5 * w + 5] = ROAD                    # a lone road tile in grass
    for x in range(10):
        terrain[10 * w + x] = ROAD               # a real road: 10 tiles in a row
    out = clean_terrain(terrain, w, h, frozenset({ROAD}), 8)
    assert out[5 * w + 5] == 0
    assert all(out[10 * w + x] == ROAD for x in range(10))


@needs_setup
def test_converted_scenario_reads_back(tmp_path):
    conv = load()
    m = CAMPAIGNS[0].missions[0]
    res = convert_mission(m, conv, tmp_path)
    src = load_scenario(m.scenario_path)
    s = AoE2DEScenario.from_file(str(res.out))

    assert games.scenario_game(s) == "ror"
    tiles = s.map_manager.terrain
    assert s.map_manager.map_size == src.width
    assert [t.terrain_id for t in tiles] == ror_terrain(src, conv)
    assert [t.elevation for t in tiles] == src.elevation

    pm = s.player_manager
    assert pm.active_players == len(src.active_players)
    for p in src.active_players:
        assert pm.players[p.number].civilization == games.ror_data()["civs"][ROR_CIVS[p.civ]]
        assert pm.players[p.number].food == int(p.resources["food"])

    def key(owner, ror_id, x, y):
        return owner, ror_id, round(x, 3), round(y, 3)
    expected = Counter(key(o, rid, u.x, u.y) for o, rid, u in placements(src, conv, ror_terrain(src, conv), Counter()))
    written = Counter(key(owner, u.unit_const, u.x, u.y)
                      for owner, units in enumerate(s.unit_manager.units) for u in units)
    assert written == expected and res.placed == sum(expected.values())


@needs_setup
def test_mission_override_reaches_the_map(tmp_path):
    conv = load()
    m = CAMPAIGNS[0].missions[3]
    sand = {i for i, t in enumerate(load_scenario(m.scenario_path).terrain) if t == 6}   # Desert
    assert sand
    conv.missions[m.key] = {"terrain": {6: 32}, "objects": {}}                          # Desert -> SNOW
    s = AoE2DEScenario.from_file(str(convert_mission(m, conv, tmp_path).out))
    assert all(s.map_manager.terrain[i].terrain_id == 32 for i in sand)


@needs_ror
def test_campaign_file_and_screen(tmp_path):
    c = CAMPAIGNS[0]                                         # Ascent of Egypt: 12 missions, RoR has its screen
    paths, results = convert_campaign(c, load(), tmp_path)
    camp = RorCampaign.read(campaign_path(c, tmp_path))
    assert camp.name == c.slug                               # the game finds the screen by the internal name
    assert [s.name for s in camp.scenarios] == [m.title for m in c.missions]
    assert [s.data for s in camp.scenarios] == [r.out.read_bytes() for r in results]
    lay = json.loads((tmp_path / c.slug / f"{c.slug}_layout.json").read_text(encoding="utf-8"))
    widgets = {w["Widget"]["Name"]: w["Widget"] for w in lay["Widgets"]}
    assert widgets["TitleLabel"]["Text"] == "AoE1 Ascent of Egypt" and "ZPlane" not in json.dumps(lay)
    assert widgets["ScenarioButton12"]["ChildWidgets"][0]["Widget"]["Text"] == "12. The Siege in Canaan"
    intro = json.loads((tmp_path / c.slug / f"{c.slug}.json").read_text(encoding="utf-8"))
    assert len(intro["Scenarios"]) == 12 and len(paths) == 3


@needs_ror
def test_campaigns_without_a_ror_screen_have_none(tmp_path):
    c = next(c for c in CAMPAIGNS if c.slug == "reign_of_the_hittites")
    paths, _ = convert_campaign(c, load(), tmp_path)
    assert paths == [campaign_path(c, tmp_path)]


@needs_ror
def test_committed_maps_are_up_to_date(tmp_path):
    """aoe2de_ror/ must be what `reimagined convert` builds from conversion.yaml today."""
    conv = load()
    stale = []
    for c in CAMPAIGNS:
        paths, results = convert_campaign(c, conv, tmp_path)
        assert not [r.skipped for r in results if r.skipped], f"{c.slug}: victory conditions not converted"
        fresh = paths + [scenario_path(m, tmp_path) for m in c.missions]
        for f in fresh:
            committed = layout.AOE2DE_ROR / f.relative_to(tmp_path)
            if not committed.is_file() or committed.read_bytes() != f.read_bytes():
                stale.append(str(committed.relative_to(layout.ROOT)))
    assert not stale, f"run `uv run reimagined convert`; out of date: {stale}"
