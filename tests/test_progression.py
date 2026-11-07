"""The reimagined layer: no ending on the primary objective, bonus objectives by difficulty, banked upgrades."""
from __future__ import annotations

import pytest

from reimagined import progression

CAMP = progression.Campaign(
    upgrades={"a": {"label": "A", "text": "Long A.", "effects": [{"type": "modify_resource", "tribute_list": 0, "operation": "ADD",
                                               "quantity": 50}]},
              "b": {"label": "B", "effects": []}, "c": {"label": "C", "effects": []}, "d": {"label": "D"}},
    missions={"01_one": {"rewards": ["a", "b"], "bonus": [
        {"text": "Hunt.", "conditions": [{"type": "own_fewer_objects", "source_player": 0, "quantity": 0}],
         "rewards": ["c", "d"], "setup": [{"type": "create_object", "source_player": 0, "object_list_unit_id": 1029}]},
        {"text": "Grow.", "conditions": [{"type": "accumulate_attribute", "attribute": 11, "quantity": 15}],
         "setup": [{"type": "modify_attribute", "source_player": 0, "object_list_unit_id": [1301, 333]}]}]},
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
    assert [e["trigger_id"] for e in moderate if e["type"] == "activate_trigger"] == ["RI Bonus 1"]
    assert moderate[0]["quantity"] == 2
    hard = ts["RI Difficulty hard 1"]["effects"]
    assert [e["trigger_id"] for e in hard if e["type"] == "activate_trigger"] == ["RI Bonus 1", "RI Bonus 2"]
    assert hard[0]["quantity"] == 3
    assert "RI Difficulty hard -1" in ts                                        # Extreme plays as Hard
    assert ts["RI Bonus 2"]["conditions"][0]["source_player"] == 1             # the human's unless given
    assert ts["RI Bonus 1"]["conditions"][0]["source_player"] == 0


def test_rewards_are_stored_per_objective():
    ts = by_name(progression.triggers(CAMP, FOLDERS, 1))
    offer = ts["RI Reward bonus1"]["effects"][0]
    assert offer["type"] == "create_decision" and (offer["message_option1"], offer["message_option2"]) == ("C", "D")
    pick = ts["RI Reward bonus1 pick 2"]["effects"]
    assert pick[0]["variable"] == "RI m01_bonus1" and pick[0]["quantity"] == 2
    assert pick[1] == {"type": "store_key_value", "variable": "RI m01_bonus1", "message": "m01_bonus1"}
    assert {e["trigger_id"] for e in pick if e["type"] == "deactivate_trigger"} == {
        "RI Reward bonus1 option 1", "RI Reward bonus1 option 2"}                # the long lines go once picked


def test_completing_an_objective_marks_its_choice_pending_at_once():
    """The last objective mustn't end the mission before its upgrade is picked."""
    ts = by_name(progression.triggers(CAMP, FOLDERS, 1))
    effects = ts["RI Bonus 1"]["effects"]
    assert effects[0]["variable"] == "RI done" and effects[1] == {
        "type": "change_variable", "variable": "RI pending", "operation": "ADD", "quantity": 1}
    assert not any(e.get("variable") == "RI pending" for e in ts["RI Reward bonus1"]["effects"])


def test_buttons_are_short_and_the_objectives_list_explains():
    ts = by_name(progression.triggers(CAMP, FOLDERS, 2))
    offer = ts["RI Reward primary"]["effects"][0]
    assert (offer["message_option1"], offer["message_option2"]) == ("C", "A")
    line = ts["RI Reward primary option 2"]
    assert line["short_description"] == "A: Long A." and not line["enabled"] and line["display_on_screen"]
    assert ts["RI Reward primary option 1"]["short_description"] == "C"
    assert line["description_order"] < ts["RI Reward primary option 1"]["description_order"]
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
    assert camp.missions["01_hunting"]["rewards"] == ["preserved_meat", "town_hearth"]


def test_bonus_setup_runs_on_its_difficulty_and_lists_expand():
    ts = by_name(progression.triggers(CAMP, FOLDERS, 1))
    moderate = [e for e in ts["RI Difficulty moderate 2"]["effects"] if e["type"] not in ("change_variable",
                                                                                          "activate_trigger")]
    assert moderate == [{"type": "create_object", "source_player": 0, "object_list_unit_id": 1029}]
    hard = [e["object_list_unit_id"] for e in ts["RI Difficulty hard 1"]["effects"] if "object_list_unit_id" in e]
    assert hard == [1029, 1301, 333]                                            # Hard: both setups, one per unit


def test_setup_runs_before_the_upgrades_and_is_the_humans():
    camp = progression.Campaign(upgrades=CAMP.upgrades, missions={"01_one": {"rewards": ["a", "b"], "bonus": [
        {"text": "Bare.", "conditions": [], "setup": [
            {"type": "modify_resource", "tribute_list": 0, "operation": "SET", "quantity": 0}]}]}})
    ts = progression.triggers(camp, ["01_one"], 1, player=2)
    names = [t["name"] for t in ts]
    assert names.index("RI Difficulty moderate 2") < names.index("RI Upgrades load")   # perks survive an empty start
    setup = ts[names.index("RI Difficulty moderate 2")]["effects"][-1]
    assert setup["type"] == "modify_resource" and setup["source_player"] == 2


def test_select_resolves_to_the_placed_objects():
    ts = [{"name": "t", "effects": [{"type": "remove_object", "source_player": 1,
                                     "select": {"player": 0, "unit": [59]}}]}]
    progression.select_objects(ts, {0: [(59, 7), (22, 8), (59, 9)], 1: [(59, 10)]})
    assert ts[0]["effects"][0] == {"type": "remove_object", "selected_object_ids": [7, 9], "source_player": 0}


def test_failable_bonus_and_mission_aware_upgrades():
    camp = progression.Campaign(
        upgrades={"stable": {"label": "S", "effects": [
                      {"type": "enable_disable_object", "object_list_unit_id": 101, "enabled": 1,
                       "unless_disabled": ["stable"]}]},
                  "free": {"label": "F", "effects": [{"type": "change_variable", "variable": "v", "quantity": 1}],
                           "triggers": [
                               {"name": "count", "looping": True, "effects": [{"type": "change_variable",
                                                                               "variable": "n", "quantity": 1}]},
                               {"name": "stop", "conditions": [{"type": "variable_value", "variable": "n",
                                                                "quantity": 10}],
                                "effects": [{"type": "deactivate_trigger", "trigger_id": "@count"}]}]}},
        missions={"01_one": {"rewards": ["stable", "free"], "bonus": [
            {"text": "Lose nothing.", "conditions": [], "fail": [
                {"type": "accumulate_attribute", "attribute": 154, "quantity": 1},
                {"type": "accumulate_attribute", "attribute": 227, "quantity": 1}]}]}})
    ts = by_name(progression.triggers(camp, ["01_one"], 1))
    assert ts["RI Upgrade m01_primary 1"]["effects"][0]["type"] == "enable_disable_object"
    assert by_name(progression.triggers(camp, ["01_one"], 1, disabled={"stable"}))[
        "RI Upgrade m01_primary 1"]["effects"] == []                            # the mission takes the Stable away
    free = ts["RI Upgrade m01_primary 2"]["effects"]
    assert {e.get("trigger_id") for e in free} >= {"RI Upgrade m01_primary 2 count", "RI Upgrade m01_primary 2 stop"}
    assert ts["RI Upgrade m01_primary 2 count"]["looping"] and not ts["RI Upgrade m01_primary 2 count"]["enabled"]
    assert ts["RI Upgrade m01_primary 2 stop"]["effects"][0]["trigger_id"] == "RI Upgrade m01_primary 2 count"
    fail = ts["RI Bonus 1 fail 1"]
    assert fail["conditions"][0]["source_player"] == 1 and not fail["enabled"]
    assert [e["type"] for e in fail["effects"]] == ["deactivate_trigger", "deactivate_trigger", "change_variable",
                                                    "display_instructions"]
    assert fail["effects"][2]["operation"] == "SUBTRACT"                      # the mission can still end by itself
    moderate = [e.get("trigger_id") for e in ts["RI Difficulty moderate 2"]["effects"]]
    assert {"RI Bonus 1", "RI Bonus 1 fail 1", "RI Bonus 1 fail 2"} <= set(moderate)
    done = [e.get("trigger_id") for e in ts["RI Bonus 1"]["effects"] if e["type"] == "deactivate_trigger"]
    assert done == ["RI Bonus 1 fail 1", "RI Bonus 1 fail 2"]                 # completing it stops the failing
