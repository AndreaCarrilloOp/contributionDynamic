# Architecture

## Planned pipeline

GitHub contribution collector → normalized calendar → scenario simulation → SVG renderer.

The simulation will be deterministic for identical input, configuration, and seed. SVG output must work as a static image resource with embedded animation, without JavaScript.

## Boundaries

- Collectors: retrieve and normalize contribution data.
- Core: calendar models, timing and simulation contracts.
- Scenarios: GitFactory and GitOrigami behavior.
- Renderers: translate simulation frames into self-contained SVG.
- Themes: visual configuration independent of simulation.

These are intended components, not implemented modules. The first milestone provides packaging, a CLI entry point, and basic tests. No GitHub token is needed yet.
