"""Shared exact calendar geometry and visual-only grid completion."""

from contribution_dynamic.calendar import Day, board_weeks
from contribution_dynamic.labels import LEFT, STEP, TOP

ROWS = 7


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
