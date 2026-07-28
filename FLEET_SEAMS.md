# Fleet seams

Where two Willow components each do half a job and the halves do not meet.

Surveyed 2026-07-27 against these commits:

| Repo | Commit |
|------|--------|
| `safe-app-willow-grove` | `980aca5` |
| `willow-mcp` | `1fde028` |
| `willow-2.0` | `aeead3b` |
| `safe-app-store` | `42572a3` |
| `Nestor` | `7422c9a` |

**Read [Provenance and confidence](#provenance-and-confidence) before acting on
any of this.** Some claims were verified directly; most come from an automated
survey and carry citations but have not been independently re-checked.

---

## Break 0 — the migration has a direction; one README has not caught up

**Intended direction, confirmed by the operator: all the good from `willow-2.0`
moves into `willow-mcp` and its associated repos. willow-2.0 was a building
block, not the destination.** The migration is *unfinished*, not disputed — but
the artifacts still read as a dispute, which is what made this map get it wrong
the first time.

`willow-2.0/README.md`:

> **Canonical repo:** `willow-1.9`, **`willow-mcp`**, `willow-nest`, and
> `willow-seed` **are archived — everything ships here now.**

`willow-mcp/docs/repatriation/SESSION_HANDOFF.md`:

> It started as a migration audit — **willow-2.0 → willow-mcp**, inventory the
> gap, dedupe

willow-2.0 declares willow-mcp archived — **that line is stale and now
backwards**, and it is the single most misleading sentence in the fleet: it tells
a reader (or an agent) that the destination repo is dead. willow-mcp merged
**PR #190 on 2026-07-27** and holds the plan for moving things *out of*
willow-2.0, which was itself committed to on 2026-07-25. Neither is dormant, but
only one is the target.

**Fixing that README line is the cheapest high-value change available here.**

And the consolidation is a **plan, not a record** —
`willow-mcp/docs/repatriation/CONSOLIDATION_MATRIX.md`, generated 2026-07-18
over 24 repos and 28,825 pieces, with **no completion markers on any row**:

| verdict | clusters | versions |
|---------|---------:|---------:|
| REVIEW | 162 | 406 |
| FOLD→mcp | 72 | 184 |
| STANDALONE-LIB | 54 | 166 |
| APP-LOCAL | 1 | 4 |

`list_channels` alone has 26 versions across three repos.

**So the ownership column below records where code currently lives, not who is
entitled to own it** — and with the direction settled, "currently in willow-2.0"
should be read as *not yet migrated*, not as *owned*.

- The **human queue** (Break 1) is not split-brain at all once the direction is
  known — willow-mcp's copy is the *port*, and Grove is still reading the
  original.
- The **`routing_decisions` race** (Break 2) is two live repos both creating one
  table, each believing itself authoritative.
- The **duplicate Grove inside willow-2.0** is not an accident — it is willow-2.0
  acting as the canonical home while Grove also ships separately.

**The remaining decision is narrower than "who owns the schema".** It is: does
willow-mcp take ownership of the shared fleet Postgres (lifting B-28 with
operator consent), or does the fleet move off shared Postgres onto willow-mcp's
SOIL store, and consumers get repointed? willow-mcp's own design leans hard
toward the second — see Break 1.

---

## The map

Read this as *where the code is today*, not *where it belongs*. Rows marked
*(not yet migrated)* live in willow-2.0 and are destined for willow-mcp per
Break 0 — the direction is settled, the move is not done.

| Thing | Declared in | Where it currently lives | Read by |
|-------|-------------|--------------------------|---------|
| `public.human_required_queue` | — | willow-2.0 *(not yet migrated)* | Grove |
| `human_required` (SQLite collection) | — | willow-mcp *(not yet migrated)* | *nobody* |
| `grove.*` (channels, messages, message_flags, agent_cursors) | — | willow-2.0 *and* Grove, independently *(not yet migrated)* | Grove, willow-2.0 |
| `willow.routing_decisions` | Grove `schema.sql` (stub) | **both**, racing *(not yet migrated)* | Grove |
| `public.routing_decisions` | — | willow-2.0 *(not yet migrated)* | willow-2.0 |
| `frank_ledger` | — | willow-2.0 governance schema *(not yet migrated)* | willow-mcp appends |
| `frank_write` permission | — | **willow-mcp** `gate.py` | — |
| App manifests | **safe-app-store** | **willow-mcp** resolves via `whoami` | — |

The shape of every break below: **declaration and enforcement live in different
repos**, and the link between them is either missing, racing, or pointed at the
wrong datastore. None of them fails loudly.

---

## Break 1 — Grove reads the legacy half of a migrated queue

**Corrected.** An earlier revision of this document called willow-mcp's copy
"orphaned" and willow-2.0's the working one. That is backwards. willow-mcp's is
**the port** — `willow-mcp/src/willow_mcp/human_loop.py:14-22`:

> Two deliberate departures from the willow-2.0 original: **1. SOIL, not the
> fleet Postgres.** willow-2.0 backs these with Postgres tables … **the port
> homes them there.**

```
willow-2.0  →  Postgres  public.human_required_queue   →  Grove reads it   (legacy origin)
willow-mcp  →  SOIL      "human_required" collection   →  nothing reads it (the port)
```

So nothing is orphaned — **Grove has simply not been repointed.** It is wired to
the repo being migrated out of, and the destination's queue has no reader yet.
That is why a stock Grove shows an empty pane: not a bug in either queue, but a
consumer still pointed at the old world.

**willow-2.0 — the origin, still running.** Owns the Postgres table and is the
only reason Grove's pane ever shows anything:

- DDL — `willow-2.0/core/pg_bridge.py:380` (repeated in `_MIGRATIONS` at `:503`)
- `INSERT` — `willow-2.0/core/human_required.py:178`
- `UPDATE` — `willow-2.0/core/human_required.py:289`
- Agent-facing MCP tool `human_required_queue_enqueue` — `willow-2.0/sap/sap_mcp.py:6431`

**willow-mcp — the port, with no consumer yet.** Same primitive, homed on SOIL:

- `QUEUE_COLLECTION = "human_required"` — `willow-mcp/src/willow_mcp/human_loop.py:44`
  (note: no `_queue` suffix)
- `store.put(...)` — `willow-mcp/src/willow_mcp/human_loop.py:194`
- backing store is SQLite — `willow-mcp/src/willow_mcp/db.py:77`
- MCP tool `human_required_enqueue` — `willow-mcp/src/willow_mcp/server.py:4485`

**Why the port chose a different datastore** —
`willow-mcp/src/willow_mcp/human_loop.py:16-22`:

> SOIL, not the fleet Postgres. willow-2.0 backs these with Postgres tables
> (`human_required`, `human_attestations`) and `core.pg_bridge`. Porting that
> verbatim would drag a schema migration into the *shared fleet database* — the
> operator-gated act willow-mcp refuses to take unilaterally (B-28).

That is a deliberate, defensible choice — and it is also the thing that leaves a
gap during the migration, because **an agent escalating through the port reaches
no surface a human is watching.** Not because the port is wrong, but because
nothing has been repointed at it yet.

The vocabularies have drifted too, so repointing Grove is not purely a
connection-string change:

| willow-2.0 (`core/human_required.py:13-18`) | willow-mcp (`server.py:4485`) |
|---|---|
| `needs_consent` | `consent` |
| `needs_attestation` | `attestation` |
| `needs_review` | `review` |
| `operator_overload` | `overload` |
| `external_onboarding` | `onboarding` |

Grove renders `kind.replace("_", " ")`
(`safe-app-willow-grove/panes/human.py:118`), so it is built for willow-2.0's
spelling.

**Impact.** During the migration the human sees only the escalations still
arriving through the origin, with no indication that a second queue exists — and
on a standalone Grove, which never gets willow-2.0's schema, they see nothing at
all behind a green tick.

**The concrete task** is repointing Grove at the port (or at both, labelled),
plus reconciling the `kind` vocabulary. Neither is blocked on the ownership
question — the direction is settled.

**Re-verify with**
`grep -rn "human_required" willow-mcp/src/willow_mcp/human_loop.py willow-2.0/core/human_required.py`

---

## Break 2 — two repos race to create `willow.routing_decisions`

Same table name, different shapes, both `CREATE TABLE IF NOT EXISTS`. **Whichever
process starts first wins; the loser silently no-ops.**

- willow-2.0 creates it lazily — `willow-2.0/core/grove_reader.py:604-617`
  (`ts, session_id, prompt_snippet, routed_to, rule_matched, confidence, latency_ms`)
- Grove ships its own in `safe-app-willow-grove/schema.sql`
- willow-2.0 knows — `willow-2.0/docs/db/WILLOW_SCHEMA.md:7-9`:

> **Authoritative source:** `core/pg_bridge.py`. **Note:**
> `safe-app-willow-grove/schema.sql` includes a **stub** `willow.routing_decisions`
> for standalone installs. The **rich** shapes are created by `pg_bridge` in a
> full Willow install.

Knowing is not reconciling: no migration exists, and `IF NOT EXISTS` means the
"authoritative" definition loses whenever Grove boots first.

A third table shares the base name and is *not* the same thing —
`public.routing_decisions` (`willow-2.0/core/pg_bridge.py:319-327`), documented
at `willow-2.0/core/grove_reader.py:622-624`. willow-mcp has a fourth DDL for an
unqualified `routing_decisions` (`willow-mcp/docs/schema/routing_decisions.postgres.sql:18`).

**Impact.** Schema depends on boot order. A column Grove's reader expects may
simply not exist, with no error at create time.

**Re-verify with**
`grep -rn "routing_decisions" willow-2.0/core/grove_reader.py safe-app-willow-grove/schema.sql`

---

## Break 3 — apps declare in one repo, the gate enforces in another

The manifest ACL is real and well built. It is just not where the manifests are.

**Declared in `safe-app-store`:** `safe-app-manifest.json` per app, `catalog.json`,
a human consent modal at install (`safe-app-store/tui.py:110-195`, blocking at
`:624`), and CI shape-linting.

**Enforced in `willow-mcp`:**

- `"frank_write": frozenset({"frank_append"})` — `willow-mcp/src/willow_mcp/gate.py:97-99`
- missing manifest or empty permissions → deny, fail-closed — `gate.py:13`
- deliberately excluded from `full_access` — `willow-mcp/docs/design/permissions-matrix.md:51`
- additionally requires the human-orchestrator seat — `willow-mcp/src/willow_mcp/human_session.py:24-33`

`safe-app-store` itself enforces nothing: `grep 'def whoami'` returns nothing
there, and `frank_write` does not appear anywhere in it. Its own docs say so —
`safe-app-store/docs/conventions/gate-record.md:90-93`:

> A safe-app-store app declares what it may do … in `safe-app-manifest.json`;
> **the willow-mcp gate resolves it via `whoami`**. The grant is the operator's —
> the app declares, it does not self-authorize.

**Worth preserving:** writing a manifest is CLI-only and explicitly forbidden
from being an MCP tool — `willow-mcp/src/willow_mcp/manifest_admin.py:4-9`:
*"an agent could otherwise grant itself whatever it was just denied."* That is
the right instinct and should survive any consolidation.

**Impact.** No single repo can be reviewed to answer "what may this app do?"

---

## Break 4 — Grove is in the catalog but granted nothing

`safe-app-store/catalog.json:267-286` lists `willow-grove` with `"canonical": true`
— and:

- **no `path`**, so no `apps/willow-grove/` directory exists
- **no manifest in the store**, so no declared permissions
- **exempt from the manifest lint** — `safe-app-store/tools/catalog_lint.py:71-73`
  only errors on a missing manifest when the entry has a local `path`
- **not installable** — `safe-app-store/store_mcp.py:172` hardcodes
  `source="monorepo"`

The only real coupling is an env var: `WILLOW_GROVE_ROOT` pointing at a
filesystem path, injected into every app's MCP config
(`safe-app-store/.mcp.json:11` and ~18 copies under `apps/*/.mcp.json:13`). A
path is not a permission grant.

**Impact.** Grove is a name, a URL and nine tags. Its manifest is never
validated by anything.

---

## Smaller drift

- **`grove.messages` bus columns are added by runtime `ALTER`**, not by the base
  `CREATE` — `to_agent`, `bus_type`, `priority`, `correlation_id`, `ttl` at
  `willow-2.0/core/grove_db.py:145-158`, applied conditionally after probing
  `information_schema`. Anything bootstrapped from a plain schema file lacks
  columns that agent writers depend on
  (`willow-2.0/agents/hanuman/lib/skill_steward.py:288`).
- **NOTIFY channel mismatch.** The trigger fires `pg_notify('grove_channel', …)`
  (`willow-2.0/core/grove_db.py:191-212`) while agents issue
  `NOTIFY grove_messages` (`willow-2.0/agents/hanuman/lib/skill_steward.py:294`).
  Two channels, one bus.
- **`public.tasks` id type conflict**, already flagged in-repo —
  `willow-2.0/docs/db/WILLOW_SCHEMA.md:26-31`: *"`id` TEXT PK in pg_bridge …
  Standalone `schema.sql` may use BIGINT id — converge on one bootstrap path."*
- **`frank_ledger` DDL is in willow-2.0, not willow-mcp** —
  `willow-mcp/docs/schema/frank-ledger-prevent-fork.sql:13-15` says so, and
  `willow-mcp/src/willow_mcp/governance_ledger.py:78` INSERTs into a table
  nothing in willow-mcp creates. A consumer pointed at a fresh database gets a
  silent no-op if its forwarder is best-effort — which Nestor's is by design.
- **A whole second Grove lives in willow-2.0** — `willow-2.0/grove/` (MCP
  server), `willow-2.0/scripts/grove_standalone.py` (TUI),
  `willow-2.0/core/grove_db.py` (schema, marked *"self-contained — no sibling
  repo dependency"*). Meanwhile `willow-2.0/sap/ONBOARDING.md:35` tells agents
  `grove_*` tools live on the Grove MCP server, while
  `willow-2.0/sap/grove_tools.py` registers them on the willow MCP anyway.
  willow-mcp's `docs/repatriation/CONSOLIDATION_MATRIX.md:15-68` already
  inventories ~30 duplicated Grove functions.

---

## The recurring pattern

Every break above has the same shape, and it is worth naming because it defeats
review: **correct components, absent linkage, rendered as success.**

Grove's human pane is the clearest instance. `fetch_human_queue`
(`safe-app-willow-grove/panes/human.py:31-35`) catches every exception and
returns `[]`, and an empty list renders as:

```
Human — required actions   ✓ queue clear
```

So *"I could not reach the queue"* and *"nothing is waiting for you"* are the
same pixels, with a green check on the failure — on the one surface whose stated
purpose is that automation pauses until a human acts. That file states the
principle it then undercuts (`panes/human.py:5-7`):

> a human+agent workspace that hides its own consent gates is not honestly
> collaborative — it just looks like one.

The same fail-soft appears 18 times in `safe-app-willow-grove/grove_reader.py`,
so it is house style rather than an oversight in one pane. `panes/agents.py:104`
does it too: no heartbeat rows renders as `no agents / on bus`, which reads as a
quiet fleet rather than an unreachable one.

**The fix is a third state.** These surfaces have "empty" and "populated" but no
"unknown". A sibling project solved the same problem by making the three states
structural and never guessable — an answer is `sealed`, `draft`, or `pending`,
and `pending` says *"nothing to offer"* rather than improvising. Grove needs the
equivalent: *"could not reach the source"* must not collapse into *"clear"*.

**It is not Grove's pattern — it is the fleet's.** A later per-repo review found
the same shape in `safe-app-store` (a *missing* manifest rendering as "No special
permissions required"), in `willow-2.0` (`sap/middleware.py:211-212` returns `[]`
on any policy-load error, so every rate rule silently stops firing), and in
`willow-mcp` (`oauth.py:77-83` turns a corrupt token store into an empty valid
one). It also found the cure already written, in about six files across the same
four repos. See [`CODE_REVIEW.md`](CODE_REVIEW.md#the-one-pattern).

---

## Naming

Four grove-ish names, one of them empty:

| Name | State |
|------|-------|
| `safe-app-willow-grove` | the running TUI — 208 files |
| `willow-2.0/grove/` + `scripts/grove_standalone.py` | a duplicate MCP server and TUI |
| `safe-app-grove` | a *different* app in the catalog (p2p messaging) |
| `willow-grove` | this repo — was empty, now holds these notes |

`safe-app-store/docs/system_spec.md:325-327` already flags it:
*"safe-app-willow-grove | unknown | Grove variant — relationship to
safe-app-grove unclear."*

Also a false friend: `willow-mcp/src/willow_mcp/the_grove.py` is a local JSON
store of "rings of lessons" with no relation to the Grove app. Grep carefully.

---

## Open questions

0. **Answered:** the destination is `willow-mcp` and its associated repos.
   willow-2.0's README still says the opposite and should be corrected — it is
   the one artifact actively pointing readers and agents the wrong way.
1. Does willow-mcp take ownership of the shared fleet Postgres (lifting B-28
   with operator consent), or does the fleet move onto its SOIL store and
   consumers get repointed? willow-mcp's own design leans toward the second.
   Either way **Grove needs repointing at the port**, which is the concrete task
   behind the empty pane.
2. Who owns `grove.*` after consolidation? Two independent bootstraps currently
   race, and Break 0 means there is no agreed answer to appeal to.
3. Should `safe-app-store` gain enforcement, or should manifests move to where
   the gate is?
4. Does Grove's `schema.sql` still need to exist, given `pg_bridge` is
   authoritative? It is the losing half of Break 2.

---

## Provenance and confidence

**Reproduced against a live PostgreSQL 16 instance** (2026-07-27, Grove at
`980aca5`, deps installed from its own `requirements.txt`, schema loaded with its
own `schema.sql` exactly as its README instructs):

```
$ createdb willow_20 && psql -d willow_20 -f schema.sql
$ python -c "from panes.human import fetch_human_queue; print(fetch_human_queue())"
grove_reader.human_required_queue: relation "public.human_required_queue" does not exist
[]
```

The pane therefore renders `Human — required actions  ✓ queue clear` /
`nothing awaiting you`. **This is not a failure mode — it is what a stock Grove
install does.** The database is up and healthy; `grove.channels` queries fine.
`human_required_queue` simply belongs to willow-2.0 (§Break 1) and Grove's own
`schema.sql` does not create it, so a standalone Grove shows a permanent green
check on the one surface whose stated purpose is that automation pauses until a
human acts.

Worse, the warning that *is* emitted reaches nobody: `grove_reader` logs to a
module logger, and `app.py:37` routes logging to
`~/.willow/grove_error.log` — a file, at DEBUG level, not the screen. So the
operator sees a green tick and the explanation is in a log they have no reason
to open.

**Directly verified** (read or executed against the working tree):

- Grove's `schema.sql` creates `channels`, `messages`, `message_flags`,
  `agent_cursors`, `willow.routing_decisions`, `public.tasks`,
  `public.binder_edges`, `public.binder_files` — and **not**
  `human_required_queue` (`grep -c` returned 0).
- `safe-app-willow-grove/panes/human.py` and `grove_reader.py:1180` — the read
  path, the fail-soft, and the `✓ queue clear` rendering.
- 18 `return []` fail-softs in `safe-app-willow-grove/grove_reader.py`.
- `willow-grove` was an empty repository — no commits, no refs.

**From an automated survey, cited but not independently re-checked** — every
claim about `willow-mcp`, `willow-2.0` and `safe-app-store`, including all
`file:line` references to those repos. They were produced by three read-only
agents, one per repo, each instructed to cite `file:line` and to say plainly when
something could not be found. Spot-check before acting on any single one.

**Two corrections, recorded so they are not re-derived.**

1. An early hypothesis held that *nothing* writes `human_required_queue`, and so
   Grove's pane had never displayed a real item. Wrong — willow-2.0 writes it
   (`core/human_required.py:178`), and on a full install the link works.
2. This document then called willow-mcp's queue "orphaned" and willow-2.0's "the
   one that works". Also wrong, and in a more instructive way: willow-mcp's is
   the **port** (`human_loop.py:14-22`), willow-2.0's is the origin, and Grove
   is the consumer that has not been repointed.

The second error came from the method. The survey agents were asked *where code
is*, which cannot distinguish a port from an original — both look like live
implementations. Only knowing the migration's intended direction separates them,
and that came from the operator, not the repositories. **Treat every ownership
claim in this document as "where it currently lives"; ask a human which way the
migration runs before inferring anything else from it.**
