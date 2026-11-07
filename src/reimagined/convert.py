"""AoE DE scenarios -> Return of Rome scenarios and campaigns, following aoe2de_ror/conversion.yaml.

Per scenario: same map size; every tile's terrain swapped (after terrain.py's clean-up of stray
road tiles) and elevation copied; the active players with their civ, starting age, resources and
diplomacy; every object placed at the same position, rotation and owner (forest trees on a RoR
forest terrain take that terrain's tree). Triggers aren't converted. Dropped objects (marked `drop`,
or owned by an inactive player) are counted in the result, so nothing disappears silently.
"""
from __future__ import annotations

import contextlib
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

from . import ai, layout, missions, objectives, progression, victory
from .aoede import strings
from .aoede.names import object_name
from .aoede.scenario import Scenario, load_scenario
from .conversion import Conversion, load
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
AI_START_SIGNAL = 1               # AI Script Goal a mission's claim_base sends to computer players set to wait for it
CAMPAIGN_TITLE = "AoE1 {title}"   # keeps them apart from RoR's own campaigns of the same name
BUILDERS = ("Villager", "Town Center")            # AoE DE names: player 1 owning one can build (rules.population)


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


def campaign_title(c: layout.CampaignInfo) -> str:
    return CAMPAIGN_TITLE.format(title=c.title)


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
    if "passive" in names and "aggressive" not in names:
        tr.spec.pop("attack", None)
    tr.spec["army"] = civ_army(p, tr.spec)
    if debug:
        tr.spec["debug"] = True
    return tr


def player_settings(p) -> dict:
    """player_set fields for a player's disables and starting view."""
    out: dict = {}
    if p.disabled:
        out["disabled_buildings"] = [DISABLE_BUILDINGS[d] for d in p.disabled if d in DISABLE_BUILDINGS]
        out["disabled_techs"] = [DISABLE_TECHS[d] for d in p.disabled if d in DISABLE_TECHS]
    if p.view:
        out["initial_player_view_x"], out["initial_player_view_y"] = p.view
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


def reimagined_triggers(src: Scenario, conv: Conversion, mission: str, plan_triggers: list[dict]) -> list[dict]:
    """The reimagined layer (progression.py) for a campaign mission: winning unlocks ending it, bonus objectives
    by difficulty, upgrades. Changes the human player's victory triggers in `plan_triggers` in place."""
    slug, _, folder = mission.partition("/")
    camp = next((c for c in layout.campaigns() if c.slug == slug), None)
    human = next((p.number for p in src.active_players if p.human), None)
    if camp is None or human is None or not folder:
        return []
    folders = [m.folder.name for m in camp.missions]
    progression.hand_over(plan_triggers, human)
    return progression.triggers(progression.load(slug), folders, folders.index(folder) + 1, player=human,
                                town_center=can_build(src, conv))


