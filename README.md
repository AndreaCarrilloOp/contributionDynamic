# contributionDynamic

*Beyond static contributions.*

An animation and simulation engine for transforming GitHub contribution calendars into dynamic visual experiences.

> **Status:** Pre-alpha — core prototype under development.

## Scenarios

| Scenario | Concept | Status |
| --- | --- | --- |
| GitFactory | Robotic processing directly on the contribution calendar | Prototype |
| GitOrigami | Paper birds folding from active calendar cells | Prototype |

## Quick start

Requires Python 3.12+.

```sh
python -m pip install -e ".[dev]"
python -m contribution_dynamic generate --output examples/demo.svg
python -m pytest
python -m ruff check .
```

The default generator uses deterministic sample data. For actual GitHub contributions, set the GITHUB_TOKEN environment variable and run:

```sh
python -m contribution_dynamic generate --user YOUR_LOGIN --theme dark --output examples/profile.svg
```

Do not commit tokens. To preview the first factory scenario:

```sh
python -m contribution_dynamic generate --scenario factory --theme dark --output examples/factory-dark.svg
```

GitFactory preserves the calendar layout and uses four independent production zones. Rail-mounted grippers extract active cells, move them to local conveyors and process them at output stations. Each loop restores the calendar. Live data uses GitHub's contribution levels with a theme-specific palette; demo data uses a count-based fallback. The SVG is a separate image for use in a README; it does not alter GitHub's native calendar.

To preview GitOrigami:

```sh
python -m contribution_dynamic generate --scenario origami --theme dark --output examples/origami-dark.svg
```

GitOrigami folds each active calendar cell into a four-panel paper bird. A staggered wave travels across the board, birds fly and fade, and the original calendar returns at the end of the loop. This is a geometric animation, not a physical paper-folding solver.

Run **CI** for token-free demo previews or **Validate GitHub GraphQL** for previews based on the repository owner's actual contributions.

## Architecture

Calendar collector → normalized model → motion path → SVG renderer.

See [architecture](docs/architecture.md) and [contributing](CONTRIBUTING.md).

## Roadmap

- [x] Repository initialization
- [x] Core prototype implementation
- [x] Core tests and live GraphQL validation
- [x] GitFactory board-based parallel prototype (visual validation pending)
- [x] GitOrigami initial prototype (visual validation pending)
- [ ] Automated SVG publishing
