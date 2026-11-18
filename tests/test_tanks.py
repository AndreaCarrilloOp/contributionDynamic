from dataclasses import replace
from datetime import date
from xml.etree import ElementTree

from contribution_dynamic.calendar import Day, demo_calendar
from contribution_dynamic.scenarios.tanks import (
    FIRST,
    LEFT,
    STEP,
    TOP,
    board_weeks,
    plan_tank_route,
    render_tanks,
)

NS = {"s": "http://www.w3.org/2000/svg"}


def test_each_block_is_cleared_before_tank_enters():
    days = demo_calendar()
    steps = plan_tank_route(days)
    blocks = {(d.week, d.weekday): d for d in days if d.count}
    assert steps[0].origin not in blocks
    assert steps[0].start == FIRST
    for step in steps:
        expected = blocks.pop(step.destination, None)
        assert step.day == expected
        if expected is not None:
            assert step.start <= step.fire < step.hit < step.move_start < step.end
        else:
            assert step.fire is None and step.hit is None
    assert not blocks
    assert steps[-1].destination == steps[0].origin


def test_route_is_adjacent_continuous_and_inside_grid():
    days = demo_calendar()
    steps = plan_tank_route(days)
    for s in steps:
        dx = abs(s.origin[0] - s.destination[0])
        dy = abs(s.origin[1] - s.destination[1])
        assert dx + dy == 1
        for x, y in (s.origin, s.destination):
            assert 0 <= x < board_weeks(days) and 0 <= y < 7
    for a, b in zip(steps, steps[1:]):
        assert a.destination == b.origin
        assert a.end == b.start


def test_sparse_calendar_starts_next_to_activity():
    day = Day(date(2026, 11, 17), 9, 2, 52, 4)
    steps = plan_tank_route((day,))
    assert steps[0].day == day
    assert steps[0].fire < .5
    assert steps[0].hit < .6


def test_full_board_uses_edge_entry_only_when_necessary():
    days = tuple(replace(d, count=1) for d in demo_calendar())
    steps = plan_tank_route(days)
    assert steps[0].origin == steps[-1].destination == (-1, 0)
    assert steps[0].destination == (0, 0)
    assert {s.day for s in steps if s.day is not None} == set(days)
    assert all(s.destination[0] >= 0 for s in steps[:-1])


def test_svg_has_one_tank_and_preserves_coordinates():
    days = demo_calendar()
    for theme in ("dark", "light"):
        svg = render_tanks(days, theme)
        assert svg == render_tanks(days, theme)
        root = ElementTree.fromstring(svg)
        cells = root.findall(".//s:g[@id='calendar']/s:rect", NS)
        assert len(cells) == len(days)
        for cell, day in zip(cells, days, strict=True):
            assert cell.attrib["data-date"] == day.date.isoformat()
            assert int(cell.attrib["x"]) == LEFT + day.week * STEP
            assert int(cell.attrib["y"]) == TOP + day.weekday * STEP
        assert len(root.findall(".//s:g[@data-tank='hero']", NS)) == 1
        shots = root.findall(".//s:g[@data-shot]", NS)
        assert {s.attrib["data-shot"] for s in shots} == {
            d.date.isoformat() for d in days if d.count
        }
        assert len(shots) == sum(d.count > 0 for d in days)
        assert not root.findall(".//s:g[@data-tank='enemy']", NS)


def test_original_level_and_color_are_restored_at_cycle_boundary():
    day = Day(date(2026, 11, 17), 99, 2, 52, 1)
    root = ElementTree.fromstring(render_tanks((day,)))
    cell = root.find(".//s:g[@id='calendar']/s:rect", NS)
    assert cell is not None
    assert cell.attrib["data-level"] == "1"
    animation = cell.find("s:animate", NS)
    assert animation is not None
    values = animation.attrib["values"].split(";")
    assert values[0] == values[-1] == cell.attrib["fill"]
    assert values[1] != values[0]
    assert animation.attrib["calcMode"] == "discrete"
    assert animation.attrib["keyTimes"].split(";")[-1] == "1"


def test_no_artificial_activity_on_empty_calendar():
    for days in ((), (Day(date(2026, 11, 17), 0, 2, 52, 0),)):
        root = ElementTree.fromstring(render_tanks(days))
        assert not root.findall(".//s:g[@data-tank]", NS)
        assert not root.findall(".//s:animate", NS)
        assert not root.findall(".//s:g[@data-shot]", NS)
