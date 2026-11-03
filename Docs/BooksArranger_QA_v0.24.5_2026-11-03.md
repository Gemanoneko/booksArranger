# Books Arranger 0.24.5 QA

**Verdict:** NO-GO

Release source commit: 94be5003b1e66cd4d7a4a50afe1ec2b930b1a6cb
Release artifact manifest SHA256: a8acd696647c4a231b5724d5237f2c02fab514bb5aa3e6fc7c9f7a8cea93d9d2

The final package build `c87f0090-7289-4c9b-8eed-eacc948b6d3e` passed packaging and failed its sole full entry. Release is parked. The approved hidden Electron check remains unused.

## Parked final entry failure

The already running check closed at 19:43:24.830Z after 605.264 seconds with exit 1. All 13 Python batches reported 2,344 completed cases, one failure, zero errors and zero skips. The sole failure was ruling 56 at `tests/test_set_release.py:78`, where the private approval job exceeded the fixture's 60-second wait. All 242 Node cases passed, and the frontend emitted no assertion failure. The owned check recorded normal complete zero with 10,873 retained and no force or runner timeout. The failed entry receipt records personal folders clean with two subfolder notes. The original logs, invocation and context were preserved before removing the entire owned `q` folder. [Parked entry failure records](Evidence/v0.24.5_2026-11-03/parked-final-entry-failure/summary.json)

## Corrected candidate full entry failure

The earlier corrected build `e074bf71-d5f4-4d92-b636-581ee4348a71` used fresh context `aec48ae4d730327f0b5d4841ec799dfc6198c0b695abc6d3353410f23638e917` and the verified invocation environment. It completed at 19:27:27.973Z after 635.987 seconds with exit 1. All 13 Python batches reported 2,344 completed cases, two failures and two errors. All 242 Node cases passed. The frontend audio-format hold assertion at `tests/test_todo_holds_frontend.js:144` expected the bare reason and received the “Approval not queued” prefix.

The Python evidence records a 60-second private approval timeout in ruling 56, `updating` where the background recovery update test expected `exiting`, and SQLite WinError 32 during teardown in that test and the web shutdown test. These are observed failure signatures. The owned check closed normally with 10,873 retained and final complete zero. The runner reported no force or timeout. The failed receipt records personal folders clean with one subfolder note. [Corrected failure records](Evidence/v0.24.5_2026-11-03/corrected-build-entry-failure/summary.json)

## Earlier candidate full entry failure

The earlier build was `2c48e76e-0702-45e6-848b-811b7fb6bfa0`, source `7a50f5c50208d6967822dfa8fc296c0910e7a23f`. Two invocations stopped during runner setup before the approved exact invocation reached the full suite.

The exact invocation completed at 19:08:52.753Z after 690.333 seconds with exit 1. All 13 Python batches reported 2,344 completed cases, seven failures and two errors. The 242 Node cases passed. The frontend collision assertion at `tests/test_todo_frontend.js:189` expected the bare message and received the new “Approval not queued” prefix. Ender has the actual failing case list and original output for diagnosis.

The owned check closed normally with 10,871 retained and final complete zero. It reported no force or timeout. The failed receipt records personal folders clean with two subfolder notes. The disposable failed run was removed after preserving its proof. [Actual full entry failure](Evidence/v0.24.5_2026-11-03/full-entry-failure/summary.json)

## Entry ownership failure

The first invocation exited 1 at 18:45:56.019Z after 37.925 seconds. The owned check reported that it could not find the native Koffi module. Its result has no child exit code or native job record and contains zero output bytes. The receipt records `check fail (owned check)` and personal folders clean. The QA runtime copy omitted Koffi's five-file Windows x64 sibling dependency. [Original failure records](Evidence/v0.24.5_2026-11-03/entry-ownership-preflight-failure/files.json)

The corrected private runtime includes the installed `@koromix/koffi-win32-x64` package. The 92-file ownership tree matches the known good digest `a1629fdbc1c73fac1fabd64db245bdd2a12dafe8b93891acce9647dc163f52ad` and loads as Koffi 3.3.2 under the pinned Node. The canonical assembler accepted context `b79fc90b2e21a4a7e5d1a8d694ca152ecbe76896612d59134048d9257b40eb0f` for the same source and artifact.

## Approved replacement environment failure

The approved replacement exited 1 at 18:55:48.761Z after 43.847 seconds. The owned npm process started and closed normally with six retained and final complete zero. My direct invocation omitted the generated wrapper's runtime environment. The runner therefore fell back to the absent `electron-m1/build-cache/runtime/ffmpeg/ffmpeg.exe` before launching the test workers. The final receipt records `check fail (owned check)` and personal folders clean. [Original replacement failure records](Evidence/v0.24.5_2026-11-03/entry-replacement-runtime-failure/files.json)

The exact invocation used all four graph environment values and the successful 0.24.4 invocation's 14 environment keys, with private temporary and profile paths. All 47 media runtime files and the MP3 fixture matched their pins. Koffi, Python, FFmpeg, FFprobe and npm loaded successfully under that environment. Prepared invocation SHA256 is `86b55fe691a49d372e0d860d290f00abe0edbd1700ac33b6637500b57cecbaa0`. The user approved it separately, and its actual full suite failure appears above.

## Focused behavior evidence

- Ender reported 35 approval and action-queue Python checks plus the ruling 35 DOM check passing on the final approval change. These exercise distinct admission, row-specific feedback and response reconciliation with controlled fixtures.
- The Omen evidence records 79 checks passing. The Final Conflict and Armageddon 2000 preview and approval cases cover shared Omen routing, title-year handling and preserved explicit destination choices. [Omen results](Evidence/v0.24.5-omen_2026-11-03/passing-test-summary.json)
- Ender reported 41 update and Quit checks passing after the final pause refinement. These cover the active-work park request, saved pause reason and separate shutdown trigger. Q1 allows uncommitted in-memory approvals to drop on shutdown. The combined evidence covers the changed paths through private fixtures. An installed active-copy session on the user's catalog was outside its scope.
