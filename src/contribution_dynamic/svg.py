"""Self-contained SVG proof of concept with no JavaScript."""

from contribution_dynamic.calendar import Day
from contribution_dynamic.motion import serpentine_path

PALETTES = {
    "dark": ("#0d1117", "#21262d", "#164e45", "#0f766e", "#14b8a6", "#5eead4"),
    "light": ("#ffffff", "#ebedf0", "#ccfbf1", "#99f6e4", "#2dd4bf", "#0f766e"),
}


def render(days: tuple[Day, ...], theme: str = "dark") -> str:
    bg, *colors = PALETTES[theme]
    step, pad = 13, 12
    width = (max((d.week for d in days), default=0) + 1) * step + 2 * pad
    height = 7 * step + 2 * pad
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        'role="img" aria-label="Contribution motion prototype">',
        f'<rect width="{width}" height="{height}" rx="8" fill="{bg}"/>',
    ]
    for day in days:
        x, y = pad + day.week * step, pad + day.weekday * step
        level = 0 if day.count == 0 else min(4, day.count.bit_length())
        parts.append(
            f'<rect x="{x}" y="{y}" width="10" height="10" rx="2" '
            f'fill="{colors[level]}"/>'
        )
    route = serpentine_path(days)
    if route:
        points = [
            f"{pad + d.week * step + 5},{pad + d.weekday * step + 5}" for d in route
        ]
        if len(points) == 1:
            x, y = points[0].split(",")
            parts.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#f59e0b"/>')
        else:
            path = "M" + " L".join(points) + " Z"
            parts.append(
                '<circle r="4" fill="#f59e0b">'
                f'<animateMotion path="{path}" dur="24s" repeatCount="indefinite"/>'
                '</circle>'
            )
    return "\n".join([*parts, "</svg>"]) + "\n"
