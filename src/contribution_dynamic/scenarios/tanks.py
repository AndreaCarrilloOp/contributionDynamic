"""GitTanks: golden maze tank against waves of silver invaders."""

from collections import deque
from dataclasses import dataclass
from math import atan2, cos, degrees, radians, sin

from contribution_dynamic.animation import track
from contribution_dynamic.calendar import Day

STEP = 13
CELL = 10
LEFT = 47
TOP = 39
FIRST = .12
BASE = TOP + 7 * STEP + 15
MAX_ENEMIES = 3
WAVE_BRICKS = 5
CHASE_ROUNDS = 10
ROLES = ("hunter", "ambusher", "flanker")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
PALETTES = {
    "dark": {
        "bg": "#080808", "empty": "#101010", "text": "#b7b3a6",
        "tiles": ("#99501e", "#bb621f", "#da7d27", "#f3a342"),
        "mortar": "#663819", "brick_light": "#ffd08a", "brick_shadow": "#633311",
        "hero": "#d9b21f", "hero_top": "#ffe16a", "hero_edge": "#59400a",
        "hero_shadow": "#95700c", "tracks": "#34332e", "metal": "#ccc3a1",
        "enemy": "#b9c2c8", "enemy_top": "#f2f5f5", "enemy_shadow": "#737e85",
        "enemy_edge": "#46515a", "shield": "#90c8e8",
        "fire": "#ff8624", "core": "#fff3b0",
    },
    "light": {
        "bg": "#faf6eb", "empty": "#eee8db", "text": "#675b48",
        "tiles": ("#f4c38d", "#dfa062", "#c87934", "#a95b22"),
        "mortar": "#805027", "brick_light": "#ffe2b0", "brick_shadow": "#783f1c",
        "hero": "#be8d10", "hero_top": "#ffe16a", "hero_edge": "#59400a",
        "hero_shadow": "#8c6008", "tracks": "#38372f", "metal": "#b8ac86",
        "enemy": "#7a8791", "enemy_top": "#cbd4d7", "enemy_shadow": "#4a5964",
        "enemy_edge": "#35424b", "shield": "#237fae",
        "fire": "#e76614", "core": "#fff1a1",
    },
}


Point = tuple[float, float]
Square = tuple[int, int]
DIRECTIONS = ((1, 0), (0, 1), (-1, 0), (0, -1))


@dataclass(frozen=True)
class Attack:
    source: Square
    target: Square
    fire: float
    hit: float
    enter: float
    day: Day | None = None
    enemy: int | None = None
    counter: float | None = None
    shield_hit: float | None = None
    spawn: float | None = None


@dataclass(frozen=True)
class EnemyRoute:
    enemy: int
    role: str
    positions: tuple[Square, ...]
    times: tuple[float, ...]


@dataclass(frozen=True)
class Battle:
    spawn: Square
    positions: tuple[Square, ...]
    times: tuple[float, ...]
    angles: tuple[float, ...]
    attacks: tuple[Attack, ...]
    cycle: float
    enemies: tuple[EnemyRoute, ...] = ()


def _level(day: Day) -> int:
    if not day.count:
        return 0
    return max(1, day.level) if day.level is not None else min(4, day.count.bit_length())


def board_weeks(days: tuple[Day, ...]) -> int:
    return max(53, max((d.week + 1 for d in days), default=0))


def base_x(days: tuple[Day, ...]) -> float:
    return LEFT + (board_weeks(days)-1)*STEP/2 + CELL/2


def _center(week: int, row: int) -> Point:
    return LEFT + week*STEP + CELL/2, TOP + row*STEP + CELL/2


def _position(point: Point) -> str:
    return f"{point[0]:.3f} {point[1]:.3f}"


def _angle(a: Point, b: Point) -> float:
    return degrees(atan2(b[1]-a[1], b[0]-a[0]))


def _toward(a: Point, b: Point, distance: float) -> Point:
    theta = radians(_angle(a, b))
    return a[0]+cos(theta)*distance, a[1]+sin(theta)*distance


def _neighbors(pos: Square, width: int, spawn: Square):
    for dx, dy in DIRECTIONS:
        candidate = pos[0]+dx, pos[1]+dy
        if candidate == spawn or (0 <= candidate[0] < width and 0 <= candidate[1] < 7):
            yield candidate


