from dataclasses import replace
from datetime import date
from xml.etree import ElementTree

from contribution_dynamic.calendar import Day, demo_calendar
from contribution_dynamic.scenarios.invaders import (
    ARCADE_ALIENS,
    ARCADE_HZ,
    BOB_LIMIT,
    CELL,
    DAMAGE_INTERVAL,
    DODGE,
    FIRST,
    LEFT,
    MARCH_LIMIT,
    MARCH_STEP,
    MAX_BURST,
    MIN_MARCH_INTERVAL,
    SPRITE_HEIGHT,
    SPRITE_SCALE,
    SPRITE_WIDTH,
    STEP,
    TOP,
    alien_position,
    center,
    march_interval,
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
            assert len(volley.shots) <= MAX_BURST
            if volley.damaged:
                assert volley.base == volley.dodge
            else:
                assert abs(abs(volley.base - volley.dodge) - DODGE) < 1e-6
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
        sprites = [root.find(f".//s:g[@id='invader-sprite-{i}']/s:path", NS)
                   for i in range(1, 5)]
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


def test_column_order_alternates_within_local_sectors():
    days = tuple(Day(date(2026, 1, i+1), 1, 0, i) for i in range(8))
    battle = plan_battle(days)
    assert battle is not None
    columns = [volley.shots[0].day.week for volley in battle.volleys]
    assert columns == [0, 7, 1, 6, 2, 5, 3, 4]


def test_short_attacks_revisit_columns_and_preserve_bottom_up_order():
    days = tuple(Day(date(2026, 1, 1+i*7+j), 2, j, i)
                 for i in range(3) for j in range(7))
    battle = plan_battle(days)
    assert battle is not None
    columns = [v.shots[0].day.week for v in battle.volleys]
    assert columns[:3] == [0, 2, 1]
    assert all(a != b for a, b in zip(columns, columns[1:]))
    for week in range(3):
        rows = [s.day.weekday for v in battle.volleys for s in v.shots
                if s.day.week == week]
        assert rows == list(range(6, -1, -1))
        assert sum(v.shots[0].day.week == week for v in battle.volleys) > 1


def test_hits_are_occasional_and_visually_distinct_from_misses():
    days = demo_calendar()
    battle = plan_battle(days)
    assert battle is not None
    hits = sum(v.damaged for v in battle.volleys)
    assert hits == len(battle.volleys) // DAMAGE_INTERVAL
    assert 0 < hits < len(battle.volleys) / 4
    root = ElementTree.fromstring(render_invaders(days))
    assert len(root.findall(".//s:g[@data-hit-kind='ship']", NS)) == hits
    assert len(root.findall(".//s:g[@data-hit-kind='miss']", NS)) == len(battle.volleys)-hits
    assert root.find(".//s:g[@data-ship-body='true']/s:animate", NS) is not None


def test_arcade_oscillation_has_discrete_turns_and_progressive_speed():
    battle = plan_battle(demo_calendar())
    assert battle is not None
    march = battle.march
    assert march[0].time == 0
    assert march[1].time == ARCADE_ALIENS/ARCADE_HZ
    assert all(abs(step.x) <= MARCH_LIMIT and 0 <= step.y <= BOB_LIMIT for step in march)
    assert any(step.y > 0 for step in march)
    assert any(b.x < a.x for a, b in zip(march, march[1:]))
    assert all(b.frame != a.frame and b.alive <= a.alive for a, b in zip(march, march[1:]))
    for a, b in zip(march, march[1:]):
        assert abs(b.x-a.x) in (0, MARCH_STEP)
        assert abs(b.y-a.y) in (0, BOB_LIMIT)
        assert abs((b.time-a.time)-march_interval(a.alive, march[0].alive)) < 1e-7
    assert march_interval(1, 55) == MIN_MARCH_INTERVAL
    assert march_interval(20, 55) < march_interval(55, 55)


def test_formation_and_impacts_share_march_clock():
    days = demo_calendar()
    battle = plan_battle(days)
    assert battle is not None
    for theme in ("dark", "light"):
        root = ElementTree.fromstring(render_invaders(days, theme))
        motion = root.find(".//s:g[@id='invaders']/s:animateTransform", NS)
        assert motion is not None and motion.attrib["calcMode"] == "discrete"
        for level in range(1, 5):
            poses = root.findall(f".//s:g[@id='invader-sprite-{level}']/s:path", NS)
            assert len(poses) == 2 and poses[0].attrib["d"] != poses[1].attrib["d"]
        impacts = root.findall(".//s:g[@data-hit-kind='alien']", NS)
        shots = [shot for volley in battle.volleys for shot in volley.shots]
        for impact, shot in zip(impacts, shots, strict=True):
            x, y = alien_position(shot.day, battle.march, shot.hit)
            assert impact.attrib["transform"] == f"translate({x} {y})"


def test_entire_alien_silhouette_remains_in_its_source_cell():
    days = demo_calendar()
    battle = plan_battle(days)
    assert battle is not None
    half_width = SPRITE_WIDTH*SPRITE_SCALE/2
    half_height = SPRITE_HEIGHT*SPRITE_SCALE/2
    for step in battle.march:
        assert abs(step.x)+half_width <= CELL/2
        assert abs(step.y)+half_height <= CELL/2
    for day in (days[0], days[-1]):
        cx, cy = center(day)
        for step in battle.march:
            x, y = alien_position(day, battle.march, step.time)
            assert cx-CELL/2 <= x-half_width <= x+half_width <= cx+CELL/2
            assert cy-CELL/2 <= y-half_height <= y+half_height <= cy+CELL/2
    for theme in ("dark", "light"):
        root = ElementTree.fromstring(render_invaders(days, theme))
        for level in range(1, 5):
            sprite = root.find(f".//s:g[@id='invader-sprite-{level}']", NS)
            assert sprite is not None
            assert sprite.attrib["transform"] == f"scale({SPRITE_SCALE})"
        motion = root.find(".//s:g[@id='invaders']/s:animateTransform", NS)
        assert motion is not None
        for value in motion.attrib["values"].split(";"):
            x, y = map(float, value.split())
            assert abs(x)+half_width <= CELL/2
            assert abs(y)+half_height <= CELL/2
