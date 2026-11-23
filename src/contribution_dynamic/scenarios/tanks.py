"""Tanks: golden maze tank against waves of silver invaders."""

from collections import deque
from dataclasses import dataclass
from math import atan2, cos, degrees, hypot, radians, sin

from contribution_dynamic.animation import track
from contribution_dynamic.calendar import Day, board_weeks, contribution_level
from contribution_dynamic.labels import LEFT, RIGHT, STEP, TOP, render_labels
from contribution_dynamic.layout import (
    SIGNATURE_HEIGHT,
    calendar_width,
    render_padding,
    render_signature,
)

CELL = 10
FIRST = .12
BASE = TOP + 7 * STEP + 15
MAX_ENEMIES = 3
SPAWN_GAP = .36
WAVE_BRICKS = 5
CHASE_ROUNDS = 10
PURSUIT_STEP = .18
FIRE_RANGE = 5
SPAWN_RADIUS = 2
SPAWN_SEPARATION = 3
PROJECTILE_SPEED = 150
SHIELD_RADIUS = 8.5
ROLES = ("hunter", "ambusher", "flanker")
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
    complete: float
    day: Day | None = None
    enemy: int | None = None
    counter: float | None = None
    counter_hit: float | None = None
    spawn: float | None = None
    evade: Square | None = None
    counter_outcome: str | None = None
    counter_target: Square | None = None


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


def _distance(a: Square, b: Square) -> int:
    return abs(a[0]-b[0]) + abs(a[1]-b[1])


def can_fire(source: Square, target: Square, blocked: set[Square]) -> bool:
    """Only cardinal shots within range; intervening bricks and tanks stop fire."""
    dx, dy = target[0]-source[0], target[1]-source[1]
    distance = abs(dx)+abs(dy)
    if not 1 <= distance <= FIRE_RANGE or (dx and dy):
        return False
    sx, sy = dx // distance, dy // distance
    return all(
        (source[0]+sx*i, source[1]+sy*i) not in blocked
        for i in range(1, distance)
    )


def _visible(source, blocked, targets):
    """The first solid square along each ray is the only possible target."""
    for dx, dy in DIRECTIONS:
        for distance in range(1, FIRE_RANGE+1):
            target = source[0]+dx*distance, source[1]+dy*distance
            if target in targets:
                yield target
                break
            if target in blocked:
                break


def _approach(start, blocked, targets, width, spawn):
    """Find the nearest reachable square with a clear firing line."""
    parents = _paths(start, blocked, width, spawn)
    for pos in parents:
        target = next(_visible(pos, blocked, targets), None)
        if target is not None:
            return _path(parents, pos), target
    raise ValueError("No reachable target")


def _flight(source: Square, target: Square) -> float:
    return max(.12, (_distance(source, target)*STEP-7)/PROJECTILE_SPEED)


def _enemy_positions(current, blocked, width, spawn, count, cleared, occupied=()):
    """Choose spread-out reinforcement sites near bricks, never clustered."""
    occupied = set(occupied)
    parents = _paths(current, blocked | occupied, width, spawn)
    if not blocked:
        return ()
    near = {
        (x+dx, y+dy)
        for x, y in blocked
        for dx in range(-SPAWN_RADIUS, SPAWN_RADIUS+1)
        for dy in range(-SPAWN_RADIUS, SPAWN_RADIUS+1)
        if 0 < abs(dx)+abs(dy) <= SPAWN_RADIUS
    }
    candidates = [
        pos for pos in parents
        if pos not in (current, spawn) and pos in near
        and 0 <= pos[0] < width and 0 <= pos[1] < 7
        and all(_distance(pos, other) >= SPAWN_SEPARATION for other in occupied)
    ]
    distances = {pos: len(_path(parents, pos))-1 for pos in candidates}
    chosen = []
    while candidates and len(chosen) < count:
        target = min(candidates, key=lambda pos: (
            abs(distances[pos]-(FIRE_RANGE+2))
            + (3 if can_fire(current, pos, blocked) else 0)
            - min(5, min((_distance(pos, other) for other in chosen), default=0))*.8,
            pos not in cleared,
            pos,
        ))
        chosen.append(target)
        candidates = [
            pos for pos in candidates
            if _distance(pos, target) >= SPAWN_SEPARATION
        ]
    return tuple(chosen)


