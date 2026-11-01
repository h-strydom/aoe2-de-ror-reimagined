"""AoE DE scenarios -> Return of Rome scenarios and campaigns, following aoe2de_ror/conversion.yaml.

Per scenario: same map size; every tile's terrain swapped (after terrain.py's clean-up of stray
road tiles) and elevation copied; the active players with their civ, starting age, resources and
diplomacy; every object placed at the same position, rotation and owner (forest trees on a RoR
forest terrain take that terrain's tree). Triggers aren't converted. Dropped objects (marked `drop`,
or owned by an inactive player) are counted in the result, so nothing disappears silently.
"""
from __future__ import annotations

import contextlib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from aoe2ed.campaign import Campaign as RorCampaign
from aoe2ed.campaign import CampaignScenario
from aoe2ed.session import SESSIONS
from aoe2ed.tools.world import diplomacy_set, player_set

from . import layout
from .aoede.names import object_name
from .aoede.scenario import Scenario, load_scenario
from .conversion import Conversion, load
from .terrain import clean_terrain

# RoR civ data names by civ id. AoE DE's civs 0..16 (Gaia..Macedonian) are RoR's first 17, same order.
ROR_CIVS = (None, "EGYPTIAN", "GREEK", "BABYLONIAN", "ASSYRIAN", "MINOAN", "HITTITE", "PHOENICIAN",
            "SUMERIAN", "PERSIAN", "SHANG", "YAMATO", "CHOSON", "ROMAN", "CARTHAGINIAN", "PALMYRAN",
            "MACEDONIAN")
# AoE DE starting age 0..4 (Stone, Tool, Bronze, Iron, post-Iron) -> the parser's age names.
# Unverified in game: RoR may not map its ages one to one onto these values.
ROR_AGES = ("DARK", "FEUDAL", "CASTLE", "IMPERIAL", "POST_IMPERIAL")
DIPLOMACY = {0: "ALLY", 1: "NEUTRAL", 3: "ENEMY"}
# RoR's campaign map places at most 9 flags for a campaign without its own layout file
# (proof-of-concept playtest: Ascent of Egypt's missions 10-12 had no flag), so longer campaigns
# ship in parts.
MAX_MISSIONS_PER_CAMPAIGN = 9
MAX_ROR_PLAYERS = 8
NORMAL_STATUS = 2
CAMPAIGN_TITLE = "AoE1 {title}"   # keeps them apart from RoR's own campaigns of the same name


@dataclass
class ConvertResult:
    mission: str
    out: Path
    placed: int = 0
    dropped: Counter = field(default_factory=Counter)   # reason -> count
    players: int = 0


def scenario_path(m: layout.Mission, out_root: Path = layout.AOE2DE_ROR) -> Path:
    camp, mission = m.key.split("/")
    return out_root / camp / mission / f"{camp}_{mission}.aoe2scenario"


def campaign_parts(n_missions: int) -> list[range]:
    """0-based mission indexes per campaign file: 12 missions -> [0..8], [9..11]."""
    step = MAX_MISSIONS_PER_CAMPAIGN
    return [range(a, min(a + step, n_missions)) for a in range(0, n_missions, step)]


def campaign_path(c: layout.CampaignInfo, part: int, out_root: Path = layout.AOE2DE_ROR) -> Path:
    suffix = f"_part{part}" if part > 1 else ""
    return out_root / c.slug / f"{c.slug}{suffix}.aoe2campaign"


def campaign_title(c: layout.CampaignInfo, part: int, parts: int) -> str:
    title = CAMPAIGN_TITLE.format(title=c.title)
    return f"{title} ({part}/{parts})" if parts > 1 else title


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


@contextlib.contextmanager
def build_scenario(src: Scenario, conv: Conversion, mission: str = ""):
    """Yield (AoE2ScenarioParser scenario flagged for RoR, ConvertResult). The scenario lives in an
    aoe-agent-editor session that closes on exit, so write or inspect it inside the block."""
    res = ConvertResult(mission or src.filename, Path())
    if src.width != src.height:
        raise ValueError(f"{src.filename}: map {src.width}x{src.height} can't become a square RoR map")
    active = src.active_players
    if len(active) > MAX_ROR_PLAYERS:
        raise ValueError(f"{src.filename}: {len(active)} active players, RoR scenarios hold {MAX_ROR_PLAYERS}")
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
                "tribe_name": p.name,
            })
        for p in active:
            others = [q for q in active if q.number != p.number]
            for q in others:
                state = DIPLOMACY.get(src.diplomacy[p.number - 1][q.number - 1], "ENEMY")
                diplomacy_set(o.handle, p.number, [q.number], state, mutual=False)

        if src.description:
            s.message_manager.instructions = src.description

        for owner, ror_id, u in placements(src, conv, terrain, res.dropped):
            s.unit_manager.add_unit(player=owner, unit_const=ror_id, x=u.x, y=u.y, z=u.z,
                                    rotation=u.rotation, status=NORMAL_STATUS)
            res.placed += 1
        yield s, res
    finally:
        SESSIONS.close(o.handle)


def convert_mission(m: layout.Mission, conv: Conversion, out_root: Path = layout.AOE2DE_ROR) -> ConvertResult:
    out = scenario_path(m, out_root)
    out.parent.mkdir(parents=True, exist_ok=True)
    with build_scenario(load_scenario(m.scenario_path), conv.for_mission(m.key), m.key) as (s, res):
        s.write_to_file(str(out))
    res.out = out
    return res


def convert_campaign(c: layout.CampaignInfo, conv: Conversion | None = None,
                     out_root: Path = layout.AOE2DE_ROR) -> tuple[list[Path], list[ConvertResult]]:
    """Convert every mission of a campaign and bundle them into its .aoe2campaign file(s)."""
    conv = conv or load()
    results = [convert_mission(m, conv, out_root) for m in c.missions]
    parts = campaign_parts(len(c.missions))
    paths = []
    for part, indexes in enumerate(parts, start=1):
        bundle = RorCampaign(campaign_title(c, part, len(parts)))
        for i in indexes:
            out = results[i].out
            bundle.scenarios.append(CampaignScenario(c.missions[i].title, out.name, out.read_bytes()))
        paths.append(bundle.write(campaign_path(c, part, out_root)))
    return paths, results
