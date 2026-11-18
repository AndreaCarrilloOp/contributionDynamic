from datetime import date
from xml.etree import ElementTree

from contribution_dynamic.calendar import Day, demo_calendar
from contribution_dynamic.scenarios.origami import LEFT, STEP, TOP, render_origami

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
    assert all(len(bird.findall("s:polygon", NS)) == 4 for bird in birds)


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