def _chase_step(position, hero, heading, role, blocked, width, spawn, previous=None):
    """Find a role-specific firing position while avoiding unnecessary reversals."""
    parents = _paths(position, blocked | {hero, spawn}, width, spawn)
    goals = [pos for pos in parents if can_fire(pos, hero, blocked)]
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
    if len(route) <= 1:
        return position

    choices = [
        pos for pos in _neighbors(position, width, spawn)
        if pos not in blocked and pos not in (hero, spawn)
    ]
    if not choices:
        return position
    forward = (
        (position[0] * 2 - previous[0], position[1] * 2 - previous[1])
        if previous is not None else None
    )
    non_reverse = [pos for pos in choices if pos != previous]
    if non_reverse:
        choices = non_reverse

    step = route[1]
    if step in choices and (forward is None or step == forward):
        return step
    # Multi-source BFS avoids a separate search for each candidate.
    distances_to_goal = dict.fromkeys(goals, 0)
    frontier = deque(goals)
    while frontier:
        square = frontier.popleft()
        for neighbor in _neighbors(square, width, spawn):
            if neighbor in parents and neighbor not in distances_to_goal:
                distances_to_goal[neighbor] = distances_to_goal[square] + 1
                frontier.append(neighbor)
    distances = {
        pos: distances_to_goal[pos]
        for pos in choices if pos in distances_to_goal
    }
    if not distances:
        return step if step in choices else position
    best = min(distances.values())
    if forward in distances and distances[forward] <= best + 1:
        return forward
    return min(distances, key=lambda pos: (
        distances[pos], pos != step, pos,
    ))


