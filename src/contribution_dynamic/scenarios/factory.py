"""Compact contribution-board factory with parallel, independent work zones."""

from dataclasses import dataclass

from contribution_dynamic.animation import track as _track
from contribution_dynamic.calendar import Day

STEP = 13
CELL = 10
LEFT = 47
TOP = 39
RAIL = 25
BELT = TOP + 7 * STEP + 13
CADENCE = 2.4
LANE_COUNT = 4
GRAB = 0.72
DROP = 1.28
FINISH = 2.28

PALETTES = {
    "dark": {
        "bg": "#0d1117", "empty": "#161b22", "text": "#8b949e",
        "rail": "#30363d", "metal": "#94a3b8", "belt": "#34434e",
        "surface": "#596c79", "arm": "#f1b450", "accent": "#2dd4bf",
        "levels": ("#0e4429", "#006d32", "#26a641", "#39d353"),
    },
    "light": {
        "bg": "#ffffff", "empty": "#ebedf0", "text": "#57606a",
        "rail": "#d0d7de", "metal": "#64748b", "belt": "#d8dee4",
        "surface": "#b8c4cf", "arm": "#b45309", "accent": "#0f766e",
        "levels": ("#9be9a8", "#40c463", "#30a14e", "#216e39"),
    },
}


@dataclass(frozen=True)
class Job:
    day: Day
    start: float
    lane: int


def active_days(days: tuple[Day, ...]) -> tuple[Day, ...]:
    return tuple(sorted((d for d in days if d.count > 0), key=lambda d: d.date))


def board_weeks(days: tuple[Day, ...]) -> int:
    return max(53, max((day.week + 1 for day in days), default=0))


