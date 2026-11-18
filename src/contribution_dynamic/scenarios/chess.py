"""GitChess: a quiet board and a turn-based team of chess attackers."""

from collections import deque
from dataclasses import dataclass
from math import hypot

from contribution_dynamic.animation import track
from contribution_dynamic.calendar import Day, month_label_positions

STEP = CELL = 13
LEFT = 47
TOP = 26
STAGING_ROW = 7
FIRST_MOVE = .12
TEAM = ("queen", "rook", "bishop", "knight")
PIECE_BY_LEVEL = {1: "pawn", 2: "knight", 3: "bishop", 4: "rook"}
FOCUS = 4
RADII = (1.1, 1.6, 2.1, 2.7)
CARDINAL = ((1, 0), (0, 1), (-1, 0), (0, -1))
DIAGONAL = ((1, 1), (-1, 1), (-1, -1), (1, -1))
JUMPS = ((1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2))
PALETTES = {
    "dark": {
        "bg": "#171e1b", "text": "#a6b5a9", "squares": ("#82927f", "#6d806e"),
        "frame": "#415347", "marker": "#344e3b", "enemy": "#222a25",
        "enemy_edge": "#c3cdbc", "ally": "#f5f1de", "ally_edge": "#29392d",
        "queen": "#f2d785", "gold": "#e9d48a",
    },
    "light": {
        "bg": "#f5f6ef", "text": "#53634f", "squares": ("#d5dfc8", "#bacbb0"),
        "frame": "#9aaf92", "marker": "#4e6c4b", "enemy": "#24352a",
        "enemy_edge": "#e1ead7", "ally": "#fffdf0", "ally_edge": "#344638",
        "queen": "#f4d78a", "gold": "#947232",
    },
}
Square = tuple[int, int]


@dataclass(frozen=True)
class Move:
    piece: str
    origin: Square
    destination: Square
    start: float
    arrive: float
    day: Day | None = None


@dataclass(frozen=True)
class Match:
    homes: tuple[tuple[str, Square], ...]
    moves: tuple[Move, ...]
    restore: float
    cycle: float


def legal_move(piece: str, origin: Square, destination: Square, side: int = 1) -> bool:
    dx, dy = destination[0] - origin[0], destination[1] - origin[1]
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
    return max(53, max((d.week + 1 for d in days), default=0))


def _inside(pos: Square, weeks: int) -> bool:
    return 0 <= pos[0] < weeks and 0 <= pos[1] <= STAGING_ROW


def destinations(piece, origin, enemies, allies, weeks):
    """Yield reachable chess squares; friendly pieces block but cannot be captured."""
    if piece == "knight":
        for dx, dy in JUMPS:
            pos = (origin[0]+dx, origin[1]+dy)
            if _inside(pos, weeks) and pos not in allies:
                yield pos
        return
    directions = {
        "queen": CARDINAL + DIAGONAL, "rook": CARDINAL, "bishop": DIAGONAL,
    }[piece]
    for dx, dy in directions:
        x, y = origin
        while True:
            x, y = x + dx, y + dy
            pos = (x, y)
            if not _inside(pos, weeks) or pos in allies:
                break
            yield pos
            if pos in enemies:
                break


def queen_rays(origin, occupied, weeks):
    yield from destinations("queen", origin, occupied, set(), weeks)


def _queen_has_exit(queen, allies, weeks):
    return any(_inside((queen[0]+dx, queen[1]+dy), weeks)
               and (queen[0]+dx, queen[1]+dy) not in allies
               for dx, dy in CARDINAL + DIAGONAL)


def _find_path(piece, origin, pending, allies, weeks, goal=None, queen=None):
    """Breadth-first search with enemy capture and friendly blocking."""
    queue = deque([origin])
    previous = {origin: None}
    enemies = set(pending)
    if goal == origin:
        return (origin,)
    while queue:
        current = queue.popleft()
        visible = tuple(destinations(piece, current, enemies, allies, weeks))
        if queen is not None:
            others = allies - {queen}
            visible = tuple(pos for pos in visible
                            if _queen_has_exit(queen, others | {pos}, weeks))
        targets = ([goal] if goal in visible else []) if goal is not None else [
            pos for pos in visible if pos in enemies
        ]
        if targets:
            target = min(targets, key=lambda pos: (
                hypot(pos[0]-current[0], pos[1]-current[1]), pos,
            ))
            path = [target, current]
            while previous[path[-1]] is not None:
                path.append(previous[path[-1]])
            return tuple(reversed(path))
        for pos in visible:
            if pos not in enemies and pos not in previous:
                previous[pos] = current
                queue.append(pos)
    return None


