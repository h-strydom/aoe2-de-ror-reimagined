"""The reimagined layer: no ending on the primary objective, bonus objectives by difficulty, banked upgrades."""
from __future__ import annotations

import pytest

from reimagined import progression

CAMP = progression.Campaign(
    upgrades={"a": {"label": "A", "effects": [{"type": "modify_resource", "tribute_list": 0, "operation": "ADD",
                                               "quantity": 50}]},
              "b": {"label": "B", "effects": []}, "c": {"label": "C", "effects": []}, "d": {"label": "D"}},
    missions={"01_one": {"rewards": ["a", "b"], "bonus": [
        {"text": "Hunt.", "conditions": [{"type": "own_fewer_objects", "source_player": 0, "quantity": 0}],
         "rewards": ["c", "d"]},
        {"text": "Grow.", "conditions": [{"type": "accumulate_attribute", "attribute": 11, "quantity": 15}]}]},
        "02_two": {"rewards": ["c", "a"]}})
FOLDERS = ["01_one", "02_two"]


def by_name(ts):
    return {t["name"]: t for t in ts}


def test_every_mission_loads_every_slot_and_applies_picks():
    ts = by_name(progression.triggers(CAMP, FOLDERS, 2))
    loads = [e["message"] for e in ts["RI Upgrades load"]["effects"]]
    assert loads == ["m01_primary", "m01_bonus1", "m02_primary"]          # mission 1's picks count in mission 2
    apply = ts["RI Upgrade m02_primary 2"]                                   # option 2 of slot m02_primary is "a"
    assert apply["conditions"][0]["quantity"] == 2 and apply["effects"][0]["quantity"] == 50
    assert apply["effects"][0]["source_player"] == 1


def test_bonus_objectives_follow_the_difficulty():
    ts = by_name(progression.triggers(CAMP, FOLDERS, 1))
    assert not ts["RI Bonus 1"]["enabled"] and ts["RI Bonus 1"]["short_description"] == "- Hunt."
    moderate = ts["RI Difficulty moderate 2"]["effects"]
    assert [e.get("trigger_id") for e in moderate[1:]] == ["RI Bonus 1"] and moderate[0]["quantity"] == 2
    hard = ts["RI Difficulty hard 1"]["effects"]
    assert [e.get("trigger_id") for e in hard[1:]] == ["RI Bonus 1", "RI Bonus 2"] and hard[0]["quantity"] == 3
    assert "RI Difficulty hard -1" in ts                                        # Extreme plays as Hard
    assert ts["RI Bonus 2"]["conditions"][0]["source_player"] == 1             # the human's unless given
    assert ts["RI Bonus 1"]["conditions"][0]["source_player"] == 0


def test_rewards_are_stored_per_objective():
    ts = by_name(progression.triggers(CAMP, FOLDERS, 1))
    offer = ts["RI Reward bonus1"]["effects"][1]
    assert offer["type"] == "create_decision" and (offer["message_option1"], offer["message_option2"]) == ("C", "D")
    pick = ts["RI Reward bonus1 pick 2"]["effects"]
    assert pick[0]["variable"] == "RI m01_bonus1" and pick[0]["quantity"] == 2
    assert pick[1] == {"type": "store_key_value", "variable": "RI m01_bonus1", "message": "m01_bonus1"}
    assert "RI Reward bonus2" not in ts                                         # bonus 2 offers no reward


def test_winning_unlocks_ending_and_all_done_ends():
    plan = [{"name": "P1 Victory", "effects": [{"type": "declare_victory", "source_player": 1, "enabled": True}]},
            {"name": "P2 Victory", "effects": [{"type": "declare_victory", "source_player": 2, "enabled": True}]},
            {"name": "P1 Objective 1", "display_on_screen": True, "description_order": 1}]
    assert progression.hand_over(plan, 1) == ["P1 Victory"]
    assert plan[0]["effects"] == [{"type": "activate_trigger", "trigger_id": "RI Primary complete"}]
    assert plan[1]["effects"][0]["type"] == "declare_victory"                  # losing still loses
    assert plan[2]["description_order"] == 1 + progression.OBJECTIVE_ORDER_OFFSET
    ts = by_name(progression.triggers(CAMP, FOLDERS, 1))
    primary = [e["type"] for e in ts["RI Primary complete"]["effects"]]
    assert "change_technology_location" in primary and "enable_technology_stacking" in primary
    assert ts["RI End Mission"]["conditions"][0]["type"] == "researching_tech"
    assert [c["type"] for c in ts["RI All done"]["conditions"]] == ["compare_variables", "variable_value"]
    no_tc = by_name(progression.triggers(CAMP, FOLDERS, 1, town_center=False))
    assert "RI End Mission" not in no_tc and no_tc["RI End offer"]["effects"][0]["type"] == "create_decision"


def test_content_errors_are_reported(tmp_path):
    (tmp_path / "x.yaml").write_text("upgrades: {a: {label: A}}\nmissions: {01_one: {rewards: [a, zz]}}\n")
    with pytest.raises(ValueError, match="two upgrade keys"):
        progression.load("x", tmp_path)
    assert progression.load("missing", tmp_path).missions == {}


def test_ascent_of_egypt_content_loads():
    camp = progression.load("ascent_of_egypt")
    assert camp.missions["01_hunting"]["rewards"] == ["hunters_cache", "timber_stock"]
