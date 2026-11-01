"""AoE DE .aoecpn campaign containers.

Layout (little endian), established by reading the 10 official campaigns:
  char[4]  version              b"1.10" in every official campaign
  u32      scenario count
  DE str   campaign name
  per scenario: u64 size, u64 offset (absolute, into this file), DE str name, DE str filename
  scenario files (.aoescn), stored as is at their offsets
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

from .binary import Cursor, de_string


@dataclass
class CampaignEntry:
    name: str
    filename: str
    data: bytes


@dataclass
class Campaign:
    version: str
    name: str
    entries: list[CampaignEntry]


def read_campaign(data: bytes) -> Campaign:
    c = Cursor(data)
    version = c.raw(4).decode("ascii", "replace")
    count = c.u32()
    name = c.de_string()
    entries = []
    for _ in range(count):
        size, offset = c.u64(), c.u64()
        entry_name, filename = c.de_string(), c.de_string()
        if offset + size > len(data):
            raise ValueError(f"{name}: {filename} runs past the end of the file")
        entries.append(CampaignEntry(entry_name, filename, data[offset:offset + size]))
    return Campaign(version, name, entries)


def load_campaign(path: str | Path) -> Campaign:
    return read_campaign(Path(path).read_bytes())


def build_campaign(name: str, entries: list[CampaignEntry], version: str = "1.10") -> bytes:
    """Write a container in the same layout (used for test fixtures)."""
    head = version.encode("ascii") + struct.pack("<I", len(entries)) + de_string(name)
    table_size = sum(16 + len(de_string(e.name)) + len(de_string(e.filename)) for e in entries)
    offset = len(head) + table_size
    table = b""
    for e in entries:
        table += struct.pack("<QQ", len(e.data), offset) + de_string(e.name) + de_string(e.filename)
        offset += len(e.data)
    return head + table + b"".join(e.data for e in entries)
