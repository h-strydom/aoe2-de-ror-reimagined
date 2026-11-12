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


def _active(players, key):
    return [players[p.number] for p in load_scenario(MISSIONS[key].scenario_path).active_players]


def test_disables_and_view_reach_the_ror_map(tmp_path):
    p1 = _converted(tmp_path, "ascent_of_egypt/02_foraging")[1]
    assert set(p1.disabled_techs) == {101, 102, 103}                    # Tool, Bronze, Iron Age
    assert 12 in p1.disabled_buildings and 68 not in p1.disabled_buildings   # barracks off, granary allowed
    # the camera starts over the Town Center (22,18), not AoE DE's view, the map's centre (24,24)
    assert (p1.initial_player_view_x, p1.initial_player_view_y) == (22, 18)


def test_ai_carries_over(tmp_path):
    assassins = _converted(tmp_path, "yamato_empire_of_the_rising_sun/01_the_assassins")
    assert assassins[2].personality == "Immobile AI"                    # AoE1 "ImmobileUnitsAII"
    troy = _converted(tmp_path, "glory_of_greece/04_the_trojan_war")
    # Troy builds: RoR's standard skirmish AI, a level harder (Moderate plays Hard), never resigning
    assert troy[2].personality == "Standard AI"
    assert r'(load "default\init")' in troy[2].ai_script and r'(load "default\resign")' not in troy[2].ai_script
    i = troy[2].ai_script.index("#load-if-defined DIFFICULTY-MODERATE")
    assert "(defconst diff 4)" in troy[2].ai_script[i:i + 80]
    # its first attack waits as long as the AoE1 AI's did, though Hard plays Hardest (0)
    j = troy[2].ai_script.index("#load-if-defined DIFFICULTY-HARD\n")
    assert "(defconst min-attack-time 0)" not in troy[2].ai_script[j:j + 400]
    # Farming's Lower Egypt plays the AI toolbox's town profile from conversion.yaml (2026-11-12): Axemen by line,
    # light fishing, a home guard, and it holds its food past 1200 for its 2000-food goal
    ri = convert_mission(MISSIONS["ascent_of_egypt/06_farming"], load(), tmp_path, reimagined=False).out
    red = AoE2DEScenario.from_file(str(ri)).player_manager.players[2]
    assert red.personality == "Lower Egypt (toolbox)"
    for part in ("(train my-line266)", "water: fishing up to 3", "(food-amount < 1200)", "(up-retreat-now)"):
        assert part in red.ai_script
    # the Greek army (P3, no villagers or town center) keeps its translated AoE1 plan
    assert troy[3].personality.endswith("(AoE1)")
    trade = _converted(tmp_path, "ascent_of_egypt/07_trade")
    # a passive AoE1 AI never attacks unless conversion.yaml says so (the Canaanites, P3, now play the reimagined mission's own AI)
    assert trade[4].personality == "PASSIVE (AoE1)" and "(attack-now)" in trade[4].ai_script   # told to (audit)
    nubians = _converted(tmp_path, "ascent_of_egypt/09_the_river_outpost")[2]
    assert nubians.personality == "PASSIVE (AoE1)" and "(attack-now)" not in nubians.ai_script
    assert trade[3].personality == "Canaanites"


def test_ai_translation():
    from reimagined.ai import sn_name, translate
    assert sn_name("SNPercentCivilianExplorers") == "sn-percent-civilian-explorers"
    p = load_scenario(MISSIONS["glory_of_greece/04_the_trojan_war"].scenario_path).players[2]
    t = translate(p.ai, missions.personality(p.ai.personality_text), load(), "Trojan Defenders")
    assert t.spec["build_order"][:2] == [{"build": "TOWN_CENTER", "count": 1}, {"train": "VILLAGER", "count": 1}]
    assert {"train": "VILLAGER", "count": 6} in t.spec["build_order"]          # counts add up per unit
    assert t.spec["attack"]["first"] == 7200 and t.spec["attack"]["min_group"] == 1
    assert any("walls aren't built" in s for s in t.skipped)


def test_water_maps_keep_transports_and_rebuild_buildings():
    from reimagined.ai import translate
    p = load_scenario(MISSIONS["glory_of_greece/04_the_trojan_war"].scenario_path).players[1]   # Troy
    t = translate(p.ai, missions.personality(p.ai.personality_text), load(), "Troy")
    assert t.spec["transports"] == 2 and t.spec["transport_unit"] == "LIGHT_TRANSPORT"
    assert t.spec["villagers"] == 25 and "gatherers" not in t.spec                # auto split from its list
    assert {"build": "STABLE", "count": 1} in t.spec["keep"] and {"build": "SIEGE_WORKSHOP", "count": 1} in t.spec["keep"]
    assert not any(k.get("build") == "HOUSE" for k in t.spec["keep"])


def test_specific_build_item_builds_the_wonder():
    from aoe2ed.ai.spec import build_script
    from reimagined.ai import translate
    p = load_scenario(MISSIONS["voices_of_babylon/08_the_conquest_of_nineveh"].scenario_path).players[1]   # Nineveh
    t = translate(p.ai, missions.personality(p.ai.personality_text), load(), "Nineveh")
    script = build_script(t.spec)
    assert "(game-time >= 0)" in script and "(build 276)" in script            # AoE1: a Wonder at minute 0
    p = load_scenario(MISSIONS["glory_of_greece/08_alexander_the_great"].scenario_path).players[3]   # Persian Army
    t = translate(p.ai, missions.personality(p.ai.personality_text), load(), "Persian Army")
    assert "(game-time >= 360)" in t.spec["rules"]


def test_population_200_where_player_1_can_build(tmp_path):
    from aoe2ed.ai import per
    troy = _converted(tmp_path, "glory_of_greece/04_the_trojan_war")
    assert {pl.population_cap for pl in _active(troy, "glory_of_greece/04_the_trojan_war")} == {200}   # human and AI
    # a passive builder keeps its translated plan, which grows toward the cap
    script = _converted(tmp_path, "ascent_of_egypt/09_the_river_outpost")[2].ai_script
    assert "grow stage 8/8: villagers" in script
    assert [d for d in per.check(script) if d.severity == "error"] == []
    # Moderate grows over an hour in 8 stages; Standard 3x slower, Hard 2x faster (one copy of the rules per level)
    assert all(f"(enable-timer 5 {s})" in script for s in (1350, 450, 225))
    skirmish = _converted(tmp_path, "ascent_of_egypt/05_skirmish")             # no villager, no town center
    assert {pl.population_cap for pl in _active(skirmish, "ascent_of_egypt/05_skirmish")} == {50}
    assert "grow stage" not in skirmish[2].ai_script
    caesar = _converted(tmp_path, "ave_caesar/01_caesars_revenge")             # claims a base
    assert caesar[1].population_cap == 200
