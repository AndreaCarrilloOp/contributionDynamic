from xml.etree import ElementTree

import pytest

from contribution_dynamic.calendar import demo_calendar
from contribution_dynamic.publish import build_assets


def test_build_assets_generates_public_scenarios_only(tmp_path):
    days = demo_calendar(42, 2)
    assets = build_assets(days, tmp_path)
    assert {path.name for path in assets} == {
        f"{scenario}-{theme}.svg"
        for scenario in ("tanks", "blast", "chess", "invaders", "origami")
        for theme in ("dark", "light")
    }
    assert set(tmp_path.glob("*.svg")) == set(assets)
    snapshots = {path: path.read_bytes() for path in assets}
    names = {
        "blast": "Bomberman",
        "tanks": "Tanks",
        "chess": "Chess",
        "invaders": "Space Invaders",
        "origami": "Origami Folding",
    }
    for path in assets:
        root = ElementTree.parse(path).getroot()
        assert root.tag.endswith("svg")
        title = root.find("{http://www.w3.org/2000/svg}title")
        assert title is not None
        assert title.text.startswith(names[path.stem.rsplit("-", 1)[0]])
        assert root.attrib["aria-label"].startswith(names[path.stem.rsplit("-", 1)[0]])
        assert "GitBlast" not in path.read_text(encoding="utf-8")
        assert "GitTanks" not in path.read_text(encoding="utf-8")
        assert "GitChess" not in path.read_text(encoding="utf-8")
        assert "GitInvaders" not in path.read_text(encoding="utf-8")
        assert "GitOrigami" not in path.read_text(encoding="utf-8")
    build_assets(days, tmp_path)
    assert all(path.read_bytes() == content for path, content in snapshots.items())


def test_build_assets_rejects_empty_calendar(tmp_path):
    destination = tmp_path / "output"
    with pytest.raises(ValueError, match="empty contribution calendar"):
        build_assets((), destination)
    assert not destination.exists()


def test_build_assets_selects_scenario_and_theme(tmp_path):
    paths = build_assets(demo_calendar(42, 1), tmp_path, ("chess",), ("light",))
    assert [p.name for p in paths] == ["chess-light.svg"]


@pytest.mark.parametrize("scenarios", [(), ("unknown",), ("chess", "unknown")])
def test_rejects_invalid_scenario_selection(tmp_path, scenarios):
    with pytest.raises(ValueError, match="Unknown public scenario"):
        build_assets(demo_calendar(42, 1), tmp_path, scenarios)
