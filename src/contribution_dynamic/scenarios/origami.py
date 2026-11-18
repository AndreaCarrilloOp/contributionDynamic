"""Fold active contribution cells into paper birds using declarative SVG."""

from contribution_dynamic.animation import track as _track
from contribution_dynamic.calendar import Day, board_weeks, contribution_level
from contribution_dynamic.labels import LEFT, RIGHT, STEP, TOP, render_labels

CELL = 10
FLIGHT = 2.6
FIRST_FOLD = 0.25
MAX_CADENCE = 0.48
MIN_CADENCE = 0.14
TARGET_WAVE = 18.0

PALETTES = {
    "dark": ("#0d1117", "#161b22", "#8b949e",
             ("#0e4429", "#006d32", "#26a641", "#39d353"),
             "#b8f5db", "#48bfa9", "#137b70"),
    "light": ("#ffffff", "#ebedf0", "#57606a",
              ("#9be9a8", "#40c463", "#30a14e", "#216e39"),
              "#65bda2", "#198f80", "#075e55"),
}

# Six triangular faces. The last two unfold into the head and beak.
PAPER = (
    "-5,-5 5,-5 0,0", "5,-5 5,5 0,0", "5,5 -5,5 0,0",
    "-5,5 -5,-5 0,0", "5,-5 5,-5 5,-5", "5,-5 5,-5 5,-5",
)
FOLD = (
    "-5,-2 0,-5 1,2", "0,-5 5,-2 1,2", "5,-2 1,5 1,2",
    "1,5 -5,-2 1,2", "5,-2 5,-2 5,-2", "5,-2 5,-2 5,-2",
)
BIRD_UP = (
    "0,0 4,-11 7,-2", "-11,-1 -4,-2 -5,4", "-5,-2 6,-2 1,5",
    "-3,1 -11,-8 3,4", "5,-2 7,-5 9,-1", "7,-3 12,-2 9,-1",
)
BIRD_DOWN = (
    "0,0 4,8 7,-2", "-11,-1 -4,-2 -5,4", "-5,-2 6,-2 1,5",
    "-3,1 -10,8 3,4", "5,-2 7,-5 9,-1", "7,-3 12,-2 9,-1",
)


def fold_schedule(days: tuple[Day, ...]) -> dict[Day, float]:
    """Schedule only active cells so sparse calendars start immediately."""
    active = sorted((d for d in days if d.count > 0), key=lambda d: (d.week, d.weekday))
    cadence = max(MIN_CADENCE, min(MAX_CADENCE, TARGET_WAVE / max(1, len(active))))
    return {day: FIRST_FOLD + i * cadence for i, day in enumerate(active)}


def _bird(day, color, shades, cycle, width, s):
    x = LEFT + day.week * STEP + CELL / 2
    y = TOP + day.weekday * STEP + CELL / 2
    end = s + FLIGHT
    dx = 1 if x < width - 90 else -1
    # All flight positions remain in the SVG; the board itself stays in place.
    locations = [
        f"{x} {y}", f"{x} {y}", f"{x+dx*12} {y-6}",
        f"{x+dx*34} {max(27, y-18)}", f"{x+dx*55} {max(27, y-28)}",
    ]
    p = [
        f'<g data-bird="{day.date.isoformat()}" opacity="0" '
        f'transform="translate({x} {y})">',
        _track("opacity", [0, 0, 1, 1, 0],
               [0, s-.015, s, end-.35, end], cycle),
        _track("transform", locations, [s, s+.36, s+.85, s+1.6, end], cycle,
               transform=True),
        f'<g transform="scale({dx} 1)">',
    ]
    for i in range(len(PAPER)):
        p.append(f'<polygon points="{PAPER[i]}" fill="{color}">')
        p.append(_track("points", [
            PAPER[i], FOLD[i], BIRD_UP[i], BIRD_DOWN[i], BIRD_UP[i],
            BIRD_DOWN[i], BIRD_UP[i], BIRD_DOWN[i],
        ], [s, s+.19, s+.43, s+.79, s+1.15, s+1.51, s+1.87, end], cycle))
        p.append(_track("fill", [color, color, shades[i]], [s, s+.19, s+.43], cycle))
        p.append('</polygon>')
    p.extend(['</g>', '</g>'])
    return p


def render_origami(days: tuple[Day, ...], theme: str = "dark") -> str:
    bg, empty, text, levels, highlight, middle, shadow = PALETTES[theme]
    weeks = board_weeks(days)
    width, height = LEFT + weeks * STEP + RIGHT, TOP + 7 * STEP + 13
    schedule = fold_schedule(days)
    cycle = max(4.0, max(schedule.values(), default=0) + FLIGHT + .65)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        'aria-label="GitOrigami contribution calendar animation">',
        '<title>GitOrigami — contribution calendar</title>',
        f'<rect width="{width}" height="{height}" rx="6" fill="{bg}"/>',
    ]
    parts.extend(render_labels(days, width, CELL, text))
    parts.append('<g id="calendar">')
    for day in sorted(days, key=lambda d: (d.week, d.weekday)):
        x, y = LEFT + day.week * STEP, TOP + day.weekday * STEP
        level = contribution_level(day)
        color = levels[level-1] if level else empty
        parts.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
                     f'fill="{color}" data-date="{day.date.isoformat()}">')
        parts.append(f'<title>{day.date.isoformat()}: {day.count} contributions</title>')
        if day in schedule:
            s = schedule[day]
            # Restore each source cell after its bird fades, not just at loop reset.
            parts.append(_track("fill", [color, empty, color],
                                [0, s, s+FLIGHT], cycle, "discrete"))
        parts.append('</rect>')
    parts.extend(['</g>', '<g id="paper-birds">'])
    for day, start in schedule.items():
        parts.extend(_bird(day, levels[contribution_level(day)-1],
                           (shadow, middle, middle, highlight, highlight, shadow),
                           cycle, width, start))
    parts.extend(['</g>', '</svg>'])
    return "\n".join(parts) + "\n"
