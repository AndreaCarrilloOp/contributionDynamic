"""GitBlast: arcade-style bombs and destructible contribution bricks."""

from dataclasses import dataclass

from contribution_dynamic.animation import track
from contribution_dynamic.calendar import Day

STEP = 13
CELL = 10
LEFT = 47
TOP = 30
LANES = 4
FIRST = .12
CADENCE = 1.95
PLANT = .48
IGNITE = .98
CLEAR = 1.40
RESTORE = 1.76
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
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
    lane: int
    start: float


def _level(day: Day) -> int:
    if not day.count:
        return 0
    return max(1, day.level) if day.level is not None else min(4, day.count.bit_length())


def board_weeks(days: tuple[Day, ...]) -> int:
    return max(53, max((d.week + 1 for d in days), default=0))


def blast_cross(center: Square, radius: int, left: int, right: int) -> tuple[Square, ...]:
    """Return the center and four arms, clipped to a work zone and seven rows."""
    x, y = center
    points = [center]
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for distance in range(1, radius + 1):
            a, b = x + dx * distance, y + dy * distance
            if left <= a < right and 0 <= b < 7:
                points.append((a, b))
    return tuple(points)


def plan_blasts(days: tuple[Day, ...]) -> tuple[Blast, ...]:
    """Cover every active cell with local cross-shaped detonations."""
    weeks = board_weeks(days)
    active = {(d.week, d.weekday): d for d in days if d.count}
    events = []
    for lane in range(LANES):
        left, right = lane * weeks // LANES, (lane + 1) * weeks // LANES
        pending = {pos for pos in active if left <= pos[0] < right}
        i = 0
        while pending:
            # Strong cells first; each detonation can cover neighboring activity.
            center = min(pending, key=lambda pos: (-_level(active[pos]), pos))
            radius = 1 if _level(active[center]) <= 2 else 2
            cross = blast_cross(center, radius, left, right)
            hits = tuple(active[pos] for pos in cross if pos in active)
            pending.difference_update(cross)
            x, y = center
            dx = 1 if x + 1 < right else -1
            dy = 1 if y + 1 < 7 else -1
            origin = (x + dx, y)
            shelter = (x + dx, y + dy)
            events.append(Blast(center, origin, shelter, cross, hits,
                                lane, FIRST + i * CADENCE))
            i += 1
    return tuple(events)


def _point(square: Square) -> tuple[float, float]:
    return LEFT + square[0] * STEP + CELL / 2, TOP + square[1] * STEP + CELL / 2


def _months(days):
    seen = set()
    last = -4
    for day in sorted(days, key=lambda d: d.date):
        month = day.date.year, day.date.month
        if month not in seen:
            seen.add(month)
            if day.week - last >= 3:
                yield day.week, MONTHS[day.date.month - 1]
                last = day.week


def _brick_track(color, events, empty, cycle):
    values, times = [color], [0.0]
    for event in events:
        values.extend((empty, color))
        times.extend((event.start + IGNITE, event.start + RESTORE))
    return track("fill", values, times, cycle, "discrete")


