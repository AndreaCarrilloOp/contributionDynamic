# Architecture

The core prototype implements a normalized immutable calendar model, deterministic demo input, GitHub GraphQL collector, serpentine motion path and self-contained SVG renderer.

The first motion path visits active cells in alternating column order. It is a baseline for testing, not the final scenario behavior. Future scenarios will define their own simulation state, timing and geometry.

SVG output uses embedded declarative animation without JavaScript. GitHub image rendering compatibility and live API access require verification.

The collector accepts credentials from the environment through the CLI. The default demo requires no token.

GitFactory assigns active days to four disjoint column zones with independent schedules. Each zone uses a persistent trolley, a gripper, a conveyor and an output station. Shared SVG timelines preserve source coordinates and reset the board at the cycle boundary. The collector retains GitHub contribution levels when available.

GitOrigami animates six triangular SVG paper panels per active day. A deterministic active-cell wave schedules folding, flight and fade-out without waiting for empty columns. Each source cell is restored after its own flight. The CLI selects a renderer through a scenario registry. CI generates demo previews without credentials; the manual GraphQL workflow fetches live data once for the six public scenarios.

Publishing renders and XML-validates twelve public assets from one calendar before uploading an artifact. A separate job with contents write permission updates the output branch without force-pushing. Generation uses read-only repository permissions and receives the contribution token only during the fetch step. Existing assets remain available if generation fails.

The experimental motion renderer is retained for local development and unit tests, but is excluded from publishing and CI preview artifacts.

GitAbyss partitions active calendar days into up to seven deterministic serpentine routes. Jellyfish translation, cell illumination and expanding energy rings share visit timestamps. Each route returns to its start, and source colors are restored after every pulse. Independent SMIL animations create bell contractions and tentacle motion without JavaScript or blur filters.

GitChess divides the board into four disjoint column zones, prioritizes active cells by relative intensity and count, and schedules one temporary piece per zone. Each capture selects an in-bounds launch square satisfying the piece's movement geometry. SVG vector symbols, capture highlights, and restoration share a deterministic timeline. Chess check, checkmate, blocking, and turn-by-turn game state are intentionally out of scope.

All six public scenarios share SMIL timeline serialization, retaining plateau boundaries while removing redundant interior keyframes and trailing numeric zeros. The registry drives batch generation and the composite action; selected themes and scenarios reuse one calendar fetch. No runtime speedup or browser-performance guarantee has been benchmarked yet.

GitChess separates board parity from contribution intensity: alternating tan and brown squares are static at rest, while four golden token radii encode activity. Capture flashes and temporary token removal reuse the existing capture timestamps; ivory and ebony pieces have contrasting outlines.

GitBlast partitions the board into four zones and schedules bombs until every active cell has been covered. Each cross is clipped to its zone and the seven calendar rows; multiple blasts may hit a previously restored cell. A diagonal shelter is outside the cross. Brick color and metadata preserve contribution level; synchronized timelines control the robot, fuse, explosion, debris and restoration. The simulation is arcade-inspired, not a playable game or full collision/pathfinding engine.

GitTanks uses four independent horizontal patrol zones. Each active column is cleared top to bottom so projectiles do not pass through a standing target; the column is restored after its final impact. A persistent tank per active zone translates along a dedicated service lane, aims its turret, fires, and returns home. Contribution targets preserve their original dates and levels. This is an arcade animation rather than a full combat game.
