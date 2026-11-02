"""AoE1 computer player AI -> an aoe-agent-editor AI spec, compiled to a RoR script and embedded in the map.

An AoE1 AI is three files (aoede.scenario.Ai): a strategy (build list), a city plan (building placement;
RoR's engine places buildings itself, so it isn't carried over) and a personality (strategic numbers).

Build list lines are `<type><id> <name> <count> <made at> [<group>]`, worked through in order:
  B build, U train, T train (the trailing number is a group), R research, C age, A (two uses: skipped).
Counts add up per id (two "B70 House 2" lines = 4 houses in total). AoE DE ids convert through
aoe2de_ror/conversion.yaml; tech and age ids are RoR's own. Walls aren't built (RoR's AI builds walls with
a different command), and dropped objects are left out.

Personality: strategic numbers become RoR ones of the same name (SNPercentCivilianExplorers ->
sn-percent-civilian-explorers) when RoR's scripts know that name; the attack numbers become the spec's
attack (initial delay and separation time read as seconds: unverified in game). After the build list the
AI keeps its army topped up to the build list's unit counts, as AoE1's AI rebuilds its list. Scripted AIs
never resign.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cache

from aoe2ed import games
from aoe2ed.ai.per import vocab

from .aoede.scenario import Ai
from .conversion import Conversion

_LINE = re.compile(r"^([BURCTA])(-?\d+)\s+(.+?)\s+(-?\d+)\s+(-?\d+)(?:\s+(-?\d+))?\.?$")
ATTACK_SNS = {"SNInitialAttackDelay", "SNInitialAttackDelayType", "SNAttackSeparationTime",
              "SNAttackSeparationTimeRandomness", "SNMinimumAttackGroupSize", "SNMaximumAttackGroupSize",
              "SNNumberAttackGroups"}
DEFAULT_FIRST_ATTACK, DEFAULT_ATTACK_EVERY = 600, 240
STEP_TIMEOUT = 180


@dataclass
class Translation:
    spec: dict
    skipped: list[str] = field(default_factory=list)       # build list lines that couldn't carry over


def sn_name(name: str) -> str:
    """SNPercentCivilianExplorers -> sn-percent-civilian-explorers."""
    return "sn-" + re.sub(r"(?<!^)(?=[A-Z])", "-", name.removeprefix("SN")).lower()


@cache
def _tech_names() -> dict[int, str]:
    out: dict[int, str] = {}
    for name, tid in games.ror_data()["techs"].items():
        out.setdefault(tid, name)
    return out


def translate(ai: Ai, personality: dict[str, int], conv: Conversion, name: str) -> Translation:
    """The AI spec for an AoE1 AI. personality: its strategic numbers (the stock ones where it has no file)."""
    t = Translation({"name": name, "step_timeout": STEP_TIMEOUT})
    steps, totals, army = [], {}, {}
    for line in _lines(ai.strategy_text):
        m = _LINE.match(line)
        if not m:
            t.skipped.append(f"{line}: not a build list line")
            continue
        kind, oid, count = m.group(1), int(m.group(2)), int(m.group(4))
        if kind == "A":
            t.skipped.append(f"{line}: 'A' entries aren't understood")
            continue
        if kind in "RC":
            tech = _tech_names().get(oid)
            if tech is None:
                t.skipped.append(f"{line}: no RoR tech {oid}")
                continue
            steps.append({"research": tech})
            continue
        target = conv.objects.get(oid)
        if target is None or target.ror_name is None:
            t.skipped.append(f"{line}: object {oid} doesn't convert")
            continue
        if "WALL" in target.ror_name:
            t.skipped.append(f"{line}: walls aren't built")
            continue
        totals[target.ror_name] = totals.get(target.ror_name, 0) + max(count, 0)
        if count <= 0:
            continue
        verb = "build" if kind == "B" else "train"
        steps.append({verb: target.ror_name, "count": totals[target.ror_name]})
        if verb == "train" and target.ror_name != "VILLAGER":
            army[target.ror_name] = totals[target.ror_name]
    t.spec["build_order"] = steps
    if army:
        t.spec["keep"] = [{"train": u, "count": n} for u, n in army.items()]
    t.spec.update(_personality(personality))
    return t


def _lines(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        line = line.split("//", 1)[0].strip()
        if line:
            out.append(" ".join(line.split()))
    return out


def _personality(sns: dict[str, int]) -> dict:
    known = vocab()["strategic_numbers"]
    out: dict = {"strategic_numbers": {sn_name(k): v for k, v in sns.items()
                                       if k not in ATTACK_SNS and sn_name(k) in known}}
    if sns.get("SNNumberAttackGroups", 1) > 0:
        first = sns.get("SNInitialAttackDelay", DEFAULT_FIRST_ATTACK)
        out["attack"] = {"first": max(first, 1), "every": max(sns.get("SNAttackSeparationTime", DEFAULT_ATTACK_EVERY), 1),
                         "min_group": max(sns.get("SNMinimumAttackGroupSize", 4), 1),
                         "max_group": max(sns.get("SNMaximumAttackGroupSize", 12), 1)}
    return out
