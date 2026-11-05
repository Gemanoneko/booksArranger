# Durable Save/Approve implementation design

Ender · 2026-11-05 · Proposed implementation, awaiting Senua boundary review. This extends the existing SQLite catalog and book-local Save/Approve routes. It is separate from the narrow Tolkien provenance correction. No build/release or live-data mutation is part of preparation.

Authority: Sergei's current instruction to record Save/Approve decisions immediately and preserve them through unrelated work/restart, plus committed UX `d45f6cd8b475bde4c332907163ff8c427d9853e8`. Discard remains an unsaved-draft action; it is not cancellation of an accepted decision.

## Durable record and acceptance

One new `durable_decisions.py` owns schema, validation, acceptance, CAS application and recovery. Proposed tables:

- `book_decisions`: immutable UUID request identity, action, candidate ID, library, observed candidate revision and complete source fingerprint, per-book sequence, predecessor decision ID, bounded canonical payload JSON and SHA256, accepted UTC, state, current typed application error, and optional resulting candidate revision/job ID/application receipt. The accepted payload is never rewritten by a retry.
- `book_decision_heads`: current compatible generation plus a bounded cumulative snapshot of unresolved effects, their original request IDs, domain/field ownership and dependency receipts. Domains distinguish names fields, review fields/metadata choices, track review and approval. The head is an application fence, not blanket supersession of all earlier requests.
- `book_decision_steps`: request ID plus named step, immutable input hash, durable outcome reference/hash and committed UTC. Unique `(request_id, step)` prevents repeated side effects.
- A compact completed-request tombstone retains request ID, action, book ID, payload hash, sequence, disposition and applied result identity after the temporary payload is purged.

HTTP validates the existing control's types, bounds, authentication, local origin and request identity. It then commits the intent in a short `BEGIN IMMEDIATE` transaction before acquiring worker/operation/review/group locks, checking media or planning a destination. This receipt confirms a saved decision, not successful conversion or unsafe approval. SQLite busy remains bounded and is an explicit acceptance failure if no durable commit can be established; the UI never guesses success.

UUID request identity is generated before sending and reused for reconciliation. Same ID plus same hash returns the original receipt. Same ID plus different payload is a conflict; it cannot overwrite the original. Different accepted decisions for a book have ordered sequence numbers assigned transactionally. Only a compatible request advances the effective head generation. An out-of-order late or incompatible request is durably audited as `needs_review`, retains its captured predecessor/revision, and does not advance the effective head/fence or strand the valid pending chain.

## Application, ordering and crash boundaries

A small worker claims one decision with CAS; unrelated books can be selected when one decision is held. It uses the existing safe Save/Approve application calls, with request-bound transaction hooks at their actual commit points. It never simply invokes a mutating call and writes `applied` afterward.

Every application-step transaction checks the book's current compatible head generation. When a successor is accepted, its cumulative snapshot carries forward every unresolved disjoint predecessor effect. Only explicitly overlapping submitted values supersede the corresponding older values. For example, Names Save A followed by Tracks Save B retains A's names effects and B's track effects; B cannot fence out and lose A. This composition rule applies to all covered Save/Approve controls.

The current head's worker may apply an inherited predecessor effect, recording that original request's step receipt, under the current head-generation fence. An old worker using the preceding generation cannot commit after the new head is accepted. For explicit overlapping replacement, the older value's receipt names the exact newer user decision; it is never cancelled merely because another book was busy. Temporary old payload is removed only after all its effects have applied or been fulfilled by a confirmed explicit replacement. Accepted names remain available from the cumulative ledger snapshot while application is pending.

Save followed by Approve captures the predecessor Save ID and its immutable accepted names snapshot. The current Approve applies that exact names snapshot in its own request-bound names substep if the predecessor had not yet applied; if the predecessor did apply, it reuses the saved names receipt. It never overwrites a newer accepted decision or applies the old pre-Save name plan. A source membership/identity change is not auto-rebased; a record-only revision can rebase only through the existing exact-fingerprint/full-source receipt guard. Failure to compose is a retained `needs_review` decision with the actual reason.

Required integration boundaries:

