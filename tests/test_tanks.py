from datetime import date
from xml.etree import ElementTree

from contribution_dynamic.calendar import Day, demo_calendar
from contribution_dynamic.scenarios.tanks import (
    FIRST,
    LEFT,
    STEP,
    TOP,
    plan_waves,
    render_tanks,
)

NS = {"s": "http://www.w3.org/2000/svg"}


def test_each_active_day_is_one_enemy():
    days = demo_calendar()
    waves = plan_waves(days)
    duels = [d for wave in waves for d in wave.duels]
    assert len(duels) == len({d.day for d in duels})
    assert {d.day for d in duels} == {d for d in days if d.count}
    assert waves[0].start == FIRST
    assert all(1 <= len(w.duels) <= 6 for w in waves)
    assert any(len(w.duels) > 1 for w in waves)


def test_enemy_counterfire_and_hero_dodge_precede_impact():
    waves = plan_waves(demo_calendar())
    for wave in waves:
        assert wave.start < wave.arrive < wave.dodge_start < wave.dodge_end
        assert abs(abs(wave.base - wave.dodge) - 18) < 1e-6
        for duel in wave.duels:
            assert duel.return_launch < wave.dodge_end < duel.return_hit
            assert duel.return_hit < duel.launch < duel.hit < wave.restore
    for previous, current in zip(waves, waves[1:]):
        assert previous.restore < current.start
        assert previous.dodge == current.origin


def test_sparse_calendar_starts_without_empty_column_delay():
    day = Day(date(2026, 11, 17), 9, 2, 52, 4)
    wave, = plan_waves((day,))
    assert wave.start == FIRST
    assert wave.duels[0].day == day
    assert wave.duels[0].launch < 1.5


def test_svg_has_exactly_one_hero_and_preserves_calendar():
    days = demo_calendar()
    for theme in ("dark", "light"):
        svg = render_tanks(days, theme)
        assert svg == render_tanks(days, theme)
        root = ElementTree.fromstring(svg)
        cells = root.findall(".//s:g[@id='calendar']/s:rect", NS)
        assert len(cells) == len(days)
        for cell, day in zip(cells, days, strict=True):
            assert cell.attrib["data-date"] == day.date.isoformat()
            assert int(cell.attrib["x"]) == LEFT + day.week * STEP
            assert int(cell.attrib["y"]) == TOP + day.weekday * STEP
        assert len(root.findall(".//s:g[@data-tank='hero']", NS)) == 1
        enemies = root.findall(".//s:g[@data-tank='enemy']", NS)
        assert {e.attrib["data-enemy"] for e in enemies} == {
            day.date.isoformat() for day in days if day.count
        }
        assert len(root.findall(".//s:g[@data-projectile='hero']", NS)) == len(enemies)
        assert len(root.findall(".//s:g[@data-projectile='enemy']", NS)) == len(enemies)


def test_original_level_and_color_are_restored():
    day = Day(date(2026, 11, 17), 99, 2, 52, 1)
    root = ElementTree.fromstring(render_tanks((day,)))
    cell = root.find(".//s:g[@id='calendar']/s:rect", NS)
    assert cell is not None
    assert cell.attrib["data-level"] == "1"
    animation = cell.find("s:animate", NS)
    assert animation is not None
    values = animation.attrib["values"].split(";")
    assert values[0] == values[-1] == cell.attrib["fill"]
    assert values[1] != values[0]


def test_no_fabricated_battle_on_empty_calendar():
    for days in ((), (Day(date(2026, 11, 17), 0, 2, 52, 0),)):
        root = ElementTree.fromstring(render_tanks(days))
        assert not root.findall(".//s:g[@data-tank]", NS)
        assert not root.findall(".//s:animate", NS)
        assert not root.findall(".//s:g[@data-shot]", NS)
