# contributionDynamic

*Beyond static contributions.*

An animation and simulation engine for transforming GitHub contribution calendars into dynamic visual experiences.

> **Status:** Pre-alpha — core prototype under development.

## Scenarios

| Scenario | Concept | Status |
| --- | --- | --- |
| GitFactory | Automated production lines powered by contributions | Planned |
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

Do not commit tokens. The current renderer is a motion prototype, not a completed scenario.

## Architecture

Calendar collector → normalized model → motion path → SVG renderer.

See [architecture](docs/architecture.md) and [contributing](CONTRIBUTING.md).

## Roadmap

- [x] Repository initialization
- [x] Core prototype implementation
- [ ] Foundation and API validation
- [ ] GitFactory prototype
- [ ] GitOrigami prototype
- [ ] Automated SVG publishing
