from datetime import date
from xml.etree import ElementTree

from contribution_dynamic.calendar import Day, demo_calendar
from contribution_dynamic.scenarios.origami import (
    FIRST_FOLD,
    FLIGHT,
    LEFT,
    PAPER,
    STEP,
    TOP,
    fold_schedule,
    render_origami,
)

NS = {"s": "http://www.w3.org/2000/svg"}


def test_origami_preserves_calendar():
    days = demo_calendar()
    for theme in ("dark", "light"):
        svg = render_origami(days, theme)
        assert svg == render_origami(days, theme)
        root = ElementTree.fromstring(svg)
        cells = root.findall(".//s:g[@id='calendar']/s:rect", NS)
        assert len(cells) == len(days)
        for cell, day in zip(cells, days, strict=True):
            assert cell.attrib["data-date"] == day.date.isoformat()
            assert int(cell.attrib["x"]) == LEFT + day.week * STEP
            assert int(cell.attrib["y"]) == TOP + day.weekday * STEP


def test_one_bird_per_active_day():
    days = demo_calendar()
    root = ElementTree.fromstring(render_origami(days))
    birds = root.findall(".//s:g[@data-bird]", NS)
    assert [bird.attrib["data-bird"] for bird in birds] == [
        day.date.isoformat() for day in days if day.count
    ]
    assert all(len(bird.findall(".//s:polygon", NS)) == len(PAPER) for bird in birds)


def test_animation_timelines_are_complete():
    root = ElementTree.fromstring(render_origami(demo_calendar()))
    for tag in ("animate", "animateTransform"):
        for animation in root.findall(f".//s:{tag}[@keyTimes]", NS):
            keys = list(map(float, animation.attrib["keyTimes"].split(";")))
            assert keys[0] == 0 and keys[-1] == 1
            assert all(a < b for a, b in zip(keys, keys[1:]))
            assert len(keys) == len(animation.attrib["values"].split(";"))


def test_origami_empty_calendar_and_inactive_cells():
    day = Day(date(2025, 1, 5), 0, 0, 0)
    for days in ((), (day,)):
        root = ElementTree.fromstring(render_origami(days))
        assert not root.findall(".//s:g[@data-bird]", NS)
        assert not root.findall(".//s:animate", NS)


def test_origami_uses_api_intensity():
    day = Day(date(2025, 1, 5), 99, 0, 0, 1)
    for theme, color in (("dark", "#0e4429"), ("light", "#9be9a8")):
        root = ElementTree.fromstring(render_origami((day,), theme))
        cell = root.find(".//s:g[@id='calendar']/s:rect", NS)
        assert cell is not None
        assert cell.attrib["fill"] == color


def test_sparse_calendar_starts_immediately_and_preserves_order():
    days = (
        Day(date(2026, 11, 17), 7, 2, 51),
        Day(date(2026, 6, 18), 3, 4, 30),
        Day(date(2025, 11, 23), 0, 0, 0),
    )
    schedule = fold_schedule(days)
    assert list(schedule) == [days[1], days[0]]
    assert schedule[days[1]] == FIRST_FOLD
    assert schedule[days[0]] - schedule[days[1]] < 1


def test_source_cell_restores_after_flight():
    day = Day(date(2026, 11, 17), 7, 2, 51)
    root = ElementTree.fromstring(render_origami((day,)))
    cell = root.find(".//s:g[@id='calendar']/s:rect", NS)
    assert cell is not None
    animation = cell.find("s:animate", NS)
    assert animation is not None
    values = animation.attrib["values"].split(";")
    assert values[0] == values[2] == cell.attrib["fill"]
    assert values[1] != values[0]
    duration = float(animation.attrib["dur"].removesuffix("s"))
    keys = list(map(float, animation.attrib["keyTimes"].split(";")))
    assert abs(keys[1] * duration - FIRST_FOLD) < 1e-6
    assert abs(keys[2] * duration - (FIRST_FOLD + FLIGHT)) < 1e-6
    assert keys[2] < 1


def test_right_edge_bird_faces_inward():
    day = Day(date(2026, 11, 17), 7, 2, 52)
    root = ElementTree.fromstring(render_origami((day,)))
    assert root.find(".//s:g[@data-bird]/s:g[@transform='scale(-1 1)']", NS) is not None
