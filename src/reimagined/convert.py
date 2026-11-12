"""AoE DE scenarios -> Return of Rome scenarios and campaigns, following aoe2de_ror/conversion.yaml.

Per scenario: same map size; every tile's terrain swapped (after terrain.py's clean-up of stray
road tiles) and elevation copied; the active players with their civ, starting age, resources and
diplomacy; every object placed at the same position, rotation and owner (forest trees on a RoR
forest terrain take that terrain's tree). Triggers aren't converted. Dropped objects (marked `drop`,
or owned by an inactive player) are counted in the result, so nothing disappears silently.
"""
from __future__ import annotations

import contextlib
import dataclasses
import functools
from collections import Counter
from concurrent.futures import Executor
from dataclasses import dataclass, field
from pathlib import Path

from aoe2ed import blocks, games
from aoe2ed.campaign import Campaign as RorCampaign
from aoe2ed.campaign import CampaignScenario
from aoe2ed.session import SESSIONS
from aoe2ed.tools.ai import ai_set
from aoe2ed.tools.logic import triggers_add
from aoe2ed.tools.world import diplomacy_set, options_set, player_set
from AoE2ScenarioParser.datasets.terrains import TerrainId

from . import ai, editions, layout, missions, objectives, progression, victory
from .aoede import strings
from .aoede.names import object_name
from .aoede.scenario import Scenario, load_scenario
from .conversion import Conversion, load
from .editions import Edition
from .missions import mission_data
from .screens import dumps, screens
from .terrain import clean_terrain

# RoR civ data names by civ id. AoE DE's civs 0..16 (Gaia..Macedonian) are RoR's first 17, same order.
ROR_CIVS = (None, "EGYPTIAN", "GREEK", "BABYLONIAN", "ASSYRIAN", "MINOAN", "HITTITE", "PHOENICIAN",
            "SUMERIAN", "PERSIAN", "SHANG", "YAMATO", "CHOSON", "ROMAN", "CARTHAGINIAN", "PALMYRAN",
            "MACEDONIAN")
# AoE DE starting age 0..4 (Stone, Tool, Bronze, Iron, post-Iron) -> the parser's age names.
# Unverified in game: RoR may not map its ages one to one onto these values.
ROR_AGES = ("DARK", "FEUDAL", "CASTLE", "IMPERIAL", "POST_IMPERIAL")
DIPLOMACY = {0: "ALLY", 1: "NEUTRAL", 3: "ENEMY"}
MAX_ROR_PLAYERS = 8
NORMAL_STATUS = 2
PROVOKED_SIGNAL = 100            # + player: the AI Signal a provoked computer player sends when it turns hostile
AI_START_SIGNAL = 1               # AI Script Goal a mission's claim_base sends to computer players set to wait for it
BUILDERS = ("Villager", "Town Center")            # AoE DE names: player 1 owning one can build (rules.population)
# Computer players that build (they start with a villager or town center, and aren't passive) play RoR's standard
# skirmish AI, a level harder than the game's difficulty: Standard plays Standard, Moderate plays Hard, Hard plays
# Hardest (the user, 2026-11-12: "standard skirmish AIs of that difficulty"). It never resigns. Army-only, passive
# and waiting AIs keep their translated AoE1 build list. Players racing you to a resource goal play it too (the
# user, 2026-11-12, after Farming's Lower Egypt stalled on its AoE1 plan): their goal shows as a line to prevent.
# Its first attack waits as long as the AoE1 AI's did (SNInitialAttackDelay; Hard and Hardest attack at once).
STANDARD_AI = {"name": "Standard AI", "standard": {"plays": {"moderate": "hard", "hard": "hardest",
                                                             "hardest": "extreme"}}}
