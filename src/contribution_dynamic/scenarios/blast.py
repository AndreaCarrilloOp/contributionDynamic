"""GitBlast: arcade-style bombs and destructible contribution bricks."""

from bisect import bisect_left, bisect_right
from collections import deque
from dataclasses import dataclass

from contribution_dynamic.animation import track
from contribution_dynamic.calendar import Day, board_weeks, contribution_level
from contribution_dynamic.labels import LEFT, RIGHT, STEP, TOP, render_labels
from contribution_dynamic.layout import (
    ROWS,
    SIGNATURE_HEIGHT,
    calendar_height,
    calendar_width,
    render_padding,
    render_signature,
)

CELL = 10
FIRST = .12
WALK_TIME = .12
RADIUS = 2
FUSE = .45
FLAME_TIME = .42
MAX_ENEMIES = 3
DIRECTIONS = ((1, 0), (0, 1), (-1, 0), (0, -1))
PALETTES = {
    "dark": {
        "bg": "#111c19", "empty": "#26352e", "text": "#a6b9ac",
        "bricks": ("#52645d", "#6c8174", "#8b9e8c", "#acbca7"),
        "mortar": "#26372d", "highlight": "#dce7d5", "shadow": "#182720",
        "helmet": "#f0eee4", "outline": "#293a48", "face": "#efc5a4",
        "suit": "#4086a6", "boots": "#bc696b", "eye": "#16252c",
        "enemies": ("#e07b72", "#d7ae66", "#b596ce"),
        "enemy_edge": "#41323c", "enemy_eye": "#fff5dc",
        "bomb": "#151c21", "bomb_edge": "#b9c6c3", "spark": "#ffe4a1",
        "fire": "#e38846", "core": "#fff0b5",
    },
    "light": {
        "bg": "#f3f5ee", "empty": "#e0e8dc", "text": "#4d6254",
        "bricks": ("#c3cec0", "#a2b4a3", "#799180", "#506c5c"),
        "mortar": "#384f43", "highlight": "#f6fff1", "shadow": "#3e5548",
        "helmet": "#fffdf5", "outline": "#364755", "face": "#edbc99",
        "suit": "#256284", "boots": "#9b4452", "eye": "#17252e",
        "enemies": ("#b64f4c", "#a1772f", "#8462a8"),
        "enemy_edge": "#4b3540", "enemy_eye": "#fff9e8",
        "bomb": "#20272b", "bomb_edge": "#83948b", "spark": "#b97a24",
        "fire": "#d06a30", "core": "#ffe6a0",
    },
}
Square = tuple[int, int]


@dataclass(frozen=True)
class Blast:
    center: Square
    origin: Square
    shelter: Square
    cross: tuple[Square, ...]
    hits: tuple[Day, ...]
    start: float
    plant: float
    hit: float
    clear: float


@dataclass(frozen=True)
class Enemy:
    event: int
    kind: int
    route: tuple[Square, ...]
    spawn: float
    arrive: float
    end: float
    defeated: bool


@dataclass(frozen=True)
class Run:
    positions: tuple[Square, ...]
    times: tuple[float, ...]
    events: tuple[Blast, ...]
    cycle: float
    entry: tuple[Day, ...]
    enemies: tuple[Enemy, ...] = ()


def _inside(pos: Square, weeks: int) -> bool:
    return 0 <= pos[0] < weeks and 0 <= pos[1] < ROWS


def _neighbors(pos: Square, weeks: int):
    for dx, dy in DIRECTIONS:
        candidate = pos[0]+dx, pos[1]+dy
        if _inside(candidate, weeks):
            yield candidate


def _paths(start: Square, blocked: set[Square], weeks: int):
    parents = {start: None}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        for pos in _neighbors(current, weeks):
            if pos not in blocked and pos not in parents:
                parents[pos] = current
                queue.append(pos)
    return parents


def _route(parents, end: Square) -> tuple[Square, ...]:
    route = [end]
    while parents[route[-1]] is not None:
        route.append(parents[route[-1]])
    return tuple(reversed(route))


