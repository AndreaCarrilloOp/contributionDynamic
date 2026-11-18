# contributionDynamic

*Beyond static contributions.*

An animation and simulation engine for transforming GitHub contribution calendars into dynamic visual experiences.

> **Status:** Pre-alpha — core prototype under development.

## Scenarios

| Scenario | Concept | Status |
| --- | --- | --- |
| GitFactory | Robotic processing directly on the contribution calendar | Prototype |
| GitOrigami | Geometric folding and transformation | Planned |

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

GitFactory preserves the calendar layout and animates a rail-mounted gripper that extracts active cells, transports them along a conveyor, and restores the calendar on each loop. Color levels are currently derived from contribution counts. The SVG is a separate image for use in a README; it does not alter GitHub's native calendar.

## Architecture

Calendar collector → normalized model → motion path → SVG renderer.

See [architecture](docs/architecture.md) and [contributing](CONTRIBUTING.md).

## Roadmap

- [x] Repository initialization
- [x] Core prototype implementation
- [x] Core tests and live GraphQL validation
- [x] GitFactory initial prototype (visual validation pending)
- [ ] GitOrigami prototype
- [ ] Automated SVG publishing
