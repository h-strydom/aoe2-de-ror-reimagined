"""AoE DE scenarios -> Return of Rome scenarios and campaigns, following aoe2de_ror/conversion.yaml.

Per scenario: same map size; every tile's terrain swapped (after terrain.py's clean-up of stray
road tiles) and elevation copied; the active players with their civ, starting age, resources and
diplomacy; every object placed at the same position, rotation and owner (forest trees on a RoR
forest terrain take that terrain's tree). Triggers aren't converted. Dropped objects (marked `drop`,
or owned by an inactive player) are counted in the result, so nothing disappears silently.
"""
from __future__ import annotations

import contextlib
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from aoe2ed.campaign import Campaign as RorCampaign
from aoe2ed.campaign import CampaignScenario
from aoe2ed.session import SESSIONS
from aoe2ed.tools.logic import triggers_add
from aoe2ed.tools.world import diplomacy_set, options_set, player_set

from . import layout, victory
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
CAMPAIGN_TITLE = "AoE1 {title}"   # keeps them apart from RoR's own campaigns of the same name
MOD_NAME = "AoE1 DE Campaigns (RoR Reimagined)"   # local mod `convert --install` writes; screens need a mod


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


def ror_ai(p) -> str | None:
    """The RoR AI setting closest to a computer player's AoE1 AI, or None for RoR's standard AI.
    AoE1 AI files (build list, city plan, personality) are a different system from RoR's scripts, so
    only their intent carries over: immobile units stay put, passive players do nothing on their own."""
    if p.human or p.ai is None:
        return None
    names = f"{p.ai.strategy} {p.ai.personality}".lower()
    if "immobile" in names:
        return "immobile"
    if "passive" in names and "aggressive" not in names:
        return "none"
    return None


def player_settings(p) -> dict:
    """player_set fields for a player's disables, starting view and AI."""
    out: dict = {}
    if p.disabled:
        out["disabled_buildings"] = [DISABLE_BUILDINGS[d] for d in p.disabled if d in DISABLE_BUILDINGS]
        out["disabled_techs"] = [DISABLE_TECHS[d] for d in p.disabled if d in DISABLE_TECHS]
    if p.view:
        out["initial_player_view_x"], out["initial_player_view_y"] = p.view
    ai = ror_ai(p)
    if ai:
        out["ai"] = ai
    return out


def mission_text(src: Scenario, table: dict[int, str]) -> tuple[dict[str, str], dict[int, str], dict[int, list[str]]]:
    """The messages (instructions, hints, victory, loss, history) and player names the game shows
    (AoE DE's string table where the scenario names an id, else the scenario's own text), and each
    player's objective lines."""
    data = mission_data(src, table)
    objectives: dict[int, list[str]] = {}
    for o in data["objectives"]:
        line = re.sub(r" \(#\d+\)", "", o["summary"])
        line = re.sub(r"the area \(.*\)", "the marked area", line)   # AoE DE's wording (strings 62804, 62808)
        objectives.setdefault(o["player"], []).append(line + ".")
    return data["text"], {p["number"]: p["name"] for p in data["players"]}, objectives


@contextlib.contextmanager
def build_scenario(src: Scenario, conv: Conversion, mission: str = "", table: dict[int, str] | None = None):
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
        for p in active:
            r = p.resources
            player_set(o.handle, p.number, {
                "civilization": ROR_CIVS[p.civ],
                "starting_age": ROR_AGES[p.starting_age],
                "human": p.human,
                "food": int(r["food"]), "wood": int(r["wood"]), "gold": int(r["gold"]),
                "stone": int(r["stone"]), "population_cap": int(r["pop_cap"]),
                "tribe_name": names.get(p.number, p.name),
                "allied_victory": p.allied_victory,
                **player_settings(p),
            })
        for p in active:
            others = [q for q in active if q.number != p.number]
            for q in others:
                state = DIPLOMACY.get(src.diplomacy[p.number - 1][q.number - 1], "ENEMY")
                diplomacy_set(o.handle, p.number, [q.number], state, mutual=False)

        for k, v in text.items():
            setattr(s.message_manager, k, v)

        refs = {}
        for owner, ror_id, u in placements(src, conv, terrain, res.dropped):
            unit = s.unit_manager.add_unit(player=owner, unit_const=ror_id, x=u.x, y=u.y, z=u.z,
                                           rotation=u.rotation, status=NORMAL_STATUS)
            refs[u.id] = unit.reference_id
            res.placed += 1

        vp = victory.plan(src, conv, refs, objective_texts)
        options_set(o.handle, {"victory_condition": vp.mode})
        if vp.triggers:
            triggers_add(o.handle, vp.triggers)
        res.victory, res.triggers, res.skipped = vp.mode, len(vp.triggers), vp.skipped
        yield s, res
    finally:
        SESSIONS.close(o.handle)


def convert_mission(m: layout.Mission, conv: Conversion, out_root: Path = layout.AOE2DE_ROR) -> ConvertResult:
    out = scenario_path(m, out_root)
    out.parent.mkdir(parents=True, exist_ok=True)
    with build_scenario(load_scenario(m.scenario_path), conv.for_mission(m.key), m.key, strings.load()) as (s, res):
        s.write_to_file(str(out))
    res.out = out
    return res


def convert_campaign(c: layout.CampaignInfo, conv: Conversion | None = None,
                     out_root: Path = layout.AOE2DE_ROR) -> tuple[list[Path], list[ConvertResult]]:
    """Convert every mission of a campaign and bundle them into its .aoe2campaign, plus the campaign
    screen (`<slug>_layout.json`, `<slug>.json`) when RoR has one for it. The campaign's internal name
    is its slug, which the game needs to find the screen."""
    conv = conv or load()
    results = [convert_mission(m, conv, out_root) for m in c.missions]
    bundle = RorCampaign(c.slug)
    for m, r in zip(c.missions, results, strict=True):
        bundle.scenarios.append(CampaignScenario(m.title, r.out.name, r.out.read_bytes()))
    path = bundle.write(campaign_path(c, out_root))
    paths = [path]
    for suffix, data in screens(c, campaign_title(c)).items():
        f = path.with_name(f"{c.slug}{suffix}")
        f.write_text(dumps(data), encoding="utf-8", newline="\n")
        paths.append(f)
    return paths, results
