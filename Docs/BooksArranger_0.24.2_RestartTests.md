# Books Arranger 0.24.2 — Start over regression tests

Status: authored; not executed. Production Start over source is owned by the lead developer and is still being finalized. No restart-1 snapshot or invocation has been prepared or admitted. Parent requested this handoff to free the review slot.

## Changed files

- tests/test_restart_242.py: 17 new methods, private SQLite catalogs and tiny synthetic source bytes.
- tests/test_start_over.py: existing 32 methods, self-contained fixture fixes.
- This note only. No production source changed in this slice.

## m8 fixture root causes

The old Base fixture supplied no separate sorted output folder, so the real Start prerequisite refused it. It now creates a private sibling sorted folder and supplies inventory.output_root. Five pending-start fixture paths used Running as a conversion blocker, although ruling 34 permits Start during Running and only Pausing blocks it; these inputs now use Pausing. Production output and start predicates are not mocked. The route fixture no longer borrows another test module's methods or imports that module. Its local Handler/BrowserServer objects use BytesIO; no sockets or app are started. Existing patches remain test-scoped with registered cleanup. AREA creation moved from module import into setUp.

## New regression coverage

The exact accepted review returns to automatic processing while the original job row, manifest, hash and journal remain unchanged; track order, included members, cover choice, manual note and custom destination context survive. Stale metadata proofs and source hashes are cleared. A genuinely edited title, note, cover, order, manual-draft flag or active editing lease remains held.

Restart binding is checked against candidate ID, revision, fingerprint and review. A missing automatic record is created Pending with immediate source_refresh_required; an old 300-second retry and reasons are removed while research history stays.

The real Inventory.refresh_candidate_sources updates only private observed files, and AutomaticProcessing._refresh_observed_sources rebases retained choices to the resulting revision/fingerprint. Tests reject absent/wrong restart authority, wrong paths, unrelated durable work on a member, a newer same-candidate job, publication intent/output/cleanup evidence, changed saved choices and changed candidate revision during rebase. Cancellation reads no source bytes; an ordinary unchanged candidate requests no forced refresh.

The new fixture invokes the real MergeService.start_over transaction. Its precomputed attention offer is a Mock (the existing six 75b tests still exercise actual changed-source offer checks); its automatic request_start is a Mock, so new tests do not run discovery, research or conversion. It uses real SQLite, grouping and native verified-file refresh on generated fixture bytes, with an injected metadata reader. Existing standalone tests use bounded threads and private catalog fixtures; they exercise callbacks, Cancel, Stop and Quit through doubles, no real desktop launch.

## Run handoff

Expected authored counts: test_start_over 32; test_restart_242 17; total 49, zero skips expected. Run test_start_over before importing/running the new module to demonstrate its standalone fixture independence. No test pass is claimed. git diff --check on the owned test paths passed (normal LF/CRLF notice).

Prepare a NEW restart-1 batch from the fresh frozen root Python sources, these two tests and any actually reached support files only. Reuse the exact previously admitted installed-Node fixed-driver/runOwned bootstrap pattern, source/runtime/ownership/helper pins, literal environment, whole-controller 600000 ms hard deadline and owned closure. Declare actual test graph: SQLite and generated fixture I/O, native file guards and bounded Python threads are exercised, so this is not a pure in-memory batch. No network, subprocess, codec, app endpoint, real media/library, install, tray or UI operation is intended. Separate Senua admission is required before execution. No changes to shared runtime or ownership dependencies.

Prior slices: routing-1 passed 45 tests. Lead reports series-1 passed 19 tests, zero skips, outer exit 0 and native closure complete/zero with postflight pins; these results do not validate the new restart slice.
