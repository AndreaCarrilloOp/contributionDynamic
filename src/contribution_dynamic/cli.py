"""Command-line interface for local generation and batch publishing."""

import argparse
import os
from pathlib import Path

from contribution_dynamic import __version__
from contribution_dynamic.calendar import demo_calendar
from contribution_dynamic.collector import collect
from contribution_dynamic.publish import build_assets
from contribution_dynamic.registry import PUBLISHED_SCENARIOS, RENDERERS, THEMES


def _source_args(parser):
    parser.add_argument("--user", help="GitHub login; omit for deterministic demo data")
    parser.add_argument("--seed", type=int, default=42)


def main() -> int:
    parser = argparse.ArgumentParser(description="Contribution animation engine")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command")
    generate = commands.add_parser("generate", help="Generate one SVG")
    _source_args(generate)
    generate.add_argument("--scenario", choices=RENDERERS, default="invaders")
    generate.add_argument("--theme", choices=THEMES, default="dark")
    generate.add_argument("--output", type=Path, default=Path("contributions.svg"))
    batch = commands.add_parser("batch", help="Generate public scenarios in one fetch")
    _source_args(batch)
    batch.add_argument("--scenario", choices=("all", *PUBLISHED_SCENARIOS), default="all")
    batch.add_argument("--theme", choices=("both", *THEMES), default="both")
    batch.add_argument("--output-dir", type=Path, default=Path("generated"))
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0
    days = collect(args.user, os.getenv("GITHUB_TOKEN", "")) if args.user else demo_calendar(
        args.seed
    )
    if args.command == "batch":
        scenarios = PUBLISHED_SCENARIOS if args.scenario == "all" else (args.scenario,)
        themes = THEMES if args.theme == "both" else (args.theme,)
        for path in build_assets(days, args.output_dir, scenarios, themes):
            print(path)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        renderer = RENDERERS[args.scenario]
        args.output.write_text(renderer(days, args.theme), encoding="utf-8")
        print(args.output)
    return 0
