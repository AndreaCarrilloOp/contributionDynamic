from dataclasses import replace
from datetime import date
from xml.etree import ElementTree

from contribution_dynamic.calendar import Day, demo_calendar
from contribution_dynamic.scenarios.invaders import (
    FIRST,
    LEFT,
    STEP,
    TOP,
    plan_battle,
    render_invaders,
)

NS = {"s": "http://www.w3.org/2000/svg"}


def test_one_ship_clears_every_active_day_from_bottom_up():
    demo = demo_calendar()
    for days in (demo, tuple(replace(d, count=1) for d in demo)):
        battle = plan_battle(days)
        assert battle is not None
        assert battle == plan_battle(days)
        shots = [s for v in battle.volleys for s in v.shots]
        assert len(shots) == len({s.day for s in shots})
        assert {s.day for s in shots} == {d for d in days if d.count}
        for volley in battle.volleys:
            rows = [s.day.weekday for s in volley.shots]
            assert rows == sorted(rows, reverse=True)
            assert abs(abs(volley.base - volley.dodge) - 11) < 1e-6
            assert volley.enemy_launch < volley.dodge_end < volley.enemy_hit
            assert volley.enemy_hit < volley.settle < volley.shots[0].launch
            assert all(a.hit < b.hit for a, b in zip(volley.shots, volley.shots[1:]))
            assert volley.shots[-1].hit < volley.end < battle.restore


def test_sparse_calendar_does_not_wait_for_empty_columns():
    day = Day(date(2026, 11, 17), 9, 2, 52, 4)
    battle = plan_battle((day,))
    assert battle is not None
    volley, = battle.volleys
    assert volley.start == FIRST
    assert volley.shots[0].day == day
    assert volley.shots[0].hit < 1.5


def test_svg_is_deterministic_and_preserves_levels_and_coordinates():
    days = demo_calendar()
    for theme in ("dark", "light"):
        svg = render_invaders(days, theme)
        assert svg == render_invaders(days, theme)
        root = ElementTree.fromstring(svg)
        cells = root.findall(".//s:g[@id='calendar']/s:rect", NS)
        assert len(cells) == len(days)
        for cell, day in zip(cells, days, strict=True):
            assert cell.attrib["data-date"] == day.date.isoformat()
            assert int(cell.attrib["x"]) == LEFT + day.week*STEP
            assert int(cell.attrib["y"]) == TOP + day.weekday*STEP
        assert len(root.findall(".//s:g[@data-ship='hero']", NS)) == 1
        invaders = root.findall(".//s:g[@data-invader]", NS)
        assert {i.attrib["data-invader"] for i in invaders} == {
            d.date.isoformat() for d in days if d.count
        }
        assert len(root.findall(".//s:g[@data-laser='hero']", NS)) == len(invaders)
        assert root.findall(".//s:g[@data-laser='enemy']", NS)
        for invader in invaders:
            anim = invader.find("s:animate[@attributeName='opacity']", NS)
            assert anim is not None
            assert anim.attrib["calcMode"] == "discrete"
            assert anim.attrib["values"].split(";")[:3] == ["1", "0", "1"]


def test_level_selects_original_pixel_sprite():
    days = tuple(Day(date(2026, 11, 15+i), 99, i, 52, i) for i in range(1, 5))
    for theme in ("dark", "light"):
        root = ElementTree.fromstring(render_invaders(days, theme))
        invaders = root.findall(".//s:g[@data-invader]", NS)
        assert {i.attrib["data-level"] for i in invaders} == {"1", "2", "3", "4"}
        sprites = [i.find("s:path", NS) for i in invaders]
        assert all(s is not None for s in sprites)
        assert len({s.attrib["d"] for s in sprites}) == 4
        assert len({s.attrib["fill"] for s in sprites}) == 4


def test_no_fabricated_activity():
    for days in ((), (Day(date(2026, 11, 17), 0, 2, 52, 0),)):
        assert plan_battle(days) is None
        root = ElementTree.fromstring(render_invaders(days))
        assert not root.findall(".//s:g[@data-invader]", NS)
        assert not root.findall(".//s:g[@data-ship]", NS)
        assert not root.findall(".//s:animate", NS)
