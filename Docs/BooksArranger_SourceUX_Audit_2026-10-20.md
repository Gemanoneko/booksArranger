# Books Arranger — source UX audit

2026-10-20, Judy. **Final verdict: SOURCE UX CLEAR — all four scoped Minor findings resolved at the v2 pins below.** Initial findings and intermediate recheck are retained as evidence. Finite source audit only, not packaged QA, rendered accessibility/geometry verification, backend correctness review or release approval. References: Reacquire UX and BulkRetryFeedback UX dated 2026-10-20.

## Inspected pins

Desktop checkout: `C:/Antigravity Projects/Worktrees/Books Arranger/electron-m1`.

| File | SHA256 |
|---|---|
| `web/app.js` | `65fa1330b9f058555d328e27f73deea574ae12839b951a68afbfd1163594c912` |
| `web/index.html` | `2fc5dedef03362725d5f52329dabf9b22cafd18932775ebd22ec3055da83e35d` |

Both hashes rechecked unchanged after frontend inspection. Necessary read-only field consumers consulted: `MergeService._bulk_retry_view`, `automatic_processing.status/_start_block`, `audio_jobs` retry-check status projection, and `reacquire_sources.assess_live_sources/project`. Backend files are concurrently owned and not certified/pinned by this UX audit.

## What matches the specs

- Retry all and Retry selected share the acknowledged run through `acceptBulkResponse` and the one `retry-all-status` receipt. A newer submission clears the selected legacy banner and suppresses replay of the older receipt on failed acknowledgement. Confirmation says Request retries; accepted requests are distinguished from actual child jobs by versioned per-target progress. A 69-request/zero-child state can show waiting checks alongside global zero actual queued jobs.
- Pending readmissions produce a disabled waiting/checking remedy and are excluded from new selected retry eligibility. Backend attention projection supplies the distinct Retry checks group; the renderer uses the renamed group and preserves selection while explaining already waiting/new retries available. This source audit does not execute or independently certify server admission/duplicate guards.
- The receipt uses actual current worker/start failure reasons only while stalled; an older startup failure is suppressed once checking/queued/running work is observed. Request-only Resume availability includes `retry_checks.waiting`, and Start rendering uses authoritative `can_start`/block reason rather than conversion queue size. Supported idle/paused/completed/needs-attention backend job states do not become Running merely because requests exist.
- Conversion activity headings are state-first: Audiobook on hold, Audiobook paused, Pausing audiobook. Held progress suppresses advancing count/clock. This addresses the screenshot's misleading Converting label in candidate source, not proof of an installed update.
- Need to reacquire requires a typed required projection; it is not inferred from source error English or broad attention membership. The projection preserves uncertainty wording, exact source paths, reason/repair limit and source-presence distinction. Row remedies cannot offer Retry/Repair for that primary group. Active-entry archive acknowledgement hides conversion controls while retaining a readable historical-evidence notice; normal selection restores Manual review visibility. No damaged-source Delete control was added.
- The audio-analysis bridge requires the supported internal typed assessment and exact evidence binding. Primary's bounded implementation receipt says no supported positive producer currently marks serious corruption, and Iron Inferno is the harmless trailing-tag case. Nothing in the inspected frontend independently labels Iron Inferno Need to reacquire. This is not a live catalog audit or a promise that every serious future corruption is automatically diagnosed.

## Findings

1. **Minor — Retry selected tooltip still promises queue placement.** `renderRetrySelected` retains “queue each one, right after the current book.” That is stronger than accepted-request semantics and can repeat the original misunderstanding for deferred/refused admission. Use the same request/check-before-job wording as Retry all.
2. **Minor — Retry checks tooltip excludes waiting state.** `web/index.html` group-checking still describes only active checking before Retry is offered, while its visible label and membership now include saved requests waiting for checks. Use the committed “waiting for or undergoing retry checks” tooltip.
3. **Minor — absent progress schema lacks its explicit unavailable fact.** `retryReceiptText` preserves the accepted receipt but does not add Current retry progress unavailable when versioned progress counts are absent. Users cannot distinguish a complete short receipt from missing current telemetry. Keep accepted history and state the unavailable progress without inventing zeros.
4. **Minor — ordinary lifecycle count changes rewrite a polite live region.** `retryReceiptText` concatenates all six changing per-target counts into `retry-all-status`, whose markup is role=status. Polling a progressing batch can repeatedly announce the whole receipt instead of meaningful acknowledgement/block/phase/completion changes only. Reuse the existing non-live `retry-all-count` for routine counts; no new layout/control is necessary.

