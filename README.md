# willow-grove

**Where the Willow fleet's seams are written down.**

This repo holds cross-repo findings — the places where two components each do
half a job and the halves do not meet. It owns no runtime code and no schema.

> **This is not the Grove app.** The running Textual TUI dashboard is
> [`safe-app-willow-grove`](https://github.com/rudi193-cmd/safe-app-willow-grove).
> This repo was an empty reserved name; it is being used for fleet-level notes
> because no single component repo can own a finding that spans four of them.
> See [Naming](FLEET_SEAMS.md#naming) — there are four grove-ish names in play
> and the store's own spec already flags the confusion.

## What is here

| Document | What it is |
|----------|------------|
| [`FLEET_SEAMS.md`](FLEET_SEAMS.md) | The map: who owns which table, where declaration and enforcement diverge, and four breaks with evidence |

## Why a separate repo

The findings in `FLEET_SEAMS.md` are not any one component's bug. The
human-required queue is split across `willow-2.0` and `willow-mcp`; the
`routing_decisions` race is between `willow-2.0` and `safe-app-willow-grove`;
the manifest ACL is declared in `safe-app-store` and enforced in `willow-mcp`.
Filing each in a component repo makes it look like that component's problem, and
the half that needs to change is usually the other one.

## Reading it

Every claim carries a `file:line` citation into the repo it came from. The
provenance and confidence of each section is stated at the bottom of
`FLEET_SEAMS.md` — including which claims were verified directly and which came
from an automated survey and have not been independently checked.

Findings go stale. Each one carries a "re-verify with" command so a reader can
tell in seconds whether it still holds rather than trusting the date at the top.