def plan_match(days: tuple[Day, ...]) -> Match | None:
    """Rotate attackers through legal moves; capture each contribution exactly once."""
    pending = {(d.week, d.weekday): d for d in days if d.count}
    if not pending:
        return None
    weeks = board_weeks(days)
    count = min(len(TEAM), len(pending))
    first = min(pending)[0]
    start_col = max(0, min(weeks-count, first-1))
    home_columns = sorted(range(start_col, start_col+count), key=lambda x: (abs(x-first), x))
    homes = tuple((piece, (col, STAGING_ROW))
                  for piece, col in zip(TEAM[:count], home_columns))
    positions = dict(homes)
    moves = []
    time = FIRST_MOVE
    fast = len(pending) > 100

    def append_move(piece, destination, day=None):
        nonlocal time
        origin = positions[piece]
        distance = hypot(destination[0]-origin[0], destination[1]-origin[1])
        duration = (.11 if fast else .21) + min(.40, distance * .028)
        arrive = time + duration
        moves.append(Move(piece, origin, destination, time, arrive, day))
        positions[piece] = destination
        time = arrive + (.065 if fast else .13)

    # Each piece takes a turn, following legal geometry even for preparatory moves.
    while pending:
        captured = False
        for piece, _ in homes:
            if not pending:
                break
            allies = {pos for other, pos in positions.items() if other != piece}
            queen = positions["queen"] if piece != "queen" else None
            path = _find_path(piece, positions[piece], pending, allies, weeks, queen=queen)
            if path is None:
                continue
            for pos in path[1:]:
                day = pending.pop(pos, None)
                append_move(piece, pos, day)
                captured |= day is not None
        if not captured:
            raise RuntimeError("No legal capture route for the attacking team")

    # Return through free squares. Reversing the forward sequence is a safe fallback
    # if a friendly piece temporarily occupies another piece's home.
    forward, final_positions, end = tuple(moves), positions.copy(), time
    for piece, home in reversed(homes):
        allies = {pos for other, pos in positions.items() if other != piece}
        path = _find_path(piece, positions[piece], {}, allies, weeks, goal=home)
        if path is None:
            moves[:] = forward
            positions.clear()
            positions.update(final_positions)
            time = end
            for move in reversed(forward):
                append_move(move.piece, move.origin)
            break
        for pos in path[1:]:
            append_move(piece, pos)
    restore = time + .12
    return Match(homes, tuple(moves), restore, max(4.0, restore + .65))


def _point(square):
    return LEFT + square[0] * STEP + CELL / 2, TOP + square[1] * STEP + CELL / 2


def _position(square):
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



def _attacker(piece, home, match, p):
    positions, times = [_position(home)], [0.0]
    moves = [m for m in match.moves if m.piece == piece]
    for move in moves:
        positions.extend((_position(move.origin), _position(move.destination)))
        times.extend((move.start, move.arrive))
    color = p["queen"] if piece == "queen" else p["ally"]
    parts = [
        f'<g data-attacker="{piece}" transform="translate({_position(home)})">',
    ]
    if moves:
        parts.append(track("transform", positions, times, match.cycle, transform=True))
    parts.extend([
        '<g transform="scale(.83)">',
        f'<g fill="{color}" stroke="{p["ally_edge"]}" stroke-width=".75" '
        'stroke-linejoin="round" stroke-linecap="round">',
        f'<use href="#chess-{piece}" xlink:href="#chess-{piece}"/>',
        '</g></g></g>',
    ])
    return parts