Ender acknowledged these four gaps and supplied the narrow correction packet. Its recheck is recorded below; the earlier pins remain the evidence for the original findings.

## Narrow correction recheck

**Verdict: SOURCE UX FINDING — one remaining Minor accessibility gap; three original Minor findings resolved and the fourth partially resolved.** This supersedes the opening verdict for only these four corrections. No broader audit, rendered test or release clearance is added.

Packet: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/bulk-reacquire-source-review-packet-20261020-v1.json`, independently read SHA256 `b38635e6aa474d85872c97be1088ff0dbd3bcf721234ca34986de6768dbb5d62`. Its metadata calls itself non-authoritative; the matching independently read frontend bytes are the scope of this source verdict.

| File | Final packet SHA256 independently matched and rechecked |
|---|---|
| `web/app.js` | `f5e44af8983b1d11b877d09bd9ceb7a648a644921e81c4b4018d0b0125c33ce4` |
| `web/index.html` | `bc669770205f2df57225cd17f942c1a7ed3acaec2f48aefe45944826554788e3` |

1. **Resolved:** Retry selected now says Request retries and checks-before-conversion-job, matching Retry all without a queue-order promise.
2. **Resolved:** Retry checks tooltip names both saved requests waiting for checks and books undergoing checks.
3. **Resolved:** absent versioned progress appends **Current retry progress unavailable.** while preserving accepted-request history.
4. **Partially resolved:** `retryReceiptText(run,false)` now provides stable receipt/phase/block text to the polite live region; routine changing numbers are placed outside it in `retry-all-count`. Same-phase ordinary progress no longer changes the live text by numeric count alone. However, `web/index.html` still sets `aria-hidden="true"` on that span. All six numeric lifecycle counts are consequently removed from the accessibility tree, with no numeric equivalent remaining in the phase-only live status. The counts must remain readable as non-live text (for example by removing aria-hidden) while avoiding per-tick announcements. No new control/layout is needed. Ender notified; this is the remaining closure issue for the original accessibility finding.

The packet reports 23 in-process DOM assertions and syntax checks passing. Judy did not rerun them, inspect renderer pixels or claim a screen-reader runtime result. The remaining issue is directly visible in the source semantics. No source drift occurred during this recheck; any corrected subsequent packet/hash needs its own bounded acknowledgement.

## Final v2 accessibility closure

**Verdict: SOURCE UX CLEAR for the four reported Minor findings.** The remaining fourth issue is resolved: `retry-all-count` is now an ordinary readable span without aria-hidden, outside the sibling `retry-all-status` polite live region. Routine lifecycle numbers remain inspectable in the accessibility tree without each numeric update rewriting the live announcement. `web/app.js` is unchanged from the previous correction recheck, so the three wording/progress fixes and phase-only live rendering remain at their already inspected bytes. No remaining finding in this bounded scope.

Independently read packet: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/bulk-reacquire-source-review-packet-20261020-v2.json`, SHA256 `344c365cffef477c434dea5e30ebed8f5ebf85ff18f873a672bd79131dc08635`. Its frontend entries match the actual files independently hashed during this final recheck:

| File | Final v2 SHA256 |
|---|---|
| `web/app.js` | `f5e44af8983b1d11b877d09bd9ceb7a648a644921e81c4b4018d0b0125c33ce4` |
| `web/index.html` | `670233a0e751f8458ac7b0491912a0349dcc4ebf3727832cf1ecf45863c12c92` |

Developer reports 25 focused DOM assertions and syntax PASS for v2; this audit does not independently rerun them. No screen-reader runtime, rendered geometry, native/app operation, test launch, live mutation or release approval is claimed. Only this report changed. Earlier/intermediate verdicts above are superseded by this final result for the exact four findings and these bytes.

## Limits

No code or other agent files changed by Judy; only this report written. No tests rerun, app/browser/native/process launch, focus/input/click, media/NAS mutation, live API request/write, global setting or scratch output. Developer-reported in-process DOM assertions are supplementary evidence, not formal QA executed here. No target rectangles, screen-reader announcements or theme pixels were measured. Futaba's committed-build checks and Senua's backend review remain separate.
