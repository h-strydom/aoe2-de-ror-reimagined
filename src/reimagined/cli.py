"""Command line entry point: `uv run reimagined <command>`."""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reimagined", description=__doc__)
    sub = parser.add_subparsers(dest="command")
    p_setup = sub.add_parser("setup", help="copy the AoE DE campaigns and game data from your install into aoe1de/")
    p_setup.add_argument("--from", dest="source", help="AoE DE folder (default: AOEDE_DIR, then Steam)")
    args = parser.parse_args(argv)

    if args.command == "setup":
        from .sources import describe, setup
        try:
            report = setup(args.source)
        except FileNotFoundError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        print(describe(report))
        return 1 if report.problems else 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
