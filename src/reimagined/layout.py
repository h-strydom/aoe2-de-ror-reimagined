"""Where things live in the repository.

aoe1de/
  <campaign>.yaml                 campaign file: title, display name, description, source .aoecpn, missions
  <campaign>/
    <source>.aoecpn               copy of the original campaign file (local only, git-ignored)
    NN_<mission>/
      mission.yaml                title, source scenario, players, victory, objectives, mission text
      <source>.aoescn             the original scenario, extracted (local only, git-ignored)
  data/                           AoE DE game data the converter reads: empires.dat, strings.txt, and under
                                  Data/, Assets/UI/, Content/Voice Over/en/ the campaign art and narration
                                  (local only, git-ignored)

aoe2de_ror/
  conversion.yaml                 what each AoE DE terrain and object becomes in RoR, plus mission overrides
  <campaign>/
    <campaign>.aoe2campaign       the converted campaign (_part2... when RoR's map can't show every mission)
    NN_<mission>/
      <campaign>_NN_<mission>.aoe2scenario   the converted scenario
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
AOE1DE = ROOT / "aoe1de"
AOE2DE_ROR = ROOT / "aoe2de_ror"


@dataclass
class Mission:
    folder: Path
    title: str
    source_scenario: str

    @property
    def scenario_path(self) -> Path:
        return self.folder / self.source_scenario

    @property
    def key(self) -> str:
        """`<campaign>/<NN_mission>`, the name conversion.yaml's mission overrides use."""
        return f"{self.folder.parent.name}/{self.folder.name}"


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
