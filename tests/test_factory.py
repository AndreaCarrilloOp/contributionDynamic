from xml.etree import ElementTree

from contribution_dynamic.calendar import demo_calendar
from contribution_dynamic.scenarios.factory import render_factory, schedule

NS = {"s": "http://www.w3.org/2000/svg"}


def test_factory_schedule_preserves_active_days():
    days = demo_calendar()
    jobs = schedule(days)
    assert [job.day for job in jobs] == [d for d in days if d.count]
    assert sum(job.day.count for job in jobs) == sum(d.count for d in days)


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
            assert int(cell.attrib["x"]) == 47 + day.week * 13
            assert int(cell.attrib["y"]) == 57 + day.weekday * 13


def test_factory_animation_timelines():
    root = ElementTree.fromstring(render_factory(demo_calendar(42, 2)))
    for anim in root.findall(".//s:animate[@keyTimes]", NS):
        keys = list(map(float, anim.attrib["keyTimes"].split(";")))
        assert keys[0] == 0 and keys[-1] == 1
        assert all(a < b for a, b in zip(keys, keys[1:]))
        assert len(keys) == len(anim.attrib["values"].split(";"))


def test_factory_empty_calendar():
    assert schedule(()) == ()
    root = ElementTree.fromstring(render_factory(()))
    assert not root.findall(".//s:animate", NS)
