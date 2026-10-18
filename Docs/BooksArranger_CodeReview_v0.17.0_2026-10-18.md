# Code Review — Books Arranger v0.17.0

## Header

Reviewer: Senua (Code Reviewer)
Date: 2026-10-18
Tool: Books Arranger (Electron desktop utility)
Release: v0.17.0
Commit range: 09714f2a0a607f670a14c120e32f12dad2d2158b..e028fc04c4b30ee26b6960f90948526205acb3ac
Files changed: 13 files, +509 / -70 (git diff --stat; includes prior release documentation)
Release source commit: e028fc04c4b30ee26b6960f90948526205acb3ac
Release artifact manifest SHA256: 3797c7d5117abdaf2f1cdd9b5879e7d8b51dfb370d6c9064b4c148f762716584
Release installer: dist/builds/ca0f85ed-aee7-458f-9709-44e9da85ed95/Books-Arranger-Setup-0.17.0.exe
Release installer SHA256: 1c6e17972f9410c818d4e4da82d0c506e8f2552cc15587ba4a33e3fae75272dd
Stand-down dimensions: none.

## Summary

Red-team review of durable per-book research deferrals, independent-candidate fairness, retained findings/provenance, and citation-only Goodreads series discovery. Exact target identity comes from the search row's title, all authors and immutable book id joined to the series page's own explicit matching entry. The ordinal is neither configured in the lead nor inferred from row order. Previous v0.16.12 Critical fixes remain intact. No product code, live catalog/library, provider request, installed app or shared safety configuration was modified by this reviewer.

## Rubric

### 1. Security

Status: Pass. Discovery citations use a bounded HTTPS Goodreads series URL; normal PublicClient transport, shared quotas/cache, human-check holds and challenge handling remain unchanged. No new shell or Electron configuration surface.

### 2. Correctness & Logic

Status: Pass. Per-book waits continue the batch; cached independent candidates remain reachable. Goodreads parsing requires a canonical source URL, one title header, each block's equal-length row/header arrays, unique matching book id, exact title/series consistency, whole-number explicit Book N, and compatible primary-author credit after independently matching all search authors. Known conflict with retained preferred Goodreads evidence holds for review.

### 3. Crash / Stability Safety

Status: Pass. Deferred retry metadata preserves ACTIVE file-recovery states and their proof record. The replacement remains proven/held through native former-file disposal; intent-before-disposal and replay behavior from the preceding release are unchanged.

### 4. Performance

Status: Pass. Unvisited/least-recently-attempted candidates get turns, due dates are durable, and the pass wake has a 30-second minimum. A provider pause no longer returns from the entire candidate batch. Per-candidate request budgets and provider-wide reservations remain enforced by the existing client.

### 5. State & Data Safety

Status: Pass. Native file identity, full byte proof, historical ancestry, no-replace publication, single-link former-file checks and exact-handle disposal are unchanged. Retained findings bind the frozen manifest; evidence age uses the oldest actual receipt and is not renewed by idle postponement.

### 6. Input Handling

Status: Pass. Duplicate JSON fields, malformed props/positions/identity associations and ambiguous matching editions refuse verification. Retained evidence freshness rejects malformed SHA/timestamp data, timezone-free timestamps and future timestamps outside the small clock tolerance. Source-specific numbering provenance is retained instead of merging Goodreads's original #10 with a retailer's shorter #9 sequence.

### 7. Maintainability

Status: Pass. Changes stay in the scheduler, existing research/parser, discovery data and focused tests; no maintenance CLI, constructor bypass or extra worker framework was introduced.

### 8. Doc/Code Drift

Status: Pass. Updated Brief describes actual scheduling, receipt retention, citation identity chain and normal paused-startup live plan. Wikipedia/Ozon/Open Library/local dumps remain research options, not newly implemented automatic ordering authorities.

### 9. Build & Release Hygiene

Status: Pass. Version/lockfile advance together. Actual manifest and installer hashes independently match the header, manifest source_head matches e028fc0, and the three changed packaged production inputs match the reviewed source byte-for-byte.

## Evidence and limits

