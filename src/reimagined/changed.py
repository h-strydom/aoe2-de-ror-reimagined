"""Which campaigns a change touches, so `convert --changed` and `pytest --campaign changed` skip the rest.

The change is everything not yet pushed: uncommitted edits, new files, and commits ahead of the upstream branch
(HEAD when there's none). A campaign is touched by its own files: its aoe1de/ campaign file and mission folders,
its converted files in aoe2de_ror/, and its reimagined content (aoe2de_ror/reimagined/<campaign>.yaml). Docs
don't touch any. Anything else (the converter's code, conversion.yaml, the dependencies, the tests) may change
every campaign, so then all of them count.
"""
from __future__ import annotations

import subprocess
from pathlib import PurePosixPath

from . import layout

IGNORED_SUFFIXES = {".md", ".txt"}
IGNORED_DIRS = {".github", "docs"}


def _git(*args: str) -> list[str]:
    out = subprocess.run(["git", *args], cwd=layout.ROOT, capture_output=True, text=True, encoding="utf-8")
    return out.stdout.splitlines() if out.returncode == 0 else []


def changed_files() -> list[str]:
    base = "@{u}" if _git("rev-parse", "--verify", "--quiet", "@{u}") else "HEAD"
    files = _git("diff", "--name-only", base) + _git("ls-files", "--others", "--exclude-standard")
    return sorted(set(files))


def campaigns_of(files: list[str], slugs: list[str]) -> list[str] | None:
    """The campaigns `files` (repository paths) touch, in `slugs` order; None when they may touch all."""
    touched: set[str] = set()
    for f in files:
        p = PurePosixPath(f)
        if p.suffix in IGNORED_SUFFIXES or p.parts[0] in IGNORED_DIRS:
            continue
        slug = None
        if p.parts[0] in ("aoe1de", "aoe2de_ror") and len(p.parts) >= 2:
            first = p.parts[1]
            if p.parts[0] == "aoe2de_ror" and first == "reimagined" and len(p.parts) == 3:
                first = p.stem
            elif len(p.parts) == 2:
                first = p.stem                       # aoe1de/<campaign>.yaml
            slug = first if first in slugs else None
        if slug is None:
            return None
        touched.add(slug)
    return [s for s in slugs if s in touched]


def changed_campaigns() -> list[str] | None:
    """The campaigns the unpushed changes touch ([] for none), or None when they may touch every campaign."""
    return campaigns_of(changed_files(), [c.slug for c in layout.campaigns()])
