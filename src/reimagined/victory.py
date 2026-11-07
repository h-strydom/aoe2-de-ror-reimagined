"""AoE DE victory settings and objectives -> RoR scenario options and triggers.

AoE DE scenarios have no triggers: a mission is won through its global victory settings and each
player's individual victory conditions (aoede.scenario.VictoryCondition). AoE2/RoR has neither, so:

  - the victory mode maps one to one (standard, conquest, score, time, custom);
  - each player with individual conditions gets a "P<n> Victory" trigger: all their conditions at
    once -> declare victory for that player. An enemy's conditions (Caesar must die) so become a loss;
  - the human player's conditions also show as objective lines, on screen (the game's to-do list) and in the
    objectives panel, that tick off when met;
  - in custom mode, the global settings (conquest, artifacts, ruins, discoveries, exploration, gold)
    are extra ways to win; with "all custom conditions required" they join the victory trigger instead.

Individual conditions are always all required: Foraging (all_custom off) needs all three buildings.

"Destroy N" of objects the target doesn't own yet would be met from the first second as "own fewer":
Nineveh builds the Wonder you must destroy (Voices of Babylon 8 was won at once). Such a condition waits
for the objects: an "armed" trigger fires once the target owns them and turns the objective and victory
triggers on, which start off. Several of them arm one after another. "Destroy all" stays "own none", met
when there are none from the start: AoE1 counts them so too (Yamato 1's Jomon win when Xu Fu dies, though
he never owns some of the soldier types they must kill).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .aoede.names import object_name
from .aoede.scenario import VICTORY_MODES, Scenario, VictoryCondition
from .conversion import Conversion

ROR_VICTORY = {"standard": "STANDARD", "conquest": "CONQUEST", "score": "SCORE", "time": "TIME_LIMIT",
               "custom": "CUSTOM"}
# Global victory settings -> the RoR attribute (resource) that counts them; AoE2 kept AoE1's resource ids.
GLOBAL_ATTRIBUTES = {"artifacts": 7, "ruins": 14, "discoveries": 13, "exploration": 22, "gold": 3}
# AoE DE's Discovery has no RoR object: conversion.yaml places RoR's Ruins (52) instead, which the game counts in
# Ruins (14). Capturing them left Discoveries (13) at 0 in game (Ascent of Egypt 3 playtest, 2026-11-07).
RESOURCE = {13: 14}
GLOBAL_ATTRIBUTES = {k: RESOURCE.get(v, v) for k, v in GLOBAL_ATTRIBUTES.items()}
CURRENT_AGE = 6
# AoE DE's "advance to the Tool Age" asks for current age 2 (Ascent of Egypt 4); RoR counts the Stone
# Age as 0, so the Tool Age is 1. Unverified in game.
AGE_OFFSET = -1
ENEMY = 3


@dataclass
class Condition:
    cond: dict
    arm: dict | None = None                           # met once there is something to destroy (None: from the start)


@dataclass
class VictoryPlan:
    mode: str                                         # RoR VictoryCondition name
    triggers: list[dict] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)  # conditions that point at objects the conversion dropped
    # The Custom victory's Conquest checkbox (on by default in the scenario file): the original's setting. Left on,
    # killing every Libyan won Ascent of Egypt 3 although AoE DE's custom victory there has no conquest.
    conquest: bool = True


def _area(c: VictoryCondition) -> list[int]:
    return [int(v) for v in c.area]


def _condition(c: VictoryCondition, owner: int, src: Scenario, conv: Conversion, refs: dict[int, int],
               start_counts: Counter) -> tuple[Condition | dict | None, str | None]:
    """(RoR trigger condition, problem) for one AoE DE victory condition of player `owner`."""
    def ref(uid: int) -> int | None:
        return refs.get(uid)

    obj = conv.objects[c.object_type].ror_id if c.object_type > 0 and c.object_type in conv.objects else None
    if c.object_type > 0 and obj is None:
        return None, f"{object_name(c.object_type)} is dropped by the conversion"
    for uid in (c.source, c.target):
        if uid >= 0 and ref(uid) is None:
            return None, f"unit #{uid} isn't in the converted map"
    t = c.type
    if t == "capture":
        return {"type": "capture_object", "unit_object": ref(c.target), "source_player": owner}, None
    if t == "create":
        return {"type": "own_objects", "quantity": c.number, "object_list": obj, "source_player": owner}, None
    if t == "destroy":
        return {"type": "destroy_object", "unit_object": ref(c.target)}, None
    if t == "destroy_multiple":
        if obj is None:
            return {"type": "own_fewer_objects", "quantity": 0, "source_player": c.player}, None
        start = start_counts[(c.player, c.object_type)]
        if start < c.number:
            return Condition({"type": "own_fewer_objects", "quantity": 0, "object_list": obj, "source_player": c.player},
                             {"type": "own_objects", "quantity": c.number, "object_list": obj,
                              "source_player": c.player}), None
        return {"type": "own_fewer_objects", "quantity": start - c.number, "object_list": obj,
                "source_player": c.player}, None
    if t == "bring_to_area":
        return {"type": "bring_object_to_area", "unit_object": ref(c.source), "area": _area(c)}, None
    if t == "bring_to_object":
        return {"type": "bring_object_to_object", "unit_object": ref(c.source), "next_object": ref(c.target)}, None
    if t == "attribute":
        amount = c.amount + AGE_OFFSET if c.number == CURRENT_AGE else c.amount
        return {"type": "accumulate_attribute", "attribute": RESOURCE.get(c.number, c.number), "quantity": amount,
                "source_player": owner}, None
    if t == "create_in_area":
        return {"type": "objects_in_area", "quantity": c.number, "object_list": obj, "source_player": owner,
                "area": _area(c)}, None
    if t == "destroy_all":
        return {"type": "own_fewer_objects", "quantity": 0, "object_list": obj, "source_player": c.player}, None
    if t == "destroy_player":
        return {"type": "player_defeated", "source_player": c.player}, None
    return None, f"no RoR condition for '{t}'"


MAX_COUNTED = 30          # "Build 5 Farms" counts with a trigger per step; larger counts show no counter


def _counter(name: str, conds: list[dict], player: int, armed: bool) -> tuple[int, list[dict]] | None:
    """(target, triggers) for an objective line's progress counter, which the line shows as "(<name>/target)":
    looping triggers keep the variable `name` current. The game's own campaigns count this way ("+ <Variable 1>/4
    Chinese factions defeated."). Several conditions count how many are met; a resource goal (population, food,
    discoveries...) is the player's amount; "own" or "in area" goals count objects up to the target."""
    if armed or not conds:
        return None
    loop = {"looping": True}
    if len(conds) > 1:
        return len(conds), [
            {"name": f"{name} count", **loop, "effects": [
                {"type": "change_variable", "variable": name, "operation": "SET", "quantity": 0}]},
            *({"name": f"{name} count {k + 1}", **loop, "conditions": [c], "effects": [
                {"type": "change_variable", "variable": name, "operation": "ADD", "quantity": 1}]}
              for k, c in enumerate(conds))]
    [c] = conds
    if c["type"] == "accumulate_attribute" and c["attribute"] != CURRENT_AGE:
        return c["quantity"], [{"name": f"{name} count", **loop, "effects": [
            {"type": "modify_variable_by_resource", "tribute_list": c["attribute"], "source_player": player,
             "operation": "SET", "variable": name}]}]
    if c["type"] in ("own_objects", "objects_in_area") and 1 < c["quantity"] <= MAX_COUNTED:
        steps = [{"name": f"{name} count", **loop, "effects": [
            {"type": "change_variable", "variable": name, "operation": "SET", "quantity": 0}]}]
        for k in range(1, c["quantity"] + 1):
            steps.append({"name": f"{name} count {k}", **loop, "conditions": [dict(c, quantity=k)], "effects": [
                {"type": "change_variable", "variable": name, "operation": "SET", "quantity": k}]})
        return c["quantity"], steps
    return None


