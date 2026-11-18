# Architecture

The engine uses an immutable contribution calendar, deterministic demo input, a GitHub GraphQL collector, five scenario planners and self-contained SVG renderers. Shared calendar helpers resolve intensity and board width; shared label and animation modules serialize consistent SVG geometry and timelines.

SVG output uses embedded declarative animation without JavaScript. GitHub image rendering compatibility and live API access require verification.

The collector accepts credentials from the environment through the CLI. The default demo requires no token.

GitOrigami animates six triangular SVG paper panels per active day. A deterministic active-cell wave schedules folding, flight and fade-out without waiting for empty columns. Each source cell is restored after its own flight. The CLI selects a renderer through a scenario registry. CI generates demo previews without credentials; the manual publishing workflow fetches live data once for the five public scenarios.

Publishing renders and XML-validates ten public assets from one calendar before uploading an artifact. A separate job with contents write permission updates the output branch without force-pushing. Generation uses read-only repository permissions and receives the contribution token only during the fetch step. Existing assets remain available if generation fails.

GitChess schedules a team of up to four attackers with queen, rook, bishop and knight movement. A breadth-first search plans unobstructed captures and preparatory moves, with a shared occupancy map preventing friendly collisions. The team takes turns. After every active day has been captured, attackers return to their starting squares before restoration. Reverse traversal is a deterministic fallback for obstructed return paths.

All five public scenarios share SMIL timeline serialization, retaining plateau boundaries while removing redundant interior keyframes and trailing numeric zeros. The registry drives batch generation and the composite action; selected themes and scenarios reuse one calendar fetch. No runtime speedup or browser-performance guarantee has been benchmarked yet.

GitChess uses contiguous, low-contrast sage squares and reserve dots of four radii. At most four upcoming targets are visible as level-coded dark chess pieces; all other contributions remain quiet dots. Source coordinates, metadata and activity levels are preserved.

GitBlast uses one persistent actor and a BFS route through free squares. The planner selects a reachable bomb site adjacent to a standing contribution brick, verifies a safe escape outside the blast cross, and schedules only one bomb at a time. Flames stop at the first intact brick on each ray. Cleared bricks remain passable until the hero returns home and the full calendar resets. A narrow perimeter corridor provides safe entry and escape for dense calendars. This is deterministic SVG choreography, not an interactive game.

GitTanks uses breadth-first search on the contribution grid. One golden tank destroys bricks along clear cardinal firing lines of up to five cells. Waves of up to three silver enemies spawn only on reachable free squares within two Manhattan cells of a standing brick and pursue the hero using hunter, ambusher and flanker roles. No valid spawn means no new wave. Each pursuit tick reserves occupied and destination cells to prevent overlaps and head-on swaps; the hero continues clearing reachable bricks or fights visible enemies at range. Projectile travel time scales with distance; standing bricks and intervening tanks block firing lines. Bounded pursuit gives way to a deterministic interception fallback. The hero absorbs counterfire with a shield and clears every active day once. The calendar restores only after the hero returns home. The eagle remains decorative, and a full grid uses a top-edge entry square. The simulation is precomputed, not an interactive game.

All five public renderers share calendar geometry and SVG label rendering. Months are anchored at the exact first displayed week; overlapping boundary months occupy alternating header baselines without shifting columns. Mon, Wed and Fri are right-aligned and vertically centered on Sunday-first rows 1, 3 and 5. The shared gutter reserves space for arcade perimeter movement.

GitChess uses the shared month and weekday header. A restrained origin-and-destination highlight replaces separate capture flashes. Opposing contribution pieces remain stationary; this is a tactical visualization, not a full two-player chess engine.

GitInvaders schedules one persistent ship against a formation of original pixel-art aliens. Each active day maps to one alien, with its relative contribution level determining silhouette and color. The formation sways along a common horizontal timeline, holding its position during each column's engagement. The lowest remaining alien fires first; the ship evades, realigns and clears that column from bottom to top. Laser positions, enemy visibility and cell restoration share the battle clock; no empty days generate invaders. At the loop boundary the ship and formation return home and all active cells restore. GitFactory and GitAbyss are retired from the public catalog; their implementation remains recoverable in Git history.
