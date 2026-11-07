"""`pytest --campaign <slug>|changed|all`: run the per-campaign tests for some campaigns only.

Per-campaign tests are the ones parametrized by a campaign (its slug, CampaignInfo or a Mission). The option
can repeat; `changed` means the campaigns the unpushed changes touch (reimagined.changed: all of them when
shared code or settings changed). Tests that aren't per campaign always run.
"""
from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor

import pytest

from reimagined import layout


def pytest_addoption(parser):
    parser.addoption("--campaign", action="append", default=[], metavar="SLUG",
                     help="run per-campaign tests only for this campaign (repeatable; 'changed' for the campaigns "
                          "the unpushed changes touch, 'all' for every one)")


def _selected(config) -> set[str] | None:
    chosen = config.getoption("campaign")
    if not chosen or "all" in chosen:
        return None
    slugs = {c.slug for c in layout.campaigns()}
    out = set()
    for name in chosen:
        if name == "changed":
            from reimagined.changed import changed_campaigns
            touched = changed_campaigns()
            if touched is None:
                return None
            out.update(touched)
        elif name in slugs:
            out.add(name)
        else:
            raise pytest.UsageError(f"--campaign {name}: choose from {', '.join(sorted(slugs))}, changed or all")
    return out


def _slug(value, slugs: set[str]) -> str | None:
    if isinstance(value, layout.CampaignInfo):
        return value.slug
    if isinstance(value, layout.Mission):
        return value.folder.parent.name
    if isinstance(value, str) and value in slugs:
        return value
    return None


def pytest_collection_modifyitems(config, items):
    selected = _selected(config)
    if selected is None:
        return
    slugs = {c.slug for c in layout.campaigns()}
    keep, drop = [], []
    for item in items:
        params = getattr(getattr(item, "callspec", None), "params", {})
        found = {s for v in params.values() if (s := _slug(v, slugs))}
        (drop if found and not found & selected else keep).append(item)
    if drop:
        config.hook.pytest_deselected(items=drop)
        items[:] = keep


@pytest.fixture(scope="session")
def mission_pool(request):
    """A process pool for converting a campaign's missions side by side, when few campaigns are under test (the
    test workers then have cores to spare); None, to convert one by one, when every campaign is."""
    selected = _selected(request.config)
    cores = os.cpu_count() or 1
    if selected is None or len(selected) * 2 > cores:
        yield None
        return
    with ProcessPoolExecutor(max(1, cores // len(selected))) as pool:
        yield pool
