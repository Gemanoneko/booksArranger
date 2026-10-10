# Books Arranger QA — v0.7.0 — 2026-10-10

**Verdict:** GO

Final candidate-v3 passes the fixed receiver graph: 37 Python tests and two Node commands covering progress, cleanup and metadata frontend routes. Required output/source/payload cleanup governs Converted; empty-folder housekeeping remains separate. Real NTFS named-stream capability is refused safely, so automatic empty-folder removal on the current Z: drive is not delivered by this build. The UI reports retained folders in plain language.

## Exact build and manual handoff

| Binding | Identity |
| --- | --- |
| Target / snapshot VERSION | 0.7.0 / 0.6.0, pending Sully bump |
| Snapshot HEAD / dirty | f7cb9d8fe0062ec15592fd78e21cfb227fb63dc9 / true |
| Baseline | c9617e90bff45c6e56eae2504861f786ef5a4203 |
| Immutable snapshot | scratch/progress-folders-2026-10-10/candidate-v3 |
| Complete first-party manifest | 52 files |
| Source digest | b7e8b35d692202018109c915fb9cb766954f0e541bc22b7b7e188e77f0b3cd46 |
| manifest.json SHA256 | a4773a9dfed840cbed78d2defb07f326a8cd4a48cc6129fc8c7483334b293a67 |
| manual-contract-v3.json SHA256 | e8ff11d3f357b96a5b8090b98adc04319391e44755a07fcd98531ef5fd63cc65 |
| Outer run_qa_v3_owned.py SHA256 | 4e4868f75a099a6b47b016b194c50abd0419ae63602aeeb0855c4a43c6c32234 |
| Inner qa_checks_v3.py SHA256 | 60b140d4859a348d654ff5ddfd43c022cab96fb4bc66607bf1c002bc6245cf0d |
| Actual receiver-check-receipt.json SHA256 | c8f882cf7acc6618f2aafe2b99cb42de2bb0667b290c8612670fa5712d4efd3c |
| Actual owned-launcher-receipt.json SHA256 | 5c5633d1a13bd696f5abe0539438578ae205776e8b91022662d52a29a1102a29 |
| Bound manual-receiver-receipt.json SHA256 | 01fa0fdcbeefff0b622efe4f6229846070e485ce709efcff12ea6e0d9c1e0b7e |

Receipts are under scratch/progress-qa-2026-10-10/. This is an independently executed, separately reviewed Python/manual contract; no formal package checker receipt was fabricated. The sender's earlier component receipts describe their respective snapshots; they are not copied as receiver evidence.

I independently rederived SHA256(JSON.stringify(manifest.files)), verified every manifest size/hash, and checked the complete first-party Python/web/test inventory. Candidate-v1's only unlisted files were its nonexecutable HANDOFF.md and manifest.json. Final v3 preserves that source graph; all 52 immutable source and private-copy files match before/after. All four runtime size/hashes match: Python, bundled Node, FFmpeg and FFprobe. Launcher/inner/contract/manifest pins also match after testing. Reviewed containment native module SHA256: 9939de63b3448e02f0c664d43242fe46e728a2f4f77ad21ed62f0bf98c7fad44; candidate's new native_io.py remains separately source-pinned. No live shared checkout was tested.

## Actual execution and results

Invocation: absolute C:/Python314/python.exe plus the absolute run_qa_v3_owned.py path, no extra arguments, through actual Git Bash. Tests used the exact private copy scratch/progress-qa-2026-10-10/candidate-run. The outer owned Windows job covers identity work and all fixed children from a shared monotonic start; children are suspended until assigned, output is bounded, expiration refuses another child, and exact child/descendant shutdown is awaited. Total hard deadline: 600000ms. Actual outer elapsed: 26.344 seconds. One run only; no timeout, duplicate, failure or skip.

| Declared fixed check | Actual result |
| --- | --- |
| test_progress.py | 7 pass |
| test_merge_service.py | 6 pass |
| test_source_folders.py | 24 pass |
| test_progress_frontend.js | pass |
| test_cleanup_frontend.js, including metadata frontend fixture | pass |

Count method: completed unittest counts in the receiver receipt, 7 + 6 + 24 = 37. Frontend count is two invoked Node commands exercising three routes; it is not a fabricated assertion count. All five child exit codes are zero, no errors/truncated streams, and both inner/outer receipts report passed=true.

