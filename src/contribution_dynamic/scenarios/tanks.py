"""GitTanks: armored patrols and contribution targets with ordered impacts."""

from dataclasses import dataclass, replace

from contribution_dynamic.animation import track
from contribution_dynamic.calendar import Day

STEP = 13
CELL = 10
LEFT = 47
TOP = 48
ROAD = TOP - 16
MUZZLE = ROAD + 10
LANES = 4
FIRST = .12
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
PALETTES = {
    "dark": {
        "bg": "#151d1b", "road": "#29352f", "line": "#46584b",
        "empty": "#27342e", "text": "#a2b5a7",
        "walls": ("#43523a", "#61724b", "#81945c", "#b2bf76"),
        "edge": "#253426", "track": "#171f1b", "hull": "#72905f",
        "turret": "#9dad70", "metal": "#c8d2b0", "flash": "#ffae42",
        "core": "#fff2a8",
    },
    "light": {
        "bg": "#f6f5e9", "road": "#d9dfcd", "line": "#a4ae94",
        "empty": "#e5e9da", "text": "#4c5c46",
        "walls": ("#b7c79c", "#93ab73", "#708f53", "#4c6937"),
        "edge": "#637852", "track": "#343c30", "hull": "#637e4b",
        "turret": "#90a65f", "metal": "#e5ebcf", "flash": "#e96b23",
        "core": "#ffdf76",
    },
}


@dataclass(frozen=True)
class Shot:
    day: Day
    lane: int
    origin_week: int
    start: float
    aim: float
    launch: float
    hit: float
    restore: float


def _level(day: Day) -> int:
    if not day.count:
        return 0
    return max(1, day.level) if day.level is not None else min(4, day.count.bit_length())


def board_weeks(days: tuple[Day, ...]) -> int:
    return max(53, max((d.week + 1 for d in days), default=0))


def _x(week: int) -> float:
    return LEFT + week * STEP + CELL / 2


def _y(row: int) -> float:
    return TOP + row * STEP + CELL / 2


def plan_shots(days: tuple[Day, ...]) -> tuple[Shot, ...]:
    """Clear each column top to bottom before restoring it."""
    weeks = board_weeks(days)
    shots = []
    for lane in range(LANES):
        left, right = lane * weeks // LANES, (lane + 1) * weeks // LANES
        active = sorted(
            (d for d in days if d.count and left <= d.week < right),
            key=lambda d: (d.week, d.weekday),
        )
        if not active:
            continue
        start, previous = FIRST, active[0].week
        column = []
        for day in active:
            if column and day.week != column[-1].day.week:
                restore = column[-1].hit + .48
                shots.extend(replace(shot, restore=restore) for shot in column)
                column = []
            aim = start + max(.20, abs(day.week - previous) * STEP / 115)
            launch = aim + .30
            hit = launch + max(.15, (_y(day.weekday) - MUZZLE) / 160)
            column.append(Shot(day, lane, previous, start, aim, launch, hit, 0))
            start, previous = hit + .28, day.week
        restore = column[-1].hit + .48
        shots.extend(replace(shot, restore=restore) for shot in column)
    return tuple(shots)


def _return_time(shots: list[Shot]) -> float:
    distance = abs(shots[-1].day.week - shots[0].day.week) * STEP
    return shots[-1].hit + .6 + max(.4, distance / 115)


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


def _tank(shots: list[Shot], lane: int, cycle: float, p: dict) -> list[str]:
    home = _x(shots[0].day.week)
    positions, times = [f"{home} {ROAD}"], [0.0]
    angles, angle_times = [90], [0.0]
    flash, flash_times = [0], [0.0]
    for shot in shots:
        origin, target = _x(shot.origin_week), _x(shot.day.week)
        positions.extend((f"{origin} {ROAD}", f"{target} {ROAD}"))
        times.extend((shot.start, shot.aim))
        if origin != target:
            angles.extend((90, 0, 0, 90))
            angle_times.extend((shot.start, shot.start+.10, shot.aim, shot.launch-.04))
        flash.extend((0, 1, 0))
        flash_times.extend((shot.launch-.015, shot.launch, shot.launch+.09))
    positions.extend((positions[-1], f"{home} {ROAD}"))
    times.extend((shots[-1].hit+.6, _return_time(shots)))
    parts = [
        f'<g data-tank="{lane}" transform="translate({home} {ROAD})">',
        track("transform", positions, times, cycle, transform=True),
        f'<rect x="-9" y="-6" width="18" height="12" rx="3" fill="{p["track"]}"/>',
        f'<path d="M-6 -5H6M-6 5H6" stroke="{p["metal"]}" stroke-width="1.2" '
        'stroke-dasharray="1 2"/>',
        f'<rect x="-7" y="-4" width="14" height="8" rx="2" fill="{p["hull"]}"/>',
        f'<path d="M-5 -2H5M-5 2H5" stroke="{p["edge"]}" stroke-width=".6"/>',
        '<g transform="rotate(90)">',
    ]
    if len(angles) > 1:
        parts.append(track("transform", angles, angle_times, cycle,
                           transform=True).replace('type="translate"', 'type="rotate"'))
    parts.extend([
        f'<rect x="1" y="-1.25" width="9" height="2.5" rx=".5" fill="{p["metal"]}"/>',
        f'<circle r="3.6" fill="{p["turret"]}" stroke="{p["edge"]}" stroke-width=".7"/>',
        f'<circle r="1.2" fill="{p["metal"]}"/>',
        f'<path d="M10 -3L15 0L10 3Z" fill="{p["flash"]}" opacity="0">',
        track("opacity", flash, flash_times, cycle),
        '</path></g></g>',
    ])
    return parts


