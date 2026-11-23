from dataclasses import replace
from xml.etree import ElementTree

import pytest

from contribution_dynamic.calendar import demo_calendar
from contribution_dynamic.registry import PUBLISHED_SCENARIOS, RENDERERS, THEMES

NS = {"s": "http://www.w3.org/2000/svg"}


@pytest.mark.parametrize("scenario", PUBLISHED_SCENARIOS)
@pytest.mark.parametrize("theme", THEMES)
def test_dense_calendar_preserves_every_cell(scenario, theme):
    days = tuple(replace(d, count=1 + i % 12) for i, d in enumerate(demo_calendar()))
    svg = RENDERERS[scenario](days, theme)
    root = ElementTree.fromstring(svg)
    cells = root.findall(".//s:g[@id='calendar']/s:rect", NS)
    assert len(cells) == len(days)
    assert {c.attrib["data-date"] for c in cells} == {d.date.isoformat() for d in days}
    for animation in root.findall(".//s:*[@keyTimes]", NS):
        keys = list(map(float, animation.attrib["keyTimes"].split(";")))
        assert keys[0] == 0 and keys[-1] == 1
        assert all(a < b for a, b in zip(keys, keys[1:]))
        assert len(keys) == len(animation.attrib["values"].split(";"))
