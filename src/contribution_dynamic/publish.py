"""Generate validated SVG assets from one contribution calendar."""

from pathlib import Path
from xml.etree import ElementTree

from contribution_dynamic.calendar import Day
from contribution_dynamic.registry import PUBLISHED_SCENARIOS, RENDERERS, THEMES


def build_assets(
    days: tuple[Day, ...],
    destination: Path,
    scenarios: tuple[str, ...] = PUBLISHED_SCENARIOS,
    themes: tuple[str, ...] = THEMES,
    *,
    signature: bool = False,
) -> tuple[Path, ...]:
    """Render public scenarios before writing anything to the output directory."""
    if not days:
        raise ValueError("Cannot publish an empty contribution calendar")
    if not scenarios or any(s not in PUBLISHED_SCENARIOS for s in scenarios):
        raise ValueError("Unknown public scenario")
    if not themes or any(t not in THEMES for t in themes):
        raise ValueError("Unknown theme")
    assets = {}
    for scenario in scenarios:
        renderer = RENDERERS[scenario]
        for theme in themes:
            svg = renderer(days, theme, signature=signature)
            if ElementTree.fromstring(svg).tag != "{http://www.w3.org/2000/svg}svg":
                raise ValueError(f"Invalid SVG generated for {scenario}/{theme}")
            assets[f"{scenario}-{theme}.svg"] = svg
    destination.mkdir(parents=True, exist_ok=True)
    for filename, svg in assets.items():
        (destination / filename).write_text(svg, encoding="utf-8")
    return tuple(destination / name for name in assets)
