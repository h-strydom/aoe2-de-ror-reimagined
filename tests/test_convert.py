"""The converter: terrain clean-up, converted files read back, campaign files and screens, committed maps up to date."""
from __future__ import annotations

import json
from collections import Counter

import pytest
from aoe2ed import games
from aoe2ed.campaign import Campaign as RorCampaign
from aoe2ed.screens import game_campaign_dir
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

from reimagined import editions, layout
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


@pytest.mark.parametrize("c", CAMPAIGNS[:1], ids=lambda c: c.slug)
def test_campaign_file_and_screen(c):
    """Reads the committed build (test_committed_maps_are_up_to_date checks it's what convert makes today)."""
    out = layout.AOE2DE_ROR                                  # Ascent of Egypt: 12 missions, RoR has its screen
    camp = RorCampaign.read(campaign_path(c, out))
    assert camp.name == c.slug                               # the game finds the screen by the internal name
    assert [s.name for s in camp.scenarios] == [m.title for m in c.missions]
    assert [s.data for s in camp.scenarios] == [scenario_path(m, out).read_bytes() for m in c.missions]
    lay = json.loads((out / c.slug / f"{c.slug}_layout.json").read_text(encoding="utf-8"))
    widgets = {w["Widget"]["Name"]: w["Widget"] for w in lay["Widgets"]}
    assert widgets["TitleLabel"]["Text"] == "AoE1 Ascent of Egypt" and "ZPlane" not in json.dumps(lay)
    assert widgets["ScenarioButton12"]["ChildWidgets"][0]["Widget"]["Text"] == "12. The Siege in Canaan"
    intro = json.loads((out / c.slug / f"{c.slug}.json").read_text(encoding="utf-8"))
    assert len(intro["Scenarios"]) == 12


@pytest.mark.parametrize("c", [c for c in CAMPAIGNS if c.slug == "reign_of_the_hittites"], ids=lambda c: c.slug)
def test_campaigns_without_ror_art_get_our_own_screen(c):
    out = layout.AOE2DE_ROR                                  # the committed build, as above
    lay = json.loads((out / c.slug / f"{c.slug}_layout.json").read_text(encoding="utf-8"))
    assert lay["UserMaterials"][0]["FileName"] == f"{c.slug}_map.dds"


EDITIONS = [(c, e) for c in CAMPAIGNS for e in editions.of(c)]


@needs_ror
@pytest.mark.parametrize("c,edition", EDITIONS, ids=lambda x: getattr(x, "slug", None) or x.key)
def test_committed_maps_are_up_to_date(c, edition, tmp_path, mission_pool):
    """aoe2de_ror/ (and aoe2de_ror_x/) must be what `reimagined convert` builds from conversion.yaml today."""
    paths, results = convert_campaign(c, load(), tmp_path, pool=mission_pool, edition=edition)
    assert not [r.skipped for r in results if r.skipped], f"{c.slug}: victory conditions not converted"
    stale = []
    for f in paths + [scenario_path(m, tmp_path) for m in c.missions]:
        committed = edition.out / f.relative_to(tmp_path)
        if not committed.is_file() or committed.read_bytes() != f.read_bytes():
            stale.append(str(committed.relative_to(layout.ROOT)))
    assert not stale, f"run `uv run reimagined convert {c.slug}`; out of date: {stale}"


@pytest.mark.parametrize("c,edition", EDITIONS, ids=lambda x: getattr(x, "slug", None) or x.key)
def test_every_committed_scenario_reads_back(c, edition):
    """A list left in a trigger effect once wrote an unreadable scenario (Ascent of Egypt 5)."""
    for m in c.missions:
        AoE2DEScenario.from_file(str(scenario_path(m, edition.out)))


@needs_setup
def test_the_faithful_edition_has_no_reimagined_layer(tmp_path):
    """RoR-RI wins as the original does; the reimagined Ascent of Egypt is RoR-RIX's (the user, 2026-11-12)."""
    m = CAMPAIGNS[0].missions[7]                             # Egypt 8: reimagined content, a mission AI
    names = {t.name for t in AoE2DEScenario.from_file(
        str(convert_mission(m, load(), tmp_path, reimagined=False).out)).trigger_manager.triggers}
    assert names and not [n for n in names if n.startswith("RI ")]
    x = {t.name for t in AoE2DEScenario.from_file(
        str(convert_mission(m, load(), tmp_path / "x", reimagined=True).out)).trigger_manager.triggers}
    assert "RI Bonus 1" in x and "RI End offer" in x


