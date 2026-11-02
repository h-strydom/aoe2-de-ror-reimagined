"""AoE DE scenarios (.aoescn, body version 3.13, as embedded in the official .aoecpn campaigns).

Layout established in the proof of concept (aoe1-to-ror) by reading all 61 official campaign scenarios;
every one of them parses with the invariants in tests/test_scenario.py, and every body is read to its
last byte. Decoded: players, messages (instructions, hints, victory, loss, history) with their
string-table ids, cinematics, global victory settings, diplomacy, starting ages and resources, the
tile map, units, and each player's individual victory conditions (the mission objectives). AoE DE
has no trigger system in these files: objectives are those victory conditions. AI files and
disables are skipped.

Layout (offsets into the inflated body):
  u32 next_unit_id, f32 version (3.13)
  16 x DE string            player names
  16 x u32                  player name string-table ids (-1 = none)
  16 x (u32 active, u32 human, u32 civ, u32 unknown)
  u32 (1), u8, f32 (-1)
  DE string filename; 5 x DE string: instructions, hints, victory, loss, history
  5 x (u32 string-table id, DE string label)   same order; the game shows strings.txt's text for the id
  4 x DE string             pregame, victory and loss cinematics, background bitmap (" <None> " = none)
  u32 bitmap included, i32 w, i32 h, i16 (no campaign scenario has a bitmap)
  3 x 16 x (u16 len + text) AI names per player: strategy (build list), city plan, personality
  16 x (3 x u32 lengths, then the three files' text)       the AI files themselves
  -99, -99                  double separator: the fixed-size block below hangs off it
  +8   10 x i32             global victory: conquest, ruins, artifacts, discoveries, exploration,
                            gold, all_custom, mode (0 standard, 1 conquest, 2 score, 3 time, 4 custom),
                            score, time
  +48  16 x 16 x i32        diplomacy (0 ally, 1 neutral, 3 enemy)
  +1072 11520 bytes          legacy individual victory (16 x 12 x 60; the conditions after the units are used)
  +12592 -99, 16 x i32       allied victory
  +12660 16 x 20 x i32       the editor's "Disable Technology" panel per player, 1 = allowed: DISABLES
                             (0xCDCDCDCD = never written, all allowed), then 3 x i32 (always 0)
  +13952 16 x i32            starting ages (0 Stone .. 3 Iron, 4 post-Iron; unverified)
  +14016 -99, f32, f32
  map  u32 w, u32 h, w*h x (u8 terrain, u8 elevation, u8 unused)     map = separator + 14028
  u32 sections (gaia + players), (sections-1) x 5 f32 resources (food, wood, gold, stone, pop cap)
  per section: u32 count, count x 23-byte unit (f32 x, f32 y, f32 z, u32 id, u16 type, u8 state, f32 rot)
  u32 9, then players 1..8:
    u16 len + name (NUL-terminated), f32 editor camera x, y, i16 view x, y (the editor's Set View: where
    the player's camera starts), u8 allied victory,
    u16 n, n x u8 diplomacy, n x i32, f32 (1.0), u32 conditions, u8,
    conditions x 44-byte victory condition (see VictoryCondition), 8 x u8
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field

from .binary import Cursor

SUPPORTED_BODY_VERSIONS = (3.13,)
MAX_PLAYERS = 16
SEPARATOR_PAIR = b"\x9d\xff\xff\xff" * 2
MAP_FROM_SEPARATOR = 14028
AGES = ("stone", "tool", "bronze", "iron", "post_iron")
MESSAGES = ("instructions", "hints", "victory", "loss", "history")
CINEMATICS = ("pregame", "victory", "loss", "bitmap")
NO_CINEMATIC = " <None> "
GLOBAL_VICTORY = ("conquest", "ruins", "artifacts", "discoveries", "exploration", "gold", "all_custom",
                  "mode", "score", "time")
VICTORY_MODES = ("standard", "conquest", "score", "time", "custom")
# Individual victory condition types, named after the game's objective texts (strings.txt 62801-62813)
# and checked against each mission's instructions.
# The editor's "Disable Technology" panel (strings.txt 13001-13017), in its order: buildings, ages.
DISABLES = ("granary", "storage_pit", "dock", "barracks", "market", "archery_range", "stable", "temple",
            "government_center", "siege_workshop", "academy", "tool_age", "bronze_age", "iron_age",
            "town_center", "wonder")
DISABLES_OFFSET, DISABLE_SLOTS = 12660, 20
UNSET = -842150451                            # 0xCDCDCDCD: memory the editor never wrote
AI_FILES = ("strategy", "city_plan", "personality")
NO_AI = ("", "NONE", " <None> ")
CONDITION_TYPES = ("capture", "create", "destroy", "destroy_multiple", "bring_to_area", "bring_to_object",
                   "attribute", "explore", "create_in_area", "destroy_all", "destroy_player")


@dataclass
class Unit:
    x: float
    y: float
    z: float
    id: int
    type: int
    state: int
    rotation: float


@dataclass
class VictoryCondition:
    """One individual victory condition (44 bytes). Fields a type doesn't use are 0 / -1."""
    type: str                         # CONDITION_TYPES
    object_type: int                  # object id (create, destroy_all, destroy_multiple ...)
    player: int                       # target player (destroy_player, owner of the target ...)
    area: tuple[float, float, float, float]   # x0, y0, x1, y1 (bring_to_area, create_in_area)
    number: int                       # count, or the attribute id for `attribute`
    amount: int                       # the attribute amount for `attribute`
    source: int                       # unit instance id (the object to bring)
    target: int                       # unit instance id (to destroy, capture, bring to)
    group: int                        # three trailing bytes: 1 (8 in Discoveries), 1 on every capture, 0
    ally: int
    state: int