# The standard AI's map type (Options > AI Map Type): islands when a computer player can't walk to the human player,
# which teaches it boats and transports; else Highland, a land map. Continental told it to use the water: it built a
# Dock and galley-rushed Farming's river (the user, 2026-11-12; ai/default/init.per). On Highland only many fish
# (over 5 ocean or 25 shore fish) still do, which is then right.
AI_MAP_TYPES = {"islands": "small_islands", "land": "highland"}
WATER = frozenset(t.value for t in TerrainId.water_terrains())   # RoR terrains no land unit crosses (shallows do)
# Scouts page: where the project lives and where to report a problem (the user, 2026-11-12).
REPO = "https://github.com/h-strydom/aoe2-de-ror-reimagined"
LINKS = (f"RoR-RI is open source: {REPO}\n"
         f"Found a bug or have an idea? Report it at {REPO}/issues")
VIEW_RADIUS = 8                   # tiles: the start camera goes to the player's densest group of units


@dataclass
class ConvertResult:
    mission: str
    out: Path
    placed: int = 0
    dropped: Counter = field(default_factory=Counter)   # reason -> count
    players: int = 0
    victory: str = ""                                    # RoR victory mode
    triggers: int = 0                                    # objective and victory triggers
    skipped: list[str] = field(default_factory=list)     # victory conditions that couldn't be converted
    ai: dict[int, str] = field(default_factory=dict)     # computer player -> its RoR AI
    ai_skipped: list[str] = field(default_factory=list)  # AoE1 build list lines that couldn't carry over
    specs: dict[int, dict] = field(default_factory=dict)  # computer player -> its AI spec


def scenario_path(m: layout.Mission, out_root: Path = layout.AOE2DE_ROR) -> Path:
    camp, mission = m.key.split("/")
    return out_root / camp / mission / f"{camp}_{mission}.aoe2scenario"


def campaign_path(c: layout.CampaignInfo, out_root: Path = layout.AOE2DE_ROR) -> Path:
    return out_root / c.slug / f"{c.slug}.aoe2campaign"


def ror_terrain(src: Scenario, conv: Conversion) -> list[int]:
    """Every tile's RoR terrain id, row-major (index y * width + x) like both formats store them."""
    cleaned = clean_terrain(src.terrain, src.width, src.height, conv.road_terrains, conv.min_road_cluster)
    return [conv.terrain[t] for t in cleaned]


def placements(src: Scenario, conv: Conversion, terrain: list[int], dropped: Counter):
    """(owner, RoR id, unit) for every object that converts; the rest are counted in `dropped`."""
    owners = [(0, src.gaia_units)] + [(p.number, p.units) for p in src.players]
    for owner, units in owners:
        if owner and not src.players[owner - 1].active:
            if units:
                dropped[f"owned by inactive player {owner}"] += len(units)
            continue
        for u in units:
            ror_id = conv.place(u.type, terrain[int(u.y) * src.width + int(u.x)])
            if ror_id is None:
                dropped[f"{object_name(u.type)} (drop)"] += 1
            else:
                yield owner, ror_id, u


# AoE DE's "Disable Technology" entries -> RoR: a building to disable, or an age (tech) to disable.
DISABLE_BUILDINGS = {"granary": "GRANARY", "storage_pit": "STORAGE_PIT", "dock": "DOCK", "barracks": "BARRACKS",
                     "market": "MARKET", "archery_range": "ARCHERY_RANGE", "stable": "STABLE", "temple": "TEMPLE",
                     "government_center": "GOVERNMENT_CENTER", "siege_workshop": "SIEGE_WORKSHOP",
                     "academy": "ACADEMY", "town_center": "TOWN_CENTER", "wonder": "WONDER"}
DISABLE_TECHS = {"tool_age": "TOOL_AGE", "bronze_age": "BRONZE_AGE", "iron_age": "IRON_AGE"}


AGE_CAPS = {"tool_age": 1, "bronze_age": 2, "iron_age": 3}       # a disabled age caps the player below it
ARMY_SHARE = 50                                                   # % of a computer player's soldiers from its civ bonuses


