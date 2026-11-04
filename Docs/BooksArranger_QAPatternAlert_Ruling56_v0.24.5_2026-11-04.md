# Books Arranger 0.24.5 QA pattern alert — ruling 56 private job wait

**Pattern:** Two separate full entry builds have failed `test_set_release.SetReleaseTests.test_ruling_56_an_approve_leaves_unrelated_paused_jobs_pending_until_start` at its 60-second private Approve job wait. The `94be500` build failed its initial full entry, passed the separately approved same-build repeat, and passed Ender's focused isolation and contention probes. The new `cc5ea7f` build failed its one authorized full entry at the same assertion. The new entry's other 12 Python batches and all 242 Node tests passed; its owner closed with native complete zero.

**Evidence:** [Earlier source and repeat](BooksArranger_QA_v0.24.5_2026-11-03.md); [new r2 full entry](Evidence/v0.24.5_2026-11-04/new-build-r2-full-entry-failure/summary.json). The full-load cause is not established by these results.

**Disposition:** **Fix.** Ender owns diagnosis and a correction or proof of the underlying full-load condition. Futaba will verify a committed correction or pinned snapshot. This alert grants no same-build full repeat, hidden check or release clearance.

**Release verification:** Ender's process-local primary-thread recovery in `bf4425d` removes the global thread scan on each owned media launch. Futaba independently passed the full lifecycle module and SetRelease class, 47/47 including ruling 56 and 57. The final build's one full entry passed 2,360 Python tests across all 13 batches and all 242 Node tests, with ruling 56 included. Disposition for this release: **fix verified**. A single passing full load does not establish a statistical guarantee against future timing variation. [Final full entry](Evidence/v0.24.5_2026-11-04/new-build-r3-full-entry-pass/summary.json).
