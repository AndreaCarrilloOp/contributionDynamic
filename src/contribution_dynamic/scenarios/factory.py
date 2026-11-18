"""Animate production directly on the GitHub contribution calendar."""

from dataclasses import dataclass

from contribution_dynamic.calendar import Day

STEP = 13
CELL = 10
LEFT = 47
TOP = 57
CADENCE = 3.6

PALETTES = {
    "dark": ("#0d1117", "#161b22", "#c9d1d9", "#30363d", "#94a3b8", "#2dd4bf",
             ("#0e4429", "#006d32", "#26a641", "#39d353")),
    "light": ("#ffffff", "#ebedf0", "#24292f", "#d0d7de", "#64748b", "#0f766e",
              ("#9be9a8", "#40c463", "#30a14e", "#216e39")),
}


@dataclass(frozen=True)
class Job:
    day: Day
    start: float


def active_days(days: tuple[Day, ...]) -> tuple[Day, ...]:
    return tuple(sorted((d for d in days if d.count > 0), key=lambda d: d.date))


def schedule(days: tuple[Day, ...]) -> tuple[Job, ...]:
    return tuple(Job(day, i * CADENCE) for i, day in enumerate(active_days(days)))


def contribution_level(count: int) -> int:
    return 0 if count == 0 else min(4, count.bit_length())


def month_labels(days: tuple[Day, ...]) -> list[tuple[int, str]]:
    labels = []
    seen = set()
    last_week = -4
    for day in sorted(days, key=lambda d: d.date):
        month = (day.date.year, day.date.month)
        if month not in seen:
            seen.add(month)
            if day.week - last_week >= 3:
                labels.append((day.week, day.date.strftime("%b")))
                last_week = day.week
    return labels


def _animation(name, values, times, duration, mode="linear"):
    keys = ";".join(f"{t / duration:.9f}" for t in times)
    vals = ";".join(str(v) for v in values)
    return (
        f'<animate attributeName="{name}" values="{vals}" keyTimes="{keys}" '
        f'dur="{duration}s" calcMode="{mode}" repeatCount="indefinite"/>'
    )


def _track(name, values, times, duration, mode="linear"):
    """Extend a local timeline to the full cycle without duplicate end times."""
    values, times = list(values), list(times)
    if times[0] > 0:
        times.insert(0, 0)
        values.insert(0, values[0])
    if times[-1] < duration:
        times.append(duration)
        values.append(values[-1])
    return _animation(name, values, times, duration, mode)


