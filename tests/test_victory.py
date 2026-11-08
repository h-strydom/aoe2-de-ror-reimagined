"""Mission text, player names, victory mode and objective triggers in the converted scenarios."""
from __future__ import annotations

import pytest
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

from reimagined import layout
from reimagined.aoede import strings
from reimagined.conversion import load
from reimagined.convert import convert_mission

CAMPAIGNS = layout.campaigns()
SET_UP = all(m.scenario_path.is_file() for c in CAMPAIGNS for m in c.missions) and strings.STRINGS_FILE.is_file()
pytestmark = pytest.mark.skipif(not SET_UP, reason="run `reimagined setup` first")


def _convert(tmp_path, campaign: str, mission: str):
    c = next(c for c in CAMPAIGNS if c.slug == campaign)
    m = next(m for m in c.missions if m.folder.name == mission)
    res = convert_mission(m, load(), tmp_path)
    s = AoE2DEScenario.from_file(str(res.out))
    return res, s, {t.name: t for t in s.trigger_manager.triggers}


def test_text_and_names_come_from_the_string_table(tmp_path):
    _, s, _ = _convert(tmp_path, "ascent_of_egypt", "08_religion")
    table = strings.load()
    assert s.message_manager.instructions == table[70080].rstrip()
    assert s.message_manager.history == table[70084].rstrip()
    assert s.player_manager.players[1].tribe_name == "Kingdom of Egypt"


def test_religion_objectives_and_custom_victory(tmp_path):
    res, s, triggers = _convert(tmp_path, "ascent_of_egypt", "08_religion")
    assert res.victory == "CUSTOM" and not res.skipped
    assert triggers["P1 Objective 1"].display_as_objective and triggers["P1 Objective 1"].display_on_screen
    assert triggers["P1 Objective 1"].short_description == "+ Bring the Libyan Raiders' Stone Thrower to the marked area."
    win = triggers["P1 Victory"]
    assert [c.condition_type for c in win.conditions] == [1, 7]       # bring object to area, capture object
    assert win.effects[0].effect_type == 8                           # unlocks ending the mission (progression.py)
    assert "P1 Victory: conquest" in triggers                         # conquest is on, all_custom off


def test_hunting_population_objective(tmp_path):
    res, _, triggers = _convert(tmp_path, "ascent_of_egypt", "01_hunting")
    assert res.victory == "STANDARD"
    [cond] = triggers["P1 Victory"].conditions
    assert (cond.attribute, cond.quantity, cond.source_player) == (11, 7, 1)


def test_enemy_conditions_become_losses(tmp_path):
    _, _, triggers = _convert(tmp_path, "ave_caesar", "03_the_siege_of_alesia")
    for p in (2, 3, 4, 5):                                             # the Gauls win if Caesar dies
        assert triggers[f"P{p} Victory"].effects[0].source_player == p
    assert "P2 Objective 1" not in triggers                            # only the human player's lines show



def test_destroying_a_wonder_that_is_built_later(tmp_path):
    # Nineveh has no Wonder at the start: its AI builds one. "Own fewer than 1" would win at once.
    res, _, triggers = _convert(tmp_path, "voices_of_babylon", "08_the_conquest_of_nineveh")
    assert not res.skipped
    win, armed, met = triggers["P1 Victory"], triggers["P1 Victory armed 1"], triggers["P1 Objective 1 met"]
    objective = triggers["P1 Objective 1"]
    assert not win.enabled and armed.enabled and not met.enabled
    assert objective.enabled and objective.display_on_screen               # on the to-do list from the start
    [tick] = objective.conditions                                          # ticked by the variable "met" sets
    [effect] = met.effects
    assert tick.condition_type == 22 and tick.variable == effect.variable and effect.quantity == 1
    [cond] = armed.conditions
    assert (cond.condition_type, cond.quantity, cond.object_list, cond.source_player) == (3, 1, 276, 2)   # owns one
    assert {e.trigger_id for e in armed.effects} == {win.trigger_id, met.trigger_id}
    [cond] = met.conditions
    assert (cond.condition_type, cond.quantity, cond.object_list, cond.source_player) == (4, 0, 276, 2)
    [cond] = win.conditions
    assert (cond.condition_type, cond.quantity, cond.object_list, cond.source_player) == (4, 0, 276, 2)   # then none


