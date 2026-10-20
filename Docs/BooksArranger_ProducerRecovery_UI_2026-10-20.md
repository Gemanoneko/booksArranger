# Conditional producer recovery UI/API checkpoint — 2026-10-20

Scoped consumer implementation only, not backend acceptance, formal QA or live recovery clearance. Judy §8 is pinned at `499c3f5ea7951b1aa7218bcbb43acc098fb5d227`; technical design reference `2c4f716`. The actual historical human-origin fact remains absent; this UI supplies no attestation or origin control and cannot unblock that actual attempt.

## Consumer boundary

- `web_server.py` (the existing route file; no `server.py` exists) admits `POST /api/audiobook/prepare-recovery` through the existing token/origin/body/control-admission protections. Its exact body is `{job_id}`; UUID validation and strict shape reject actor, evidence, path, origin-fact and other fields. The branch calls only `MergeService.prepare_producer_recovery(job_id)` and returns its authoritative response with HTTP200. It starts no restart, Retry, queue or deletion.
- `web/app.js` reuses the existing first row remedy and selected `retry-job` control for Prepare recovery. It reads `attention.producer_recovery`, schema `books-producer-recovery-capability-v1`, typed state/cause and exact capability booleans. It does not infer causes from reason text. Pending has one shared in-flight guard, aria-disabled focus retention and ignored duplicate activation. No metadata form refresh is used; saved edits/caret remain intact.
- Confirmed checkpoint instructions require matching job, `queued:false`, `outputs_changed:false`, the typed capability and a nonempty saved checkpoint ID for `waiting_restart`. Malformed replies, HTTP save errors and uncertain transport never announce preparation. Transport failure retains the old capability, disables writes and asks for durable-state refresh. No Windows restart is initiated or promised sufficient.
- Producer holds suppress Clear working files in the list, details and client action guard. Ready/isolated states offer ordinary Retry only when both producer capability and existing job Retry eligibility allow it. Persistent `row.producer_recovery_retained`, schema `books-producer-retention-v1`, renders the specified retained warning and supplied attempt/path/reason facts beside later jobs. No path or history is guessed.
- `web/index.html` adds only the specified retained-files warning/path container after existing Automatic result facts. Existing typography/actions are reused. No new origin control, dialog, color or disposal action was added.

Exact literal scan found the endpoint in the route allowlist/branch and frontend request/action, the capability schema in frontend and new fixtures, and the retention schema/field in frontend/fixtures. At handback, `producer_recovery.py` had begun defining the capability schema, but `MergeService.prepare_producer_recovery` and the final attention/retention projection were not yet present in the cross-boundary scan. Primary Ender owns those pending internals. No complete backend wiring or real recovery workflow is claimed by this checkpoint.

## Checks and limits

`tests/test_producer_recovery_http.py`: **3 passed in0.005s** against the real HTTP handler with an explicitly mocked service. Covers token/origin/strict shape/shutdown, exact job-only forwarding, repeated authoritative checkpoint response, unsupported refusal/save failure and no queue/resume/create calls. It does not establish real backend idempotency or closure.

`tests/test_producer_recovery_frontend.js`: **PASS**, final owned elapsed155.5ms. Runs the actual app code and click paths against isolated DOM/transport doubles: typed unsupported/startup/mismatch states, Prepare placement/tooltips/described-by, one pending request across row/details, exact body, pending focus, acknowledged-only instructions, malformed missing-checkpoint refusal, HTTP/transport failures, dirty Cyrillic draft/caret preservation, allowed/blocked Retry, Clear suppression, persistent old-attempt facts and no programmatic focus move on background capability changes. No browser geometry, zoom, real assistive-technology announcement count or focus-taking QA was measured.

Existing attention and Retry DOM suites also passed. Existing HTTP regression initially reported13/15, with these exact failures:

- `test_automatic_controls_draft_token_shape_and_scanner_owner`: expected `automatic.start()` while current code passed `server_closing=False`.
- `test_protected_cover_and_candidate_page_enrichment`: `BrowserServer.__new__` fixture lacked `loaded_version` needed by `health()`; that health shape also requires restart context/recovery-operation fields.

Primary Ender explicitly authorized faithful fixture-only corrections: the expected current closing argument and initialized health fields. The coherent HTTP suite then passed **15/15 in0.023s**, preserving its behavioral assertions. Causal baseline execution/comparison against immutable `0469966` was not performed, so these failures are not claimed proven unrelated regressions. No product behavior was changed to satisfy them.

Every cited check used the unchanged reviewed native-owned runner, `timeoutMs=600000`, sequentially; all returned `closed=true`, `forced=false`, native `active=0`, `unsignaled=0`, `zero=true`. No broad heavy/uncertain-owner command, live API, media/catalog/settings mutation, OS restart, compiler, new binary, iTunes or focus-taking window was used. New HTTP fixture scratch is retained under the session shared folder for Sergei's manual cleanup.

## Handback pins

| File | SHA256 |
| --- | --- |
| web_server.py | 5a0c559bcb9adc154fb8e4b429dfcd2a250ff01397a546aac07da7dc3264bee5 |
| web/app.js | 20024dcf09893c9d28ac745a8bed5415a2fde25b2a680ce4202bdddb6fdb5df9 |
| web/index.html | e1894e1fd5b7e7c31b485dd802688fe87daece75e408576043f4b7cce4d8a848 |
| tests/test_producer_recovery_http.py | 5558c94046e72383880b09e59e5769971cad16b471fe9fd3045f7906ad21f10a |
| tests/test_producer_recovery_frontend.js | 19269999f2b983973210f0b99bdf111337451fa8168bccea065d3d036e9ef830 |
| tests/test_merge_http.py | 0e5ac1c4c3eba967469966958e8068b15efbcc42741d444616e3c9760ee49a19 |

Full backend integration, real private closure/isolation/fresh Retry checks, stale server Clear refusal, Judy geometry/accessibility verification, formal QA and release review remain separate pending gates. The actual unsupported attempt remains held.
