"""Reimagined progression: missions go on after the primary objective, bonus objectives by difficulty, and
permanent upgrades chosen on completing objectives, kept in the campaign bank.

Difficulty (the game's, as the campaign offers it): Standard has the primary objective only; Moderate adds the
first bonus objective; Hard (and Hardest/Extreme) add the second too. The bonus lines show as optional ("- ").

Completing the primary objective doesn't end the mission: a popup says so and an "End Mission" tech appears at the
Town Center, which ends the mission in victory the moment its research starts. Missions where the player can't
build (no villager or Town Center at the start) offer a popup instead, again five minutes after each "keep
playing". Losing still works as before. Once every objective on the difficulty is done, the mission ends by itself
after any pending upgrade choice.

A bonus objective may change the mission when its difficulty shows it (`setup` effects: more predators, a
tougher quarry...); Hard runs both bonus objectives' setups.

Each objective may offer a choice of two upgrades (the game's decision popup). The pick is stored in the campaign
bank under the objective's slot ("m01_primary", "m01_bonus1"...), and every mission of the campaign loads every
slot at its start and applies the chosen upgrades. One slot per objective: replaying it lets the player re-pick,
never stack (the game asks on a replay whether to keep the new choices).

The content (bonus objectives, upgrades, which objective offers which) lives in aoe2de_ror/reimagined/<campaign>.yaml.

End Mission uses RoR tech 153 "Dupl. Stone Age": no effect, no building, and its only prerequisite is the Stone
Age, so the game researches it by itself at the start. Re-enabled with stacking (researchable again), moved to the
Town Center (109; RoR's own age techs live there and show in every age) and renamed. Its *research starting* ends
the mission (condition researching_tech), as "researched" is true from the start. Every tech a civ can't otherwise
research needs the Tool Age or later, which rules those out for the early missions (RoR tech trees, 2026-11-07).
Unverified in game.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import layout

DATA = layout.AOE2DE_ROR / "reimagined"
END_TECH, END_LOCATION, END_BUTTON, END_SECONDS = 153, 109, 10, 5
DIFFICULTY = {"moderate": [2], "hard": [1, 0, -1]}          # the Difficulty Level condition's values (equality)
SLOTS = ("primary", "bonus1", "bonus2")
REOFFER_SECONDS = 300
PRIMARY_TEXT = ("Primary objective complete! Research End Mission at your Town Center to claim victory whenever you "
                "like, or keep playing for the bonus objectives.")
PRIMARY_TEXT_NO_TC = "Primary objective complete! You can end the mission now, or keep playing for the bonus objectives."
CHOOSE = "Choose a permanent upgrade for this campaign (details in your objectives):"
OBJECTIVE_ORDER_OFFSET = 10      # primary lines above the bonus lines (higher display order shows higher)
BONUS_ORDER = 3                  # bonus lines (orders 4, 3), then a pending choice's two options (2, 1)
CHOICE_ORDER = 1


@dataclass
class Campaign:
    upgrades: dict[str, dict] = field(default_factory=dict)
    missions: dict[str, dict] = field(default_factory=dict)     # mission folder name -> {rewards, bonus}


def load(slug: str, root: Path = DATA) -> Campaign:
    path = root / f"{slug}.yaml"
    if not path.is_file():
        return Campaign()
    spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    camp = Campaign(spec.get("upgrades") or {}, spec.get("missions") or {})
    problems = []
    for name, m in camp.missions.items():
        offers = [("primary", m.get("rewards"))] + [(f"bonus{k}", b.get("rewards"))
                                                    for k, b in enumerate(m.get("bonus") or [], 1)]
        for slot, pair in offers:
            if pair is not None and (len(pair) != 2 or any(u not in camp.upgrades for u in pair)):
                problems.append(f"{slug}/{name} {slot}: rewards are two upgrade keys from `upgrades`, got {pair}")
        if len(m.get("bonus") or []) > 2:
            problems.append(f"{slug}/{name}: at most two bonus objectives (Moderate, Hard)")
    if problems:
        raise ValueError("; ".join(problems))
    return camp


def slot_key(number: int, slot: str) -> str:
    return f"m{number:02d}_{slot}"


def _slots(camp: Campaign, folders: list[str]) -> list[tuple[str, list[str]]]:
    """(bank key, [upgrade for option 1, option 2]) for every reward slot of the campaign."""
    out = []
    for n, folder in enumerate(folders, start=1):
        m = camp.missions.get(folder) or {}
        if m.get("rewards"):
            out.append((slot_key(n, "primary"), m["rewards"]))
        for k, b in enumerate(m.get("bonus") or [], start=1):
            if b.get("rewards"):
                out.append((slot_key(n, f"bonus{k}"), b["rewards"]))
    return out


def upgrade_line(up: dict) -> str:
    """An upgrade's line in the objectives list: its short label (the popup button) and what it does."""
    return f"{up['label']}: {up['text']}" if up.get("text") else up["label"]


