"""The scenario reader against every local AoE DE campaign scenario (skipped before `reimagined setup`)."""
from __future__ import annotations

import pytest

from reimagined import layout
from reimagined.aoede.scenario import load_scenario

MISSIONS = [(c, m) for c in layout.campaigns() for m in c.missions]
pytestmark = pytest.mark.skipif(not all(m.scenario_path.is_file() for _, m in MISSIONS),
                                reason="run `reimagined setup` first")


@pytest.mark.parametrize("camp,mission", MISSIONS, ids=lambda v: getattr(v, "folder", v).name if hasattr(v, "folder") else "")
def test_scenario_invariants(camp, mission):
    s = load_scenario(mission.scenario_path)
    assert s.body_version == 3.13
    assert s.width == s.height and s.width in (48, 72, 96, 120, 144, 200, 250)
    assert len(s.terrain) == len(s.elevation) == s.width * s.height
    assert max(s.elevation) <= 7 and max(s.terrain) < 64
    assert s.active_players and any(p.human for p in s.players)
    for p in s.players:
        assert 0 <= p.starting_age <= 4
        if p.active and p.number <= 8:
            assert set(p.resources) == {"food", "wood", "gold", "stone", "pop_cap"}
        if not p.active:
            # Inactive players can still own a few placeholder objects (Siege of Alesia: Gaul's 3 x 112).
            assert len(p.units) <= 3, f"inactive player {p.number} owns {len(p.units)} units"
    for u in s.gaia_units + [u for p in s.players for u in p.units]:
        assert 0 <= u.x <= s.width and 0 <= u.y <= s.height


def test_first_scenario_known_values():
    s = load_scenario(MISSIONS[0][1].scenario_path)
    assert s.filename == "Scn1-01-Hunting.aoescn" and (s.width, s.height) == (48, 48)
    p1 = s.players[0]
    assert p1.name == "Your Tribe" and p1.active and p1.human
    assert s.description.startswith("Island in the Nile Delta")


def test_mission_files_match_the_scenarios():
    import yaml
    for _camp, m in MISSIONS:
        s = load_scenario(m.scenario_path)
        meta = yaml.safe_load((m.folder / "mission.yaml").read_text(encoding="utf-8"))
        assert meta["source"]["map_size"] == s.width
        assert meta["source"]["players"] == len(s.active_players), m.folder
