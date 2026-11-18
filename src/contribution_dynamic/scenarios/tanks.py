"""GitTanks: one hero against waves of contribution-powered enemy tanks."""

from dataclasses import dataclass
from math import atan2, cos, degrees, hypot, radians, sin

from contribution_dynamic.animation import track
from contribution_dynamic.calendar import Day

STEP = 13
CELL = 10
LEFT = 47
TOP = 30
ROAD = TOP + 7 * STEP + 15
FIRST = .12
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
PALETTES = {
    "dark": {
        "bg": "#111b1a", "road": "#263832", "line": "#476456",
        "empty": "#23332e", "text": "#a2b5a7",
        "tiles": ("#354c39", "#526d45", "#779359", "#a3bd70"),
        "hero": "#2fb894", "hero_top": "#85ead1", "hero_edge": "#123f38",
        "enemy": "#b65343", "enemy_top": "#f2a18b", "enemy_edge": "#592d2e",
        "tracks": "#141d1b", "metal": "#dce4ce",
        "fire": "#ff9d43", "core": "#fff0a3", "return": "#fd7a72",
    },
    "light": {
        "bg": "#f8f6eb", "road": "#d7e1d1", "line": "#9eae93",
        "empty": "#e7ebdd", "text": "#465a47",
        "tiles": ("#c5d5ae", "#a4bc88", "#809b5c", "#52733e"),
        "hero": "#087b68", "hero_top": "#5ad7bf", "hero_edge": "#174b43",
        "enemy": "#af4334", "enemy_top": "#e78673", "enemy_edge": "#712f29",
        "tracks": "#303a32", "metal": "#edf2d8",
        "fire": "#e96c22", "core": "#ffe08a", "return": "#c73737",
    },
}
Point = tuple[float, float]


@dataclass(frozen=True)
class Duel:
    day: Day
    return_launch: float
    return_hit: float
    launch: float
    hit: float


@dataclass(frozen=True)
class Wave:
    origin: float
    base: float
    dodge: float
    start: float
    arrive: float
    dodge_start: float
    dodge_end: float
    restore: float
    duels: tuple[Duel, ...]


def _level(day: Day) -> int:
    if not day.count:
        return 0
    return max(1, day.level) if day.level is not None else min(4, day.count.bit_length())


def board_weeks(days: tuple[Day, ...]) -> int:
    return max(53, max((d.week + 1 for d in days), default=0))


def _center(day: Day) -> Point:
    return LEFT + day.week * STEP + CELL / 2, TOP + day.weekday * STEP + CELL / 2


def _aim(origin: Point, target: Point) -> float:
    dx, dy = target[0] - origin[0], target[1] - origin[1]
    return round(degrees(atan2(dy, dx)), 3)


def _point(x: float, y: float) -> str:
    return f"{x:.3f} {y:.3f}"


def _muzzle(origin: Point, angle: float, length: float) -> Point:
    theta = radians(angle)
    return origin[0] + length * cos(theta), origin[1] + length * sin(theta)


def plan_waves(days: tuple[Day, ...]) -> tuple[Wave, ...]:
    """Schedule every active day once, with a single persistent hero."""
    active = sorted((d for d in days if d.count), key=lambda d: (d.week, d.weekday))
    if not active:
        return ()
    size = 6 if len(active) > 120 else 4
    lo = LEFT + 12
    hi = LEFT + (board_weeks(days) - 1) * STEP + CELL / 2 - 12
    waves = []
    previous = max(lo, min(hi, _center(active[0])[0]))
    start = FIRST
    for index in range(0, len(active), size):
        group = active[index:index + size]
        base = max(lo, min(hi, sum(_center(d)[0] for d in group) / len(group)))
        dodge = base + 18 if base + 18 <= hi else base - 18
        arrive = start + max(.18, abs(base - previous) / 180)
        dodge_start, dodge_end = arrive + .11, arrive + .40
        duels = []
        first_launch = arrive + .78 + (len(group) - 1) * .045
        for i, day in enumerate(group):
            return_launch = arrive + .10 + i * .045
            return_hit = arrive + .50 + i * .045
            launch = first_launch + i * .25
            x, y = _center(day)
            hit = launch + max(.18, hypot(x-dodge, y-ROAD) / 260)
            duels.append(Duel(day, return_launch, return_hit, launch, hit))
        restore = max(duel.hit for duel in duels) + .48
        waves.append(Wave(previous, base, dodge, start, arrive, dodge_start,
                          dodge_end, restore, tuple(duels)))
        previous, start = dodge, restore + .12
    return tuple(waves)


