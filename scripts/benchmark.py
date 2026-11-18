"""Measure deterministic SVG generation (not browser frame rates)."""

import argparse
import json
import platform
from dataclasses import replace
from pathlib import Path
from statistics import median
from time import perf_counter
from xml.etree import ElementTree

from contribution_dynamic.calendar import demo_calendar
from contribution_dynamic.registry import PUBLISHED_SCENARIOS, RENDERERS, THEMES


def calendars():
    demo = demo_calendar()
    return {
        "empty": tuple(replace(d, count=0, level=0) for d in demo),
        "sparse": tuple(replace(d, count=3 if i % 45 == 0 else 0)
                        for i, d in enumerate(demo)),
        "demo": demo,
        "dense": tuple(replace(d, count=1 + i % 12) for i, d in enumerate(demo)),
    }


def run(repeats):
    records = []
    for name, days in calendars().items():
        for scenario in PUBLISHED_SCENARIOS:
            for theme in THEMES:
                samples = []
                for _ in range(repeats):
                    start = perf_counter()
                    svg = RENDERERS[scenario](days, theme)
                    samples.append((perf_counter() - start) * 1000)
                root = ElementTree.fromstring(svg)
                records.append({
                    "calendar": name, "scenario": scenario, "theme": theme,
                    "active_days": sum(d.count > 0 for d in days),
                    "median_ms": round(median(samples), 3),
                    "bytes": len(svg.encode("utf-8")),
                    "svg_elements": sum(1 for _ in root.iter()),
                })
    return {"python": platform.python_version(), "platform": platform.platform(),
            "repeats": repeats, "results": records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("benchmark.json"))
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    results = run(args.repeats)
    args.output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    for row in results["results"]:
        print(row)


if __name__ == "__main__":
    main()