- Reviewed the accumulated product delta and test source; independently checked final committed artifact bindings. Equivalent source/unpacked module SHA256: series_backfill.py `b16a650bcf95b2b28e894064e6cd7b1b68a027a592bd0dc891d99320020175cc`; public_research.py `cfc6906ac12173c84727d252ad90f1743bb19e3999744d1c484fbebe521fc197`; public_source_leads.json `0993201811aa863e41c08b130525d203df547e698dc6115fd3be5398a6f3a98a`.
- Independently parsed retained Goodreads series HTML locally: it has two SeriesList blocks, Book 1–2 then Book 3–14; book 55108791/work 85913581 occupies index 7 of the second block but its parallel header explicitly says Book 10. Series-level author credit was not accepted as target authorship. Ender's actual-source capture join reports the independently fetched search row binds this exact title and both authors to that same book id. No new provider request was made by Senua.
- Developer test evidence supplied: 10 parser/research cases; 8 scheduler cases; 4 real-media recovery cases (34.905s); 3 restart-filter cases (14.931s); 5 proof/collision/success/held-mutation cases (30.505s); no-series/idle case (6.795s), all passed. These are Ender's runs, not represented as an independent Senua execution.
- During review, one Major freshness defect was found and corrected before commit: repeated idle deferrals renewed the finding timestamp, and observing a nearly expired cached response could grant another seven days. Final code uses oldest actual provider receipt time and preserves age on repeated use. Regression source covers repeated daily busy deferrals beyond seven days, near-expiry cache, malformed evidence, manifest changes, preferred-source conflicts and ACTIVE checkpoint preservation. Open findings: none.
- This report is construction clearance, not a claim that the target's live metadata has already been changed. Live verification follows the normal exclusive app/catalog ownership, genuine paused startup without Start, scheduler eligibility/idle checks and native file proofs. Standard startup reconciliation is authorized; no fake idle or direct metadata override is needed.
- The canonical handoff receipt-read operation was previously denied; it was not rerouted and no canonical receipt is asserted. No broad independent suite, playback check, installer run or live publication was performed by Senua. Futaba's behavior verdict and actual post-install target proof remain independent.

## Scoped reconstructed QA harness review

The earlier session scratch was removed by the user. This is a newly reconstructed fixed smoke, reviewed from its actual current source; it is not claimed to be a byte-exact restoration. Files under `C:/Users/AnGeLZzZ/AppData/Local/Temp/books-codex-20261018/shared/tools` independently hash to:

- smoke-owned.mjs: `b0b6815fd0627252e9e17cfbe7ec652719b47baecff536316b12f7364f764d1a`
- smoke-empty.mjs: `7a615ba16bdf5998535510ffc87d816d5a13e6ca3128ba4b7bc6b530d25e0446`
- smoke-owner-pins.json: `e2d8898ff67d48c1b7f9d32e409fb1984f4c6e857d5e479cad1f926999e67c9c`

Narrow source review is clear for fixed private qa-v0170 version/status/normal Quit smoke only. The helper requires all three explicit empty private roots and fresh catalog/profile/temp/appdata/localappdata, uses hidden/inactive launch, binds its private page and graceful Quit, and never kills by process name/bare PID. The owner validates the fixed complete file inventory, retains native deny-write/delete handles and rehashes inputs before invoking the unchanged canonical runOwned/bounded-child owner. Success requires closed ownership, zero descendants, no unsignaled native processes, no forced termination, no timeout and no output overflow. Actual execution still requires ordinary guard evaluation.

Limitations: canonical ownership-before-release semantics are inherited from the unchanged reviewed route described by Ender, not newly established by running it here. The bootstrap's JavaScript timer cannot preempt a synchronous filesystem read; total-deadline enforcement also depends on host/canonical ownership behavior. Source review is not runtime closure evidence, QA GO or general route enrollment. Failed earlier v0.16.12 scratch smoke/CSP history remains historical evidence and is not promoted to v0.17.0 behavior clearance. Senua launched no smoke and created no disposable probes during this review; session scratch is retained under the standing exception.

## Verdict

- Open Critical: 0
- Open Major: 0 (1 corrected before commit)
- Open Minor: 0

**Verdict:** RELEASE CLEAR