@contextlib.contextmanager
def build_scenario(src: Scenario, conv: Conversion, mission: str = "", table: dict[int, str] | None = None,
                   ai_debug: bool = False):
    """Yield (AoE2ScenarioParser scenario flagged for RoR, ConvertResult). The scenario lives in an
    aoe-agent-editor session that closes on exit, so write or inspect it inside the block."""
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

        s.player_manager.active_players = len(active)
        res.players = len(active)
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
                **player_settings(p),
            })
        claim = conv.claim_base
        for p in active:
            plan = ror_ai(p, conv, ai_debug)
            if plan == "immobile":
                ai_set(o.handle, p.number, "immobile")
                res.ai[p.number] = "immobile"
            elif plan is not None:
                if conv.ai_levels:
                    plan.spec["levels"] = conv.ai_levels
                if population:
                    plan.spec["grow"] = {"to": population["cap"], "minutes": population["grow_minutes"]}
                if claim and claim["start_ai"]:
                    plan.spec["start"] = {"trigger": AI_START_SIGNAL}
                done = ai_set(o.handle, p.number, plan.spec)
                res.specs[p.number] = plan.spec
                res.ai[p.number] = f"{done['ai']}: {done['rules']} rules"
                res.ai_skipped += [f"P{p.number} {s}" for s in plan.skipped]
        for p in active:
            others = [q for q in active if q.number != p.number]
            for q in others:
                state = DIPLOMACY.get(src.diplomacy[p.number - 1][q.number - 1], "ENEMY")
                diplomacy_set(o.handle, p.number, [q.number], state, mutual=False)

        for k, v in text.items():
            setattr(s.message_manager, k, v)

        refs = {}
        placed: dict[int, list[tuple[int, int]]] = {}
        for owner, ror_id, u in placements(src, conv, terrain, res.dropped):
            unit = s.unit_manager.add_unit(player=owner, unit_const=ror_id, x=u.x, y=u.y, z=u.z,
                                           rotation=u.rotation, status=NORMAL_STATUS)
            refs[u.id] = unit.reference_id
            placed.setdefault(owner, []).append((ror_id, unit.reference_id))
            res.placed += 1

        vp = victory.plan(src, conv, refs, objective_texts)
        reimagined = reimagined_triggers(src, conv, mission, vp.triggers)
        progression.select_objects(reimagined, placed)
        vp.triggers += reimagined
        options_set(o.handle, {"victory_condition": vp.mode})
        if vp.triggers:
            triggers_add(o.handle, vp.triggers)
        res.victory, res.triggers, res.skipped = vp.mode, len(vp.triggers), vp.skipped
        if conv.reveal or conv.show_base or claim:
            ctx = blocks.Ctx(s)
            enemies = [p.number for p in active if not p.human and p.ai is not None
                       and DIPLOMACY.get(src.diplomacy[p.number - 1][0], "ENEMY") == "ENEMY"]
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
                    *, ai_debug: bool = False) -> ConvertResult:
    out = scenario_path(m, out_root)
    out.parent.mkdir(parents=True, exist_ok=True)
    with build_scenario(load_scenario(m.scenario_path), conv.for_mission(m.key), m.key, strings.load(),
                        ai_debug) as (s, res):
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
    with build_scenario(load_scenario(m.scenario_path), conv.for_mission(m.key), m.key, strings.load(),
                        ai_debug) as (s, res):
        return probe(s, out, specs=res.specs, game="ror", stop_after=minutes * 60)


def convert_campaign(c: layout.CampaignInfo, conv: Conversion | None = None, out_root: Path = layout.AOE2DE_ROR,
                     *, ai_debug: bool = False, pool: Executor | None = None
                     ) -> tuple[list[Path], list[ConvertResult]]:
    """Convert every mission of a campaign and bundle them into its .aoe2campaign, plus the campaign
    screen (`<slug>_layout.json`, `<slug>.json`) when RoR has one for it. The campaign's internal name
    is its slug, which the game needs to find the screen. With a process `pool`, missions convert side by side."""
    conv = conv or load()
    convert = functools.partial(convert_mission, conv=conv, out_root=out_root, ai_debug=ai_debug)
    results = list(pool.map(convert, c.missions) if pool else map(convert, c.missions))
    return bundle_campaign(c, results, out_root), results


def bundle_campaign(c: layout.CampaignInfo, results: list[ConvertResult],
                    out_root: Path = layout.AOE2DE_ROR) -> list[Path]:
    """Bundle a campaign's converted missions into its .aoe2campaign and write its screen files."""
    bundle = RorCampaign(c.slug)
    for m, r in zip(c.missions, results, strict=True):
        bundle.scenarios.append(CampaignScenario(m.title, r.out.name, r.out.read_bytes()))
    path = bundle.write(campaign_path(c, out_root))
    paths = [path]
    for suffix, data in screens(c, campaign_title(c)).items():
        f = path.with_name(f"{c.slug}{suffix}")
        f.write_text(dumps(data), encoding="utf-8", newline="\n")
        paths.append(f)
    return paths
