from xml.etree import ElementTree

import pytest

from contribution_dynamic.calendar import demo_calendar
from contribution_dynamic.publish import build_assets


def test_build_assets_generates_all_scenarios(tmp_path):
    days = demo_calendar(42, 2)
    assets = build_assets(days, tmp_path)
    assert {path.name for path in assets} == {
        f"{scenario}-{theme}.svg"
        for scenario in ("motion", "factory", "origami")
        for theme in ("dark", "light")
    }
    snapshots = {path: path.read_bytes() for path in assets}
    for path in assets:
        assert ElementTree.parse(path).getroot().tag.endswith("svg")
    build_assets(days, tmp_path)
    assert all(path.read_bytes() == content for path, content in snapshots.items())


def test_build_assets_rejects_empty_calendar(tmp_path):
    destination = tmp_path / "output"
    with pytest.raises(ValueError, match="empty contribution calendar"):
        build_assets((), destination)
    assert not destination.exists()
