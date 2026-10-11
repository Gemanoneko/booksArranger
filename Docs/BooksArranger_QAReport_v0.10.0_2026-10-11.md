# Books Arranger QA — v0.10.0 (2026-10-11)

**Verdict: GO**

Final candidate-v2: 65 files, source digest `f844942df51295f70aedb7769cbb6c4f2a14be6359a3551cb846fd5a3e268a46`, manifest SHA-256 `e0e8e960a86689692746be0e099ff0ff0f06ad7a60a642ff6b562eb0dc33f65a`. HEAD/committed UX addendum `fa2ef0107b32bda7066cca63f4348688ab7efea3`; baseline `78f0c41fcd900ac42a0794052f3ac4589674b165`; source version 0.9.2, target 0.10.0, dirty=true. The snapshot includes staged web/app.js SHA-256 `c33d731696b400bcde97866ef9f93846e3a4b0ae86cf56d2a793a0afdda4244d`. QA used an independently verified immutable private copy; live canonical assets were not modified.

## Executed matching gate

| Run | Actual checks | Elapsed |
|---|---|---|
| Final v2 producer | 48 processing + 8 media Python cases; 3 Node routes; all PASS | 67.739 s owned / 67.697 s manual |
| Final v2 independent receiver | Identical 5 commands, 56 Python + 3 Node; all PASS | 68.380 s owned / 68.339 s manual |

Receiver Python case times: 28.313 s processing and 34.354 s media. Producer and receiver actual receipt lines, identities, command arrays and result fields match. All exits are zero; held source/manifest/native/four-runtime pins remained unchanged through post-run checks; owned descendants and output drains closed. Senua cleared the exact finite manual route before execution: hidden owned jobs, shared total 600000 ms deadline, bounded streams and pinned executable resolution. No extra graph or probes were run.

## Behavior verified by private fixtures

- Own request guard is 100 uncached requests per hour **per host**; cached evidence and another host remain available. Eligibility uses the oldest reservation's expiry. Concurrent clients atomically reserve the remaining slot.
- Genuine source pauses retain numeric/date Retry-After semantics and their separate recorded cause. A later concurrent failure cannot shorten a longer shared pause. Only the explicitly recognized legacy app-limit wait is recalculated; genuine source pauses and unknown waits are preserved.
- An authorized run stays Running in waiting phase, with no current research candidate, Start disabled and Stop enabled. Saved research retries unattended at the earliest eligible candidate time; later candidates are not revisited early. Other eligible work and required working cleanup drain before retry is armed.
- Stop during an armed hour-long fixture wait completes within the existing case's one-second bound, disables retries and preserves pending IDs. Restart leaves Paused with no retry thread or autostart. Legacy wait migration preserves compact evidence and does not approve a book.
- Existing uncertainty, identity/language/credit/cover/order gates, source revalidation, atomic approval/job admission, draft protection and safe failure diagnostics still pass. Uncertain books remain Held; source waits do not approve or convert them.
- Eight media cases use actual private generated audio/FFmpeg. Confident fixture admission reaches verified chaptered output, source/working-copy cleanup and registered recovery; collision, rollback, changed tags, cover mismatch and interruption safeguards pass. This is fixture conversion, not a real-library conversion or elapsed 24-hour retention soak.
- Three Node VM routes verify automatic/progress/recovery UI behavior. New retry text distinguishes app limits, source pauses and unavailable sources, uses backend next-check/candidate timestamps, and falls back truthfully for invalid times. Paused/old-backend status has no automatic-retry promise. These are synthetic DOM/VM assertions, not a new rendered screenshot pass.

No live service, production database, actual library, public-provider request, signed-in browser, desktop focus, audio playback, Comics, runtime replacement or Git operation occurred. Fake clocks test eligibility boundaries; no real hour/day soak or public-network success is claimed.

## Prior failure and warning limitation

