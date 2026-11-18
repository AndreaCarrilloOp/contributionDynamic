"""GitTanks: defend an eagle base against waves of arcade enemy tanks."""

from dataclasses import dataclass
from math import atan2, cos, degrees, radians, sin

from contribution_dynamic.animation import track
from contribution_dynamic.calendar import Day

STEP = 13
CELL = 10
LEFT = 47
TOP = 39
FIRST = .12
ASSAULT = TOP + 7 * STEP + 13
GUARD = ASSAULT + 23
BASE = GUARD + 21
MAX_ENEMIES = 4
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
PALETTES = {
    "dark": {
        "bg": "#080808", "empty": "#101010", "text": "#b7b3a6",
        "tiles": ("#99501e", "#bb621f", "#da7d27", "#f3a342"),
        "mortar": "#663819", "brick_light": "#ffd08a", "brick_shadow": "#633311",
        "hero": "#d9b21f", "hero_top": "#ffe16a", "hero_edge": "#59400a",
        "hero_shadow": "#95700c", "tracks": "#34332e", "metal": "#ccc3a1",
        "enemy": "#b9c2c8", "enemy_top": "#f2f5f5", "enemy_shadow": "#737e85",
        "enemy_edge": "#46515a", "shield": "#90c8e8",
        "fire": "#ff8624", "core": "#fff3b0",
    },
    "light": {
        "bg": "#faf6eb", "empty": "#eee8db", "text": "#675b48",
        "tiles": ("#f4c38d", "#dfa062", "#c87934", "#a95b22"),
        "mortar": "#805027", "brick_light": "#ffe2b0", "brick_shadow": "#783f1c",
        "hero": "#be8d10", "hero_top": "#ffe16a", "hero_edge": "#59400a",
        "hero_shadow": "#8c6008", "tracks": "#38372f", "metal": "#b8ac86",
        "enemy": "#7a8791", "enemy_top": "#cbd4d7", "enemy_shadow": "#4a5964",
        "enemy_edge": "#35424b", "shield": "#237fae",
        "fire": "#e76614", "core": "#fff1a1",
    },
}


Point = tuple[float, float]


@dataclass(frozen=True)
class Breach:
    day: Day
    origin: Point
    target: Point
    fire: float
    hit: float


@dataclass(frozen=True)
class Invader:
    week: int
    positions: tuple[Point, ...]
    times: tuple[float, ...]
    breaches: tuple[Breach, ...]
    station: Point
    attack: float
    shield_hit: float
    guard_x: float
    counter: float
    defeated: float


@dataclass(frozen=True)
class Wave:
    start: float
    ready: float
    restore: float
    enemies: tuple[Invader, ...]


def _level(day: Day) -> int:
    if not day.count:
        return 0
    return max(1, day.level) if day.level is not None else min(4, day.count.bit_length())


def board_weeks(days: tuple[Day, ...]) -> int:
    return max(53, max((d.week + 1 for d in days), default=0))


def base_x(days: tuple[Day, ...]) -> float:
    return LEFT + (board_weeks(days)-1)*STEP/2 + CELL/2


def _center(week: int, row: int) -> Point:
    return LEFT + week*STEP + CELL/2, TOP + row*STEP + CELL/2


def _position(point: Point) -> str:
    return f"{point[0]:.3f} {point[1]:.3f}"


def _angle(a: Point, b: Point) -> float:
    return degrees(atan2(b[1]-a[1], b[0]-a[0]))


def _toward(a: Point, b: Point, distance: float) -> Point:
    theta = radians(_angle(a, b))
    return a[0]+cos(theta)*distance, a[1]+sin(theta)*distance


