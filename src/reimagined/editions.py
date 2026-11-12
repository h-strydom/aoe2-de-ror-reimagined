"""The two editions every campaign can come in, each its own mod:

- **RoR-RI**, the faithful rebuild: every campaign, converted tile for tile, winning as the original does.
- **RoR-RIX (Xtreme)**, the reimagined campaigns: difficulty with bonus objectives, banked upgrades, a campaign
  tech tree, computer players with their own AI (progression.py, aoe2de_ror/reimagined/<campaign>.yaml). Only the
  campaigns that have reimagined content (the user split Ascent of Egypt out into it, 2026-11-12).

Both can be installed at once: each edition has its own folder, mod and name in the Custom Campaign list, which is
also the installed campaign's internal name (the game finds its screen and intros by it, `<name>_layout.json` and
`<name>.json`; aoe-agent-editor's install_campaign_mod).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import layout


@dataclass(frozen=True)
class Edition:
    key: str
    prefix: str             # the mod's title: "<prefix> <campaign>"
    out: Path               # where its converted campaigns are committed
    title: str              # the campaign's title on its screen, "{title}" the campaign's
    list_name: str          # its name in the Custom Campaign list (the installed campaign file's name)
    reimagined: bool        # the reimagined layer (progression.py) on top of the faithful map

    def mod_title(self, c: layout.CampaignInfo) -> str:
        return f"{self.prefix} {c.title}"

    def campaign_title(self, c: layout.CampaignInfo) -> str:
        return self.title.format(title=c.title)

    def campaign_name(self, c: layout.CampaignInfo) -> str:
        return self.list_name.format(title=c.title)


RI = Edition("ri", "[RoR-RI]", layout.AOE2DE_ROR, "AoE1 {title}", "{title}", False)
RIX = Edition("rix", "[RoR-RIX]", layout.AOE2DE_ROR_X, "AoE1 {title} Xtreme", "{title} Xtreme", True)
EDITIONS = (RI, RIX)


def has_reimagined(c: layout.CampaignInfo) -> bool:
    return (layout.REIMAGINED / f"{c.slug}.yaml").is_file()


def of(c: layout.CampaignInfo) -> list[Edition]:
    """The editions a campaign comes in: RoR-RI always, RoR-RIX when it has reimagined content."""
    return [RI, RIX] if has_reimagined(c) else [RI]


def by_key(key: str) -> Edition:
    return next(e for e in EDITIONS if e.key == key)
