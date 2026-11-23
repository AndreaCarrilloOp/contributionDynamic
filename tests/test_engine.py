from datetime import date

from contribution_dynamic.calendar import Day, board_weeks, contribution_level, demo_calendar
from contribution_dynamic.collector import parse_calendar


def test_demo_is_deterministic():
    assert demo_calendar(42) == demo_calendar(42)
    assert len(demo_calendar()) == 371


def test_shared_calendar_intensity_and_width():
    day = date(2026, 11, 18)
    assert contribution_level(Day(day, 0, 3, 53, 0)) == 0
    assert contribution_level(Day(day, 99, 3, 53, 1)) == 1
    assert contribution_level(Day(day, 8, 3, 53)) == 4
    assert board_weeks(()) == 53
    assert board_weeks((Day(day, 1, 3, 53),)) == 54


def test_graphql_parser():
    payload = {"data": {"user": {"contributionsCollection": {"contributionCalendar": {
        "weeks": [{"contributionDays": [
            {"date": "2025-01-05", "weekday": 0, "contributionCount": 3,
             "contributionLevel": "SECOND_QUARTILE"}
        ]}]
    }}}}}
    day, = parse_calendar(payload)
    assert day.count == 3
    assert day.week == 0
    assert day.level == 2