def plan(src: Scenario, conv: Conversion, refs: dict[int, int],
         objective_texts: dict[int, list[tuple[str, list[int]]]]) -> VictoryPlan:
    """Options and triggers for a converted scenario. refs: AoE DE unit id -> RoR unit reference id.
    objective_texts: per player, (line, indexes of the conditions it covers) per to-do line (objectives.lines;
    shown for human players)."""
    gv = src.global_victory
    mode = VICTORY_MODES[gv["mode"]]
    out = VictoryPlan(ROR_VICTORY[mode], conquest=bool(gv["conquest"]) if mode == "custom" else True)
    active = src.active_players
    start_counts = Counter((p.number, u.type) for p in src.players for u in p.units)
    custom = mode == "custom"
    all_custom = bool(gv["all_custom"])
    globals_ = [{"type": "accumulate_attribute", "attribute": GLOBAL_ATTRIBUTES[k], "quantity": gv[k],
                 "source_player": 0} for k in GLOBAL_ATTRIBUTES if custom and gv[k] > 0]

    def win(p: int) -> list[dict]:
        return [{"type": "declare_victory", "source_player": p, "enabled": True}]

    for p in active:
        conds, arms, ticks, armed_ix = [], [], {}, set()
        for i, c in enumerate(p.victory):
            cond, problem = _condition(c, p.number, src, conv, refs, start_counts)
            if problem:
                out.skipped.append(f"player {p.number} {c.type}: {problem}")
                continue
            if isinstance(cond, Condition):
                cond, arm = cond.cond, cond.arm
            else:
                arm = None
            conds.append(cond)
            met = f"P{p.number} Objective {i + 1} met"
            if arm:
                arms.append((arm, met if p.human else None))
                armed_ix.add(i)
            if p.human:
                # An armed condition shows from the start and ticks through a variable its hidden "met" trigger sets.
                ticks[i] = cond
                if arm:
                    var = f"p{p.number}_objective_{i + 1}"
                    ticks[i] = {"type": "variable_value", "variable": var, "comparison": "EQUAL", "quantity": 1}
                    out.triggers.append({"name": met, "enabled": False, "conditions": [cond], "effects": [
                        {"type": "change_variable", "variable": var, "operation": "SET", "quantity": 1}]})
        # On screen as well as in the objectives panel: the game's to-do list, a line ticked when its conditions
        # are all met (objectives.lines: conditions that read the same share one).
        groups = objective_texts.get(p.number) or [(c.type, [i]) for i, c in enumerate(p.victory)]
        shown = [g for g in groups if any(i in ticks for i in g[1])]
        for order, (text, indexes) in enumerate(shown):
            name = f"P{p.number} Objective {order + 1}"
            tick = [ticks[i] for i in indexes if i in ticks]
            counter = _counter(name, tick, p.number, armed=any(i in armed_ix for i in indexes))
            short = text
            if counter:
                total, triggers = counter
                out.triggers += triggers
                short = f"{text.removesuffix('.')} (<{name}>/{total})."
            # "+ " is how the game's own objectives start; on screen it draws as the checkbox. Higher display order
            # shows higher, so the first line gets the highest.
            out.triggers.append({"name": name, "display_as_objective": True, "display_on_screen": True,
                                 "description": f"+ {text}", "short_description": f"+ {short}",
                                 "description_order": len(shown) - order, "conditions": tick})
        enemies = [q.number for q in active if src.diplomacy[p.number - 1][q.number - 1] == ENEMY]
        conquest = [{"type": "player_defeated", "source_player": q} for q in enemies]
        mine = [dict(g, source_player=p.number) for g in globals_]
        if custom and all_custom:
            conds += mine + (conquest if gv["conquest"] and p.human else [])
            mine, conquest = [], []
        if conds:
            name = f"P{p.number} Victory"
            out.triggers.append({"name": name, "enabled": not arms, "conditions": conds, "effects": win(p.number)})
            for k, (arm, objective) in enumerate(arms):
                last = k == len(arms) - 1
                then = [objective] if objective else []
                then += [name] if last else [f"P{p.number} Victory armed {k + 2}"]
                out.triggers.append({"name": f"P{p.number} Victory armed {k + 1}", "enabled": k == 0,
                                     "conditions": [arm],
                                     "effects": [{"type": "activate_trigger", "trigger_id": t} for t in then]})
        if custom:
            for g in mine:
                out.triggers.append({"name": f"P{p.number} Victory: attribute {g['attribute']}", "conditions": [g],
                                     "effects": win(p.number)})
            if gv["conquest"] and p.human and conquest:
                out.triggers.append({"name": f"P{p.number} Victory: conquest", "conditions": conquest,
                                     "effects": win(p.number)})
    return out
