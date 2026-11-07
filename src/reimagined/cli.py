"""Command line entry point: `uv run reimagined <command>`."""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reimagined", description=__doc__)
    sub = parser.add_subparsers(dest="command")
    p_setup = sub.add_parser("setup", help="copy the AoE DE campaigns and game data from your install into aoe1de/")
    p_setup.add_argument("--from", dest="source", help="AoE DE folder (default: AOEDE_DIR, then Steam)")
    sub.add_parser("extract", help="fill aoe1de/'s campaign and mission files with players, objectives and text")
    p_conv = sub.add_parser("convert", help="convert campaigns to Return of Rome into aoe2de_ror/ (needs setup)")
    p_conv.add_argument("campaigns", nargs="*", help="campaign folder names (default: all)")
    p_conv.add_argument("--install", action="store_true",
                        help="also install each campaign into your profile as the local mod '[RoR-RI] <campaign>', "
                             "where the game's mod manager can publish and update it")
    p_conv.add_argument("--images-to", metavar="FOLDER",
                        help="also write each campaign's mod page image ('[RoR-RI] <campaign>.jpg', the campaign "
                             "screen at 1920 x 1080) and its title and description (.txt) into FOLDER")
    p_conv.add_argument("--ai-debug", action="store_true",
                        help="computer players announce their build steps and attacks in chat (built into out/debug, "
                             "not aoe2de_ror/; use with --install for playtests)")
    p_probe = sub.add_parser("probe", help="build an AI probe of one mission: records what the computer players do "
                                           "and stops itself (see aoe-agent-editor's ai-behaviour guide)")
    p_probe.add_argument("campaign", help="campaign folder name, e.g. glory_of_greece")
    p_probe.add_argument("mission", help="mission number or folder, e.g. 4 or 04_the_trojan_war")
    p_probe.add_argument("--minutes", type=int, default=15, help="game minutes to record (default 15)")
    p_probe.add_argument("--ai-debug", action="store_true", help="AIs also announce build steps in chat")
    p_probe.add_argument("--install", action="store_true", help="copy the probe into your RoR scenario folder")
    p_pack = sub.add_parser("package", help="package converted campaigns as mods for the official mod site, one per "
                                            "campaign, titled '[RoR-RI] <campaign>' (a zip to upload, plus the mod "
                                            "folder to test in mods/local)")
    p_pack.add_argument("campaigns", nargs="*", help="campaign folder names (default: all)")
    p_pack.add_argument("--to", help="output folder (default: out/mods)")
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
    if args.command == "extract":
        from . import layout
        from .missions import extract
        try:
            changed = extract()
        except FileNotFoundError as e:
            print(f"error: {e} (run `reimagined setup` first)", file=sys.stderr)
            return 1
        print(f"{len(changed)} files updated")
        for p in changed:
            print(f"  {p.relative_to(layout.ROOT)}")
        return 0
    if args.command == "convert":
        return _convert(args.campaigns, args.install, args.ai_debug, args.images_to)
    if args.command == "probe":
        return _probe(args.campaign, args.mission, args.minutes, args.ai_debug, args.install)
    if args.command == "package":
        return _package(args.campaigns, args.to)
    parser.print_help()
    return 0


def _convert(names: list[str], install: bool = False, ai_debug: bool = False, images_to: str | None = None) -> int:
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
        out_root = layout.ROOT / "out" / "debug" if ai_debug else layout.AOE2DE_ROR
        paths, results = convert_campaign(c, conv, out_root, ai_debug=ai_debug)
        print(f"{c.title}: {', '.join(p.name for p in paths)}")
        if install:
            from aoe2ed import screens as ed_screens

            from . import package

            data = {p.name[len(c.slug):]: ed_screens.read_json(p) for p in paths[1:]}
            res = package.install_local(c, paths[0], data)
            print(f"  installed as the local mod {res['title']!r}" + (f" ({res['next']})" if res["next"] else ""))
        if images_to:
            from pathlib import Path

            from aoe2ed import screens as ed_screens

            from . import package

            lay = ed_screens.read_json(paths[0].with_name(f"{c.slug}_layout.json"))
            image, page = package.page_files(c, Path(images_to), lay)
            print(f"  mod page: {image or '(no image: run `reimagined setup` for the map art)'}, {page.name}")
        for r in results:
            dropped = sum(r.dropped.values())
            print(f"  {r.mission}: {r.players} players, {r.placed} objects placed, {dropped} dropped")
    return 0


def _package(names: list[str], to: str | None) -> int:
    from pathlib import Path

    from . import layout, package
    camps = layout.campaigns()
    unknown = set(names) - {c.slug for c in camps}
    if unknown:
        print(f"error: no campaign {', '.join(sorted(unknown))}; choose from {', '.join(c.slug for c in camps)}",
              file=sys.stderr)
        return 1
    out = Path(to) if to else layout.ROOT / "out" / "mods"
    for c in camps:
        if names and c.slug not in names:
            continue
        try:
            res = package.package(c, out)
        except FileNotFoundError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        print(f"{res['title']}: {res['zip']} ({res['zip_mb']} MB zipped, {res['mb']} MB unpacked)"
              + ("" if res["thumbnail"] else "; no thumbnail (no campaign map art: run `reimagined setup`)"))
    return 0


def _probe(campaign: str, mission: str, minutes: int, ai_debug: bool, install: bool) -> int:
    from . import layout
    from .conversion import load
    from .convert import probe_mission

    camp = next((c for c in layout.campaigns() if c.slug == campaign), None)
    if camp is None:
        print(f"error: no campaign {campaign}", file=sys.stderr)
        return 1
    m = next((m for m in camp.missions if m.folder.name == mission or m.folder.name.split("_")[0].lstrip("0") ==
              mission.lstrip("0")), None)
    if m is None:
        print(f"error: {campaign} has no mission {mission}", file=sys.stderr)
        return 1
    res = probe_mission(m, load(), layout.ROOT / "out" / "probes", minutes=minutes, ai_debug=ai_debug)
    print(res["scenario"])
    print(f"  manifest {res['manifest']}")
    print(f"  records {', '.join(res['tracked'])} for players {res['players']}; stops after {minutes} game minutes (~{res['real_minutes_at_8x']} real minutes at 8x)")
    if install:
        from aoe2ed import game
        print(f"  installed: {game.install(res['scenario'], game='ror')['installed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
