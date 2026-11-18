"""Fold active contribution cells into paper birds using declarative SVG."""

from contribution_dynamic.calendar import Day

STEP = 13
CELL = 10
LEFT = 47
TOP = 32
FLIGHT = 2.6
WEEK_DELAY = 0.42
ROW_DELAY = 0.11

PALETTES = {
    "dark": ("#0d1117", "#161b22", "#8b949e",
             ("#0e4429", "#006d32", "#26a641", "#39d353"),
             "#b8f5db", "#48bfa9", "#137b70"),
    "light": ("#ffffff", "#ebedf0", "#57606a",
              ("#9be9a8", "#40c463", "#30a14e", "#216e39"),
              "#65bda2", "#198f80", "#075e55"),
}

# Four triangular paper panels; each has matching vertex counts in all states.
PAPER = ("-5,-5 5,-5 0,0", "5,-5 5,5 0,0",
         "5,5 -5,5 0,0", "-5,5 -5,-5 0,0")
FOLD = ("-4,-4 4,-4 0,1", "4,-4 3,2 0,1",
        "3,2 -3,4 0,1", "-3,4 -4,-4 0,1")
BIRD_UP = ("-10,-6 0,-1 3,3", "0,-1 10,-8 3,3",
           "-4,3 3,3 -9,7", "0,-1 8,0 3,3")
BIRD_DOWN = ("-10,5 0,-1 3,3", "0,-1 10,6 3,3",
             "-4,3 3,3 -9,7", "0,-1 8,0 3,3")


def _track(name, values, times, cycle, mode="linear", transform=False):
    """Pad a local timeline to the shared loop."""
    values, times = list(values), list(times)
    if times[0] > 0:
        values.insert(0, values[0])
        times.insert(0, 0)
    if times[-1] < cycle:
        values.append(values[-1])
        times.append(cycle)
    keys = ";".join(f"{t / cycle:.9f}" for t in times)
    vals = ";".join(map(str, values))
    tag = "animateTransform" if transform else "animate"
    extra = ' type="translate"' if transform else ""
    return (
        f'<{tag} attributeName="{name}"{extra} values="{vals}" keyTimes="{keys}" '
        f'dur="{cycle:.6f}s" calcMode="{mode}" repeatCount="indefinite"/>'
    )


def _level(day: Day) -> int:
    if day.count == 0:
        return 0
    return max(1, day.level) if day.level is not None else min(4, day.count.bit_length())


def _start(day: Day) -> float:
    # A left-to-right wave; Sundays through Saturdays fold in quick succession.
    return day.week * WEEK_DELAY + day.weekday * ROW_DELAY + 0.15


def _months(days: tuple[Day, ...]) -> list[tuple[int, str]]:
    names = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    labels = []
    seen = set()
    last = -4
    for day in sorted(days, key=lambda d: d.date):
        key = (day.date.year, day.date.month)
        if key not in seen:
            seen.add(key)
            if day.week - last >= 3:
                labels.append((day.week, names[day.date.month - 1]))
                last = day.week
    return labels


def _bird(day, color, shades, cycle, width):
    x = LEFT + day.week * STEP + CELL / 2
    y = TOP + day.weekday * STEP + CELL / 2
    s = _start(day)
    end = s + FLIGHT
    dx = 1 if x < width - 90 else -1
    # All flight positions remain in the SVG; the board itself stays in place.
    locations = [
        f"{x} {y}", f"{x} {y}", f"{x+dx*12} {y-6}",
        f"{x+dx*34} {max(14, y-18)}", f"{x+dx*55} {max(12, y-28)}",
    ]
    p = [
        f'<g data-bird="{day.date.isoformat()}" opacity="0" '
        f'transform="translate({x} {y})">',
        _track("opacity", [0, 0, 1, 1, 0],
               [0, s-.015, s, end-.45, end], cycle),
        _track("transform", locations, [s, s+.36, s+.85, s+1.6, end], cycle,
               transform=True),
    ]
    for i in range(4):
        p.append(f'<polygon points="{PAPER[i]}" fill="{color}">')
        p.append(_track("points", [
            PAPER[i], FOLD[i], BIRD_UP[i], BIRD_DOWN[i], BIRD_UP[i],
            BIRD_DOWN[i], BIRD_UP[i], BIRD_DOWN[i],
        ], [s, s+.19, s+.43, s+.79, s+1.15, s+1.51, s+1.87, end], cycle))
        p.append(_track("fill", [color, color, shades[i]], [s, s+.19, s+.43], cycle))
        p.append('</polygon>')
    p.append('</g>')
    return p


def render_origami(days: tuple[Day, ...], theme: str = "dark") -> str:
    bg, empty, text, levels, highlight, middle, shadow = PALETTES[theme]
    weeks = max(53, max((d.week + 1 for d in days), default=0))
    width, height = LEFT + weeks * STEP + 16, TOP + 7 * STEP + 13
    active = [day for day in days if day.count > 0]
    cycle = max(4.0, max((_start(d) + FLIGHT for d in active), default=0) + 1.2)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        'aria-label="GitOrigami contribution calendar animation">',
        '<title>GitOrigami — contribution calendar</title>',
        f'<rect width="{width}" height="{height}" rx="6" fill="{bg}"/>',
        f'<g font-family="system-ui,sans-serif" font-size="10" fill="{text}">',
    ]
    for week, label in _months(days):
        parts.append(f'<text x="{LEFT+week*STEP}" y="14">{label}</text>')
    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(f'<text x="10" y="{TOP+row*STEP+8}">{label}</text>')
    parts.extend(['</g>', '<g id="calendar">'])
    for day in sorted(days, key=lambda d: (d.week, d.weekday)):
        x, y = LEFT + day.week * STEP, TOP + day.weekday * STEP
        level = _level(day)
        color = levels[level-1] if level else empty
        parts.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
                     f'fill="{color}" data-date="{day.date.isoformat()}">')
        parts.append(f'<title>{day.date.isoformat()}: {day.count} contributions</title>')
        if day.count:
            s = _start(day)
            # The source fades to an empty cell at the same time the paper appears.
            parts.append(_track("fill", [color, color, empty, empty, color],
                                [0, s-.015, s, s+FLIGHT, cycle], cycle, "discrete"))
        parts.append('</rect>')
    parts.extend(['</g>', '<g id="paper-birds">'])
    for day in sorted(active, key=lambda d: (d.week, d.weekday)):
        parts.extend(_bird(day, levels[_level(day)-1],
                           (highlight, middle, shadow, highlight), cycle, width))
    parts.extend(['</g>', '</svg>'])
    return "\n".join(parts) + "\n"
