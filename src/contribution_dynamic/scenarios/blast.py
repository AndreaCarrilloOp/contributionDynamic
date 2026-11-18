"""GitBlast: arcade-style bombs and destructible contribution bricks."""

from collections import deque
from dataclasses import dataclass

from contribution_dynamic.animation import track
from contribution_dynamic.calendar import Day, board_weeks, contribution_level
from contribution_dynamic.labels import LEFT, RIGHT, STEP, TOP, render_labels
from contribution_dynamic.layout import ROWS, calendar_width

CELL = 10
FIRST = .12
WALK_TIME = .12
RADIUS = 2
FUSE = .45
FLAME_TIME = .42
DIRECTIONS = ((1, 0), (0, 1), (-1, 0), (0, -1))
PALETTES = {
    "dark": {
        "bg": "#10151e", "empty": "#202b38", "text": "#a5b4c6",
        "bricks": ("#78402e", "#a65336", "#d07842", "#f4a65d"),
        "mortar": "#482b28", "actor": "#eef6ff", "visor": "#22d3ee",
        "bomb": "#171b26", "outline": "#97a9bd", "spark": "#fff0a1",
        "fire": "#f97316", "core": "#fff0a1",
    },
    "light": {
        "bg": "#fff8ef", "empty": "#e9e1d9", "text": "#67594d",
        "bricks": ("#f2c09a", "#de986d", "#bf6942", "#984326"),
        "mortar": "#8a4e35", "actor": "#245aa4", "visor": "#a5f3fc",
        "bomb": "#202430", "outline": "#55616e", "spark": "#c27a08",
        "fire": "#ea580c", "core": "#fef08a",
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
class Run:
    positions: tuple[Square, ...]
    times: tuple[float, ...]
    events: tuple[Blast, ...]
    cycle: float
    entry: tuple[Day, ...]


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
    return Run(tuple(positions), tuple(times), tuple(events), max(4.0, clock+.15), entry)


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
        '<g transform="scale(.65)">',
        f'<rect x="-4" y="-1" width="8" height="6" rx="1" fill="{p["actor"]}"/>',
        f'<rect x="-5" y="-6" width="10" height="8" rx="2" fill="{p["actor"]}" '
        f'stroke="{p["outline"]}" stroke-width=".6"/>',
        f'<rect x="-3" y="-4" width="6" height="3" rx="1" fill="{p["visor"]}"/>',
        f'<path d="M-3 5V7M3 5V7" stroke="{p["outline"]}" stroke-width="2"/>',
        '</g></g>',
    ]


def _event(event: Blast, cycle: float, p: dict) -> list[str]:
    x, y = _point(event.center)
    place, hit, clear = event.plant, event.hit, event.clear
    parts = [
        f'<g data-blast="{event.center[0]},{event.center[1]}">',
        f'<g data-bomb="true" transform="translate({x} {y})" opacity="0">',
        track("opacity", [0, 1, 1, 0], [place-.03, place, hit-.02, hit], cycle),
        f'<circle r="4.4" fill="{p["bomb"]}" stroke="{p["outline"]}" stroke-width=".6"/>',
        f'<path d="M1 -4Q1 -7 4 -7" fill="none" stroke="{p["spark"]}" stroke-width="1"/>',
        f'<circle cx="4" cy="-7" r="1.5" fill="{p["spark"]}">',
        track("r", [1, 2.5, 1, 3], [place, place+.12, place+.24, hit], cycle),
        '</circle></g>',
        '<g data-explosion="true" opacity="0">',
        track("opacity", [0, 1, .85, 0], [hit-.01, hit+.06, hit+.20, clear], cycle),
    ]
    for pos in event.cross:
        cx, cy = _point(pos)
        parts.extend([
            f'<rect x="{cx-6.5}" y="{cy-6.5}" width="13" height="13" rx="2" '
            f'fill="{p["fire"]}" opacity=".85"/>',
            f'<path d="M{cx-4} {cy}L{cx} {cy-4}L{cx+4} {cy}L{cx} {cy+4}Z" '
            f'fill="{p["core"]}"/>',
        ])
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


def render_blast(days: tuple[Day, ...], theme: str = "dark") -> str:
    p = PALETTES[theme]
    width = calendar_width(LEFT, STEP, CELL, RIGHT, board_weeks(days))
    height = TOP + ROWS * STEP + 18
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
        parts.append(f'<path d="M{x} {y+5}H{x+10}M{x+5} {y}V{y+5}M{x+3} {y+5}V{y+10}" '
                     f'fill="none" stroke="{p["mortar"]}" stroke-width=".6" opacity=".65">')
        parts.append(track("opacity", [.65, 0, .65],
                           [0, hit_times[day], cycle], cycle, "discrete"))
        parts.append('</path>')
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
        f'<text x="{LEFT}" y="{height-6}" fill="{p["fire"]}" font-size="8" '
        'letter-spacing="1.3" font-family="system-ui,sans-serif">GITBLAST</text>',
        '</svg>',
    ])
    return "\n".join(parts) + "\n"
