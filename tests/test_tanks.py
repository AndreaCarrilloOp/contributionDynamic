from dataclasses import replace
from datetime import date
from xml.etree import ElementTree

from contribution_dynamic.calendar import Day, demo_calendar
from contribution_dynamic.scenarios.tanks import (
    FIRE_RANGE,
    LEFT,
    MAX_ENEMIES,
    SPAWN_RADIUS,
    STEP,
    TOP,
    can_fire,
    plan_battle,
    render_tanks,
)

NS = {"s": "http://www.w3.org/2000/svg"}


def test_all_active_bricks_are_destroyed_once():
    days = demo_calendar()
    battle = plan_battle(days)
    assert battle is not None
    bricks = [a.day for a in battle.attacks if a.day is not None]
    assert set(bricks) == {d for d in days if d.count}
    assert len(bricks) == len(set(bricks))
    assert battle.positions[0] == battle.positions[-1] == battle.spawn


def test_dense_and_demo_routes_never_enter_standing_bricks_or_enemies():
    for days in (demo_calendar(), tuple(replace(d, count=1) for d in demo_calendar())):
        battle = plan_battle(days)
        assert battle is not None
        bricks = {(d.week, d.weekday) for d in days if d.count}
        assert battle.spawn not in bricks
        assert len(battle.positions) == len(battle.times) == len(battle.angles)
        assert all(a < b for a, b in zip(battle.times, battle.times[1:]))
        for pos, dest, t in zip(battle.positions, battle.positions[1:], battle.times[1:]):
            assert abs(pos[0]-dest[0])+abs(pos[1]-dest[1]) <= 1
            if dest in bricks:
                assert any(a.day and a.target == dest and a.hit < t for a in battle.attacks)
            for enemy in battle.enemies:
                a = next(a for a in battle.attacks if a.enemy == enemy.enemy)
                if a.spawn <= t < a.hit:
                    occupied = max(i for i, tick in enumerate(enemy.times) if tick <= t)
                    assert dest != enemy.positions[occupied]
        for a in battle.attacks:
            obstacles = {
                b.target for b in battle.attacks if b.day is not None and b.hit >= a.fire
            }
            for route in battle.enemies:
                encounter = next(b for b in battle.attacks if b.enemy == route.enemy)
                if encounter.spawn <= a.fire < encounter.hit:
                    index = max(i for i, t in enumerate(route.times) if t <= a.fire)
                    obstacles.add(route.positions[index])
            assert can_fire(a.source, a.target, obstacles)
            assert a.fire < a.hit < a.complete


def test_enemy_waves_return_fire_and_are_defeated():
    battle = plan_battle(demo_calendar())
    assert battle is not None
    enemies = [a for a in battle.attacks if a.enemy is not None]
    assert enemies
    groups = {}
    for enemy in enemies:
        assert enemy.spawn < enemy.counter < enemy.shield_hit < enemy.fire < enemy.hit
        groups.setdefault(enemy.spawn, []).append(enemy)
    assert all(len(group) <= MAX_ENEMIES for group in groups.values())
    assert any(len(group) > 1 for group in groups.values())


def test_sparse_activity_starts_immediately():
    day = Day(date(2026, 11, 17), 9, 2, 52, 4)
    battle = plan_battle((day,))
    assert battle is not None
    assert battle.attacks[0].day == day
    assert battle.attacks[0].fire < 1


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
        assert len(enemies) > 1
        assert len(root.findall(".//s:g[@data-projectile='enemy']", NS)) == len(enemies)
        assert root.find(".//s:g[@data-base='eagle']", NS) is not None


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
    detail = root.find(".//s:g[@data-brick]", NS)
    assert detail is not None
    assert len(detail.findall("s:path", NS)) == 3


def test_no_fabricated_battle_on_empty_calendar():
    for days in ((), (Day(date(2026, 11, 17), 0, 2, 52, 0),)):
        assert plan_battle(days) is None
        root = ElementTree.fromstring(render_tanks(days))
        assert not root.findall(".//s:g[@data-tank]", NS)
        assert not root.findall(".//s:animate", NS)


def test_enemies_have_distinct_roles_and_pursue_on_free_squares():
    days = demo_calendar()
    battle = plan_battle(days)
    assert battle is not None
    attacks = {a.enemy: a for a in battle.attacks if a.enemy is not None}
    cleared = {a.target: a.hit for a in battle.attacks if a.day is not None}
    assert {route.role for route in battle.enemies} == {"hunter", "ambusher", "flanker"}
    assert any(len(set(route.positions)) > 1 for route in battle.enemies)
    for route in battle.enemies:
        attack = attacks[route.enemy]
        assert route.positions[-1] == attack.target
        assert route.times[0] == attack.spawn
        assert route.times[-1] < attack.hit
        assert all(a < b for a, b in zip(route.times, route.times[1:]))
        for pos, time in zip(route.positions, route.times, strict=True):
            assert pos not in cleared or cleared[pos] < time
        for a, b in zip(route.positions, route.positions[1:]):
            assert abs(a[0]-b[0])+abs(a[1]-b[1]) <= 1


def test_enemies_do_not_share_squares_at_movement_boundaries():
    battle = plan_battle(demo_calendar())
    assert battle is not None
    attacks = {a.enemy: a for a in battle.attacks if a.enemy is not None}
    ticks = sorted({
        t for route in battle.enemies for t in route.times
    })
    for tick in ticks:
        positions = []
        for route in battle.enemies:
            attack = attacks[route.enemy]
            if attack.spawn <= tick < attack.hit:
                i = max(i for i, t in enumerate(route.times) if t <= tick)
                positions.append(route.positions[i])
        assert len(positions) == len(set(positions))


def test_ranged_fire_stops_at_bricks_and_tanks():
    assert can_fire((2, 2), (7, 2), set())
    assert can_fire((7, 2), (2, 2), {(2, 2)})
    assert not can_fire((2, 2), (7, 2), {(4, 2)})
    assert not can_fire((2, 2), (2, 7), {(2, 4)})
    assert not can_fire((2, 2), (8, 2), set())
    assert not can_fire((2, 2), (3, 3), set())


def test_enemy_spawn_is_near_a_standing_brick():
    for days in (demo_calendar(), tuple(replace(d, count=1) for d in demo_calendar())):
        battle = plan_battle(days)
        assert battle is not None
        bricks = {a.target: a.hit for a in battle.attacks if a.day is not None}
        for enemy in battle.enemies:
            x, y = enemy.positions[0]
            born = enemy.times[0]
            standing = {pos for pos, hit in bricks.items() if hit > born}
            assert (x, y) not in standing
            assert any(0 < abs(x-a)+abs(y-b) <= SPAWN_RADIUS for a, b in standing)


def test_both_sides_fire_across_multiple_cells():
    battle = plan_battle(demo_calendar())
    assert battle is not None
    ranged = [
        a for a in battle.attacks
        if a.enemy is not None
        and 1 < abs(a.source[0]-a.target[0])+abs(a.source[1]-a.target[1]) <= FIRE_RANGE
    ]
    assert ranged
    for attack in ranged:
        assert attack.counter < attack.shield_hit < attack.fire < attack.hit
        assert abs((attack.shield_hit-attack.counter)-(attack.hit-attack.fire)) < 1e-6


def test_no_enemy_spawns_after_the_last_brick_is_destroyed():
    day = Day(date(2026, 11, 17), 1, 2, 52, 1)
    battle = plan_battle((day,))
    assert battle is not None
    assert not battle.enemies
