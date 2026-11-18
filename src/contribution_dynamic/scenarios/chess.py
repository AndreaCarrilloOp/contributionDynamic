"""GitChess: one persistent golden queen captures level-coded contribution pieces."""

from collections import deque
from dataclasses import dataclass
from math import hypot

from contribution_dynamic.animation import track
from contribution_dynamic.calendar import Day, month_label_positions

STEP = 13
CELL = 10
LEFT = 47
TOP = 30
FIRST_MOVE = .12
STAGING_ROW = 7
PIECE_BY_LEVEL = {1: "pawn", 2: "knight", 3: "bishop", 4: "rook"}
PIECE_SCALES = {1: .48, 2: .56, 3: .62, 4: .70}
DIRECTIONS = ((1, 0), (0, 1), (-1, 0), (0, -1),
              (1, 1), (-1, 1), (-1, -1), (1, -1))
PALETTES = {
    "dark": {
        "bg": "#111417", "text": "#d6c6a8", "squares": ("#f3e4bf", "#8f6c47"),
        "piece": "#1d2229", "piece_edge": "#fff2d6",
        "queen": "#ffd45c", "queen_edge": "#6a4708", "gold": "#f0c94d",
    },
    "light": {
        "bg": "#faf8f3", "text": "#574636", "squares": ("#f3e4bf", "#8f6c47"),
        "piece": "#20242b", "piece_edge": "#fff2d6",
        "queen": "#f2c94c", "queen_edge": "#6a4708", "gold": "#d4a72c",
    },
}
Square = tuple[int, int]


@dataclass(frozen=True)
class Move:
    origin: Square
    destination: Square
    start: float
    arrive: float
    day: Day | None = None


@dataclass(frozen=True)
class Match:
    home: Square
    moves: tuple[Move, ...]
    restore: float
    cycle: float


def legal_move(piece: str, origin: Square, destination: Square, side: int = 1) -> bool:
    """Validate chess geometry; blocking is handled by the queen route planner."""
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
    if not day.count:
        return 0
    return max(1, day.level) if day.level is not None else min(4, day.count.bit_length())


def board_weeks(days: tuple[Day, ...]) -> int:
    return max(53, max((d.week + 1 for d in days), default=0))


def queen_rays(origin: Square, occupied: set[Square], weeks: int):
    """Yield legal destinations, ending each ray at its first standing piece."""
    for dx, dy in DIRECTIONS:
        x, y = origin
        while True:
            x, y = x + dx, y + dy
            if not (0 <= x < weeks and 0 <= y <= STAGING_ROW):
                break
            pos = (x, y)
            yield pos
            if pos in occupied:
                break


def _path_to_capture(origin: Square, pending: dict[Square, Day], weeks: int):
    """Find a visible piece, or the shortest legal sequence of empty queen moves."""
    occupied = set(pending)
    queue = deque([origin])
    previous = {origin: None}
    while queue:
        current = queue.popleft()
        visible = tuple(queen_rays(current, occupied, weeks))
        targets = [pos for pos in visible if pos in occupied]
        if targets:
            target = min(targets, key=lambda pos: (
                hypot(pos[0]-current[0], pos[1]-current[1]),
                -_level(pending[pos]), pos,
            ))
            path = [target, current]
            while previous[path[-1]] is not None:
                path.append(previous[path[-1]])
            return tuple(reversed(path))
        for pos in visible:
            if pos not in previous:
                previous[pos] = current
                queue.append(pos)
    raise RuntimeError("No queen route to a remaining piece")


def plan_match(days: tuple[Day, ...]) -> Match | None:
    """Capture every active day exactly once, then return and restore the board."""
    pending = {(d.week, d.weekday): d for d in days if d.count}
    if not pending:
        return None
    weeks = board_weeks(days)
    home = (min(pending)[0], STAGING_ROW)
    current = home
    moves = []
    time = FIRST_MOVE

    def append_move(destination: Square, day: Day | None = None):
        nonlocal current, time
        distance = hypot(destination[0]-current[0], destination[1]-current[1])
        duration = .16 + min(.70, distance * .045)
        arrive = time + duration
        moves.append(Move(current, destination, time, arrive, day))
        current = destination
        time = arrive + (.12 if day is not None else .035)

    while pending:
        path = _path_to_capture(current, pending, weeks)
        for pos in path[1:]:
            append_move(pos, pending.pop(pos, None))

    # The board is now empty: return via the staging row using legal queen moves.
    for pos in ((current[0], STAGING_ROW), home):
        if current != pos:
            append_move(pos)
    restore = time + .08
    return Match(home, tuple(moves), restore, max(4.0, restore + .35))


def _point(square: Square) -> tuple[float, float]:
    return LEFT + square[0] * STEP + CELL / 2, TOP + square[1] * STEP + CELL / 2


def _position(square: Square) -> str:
    x, y = _point(square)
    return f"{x} {y}"


