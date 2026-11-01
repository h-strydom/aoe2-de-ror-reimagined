"""Command line entry point: `uv run reimagined <command>`."""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reimagined", description=__doc__)
    sub = parser.add_subparsers(dest="command")
    p_setup = sub.add_parser("setup", help="copy the AoE DE campaigns and game data from your install into aoe1de/")
    p_setup.add_argument("--from", dest="source", help="AoE DE folder (default: AOEDE_DIR, then Steam)")
    p_conv = sub.add_parser("convert", help="convert campaigns to Return of Rome into aoe2de_ror/ (needs setup)")
    p_conv.add_argument("campaigns", nargs="*", help="campaign folder names (default: all)")
    p_conv.add_argument("--install", action="store_true", help="also copy the campaign files into your AoE2 DE profile")
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
    if args.command == "convert":
        return _convert(args.campaigns, args.install)
    parser.print_help()
    return 0


def _convert(names: list[str], install: bool = False) -> int:
    from . import layout
    from .conversion import ConversionError, load
    from .convert import convert_campaign

    try:
        conv = load()
    except ConversionError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    camps = layout.campaigns()
    unknown = set(names) - {c.slug for c in camps}
    if unknown:
        print(f"error: no campaign {', '.join(sorted(unknown))}; choose from {', '.join(c.slug for c in camps)}",
              file=sys.stderr)
        return 1
    for c in camps:
        if names and c.slug not in names:
            continue
        missing = [m.folder.name for m in c.missions if not m.scenario_path.is_file()]
        if missing:
            print(f"error: {c.slug}: no source scenario in {', '.join(missing)}; run `reimagined setup`",
                  file=sys.stderr)
            return 1
        paths, results = convert_campaign(c, conv)
        print(f"{c.title}: {', '.join(p.name for p in paths)}")
        if install:
            from aoe2ed.game import install as install_file
            for p in paths:
                print(f"  installed {install_file(p)['installed']}")
        for r in results:
            dropped = sum(r.dropped.values())
            print(f"  {r.mission}: {r.players} players, {r.placed} objects placed, {dropped} dropped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
