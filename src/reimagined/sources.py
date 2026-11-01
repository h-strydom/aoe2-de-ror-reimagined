"""`reimagined setup`: copy the AoE DE source files from a local install into aoe1de/.

The copies are git-ignored: the original game files aren't redistributed, so everyone fills
aoe1de/ from their own install. After setup, nothing reads the install again, so AoE DE can be
uninstalled and every path stays inside the repository.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from . import layout
from .aoede.campaign import load_campaign
from .aoede.install import CAMPAIGN_DIR, DATA_FILES, find_aoede


@dataclass
class SetupReport:
    source: Path
    campaigns: int = 0
    scenarios: int = 0
    data_files: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def setup(source: str | Path | None = None, root: Path = layout.AOE1DE) -> SetupReport:
    """Copy each campaign file and its scenarios into aoe1de/, and the game data into aoe1de/data/.

    Every scenario inside a campaign file must match a mission folder (by its source scenario name);
    anything that doesn't is reported, so a game update that changes the campaigns can't go unnoticed.
    """
    install = find_aoede(source)
    report = SetupReport(install)
    for camp in layout.campaigns(root):
        src = install / CAMPAIGN_DIR / camp.source_file
        if not src.is_file():
            report.problems.append(f"{camp.title}: {src} is missing")
            continue
        shutil.copy2(src, camp.source_path)
        container = load_campaign(camp.source_path)
        by_file = {e.filename: e for e in container.entries}
        expected = {m.source_scenario for m in camp.missions}
        for extra in sorted(set(by_file) - expected):
            report.problems.append(f"{camp.title}: {extra} is in the campaign file but has no mission folder")
        for m in camp.missions:
            entry = by_file.get(m.source_scenario)
            if entry is None:
                report.problems.append(f"{camp.title}: {m.source_scenario} is not in {camp.source_file}")
                continue
            m.scenario_path.write_bytes(entry.data)
            report.scenarios += 1
        report.campaigns += 1
    data_dir = root / "data"
    for rel in DATA_FILES:
        src = install / rel
        if src.is_file():
            data_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, data_dir / src.name)
            report.data_files.append(src.name)
        else:
            report.problems.append(f"game data {rel} is missing")
    return report


def describe(report: SetupReport) -> str:
    lines = [f"Copied from {report.source}",
             f"  {report.campaigns} campaign files, {report.scenarios} scenarios, data: {', '.join(report.data_files) or 'none'}"]
    if report.problems:
        lines.append("Problems:")
        lines += [f"  - {p}" for p in report.problems]
    return "\n".join(lines)
