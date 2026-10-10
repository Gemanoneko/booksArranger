# Books Arranger QA — recovery retention v0.8.0

Date: 2026-10-10. Futaba independent QA.

**Verdict: GO** for the frozen candidate described below. No live-library or production recovery deletion was performed.

## Exact build and handoff

Base HEAD: `41119fb063bc895a12b78459b7424b5d7ac17643`. Target version: 0.8.0 (candidate retains base VERSION pending Sully's marker-only bump).

Manifest: `scratch/recovery-retention-2026-10-10/manifest-frozen-2.json`; SHA-256 `4cd2099b00860704fe88394c31719c1da18851e15e355c0218e8a86e4df198da`. Complete raw source pins verified before and after testing. Subsequent implementation drift invalidates this report.

Entry check: MANUAL Python no package.json: scoped pinned native fixture contract; package-based entry checker not applicable. The qa-handoff skill explicitly excludes prototype smoke testing and its package checker does not accept this non-package tool; no automated formal receipt is claimed. Ender's identical manual classification accompanies the frozen handoff. Python `C:\Python314\python.exe`; Node `C:\Program Files\nodejs\node.EXE`.

## Behavior checked

35 distinct Python cases passed: 12 recovery-retention, 13 HTTP, 7 progress/completion, and 3 independently authored native fixture cases. Three frontend routes passed: recovery, cleanup, progress; a fourth independent contract route passed against freeze 2. The independent harness inadvertently collected ten imported cases again; these repeats are excluded from the distinct count.

Verified exact 86,400-second boundary, stored deadline surviving restart, immediate working-stage cleanup with retained backups, mutable status timestamps unable to extend expiry, startup idle worker and joined shutdown, busy scan/queue admission, manual stale scope and duplicate exclusion, crash intent reconciliation and partial-purge restart, unknown content/replacement preservation, incomplete source removal and changed output blocking purge. Completed books still satisfy the converted predicate while recovery is intentionally retained. Independent cases additionally proved backward wall-clock deferral, newly arrived same-name original preservation, and unchanged completed-output SHA-256 after manual and exact-expiry purge.

The first HTTP/progress invocations used the QA parent working directory and failed imports before product execution. Corrected private-copy invocations passed. The first browser harness path mishandled URL-encoded spaces and returned 404; corrected QA-only harness passed. These were harness setup errors, not product bugs.

## Rendered UI and limits

An owned headless browser rendered the actual frozen HTML/CSS/JavaScript against a static private response fixture at 1440, 700 and 350 CSS-pixel widths. The dialog fit without horizontal overflow, including long Russian title/path; screenshots and rectangles retained in `scratch/recovery-retention-qa-2026-10-10/`. Cancel received initial focus; Enter cancelled without an API request, Tab/Shift+Tab stayed in the dialog, Escape closed and returned focus to the initiating action. Attention disabled the manual button. VM frontend cases also verified expiry/deleting/deleted/disconnected states, immutable displayed scope, polling focus preservation, changed scope cancellation, single guarded submission, unknown values and selection clearing.

Browser lease `c65edc954ba4` closed with remaining process count zero. The prior failed setup lease `b5e34223a6c8` also closed with zero remaining. No native app, Explorer, audio playback or user's browser was touched. No complete live-library scan, bulk hashes or AAC decode ran. UI fixtures establish rendering/keyboard behavior; backend fixtures establish deletion guards. Actual live retained backups were not available for a production purge test. 200% browser zoom and independent contrast measurement were not covered; narrow 350px reflow was checked.

## Findings and cleanup

Blocker: 0. Major: 0. Minor: 0. Pattern alerts: none. Release GO remains conditional on Senua's separate construction verdict and matching deployed source. QA fixture temporary directories self-cleaned; browser leases ended. Unique screenshots, harnesses and pin evidence are preserved. No recovery copies or library originals were treated as disposable test output.

## Freeze 2 focused recheck

Manifest comparison proved exactly three changed files: README.md, web/app.js and tests/test_recovery_frontend.js; all backend and layout pins are unchanged. Carried freeze-1 behavioral and rendered-layout evidence remains applicable. README now consistently distinguishes immediate working-copy disposal from 24-hour original-track recovery retention. The recovery frontend route passed again with retained-busy waiting copy.

A real contract gap found before release was corrected: CandidateReviewService supplies `creation.job.job_id`, rather than the synthetic fixture's top-level `creation.job_id`. Independent inspection of review_backend.py confirmed that actual response shape. A separate private VM fixture mirrored it, verified the manual action is enabled for eligible copies and submits exactly `backend-real-job` with the observed token/count/bytes, and proved missing job identity cannot submit. Retained copies blocked by an active scan remain a waiting state rather than falsely needing attention. Initial independent harness used `busy`, colliding with the app's lexical variable; renaming that QA-only fixture binding produced PASS. This was a harness failure, not a product regression. No full backend graph was rerun for the frontend-only delta.