def civ_army(p, spec: dict) -> dict:
    """The AI spec's `army`: lean its soldiers toward the units the player's civ bonuses favour, among those it can
    reach (its starting age or the ages its build order researches, below any disabled age) and make (not at a
    disabled building)."""
    reached = [{"TOOL_AGE": 2, "BRONZE_AGE": 3, "IRON_AGE": 4}.get(s.get("research"), 0)
               for s in spec.get("build_order") or []]
    age = max([p.starting_age + 1, *reached])
    caps = [cap for d, cap in AGE_CAPS.items() if d in p.disabled]
    return {"civ": ROR_CIVS[p.civ], "share": ARMY_SHARE, "max_age": min([age, *caps]),
            "exclude": [DISABLE_BUILDINGS[d] for d in p.disabled if d in DISABLE_BUILDINGS]}


def ror_ai(p, conv: Conversion, debug: bool = False) -> str | ai.Translation | None:
    """A computer player's AI in RoR: its AoE1 AI translated to a script (ai.py), RoR's immobile AI for
    AoE1's immobile-unit AIs, None for human players. Passive personalities build but never attack."""
    if p.human or p.ai is None:
        return None
    names = f"{p.ai.strategy} {p.ai.personality}".lower()
    if "immobile" in names:
        return "immobile"
    sns = missions.personality(p.ai.personality_text) if p.ai.personality_text else missions.default_personality()
    label = p.ai.strategy or p.ai.personality or "Default"
    tr = ai.translate(p.ai, sns, conv, f"{label} (AoE1)")
    if "passive" in names and "aggressive" not in names and p.number not in conv.attacks:
        tr.spec.pop("attack", None)
    if p.number in conv.attacks and "attack" not in tr.spec:
        # A personality without attack groups (AoE1's PASSIVE) told to attack: its own timing, and its boats too.
        tr.spec["attack"] = {"first": max(sns.get("SNInitialAttackDelay", ai.DEFAULT_FIRST_ATTACK), 1),
                             "every": max(sns.get("SNAttackSeparationTime", ai.DEFAULT_ATTACK_EVERY), 1),
                             "min_group": 2, "max_group": 12,
                             "naval": sns.get("SNNumberBoatAttackGroups", 0) > 0}
    if p.number in conv.attacks:
        # Small groups: Trade's Libyan raiders have 5 Scout Ships against their personality's boat groups of 6.
        tr.spec["attack"]["min_group"] = 2
        tr.spec.setdefault("strategic_numbers", {})["sn-minimum-boat-attack-group-size"] = 2
    tr.spec["army"] = civ_army(p, tr.spec)
    if debug:
        tr.spec["debug"] = True
    return tr


def builds(p) -> bool:
    """The player starts with a villager or town center."""
    return any(object_name(u.type).startswith(BUILDERS) for u in p.units)


def standard_ai(p, plan, conv: Conversion) -> dict | None:
    """RoR's standard skirmish AI (STANDARD_AI) for a computer player instead of its translated plan, or None."""
    if not isinstance(plan, ai.Translation) or not builds(p):
        return None
    names = f"{p.ai.strategy} {p.ai.personality}".lower()
    passive = "passive" in names and "aggressive" not in names and p.number not in conv.attacks
    waits = bool(conv.claim_base and conv.claim_base.get("start_ai"))
    if passive or waits:
        return None
    first = (plan.spec.get("attack") or {}).get("first", 0)
    return {**STANDARD_AI, "standard": {**STANDARD_AI["standard"], "attack_after": int(first)}}


