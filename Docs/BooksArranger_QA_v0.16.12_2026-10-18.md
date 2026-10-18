# Books Arranger v0.16.12 — final lean packaged QA

Author: Futaba. Date: 2026-10-18. Supersedes the earlier source 4aff686 smoke.

**Verdict:** GO

Release source commit: 09714f2a0a607f670a14c120e32f12dad2d2158b
Release artifact manifest SHA256: d10b4265941fc217265e2aa0f968eec1968afe45b2404eee711123d2ae6b4db6

Installer: `dist/builds/db404224-54fa-4c4a-8d50-602d5cded895/Books-Arranger-Setup-0.16.12.exe`
Installer SHA256: 5e0670fab2b26b57f8ad24ab3a7322305296a842e08c7a9715d5202d4965da3e
Installer size: 173132445 bytes.

## Scope and independent binding

GO covers the requested empty-catalog packaged smoke and synthetic retry regression in the shipped handlers. No real catalog was copied or connected by QA, no live library writes, installation or live-app shutdown occurred. Real backfill/playability and real backend enqueue are outside this smoke.

Independently recomputed installer and manifest hashes match above; manifest source_head, version 0.16.12 and build_id match. Extracted without installing: **225/225** payload files match manifest SHA256 and size, zero mismatches. Tested the extracted payload directly.

Final launch 15:09:56 UTC / 18:09:56 Jerusalem: fresh empty private catalog (`--catalog-mode=new`), private empty Audiobooks/Podcasts/Ebooks roots, profile, APPDATA, LOCALAPPDATA, TEMP and ports 5213/19227. Hidden subprocesses, `--show-inactive --quiet-errors`, no audio/focus activation. Synthetic mutations are intercepted in renderer memory before native fetch; no synthetic jobs exist on disk. The live app was already stopped by the release owner.

After Senua's updated product/artifact/scratch reviews, normal guard accepted once from session `shared/tools`: `C:/Program Files/nodejs/node.exe ./smoke-owned.mjs --pins-sha c276eb0b82ad71a14017d4f621888e9f51a7961cb4104d658ec284290eb56f9b`.

The fixed owner hashes/native-holds its complete input inventory and uses a private native Job with a 600000 ms supervised deadline. Measured total 35229 ms, supervised phase 29988 ms. Synchronous bootstrap hashes cannot be preempted by its JavaScript timer; limitation retained.

No canonical qa-handoff receipt is claimed: its read was refused by the guard P9 filename rule, and that path stopped. Sergei's explicit lean handoff controls focused scope. Actual packaged results and independent binding are evidence here; Ender's three frontend suites and 21 backend tests are separate developer evidence, not rerun/certified by Futaba.

## Measured results

| Check | Result |
|---|---|
| Version/status | PASS: backend/window 0.16.12, first health1243 ms. Empty status Idle/zero queued/attention/Nothing running. State12/12HTTP200, p50 3 ms, maximum5 ms. |
| Strip/held row | PASS synthetic counts9/5/2/1/1; Retry all hidden in All and shown in retry filter; no overlaps/horizontal overflow. Held reason/no progress/no elapsed; running30% row retains progress/time. |
| Retry selected | PASS empty disabled Retry selected(0), ordinary Queue hidden; synthetic eligible row enables confirmation/cancel. |
| Accepted single | PASS shipped handler+synthetic202: disabled Queued across3stale polls; no second enqueue. |
| Accepted selected | PASS2synthetic rows: both Queued across3stale polls; exactly2intercepted requests. |
| Accepted Retry all | PASS delayed preacceptance state cannot erase acceptance; disabled bulk and Queued rows across3stale polls; no duplicate request. |
| Desktop status race | PASS shipped desktop script on detached real DOM: unavailable keeps eligible controls enabled; genuine quit disables them. Production desktop API unchanged. |
| Mutation isolation | PASS all19retry assertions;4intercepted synthetic POSTs(single,selectedA/B,bulk), **zero retry/repair mutations reached native fetch**. |
| Quit/closure | PASS hit-tested UI Quit, shell exit0after408 ms. Private Job closedtrue,active0,retained29,unsignaled0,zerotrue; no force/timeout/overflow/retained process. Original Books Arranger/listener sets empty before/after; private ports gone. |
| Real fingerprints | PASS identical catalog hash/identity/stat and recovery/library fingerprints below. |

## Real-data read-only observations

Before/after successful run, without database connection or copy: inventory.sqlite3 retained device133335364132330000,inode69805794224273076,size533569536,mtime_ns1792335428361970700 and SHA256 **54b03228aed98fcc585f084e6f48d5da6a2d5238a39077969e55d6ed737458c8**.

Z:/Audiobooks identical8890files/757directories/740396281945bytes; name-size-mtime digest **be5dcb61d103a76e82f08fb0f9343deb4ed473736eac0b5f925aae9f3876b76c**. Source-recovery0files/3directories, replacement-recovery0files/0directories, identical empty-file digests. No fingerprint errors.

## Findings, patterns, limitations

No observed product blocker in final focused QA. User-reported transient-disable and stale-accepted-queue regressions verified against09714f2 with rebuilt shipped handlers and synthetic responses.

Pattern alerts: two carried with dispositions. **Defer** real-catalog-copy testing: historical held-cleanup paths may point at real Z:, so only empty private catalogs launch. **Accept** attribution of concurrent live fingerprint drift when applicable; final run fingerprints stable. No new pattern alert.

Not covered: real backend queue/worker order under load, real network series matching/backfill/crash recovery/playability, installer/updater, tray/Alt+F4/all error screens, small widths/light theme. Backend correctness rests on separate Ender tests/Senua review; this pass tests frontend acceptance with intercepted responses. Native closure is not full system isolation.

## Evidence and prior attempts

Final evidence: `C:/Users/AnGeLZzZ/AppData/Local/Temp/books-codex-20261018/shared/qa-v01612-r2/evidence/`: payload-binding.json,result-empty.json(19retry checks/request counts),native-smoke-closure.json,screenshots,shell logs,real-before/after.json+UTF-8entry lists,catalog-before/after.json.

Preserved historical evidence, not final acceptance:

- `shared/qa-v01612/`: prior successful4aff686smoke superseded by retry fixes. Concurrent live catalog hash changed and one same-size/mtime partial→final library rename occurred; no unchanged-hash claim for that run.
- `shared/qa-v01612-r2/history-attempt-r2/`: initial regression harness failed because shipped CSP correctly blocked detached-script new Function; graceful Quit/native closure succeeded. Ender removed unsafe evaluation without changing product CSP; Senua reviewed refreshed pins before final fresh successful run. Old harness/pins retained `shared/tools/history-r2-csp-failure/`.

No session scratch cleanup per Sergei. No repository throwaways; report is sole tracked QA deliverable. Scratch for Sergei to delete later: `C:/Users/AnGeLZzZ/AppData/Local/Temp/books-codex-20261018`.