def test_objectives_have_checkboxes_and_counters(tmp_path):
    _, _, triggers = _convert(tmp_path, "ascent_of_egypt", "01_hunting")
    line = triggers["P1 Objective 1"]
    assert line.short_description == "+ Grow your population to 7 (<P1 Objective 1>/7)."   # "+ " draws the box
    [count] = triggers["P1 Objective 1 count"].effects                     # population into the line's variable
    assert triggers["P1 Objective 1 count"].looping and count.effect_type == 86 and count.tribute_list == 11
    _, _, triggers = _convert(tmp_path, "the_rise_of_rome", "01_the_birth_of_rome")
    assert triggers["P1 Objective 1"].short_description.endswith("(<P1 Objective 1>/12).")
    assert sum(1 for n in triggers if n.startswith("P1 Objective 1 count ")) == 12        # one per tower site
    _, _, triggers = _convert(tmp_path, "glory_of_greece", "01_claiming_territory")
    first, second = triggers["P1 Objective 1"], triggers["P1 Objective 2"]
    assert first.description_order > second.description_order               # higher shows higher: first on top
    assert second.short_description == "+ Build 5 Farms (<P1 Objective 2>/5)."


def test_custom_victory_leaves_winning_to_the_triggers(tmp_path):
    """A custom victory checks none of the game's conditions and asks for "All": killing every Libyan in Ascent of
    Egypt 3 mustn't win. Its discoveries (RoR Ruins) count in the Ruins resource."""
    _, s, ts = _convert(tmp_path, "ascent_of_egypt", "03_discoveries")
    gv = s.sections["GlobalVictory"]
    assert gv.conquest_required == 0 and gv.all_custom_conditions_required == 1   # "All", and
    assert gv.artifacts_required == 10                                            # relics no map has
    # Saved like the RoR editor saves: data set 11, and the header byte that otherwise ends the game on the last
    # enemy's defeat at 0.
    assert list(s.sections["FileHeader"].unknown_numbers) == [11] and s.sections["DataHeader"].unknown == bytes(9)
    assert {c.attribute for c in ts["P1 Victory"].conditions} == {14}


def test_added_players_and_mission_units(tmp_path):
    """Egypt 4 adds the Raiders (no AI, enemies), whose guards stand on the map from the start and leave easier
    games by trigger; the waves order them by group."""
    _, s, ts = _convert(tmp_path, "ascent_of_egypt", "04_the_dawn_of_a_new_age")
    assert s.player_manager.active_players == 2 and s.player_manager.players[2].tribe_name == "Raiders"
    assert s.sections["GlobalVictory"].conquest_required == 0
    guards = {u.reference_id for u in s.unit_manager.units[2]}
    assert len(guards) == 8
    gone = set(ts["RI Units from moderate"].effects[0].selected_object_ids) | set(
        ts["RI Units from hard"].effects[0].selected_object_ids)
    assert gone == guards                                                     # Standard: none of them stay
    wave = next(e for e in ts["RI Bonus 2 north attack"].effects if e.effect_type == 30)
    assert len(wave.selected_object_ids) == 4 and set(wave.selected_object_ids) <= guards


def test_mission_ai_and_dropped_objectives(tmp_path):
    """Egypt 6: Lower Egypt plays the mission's own AI per difficulty and wins only by defeating you; the tech
    tree holds for it too. Egypt 5: red's AI sends the landing party (a raid on AI Script Goal 7)."""
    res, _, ts = _convert(tmp_path, "ascent_of_egypt", "06_farming")
    assert "P2 Victory" not in ts and "P1 Victory" in ts
    spec = res.specs[2]
    assert spec["name"] == "Lower Egypt" and set(spec["levels"]) == {"easy", "normal", "hard"}
    assert "grow" not in spec and spec["levels"]["hard"]["raids"]
    assert "Lower Egypt" in res.ai[2] and not [s for s in res.ai_skipped if s.startswith("P2")]
    tree = [e for e in ts["RI Objectives"].effects if e.effect_type == 38 and e.source_player == 2]
    assert tree                                                                   # red's tech tree too
    res5, _, _ = _convert(tmp_path, "ascent_of_egypt", "05_skirmish")
    assert res5.specs[2]["raids"][0]["start"] == {"trigger": 7} and res5.specs[2].get("levels")