## Behavior verified

- Split/malformed FFmpeg measurements, negative values, oversized parser input, bounded pending data, monotonic/clamped progress, absent/zero/nonfinite denominators. A 100-tick private worker fixture confirms measurement updates stay in memory while durable history has one stage entry; interrupted attempts restart with a new identity and no previous numeric progress.
- Actual FFmpeg fixture merge follows the real protected-source/encoder/validation/publication path and succeeds. The pipeline's progress pipe is consumed through the validated callback route. Fixture output is verified; included originals and all staging/recovery payloads are removed; restore is unavailable after successful payload purge; close/reopen reuses the output. All private scratch fixture leaves are absent after the suites.
- Fully approved unqueued membership is eligible; partial/malformed/stale source approvals, changed review revision and changed selected cover are excluded. Actual backend totals admit one completed candidate once even when durable job records repeat. Converted and the counter share the predicate; search and pagination apply; pending/blocked required payload cleanup excludes Converted while the existing created filter remains intact. Source inspection confirms discovery-only rows never enter the metadata-approved candidate query. A fresh multi-book discovery scenario was not separately run beyond these predicate/catalog fixtures.
- Complete payload cleanup counts a book despite absent/checking/needs-attention/unsupported folder housekeeping. Both completed and unsupported folder receipts return without output rehash; replacement content at an already-completed folder path is preserved.
- Real Windows native fixtures preserve hidden files, covers, unselected source files, directory alternate streams, nested Git data, junction targets, changed output/retirement correspondence and replacement originals. Unknown volume/provider/identity capabilities fail closed. A late-added unique directory stream survives even with empty() forced true: the capability check inside actual dispose_empty refuses disposition.
- Positive bottom-up folder deletion, native nonempty atomic refusal, delete-pending behavior and folder crash/intent transitions explicitly simulate a proved streamless provider by mocking require_empty_disposition. They are fixture transition tests on private NTFS paths, not proof that current Z: supports safe deletion. The unmocked NTFS case retains empty source folders, records unsupported with the named-stream reason, and leaves required source/storage completion successful.
- Actual app.js fake-DOM coverage verifies the Converted option's existing-menu position, truthful phase-scoped progress and indeterminate finalizing/validation, zero/unavailable counters, idle state, pause/error labeling, no per-tick aria-live, cleanup success/pending/failure facts, historical retained sources and the approved plain-language retained-folder sentence.

## Findings and dispositions

No open Blocker, Major or Minor in this bounded pass.

| Earlier finding | Disposition and regression |
| --- | --- |
| Senua Major: folder housekeeping wrongly withheld Converted | Fixed in v2 and independently verified by final v3 completion checks with absent/checking/needs-attention folder states |
| Senua Major: terminal folder retries rehashed output | Fixed in v2; final native suite verifies both terminal states with protected_output deliberately failing if called |
| QA Major: v2 unrelated-sibling fixture lost its mock decorator | Reported immediately before full suite; corrected in v3; that exact fixture passes in the receiver's 24 native checks |
| Entry runner: deadline began after identity work | Replaced by reviewed outer/inner shared full-budget guard; final exact pins above |

The v1/v2 full receiver suites were held, never run against an invalid graph or shared tree. Their identities and entry findings remain in scratch/progress-qa-2026-10-10/entry-findings.json. Regression names an immutable dirty snapshot, not a separate fix commit that does not yet exist.

**Pattern alerts:** none.

## Limits and hygiene

No live NAS/library deletion, real conversion enrollment, service restart, current app interaction, browser, desktop focus or other-project work occurred. Native disposition was confined to disposable private fixtures. This is functional/receipt QA; no visual 700/1440-pixel layout, live-user interaction or large real-book timing test was added to the reviewed graph. The current drive's folder retention is an explicit limitation, not a successful removal claim.

Own executable copy, generated bytecode, empty fixture directories and temporary diff inputs were removed after testing. Small manual receipts, logs, identities and entry-findings evidence remain. The immutable candidate and sender's evidence were preserved. This GO certifies exactly candidate-v3 and its reviewed manual graph; any executable delta requires another matching verification.