def _projectile(shot: Shot, cycle: float, p: dict) -> list[str]:
    x, y = _x(shot.day.week), _y(shot.day.weekday)
    hit = shot.hit
    radius = 4 + _level(shot.day)
    parts = [
        f'<g data-shot="{shot.day.date.isoformat()}" data-lane="{shot.lane}">',
        f'<g transform="translate({x} {MUZZLE})" opacity="0">',
        track("opacity", [0, 1, 1, 0], [shot.launch-.01, shot.launch,
                                       hit-.01, hit], cycle),
        track("transform", [f"{x} {MUZZLE}", f"{x} {y}"],
              [shot.launch, hit], cycle, transform=True),
        f'<path d="M0 -5V0" stroke="{p["flash"]}" stroke-width="1.5" '
        'stroke-linecap="round"/>',
        f'<circle r="1.8" fill="{p["core"]}"/>',
        '</g>',
        f'<g transform="translate({x} {y})" opacity="0" data-impact="true">',
        track("opacity", [0, 1, .7, 0], [hit-.01, hit, hit+.10, hit+.25], cycle),
        f'<circle r="2" fill="none" stroke="{p["flash"]}" stroke-width="1.6">',
        track("r", [2, radius], [hit, hit+.25], cycle),
        '</circle>',
        f'<path d="M-4 0L0 -4L4 0L0 4Z" fill="{p["core"]}"/>',
        '</g>',
    ]
    for dx, dy in ((-6, -5), (6, -6), (-5, 6), (5, 6)):
        parts.extend([
            f'<rect x="{x-1}" y="{y-1}" width="2" height="2" fill="{p["flash"]}" '
            'opacity="0">',
            track("opacity", [0, 1, 0], [hit-.01, hit, hit+.24], cycle),
            track("x", [x-1, x+dx], [hit, hit+.24], cycle),
            track("y", [y-1, y+dy], [hit, hit+.24], cycle),
            '</rect>',
        ])
    parts.append('</g>')
    return parts


def render_tanks(days: tuple[Day, ...], theme: str = "dark") -> str:
    p = PALETTES[theme]
    weeks = board_weeks(days)
    width, height = LEFT + weeks * STEP + 16, TOP + 7 * STEP + 17
    shots = plan_shots(days)
    zones = [[s for s in shots if s.lane == i] for i in range(LANES)]
    cycle = max(4.0, max((_return_time(z) for z in zones if z), default=0) + .5)
    by_day = {shot.day: shot for shot in shots}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        'aria-label="GitTanks armored contribution calendar">',
        '<title>GitTanks — armored contribution patrol</title>',
        f'<rect width="{width}" height="{height}" rx="6" fill="{p["bg"]}"/>',
        f'<g font-family="system-ui,sans-serif" font-size="10" fill="{p["text"]}">',
    ]
    for week, label in _months(days):
        parts.append(f'<text x="{LEFT+week*STEP}" y="14">{label}</text>')
    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(f'<text x="10" y="{TOP+row*STEP+8}">{label}</text>')
    parts.extend(['</g>', '<g id="patrol-road">'])
    # A dedicated service lane prevents tanks crossing active targets.
    for lane in range(LANES):
        x = LEFT + lane * weeks // LANES * STEP
        right = LEFT + (lane + 1) * weeks // LANES * STEP
        parts.extend([
            f'<rect x="{x-4}" y="{ROAD-9}" width="{right-x+3}" height="18" '
            f'rx="3" fill="{p["road"]}"/>',
            f'<path d="M{x+1} {ROAD+7}H{right-5}" stroke="{p["line"]}" '
            'stroke-width="1" stroke-dasharray="3 4"/>',
        ])
    parts.extend(['</g>', '<g id="calendar">'])
    for day in sorted(days, key=lambda d: (d.week, d.weekday)):
        x, y = LEFT + day.week*STEP, TOP + day.weekday*STEP
        level = _level(day)
        color = p["walls"][level-1] if level else p["empty"]
        parts.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="1" '
                     f'fill="{color}" data-date="{day.date.isoformat()}" data-level="{level}">')
        parts.append(f'<title>{day.date.isoformat()}: {day.count} contributions</title>')
        if day in by_day:
            shot = by_day[day]
            parts.append(track("fill", [color, p["empty"], color],
                               [0, shot.hit, shot.restore], cycle, "discrete"))
        parts.append('</rect>')
    parts.extend(['</g>', '<g id="armor-detail">'])
    for day in sorted(by_day, key=lambda d: (d.week, d.weekday)):
        x, y = LEFT + day.week*STEP, TOP + day.weekday*STEP
        shot = by_day[day]
        parts.append(f'<path d="M{x+2} {y+2}H{x+8}V{y+8}H{x+2}Z" '
                     f'fill="none" stroke="{p["edge"]}" stroke-width=".65" opacity=".65">')
        parts.append(track("opacity", [.65, 0, .65],
                           [0, shot.hit, shot.restore], cycle, "discrete"))
        parts.append('</path>')
    parts.extend(['</g>', '<g id="patrols">'])
    for lane, zone in enumerate(zones):
        if zone:
            parts.extend(_tank(zone, lane, cycle, p))
    parts.extend(['</g>', '<g id="projectiles">'])
    for shot in shots:
        parts.extend(_projectile(shot, cycle, p))
    parts.extend([
        '</g>',
        f'<text x="{LEFT}" y="{height-6}" fill="{p["text"]}" font-size="8" '
        'letter-spacing="1.3" font-family="system-ui,sans-serif">GITTANKS</text>',
        '</svg>',
    ])
    return "\n".join(parts) + "\n"
