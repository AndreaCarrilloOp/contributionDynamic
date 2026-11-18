"""Deterministic factory production schedule and animated SVG renderer."""

from dataclasses import dataclass

from contribution_dynamic.calendar import Day


@dataclass(frozen=True)
class Job:
    day: Day
    start: float


PERIOD = 8
CADENCE = 2


def schedule(days: tuple[Day, ...]) -> tuple[Job, ...]:
    """Release one batch per active day; count determines its load."""
    active = sorted((d for d in days if d.count), key=lambda d: d.date)
    return tuple(Job(day, i * CADENCE) for i, day in enumerate(active))


def render_factory(days: tuple[Day, ...], theme: str = "dark") -> str:
    dark = theme == "dark"
    bg, panel, metal, text = (
        ("#0d1117", "#21262d", "#718697", "#dbe9ef") if dark
        else ("#ffffff", "#e7edf1", "#526b7b", "#233846")
    )
    accent = "#14b8a6" if dark else "#0f766e"
    jobs = schedule(days)
    cycle = max(PERIOD, len(jobs) * CADENCE + PERIOD)
    p = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 220" '
        'role="img" aria-label="GitFactory contribution production line">',
        f'<rect width="760" height="220" rx="10" fill="{bg}"/>',
        f'<g font-family="monospace" fill="{text}">',
        '<text x="20" y="25" font-size="15" font-weight="bold">GitFactory</text>',
        f'<text x="740" y="25" font-size="11" text-anchor="end">'
        f'{len(jobs)} batches / {sum(d.count for d in days)} contributions</text>',
    ]
    for x, label in ((65, "INPUT"), (260, "ASSEMBLE"), (460, "INSPECT"), (680, "OUTPUT")):
        p.append(f'<text x="{x}" y="193" text-anchor="middle" font-size="10">{label}</text>')
    p.extend([
        '</g>',
        f'<rect x="30" y="140" width="700" height="27" rx="7" fill="{panel}"/>',
        f'<rect x="36" y="145" width="688" height="15" rx="4" fill="{metal}" opacity=".45"/>',
    ])
    for x in range(44, 720, 22):
        p.append(f'<circle cx="{x}" cy="153" r="4" fill="{metal}"/>')
    if jobs:
        p.append(
            f'<path d="M44 152H716" stroke="{accent}" stroke-width="2" '
            'stroke-dasharray="8 14" opacity=".7">'
            '<animate attributeName="stroke-dashoffset" from="0" to="-22" dur=".6s" '
            'repeatCount="indefinite"/></path>'
        )
    for x in (260, 460):
        p.extend([
            f'<rect x="{x-27}" y="48" width="54" height="18" rx="4" fill="{panel}"/>',
            f'<g transform="translate({x} 66)">',
            f'<path d="M0 0L-22 29L0 55" fill="none" stroke="{metal}" '
            'stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>',
            f'<circle cx="-22" cy="29" r="6" fill="{accent}"/>',
            f'<path d="M-9 55V65M9 55V65M-9 55H9" stroke="{accent}" '
            'stroke-width="4" fill="none"/>',
        ])
        if jobs:
            phase = 2 if x == 260 else 4
            p.append(
                '<animateTransform attributeName="transform" type="rotate" additive="sum" '
                f'values="-18 0 0;-18 0 0;0 0 0;-18 0 0" begin="{phase}s" '
                'keyTimes="0;.65;.85;1" dur="2s" repeatCount="indefinite"/>'
            )
        p.append('</g>')
    for job in jobs:
        # One batch moves through four stations; the batch color changes after processing.
        start = job.start / cycle
        end = (job.start + PERIOD) / cycle
        times = ";".join(f"{v:.10f}" for v in (start, end))
        size = min(19, 10 + job.day.count.bit_length())
        p.extend([
            '<g opacity="0">',
            f'<title>{job.day.date.isoformat()}: {job.day.count} contributions</title>',
            f'<rect x="{-size/2}" y="{-size}" width="{size}" height="{size}" '
            'rx="2" fill="#94a3b8">',
            f'<animate attributeName="fill" values="#94a3b8;#94a3b8;{accent};#eab308;#eab308" '
            f'keyTimes="0;{start:.10f};{(start+end)/2:.10f};{end:.10f};1" '
            f'dur="{cycle}s" repeatCount="indefinite"/>',
            '</rect>',
            f'<animate attributeName="opacity" values="0;1;0;0" keyTimes="0;{times};1" '
            f'calcMode="discrete" dur="{cycle}s" repeatCount="indefinite"/>'
            if start > 0 else
            f'<animate attributeName="opacity" values="1;0;0" keyTimes="0;{end:.10f};1" '
            f'calcMode="discrete" dur="{cycle}s" repeatCount="indefinite"/>',
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="45 140;45 140;715 140;715 140" '
            f'keyTimes="0;{start:.10f};{end:.10f};1" dur="{cycle}s" '
            'repeatCount="indefinite"/>',
            '</g>',
        ])
    p.append('</svg>')
    return "\n".join(p) + "\n"
