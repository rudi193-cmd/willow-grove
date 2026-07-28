# Design constraints for the fresh build

Willow Grove is being rebuilt here rather than transplanted. That makes the
findings in [`FLEET_SEAMS.md`](FLEET_SEAMS.md) usable as constraints instead of
as a post-mortem: each item below is something the current implementation or its
neighbours got wrong, stated as a rule the new build can be held to.

Every constraint carries **how to check you complied**, because a constraint
without a test is a preference. Where a rule is a judgement call rather than a
correctness requirement, it says so.

Confidence caveat: constraints 2–5 rest partly on an automated survey of
`willow-mcp`, `willow-2.0` and `safe-app-store` that has not been independently
re-verified. See [Provenance](FLEET_SEAMS.md#provenance-and-confidence). Confirm
before treating any of them as settled fact.

---

## 1. Never render absence as assurance

**Rule.** Every surface has at least three states — *populated*, *empty*, and
**unknown**. "I could not reach the source" must never collapse into "there is
nothing there."

**Where it comes from.** `safe-app-willow-grove/panes/human.py:31-35` catches
every exception and returns `[]`; an empty list renders as
`Human — required actions  ✓ queue clear`. So a dead database and a clear queue
are the same pixels, with a green check on the failure — on the surface whose
stated purpose is that automation pauses until a human acts. The same fail-soft
appears 18 times in `safe-app-willow-grove/grove_reader.py`, and again in
`panes/agents.py:104`, where no heartbeats renders as `no agents / on bus`.

That file states the principle it then undercuts (`panes/human.py:5-7`):

> a human+agent workspace that hides its own consent gates is not honestly
> collaborative — it just looks like one.

**Rule of thumb.** A reader function returns `Result[list] | Unreachable`, not
`list`. The renderer must be unable to display "clear" without having actually
received an answer. If that requires a sentinel rather than a bare list, use one.

**This is the load-bearing constraint.** Every other item here is a specific
instance of it.

**Check.** Kill the database and open every pane. Any pane that shows a green
state, a zero count, or an empty-but-fine message has failed. Do this as a test,
not by hand: point the app at an unreachable DSN in CI and assert no surface
reports health.

---

## 2. Do not create schema you do not own

**Rule.** The app either reads a schema someone else owns, or owns a schema
nobody else creates. Never `CREATE TABLE IF NOT EXISTS` against shared ground.

**Where it comes from.** `willow.routing_decisions` is created by both
`willow-2.0/core/grove_reader.py:604-617` and `safe-app-willow-grove/schema.sql`,
with different shapes and both using `IF NOT EXISTS` — so **boot order silently
decides the schema and the loser no-ops**. `willow-2.0/docs/db/WILLOW_SCHEMA.md:7-9`
names `core/pg_bridge.py` authoritative and calls Grove's copy a "stub", but no
migration reconciles them. Related: `public.tasks` has a `TEXT` vs `BIGINT` id
conflict already flagged at `WILLOW_SCHEMA.md:26-31`.

**Consequence to avoid.** A column the reader expects may simply not exist, with
no error at create time and no error at boot — only a failure much later, in a
query, on someone else's machine.

**Check.** `grep -rn "CREATE TABLE" src/` should return nothing for any table
also created by `willow-2.0/core/pg_bridge.py` or `core/grove_db.py`. If the app
needs a table of its own, name it distinctly and say who owns it in a comment.

---

## 3. Decide the human-queue question out loud

**Rule.** The human-required surface must state which sources it covers, and
must visibly indicate when a source is unavailable or unread.

**Where it comes from.** Two implementations of one concept exist:
`willow-2.0/core/human_required.py:178` writes Postgres
`public.human_required_queue` (which today's Grove reads), and
`willow-mcp/src/willow_mcp/human_loop.py:194` writes a SQLite collection named
`human_required` that **nothing reads**. The split is deliberate
(`human_loop.py:16-22` — willow-mcp will not migrate the shared fleet DB
unilaterally, B-28); the orphaning was not. The `kind` vocabularies have also
drifted (`needs_consent` vs `consent`), so repointing the datastore alone would
not merge them.

**With the migration direction settled, this has a preferred answer.**
willow-mcp's SOIL queue is the *port*; willow-2.0's Postgres table is the
original. A fresh build should target the port, not the origin:

- **Read willow-mcp's SOIL queue** — the destination, and the only one that
  survives the migration.
- Read both *during* the migration, tagging each item with its source, and say
  in the UI which is which.
- Read willow-2.0's Postgres only — **and label the pane with that scope**, so a
  reader knows willow-mcp escalations are excluded. This is what today's Grove
  does, minus the label.

Silently doing the last one is what produces an empty pane on a stock install.

**Judgement call**, not a correctness requirement — except the labelling, which
is constraint 1 applied to scope rather than to reachability.

**Check.** Ask someone who has not read this file: "does this pane show
everything the fleet has escalated?" If they cannot answer from the UI, it fails.

---

## 4. Ship a manifest that something actually validates

**Rule.** If the app is a store app, it declares permissions in
`safe-app-manifest.json` and something in CI validates that file.

**Where it comes from.** `safe-app-store/catalog.json:267-286` lists
`willow-grove` with `"canonical": true` — and no `path`, no manifest in the
store, no declared permissions. It is exempt from the manifest lint by
construction: `safe-app-store/tools/catalog_lint.py:71-73` only errors on a
missing manifest when the entry has a local `path`. It is also not installable —
`safe-app-store/store_mcp.py:172` hardcodes `source="monorepo"`.

Note the ACL that would enforce a manifest lives in `willow-mcp`
(`gate.py:97-99`, resolved via `whoami`), not in the store. The store is a
declaration surface; `safe-app-store/docs/conventions/gate-record.md:90-93` says
so directly.

**Check.** A manifest exists, `catalog_lint.py --strict` actually exercises it,
and `whoami` resolves the declared permissions to something non-empty. If the
entry stays external-repo-only, at minimum lint the manifest in **this** repo's
CI, since the store's lint will keep skipping it.

---

## 5. Do not become the third fork

**Rule.** Before porting a subsystem, check whether it already exists twice.

**Where it comes from.** `willow-2.0` carries a complete second Grove:
`willow-2.0/grove/` (MCP server), `willow-2.0/scripts/grove_standalone.py`
(TUI), `willow-2.0/core/grove_db.py` (schema, marked *"self-contained — no
sibling repo dependency"*). Agent instructions contradict each other about who
owns the tools — `willow-2.0/sap/ONBOARDING.md:35` says `grove_*` lives on the
Grove MCP server, while `willow-2.0/sap/grove_tools.py` registers them on the
willow MCP anyway. `willow-mcp/docs/repatriation/CONSOLIDATION_MATRIX.md:15-68`
already inventories ~30 duplicated Grove functions.

A fresh public build makes **three** unless the ownership question is settled
first.

**Check.** For each subsystem, name the one repo that owns it before writing it.
If the answer is "two", the destination is **`willow-mcp` and its associated
repos** — the good from willow-2.0 moves there, and willow-2.0 was a building
block rather than the target ([`FLEET_SEAMS.md` Break 0](FLEET_SEAMS.md#break-0--the-migration-has-a-direction-one-readme-has-not-caught-up)). Beware
willow-2.0's README, which still declares willow-mcp archived; that line is stale
and backwards. Port *from* willow-2.0, target willow-mcp's surfaces, and do not
build a fresh dependency on willow-2.0's schema. `NESTOR_ON_GROVE.md` (in
this repo, when the survey completes) measures which duplicates are genuinely
the same code versus which only look alike — use it rather than eyeballing.

---

## 6. Keep the bus contract single-valued

**Rule.** One NOTIFY channel name, one flag vocabulary, one set of column names,
each defined in exactly one place.

**Where it comes from.** The trigger fires `pg_notify('grove_channel', …)`
(`willow-2.0/core/grove_db.py:191-212`) while agents issue
`NOTIFY grove_messages` (`willow-2.0/agents/hanuman/lib/skill_steward.py:294`) —
two channels on one bus. Separately, `grove.messages`'s bus columns
(`to_agent`, `bus_type`, `priority`, `correlation_id`, `ttl`) are added by
runtime `ALTER` after probing `information_schema`
(`willow-2.0/core/grove_db.py:145-158`), not by the base `CREATE` — so a
plain-schema bootstrap lacks columns that writers depend on.

**Check.** Every channel name, flag string and bus column appears as a named
constant in one module. `grep` for the literal should find the constant and its
uses, never a second definition.

---

## 7. Do not add a fifth Grove name

**Rule.** State in the README what this repo is and what it is not.

**Where it comes from.** Four grove-ish names already exist —
`safe-app-willow-grove` (running), `willow-2.0/grove/` (duplicate),
`safe-app-grove` (a *different* p2p app), and this repo.
`safe-app-store/docs/system_spec.md:325-327` already flags the confusion as
unresolved. There is also a false friend: `willow-mcp/src/willow_mcp/the_grove.py`
is an unrelated local JSON store of "rings of lessons".

**Check.** A newcomer reading only the README can say which repo runs, which is
archived, and which is this. Retire or clearly mark the others as part of
landing the build.

---

## What to carry over

The current implementation has good instincts worth keeping, not just mistakes:

- **The stated principle** in `panes/human.py:5-7` — that hiding consent gates
  makes a workspace *look* collaborative rather than *be* it. Constraint 1 exists
  to make the code match that sentence.
- **Manifest writes are CLI-only and explicitly forbidden from being an MCP
  tool** — `willow-mcp/src/willow_mcp/manifest_admin.py:4-9`: *"an agent could
  otherwise grant itself whatever it was just denied."* Whatever the new build
  exposes, no surface it offers should be able to widen its own permissions.
- **Fail-closed gates.** `willow-mcp/src/willow_mcp/gate.py:13` denies on a
  missing manifest. Grove's own reads fail *soft*, which is the opposite posture
  — reads and grants can legitimately differ here, but the choice should be
  deliberate per call site rather than inherited by copy-paste.
- **The compact presence vocabulary** (`●` `◐` `○`, and the state colouring in
  `panes/chat_format.py:214-234`) reads well and is cheap to keep.

---

## Using this file

Treat it as a checklist at review time, not a manifesto. When a constraint stops
being relevant, delete it and say why in the commit message — a stale constraint
is worse than none, because it trains people to skip the list.