def land_reach(terrain: list[int], width: int, starts: list[tuple[float, float]]) -> set[int]:
    """Tiles reachable on foot from any of `starts` (8-connected, water blocks)."""
    seen: set[int] = set()
    stack = []
    for x, y in starts:
        i = min(width - 1, max(0, int(y))) * width + min(width - 1, max(0, int(x)))
        if i not in seen:
            seen.add(i)
            stack.append(i)
    while stack:
        i = stack.pop()
        x, y = i % width, i // width
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < width:
                    j = ny * width + nx
                    if j not in seen and terrain[j] not in WATER:
                        seen.add(j)
                        stack.append(j)
    return seen


def ai_map_type(terrain: list[int], width: int, human, computers) -> str:
    """Islands when a computer player's units can't walk to the human player's, else land (AI_MAP_TYPES)."""
    if human is None or not human.units:
        return AI_MAP_TYPES["land"]
    reach = land_reach(terrain, width, [(u.x, u.y) for u in human.units])
    for p in computers:
        tiles = [min(width - 1, max(0, int(u.y))) * width + min(width - 1, max(0, int(u.x))) for u in p.units]
        if tiles and not any(t in reach for t in tiles):
            return AI_MAP_TYPES["islands"]
    return AI_MAP_TYPES["land"]


def start_view(p) -> tuple[int, int] | None:
    """Where a player's camera starts: over its Town Center (the busiest one), else over its densest group of units.
    AoE DE's start views are mostly the map's centre, far from the player (the user, 2026-11-12)."""
    if not p.units:
        return None

    def crowd(u) -> int:
        return sum((v.x - u.x) ** 2 + (v.y - u.y) ** 2 <= VIEW_RADIUS ** 2 for v in p.units)
    tcs = [u for u in p.units if object_name(u.type).startswith("Town Center")]
    best = max(tcs or p.units, key=crowd)
    return int(best.x), int(best.y)


def turn_hostile(conv: Conversion, humans: list[int], stances: dict) -> list[dict]:
    """Triggers for players that turn on you (conversion.yaml `attacks: {3: {hostile_at: 1200, message: ...}}`):
    AoE1's AIs change their stance in game (Trade's partners "could become jealous ... and attack"), RoR's scripts
    can't, so a timer makes them enemies of the human players. Not where the mission's own stances say otherwise."""
    out = []
    for n, a in conv.attacks.items():
        if not a.get("hostile_at") or any((n, h) in stances and (n, h) not in conv.diplomacy for h in humans):
            continue
        effects = [{"type": "change_diplomacy", "source_player": x, "target_player": y, "diplomacy": 3}
                   for h in humans for x, y in ((n, h), (h, n))]
        if a.get("message"):
            effects.append({"type": "display_instructions", "display_time": 10, "message": a["message"]})
        out.append({"name": f"P{n} turns hostile", "conditions": [{"type": "timer", "timer": int(a["hostile_at"])}],
                    "effects": effects})
    return out


def provoked_by(n: int, active) -> dict:
    """The AI's `provoked` setting: the human players, and the signal it sends when it turns on them."""
    return {"players": [q.number for q in active if q.human], "signal": PROVOKED_SIGNAL + n}


def answer_provoked(conv: Conversion, humans: list[int]) -> list[dict]:
    """Triggers for provoked players (conversion.yaml `provoked: {2: message}`): when the AI signals it has turned
    hostile (its town attacked), the human players are at war with it too, with the message. AoE1's AIs turned on
    whoever attacked them; RoR's keep their stance (the audit of neutral missions, 2026-11-12). Unverified in game."""
    out = []
    for n, message in conv.provoked.items():
        effects = [{"type": "change_diplomacy", "source_player": x, "target_player": y, "diplomacy": 3}
                   for h in humans for x, y in ((n, h), (h, n))]
        if message:
            effects.append({"type": "display_instructions", "display_time": 10, "message": message})
        out.append({"name": f"P{n} provoked", "conditions": [{"type": "ai_signal", "ai_signal": PROVOKED_SIGNAL + n}],
                    "effects": effects})
    return out