def _paths(start, blocked, width, spawn):
    """BFS parent map; all discovered squares are traversable."""
    parents = {start: None}
    queue = deque([start])
    while queue:
        pos = queue.popleft()
        for neighbor in _neighbors(pos, width, spawn):
            if neighbor not in blocked and neighbor not in parents:
                parents[neighbor] = pos
                queue.append(neighbor)
    return parents


def _path(parents, end):
    route = [end]
    while parents[route[-1]] is not None:
        route.append(parents[route[-1]])
    return tuple(reversed(route))


def _approach(start, blocked, targets, width, spawn):
    """Find the closest reachable firing square adjacent to a blocked target."""
    parents = _paths(start, blocked, width, spawn)
    for pos in parents:
        for neighbor in _neighbors(pos, width, spawn):
            if neighbor in targets:
                return _path(parents, pos), neighbor
    raise ValueError("No reachable target")


def _distance(a: Square, b: Square) -> int:
    return abs(a[0]-b[0]) + abs(a[1]-b[1])


def _enemy_positions(current, blocked, width, spawn, count, cleared):
    parents = _paths(current, blocked, width, spawn)
    candidates = [pos for pos in parents if pos not in (current, spawn)]
    distances = {pos: len(_path(parents, pos))-1 for pos in candidates}
    chosen = []
    while candidates and len(chosen) < count:
        # Prefer several approach directions and avoid distant, inactive waiting.
        target = min(candidates, key=lambda pos: (
            abs(distances[pos]-5)
            - min(5, min((_distance(pos, other) for other in chosen), default=0))*.8,
            pos not in cleared,
            pos,
        ))
        chosen.append(target)
        candidates.remove(target)
    return tuple(chosen)


def _chase_step(position, hero, heading, role, blocked, width, spawn):
    """Find one legal BFS step toward a role-specific interception square."""
    parents = _paths(position, blocked | {hero, spawn}, width, spawn)
    goals = [pos for pos in _neighbors(hero, width, spawn) if pos in parents]
    if not goals:
        return position
    dx, dy = heading
    preferred = hero
    if role == "ambusher":
        preferred = hero[0]+dx, hero[1]+dy
    elif role == "flanker":
        preferred = hero[0]-dy, hero[1]+dx
    destination = min(goals, key=lambda pos: (
        len(_path(parents, pos)) + _distance(pos, preferred)*.85,
        pos,
    ))
    route = _path(parents, destination)
    return route[1] if len(route) > 1 else position


