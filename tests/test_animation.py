from xml.etree import ElementTree

import pytest

from contribution_dynamic.animation import track


@pytest.mark.parametrize("mode", ["linear", "discrete"])
def test_compact_timeline_preserves_plateau_boundaries(mode):
    root = ElementTree.fromstring(track(
        "opacity", [0, 0, 0, 1, 1, 1, 0], [0, 1, 2, 3, 4, 5, 6], 6, mode,
    ))
    assert root.attrib["values"] == "0;0;1;1;0"
    keys = list(map(float, root.attrib["keyTimes"].split(";")))
    assert keys == pytest.approx([0, 2/6, 3/6, 5/6, 1])
    assert root.attrib["dur"] == "6s"


def test_rejects_invalid_timeline():
    with pytest.raises(ValueError):
        track("fill", ["red", "blue"], [1, 1], 3)
