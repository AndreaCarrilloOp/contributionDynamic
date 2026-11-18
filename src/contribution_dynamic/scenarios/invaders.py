"""GitInvaders: a single pixel-art ship against the contribution formation."""

from dataclasses import dataclass
from itertools import groupby

from contribution_dynamic.animation import track
from contribution_dynamic.calendar import Day, board_weeks, contribution_level
from contribution_dynamic.labels import LEFT, RIGHT, STEP, TOP, render_labels

CELL = 10
SHIP_Y = TOP + 7 * STEP + 17
FIRST = .12
SWAY = 2.5
DODGE = 11
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


@dataclass(frozen=True)
class Battle:
    home: float
    volleys: tuple[Volley, ...]
    restore: float
    cycle: float


def center(day: Day) -> tuple[float, float]:
    return LEFT + day.week * STEP + CELL / 2, TOP + day.weekday * STEP + CELL / 2


def plan_battle(days: tuple[Day, ...]) -> Battle | None:
    """Fire bottom-to-top so a living invader never blocks a later shot."""
    active = sorted((d for d in days if d.count), key=lambda d: (d.week, -d.weekday))
    if not active:
        return None
    home = center(active[0])[0]
    previous, start = home, FIRST
    volleys = []
    cadence = .115 if len(active) > 100 else .19
    for i, (_, group) in enumerate(groupby(active, key=lambda d: d.week)):
        column = tuple(group)
        shift = SWAY if i % 2 == 0 else -SWAY
        base = center(column[0])[0] + shift
        # At the right edge evade to the left; the ship remains inside the SVG.
        dodge = base + DODGE if base + DODGE < LEFT + board_weeks(days)*STEP else base-DODGE
        arrive = start + max(.14, abs(base - previous) / 230)
        enemy_launch = arrive + .04
        distance = SHIP_Y - center(column[0])[1]
        enemy_hit = enemy_launch + max(.24, distance / 280)
        dodge_start, dodge_end = arrive + .06, arrive + .21
        settle = enemy_hit + .16
        shots = []
        for j, day in enumerate(column):
            launch = settle + .025 + j * cadence
            distance = SHIP_Y - 6 - center(day)[1]
            hit = launch + distance / 320
            shots.append(Shot(day, launch, hit))
        end = shots[-1].hit + .14
        volleys.append(Volley(previous, base, dodge, shift, start, arrive,
                              enemy_launch, enemy_hit, dodge_start, dodge_end,
                              settle, tuple(shots), end))
        previous, start = base, end + .035
    restore = volleys[-1].end + max(.3, abs(previous - home) / 230)
    return Battle(home, tuple(volleys), restore, max(4.0, restore + .55))


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
    for volley in battle.volleys:
        positions.extend(_xy(x, SHIP_Y) for x in (
            volley.origin, volley.base, volley.base, volley.dodge,
            volley.dodge, volley.base, volley.base,
        ))
        times.extend((volley.start, volley.arrive, volley.dodge_start, volley.dodge_end,
                      volley.enemy_hit+.035, volley.settle, volley.end))
        for shot in volley.shots:
            flash.extend((0, 1, 0))
            flash_times.extend((shot.launch-.012, shot.launch, shot.launch+.06))
    positions.append(_xy(battle.home, SHIP_Y))
    times.append(battle.restore)
    return [
        f'<g data-ship="hero" transform="translate({battle.home} {SHIP_Y})">',
        track("transform", positions, times, battle.cycle, transform=True),
        f'<path d="{_pixels(SHIP, -7, -4)}" fill="{p["ship"]}"/>',
        f'<path d="M-1 -1h3v4h-3Z" fill="{p["ship_core"]}"/>',
        f'<path d="M-1 -5h3v-3h-3Z" fill="{p["laser"]}" opacity="0">',
        track("opacity", flash, flash_times, battle.cycle),
        '</path></g>',
    ]


def _formation(battle, p):
    shifts, times = ["0 0"], [0.0]
    previous = 0.0
    for volley in battle.volleys:
        shifts.extend((f"{previous} 0", f"{volley.shift} 0", f"{volley.shift} 0"))
        times.extend((volley.start, volley.arrive, volley.end))
        previous = volley.shift
    shifts.append("0 0")
    times.append(battle.restore)
    parts = [
        '<g id="invaders" shape-rendering="crispEdges">',
        track("transform", shifts, times, battle.cycle, transform=True),
    ]
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
                f'<path d="{_pixels(ALIENS[variant-1], -4, -3)}" '
                f'fill="{p["aliens"][variant-1]}"/>',
                '</g>',
            ])
    parts.append('</g>')
    return parts


def _laser(x, origin, target, launch, hit, cycle, color, side):
    direction = -1 if target < origin else 1
    return [
        f'<g data-laser="{side}" transform="translate({x} {origin})" opacity="0">',
        track("opacity", [0, 1, 1, 0], [launch-.01, launch, hit-.01, hit], cycle),
        track("transform", [_xy(x, origin), _xy(x, target)],
              [launch, hit], cycle, transform=True),
        f'<path d="M0 0V{-direction*5}" stroke="{color}" stroke-width="1.5" '
        'stroke-linecap="square"/>',
        '</g>',
    ]


def _burst(x, y, hit, cycle, color, spark):
    parts = [
        f'<g data-impact="true" transform="translate({x} {y})" opacity="0">',
        track("opacity", [0, 1, .7, 0], [hit-.01, hit, hit+.045, hit+.12], cycle),
        f'<path d="M-1 -5h2v4h4v2h-4v4h-2v-4h-4v-2h4Z" fill="{color}"/>',
        f'<path d="M-2 -2h4v4h-4Z" fill="{spark}"/>',
        '</g>',
    ]
    return parts


def _combat(battle, p):
    parts = ['<g id="lasers">']
    for volley in battle.volleys:
        _, enemy_y = center(volley.shots[0].day)
        parts.extend(_laser(volley.base, enemy_y+3, SHIP_Y, volley.enemy_launch,
                            volley.enemy_hit, battle.cycle, p["hostile"], "enemy"))
        parts.extend(_burst(volley.base, SHIP_Y, volley.enemy_hit, battle.cycle,
                            p["hostile"], p["spark"]))
        for shot in volley.shots:
            _, y = center(shot.day)
            parts.extend(_laser(volley.base, SHIP_Y-6, y, shot.launch, shot.hit,
                                battle.cycle, p["laser"], "hero"))
            parts.extend(_burst(volley.base, y, shot.hit, battle.cycle,
                                p["aliens"][contribution_level(shot.day)-1], p["spark"]))
    parts.append('</g>')
    return parts


def render_invaders(days: tuple[Day, ...], theme: str = "dark") -> str:
    p = PALETTES[theme]
    weeks = board_weeks(days)
    width, height = LEFT + weeks * STEP + RIGHT, SHIP_Y + 23
    battle = plan_battle(days)
    by_day = {s.day: s for v in battle.volleys for s in v.shots} if battle else {}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        'aria-label="GitInvaders pixel-art contribution battle">',
        '<title>GitInvaders — defend your contributions</title>',
        f'<rect width="{width}" height="{height}" rx="6" fill="{p["bg"]}"/>',
    ]
    parts.extend(render_labels(days, width, CELL, p["text"]))
    parts.append('<g id="calendar">')
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
        f'<text x="{LEFT}" y="{height-5}" fill="{p["text"]}" font-size="8" '
        'letter-spacing="1.4" font-family="monospace">GITINVADERS</text>',
        '</svg>',
    ])
    return "\n".join(parts) + "\n"
