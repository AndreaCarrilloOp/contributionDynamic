"""GitAbyss: bioluminescent jellyfish feeding on contribution energy."""

from dataclasses import dataclass
from math import hypot

from contribution_dynamic.animation import track as _track
from contribution_dynamic.calendar import Day, month_label_positions

STEP = 13
CELL = 10
LEFT = 47
TOP = 34
MAX_JELLIES = 7

PALETTES = {
    "dark": {
        "bg": "#071522", "empty": "#102536", "text": "#91aeba",
        "levels": ("#0e4429", "#006d32", "#26a641", "#39d353"),
        "pulse": "#67e8f9", "bell": "#22d3ee", "rim": "#cffafe",
        "deep": "#2563eb", "tentacle": "#67e8f9",
    },
    "light": {
        "bg": "#f0faff", "empty": "#dceaf0", "text": "#426474",
        "levels": ("#9be9a8", "#40c463", "#30a14e", "#216e39"),
        "pulse": "#0891b2", "bell": "#0e7490", "rim": "#ecfeff",
        "deep": "#2563eb", "tentacle": "#0369a1",
    },
}


@dataclass(frozen=True)
class Visit:
    day: Day
    arrival: float


@dataclass(frozen=True)
class Journey:
    visits: tuple[Visit, ...]
    positions: tuple[tuple[float, float], ...]
    times: tuple[float, ...]


def _level(day: Day) -> int:
    if not day.count:
        return 0
    return max(1, day.level) if day.level is not None else min(4, day.count.bit_length())


def _center(day: Day) -> tuple[float, float]:
    return LEFT + day.week * STEP + CELL / 2, TOP + day.weekday * STEP + CELL / 2


def _target(day: Day) -> tuple[float, float]:
    x, y = _center(day)
    # The luminous tips touch the cell while the bell remains above it.
    return x, y - 11


def _travel(a: tuple[float, float], b: tuple[float, float]) -> float:
    return max(.30, hypot(b[0] - a[0], b[1] - a[1]) / 95)