def zone_edges(weeks: int) -> tuple[int, ...]:
    return tuple(i * weeks // LANE_COUNT for i in range(LANE_COUNT + 1))


def schedule(days: tuple[Day, ...]) -> tuple[Job, ...]:
    edges = zone_edges(board_weeks(days))
    loads = [0] * LANE_COUNT
    jobs = []
    for day in active_days(days):
        lane = next(i for i in range(LANE_COUNT) if day.week < edges[i + 1])
        jobs.append(Job(day, loads[lane] * CADENCE, lane))
        loads[lane] += 1
    return tuple(jobs)


def contribution_level(count: int) -> int:
    return 0 if count <= 0 else min(4, count.bit_length())


def _level(day: Day) -> int:
    if day.count == 0:
        return 0
    return max(1, day.level) if day.level is not None else contribution_level(day.count)


def month_labels(days: tuple[Day, ...]) -> list[tuple[int, str]]:
    labels = []
    seen = set()
    last_week = -4
    names = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    for day in sorted(days, key=lambda d: d.date):
        month = (day.date.year, day.date.month)
        if month not in seen:
            seen.add(month)
            if day.week - last_week >= 3:
                labels.append((day.week, names[day.date.month - 1]))
                last_week = day.week
    return labels


def _color(day, palette):
    level = _level(day)
    return palette["levels"][level - 1] if level else palette["empty"]


def _machine(left, right, jobs, cycle, p):
    """Draw a short conveyor and a processing station for one work zone."""
    width = right - left - 4
    output = right - 8
    parts = [
        f'<rect x="{left}" y="{BELT}" width="{width}" height="13" '
        f'rx="3" fill="{p["belt"]}"/>',
        f'<rect x="{left+2}" y="{BELT+2}" width="{width-4}" height="7" '
        f'fill="{p["surface"]}"/>',
    ]
    for x in range(left + 6, right - 6, 12):
        parts.append(f'<circle cx="{x}" cy="{BELT+10}" r="2" fill="{p["metal"]}"/>')
    if jobs:
        parts.append(
            f'<path d="M{left+3} {BELT+5}H{right-7}" stroke="{p["rail"]}" '
            'stroke-width="6" stroke-dasharray="2 10">'
            '<animate attributeName="stroke-dashoffset" from="0" to="-12" '
            'dur=".5s" repeatCount="indefinite"/></path>'
        )
    # Frame the output above the line, leaving the moving package visible.
    parts.extend([
        f'<path d="M{output-8} {BELT+1}V{BELT-15}H{output+6}V{BELT+1}" '
        f'fill="none" stroke="{p["metal"]}" stroke-width="3"/>',
        f'<rect x="{output-7}" y="{BELT-16}" width="12" height="3" '
        f'fill="{p["arm"]}"/>',
        f'<rect x="{output-7}" y="{BELT+15}" width="12" height="3" '
        f'rx="1" fill="{p["accent"]}" opacity=".3">',
    ])
    if jobs:
        times = [0]
        values = [.3]
        for job in jobs:
            times.extend([job.start+FINISH-.16, job.start+FINISH+.06])
            values.extend([1, .3])
        parts.append(_track("opacity", values, times, cycle, "discrete"))
    parts.append('</rect>')
    return parts


def _arm(jobs, left, cycle, p):
    """Animate one persistent trolley and its telescoping, articulated gripper."""
    home = left + 5
    xs = [home]
    ts = [0]
    tips = [RAIL + 10]
    ys = [0]
    for job in jobs:
        s = job.start
        x = LEFT + job.day.week * STEP + CELL / 2
        y = TOP + job.day.weekday * STEP + CELL / 2
        xs.extend([x, x])
        ts.extend([s+.30, s+CADENCE-.08])
        tips.extend([RAIL+10, y, BELT-CELL/2, RAIL+10])
        ys.extend([s+.30, s+GRAB, s+DROP, s+1.85])
    # Return home before the shared loop resets.
    if jobs:
        xs.append(home)
        ts.append(cycle)
    parts = [
        f'<g transform="translate({home} 0)">',
        f'<rect x="-7" y="{RAIL-4}" width="14" height="9" '
        f'rx="2" fill="{p["metal"]}"/>',
        f'<rect x="-5" y="{RAIL-2}" width="10" height="2" fill="{p["arm"]}"/>',
    ]
    if jobs:
        parts.append(_track("transform", [f"{x} 0" for x in xs], ts, cycle,
                            transform=True))
    parts.append(f'<g transform="translate(0 {RAIL+10})">')
    # A solid two-segment arm, with its endpoint calculated from the same tip track.
    paths = [f"M0 {RAIL+4-v} L-5 {(RAIL+4-v)/2:.3f} L0 0" for v in tips]
    parts.append(f'<path d="{paths[0]}" fill="none" stroke="{p["arm"]}" '
                 'stroke-width="4" stroke-linejoin="round" stroke-linecap="round">')
    if jobs:
        parts.append(_track("d", paths, ys, cycle))
    parts.append('</path>')
    if jobs:
        parts.append(_track("transform", [f"0 {v}" for v in tips], ys, cycle,
                            transform=True))
    parts.append(f'<rect x="-2" y="-2" width="4" height="4" fill="{p["metal"]}"/>')
    for x in (-6, 6):
        parts.append(f'<path d="M{x} -3V4" stroke="{p["accent"]}" '
                     'stroke-width="2" stroke-linecap="round"/>')
    parts.extend(['</g>', '</g>'])
    return parts


def render_factory(days: tuple[Day, ...], theme: str = "dark") -> str:
    palette = PALETTES[theme]
    weeks = board_weeks(days)
    edges = zone_edges(weeks)
    width = LEFT + weeks * STEP + 16
    height = BELT + 25
    jobs = schedule(days)
    cycle = max(4.0, max((j.start + CADENCE for j in jobs), default=0) + .8)
    by_day = {job.day: job for job in jobs}
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        'aria-label="GitFactory contribution board animation">',
        '<title>GitFactory — contribution calendar</title>',
        f'<rect width="{width}" height="{height}" rx="6" fill="{palette["bg"]}"/>',
        f'<g font-family="system-ui,sans-serif" font-size="10" fill="{palette["text"]}">',
    ]
    for week, label in month_labels(days):
        p.append(f'<text x="{LEFT+week*STEP}" y="13">{label}</text>')
    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        p.append(f'<text x="10" y="{TOP+row*STEP+8}">{label}</text>')
    p.extend(['</g>', '<g id="calendar">'])
    for day in sorted(days, key=lambda d: (d.week, d.weekday)):
        x, y = LEFT + day.week * STEP, TOP + day.weekday * STEP
        fill = _color(day, palette)
        p.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
                 f'fill="{fill}" data-date="{day.date.isoformat()}">')
        p.append(f'<title>{day.date.isoformat()}: {day.count} contributions</title>')
        if day in by_day:
            grab = by_day[day].start + GRAB
            p.append(_track("fill", [fill, palette["empty"], fill],
                            [0, grab, cycle], cycle, "discrete"))
        p.append('</rect>')
    p.append('</g>')
    for lane in range(LANE_COUNT):
        left, right = LEFT + edges[lane]*STEP, LEFT + edges[lane+1]*STEP
        lane_jobs = [j for j in jobs if j.lane == lane]
        p.append(f'<g id="zone-{lane}">')
        p.append(f'<path d="M{left} {RAIL}H{right-4}" stroke="{palette["rail"]}" '
                 'stroke-width="4"/>')
        p.extend(_machine(left, right, lane_jobs, cycle, palette))
        p.extend(_arm(lane_jobs, left, cycle, palette))
        for job in lane_jobs:
            x = LEFT + job.day.week*STEP
            y = TOP + job.day.weekday*STEP
            s = job.start
            grab, drop, end = s+GRAB, s+DROP, s+FINISH
            out_x = right - 8 - CELL/2
            fill = _color(job.day, palette)
            p.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
                     f'fill="{fill}" opacity="0" data-batch="{job.day.date.isoformat()}">')
            p.append(_track("opacity", [0, 1, 0], [0, grab, end], cycle, "discrete"))
            p.append(_track("x", [x, x, out_x], [grab, drop, end], cycle))
            p.append(_track("y", [y, BELT-CELL, BELT-CELL], [grab, drop, end], cycle))
            p.append(_track("fill", [fill, fill, palette["accent"]],
                            [grab, drop, end], cycle))
            p.append('</rect>')
        p.append('</g>')
    p.append('</svg>')
    return "\n".join(p) + "\n"