def blast_cross(center: Square, radius: int, weeks: int,
                blocked: set[Square]) -> tuple[Square, ...]:
    """A cross stops at the first intact brick in each direction."""
    x, y = center
    points = [center]
    for dx, dy in DIRECTIONS:
        for distance in range(1, radius+1):
            pos = x+dx*distance, y+dy*distance
            if not _inside(pos, weeks):
                break
            points.append(pos)
            if pos in blocked:
                break
    return tuple(points)


def _shelter(center, cross, blocked, weeks):
    """Find an escape route outside the cross before detonation."""
    parents = {center: None}
    queue = deque([center])
    while queue:
        pos = queue.popleft()
        if pos not in cross:
            return _route(parents, pos)
        for neighbor in _neighbors(pos, weeks):
            if neighbor not in blocked and neighbor not in parents:
                parents[neighbor] = pos
                queue.append(neighbor)
    return ()


def _site(current, blocked, weeks):
    parents = _paths(current, blocked, weeks)
    for pos in parents:
        if not any(neighbor in blocked for neighbor in _neighbors(pos, weeks)):
            continue
        cross = blast_cross(pos, RADIUS, weeks, blocked)
        escape = _shelter(pos, cross, blocked, weeks)
        if escape:
            return _route(parents, pos), cross, escape
    raise RuntimeError("No safe bomb placement")


def plan_enemies(run: Run, days: tuple[Day, ...]) -> tuple[Enemy, ...]:
    """Plan distinct enemy patrols on free cells near each bomb."""
    weeks = board_weeks(days)
    blocked = {(d.week, d.weekday) for d in days if d.count}
    blocked.difference_update((d.week, d.weekday) for d in run.entry)
    enemies = []
    for index, event in enumerate(run.events):
        left = bisect_left(run.times, event.start)
        right = bisect_right(run.times, event.clear)
        reserved = set(run.positions[left:right]) | {event.center}
        x, y = event.center
        local = {
            (a, b)
            for a in range(max(0, x-4), min(weeks, x+5))
            for b in range(max(0, y-4), min(ROWS, y+5))
            if abs(a-x)+abs(b-y) <= 4
        } - blocked - reserved
        cross = set(event.cross)
        candidates = sorted(local, key=lambda q: (
            q not in cross, abs(q[0]-x)+abs(q[1]-y), q,
        ))
        count = 0
        for target in candidates:
            if target not in local:
                continue
            defeated = target in cross
            starts = sorted(
                q for q in _neighbors(target, weeks)
                if q in local and (defeated or q not in cross)
            )
            if not starts:
                continue
            origin = min(starts, key=lambda q: (q in cross, q))
            spawn = event.start + .015
            arrive = event.hit - .065
            if arrive <= spawn + .1:
                continue
            end = event.hit if defeated else event.clear
            enemies.append(Enemy(index, (index+count) % 3, (origin, target),
                                 spawn, arrive, end, defeated))
            local.difference_update((origin, target))
            count += 1
            if count == MAX_ENEMIES:
                break
        blocked.difference_update((d.week, d.weekday) for d in event.hits)
    return tuple(enemies)


