"""Generate validated SVG assets from one contribution calendar."""

from pathlib import Path
from xml.etree import ElementTree

from contribution_dynamic.calendar import Day
from contribution_dynamic.cli import RENDERERS

THEMES = ("dark", "light")
PUBLISHED_SCENARIOS = ("factory", "origami", "abyss", "chess")


def build_assets(days: tuple[Day, ...], destination: Path) -> tuple[Path, ...]:
    """Render public scenarios before writing anything to the output directory."""
    if not days:
        raise ValueError("Cannot publish an empty contribution calendar")
    assets = {}
    for scenario in PUBLISHED_SCENARIOS:
        renderer = RENDERERS[scenario]
        for theme in THEMES:
            svg = renderer(days, theme)
            if ElementTree.fromstring(svg).tag != "{http://www.w3.org/2000/svg}svg":
                raise ValueError(f"Invalid SVG generated for {scenario}/{theme}")
            assets[f"{scenario}-{theme}.svg"] = svg
    destination.mkdir(parents=True, exist_ok=True)
    for filename, svg in assets.items():
        (destination / filename).write_text(svg, encoding="utf-8")
    return tuple(destination / name for name in assets)
