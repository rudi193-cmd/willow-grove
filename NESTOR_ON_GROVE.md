# Nestor on Grove

*Nestor's verified-match engine (`/home/user/Nestor`) pointed at the duplicated Grove
code in the Willow fleet, used as an analysis tool. Run 2026-07-27.*

Two things are reported here and they are kept strictly apart:

1. **What popped in Grove** — true duplicates (consolidation targets) and **false seals**
   (pairs that score high and are *not* the same thing).
2. **What this says about Nestor** — the first time it has been run on a real corpus
   rather than a synthetic bench.

Every claim below carries `file:line`. Where a thing could not be determined it says so.

### Findings at a glance

**Grove**

* **69 cross-repo byte-identical function groups** — `grove_db.py`, `grove_reader.py`,
  `mcp_auth.py`, `mcp_local.py`, `theme.py` and `grove_client.py` are wholesale forks between
  `safe-app-willow-grove` and `willow-2.0` (§1.1).
* **38 duplicate groups the CONSOLIDATION_MATRIX missed**, including one real duplicate hiding
  under two different names (`_ollama_models` / `list_models`) that name-clustering cannot
  see by construction (§1.3).
* **Four matrix entries are not duplicates at all** — `routing_decisions`, `grove_messages`,
  `init_schema`, `create_channel` (§1.5, §2.4).
* **Of 12 identically-named MCP tools shared between `willow-2.0` and `willow-mcp`, 11 are
  false seals.** Exactly one (`code_graph_index`) is a consolidation target (§2.5).
* **Seven table names carry incompatible schemas** across repos — `routing_decisions` (3
  shapes), `tasks` (4), `records` (6), `knowledge`, `dispatch_tasks`, `agents`, `binder_edges` (§2.1).
* **`NOTIFY grove_messages` has zero listeners** anywhere in the fleet — two live dead-writes (§2.3).
* **`human_required` vs `human_required_queue`**: not one queue-kind value, not the top
  priority value, not the id format, not the sort order and not the enqueue return
  discriminator is shared — behind matching parameter names (§2.2).

**Nestor**

* **Bug:** `StringMatcher` is broken on keys >= 200 chars — difflib's `autojunk` default makes
  the median score collapse from 0.954 to 0.547 on 1000-char keys (§3.1).
* **Worse bug:** `similarity` is **not symmetric**, so *which pair member was sealed first*
  decides whether a match is served. Reproduced: 0.921 one way, 0.318 the other (§3.2).
* **The memory cannot hold the fleet's actual drift signature** — a conflicting seal on the
  same surface silently overwrites, with no error analogous to `RejectedPairError` (§3.4).
* **0.92 is right for function bodies, inverted for identifiers** — 0/10 true synonyms found,
  2 false seals produced (§3.3).
* A code-aware matcher raised recall **52%** (23 -> 35 pairs) with no precision loss (§3.5).

---

## 0. Method, so the numbers are readable

Units were extracted with Python's `ast` (no regex over Python source), then sealed into
Nestor's memory as `source_text -> "repo:path:line:name"` pairs and probed back with
`memory.lookup` / `memory.best_sealed`. Three disjoint domain-tagged corpora:

| corpus | domain tag | extracted | sealed (distinct normalized keys) |
|---|---|---|---|
| function bodies (`def`, non-test, >= 4 lines) | `fn` | 1 943 | 1 870 |
| SQL statements (from `.sql` + Python string constants) | `sql` | 336 | 274 |
| identifiers (MCP tool names, table names, NOTIFY channels, permission strings, queue vocabularies) | `ident-*` | 2 344 (267 distinct tool names) | per class |

Repos scanned: `/workspace/safe-app-willow-grove` (all Python), `/workspace/willow-2.0`
(Grove-related paths + `sap/sap_mcp.py`, `core/pg_bridge.py`, `core/human_required.py`,
`sap/core/gate.py`), `/workspace/willow-mcp` (`src/willow_mcp/`). A separate sweep collected
**149 `CREATE TABLE` statements under 86 distinct bare table names** across all three.

Four matchers were run through Nestor's `Matcher` seam so the scores are comparable:

* **`stock`** — `nestor.matcher.StringMatcher` exactly as shipped.
* **`nojunk`** — same normalization, `difflib.SequenceMatcher(..., autojunk=False)`.
* **`tokenset`** — code-aware: lex to identifier/number/punctuation tokens, case preserved,
  difflib over the *token* sequence.
* **`sqlshape`** — SQL-aware: Jaccard over the `(column, type)` set of a `CREATE TABLE`,
  ignoring the table name.

Scores below are labelled with which matcher produced them. `tokenset` is the default
citation because `stock` is broken on long keys — see §3.1.

---

## 1. TRUE duplicates — consolidation targets

### 1.1 Sixty-nine byte-identical function groups across repos

After normalization, **69 function groups are token-identical across more than one repo**
(one further group is intra-repo). Nestor surfaced these not through `lookup` but as
*seal collisions*: `memory.add_pair` keys on the normalized source, so a second identical
body collapses onto the first (that behaviour is itself a finding — §3.4).

The bulk is a wholesale file-level fork:

| file pair | identical functions |
|---|---|
| `safe-app-willow-grove/grove_db.py` <-> `willow-2.0/core/grove_db.py` | 22 (`_get_pool` :43/:42, `get_connection` :69/:68, `listen_connection` :91/:90, `list_channels` :295/:235, `get_history` :403/:287, `search_messages` :454/:338, `bus_send` :533/:417, `cursor_load` :615/:479, `mark_indexed` :654/:518, …) |
| `safe-app-willow-grove/grove_reader.py` <-> `willow-2.0/core/grove_reader.py` | 15 (`_conn_ctx` :23/:23, `desk_mention_handles` :48/:48, `grove_messages_bus_addressed_to` :100/:100, `grove_agent_fleet_rows` :348/:311, `grove_mentions_for_handles` :1010/:550, …) |
| `safe-app-willow-grove/grove/mcp_auth.py` <-> `willow-2.0/grove/mcp_auth.py` | 10 (`issue_code` :78/:75, `exchange_authorization_code` :139/:128, `exchange_refresh_token` :190/:179, `revoke_token` :237/:226, …) |
| `safe-app-willow-grove/grove/mcp_local.py` <-> `willow-2.0/grove/mcp_local.py` | 13 (`grove_watch_all` :383/:378, `grove_get_thread` :438/:433, `grove_heartbeat` :622/:598, `_watch_serve_supervisor` :748/:724, …) |
| `safe-app-willow-grove/grove/theme.py` <-> `willow-2.0/grove/theme.py` | 4 (`truncate` :62/:62, `init_pairs` :70/:70, `safe_addstr` :106/:106, `draw_rounded_box` :121/:121) |
| `safe-app-willow-grove/grove_client.py` <-> `willow-2.0/core/grove_client.py` | 2 (`load_token` :30/:32, `main` :122/:129) |

