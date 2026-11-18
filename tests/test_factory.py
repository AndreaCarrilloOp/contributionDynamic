from xml.etree import ElementTree

from contribution_dynamic.calendar import demo_calendar
from contribution_dynamic.scenarios.factory import render_factory, schedule


def test_factory_schedule_preserves_active_days():
    days = demo_calendar()
    jobs = schedule(days)
    assert [j.day for j in jobs] == sorted(
        (d for d in days if d.count), key=lambda d: d.date
    )
    assert sum(j.day.count for j in jobs) == sum(d.count for d in days)


def test_factory_svg_is_deterministic_and_valid():
    days = demo_calendar()
    for theme in ("dark", "light"):
        svg = render_factory(days, theme)
        assert svg == render_factory(days, theme)
        assert ElementTree.fromstring(svg).tag.endswith("svg")


def test_factory_empty_calendar():
    assert schedule(()) == ()
    assert "0 batches / 0 contributions" in render_factory(())
