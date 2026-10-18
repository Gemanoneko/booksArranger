# Books Arranger v0.16.12 — lean isolated packaged smoke

Author: Futaba. Date: 2026-10-18.

**Verdict:** GO

Scope: the requested empty-catalog packaged smoke only. This accepts version/status, the attention strip, Retry selected confirmation/cancel, and owned-process Quit. No real catalog was copied or opened by QA; no live library writes, installation, live-app shutdown or processing were performed. This is not verification of real series backfill, playable rewritten books, crash recovery on real files, actual Retry execution, or the later live apply.

Release source commit: 4aff68677851448f9f51f27d522e1094941ddd3e
Release artifact manifest SHA256: 334de7d785a30aa57285d61468f52a885cdd101eb9ca34d4b03bde94144741bf

Artifact: `dist/builds/d7fce1bd-d21b-40c0-ad11-136b30588ae2/Books-Arranger-Setup-0.16.12.exe`.
Installer SHA256: f18300fb13ef86cbc573fee0c56f41eb331adb5951f334df2e8b34973628221d

## Binding and method

Independently recomputed installer and manifest hashes match the identities above. Manifest version is 0.16.12, source_head matches the committed source, build_id is d7fce1bd-d21b-40c0-ad11-136b30588ae2. Extracted the installer without installing it: all **225/225** payload files match manifest SHA256 and size; zero mismatches. The tested payload was copied from that verified extraction into private scratch.

One launch at 14:48:52 UTC (17:48:52 Jerusalem), after Senua's source/artifact and scratch-owner reviews. Fresh empty private catalog with `--catalog-mode=new`; private empty Audiobooks/Podcasts/Ebooks roots; private shell profile, APPDATA, LOCALAPPDATA and TEMP; private ports 5213/19227. Used `--show-inactive --quiet-errors`, hidden subprocesses and no audio or foreground activation. Synthetic state modifies renderer memory only; selected synthetic row confirmation was canceled before any action request.

Exact reviewed owner invocation from session `shared/tools`: pinned `C:/Program Files/nodejs/node.exe ./smoke-owned.mjs --pins-sha 96e95bd5ae83b7c3ba9cb80683130411bb68b00af1eb41837bd223dd118502eb`. Normal guard accepted it. The fixed owner verifies and holds payload/harness/runtime/native inputs and uses a private native Job. Its supervised phase has a 600000 ms deadline; synchronous bootstrap hashing is not preemptible by the JavaScript timer. Measured total 35,874 ms, supervised phase 30,685 ms.

No canonical qa-handoff receipt exists: the canonical checker read was rejected by the command guard's P9 filename rule, and that path was stopped. This report does not invent sender/receiver receipt evidence. The explicitly requested lean scope uses independent artifact binding and measured packaged behavior. Ender's focused 17-test and held-race results are developer evidence, not tests rerun or certified here.

## Measured results

| Check | Result |
|---|---|
| Version | PASS: backend health and window badge 0.16.12; first health after 1,189 ms. |
| Status | PASS on empty catalog: automatic Idle, zero approved/converted/queued/attention, Nothing running. Twelve state requests returned 200; p50 4 ms, maximum 7 ms. Subsequent health requests 2–12 ms. |
| Attention strip | PASS with synthetic payload: All 9, retry 5, repair 2, other 1, unsupported 1. Retry all hidden in All view and visible after retry filter. Zero control overlaps; scroll width equals client width (1251 px). Screenshot visually inspected. |
| Held activity | PASS with synthetic payload: held reason shown, progress hidden, elapsed text empty across reads 2.5 seconds apart; running activity retains 30% progress and elapsed text. Zero row/panel overlaps. |
| Retry selected | PASS: visible `Retry selected (0)` disabled on empty selection; ordinary Queue hidden. One synthetic retryable row enables `Retry selected (1)`, opens confirmation, and cancels successfully. Zero real retry/repair requests; row/selection restored immediately. Actual enqueue and Queued persistence remain outside this smoke. |
| Quit/process closure | PASS: hit-tested UI Quit click; shell exit 0 after 526 ms. Private ports gone. Native Job closure: active 0, retained 29, unsignaled 0, zero true, closed true; no force, timeout, overflow or retained owned process. Original Books Arranger process set unchanged; live port 5210 stayed PID 18260. One unrelated Python PID disappeared; native ownership proves all QA descendants closed. Zero etilqs files before/after. |
| Real recovery folders | PASS unchanged: source-recovery 0 files/3 directories; replacement-recovery 0 files/0 directories; both empty-file digests identical before/after. |
| Real catalog and library observation | Identity preserved; contents changed during the live conversion, described below. No claim of an unchanged real-catalog hash. |

## Read-only real-data observations

Before/after read-only fingerprints were taken around the run, without a database connection, catalog copy or requests to the live engine. Real inventory.sqlite3 retained device 133335364132330000, inode 69805794224273076 and size 533,569,536 bytes. Its SHA256 changed from `07a7c990a2c38ba134e24d98052cf57e92e3adcdadb55947a8bf5bf7e26a11dc` to `16586fcf6017e0477039576c0bedbb0583d6ec4292aa6d65b8dbce6a67f46c10`; active WAL/SHM existed before QA. A live mutable file hash is not a consistent database snapshot.

Z:/Audiobooks remained 8,891 files, 757 directories, 741,020,539,180 bytes. Exactly one fingerprint entry changed: a Books Arranger `.partial` under `Sawyer Robert J` became `Неандертальский параллакс. Гоминиды - Sawyer Robert J.m4b`, with identical 642,820,798-byte size and modification time. This is consistent with the already-running live engine publishing its book. The isolated engine had an empty catalog, private empty roots and no real paths; it made no action requests. Therefore this drift is attributed to concurrent live processing, not reported as unchanged. No content hash/playability check of that book was performed.

## Findings, patterns and limitations

No observed build behavior blocker in this focused smoke.

Pattern alerts: two carried, with explicit disposition. **Defer** real-catalog-copy testing: historical held-cleanup entries can reach real Z: paths, so only an empty catalog was launched; real backfill/recovery behavior remains for the separately authorized live watch. **Accept** normal live fingerprint drift with attribution and preserved evidence; do not retry until a coincidentally identical pair or mislabel a changing database unchanged.

Not covered: NSIS installation, updater, tray/Alt+F4 behavior, all startup/error screens, smaller widths/light theme, actual real Retry/Repair jobs, network series matching, conversion or rewritten-output playability. Series crash/recovery correctness rests on Senua's separate review and Ender's focused tests, not this empty-catalog behavior pass.

## Evidence and hygiene

Evidence root: `C:/Users/AnGeLZzZ/AppData/Local/Temp/books-codex-20261018/shared/qa-v01612/evidence/`: `payload-binding.json`, `result-empty.json`, `native-smoke-closure.json`, `strip-synthetic.png`, `jobs-synthetic.png`, shell logs, extraction log, `real-before.json`/`real-after.json` and full `.lines.txt` lists, `catalog-before.json`/`catalog-after.json`. Scratch harness/owner/pins are in sibling `shared/tools/`.

No session scratch cleanup, per Sergei's instruction. No repository throwaways created; this report is the only tracked QA deliverable. Session scratch retained for Sergei to delete: `C:/Users/AnGeLZzZ/AppData/Local/Temp/books-codex-20261018`.