def plan_run(days: tuple[Day, ...]) -> Run | None:
    """Move one persistent actor; place one bomb on a free neighboring square."""
    bricks = {(d.week, d.weekday): d for d in days if d.count}
    if not bricks:
        return None
    weeks = board_weeks(days)
    blocked = set(bricks)
    first = min(bricks)
    # A free 2x2 component can always offer shelter outside a cross.
    # If none exists, open the least occupied pocket before the hero arrives.
    pockets = [
        tuple((x+dx, y+dy) for dx in range(2) for dy in range(2))
        for x in range(weeks-1) for y in range(ROWS-1)
    ]
    pocket = min(pockets, key=lambda cells: (
        sum(pos in blocked for pos in cells),
        min(abs(x-first[0])+abs(y-first[1]) for x, y in cells),
        cells,
    ))
    entry = tuple(bricks[pos] for pos in pocket if pos in blocked)
    blocked.difference_update(pocket)
    reachable = _paths(pocket[0], blocked, weeks)
    candidates = sorted(reachable, key=lambda pos: (
        abs(pos[0]-first[0])+abs(pos[1]-first[1]), pos,
    ))
    if blocked:
        spawn = next(
            pos for pos in candidates
            if any(n in blocked for n in _neighbors(pos, weeks))
            and _shelter(pos, blast_cross(pos, RADIUS, weeks, blocked), blocked, weeks)
        )
    else:
        spawn = pocket[0]
    positions, times = [spawn, spawn], [0.0, FIRST]
    events = []
    clock = FIRST

    def hold(duration):
        nonlocal clock
        clock += duration
        positions.append(positions[-1])
        times.append(clock)

    def walk(route):
        nonlocal clock
        for pos in route[1:]:
            clock += WALK_TIME
            positions.append(pos)
            times.append(clock)

    while blocked:
        start = clock
        approach, cross, escape = _site(positions[-1], blocked, weeks)
        walk(approach)
        center = positions[-1]
        hold(.10)
        plant = clock
        walk(escape)
        # Wait in safety until the fuse and the flame have finished.
        hold(max(.12, plant+FUSE-clock))
        hit = clock
        hold(FLAME_TIME)
        clear = clock
        hits = tuple(bricks[pos] for pos in cross if pos in blocked)
        blocked.difference_update(cross)
        events.append(Blast(center, approach[0], escape[-1], cross, hits,
                            start, plant, hit, clear))
        hold(.10)

    walk(_route(_paths(positions[-1], set(), weeks), spawn))
    hold(.45)
    run = Run(tuple(positions), tuple(times), tuple(events), max(4.0, clock+.15), entry)
    return Run(run.positions, run.times, run.events, run.cycle, entry, plan_enemies(run, days))


def plan_blasts(days: tuple[Day, ...]) -> tuple[Blast, ...]:
    run = plan_run(days)
    return run.events if run else ()


def _point(square: Square) -> tuple[float, float]:
    return LEFT + square[0] * STEP + CELL / 2, TOP + square[1] * STEP + CELL / 2


def _actor(run: Run, p: dict) -> list[str]:
    positions = [f"{x} {y}" for x, y in map(_point, run.positions)]
    return [
        f'<g data-actor="hero" transform="translate({positions[0]})">',
        track("transform", positions, run.times, run.cycle, transform=True),
        *([track("opacity", [0, 1, 1, 0], [0, FIRST, run.cycle-.08, run.cycle],
                 run.cycle)] if run.entry else []),
        '<g data-sprite="bomber" shape-rendering="crispEdges">',
        f'<path d="M-3 -1H3V3H-3Z" fill="{p["suit"]}"/>',
        f'<path d="M-4 0H-2V2H-4ZM2 0H4V2H2Z" fill="{p["helmet"]}"/>',
        f'<path d="M-3 3H-1V5H-4V4H-3ZM1 3H3V4H4V5H1Z" fill="{p["boots"]}"/>',
        f'<path d="M-3 -6H3V-5H5V0H3V1H-3V0H-5V-5H-3Z" '
        f'fill="{p["helmet"]}" stroke="{p["outline"]}" stroke-width=".65"/>',
        f'<path d="M-3 -3H3V0H-3Z" fill="{p["face"]}"/>',
        f'<path d="M-2 -2H-1V-1H-2ZM1 -2H2V-1H1Z" fill="{p["eye"]}"/>',
        f'<path d="M-1 -7H1V-5H-1Z" fill="{p["boots"]}"/>',
        f'<path d="M-1 1H1V3H-1Z" fill="{p["helmet"]}"/>',
        '</g></g>',
    ]


