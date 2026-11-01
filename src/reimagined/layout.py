"""Where things live in the repository.

aoe1de/
  <campaign>.yaml                 campaign file: title, source .aoecpn, missions in play order
  <campaign>/
    <source>.aoecpn               copy of the original campaign file (local only, git-ignored)
    NN_<mission>/
      mission.yaml                mission title and its source scenario
      <source>.aoescn             the original scenario, extracted (local only, git-ignored)
  data/                           AoE DE game data the converter reads (local only, git-ignored)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
AOE1DE = ROOT / "aoe1de"


@dataclass
class Mission:
    folder: Path
    title: str
    source_scenario: str

    @property
    def scenario_path(self) -> Path:
        return self.folder / self.source_scenario


@dataclass
class CampaignInfo:
    slug: str
    title: str
    order: int
    source_file: str
    missions: list[Mission]
    root: Path = AOE1DE

    @property
    def folder(self) -> Path:
        return self.root / self.slug

    @property
    def source_path(self) -> Path:
        return self.folder / self.source_file


def campaigns(root: Path = AOE1DE) -> list[CampaignInfo]:
    """Every campaign under aoe1de/, in the original order."""
    out = []
    for f in root.glob("*.yaml"):
        spec = yaml.safe_load(f.read_text(encoding="utf-8"))
        missions = []
        for name in spec["missions"]:
            m = yaml.safe_load((root / f.stem / name / "mission.yaml").read_text(encoding="utf-8"))
            missions.append(Mission(root / f.stem / name, m["title"], m["source"]["scenario"]))
        out.append(CampaignInfo(f.stem, spec["title"], spec["order"], spec["source_file"], missions, root))
    return sorted(out, key=lambda c: c.order)
