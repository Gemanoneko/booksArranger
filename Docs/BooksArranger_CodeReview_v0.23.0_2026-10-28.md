# Code Review — Books Arranger v0.23.0

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-10-28
Tool: Books Arranger (Electron desktop utility)
Release: v0.23.0
Commit range: 8057ab4e8d39ed9cd3aab7ff605d13fcf7501686..d115eeda816d275a22b57616e955850443ea06e0
Baseline: v0.22.3 (peeled release commit)
Files changed: 31 files, +1047 / -77
Stand-down dimensions: none
```

Release source commit: d115eeda816d275a22b57616e955850443ea06e0

Release artifact manifest SHA256: 36d601be44289817ca2fe8082087d5e2ae6f9165cc3804851ee21630b4e54f9c

Build UUID: `1d72e68b-d159-4439-ae75-3c6592d48419`. Installer: `dist/builds/1d72e68b-d159-4439-ae75-3c6592d48419/Books-Arranger-Setup-0.23.0.exe`, 174263993 bytes; SHA256 `d2559b462ac705c01dd438f96c7533218220232faff0979f1c2bb3595958f4e9`. Product digest: `a110e75ec3034070d8951cb718c39e315c25b32a324ecd8c65ff6644f3b5b6ff`. Full 296-file payload-map SHA256: `ffa23c062cf078677cb2368afc7c15aa99882f22142fbe584df86e55b6488c3e`.

## Summary

Reviewed the accumulated release delta through the final picker fix: one inline Author/Title/Series/Number draft and approval, typed saved-but-series-needed results, optional canonical Litres evidence, confirmed anthology membership and credited chapters, exact four Horror volume names and concise paths, and the explicitly authorized 13-worker gate. Static follow-ups certify the final commit; previous 0.22.3 findings retain their recorded dispositions rather than being silently reopened or erased. No product edits, full-suite reruns, native app launches or registry operations were performed by this reviewer.

## Rubric

Severity definitions and safety floor: `Team/Docs/ProcessRules.md`, Severity definitions.

### 1. Security

Pass — Litres admits bounded query-free canonical HTTPS book URLs through existing transport/cache/pacing; no new credentials, shell interpolation, IPC or Electron-security changes. Native smoke uses private payload/profile/roots and the canonical owned Job.

### 2. Correctness & Logic

Pass — Complete title/all-author/explicit-ordinal Litres evidence excludes readBy/related products; existing source precedence and manual answers win. Inline draft preserves R49/R56/R57/R59 controls. Named anthology rules re-prove all members, preserve protected/completed/GONE claims and hold unknown order; generic mixed-author grouping remains guarded.

### 3. Crash / Stability Safety

Pass — Closed finding CR23-M1 at `web/app.js:3983`: the new saved-result announcement dereferenced an absent queued book row. Final code uses the queued title/Book fallback, retains the neutral receipt and acknowledges the outcome. Focused missing-row regression passed. Direct HTTP and queued typed outcomes preserve unrelated error handling.

### 4. Performance

Pass — Sergei expressly approved 13 workers after the nine-worker gate exhausted capacity. All 119 patterns and 1959 required occurrences, ten serial server modules, complementary class halves and declared order remain. Worker/inner/owner limits stay 540/580/600 seconds; output cap and positive closure remain. Final measured slowest worker is 484.8 seconds; historical weight estimates were never treated as guaranteed capacity.

### 5. State & Data Safety

Pass — Human Approve queues without starting/resuming unrelated work; answers remain per book. Regrouping does not inherit per-story approval/manual evidence or consume an unprotected partial volume. Exact-family filename exception preserves explicit/custom titles and ordinary series behavior. Native cleanup deletes only its verified own leaf through the same validated DELETE handle; shared root/history are never written.

### 6. Input Handling

Pass — Paired Series/Number validation, intentional clearing, untouched Title/author omission and shared expanded-editor state remain. Reused Series now links to the existing datalist after the editor opens/loads; the original failing assertion passed unchanged. No duplicated controls or added focus movement.

### 7. Maintainability

Pass — Two small pure evidence/membership modules contain the new exceptions; shared queue machinery is unchanged. Proposed process-global MP3 fixture cache was dropped completely after its measured benefit did not establish capacity; no unvalidated cache optimization ships.

### 8. Doc/Code Drift

Pass — Brief/backlog/UX specifications describe scope and actual proof limitations, including the saved answer and full-editor pick-list. The old next-Start instruction was corrected. Prior deferred Minor backlog remains outside this delta; no new Minor finding is opened here.

### 9. Build & Release Hygiene

Pass — Clean final source, synchronized version/lockfile and actual passing entry bind the accepted installer. Independently verified all 296 unpacked payload files/no extras/links, three artifacts, source/runtime/owner pins and manifest. Builder independently verified NSIS/full-payload equivalence and shell/backend 0.23.0. All 47 qualified media files match; the sole additional runtime item `resources/ffmpeg/BUILD.txt` is exactly 3761 bytes, SHA256 `feda03f314046e9c4cfe658097cdd6223e216ac457b21f34c06d79f1698f6633`, generated provenance text from pinned FFmpeg JSON/version/license by unchanged `build_phase.prepare`, not an ignored executable addition.

## Actual verification and limits

Final r5: **1959 Python cases, 143 Node cases, 34 frontend scripts and 10 syntax files passed**, zero failures/errors/skips. Owned wall 498.315 seconds, closed/native zero. Context SHA256 `2adeccebe0d604bb51f5682a5057ef03c76b10bea328208de773a9940f156789`; wrapper SHA256 `19fe5ad2b397cd6fcba6d11063cb7710ad9e7000515d29422341358cd783b58c`. Exact receipt is retained at `q230/r5/logs/entry-check-receipt.txt`. Earlier r3 deadline/path-fixture failure and r4 frontend failure remain failures in preserved evidence; no external-load-only explanation is asserted.

The single guarded build passed in 76.933 seconds with both outer owner/native zero and inner native build closure. Process-only private cache paths kept packaging out of Sergei's profile. No install/publish occurred during verification.

Futaba's packaged backend/DOM delta passed in 14.138 seconds, including one actual conversion/decode, exact source/planner cases and saved-result controls. Synthetic DOM/HTTP doubles are distinguished from the native renderer. The retained successful RPC/output trace supports the measured claims; the frontend driver was reconstructed after a future-only pre-Approve assertion was added, with no contemporaneous driver hash. That limitation is accepted explicitly: the later assertion is not claimed as executed. No conversion or full suite was repeated to obscure it. Litres's first guarded request paused normally; a later single guarded request after normal cooldown returned HTTP 200 and supplied actual book evidence. QA made no additional provider request.

## Native smoke and explicit cleanup exception

One reviewed hidden packaged-app run passed displayed/engine 0.23.0, close-window hides while the engine remains alive, normal Quit, unchanged payload and no intrusion; owned closure/native zero in 6.672 seconds. **The raw strict smoke result remains FAIL/code 1**, because Windows changed the shared tray root. The smoke helper has an explicit fresh-consent guard before owned activity and contains no registry mutation.

Offline comparison proved only one new private EXE leaf, ID `15104638555172490743`, and an eight-byte uint64 prefix in UIOrderList (1904 to 1912 bytes). All prior child records, other root values and remaining bytes/order were unchanged. Sergei expressly authorized the 0.23.0-only exception: “Yes—use the same cleanup for0.23.0”, question `call_934943a029bf4048869be615ba6cb613`: delete this temporary leaf and retain one numeric eight-byte Windows reference containing no name/path.

Separately reviewed same-open-handle cleanup **PASS**: 1.028 seconds, exit 0, closed/native zero, exact copied EXE/no subkeys, own leaf absent afterward, CURRENT UIOrderList and every other record unchanged; `rootWritten=false`, `uiOrderWritten=false`. No app rerun, shared-value restoration, recursive path deletion or TxR repair. This is functional smoke plus separately authorized cleanup/exception completion, not a relabeling of the original raw guard failure.

Exact smoke helper SHA256 `1274717e378060fb8fc79892893f3547090f78062f5eda2ac26d8088f3ae0297`; active plan `e048d26cd812b3cad5499b042b7ed64da29fabd323f825bc693355be82a80499`. Cleanup helper `29395c329ff1a2be16190fb706f0cfa2512e2d0207b9cecede00cfbc640ee5d5`; executed plan `2dedeb9c6691f8ea12e8ce50784efa5f4d1a55de3cf7db1b6d1974a0fc7d0bfc`. Raw smoke receipt `q230/logs/hidden-package-smoke-result.json` SHA256 `05f4f2378e9b35a6cb1df4776c7a5a165aab841b265002b44ad54141296cc258`; cleanup receipt `q230/logs/owned-tray-leaf-023-0feb92cea243208ca090ee9d1743ea25-delete.json` SHA256 `78ff88145fcab7b254c05c718529bf0f69ad010ac0323409e0ce72f448bd1af9`.

Reviewer created no disposable probes or private registry exports in this release pass. Active evidence remains in the owned q230 workspace until accepted promotion/curation; routine final cleanup belongs to the coordinated handoff. Raw registry values must not be committed.

## Frozen acceptance evidence

Durable compact native proof: `Docs/BooksArranger_NativeSmokeProvenance_v0.23.0_2026-10-28.json`, SHA256 `99ec607a4fafec4faa97b8ef6733f60dd9367ed0cc5f3a6c3808283c795ffb4d`. The two archived executed LF helper sources match the smoke/cleanup hashes above exactly; historical provenance remains intact. No raw whole-registry exports or unrelated private records are archived.

Futaba's final `Docs/BooksArranger_QA_v0.23.0_2026-10-28.md` is GO for the identical source/manifest, SHA256 `2a80667478171de6337b257f9f9ddb88fa503a1dfda7ad3e616845c33bd51427`. Acceptance schema `books-desktop-acceptance-v1` names version 0.23.0 and these exact QA/review report paths. Promotion must preserve the accepted source, installer, manifest and proof identities; no additional source/build/test/native work is required for this clearance.

## Verdict

- Open Critical: 0; safety floor intact.
- Open Major in this delta: 0; CR23-M1 closed.
- New Minor in this delta: 0; earlier deferred backlog retains prior dispositions.

**Verdict:** RELEASE CLEAR
