# Books Arranger QA — v0.9.2 (2026-10-11)

**Verdict: GO**

Final frozen endpoint: candidate-v2, 65 files. Source digest `945b54d8fed6cecd3b659fc033d36a6d8b8342bf5c2833fa9ca96b846a8002d2`; manifest SHA-256 `ad89032715dce0c294d0f7296e98a230aa1d4484d1fce32ad30d9002ee8b7483`. HEAD/baseline `2235ad8c1fd6e6bac3f11136c1bcf2277b52256f`; source version 0.9.1, target 0.9.2, dirty=true. Independent QA used the exact private snapshot, never a moving working tree.

This patch handles recognized response disconnects across headers and body, including ConnectionAbortedError. The OS-side reason for the original client disconnection remains unknown. The verified correction closes the affected request without attempting another error response on its failed socket; unrelated errors retain their existing handling.

## Actual execution

| Endpoint/run | Cases | Test time | Owned elapsed | Outcome |
|---|---:|---:|---:|---|
| V1 producer | 13 | 3.426 s | 7.095 s | 12 PASS / 1 FAIL; all four new response cases PASS |
| Final v2 producer | 13 | 2.599 s | 4.874 s | PASS |
| Final v2 independent receiver | 13 | 2.454 s | 6.097 s | PASS; manual elapsed 6.056 s |

Final producer and receiver executed the identical declared command once each: Python unittest discover, tests/test_web.py, verbose. All final command exits are zero; actual identities and command result fields match. Source, manifest, native containment and four runtime pins were independently checked before execution, held through the run and verified unchanged afterward. Senua cleared the exact source and manual route before execution. Hidden owned process jobs use a shared total 600000 ms deadline, bounded streams and completed descendant/drain closure.

There were no public-provider, live service, actual library, production database, real Start/Stop, audio, browser-focus, Comics or Git operations. Nine existing cases use ephemeral loopback servers and private databases/files; their fixture scan/stop/resume/shutdown operations do not operate the live app. Four new response cases are network-free mocked handlers. No UI or conversion graph was rerun for this backend-only correction; released conversion and 24-hour retention behavior were not changed or recertified by these HTTP checks.

## Verified behavior

- Aborted headers attempt the original response once, perform no body write, set close_connection and do not trigger a second error reply.
- Broken pipe, reset and abort during a body write attempt that write once and close only the affected request.
- A connected backend failure retains the existing 500 response and safe error body; it is not treated as a disconnect.
- Unexpected OSError propagates, with no body write and no false disconnect flag.
- Existing routing/health identity, source-file exclusion, token/host/origin rejection, malformed payload/configured-root restrictions, catalog ownership/port rules, inventory/review revisions, anthology roles, scan lifecycle and protected shutdown all pass against private fixtures.

**Blocker: 0 / Major: 0 / Minor: 0 open.**

## V1 failure and v2 isolation

V1's existing incremental inventory fixture expected 200 from its first Ebooks scan request and received 409. Its four new response cases passed. The source supports an unrelated retention-startup admission race with that fixture's idle assumption; the active admission was not captured, so QA does not claim direct proof of that race.

V2 changes only tests/test_web.py relative to v1: the private server constructor patches MergeService.start_retention for these HTTP fixtures. Production retention and API admission policy are unchanged, all 13 cases/assertions remain, and no product gate was relaxed. V1 snapshot and actual failed receipts are preserved. The v2 producer and independent receiver both pass the declared suite.

**Pattern alerts:** secondary reply after client disconnect — **fix**, verified on final v2. Unrelated background startup racing an idle HTTP fixture — **fix fixture isolation**, source-supported explanation with the stated observation limit. OS-side client-abort cause — **defer**, no evidence identifying it.

## Identical final receipt

```text
BOOKS_MANUAL_QA|tool=Books Arranger|target=0.9.2|source=0.9.1|HEAD=2235ad8c1fd6e6bac3f11136c1bcf2277b52256f|dirty=true|source_digest=945b54d8fed6cecd3b659fc033d36a6d8b8342bf5c2833fa9ca96b846a8002d2|manifest_sha256=ad89032715dce0c294d0f7296e98a230aa1d4484d1fce32ad30d9002ee8b7483|python=pass|node=n/a(backend-only HTTP correction)|package=n/a(manual nonpackage contract)
```

Python app uses a reviewed manual nonpackage contract; package n/a is explicit. Node n/a is the declared backend-only scope.

## Preserved proof

Artifact paths are relative to scratch/http-disconnect-qa-2026-10-11/ unless marked sender (scratch/http-disconnect-2026-10-11/).

| Artifact | SHA-256 |
|---|---|
| sender-manual-receipt-v1.json (failed) | 8a071336fa1a897f1da90e05087cd93e216211f3e8b3b3fa160f4656d3aaa264 |
| sender-owned-receipt-v1.json (failed) | 61fe67aa7d25dce04638a80dfeb2150a157aa572577e1b9e30b451d6bc74cb4f |
| sender-manual-receipt-v2.json | 6c5548d3908cd34f271a339edb6e56b10908c3f430efc64e2a1fd83a3ee94de5 |
| sender-owned-receipt-v2.json | cedaaf3dca19b44cb691235b0a34238e5b06dd5361d4a2e57cf6244efef855e0 |
| receiver-manual-receipt-v2.json | f909107553efffddc575084c9ded33d546b31694e22a13e783301f654f0bcc2e |
| receiver-owned-receipt-v2.json | 72d34b1f5b62fdc5fc52eafabc1903075e8a141f1bbbcb8846d6fe584eeeefbb |
| sender/manual-contract-v2.json | 8fd3a3b72f0331ccefdecbd1b0a0f37897883170f4a95724ca370a8ff5c909d3 |
| sender/qa_checks_v2.py | 7dad8b00356e30d436d1a54371b7c1552c91c99dbc806fbeed038d0aa94d63d7 |
| sender/run_qa_v2_owned.py | 3cb017e6cfcf183cc082b4f5688128f53e17f68ca10f51b4596ac5b685f600da |
| preparation-receipt-v2.json | 00de1640ded477e2900345b43852f5e23877c0c2a10d659c0d4934f0c6f59135 |

Snapshot copies, contracts, reviewed harnesses and unique failure/acceptance proof remain for release consumers. Disposable bytecode cleanup is separate, after all consumers close, using studio-cleanup's exact native plan/check/remove/verify route. Prior release reports and evidence remain unchanged.
