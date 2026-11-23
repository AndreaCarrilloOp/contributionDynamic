from datetime import date, timedelta
from xml.etree import ElementTree

import pytest

from contribution_dynamic.calendar import Day, month_label_positions
from contribution_dynamic.labels import LEFT, MONTH_BASELINE, MONTH_SPACING, RIGHT, STEP, TOP, WEEKDAYS
from contribution_dynamic.layout import calendar_width
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
    months = {}
    for day in days:
        months.setdefault((day.date.year, day.date.month), day.week)
    xs = [int(node.attrib["x"]) for node in labels]
    assert xs == [LEFT + week * STEP for week in months.values()]
    assert xs[0] >= 0 and xs[-1]+24 <= int(root.attrib["width"])
    assert all(int(n.attrib["y"]) == MONTH_BASELINE for n in labels)
    for first, second in zip(labels, labels[1:]):
        if int(second.attrib["x"])-int(first.attrib["x"]) < MONTH_SPACING:
            assert first.attrib["text-anchor"] == "end"
            assert first.attrib["dx"] == "-3"
    cells = root.findall(".//s:g[@id='calendar']/s:rect", NS)
    assert {c.attrib["data-date"] for c in cells} == {d.date.isoformat() for d in days}
    cell = float(cells[0].attrib["height"])
    weeks = max(53, days[-1].week+1)
    assert int(root.attrib["width"]) == calendar_width(LEFT, STEP, int(cell), RIGHT, weeks)
    for node, day in zip(cells, days, strict=True):
        assert float(node.attrib["x"]) == LEFT + day.week * STEP
        assert float(node.attrib["y"]) == TOP + day.weekday * STEP
    weekdays = root.find(".//s:g[@id='weekday-labels']", NS)
    assert weekdays is not None
    assert weekdays.attrib["dominant-baseline"] == "central"
    assert weekdays.attrib["text-anchor"] == "end"
    day_labels = weekdays.findall("s:text", NS)
    assert [n.text for n in day_labels] == [name for _, name in WEEKDAYS]
    for node, (row, _) in zip(day_labels, WEEKDAYS, strict=True):
        assert float(node.attrib["y"]) == TOP + row * STEP + cell / 2
        assert int(node.attrib["x"]) == LEFT-18


def test_december_stays_aligned_when_there_is_room():
    days = _calendar(date(2025, 11, 16), date(2025, 12, 31))
    assert month_label_positions(days, 47, 13, 752) == ((47, "Nov"), (73, "Dec"))


def test_no_month_is_invented_or_added_to_empty_calendar():
    days = _calendar(date(2026, 11, 18), date(2026, 11, 19))
    assert month_label_positions(days, 47, 13, 752) == ((47, "Nov"),)
    assert month_label_positions((), 47, 13, 752) == ()


def test_partial_boundary_months_keep_exact_columns():
    days = _calendar(date(2025, 11, 30), date(2026, 11, 1))
    assert month_label_positions(days, LEFT, STEP, 752)[:2] == (
        (LEFT, "Nov"), (LEFT, "Dec"),
    )
    for scenario in PUBLISHED_SCENARIOS:
        root = ElementTree.fromstring(RENDERERS[scenario](days, "dark"))
        labels = root.findall(".//s:g[@id='month-labels']/s:text", NS)
        assert labels[0].attrib["x"] == labels[1].attrib["x"]
        assert labels[0].attrib["y"] == labels[1].attrib["y"] == str(MONTH_BASELINE)
        assert labels[0].attrib["text-anchor"] == "end"
        assert labels[0].attrib["dx"] == "-3"


@pytest.mark.parametrize("scenario", PUBLISHED_SCENARIOS)
@pytest.mark.parametrize("theme", THEMES)
def test_december_shares_month_baseline_in_published_calendar(scenario, theme):
    days = _calendar(date(2025, 11, 23), date(2026, 11, 22))
    root = ElementTree.fromstring(RENDERERS[scenario](days, theme))
    labels = root.findall(".//s:g[@id='month-labels']/s:text", NS)
    assert [(node.text, node.attrib["x"]) for node in labels[:3]] == [
        ("Nov", "47"), ("Dec", "60"), ("Jan", "112"),
    ]
    assert {node.attrib["y"] for node in labels} == {str(MONTH_BASELINE)}
    assert labels[0].attrib["text-anchor"] == "end"
    assert "text-anchor" not in labels[1].attrib