def _months(days):
    seen = set()
    last = -4
    for day in sorted(days, key=lambda d: d.date):
        month = (day.date.year, day.date.month)
        if month not in seen:
            seen.add(month)
            if day.week - last >= 3:
                yield day.week, MONTHS[day.date.month - 1]
                last = day.week


def _sprite(p, side, angle):
    """A compact original vector tank, facing right before turret rotation."""
    return [
        f'<rect x="-5.5" y="-4.5" width="11" height="9" rx="1.4" '
        f'fill="{p["tracks"]}" stroke="{p[f"{side}_edge"]}" stroke-width=".6"/>',
        f'<path d="M-4 -3.5H4M-4 3.5H4" stroke="{p["metal"]}" '
        'stroke-width=".8" stroke-dasharray="1 1.5" opacity=".7"/>',
        f'<rect x="-4" y="-2.5" width="8" height="5" rx="1" fill="{p[side]}"/>',
        f'<g transform="rotate({angle})">',
        f'<rect x="0" y="-.8" width="7" height="1.6" rx=".4" '
        f'fill="{p[f"{side}_top"]}" stroke="{p[f"{side}_edge"]}" stroke-width=".35"/>',
        f'<circle r="2.65" fill="{p[f"{side}_top"]}" '
        f'stroke="{p[f"{side}_edge"]}" stroke-width=".5"/>',
        f'<circle r=".8" fill="{p[side]}"/>',
    ]


def _hero(waves, cycle, p):
    home = waves[0].origin
    positions, times = [_point(home, ROAD)], [0.0]
    angles, angle_times = [-90], [0.0]
    for wave in waves:
        positions.extend((_point(wave.origin, ROAD), _point(wave.base, ROAD),
                          _point(wave.base, ROAD), _point(wave.dodge, ROAD)))
        times.extend((wave.start, wave.arrive, wave.dodge_start, wave.dodge_end))
        for duel in wave.duels:
            angle = _aim((wave.dodge, ROAD), _center(duel.day))
            angles.extend((angle, angle))
            angle_times.extend((duel.launch-.09, duel.launch+.045))
    end = waves[-1].restore
    positions.extend((_point(waves[-1].dodge, ROAD), _point(home, ROAD)))
    times.extend((end, cycle-.3))
    angles.append(-90)
    angle_times.append(cycle-.3)
    parts = [
        f'<g data-tank="hero" transform="translate({home} {ROAD})">',
        track("transform", positions, times, cycle, transform=True),
        '<g transform="scale(1.5)">',
        *_sprite(p, "hero", -90),
        track("transform", angles, angle_times, cycle,
              transform=True).replace('type="translate"', 'type="rotate"'),
        '</g></g></g>',
    ]
    return parts


def _missile(origin, target, launch, hit, cycle, color, core, angle, length):
    start = _muzzle(origin, angle, length)
    x, y = start
    return [
        f'<g transform="translate({x:.3f} {y:.3f})" opacity="0">',
        track("opacity", [0, 1, 1, 0], [launch-.01, launch, hit-.01, hit], cycle),
        track("transform", [_point(*start), _point(*target)], [launch, hit], cycle,
              transform=True),
        f'<g transform="rotate({angle})">',
        f'<path d="M-4 0H0" stroke="{color}" stroke-width="1.35" '
        'stroke-linecap="round"/>',
        f'<circle r="1.35" fill="{core}"/>',
        '</g></g>',
    ]


def _enemy(duel, wave, cycle, p):
    x, y = _center(duel.day)
    angle = _aim((x, y), (wave.base, ROAD))
    return [
        f'<g data-tank="enemy" data-enemy="{duel.day.date.isoformat()}" '
        f'transform="translate({x} {y})" opacity="0">',
        track("opacity", [0, 1, 1, 0],
              [wave.start, wave.start+.12, duel.hit-.015, duel.hit], cycle),
        *_sprite(p, "enemy", angle),
        '</g></g>',
    ]