@dataclass
class Ai:
    """A player's AoE1 AI: three named files embedded in the scenario."""
    strategy: str                 # build list name ("" = none)
    city_plan: str
    personality: str
    strategy_text: str = ""
    city_plan_text: str = ""
    personality_text: str = ""


@dataclass
class Player:
    number: int                       # 1..16
    name: str
    name_string_id: int               # strings.txt id for the name, -1 = none
    active: bool
    human: bool
    civ: int
    unknown: int                      # fourth u32 of the player record; meaning not yet known
    starting_age: int
    resources: dict[str, float] = field(default_factory=dict)
    units: list[Unit] = field(default_factory=list)
    allied_victory: bool = False      # players 1..8 only
    victory: list[VictoryCondition] = field(default_factory=list)   # players 1..8 only
    view: tuple[int, int] | None = None                              # players 1..8 only
    disabled: list[str] = field(default_factory=list)                # DISABLES entries turned off
    ai: Ai | None = None


@dataclass
class Scenario:
    filename: str
    header_version: str
    body_version: float
    description: str
    width: int
    height: int
    terrain: list[int]                # row-major, index y * width + x
    elevation: list[int]
    players: list[Player]             # players 1..16
    gaia_units: list[Unit]
    diplomacy: list[list[int]]        # diplomacy[i][j]: stance of player i+1 toward player j+1
    messages: dict[str, str] = field(default_factory=dict)            # MESSAGES -> embedded text
    message_ids: dict[str, int] = field(default_factory=dict)         # MESSAGES -> strings.txt id
    cinematics: dict[str, str] = field(default_factory=dict)          # CINEMATICS -> name, "" = none
    global_victory: dict[str, int] = field(default_factory=dict)      # GLOBAL_VICTORY -> value

    def tile(self, x: int, y: int) -> tuple[int, int]:
        i = y * self.width + x
        return self.terrain[i], self.elevation[i]

    @property
    def active_players(self) -> list[Player]:
        return [p for p in self.players if p.active]


def split_scenario(data: bytes) -> tuple[str, bytes, bytes]:
    """Split a scenario file into (header version, header bytes, inflated body)."""
    version = data[:4].decode("ascii")
    header_len = struct.unpack_from("<I", data, 4)[0]
    header = data[8:8 + header_len]
    body = zlib.decompress(data[8 + header_len:], -15)
    return version, header, body


def _header_description(header: bytes) -> str:
    c = Cursor(header)
    c.u32()  # header version (3)
    c.u32()  # timestamp
    return c.de_string()


def _unit(c: Cursor) -> Unit:
    x, y, z, uid, typ, state, rot = c.unpack("fffIHBf")
    return Unit(x, y, z, uid, typ, state, rot)


def _condition(c: Cursor) -> VictoryCondition:
    typ, obj, player, x0, y0, x1, y1, number, amount, source, target, group, ally, state = c.unpack("BiiffffiiiiBBB")
    if typ >= len(CONDITION_TYPES):
        raise ValueError(f"unknown victory condition type {typ} at {c.pos - 44}")
    return VictoryCondition(CONDITION_TYPES[typ], obj, player, (x0, y0, x1, y1), number, amount, source,
                            target, group, ally, state)


def _victory_players(c: Cursor, filename: str) -> list[tuple[bool, list[VictoryCondition], tuple[int, int]]]:
    """Players 1..8 after the units: (allied victory, individual victory conditions, start view)."""
    count = c.u32()
    if count != 9:
        raise ValueError(f"{filename}: expected 9 player slots after the units, got {count}")
    out = []
    for _ in range(count - 1):
        c.raw(c.u16())                       # name, NUL-terminated (the names at the top are the real ones)
        view = c.unpack("ffhh")[2:]          # editor camera (floats), then the start view
        allied = c.unpack("B")[0]
        n = c.u16()
        c.raw(n)
        c.unpack(f"{n}i")
        c.f32()
        conditions = c.u32()
        c.raw(1)
        out.append((allied == 1, [_condition(c) for _ in range(conditions)], view))
        c.raw(8)
    return out


def load_scenario(path) -> Scenario:
    from pathlib import Path
    p = Path(path)
    return read_scenario(p.read_bytes(), p.name)


