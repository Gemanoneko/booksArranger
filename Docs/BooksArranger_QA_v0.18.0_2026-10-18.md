# Books Arranger v0.18.0 — lean packaged QA

Author: Futaba. Date: 2026-10-18.

**Verdict:** GO

Release source commit: adef2118ecac4d7c3202e364bbd7c5423fd7baf7
Release artifact manifest SHA256: 8f3e4b2e39e2a3dddb33b47415af2e444e0009c6bc621fd38890810233a5714b

Installer: `dist/builds/bc7ac95d-e228-45ca-b87a-61363b8b1494/Books-Arranger-Setup-0.18.0.exe`
Installer SHA256: 20784d8607b4c58d3496a9c29cb5ea62230ebc59883789c8a9bf9c4b18cd211f
Installer size: 173192373 bytes.

## Scope and binding

GO covers the replacement artifact's requested private empty-catalog version/status/Quit smoke and exact binding. Real local-index activation proof is separately attributed below; installed-live target #10 remains the release owner's check. No real catalog copy/connection, real job/library mutation, provider requests, partial Editions read, installation or live controls by QA. The first prepublication candidate is superseded by the CLI Unicode-output-only correction and is not the artifact accepted here.

Independently recomputed installer and manifest hashes match above; source_head, version and build ID match the candidate. Extracted the actual installer without installing it: **229/229** payload files match manifest SHA256 and size, zero mismatches. The extracted payload was tested directly. Senua independently reviewed the exact packaged production modules and complete execution pin inventory.

The earlier scratch sources were missing. This is a newly reconstructed fixed-scope QA runner, not a byte-exact restoration or canonical receipt framework. Owner SHA256 `a10ee03c8569600ba1288d9691582eca817225469e6ab0a480009cc8eb46c9b0`; helper SHA256 `d905f2f7befbbe3ddc5a7c1505bde76e0a6c7f5ee675ef43574c379ac9520a89`. Both syntax checks passed; Senua reviewed full source and then the final 327-file pins with zero mismatches before execution.

Normal guard accepted this exact replacement command once from session `shared/tools`: `C:/Program Files/nodejs/node.exe ./smoke-owned.mjs --pins-sha 252b4191229ec8322f01bd50f86cbed6686518e2f21f6ecf759aef29b09438f5`.

Runner hashes/native-holds exact input files before/after and uses existing runOwned private native Job supervision with a 600000 ms deadline. Total 8644 ms; supervised phase 3174 ms. Synchronous bootstrap hashing cannot be preempted by the JavaScript timer; inherited limitation retained. No canonical qa-handoff receipt is claimed: its refused path remains stopped. Independent binding and measured behavior are the lean evidence here.

## Actual packaged behavior

One replacement launch at 17:38:06 UTC / 20:38:06 Jerusalem. Fresh private empty catalog with `--catalog-mode=new`, private empty Audiobooks/Podcasts/Ebooks roots, profile, APPDATA, LOCALAPPDATA and TEMP; ports 5213/19227. Hidden subprocesses and `--show-inactive --quiet-errors`; no focus activation or audio.

| Check | Result |
|---|---|
| Backend version | PASS: private health reports Books Arranger 0.18.0, closing false. |
| Empty status | PASS: state version 0.18.0, automatic Idle, jobs Completed, zero queued. |
| Shipped renderer | PASS: v0.18.0 badge and Quit Books Arranger control. |
| Normal Quit | PASS: shipped UI handler clicked; exit code 0, no signal, 370 ms after request. |
| Native/port closure | PASS: private ports absent, closed true, active 0, retained 15, unsignaled 0, zero true; no force, timeout, overflow, truncation or retained owned process. |
| Real-data observation | PASS: read-only before/after catalog/library/recovery fingerprints identical, below. |

## Real-data fingerprints

No database connection or copy was made. Real inventory.sqlite3 retained device 133335364132330000, inode 69805794224273076, size 537026560, mtime_ns 1792344655545984200 and SHA256 **fbeea242c831760bc0b12161e9c0e94336f8a3f23966215216f7d823a9e9451d**.