def render_factory(days: tuple[Day, ...], theme: str = "dark") -> str:
    bg, empty, text, panel, metal, accent, levels = PALETTES[theme]
    weeks = max(53, max((day.week + 1 for day in days), default=0))
    grid_width = weeks * STEP
    width = LEFT + grid_width + 20
    belt = TOP + 7 * STEP + 14
    height = belt + 37
    output = LEFT + grid_width - 10
    jobs = schedule(days)
    cycle = max(4.0, len(jobs) * CADENCE + 0.6)
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        'role="img" aria-label="GitFactory contribution board animation">',
        '<title>GitFactory — contribution calendar</title>',
        f'<rect width="{width}" height="{height}" rx="8" fill="{bg}"/>',
        f'<g font-family="system-ui,sans-serif" fill="{text}" font-size="10">',
        '<text x="12" y="17" font-weight="bold" font-size="13">GitFactory</text>',
        f'<text x="{width-12}" y="17" text-anchor="end">'
        f'{len(jobs)} batches / {sum(d.count for d in days)} contributions</text>',
    ]
    for week, label in month_labels(days):
        p.append(f'<text x="{LEFT + week * STEP}" y="33">{label}</text>')
    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        p.append(f'<text x="12" y="{TOP + row * STEP + 8}">{label}</text>')
    p.append('</g>')
    p.append('<g id="calendar">')
    by_position = {(d.week, d.weekday): d for d in days}
    for week in range(weeks):
        for row in range(7):
            day = by_position.get((week, row))
            if day is None:
                continue
            x, y = LEFT + week * STEP, TOP + row * STEP
            level = contribution_level(day.count)
            fill = levels[level - 1] if level else empty
            p.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
                f'fill="{fill}" data-date="{day.date.isoformat()}">'
                f'<title>{day.date.isoformat()}: {day.count} contributions</title></rect>'
            )
    p.append('</g>')
    p.extend([
        f'<path d="M{LEFT} 45H{LEFT+grid_width-3}" stroke="{panel}" stroke-width="5"/>',
        f'<rect x="{LEFT}" y="{belt}" width="{grid_width-3}" height="17" '
        f'rx="4" fill="{panel}"/>',
        f'<rect x="{output-8}" y="{belt-4}" width="16" height="23" rx="3" '
        f'fill="{metal}"/>',
    ])
    for x in range(LEFT + 8, output - 8, 19):
        p.append(f'<circle cx="{x}" cy="{belt+9}" r="4" fill="{metal}" opacity=".5"/>')
    if jobs:
        p.append(
            f'<path d="M{LEFT+3} {belt+3}H{output-9}" stroke="{accent}" '
            'stroke-width="1.5" stroke-dasharray="6 13">'
            '<animate attributeName="stroke-dashoffset" from="0" to="-19" dur=".7s" '
            'repeatCount="indefinite"/></path>'
        )
    for job in jobs:
        x = LEFT + job.day.week * STEP
        y = TOP + job.day.weekday * STEP
        cx, cy = x + CELL / 2, y + CELL / 2
        s = job.start
        grab, drop, end = s + .9, s + 1.8, s + 3.4
        fill = levels[contribution_level(job.day.count) - 1]
        # The source is visually removed after pickup, restored at cycle reset.
        p.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                 f'rx="2" fill="{empty}" opacity="0">')
        p.append(_track("opacity", [0, 1, 1, 0], [0, grab, cycle-.1, cycle],
                        cycle, "discrete"))
        p.append('</rect>')
        # A rail-mounted gripper extends to the source, then lowers the payload.
        p.append('<g opacity="0">')
        p.append(_track("opacity", [0, 1, 0], [0, s+.1, drop], cycle, "discrete"))
        p.append(f'<rect x="{cx-7}" y="40" width="14" height="10" rx="2" fill="{metal}"/>')
        p.append(f'<line x1="{cx}" y1="49" x2="{cx}" y2="49" stroke="{metal}" '
                 'stroke-width="2">')
        p.append(_track("y2", [49, cy, belt-6], [s+.1, grab, drop], cycle))
        p.append('</line>')
        for offset in (-5, 5):
            p.append(f'<line x1="{cx+offset}" x2="{cx+offset}" y1="49" y2="55" '
                     f'stroke="{accent}" stroke-width="2" stroke-linecap="round">')
            p.append(_track("y1", [49, cy, belt-6], [s+.1, grab, drop], cycle))
            p.append(_track("y2", [55, cy+6, belt], [s+.1, grab, drop], cycle))
            p.append('</line>')
        p.append('</g>')
        # The same calendar cell travels down to the belt and to the output.
        p.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
                 f'fill="{fill}" opacity="0">')
        p.append(_track("opacity", [0, 1, 0], [0, grab, end], cycle, "discrete"))
        p.append(_track("x", [x, x, output-CELL/2], [grab, drop, end], cycle))
        p.append(_track("y", [y, belt-CELL, belt-CELL], [grab, drop, end], cycle))
        p.append(_track("fill", [fill, fill, accent], [grab, drop, end], cycle))
        p.append('</rect>')
    p.append(f'<text x="{LEFT}" y="{height-8}" font-family="monospace" '
             f'font-size="9" fill="{text}">CONTRIBUTION PROCESSING</text>')
    p.append('</svg>')
    return "\n".join(p) + "\n"
