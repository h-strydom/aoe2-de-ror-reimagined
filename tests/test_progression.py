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
    moderate = ts["RI Difficulty moderate"]["effects"]
    assert [e["trigger_id"] for e in moderate if e["type"] == "activate_trigger"] == ["RI Bonus 1"]
    assert moderate[0]["quantity"] == 2
    hard = ts["RI Difficulty hard"]["effects"]
    assert [e["trigger_id"] for e in hard if e["type"] == "activate_trigger"] == ["RI Bonus 1", "RI Bonus 2"]
    assert hard[0]["quantity"] == 3
    # The condition is true at its level or easier: one trigger per band, so a setup runs once.
    assert ts["RI Difficulty moderate"]["conditions"] == [
        {"type": "difficulty_level", "quantity": 2}, {"type": "difficulty_level", "quantity": 3, "inverted": True}]
    assert ts["RI Difficulty hard"]["conditions"] == [{"type": "difficulty_level", "quantity": 2, "inverted": True}]
    assert not any(n.startswith("RI Difficulty hard ") for n in ts)
    assert ts["RI Bonus 2"]["conditions"][0]["source_player"] == 1             # the human's unless given
    assert ts["RI Bonus 1"]["conditions"][0]["source_player"] == 0


def test_rewards_are_stored_per_objective():
    ts = by_name(progression.triggers(CAMP, FOLDERS, 1))
    offer = ts["RI Reward bonus1"]["effects"][0]
    assert offer["type"] == "create_decision" and (offer["message_option1"], offer["message_option2"]) == ("C", "D")
    pick = ts["RI Reward bonus1 pick 2"]["effects"]
    assert pick[0]["variable"] == "RI m01_bonus1" and pick[0]["quantity"] == 2
    assert pick[1] == {"type": "store_key_value", "variable": "RI m01_bonus1", "message": "m01_bonus1"}


def test_completing_an_objective_marks_its_choice_pending_at_once():
    """The last objective mustn't end the mission before its upgrade is picked."""
    ts = by_name(progression.triggers(CAMP, FOLDERS, 1))
    effects = ts["RI Bonus 1"]["effects"]
    assert effects[0]["variable"] == "RI done" and effects[1] == {
        "type": "change_variable", "variable": "RI pending", "operation": "ADD", "quantity": 1}
    assert not any(e.get("variable") == "RI pending" for e in ts["RI Reward bonus1"]["effects"])


def test_buttons_are_short_and_the_scouts_page_explains():
    ts = by_name(progression.triggers(CAMP, FOLDERS, 2))
    offer = ts["RI Reward primary"]["effects"][0]
    assert (offer["message_option1"], offer["message_option2"]) == ("C", "A") and "Scouts" in offer["message"]
    assert not any("option" in name for name in ts)                           # no lines in the objectives list
    page = progression.scouts_text(CAMP, "01_one")
    assert page.splitlines()[0] == progression.SCOUTS_TITLE
    assert "Main objective\n  A: Long A.\n  B" in page
    assert "Bonus objective (Moderate and Hard): Hunt.\n  C\n  D" in page
    assert "Grow." not in page                                                  # bonus 2 offers no reward
    assert progression.scouts_text(CAMP, "99_none") == ""
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
    moderate = [e for e in ts["RI Difficulty moderate"]["effects"] if e["type"] not in ("change_variable",
                                                                                          "activate_trigger")]
    assert moderate == [{"type": "create_object", "source_player": 0, "object_list_unit_id": 1029}]
    hard = [e["object_list_unit_id"] for e in ts["RI Difficulty hard"]["effects"] if "object_list_unit_id" in e]
    assert hard == [1029, 1301, 333]                                            # Hard: both setups, one per unit


def test_setup_runs_before_the_upgrades_and_is_the_humans():
    camp = progression.Campaign(upgrades=CAMP.upgrades, missions={"01_one": {"rewards": ["a", "b"], "bonus": [
        {"text": "Bare.", "conditions": [], "setup": [
            {"type": "modify_resource", "tribute_list": 0, "operation": "SET", "quantity": 0}]}]}})
    ts = progression.triggers(camp, ["01_one"], 1, player=2)
    names = [t["name"] for t in ts]
    assert names.index("RI Difficulty moderate") < names.index("RI Upgrades load")   # perks survive an empty start
    setup = ts[names.index("RI Difficulty moderate")]["effects"][-1]
    assert setup["type"] == "modify_resource" and setup["source_player"] == 2