def plan_battle(days: tuple[Day, ...]) -> Battle | None:
    """Clear active bricks with one tank, then fight enemies on open grid squares."""
    bricks = {(d.week, d.weekday): d for d in days if d.count}
    if not bricks:
        return None
    width = board_weeks(days)
    first = min(bricks)
    # Prefer an actual inactive day. Dense or partial boards may need a nearby
    # blank square; a completely full board uses a single top-edge entry square.
    free = [(d.week, d.weekday) for d in days if not d.count]
    if not free:
        free = [(x, y) for x in range(width) for y in range(7) if (x, y) not in bricks]
    spawn = min(free, key=lambda pos: (
        abs(pos[0]-first[0])+abs(pos[1]-first[1]), pos,
    )) if free else (first[0], -1)
    blocked = set(bricks)
    cleared = set()
    positions = [spawn, spawn]
    times = [0.0, FIRST]
    angles = [90.0, 90.0]
    attacks = []
    enemy_routes = []
    clock = FIRST
    enemy_id = 0
    heading = (1, 0)

    def pose(pos, t, angle):
        nonlocal clock
        positions.append(pos)
        times.append(t)
        angles.append(angle)
        clock = t

    def turn(target):
        pos = positions[-1]
        desired = _angle(_center(*pos), _center(*target))
        previous = angles[-1]
        angle = previous + (desired-previous+180) % 360 - 180
        pose(pos, clock+.07, angle)

    def walk(route):
        nonlocal heading
        for pos in route[1:]:
            prior = positions[-1]
            heading = pos[0]-prior[0], pos[1]-prior[1]
            turn(pos)
            pose(pos, clock+.11, angles[-1])

    def engage(target, day=None, enemy=None, born=None):
        source = positions[-1]
        turn(target)
        counter = shield_hit = None
        if enemy is not None:
            counter = clock+.04
            shield_hit = counter+.12
            pose(source, shield_hit+.08, angles[-1])
        fire = clock+.04
        hit = fire+.12
        pose(source, hit+.16, angles[-1])
        pose(target, clock+.11, angles[-1])
        attacks.append(Attack(source, target, fire, hit, clock, day, enemy,
                              counter, shield_hit, born))

    while blocked:
        count = min(WAVE_BRICKS, len(blocked))
        for _ in range(count):
            route, target = _approach(positions[-1], blocked, blocked, width, spawn)
            walk(route)
            engage(target, day=bricks[target])
            blocked.remove(target)
            cleared.add(target)
        spawns = _enemy_positions(
            positions[-1], blocked, width, spawn, min(MAX_ENEMIES, count), cleared,
        )
        if not spawns:
            continue
        born = clock
        living = {enemy_id+i: pos for i, pos in enumerate(spawns)}
        roles = {key: ROLES[i] for i, key in enumerate(living)}
        enemy_id += len(living)
        trails = {key: ([pos], [born]) for key, pos in living.items()}
        pose(positions[-1], clock+.16, angles[-1])

        def defeat(key):
            target = living[key]
            engage(target, enemy=key, born=born)
            path, ticks = trails[key]
            enemy_routes.append(EnemyRoute(key, roles[key], tuple(path), tuple(ticks)))
            del living[key]

        for round_index in range(CHASE_ROUNDS):
            if not living:
                break
            hero = positions[-1]
            # Fire immediately when a pursuer reaches an adjacent square.
            close = [key for key, pos in living.items() if _distance(hero, pos) == 1]
            if close:
                defeat(min(close))
                continue
            obstacles = blocked | set(living.values())
            # Keep clearing the maze while enemies approach. If the corridor
            # is cut off, advance toward an enemy instead of crossing a wall.
            goals = blocked if blocked and round_index < 5 else set(living.values())
            try:
                route, target = _approach(hero, obstacles, goals, width, spawn)
            except ValueError:
                route, target = _approach(
                    hero, obstacles, set(living.values()), width, spawn,
                )
            if len(route) > 1:
                walk(route[:2])
            elif target in blocked:
                engage(target, day=bricks[target])
                blocked.remove(target)
                cleared.add(target)
            else:
                defeat(next(key for key, pos in living.items() if pos == target))
                continue

            # Enemies pursue in the same tick. Reserve every old square plus
            # each chosen destination to prohibit overlap and head-on swaps.
            occupied = set(living.values())
            reserved = set()
            next_positions = {}
            for key, pos in living.items():
                destination = _chase_step(
                    pos, positions[-1], heading, roles[key],
                    blocked | (occupied - {pos}) | reserved, width, spawn,
                )
                next_positions[key] = destination
                reserved.add(destination)
            begin, finish = clock, clock+.18
            for key, destination in next_positions.items():
                pos = living[key]
                if destination != pos:
                    path, ticks = trails[key]
                    if begin > ticks[-1]:
                        path.append(pos)
                        ticks.append(begin)
                    path.append(destination)
                    ticks.append(finish)
            living.update(next_positions)
            pose(positions[-1], finish, angles[-1])

        # A bounded pursuit phase guarantees progress even on narrow mazes.
        while living:
            route, target = _approach(
                positions[-1], blocked | set(living.values()),
                set(living.values()), width, spawn,
            )
            walk(route)
            defeat(next(key for key, pos in living.items() if pos == target))
        pose(positions[-1], clock+.10, angles[-1])

    # With all bricks destroyed the hero can return through open lanes.
    parents = _paths(positions[-1], set(), width, spawn)
    walk(_path(parents, spawn))
    previous = angles[-1]
    home_angle = previous + (90-previous+180) % 360 - 180
    pose(spawn, clock+.15, home_angle)
    # Reset only when the hero is safely back at its starting square.
    return Battle(spawn, tuple(positions), tuple(times), tuple(angles),
                  tuple(attacks), max(4.0, clock+.6),
                  tuple(sorted(enemy_routes, key=lambda enemy: enemy.enemy)))


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



