import tomllib
from pathlib import Path

import reimagined
from reimagined.cli import main


def test_version_matches_pyproject():
    pyproject = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    assert reimagined.__version__ == pyproject["project"]["version"]


def test_cli_runs():
    assert main([]) == 0
