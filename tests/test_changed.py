"""Which campaigns a change touches (`convert --changed`, `pytest --campaign changed`)."""
from __future__ import annotations

from reimagined.changed import campaigns_of

SLUGS = ["ascent_of_egypt", "glory_of_greece"]


def test_campaign_files_touch_their_campaign_only():
    files = ["aoe1de/glory_of_greece.yaml", "aoe1de/glory_of_greece/01_x/mission.yaml",
             "aoe2de_ror/reimagined/ascent_of_egypt.yaml", "aoe2de_ror/ascent_of_egypt/ascent_of_egypt.json",
             "README.md", ".github/ISSUE_TEMPLATE/bug_report.yml"]
    assert campaigns_of(files, SLUGS) == ["ascent_of_egypt", "glory_of_greece"]


def test_docs_alone_touch_none():
    assert campaigns_of(["README.md", "docs/notes.md"], SLUGS) == []


def test_shared_code_and_settings_touch_all():
    for f in ["src/reimagined/convert.py", "aoe2de_ror/conversion.yaml", "pyproject.toml", "tests/test_convert.py",
              "aoe2de_ror/reimagined/unknown.yaml"]:
        assert campaigns_of([f, "aoe1de/glory_of_greece.yaml"], SLUGS) is None, f
