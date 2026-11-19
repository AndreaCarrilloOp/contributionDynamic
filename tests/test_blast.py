from dataclasses import replace
from datetime import date
from xml.etree import ElementTree

import pytest

from contribution_dynamic.calendar import Day, demo_calendar
from contribution_dynamic.scenarios.blast import (
    FIRST,
    INITIAL_ENEMIES,
    LEFT,
    MAX_ENEMIES,
    SPAWN_GAP,
    STEP,
    TOP,
    blast_cross,
    board_weeks,
    plan_blasts,
    plan_run,
    render_blast,
)

NS = {"s": "http://www.w3.org/2000/svg"}


def test_cross_stops_at_first_intact_brick():
    blocked = {(3, 2), (4, 2)}
    cross = blast_cross((2, 2), 2, 53, blocked)
    assert (3, 2) in cross
    assert (4, 2) not in cross
    assert (3, 3) not in cross
    assert (2, 0) in cross


@pytest.mark.parametrize("dense", [False, True])
def test_one_continuous_safe_route_and_valid_bombs(dense):
    days = demo_calendar()
    if dense:
        days = tuple(replace(d, count=1) for d in days)
    run = plan_run(days)
    assert run is not None
    blocked = {(d.week, d.weekday) for d in days if d.count}
    original = blocked.copy()
    hits = {(d.week, d.weekday) for d in run.entry}
    assert hits <= original
    blocked.difference_update(hits)
    assert run.positions[0] not in blocked
    if dense:
        assert len(run.entry) == 4
    assert run.positions[0] == run.positions[-1]
    assert len(run.positions) == len(run.times)
    assert all(a < b for a, b in zip(run.times, run.times[1:]))
    last = FIRST
    for event in run.events:
        assert last <= event.start < event.plant < event.hit < event.clear
        assert event.center not in blocked
        x, y = event.center
        assert any(abs(x-a)+abs(y-b) == 1 for a, b in blocked)
        assert event.shelter not in event.cross
        assert event.hits
        actual_hits = {(d.week, d.weekday) for d in event.hits}
        assert actual_hits == blocked.intersection(event.cross)
        assert not hits.intersection(actual_hits)
        hits.update(actual_hits)
        for pos, tick in zip(run.positions, run.times, strict=True):
            if event.start <= tick <= event.clear:
                assert pos not in blocked
            if event.hit <= tick <= event.clear:
                assert pos not in event.cross
        blocked.difference_update(actual_hits)
        last = event.clear
    assert not blocked
    assert hits == original
    for a, b in zip(run.positions, run.positions[1:]):
        assert abs(a[0]-b[0])+abs(a[1]-b[1]) <= 1
        assert 0 <= b[0] < board_weeks(days) and 0 <= b[1] < 7
    assert all(0 <= x < board_weeks(days) and 0 <= y < 7 for x, y in run.positions)
    for event in run.events:
        assert all(0 <= x < board_weeks(days) and 0 <= y < 7 for x, y in event.cross)


def test_sparse_calendar_starts_without_empty_column_delay():
    day = Day(date(2026, 11, 17), 7, 2, 52, 3)
    event, = plan_blasts((day,))
    assert event.start == FIRST
    assert event.hits == (day,)
    assert event.plant < .5
    assert event.center != (day.week, day.weekday)


def test_svg_has_one_actor_and_preserves_calendar():
    days = demo_calendar()
    for theme in ("dark", "light"):
        svg = render_blast(days, theme)
        assert svg == render_blast(days, theme)
        root = ElementTree.fromstring(svg)
        cells = root.findall(".//s:g[@id='calendar']/s:rect", NS)
        assert len(cells) == len(days)
        for cell, day in zip(cells, days, strict=True):
            assert cell.attrib["data-date"] == day.date.isoformat()
            assert int(cell.attrib["x"]) == LEFT + day.week * STEP
            assert int(cell.attrib["y"]) == TOP + day.weekday * STEP
        assert len(root.findall(".//s:g[@data-actor='hero']", NS)) == 1
        assert len(root.findall(".//s:g[@data-bomb='true']", NS)) == len(plan_blasts(days))


def test_no_bombs_when_no_activity():
    for days in ((), (Day(date(2026, 11, 17), 0, 2, 52, 0),)):
        root = ElementTree.fromstring(render_blast(days))
        assert not root.findall(".//s:g[@data-bomb]", NS)
        assert not root.findall(".//s:g[@data-actor]", NS)
        assert not root.findall(".//s:animate", NS)