def player_settings(p, disable: list[str] = ()) -> dict:
    """player_set fields for a player's disables (the original's, plus `disable`: ror_tech_tree.yaml names) and
    starting view."""
    out: dict = {}
    if p.disabled or disable:
        tree = progression.tech_tree()
        out["disabled_buildings"] = [DISABLE_BUILDINGS[d] for d in p.disabled if d in DISABLE_BUILDINGS]
        out["disabled_techs"] = [DISABLE_TECHS[d] for d in p.disabled if d in DISABLE_TECHS]
        for name in disable:
            out["disabled_buildings"] += tree[name].get("objects", [])
            out["disabled_techs"] += tree[name].get("techs", [])
    view = start_view(p) or p.view
    if view:
        out["initial_player_view_x"], out["initial_player_view_y"] = view
    return out


def mission_text(src: Scenario, table: dict[int, str]) -> tuple[dict[str, str], dict[int, str],
                                                              dict[int, list[tuple[str, list[int]]]]]:
    """The messages (instructions, hints, victory, loss, history) and player names the game shows
    (AoE DE's string table where the scenario names an id, else the scenario's own text), and each
    player's to-do lines with the conditions each covers (objectives.lines)."""
    data = mission_data(src, table)
    names = {p["number"]: p["name"] for p in data["players"]}
    mine: dict[int, list[dict]] = {}
    for o in data["objectives"]:
        mine.setdefault(o["player"], []).append(o)
    return data["text"], names, {p: objectives.lines(objs, names) for p, objs in mine.items()}


def can_build(src: Scenario, conv: Conversion) -> bool:
    """Whether player 1 can build in this mission: starts with a villager or a town center, or claims a base."""
    if conv.claim_base:
        return True
    return any(object_name(u.type).startswith(BUILDERS) for u in src.players[0].units)


def reimagined_triggers(src: Scenario, conv: Conversion, mission: str, plan_triggers: list[dict],
                        all_perks: bool = False) -> list[dict]:
    """The reimagined layer (progression.py) for a campaign mission: winning unlocks ending it, bonus objectives
    by difficulty, upgrades. Changes the human player's victory triggers in `plan_triggers` in place."""
    slug, _, folder = mission.partition("/")
    camp = next((c for c in layout.campaigns() if c.slug == slug), None)
    human = next((p for p in src.active_players if p.human), None)
    if camp is None or human is None or not folder:
        return []
    folders = [m.folder.name for m in camp.missions]
    progression.hand_over(plan_triggers, human.number)
    computers = tuple(p.number for p in src.active_players if not p.human and p.ai is not None)
    return progression.triggers(progression.load(slug), folders, folders.index(folder) + 1, player=human.number,
                                computers=computers, all_perks=all_perks)


def mission_content(mission: str) -> tuple[progression.Campaign, str]:
    """The campaign's reimagined content and the mission's folder name ("" outside a campaign)."""
    slug, _, folder = mission.partition("/")
    return (progression.load(slug), folder) if folder else (progression.Campaign(), "")