def plan_journeys(days: tuple[Day, ...]) -> tuple[Journey, ...]:
    """Allocate each active cell once, with no waiting for empty columns."""
    active = sorted(
        (day for day in days if day.count),
        key=lambda d: (d.week, d.weekday if d.week % 2 == 0 else -d.weekday),
    )
    if not active:
        return ()
    count = min(MAX_JELLIES, len(active))
    routes = []
    for i in range(count):
        group = active[i * len(active) // count:(i + 1) * len(active) // count]
        first = _target(group[0])
        home = (first[0] - 9, first[1] - 3)
        positions = [home]
        times = [0.0]
        visits = []
        for day in group:
            target = _target(day)
            arrival = times[-1] + _travel(positions[-1], target)
            visits.append(Visit(day, arrival))
            positions.extend((target, target))
            times.extend((arrival, arrival + .40))
        # Return to the starting point for a seamless repeating journey.
        times.append(times[-1] + max(.75, _travel(positions[-1], home)))
        positions.append(home)
        routes.append(Journey(tuple(visits), tuple(positions), tuple(times)))
    return tuple(routes)


def _jelly(route: Journey, index: int, cycle: float, p: dict) -> list[str]:
    x, y = route.positions[0]
    points = [f"{a:.3f} {b:.3f}" for a, b in route.positions]
    period = 1.4 + index * .09
    parts = [
        f'<g data-jelly="{index}" transform="translate({x} {y})">',
        _track("transform", points, route.times, cycle, transform=True),
        '<g>',
        '<animateTransform attributeName="transform" type="translate" '
        f'values="0 0;0 -1.2;0 0" dur="{period:.2f}s" repeatCount="indefinite"/>',
        # Concentric translucent halos avoid expensive blur filters.
        f'<ellipse rx="13" ry="9" cy="-1" fill="{p["bell"]}" opacity=".08"/>',
        f'<ellipse rx="10" ry="7" cy="-1" fill="{p["bell"]}" opacity=".13"/>',
    ]
    for n, dx in enumerate((-6, -3, 0, 3, 6)):
        length = 11 + (2 - abs(n - 2)) * 2
        a = f"M{dx} 2 Q{dx-3} 7 {dx+1} {length}"
        b = f"M{dx} 2 Q{dx+3} 7 {dx-1} {length}"
        parts.extend([
            f'<path d="{a}" fill="none" stroke="{p["tentacle"]}" '
            'stroke-width=".85" stroke-linecap="round" opacity=".85">',
            f'<animate attributeName="d" values="{a};{b};{a}" '
            f'dur="{period+.15*n:.2f}s" repeatCount="indefinite"/>',
            '</path>',
        ])
    shell = "M-8 1 C-8 -10 8 -10 8 1 Q0 5 -8 1Z"
    contracted = "M-7 1 C-7 -12 7 -12 7 1 Q0 4 -7 1Z"
    parts.extend([
        f'<path d="{shell}" fill="url(#abyss-bell)" stroke="{p["rim"]}" '
        'stroke-width=".65">',
        f'<animate attributeName="d" values="{shell};{contracted};{shell}" '
        f'dur="{period:.2f}s" repeatCount="indefinite"/>',
        '</path>',
        f'<ellipse cx="0" cy="1" rx="7" ry="2" fill="{p["deep"]}" opacity=".65"/>',
        f'<path d="M-5 -2 Q-3 -6 0 -6" fill="none" stroke="{p["rim"]}" '
        'stroke-width="1" stroke-linecap="round" opacity=".85"/>',
        f'<circle r="1.6" cy="-2" fill="{p["rim"]}">',
        '<animate attributeName="opacity" values=".35;1;.35" '
        f'dur="{period:.2f}s" repeatCount="indefinite"/>',
        '</circle></g></g>',
    ])
    return parts


def render_abyss(days: tuple[Day, ...], theme: str = "dark") -> str:
    p = PALETTES[theme]
    weeks = max(53, max((day.week + 1 for day in days), default=0))
    width, height = LEFT + weeks * STEP + 16, TOP + 7 * STEP + 22
    routes = plan_journeys(days)
    cycle = max(4.0, max((r.times[-1] for r in routes), default=0) + .3)
    visit_times = {visit.day: visit.arrival for route in routes for visit in route.visits}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        'aria-label="GitAbyss bioluminescent contribution calendar">',
        '<title>GitAbyss — bioluminescence</title>',
        '<defs><radialGradient id="abyss-bell" cx=".42" cy=".25" r=".8">',
        f'<stop offset="0" stop-color="{p["rim"]}"/>',
        f'<stop offset=".45" stop-color="{p["bell"]}"/>',
        f'<stop offset="1" stop-color="{p["deep"]}"/>',
        '</radialGradient></defs>',
        f'<rect width="{width}" height="{height}" rx="6" fill="{p["bg"]}"/>',
        f'<g font-family="system-ui,sans-serif" font-size="10" fill="{p["text"]}">',
    ]
    for x, label in month_label_positions(days, LEFT, STEP, width):
        parts.append(f'<text x="{x}" y="14">{label}</text>')
    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(f'<text x="10" y="{TOP+row*STEP+8}">{label}</text>')
    parts.extend(['</g>', '<g id="calendar">'])
    for day in sorted(days, key=lambda d: (d.week, d.weekday)):
        x, y = LEFT + day.week * STEP, TOP + day.weekday * STEP
        level = _level(day)
        color = p["levels"][level-1] if level else p["empty"]
        parts.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
                     f'fill="{color}" data-date="{day.date.isoformat()}">')
        parts.append(f'<title>{day.date.isoformat()}: {day.count} contributions</title>')
        if day in visit_times:
            t = visit_times[day]
            parts.append(_track("fill", [color, p["pulse"], color],
                                [max(0, t-.12), t+.10, t+.60], cycle))
        parts.append('</rect>')
    parts.extend(['</g>', '<g id="energy-pulses">'])
    for day, t in visit_times.items():
        x, y = _center(day)
        radius = 5 + 2 * _level(day)
        parts.append(f'<circle cx="{x}" cy="{y}" r="4" fill="none" '
                     f'stroke="{p["pulse"]}" stroke-width="1" opacity="0" '
                     f'data-energy="{day.date.isoformat()}">')
        parts.append(_track("r", [4, radius], [t, t+.65], cycle))
        parts.append(_track("opacity", [0, .85, 0], [t-.04, t+.15, t+.65], cycle))
        parts.append('</circle>')
    parts.extend(['</g>', '<g id="jellyfish">'])
    for i, route in enumerate(routes):
        parts.extend(_jelly(route, i, cycle, p))
    parts.extend([
        '</g>',
        f'<text x="{LEFT}" y="{height-7}" font-size="8" letter-spacing="1.5" '
        f'font-family="system-ui,sans-serif" fill="{p["text"]}">BIOLUMINESCENCE</text>',
        '</svg>',
    ])
    return "\n".join(parts) + "\n"
