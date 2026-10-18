# Books Arranger v0.17.0 — lean isolated packaged smoke

Author: Futaba. Date: 2026-10-18.

**Verdict:** GO

Release source commit: e028fc04c4b30ee26b6960f90948526205acb3ac
Release artifact manifest SHA256: 3797c7d5117abdaf2f1cdd9b5879e7d8b51dfb370d6c9064b4c148f762716584

Installer: `dist/builds/ca0f85ed-aee7-458f-9709-44e9da85ed95/Books-Arranger-Setup-0.17.0.exe`
Installer SHA256: 1c6e17972f9410c818d4e4da82d0c506e8f2552cc15587ba4a33e3fae75272dd
Installer size: 173141509 bytes.

## Scope and artifact binding

This GO covers the authorized lean version/status/normal Quit smoke on a fresh empty private catalog. UI is unchanged; retry regression was not repeated. It does not certify real series backfill, quota/source fallback behavior, per-book deferral fairness, target book #10, output metadata/playability or live release application. Those require the separate developer/review evidence and live acceptance check.

Independently recomputed manifest and installer hashes match above; manifest source_head, version 0.17.0 and build ID match. Extracted the actual installer without installation. All **225/225** payload files match the manifest SHA256 and size, zero mismatches. Tested that extracted payload directly.

At 15:57:57 UTC / 18:57:57 Jerusalem, launched once with `--catalog-mode=new`, private empty data and Audiobooks/Podcasts/Ebooks roots, private profile, APPDATA, LOCALAPPDATA and TEMP; private ports 5213/19227. Used hidden subprocesses and `--show-inactive --quiet-errors`; no focus activation, audio, provider calls, real catalog copy, live controls or real data writes.

The earlier scratch owner had been removed; Ender reconstructed a fixed owner/harness, explicitly not a byte-exact restoration. Senua reviewed the fresh source, complete pins and final artifact before execution. Normal guard accepted the exact transparent command once from session `shared/tools`: `C:/Program Files/nodejs/node.exe ./smoke-owned.mjs --pins-sha e2d8898ff67d48c1b7f9d32e409fb1984f4c6e857d5e479cad1f926999e67c9c`.

The fixed owner hashes/native-holds its inventory and uses the existing private native Job supervisor with a 600000 ms deadline. Total measured 8828 ms, supervised phase 3399 ms. Synchronous bootstrap hashing cannot be preempted by the JavaScript timer; that limitation remains explicit. No canonical qa-handoff receipt is claimed: its prior refused path remains stopped; this lean pass uses independent artifact binding and actual results, not an invented receipt.

## Measured results

| Check | Result |
|---|---|
| Backend version | PASS: private health reports Books Arranger 0.17.0, port 5213, closing false. |
| Empty status | PASS: state version 0.17.0, automatic Idle, jobs Completed, zero queued. |
| Shipped renderer | PASS: badge v0.17.0 and Quit Books Arranger control present. |
| Normal Quit | PASS: clicked the shipped UI Quit handler; shell exit code 0, no signal, 493 ms after request. No force termination. |
| Process/port release | PASS: private ports absent; private Job closed true, active 0, retained 15, unsignaled 0, zero true; no timeout, force, overflow, closure error or retained owned process. |
| Real catalog/library observation | PASS: read-only before/after fingerprints unchanged, below. |

## Real-data read-only fingerprints

No database connection or copy was made. Around the smoke, real inventory.sqlite3 retained device 133335364132330000, inode 69805794224273076, size 535433216 bytes, mtime_ns 1792338956105841900 and SHA256 **803e96f2c39ed428e8f982ec5c204bbbbe4e22832af9b6401504032c02ee5561**.

Z:/Audiobooks remained 8890 files, 758 directories, 740431193976 bytes; identical name/size/mtime digest **25f250368c96db560d9abc45ad3e9edaf85511be313c5e0e366303b4539d9d4b**. Source-recovery remains zero files/three directories; replacement-recovery zero files/zero directories; both empty-file digests unchanged. No fingerprint errors. These measurements establish unchanged observed files around this run, not a database consistency or output-content audit.

## Findings, patterns and limitations

No observed blocker within the requested smoke. No product fixes made by QA.

Pattern alerts: no new alert. Carried dispositions: **defer** real-catalog-copy launches because historical cleanup entries can reach real Z: paths; **accept** explicitly attributed live fingerprint drift when concurrent processing changes data. Final fingerprints here were identical.

Not covered: provider research/network quotas, scheduling/defer fairness, proof retention until genuine idle, real conversions/recovery/target #10 verification, media tags/full output hash, installer/updater, tray/Alt+F4/all error screens, retries, load/performance, light theme/small widths. Developer focused tests and Senua construction review remain separate evidence; the live target check belongs to the release owner. Native process closure does not imply full system isolation.

## Evidence and hygiene

Evidence root: `C:/Users/AnGeLZzZ/AppData/Local/Temp/books-codex-20261018/shared/qa-v0170/evidence/`: payload-binding.json, extract-installer.log, result-empty.json, native-smoke-closure.json, shell logs, real-before.json/real-after.json and UTF-8 full entry lists, catalog-before.json/catalog-after.json. Reviewed scratch owner, harness and pins are in sibling `shared/tools/`.

No session scratch deletion per Sergei's instruction. No repository throwaways; this report is the sole tracked QA deliverable. Scratch for Sergei to delete later: `C:/Users/AnGeLZzZ/AppData/Local/Temp/books-codex-20261018`.
