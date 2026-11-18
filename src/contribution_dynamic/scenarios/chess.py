"""GitChess: strategic chess-inspired captures on the contribution calendar."""

from dataclasses import dataclass
from math import hypot

from contribution_dynamic.calendar import Day

STEP = 13
CELL = 10
LEFT = 47
TOP = 30
LANES = 4
FIRST_MOVE = .18
CADENCE = 1.65
ARRIVAL = .88
RESTORE = 1.48
PIECES = ("knight", "rook", "bishop", "queen", "pawn", "king")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

PALETTES = {
    "dark": {
        "bg": "#0d1117", "empty": "#161b22", "text": "#8b949e",
        "levels": ("#0e4429", "#006d32", "#26a641", "#39d353"),
        "ivory": "#f1e5c9", "dark_piece": "#303943", "ink": "#111820",
        "gold": "#d6b575",
    },
    "light": {
        "bg": "#ffffff", "empty": "#ebedf0", "text": "#57606a",
        "levels": ("#9be9a8", "#40c463", "#30a14e", "#216e39"),
        "ivory": "#fff3d8", "dark_piece": "#343b43", "ink": "#574630",
        "gold": "#a47935",
    },
}

# Original vector silhouettes. Shared bases and strokes keep pieces legible
# at calendar-cell size without chess fonts or external image dependencies.
SHAPES = {
    "pawn": '<circle cx="0" cy="-4" r="2.5"/><path d="M-1.8 -1.5H1.8L3 4H-3Z"/>',
    "rook": '<path d="M-5 -6H-3V-3.8H-1V-6H1V-3.8H3V-6H5V-1.5'
            'L3 0L3.5 4H-3.5L-3 0L-5 -1.5Z"/>',
    "knight": '<path d="M-4.5 4L-3.5 1L-1 -1L-4.4 -.6L-5 -3L-1.5 -6'
              'L-1.2 -8L.5 -6.7C4.5 -6 5 -1 3.4 4Z"/>'
              '<circle cx="-1.3" cy="-3.9" r=".65" fill="currentColor" stroke="none"/>',
    "bishop": '<path d="M0 -7Q5 -3 2.5 -.5L1.5 .5L3.5 4H-3.5L-1.5 .5'
              'Q-5 -2 0 -7Z"/><path d="M.3 -5.4L-1 -2.4" fill="none"/>',
    "queen": '<path d="M-5 -4L-2.5 -1L0 -5L2.5 -1L5 -4L3.1 1L3.7 4'
             'H-3.7L-3.1 1Z"/><circle cx="-5" cy="-5" r=".9"/>'
             '<circle cx="0" cy="-6" r="1"/><circle cx="5" cy="-5" r=".9"/>',
    "king": '<path d="M-4.5 -3Q-5 -5 -2 -5L0 -2L2 -5Q5 -5 4.5 -3'
            'L2.5 1L3.5 4H-3.5L-2.5 1Z"/>'
            '<path d="M0 -8V-2M-2 -6H2" fill="none" stroke-width="1.2"/>',
}

Square = tuple[int, int]


@dataclass(frozen=True)
class Capture:
    day: Day
    piece: str
    origin: Square
    destination: Square
    lane: int
    side: int
    start: float


def legal_move(piece: str, origin: Square, destination: Square, side: int = 1) -> bool:
    """Validate chess geometry; calendar tokens are energy, not blocking pieces."""
    dx = destination[0] - origin[0]
    dy = destination[1] - origin[1]
    a, b = abs(dx), abs(dy)
    if a == b == 0:
        return False
    if piece == "pawn":
        return a == 1 and dy == side
    if piece == "knight":
        return (a, b) in ((1, 2), (2, 1))
    if piece == "bishop":
        return a == b
    if piece == "rook":
        return a == 0 or b == 0
    if piece == "queen":
        return a == b or a == 0 or b == 0
    if piece == "king":
        return max(a, b) == 1
    raise ValueError(f"Unknown chess piece: {piece}")


def _level(day: Day) -> int:
    if day.count == 0:
        return 0
    return max(1, day.level) if day.level is not None else min(4, day.count.bit_length())


def board_weeks(days: tuple[Day, ...]) -> int:
    return max(53, max((day.week + 1 for day in days), default=0))