| Existing consumer | Durable boundary |
|---|---|
| `MergeService.names_save`, `entered_names.save_in_transaction` | Names entries, pending approval hold, request's names-step receipt and resulting candidate revision are committed in the same transaction. A replay reads that receipt and does not insert names again. |
| `CandidateReviewService._write` / `save`, metadata-choice record | Saved review/context/manual metadata or choice record and request's review-step receipt share the existing transaction. Existing `decision_record` hook for metadata choices is reused, not bypassed. |
| Track review | Track order/inclusion/coverage receipt and request step are committed together after existing fresh-source validation. |
| `_approve_values` and `_approve_book` preliminary name/rule/set-aside operations | Each independently committed mutation receives a request-bound idempotent substep in the same SQLite transaction. Durable application does not use the legacy refusal path's `_names_take_back` / `_drop_answer_rule` to erase a previously accepted decision. Names/rules already applied remain represented as that request's completed substep while unsafe later approval stays held. Every step CAS checks current accepted generation. |
| `AudioJobs.enqueue` with `approval_context` | Job insertion, final approved context and decision's applied receipt/resulting job identity are one transaction. Recovery resolves this receipt before considering another enqueue. Existing candidate/job uniqueness remains in force. |
| Non-enqueue terminal outcomes | Save, no-op, answer-only/next-question and finished-book metadata paths record their applied receipt with the final mutation transaction; no-op uses a short guarded receipt transaction. Enqueue is not the sole completion hook. |

The atomicity strategy is explicitly request-bound substep receipts, not one SQLite write transaction spanning hashing/media work and not an outer applied flag. No worker holding operation/review/group locks waits on another decision worker. Acceptance never takes those locks. The application worker retains existing lock ordering and source/output/native validation. Busy is a retriable application state, not cancellation of the stored decision. Real validation failures become a retained, typed `needs_review` result with its supported next step.

Startup recovers accepted/applying rows by inspecting the request-bound committed step receipts; an interrupted step without a committed receipt is retried through its original CAS. Existing paused audiobook conversion remains paused: recovering metadata and creating a safe pending job does not implicitly press Resume or recreate a completed publication.

## Retention and UI consumers

After the final application transaction records its minimum idempotency/result receipt, delete the temporary payload and substep scratch that the application no longer needs. Keep only compact request/result identity and hashes needed to reconcile a lost reply or avoid a duplicate effect. Failed/blocked decisions retain their bounded payload while needed to finish or display a specific correction. No source/media copies are created by intent storage. Completed-payload cleanup is idempotent and restart-safe; it cannot delete catalog history, media, names evidence or job/publication receipts.

No new generic queue screen, settings or Cancel for accepted decisions. Existing explicit unsaved-draft Discard clears only the frontend draft; there is no new endpoint that cancels accepted decisions. Existing withdrawal/review actions keep their own guarded meaning. A newer compatible accepted edit creates a new cumulative generation and preserves original requests/effects; explicit overlapping replacement has a compact supersession relation. It does not mutate the preceding request's captured values or silently delete its audit receipt.

Routes/consumers covered by the UX: row Approve, Edit names Save, Save preview metadata (`/api/review` for existing file-local review and `/api/candidate/review`), Save choices (`/api/candidate/metadata-choice`), Save track review (`/api/candidate/tracks`), and their existing equivalent book-local approval forms. `web_server.py` accepts and exposes/reconciles durable receipts. `ActionQueue` no longer owns these decisions in RAM; destructive Retry/Delete/Move behavior stays unchanged. `web/app.js` shows accepted versus applied/held states from the receipt, overlays accepted saved values on reopen, and reconciles silence without inventing success. Automatic Paused uses the committed Resume label addendum.

## Focused verification stages

1. Ledger acceptance under unrelated operation/review/group locks; original process closes and a fresh instance reads the exact payload. Duplicate/reused-ID/late predecessor and bounds checks.
2. Names/review/choice/track actual transaction hooks: crash before commit has no effect; crash after commit reuses the request receipt. Source/revision drift is held, never silently reapplied.
3. Actual Approve: request-bound names/rules/set-aside substeps, crash around final enqueue, exactly one pending job, immutable completed output, Save then Approve uses accepted names.
4. Restart worker, independent held-book continuation, compact completed-payload deletion and retained error payload, lost-reply reconciliation.
5. Committed Judy UI states and affected DOM/source tests, then independent Futaba focused QA. No full gate, native phase, build or release without a separate coordinated handoff.

The work is a bounded API/persistence feature, not a copy patch. The critical implementation prerequisite is enumeration of every independent Approve commit point before wiring the worker; no post-hoc outer `applied` flag is acceptable.
