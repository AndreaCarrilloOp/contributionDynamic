from dataclasses import replace
from datetime import date
from xml.etree import ElementTree

from contribution_dynamic.calendar import Day, demo_calendar
from contribution_dynamic.scenarios.tanks import (
    ASSAULT,
    BASE,
    FIRST,
    LEFT,
    MAX_ENEMIES,
    STEP,
    TOP,
    base_x,
    plan_waves,
    render_tanks,
)

NS = {"s": "http://www.w3.org/2000/svg"}


def test_waves_cover_every_active_day_once():
    days = demo_calendar()
    waves = plan_waves(days)
    breaches = [b for w in waves for e in w.enemies for b in e.breaches]
    assert {b.day for b in breaches} == {d for d in days if d.count}
    assert len(breaches) == sum(d.count > 0 for d in days)
    assert waves[0].start == FIRST
    assert all(1 <= len(w.enemies) <= MAX_ENEMIES for w in waves)
    assert any(len(w.enemies) > 1 for w in waves)


def test_enemies_clear_bricks_before_crossing_and_are_defeated():
    days = tuple(replace(d, count=1) for d in demo_calendar())
    for wave in plan_waves(days):
        for enemy in wave.enemies:
            assert len(enemy.positions) == len(enemy.times)
            assert all(a < b for a, b in zip(enemy.times, enemy.times[1:]))
            for breach in enemy.breaches:
                arrival = enemy.times[enemy.positions.index(breach.target)]
                assert breach.fire < breach.hit < arrival
            assert enemy.station[1] == ASSAULT < BASE
            assert enemy.times[-1] == wave.ready
            assert wave.ready < enemy.attack < enemy.shield_hit < enemy.counter
            assert enemy.counter < enemy.defeated < wave.restore
        slots = [enemy.station[0] for enemy in wave.enemies]
        assert slots == sorted(set(slots))


def test_sparse_activity_starts_immediately():
    day = Day(date(2026, 11, 17), 9, 2, 52, 4)
    wave, = plan_waves((day,))
    enemy, = wave.enemies
    assert wave.start == FIRST
    assert enemy.breaches[0].day == day
    assert enemy.breaches[0].fire < 1


def test_svg_has_one_hero_multiple_enemies_and_eagle():
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
        assert len(enemies) == len({d.week for d in days if d.count})
        assert len(enemies) > 1
        assert len(root.findall(".//s:g[@data-projectile='hero']", NS)) == len(enemies)
        assert root.find(".//s:g[@data-base='eagle']", NS) is not None
        assert root.find(".//s:circle[@data-shield]/s:animate", NS) is not None
        assert {s.attrib["data-shot"] for s in root.findall(".//s:g[@data-shot]", NS)} == {
            d.date.isoformat() for d in days if d.count
        }


def test_eagle_cannot_be_reached_by_enemy_routes():
    days = demo_calendar()
    center = base_x(days)
    for wave in plan_waves(days):
        for enemy in wave.enemies:
            assert all(point[1] <= ASSAULT for point in enemy.positions)
            assert abs(enemy.guard_x - center) <= 28


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


def test_empty_calendar_has_no_fake_combat():
    for days in ((), (Day(date(2026, 11, 17), 0, 2, 52, 0),)):
        root = ElementTree.fromstring(render_tanks(days))
        assert not root.findall(".//s:g[@data-tank]", NS)
        assert not root.findall(".//s:animate", NS)
        assert not root.findall(".//s:g[@data-shot]", NS)
        assert root.find(".//s:g[@data-base='eagle']", NS) is not None


def test_retro_sprite_and_bricks_use_theme_palette():
    day = Day(date(2026, 11, 17), 7, 2, 52, 4)
    for theme, background, gold, brick in (
        ("dark", "#080808", "#d9b21f", "#f3a342"),
        ("light", "#faf6eb", "#be8d10", "#a95b22"),
    ):
        root = ElementTree.fromstring(render_tanks((day,), theme))
        assert root.find("s:rect", NS).attrib["fill"] == background
        sprite = root.find(".//s:g[@data-tank='hero']//s:g[@data-sprite]", NS)
        assert sprite is not None
        assert gold in {part.get("fill") for part in sprite}
        cell = root.find(".//s:g[@id='calendar']/s:rect", NS)
        assert cell.attrib["fill"] == brick
        detail = root.find(".//s:g[@data-brick]", NS)
        assert detail is not None
        assert len(detail.findall("s:path", NS)) == 3
        assert detail.find("s:animate", NS).attrib["values"].split(";")[:3] == ["1", "0", "1"]