Three reach into `willow-mcp` as well:
`_load_state` (`safe-app-willow-grove/grove/mcp_auth.py:61` | `willow-2.0/grove/mcp_auth.py:58` | `willow-mcp/src/willow_mcp/oauth.py:77`),
`load_authorization_code` (`…mcp_auth.py:124` | `…mcp_auth.py:113` | `…oauth.py:149`),
`revoke_token` (`…mcp_auth.py:237` | `…mcp_auth.py:226` | `…oauth.py:244`).

*How decided:* identity after normalization is not a judgement call. Spot-verified by
reading `grove_db.py:43-57` vs `core/grove_db.py:42-56` and `grove/theme.py:106-118` vs
`grove/theme.py:106-118`.

### 1.2 Verified near-duplicates (read and confirmed, not inferred)

| pair | tokenset | verdict |
|---|---|---|
| `_ollama_models` `safe-app-willow-grove/panes/providers.py:25-31` <-> `list_models` `willow-2.0/grove/apps/models.py:16-22` | **0.976** | **TRUE duplicate.** Byte-identical but for the name and `timeout=2` vs `timeout=3`. Same URL `http://localhost:11434/api/tags`, same parse, same `except Exception: return []`. |
| `_unique_dest` `willow-2.0/tools/grove_p2p.py:62-71` <-> `willow-mcp/src/willow_mcp/nest/intake.py:88-97` | **0.963** | **TRUE duplicate.** Only difference is the parameter name `out_dir` vs `dest_dir`; all three call sites (`grove_p2p.py:224`, `intake.py:130`, `intake.py:254`) pass positionally, so the rename is not load-bearing. |
| `authorize` `willow-mcp/src/willow_mcp/oauth.py:144-147` <-> `willow-mcp/src/willow_mcp/oauth.py:500-503` | **0.937** | **TRUE duplicate, and dead code.** `WillowOAuthProvider` (`oauth.py:466`) subclasses `GroveOAuthProvider` (`oauth.py:58`) and re-declares `authorize` with an identical body and weaker annotations. Deleting `oauth.py:500-503` is behaviour-preserving. Highest-confidence safe deletion found. |

*How decided:* both bodies read in full; differences enumerated; call sites checked.

### 1.3 Thirty-eight duplicates the CONSOLIDATION_MATRIX missed

`willow-mcp/docs/repatriation/CONSOLIDATION_MATRIX.md` clusters by component name over a
MinHash index. Measuring content instead found **38 cross-repo duplicate groups whose names
do not appear anywhere in that matrix**, 33 of them byte-identical:

`_add`, `_bootstrap_schema`, `_conn_ctx`, `_load_state`, `_ollama_models`/`list_models`,
`_ui_state`, `_watcher`, `archive_channel`, `authorize`, `bus_receive`, `bus_send`,
`child_argv`, `clear_flag`, `cursor_save`, `delete_message`, `exchange_refresh_token`,
`get_client`, `get_flagged`, `get_history`, `get_thread`, `get_unindexed`, `grove_ack`,
`grove_bus_receive`, `grove_bus_send`, `grove_flagged`, `grove_heartbeat`,
`grove_own_channel_since`, `grove_send_message`, `grove_watch`, `load_access_token`,
`mark_indexed`, `release_connection`, `revoke_token`, `root_redirect`, `search_messages`,
`send_command`, `truncate`.

Two of these are the interesting kind:

* **`_ollama_models` / `list_models`** — a real duplicate under **two different names**.
  A name-clustering matrix cannot see it by construction. (The matrix does list
  `_query_ollama_models`, a *third*, differently-named copy at
  `willow-2.0/willow/grove_coordination.py:41`.)
* **`authorize`** — spans `willow-2.0/grove/mcp_auth.py:104` and *two* sites in
  `willow-mcp/src/willow_mcp/oauth.py`, i.e. it crosses the repo boundary the matrix's
  Grove rows stop at.

### 1.4 Where measurement AGREES with the matrix

The matrix's `STANDALONE-LIB` block is largely confirmed: `get_connection`, `list_channels`,
`get_channel`, `set_flag`, `get_flags`, `cursor_load`, `load_token`, `listen_connection`,
`_get_pool`, `_pg_ok`, `_kart_ok`, `_msgs_to_dicts`, `ensure_card_builder_channel`,
`desk_mention_handles`, `dashboard_grove_sender`, `merge_attention_messages`,
`grove_inbox_bundle`, `grove_agents`, `grove_latest_message_for_sender`,
`grove_agent_fleet_rows`, `coordinator_heartbeat`, `grove_messages_all_agents`,
`_ensure_mention_index`, `grove_mentions_for_handles`, `grove_list_channels`,
`grove_get_history`, `grove_search`, `grove_get_identity`, `grove_channel_resource`,
`_on_subscribe`, `grove_watch_all`, `grove_get_thread`, `grove_flag`, `grove_unflag`,
`grove_inbox`, `grove_approve`, `_watch_serve_supervisor`, `grove_reply`,
`grove_messages_bus_addressed_to`, `_unique_dest`, `load_refresh_token`,
`exchange_authorization_code` — all measured as exact or >= 0.92 cross-repo.

### 1.5 Where measurement DISAGREES with the matrix

Four matrix entries are **not** duplicates by content. These are covered in §2 as false
seals: `routing_decisions` (0.49), `grove_messages` (0.92), `init_schema` (0.90),
`create_channel` (0.93). The matrix calls each one component; each is materially divergent.

`xterm256` (matrix: `safe-app-willow-grove` + `safe-design`) and `pg_notify_thread`
(matrix: two repos) **could not be checked** — `safe-design` was not in scope, and
`pg_notify_thread` exists only once in the scanned set
(`willow-2.0/sap/grove_tools.py:66`).

---

## 2. FALSE SEALS — pairs that look interchangeable and are not

This is the high-value output. Ordered roughly by blast radius.

### 2.1 Same table name, incompatible shape — the fleet's dominant drift

Grouping all 149 `CREATE TABLE` statements by bare name and scoring the distinct shapes:

#### `routing_decisions` — four sites, three incompatible shapes

| site | shape |
|---|---|
| `safe-app-willow-grove/schema.sql:103` (`willow.routing_decisions`) | `id BIGINT GENERATED ALWAYS AS IDENTITY`, `ts`, `session_id`, `prompt_snippet`, `routed_to`, `rule_matched`, `confidence FLOAT`, `latency_ms INTEGER` |
| `safe-app-willow-grove/grove_reader.py:1064` (`willow.routing_decisions`) | identical to the above (whitespace only) |
| `willow-2.0/core/grove_reader.py:604` (`willow.routing_decisions`) | identical to the above |
| `willow-2.0/core/pg_bridge.py:319` (`routing_decisions`, **unqualified — `public`**) | `id TEXT PRIMARY KEY`, `created_at`, `prompt_hash TEXT NOT NULL`, `session_id`, `rule_id`, `confidence FLOAT`, `decision JSONB NOT NULL` |
| `willow-mcp/docs/schema/routing_decisions.postgres.sql:18` (`routing_decisions`) | `id text PRIMARY KEY`, `prompt_hash`, `session_id`, `rule_id`, `confidence real`, `decision jsonb`, **`kind text`**, `created_at` |

