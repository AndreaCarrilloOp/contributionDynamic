<div align="center">
  <img src="assets/brand/logo.svg" width="88" height="88" alt="contributionDynamic logo">
  <h1>contributionDynamic</h1>
  <p><em>Beyond static contributions.</em></p>
  <p>Transform GitHub contribution calendars into animated worlds.</p>
  <a href="https://github.com/AndreaCarrilloOp/contributionDynamic/actions/workflows/ci.yml"><img src="https://github.com/AndreaCarrilloOp/contributionDynamic/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-148a83" alt="MIT license"></a>
  <img src="https://img.shields.io/badge/Python-3.12%2B-203543" alt="Python 3.12+">
</div>

> Beta development · Prototype scenarios. Animated SVGs require a viewer that supports SMIL. The gallery uses the owner's published calendar; new assets appear after the publishing workflow succeeds.

## Gallery

### GitFactory

Robotic production lines process active cells.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/factory-dark.svg">
  <img alt="GitFactory animated contribution calendar" src="https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/factory-light.svg" width="100%">
</picture>

[Dark SVG](https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/factory-dark.svg) · [Light SVG](https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/factory-light.svg)

### GitOrigami

Paper birds fold, fly, and restore the calendar.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/origami-dark.svg">
  <img alt="GitOrigami animated contribution calendar" src="https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/origami-light.svg" width="100%">
</picture>

[Dark SVG](https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/origami-dark.svg) · [Light SVG](https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/origami-light.svg)

### GitAbyss

Bioluminescent jellyfish collect contribution energy.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/abyss-dark.svg">
  <img alt="GitAbyss animated contribution calendar" src="https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/abyss-light.svg" width="100%">
</picture>

[Dark SVG](https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/abyss-dark.svg) · [Light SVG](https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/abyss-light.svg)

### GitChess

Ivory and ebony chess pieces capture golden contribution tokens on a classic wood-toned checkerboard. Token size encodes GitHub activity levels.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/chess-dark.svg">
  <img alt="GitChess animated contribution calendar" src="https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/chess-light.svg" width="100%">
</picture>

[Dark SVG](https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/chess-dark.svg) · [Light SVG](https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/chess-light.svg)

### GitBlast

Arcade robots plant bombs that break contribution bricks in cross-shaped explosions. Brick color encodes contribution intensity, and each affected cell is restored.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/blast-dark.svg">
  <img alt="GitBlast animated contribution calendar" src="https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/blast-light.svg" width="100%">
</picture>

[Dark SVG](https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/blast-dark.svg) · [Light SVG](https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/blast-light.svg)

### GitTanks

A golden retro tank navigates the contribution maze, breaks bricks before entering their cells, and fights waves of silver enemies. The eagle remains a visual base; the original calendar is restored when the tank returns to its starting square.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/tanks-dark.svg">
  <img alt="GitTanks animated contribution calendar" src="https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/tanks-light.svg" width="100%">
</picture>

[Dark SVG](https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/tanks-dark.svg) · [Light SVG](https://raw.githubusercontent.com/AndreaCarrilloOp/contributionDynamic/output/tanks-light.svg)

## Quick start

Requires Python 3.12 or newer.

```sh
git clone https://github.com/AndreaCarrilloOp/contributionDynamic.git
cd contributionDynamic
python -m pip install -e .
python -m contribution_dynamic batch --output-dir generated
```

The default uses deterministic demo data. To fetch a live calendar, set the `GITHUB_TOKEN` environment variable securely and pass `--user YOUR_LOGIN`.

```sh
python -m contribution_dynamic generate --scenario abyss --theme dark --output abyss.svg
```

## GitHub Action

Add the following step to an Ubuntu workflow. Until a release is published, use `@main` for evaluation only; pin a verified release or commit SHA for production.

```yaml
- uses: AndreaCarrilloOp/contributionDynamic@main
  with:
    github-user: ${{ github.repository_owner }}
    github-token: ${{ secrets.CONTRIBUTION_TOKEN }}
    scenario: all
    theme: both
    output-dir: generated
```

| Input | Default | Options |
| --- | --- | --- |
| github-user | empty | GitHub login or demo |
| github-token | empty | Read-only token for live data |
| scenario | all | all, factory, origami, abyss, chess, blast, tanks |
| theme | both | both, dark, light |
| output-dir | generated | Destination directory |

The action generates SVGs; it does not push changes. See the [setup guide](docs/setup.md) for a complete scheduled profile workflow and theme-aware embedding. Never commit tokens. Public SVGs disclose dates, counts and activity levels.

## Architecture

GraphQL collector → calendar model → scenario simulation → compact SVG → publication

- Dependency-free runtime engine and deterministic animation.
- Calendar positions and GitHub intensity levels preserved.
- Declarative SVG motion, no JavaScript or external sprites.
- Shared timeline compaction and batch generation from a single API request.

The experimental `motion` renderer remains available locally, but is not published. GitChess models chess movement geometry, not a full game. GitOrigami is a geometric animation, not a physical folding solver.

## Development

```sh
python -m pip install -e ".[dev]"
python -m pytest -v
python -m ruff check .
```

[Architecture](docs/architecture.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Changelog](CHANGELOG.md) · [MIT license](LICENSE)
