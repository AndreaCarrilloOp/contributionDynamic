# Release candidate: v0.2.0-beta.1

## Gate before tagging

- [ ] CI succeeds on the release commit (unit tests, Ruff, action smoke test).
- [ ] Publish contribution animations succeeds and all ten SVGs exist.
- [ ] Verify dark/light rendering, full loops, sparse and dense calendars.
- [ ] Confirm MIT license and review public contribution data.
- [ ] Test the action from a separate repository with a read-only token.
- [ ] Verify the Marketplace action name is available and accept the developer agreement.

## Release notes draft

First public beta of contributionDynamic: five calendar-driven worlds (GitFactory, GitOrigami, GitAbyss, GitChess and GitBlast), dual themes, deterministic demo data, live GraphQL, compact shared timelines, batch CLI and a reusable composite action. This is an early-access release; full browser compatibility and performance benchmarks are not yet established.

Open a new GitHub release from the release commit, create tag `v0.2.0-beta.1`, select pre-release, and publish only after the gates pass. Marketplace listing may be selected in the release form when GitHub validates the action metadata. Do not advertise stable v1 compatibility yet.