def plan_waves(days: tuple[Day, ...]) -> tuple[Wave, ...]:
    """Send up to four enemies through active columns before attacking the base."""
    columns: dict[int, dict[int, Day]] = {}
    for day in sorted(days, key=lambda d: (d.week, d.weekday)):
        if day.count:
            columns.setdefault(day.week, {})[day.weekday] = day
    center = base_x(days)
    weeks = list(columns)
    waves = []
    start = FIRST
    for offset in range(0, len(weeks), MAX_ENEMIES):
        group = weeks[offset:offset+MAX_ENEMIES]
        routes = []
        for week in group:
            origin = _center(week, -1)
            positions, times = [origin, origin], [start, start+.12]
            breaches = []
            t = times[-1]
            for row in range(7):
                target = _center(week, row)
                day = columns[week].get(row)
                if day is not None:
                    fire, hit = t+.04, t+.20
                    breaches.append(Breach(day, positions[-1], target, fire, hit))
                    positions.append(positions[-1])
                    t = hit+.06
                    times.append(t)
                positions.append(target)
                t += .16
                times.append(t)
            positions.append((origin[0], ASSAULT))
            times.append(t+.20)
            routes.append((week, positions, times, breaches))
        gather = max(route[2][-1] for route in routes)+.14
        slots = [center+(i-(len(group)-1)/2)*31 for i in range(len(group))]
        travel = max(abs(slot-route[1][-1][0]) for slot, route in zip(slots, routes))
        ready = gather+max(.45, travel/185)
        enemies = []
        for i, ((week, positions, times, breaches), slot) in enumerate(zip(routes, slots)):
            station = (slot, ASSAULT)
            positions.extend((positions[-1], station))
            times.extend((gather, ready))
            duel = ready+.10+i*1.02
            guard_x = center+max(-28, min(28, (slot-center)*.56))
            enemies.append(Invader(
                week, tuple(positions), tuple(times), tuple(breaches), station,
                duel+.28, duel+.58, guard_x, duel+.70, duel+.92,
            ))
        restore = enemies[-1].defeated+.52
        waves.append(Wave(start, ready, restore, tuple(enemies)))
        start = restore+.28
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



def _tank_sprite(p: dict, side: str = "hero") -> list[str]:
    """An original pixel-inspired silhouette, facing right, with a seven-unit muzzle."""
    return [
        '<g data-sprite="retro-tank" shape-rendering="crispEdges">',
        # Dark track beds with bright, square tread links.
        f'<path d="M-5 -5H5V-2H-5ZM-5 2H5V5H-5Z" fill="{p["tracks"]}"/>',
        f'<path d="M-4.5 -4.5H4.5M-4.5 4.5H4.5" stroke="{p["metal"]}" '
        'stroke-width="1" stroke-dasharray="1.2 1.1"/>',
        f'<path d="M-4 -3H4V3H-4Z" fill="{p[f"{side}_shadow"]}" '
        f'stroke="{p[f"{side}_edge"]}" stroke-width="1"/>',
        f'<path d="M-3 -2.5H3V2H-3Z" fill="{p[side]}"/>',
        f'<path d="M-3 -2H2V-1H-3Z" fill="{p[f"{side}_top"]}" opacity=".8"/>',
        # Octagonal turret and a broad, beveled cannon. The tip matches _impact.
        f'<path d="M0 -1H7V1H0Z" fill="{p[f"{side}_top"]}" '
        f'stroke="{p[f"{side}_edge"]}" stroke-width=".55"/>',
        f'<path d="M-2 -3H1L3 -1V1L1 3H-2L-3 1V-1Z" '
        f'fill="{p[side]}" stroke="{p[f"{side}_edge"]}" stroke-width=".6"/>',
        f'<path d="M-2 -2H1L2 -1H-2Z" fill="{p[f"{side}_top"]}"/>',
        f'<rect x="-.8" y="-.8" width="1.6" height="1.6" fill="{p[f"{side}_shadow"]}"/>',
        '</g>',
    ]



def _projectile(origin, target, fire, hit, cycle, p, side):
    muzzle = _toward(origin, target, 7)
    return [
        f'<g data-projectile="{side}" opacity="0" transform="translate({_position(muzzle)})">',
        track("opacity", [0, 1, 1, 0], [fire-.01, fire, hit-.01, hit], cycle),
        track("transform", [_position(muzzle), _position(target)], [fire, hit],
              cycle, transform=True),
        f'<rect x="-1.2" y="-1.2" width="2.4" height="2.4" fill="{p["core"]}" '
        f'stroke="{p["fire"]}" stroke-width=".5"/>',
        '</g>',
    ]


def _explosion(point, hit, cycle, p, radius=7):
    end = hit+.24
    return [
        f'<g data-impact="true" opacity="0" transform="translate({_position(point)})">',
        track("opacity", [0, 1, .7, 0], [hit-.01, hit, hit+.08, end], cycle),
        f'<circle r="2" fill="none" stroke="{p["fire"]}" stroke-width="1.4">',
        track("r", [2, radius], [hit, end], cycle),
        '</circle>',
        f'<path d="M-4 0L0 -4L4 0L0 4Z" fill="{p["core"]}"/>',
        '<path d="M-5 -3l-2 -2M5 -3l2 -2M-4 4l-2 2M4 4l2 2" '
        f'stroke="{p["fire"]}" stroke-width="1.6"/>',
        '</g>',
    ]


