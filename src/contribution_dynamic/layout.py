"""Shared exact calendar geometry and visual-only grid completion."""

from contribution_dynamic.calendar import Day, board_weeks
from contribution_dynamic.labels import LEFT, STEP, TOP

ROWS = 7
BOTTOM_PADDING = 8
SIGNATURE_HEIGHT = 10


def calendar_width(left: int, step: int, cell: int, right: int, weeks: int) -> int:
    """Measure to the last cell's right edge, then add the right margin."""
    return left + (max(1, weeks) - 1) * step + cell + right


def render_padding(
    days: tuple[Day, ...],
    cell: int,
    colors: str | tuple[str, str],
    radius: int = 1,
) -> list[str]:
    """Fill omitted grid slots without introducing dates or contributions."""
    occupied = {(day.week, day.weekday) for day in days}
    parts = ['<g id="calendar-padding" aria-hidden="true">']
    for week in range(board_weeks(days)):
        for row in range(ROWS):
            if (week, row) in occupied:
                continue
            color = colors if isinstance(colors, str) else colors[(week+row) % 2]
            x, y = LEFT + week*STEP, TOP + row*STEP
            parts.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
                         f'rx="{radius}" fill="{color}" data-placeholder="true"/>')
    parts.append('</g>')
    return parts


def calendar_height(cell: int, rows: int = ROWS, bottom: int = BOTTOM_PADDING) -> int:
    """Measure to the final visible cell edge, leaving room for animated sprites."""
    return TOP + (rows - 1) * STEP + cell + bottom


def render_signature(width: int, height: int, color: str, enabled: bool) -> list[str]:
    """Optional quiet attribution in reserved space below the animation."""
    if not enabled:
        return []
    return [
        f'<text id="repo-signature" x="{width-6}" y="{height-4}" '
        f'fill="{color}" font-size="7" opacity=".5" text-anchor="end" '
        'font-family="system-ui,sans-serif">contributionDynamic</text>',
    ]