def expand(effects: list[dict]) -> list[dict]:
    """One effect per unit (or tech) when an effect's object_list_unit_id (or technology) lists several."""
    out = []
    for e in effects:
        key = next((k for k in LIST_KEYS if isinstance(e.get(k), list)), None)
        out.extend([{**e, key: v} for v in e[key]] if key else [e])
    return out


LIST_KEYS = ("object_list_unit_id", "technology")


def _player(effects: list[dict], player: int) -> list[dict]:
    """Effects act for `player` unless they name one; effects without a player (variables, triggers) stay as they are."""
    return [e if e["type"] in _NO_PLAYER else {"source_player": player, **e} for e in effects]


# Effects without a source_player (aoe-agent-editor's effect reference).
_NO_PLAYER = {"change_variable", "activate_trigger", "deactivate_trigger", "create_decision", "load_key_value",
              "store_key_value", "delete_key", "modify_variable_by_variable", "clear_timer", "display_timer",
              "clear_instructions", "change_color_mood", "script_call", "ai_script_goal"}


def triggers(camp: Campaign, folders: list[str], number: int, *, player: int = 1,
             town_center: bool = True) -> list[dict]:
    """The progression triggers for mission `number` (1-based) of a campaign whose missions are `folders`. The
    human player's victory triggers must activate "RI Primary complete" instead of winning (hand_over).
    Upgrades trump the mission's own settings (an upgrade enabling the Stable enables it where a mission doesn't)."""
    out: list[dict] = []
    m = camp.missions.get(folders[number - 1]) or {}
    bonus = m.get("bonus") or []

    def own(conds: list[dict]) -> list[dict]:
        """Conditions about a player are the human's unless they say otherwise."""
        return [{"source_player": player, **c} if c["type"] in _PLAYER_CONDITIONS else c for c in conds]

    def own_triggers(prefix: str, specs: list[dict]) -> list[str]:
        """Content's own triggers (an upgrade's, a bonus objective's), named "<prefix> <name>", off until the
        owner turns them on; trigger_id "@<name>" points at a sibling. Returns their names."""
        names = []
        for t in specs:
            name = f"{prefix} {t['name']}"
            out.append({"name": name, "enabled": False, "looping": bool(t.get("looping")),
                        "conditions": own(t.get("conditions") or []),
                        "effects": _player([{**e, "trigger_id": f"{prefix} {e['trigger_id'][1:]}"}
                                            if str(e.get("trigger_id", "")).startswith("@") else e
                                            for e in expand(t.get("effects") or [])], player)})
            names.append(name)
        return names

    # The mission's own settings on every difficulty (`setup`), how many objectives this difficulty has (primary +
    # bonuses), showing its bonus lines and running their setup and triggers (for the human player unless an
    # effect says otherwise). All before the upgrades: a setup that empties the stockpile leaves what upgrades add,
    # and an upgrade enabling what the mission disables wins.
    out.append({"name": "RI Objectives", "effects": [
        {"type": "change_variable", "variable": "RI objectives", "operation": "SET", "quantity": 1},
        *_player(expand(m.get("setup") or []), player)]})
    for p_ in m.get("keep_alive") or []:
        # A hidden marker the converter places keeps the player in the game, e.g. an added player with no units
        # on Standard. (Winning on the last enemy's defeat is the victory options' business: victory.py.)
        marker = {"select": {"marker": p_}}
        out.append({"name": f"RI Keep P{p_}", "effects": [
            {"type": "disable_unit_attackable", **marker}, {"type": "disable_object_selection", **marker},
            {"type": "change_object_visibility", "target_player": player, "visibility_state": "INVISIBLE",
             **marker}]})
    bonus_triggers = {k: own_triggers(f"RI Bonus {k}", b.get("triggers") or []) for k, b in enumerate(bonus, 1)}
    levels = [("moderate", bonus[:1]), ("hard", bonus[:2])]
    for level, shown in levels:
        if not shown:
            continue
        for q in DIFFICULTY[level]:
            out.append({"name": f"RI Difficulty {level} {q}", "conditions": [
                {"type": "difficulty_level", "quantity": q}], "effects": [
                {"type": "change_variable", "variable": "RI objectives", "operation": "SET", "quantity": 1 + len(shown)},
                *({"type": "activate_trigger", "trigger_id": name} for k, b in enumerate(shown, start=1)
                  for name in [f"RI Bonus {k}", *_fail_names(k, b), *bonus_triggers[k]]),
                *_player([e for b in shown for e in expand(b.get("setup") or [])], player)]})

    # Upgrades earned anywhere in the campaign: load every slot, apply the chosen option. A slot gives one upgrade
    # per mission: applying an option switches the other off, so re-picking a slot (replaying its mission) can't
    # add the second on top of the first; the new pick counts from the next mission (an upgrade can't be undone).
    slots = _slots(camp, folders)
    if slots:
        out.append({"name": "RI Upgrades load", "effects": [
            {"type": "load_key_value", "variable": f"RI {key}", "message": key, "quantity": 0} for key, _ in slots]})
        for key, pair in slots:
            for opt, up in enumerate(pair, start=1):
                name = f"RI Upgrade {key} {opt}"
                apply = {"name": name, "conditions": [
                    {"type": "variable_value", "variable": f"RI {key}", "comparison": "EQUAL", "quantity": opt}]}
                out.append(apply)
                # An upgrade's own triggers (e.g. watching for when a bonus runs out) start with it.
                extra = own_triggers(name, camp.upgrades[up].get("triggers") or [])
                apply["effects"] = (_player(expand(camp.upgrades[up].get("effects") or []), player)
                                    + [{"type": "activate_trigger", "trigger_id": t} for t in extra]
                                    + [{"type": "deactivate_trigger", "trigger_id": f"RI Upgrade {key} {3 - opt}"}])

    def reward(slot: str, pair: list[str] | None, decision: int) -> list[dict]:
        """Effects that offer slot's choice, and the triggers behind it. The choice counts as pending in the same
        trigger that completes the objective, so "RI All done" can't end the mission before it's picked. The popup's
        buttons carry the short labels; while it's up, each option's full text shows in the objectives list."""
        if not pair:
            return []
        key = slot_key(number, slot)
        offer = f"RI Reward {slot}"
        infos = [f"{offer} option {opt}" for opt in (1, 2)]
        out.append({"name": offer, "enabled": False, "effects": [
            {"type": "create_decision", "decision_id": decision, "message": CHOOSE,
             "message_option1": camp.upgrades[pair[0]]["label"], "message_option2": camp.upgrades[pair[1]]["label"]}]})
        for opt, (up, info) in enumerate(zip(pair, infos, strict=True), start=1):
            line = upgrade_line(camp.upgrades[up])
            out.append({"name": info, "enabled": False, "display_as_objective": True, "display_on_screen": True,
                        "description": line, "short_description": line, "description_order": CHOICE_ORDER + 2 - opt,
                        "conditions": [{"type": "variable_value", "variable": "RI never", "comparison": "EQUAL",
                                        "quantity": 1}]})
        for opt in (1, 2):
            out.append({"name": f"{offer} pick {opt}", "conditions": [
                {"type": "decision_triggered", "decision_id": decision, "decision_option": opt}], "effects": [
                {"type": "change_variable", "variable": f"RI {key}", "operation": "SET", "quantity": opt},
                {"type": "store_key_value", "variable": f"RI {key}", "message": key},
                *({"type": "deactivate_trigger", "trigger_id": info} for info in infos),
                {"type": "change_variable", "variable": "RI pending", "operation": "SUBTRACT", "quantity": 1}]})
        return [{"type": "change_variable", "variable": "RI pending", "operation": "ADD", "quantity": 1},
                {"type": "activate_trigger", "trigger_id": offer},
                *({"type": "activate_trigger", "trigger_id": info} for info in infos)]

    # Bonus objectives: optional lines, off until the difficulty shows them. A bonus with `fail` conditions (each
    # one alone fails it) can be lost: its line goes, a message says so, and it no longer counts toward ending.
    for k, b in enumerate(bonus, start=1):
        text = b["text"]
        fails = _fail_names(k, b)
        out.append({"name": f"RI Bonus {k}", "enabled": False, "display_as_objective": True, "display_on_screen": True,
                    "description": f"- {text}", "short_description": f"- {text}", "description_order": BONUS_ORDER + 2 - k,
                    "conditions": own(b["conditions"]), "effects": [
                        {"type": "change_variable", "variable": "RI done", "operation": "ADD", "quantity": 1},
                        *reward(f"bonus{k}", b.get("rewards"), 10 + k),
                        *({"type": "deactivate_trigger", "trigger_id": f} for f in fails)]})
        for name, cond in zip(fails, b.get("fail") or [], strict=True):
            out.append({"name": name, "enabled": False, "conditions": own([cond]), "effects": [
                {"type": "deactivate_trigger", "trigger_id": f"RI Bonus {k}"},
                *({"type": "deactivate_trigger", "trigger_id": f} for f in fails if f != name),
                {"type": "change_variable", "variable": "RI objectives", "operation": "SUBTRACT", "quantity": 1},
                {"type": "display_instructions", "display_time": 10, "message": f"Bonus objective failed: {text}"}]})

    # The primary objective: what used to win the mission now unlocks ending it.
    unlock: list[dict] = []
    if town_center:
        unlock = [
            {"type": "enable_disable_technology", "technology": END_TECH, "enabled": 1},
            {"type": "enable_technology_stacking", "technology": END_TECH},
            {"type": "change_technology_location", "technology": END_TECH, "object_list_unit_id_2": END_LOCATION,
             "button_location": END_BUTTON},
            {"type": "change_technology_name", "technology": END_TECH, "message": "End Mission"},
            {"type": "change_technology_description", "technology": END_TECH,
             "message": "Claim victory and end the mission."},
            {"type": "change_technology_research_time", "technology": END_TECH, "quantity": END_SECONDS},
            {"type": "activate_trigger", "trigger_id": "RI End Mission"}]
        out.append({"name": "RI End Mission", "enabled": False, "conditions": [
            {"type": "researching_tech", "technology": END_TECH}], "effects": [
            {"type": "declare_victory", "enabled": True}]})
    else:
        out.append({"name": "RI End offer", "enabled": False, "effects": [
            {"type": "create_decision", "decision_id": 20, "message": "End the mission now?",
             "message_option1": "Claim victory", "message_option2": "Keep playing"}]})
        out.append({"name": "RI End offer claim", "conditions": [
            {"type": "decision_triggered", "decision_id": 20, "decision_option": 1}],
            "effects": [{"type": "declare_victory", "enabled": True}]})
        out.append({"name": "RI End offer later", "looping": True, "conditions": [
            {"type": "decision_triggered", "decision_id": 20, "decision_option": 2}],
            "effects": [{"type": "activate_trigger", "trigger_id": "RI End offer again"}]})
        out.append({"name": "RI End offer again", "enabled": False, "looping": False, "conditions": [
            {"type": "timer", "timer": REOFFER_SECONDS}], "effects": [
            {"type": "activate_trigger", "trigger_id": "RI End offer"}]})
        unlock = [{"type": "activate_trigger", "trigger_id": "RI End offer"}]
    # Several triggers may win (the objectives, conquest...): the first one counts.
    out.append({"name": "RI Primary complete", "enabled": False, "conditions": [
        {"type": "variable_value", "variable": "RI primary", "comparison": "EQUAL", "quantity": 0}], "effects": [
        {"type": "change_variable", "variable": "RI primary", "operation": "SET", "quantity": 1},
        {"type": "change_variable", "variable": "RI done", "operation": "ADD", "quantity": 1},
        {"type": "display_instructions", "display_time": 15,
         "message": PRIMARY_TEXT if town_center else PRIMARY_TEXT_NO_TC},
        *unlock, *reward("primary", m.get("rewards"), 1),
        {"type": "activate_trigger", "trigger_id": "RI All done"}]})

    # Everything on this difficulty done, no choice pending: the mission ends.
    out.append({"name": "RI All done", "enabled": False, "conditions": [
        {"type": "compare_variables", "variable": "RI done", "comparison": "LARGER_OR_EQUAL",
         "variable2": "RI objectives"},
        {"type": "variable_value", "variable": "RI pending", "comparison": "EQUAL", "quantity": 0}],
        "effects": [{"type": "declare_victory", "enabled": True}]})
    return _player_all(out, player)