@contextlib.contextmanager
def build_scenario(src: Scenario, conv: Conversion, mission: str = "", table: dict[int, str] | None = None,
                   ai_debug: bool = False, all_perks: bool = False, reimagined: bool = True):
    """Yield (AoE2ScenarioParser scenario flagged for RoR, ConvertResult). The scenario lives in an
    aoe-agent-editor session that closes on exit, so write or inspect it inside the block. `reimagined`: the
    reimagined layer on top (the RoR-RIX edition); without it the mission is the faithful one (RoR-RI)."""
    res = ConvertResult(mission or src.filename, Path())
    if src.width != src.height:
        raise ValueError(f"{src.filename}: map {src.width}x{src.height} can't become a square RoR map")
    active = src.active_players
    if len(active) > MAX_ROR_PLAYERS:
        raise ValueError(f"{src.filename}: {len(active)} active players, RoR scenarios hold {MAX_ROR_PLAYERS}")
    text, names, objective_texts = mission_text(src, table or {})
    o = SESSIONS.new(src.width, game="ror")
    s = o.scenario
    try:
        terrain = ror_terrain(src, conv)
        for i, tile in enumerate(s.map_manager.terrain):
            tile.terrain_id = terrain[i]
            tile.elevation = src.elevation[i]

        content, folder = mission_content(mission) if reimagined else (progression.Campaign(), "")
        # The mission's own disables and diplomacy, where it sets them (progression.disabled / diplomacy).
        own_disabled = progression.disabled(content, folder)
        active = [dataclasses.replace(p, disabled=own_disabled[p.number]) if p.number in own_disabled else p
                  for p in active]
        own_start = progression.starts(content, folder)
        active = [dataclasses.replace(p, starting_age=own_start[p.number].get("starting_age", p.starting_age),
                                      resources={**p.resources, **own_start[p.number].get("resources", {})})
                  if p.number in own_start else p for p in active]
        stances = {**conv.diplomacy, **progression.diplomacy(content, folder)}

        humans = {p.number for p in active if p.human}

        def stance(a: int, b: int) -> str:
            own = stances.get((a, b)) or DIPLOMACY.get(src.diplomacy[a - 1][b - 1], "ENEMY")
            back = stances.get((b, a)) or DIPLOMACY.get(src.diplomacy[b - 1][a - 1], "ENEMY")
            # A human neutral toward a player at war with them is at war too: RoR's neutral units don't fight back on
            # their own (Ascent of Egypt 6, Lower Egypt attacking a neutral you; the user, 2026-11-12).
            if a in humans and own == "NEUTRAL" and back == "ENEMY":
                return "ENEMY"
            return own
        extras = progression.extra_players(content, folder)
        custom_ai = progression.mission_ai(content, folder)
        s.player_manager.active_players = len(active) + len(extras)
        res.players = len(active) + len(extras)
        population = conv.population if conv.population and can_build(src, conv) else None
        for p in active:
            r = p.resources
            player_set(o.handle, p.number, {
                "civilization": ROR_CIVS[p.civ],
                "starting_age": ROR_AGES[p.starting_age],
                "human": p.human,
                "food": int(r["food"]), "wood": int(r["wood"]), "gold": int(r["gold"]),
                "stone": int(r["stone"]),
                "population_cap": population["cap"] if population else int(r["pop_cap"]),
                "tribe_name": names.get(p.number, p.name),
                "allied_victory": p.allied_victory,
                **player_settings(p, conv.disable.get(p.number, [])),
            })
        claim = conv.claim_base
        for p in active:
            plan = ror_ai(p, conv, ai_debug)
            change = custom_ai.get(p.number) or {}
            if plan == "immobile":
                ai_set(o.handle, p.number, "immobile")
                res.ai[p.number] = "immobile"
            elif not change and (std := standard_ai(p, plan, conv)):
                if p.number in conv.provoked:
                    std = {**std, "standard": {**std["standard"], "provoked": provoked_by(p.number, active)}}
                ai_set(o.handle, p.number, std)
                res.ai[p.number] = "standard (a level harder)"
            elif plan is not None:
                if not change.get("replace"):
                    if conv.ai_levels:
                        plan.spec["levels"] = conv.ai_levels
                    if population:
                        plan.spec["grow"] = {"to": population["cap"], "minutes": population["grow_minutes"]}
                if change:
                    plan.spec = progression.apply_ai(plan.spec, change)
                    if ai_debug:
                        plan.spec["debug"] = True
                    plan.skipped = [] if change.get("replace") else plan.skipped
                if claim and claim["start_ai"]:
                    plan.spec["start"] = {"trigger": AI_START_SIGNAL}
                if p.number in conv.provoked:
                    plan.spec["provoked"] = provoked_by(p.number, active)
                done = ai_set(o.handle, p.number, plan.spec)
                res.specs[p.number] = plan.spec
                res.ai[p.number] = f"{done['ai']}: {done['rules']} rules"
                res.ai_skipped += [f"P{p.number} {s}" for s in plan.skipped]
        for p in active:
            others = [q for q in active if q.number != p.number]
            for q in others:
                diplomacy_set(o.handle, p.number, [q.number], stance(p.number, q.number), mutual=False)
        # Players the reimagined mission adds: enemies of all but their `allies`, no AI (their units move by
        # trigger), no stockpile.
        for x in extras:
            player_set(o.handle, x["number"], {"civilization": x["civ"], "human": False, "food": 0, "wood": 0,
                                               "gold": 0, "stone": 0, "tribe_name": x["name"]})
            ai_set(o.handle, x["number"], "immobile")
            res.ai[x["number"]] = "immobile (reimagined)"
            for q in [p.number for p in active] + [y["number"] for y in extras if y is not x]:
                state = "ALLY" if q in (x.get("allies") or []) else "ENEMY"
                diplomacy_set(o.handle, x["number"], [q], state, mutual=True)

        for k, v in text.items():
            setattr(s.message_manager, k, v)
        # The Scouts page: anything the original has there, the upgrade choices (RoR-RIX), and the project's links.
        choices = progression.scouts_text(content, folder)
        s.message_manager.scouts = "\n\n".join(t for t in (text.get("scouts", ""), choices, LINKS) if t)

        refs = {}
        placed: dict[int, list[tuple[int, int]]] = {}
        for owner, ror_id, u in placements(src, conv, terrain, res.dropped):
            unit = s.unit_manager.add_unit(player=owner, unit_const=ror_id, x=u.x, y=u.y, z=u.z,
                                           rotation=u.rotation, status=NORMAL_STATUS)
            refs[u.id] = unit.reference_id
            placed.setdefault(owner, []).append((ror_id, unit.reference_id))
            res.placed += 1

        # The reimagined mission's own units, on the map from the start; groups name them for its triggers.
        groups: dict[str, tuple[int, list[int]]] = {}
        unit_hp: dict[int, int] = {}
        for mu in progression.mission_units(content, folder):
            ref = s.unit_manager.add_unit(player=mu["player"], unit_const=mu["unit"], x=mu["x"] + 0.5,
                                          y=mu["y"] + 0.5, status=NORMAL_STATUS).reference_id
            if "hp" in mu:
                unit_hp[ref] = mu["hp"]
            for g in [mu.get("group"), f"from {mu['from']}" if mu.get("from") else None]:
                if g:
                    groups.setdefault(g, (mu["player"], []))[1].append(ref)
            res.placed += 1

        vp = victory.plan(src, conv, refs, objective_texts, drop=progression.dropped_objectives(content, folder),
                          names=names, lose_needed=not reimagined)
        if extras and vp.mode != "CUSTOM":
            # Only a Custom victory keeps the game from ending when an added player is defeated.
            raise ValueError(f"{mission}: added players need a Custom victory, this mission is {vp.mode}")
        vp.triggers += turn_hostile(conv, [p.number for p in active if p.human], stances)
        vp.triggers += answer_provoked(conv, [p.number for p in active if p.human])
        layer = reimagined_triggers(src, conv, mission, vp.triggers, all_perks) if reimagined else []
        progression.select_objects(layer, placed, groups, unit_hp)
        vp.triggers += layer
        human = next((p for p in active if p.human), None)
        computers = [p for p in active if not p.human and p.ai is not None]
        options_set(o.handle, {**vp.options(), "ai_map_type": ai_map_type(terrain, src.width, human, computers)})
        if vp.triggers:
            triggers_add(o.handle, vp.triggers)
        res.victory, res.triggers, res.skipped = vp.mode, len(vp.triggers), vp.skipped
        if conv.reveal or conv.show_base or claim:
            ctx = blocks.Ctx(s)
            enemies = [p.number for p in active if not p.human and p.ai is not None
                       and stance(p.number, 1) == "ENEMY"]
            with games.use("ror"):
                for area in conv.reveal:
                    blocks.reveal(ctx, area=area, player=1)
                for area in conv.show_base:                 # the enemy AIs know where to attack from the start
                    for e in enemies:
                        blocks.reveal(ctx, area=area, player=e)
                if claim:
                    blocks.claim_base(ctx, area=claim["area"], player=claim["player"],
                                      signal=AI_START_SIGNAL if claim["start_ai"] else None,
                                      name="Base found")
            res.triggers = len(ctx.trigger_names())
        yield s, res
    finally:
        SESSIONS.close(o.handle)


