"""Write docs/audits/missions.md: for every campaign and mission, whether you can build, the players (civ, stance,
the AI each gets in RoR-RI and RoR-RIX), and what each player's tech tree is cut down to.

    uv run python scripts/mission_breakdown.py [campaign ...]

Reads the original missions (aoe1de/) and converts each one into a temporary folder, the way `reimagined convert`
does, so it shows what the game gets. Ages come from RoR's civ tech trees (CivTechTrees/*.json in your install).
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from aoe2ed import tables
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

from reimagined import editions, layout, progression
from reimagined.aoede.scenario import load_scenario
from reimagined.conversion import load
from reimagined.convert import DIPLOMACY, ROR_CIVS, can_build, convert_mission

OUT = layout.ROOT / "docs" / "audits" / "missions.md"
TREES = Path(r"C:/Program Files (x86)/Steam/steamapps/common/AoE2DE/modes/Pompeii/resources/_common/dat/CivTechTrees")
AGE_NAMES = ("Stone", "Tool", "Bronze", "Iron")
AGE_TECHS = {101: 1, 102: 2, 103: 3}                 # tech -> the age it reaches (0 Stone .. 3 Iron)
AGES: dict[str, dict] = {}                         # civ -> tree_ages(civ), filled as needed
STANCE = {"ALLY": "ally", "NEUTRAL": "neutral", "ENEMY": "enemy"}


def key(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


CIV_FILES = {"EGYPTIAN": "EGYPTIANS", "GREEK": "GREEKS", "BABYLONIAN": "BABYLONIANS", "ASSYRIAN": "ASSYRIANS",
             "MINOAN": "MINOANS", "HITTITE": "HITTITES", "PHOENICIAN": "PHOENICIANS", "SUMERIAN": "SUMERIANS",
             "PERSIAN": "PERSIANS", "SHANG": "SHANG", "YAMATO": "YAMATO", "CHOSON": "CHOSON", "ROMAN": "ROMANS",
             "CARTHAGINIAN": "CARTHAGIANS", "PALMYRAN": "PALMYRANS", "MACEDONIAN": "MACEDONIANS"}


def tree_ages(civ: str) -> dict:
    """For one civ: object or tech id, and name (key()), -> the age (0..3) it opens in. What the civ can't make
    (NotAvailable) is left out."""
    stem = CIV_FILES.get(civ) or next(f.stem for f in TREES.glob("*.json") if f.stem.startswith(civ[:6]))
    d = json.loads((TREES / f"{stem}.json").read_text(encoding="utf-8"))
    out: dict = {}
    for n in d["civ_techs_buildings"] + d["civ_techs_units"]:
        if "Age ID" in n and n.get("Node Status") != "NotAvailable":
            kind = "tech" if n.get("Use Type") == "Tech" else "object"     # object and tech ids overlap
            for k in ((kind, n.get("Node ID")), key(n.get("Name", ""))):
                out[k] = min(out.get(k, 9), n["Age ID"] - 1)
    return out


def reachable(civ: str, name: str, ids, cap: int) -> bool:
    """Whether the civ makes this item within its ages (by name, else by its ("object"|"tech", id) keys)."""
    ages = AGES.setdefault(civ, tree_ages(civ))
    known = [ages[key(name)]] if key(name) in ages else [ages[i] for i in ids if i in ages]
    return bool(known) and min(known) <= cap


def names(ids, kind: str) -> list[str]:
    """Display names, one per name (a building's age versions share one)."""
    out = []
    for i in ids:
        info = tables.info(int(i), "ror", kind) if hasattr(tables, "info") else None
        n = (info or {}).get("display") or str(i)
        if n not in out:
            out.append(n)
    return out


def display(i: int, kind: str) -> str:
    d = json.loads((Path(tables.__file__).parent / "data" / "tables" / "ror.json").read_text(encoding="utf-8"))
    return (d["objects" if kind == "object" else "techs"].get(str(i)) or {}).get("display") or str(i)


def mission(args) -> dict:
    key, slug, number, folders = args
    m = {x.key: x for c in layout.campaigns() for x in c.missions}[key]
    conv = load()
    src = load_scenario(m.scenario_path)
    tmp = Path(tempfile.mkdtemp())
    eds = editions.of(next(c for c in layout.campaigns() if c.slug == slug))
    rec = {"key": key, "title": m.key.split("/")[1], "build": can_build(src, conv.for_mission(key)), "players": {},
           "rix_unlocks": None}
    for ed in eds:
        with contextlib.redirect_stdout(io.StringIO()):
            r = convert_mission(m, conv, tmp / ed.key, reimagined=ed.reimagined)
            s = AoE2DEScenario.from_file(str(r.out))
        rec["title"] = s.player_manager.players[1].tribe_name and rec["title"]
        for n in range(1, s.player_manager.active_players + 1):
            p = s.player_manager.players[n]
            row = rec["players"].setdefault(n, {"name": p.tribe_name, "civ": str(p.civilization).split(".")[-1]
                                                .split(":")[0].title().replace("_Civ", "").replace("-Civ", ""),
                                                "human": bool(p.human)})
            ai = "you" if p.human else r.ai.get(n, "no AI")
            if "PASSIVE" in ai and "attack" in (r.specs.get(n) or {}):
                ai = "AoE1 plan, told to attack (conversion.yaml)"
            row[f"ai_{ed.key}"] = ai
            row[f"diplomacy_{ed.key}"] = STANCE.get(DIPLOMACY.get(int(p.diplomacy[0])), "?") if n > 1 else ""
            them = s.player_manager.players[1].diplomacy[n - 1] if n > 1 else None
            row[f"you_to_them_{ed.key}"] = STANCE.get(DIPLOMACY.get(int(them)), "?") if them is not None else ""
            # The parser's StartingAge: 2 Dark (RoR's Stone) .. 5 Imperial (Iron); -1 or 0 unset (Stone).
            start = int(getattr(p.starting_age, "value", p.starting_age))
            row[f"start_{ed.key}"] = max(0, start - 2)
            dt, db = list(p.disabled_techs), list(p.disabled_buildings)
            caps = [AGE_TECHS[t] - 1 for t in dt if t in AGE_TECHS]
            cap = min([3, *caps])
            row[f"cap_{ed.key}"] = cap
            # Only what the player could otherwise reach: a Fortified Wall is no loss in a Tool Age mission.
            civ = str(getattr(p.civilization, "value", p.civilization)).removesuffix("-CIV")
            row["civ_key"] = civ
            row[f"off_{ed.key}"] = sorted({d for b in db
                                           if reachable(civ, d := display(b, "object"), [("object", b)], cap)}
                                          | {d for t in dt if t not in AGE_TECHS
                                             and reachable(civ, d := display(t, "tech"), [("tech", t)], cap)})
        if ed.reimagined:
            camp = progression.load(slug)
            listed = [i for i, f in enumerate(folders, 1) if f in camp.unlocks]
            if listed and number <= max(listed):
                on = {u for f in folders[:number] for u in camp.unlocks.get(f) or []}
                cap = rec["players"][1]["cap_rix"]
                tree = progression.tech_tree()
                reach = {name for name, e in tree.items()
                         if reachable(rec["players"][1]["civ_key"], name.replace("_", " "),
                                      [("object", i) for i in e.get("objects", [])]
                                      + [("tech", i) for i in e.get("techs", [])], cap)}
                locked = sorted(reach - on)
                opened = sorted(on & reach)
                rec["rix_unlocks"] = ("open", opened) if len(opened) <= len(locked) else ("locked", locked)
    return rec


def age_span(start: int, cap: int) -> str:
    start = max(0, min(start, 3))
    span = AGE_NAMES[start] if start >= cap else f"{AGE_NAMES[start]} to {AGE_NAMES[cap]}"
    if cap < 3:
        span += f" (no {', '.join(AGE_NAMES[cap + 1:])})"
    return span


def ai_label(a: str) -> str:
    if a in ("you", "no AI"):
        return a
    if a.startswith("toolbox"):
        return f"AI toolbox: {a.split(':')[0].split()[-1]} profile"
    if a.startswith("standard"):
        return "standard skirmish AI, a level harder"
    if a.startswith("immobile"):
        return "immobile (holds position)"
    if "told to attack" in a:
        return a
    if "PASSIVE" in a:
        return "AoE1 plan, passive (never attacks)"
    if "(AoE1)" in a:
        return "AoE1 plan (translated)"
    return f"mission's own ({a.split(':')[0]})"


def write(records: dict[str, list[dict]]) -> None:
    lines = ["# Missions: players, AI and tech", "",
             "Generated by `scripts/mission_breakdown.py` from the original missions, converted as `reimagined convert`",
             "does. Rerun it after changing the converter or conversion.yaml.", "",
             "- **Build mission**: you start with a villager or town center, or claim a base. A no-build mission is",
             "  played with the units you're given.",
             "- **AI**: the standard skirmish AI plays a level harder than the game's difficulty. An AoE1 plan is the",
             "  original AI translated: its build list, army and attack timing.",
             "- **Ages and off**: the ages a player can reach and what's switched off for them. When nothing is listed,",
             "  everything RoR's tree has for those ages is open. RoR-RIX also locks by trigger: its campaign tech tree",
             "  is listed under the mission.",
             "- Stances read: what they are to you / what you are to them.", ""]
    for slug, recs in records.items():
        c = next(c for c in layout.campaigns() if c.slug == slug)
        rix = any(e.reimagined for e in editions.of(c))
        lines += [f"## {c.title}", ""]
        for i, r in enumerate(recs, 1):
            title = r["key"].split("/")[1].split("_", 1)[1].replace("_", " ").title()
            lines += [f"### {i}. {title}: {'build mission' if r['build'] else 'no-build mission'}", ""]
            head = "| Player | Civ | Stance | AI (RoR-RI) |" + (" AI (RoR-RIX) |" if rix else "") + " Ages | Off |"
            lines += [head, "|" + "---|" * (head.count("|") - 1)]
            for n, p in sorted(r["players"].items()):
                ed = "ri" if "ai_ri" in p else "rix"            # a player only RoR-RIX adds
                stance = "" if p["human"] else f"{p['diplomacy_' + ed]} / {p['you_to_them_' + ed]}"
                cells = [f"P{n} {p['name']}" + (" (you)" if p["human"] else ""), p["civ"], stance,
                         ai_label(p["ai_ri"]) if ed == "ri" else "not in RoR-RI"]
                if rix:
                    rx = ai_label(p.get("ai_rix", "")) if "ai_rix" in p else ""
                    if ed == "ri" and "diplomacy_rix" in p and not p["human"] and p["diplomacy_rix"] != p["diplomacy_ri"]:
                        rx += f" ({p['diplomacy_rix']} / {p['you_to_them_rix']})"
                    cells.append(rx)
                cells += [age_span(p["start_" + ed], p["cap_" + ed]), ", ".join(p["off_" + ed]) or "nothing"]
                lines.append("| " + " | ".join(cells) + " |")
            if r["rix_unlocks"] is not None:
                kind, items = r["rix_unlocks"]
                said = ", ".join(u.replace("_", " ") for u in items) or "nothing"
                lines += ["", f"RoR-RIX tech tree for you, within your ages: only {said} open." if kind == "open"
                          else f"RoR-RIX tech tree for you, within your ages: everything open but {said}."]
            lines.append("")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main(slugs: list[str]) -> None:
    camps = [c for c in layout.campaigns() if not slugs or c.slug in slugs]
    jobs = []
    for c in camps:
        folders = [x.key.split("/")[1] for x in c.missions]
        jobs += [(x.key, c.slug, i, folders) for i, x in enumerate(c.missions, 1)]
    with ProcessPoolExecutor() as pool:
        done = list(pool.map(mission, jobs))
    records: dict[str, list[dict]] = {}
    for (key, slug, *_), rec in zip(jobs, done):
        records.setdefault(slug, []).append(rec)
    write(records)
    print(f"wrote {OUT} ({len(done)} missions)")


if __name__ == "__main__":
    main(sys.argv[1:])