def _defender(move, reveal, match, p):
    day = move.day
    level = _level(day)
    x, y = _point(move.destination)
    kind = PIECE_BY_LEVEL[level]
    first = reveal == 0
    parts = []
    if not first:
        parts.extend([
            f'<circle data-reserve="{day.date.isoformat()}" cx="{x}" cy="{y}" '
            f'r="{RADII[level-1]}" fill="{p["marker"]}" opacity=".8">',
            track("opacity", [.8, 0, .8], [0, reveal, match.restore],
                  match.cycle, "discrete"),
            '</circle>',
        ])
    opacity = [1, 0, 1] if first else [0, 1, 0]
    times = [0, move.arrive, match.restore] if first else [0, reveal, move.arrive]
    parts.extend([
        f'<g data-piece="contribution" data-kind="{kind}" '
        f'data-piece-date="{day.date.isoformat()}" data-level="{level}" '
        f'transform="translate({x} {y}) scale(.75)" opacity="{int(first)}">',
        track("opacity", opacity, times, match.cycle, "discrete"),
        f'<g fill="{p["enemy"]}" stroke="{p["enemy_edge"]}" stroke-width=".55" '
        'stroke-linejoin="round">',
        f'<use href="#chess-{kind}" xlink:href="#chess-{kind}"/></g></g>',
    ])
    return parts


def _highlight(move, match, p):
    parts = []
    for pos in (move.origin, move.destination):
        x, y = _point(pos)
        parts.extend([
            f'<rect x="{x-CELL/2}" y="{y-CELL/2}" width="{CELL}" height="{CELL}" '
            f'fill="{p["gold"]}" opacity="0" data-move="{move.piece}">',
            track("opacity", [0, .32, .32, 0],
                  [move.start-.01, move.start, move.arrive, move.arrive+.05], match.cycle),
            '</rect>',
        ])
    return parts


def render_chess(days: tuple[Day, ...], theme: str = "dark") -> str:
    p = PALETTES[theme]
    weeks = board_weeks(days)
    width = LEFT + weeks * STEP + 16
    height = TOP + 8 * STEP + 19
    match = plan_match(days)
    captures = [m for m in match.moves if m.day is not None] if match else []
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        'role="img" aria-label="GitChess turn-based contribution tactics">',
        '<title>GitChess — tactical play</title>',
        f'<rect width="{width}" height="{height}" rx="6" fill="{p["bg"]}"/>',
        *_sprite_defs(),
        '<g id="month-labels" font-family="Georgia,serif" font-size="10.5" '
        f'letter-spacing=".2" fill="{p["text"]}">',
    ]
    for x, name in month_label_positions(days, LEFT, STEP, width):
        parts.append(f'<text x="{x}" y="15">{name}</text>')
    parts.extend([
        '</g>',
        f'<rect x="{LEFT-2}" y="{TOP-2}" width="{weeks*STEP+4}" height="{8*STEP+4}" '
        f'rx="1" fill="{p["frame"]}"/>',
        '<g id="staging">',
    ])
    for week in range(weeks):
        color = p["squares"][(week+STAGING_ROW) % 2]
        parts.append(f'<rect x="{LEFT+week*STEP}" y="{TOP+STAGING_ROW*STEP}" '
                     f'width="{CELL}" height="{CELL}" fill="{color}"/>')
    parts.extend(['</g>', '<g id="calendar">'])
    for day in sorted(days, key=lambda d: (d.week, d.weekday)):
        x, y = LEFT + day.week * STEP, TOP + day.weekday * STEP
        color = p["squares"][(day.week + day.weekday) % 2]
        parts.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                     f'fill="{color}" data-date="{day.date.isoformat()}" '
                     f'data-level="{_level(day)}">')
        parts.append(f'<title>{day.date.isoformat()}: {day.count} contributions</title></rect>')
    parts.extend(['</g>', '<g id="move-highlights">'])
    if match:
        for move in match.moves:
            parts.extend(_highlight(move, match, p))
    parts.extend(['</g>', '<g id="contribution-pieces">'])
    if match:
        for i, move in enumerate(captures):
            reveal = 0 if i < FOCUS else captures[i-FOCUS].arrive + .02
            parts.extend(_defender(move, reveal, match, p))
    parts.extend(['</g>', '<g id="attackers">'])
    if match:
        for piece, home in match.homes:
            parts.extend(_attacker(piece, home, match, p))
    parts.extend([
        '</g>',
        f'<text x="{LEFT}" y="{height-6}" fill="{p["text"]}" font-size="8" '
        'letter-spacing="1.2" font-family="system-ui,sans-serif">GITCHESS</text>',
        '</svg>',
    ])
    return "\n".join(parts) + "\n"
