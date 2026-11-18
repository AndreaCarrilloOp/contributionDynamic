from datetime import date
from xml.etree import ElementTree

from contribution_dynamic.calendar import Day, demo_calendar
from contribution_dynamic.scenarios.tanks import (
    FIRST,
    LEFT,
    STEP,
    TOP,
    plan_shots,
    render_tanks,
)

NS = {"s": "http://www.w3.org/2000/svg"}


def test_patrol_covers_each_active_cell_once():
    days = demo_calendar()
    shots = plan_shots(days)
    assert len(shots) == len({s.day for s in shots})
    assert {s.day for s in shots} == {d for d in days if d.count}
    assert len([s for s in shots if s.start == FIRST]) == 4
    for shot in shots:
        assert shot.start < shot.aim < shot.launch < shot.hit < shot.restore


def test_projectiles_clear_nearer_targets_before_farther_ones():
    days = tuple(Day(date(2026, 1, 4 + row), 3, row, 0) for row in range(7))
    shots = plan_shots(days)
    assert [s.day.weekday for s in shots] == list(range(7))
    for earlier, later in zip(shots, shots[1:]):
        assert earlier.hit < later.launch < earlier.restore
    assert len({s.restore for s in shots}) == 1


def test_sparse_calendar_starts_immediately():
    day = Day(date(2026, 11, 17), 9, 2, 52, 4)
    shot, = plan_shots((day,))
    assert shot.start == FIRST
    assert shot.origin_week == day.week
    assert shot.hit < 1.5


def test_svg_preserves_coordinates_and_repeats_exactly():
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
        assert len(root.findall(".//s:g[@data-tank]", NS)) == 4
        assert len(root.findall(".//s:g[@data-shot]", NS)) == sum(d.count > 0 for d in days)


def test_original_level_and_color_are_restored():
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


def test_no_artificial_activity_on_empty_board():
    for days in ((), (Day(date(2026, 11, 17), 0, 2, 52, 0),)):
        root = ElementTree.fromstring(render_tanks(days))
        assert not root.findall(".//s:g[@data-tank]", NS)
        assert not root.findall(".//s:animate", NS)
        assert not root.findall(".//s:g[@data-shot]", NS)