def _patrol_step(position, hero, heading, role, blocked, width, spawn, previous=None):
    """Patrol forward along corridors instead of oscillating left and right."""
    destination = _chase_step(
        position, hero, heading, role, blocked, width, spawn, previous,
    )
    if destination != position:
        return destination
    choices = [
        pos for pos in _neighbors(position, width, spawn)
        if pos not in blocked and pos not in (hero, spawn)
    ]
    if not choices:
        return position
    forward = (
        (2 * position[0] - previous[0], 2 * position[1] - previous[1])
        if previous is not None else None
    )
    if forward in choices:
        return forward
    turns = [pos for pos in choices if pos != previous]
    if turns:
        choices = turns
    return min(choices, key=lambda pos: (_distance(pos, hero), pos))


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

    def turn(target, duration=.07):
        pos = positions[-1]
        desired = _angle(_center(*pos), _center(*target))
        previous = angles[-1]
        angle = previous + (desired-previous+180) % 360 - 180
        pose(pos, clock+duration, angle)

    def walk(route, turn_time=.07, move_time=.11):
        nonlocal heading
        for pos in route[1:]:
            prior = positions[-1]
            heading = pos[0]-prior[0], pos[1]-prior[1]
            turn(pos, turn_time)
            pose(pos, clock+move_time, angles[-1])

    def engage(target, day=None, enemy=None, born=None, occupied=()):
        source = positions[-1]
        counter = counter_hit = counter_target = None
        evade = outcome = None
        obstacles = blocked | set(occupied)
        if enemy is not None:
            counter_target = source
            dx, dy = target[0]-source[0], target[1]-source[1]
            sidesteps = [
                pos for pos in _neighbors(source, width, spawn)
                if pos not in obstacles
                and (pos[0]-source[0])*dx+(pos[1]-source[1])*dy == 0
            ]
            if sidesteps:
                # Prefer another firing lane instead of immediately reversing.
                choices = []
                for pos in sidesteps:
                    try:
                        route, _ = _approach(
                            pos, obstacles | {source}, {target}, width, spawn,
                        )
                    except ValueError:
                        continue
                    if len(route) <= 6:
                        choices.append((pos, route))
                if choices:
                    evade, route = min(choices, key=lambda item: (len(item[1]), item))
                else:
                    evade = min(sidesteps)
                    route, _ = _approach(evade, obstacles, {target}, width, spawn)
                # Turn the hull first; the enemy fires during the maneuver.
                counter = clock+.22
                counter_hit = counter+_flight(source, target)
                walk((source, evade), turn_time=.10, move_time=.16)
                pose(evade, max(clock+.04, counter_hit+.08), angles[-1])
                walk(route, turn_time=.10, move_time=.16)
                source = positions[-1]
                outcome = "miss"
            else:
                turn(target)
                counter = clock+.04
                # No safe escape: intercept the shell outside the hull.
                outcome = "shield"
                counter_hit = counter+max(
                    .12, (_distance(source, target)*STEP-7-SHIELD_RADIUS)/PROJECTILE_SPEED,
                )
                pose(source, counter_hit+.08, angles[-1])
        turn(target)
        flight = _flight(source, target)
        fire = clock+.04
        hit = fire+flight
        pose(source, hit+.16, angles[-1])
        # Distant targets are shot without teleporting the tank to the impact.
        if day is not None and _distance(source, target) == 1:
            pose(target, clock+.11, angles[-1])
        attacks.append(Attack(source, target, fire, hit, clock, day, enemy,
                              counter, counter_hit, born, evade, outcome, counter_target))

    living, roles, trails, births = {}, {}, {}, {}
    last_birth = -SPAWN_GAP
    budget = MAX_ENEMIES * ((len(bricks)+WAVE_BRICKS-1)//WAVE_BRICKS+1)

    def advance_enemies(begin, finish, protected=(), patrol=False):
        """Advance opponents on the existing hero clock, without adding a pause.

        Protect the entire planned hero route and its firing lane, reserve enemy
        starts and destinations, and commit each movement before the next tick.
        """
        protected = set(protected) | {positions[-1], spawn}
        while living and finish-begin >= PURSUIT_STEP-1e-8:
            end = min(finish, begin+PURSUIT_STEP)
            occupied = set(living.values())
            reserved = set()
            next_positions = {}
            for key, pos in living.items():
                obstacles = blocked | (occupied - {pos}) | reserved | protected
                path, _ = trails[key]
                previous = next((p for p in reversed(path) if p != pos), None)
                if patrol:
                    destination = _patrol_step(
                        pos, positions[-1], heading, roles[key], obstacles,
                        width, spawn, previous,
                    )
                else:
                    destination = _chase_step(
                        pos, positions[-1], heading, roles[key], obstacles,
                        width, spawn, previous,
                    )
                next_positions[key] = destination
                reserved.add(destination)
            for key, destination in next_positions.items():
                pos = living[key]
                if destination != pos:
                    path, ticks = trails[key]
                    if begin > ticks[-1]:
                        path.append(pos)
                        ticks.append(begin)
                    path.append(destination)
                    ticks.append(end)
            living.update(next_positions)
            begin = end

    def clear_brick(route, target):
        # Preserve the hero's BFS route and cardinal ray while enemies move.
        source = route[-1]
        distance = _distance(source, target)
        dx = (target[0]-source[0]) // distance
        dy = (target[1]-source[1]) // distance
        protected = set(route) | {
            (source[0]+dx*i, source[1]+dy*i) for i in range(distance+1)
        }
        for pos in route[1:]:
            begin = clock
            walk((positions[-1], pos))
            advance_enemies(begin, clock, protected, patrol=True)
        begin = clock
        engage(target, day=bricks[target])
        advance_enemies(begin, clock, protected, patrol=True)
        blocked.remove(target)
        cleared.add(target)

    def deploy(count):
        nonlocal enemy_id, last_birth, budget
        if count <= 0 or budget <= 0:
            return
        spawns = _enemy_positions(
            positions[-1], blocked, width, spawn, min(count, budget),
            cleared, living.values(),
        )
        for pos in spawns:
            if clock < last_birth+SPAWN_GAP:
                begin = clock
                pose(positions[-1], last_birth+SPAWN_GAP, angles[-1])
                advance_enemies(begin, clock, spawns, patrol=True)
            # Recheck spacing after existing enemies have moved.
            if any(_distance(pos, other) < SPAWN_SEPARATION for other in living.values()):
                continue
            key = enemy_id
            enemy_id += 1
            budget -= 1
            last_birth = clock
            births[key] = clock
            living[key] = pos
            roles[key] = ROLES[key % len(ROLES)]
            trails[key] = ([pos], [clock])
            begin = clock
            pose(positions[-1], clock+SPAWN_GAP, angles[-1])
            advance_enemies(begin, clock, spawns, patrol=True)

    def defeat(key):
        target = living[key]
        engage(target, enemy=key, born=births[key], occupied=set(living.values()))
        path, ticks = trails.pop(key)
        enemy_routes.append(EnemyRoute(key, roles.pop(key), tuple(path), tuple(ticks)))
        del living[key]

    def brick_route():
        if not blocked:
            return None
        try:
            return _approach(positions[-1], blocked | set(living.values()),
                             blocked, width, spawn)
        except ValueError:
            return None

    while blocked or living:
        count = min(WAVE_BRICKS, max(1, len(blocked)-1))
        progress = False
        for _ in range(count):
            reachable = brick_route()
            if reachable is None:
                break
            route, target = reachable
            clear_brick(route, target)
            progress = True
        if blocked and progress:
            deploy(MAX_ENEMIES-len(living))
        if not living:
            continue

        for round_index in range(CHASE_ROUNDS):
            if not living or (len(living) == 1 and brick_route() is not None):
                break
            hero = positions[-1]
            obstacles = blocked | set(living.values())
            visible = [
                key for key, pos in living.items() if can_fire(hero, pos, obstacles)
            ]
            if visible:
                key = min(visible, key=lambda key: (_distance(hero, living[key]), key))
                if len(living) == 1 and blocked and budget:
                    deploy(1)
                    if not can_fire(hero, living[key], blocked | set(living.values())):
                        continue
                defeat(key)
                continue
            # Keep clearing the maze while enemies approach. If the corridor
            # is cut off, seek a firing line instead of crossing a wall.
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
                clear_brick(route, target)
            else:
                key = next(key for key, pos in living.items() if pos == target)
                if len(living) == 1 and blocked and budget:
                    deploy(1)
                    if not can_fire(
                        positions[-1], living[key], blocked | set(living.values()),
                    ):
                        continue
                defeat(key)
                continue

            finish = clock+PURSUIT_STEP
            advance_enemies(clock, finish)
            pose(positions[-1], finish, angles[-1])

        # A bounded pursuit phase guarantees progress even on narrow mazes.
        replenished = False
        while living and (len(living) > 1 or brick_route() is None):
            if len(living) == 1 and blocked and budget and not replenished:
                deploy(1)
                replenished = True
            route, target = _approach(
                positions[-1], blocked | set(living.values()),
                set(living.values()), width, spawn,
            )
            walk(route)
            defeat(next(key for key, pos in living.items() if pos == target))
        pose(positions[-1], clock+.10, angles[-1])

    parents = _paths(positions[-1], set(), width, spawn)
    walk(_path(parents, spawn))
    previous = angles[-1]
    home_angle = previous + (90-previous+180) % 360 - 180
    pose(spawn, clock+.15, home_angle)
    return Battle(spawn, tuple(positions), tuple(times), tuple(angles),
                  tuple(attacks), max(4.0, clock+.6),
                  tuple(sorted(enemy_routes, key=lambda enemy: enemy.enemy)))


def _tank_sprite(p: dict, side: str = "hero") -> list[str]:
    """Render a tank sprite with its cannon aligned to projectile origins."""
    return [
        '<g data-sprite="retro-tank" shape-rendering="crispEdges">',
        f'<path d="M-5 -5H5V-2H-5ZM-5 2H5V5H-5Z" fill="{p["tracks"]}"/>',
        f'<path d="M-4.5 -4.5H4.5M-4.5 4.5H4.5" stroke="{p["metal"]}" '
        'stroke-width="1" stroke-dasharray="1.2 1.1"/>',
        f'<path d="M-4 -3H4V3H-4Z" fill="{p[f"{side}_shadow"]}" '
        f'stroke="{p[f"{side}_edge"]}" stroke-width="1"/>',
        f'<path d="M-3 -2.5H3V2H-3Z" fill="{p[side]}"/>',
        f'<path d="M-3 -2H2V-1H-3Z" fill="{p[f"{side}_top"]}" opacity=".8"/>',
        f'<path d="M0 -1H7V1H0Z" fill="{p[f"{side}_top"]}" '
        f'stroke="{p[f"{side}_edge"]}" stroke-width=".55"/>',
        f'<path d="M-2 -3H1L3 -1V1L1 3H-2L-3 1V-1Z" '
        f'fill="{p[side]}" stroke="{p[f"{side}_edge"]}" stroke-width=".6"/>',
        f'<path d="M-2 -2H1L2 -1H-2Z" fill="{p[f"{side}_top"]}"/>',
        f'<rect x="-.8" y="-.8" width="1.6" height="1.6" fill="{p[f"{side}_shadow"]}"/>',
        '</g>',
    ]



def _projectile(origin, target, fire, hit, cycle, p, side):
    # A nearby protective barrier may be closer than the usual cannon tip.
    distance = hypot(target[0]-origin[0], target[1]-origin[1])
    muzzle = _toward(origin, target, min(7, max(0, distance-1)))
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
        '<g data-tank-body="hero">',
        *_tank_sprite(p, "hero"),
        '</g>',
        '</g></g>',
    ]