def _enemy(enemy: Enemy, cycle: float, p: dict) -> list[str]:
    x, y = _point(enemy.route[0])
    tx, ty = _point(enemy.route[-1])
    spawn, arrive, end = enemy.spawn, enemy.arrive, enemy.end
    fill = p["enemies"][enemy.kind]
    outcome = "defeated" if enemy.defeated else "withdrawn"
    shapes = (
        "M-3 -5H3V-4H5V1H4V3H2V5H-2V3H-4V1H-5V-4H-3Z",
        "M-2 -5H2V-3H4V-2H5V3H3V5H1V3H-1V5H-3V3H-5V-2H-4V-3H-2Z",
        "M-4 -4H-2V-5H2V-4H4V-1H5V3H3V4H-3V3H-5V-1H-4Z",
    )
    parts = [
        f'<g data-actor="enemy" data-enemy="{enemy.event}-{enemy.kind}" '
        f'data-outcome="{outcome}" transform="translate({x} {y})" opacity="0">',
        track("opacity", [0, 1, 1, 0], [spawn, spawn+.07, end-.035, end], cycle),
        track("transform", [f"{x} {y}", f"{tx} {ty}"], [spawn+.07, arrive],
              cycle, transform=True),
        '<g shape-rendering="crispEdges">',
        f'<path d="{shapes[enemy.kind]}" fill="{fill}" stroke="{p["enemy_edge"]}" '
        'stroke-width=".65" stroke-linejoin="round"/>',
        f'<path d="M-3 -2H-1V1H-3ZM1 -2H3V1H1Z" fill="{p["enemy_eye"]}"/>',
        f'<path d="M-2 -1H-1V1H-2ZM2 -1H3V1H2Z" fill="{p["eye"]}"/>',
        f'<path d="M-1 2H1V3H-1Z" fill="{p["enemy_edge"]}"/>',
        '</g></g>',
    ]
    if enemy.defeated:
        parts.extend([
            f'<circle data-enemy-impact="true" cx="{tx}" cy="{ty}" r="2" '
            f'fill="none" stroke="{p["core"]}" stroke-width="1.1" opacity="0">',
            track("opacity", [0, 1, 0], [end-.01, end, end+.22], cycle),
            track("r", [2, 7], [end, end+.22], cycle),
            '</circle>',
        ])
    return parts


def _event(event: Blast, cycle: float, p: dict) -> list[str]:
    x, y = _point(event.center)
    place, hit, clear = event.plant, event.hit, event.clear
    parts = [
        f'<g data-blast="{event.center[0]},{event.center[1]}">',
        f'<g data-bomb="true" transform="translate({x} {y})" opacity="0">',
        track("opacity", [0, 1, 1, 0], [place-.03, place, hit-.02, hit], cycle),
        f'<circle r="4.2" fill="{p["bomb"]}" stroke="{p["bomb_edge"]}" stroke-width=".6"/>',
        f'<path d="M1 -4Q1 -7 4 -7" fill="none" stroke="{p["spark"]}" stroke-width="1"/>',
        f'<circle cx="4" cy="-7" r="1.5" fill="{p["spark"]}">',
        track("r", [1, 2.5, 1, 3], [place, place+.12, place+.24, hit], cycle),
        '</circle></g>',
        '<g data-explosion="true" opacity="0">',
        track("opacity", [0, 1, .85, 0], [hit-.01, hit+.06, hit+.20, clear], cycle),
    ]
    for pos in event.cross:
        cx, cy = _point(pos)
        horizontal = pos[1] == event.center[1]
        vertical = pos[0] == event.center[0]
        for w, h in ([(13, 7)] if horizontal else []) + ([(7, 13)] if vertical else []):
            parts.append(f'<rect x="{cx-w/2}" y="{cy-h/2}" width="{w}" height="{h}" '
                         f'rx="1" fill="{p["fire"]}" opacity=".9"/>')
        if horizontal:
            parts.append(f'<path d="M{cx-6.5} {cy}H{cx+6.5}" '
                         f'stroke="{p["core"]}" stroke-width="2.4"/>')
        if vertical:
            parts.append(f'<path d="M{cx} {cy-6.5}V{cy+6.5}" '
                         f'stroke="{p["core"]}" stroke-width="2.4"/>')
    parts.append('</g>')
    for day in event.hits:
        bx, by = _point((day.week, day.weekday))
        color = p["bricks"][contribution_level(day)-1]
        for dx, dy in ((-7, -8), (7, -7), (-6, 7), (6, 8)):
            parts.extend([
                f'<rect x="{bx-1}" y="{by-1}" width="2" height="2" fill="{color}" '
                'opacity="0">',
                track("opacity", [0, 1, 0], [hit, hit+.04, clear], cycle),
                track("x", [bx-1, bx+dx], [hit, clear], cycle),
                track("y", [by-1, by+dy], [hit, clear], cycle),
                '</rect>',
            ])
    parts.append('</g>')
    return parts


