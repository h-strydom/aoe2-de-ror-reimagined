"""Fill aoe1de/'s campaign and mission files with what the original campaigns contain.

Mission files get the players, the victory settings, every player's objectives (the scenario's
individual victory conditions) and the mission text the game shows: instructions, hints, victory,
loss and history. Campaign files get the campaign's display name and description. Text comes from
AoE DE's string table when the scenario names a string id there (that is what the game displays),
otherwise from the scenario itself.

`reimagined extract` writes the files; tests check the committed files still match.
"""
from __future__ import annotations

import re
from collections import Counter
from functools import cache

import yaml

from . import layout
from .aoede import strings
from .aoede.names import object_name
from .aoede.scenario import AGES, MESSAGES, VICTORY_MODES, Scenario, Unit, VictoryCondition, load_scenario

CIVS = (None, "Egyptian", "Greek", "Babylonian", "Assyrian", "Minoan", "Hittite", "Phoenician", "Sumerian",
        "Persian", "Shang", "Yamato", "Choson", "Roman", "Carthaginian", "Palmyran", "Macedonian")
# AoE DE attribute (resource) ids the campaigns' `attribute` objectives use.
ATTRIBUTES = {0: "food", 1: "wood", 2: "stone", 3: "gold", 6: "current_age", 11: "population", 13: "discoveries"}
# current_age amounts: Ascent of Egypt 4 ("Advance to the Tool Age") asks for 2, so 1 = Stone Age.
AGE_NAMES = {i + 1: f"{a.replace('_', '-').title()} Age" for i, a in enumerate(AGES)}


def _text(s: Scenario, table: dict[int, str]) -> tuple[dict[str, str], dict[str, int]]:
    text, ids = {}, {}
    for k in MESSAGES:
        sid = s.message_ids[k]
        value = table.get(sid) if sid >= 0 else None
        value = (value if value is not None else s.messages[k]).replace("\r", "").rstrip()
        if value:
            text[k] = value
            if sid in table:
                ids[k] = sid
    return text, ids


def _units(s: Scenario) -> dict[int, tuple[int, Unit]]:
    out = {u.id: (0, u) for u in s.gaia_units}
    for p in s.players:
        out.update({u.id: (p.number, u) for u in p.units})
    return out


def _player_name(s: Scenario, n: int, names: dict[int, str]) -> str:
    return names.get(n, f"player {n}") if n > 0 else "Gaia"


def _unit_ref(uid: int, units: dict[int, tuple[int, Unit]]) -> dict:
    owner, u = units[uid]
    return {"id": uid, "object": object_name(u.type), "owner": owner, "at": [round(u.x, 1), round(u.y, 1)]}


def _area(c: VictoryCondition) -> list[int]:
    return [int(v) for v in c.area]


def objective(c: VictoryCondition, s: Scenario, units: dict, names: dict[int, str]) -> dict:
    """One victory condition as a mission-file entry, with a readable summary first."""
    who = _player_name(s, c.player, names)
    obj = object_name(c.object_type) if c.object_type > 0 else None
    src = _unit_ref(c.source, units) if c.source >= 0 else None
    tgt = _unit_ref(c.target, units) if c.target >= 0 else None
    area = f"the area ({_area(c)[0]}, {_area(c)[1]})-({_area(c)[2]}, {_area(c)[3]})"
    d: dict = {"type": c.type}
    if c.type == "capture":
        d["summary"] = f"Capture the {tgt['object']} (#{tgt['id']})"
    elif c.type == "create":
        d["summary"] = f"Create {c.number} {obj}"
    elif c.type == "destroy":
        d["summary"] = f"Destroy the {tgt['object']} (#{tgt['id']}) of {who}"
    elif c.type == "destroy_multiple":
        d["summary"] = f"Destroy {c.number} {obj} of {who}" if obj else f"Destroy the units of {who}"
    elif c.type == "bring_to_area":
        d["summary"] = f"Bring the {src['object']} (#{src['id']}) to {area}"
    elif c.type == "bring_to_object":
        d["summary"] = f"Bring the {src['object']} (#{src['id']}) to the {tgt['object']} (#{tgt['id']})"
    elif c.type == "attribute":
        attr = ATTRIBUTES.get(c.number, f"attribute {c.number}")
        d["summary"] = (f"Advance to the {AGE_NAMES.get(c.amount, c.amount)}" if attr == "current_age"
                        else f"Reach {c.amount} {attr}")
        d["attribute"] = attr
        d["amount"] = c.amount
    elif c.type == "create_in_area":
        d["summary"] = f"Create {c.number} {obj} in {area}"
    elif c.type == "destroy_all":
        d["summary"] = f"Destroy all {obj} of {who}"
    elif c.type == "destroy_player":
        d["summary"] = f"Defeat {who}"
    else:
        d["summary"] = c.type
    if obj:
        d["object"] = obj
    if c.type in ("create", "create_in_area", "destroy_multiple"):
        d["number"] = c.number
    if c.player > 0 and c.type != "attribute":
        d["target_player"] = c.player
    if any(c.area):
        d["area"] = _area(c)
    if src:
        d["source"] = src
    if tgt:
        d["target"] = tgt
    for k, default in (("group", 1), ("ally", 0), ("state", 0)):
        if getattr(c, k) != default:
            d[k] = getattr(c, k)
    return d


