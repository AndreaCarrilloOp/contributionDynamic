from dataclasses import replace
from datetime import date
from math import hypot
from xml.etree import ElementTree

from contribution_dynamic.calendar import Day, demo_calendar
from contribution_dynamic.scenarios.tanks import (
    FIRE_RANGE,
    LEFT,
    MAX_ENEMIES,
    PROJECTILE_SPEED,
    SHIELD_RADIUS,
    SPAWN_GAP,
    SPAWN_RADIUS,
    STEP,
    TOP,
    _patrol_step,
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
    births = sorted(enemy.spawn for enemy in enemies)
    assert all(b-a >= SPAWN_GAP-1e-8 for a, b in zip(births, births[1:]))
    for enemy in enemies:
        assert enemy.spawn < enemy.counter < enemy.counter_hit < enemy.fire < enemy.hit
    concurrent = [sum(e.spawn <= t < e.hit for e in enemies) for t in births]
    assert max(concurrent) <= MAX_ENEMIES
    assert max(concurrent) > 1


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
        assert attack.counter < attack.counter_hit < attack.fire < attack.hit
        distance = sum(abs(a-b) for a, b in zip(attack.counter_target, attack.target))
        protection = SHIELD_RADIUS if attack.counter_outcome == "shield" else 0
        assert abs(attack.counter_hit-attack.counter
                   - max(.12, (distance*STEP-7-protection)/PROJECTILE_SPEED)) < 1e-6


def test_no_enemy_spawns_after_the_last_brick_is_destroyed():
    day = Day(date(2026, 11, 17), 1, 2, 52, 1)
    battle = plan_battle((day,))
    assert battle is not None
    assert not battle.enemies


def test_counterfire_is_evaded_or_blocked_without_damage():
    for days in (demo_calendar(), tuple(replace(d, count=1) for d in demo_calendar())):
        battle = plan_battle(days)
        assert battle is not None
        counters = [a for a in battle.attacks if a.enemy is not None]
        assert counters
        missed = [a for a in counters if a.counter_outcome == "miss"]
        assert missed
        assert all(a.counter_outcome in {"miss", "shield"} for a in counters)
        assert any(a.source != a.counter_target for a in missed)
        for attack in missed:
            assert attack.evade is not None
            dx = attack.evade[0]-attack.counter_target[0]
            dy = attack.evade[1]-attack.counter_target[1]
            assert abs(dx)+abs(dy) == 1
            assert dx*(attack.target[0]-attack.counter_target[0])+dy*(
                attack.target[1]-attack.counter_target[1]
            ) == 0
            at_impact = max(i for i, t in enumerate(battle.times) if t <= attack.counter_hit)
            assert battle.positions[at_impact] == attack.evade
            assert battle.positions[at_impact+1] == attack.evade


def test_render_counterfire_outcomes_match_the_simulation():
    days = demo_calendar()
    battle = plan_battle(days)
    assert battle is not None
    expected = [a.counter_outcome for a in battle.attacks if a.enemy is not None]
    assert expected.count("miss") > len(expected)/2
    for theme in ("dark", "light"):
        root = ElementTree.fromstring(render_tanks(days, theme))
        outcomes = root.findall(".//s:g[@data-counter-outcome]", NS)
        assert [node.attrib["data-counter-outcome"] for node in outcomes] == expected
        assert set(expected) <= {"miss", "shield"}
        hero = root.find(".//s:g[@data-tank-body='hero']", NS)
        assert hero is not None
        assert hero.find("s:animate[@attributeName='opacity']", NS) is None
        for attack in battle.attacks:
            if attack.counter_outcome != "shield":
                continue
            group = root.find(f".//s:g[@data-shot='{attack.enemy}']", NS)
            assert group is not None
            shell = group.find("s:g[@data-projectile='enemy']/s:animateTransform", NS)
            assert shell is not None
            values = shell.attrib["values"].split(";")
            x, y = map(float, values[-1].split())
            cx = LEFT + attack.counter_target[0]*STEP + 5
            cy = TOP + attack.counter_target[1]*STEP + 5
            assert abs(hypot(x-cx, y-cy)-SHIELD_RADIUS) < .002
            assert group.find(".//s:circle[@data-protection='true']", NS) is not None


def test_enemy_reinforcements_overlap_existing_opponents():
    battle = plan_battle(demo_calendar())
    assert battle is not None
    enemies = sorted((a for a in battle.attacks if a.enemy is not None),
                     key=lambda a: a.spawn)
    assert len(enemies) > MAX_ENEMIES
    end = enemies[0].hit
    for enemy in enemies[1:]:
        assert enemy.spawn < end, "Enemy-free gap between reinforcements"
        end = max(end, enemy.hit)


def test_surviving_enemy_keeps_moving_during_brick_attacks():
    battle = plan_battle(demo_calendar())
    assert battle is not None
    attacks = {a.enemy: a for a in battle.attacks if a.enemy is not None}
    moved = False
    for brick in (a for a in battle.attacks if a.day is not None):
        survivors = [
            route for route in battle.enemies
            if attacks[route.enemy].spawn < brick.fire < brick.complete
            < attacks[route.enemy].hit
        ]
        if len(survivors) != 1:
            continue
        route = survivors[0]
        if any(a != b and brick.fire < tick <= brick.complete
               for a, b, tick in zip(route.positions, route.positions[1:], route.times[1:])):
            moved = True
    assert moved, "The sole surviving enemy must move while the hero clears bricks"


def test_patrol_fallback_moves_only_when_a_legal_square_exists():
    position, hero, spawn = (2, 2), (5, 5), (0, 0)
    # No reachable firing line: the enemy has one legal patrol step.
    blocked = {(x, y) for x in range(53) for y in range(7)}
    blocked.difference_update({position, (3, 2), hero})
    assert _patrol_step(position, hero, (1, 0), "hunter", blocked, 53, spawn) == (3, 2)
    blocked.add((3, 2))
    assert _patrol_step(position, hero, (1, 0), "hunter", blocked, 53, spawn) == position