def convert_mission(m: layout.Mission, conv: Conversion, out_root: Path = layout.AOE2DE_ROR,
                    *, ai_debug: bool = False, reimagined: bool = True) -> ConvertResult:
    out = scenario_path(m, out_root)
    out.parent.mkdir(parents=True, exist_ok=True)
    with build_scenario(load_scenario(m.scenario_path), conv.for_mission(m.key), m.key, strings.load(),
                        ai_debug, reimagined=reimagined) as (s, res):
        s.write_to_file(str(out))
    res.out = out
    return res


def probe_mission(m: layout.Mission, conv: Conversion, out_root: Path, *, minutes: int = 15,
                  ai_debug: bool = False) -> dict:
    """The converted mission as an AI probe (aoe2ed.ai.probe): it records what every player builds, trains and
    gathers, and stops itself after `minutes` game minutes. The checks compare each AI with its translated spec."""
    from aoe2ed.ai.probe import probe

    camp, mission = m.key.split("/")
    out = out_root / f"probe_{camp}_{mission}.aoe2scenario"
    # Every perk of the campaign applies in a probe, so the user can try them while the AIs are recorded.
    with build_scenario(load_scenario(m.scenario_path), conv.for_mission(m.key), m.key, strings.load(),
                        ai_debug, all_perks=True) as (s, res):
        return probe(s, out, specs=res.specs, game="ror", stop_after=minutes * 60)