def _invader(enemy, wave, center, cycle, p):
    pos, times = enemy.positions, enemy.times
    station = enemy.station
    lateral = 0 if station[0] >= pos[-2][0] else 180
    gather = times[-2]
    angle = _angle(station, (center, BASE))
    parts = [
        f'<g data-tank="enemy" data-column="{enemy.week}" opacity="0" '
        f'transform="translate({_position(pos[0])})">',
        track("opacity", [0, 1, 1, 0],
              [wave.start, wave.start+.10, enemy.defeated-.015, enemy.defeated], cycle),
        track("transform", [_position(pt) for pt in pos], times, cycle, transform=True),
        '<g transform="rotate(90)">',
        track("transform", [90, 90, lateral, lateral, angle],
              [wave.start, gather-.10, gather, wave.ready-.12, wave.ready], cycle,
              transform=True).replace('type="translate"', 'type="rotate"'),
        *_tank_sprite(p, "enemy"),
        '</g></g>',
    ]
    for breach in enemy.breaches:
        parts.append(f'<g data-shot="{breach.day.date.isoformat()}">')
        parts.extend(_projectile(breach.origin, breach.target, breach.fire,
                                 breach.hit, cycle, p, "enemy"))
        parts.extend(_explosion(breach.target, breach.hit, cycle, p,
                                5+_level(breach.day)))
        parts.append('</g>')
    shield_point = _toward((center, BASE), station, 12)
    parts.extend(_projectile(station, shield_point, enemy.attack,
                             enemy.shield_hit, cycle, p, "enemy"))
    parts.extend(_projectile((enemy.guard_x, GUARD), station, enemy.counter,
                             enemy.defeated, cycle, p, "hero"))
    parts.extend(_explosion(station, enemy.defeated, cycle, p))
    return parts


def _hero(waves, center, cycle, p):
    positions, times = [_position((center, GUARD))], [0.0]
    angles, angle_times = [-90.0], [0.0]
    current, angle = center, -90.0
    for wave in waves:
        for enemy in wave.enemies:
            start = enemy.attack-.28
            positions.extend((_position((current, GUARD)), _position((enemy.guard_x, GUARD))))
            times.extend((start, start+.22))
            target = _angle((enemy.guard_x, GUARD), enemy.station)
            next_angle = angle+(target-angle+180)%360-180
            angles.extend((angle, next_angle))
            angle_times.extend((start+.22, enemy.counter-.06))
            current, angle = enemy.guard_x, next_angle
        positions.extend((_position((current, GUARD)), _position((center, GUARD))))
        times.extend((wave.enemies[-1].defeated+.08, wave.restore))
        angles.extend((angle, -90.0))
        angle_times.extend((wave.enemies[-1].defeated+.08, wave.restore))
        current, angle = center, -90.0
    return [
        f'<g data-tank="hero" transform="translate({center} {GUARD})">',
        track("transform", positions, times, cycle, transform=True),
        '<g transform="rotate(-90)">',
        track("transform", angles, angle_times, cycle,
              transform=True).replace('type="translate"', 'type="rotate"'),
        *_tank_sprite(p),
        '</g></g>',
    ]


def _eagle(waves, center, cycle, p):
    parts = [
        f'<g data-base="eagle" transform="translate({center} {BASE})">',
        f'<rect x="-10" y="-9" width="20" height="18" rx="1" fill="{p["empty"]}" '
        f'stroke="{p["brick_shadow"]}" stroke-width="1.3"/>',
        '<g shape-rendering="crispEdges">',
        '<path d="M-8 -6H-5V-4H-3V-2H-1V-5H1V-6H4V-3H2V-2H4V-4'
        'H6V-6H8V-1H6V1H3V4H5V6H-5V4H-3V1H-6V-1H-8Z" '
        f'fill="{p["hero_top"]}" stroke="{p["hero_edge"]}" stroke-width=".6"/>',
        f'<rect x="1" y="-5" width="1" height="1" fill="{p["hero_edge"]}"/>',
        '</g>',
        f'<circle r="12" fill="none" stroke="{p["shield"]}" stroke-width="1.6" '
        'opacity="0" data-shield="true">',
    ]
    if waves:
        values, times = [0], [0.0]
        for wave in waves:
            for enemy in wave.enemies:
                t = enemy.shield_hit
                values.extend((0, 1, 0))
                times.extend((t-.02, t, t+.20))
        parts.append(track("opacity", values, times, cycle))
    parts.extend(('</circle>', '</g>'))
    return parts