Pairwise (`stock` / `nojunk` / `tokenset` / `sqlshape`):

```
grove:schema.sql:103          <-> w20:core/pg_bridge.py:319                0.130 0.650 0.659 0.154
grove:schema.sql:103          <-> mcp:docs/schema/routing_decisions:18     0.122 0.430 0.383 0.067
w20:core/pg_bridge.py:319     <-> mcp:docs/schema/routing_decisions:18     0.512 0.512 0.427 0.667
```

**VERDICT: FALSE SEAL.** Only `session_id` and `confidence` are common to all three; there
is no column overlap at all between `prompt_snippet/routed_to/rule_matched/latency_ms` and
`prompt_hash/rule_id/decision/kind`. The `willow.`-qualified and unqualified names denote
**different tables in different schemas**. *How decided:* read all five DDLs; column sets are
disjoint apart from two columns.

#### Same pattern, five more tables

| table | distinct shapes | worst-pair `sqlshape` | sites |
|---|---|---|---|
| `knowledge` | 3 | **0.095** | `willow-2.0/core/sqlite_bridge.py:42`, `willow-2.0/core/pg_bridge.py:69`, `willow-mcp/docs/schema/knowledge.postgres.sql:20` |
| `tasks` | 4 | **0.176** | `safe-app-willow-grove/schema.sql:123` (`public.tasks`), `willow-2.0/core/sqlite_bridge.py:97`, `willow-2.0/core/pg_bridge.py:118`, `willow-mcp/docs/schema/tasks.postgres.sql:14` |
| `dispatch_tasks` | 2 | **0.174** | `willow-2.0/core/pg_bridge.py:220`, `willow-mcp/src/willow_mcp/dispatch.py:63` |
| `records` (the SOIL store) | **6** | 0.250 | `safe-app-willow-grove/soil.py:25`, `willow-2.0/seed.py:1471`, `willow-2.0/scripts/init_db.py:22`, `willow-2.0/scripts/soil_merge_layouts.py:37`, `willow-2.0/core/metabolic.py:195`, `willow-mcp/src/willow_mcp/soil_heartbeat.py:100` |
| `agents` | 3 | 0.455 | `willow-2.0/core/sqlite_bridge.py:87`, `willow-2.0/core/pg_bridge.py:108`, `willow-mcp/docs/schema/agents.postgres.sql:23` |
| `binder_edges` | 3 | 0.417 | `safe-app-willow-grove/schema.sql:141` (`public.binder_edges`), `willow-2.0/core/sqlite_bridge.py:176`, `willow-2.0/core/pg_bridge.py:199` |
| `frank_ledger` | 3 | 0.556 (sqlite) / 1.000 (pg) | `safe-app-willow-grove/grove_db.py:222` (`public.frank_ledger`), `willow-2.0/core/sqlite_bridge.py:77`, `willow-2.0/core/pg_bridge.py:98` |

**VERDICT for `knowledge`, `tasks`, `dispatch_tasks`, `records`, `agents`, `binder_edges`:
FALSE SEALS.** Same name, `sqlshape` agreement 0.10–0.46 — i.e. most columns are not shared.
`frank_ledger` is the one benign case: the `safe-app-willow-grove` and `willow-2.0` Postgres
shapes agree exactly (`sqlshape=1.000`) and only the SQLite mirror diverges, which is
expected. *How decided:* the `sqlshape` matcher compares `(column, type)` sets directly, so a
low score is a literal statement about which columns exist.

### 2.2 The human-required queue: two vocabularies behind one name

`willow-2.0` and `willow-mcp` both expose `human_required_*` MCP tools. They do not share a
store, a table name, or a vocabulary.

**Store.** `willow-2.0` uses Postgres table `human_required_queue`
(`willow-2.0/core/pg_bridge.py:380-394`). `willow-mcp` uses SOIL/sqlite collection
`"human_required"` — **no `_queue` suffix** (`willow-mcp/src/willow_mcp/human_loop.py:44`).
The split is deliberate and documented (`human_loop.py:14-22`, B-28: refuses to migrate the
shared fleet DB).

**Kinds — zero overlap. Every value is mutually rejected.**

| `willow-2.0/core/human_required.py:13-19` | `willow-mcp/src/willow_mcp/human_loop.py:45` |
|---|---|
| `needs_consent` (:14) | `consent` |
| `needs_attestation` (:15) | `attestation` |
| `needs_review` (:16) | `review` |
| `operator_overload` (:17) | `overload` |
| `external_onboarding` (:18) | `onboarding` |

Both sides hard-validate: `human_required.py:113-117` raises `ValueError`,
`human_loop.py:170-172` raises `HumanLoopError`. `willow-2.0`'s gate logic even *constructs*
kinds by prefix — `kind = f"needs_{requirement}"` (`human_required.py:425`) — which can never
produce a value `willow-mcp` accepts.

**Priorities — the top of the scale differs.**
`willow-2.0` `("low","normal","high","critical")` (`human_required.py:21`) vs `willow-mcp`
`("low","normal","high","urgent")` (`human_loop.py:49`). `critical` is not cosmetic: it is
encoded in SQL sort order (`CASE priority WHEN 'critical' THEN 0 …`,
`human_required.py:240-245`) and in operator-load scoring where it weights x3 and alone forces
`level="high"` (`human_required.py:356`, `:371-373`). `willow-mcp` has no `critical`, no
priority ordering, and no `operator_load_state` at all — it sorts newest-first on `created_at`
(`human_loop.py:221`).

**Statuses — same four names, different structure and different meaning.**
`willow-2.0` treats `open` + `acknowledged` jointly as "still open", encoded in SQL in three
places (dedupe `human_required.py:163`, resolve guard `:298`, `open_total` `:324-325`).
`willow-mcp` has no such notion and does no status validation on list at all
(`human_loop.py:218`) — a typo returns `[]` instead of erroring.

**Record shape.** `context` JSONB (`pg_bridge.py:390`, returned `human_required.py:265`) and
`updated_at` (`pg_bridge.py:392`) exist only in `willow-2.0`. The resolution note lives
*inside* `context` as `resolution_note` there (`human_required.py:294-297`) and as a
**top-level `note` field** in `willow-mcp` (`human_loop.py:192`). Empty values are `NULL`
in one (`human_required.py:190-192`) and `""` in the other (`human_loop.py:187-192`).
IDs are 8-char **UPPERCASE** hex (`pg_bridge.py:1230-1233`) vs 8-char **lowercase**
(`human_loop.py:178`) — not comparable without normalization.