def _enemy(attack, route, cycle, p):
    positions = [_position(_center(*pos)) for pos in route.positions]
    aim = _angle(_center(*attack.target), _center(*attack.counter_target))
    angles, angle_times = [90], [attack.spawn]
    for a, b, t in zip(route.positions, route.positions[1:], route.times[1:]):
        if a != b:
            angles.append(_angle(_center(*a), _center(*b)))
            angle_times.append(t)
    angles.append(aim)
    angle_times.append(attack.counter-.03)
    return [
        f'<g data-tank="enemy" data-enemy="{attack.enemy}" data-role="{route.role}" '
        f'data-spawn="{attack.spawn:.6f}" opacity="0" transform="translate({positions[0]})">',
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
    distance = _distance(attack.source, attack.target)
    parts = [f'<g data-shot="{label}" data-distance="{distance}">']
    if attack.enemy is not None:
        counter_origin = _center(*attack.counter_target)
        outcome = attack.counter_outcome
        impact = (_toward(counter_origin, target, SHIELD_RADIUS)
                  if outcome == "shield" else counter_origin)
        parts.extend(_projectile(target, impact, attack.counter,
                                 attack.counter_hit, cycle, p, "enemy"))
        parts.append(f'<g data-counter-outcome="{outcome}">')
        if outcome == "shield":
            # Activate protection before launch, then dissipate at interception.
            parts.extend([
                f'<circle cx="{counter_origin[0]}" cy="{counter_origin[1]}" '
                f'r="{SHIELD_RADIUS}" fill="none" stroke="{p["shield"]}" '
                'stroke-width="1" opacity="0" data-protection="true">',
                track("opacity", [0, .65, .65, 0],
                      [attack.counter-.035, attack.counter, attack.counter_hit,
                       attack.counter_hit+.12], cycle),
                '</circle>',
                f'<circle cx="{impact[0]:.3f}" cy="{impact[1]:.3f}" r="2" '
                f'fill="{p["core"]}" opacity="0">',
                track("opacity", [0, .9, 0],
                      [attack.counter_hit-.01, attack.counter_hit, attack.counter_hit+.10],
                      cycle),
                '</circle>',
            ])
        else:
            parts.extend(_explosion(counter_origin, attack.counter_hit, cycle, p, 4))
        parts.append('</g>')
    parts.extend(_projectile(origin, target, attack.fire, attack.hit, cycle, p, "hero"))
    parts.extend(_explosion(target, attack.hit, cycle, p,
                            5+contribution_level(attack.day) if attack.day else 8))
    parts.append('</g>')
    return parts


def _eagle(center, p):
    """Render the stationary eagle base."""
    return [
        f'<g data-base="eagle" transform="translate({center} {BASE})">',
        f'<rect x="-10" y="-9" width="20" height="18" rx="1" fill="{p["empty"]}" '
        f'stroke="{p["brick_shadow"]}" stroke-width="1.3"/>',
        '<path d="M-8 -6H-5V-4H-3V-2H-1V-5H1V-6H4V-3H2V-2H4V-4'
        'H6V-6H8V-1H6V1H3V4H5V6H-5V4H-3V1H-6V-1H-8Z" '
        f'fill="{p["hero_top"]}" stroke="{p["hero_edge"]}" stroke-width=".6"/>',
        '</g>',
    ]


def render_tanks(
    days: tuple[Day, ...], theme: str = "dark", *, signature: bool = False,
) -> str:
    p = PALETTES[theme]
    weeks, center = board_weeks(days), base_x(days)
    width, height = calendar_width(LEFT, STEP, CELL, RIGHT, weeks), BASE+14
    height += SIGNATURE_HEIGHT if signature else 0
    battle = plan_battle(days)
    cycle = battle.cycle if battle else 4.0
    by_day = {a.day: a for a in battle.attacks if a.day} if battle else {}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        'aria-label="Tanks golden tank navigates the contribution maze">',
        '<title>Tanks — one versus many</title>',
        f'<rect width="{width}" height="{height}" rx="6" fill="{p["bg"]}"/>',
    ]
    parts.extend(render_labels(days, width, CELL, p["text"]))
    parts.append('<g id="calendar">')
    parts.extend(render_padding(days, CELL, p["empty"]))
    for day in sorted(days, key=lambda d: (d.week, d.weekday)):
        x, y = LEFT+day.week*STEP, TOP+day.weekday*STEP
        level = contribution_level(day)
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
        *render_signature(width, height, p["text"], signature),
        '</svg>',
    ])
    return "\n".join(parts) + "\n"
