"""GitInvaders: a single pixel-art ship against the contribution formation."""

from bisect import bisect_right
from dataclasses import dataclass, replace
from itertools import groupby

from contribution_dynamic.animation import track
from contribution_dynamic.calendar import Day, board_weeks, contribution_level
from contribution_dynamic.labels import LEFT, RIGHT, STEP, TOP, render_labels
from contribution_dynamic.layout import (
    SIGNATURE_HEIGHT,
    calendar_width,
    render_padding,
    render_signature,
)

CELL = 10
SHIP_Y = TOP + 7 * STEP + 17
FIRST = .12
ARCADE_ALIENS = 55
ARCADE_HZ = 60
MARCH_STEP = 2
MARCH_LIMIT = 10
DROP_STEP = 4
DROP_LIMIT = 8
MIN_MARCH_INTERVAL = .12
DODGE = 16
DAMAGE_INTERVAL = 9
MAX_BURST = 2
PALETTES = {
    "dark": {
        "bg": "#090e1a", "empty": "#141f30", "text": "#93a6c3",
        "tiles": ("#34304c", "#243a59", "#53344e", "#514026"),
        "aliens": ("#49d8a0", "#48b8ff", "#ef58be", "#ffcd53"),
        "ship": "#edf6ff", "ship_core": "#38bdf8", "laser": "#7fffe4",
        "hostile": "#ff745e", "spark": "#fff2bc", "line": "#263751",
    },
    "light": {
        "bg": "#f5f8ff", "empty": "#e5ebf5", "text": "#455675",
        "tiles": ("#d7eee5", "#dce9fb", "#f4dcea", "#f5e8ce"),
        "aliens": ("#12865c", "#1664ad", "#b52783", "#b06c0b"),
        "ship": "#213e73", "ship_core": "#1380b8", "laser": "#08856b",
        "hostile": "#c33137", "spark": "#f79228", "line": "#c5d1e5",
    },
}

# Original nine-pixel-wide silhouettes, independent of game ROMs and image assets.
ALIENS = (
    ("..#...#..", "...###...", ".#######.", "##.###.##",
     "#########", "#.#####.#", "..#...#.."),
    ("...###...", "..#####..", ".#######.", "##.###.##",
     "#########", "..#.#.#..", ".#.....#."),
    (".#.....#.", ".##...##.", "#########", "###.#.###",
     "#########", ".#.###.#.", "#.......#"),
    ("..##.##..", ".#######.", "#########", "##..#..##",
     "#########", ".##.#.##.", "..#...#.."),
)
# Alternating original sprite poses, sharing the same nine-by-seven footprint.
ALIENS_ALT = (
    ("..#...#..", "...###...", ".#######.", "##.###.##",
     "#########", "..#####..", ".#.....#."),
    ("...###...", "..#####..", ".#######.", "##.###.##",
     "#########", ".#..#..#.", "..#...#.."),
    (".#.....#.", ".##...##.", "#########", "###.#.###",
     "#########", "..#####..", ".#..#..#."),
    ("..##.##..", ".#######.", "#########", "##..#..##",
     "#########", "..#.#.#..", ".#.....#."),
)
SHIP = (
    ".......#.......", "......###......", "......###......",
    "....#######....", "..###########..", "###############",
    "###..#####..###", ".##.......##...",
)


@dataclass(frozen=True)
class Shot:
    day: Day
    launch: float
    hit: float


@dataclass(frozen=True)
class Volley:
    origin: float
    base: float
    dodge: float
    shift: float
    start: float
    arrive: float
    enemy_launch: float
    enemy_hit: float
    dodge_start: float
    dodge_end: float
    settle: float
    shots: tuple[Shot, ...]
    end: float
    damaged: bool


@dataclass(frozen=True)
class March:
    time: float
    x: int
    y: int
    frame: int
    alive: int


@dataclass(frozen=True)
class Battle:
    home: float
    volleys: tuple[Volley, ...]
    restore: float
    cycle: float
    march: tuple[March, ...]


def center(day: Day) -> tuple[float, float]:
    return LEFT + day.week * STEP + CELL / 2, TOP + day.weekday * STEP + CELL / 2


