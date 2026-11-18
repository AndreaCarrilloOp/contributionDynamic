"""GitTanks: a single arcade tank clears a path through contribution blocks."""

from dataclasses import dataclass

from contribution_dynamic.animation import track
from contribution_dynamic.calendar import Day

STEP = 13
CELL = 10
LEFT = 47
TOP = 30
FIRST = .12
TURN = .09
DIRECTIONS = ((1, 0), (0, 1), (-1, 0), (0, -1))
ANGLES = {(1, 0): 0, (0, 1): 90, (-1, 0): 180, (0, -1): -90}
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
PALETTES = {
    "dark": {
        "bg": "#080808", "empty": "#101010", "text": "#b7b3a6",
        "tiles": ("#99501e", "#bb621f", "#da7d27", "#f3a342"),
        "mortar": "#663819", "brick_light": "#ffd08a", "brick_shadow": "#633311",
        "hero": "#d9b21f", "hero_top": "#ffe16a", "hero_edge": "#59400a",
        "hero_shadow": "#95700c", "tracks": "#34332e", "metal": "#ccc3a1",
        "fire": "#ff8624", "core": "#fff3b0",
    },
    "light": {
        "bg": "#faf6eb", "empty": "#eee8db", "text": "#675b48",
        "tiles": ("#f4c38d", "#dfa062", "#c87934", "#a95b22"),
        "mortar": "#805027", "brick_light": "#ffe2b0", "brick_shadow": "#783f1c",
        "hero": "#be8d10", "hero_top": "#ffe16a", "hero_edge": "#59400a",
        "hero_shadow": "#8c6008", "tracks": "#38372f", "metal": "#b8ac86",
        "fire": "#e76614", "core": "#fff1a1",
    },
}

Square = tuple[int, int]


@dataclass(frozen=True)
class TankStep:
    origin: Square
    destination: Square
    start: float
    move_start: float
    end: float
    angle: int
    turn: float
    day: Day | None = None
    fire: float | None = None
    hit: float | None = None


def _level(day: Day) -> int:
    if not day.count:
        return 0
    return max(1, day.level) if day.level is not None else min(4, day.count.bit_length())


def board_weeks(days: tuple[Day, ...]) -> int:
    return max(53, max((d.week + 1 for d in days), default=0))


def _center(square: Square) -> tuple[float, float]:
    return LEFT + square[0] * STEP + CELL / 2, TOP + square[1] * STEP + CELL / 2


def _position(square: Square) -> str:
    x, y = _center(square)
    return f"{x:g} {y:g}"


def _distance(a: Square, b: Square) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _inside(square: Square, weeks: int) -> bool:
    return 0 <= square[0] < weeks and 0 <= square[1] < 7


def _spawn(blocks: dict[Square, Day], weeks: int) -> Square:
    """Prefer a vacant cell beside activity; only a full board needs an edge entry."""
    for x, y in sorted(blocks):
        for dx, dy in DIRECTIONS:
            neighbor = (x + dx, y + dy)
            if _inside(neighbor, weeks) and neighbor not in blocks:
                return neighbor
    return (-1, 0)


def _path(origin: Square, target: Square, vertical_first=False):
    """Yield adjacent orthogonal squares; never teleport across the board."""
    x, y = origin
    axes = (1, 0) if vertical_first else (0, 1)
    for axis in axes:
        if axis == 0:
            while x != target[0]:
                x += 1 if target[0] > x else -1
                yield (x, y)
        else:
            while y != target[1]:
                y += 1 if target[1] > y else -1
                yield (x, y)