def _sprite_defs():
    return [
        '<defs>',
        '<g id="chess-pawn"><circle cy="-4" r="2.6"/>',
        '<path d="M-1.7 -1.5H1.7Q1.7 1 3.5 4H-3.5Q-1.7 1 -1.7 -1.5Z"/>',
        '<path d="M-3.5 4H3.5L4.5 6H-4.5Z"/></g>',
        '<g id="chess-knight">',
        '<path d="M-4.5 4L-3.5 1L-1 -1L-4.4 -.6L-5 -3L-1.5 -6'
        'L-1.2 -8L.5 -6.7C4.5 -6 5 -1 3.4 4Z"/>',
        '<circle cx="-1.3" cy="-3.9" r=".65" fill="#fff2d6" stroke="none"/>',
        '<path d="M-4 4H4L5 6H-5Z"/></g>',
        '<g id="chess-bishop">',
        '<path d="M0 -7Q5 -3 2.5 -.5L1.5 .5L3.5 4H-3.5L-1.5 .5'
        'Q-5 -2 0 -7Z"/>',
        '<path d="M.3 -5.4L-1 -2.4" fill="none"/>',
        '<path d="M-4 4H4L5 6H-5Z"/></g>',
        '<g id="chess-rook">',
        '<path d="M-5 -6H-3V-3.8H-1V-6H1V-3.8H3V-6H5V-1.5'
        'L3 0L3.5 4H-3.5L-3 0L-5 -1.5Z"/>',
        '<path d="M-4 4H4L5 6H-5Z"/></g>',
        '<g id="chess-queen">',
        '<path d="M-5 -4L-2.5 -1L0 -5L2.5 -1L5 -4L3.1 1L3.7 4H-3.7L-3.1 1Z"/>',
        '<circle cx="-5" cy="-5" r=".9"/><circle cy="-6" r="1"/>',
        '<circle cx="5" cy="-5" r=".9"/><path d="M-4 4H4L5 6H-5Z"/>',
        '</g></defs>',
    ]


def _queen(match: Match, p: dict) -> list[str]:
    positions, times = [_position(match.home)], [0.0]
    for move in match.moves:
        positions.extend((_position(move.origin), _position(move.destination)))
        times.extend((move.start, move.arrive))
    return [
        f'<g data-piece="queen" transform="translate({_position(match.home)})">',
        track("transform", positions, times, match.cycle, transform=True),
        '<ellipse cy="5" rx="5.8" ry="1.6" fill="#000000" opacity=".25"/>',
        f'<g fill="{p["queen"]}" stroke="{p["queen_edge"]}" stroke-width=".7" '
        'stroke-linejoin="round" stroke-linecap="round">',
        '<use href="#chess-queen" xlink:href="#chess-queen"/>',
        '</g></g>',
    ]


def render_chess(days: tuple[Day, ...], theme: str = "dark") -> str:
    p = PALETTES[theme]
    width = LEFT + board_weeks(days) * STEP + 16
    height = TOP + 8 * STEP + 19
    match = plan_match(days)
    by_day = {m.day: m for m in match.moves if m.day is not None} if match else {}
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        'role="img" aria-label="GitChess queen captures contribution pieces">',
        '<title>GitChess — one queen against many pieces</title>',
        f'<rect width="{width}" height="{height}" rx="6" fill="{p["bg"]}"/>',
        *_sprite_defs(),
        f'<g font-family="system-ui,sans-serif" font-size="10" fill="{p["text"]}">',
    ]
    for x, name in month_label_positions(days, LEFT, STEP, width):
        parts.append(f'<text x="{x}" y="14">{name}</text>')
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(f'<text x="10" y="{TOP+row*STEP+8}">{name}</text>')
    parts.extend(['</g>', '<g id="calendar">'])
    for day in sorted(days, key=lambda d: (d.week, d.weekday)):
        x, y = LEFT + day.week * STEP, TOP + day.weekday * STEP
        level = _level(day)
        color = p["squares"][(day.week + day.weekday) % 2]
        parts.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx=".5" '
                     f'fill="{color}" data-date="{day.date.isoformat()}" '
                     f'data-level="{level}">')
        parts.append(f'<title>{day.date.isoformat()}: {day.count} contributions</title>')
        if match and day in by_day:
            hit = by_day[day].arrive
            parts.append(track("fill", [color, p["gold"], color],
                               [hit-.035, hit, hit+.15], match.cycle))
        parts.append('</rect>')
    parts.extend(['</g>', '<g id="contribution-pieces">'])
    if match:
        for day, move in by_day.items():
            level = _level(day)
            x, y = _point(move.destination)
            kind = PIECE_BY_LEVEL[level]
            scale = PIECE_SCALES[level]
            parts.append(f'<g data-piece="contribution" data-kind="{kind}" '
                         f'data-piece-date="{day.date.isoformat()}" '
                         f'data-level="{level}" data-scale="{scale}" opacity="1" '
                         f'transform="translate({x} {y}) scale({scale})">')
            parts.append(track("opacity", [1, 0, 1],
                               [0, move.arrive, match.restore], match.cycle, "discrete"))
            parts.append(f'<g fill="{p["piece"]}" stroke="{p["piece_edge"]}" '
                         'stroke-width=".8" stroke-linejoin="round">')
            parts.append(f'<use href="#chess-{kind}" xlink:href="#chess-{kind}"/></g></g>')
    parts.extend(['</g>', '<g id="capture-effects">'])
    if match:
        for move in by_day.values():
            x, y = _point(move.destination)
            hit = move.arrive
            parts.extend([
                f'<circle data-capture="{move.day.date.isoformat()}" cx="{x}" cy="{y}" '
                f'r="3" fill="none" stroke="{p["gold"]}" stroke-width="1.1" opacity="0">',
                track("opacity", [0, 1, 0], [hit-.02, hit, hit+.18], match.cycle),
                track("r", [3, 7], [hit, hit+.18], match.cycle),
                '</circle>',
            ])
    parts.extend(['</g>', '<g id="queen">'])
    if match:
        parts.extend(_queen(match, p))
    parts.extend([
        '</g>',
        f'<text x="{LEFT}" y="{height-6}" fill="{p["gold"]}" font-size="8" '
        'letter-spacing="1.3" font-family="system-ui,sans-serif">GITCHESS</text>',
        '</svg>',
    ])
    return "\n".join(parts) + "\n"