def _combat(duel, wave, cycle, p):
    enemy = _center(duel.day)
    hero = (wave.dodge, ROAD)
    missed = (wave.base, ROAD)
    angle = _aim(hero, enemy)
    counter_angle = _aim(enemy, missed)
    x, y = enemy
    hit = duel.hit
    parts = [
        f'<g data-shot="{duel.day.date.isoformat()}">',
        '<g data-projectile="enemy">',
        *_missile(enemy, missed, duel.return_launch, duel.return_hit, cycle,
                  p["return"], p["core"], counter_angle, 7),
        '</g>',
        '<g data-projectile="hero">',
        *_missile(hero, enemy, duel.launch, hit, cycle,
                  p["fire"], p["core"], angle, 10.5),
        '</g>',
        f'<g transform="translate({x} {y})" opacity="0" data-impact="true">',
        track("opacity", [0, 1, .65, 0], [hit-.01, hit, hit+.09, hit+.27], cycle),
        f'<circle r="2" stroke="{p["fire"]}" stroke-width="1.55" fill="none">',
        track("r", [2, 5+_level(duel.day)], [hit, hit+.27], cycle),
        '</circle>',
        f'<path d="M-4 0L0 -4L4 0L0 4Z" fill="{p["core"]}"/>',
        '</g>',
        f'<circle cx="{missed[0]}" cy="{ROAD}" r="2" fill="none" '
        f'stroke="{p["return"]}" stroke-width="1" opacity="0">',
        track("opacity", [0, .75, 0],
              [duel.return_hit-.01, duel.return_hit, duel.return_hit+.16], cycle),
        track("r", [2, 6], [duel.return_hit, duel.return_hit+.16], cycle),
        '</circle></g>',
    ]
    return parts


def render_tanks(days: tuple[Day, ...], theme: str = "dark") -> str:
    p = PALETTES[theme]
    weeks = board_weeks(days)
    width, height = LEFT + weeks * STEP + 16, ROAD + 22
    waves = plan_waves(days)
    cycle = 4.0
    if waves:
        travel = abs(waves[-1].dodge - waves[0].origin) / 180
        cycle = max(cycle, waves[-1].restore + max(.45, travel) + .3)
    by_day = {d.day: (d, w) for w in waves for d in w.duels}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        'aria-label="GitTanks one versus many contribution battle">',
        '<title>GitTanks — one hero against the invasion</title>',
        f'<rect width="{width}" height="{height}" rx="6" fill="{p["bg"]}"/>',
        f'<g font-family="system-ui,sans-serif" font-size="10" fill="{p["text"]}">',
    ]
    for week, label in _months(days):
        parts.append(f'<text x="{LEFT+week*STEP}" y="14">{label}</text>')
    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(f'<text x="10" y="{TOP+row*STEP+8}">{label}</text>')
    parts.extend([
        '</g>',
        f'<rect x="{LEFT-4}" y="{ROAD-10}" width="{weeks*STEP+4}" height="20" '
        f'rx="4" fill="{p["road"]}"/>',
        f'<path d="M{LEFT} {ROAD}H{LEFT+weeks*STEP-4}" stroke="{p["line"]}" '
        'stroke-width="1" stroke-dasharray="3 5"/>',
        '<g id="calendar">',
    ])
    for day in sorted(days, key=lambda d: (d.week, d.weekday)):
        x, y = LEFT + day.week*STEP, TOP + day.weekday*STEP
        level = _level(day)
        color = p["tiles"][level-1] if level else p["empty"]
        parts.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="1" '
                     f'fill="{color}" data-date="{day.date.isoformat()}" data-level="{level}">')
        parts.append(f'<title>{day.date.isoformat()}: {day.count} contributions</title>')
        if day in by_day:
            duel, wave = by_day[day]
            parts.append(track("fill", [color, p["empty"], color],
                               [0, duel.hit, wave.restore], cycle, "discrete"))
        parts.append('</rect>')
    parts.extend(['</g>', '<g id="enemies">'])
    for wave in waves:
        for duel in wave.duels:
            parts.extend(_enemy(duel, wave, cycle, p))
    parts.extend(['</g>', '<g id="combat">'])
    for wave in waves:
        for duel in wave.duels:
            parts.extend(_combat(duel, wave, cycle, p))
    parts.extend(['</g>', '<g id="hero">'])
    if waves:
        parts.extend(_hero(waves, cycle, p))
    parts.extend([
        '</g>',
        f'<text x="{LEFT}" y="{height-4}" fill="{p["text"]}" font-size="8" '
        'letter-spacing="1.2" font-family="system-ui,sans-serif">GITTANKS · ONE VS MANY</text>',
        '</svg>',
    ])
    return "\n".join(parts) + "\n"
