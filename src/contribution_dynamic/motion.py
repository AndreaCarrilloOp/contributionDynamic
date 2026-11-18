"""Deterministic path generation shared by scenario renderers."""

from contribution_dynamic.calendar import Day


def serpentine_path(days: tuple[Day, ...]) -> tuple[Day, ...]:
    """Visit active cells by week, alternating vertical direction."""
    return tuple(
        sorted(
            (day for day in days if day.count > 0),
            key=lambda day: (day.week, day.weekday if day.week % 2 == 0 else -day.weekday),
        )
    )