def _event(event: Blast, cycle: float, p: dict) -> list[str]:
    sx, sy = _point(event.origin)
    x, y = _point(event.center)
    hx, hy = _point(event.shelter)
    s = event.start
    place, hit = s + PLANT, s + IGNITE
    end = s + RESTORE
    # Each sprite uses the same clock as the brick and blast tracks.
    parts = [
        f'<g data-blast="{event.center[0]},{event.center[1]}" '
        f'data-lane="{event.lane}">',
        f'<g opacity="0" transform="translate({sx} {sy})">',
        track("opacity", [0, 1, 1, 0], [s, s+.09, hit+.15, end], cycle),
        track("transform", [f"{sx} {sy}", f"{x} {y}", f"{sx} {sy}", f"{hx} {hy}"],
              [s, place, place+.22, hit-.06], cycle, transform=True),
        f'<rect x="-4" y="-1" width="8" height="6" rx="1" fill="{p["actor"]}"/>',
        f'<rect x="-5" y="-6" width="10" height="8" rx="2" fill="{p["actor"]}" '
        f'stroke="{p["outline"]}" stroke-width=".6"/>',
        f'<rect x="-3" y="-4" width="6" height="3" rx="1" fill="{p["visor"]}"/>',
        f'<path d="M-3 5V7M3 5V7" stroke="{p["outline"]}" stroke-width="2"/>',
        '</g>',
        f'<g data-bomb="true" transform="translate({x} {y})" opacity="0">',
        track("opacity", [0, 1, 1, 0], [place-.03, place, hit-.02, hit], cycle),
        f'<circle r="4.4" fill="{p["bomb"]}" stroke="{p["outline"]}" stroke-width=".6"/>',
        f'<path d="M1 -4Q1 -7 4 -7" fill="none" stroke="{p["spark"]}" stroke-width="1"/>',
        f'<circle cx="4" cy="-7" r="1.5" fill="{p["spark"]}">',
        track("r", [1, 2.5, 1, 3], [place, place+.16, place+.30, hit], cycle),
        '</circle></g>',
        '<g data-explosion="true" opacity="0">',
        track("opacity", [0, 1, .85, 0], [hit-.01, hit+.06, hit+.20, s+CLEAR], cycle),
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
        color = p["bricks"][_level(day)-1]
        for dx, dy in ((-7, -8), (7, -7), (-6, 7), (6, 8)):
            parts.extend([
                f'<rect x="{bx-1}" y="{by-1}" width="2" height="2" fill="{color}" '
                'opacity="0">',
                track("opacity", [0, 1, 0], [hit, hit+.04, s+CLEAR], cycle),
                track("x", [bx-1, bx+dx], [hit, s+CLEAR], cycle),
                track("y", [by-1, by+dy], [hit, s+CLEAR], cycle),
                '</rect>',
            ])
    parts.append('</g>')
    return parts


def render_blast(days: tuple[Day, ...], theme: str = "dark") -> str:
    p = PALETTES[theme]
    width, height = LEFT + board_weeks(days) * STEP + 16, TOP + 7 * STEP + 17
    events = plan_blasts(days)
    cycle = max(4.0, max((e.start + CADENCE for e in events), default=0) + .5)
    by_day = {}
    for event in events:
        for day in event.hits:
            by_day.setdefault(day, []).append(event)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        'aria-label="GitBlast arcade contribution calendar">',
        '<title>GitBlast — ignite your contributions</title>',
        f'<rect width="{width}" height="{height}" rx="6" fill="{p["bg"]}"/>',
        f'<g font-family="system-ui,sans-serif" font-size="10" fill="{p["text"]}">',
    ]
    for week, name in _months(days):
        parts.append(f'<text x="{LEFT+week*STEP}" y="14">{name}</text>')
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(f'<text x="10" y="{TOP+row*STEP+8}">{name}</text>')
    parts.extend(['</g>', '<g id="calendar">'])
    for day in sorted(days, key=lambda d: (d.week, d.weekday)):
        x, y = LEFT + day.week * STEP, TOP + day.weekday * STEP
        level = _level(day)
        color = p["bricks"][level-1] if level else p["empty"]
        parts.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="1" '
                     f'fill="{color}" data-date="{day.date.isoformat()}" data-level="{level}">')
        parts.append(f'<title>{day.date.isoformat()}: {day.count} contributions</title>')
        if day in by_day:
            parts.append(_brick_track(color, by_day[day], p["empty"], cycle))
        parts.append('</rect>')
    parts.extend(['</g>', '<g id="brick-mortar">'])
    for day in sorted(by_day, key=lambda d: (d.week, d.weekday)):
        x, y = LEFT + day.week*STEP, TOP + day.weekday*STEP
        parts.append(f'<path d="M{x} {y+5}H{x+10}M{x+5} {y}V{y+5}M{x+3} {y+5}V{y+10}" '
                     f'fill="none" stroke="{p["mortar"]}" stroke-width=".6" opacity=".65">')
        values, times = [.65], [0.0]
        for event in by_day[day]:
            values.extend((0, .65))
            times.extend((event.start + IGNITE, event.start + RESTORE))
        parts.append(track("opacity", values, times, cycle, "discrete"))
        parts.append('</path>')
    parts.extend(['</g>', '<g id="arcade-events">'])
    for event in events:
        parts.extend(_event(event, cycle, p))
    parts.extend([
        '</g>',
        f'<text x="{LEFT}" y="{height-6}" fill="{p["fire"]}" font-size="8" '
        'letter-spacing="1.3" font-family="system-ui,sans-serif">GITBLAST</text>',
        '</svg>',
    ])
    return "\n".join(parts) + "\n"
