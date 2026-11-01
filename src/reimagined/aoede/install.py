"""Find an AoE DE install, or a folder with the same layout (such as a backup copy).

Order: an explicit path, the AOEDE_DIR environment variable, then AoEDE in every Steam library.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

STEAM_FOLDER = "AoEDE"
CAMPAIGN_DIR = Path("Content") / "Campaigns"
# Game data the later layers read (object names for the id mapping).
DATA_FILES = (Path("Data") / "empires.dat", Path("Data") / "Localization" / "en" / "strings.txt")
# Campaign presentation: which art belongs to which campaign, the briefing map per mission, the campaign
# illustrations and victory backdrops (SLP sprites), and the English narration (MP3 per string id).
# Copied keeping their path relative to the install.
ASSETS = (
    (Path("Data"), "campaigns.json"),
    (Path("Data"), "scenarios.json"),
    (Path("Assets") / "UI" / "images", "campaignillustrations.SLP"),
    (Path("Assets") / "UI" / "images" / "maps", "maps*.SLP"),
    (Path("Assets") / "UI" / "backdrops" / "campaigns", "victory*.SLP"),
    (Path("Assets") / "UI" / "backdrops", "backgroundcampaign.SLP"),
    (Path("Assets") / "UI" / "backdrops", "scenariomapborder.slp"),
    (Path("Content") / "Voice Over" / "en", "*.mp3"),
)


def has_campaigns(root: Path) -> bool:
    return (root / CAMPAIGN_DIR).is_dir() and any((root / CAMPAIGN_DIR).glob("*.aoecpn"))


def _steam_libraries() -> list[Path]:
    roots: list[Path] = []
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
                roots.append(Path(winreg.QueryValueEx(k, "SteamPath")[0]))
        except OSError:
            pass
        roots.append(Path(r"C:\Program Files (x86)\Steam"))
    else:
        roots += [Path.home() / ".steam/steam", Path.home() / ".local/share/Steam"]
    libs: list[Path] = []
    for root in roots:
        vdf = root / "steamapps" / "libraryfolders.vdf"
        if vdf.is_file():
            libs += [Path(m.replace("\\\\", "\\")) for m in
                     re.findall(r'"path"\s+"([^"]+)"', vdf.read_text(encoding="utf-8", errors="ignore"))]
        libs.append(root)
    return list(dict.fromkeys(libs))


def find_aoede(explicit: str | Path | None = None) -> Path:
    """The AoE DE folder to read from; raises FileNotFoundError with every place it looked."""
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    elif os.environ.get("AOEDE_DIR"):
        candidates.append(Path(os.environ["AOEDE_DIR"]))
    else:
        candidates += [lib / "steamapps" / "common" / STEAM_FOLDER for lib in _steam_libraries()]
    for c in candidates:
        if has_campaigns(c):
            return c
    looked = "\n  ".join(str(c) for c in candidates) or "(nowhere)"
    raise FileNotFoundError(f"No AoE DE campaigns ({CAMPAIGN_DIR}/*.aoecpn) found. Looked in:\n  {looked}\n"
                            "Pass --from <folder> or set AOEDE_DIR.")