def read_scenario(data: bytes, filename: str = "") -> Scenario:
    header_version, header, body = split_scenario(data)
    c = Cursor(body)
    c.u32()  # next unit id
    body_version = round(c.f32(), 3)
    if body_version not in SUPPORTED_BODY_VERSIONS:
        raise ValueError(f"{filename}: unsupported scenario body version {body_version}")

    names = [c.de_string() for _ in range(MAX_PLAYERS)]
    name_ids = c.unpack(f"{MAX_PLAYERS}i")
    records = [c.unpack("IIII") for _ in range(MAX_PLAYERS)]
    c.raw(9)
    c.de_string()  # filename
    messages = {k: c.de_string() for k in MESSAGES}
    message_ids = {}
    for k in MESSAGES:
        message_ids[k] = c.unpack("i")[0]
        c.de_string()  # label (the id as text, or empty)
    cinematics = {k: ("" if (v := c.de_string()) == NO_CINEMATIC else v) for k in CINEMATICS}
    if c.unpack("IiiH")[0]:
        raise ValueError(f"{filename}: scenario bitmaps aren't supported")
    ai_names = [[c.raw(c.u16()).decode("latin-1") for _ in range(MAX_PLAYERS)] for _ in AI_FILES]
    ais = []
    for i in range(MAX_PLAYERS):
        lengths = c.unpack("III")
        texts = [c.raw(n).decode("latin-1").replace("\r\n", "\n") for n in lengths]
        files = ["" if ai_names[k][i] in NO_AI else ai_names[k][i] for k in range(3)]
        ais.append(Ai(*files, *texts))

    sep = body.find(SEPARATOR_PAIR, c.pos)
    if sep < 0:
        raise ValueError(f"{filename}: section separator not found")
    if c.pos != sep:
        raise ValueError(f"{filename}: {sep - c.pos} unread bytes before the separator")
    global_victory = dict(zip(GLOBAL_VICTORY, struct.unpack_from("<10i", body, sep + 8), strict=True))
    grid = struct.unpack_from(f"<{MAX_PLAYERS * DISABLE_SLOTS}i", body, sep + DISABLES_OFFSET)
    disabled = [[name for k, name in enumerate(DISABLES) if grid[i * DISABLE_SLOTS + k] == 0]
                for i in range(MAX_PLAYERS)]
    diplomacy_flat = struct.unpack_from(f"<{MAX_PLAYERS * MAX_PLAYERS}i", body, sep + 8 + 40)
    diplomacy = [list(diplomacy_flat[i * MAX_PLAYERS:(i + 1) * MAX_PLAYERS]) for i in range(MAX_PLAYERS)]

    m = sep + MAP_FROM_SEPARATOR
    if body[m - 12:m - 8] != SEPARATOR_PAIR[:4]:
        raise ValueError(f"{filename}: no separator before the map at {m - 12}")
    ages = struct.unpack_from(f"<{MAX_PLAYERS}i", body, m - 12 - 4 * MAX_PLAYERS)

    c.pos = m
    w, h = c.u32(), c.u32()
    if not (1 <= w <= 512 and 1 <= h <= 512):
        raise ValueError(f"{filename}: implausible map size {w}x{h}")
    tiles = c.raw(w * h * 3)
    terrain, elevation = list(tiles[0::3]), list(tiles[1::3])

    sections = c.u32()
    resources = [dict(zip(("food", "wood", "gold", "stone", "pop_cap"), c.unpack("5f"), strict=True))
                 for _ in range(sections - 1)]
    unit_lists = []
    for _ in range(sections):
        unit_lists.append([_unit(c) for _ in range(c.u32())])
    for u in (u for ul in unit_lists for u in ul):
        if not (-1 <= u.x <= w + 1 and -1 <= u.y <= h + 1):
            raise ValueError(f"{filename}: unit {u.id} at ({u.x}, {u.y}) is off a {w}x{h} map")

    victory = _victory_players(c, filename)
    if c.pos != len(body):
        raise ValueError(f"{filename}: {len(body) - c.pos} unread bytes after the victory conditions")

    players = []
    for i, (active, human, civ, unknown) in enumerate(records):
        n = i + 1
        allied, conditions, view = victory[i] if i < len(victory) else (False, [], None)
        players.append(Player(
            number=n, name=names[i], name_string_id=name_ids[i], active=bool(active), human=bool(human),
            civ=civ, unknown=unknown, starting_age=ages[i],
            resources=resources[i] if i < len(resources) else {},
            units=unit_lists[n] if n < len(unit_lists) else [],
            allied_victory=allied, victory=conditions, view=view, disabled=disabled[i], ai=ais[i],
        ))

    return Scenario(
        filename=filename, header_version=header_version, body_version=body_version,
        description=_header_description(header), width=w, height=h,
        terrain=terrain, elevation=elevation, players=players, gaia_units=unit_lists[0],
        diplomacy=diplomacy, messages=messages, message_ids=message_ids, cinematics=cinematics,
        global_victory=global_victory,
    )