def convert_campaign(c: layout.CampaignInfo, conv: Conversion | None = None, out_root: Path | None = None,
                     *, ai_debug: bool = False, pool: Executor | None = None, edition: Edition = editions.RI
                     ) -> tuple[list[Path], list[ConvertResult]]:
    """Convert every mission of a campaign in one edition (into its folder, or `out_root`) and bundle them into its
    .aoe2campaign, plus the campaign screen (`<slug>_layout.json`, `<slug>.json`) when RoR has one for it. The
    campaign's internal name is its slug (installing renames it). With a process `pool`, missions convert side by
    side."""
    conv = conv or load()
    out_root = out_root or edition.out
    convert = functools.partial(convert_mission, conv=conv, out_root=out_root, ai_debug=ai_debug,
                                reimagined=edition.reimagined)
    results = list(pool.map(convert, c.missions) if pool else map(convert, c.missions))
    return bundle_campaign(c, results, out_root, edition), results


def bundle_campaign(c: layout.CampaignInfo, results: list[ConvertResult],
                    out_root: Path = layout.AOE2DE_ROR, edition: Edition = editions.RI) -> list[Path]:
    """Bundle a campaign's converted missions into its .aoe2campaign and write its screen files (titled as the
    edition titles it)."""
    bundle = RorCampaign(c.slug)
    for m, r in zip(c.missions, results, strict=True):
        bundle.scenarios.append(CampaignScenario(m.title, r.out.name, r.out.read_bytes()))
    path = bundle.write(campaign_path(c, out_root))
    paths = [path]
    for suffix, data in screens(c, edition.campaign_title(c)).items():
        f = path.with_name(f"{c.slug}{suffix}")
        f.write_text(dumps(data), encoding="utf-8", newline="\n")
        paths.append(f)
    return paths
