"""The AoE DE -> Return of Rome conversion rules, read from aoe2de_ror/conversion.yaml.

That file is the single source of truth: every terrain and object swap, the few behaviour rules, and
per-mission overrides. `load()` validates all of it against RoR's own names (from aoe-agent-editor)
and reports every problem at once, so a typo in the file fails loudly instead of converting wrongly.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from functools import cache
from pathlib import Path

import yaml
from aoe2ed import games
from aoe2ed.mapgen.names import tree_for_forest
from AoE2ScenarioParser.datasets.terrains import TerrainId

from . import layout

CONVERSION_FILE = layout.AOE2DE_ROR / "conversion.yaml"
DROP = "drop"
TOP_KEYS = {"terrain", "objects", "rules", "missions"}
RULE_KEYS = {"forest_terrains", "road_terrains", "min_road_cluster", "civs", "ai_levels", "population"}
POPULATION_KEYS = {"cap", "grow_minutes"}
MISSION_KEYS = {"terrain", "objects", "reveal", "show_base", "claim_base", "diplomacy", "disable", "attacks",
                "provoked", "ai", "vision", "resources", "setup", "units"}
ATTACK_KEYS = {"hostile_at", "hostile_gold", "enemy_on", "message"}
RESOURCES = {"food", "wood", "gold", "stone"}
STANCES = {"ALLY", "NEUTRAL", "ENEMY"}
CLAIM_KEYS = {"area", "player", "start_ai"}


class ConversionError(ValueError):
    def __init__(self, problems: list[str]):
        super().__init__("conversion.yaml has problems:\n  - " + "\n  - ".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class ObjectTarget:
    ror_name: str | None            # None = dropped
    ror_id: int | None
    forest: bool = False            # a forest tree: on a RoR forest terrain it becomes that terrain's tree


@dataclass(frozen=True)
class Conversion:
    terrain: dict[int, int]                         # AoE DE terrain id -> RoR terrain id
    objects: dict[int, ObjectTarget]                # AoE DE object id -> target
    forest_terrains: frozenset[int]                 # RoR terrain ids
    road_terrains: frozenset[int]                   # AoE DE terrain ids
    min_road_cluster: int
    missions: dict[str, dict] = field(default_factory=dict)   # "campaign/NN_mission" -> raw overrides
    ai_levels: str | None = None                    # "auto": computer players follow the game's difficulty
    reveal: tuple[tuple[int, int, int, int], ...] = ()    # this mission: areas player 1 starts with explored
    show_base: tuple[tuple[int, int, int, int], ...] = ()  # this mission: areas player 1's enemies start knowing
    claim_base: dict | None = None                  # this mission: {area, player, start_ai}
    # This mission's fixes where RoR plays AoE1's settings differently (the Egypt audit, 2026-11-12):
    diplomacy: dict = field(default_factory=dict)   # {(a, b): stance}, both ways
    disable: dict = field(default_factory=dict)     # {player: [ror_tech_tree.yaml names]} switched off
    attacks: dict = field(default_factory=dict)     # {player: {hostile_at, message} or {}}: a passive AI attacks
    provoked: dict = field(default_factory=dict)    # {player: message}: neutral until you attack its town
    ai: dict = field(default_factory=dict)          # {player: toolbox profile} (aoe-agent-editor ai/profiles.py)
    vision: tuple[int, ...] = ()                    # players that see the whole map and every enemy unit
    resources: dict = field(default_factory=dict)   # {player: {food, wood, gold, stone}}: starting stockpiles
    setup: tuple = ()                               # trigger effects at the start (mission-specific rules)
    units: tuple = ()                               # ({player, unit (RoR id), at: [x, y]}, ...) added to the map
    population: dict | None = None                  # {cap, grow_minutes}: missions where player 1 can build

    def for_mission(self, key: str) -> Conversion:
        """The rules for one mission: its overrides on top of the global entries."""
        ov = self.missions.get(key)
        if not ov:
            return self
        return replace(self, terrain={**self.terrain, **ov["terrain"]}, objects={**self.objects, **ov["objects"]},
                       reveal=ov.get("reveal", ()), show_base=ov.get("show_base", ()),
                       claim_base=ov.get("claim_base"), diplomacy=ov.get("diplomacy", {}),
                       disable=ov.get("disable", {}), attacks=ov.get("attacks", {}),
                       provoked=ov.get("provoked", {}), ai=ov.get("ai", {}), vision=ov.get("vision", ()),
                       resources=ov.get("resources", {}), setup=ov.get("setup", ()), units=ov.get("units", ()))

    def place(self, aoede_id: int, ror_terrain: int) -> int | None:
        """The RoR object for an AoE DE object standing on `ror_terrain`, or None if it's dropped.

        RoR doesn't grow trees on forest terrain by itself (scenarios store every tree), so a forest
        tree on a RoR forest terrain gets the tree aoe-agent-editor's map generator plants there."""
        target = self.objects[aoede_id]
        if target.forest and ror_terrain in self.forest_terrains:
            return _forest_tree(ror_terrain)
        return target.ror_id

    def uncovered(self, terrains: set[int], objects: set[int]) -> list[str]:
        """What a map uses that this conversion doesn't say how to convert."""
        out = [f"terrain {t}" for t in sorted(terrains - set(self.terrain))]
        return out + [f"object {o}" for o in sorted(objects - set(self.objects))]


