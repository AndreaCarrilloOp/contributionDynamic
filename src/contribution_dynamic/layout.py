"""Shared exact calendar geometry."""

ROWS = 7


def calendar_width(left: int, step: int, cell: int, right: int, weeks: int) -> int:
    """Measure to the last cell's right edge, then add the right margin."""
    return left + (max(1, weeks) - 1) * step + cell + right