def _fail_names(k: int, b: dict) -> list[str]:
    return [f"RI Bonus {k} fail {i}" for i in range(1, len(b.get("fail") or []) + 1)]


# Conditions whose source_player is the human player unless the content says otherwise.
_PLAYER_CONDITIONS = {"accumulate_attribute", "own_objects", "own_fewer_objects", "objects_in_area",
                      "research_technology", "researching_tech", "player_defeated"}
_PLAYER_EFFECTS = {"enable_disable_technology", "enable_technology_stacking", "change_technology_location",
                   "change_technology_name", "change_technology_description", "change_technology_research_time",
                   "declare_victory", "display_instructions"}


def _player_all(triggers_: list[dict], player: int) -> list[dict]:
    for t in triggers_:
        t["effects"] = [{"source_player": player, **e} if e["type"] in _PLAYER_EFFECTS else e
                        for e in t.get("effects") or []]
    return triggers_


def select_objects(triggers_: list[dict], placed: dict[int, list[tuple[int, int]]],
                   markers: dict[int, int] | None = None) -> None:
    """Resolve setup effects' `select: {player, unit}` (unit: an id or a list) into selected_object_ids: the objects
    of those units the map places for that player. `placed` is player -> [(unit id, reference id)].
    `select: {marker: player}` is that player's keep-alive marker (`markers`: player -> reference id).
    remove_object by unit type over an area left Gaia's forage bushes in place (Egypt 2 playtest, 2026-11-07);
    remove_object on selected objects works (aoe-agent-editor's fog block)."""
    for t in triggers_:
        for e in t.get("effects") or []:
            sel = e.pop("select", None)
            if sel is None:
                continue
            if "marker" in sel:
                e["selected_object_ids"] = [(markers or {})[sel["marker"]]]
                e["source_player"] = sel["marker"]
                continue
            units = sel["unit"] if isinstance(sel["unit"], list) else [sel["unit"]]
            e["selected_object_ids"] = [ref for unit, ref in placed.get(sel.get("player", 0), []) if unit in units]
            e["source_player"] = sel.get("player", 0)        # the objects' owner, over the human default


