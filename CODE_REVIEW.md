# Whole-box code review — 2026-07-28

[`FLEET_SEAMS.md`](FLEET_SEAMS.md) maps the gaps **between** repos. This file
covers what is inside each one: what is good enough to preserve through the
migration, what is wrong, and what the MCP `2026-07-28` specification changes.

Reviewed at these commits:

| Repo | Commit | Branch |
|------|--------|--------|
| `Nestor` | `6bca7c3` | `claude/good-evening-qvgc23` |
| `willow-mcp` | `51aae64` | `experiment/github-transport` |
| `safe-app-willow-grove` | `3ab5691` | `deps/bound-the-pins` |
| `willow-2.0` | `4145226` | `master` |
| `safe-app-store` | `42572a3` | `master` |

**Read [Provenance](#provenance) before acting on any single item.** Findings
marked **[verified]** were re-read or executed directly. The rest come from
read-only survey agents, one per repo, and carry citations but not confirmation.

Nothing was modified in any repo to produce this document.

---

## The one pattern

Every repo has the same disease, and every repo already contains its own cure.

**Absence rendered as success.** A read fails, the failure is swallowed, and the
empty result is drawn as a confident fact. This is the same finding
[`FLEET_SEAMS.md` records for Grove's human pane](FLEET_SEAMS.md#the-recurring-pattern)
— but it is not one pane's bug, or one repo's. It is house style in four
codebases:

| Repo | Instance |
|------|----------|
| `safe-app-willow-grove` | `panes/human.py:31-35` → `✓ queue clear` on an unreachable database |
| `safe-app-store` | `tui.py:160-162` → `"No special permissions required."` when the manifest is **missing** |
| `willow-2.0` | `sap/middleware.py:211-212` → `return []` on any policy-load error, so every rate rule silently stops firing **[verified]** |
| `willow-mcp` | `oauth.py:77-83` → a corrupt token file becomes an empty-but-valid one, and the next save makes it permanent |
| `Nestor` | the original: a fuzzy match below threshold once served as a seal |

The cure also exists, written by the same hands, in about six files:

- `safe-app-willow-grove/grove/apps/vitals.py:167-171` carries an `ok` flag all
  the way to the glyph and renders `kart○`, never `kart 0/0`. Two tests pin it
  (`tests/test_vitals.py:114-118, 133-138`). **Unmeasurable and zero are
  different symbols.**
- `willow-mcp/src/willow_mcp/lease.py:44-55` states in its own module docstring
  what the mechanism does *not* fix, and `self_writable_trust_paths()` (`:333-362`)
  programmatically enumerates the trust-root keys *this process* could forge —
  rather than asserting a membrane it just measured a hole in.
- `willow-2.0/constitution/compliance.py:55-62` encodes "no attempt ≠ a pass" at
  the type level.
- `Nestor`'s three states — `sealed` / `draft` / `pending`. The whole engine is
  this principle.

That is the fleet's actual thesis. It is implemented in roughly six files and
violated in roughly a hundred and fifty. [Constraint
1](DESIGN_CONSTRAINTS.md#1-never-render-absence-as-assurance) already states the
rule; this document is the evidence of how far the practice is from it.

---

## Nestor

The healthiest thing in the box, and the only repo with no instance of the
pattern above. **[verified]** — this section is a first-hand review, not a survey.

**Good.**

- 128 tests green. All six `except Exception` handlers are justified at their
  call site.
- **No MCP SDK dependency at all** — `pyproject.toml` declares `dependencies = []`
  and `frank.py` reaches FRANK over raw `subprocess` + JSON. The
  `2026-07-28` spec cannot break Nestor directly.
- The `Matcher` and `Storage` protocols are real seams, not nominal ones: the
  optional-capability probes (`supports_rejection()`, `supports_curation()`) are
  all-or-nothing, so a half-implemented store cannot present as whole.
- The bench now exercises the regime that hid two real matcher bugs, with tests
  (`tests/test_bench_coverage.py`) that fail if the corpus ever drifts back below
  difflib's 200-element `autojunk` threshold.

**Needs improvement.**

1. **`ClaudeEngine` has zero test coverage** despite four exception handlers. It
   is the only substantial module in that position.
2. **An engine failure aborts the whole document.** Reproduced: an engine raising
   after two segments leaves `segments persisted: 2, document status:
   pending_review`. Tier 0 / `pending` exists for exactly this case and is not
   used here — the partial result should be servable-as-pending, not an abort.
3. **`translate_text` accepts only `engine_name=`, never `engine=`** — the one
   seam in the codebase that cannot be injected, which is why (1) is hard.
4. Four modules have no named test file.

---

## willow-mcp

The best-reasoned code in the fleet. Its comments are load-bearing: the
permission-group splits in `gate.py:117-249` each record *why* the split exists,
and a mechanical regeneration of those groups would silently re-merge them.

**Good — worth preserving verbatim through any consolidation.**

- **The three-key egress gate** (`web_egress.py:8-45`): a manifest capability, a
  standing operator switch, and a time-boxed lease. What matters is not the three
  keys but that they are deliberately non-substitutable, and the code says so on
  the line that would otherwise tempt a merge (`gate.py:326-341`): network egress
  from the sandbox "must be granted on its own line, so a broad
  `task_queue`/`full_access` grant never silently carries net access with it."
- **`lease.py`** — see [The one pattern](#the-one-pattern). Also: readers must
  never `mkdir` the trust root (`:88-101`), a lease with a naive timestamp is
  refused (`:198-209`, *"a deadline without a zone is not a deadline; it is a
  wish"*), and a lease whose body names a different `app_id` than the file it
  sits in is refused (`:250-257`).
- **Fail-closed defaults where the closed direction is non-obvious, and named.**
  `gate.store_scope` (`:371-413`) distinguishes absent / well-formed /
  undeterminable and denies on the third, naming the exact typo it defends
  against. `egress_secret_exempt` (`:422-456`) — *"the closed direction here is
  REDACT."* `consent._strict_bools` (`:91-98`) — *"1, 'true', and 'yes' are not
  consent."*
- **Structured, length-delimited signing payloads.** `session_binder.call_sig`
  (`:112-120`) hashes a JSON array with a domain-separation tag rather than a
  `|`-joined string; `receipts._entry_hash` (`:45-49`) cites the Nestor B4 lesson
  by name.
- **Manifest writes are CLI-only**, verified: no `@mcp.tool()` reaches
  `set_permission`. And the subtlety at `manifest_admin.py:66-71` — revoking from
  an app with *no* manifest is a deliberate write-nothing no-op, because
  materialising an empty manifest would turn a revoke into a store **grant**.
- **`require_operator_terminal()`** (`human_session.py:55-79`) — `isatty()` alone
  is forgeable by a process that allocates a pty; this adds a not-in-sandbox check
  and requires the controlling terminal's `st_uid` to match.

**Needs improvement.**

### P0 — `by_human` is forgeable, and the test hides it **[verified]**

`server.py:4546` sets `by_human=is_orchestrator_app(app_id)`, and that function
is a lowercase string comparison and nothing more (`human_session.py:38-39`).
The env-var check `human_orchestrator_attested()` is consulted only by
`orchestrator_write_denial`, which fires only for tools in
`ORCHESTRATOR_WRITE_TOOLS` (`human_session.py:29-35`) — and
`human_attestation_create` is **not in that set**.

So any caller passing `app_id="willow"` writes a record that satisfies
`has_attestation(subject_id, require_human=True)`. The docstring four lines above
the call claims the opposite: *"an agent can never write a record claiming the
operator signed something."*

**`tests/test_human_loop.py:113-118` sets `WILLOW_HUMAN_ORCHESTRATOR=1` before
asserting `by_human is True` — and passes identically without it.** Green suite,
absent invariant. This is the most consequential single finding in the review:
a documented security boundary that does not exist, with a test that reads as
proof that it does.

**Fix shape.** Add `human_attestation_create` to `ORCHESTRATOR_WRITE_TOOLS`, or
derive `by_human` from `human_orchestrator_attested()` (stdio) / the confirmed
OAuth binding (serve). Delete the misleading monkeypatch either way.

### P0 — `Store.put` resurrects soft-deleted records **[verified]**

`db.py:134-138` is `INSERT OR REPLACE INTO records (id, data, created_at,
updated_at, deviation, action)` — the `deleted` column is omitted, and the schema
defaults it to `0` (`db.py:84`). SQLite's `INSERT OR REPLACE` deletes then
inserts, so an omitted column takes its default. Re-putting a known id
**undeletes the row and rewrites `created_at`**.

Compounding it: every internal subsystem persists into an ordinary SOIL
collection with no reserved-name protection — `human_attestations`
(`human_loop.py:39`), `human_required` (`:44`), `gaps` (`gaps.py:31`),
`friction_flags`, `forks`, `willow_commitments`, lineage nodes and edges. The
generic `store_put` / `store_delete` / `store_purge_collection` tools are in
`store_write` and `full_access`, so they reach all of them **without** the
corresponding `human_loop_write` / `lineage_write` / `gap_write` grant the gate
otherwise insists on. `store_scope` would confine this but is opt-in and absent
by default (`gate.py:376-380`).

Consequences: `store_delete` is not durable; a purged row can be replaced under
the same id with different content and a fresh-looking `created_at`.

### P0 — denial receipts are attributed to the raw caller-supplied `app_id`

`server.py:717-720` logs the denial with `app_id`, while every other receipt in
`_guarded` correctly uses `effective_app_id` (`:770-821`), for the reason stated
at `:708-713`. In serve mode `app_id` is an untrusted tool-call argument. A
signed-in caller can therefore mint receipt rows attributed to any app_id string
by making calls that get denied — and `receipts.tail()` / `since()` filter on
`WHERE app_id = ?`, so those forged rows surface in a **victim's** self-audit.
It also reintroduces the unbounded-arbitrary-string vector that L-DOS-01 closed
for `_buckets`, this time as rows in an append-only chained DB.

### P1 — `rechain()` and `_migrate_backfill()` launder tampering evidence

`governance_ledger.py:161-189` rewrites `prev_hash`/`hash` in place for any row
whose stored hash does not match the recomputed digest. That predicate is
indistinguishable from "was tampered with": run it on an edited chain and
`verify()` returns `{"valid": True}` afterwards, with `{"migrated": N}` reading
as successful maintenance.

`receipts.py:77-103` has the same shape and runs **on every `ReceiptLog()`
construction** — i.e. every server start. `receipts.py:34-41` is honest that the
chain's evidence only holds within the OS-ownership boundary; that is true for
*detection*, but an unconditional auto-repair converts "chain broken" into "chain
fine" without ever emitting the intermediate state, which is the one thing the
chain exists to produce.

### P1 — `frank_append` has no forced attribution

`server.py:2875-2893`: `project`, `event_type` and `content` are all
caller-supplied and the calling `app_id` is never injected. An app holding
`frank_write` can append a governance entry claiming any author or decision, and
`frank_read` returns it indistinguishably from an operator entry. This is the
exact hole `human_loop.create_attestation` was rewritten to close, in the same
repo. `envelope_apply` gets it right — `authorize_and_cite` is passed
`actor=app_id` server-side (`server.py:2921`).

### P1 — the authority PDP *replaces* the manifest gate rather than composing

`server.py:441-455`: setting `WILLOW_MCP_AUTHORITY_CHECK` swaps which of two
independent implementations of the same policy is authoritative. They currently
agree — `authority._check_mcp_tool` is if anything stricter — so this is not a
live widening. It is a drift risk: any rule added to `gate.permitted` will be
silently absent from the PDP path and vice versa. `and`-ing the two would give
the same rollout safety with none of the divergence.

### P1 — the seat-escalation hook's denylist has drifted behind `gate.py`

`bundle/hooks/pre_tool_use.py:407-410` matches eleven write-capable permission
names out of roughly twenty-five. Unmatched: **`integration_net`** and
**`web_net`** (the two server-process egress capabilities — `_TASK_NET_RE` at
`:374` catches only `task_net`), `markdownai_directives` (which `gate.py:241-249`
calls "the dangerous half"), `integration_call`, `web_read`, `orchestrator`
(which expands to seven writes), `dispatch_write`, `fork_write`,
`commitment_write`, `human_loop_write`, `code_graph_write`, `binding`,
`envelope_apply`. The module is explicit that it is "a guardrail, not a control",
which is the right framing — but nothing keeps the list in sync with
`gate.PERMISSION_GROUPS`. Derive the pattern at import, or add a test asserting
every group is classified read-or-write.

### P1 — `self_writable_trust_paths` under-reports the forgeable key

`lease.py:354-361` skips the check when `manifest.json` does not exist, reasoning
that an unmanifested app is denied outright. True — but if `$WILLOW_HOME/mcp_apps/`
is writable by this euid (it is, on every single-uid install), the agent can
`mkdir newapp/ && write manifest.json` with `["full_access", "web_net"]` and call
as `newapp`. The forgeable key is the **apps root**, not the manifest file. This
matters because the function is the honesty instrument — it is what
`diagnostic_summary` reports and what `WILLOW_MCP_STRICT_TRUST_ROOT` gates on.

### P1 — serve mode, the L-AUTH-02 fix, has zero tests

`grep -rn "_SERVE_MODE\|_resolve_serve_identity" tests/` returns nothing.
`_resolve_serve_identity` (`server.py:374-405`) is what turns a verified OAuth
`(issuer, subject)` into an `app_id`, and `_gate`'s serve branch (`:422-425`) is
the reason a signed-in caller cannot self-declare one. `tests/test_oauth.py`
covers the base `GroveOAuthProvider` only and says so honestly.

This is structural, not laziness: `_SERVE_MODE` is computed from `sys.argv` at
import (`server.py:301`), so it cannot be toggled per test. **Making `_SERVE_MODE`
injectable is the prerequisite** for testing the highest-value branch in the gate.

### P2

- `oauth._load_state` (`:77-83`) silently resets the whole token store on a
  corrupt file, and the next `_save_state()` makes the loss permanent. Note the
  asymmetry: the *write* path in the same file is carefully atomic and explains
  why. Also `_save_state` writes plaintext bearer tokens at default umask, and
  `_prune_expired` (`:106-110`) raises `KeyError` on a state file missing a
  top-level key.
- `web_fetch`'s SSRF guard blocks literal private **IP addresses** but never
  resolves hostnames (`:34-64`), and `fetch_url` sets `allow_redirects=True`
  without re-validating the target (`:89`). A clean public URL that 302s to
  `169.254.169.254` is followed — in the *server* process, which the repo's own
  reasoning (`gate.py:332-337`) identifies as the more privileged lane.
  `mai/parser.py:_http_host_blocked` has the identical limitation.
- `integrations.request()` (`:179-181`) uses `urllib` default redirect handling,
  which carries `Authorization` across a cross-host redirect. The module is
  otherwise careful with credentials.
- `governance_ledger.verify()` orders by `clock_timestamp()` (`:141-143`), which
  ties at microsecond resolution with no deterministic tiebreaker. The head-read
  tie is mitigated by an advisory lock and a unique index; `verify()` has no such
  protection and can report `{"valid": False}` on an intact chain. A false tamper
  alarm on a governance ledger is expensive. `ORDER BY created_at ASC, hash ASC`
  settles it.
- `human_loop.resolve` (`:198-210`) is a read-modify-write via `store.put`, so
  two concurrent resolves silently drop the first resolver's attribution.
  `Store.update` already returns `None` on `rowcount == 0` and could carry a CAS.
- `_read_call_credential` (`server.py:96-115`) reads the private SDK symbol
  `mcp.server.lowlevel.server.request_ctx` under a blanket `except`. With
  enforcement **on** this fails closed and loud, correctly. With enforcement
  **off** — the default, and the whole point of the observation phase — an
  operator watching an empty `bind_observed` stream concludes "no client is
  signing yet" rather than "my SDK moved a symbol."
- `mai/parser.py:156-157` renders an `@env` **authorization denial** as the
  fallback value, while the `@db` handler four lines below is explicit that "gate
  denials are LOUD". A rendered document cannot distinguish "unset" from
  "refused". Given the opposite, correct choice one function away, this reads as
  an oversight.

**Drift with willow-2.0 — willow-mcp is authoritative, do not re-import.**
`mai/parser.py` here is the hardened copy (a 298-line diff adding
`directives_permitted()`, secret-shaped env denial, a default-deny allowlist,
per-manifest `@db` connection allowlisting, SSRF host blocking); willow-2.0's
`sap/mai/parser.py` has none of it and pulling it forward would silently undo
issue #161. `human_loop.py` closes the `attested_by` forgery hole that
willow-2.0's `core/human_attestation.py:31` still has. `vault.py` adds a real
safety check (`:88-95`) willow-2.0 lacks. `code_graph` — **cannot tell** which is
authoritative; not examined closely enough.

**And a migration blocker to flag before, not during:** `human_required`'s
vocabularies diverged in *both* the kind and priority enums
(`needs_consent`/`critical` vs `consent`/`urgent`), and `list_queue` filters on
exact string equality (`human_loop.py:218-220`). Different backends today, so
nothing is broken now — but no mapping table exists anywhere in either repo. This
is the same drift [`FLEET_SEAMS.md` Break 1](FLEET_SEAMS.md#break-1--grove-reads-the-legacy-half-of-a-migrated-queue)
records for Grove's renderer, one layer down.

---

## safe-app-willow-grove

Carry the ideas; rewrite the trust layer. This is the repo the fresh build in
this repository is replacing, so the split matters more here than anywhere else.

**Good — the rebuild must not lose this.**

- **The honest-vitals pattern** (`grove/apps/vitals.py:50-64, 167-171`;
  `grove/apps/hero_format.py:38-62`). See [The one pattern](#the-one-pattern).
  Note the contrast that proves it is a habit rather than an accident:
  `panes/tasks.py:30-66` reads the **same `public.tasks` table** and renders
  `0 running  0 pending  0 done` plus "no tasks in queue" on failure. Same data,
  opposite honesty, same app. The `grove/apps/` modules carry an `ok` flag to the
  render layer; the `panes/` modules do not.
- **Three-state process presence** (`panes/mcp.py:267-275`), including the fourth
  branch most rewrites drop: *not running, but the port is busy — someone else
  owns this port.*
- **`grove_db.release_connection:83-88`** rolls back before returning a
  connection to the pool. One line that prevents handing an aborted transaction
  to the next caller.
- **Feature-detection fallbacks for schema drift** (`grove_reader.py:264-283,
  751-765`; `panes/knowledge.py:90-102`), each doing `conn.rollback()` before the
  fallback query — which is the part a rewrite usually gets wrong.
- **`chat.py`'s hard-won interaction detail** (1,317 lines): colon-key capture
  solved at four layers because Textual's `Input` swallows characters at several;
  message-block collapse tolerant of out-of-order timestamps; two-key destructive
  confirms armed for exactly 3.0s; a stale-render guard dropping payloads for a
  channel the user has left; focus preservation across sidebar rebuilds; pane
  liveness gating so background pollers stop when a pane is hidden;
  `LISTEN/NOTIFY` on a dedicated non-pooled connection with a docstring
  explaining exactly why pool connections must not be used.
- **Never parse Rich markup from dynamic text** (`panes/chat.py:751-759`, and
  `rich.markup.escape` used consistently across four panes).
- **`u2u/identity.py:24`** creates the private key with `os.open(..., O_CREAT,
  0o600)` — never a window at default umask — and `load()` raises on a corrupt
  key file rather than silently regenerating.
- **`u2u/sender.py:51-62`** raises rather than misbehaving when the sync wrapper
  is called inside a running loop, with a message saying what to do instead.

**Needs improvement.**

### P0 — consent is checked before the signature **[verified]**

`u2u/listener.py:62` calls `self._consent.check(sender_addr, ptype)` on
**unverified header data**. `Packet.validate()` is not reached until line 79, and
only on the `ALLOW` path. `consent.py:34-35` returns `PENDING` for a KNOCK from an
unknown address, and the `PENDING` branch at `listener.py:71-77` **dispatches an
entirely unverified, attacker-controlled packet** to registered handlers.

`bridge/app.py:174-178` then calls `contacts.add(from_addr, pubkey)` — "update key
silently" — and `ContactStore.add` (`u2u/contacts.py:48-55`) **constructs a brand
new `Contact`**, resetting every field to the dataclass defaults (`:17-21`):
`blocked=False`, `consent_note=True`, `consent_ask=True`, `consent_share=True`.

So anyone who can send one TCP packet to the bridge's u2u port can, for any
already-active contact: replace its trusted Ed25519 public key with their own,
**and** unblock a blocked contact and re-grant consent. No rate limit, no proof of
possession, no confirmation. The comment calls this "silently"; the silence is the
vulnerability.

**Fix shape.** Verify the signature before consulting consent, for every packet
type including KNOCK; a KNOCK's payload key must be verified against the signature
on that same KNOCK; key rotation must require human confirmation and must preserve
`blocked` and the consent flags — add an `update_key()` that does not reconstruct
the dataclass.

### P0 — consent is advisory, not enforced **[verified]**

`u2u/consent.py:40-41` returns `ALLOW` unconditionally for `KNOCK` and `REPLY`,
with **no correlation to any outstanding request** — no thread-id check, no
pending-ASK table, though `Packet.build` already carries a `thread_id` nothing
reads. A contact with every consent flag off delivers arbitrary payloads by
labelling them `REPLY`. Enforcement is a `_TYPE_TO_FIELD` lookup that four of six
packet types route around. Defaults are opt-**out**: merely adding a contact
grants NOTE, ASK and SHARE.

### P0 — the OAuth consent page is dead code **[verified]**

`grove/mcp_auth.py:6-9` documents a manual approval flow — *"USER opens that URL
in a browser, clicks Allow"*. `authorize()` at `:117-122` issues a code
immediately and redirects, and the ~55-line approval page at
`grove/mcp_local.py:699-741` is unreachable. With `register_client` accepting any
client unvalidated and `ClientRegistrationOptions(enabled=True)`, the endpoint is
an open dispenser for **30-day** full-scope tokens.

The mitigation is that `--serve` binds `127.0.0.1` — except
`_transport_security()` (`mcp_local.py:100-112`) explicitly **disables
DNS-rebinding protection** when the base URL is `https://`, "disabled behind
ngrok". So the intended production deployment is a public tunnel, and in that
deployment the only access control is knowledge of the tunnel URL.

`SECURITY_AUDIT.md` rates this **R8 ✅ PASS** ("token-gated") and **R5 ✅ N/A**
("localhost-only by design"). Both are contradicted by code in the same repo.

### P0 — the manifest claims u2u is encrypted; it is not

`safe-app-manifest.json` describes `dm_conversations` as *"Encrypted
human-to-human direct messages via u2u"* / *"End-to-end encrypted, local-only"*,
and `README.md` calls `u2u/` an *"Encrypted LAN transport."*

`Packet.serialize` (`u2u/packets.py:74-75`) emits `json.dumps(packet) + "\n"` onto
a bare `asyncio.open_connection` socket. There is no key agreement, no AEAD, no
TLS anywhere in `u2u/`; the `cryptography` dependency is used solely for Ed25519
**signing**. Messages are authenticated, not confidential. Anyone on the LAN path
reads DM bodies in cleartext. This is a user-facing privacy claim in a manifest
declaring `privacy_tier: local_only` — implement it or change it, but do not carry
the claim forward unexamined.

### P1

- **Consent toggles report success for writes that failed, and fail open on
  corruption.** `panes/settings.py:166-169` flips the label *before* posting the
  message, and `write_consent` at `:95-96` is `except Exception: pass` — so a
  read-only filesystem shows "Internet **OFF**" while the file still says `true`.
  Separately `_DEFAULTS` (`:27`) grants all three permissions, and `read_consent`
  returns it on a missing file, non-dict JSON, **or any parse exception**. A
  truncated consent file grants everything. `tests/test_panes_settings.py:12-16`
  pins that as intended.
- **The hero band's unread count is permanently wrong.** Two SOIL collections
  hold read cursors and nothing bridges them: `willow-dashboard/cursors` has
  three writers and no reader; `willow-dashboard/channel_cursors` has one reader
  and no writer. So `_channel_cursors()` always returns `{}`, every channel gets
  `last_seen_id = 0`, and the most prominent widget in the app shows each
  channel's **lifetime** message count as unread, forever. Meanwhile the sidebar
  seeds every cursor to `max_id` on first poll, so it shows **0** unread at
  startup. Two contradictory wrong answers on one screen.
- **Sending a message can silently fail while the composer clears.**
  `panes/chat.py:1282` empties the input; `:1307-1308` is `except Exception:
  pass` with no log and no status flash — unlike the flag/delete/archive paths in
  the same file, which do log. Worse, `:1312-1314` still shows "waiting for
  hanuman…" for a message that was never persisted. It is also the one DB write
  on the UI thread.
- **Racing `_load_messages` workers rewind the read cursor.**
  `@work(thread=True)` with no `exclusive=True` and no `group=`, invoked from four
  paths that overlap. Last writer wins rather than newest data, and the lower id
  is persisted, so read messages reappear as unread. The channel-identity guard at
  `:1215-1216` is the right shape and simply does not cover same-channel
  concurrency.
- **Flagging a message clobbers other agents' flags.**
  `grove_reader.py:868-885` reads flags from *all* senders and deletes with no
  `sender` clause, while `grove_db.clear_flag:489-495` does scope correctly and is
  bypassed. A human pressing `r` on a message an **agent** flagged `needs-reply`
  clears a fleet-wide blocked signal and is told it turned *their* flag off.
- **Two tests actively certify the defect.**
  `tests/test_internal_panes.py:22-27, 34-35` call the real fetchers with no
  database, receive the swallowed all-zeros dict, and assert the shape is fine.
  They pass *because* the failure is silent, and would fail if the code started
  reporting errors.

**Coverage, honestly.** 177 tests across 33 files, all pure-function or
module-constant. No test file references `u2u/` or `bridge/`. No test for
`grove_reader.py`, `grove_db.py`, `grove/mcp_auth.py`, or `grove_client.py`. The
entire cryptographic trust surface and the entire DB read layer are untested. The
two exceptions are `tests/test_vitals.py:114-118, 133-138` — the only assertions
in the suite that touch a data fetch's failure path.

---

## willow-2.0

A settled migration *source* — see
[`FLEET_SEAMS.md` Break 0](FLEET_SEAMS.md#break-0--the-migration-has-a-direction-one-readme-has-not-caught-up).
Read this section as "what to carry out" and "what will bite during the move",
not as a backlog for this repo.

**Good — carry forward.** The FRANK `clock_timestamp()` fix; pool and destructor
deadlock handling; the migration fingerprint guard; `core/egress_authority.py`;
and `constitution/compliance.py:55-62`, which encodes "no attempt ≠ a pass" as a
type-level cure for the fleet's disease.

**Needs improvement.**

- **The MCP policy layer fails silently open. [verified]**
  `sap/middleware.py:211-212` returns `[]` on any exception while loading rules,
  and `_count_receipts` returns `0` when receipts are unavailable — so every
  `limit` rule never fires and nothing says so.
- **`migrations/*.sql` are applied by nothing.** No runner references them.
- **`tasks` / `binder_edges` / `binder_files` conflict on id type with Grove**
  (TEXT vs BIGINT), both using `CREATE TABLE IF NOT EXISTS` — the same boot-order
  race as [Break 2](FLEET_SEAMS.md#break-2--two-repos-race-to-create-willowrouting_decisions),
  on three more tables.
- **`routing_decisions` exists in two schemas**, and
  `core/grove_reader.py:635-647` diagnoses *any* read failure as "table absent" —
  a permission error and a missing table produce the same message.
- **Lane read-scope is bypassable in one search path.** `core/canonical_lanes.py:234-238`
  returns early on an explicit `project=`, skipping `lane_scope` entirely.
  **[verified, and narrower than first reported]** — this is documented intent
  ("Explicit project= wins over lane_scope"), and the four `core/pg_bridge.py`
  call sites never pass `project`. Only `willow/ranking/hybrid.py:199, 262` do.
  So it is a real hole in the ranked-search path, not a general bypass — but a
  documented precedence that silently outranks a security scope is worth an
  explicit decision rather than a docstring.
- **The `grove/` subtree here is a stale fork.** Grove's own `grove_reader.py` is
  1,211 lines against 662 in this copy. Do not treat it as a second opinion.

---

## What the `2026-07-28` specification changes

`willow-mcp/docs/design/mcp-2026-07-28-diff.md` is the detailed diff and its
headline — *the SDK absorbs the protocol changes; this is an upgrade, not a
rewrite* — is right about the protocol. It is wrong about this codebase, for one
reason it does not consider.

### The break: willow-mcp has its own session layer, and it is not the protocol's

SEP-2567 removes `Mcp-Session-Id` and protocol-level sessions. Four pieces of
load-bearing state live in **process memory** and have relied on the sticky
routing that session IDs implied: `SessionBinder._sessions`
(`session_binder.py:125`), the rate-limiter `_buckets` (`server.py:648`), and
OAuth's `_pending` and `_codes` (`oauth.py:67-74`).

Meanwhile the check-in nonce file is on **shared disk**
(`session_binder.py:144-147`). That split is the worst available one. With
`WILLOW_MCP_ENFORCE_BINDING=1` on two replicas:

1. `session_bind` lands on replica A; the nonce is burned in the shared file and
   the session is created in A's memory only.
2. The next call lands on B. `verify_call` returns `{"bound": False}` and the gate
   denies.
3. The agent retries `session_bind`; B reads the shared nonce file, finds the
   nonce spent, and refuses as a replay.

The agent is hard-locked out: its session exists nowhere it can reach and its
nonce is globally spent. Same shape for OAuth — `_pending` is set in `authorize()`
on one process and popped in the IdP callback on another. **Fix before the SDK
upgrade, not after**: the failure appears only under load and looks like a client
bug.

### The quiet break: SEP-837 breaks `get_client` on existing installs

`register_client` stores whatever the client sent, unvalidated (`oauth.py:140-142`),
and `get_client` reconstructs it via `OAuthClientInformationFull(**data)`
(`:136-138`). If `application_type` becomes required, every pre-upgrade
registration raises a pydantic `ValidationError` inside an async provider method
the SDK calls during token exchange — an unhandled 500 on an existing install's
first request, not a "please re-register". One `try/except ValidationError:
return None` turns a hard break into clean re-registration.

### The shadowed key: the `iss` you store is not the `iss` the spec means

`exchange_authorization_code` stores `"issuer": identity.get("issuer")`
(`oauth.py:173`), where the value is the literal string `"google"` or `"apple"`
(`:577, 634`). `_resolve_serve_identity` reads it back as the **upstream IdP name**
to key the identity binding. RFC 9207 / SEP-2468's `iss` is *this authorization
server's* issuer URL, and SEP-2352 binds credentials to that same value. Two
different things in one key: implement 9207 by writing the real issuer into
`claims["iss"]` and `resolve_app_id()` finds no binding file for anyone. Fail-closed,
so not a security break — a total outage from one dict key. **Rename the internal
field to `idp` before touching RFC 9207.**

Related: `_BASE_URL` defaults to `http://127.0.0.1:8765` and is passed straight
into `AuthSettings(issuer_url=...)`; an `http://` issuer is already non-conformant
and an OAuth-hardening revision is a plausible place for the SDK to start
rejecting it. And `_ACCESS_TTL = 30 * 86400` is the kind of number such a revision
exists to shorten.

### What genuinely improves

- **`_read_call_credential` stops being a hack.** It currently reaches into the
  private `mcp.server.lowlevel.server.request_ctx` and digs a pydantic internal
  under a blanket `except`. SEP-2575 removes the `initialize` handshake and makes
  `_meta` on **every request** the official carrier for client info and
  capabilities. The out-of-band credential channel goes from a private convention
  riding a private API to a documented request field. Largest cleanup available.
- **SEP-2322 is the piece the diff doc misses — and it is the one the design has
  been missing since the port.** `human_loop.py:6-7` says the discipline is
  *"automation pauses for a human"*. Nothing pauses: `human_required_enqueue`
  writes a row and returns, and the calling agent carries on. It is a bulletin
  board. `InputRequiredResult` + `inputRequests` / `requestState` **is** a native
  pause-and-resume: `human_required_enqueue` returns the input request,
  `human_required_resolve` satisfies it. That turns the HITL queue from a record
  of asks into an actual blocking gate — which is also the thing
  [`DESIGN_CONSTRAINTS.md` §3](DESIGN_CONSTRAINTS.md#3-decide-the-human-queue-question-out-loud)
  is asking Grove to render honestly.
- **`Mcp-Method` (SEP-2243) puts a control outside the process it governs.** The
  entire gate is in-process today, and `self_writable_trust_paths` exists
  precisely to admit that the server's own uid can forge the keys authorising it.
  A method-routing header lets a reverse proxy deny `tools/call` at the edge, on a
  host the server uid cannot reconfigure — **the first control in this design not
  co-resident with the thing it controls.** Worth a design note even if it is not
  built this cycle.
- **`experiment/github-transport` gets materially simpler.** A store-and-forward
  relay was swimming against a streaming assumption; the new multi-round-trip
  model *is* a retry loop.
- **SEP-2549 `tools/list` caching** removes the per-session listing cost of ~100
  registered tools, which is currently the practical argument against splitting
  permission groups further.
- **Tasks moving to an extension costs nothing** (0 hits) and offers native
  resume/cancel to replace the hand-rolled `task_submit` polling.

### What costs nothing

Verified by grep at the commits above and recorded in the diff doc: Tasks,
`-32002`, sampling, MCP logging and roots are all **0 hits**. JSON Schema 2020-12
is a constraint *removal*. Deprecated features remain functional for 12 months
under SEP-2596.

Grove's `mcp>=1.0.0` with no upper bound was the one latent break available
independent of the spec; it is fixed on `deps/bound-the-pins` (PR #27).

---

## What to do first

1. **willow-mcp `by_human`** — a documented security invariant that does not
   exist, with a test that hides it. One-line fix plus deleting the monkeypatch.
2. **willow-mcp session state (§the break above)** — before the SDK upgrade. The
   failure mode is a lockout that only appears under load.
3. **Grove's `u2u` check order** — verify before consenting, for every packet
   type. This is a restructure, not a patch: the ordering *is* the design flaw,
   which is why the [design constraints](DESIGN_CONSTRAINTS.md) list it as a rule
   rather than a bug.
4. **Grove's `SECURITY_AUDIT.md`** — it rates the auto-approving OAuth endpoint as
   PASS, claims "Full" coverage of two files that are not in the repo
   (`grove_serve.py`, `kart_worker.py`, with line-specific findings in both), and
   never mentions `u2u/` or `bridge/` — the only modules making cryptographic
   trust decisions. **An audit that reports absence as coverage is this
   document's own pattern applied to the fleet's immune system**, and it is the
   reason three P0s survived a rubric pass.

---

## Provenance

**Directly verified** for this document — read or executed against the working
trees at the commits in the header:

- `willow-mcp/src/willow_mcp/human_session.py:29-39` and `server.py:4535-4550` —
  `human_attestation_create` is not in `ORCHESTRATOR_WRITE_TOOLS`;
  `is_orchestrator_app` is a string compare.
- `willow-mcp/src/willow_mcp/db.py:80-90, 128-140` — `INSERT OR REPLACE` omits
  `deleted`, whose schema default is `0`.
- `safe-app-willow-grove/u2u/listener.py:55-85` — consent check at `:62`,
  `Packet.validate` at `:79`, `PENDING` dispatch at `:71-77`.
- `safe-app-willow-grove/u2u/consent.py:28-50` — unconditional `ALLOW` for
  `KNOCK` and `REPLY`.
- `safe-app-willow-grove/u2u/contacts.py:14-25, 44-58` — `add()` reconstructs the
  dataclass; defaults are `blocked=False`, `consent_note/ask/share=True`
  (`consent_alert` defaults `False`).
- `safe-app-willow-grove/grove/mcp_auth.py:100-125` and
  `grove/mcp_local.py:98-115` — `authorize()` auto-approves; DNS-rebinding
  protection is disabled for `https://` base URLs.
- `willow-2.0/sap/middleware.py:200-215` — `return []` on any policy-load error.
- `willow-2.0/core/canonical_lanes.py:225-245` and every `apply_lane_scope_sql`
  call site — the early return is real; only `willow/ranking/hybrid.py` passes
  `project=`.
- All Nestor claims — first-hand, including the engine-abort reproduction.

**From read-only survey agents, cited but not independently re-checked** —
everything else, including all `file:line` references not listed above. One agent
per repo, each instructed to cite `file:line` and to say plainly when something
could not be found. The same method produced a backwards conclusion once before
(see [`FLEET_SEAMS.md` provenance](FLEET_SEAMS.md#provenance-and-confidence)):
**asking an agent "where is this code" cannot distinguish a port from an
original.** The willow-2.0 lane-scope item above is a live example of the
correction that spot-checking produces — the survey framed it as a general
security bypass; reading the call sites narrowed it to one search path and
revealed it was documented intent.

Spot-check before acting on any single item, and prefer the four in
[What to do first](#what-to-do-first) — all four are verified.
