# Architecture

The core prototype implements a normalized immutable calendar model, deterministic demo input, GitHub GraphQL collector, serpentine motion path and self-contained SVG renderer.

The first motion path visits active cells in alternating column order. It is a baseline for testing, not the final scenario behavior. Future scenarios will define their own simulation state, timing and geometry.

SVG output uses embedded declarative animation without JavaScript. GitHub image rendering compatibility and live API access require verification.

The collector accepts credentials from the environment through the CLI. The default demo requires no token.

GitFactory assigns active days to four disjoint column zones with independent schedules. Each zone uses a persistent trolley, a gripper, a conveyor and an output station. Shared SVG timelines preserve source coordinates and reset the board at the cycle boundary. The collector retains GitHub contribution levels when available.

GitOrigami animates six triangular SVG paper panels per active day. A deterministic active-cell wave schedules folding, flight and fade-out without waiting for empty columns. Each source cell is restored after its own flight. The CLI selects a renderer through a scenario registry. CI generates demo previews without credentials; the manual GraphQL workflow fetches live data once for all renderers.

Publishing renders and XML-validates all six assets from one calendar before uploading an artifact. A separate job with contents write permission updates the output branch without force-pushing. Generation uses read-only repository permissions and receives the contribution token only during the fetch step. Existing assets remain available if generation fails.
