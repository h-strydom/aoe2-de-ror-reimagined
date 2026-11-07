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
    assert triggers["P1 Objective 1"].short_description == "Bring the Stone Thrower to the marked area."
    win = triggers["P1 Victory"]
    assert [c.condition_type for c in win.conditions] == [1, 7]       # bring object to area, capture object
    assert win.effects[0].source_player == 1
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