**Contract divergences that would break a swap:**

* `willow-2.0` `enqueue` **de-duplicates** on `(kind, source_ref)` and can return
  `{"status": "duplicate", …}` (`human_required.py:158-175`). `willow-mcp` never dedupes
  (`human_loop.py:178-195`).
* `enqueue` return discriminator collides: `willow-2.0` returns `status` = `"added"`/`"duplicate"`
  and puts the item's own state in **`queue_status`** (`human_required.py:199-207`);
  `willow-mcp` returns the raw record whose `status` is `"open"` (`human_loop.py:179-195`).
  A consumer reading `result["status"]` gets a different *kind of value* from each.
* Sort order is **opposite**: oldest-first, priority-weighted (`human_required.py:239-246`)
  vs newest-first (`human_loop.py:221`).
* `willow-2.0` refuses to resolve an already-closed item (`human_required.py:298`);
  `willow-mcp` will happily re-resolve one (`human_loop.py:204-209`).
* `willow-2.0` fires an operator notification on enqueue
  (`core.operator_notify.dispatch`, `human_required.py:208-212`); `willow-mcp` has no hook.
* The whole write-gate apparatus — `GATE_MODES` (`human_required.py:22`), `check_write_gate`
  (`:431-493`), `ELEVATED_TIERS` (`:23`), `consent_stamp`/`attestation_stamp` (`:496-501`) —
  exists only in `willow-2.0`.

**VERDICT: FALSE SEAL, comprehensively — and the worst case in the corpus precisely because
the surface matches so well.** Tool parameter names match exactly
(`kind, title, summary, priority, source_ref, assignee`: `sap_mcp.py:6432-6438` vs
`server.py:4486-4488`) and both return a `{items, count, stats}` envelope
(`sap_mcp.py:6426` / `server.py:4524`) — while not one `kind` value, not the top `priority`
value, not the id format, not the sort order, not the enqueue discriminator and not the note
location is shared.

**Bug found inside `willow-2.0` while checking this.** The tool docstring at
`willow-2.0/sap/sap_mcp.py:6415` advertises the *willow-mcp* vocabulary — "consent,
attestation, review, overload, onboarding" — while the validator it calls
(`willow-2.0/core/human_required.py:113-117`) accepts only the `needs_*`/`operator_*`/
`external_*` forms. A caller obeying that docstring gets a `ValueError`. The docstring was
apparently synced to `willow-mcp` and the validator was not.

**Sibling case — `human_attestation_create` is a security-relevant false seal.**
`willow-2.0/sap/sap_mcp.py:6507` takes `attested_by: str = "operator"` as **free text**
(`:6513`), so an agent can write a record claiming the operator signed off.
`willow-mcp/src/willow_mcp/server.py:4529` removed that parameter deliberately (rationale at
`server.py:4536-4540` and `human_loop.py:23-30`): the attester is always the calling identity,
plus a non-forgeable `by_human` derived from `is_orchestrator_app(app_id)` (`server.py:4548`).
`willow-2.0` has no `by_human` concept anywhere. Consolidating onto the `willow-2.0` contract
would reintroduce attestation forgery.

### 2.3 NOTIFY `grove_messages` has no listener anywhere

* Producers on `grove_channel`: `safe-app-willow-grove/schema.sql:82`
  (`PERFORM pg_notify('grove_channel', NEW.channel_id::text)`),
  `safe-app-willow-grove/grove_db.py:195`, `willow-2.0/core/grove_db.py:193`,
  `willow-2.0/scripts/grove_msg.py:74`.
* Listeners on `grove_channel`: `safe-app-willow-grove/grove/mcp_local.py:63`,
  `safe-app-willow-grove/panes/chat.py:1130`, `willow-2.0/grove/mcp_local.py:57`,
  `willow-2.0/sap/grove_tools.py:86`, `willow-2.0/scripts/grove_bridge.py:144` and `:145`,
  `willow-2.0/scripts/grove_msg.py:90`, `willow-2.0/willow/grove_listen.py:223` and `:280`,
  `willow-2.0/willow/coordinator.py:95`, `willow-2.0/scripts/health_report.py:87` and `:162`
  — 23 occurrences in total.
* Producers on `grove_messages`: `willow-2.0/agents/hanuman/lib/skill_steward.py:294` and
  `willow-2.0/agents/hanuman/bin/upstream_watcher.py:318`, both `cur.execute("NOTIFY grove_messages")`.
* Listeners on `grove_messages`: **zero, in all three repos.**

**VERDICT: FALSE SEAL, and a live dead-write.** Postgres accepts `NOTIFY` on a channel with
no subscribers silently, so both call sites fail open. Note a second layer: every
`grove_channel` listener filters on a `channel_id::text` payload, while both
`grove_messages` sites send a **payload-less** NOTIFY — fixing only the channel name would
still not wake the existing consumers. *How decided:* exhaustive grep of `LISTEN`/`NOTIFY`
across all three repos, all file types.

Nestor's own score on the pair: `grove_channel` vs `grove_messages` = **0.593** (`stock`) —
comfortably below threshold. Nestor would *not* have found this one. It was found by
enumerating the identifier corpus by hand.

### 2.4 Same function name, materially different body (0.89–0.92 — the dangerous band)

Every one of these sits at or just under Nestor's 0.92 default. All were read in full.