def _column_order(days: tuple[Day, ...]) -> tuple[int, ...]:
    """Alternate edges of local sectors rather than crossing the whole board."""
    columns = sorted({day.week for day in days if day.count})
    order = []
    for offset in range(0, len(columns), 8):
        sector = columns[offset:offset+8]
        left, right = 0, len(sector)-1
        take_left = (offset // 8) % 2 == 0
        while left <= right:
            if take_left:
                order.append(sector[left])
                left += 1
            else:
                order.append(sector[right])
                right -= 1
            take_left = not take_left
    return tuple(order)


def _ordered_active_days(days: tuple[Day, ...]) -> tuple[Day, ...]:
    order = {week: i for i, week in enumerate(_column_order(days))}
    return tuple(sorted((d for d in days if d.count),
                        key=lambda d: (order[d.week], -d.weekday)))


def _attack_groups(days: tuple[Day, ...]) -> tuple[tuple[Day, ...], ...]:
    """Revisit columns in local rounds; never sweep a tall column at once."""
    active = _ordered_active_days(days)
    columns = {week: list(group) for week, group in groupby(active, key=lambda d: d.week)}
    order = list(columns)
    groups = []
    visited = set()
    for offset in range(0, len(order), 8):
        pending = order[offset:offset+8]
        round_index = 0
        while pending:
            # Equal bursts within a round keep equal-height columns balanced.
            # Rotate the order if a boundary would immediately repeat a column.
            if len(pending) > 1 and groups and groups[-1][0].week == pending[0]:
                pending = pending[1:] + pending[:1]
            for week in pending:
                column = columns[week]
                count = min(len(column), 1 + (round_index % 2), MAX_BURST)
                if len(column) > 1 and week not in visited:
                    count = min(count, len(column)-1)
                groups.append(tuple(column[:count]))
                del column[:count]
                visited.add(week)
            pending = [week for week in pending if columns[week]]
            round_index += 1
    return tuple(groups)


def march_interval(alive: int, initial: int) -> float:
    """Scale the original 55-alien/60-Hz cadence to a variable calendar."""
    return max(MIN_MARCH_INTERVAL, ARCADE_ALIENS/ARCADE_HZ * alive/max(1, initial))


def plan_march(shots: tuple[Shot, ...]) -> tuple[March, ...]:
    """March independently of the hero: discrete steps, edge turns and acceleration."""
    if not shots:
        return ()
    hits = sorted(shot.hit for shot in shots)
    initial = len(hits)
    steps = [March(0.0, 0, 0, 0, initial)]
    x = y = frame = 0
    direction = 1
    time = march_interval(initial, initial)
    while time < hits[-1]:
        alive = initial-bisect_right(hits, time)
        if x+direction*MARCH_STEP > MARCH_LIMIT or x+direction*MARCH_STEP < -MARCH_LIMIT:
            direction *= -1
            if y < DROP_LIMIT:
                y = min(DROP_LIMIT, y+DROP_STEP)
            else:
                x += direction*MARCH_STEP
        else:
            x += direction*MARCH_STEP
        frame = 1-frame
        steps.append(March(time, x, y, frame, alive))
        time += march_interval(alive, initial)
    return tuple(steps)


def march_at(march: tuple[March, ...], time: float) -> March:
    index = bisect_right(march, time, key=lambda step: step.time)-1
    return march[max(0, index)]


def plan_battle(days: tuple[Day, ...]) -> Battle | None:
    """Plan short attacks, mostly successful evasions and occasional damage."""
    groups = _attack_groups(days)
    if not groups:
        return None
    home = center(groups[0][0])[0]
    previous, start = home, FIRST
    volleys = []
    width = calendar_width(LEFT, STEP, CELL, RIGHT, board_weeks(days))
    for i, column in enumerate(groups):
        shift = 0.0
        base = center(column[0])[0]
        damaged = (i+1) % DAMAGE_INTERVAL == 0
        direction = 1 if i % 2 == 0 else -1
        if not 8 <= base + direction*DODGE <= width-8:
            direction = -direction
        dodge = base if damaged else base + direction*DODGE
        # Reserve room for the formation's horizontal march while approaching.
        arrive = start + max(.12, (abs(base - previous)+2*MARCH_LIMIT) / 255)
        enemy_launch = arrive + .035
        distance = SHIP_Y - center(column[0])[1]
        enemy_hit = enemy_launch + max(.27, distance / 280)
        dodge_start, dodge_end = arrive + .055, arrive + .22
        settle = enemy_hit + (.24 if damaged else .14)
        shots = []
        for j, day in enumerate(column):
            launch = settle + .025 + j * .18
            distance = SHIP_Y - 6 - center(day)[1]
            hit = launch + distance / 320
            shots.append(Shot(day, launch, hit))
        end = shots[-1].hit + .15
        volleys.append(Volley(previous, base, dodge, shift, start, arrive,
                              enemy_launch, enemy_hit, dodge_start, dodge_end,
                              settle, tuple(shots), end, damaged))
        previous, start = base, end + .035
    march = plan_march(tuple(shot for volley in volleys for shot in volley.shots))
    # Align the ship with the formation at arrival; every shot uses the actual
    # launch or impact coordinates from the same clock, even between steps.
    adjusted = []
    previous = home
    for i, volley in enumerate(volleys):
        shift = march_at(march, volley.arrive).x
        base = center(volley.shots[0].day)[0] + shift
        direction = 1 if i % 2 == 0 else -1
        if not 8 <= base+direction*DODGE <= width-8:
            direction = -direction
        dodge = base if volley.damaged else base+direction*DODGE
        adjusted.append(replace(volley, origin=previous, base=base,
                                dodge=dodge, shift=shift))
        previous = base
    restore = adjusted[-1].end + max(.3, abs(previous-home)/255)
    return Battle(home, tuple(adjusted), restore, max(4.0, restore+.55), march)


def _pixels(rows, x, y):
    """Encode each horizontal pixel run as a compact path."""
    segments = []
    for row, data in enumerate(rows):
        for value, group in groupby(enumerate(data), key=lambda item: item[1]):
            run = list(group)
            if value == "#":
                segments.append(f"M{x+run[0][0]} {y+row}h{len(run)}v1h-{len(run)}Z")
    return "".join(segments)


def _xy(x, y):
    return f"{x:.3f} {y:.3f}"


def _ship(battle, p):
    positions, times = [_xy(battle.home, SHIP_Y)], [0.0]
    flash, flash_times = [0], [0.0]
    damage, damage_times = [1], [0.0]
    for volley in battle.volleys:
        positions.extend(_xy(x, SHIP_Y) for x in (
            volley.origin, volley.base, volley.base, volley.dodge,
            volley.dodge, volley.base, volley.base,
        ))
        times.extend((volley.start, volley.arrive, volley.dodge_start, volley.dodge_end,
                      volley.enemy_hit+.035, volley.settle, volley.end))
        if volley.damaged:
            damage.extend((1, .25, 1, .35, 1))
            damage_times.extend((volley.enemy_hit-.01, volley.enemy_hit,
                                 volley.enemy_hit+.05, volley.enemy_hit+.10,
                                 volley.enemy_hit+.19))
        for shot in volley.shots:
            flash.extend((0, 1, 0))
            flash_times.extend((shot.launch-.012, shot.launch, shot.launch+.06))
    positions.append(_xy(battle.home, SHIP_Y))
    times.append(battle.restore)
    return [
        f'<g data-ship="hero" transform="translate({battle.home} {SHIP_Y})">',
        track("transform", positions, times, battle.cycle, transform=True),
        '<g data-ship-body="true">',
        *([track("opacity", damage, damage_times, battle.cycle)]
          if len(damage) > 1 else []),
        f'<path d="{_pixels(SHIP, -7, -4)}" fill="{p["ship"]}"/>',
        f'<path d="M-1 -1h3v4h-3Z" fill="{p["ship_core"]}"/>',
        f'<path d="M-1 -5h3v-3h-3Z" fill="{p["laser"]}" opacity="0">',
        track("opacity", flash, flash_times, battle.cycle),
        '</path></g></g>',
    ]


def _formation(battle, p):
    times = [step.time for step in battle.march] + [battle.restore]
    shifts = [_xy(step.x, step.y) for step in battle.march] + ["0 0"]
    frames = [step.frame for step in battle.march] + [0]
    # Define four shared sprites; the two walking poses use the same march clock.
    parts = ['<defs>']
    for i, rows in enumerate(ALIENS):
        poses = (_pixels(rows, -4, -3), _pixels(ALIENS_ALT[i], -4, -3))
        parts.extend([
            f'<g id="invader-sprite-{i+1}">',
            f'<path d="{poses[0]}" fill="{p["aliens"][i]}">',
            track("opacity", [1-frame for frame in frames], times, battle.cycle, "discrete"),
            '</path>',
            f'<path d="{poses[1]}" fill="{p["aliens"][i]}" opacity="0">',
            track("opacity", frames, times, battle.cycle, "discrete"),
            '</path></g>',
        ])
    parts.extend([
        '</defs>', '<g id="invaders" shape-rendering="crispEdges">',
        track("transform", shifts, times, battle.cycle, "discrete", transform=True),
    ])
    for volley in battle.volleys:
        for shot in volley.shots:
            day = shot.day
            x, y = center(day)
            variant = contribution_level(day)
            parts.extend([
                f'<g data-invader="{day.date.isoformat()}" data-level="{variant}" '
                f'transform="translate({x} {y})" opacity="1">',
                track("opacity", [1, 0, 1], [0, shot.hit, battle.restore],
                      battle.cycle, "discrete"),
                f'<use href="#invader-sprite-{variant}" xlink:href="#invader-sprite-{variant}"/>',
                '</g>',
            ])
    parts.append('</g>')
    return parts


def _laser(origin, target, launch, hit, cycle, color, side):
    x, y = origin
    tx, ty = target
    direction = -1 if ty < y else 1
    return [
        f'<g data-laser="{side}" transform="translate({x} {y})" opacity="0">',
        track("opacity", [0, 1, 1, 0], [launch-.01, launch, hit-.01, hit], cycle),
        track("transform", [_xy(x, y), _xy(tx, ty)],
              [launch, hit], cycle, transform=True),
        f'<path d="M0 0V{-direction*5}" stroke="{color}" stroke-width="1.5" '
        'stroke-linecap="square"/>',
        '</g>',
    ]


def _burst(x, y, hit, cycle, color, spark, kind="alien"):
    parts = [
        f'<g data-impact="true" data-hit-kind="{kind}" '
        f'transform="translate({x} {y})" opacity="0">',
        track("opacity", [0, 1, .7, 0], [hit-.01, hit, hit+.045, hit+.12], cycle),
        f'<path d="M-1 -5h2v4h4v2h-4v4h-2v-4h-4v-2h4Z" fill="{color}"/>',
        f'<path d="M-2 -2h4v4h-4Z" fill="{spark}"/>',
        '</g>',
    ]
    return parts


def alien_position(day, march, time):
    x, y = center(day)
    step = march_at(march, time)
    return x+step.x, y+step.y


def _combat(battle, p):
    parts = ['<g id="lasers">']
    for volley in battle.volleys:
        x, y = alien_position(volley.shots[0].day, battle.march, volley.enemy_launch)
        target_y = SHIP_Y if volley.damaged else SHIP_Y+6
        parts.extend(_laser((x, y+3), (volley.base, target_y),
                            volley.enemy_launch, volley.enemy_hit,
                            battle.cycle, p["hostile"], "enemy"))
        parts.extend(_burst(volley.base, target_y, volley.enemy_hit, battle.cycle,
                            p["hostile"], p["spark"], "ship" if volley.damaged else "miss"))
        for shot in volley.shots:
            x, y = alien_position(shot.day, battle.march, shot.hit)
            parts.extend(_laser((volley.base, SHIP_Y-6), (x, y), shot.launch, shot.hit,
                                battle.cycle, p["laser"], "hero"))
            parts.extend(_burst(x, y, shot.hit, battle.cycle,
                                p["aliens"][contribution_level(shot.day)-1], p["spark"]))
    parts.append('</g>')
    return parts


def render_invaders(
    days: tuple[Day, ...], theme: str = "dark", *, signature: bool = False,
) -> str:
    p = PALETTES[theme]
    weeks = board_weeks(days)
    width, height = calendar_width(LEFT, STEP, CELL, RIGHT, weeks), SHIP_Y + 14
    height += SIGNATURE_HEIGHT if signature else 0
    battle = plan_battle(days)
    by_day = {s.day: s for v in battle.volleys for s in v.shots} if battle else {}
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        'aria-label="GitInvaders pixel-art contribution battle">',
        '<title>GitInvaders — defend your contributions</title>',
        f'<rect width="{width}" height="{height}" rx="6" fill="{p["bg"]}"/>',
    ]
    parts.extend(render_labels(days, width, CELL, p["text"]))
    parts.append('<g id="calendar">')
    parts.extend(render_padding(days, CELL, p["empty"]))
    for day in sorted(days, key=lambda d: (d.week, d.weekday)):
        x, y = LEFT + day.week*STEP, TOP + day.weekday*STEP
        intensity = contribution_level(day)
        color = p["tiles"][intensity-1] if intensity else p["empty"]
        parts.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="1" '
                     f'fill="{color}" data-date="{day.date.isoformat()}" '
                     f'data-level="{intensity}">')
        parts.append(f'<title>{day.date.isoformat()}: {day.count} contributions</title>')
        if battle and day in by_day:
            parts.append(track("fill", [color, p["empty"], color],
                               [0, by_day[day].hit, battle.restore],
                               battle.cycle, "discrete"))
        parts.append('</rect>')
    parts.extend([
        '</g>',
        f'<path d="M{LEFT-5} {SHIP_Y+7}H{width-12}" stroke="{p["line"]}" '
        'stroke-width="1" stroke-dasharray="3 4"/>',
    ])
    if battle:
        parts.extend(_formation(battle, p))
        parts.extend(_combat(battle, p))
        parts.extend(_ship(battle, p))
    parts.extend([
        *render_signature(width, height, p["text"], signature),
        '</svg>',
    ])
    return "\n".join(parts) + "\n"
