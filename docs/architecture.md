# Architecture

## Engine

The dependency-free Python engine collects a GitHub contribution calendar once through GraphQL. Immutable days preserve dates, counts, week indices, Sunday-first weekdays and contribution quartiles. The registry selects one of five planners; the shared geometry, labels and timeline serializer produce standalone SVGs with SMIL animations. Missing calendar slots are visual-only placeholders and never create activity.

## Scenarios

| Scenario | Simulation |
| --- | --- |
| GitTanks | One golden tank navigates free cells, destroys bricks, evades counterfire and faces silver pursuers. Bounded cardinal pathfinding respects obstacles; reinforcements overlap when safe. Enemy movement shares the hero's clock during brick clearing and deployment, so a lone survivor continues pursuing or patrolling available corridors; reserved routes and firing lanes prevent conflicts. The hero takes no damage: counterfire misses an empty square after evasion, or is intercepted outside the hull by a temporary shield when no safe route exists. |
| GitBlast | A bomber places sequential bombs beside contribution bricks and retreats outside the blast cross. Flames stop at the first intact brick. Initial patrols and staggered reinforcements use free cells. Long-lived patrols use time-dependent reachability to explore newly opened corridors while avoiding active bombs, flames, walls and other actors. |
| GitChess | Queen, rook, bishop and knight take turns capturing contribution pieces according to their movement geometry, with occupancy constraints and a limited target window. |
| GitInvaders | One ship engages a level-coded alien formation. Each alien oscillates within its own cell, alternating poses and accelerating as the formation shrinks. |
| GitOrigami | Active cells fold into geometric paper birds; timed flights restore source cells after each transformation. |

The scenarios are precomputed visual simulations, not interactive games. Dense or constrained calendars may limit legal movement and spawn sites.

## Rendering

All five renderers share the compact calendar header, month anchors, weekday labels and optional attribution. Dark and light themes use the same geometry. Each animation returns to its initial state at its loop boundary. The public registry contains five scenarios and two themes.

## Publication

The reusable composite action and CLI generate selected SVGs from one calendar fetch. Batch generation validates every SVG before writing assets. The daily or manually triggered publishing workflow tests the engine, generates the ten real-calendar SVGs, and uploads them to an isolated publication job. Only that job has repository write permission. The `output` branch contains the public SVGs; the source branch contains no generated animations.

Credentials are passed through environment variables. Public output may reveal dates and activity counts; see [Security](../SECURITY.md).

## Quality

Unit tests cover geometry, timelines, scenario behavior, sparse and dense input, and batch output. Credential-free deterministic fixtures are used internally for CI, benchmarks and browser checks. They are not published as product assets. The consumer action smoke test verifies installation from another workflow context and live GraphQL access. Browser checks use Chromium, Firefox and WebKit.

See [profile setup](setup.md) for usage.