| pair | tokenset | verdict |
|---|---|---|
| `grove_messages` `safe-app-willow-grove/grove_reader.py:809-848` <-> `willow-2.0/core/grove_reader.py:461-495` | **0.917** | **FALSE SEAL.** safe-app adds `"flags": set()` (`:841`) and calls `_attach_message_flags` (`:845`), a **second query against `grove.message_flags`**. Return shape is 5 keys vs 4; `willow-2.0` has no `_attach_message_flags` at all. Any consumer of `m["flags"]` would `KeyError`. |
| `init_schema` `safe-app-willow-grove/grove_db.py:107-237` <-> `willow-2.0/core/grove_db.py:106-213` | **0.900** | **FALSE SEAL.** safe-app is a strict superset: it also creates table `public.frank_ledger` (`:213-233`), the partial unique index `frank_ledger_no_fork` (`:234-237`), and column `messages.deleted_by` (probe `:144`, ALTER `:153`). `willow-2.0` creates none of these. Consolidating onto the `willow-2.0` body regresses the FRANK anti-fork guard to a silent no-op. Direction matters: consolidating onto **safe-app** is safe. |
| `create_channel` `safe-app-willow-grove/grove_db.py:277-292` <-> `willow-2.0/core/grove_db.py:220-232` | **0.925** | **FALSE SEAL.** safe-app calls `normalize_channel_name(name)` (`:280`, helper at `:244-252`, strips whitespace and a leading `#`) and raises `ValueError` on empty-after-normalization (`:281-282`). `willow-2.0` writes the raw string, so `"#fleet"`, `" fleet "` and `"fleet"` become three distinct rows in `grove.channels`. Same SQL, same return shape, **different rows land in the database**. |
| `routing_decisions` `safe-app-willow-grove/grove_reader.py:1084-1097` <-> `willow-2.0/core/grove_reader.py:621-662` | **0.339** | **FALSE SEAL** (and here the low score is *correct*, while the matrix is wrong). safe-app is a 14-line merge front-end over `_routing_decisions_willow` (`:1100-1135`) **and** `_routing_decisions_public` (`:1138-1175`), with `limit*2` over-fetch, a merge sort, and synthesised fields (`prompt_snippet` <- `f"[hash:{prompt_hash[:12]}]"` at `:1160`). `willow-2.0` reads `willow.routing_decisions` only — its own docstring at `:622-627` says so. Consolidating onto the `willow-2.0` body silently drops every MCP-logged decision. |
| `authorize` `willow-2.0/grove/mcp_auth.py:104-111` <-> `willow-mcp/src/willow_mcp/oauth.py:144-147` | **0.974** | **FALSE SEAL.** Identical bodies except the returned redirect: `/grove-approve` vs `/mcp-approve`. `willow-mcp` registers `@mcp.custom_route("/mcp-approve", ...)` at `oauth.py:512` and its deny link at `:442` also points there; `willow-2.0`'s module docstring at `mcp_auth.py:7` documents `/grove-approve`. Neither server serves the other's path — merging breaks one consent flow. **This is the single highest-similarity false seal in the function corpus.** |

### 2.5 Identifier-level false seals

#### Fifty MCP tool names are declared in more than one repo — and 11 of the 12 checked are false seals

The identifier corpus found **50 MCP tool names declared in two or more repos** (similarity
1.0 by construction — the names are byte-identical). Twelve were read on both sides in full.
The result is the strongest finding in this report:

| tool | same params? | same store? | same return? | verdict |
|---|---|---|---|---|
| `code_graph_index` `willow-2.0/sap/sap_mcp.py:5876` \| `willow-mcp/src/willow_mcp/server.py:4200` | near (`repo_root` required, `+db_path`) | yes (sqlite, different default path) | **yes — identical 5 keys** | **TRUE DUPLICATE** |
| `human_attestation_create` `sap_mcp.py:6507` \| `server.py:4529` | no (`attested_by` removed, `by_human` added) | no (Postgres vs SOIL) | no | FALSE SEAL — forgery |
| `human_attestation_list` `sap_mcp.py:6483` \| `server.py:4553` | yes | no | envelope yes, item schema no | FALSE SEAL |
| `agent_route` `sap_mcp.py:1642` \| `server.py:2390` | no | same table, different columns | no | FALSE SEAL |
| `fork_create` `sap_mcp.py:2353` \| `server.py:4354` | **yes, exactly** | no (Postgres+SOIL vs SOIL) | no (2 keys vs 13) | FALSE SEAL — looks drop-in |
| `context_save` `sap_mcp.py:5035` \| `server.py:3021` | no (`str`/hours vs `dict`/seconds) | no | no | FALSE SEAL |
| `kb_ingest` `sap_mcp.py:1438` \| `server.py:2210` | no (15 params vs 7; no content param) | same table, different write path | no | FALSE SEAL |
| `nest_scan` `sap_mcp.py:4862` \| `server.py:1351` | no (1 param vs 7) | no | no | FALSE SEAL |
| `diagnostic_summary` `sap_mcp.py:5472` \| `server.py:3911` | no | no | **no shared keys** | FALSE SEAL — extreme |
| `fleet_status` `sap_mcp.py:617` \| `server.py:2804` | yes (`app_id` only) | no | **no shared keys** | FALSE SEAL |
| `handoff_write_v3` `sap_mcp.py:3926` \| `handoff_write_v4` `server.py:2532` | no | no | no | FALSE SEAL — misleading version |
| `human_required_*` queue (§2.2) | tool params yes, **values no** | no | envelope yes, `stats` no | FALSE SEAL — comprehensive |

The three sharpest:

* **`diagnostic_summary`** — two genuinely unrelated tools that collided on a name.
  `willow-2.0` is a **linter runner**: shells out to `ruff check --output-format=json` and
  `mypy --output=json`, diffs against a SOIL baseline (`sap_mcp.py:5477-5545`), returns
  `{path, tool, diagnostics}` (`:5485`). `willow-mcp` is an **install health self-check**:
  SOIL status, Postgres reachability, manifest, identity bindings, worker liveness, egress
  lease (`server.py:3947-3970`), returns `{verdict, mode, serve, app_id, checks, problems}`
  (`:3965-3975`). Not one shared response key. `willow-2.0`'s is `@sap_gate()`-gated
  (`:5471`); `willow-mcp`'s is deliberately ungated because "it must answer even when your
  manifest or database is misconfigured" (`server.py:3921`). **Neither should be renamed to
  the other; one needs a new name.**
* **`fork_create`** — the most dangerous shape: the signature matches **exactly**
  (`app_id, title, created_by, topic="", fork_id=""`: `sap_mcp.py:2354-2360` vs
  `server.py:4355-4361`), so it reads as drop-in. But `willow-2.0` INSERTs into Postgres
  `forks` and separately puts the env snapshot into SOIL (`sap_mcp.py:2369-2384`), returning
  2 keys (`:2385`); `willow-mcp` puts the whole record into SOIL collection `"forks"`
  (`forks.py:100-115`, rationale `forks.py:3-6`), returning 13. ID formats differ
  (`FORK-{uuid4hex[:8].upper()}` at `sap_mcp.py:2365` vs `forks._fork_id` at `forks.py:97`),
  and only `willow-mcp` validates (`forks.py:93-99`).
* **`fleet_status`** — both take only `app_id`, and answer different questions.
  `willow-2.0` is liveness ("Call this first. Confirms Postgres, SOIL, and Ollama are up",
  `sap_mcp.py:618-619`), returning 12+ keys (`:687-700`). `willow-mcp` is roster membership
  and explicitly redirects: "Use `fleet_health` for liveness signals rather than roster
  membership" (`server.py:2815-2818`). **`willow-mcp`'s `fleet_health` — not `fleet_status` —
  is the true counterpart.** A cross-repo rename would be the correct fix and the name
  similarity actively argues against it.

