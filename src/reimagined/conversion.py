"""The AoE DE -> Return of Rome conversion rules, read from aoe2de_ror/conversion.yaml.

That file is the single source of truth: every terrain and object swap, the few behaviour rules, and
per-mission overrides. `load()` validates all of it against RoR's own names (from aoe-agent-editor)
and reports every problem at once, so a typo in the file fails loudly instead of converting wrongly.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml
from aoe2ed import games
from AoE2ScenarioParser.datasets.terrains import TerrainId

from . import layout

CONVERSION_FILE = layout.ROOT / "aoe2de_ror" / "conversion.yaml"
DROP = "drop"
TOP_KEYS = {"terrain", "objects", "rules", "missions"}
RULE_KEYS = {"forest_terrains", "road_terrains", "min_road_cluster", "civs"}


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

    def for_mission(self, key: str) -> Conversion:
        """The rules for one mission: its overrides on top of the global entries."""
        ov = self.missions.get(key)
        if not ov:
            return self
        return replace(self, terrain={**self.terrain, **ov["terrain"]}, objects={**self.objects, **ov["objects"]})

    def uncovered(self, terrains: set[int], objects: set[int]) -> list[str]:
        """What a map uses that this conversion doesn't say how to convert."""
        out = [f"terrain {t}" for t in sorted(terrains - set(self.terrain))]
        return out + [f"object {o}" for o in sorted(objects - set(self.objects))]


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

    known = {f"{c.slug}/{m.folder.name}" for c in layout.campaigns(aoe1de) for m in c.missions}
    missions = {}
    for key, ov in (spec.get("missions") or {}).items():
        if key not in known:
            problems.append(f"missions: '{key}' isn't a mission (use <campaign>/<NN_mission> from aoe1de/)")
            continue
        bad = set(ov or {}) - {"terrain", "objects"}
        problems += [f"missions.{key}: unknown key '{k}'" for k in sorted(bad)]
        t, o = _parse_maps(ov or {}, f"missions.{key}.", problems)
        missions[key] = {"terrain": t, "objects": o}

    if problems:
        raise ConversionError(problems)
    return Conversion(terrain, objects, frozenset(forest), frozenset(rules.get("road_terrains", [])),
                      int(rules.get("min_road_cluster", 8)), missions)
