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

GitChess models one persistent golden queen and one ebony pawn per active contribution day. The queen moves along unobstructed horizontal, vertical or diagonal rays, captures the first standing pawn on a ray, and uses breadth-first search of legal empty-square moves if no pawn is visible. Every capture removes the pawn from the occupied set. After the last capture the queen returns through a staging row below the calendar and all pawns are restored. Full chess rules, turns and checkmate are outside the scope.

All six public scenarios share SMIL timeline serialization, retaining plateau boundaries while removing redundant interior keyframes and trailing numeric zeros. The registry drives batch generation and the composite action; selected themes and scenarios reuse one calendar fetch. No runtime speedup or browser-performance guarantee has been benchmarked yet.

GitChess separates board parity from contribution intensity: alternating tan and brown squares remain static at rest, while four pawn scales encode activity. A shared timeline synchronizes queen movement, pawn disappearance, capture flashes, and restoration.

GitBlast uses one persistent actor and a BFS route through free squares. The planner selects a reachable bomb site adjacent to a standing contribution brick, verifies a safe escape outside the blast cross, and schedules only one bomb at a time. Flames stop at the first intact brick on each ray. Cleared bricks remain passable until the hero returns home and the full calendar resets. A narrow perimeter corridor provides safe entry and escape for dense calendars. This is deterministic SVG choreography, not an interactive game.

GitTanks uses breadth-first search on the contribution grid. One golden tank destroys bricks along clear cardinal firing lines of up to five cells. Waves of up to three silver enemies spawn only on reachable free squares within two Manhattan cells of a standing brick and pursue the hero using hunter, ambusher and flanker roles. No valid spawn means no new wave. Each pursuit tick reserves occupied and destination cells to prevent overlaps and head-on swaps; the hero continues clearing reachable bricks or fights visible enemies at range. Projectile travel time scales with distance; standing bricks and intervening tanks block firing lines. Bounded pursuit gives way to a deterministic interception fallback. The hero absorbs counterfire with a shield and clears every active day once. The calendar restores only after the hero returns home. The eagle remains decorative, and a full grid uses a top-edge entry square. The simulation is precomputed, not an interactive game.

All six public renderers share month-label placement from the calendar module. Every represented month is labeled, including partial boundary months and repeated month names across different years. A 24-pixel spacing rule adjusts label positions without removing months or changing contribution cells.