def _tank_sprite(p: dict, side: str = "hero") -> list[str]:
    """An original pixel-inspired silhouette, facing right, with a seven-unit muzzle."""
    return [
        '<g data-sprite="retro-tank" shape-rendering="crispEdges">',
        # Dark track beds with bright, square tread links.
        f'<path d="M-5 -5H5V-2H-5ZM-5 2H5V5H-5Z" fill="{p["tracks"]}"/>',
        f'<path d="M-4.5 -4.5H4.5M-4.5 4.5H4.5" stroke="{p["metal"]}" '
        'stroke-width="1" stroke-dasharray="1.2 1.1"/>',
        f'<path d="M-4 -3H4V3H-4Z" fill="{p[f"{side}_shadow"]}" '
        f'stroke="{p[f"{side}_edge"]}" stroke-width="1"/>',
        f'<path d="M-3 -2.5H3V2H-3Z" fill="{p[side]}"/>',
        f'<path d="M-3 -2H2V-1H-3Z" fill="{p[f"{side}_top"]}" opacity=".8"/>',
        # Octagonal turret and a broad, beveled cannon. The tip matches _impact.
        f'<path d="M0 -1H7V1H0Z" fill="{p[f"{side}_top"]}" '
        f'stroke="{p[f"{side}_edge"]}" stroke-width=".55"/>',
        f'<path d="M-2 -3H1L3 -1V1L1 3H-2L-3 1V-1Z" '
        f'fill="{p[side]}" stroke="{p[f"{side}_edge"]}" stroke-width=".6"/>',
        f'<path d="M-2 -2H1L2 -1H-2Z" fill="{p[f"{side}_top"]}"/>',
        f'<rect x="-.8" y="-.8" width="1.6" height="1.6" fill="{p[f"{side}_shadow"]}"/>',
        '</g>',
    ]



def _projectile(origin, target, fire, hit, cycle, p, side):
    muzzle = _toward(origin, target, 7)
    return [
        f'<g data-projectile="{side}" opacity="0" transform="translate({_position(muzzle)})">',
        track("opacity", [0, 1, 1, 0], [fire-.01, fire, hit-.01, hit], cycle),
        track("transform", [_position(muzzle), _position(target)], [fire, hit],
              cycle, transform=True),
        f'<rect x="-1.2" y="-1.2" width="2.4" height="2.4" fill="{p["core"]}" '
        f'stroke="{p["fire"]}" stroke-width=".5"/>',
        '</g>',
    ]


def _explosion(point, hit, cycle, p, radius=7):
    end = hit+.24
    return [
        f'<g data-impact="true" opacity="0" transform="translate({_position(point)})">',
        track("opacity", [0, 1, .7, 0], [hit-.01, hit, hit+.08, end], cycle),
        f'<circle r="2" fill="none" stroke="{p["fire"]}" stroke-width="1.4">',
        track("r", [2, radius], [hit, end], cycle),
        '</circle>',
        f'<path d="M-4 0L0 -4L4 0L0 4Z" fill="{p["core"]}"/>',
        '<path d="M-5 -3l-2 -2M5 -3l2 -2M-4 4l-2 2M4 4l2 2" '
        f'stroke="{p["fire"]}" stroke-width="1.6"/>',
        '</g>',
    ]


def _hero(battle, p):
    positions = [_position(_center(*pos)) for pos in battle.positions]
    return [
        f'<g data-tank="hero" transform="translate({positions[0]})">',
        track("transform", positions, battle.times, battle.cycle, transform=True),
        '<g transform="rotate(90)">',
        track("transform", [f"{a:.2f}" for a in battle.angles], battle.times,
              battle.cycle, transform=True).replace('type="translate"', 'type="rotate"'),
        *_tank_sprite(p, "hero"),
        '</g></g>',
    ]


def _enemy(attack, route, cycle, p):
    positions = [_position(_center(*pos)) for pos in route.positions]
    aim = _angle(_center(*attack.target), _center(*attack.source))
    angles, angle_times = [90], [attack.spawn]
    for a, b, t in zip(route.positions, route.positions[1:], route.times[1:]):
        if a != b:
            angles.append(_angle(_center(*a), _center(*b)))
            angle_times.append(t)
    angles.append(aim)
    angle_times.append(attack.counter-.03)
    return [
        f'<g data-tank="enemy" data-enemy="{attack.enemy}" data-role="{route.role}" '
        f'opacity="0" transform="translate({positions[0]})">',
        track("opacity", [0, 1, 1, 0],
              [attack.spawn, attack.spawn+.12, attack.hit-.015, attack.hit], cycle),
        track("transform", positions, route.times, cycle, transform=True),
        '<g transform="rotate(90)">',
        track("transform", angles, angle_times, cycle, "discrete",
              transform=True).replace('type="translate"', 'type="rotate"'),
        *_tank_sprite(p, "enemy"),
        '</g></g>',
    ]


