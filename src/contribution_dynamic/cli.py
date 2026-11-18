"""Command-line interface for the engine foundation."""
import argparse

from contribution_dynamic import __version__


def main() -> int:
    parser = argparse.ArgumentParser(description="Contribution animation engine")
    parser.add_argument("--version", action="version", version=__version__)
    parser.parse_args()
    parser.print_help()
    return 0
