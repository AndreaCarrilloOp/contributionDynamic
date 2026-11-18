"""Command-line interface for the engine."""

import argparse
import os
from pathlib import Path

from contribution_dynamic import __version__
from contribution_dynamic.calendar import demo_calendar
from contribution_dynamic.collector import collect
from contribution_dynamic.svg import render


def main() -> int:
    parser = argparse.ArgumentParser(description="Contribution animation engine")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command")
    generate = commands.add_parser("generate", help="Generate an SVG prototype")
    generate.add_argument("--user", help="GitHub login; omit for deterministic demo data")
    generate.add_argument("--seed", type=int, default=42)
    generate.add_argument("--theme", choices=["dark", "light"], default="dark")
    generate.add_argument("--output", type=Path, default=Path("contributions.svg"))
    args = parser.parse_args()
    if args.command != "generate":
        parser.print_help()
        return 0
    days = collect(args.user, os.getenv("GITHUB_TOKEN", "")) if args.user else demo_calendar(
        args.seed
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(days, args.theme), encoding="utf-8")
    print(args.output)
    return 0