@pytest.mark.parametrize("c", CAMPAIGNS[:1], ids=lambda c: c.slug)
def test_map_type_and_scouts_links(c):
    """The standard AI plays islands where it can't walk to you; the Scouts page links the project and its issues
    (the user, 2026-11-12). Reads the committed build."""
    def scn(n):
        return AoE2DEScenario.from_file(str(scenario_path(c.missions[n - 1], layout.AOE2DE_ROR)))
    assert scn(2).sections["Options"].ai_map_type == 148                      # Highland: no navy on a land map
    trade = scn(7)
    assert trade.sections["Options"].ai_map_type == 166                       # Small Islands: across the sea
    assert "github.com/h-strydom/aoe2-de-ror-reimagined/issues" in trade.message_manager.scouts
    # Farming: Lower Egypt wins at 2000 food, shown as a line with its count; you're at war with them, not neutral
    farming = scn(6)
    lines = [t.short_description for t in farming.trigger_manager.triggers if t.display_as_objective]
    assert "- Don't let Lower Egypt gather 2000 food (<P2 Threat 1>/2000)." in lines
    assert farming.player_manager.players[1].diplomacy[1] == 3
    # the Egypt audit (2026-11-12): no Granary walls or towers before Trade; Skirmish's Raiders are enemies (Trade's
    # own design: test_trade_follows_its_mission_doc)
    for n in (4, 6):
        assert {11, 16} <= set(scn(n).player_manager.players[1].disabled_techs)
    assert 16 not in scn(7).player_manager.players[1].disabled_techs
    assert scn(5).player_manager.players[1].diplomacy[1] == 3


def test_neutral_players_fight_or_answer_attacks():
    """The neutral-missions audit (2026-11-12): RoR's neutral players never fight. Armies marching on you are at war
    with you; neutral towns turn on you once you attack them (provoked), and a trigger answers their signal.
    Reads the committed build."""
    def scn(key):
        m = {x.key: x for c in layout.campaigns() for x in c.missions}[key]
        return AoE2DEScenario.from_file(str(scenario_path(m, layout.AOE2DE_ROR)))
    for key in ("voices_of_babylon/04_i_shall_return", "yamato_empire_of_the_rising_sun/05_the_canyon_of_death"):
        assert scn(key).player_manager.players[1].diplomacy[1] == 3
    holy = scn("voices_of_babylon/01_holy_man")
    assert holy.player_manager.players[1].diplomacy[1] == 1                     # neutral until provoked
    assert "(set-stance 1 enemy)" in holy.player_manager.players[2].ai_script
    signals = {t.name: t.conditions[0].ai_signal for t in holy.trigger_manager.triggers if "provoked" in t.name}
    assert signals == {"P2 provoked": 102, "P3 provoked": 103}


def test_losing_the_unit_an_objective_needs_is_a_defeat():
    """Religion's Stone Thrower destroyed left the mission unwinnable (playtest 2026-11-12): in RoR-RI its death
    makes the Libyans win. RoR-RIX lets you train another, so it has no such loss. Reads the committed build."""
    m = {x.key: x for c in layout.campaigns() for x in c.missions}["ascent_of_egypt/08_religion"]
    ri = AoE2DEScenario.from_file(str(scenario_path(m, layout.AOE2DE_ROR)))
    loss = next(t for t in ri.trigger_manager.triggers if t.name == "P1 Loss: the Stone Thrower is destroyed")
    win = loss.effects[-1]
    assert (win.source_player, win.enabled) == (2, 1)                      # the Libyans win, never you
    rix = AoE2DEScenario.from_file(str(scenario_path(m, layout.AOE2DE_ROR_X)))
    assert not any("Loss: the" in t.name for t in rix.trigger_manager.triggers)


def test_trade_follows_its_mission_doc():
    """Trade (docs/missions/ascent_of_egypt/07_trade.md, the user's design 2026-11-13): yellow raids from a trade
    economy, green is your land rival, red your partner until 250 gold (Hard: an enemy from the start). Reads the
    committed build."""
    m = {x.key: x for c in layout.campaigns() for x in c.missions}["ascent_of_egypt/07_trade"]
    s = AoE2DEScenario.from_file(str(scenario_path(m, layout.AOE2DE_ROR)))
    pm = s.player_manager
    assert list(pm.players[1].diplomacy)[1:4] == [0, 3, 3]                    # red ally, green and yellow enemies
    names = {pm.players[n].personality for n in (2, 3, 4)}
    assert names == {"Minoans (toolbox)", "Canaanites (toolbox)", "Libyans (toolbox)"}
    yellow = pm.players[4]
    assert (yellow.wood, yellow.gold) == (2500, 0)                            # trade pays for everything
    boats = [u for u in s.unit_manager.units[4] if u.unit_const == 17]
    assert len(boats) == 3 and "(train my-trade-boat-line)" not in yellow.ai_script   # given, never replaced
    assert pm.players[2].diplomacy[3] == 0 and pm.players[3].diplomacy[3] == 0    # yellow trades with red and green
    assert "(research-completed my-t-tool-age)" in pm.players[3].ai_script        # green rushes the Tool Age
    assert "(enable-timer 2 300)" in yellow.ai_script                         # five minutes' grace
    assert "naval attack" not in pm.players[3].ai_script                      # green: no warships
    triggers = {t.name: t for t in s.trigger_manager.triggers}
    gold = triggers["P2 turns hostile: P1's gold"].conditions[0]
    assert (gold.attribute, gold.quantity) == (3, 250)
    assert triggers["P2 hostile on Hard"].conditions[0].inverted == 1
    assert len(triggers["Mission setup"].effects) == 5
