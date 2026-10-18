# Books Arranger v0.18.0 — lean packaged QA

Author: Futaba. Date: 2026-10-18.

**Verdict:** GO

Release source commit: 902d3128943544ec07772fa489e94b9559ca126d
Release artifact manifest SHA256: b52be300dd46351d5ca9bb72913df6185298e5ddc32483e714696770654b9940

Installer: `dist/builds/817dc432-53b9-4834-b280-cb266a742482/Books-Arranger-Setup-0.18.0.exe`
Installer SHA256: 60a92a45905a5aa35b8d28272648b892139a434ab83236ed6157afeea195e98d
Installer size: 173192412 bytes.

## Scope and binding

GO covers the requested private empty-catalog version/status/Quit smoke and exact artifact binding. Real local-index activation/coverage and the later installed-live target #10 check remain separate acceptance work. No real catalog copy/connection, real job/library mutation, provider requests, partial Editions read, installation or live controls by QA.

Independently recomputed installer and manifest hashes match above; source_head, version and build ID match the candidate. Extracted the actual installer without installing it: **229/229** payload files match manifest SHA256 and size, zero mismatches. The extracted payload was tested directly. Senua independently reviewed the exact packaged production modules and complete execution pin inventory.

The earlier scratch sources were missing. This is a newly reconstructed fixed-scope QA runner, not a byte-exact restoration or canonical receipt framework. Owner SHA256 `a10ee03c8569600ba1288d9691582eca817225469e6ab0a480009cc8eb46c9b0`; helper SHA256 `d905f2f7befbbe3ddc5a7c1505bde76e0a6c7f5ee675ef43574c379ac9520a89`. Both syntax checks passed; Senua reviewed full source and then the final 327-file pins with zero mismatches before execution.

Normal guard accepted this exact command once from session `shared/tools`: `C:/Program Files/nodejs/node.exe ./smoke-owned.mjs --pins-sha aac65fa630e33f88516a1629df3642058c12912385d9c10231edc8c847449170`.

Runner hashes/native-holds exact input files before/after and uses existing runOwned private native Job supervision with a 600000 ms deadline. Total 9822 ms; supervised phase 3858 ms. Synchronous bootstrap hashing cannot be preempted by the JavaScript timer; inherited limitation retained. No canonical qa-handoff receipt is claimed: its refused path remains stopped. Independent binding and measured behavior are the lean evidence here.

## Actual packaged behavior

One launch at 17:24:45 UTC / 20:24:45 Jerusalem. Fresh private empty catalog with `--catalog-mode=new`, private empty Audiobooks/Podcasts/Ebooks roots, profile, APPDATA, LOCALAPPDATA and TEMP; ports 5213/19227. Hidden subprocesses and `--show-inactive --quiet-errors`; no focus activation or audio.

| Check | Result |
|---|---|
| Backend version | PASS: private health reports Books Arranger 0.18.0, closing false. |
| Empty status | PASS: state version 0.18.0, automatic Idle, jobs Completed, zero queued. |
| Shipped renderer | PASS: v0.18.0 badge and Quit Books Arranger control. |
| Normal Quit | PASS: shipped UI handler clicked; exit code 0, no signal, 424 ms after request. |
| Native/port closure | PASS: private ports absent, closed true, active 0, retained 15, unsignaled 0, zero true; no force, timeout, overflow, truncation or retained owned process. |
| Real-data observation | PASS: read-only before/after catalog/library/recovery fingerprints identical, below. |

## Real-data fingerprints

No database connection or copy was made. Real inventory.sqlite3 retained device 133335364132330000, inode 69805794224273076, size 537026560, mtime_ns 1792344250227182400 and SHA256 **588a1bf9f880ab3d3e0f1a7d6756f2c4516904bba220b545e99785a13f643181**.

Z:/Audiobooks remained 8890 files, 763 directories, 740488599494 bytes, name/size/mtime digest **5990454a7b02448d7d5a56638f22766470b29a82325fd4d8b461ca92b81c2327**. Source-recovery zero files/three directories and replacement-recovery zero files/zero directories; empty-file digests identical. No fingerprint errors. This is unchanged observation around the smoke, not an audit of output contents or database consistency.

## Local-index and test evidence truthfulness

Ender reports **59 focused cases PASS** in 7.010 seconds: 17 local-index, 9 scheduler, 33 provider/identity. Evidence `shared/research/ol-v0180-focused-test-summary.json` is explicitly a developer-transcribed summary, not a raw test log or Futaba rerun. Construction review is separate.

At report time the authenticated Works import/resume is still active; no active index or full eligible coverage is certified by this report. The observed checkpoint supplied by Ender is 18.94 GB scanned, 421 candidates, 19 held titles, which is partial progress, not completion. Compressed Works SHA256 supplied by Ender is `1e642ad9742e80f1b60f9125eb6a8fa17bafe42690a9236e0df86f86f28eaf1d`, with official SHA1/MD5 matched under source retention; Futaba did not independently hash the entire source.

Required status distinctions retained: unavailable means not activated; outside_coverage means outside the requested subset, not a global miss; identity_incomplete means a matching title retains stub/unusable/unresolved author identity even alongside another valid candidate; covered requires fully authenticated requested-title coverage. Zero works is only a sparse scanned miss. Partial Editions remains pending/excluded and was not read by QA. Any later completion/activation evidence must be recorded separately, not backdated into this smoke.

## Findings, patterns and limits

No observed blocker within this focused packaged smoke. Pattern alerts: no new alert. Carried dispositions: **defer** real-catalog-copy QA because historical cleanup entries can reach Z:; **accept** explicitly attributed concurrent live drift when applicable. Final measured fingerprints here were stable.

Not covered: real index activation, coverage/metadata accuracy over the requested local library, partial Editions, real fallback/research/network quotas, conversions or crash recovery/playability, real scheduling under load, installed-live target series #10, installer/updater, tray/Alt+F4/error screens, unchanged retry/audio flows, theme/small widths. Native closure is not full system isolation.

## Evidence and hygiene

Evidence root: `C:/Users/AnGeLZzZ/AppData/Local/Temp/books-codex-20261018/shared/qa-v0180/evidence/`: payload-binding.json, extract-installer.log, result-empty.json, native-smoke-closure.json, shell logs, real-before/after.json plus full UTF-8 entry lists, catalog-before/after.json. Reviewed owner/helper/pins in sibling `shared/tools/`.

No session scratch deletion per Sergei. No repository throwaways; report is sole tracked QA deliverable. Scratch for Sergei to delete later: `C:/Users/AnGeLZzZ/AppData/Local/Temp/books-codex-20261018`.
