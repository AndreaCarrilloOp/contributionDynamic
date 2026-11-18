from datetime import date, timedelta
from xml.etree import ElementTree

import pytest

from contribution_dynamic.calendar import Day, board_weeks
from contribution_dynamic.labels import LEFT, STEP, TOP
from contribution_dynamic.layout import ROWS, calendar_width
from contribution_dynamic.registry import PUBLISHED_SCENARIOS, RENDERERS, THEMES

NS = {"s": "http://www.w3.org/2000/svg"}


def test_width_has_no_trailing_cell_gap():
    assert calendar_width(47, 13, 10, 16, 53) == 749
    assert calendar_width(47, 13, 13, 16, 53) == 752
    assert calendar_width(47, 13, 10, 16, 54) == 762


@pytest.mark.parametrize("scenario", PUBLISHED_SCENARIOS)
@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("first,last", [(0, 367), (3, 367), (6, 371)])
def test_partial_weeks_have_complete_visual_grid(scenario, theme, first, last):
    start = date(2025, 11, 16)
    days = tuple(
        Day(start + timedelta(days=i), 0, i % ROWS, i // ROWS, 0)
        for i in range(first, last+1)
    )
    root = ElementTree.fromstring(RENDERERS[scenario](days, theme))
    real = root.findall(".//s:g[@id='calendar']/s:rect", NS)
    padding = root.findall(".//s:g[@id='calendar-padding']/s:rect", NS)
    assert len(real) == len(days)
    assert {node.attrib["data-date"] for node in real} == {str(d.date) for d in days}
    assert len(padding) == board_weeks(days)*ROWS-len(days)
    assert all(node.attrib["data-placeholder"] == "true" for node in padding)
    assert all("data-date" not in node.attrib and len(node) == 0 for node in padding)
    expected = {(LEFT+w*STEP, TOP+r*STEP)
                for w in range(board_weeks(days)) for r in range(ROWS)}
    coords = [(int(n.attrib["x"]), int(n.attrib["y"])) for n in real+padding]
    assert len(coords) == len(set(coords))
    assert set(coords) == expected
    assert all(int(n.attrib["x"])+int(n.attrib["width"]) <= int(root.attrib["width"])
               for n in real+padding)
    assert not root.findall(".//s:animate", NS)