def test_brick_restores_original_fill():
    day = Day(date(2026, 11, 17), 99, 2, 52, 1)
    root = ElementTree.fromstring(render_blast((day,)))
    cell = root.find(".//s:g[@id='calendar']/s:rect", NS)
    assert cell is not None
    assert cell.attrib["data-level"] == "1"
    animation = cell.find("s:animate", NS)
    assert animation is not None
    values = animation.attrib["values"].split(";")
    assert values[0] == values[-1] == cell.attrib["fill"]
    assert values[1] != values[0]


@pytest.mark.parametrize("dense", [False, True])
def test_enemies_spawn_after_damage_and_only_one_at_a_time(dense):
    days = demo_calendar()
    if dense:
        days = tuple(replace(day, count=1) for day in days)
    run = plan_run(days)
    assert run is not None
    assert run.enemies
    later = [enemy for enemy in run.enemies if enemy.source is not None]
    births = [enemy.spawn for enemy in later]
    assert all(b-a >= SPAWN_GAP-1e-8 for a, b in zip(births, births[1:]))
    assert len({enemy.source for enemy in later}) == len(later)
    initial = [enemy for enemy in run.enemies if enemy.spawn == 0]
    assert len(initial) <= INITIAL_ENEMIES
    if not dense:
        assert len(initial) == INITIAL_ENEMIES
    for enemy in run.enemies:
        if enemy.source is None:
            assert enemy.event == -1 and enemy.spawn == 0
        else:
            event = run.events[enemy.event]
            assert enemy.source in event.hits
            assert event.clear < enemy.spawn
        assert enemy.spawn < enemy.end < run.cycle
        assert len(enemy.route) == len(enemy.times)
        assert len(set(enemy.route)) > 1
        assert enemy.times[0] == enemy.spawn
        assert all(a < b for a, b in zip(enemy.times, enemy.times[1:]))
        assert all(0 <= x < board_weeks(days) and 0 <= y < 7 for x, y in enemy.route)
        assert all(abs(a[0]-b[0])+abs(a[1]-b[1]) <= 1
                   for a, b in zip(enemy.route, enemy.route[1:]))
        cleared = set(run.entry) if enemy.spawn else set()
        for prior in run.events[:enemy.event+1]:
            cleared.update(prior.hits)
        blocked = {(d.week, d.weekday) for d in days if d.count and d not in cleared}
        assert not set(enemy.route) & blocked
        if enemy.defeated:
            impact = run.events[enemy.hit_event]
            assert enemy.hit_event > enemy.event
            assert enemy.end == impact.hit
            assert enemy.route[-1] in impact.cross
        else:
            assert abs(enemy.end-(run.cycle-.02)) < 1e-8
        active = [e for e in run.enemies if e.spawn <= enemy.spawn < e.end]
        assert len(active) <= MAX_ENEMIES
        for other in active:
            if other != enemy:
                assert not set(enemy.route) & set(other.route)


def test_enemy_sprites_and_impacts_in_both_themes():
    days = demo_calendar()
    run = plan_run(days)
    assert run is not None
    assert run.enemies
    for theme in ("dark", "light"):
        root = ElementTree.fromstring(render_blast(days, theme))
        assert len(root.findall(".//s:g[@data-sprite='bomber']", NS)) == 1
        enemies = root.findall(".//s:g[@data-actor='enemy']", NS)
        assert len(enemies) == len(run.enemies)
        initial = [e for e in enemies if e.attrib["data-source"] == "initial"]
        assert len(initial) == INITIAL_ENEMIES
        assert all(e.attrib["opacity"] == "1" for e in initial)
        later = [e for e in enemies if e.attrib["data-source"] != "initial"]
        assert len({e.attrib["data-spawn"] for e in later}) == len(later)
        assert all(e.attrib["opacity"] == "0" for e in later)
        assert len(root.findall(".//s:circle[@data-enemy-impact]", NS)) == sum(
            e.defeated for e in run.enemies
        )


def test_sparse_calendar_has_visible_enemies_before_first_bomb():
    day = Day(date(2026, 11, 17), 7, 2, 52, 3)
    run = plan_run((day,))
    assert run is not None
    initial = [e for e in run.enemies if e.spawn == 0]
    assert len(initial) == INITIAL_ENEMIES
    assert all(e.source is None for e in initial)
    assert all((day.week, day.weekday) not in e.route for e in initial)


def test_initial_patrol_maintains_enemy_continuity():
    run = plan_run(demo_calendar())
    assert run is not None
    enemies = sorted(run.enemies, key=lambda e: e.spawn)
    assert enemies and enemies[0].spawn == 0
    end = enemies[0].end
    for enemy in enemies[1:]:
        assert enemy.spawn < end
        end = max(end, enemy.end)
    assert end >= run.times[-1]
