from xml.etree import ElementTree

from contribution_dynamic.calendar import demo_calendar
from contribution_dynamic.collector import parse_calendar
from contribution_dynamic.motion import serpentine_path
from contribution_dynamic.svg import render


def test_demo_is_deterministic():
    assert demo_calendar(42) == demo_calendar(42)
    assert len(demo_calendar()) == 371


def test_route_visits_active_cells_once():
    days = demo_calendar()
    route = serpentine_path(days)
    assert set(route) == {day for day in days if day.count > 0}
    assert len(route) == len(set(route))


def test_svg_is_valid_xml():
    for theme in ("dark", "light"):
        root = ElementTree.fromstring(render(demo_calendar(), theme))
        assert root.tag.endswith("svg")


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
