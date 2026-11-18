from datetime import date, timedelta
from xml.etree import ElementTree

import pytest

from contribution_dynamic.calendar import Day, month_label_positions
from contribution_dynamic.registry import PUBLISHED_SCENARIOS, RENDERERS, THEMES

NS = {"s": "http://www.w3.org/2000/svg"}
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _calendar(start, end):
    first_sunday = start - timedelta(days=(start.weekday()+1) % 7)
    days = []
    for i in range((end-start).days+1):
        current = start + timedelta(days=i)
        offset = (current-first_sunday).days
        days.append(Day(current, 0, offset % 7, offset // 7))
    return tuple(days)


@pytest.mark.parametrize("scenario", PUBLISHED_SCENARIOS)
@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("start,end", [
    (date(2025, 11, 16), date(2026, 11, 18)),
    (date(2025, 11, 30), date(2026, 11, 30)),
    (date(2025, 1, 1), date(2025, 12, 31)),
])
def test_all_calendar_months_are_visible(scenario, theme, start, end):
    days = _calendar(start, end)
    root = ElementTree.fromstring(RENDERERS[scenario](days, theme))
    expected = [MONTHS[month-1] for _, month in
                dict.fromkeys((d.date.year, d.date.month) for d in days)]
    labels = [node for node in root.findall(".//s:text", NS) if node.text in MONTHS]
    assert [node.text for node in labels] == expected
    assert "Dec" in expected
    xs = [int(node.attrib["x"]) for node in labels]
    assert all(b-a >= 24 for a, b in zip(xs, xs[1:]))
    assert xs[0] >= 0 and xs[-1]+24 <= int(root.attrib["width"])
    cells = root.findall(".//s:g[@id='calendar']/s:rect", NS)
    assert {c.attrib["data-date"] for c in cells} == {d.date.isoformat() for d in days}


def test_december_stays_aligned_when_there_is_room():
    days = _calendar(date(2025, 11, 16), date(2025, 12, 31))
    assert month_label_positions(days, 47, 13, 752) == ((47, "Nov"), (73, "Dec"))


def test_no_month_is_invented_or_added_to_empty_calendar():
    days = _calendar(date(2026, 11, 18), date(2026, 11, 19))
    assert month_label_positions(days, 47, 13, 752) == ((47, "Nov"),)
    assert month_label_positions((), 47, 13, 752) == ()
