"""Shared SVG calendar geometry and readable month/weekday headers."""

from contribution_dynamic.calendar import Day, month_label_positions

LEFT = 47
TOP = 38
STEP = 13
RIGHT = 16
FONT_SIZE = 9
MONTH_SPACING = 24
MONTH_BASELINES = (10, 20)
WEEKDAYS = ((1, "Mon"), (3, "Wed"), (5, "Fri"))


def render_labels(days: tuple[Day, ...], width: int, cell: int, color: str) -> list[str]:
    """Keep month anchors exact; stagger only closely spaced label baselines."""
    parts = [
        f'<g id="calendar-labels" font-family="system-ui,sans-serif" '
        f'font-size="{FONT_SIZE}" fill="{color}">',
        '<g id="month-labels" text-anchor="start">',
    ]
    last = [float("-inf")] * len(MONTH_BASELINES)
    for x, month in month_label_positions(days, LEFT, STEP, width):
        lane = next((i for i, prev in enumerate(last) if x-prev >= MONTH_SPACING), 1)
        last[lane] = x
        # Normally there is enough right padding (STEP + RIGHT) for the last
        # abbreviation. The alternate baseline handles partial boundary months.
        parts.append(f'<text x="{x}" y="{MONTH_BASELINES[lane]}">{month}</text>')
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
