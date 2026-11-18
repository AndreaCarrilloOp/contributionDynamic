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
