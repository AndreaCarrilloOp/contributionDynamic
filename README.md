# contributionDynamic

*Beyond static contributions.*

An open-source animation and simulation engine for transforming GitHub contribution calendars into dynamic visual experiences.

> **Status:** Pre-alpha — under active development. No animation generator has been released yet.

## Scenarios

| Scenario | Concept | Status |
| --- | --- | --- |
| GitFactory | Automated production lines powered by contributions | Planned |
| GitOrigami | Geometric folding and transformation | Planned |

## Development

Requires Python 3.12 or later.

```sh
python -m pip install -e ".[dev]"
python -m contribution_dynamic --version
python -m pytest
python -m ruff check .
```

## Architecture

The planned pipeline separates contribution collection, simulation, and SVG rendering. The first milestone establishes the package and development tooling.

See [architecture](docs/architecture.md) and [contributing](CONTRIBUTING.md).

## Roadmap

- [x] Repository initialization
- [ ] Foundation validation
- [ ] Contribution collector and core engine
- [ ] GitFactory prototype
- [ ] GitOrigami prototype
- [ ] Automated SVG publishing

