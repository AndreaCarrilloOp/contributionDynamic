"""Shared SVG calendar geometry and readable month/weekday headers."""

from contribution_dynamic.calendar import Day, month_label_positions

LEFT = 47
TOP = 38
STEP = 13
RIGHT = 16
FONT_SIZE = 9
MONTH_SPACING = 24
MONTH_BASELINE = 10
WEEKDAYS = ((1, "Mon"), (3, "Wed"), (5, "Fri"))


def render_labels(days: tuple[Day, ...], width: int, cell: int, color: str) -> list[str]:
    """Keep month labels level and separate adjacent boundary months."""
    parts = [
        f'<g id="calendar-labels" font-family="system-ui,sans-serif" '
        f'font-size="{FONT_SIZE}" fill="{color}">',
        '<g id="month-labels" text-anchor="start">',
    ]
    months = month_label_positions(days, LEFT, STEP, width)
    for i, (x, month) in enumerate(months):
        crowded = i+1 < len(months) and months[i+1][0]-x < MONTH_SPACING
        alignment = ' text-anchor="end" dx="-3"' if crowded else ""
        parts.append(f'<text x="{x}" y="{MONTH_BASELINE}"{alignment}>{month}</text>')
    parts.extend([
        '</g>',
        '<g id="weekday-labels" text-anchor="end" dominant-baseline="central">',
    ])
    # Leave a free gutter for the top/left perimeter in arcade scenarios.
    for row, label in WEEKDAYS:
        y = TOP + row * STEP + cell / 2
        parts.append(f'<text x="{LEFT-18}" y="{y:g}">{label}</text>')
    parts.extend(['</g>', '</g>'])
    return parts