def render_tanks(days: tuple[Day, ...], theme: str = "dark") -> str:
    p = PALETTES[theme]
    weeks, center = board_weeks(days), base_x(days)
    width, height = LEFT+weeks*STEP+16, BASE+23
    waves = plan_waves(days)
    cycle = max(4.0, waves[-1].restore+.5) if waves else 4.0
    by_day = {
        breach.day: (breach, wave)
        for wave in waves for enemy in wave.enemies for breach in enemy.breaches
    }
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        'aria-label="GitTanks golden defender protects the eagle base">',
        '<title>GitTanks — defend the eagle</title>',
        f'<rect width="{width}" height="{height}" rx="6" fill="{p["bg"]}"/>',
        f'<g font-family="system-ui,sans-serif" font-size="10" fill="{p["text"]}">',
    ]
    for week, label in _months(days):
        parts.append(f'<text x="{LEFT+week*STEP}" y="14">{label}</text>')
    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(f'<text x="10" y="{TOP+row*STEP+8}">{label}</text>')
    parts.extend(['</g>', '<g id="calendar">'])
    for day in sorted(days, key=lambda d: (d.week, d.weekday)):
        x, y = LEFT+day.week*STEP, TOP+day.weekday*STEP
        level = _level(day)
        color = p["tiles"][level-1] if level else p["empty"]
        parts.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="1" '
                     f'fill="{color}" data-date="{day.date.isoformat()}" data-level="{level}">')
        parts.append(f'<title>{day.date.isoformat()}: {day.count} contributions</title>')
        if day in by_day:
            breach, wave = by_day[day]
            parts.append(track("fill", [color, p["empty"], color],
                               [0, breach.hit, wave.restore], cycle, "discrete"))
        parts.append('</rect>')
    parts.extend(['</g>', '<g id="brick-detail">'])
    for day in sorted(by_day, key=lambda d: (d.week, d.weekday)):
        x, y = LEFT+day.week*STEP, TOP+day.weekday*STEP
        breach, wave = by_day[day]
        parts.append(f'<g data-brick="{day.date.isoformat()}" '
                     'shape-rendering="crispEdges" opacity="1">')
        parts.append(track("opacity", [1, 0, 1], [0, breach.hit, wave.restore],
                           cycle, "discrete"))
        # Three staggered courses, warm mortar, highlights and lower shadow.
        parts.append(f'<path d="M{x} {y+3.5}H{x+10}M{x} {y+7}H{x+10}'
                     f'M{x+5} {y}V{y+3.5}M{x+2.5} {y+3.5}V{y+7}'
                     f'M{x+7.5} {y+3.5}V{y+7}M{x+5} {y+7}V{y+10}" '
                     f'fill="none" stroke="{p["mortar"]}" stroke-width=".8"/>')
        parts.append(f'<path d="M{x+.5} {y+1}H{x+4.5}M{x+5.5} {y+1}H{x+9.5}'
                     f'M{x+.5} {y+4.5}H{x+2}M{x+3} {y+4.5}H{x+7}'
                     f'M{x+8} {y+4.5}H{x+9.5}M{x+.5} {y+8}H{x+4.5}'
                     f'M{x+5.5} {y+8}H{x+9.5}" stroke="{p["brick_light"]}" '
                     'stroke-width=".7" opacity=".66" fill="none"/>')
        parts.append(f'<path d="M{x} {y+9.5}H{x+10}" stroke="{p["brick_shadow"]}" '
                     'stroke-width="1" opacity=".6"/>')
        parts.append('</g>')
    parts.extend(['</g>', '<g id="combat">'])
    for wave in waves:
        for enemy in wave.enemies:
            parts.extend(_invader(enemy, wave, center, cycle, p))
    parts.extend(['</g>', '<g id="defense">', *_eagle(waves, center, cycle, p)])
    if waves:
        parts.extend(_hero(waves, center, cycle, p))
    parts.extend([
        '</g>',
        f'<text x="{LEFT}" y="{height-6}" fill="{p["text"]}" font-size="8" '
        'letter-spacing="1.2" font-family="system-ui,sans-serif">DEFEND THE EAGLE</text>',
        '</svg>',
    ])
    return "\n".join(parts) + "\n"