@cache
def _forest_tree(ror_terrain: int) -> int:
    with games.use("ror"):
        return tree_for_forest(ror_terrain)


def _terrain_id(value, where: str, problems: list[str]) -> int | None:
    if isinstance(value, int):
        return value
    try:
        return TerrainId[str(value).upper()].value
    except KeyError:
        problems.append(f"{where}: unknown RoR terrain '{value}'")
        return None


def _object_target(value, where: str, problems: list[str]) -> ObjectTarget | None:
    forest = False
    if isinstance(value, dict):
        unknown = set(value) - {"ror", "forest"}
        if unknown or "ror" not in value:
            problems.append(f"{where}: expected {{ror: NAME, forest: true}}, got {value}")
            return None
        value, forest = value["ror"], bool(value.get("forest"))
    if value == DROP or value is None:
        return ObjectTarget(None, None)
    ror = games.ror_data()["objects"]
    name = str(value).upper()
    if name not in ror:
        problems.append(f"{where}: '{value}' isn't a RoR object (find names with lookup(..., game='ror'))")
        return None
    return ObjectTarget(name, ror[name], forest)


def _int_key(k, where: str, problems: list[str]) -> int | None:
    if isinstance(k, int):
        return k
    problems.append(f"{where}: key '{k}' must be an AoE DE id (a number)")
    return None


def _parse_maps(spec: dict, where: str, problems: list[str]) -> tuple[dict[int, int], dict[int, ObjectTarget]]:
    terrain, objects = {}, {}
    for k, v in (spec.get("terrain") or {}).items():
        key, tid = _int_key(k, f"{where}terrain", problems), _terrain_id(v, f"{where}terrain {k}", problems)
        if key is not None and tid is not None:
            terrain[key] = tid
    for k, v in (spec.get("objects") or {}).items():
        key, target = _int_key(k, f"{where}objects", problems), _object_target(v, f"{where}objects {k}", problems)
        if key is not None and target is not None:
            objects[key] = target
    return terrain, objects