On `handoff_write_v3` -> `v4`: the version numbers are **not** an upgrade path.
`willow-mcp/src/willow_mcp/handoff.py:40-41` carries an explicit comment that the written
`format` field is `"handoff_v1"` and that "v4" counts *call-signature generations*, not
document format. v3 writes a validated markdown handoff with typed verifiable claims
(kind enum at `willow-2.0/willow/fylgja/handoff_v3.py:27-34`, JSON schema cited at
`sap_mcp.py:3946`); v4 writes `handoff.json` + `closeout.md` into a dispatch packet dir
(`handoff.py:38`, `:52`, `:55`) and requires a `dispatch_id`. v3's actual counterpart is
`willow-mcp`'s differently-named `session_handoff_write` (`server.py:2672`,
impl `dispatch.py:496`) — and even that is lossy: `next_bite` is `str` there
(`dispatch.py:503`) vs `dict` in v3 (`sap_mcp.py:3930`), and claims/verification are gone
entirely.

Note what this means for the tool surface as a whole: **1 consolidation target out of 12
identically-named tools.** The 38 shared tool names not examined here cannot be assumed
either way — they were not read, and on this base rate assuming duplication would be wrong
about eleven times in twelve.

#### Near-miss identifiers

Scored by `StringMatcher` as shipped:

| pair | stock | what they actually are |
|---|---|---|
| `grove_channel` vs `grove_channels` | **0.963** | a Postgres NOTIFY channel (`grove_db.py:195`) vs a Python reader function (`grove_reader.py:742`). **FALSE SEAL** — above threshold, unrelated referents. |
| `handoff_write_v3` vs `handoff_write_v4` | **0.938** | `willow-2.0/sap/sap_mcp.py:3926` vs `willow-mcp/src/willow_mcp/server.py:2532`. **FALSE SEAL** — a version bump is a one-character edit that Nestor cannot see. |
| `app_install` vs `app_uninstall` | 0.917 | `willow-2.0/sap/sap_mcp.py:5647` / `:5748`. Exact opposites, 0.003 under threshold. |
| `grove_flag` vs `grove_unflag` | 0.909 | `safe-app-willow-grove/grove/mcp_local.py:466` / `:486`. Exact opposites. |
| `fleet_read` vs `fleet_reload` | 0.909 | `willow-mcp/src/willow_mcp/gate.py:94` vs `willow-2.0/sap/core/gate.py:240`. Two **permission strings** — a read grant and a reload grant. |
| `cbm_search` vs `cmb_search` | 0.900 | `willow-2.0/sap/sap_mcp.py:6015` vs `:4974`, **same file**. `cmb_search` searches the `cmb_atoms` table; `cbm_search` shells out to the codebase-memory-mcp CLI. A two-letter transposition separating two unrelated subsystems. |
| `knowledge_write` vs `knowledge_write_ext` | 0.882 | `willow-2.0/sap/core/gate.py:196` / `:315`. Two distinct permission tiers. |

`grove_channel`/`grove_channels` and `handoff_write_v3`/`v4` are false seals *today* at the
0.92 default; the other five sit in 0.88–0.92 — i.e. one threshold nudge away.

### 2.6 The `the_grove.py` false friend: Nestor passed

`willow-mcp/src/willow_mcp/the_grove.py` is unrelated to Grove (it is a lessons-ring store,
docstring at `:1-24`). Scored against all 1 191 Grove functions, its best match is
`depth` (`the_grove.py:77`) vs `server_count`
(`safe-app-willow-grove/grove/apps/mcp_registry.py:113`) at **0.639** (`stock`/`nojunk`) and
**0.867** (`tokenset`) — below threshold on every matcher. **Nestor correctly did not seal
the false friend.** Worth stating because it is the one place the naive name-based approach
would have failed and the content-based one did not.

---

## 3. What this says about Nestor

### 3.1 A real bug: `StringMatcher` is broken on keys >= 200 characters

`nestor/matcher.py:75-80` scores with `difflib.SequenceMatcher(None, a, b).ratio()`.
`autojunk` defaults to **True**: when `len(b) >= 200`, difflib marks every element occurring
in more than 1% of `b` as junk and excludes it from matching blocks. On a *character*
sequence drawn from a ~40-symbol alphabet, that is essentially the entire alphabet. The
scores do not degrade gracefully; they collapse.

Measured over the 35 cross-repo function pairs the token matcher rates >= 0.92, scored in
both directions (70 observations — the direction matters, see §3.2):

| normalized key length | n | median `stock` | median `autojunk=False` |
|---|---|---|---|
| < 200 chars | 6 | 0.968 | 0.968 |
| 200–499 | 22 | 0.924 | 0.965 |
| 500–999 | 36 | 0.923 | 0.964 |
| 1000–1499 | 6 | **0.547** | 0.954 |

Below 200 characters the two agree to the digit. Above 1000 the shipped matcher is off by
0.4. Concretely, `grove_bus_send`
(`safe-app-willow-grove/grove/mcp_local.py:504` <-> `willow-2.0/grove/mcp_local.py:499`,
1 205-char key) scores **0.547** as shipped and **0.981** with `autojunk=False`. It is a
true duplicate and Nestor as shipped will never serve it.

This is not exotic — the *median* Grove function normalizes to 484 characters, and every
non-trivial one crosses the 200-char cliff.

**Recommendation:** `nestor/matcher.py:79` should pass `autojunk=False`, or `StringMatcher`
should take it as constructor config. Note the cost: `autojunk=False` is ~13x slower
(measured: 0.56 ms/pair -> 7 ms/pair on ~800-char keys), which is presumably why difflib
defaults it on. That trade belongs in the caller's hands, not silently in the default.

### 3.2 A worse bug: `similarity` is not symmetric, so seal ORDER decides what gets served

Because `autojunk` is applied to the **second** sequence only, `ratio(a, b) != ratio(b, a)`.
`memory.lookup` (`nestor/memory.py:245`) always calls `matcher.similarity(query_norm,
row["source_norm"])` — so which of a pair was sealed and which is being probed changes the
score, and therefore changes whether the pair is served or queued.

Reproduced against Nestor's public API with two real Grove functions
(`grove_list_channels`: `safe-app-willow-grove/grove/mcp_local.py:161-172` and
`willow-2.0/sap/grove_tools.py:138-151`, normalized to 255 and 299 chars):

```
similarity(A, B) = 0.9206
similarity(B, A) = 0.3177

SEAL grove:grove/mcp_local.py:161  then PROBE w20:sap/grove_tools.py:138  -> NO MATCH (queued for a human)
SEAL w20:sap/grove_tools.py:138    then PROBE grove:grove/mcp_local.py:161 -> SERVED sim=0.921
```

Same two texts, same threshold, opposite verdicts. Other measured swings in this corpus:
`_msgs_to_dicts` 0.970 / 0.479, `_on_subscribe` 0.948 / 0.360, `create_channel` 0.372 / 0.894,
`get_history` 0.979 / 0.618, `_kart_ok` 0.920 / 0.444, `grove_reply` 0.491 / 0.937.