def extra_players(camp: Campaign, folder: str) -> list[dict]:
    """Players a mission adds ({number, name, civ}: a RoR civ name), enemies of everyone, without an AI: they act
    through the mission's triggers. Mission content: `players: [...]`."""
    return list((camp.missions.get(folder) or {}).get("players") or [])


def keep_alive(camp: Campaign, folder: str) -> list[int]:
    """Players that keep a hidden marker so they're never defeated outright (`keep_alive: [player]`)."""
    return list((camp.missions.get(folder) or {}).get("keep_alive") or [])


def hand_over(plan_triggers: list[dict], player: int) -> list[str]:
    """Turn the human player's victory triggers into unlocking the end of the mission ("RI Primary complete"),
    and move their objective lines above the bonus lines. Returns the changed triggers' names."""
    changed = []
    for t in plan_triggers:
        effects = t.get("effects") or []
        if any(e.get("type") == "declare_victory" and e.get("source_player") == player for e in effects):
            t["effects"] = [{"type": "activate_trigger", "trigger_id": "RI Primary complete"}
                            if e.get("type") == "declare_victory" and e.get("source_player") == player else e
                            for e in effects]
            changed.append(t["name"])
        if t.get("display_on_screen"):
            t["description_order"] = t.get("description_order", 0) + OBJECTIVE_ORDER_OFFSET
    return changed
