"""Immutable contribution calendar and deterministic demo data."""

from dataclasses import dataclass
from datetime import date, timedelta
from random import Random


@dataclass(frozen=True)
class Day:
    date: date
    count: int
    weekday: int
    week: int
    level: int | None = None

    def __post_init__(self):
        if self.count < 0 or not 0 <= self.weekday <= 6 or self.week < 0:
            raise ValueError("Invalid contribution day")
        if self.level is not None and not 0 <= self.level <= 4:
            raise ValueError("Invalid contribution level")


def demo_calendar(seed: int = 42, weeks: int = 53) -> tuple[Day, ...]:
    if not 1 <= weeks <= 53:
        raise ValueError("weeks must be between 1 and 53")
    rng = Random(seed)
    start = date(2025, 1, 5)
    return tuple(
        Day(start + timedelta(days=w * 7 + d), rng.choice([0, 0, 1, 2, 4, 8]), d, w)
        for w in range(weeks)
        for d in range(7)
    )


MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def month_label_positions(
    days: tuple[Day, ...], left: int, step: int, width: int,
) -> tuple[tuple[int, str], ...]:
    """Label every represented month, including short boundary months.

    Positions normally follow the first represented week. Shift labels
    left if necessary to keep 10px month text separated and inside the SVG.
    """
    months = {}
    for day in sorted(days, key=lambda d: d.date):
        months.setdefault((day.date.year, day.date.month), day.week)
    positions = [(left + week * step, MONTHS[month-1])
                 for (_, month), week in months.items()]
    right = width - 24
    for i in range(len(positions)-1, -1, -1):
        x, label = positions[i]
        x = min(x, right)
        positions[i] = (x, label)
        right = x - 24
    return tuple(positions)