def render_blast(
    days: tuple[Day, ...], theme: str = "dark", *, signature: bool = False,
) -> str:
    p = PALETTES[theme]
    width = calendar_width(LEFT, STEP, CELL, RIGHT, board_weeks(days))
    height = calendar_height(CELL, bottom=12)
    height += SIGNATURE_HEIGHT if signature else 0
    run = plan_run(days)
    events = run.events if run else ()
    cycle = run.cycle if run else 4.0
    hit_times = {day: event.hit for event in events for day in event.hits}
    if run:
        hit_times.update((day, FIRST / 2) for day in run.entry)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        'aria-label="GitBlast arcade contribution calendar">',
        '<title>GitBlast — ignite your contributions</title>',
        f'<rect width="{width}" height="{height}" rx="6" fill="{p["bg"]}"/>',
    ]
    parts.extend(render_labels(days, width, CELL, p["text"]))
    parts.append('<g id="calendar">')
    parts.extend(render_padding(days, CELL, p["empty"]))
    for day in sorted(days, key=lambda d: (d.week, d.weekday)):
        x, y = LEFT + day.week * STEP, TOP + day.weekday * STEP
        level = contribution_level(day)
        color = p["bricks"][level-1] if level else p["empty"]
        parts.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="1" '
                     f'fill="{color}" data-date="{day.date.isoformat()}" data-level="{level}">')
        parts.append(f'<title>{day.date.isoformat()}: {day.count} contributions</title>')
        if day in hit_times:
            parts.append(track("fill", [color, p["empty"], color],
                               [0, hit_times[day], cycle], cycle, "discrete"))
        parts.append('</rect>')
    parts.extend(['</g>', '<g id="brick-mortar">'])
    for day in sorted(hit_times, key=lambda d: (d.week, d.weekday)):
        x, y = LEFT + day.week*STEP, TOP + day.weekday*STEP
        parts.append(f'<g data-brick="{day.date.isoformat()}" opacity="1">')
        parts.append(f'<path d="M{x} {y+3.5}H{x+10}M{x} {y+7}H{x+10}'
                     f'M{x+5} {y}V{y+3.5}M{x+2.5} {y+3.5}V{y+7}'
                     f'M{x+7.5} {y+3.5}V{y+7}M{x+5} {y+7}V{y+10}" '
                     f'fill="none" stroke="{p["mortar"]}" stroke-width=".6" opacity=".72"/>')
        parts.append(f'<path d="M{x+.6} {y+.8}H{x+9.4}" fill="none" '
                     f'stroke="{p["highlight"]}" stroke-width=".7" opacity=".5"/>')
        parts.append(f'<path d="M{x+.5} {y+9.5}H{x+9.5}" fill="none" '
                     f'stroke="{p["shadow"]}" stroke-width=".7" opacity=".55"/>')
        parts.append(track("opacity", [1, 0, 1],
                           [0, hit_times[day], cycle], cycle, "discrete"))
        parts.append('</g>')
    parts.extend(['</g>', '<g id="enemy-patrols">'])
    if run:
        for enemy in run.enemies:
            parts.extend(_enemy(enemy, cycle, p))
    parts.extend(['</g>', '<g id="arcade-events">'])
    if run:
        for day in run.entry:
            x, y = _point((day.week, day.weekday))
            parts.append(f'<g data-entry="{day.date.isoformat()}" opacity="0">')
            parts.append(track("opacity", [0, 1, 0], [0, FIRST/2, FIRST], cycle))
            parts.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{p["fire"]}"/>')
            parts.append('</g>')
    for event in events:
        parts.extend(_event(event, cycle, p))
    if run:
        parts.extend(_actor(run, p))
    parts.extend([
        '</g>',
        *render_signature(width, height, p["text"], signature),
        '</svg>',
    ])
    return "\n".join(parts) + "\n"
