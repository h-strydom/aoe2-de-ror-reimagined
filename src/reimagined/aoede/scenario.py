"""AoE DE scenarios (.aoescn, body version 3.13, as embedded in the official .aoecpn campaigns).

Layout established in the proof of concept (aoe1-to-ror) by reading all 61 official campaign scenarios;
every one of them parses with the invariants in tests/test_scenario.py. Only what the converter needs is
decoded: players, diplomacy, starting ages and resources,
the tile map and units. Triggers, messages, cinematics and AI files are skipped.

Layout (offsets into the inflated body):
  u32 next_unit_id, f32 version (3.13)
  16 x DE string            player names
  16 x u32                  player name string-table ids (-1 = none)
  16 x (u32 active, u32 human, u32 civ, u32 unknown)
  ... messages, cinematics, AI files (skipped) ...
  -99, -99                  double separator: the fixed-size block below hangs off it
  +8   10 x i32             global victory
  +48  16 x 16 x i32        diplomacy (0 ally, 1 neutral, 3 enemy)
  ...  individual victory, allied victory, disables
  map-76  3 x i32 + 16 x i32 starting ages (0 Stone .. 3 Iron, 4 post-Iron; unverified)
  map-12  -99, f32, f32
  map  u32 w, u32 h, w*h x (u8 terrain, u8 elevation, u8 unused)     map = separator + 14028
  u32 sections (gaia + players), (sections-1) x 5 f32 resources (food, wood, gold, stone, pop cap)
  per section: u32 count, count x 23-byte unit (f32 x, f32 y, f32 z, u32 id, u16 type, u8 state, f32 rot)
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
class Player:
    number: int                       # 1..16
    name: str
    active: bool
    human: bool
    civ: int
    unknown: int                      # fourth u32 of the player record; meaning not yet known
    starting_age: int
    resources: dict[str, float] = field(default_factory=dict)
    units: list[Unit] = field(default_factory=list)


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
    c.unpack(f"{MAX_PLAYERS}i")  # name string-table ids
    records = [c.unpack("IIII") for _ in range(MAX_PLAYERS)]

    sep = body.find(SEPARATOR_PAIR, c.pos)
    if sep < 0:
        raise ValueError(f"{filename}: section separator not found")
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

    players = []
    for i, (active, human, civ, unknown) in enumerate(records):
        n = i + 1
        players.append(Player(
            number=n, name=names[i], active=bool(active), human=bool(human), civ=civ, unknown=unknown,
            starting_age=ages[i],
            resources=resources[i] if i < len(resources) else {},
            units=unit_lists[n] if n < len(unit_lists) else [],
        ))

    return Scenario(
        filename=filename, header_version=header_version, body_version=body_version,
        description=_header_description(header), width=w, height=h,
        terrain=terrain, elevation=elevation, players=players, gaia_units=unit_lists[0],
        diplomacy=diplomacy,
    )