_SN = re.compile(r"^\s*(\d+)\s+(-?\d+)\s*//\s*(\w+)", re.M)
STOCK_STRATEGIES = {"default"}           # AoE DE's stock build list: named, not listed


def personality(text: str) -> dict[str, int]:
    """An AoE1 personality file's strategic numbers: name -> value."""
    return {m.group(3): int(m.group(2)) for m in _SN.finditer(text)}


@cache
def default_personality() -> dict[str, int]:
    """AoE DE's stock personality: the one most computer players in the campaigns use."""
    texts = Counter(p.ai.personality_text for c in layout.campaigns() for m in c.missions
                    for p in load_scenario(m.scenario_path).active_players if p.ai and p.ai.personality_text)
    return personality(texts.most_common(1)[0][0])


def build_list(text: str) -> list[str]:
    """An AoE1 strategy file's build list, one entry per line (comments dropped, spacing collapsed):
    `<B|U|R|C|T><id> <name> <count> <made at>`, B building, U unit, R research, C age, T trained."""
    out = []
    for line in text.splitlines():
        line = line.split("//", 1)[0].strip()
        if line:
            out.append(" ".join(line.split()))
    return out


def ai_summary(ai) -> dict:
    """A computer player's AoE1 AI for its mission file: the three file names, the personality's strategic
    numbers that differ from AoE DE's stock personality, and the build list unless it's the stock one."""
    out = {k: getattr(ai, k) for k in ("strategy", "city_plan", "personality") if getattr(ai, k)}
    if ai.personality_text:
        stock = default_personality()
        changed = {k: v for k, v in personality(ai.personality_text).items() if stock.get(k) != v}
        if changed:
            out["personality_changes"] = changed
    elif ai.personality:
        out["personality_note"] = "no file: the game picks a personality"
    if ai.strategy_text and ai.strategy.lower() not in STOCK_STRATEGIES:
        out["build_list"] = build_list(ai.strategy_text)
    return out


def mission_data(s: Scenario, table: dict[int, str]) -> dict:
    names = {p.number: table.get(p.name_string_id, p.name) or p.name for p in s.active_players}
    units = _units(s)
    players = []
    for p in s.active_players:
        e = {"number": p.number, "name": names[p.number], "civ": CIVS[p.civ], "human": p.human}
        if p.allied_victory:
            e["allied_victory"] = True
        if p.view:
            e["view"] = list(p.view)
        if p.disabled:
            e["disabled"] = list(p.disabled)
        if not p.human and p.ai:
            e["ai"] = ai_summary(p.ai)
        players.append(e)
    gv = dict(s.global_victory)
    victory = {"mode": VICTORY_MODES[gv.pop("mode")], **{k: bool(v) if k in ("conquest", "all_custom") else v
                                                         for k, v in gv.items()}}
    objectives = []
    for p in s.active_players:
        for c in p.victory:
            objectives.append({"player": p.number, **objective(c, s, units, names)})
    media = {k: v for k, v in s.cinematics.items() if v}
    text, ids = _text(s, table)
    return {"players": players, "victory": victory, "objectives": objectives, "media": media,
            "text": text, "text_ids": ids}