def plan_tank_route(days: tuple[Day, ...]) -> tuple[TankStep, ...]:
    """Find nearby active blocks and clear every obstacle before entering its square."""
    blocks = {(d.week, d.weekday): d for d in days if d.count}
    if not blocks:
        return ()
    weeks = board_weeks(days)
    home = _spawn(blocks, weeks)
    density = len(blocks) / (weeks * 7)
    move_time = .10 if density > .5 else .17
    shot_time = .115 if density > .5 else .16
    steps = []
    current, now, previous_angle = home, FIRST, None

    def advance(destination: Square, returning=False):
        nonlocal current, now, previous_angle
        dx, dy = destination[0] - current[0], destination[1] - current[1]
        angle = ANGLES[(dx, dy)]
        turn = TURN if previous_angle is not None and angle != previous_angle else 0.0
        day = blocks.pop(destination, None)
        fire = now + turn + .025 if day is not None else None
        hit = fire + shot_time if fire is not None else None
        move_start = hit + .05 if hit is not None else now + turn
        duration = .075 if returning else move_time
        end = move_start + duration
        steps.append(TankStep(current, destination, now, move_start, end,
                              angle, turn, day, fire, hit))
        current, now, previous_angle = destination, end, angle

    while blocks:
        target = min(blocks, key=lambda pos: (_distance(current, pos), pos))
        # In the exceptional full-board case enter horizontally at row zero.
        for destination in _path(current, target):
            advance(destination)
    # All blocks remain cleared during the return; only the loop boundary resets them.
    for destination in _path(current, home, vertical_first=True):
        advance(destination, returning=True)
    return tuple(steps)


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


def _hero(steps, cycle, p):
    home = steps[0].origin
    positions, times = [_position(home)], [0.0]
    first_angle = steps[0].angle
    angle = first_angle
    angles, angle_times = [angle], [0.0]
    for step in steps:
        if step.move_start > times[-1]:
            positions.append(_position(step.origin))
            times.append(step.move_start)
        positions.append(_position(step.destination))
        times.append(step.end)
        if step.turn:
            if step.start > angle_times[-1]:
                angles.append(angle)
                angle_times.append(step.start)
            angle += (step.angle - angle + 180) % 360 - 180
            angles.append(angle)
            angle_times.append(step.start + step.turn)
    # Face the original direction before the cycle resets.
    end = steps[-1].end
    angles.extend((angle, angle + (first_angle-angle+180) % 360 - 180))
    angle_times.extend((end, end + TURN))
    return [
        f'<g data-tank="hero" transform="translate({_position(home)})">',
        track("transform", positions, times, cycle, transform=True),
        f'<g transform="rotate({first_angle})">',
        track("transform", angles, angle_times, cycle,
              transform=True).replace('type="translate"', 'type="rotate"'),
        *_tank_sprite(p),
        '</g></g>',
    ]


def _tank_sprite(p: dict) -> list[str]:
    """An original pixel-inspired silhouette, facing right, with a seven-unit muzzle."""
    return [
        '<g data-sprite="retro-tank" shape-rendering="crispEdges">',
        # Dark track beds with bright, square tread links.
        f'<path d="M-5 -5H5V-2H-5ZM-5 2H5V5H-5Z" fill="{p["tracks"]}"/>',
        f'<path d="M-4.5 -4.5H4.5M-4.5 4.5H4.5" stroke="{p["metal"]}" '
        'stroke-width="1" stroke-dasharray="1.2 1.1"/>',
        f'<path d="M-4 -3H4V3H-4Z" fill="{p["hero_shadow"]}" '
        f'stroke="{p["hero_edge"]}" stroke-width="1"/>',
        f'<path d="M-3 -2.5H3V2H-3Z" fill="{p["hero"]}"/>',
        f'<path d="M-3 -2H2V-1H-3Z" fill="{p["hero_top"]}" opacity=".8"/>',
        # Octagonal turret and a broad, beveled cannon. The tip matches _impact.
        f'<path d="M0 -1H7V1H0Z" fill="{p["hero_top"]}" '
        f'stroke="{p["hero_edge"]}" stroke-width=".55"/>',
        f'<path d="M-2 -3H1L3 -1V1L1 3H-2L-3 1V-1Z" '
        f'fill="{p["hero"]}" stroke="{p["hero_edge"]}" stroke-width=".6"/>',
        f'<path d="M-2 -2H1L2 -1H-2Z" fill="{p["hero_top"]}"/>',
        f'<rect x="-.8" y="-.8" width="1.6" height="1.6" fill="{p["hero_shadow"]}"/>',
        '</g>',
    ]