For an engine whose whole promise is "a sealed pair either serves or it doesn't," a
serve decision that depends on insertion order is a correctness defect, not a tuning issue.
It also means the ledger's audit trail records a decision that is not reproducible from the
pair contents alone.

### 3.3 Where 0.92 sat: right for function bodies, badly wrong for identifiers

**On function bodies with a code-aware matcher, 0.92 is a good threshold.** Of 35 cross-repo
pairs at or above it, 34 are same-name and the one different-name pair
(`_ollama_models`/`list_models`) is a genuine duplicate. There were no obvious junk matches.

**On identifiers it is the wrong shape entirely — the true and false populations are
inverted.** Every same-thing-different-name pair in the human-required vocabulary scores
*below* 0.92; every different-thing-similar-name pair scores *near or above* it:

```
SAME THING, different surface            0.92 should fire
  0.880  human_required_enqueue        <-> human_required_queue_enqueue    MISS
  0.880  human_required_resolve        <-> human_required_queue_resolve    MISS
  0.864  human_required_list           <-> human_required_queue_list       MISS
  0.850  willow.routing_decisions      <-> routing_decisions               MISS
  0.824  human_required                <-> human_required_queue            MISS
  0.786  needs_attestation             <-> attestation                     MISS
  0.700  needs_consent                 <-> consent                         MISS
  0.690  external_onboarding           <-> onboarding                      MISS
  0.667  needs_review                  <-> review                          MISS
  0.640  operator_overload             <-> overload                        MISS
                                                          -> 0 / 10 found

DIFFERENT THINGS                         0.92 must not fire
  0.963  grove_channel                 <-> grove_channels                  FALSE SEAL
  0.938  handoff_write_v3              <-> handoff_write_v4                FALSE SEAL
  0.917  app_install                   <-> app_uninstall                   0.003 clear
  0.909  grove_flag                    <-> grove_unflag                    0.011 clear
  0.909  fleet_read                    <-> fleet_reload                    0.011 clear
  0.900  cbm_search                    <-> cmb_search                      0.020 clear
```

There is no threshold that works: the true set tops out at 0.880 and the false set bottoms
out at 0.286 (`critical` vs `urgent` — the one real divergence Nestor scores *lowest*).
Character-edit distance on identifiers measures typing distance, not meaning, and in code
the semantically loudest edits (`un`, `_ext`, `v3`->`v4`, a two-letter transposition) are
the *cheapest* ones.

**Also wrong-shaped for function bodies at the 0.89–0.92 boundary.** `grove_messages` (0.917),
`create_channel` (0.925), `init_schema` (0.900) and `authorize` (0.974) all sit at or above
threshold and are all false seals (§2.4). The differences that make them false — an extra
`grove.message_flags` query, a name-normalization call, an extra `CREATE TABLE`, a changed
URL path — are each a handful of characters in a body of several hundred. **Similarity is
monotone in edit size; consequence is not.** That is the structural reason a similarity
threshold cannot decide "is this a duplicate" for code, at any value.

### 3.4 The memory cannot represent the fleet's actual drift signature

Nestor's memory is keyed on the normalized source (`nestor/memory.py:133`,
`store.memory_find(norm, source_lang, target_lang)`). Two consequences:

**(a) Exact duplicates collapse.** Sealing 1 943 Grove functions produced only 1 870 rows —
the 69 cross-repo byte-identical groups are exactly the thing under investigation, and
`lookup` can never return them as a pair because only one survives. They were recovered only
by instrumenting the seal loop for collisions. *This is a missing affordance:* there is no
`memory.collisions()` or "this normalized key already exists with a different target" signal.

**(b) Same name, different referent silently overwrites — with no conflict raised.**
`add_pair` at `nestor/memory.py:151-156` calls `store.memory_seal(...)` whenever an existing
sealed row has a *different* `target_text`. Demonstrated with `EntityResolver`:

```python
r = EntityResolver(store, domain="demo")
r.seal("routing_decisions", "willow-2.0/core/pg_bridge.py:319 (id TEXT, prompt_hash, rule_id, decision JSONB)")
r.seal("routing_decisions", "safe-app-willow-grove/schema.sql:102 (id BIGINT, prompt_snippet, routed_to, ...)")
r.resolve("routing_decisions")
# -> confidence 1.0, sealed True, canonical = the SECOND definition. Same pair_id.
#    The first definition is gone. Nothing was raised.
```

Nestor has `RejectedPairError` (`nestor/memory.py:110`) precisely because "one human asserting
the opposite of another's recorded decision ... is exactly the moment that should not pass
unnoticed." **A conflicting seal on the same surface is the same moment and it passes
silently.** For this corpus that is the single most consequential gap: the fleet's dominant
failure mode is *one name, several incompatible referents*, and Nestor's data model asserts
that a surface has one canonical target. It cannot hold the finding.

### 3.5 Would a code-aware matcher have done better? Yes, measurably

At threshold 0.92 on cross-repo function pairs: `stock` finds **23**, `tokenset` finds **35**.
`tokenset ⊇ stock` — every pair `stock` finds, `tokenset` finds, plus 12 more. No `stock`-only
pairs at 0.92. Recall improved by 52% with no measured precision loss.

Concrete cases where a code-aware matcher changes the answer:

* **`grove_bus_send`** (`safe-app-willow-grove/grove/mcp_local.py:504` <->
  `willow-2.0/grove/mcp_local.py:499`): `stock` 0.547 -> not served; `tokenset` 0.962 -> served.
  A genuine duplicate the shipped matcher loses entirely.
* **`grove_channels`** (`safe-app-willow-grove/grove_reader.py:742` <->
  `willow-2.0/core/grove_reader.py:416`): `stock` 0.640, `tokenset` 0.953.
* **`routing_decisions` DDL** (`safe-app-willow-grove/schema.sql:103` <->
  `willow-mcp/docs/schema/routing_decisions.postgres.sql:18`): `stock` 0.122,
  `tokenset` 0.383, but `sqlshape` **0.067** — and `sqlshape` is the only one whose number
  is *interpretable*: "6.7% of the columns are shared." A similarity of 0.122 tells a
  reviewer nothing; "these two tables share two of twelve columns" is an actionable finding.
  For the benign case the shape matcher is equally decisive: `frank_ledger`
  (`safe-app-willow-grove/grove_db.py:222` <-> `willow-2.0/core/pg_bridge.py:98`) scores
  `stock` 0.147 / `nojunk` 0.795 / **`sqlshape` 1.000** — identical column sets, and only
  the structural matcher says so.

**What normalization destroys.** `StringMatcher.normalize` (`nestor/matcher.py:70-73`) is
`lower()` then `re.sub(r"[^\w\s]", "")` then whitespace collapse. On code that removes:

* **Schema qualification.** `willow.routing_decisions` -> `willowrouting_decisions`. The dot
  that says "different schema, different table" is deleted, and the two names are then
  glued into one token.
