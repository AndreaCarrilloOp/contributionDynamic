"""Shared compact SMIL timeline serialization."""

from collections.abc import Sequence


def track(
    name: str,
    values: Sequence,
    times: Sequence[float],
    cycle: float,
    mode: str = "linear",
    transform: bool = False,
) -> str:
    """Preserve interpolation while removing redundant interior plateau keyframes."""
    vals = list(map(str, values))
    points = list(times)
    if not vals or len(vals) != len(points):
        raise ValueError("Timeline values and times must match")
    if cycle <= 0 or points[0] < 0 or points[-1] > cycle:
        raise ValueError("Timeline exceeds its cycle")
    if any(a >= b for a, b in zip(points, points[1:])):
        raise ValueError("Timeline times must increase")
    if points[0] > 0:
        points.insert(0, 0)
        vals.insert(0, vals[0])
    if points[-1] < cycle:
        points.append(cycle)
        vals.append(vals[-1])
    keep = [
        i for i, value in enumerate(vals)
        if i == 0 or i == len(vals) - 1 or not (vals[i-1] == value == vals[i+1])
    ]
    keys = ";".join(f"{points[i] / cycle:.9f}".rstrip("0").rstrip(".") for i in keep)
    joined = ";".join(vals[i] for i in keep)
    tag = "animateTransform" if transform else "animate"
    extra = ' type="translate"' if transform else ""
    duration = f"{cycle:.6f}".rstrip("0").rstrip(".")
    return (
        f'<{tag} attributeName="{name}"{extra} values="{joined}" keyTimes="{keys}" '
        f'dur="{duration}s" calcMode="{mode}" repeatCount="indefinite"/>'
    )