def _impact(step: TankStep, cycle: float, p: dict) -> list[str]:
    assert step.day is not None and step.fire is not None and step.hit is not None
    x, y = _center(step.destination)
    sx, sy = _center(step.origin)
    dx, dy = step.destination[0] - step.origin[0], step.destination[1] - step.origin[1]
    # Projectile starts at the cannon tip and stops at the struck block.
    muzzle = f"{sx+dx*7:g} {sy+dy*7:g}"
    target = f"{x:g} {y:g}"
    fire, hit = step.fire, step.hit
    fade = hit + .23
    return [
        f'<g data-shot="{step.day.date.isoformat()}">',
        f'<g opacity="0" transform="translate({muzzle})">',
        track("opacity", [0, 1, 1, 0], [fire-.01, fire, hit-.012, hit], cycle),
        track("transform", [muzzle, target], [fire, hit], cycle, transform=True),
        f'<circle r="1.45" fill="{p["core"]}" stroke="{p["fire"]}" stroke-width=".6"/>',
        '</g>',
        f'<g data-impact="true" opacity="0" transform="translate({target})">',
        track("opacity", [0, 1, .7, 0], [hit-.01, hit, hit+.08, fade], cycle),
        f'<circle r="2" stroke="{p["fire"]}" stroke-width="1.3" fill="none">',
        track("r", [2, 5+_level(step.day)], [hit, fade], cycle),
        '</circle>',
        f'<path d="M-4 0L0 -4L4 0L0 4Z" fill="{p["core"]}"/>',
        f'<path d="M-5 -3l-2 -2M5 -3l2 -2M-4 4l-2 2M4 4l2 2" '
        f'stroke="{p["fire"]}" stroke-width="1.6" stroke-linecap="round"/>',
        '</g></g>',
    ]


def render_tanks(days: tuple[Day, ...], theme: str = "dark") -> str:
    p = PALETTES[theme]
    weeks = board_weeks(days)
    width, height = LEFT + weeks * STEP + 16, TOP + 7 * STEP + 17
    steps = plan_tank_route(days)
    cycle = max(4.0, steps[-1].end + .6) if steps else 4.0
    by_day = {step.day: step for step in steps if step.day is not None}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        'aria-label="GitTanks arcade tank clears contribution blocks">',
        '<title>GitTanks — clear the battlefield</title>',
        f'<rect width="{width}" height="{height}" rx="6" fill="{p["bg"]}"/>',
        f'<g font-family="system-ui,sans-serif" font-size="10" fill="{p["text"]}">',
    ]
    for week, label in _months(days):
        parts.append(f'<text x="{LEFT+week*STEP}" y="14">{label}</text>')
    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(f'<text x="10" y="{TOP+row*STEP+8}">{label}</text>')
    parts.extend(['</g>', '<g id="calendar">'])
    for day in sorted(days, key=lambda d: (d.week, d.weekday)):
        x, y = LEFT + day.week*STEP, TOP + day.weekday*STEP
        level = _level(day)
        color = p["tiles"][level-1] if level else p["empty"]
        parts.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="1" '
                     f'fill="{color}" data-date="{day.date.isoformat()}" data-level="{level}">')
        parts.append(f'<title>{day.date.isoformat()}: {day.count} contributions</title>')
        if day in by_day:
            step = by_day[day]
            parts.append(track("fill", [color, p["empty"], color],
                               [0, step.hit, cycle], cycle, "discrete"))
        parts.append('</rect>')
    parts.extend(['</g>', '<g id="brick-detail">'])
    for day in sorted(by_day, key=lambda d: (d.week, d.weekday)):
        x, y = LEFT + day.week*STEP, TOP + day.weekday*STEP
        step = by_day[day]
        parts.append(f'<g data-brick="{day.date.isoformat()}" '
                     'shape-rendering="crispEdges" opacity="1">')
        parts.append(track("opacity", [1, 0, 1], [0, step.hit, cycle],
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
    for step in steps:
        if step.day is not None:
            parts.extend(_impact(step, cycle, p))
    parts.extend(['</g>', '<g id="hero">'])
    if steps:
        parts.extend(_hero(steps, cycle, p))
    parts.extend([
        '</g>',
        f'<text x="{LEFT}" y="{height-6}" fill="{p["text"]}" font-size="8" '
        'letter-spacing="1.2" font-family="system-ui,sans-serif">GITTANKS</text>',
        '</svg>',
    ])
    return "\n".join(parts) + "\n"