def test_select_resolves_to_the_placed_objects():
    ts = [{"name": "t", "effects": [{"type": "remove_object", "source_player": 1,
                                     "select": {"player": 0, "unit": [59]}}]}]
    progression.select_objects(ts, {0: [(59, 7), (22, 8), (59, 9)], 1: [(59, 10)]})
    assert ts[0]["effects"][0] == {"type": "remove_object", "selected_object_ids": [7, 9], "source_player": 0}


def test_failable_bonus_and_upgrade_triggers():
    camp = progression.Campaign(
        upgrades={"stable": {"label": "S", "effects": [
                      {"type": "enable_disable_object", "object_list_unit_id": 101, "enabled": 1}]},
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
    free = ts["RI Upgrade m01_primary 2"]["effects"]
    assert {e.get("trigger_id") for e in free} >= {"RI Upgrade m01_primary 2 count", "RI Upgrade m01_primary 2 stop"}
    assert ts["RI Upgrade m01_primary 2 count"]["looping"] and not ts["RI Upgrade m01_primary 2 count"]["enabled"]
    assert ts["RI Upgrade m01_primary 2 stop"]["effects"][0]["trigger_id"] == "RI Upgrade m01_primary 2 count"
    fail = ts["RI Bonus 1 fail 1"]
    assert fail["conditions"][0]["source_player"] == 1 and not fail["enabled"]
    assert [e["type"] for e in fail["effects"]] == ["deactivate_trigger", "deactivate_trigger", "change_variable",
                                                    "display_instructions"]
    assert fail["effects"][2]["operation"] == "SUBTRACT"                      # the mission can still end by itself
    moderate = [e.get("trigger_id") for e in ts["RI Difficulty moderate"]["effects"]]
    assert {"RI Bonus 1", "RI Bonus 1 fail 1", "RI Bonus 1 fail 2"} <= set(moderate)
    done = [e.get("trigger_id") for e in ts["RI Bonus 1"]["effects"] if e["type"] == "deactivate_trigger"]
    assert done == ["RI Bonus 1 fail 1", "RI Bonus 1 fail 2"]                 # completing it stops the failing


def test_a_slot_applies_one_upgrade_per_mission():
    """Re-picking a slot's other option in its own mission mustn't stack both: each option switches the other off."""
    ts = by_name(progression.triggers(CAMP, FOLDERS, 1))
    one, two = ts["RI Upgrade m01_primary 1"]["effects"], ts["RI Upgrade m01_primary 2"]["effects"]
    assert one[-1] == {"type": "deactivate_trigger", "trigger_id": "RI Upgrade m01_primary 2"}
    assert two[-1] == {"type": "deactivate_trigger", "trigger_id": "RI Upgrade m01_primary 1"}


def test_mission_setup_players_units_and_bonus_triggers():
    camp = progression.Campaign(upgrades=CAMP.upgrades, missions={"01_one": {
        "players": [{"number": 2, "name": "Raiders", "civ": "EGYPTIAN"}],
        "units": [{"player": 2, "unit": 281, "x": 1, "y": 1, "from": "moderate", "group": "north"},
                  {"player": 2, "unit": 4, "x": 2, "y": 1, "from": "hard", "group": "north"}],
        "setup": [{"type": "enable_disable_object", "object_list_unit_id": [50, 72], "enabled": 0}],
        "rewards": ["a", "b"], "bonus": [{"text": "Rise.", "conditions": [], "triggers": [
            {"name": "wave", "effects": [{"type": "attack_move", "select": {"group": "north"}},
                                         {"type": "activate_trigger", "trigger_id": "@later"}]},
            {"name": "later", "conditions": [{"type": "timer", "timer": 60}], "effects": []}]}]}})
    assert progression.extra_players(camp, "01_one")[0]["name"] == "Raiders"
    assert [u["unit"] for u in progression.mission_units(camp, "01_one")] == [281, 4]
    ts = progression.triggers(camp, ["01_one"], 1)
    groups = {"north": (2, [7, 8]), "from moderate": (2, [7]), "from hard": (2, [8])}
    progression.select_objects(ts, {}, groups)
    ts = by_name(ts)
    setup = [e["object_list_unit_id"] for e in ts["RI Objectives"]["effects"] if "object_list_unit_id" in e]
    assert setup == [50, 72]                                                  # every difficulty, before upgrades
    # Units leave easier games: Moderate's on Standard or easier, Hard's on Moderate or easier.
    assert ts["RI Units from moderate"]["conditions"] == [{"type": "difficulty_level", "quantity": 3}]
    assert ts["RI Units from moderate"]["effects"][0]["selected_object_ids"] == [7]
    assert ts["RI Units from hard"]["conditions"] == [{"type": "difficulty_level", "quantity": 2}]
    wave = ts["RI Bonus 1 wave"]["effects"][0]
    assert wave["selected_object_ids"] == [7, 8] and wave["source_player"] == 2   # the group's owner, not the human
    started = {e.get("trigger_id") for e in ts["RI Difficulty moderate"]["effects"]}
    assert "RI Bonus 1 wave" in started and "RI Bonus 1 later" not in started   # "later" waits for "wave"
    assert not ts["RI Bonus 1 wave"]["enabled"]
    assert ts["RI Bonus 1 wave"]["effects"][1]["trigger_id"] == "RI Bonus 1 later"


def test_tech_tree_unlocks_build_up_and_stop_after_the_last_listed_mission(tmp_path):
    camp = progression.Campaign(upgrades=CAMP.upgrades, missions={},
                                unlocks={"01_one": ["house", "villager"], "02_two": ["barracks"]})
    folders = ["01_one", "02_two", "03_three"]
    on = lambda n: {e.get("object_list_unit_id") or e.get("technology")             # noqa: E731
                    for e in progression.tree_effects(camp, folders, n) if e["enabled"]}
    assert on(1) == {70, 463, 464, 465, 83}
    assert {12, 70, 83} <= on(2) and 281 not in on(2)                             # cumulative; Clubmen still off
    off = {e["object_list_unit_id"] for e in progression.tree_effects(camp, folders, 2)
           if e["type"] == "enable_disable_object" and not e["enabled"]}
    assert {50, 72, 87} <= off                                                    # Farm, walls, Archery Range
    assert progression.tree_effects(camp, folders, 3) == []                      # not designed yet: as it was
    (tmp_path / "x.yaml").write_text("unlocks: {01_one: [castle]}\n")
    with pytest.raises(ValueError, match="no 'castle'"):
        progression.load("x", tmp_path)


def test_primary_extra_gates_ending_from_its_difficulty():
    camp = progression.Campaign(upgrades=CAMP.upgrades, missions={"01_one": {
        "rewards": ["a", "b"], "primary_extra": {"text": "Defeat them.", "from": "moderate", "conditions": [
            {"type": "own_fewer_objects", "source_player": 2, "object_group": 6, "quantity": 0}]}}})
    ts = by_name(progression.triggers(camp, ["01_one"], 1))
    extra = ts["RI Primary extra"]
    assert not extra["enabled"] and extra["short_description"] == "+ Defeat them."
    for level in ("moderate", "hard"):
        effects = ts[f"RI Difficulty {level}"]["effects"]
        assert {"type": "activate_trigger", "trigger_id": "RI Primary extra"} in effects
        assert any(e.get("variable") == "RI primary gate" and e["quantity"] == 1 for e in effects)
    assert {"type": "variable_value", "variable": "RI primary gate", "comparison": "EQUAL", "quantity": 0} in \
        ts["RI Primary complete"]["conditions"]                                 # Standard: the gate stays open


def test_group_conditions_keep_the_attacker_and_use_each_units_full_health():
    ts = [{"name": "t", "conditions": [
        {"type": "object_attacked", "select": {"group": "g"}, "source_player": 1, "quantity": 1},
        {"type": "or"},
        {"type": "object_hp", "select": {"group": "g"}, "comparison": "LESS", "quantity": "full"},
        {"type": "or"},
        {"type": "destroy_object", "select": {"group": "g"}}], "effects": []}]
    progression.select_objects(ts, {}, {"g": (2, [7, 8])}, {7: 40, 8: 35})
    c = ts[0]["conditions"]
    assert [x["type"] for x in c] == ["object_attacked", "or", "object_attacked", "or", "object_hp", "or",
                                      "object_hp", "or", "destroy_object", "or", "destroy_object"]
    assert c[0]["source_player"] == 1 and c[0]["unit_object"] == 7               # the attacker, as given
    assert (c[4]["quantity"], c[6]["quantity"]) == (40, 35)                      # each unit's own full health
    assert "source_player" not in c[8]                                           # destroy_object takes none


def test_lists_of_classes_expand():
    effects = progression.expand([{"type": "modify_attribute_for_class", "object_group2": [6, 0], "quantity": 1}])
    assert [e["object_group2"] for e in effects] == [6, 0]