class _Dumper(yaml.SafeDumper):
    """Short all-scalar lists and maps on one line ({number: 1, ...}, [23, 6]); everything else one entry
    per line (build lists, personality changes)."""


def _scalar(v) -> bool:
    return not isinstance(v, (dict, list, tuple))


def _represent_list(dumper, data):
    flow = len(data) <= 4 and all(_scalar(v) for v in data)
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=flow)


def _represent_dict(dumper, data):
    flow = len(data) <= 6 and all(_scalar(v) for v in data.values())
    return dumper.represent_mapping("tag:yaml.org,2002:map", data.items(), flow_style=flow)


_Dumper.add_representer(list, _represent_list)
_Dumper.add_representer(dict, _represent_dict)


def _dump(data) -> str:
    return yaml.dump(data, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=110)


def _block(key: str, value: str, indent: int) -> str:
    pad = " " * (indent + 2)
    lines = value.split("\n")
    first = next((ln for ln in lines if ln.strip()), "")
    indicator = "|-" if not first.startswith(" ") else "|2-"
    body = "\n".join(pad + ln if ln.strip() else "" for ln in lines)
    return f"{' ' * indent}{key}: {indicator}\n{body}\n"


def mission_document(c: layout.CampaignInfo, number: int, table: dict[int, str]) -> str:
    m = c.missions[number - 1]
    s = load_scenario(m.scenario_path)
    name_id = strings.mission_name_ids([(x.order, len(x.missions)) for x in layout.campaigns(c.root)])
    data = mission_data(s, table)
    head = {
        "title": m.title,
        "display_name": table.get(name_id[(c.order, number)], m.title),
        "source": {"campaign_file": c.source_file, "scenario": m.source_scenario, "map_size": s.width,
                   "players": len(s.active_players)},
    }
    out = [f"# {c.title}, mission {number}: {m.title}\n",
           "# Generated by `reimagined extract` from the original scenario and AoE DE's string table.\n",
           _dump(head), "\n", _dump({"players": data["players"]}), "\n", _dump({"victory": data["victory"]}), "\n",
           "# Each player's individual victory conditions, as the scenario stores them.\n",
           _dump({"objectives": data["objectives"]})]
    if data["media"]:
        out += ["\n", _dump({"media": data["media"]})]
    out += ["\n", "# What the game shows (strings.txt ids in text_ids; otherwise the scenario's own text).\n",
            _dump({"text_ids": data["text_ids"]}), "text:\n"]
    out += [_block(k, v, 2) for k, v in data["text"].items()]
    return "".join(out)


def campaign_document(c: layout.CampaignInfo, table: dict[int, str]) -> str:
    name_id, desc_id = strings.campaign_ids(c.order)
    head = {"title": c.title, "display_name": table.get(name_id, c.title), "source_file": c.source_file,
            "order": c.order, "missions": [m.folder.name for m in c.missions]}
    out = [f"# {c.title}: AoE DE campaign {c.order}\n", _dump(head)]
    if desc_id in table:
        out += ["\n", _block("description", table[desc_id].replace("\r", "").rstrip(), 0)]
    return "".join(out)


def documents(root=layout.AOE1DE, table: dict[int, str] | None = None, slugs: list[str] | None = None) -> dict:
    """Path -> the text each campaign and mission file should have (of the campaigns `slugs`, default all)."""
    table = strings.load() if table is None else table
    out = {}
    for c in layout.campaigns(root):
        if slugs is not None and c.slug not in slugs:
            continue
        out[root / f"{c.slug}.yaml"] = campaign_document(c, table)
        for i, m in enumerate(c.missions, start=1):
            out[m.folder / "mission.yaml"] = mission_document(c, i, table)
    return out


def extract(root=layout.AOE1DE) -> list:
    """Write every campaign and mission file; returns the paths that changed."""
    changed = []
    for path, text in documents(root).items():
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8", newline="\n")
            changed.append(path)
    return changed
