# Architecture

The core prototype implements a normalized immutable calendar model, deterministic demo input, GitHub GraphQL collector, serpentine motion path and self-contained SVG renderer.

The first motion path visits active cells in alternating column order. It is a baseline for testing, not the final scenario behavior. Future scenarios will define their own simulation state, timing and geometry.

SVG output uses embedded declarative animation without JavaScript. GitHub image rendering compatibility and live API access require verification.

The collector accepts credentials from the environment through the CLI. The default demo requires no token.
