# Books Arranger 0.24.5 QA — corrected build r2

**Verdict:** NO-GO

Release source commit: cc5ea7f9deb3b2843cb75b1392e24314532a0f2a
Release artifact manifest SHA256: 233f2a17919e596a63a16a7661df7ce2c5972b65a84f8c1823aeaacee9a8c1dc

Build `3369d944-a8e3-4513-a758-5e006309cf9b`, product digest `749eee7ece79f60b4236cdfc6481bcf5d16595b0a88009fb5df596321cc0380f`, was pinned in a clean release worktree. The one authorized new-build full entry ran once with schema 3 context SHA256 `d69afc8c0240ea4a80ac8353f0a2ff6db7775f6b135090d6e35b4128ec0cc0f3`, 900000 ms work deadline and 930000 ms transport deadline. It ran from 2026-11-04 07:26:51.640Z to 07:37:05.658Z (614.018 seconds) and exited 1, within both bounds. No second full entry was run on this build.

The owned check exited 1 and closed normally: `closed=true`, `outputComplete=true`, `forced=false`, `timedOut=false`, native `complete=true`, `zero=true`, active 0, assigned 0 and unsignaled 0. All 242 Node tests passed. The 13 Python batches ran 2,352 tests; 12 batches passed and one reported one failure. `test_set_release.SetReleaseTests.test_ruling_56_an_approve_leaves_unrelated_paused_jobs_pending_until_start` exceeded its 60-second private Approve job wait at `tests/test_set_release.py:78` / `tests/test_approve_as_is.py:45`. This is a **Major** QA gate failure. The exact full-load cause is not established. The web and SQLite teardown cases passed this time. [Raw r2 entry evidence](Evidence/v0.24.5_2026-11-04/new-build-r2-full-entry-failure/summary.json)

Independent focused verification on the exact committed `cc5ea7f` source passed 79/79 cases under the native owner: web, startup published checks, status snapshot, folder regroup, request spacing and prior/current producer continuation. Owner closure was complete and native zero. The 1,320 archived source files were hash-identical before and after. This focused result does not override the failed full entry. [Focused evidence](Evidence/v0.24.5_2026-11-04/futaba-focused-cc5ea7f/summary.json)

The approved hidden 0.24.5 check remains unused, as do packaged app launch/close and native private closure gates downstream of full entry. The repeat-on-same-build approval has not been given. Ender has the exact failure for diagnosis. The prior build `27b521b3` on source `f6553e7` failed its one full entry on SQLite `WinError 32` during web teardown; its raw record remains [here](Evidence/v0.24.5_2026-11-04/new-build-full-entry-failure/summary.json). The [pattern alert](BooksArranger_QAPatternAlert_v0.24.5_2026-11-03.md) tracks that recurring earlier signature with disposition **fix**.

Actual Futaba receipt:

> Entry-check receipt v2: books-arranger v0.24.5 @ cc5ea7f9deb3b2843cb75b1392e24314532a0f2a (dirty: N) [source:7d46961cb5eca3742392b6bbf0565150ae54a1a52e2404701b073c8a513a301f; harness:9b22b0d8f2bbf0e97479aa66c1baadc730f20c1adfda441f59fea31130f8e6b4; runtime:184635bb7ec812008517fba764778ffcd9b6b293fb75401dd44d8c3bdaff04a0; checker:4bae2cde4e4cdd2f22fb3060571730ec32fec1dd5403ea070086973b18b695e4] — pre-qa n/a, post-build n/a, check-electron n/a, check fail (owned check), test:smoke n/a; personal-folders clean (1 subfolder note)