Original unexecuted receipt-label derivative was corrected before tests to compare executable Paths on Windows. Its source endpoint was unchanged. The subsequent v1 producer passed 55 Python cases, failed the first Node fixture, and did not run the remaining two Node routes. V1 source and raw failed proof are retained. V2 changes exactly public_research.py, tests/test_automatic_processing.py, tests/test_automatic_frontend.js and staged web/app.js: shared pause/copy corrections, one finite concurrency case, and restoration of the overwritten fixture candidate argument without weakening assertions. Final v2 passes the complete declared graph independently.

Receiver stderr contains **five ResourceWarnings** from mocked HTTPError(fp=None) cleanup. Senua's narrow classification: CPython's in-memory BytesIO wrapper finalizer closes it and emits the warning; no temporary file is allocated by that constructor. Actual production response/connection closure is source-supported in public_research.py:130–132. Production can emit the same wrapper warning; QA does not claim warnings impossible or a live-network leak test. No socket, file or process leak is demonstrated by this result.

**Blocker: 0 / Major: 0. Minor diagnostic noise: 1, accepted for this endpoint; no open behavioral blocker.**

**Pattern dispositions:** Whole-pass day-long wait from own global budget — **fix**, scoped guard and automatic earliest retry verified. Waiting/candidate time and cause conflation — **fix**, backend and VM cases pass. HTTPError wrapper warning noise — **accept** with the limitation above; no extra test or product fix implied. Missing historical program-error cause remains **defer/unknown**; these retry fixtures do not reconstruct that earlier exception.

## Identical actual receipt

```text
BOOKS_MANUAL_QA|tool=Books Arranger|target=0.10.0|source=0.9.2|HEAD=fa2ef0107b32bda7066cca63f4348688ab7efea3|dirty=true|source_digest=f844942df51295f70aedb7769cbb6c4f2a14be6359a3551cb846fd5a3e268a46|manifest_sha256=e0e8e960a86689692746be0e099ff0ff0f06ad7a60a642ff6b562eb0dc33f65a|python=pass|node=pass|package=n/a(manual nonpackage contract)
```

Package n/a is the reviewed Python manual contract, not a fabricated package-script gate.

## Retained proof identities

Paths are relative to scratch/source-retry-qa-2026-10-11/ unless prefixed sender (scratch/source-retry-2026-10-11/).

| Artifact | SHA-256 |
|---|---|
| producer-manual-v1-failed.json | 61bfb0b599e705715bb9d67e286d530d49f5d3386db56f650cad176f50278ff6 |
| producer-owned-v1-failed.json | 616d4d40dcd4ef5c381cfe7650911c02f29aa0abf92aa469dcf4ff413cc8b35c |
| producer-manual-v2-pass.json | c4792a71d81400d40613946f0024f6c0577eb9bf7d51b607c3f9734dbd348ddf |
| producer-owned-v2-pass.json | 14d6759f2a610340f64cf72886b704e5c483e295568330a08ffdbd802b98b027 |
| receiver-manual-v2-pass.json | d0e7260dde7073fdfb00db1a4f03837e6e107cffc532064ccae6ceddf6e17b08 |
| receiver-owned-v2-pass.json | d5eb9b5f5cfd52f0b7040f1c850872af7d334d28b4a853f302ff923f7fc3c81a |
| sender/manual-contract-v2.json | 829278755650a0ca997f39484766ed5b4b385eb589203c03f8a5cbf36169db1e |
| sender/qa_checks_v2.py | d34e015ce1fb03bdb5ccd3fbf5747401f0990e02498595100ad0e767d92ad669 |
| sender/run_qa_v2_owned.py | ec25edaa70b466514162415a0a626488bdcff606f534ab1cab18a4ee5f72aecd |
| preparation-receipt-v2.json | cf8e5613a7cb45f3ba8270d915e126c8beda0ce8941cc998d7150857d35abb04 |

Unique v1 failure, final source snapshots, contracts, reviewed harnesses and actual acceptance receipts remain for release consumers. Disposable task bytecode cleanup follows consumer closure through a separate studio-cleanup receipt. Prior HTTP reports/evidence/cleanup remain untouched.