Z:/Audiobooks remained 8890 files, 764 directories, 740500435119 bytes, name/size/mtime digest **c8eae49f5eca91fd61c760e30be455374aeb41141aee32a50986d0e18e80afed**. Source-recovery zero files/three directories and replacement-recovery zero files/zero directories; empty-file digests identical. No fingerprint errors. This is unchanged observation around the replacement smoke, not an audit of output contents or database consistency.

## Local-index and test evidence truthfulness

Ender reports **59 focused cases PASS** in 7.010 seconds: 17 local-index, 9 scheduler, 33 provider/identity. Evidence `shared/research/ol-v0180-focused-test-summary.json` is explicitly a developer-transcribed summary, not a raw test log or Futaba rerun. Construction review is separate.

Ender's final independent read-only proof `shared/research/ol-import-actual-r3-verification.json` reports an activated immutable completed index: 241 requested titles, 218 eligible, 23 identity-held; 451 works, 427 authors, zero editions. Works and Authors reached full EOF with official SHA1/MD5 and local compressed SHA256 authenticated. Registry/completion/native identity agreement and integrity ok are Ender's results, not Futaba reruns. Futaba independently read the proof and rehashed the actual ready index (196608 bytes): SHA256 **239ea63175ff732f59d60e6324ec0de67787eaf819843b6d886617921775c3bb**, matching the proof.

The 23 holds comprise 20 missing complete credited-author identities and three qualified relationships requiring independent evidence. The Subtle Knife remains identity_incomplete; Our Lady of Darkness is covered with multiple explicit work/author IDs, not an invented unique identity. No canonical series ordinal is inferred from Open Library strings. Editions remains partial/excluded and was not read. This requested subset does not represent full Open Library coverage.

The first importer run activated successfully but its final cp1251 stdout print raised UnicodeEncodeError. The replacement changes only CLI final JSON output to ensure_ascii=True. Ender reports 18 local tests PASS in 2.224 seconds including actual Björk/cp1251 CLI coverage; Senua cleared the two-file correction. This developer evidence is not a QA rerun and does not claim that the multi-gigabyte import was replayed.

Required status distinctions retained: unavailable means not activated; outside_coverage means outside the requested subset, not a global miss; identity_incomplete means a matching title retains stub/unusable/unresolved author identity even alongside another valid candidate; covered requires fully authenticated requested-title coverage. Zero works is only a sparse scanned miss. No local ordinal or full Editions coverage is claimed.

## Findings, patterns and limits

No observed blocker within this focused packaged smoke. Pattern alerts: no new alert. Carried dispositions: **defer** real-catalog-copy QA because historical cleanup entries can reach Z:; **accept** explicitly attributed concurrent live drift when applicable. Final measured fingerprints here were stable.

Not rerun by QA: registry/native/integrity/query proof, source full-stream authentication, real fallback/research/network quotas, conversions or crash recovery/playability, real scheduling under load, installed-live target series #10, installer/updater, tray/Alt+F4/error screens, unchanged retry/audio flows, theme/small widths. Partial Editions is excluded. Native closure is not full system isolation.

## Evidence and hygiene

Evidence root: `C:/Users/AnGeLZzZ/AppData/Local/Temp/books-codex-20261018/shared/qa-v0180/evidence/`: payload-binding.json, extract-installer.log, result-empty.json, native-smoke-closure.json, shell logs, real-before/after.json plus full UTF-8 entry lists, catalog-before/after.json. Reviewed owner/helper/pins in sibling `shared/tools/`.

The first candidate's payload, mutable directories, pins and successful smoke evidence are preserved under `shared/qa-v0180/history-superseded-prepublication/`, explicitly labeled superseded. Those measurements do not accept this replacement artifact.

No session scratch deletion per Sergei. No repository throwaways; report is sole tracked QA deliverable. Scratch for Sergei to delete later: `C:/Users/AnGeLZzZ/AppData/Local/Temp/books-codex-20261018`.