def _edges(weeks: int) -> tuple[int, ...]:
    return tuple(i * weeks // LANES for i in range(LANES + 1))


def plan_captures(days: tuple[Day, ...]) -> tuple[Capture, ...]:
    """Prioritize stronger tokens per zone and schedule one piece per zone."""
    edges = _edges(board_weeks(days))
    active = {(d.week, d.weekday) for d in days if d.count}
    result = []
    for lane in range(LANES):
        left, right = edges[lane:lane + 2]
        targets = sorted(
            (d for d in days if d.count and left <= d.week < right),
            key=lambda d: (-_level(d), -d.count, d.date),
        )
        for i, day in enumerate(targets):
            target = (day.week, day.weekday)
            piece = PIECES[(i + lane) % len(PIECES)]
            side = 1 if (i + lane) % 2 == 0 else -1
            if piece == "pawn" and target[1] - side not in range(7):
                side = -side
            candidates = [
                (x, y) for x in range(left, right) for y in range(7)
                if legal_move(piece, (x, y), target, side)
            ]
            # Prefer empty launch squares and short but visible moves (2-4 cells).
            origin = min(candidates, key=lambda pos: (
                pos in active,
                abs(hypot(pos[0] - target[0], pos[1] - target[1]) - 3),
                abs(pos[0] - target[0]),
                pos,
            ))
            result.append(Capture(day, piece, origin, target, lane, side,
                                  FIRST_MOVE + i * CADENCE))
    return tuple(result)


def _point(square: Square) -> tuple[float, float]:
    return LEFT + square[0] * STEP + CELL / 2, TOP + square[1] * STEP + CELL / 2


def _track(name, values, times, cycle, mode="linear", translate=False):
    """Create complete SMIL timelines without duplicated key times."""
    values, times = list(values), list(times)
    if times[0] > 0:
        values.insert(0, values[0])
        times.insert(0, 0)
    if times[-1] < cycle:
        values.append(values[-1])
        times.append(cycle)
    keys = ";".join(f"{time / cycle:.9f}" for time in times)
    vals = ";".join(map(str, values))
    tag = "animateTransform" if translate else "animate"
    extra = ' type="translate"' if translate else ""
    return (
        f'<{tag} attributeName="{name}"{extra} values="{vals}" keyTimes="{keys}" '
        f'dur="{cycle:.6f}s" calcMode="{mode}" repeatCount="indefinite"/>'
    )


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


def _sprite_defs():
    parts = ['<defs>']
    for piece, shape in SHAPES.items():
        parts.append(f'<g id="chess-{piece}">{shape}'
                     '<path d="M-4 4H4L5 6H-5Z"/></g>')
    parts.append('</defs>')
    return parts


def _capture(move: Capture, cycle: float, p: dict) -> list[str]:
    x, y = _point(move.origin)
    tx, ty = _point(move.destination)
    s = move.start
    hit = s + ARRIVAL
    end = s + RESTORE
    gold = p["gold"]
    locations = [f"{x} {y}", f"{x} {y}"]
    times = [s, s+.22]
    if move.piece == "knight":
        locations.append(f"{(x+tx)/2} {(y+ty)/2-7}")
        times.append(s+.55)
    locations.append(f"{tx} {ty}")
    times.append(hit)
    fill = p["ivory"] if move.side == 1 else p["dark_piece"]
    stroke = p["ink"] if move.side == 1 else gold
    parts = [
        f'<g data-capture="{move.day.date.isoformat()}" data-piece="{move.piece}" '
        f'data-lane="{move.lane}" opacity="0">',
        _track("opacity", [0, 1, 1, 0], [s, s+.16, hit+.22, end], cycle),
        f'<path d="M{x} {y}L{tx} {ty}" stroke="{gold}" fill="none" '
        'stroke-width=".7" stroke-dasharray="2 3" opacity=".5"/>',
        f'<rect x="{tx-6}" y="{ty-6}" width="12" height="12" rx="2" '
        f'fill="none" stroke="{gold}" stroke-width="1"/>',
        f'<g transform="translate({x} {y})">',
        _track("transform", locations, times, cycle, translate=True),
        f'<ellipse cy="5" rx="5.8" ry="1.7" fill="#000000" opacity=".25"/>',
        f'<g fill="{fill}" stroke="{stroke}" color="{stroke}" '
        'stroke-width=".65" stroke-linejoin="round" stroke-linecap="round">',
        f'<use href="#chess-{move.piece}" xlink:href="#chess-{move.piece}"/>',
        '</g></g></g>',
        f'<circle cx="{tx}" cy="{ty}" r="4" fill="none" stroke="{gold}" '
        'stroke-width="1" opacity="0">',
        _track("opacity", [0, 1, 0], [hit-.04, hit+.07, end], cycle),
        _track("r", [4, 6+_level(move.day)], [hit, end], cycle),
        '</circle>',
    ]
    return parts


def render_chess(days: tuple[Day, ...], theme: str = "dark") -> str:
    p = PALETTES[theme]
    width = LEFT + board_weeks(days) * STEP + 16
    height = TOP + 7 * STEP + 17
    captures = plan_captures(days)
    cycle = max(4.0, max((m.start + CADENCE for m in captures), default=0) + .5)
    by_day = {move.day: move for move in captures}
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        'role="img" aria-label="GitChess strategic contribution calendar">',
        '<title>GitChess — every contribution is a strategic move</title>',
        f'<rect width="{width}" height="{height}" rx="6" fill="{p["bg"]}"/>',
        *_sprite_defs(),
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
        color = p["levels"][level-1] if level else p["empty"]
        parts.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
                     f'fill="{color}" data-date="{day.date.isoformat()}">')
        parts.append(f'<title>{day.date.isoformat()}: {day.count} contributions</title>')
        if day in by_day:
            s = by_day[day].start
            hit, end = s + ARRIVAL, s + RESTORE
            parts.append(_track("fill", [color, p["gold"], p["empty"], color],
                                [hit-.06, hit, hit+.22, end], cycle))
        parts.append('</rect>')
    parts.extend(['</g>', '<g id="chess-moves">'])
    for move in captures:
        parts.extend(_capture(move, cycle, p))
    parts.extend([
        '</g>',
        f'<text x="{LEFT}" y="{height-6}" fill="{p["gold"]}" font-size="8" '
        'letter-spacing="1.3" font-family="system-ui,sans-serif">GITCHESS</text>',
        '</svg>',
    ])
    return "\n".join(parts) + "\n"