def _combat(attack, cycle, p):
    origin, target = _center(*attack.source), _center(*attack.target)
    label = attack.day.date.isoformat() if attack.day is not None else attack.enemy
    parts = [f'<g data-shot="{label}">']
    if attack.enemy is not None:
        parts.extend(_projectile(target, origin, attack.counter,
                                 attack.shield_hit, cycle, p, "enemy"))
        parts.extend([
            f'<circle cx="{origin[0]}" cy="{origin[1]}" r="7" fill="none" '
            f'stroke="{p["shield"]}" stroke-width="1.4" opacity="0">',
            track("opacity", [0, 1, 0],
                  [attack.shield_hit-.02, attack.shield_hit, attack.shield_hit+.16], cycle),
            '</circle>',
        ])
    parts.extend(_projectile(origin, target, attack.fire, attack.hit, cycle, p, "hero"))
    parts.extend(_explosion(target, attack.hit, cycle, p,
                            5+_level(attack.day) if attack.day else 8))
    parts.append('</g>')
    return parts


def _eagle(center, p):
    """Keep the eagle as a visual base, not a replacement for maze navigation."""
    return [
        f'<g data-base="eagle" transform="translate({center} {BASE})">',
        f'<rect x="-10" y="-9" width="20" height="18" rx="1" fill="{p["empty"]}" '
        f'stroke="{p["brick_shadow"]}" stroke-width="1.3"/>',
        '<path d="M-8 -6H-5V-4H-3V-2H-1V-5H1V-6H4V-3H2V-2H4V-4'
        'H6V-6H8V-1H6V1H3V4H5V6H-5V4H-3V1H-6V-1H-8Z" '
        f'fill="{p["hero_top"]}" stroke="{p["hero_edge"]}" stroke-width=".6"/>',
        '</g>',
    ]


def render_tanks(days: tuple[Day, ...], theme: str = "dark") -> str:
    p = PALETTES[theme]
    weeks, center = board_weeks(days), base_x(days)
    width, height = LEFT+weeks*STEP+16, BASE+23
    battle = plan_battle(days)
    cycle = battle.cycle if battle else 4.0
    by_day = {a.day: a for a in battle.attacks if a.day} if battle else {}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        'aria-label="GitTanks golden tank navigates the contribution maze">',
        '<title>GitTanks — one versus many</title>',
        f'<rect width="{width}" height="{height}" rx="6" fill="{p["bg"]}"/>',
        f'<g font-family="system-ui,sans-serif" font-size="10" fill="{p["text"]}">',
    ]
    for week, label in _months(days):
        parts.append(f'<text x="{LEFT+week*STEP}" y="14">{label}</text>')
    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(f'<text x="10" y="{TOP+row*STEP+8}">{label}</text>')
    parts.extend(['</g>', '<g id="calendar">'])
    for day in sorted(days, key=lambda d: (d.week, d.weekday)):
        x, y = LEFT+day.week*STEP, TOP+day.weekday*STEP
        level = _level(day)
        color = p["tiles"][level-1] if level else p["empty"]
        parts.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="1" '
                     f'fill="{color}" data-date="{day.date.isoformat()}" data-level="{level}">')
        parts.append(f'<title>{day.date.isoformat()}: {day.count} contributions</title>')
        if day in by_day:
            attack = by_day[day]
            parts.append(track("fill", [color, p["empty"], color],
                               [0, attack.hit, cycle], cycle, "discrete"))
        parts.append('</rect>')
    parts.extend(['</g>', '<g id="brick-detail">'])
    for day in sorted(by_day, key=lambda d: (d.week, d.weekday)):
        x, y = LEFT+day.week*STEP, TOP+day.weekday*STEP
        attack = by_day[day]
        parts.append(f'<g data-brick="{day.date.isoformat()}" '
                     'shape-rendering="crispEdges" opacity="1">')
        parts.append(track("opacity", [1, 0, 1], [0, attack.hit, cycle],
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
    if battle:
        routes = {route.enemy: route for route in battle.enemies}
        for attack in battle.attacks:
            if attack.enemy is not None:
                parts.extend(_enemy(attack, routes[attack.enemy], cycle, p))
            parts.extend(_combat(attack, cycle, p))
    parts.extend(['</g>', '<g id="base">', *_eagle(center, p), '</g>', '<g id="hero">'])
    if battle:
        parts.extend(_hero(battle, p))
    parts.extend([
        '</g>',
        f'<text x="{LEFT}" y="{height-6}" fill="{p["text"]}" font-size="8" '
        'letter-spacing="1.2" font-family="system-ui,sans-serif">GITTANKS · ONE VS MANY</text>',
        '</svg>',
    ])
    return "\n".join(parts) + "\n"