def load(path: Path = CONVERSION_FILE, aoe1de: Path = layout.AOE1DE) -> Conversion:
    spec = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    problems: list[str] = [f"unknown top-level key '{k}'" for k in spec if k not in TOP_KEYS]
    terrain, objects = _parse_maps(spec, "", problems)

    rules = spec.get("rules") or {}
    problems += [f"rules: unknown key '{k}'" for k in rules if k not in RULE_KEYS]
    forest = {t for v in rules.get("forest_terrains", []) if (t := _terrain_id(v, "rules.forest_terrains", problems)) is not None}
    if rules.get("civs", "same_order") != "same_order":
        problems.append("rules.civs: only 'same_order' is supported")

    known = {m.key for c in layout.campaigns(aoe1de) for m in c.missions}
    missions = {}
    for key, ov in (spec.get("missions") or {}).items():
        if key not in known:
            problems.append(f"missions: '{key}' isn't a mission (use <campaign>/<NN_mission> from aoe1de/)")
            continue
        ov = ov or {}
        bad = set(ov) - MISSION_KEYS
        problems += [f"missions.{key}: unknown key '{k}'" for k in sorted(bad)]
        t, o = _parse_maps(ov, f"missions.{key}.", problems)
        areas = {k: tuple(tuple(a) for i, a in enumerate(ov.get(k) or [])
                          if _area(a, f"missions.{key}.{k}[{i}]", problems)) for k in ("reveal", "show_base")}
        claim = ov.get("claim_base")
        if claim is not None:
            if not isinstance(claim, dict) or set(claim) - CLAIM_KEYS or "area" not in claim:
                problems.append(f"missions.{key}.claim_base: expected {{area: [x1, y1, x2, y2], player: 1, "
                                f"start_ai: true}}, got {claim}")
                claim = None
            elif _area(claim["area"], f"missions.{key}.claim_base.area", problems):
                claim = {"area": tuple(claim["area"]), "player": int(claim.get("player", 1)),
                         "start_ai": bool(claim.get("start_ai", False))}
            else:
                claim = None
        dip = {}
        for i, d in enumerate(ov.get("diplomacy") or []):
            if not (isinstance(d, list) and len(d) == 3 and str(d[2]).upper() in STANCES):
                problems.append(f"missions.{key}.diplomacy[{i}]: [a, b, ALLY|NEUTRAL|ENEMY], got {d}")
                continue
            dip[(int(d[0]), int(d[1]))] = dip[(int(d[1]), int(d[0]))] = str(d[2]).upper()
        disable = {int(k): list(v) for k, v in (ov.get("disable") or {}).items()}
        attacks = {}
        for k, v in (ov.get("attacks") or {}).items():
            v = v or {}
            if set(v) - ATTACK_KEYS or v.get("enemy_on", "hard") != "hard":
                problems.append(f"missions.{key}.attacks.{k}: {{hostile_at: seconds | hostile_gold: N, enemy_on: hard, "
                                f"message: text}}, got {v}")
            attacks[int(k)] = v
        provoked = {int(k): str(v or "") for k, v in (ov.get("provoked") or {}).items()}
        ai = {}
        for k, v in (ov.get("ai") or {}).items():
            if not isinstance(v, dict) or "kind" not in v:
                problems.append(f"missions.{key}.ai.{k}: a toolbox profile {{kind: town|army, ...}}, got {v!r}")
                continue
            ai[int(k)] = v
        missions[key] = {"terrain": t, "objects": o, **areas, "claim_base": claim, "diplomacy": dip,
                         "disable": disable, "attacks": attacks, "provoked": provoked, "ai": ai,
                         "vision": tuple(int(v) for v in ov.get("vision") or []),
                         "resources": {int(k): {r: int(n) for r, n in v.items() if r in RESOURCES}
                                       for k, v in (ov.get("resources") or {}).items()},
                         "setup": tuple(ov.get("setup") or ()),
                         "units": tuple(ov.get("units") or ())}

    population = rules.get("population")
    if population is not None:
        if (not isinstance(population, dict) or set(population) != POPULATION_KEYS
                or not all(isinstance(v, int) and v > 0 for v in population.values())):
            problems.append(f"rules.population: expected {{cap: 200, grow_minutes: 60}}, got {population!r}")
            population = None
    levels = rules.get("ai_levels")
    if levels not in (None, "auto"):
        problems.append(f"rules.ai_levels: 'auto' or left out, got {levels!r}")
    if problems:
        raise ConversionError(problems)
    return Conversion(terrain, objects, frozenset(forest), frozenset(rules.get("road_terrains", [])),
                      int(rules.get("min_road_cluster", 8)), missions, levels, population=population)


def _area(value, where: str, problems: list[str]) -> bool:
    ok = (isinstance(value, (list, tuple)) and len(value) == 4 and all(isinstance(v, int) for v in value)
          and value[0] <= value[2] and value[1] <= value[3])
    if not ok:
        problems.append(f"{where}: an area is [x1, y1, x2, y2] in tiles, got {value}")
    return ok
