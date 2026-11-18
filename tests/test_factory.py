from datetime import date
from xml.etree import ElementTree

from contribution_dynamic.calendar import Day, demo_calendar
from contribution_dynamic.scenarios.factory import (
    CADENCE,
    CELL,
    LEFT,
    STEP,
    TOP,
    render_factory,
    schedule,
)

NS = {"s": "http://www.w3.org/2000/svg"}


def test_factory_schedule_preserves_active_days():
    days = demo_calendar()
    jobs = schedule(days)
    assert [job.day for job in jobs] == [d for d in days if d.count]
    assert sum(job.day.count for job in jobs) == sum(d.count for d in days)


def test_parallel_zones_have_independent_nonoverlapping_schedules():
    jobs = schedule(demo_calendar())
    for lane in range(4):
        starts = [j.start for j in jobs if j.lane == lane]
        assert starts
        assert starts == [i * CADENCE for i in range(len(starts))]
    assert len([j for j in jobs if j.start == 0]) == 4


def test_factory_svg_preserves_calendar_coordinates():
    days = demo_calendar()
    for theme in ("dark", "light"):
        svg = render_factory(days, theme)
        assert svg == render_factory(days, theme)
        root = ElementTree.fromstring(svg)
        cells = root.findall(".//s:g[@id='calendar']/s:rect", NS)
        assert len(cells) == len(days)
        for cell, day in zip(cells, days, strict=True):
            assert cell.attrib["data-date"] == day.date.isoformat()
            assert int(cell.attrib["x"]) == LEFT + day.week * STEP
            assert int(cell.attrib["y"]) == TOP + day.weekday * STEP
            assert int(cell.attrib["width"]) == CELL


def test_api_level_overrides_count_heuristic():
    day = Day(date(2025, 1, 5), 99, 0, 0, 1)
    for theme, color in (("dark", "#0e4429"), ("light", "#9be9a8")):
        root = ElementTree.fromstring(render_factory((day,), theme))
        cell = root.find(".//s:g[@id='calendar']/s:rect", NS)
        assert cell is not None
        assert cell.attrib["fill"] == color


def test_factory_animation_timelines():
    root = ElementTree.fromstring(render_factory(demo_calendar()))
    for tag in ("animate", "animateTransform"):
        for anim in root.findall(f".//s:{tag}[@keyTimes]", NS):
            keys = list(map(float, anim.attrib["keyTimes"].split(";")))
            assert keys[0] == 0 and keys[-1] == 1
            assert all(a < b for a, b in zip(keys, keys[1:]))
            assert len(keys) == len(anim.attrib["values"].split(";"))


def test_factory_empty_calendar():
    assert schedule(()) == ()
    root = ElementTree.fromstring(render_factory(()))
    assert not root.findall(".//s:animate", NS)
    assert not root.findall(".//s:animateTransform", NS)
