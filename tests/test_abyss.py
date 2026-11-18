from datetime import date
from xml.etree import ElementTree

from contribution_dynamic.calendar import Day, demo_calendar
from contribution_dynamic.scenarios.abyss import (
    LEFT,
    MAX_JELLIES,
    STEP,
    TOP,
    plan_journeys,
    render_abyss,
)

NS = {"s": "http://www.w3.org/2000/svg"}


def test_every_active_cell_is_visited_once():
    days = demo_calendar()
    routes = plan_journeys(days)
    visits = [visit.day for route in routes for visit in route.visits]
    assert len(routes) == MAX_JELLIES
    assert len(visits) == len(set(visits))
    assert set(visits) == {day for day in days if day.count}
    for route in routes:
        assert route.positions[0] == route.positions[-1]
        assert len(route.positions) == len(route.times)
        assert all(a < b for a, b in zip(route.times, route.times[1:]))


def test_sparse_calendar_feeds_immediately():
    days = (Day(date(2026, 11, 17), 9, 2, 52, 4),)
    routes = plan_journeys(days)
    assert len(routes) == 1
    assert routes[0].visits[0].arrival < .5


def test_calendar_coordinates_and_api_intensity():
    day = Day(date(2026, 11, 17), 99, 2, 52, 1)
    for theme, color in (("dark", "#0e4429"), ("light", "#9be9a8")):
        root = ElementTree.fromstring(render_abyss((day,), theme))
        cell = root.find(".//s:g[@id='calendar']/s:rect", NS)
        assert cell is not None
        assert cell.attrib["fill"] == color
        assert int(cell.attrib["x"]) == LEFT + day.week * STEP
        assert int(cell.attrib["y"]) == TOP + day.weekday * STEP


def test_svg_and_energy_pulses_are_deterministic():
    days = demo_calendar()
    for theme in ("dark", "light"):
        svg = render_abyss(days, theme)
        assert svg == render_abyss(days, theme)
        root = ElementTree.fromstring(svg)
        assert len(root.findall(".//s:g[@data-jelly]", NS)) == MAX_JELLIES
        pulses = root.findall(".//s:circle[@data-energy]", NS)
        assert {p.attrib["data-energy"] for p in pulses} == {
            day.date.isoformat() for day in days if day.count
        }
        for tag in ("animate", "animateTransform"):
            for anim in root.findall(f".//s:{tag}[@keyTimes]", NS):
                keys = list(map(float, anim.attrib["keyTimes"].split(";")))
                assert keys[0] == 0 and keys[-1] == 1
                assert all(a < b for a, b in zip(keys, keys[1:]))
                assert len(keys) == len(anim.attrib["values"].split(";"))


def test_empty_calendar_has_no_fake_activity():
    day = Day(date(2026, 11, 17), 0, 2, 52, 0)
    for days in ((), (day,)):
        root = ElementTree.fromstring(render_abyss(days))
        assert not root.findall(".//s:g[@data-jelly]", NS)
        assert not root.findall(".//s:circle[@data-energy]", NS)
        assert not root.findall(".//s:animate", NS)
