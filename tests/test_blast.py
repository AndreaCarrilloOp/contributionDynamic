from datetime import date
from xml.etree import ElementTree

from contribution_dynamic.calendar import Day, demo_calendar
from contribution_dynamic.scenarios.blast import (
    FIRST,
    LEFT,
    STEP,
    TOP,
    blast_cross,
    plan_blasts,
    render_blast,
)

NS = {"s": "http://www.w3.org/2000/svg"}


def test_cross_is_clipped_and_has_no_diagonal():
    assert set(blast_cross((0, 0), 2, 0, 13)) == {
        (0, 0), (1, 0), (2, 0), (0, 1), (0, 2),
    }


def test_all_activity_is_covered_and_shelters_are_safe():
    days = demo_calendar()
    events = plan_blasts(days)
    assert {day for e in events for day in e.hits} == {d for d in days if d.count}
    for event in events:
        assert event.shelter not in event.cross
        assert all((d.week, d.weekday) in event.cross for d in event.hits)
        assert event.center in event.cross
    assert len([e for e in events if e.start == FIRST]) == 4


def test_sparse_calendar_starts_without_empty_column_delay():
    day = Day(date(2026, 11, 17), 7, 2, 52, 3)
    event, = plan_blasts((day,))
    assert event.start == FIRST
    assert event.hits == (day,)


def test_blast_preserves_calendar_and_levels():
    days = demo_calendar()
    for theme in ("dark", "light"):
        svg = render_blast(days, theme)
        assert svg == render_blast(days, theme)
        root = ElementTree.fromstring(svg)
        cells = root.findall(".//s:g[@id='calendar']/s:rect", NS)
        assert len(cells) == len(days)
        for cell, day in zip(cells, days, strict=True):
            assert cell.attrib["data-date"] == day.date.isoformat()
            assert int(cell.attrib["x"]) == LEFT + day.week * STEP
            assert int(cell.attrib["y"]) == TOP + day.weekday * STEP
        assert len(root.findall(".//s:g[@data-bomb='true']", NS)) == len(plan_blasts(days))


def test_no_bombs_when_no_activity():
    for days in ((), (Day(date(2026, 11, 17), 0, 2, 52, 0),)):
        root = ElementTree.fromstring(render_blast(days))
        assert not root.findall(".//s:g[@data-bomb]", NS)
        assert not root.findall(".//s:animate", NS)


def test_brick_restores_original_fill():
    day = Day(date(2026, 11, 17), 99, 2, 52, 1)
    root = ElementTree.fromstring(render_blast((day,)))
    cell = root.find(".//s:g[@id='calendar']/s:rect", NS)
    assert cell is not None
    assert cell.attrib["data-level"] == "1"
    animation = cell.find("s:animate", NS)
    assert animation is not None
    values = animation.attrib["values"].split(";")
    assert values[0] == values[-1] == cell.attrib["fill"]
    assert values[1] != values[0]