* **Case, which is Python's type/constant convention.** `KINDS` and `kinds`,
  `OAuthClientInformationFull` and a local `oauthclientinformationfull` become the same key.
* **Every operator and delimiter.** `a == b` and `a != b` normalize identically
  (`a b`); so do `x[0]` and `x(0)`, `->` and nothing, `%s` and `s`. In SQL, `NOT NULL`
  survives but `<>`, `>=`, `!=` do not, and `'{}'::jsonb` becomes `jsonb`.
* **Structure.** Indentation is whitespace, so a body and the same body inside an
  `if/else` normalize to nearly the same key.

For SQL specifically the most damaging loss is the comma-and-parenthesis structure: a
`CREATE TABLE` becomes a bag of words in which column *order* and column *boundaries* are
gone, which is why `stock` rates two disjoint `routing_decisions` schemas 0.122 rather than 0.

**What an identifier-weighted or AST-shape matcher would add** (not built here, so this is a
recommendation, not a measurement): weighting rare identifiers (`frank_ledger`,
`normalize_channel_name`, `_attach_message_flags`, `mcp-approve`) far above boilerplate
(`conn`, `cur`, `return`, `try`) would push exactly the §2.4 false seals below threshold,
because in each of those the divergence is carried by one or two rare tokens against a
background of identical plumbing.

### 3.6 API and ergonomics notes

Things hit while driving Nestor, in rough order of how much they cost:

1. **`lookup` is O(n) with no pruning hook.** `nestor/memory.py:240-247` scores every
   candidate through the matcher with no early exit. At 1 870 pairs of ~800-char keys that
   is 1.25 s per lookup, ~40 minutes for a self-join. `real_quick_ratio()`/`quick_ratio()`
   are valid upper bounds and `lookup` already knows the threshold it will filter on — it
   could expose a `min_similarity` and let a matcher short-circuit. I had to reimplement
   pruning inside my own `Matcher`, which is the wrong layer: **the matcher is called
   stateless per candidate**, so difflib's `b2j` map and my character-multiset bound were
   rebuilt on every call. Memoizing inside the matcher took the run from ~45 min to ~2 min.
   A `Matcher` protocol with an optional `prepare(keys)` / batch `similarity_many(query,
   keys)` would make this a library concern instead of a user workaround.
2. **No collision or conflict signal on seal** (§3.4). `add_pair` returns the existing pair
   on a collision, but the caller cannot distinguish "already had this" from "just silently
   replaced a different target" without comparing `target_text` by hand.
3. **`memory.lookup(limit=5)` default is too small for analysis.** Fine for serving one
   answer; useless for surveying a cluster. Not a bug, but the default fights the
   analysis use case.
4. **`set_ledger_path` is module-global**, as are `set_store` and `set_matcher`
   (`nestor/cascade.py`, `nestor/storage.py`, `nestor/memory.py:50`). Running four matcher
   variants meant four processes, because there is no per-run context object. The
   `matcher=` and `store=` per-call arguments help, but the ledger has no equivalent.
5. **Domain tags as `source_lang`/`target_lang` works well.** Genuinely convenient — five
   disjoint corpora in one SQLite store with no cross-talk, and it made the "keep corpora
   small" discipline easy to follow. This part of the design earned its keep.
6. **`NESTOR_SEAL_KEY` as an env var** is awkward for a tool that wants several signing
   contexts in one process, and forgetting it emits a `RuntimeWarning` rather than failing
   loudly or defaulting quietly. Minor.

### 3.7 Did Nestor earn its keep, or would `grep` + `difflib` have done the same?

Honest answer: **for this corpus, mostly no — but not entirely, and the failure is
informative.**

What Nestor actually contributed:

* **The `Matcher` seam is the real product.** Being able to inject `tokenset` and `sqlshape`
  and have sealing, thresholds, domain tags, and the ledger keep working unchanged is
  genuinely useful, and it is what made the `stock`-vs-code-aware comparison in §3.5 a
  controlled experiment rather than two unrelated scripts.
* **Domain-tagged corpora in one store** (§3.6.5) removed real bookkeeping.
* **The seal-collision behaviour**, once instrumented, handed over the 69 exact duplicate
  groups for free.

What it did not contribute:

* **Every result in §1 and §2 is reachable with `ast` + `difflib` + `collections.Counter`.**
  The extraction — which is where the actual work was — is `ast`, not Nestor. Nestor scored
  strings I had already isolated.
* **The seal/serve/queue mechanic did not fit.** Nestor's mechanic answers *"what is the one
  verified answer for this input?"* The question here is *"which inputs collide, and are the
  collisions real?"* — a clustering question, not a serving one. The mismatch is why §3.4
  bites: a one-canonical-target memory cannot store "this name has four referents."
* **`stock` alone would have produced a materially worse answer** (23 pairs instead of 35,
  plus the order-dependence of §3.2), so the shipped configuration was *net negative* versus
  plain `difflib.SequenceMatcher(..., autojunk=False)` — which is 15 lines of script.

The sharpest verdict: **on the highest-value output — the false seals — Nestor's score was
actively anti-correlated with the truth.**

* At similarity **1.0** — byte-identical MCP tool names, the maximum confidence the engine can
  express — **11 of the 12 pairs checked are false seals** (§2.5). A perfect score meant a
  92% chance of being wrong.
* At **0.974**, the highest-scoring function pair in the corpus, `authorize` is a false seal
  whose merge breaks a live OAuth consent flow (§2.4).
* At **0.122** and **0.593**, near the bottom of the range, sit two of the most consequential
  real defects: three incompatible `routing_decisions` schemas (§2.1) and a `NOTIFY` with no
  listener anywhere in the fleet (§2.3).

A verified-match engine asked "are these the same?" that answers with edit distance will, on
code, be most confident exactly where the difference is smallest and most consequential — a
changed URL path, an added `flags` key, a `v3` -> `v4`, a `needs_` prefix.

That is not a reason to abandon Nestor. It is a reason to say plainly what its threshold
means: **similarity is a retrieval prior, never a verdict.** Nestor's own design already
agrees — a match above threshold is *served with provenance*, and the whole point of the
seal is that a human looked. Used that way here — as a candidate generator whose output was
read by a human before any verdict — it worked. Used as an oracle it would have proposed
five consolidations that break the fleet.

---

## Appendix: reproducing

Extraction and driver scripts were kept in `/tmp/grove/` and are not committed:
`extract.py` (ast unit extraction), `extract_ident.py` (identifier corpus),
`matchers.py` (the four `Matcher` implementations), `run_fn.py` / `run_sql.py` /
`run_ident.py` (Nestor drivers), `tables.py` (cross-repo `CREATE TABLE` sweep).
Repos were treated as read-only throughout; nothing outside this file was modified.
