"""Per-player settings: the editor's disables, the start view and the AI, decoded and carried into RoR."""
from __future__ import annotations

import pytest
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

from reimagined import layout, missions
from reimagined.aoede.scenario import DISABLES, load_scenario
from reimagined.conversion import load
from reimagined.convert import convert_mission

MISSIONS = {m.key: m for c in layout.campaigns() for m in c.missions}
SET_UP = all(m.scenario_path.is_file() for m in MISSIONS.values())
pytestmark = pytest.mark.skipif(not SET_UP, reason="run `reimagined setup` first")


def test_foraging_allows_only_its_three_objective_buildings():
    p1 = load_scenario(MISSIONS["ascent_of_egypt/02_foraging"].scenario_path).players[0]
    allowed = {"granary", "storage_pit", "dock", "town_center", "wonder"}
    assert set(p1.disabled) == set(DISABLES) - allowed
    assert p1.view == (24, 24)


def test_ai_files_are_decoded():
    s = load_scenario(MISSIONS["glory_of_greece/04_the_trojan_war"].scenario_path)
    troy = s.players[1].ai
    assert (troy.strategy, troy.personality) == ("TrojanWar2", "Scn2-4-P2")
    entries = missions.build_list(troy.strategy_text)
    assert entries[0] == "B109 Town_Center1 1 -1" and all(not e.startswith("//") for e in entries)
    assert missions.personality(troy.personality_text)["SNMaximumAttackGroupSize"] == 8


def test_mission_files_carry_the_settings():
    import yaml
    d = yaml.safe_load((MISSIONS["glory_of_greece/04_the_trojan_war"].folder / "mission.yaml").read_text(encoding="utf-8"))
    troy = d["players"][1]
    assert troy["disabled"] == ["iron_age"] and troy["view"] == [23, 6]
    assert troy["ai"]["strategy"] == "TrojanWar2" and troy["ai"]["build_list"][0] == "B109 Town_Center1 1 -1"
    assert "ai" not in d["players"][0]                                  # the human player's AI isn't used


def _converted(tmp_path, key):
    return AoE2DEScenario.from_file(str(convert_mission(MISSIONS[key], load(), tmp_path).out)).player_manager.players


def test_disables_and_view_reach_the_ror_map(tmp_path):
    p1 = _converted(tmp_path, "ascent_of_egypt/02_foraging")[1]
    assert set(p1.disabled_techs) == {101, 102, 103}                    # Tool, Bronze, Iron Age
    assert 12 in p1.disabled_buildings and 68 not in p1.disabled_buildings   # barracks off, granary allowed
    assert (p1.initial_player_view_x, p1.initial_player_view_y) == (24, 24)


def test_ai_intent_carries_over(tmp_path):
    assassins = _converted(tmp_path, "yamato_empire_of_the_rising_sun/01_the_assassins")
    assert assassins[2].personality == "Immobile AI"                    # AoE1 "ImmobileUnitsAII"
    trade = _converted(tmp_path, "ascent_of_egypt/07_trade")
    assert trade[3].personality == "NoneAi"                             # AoE1 "PASSIVE"
    assert trade[2].personality == ""                                   # RoR's standard AI
