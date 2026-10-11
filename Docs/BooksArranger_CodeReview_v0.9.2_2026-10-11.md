# Code Review — Books Arranger v0.9.2

## Header

```
Reviewer: Senua (Code Reviewer), Codex gpt-6.1-sol xhigh
Date: 2026-10-11
Tool: Books Arranger
Release: v0.9.2
Commit range: 2235ad8c1fd6e6bac3f11136c1bcf2277b52256f..2235ad8c1fd6e6bac3f11136c1bcf2277b52256f plus the immutable candidate-v2 delta below
Files changed: 3 files, +75 / -13 versus released v0.9.1
Stand-down dimensions: none; Electron and installer-specific checks are not applicable to this Python/manual tool
```

## Summary

The HTTP response writer now contains recognized client disconnects during both header and body writes and marks that request for closure. JSON serialization stays outside the disconnect catch, and unrelated I/O or backend failures retain their existing behavior. Review covered only the accumulated response patch, its private HTTP fixtures and Brief update against released v0.9.1. No findings remain open.

This patch does not establish why the operating system reported WinError 10053 or why the previous service exited. Runtime persistence, startup and production health are outside this source certificate.

## Certified endpoint and method

- Released baseline/source HEAD: `2235ad8c1fd6e6bac3f11136c1bcf2277b52256f`.
- Source VERSION `0.9.1`; target `0.9.2`; dirty `true`.
- Immutable snapshot: `scratch/http-disconnect-2026-10-11/candidate-v2`.
- Raw manifest SHA-256: `ad89032715dce0c294d0f7296e98a230aa1d4484d1fce32ad30d9002ee8b7483`.
- Source digest: `945b54d8fed6cecd3b659fc033d36a6d8b8342bf5c2833fa9ca96b846a8002d2`, SHA-256 of compact JSON for the ordered manifest entries.

All 65 frozen source sizes and raw SHA-256 pins matched independently. Git baseline text for the three changed paths matched the prior frozen source used for the diff. Comparison of the remaining manifest entries against the verified release graph, including released VERSION, identified no additional source changes. Confidence, public-source evidence, metadata approval, conversion, original cleanup, native I/O, retention, authentication, request validation and frontend implementations are unchanged; they were not subjected to a new broad review.

| Changed path | Final raw SHA-256 |
|---|---|
| web_server.py | 61ced64e25b432883b15760443acd4bfc90619de9c8505fa1eab3bed28164a66 |
| tests/test_web.py | 4686b54babd10aa6c3ad07ad955d4bfa9147cff107e820956e36479f549f542b |
| Docs/BooksArranger_Brief.md | 8ade4f68dac6a141660c38a7fea261163c10bd64e9ab860e9c5246c6a9fd6505 |

## Rubric

Severity and the always-blocking safety floor follow `Team/Docs/ProcessRules.md` § Severity definitions.

### 1. Security

Pass — `web_server.py:119` moves the same headers under the socket-write boundary without changing CSP, origin/token checks, response encoding or content length. No new shell, credential, network destination or file operation enters product code.

### 2. Correctness & Logic

Pass — `web_server.py:130` catches only BrokenPipeError, ConnectionResetError and ConnectionAbortedError from response writes; `close_connection=True` prevents continuation of that request. A disconnected successful reply no longer escapes into a second error reply.

### 3. Crash / Stability Safety

Pass — both header flush and body write share the recognized-disconnect boundary. Unrelated OSError still propagates from the writer; connected backend failure still follows the existing 500-response path.

### 4. Performance

Pass — the patch adds no buffering, retry, worker, scheduler or loop and leaves successful-response work unchanged.

### 5. State & Data Safety

Pass — only the request connection state changes. No approval, scan, queue, media, catalog, retention or deletion transition is introduced or weakened.

### 6. Input Handling

Pass — JSON serialization remains outside the catch at `web_server.py:118`; unexpected serialization/I/O/backend failures are not relabelled as client disconnects. The three recognized socket exception classes are explicit.

### 7. Maintainability

Pass — the correction stays in the single response helper. Four focused handler cases distinguish header disconnect, all three body-disconnect classes, connected backend failure and unrelated I/O failure.

### 8. Doc/Code Drift

Pass — the Brief describes the narrow request behavior and preserves the unknown operating-system disconnect cause. Private fixture isolation is documented in code and the final contract without asserting captured admission telemetry.

### 9. Build & Release Hygiene

Pass — final producer and receiver identities, fixed command and successful exits match. Source VERSION intentionally remains 0.9.1 before Sully's release metadata change; this clearance permits the 0.9.2 metadata bump, with any additional source change requiring endpoint reconciliation. No package/installer or frontend check is declared for this backend patch.

## Verification evidence

Senua audited source and independently verified the receipts; Ender and Futaba executed the checks. The fixed command is `python -m unittest discover -s tests -p test_web.py -v`: four network-free response-handler cases and nine existing private HTTP cases using temporary catalogs/library roots and ephemeral IPv4 loopback servers. No live service, production database, actual library, public provider, account, browser or Start action was used by this review.

The first candidate's actual producer result was 12 PASS / 1 FAIL; all four new response cases passed. The existing first-scan assertion returned 409. Unchanged source shows that BrowserServer starts retention and its worker takes recovery admission before its first wait, while the scan gate rejects an occupied admission. This is a source-supported race explanation; the active admission was not captured. Its failed receipts remain retained below.

V2 changes only that private fixture setup: `tests/test_web.py:88` patches MergeService.start_retention during BrowserServer construction. These nine HTTP cases do not test retention. All 13 cases and assertions remain; production retention and busy gates are untouched. Final producer and receiver each ran the identical 13-case command once and passed, with held source/runtime pins unchanged, owned descendant closure, zero command errors and no truncated streams.

| Evidence | Actual result | Manual receipt SHA-256 | Owned receipt SHA-256 |
|---|---|---|---|
| V1 producer, retained failure | 12 PASS / 1 FAIL; 13 tests in 3.426s; owned 7.095s | 8a071336fa1a897f1da90e05087cd93e216211f3e8b3b3fa160f4656d3aaa264 | 61fe67aa7d25dce04638a80dfeb2150a157aa572577e1b9e30b451d6bc74cb4f |
| V2 Ender producer | 13/13 PASS in 2.599s; owned 4.874s | 6c5548d3908cd34f271a339edb6e56b10908c3f430efc64e2a1fd83a3ee94de5 | cedaaf3dca19b44cb691235b0a34238e5b06dd5361d4a2e57cf6244efef855e0 |
| V2 Futaba receiver | 13/13 PASS in 2.454s; owned 6.097s | f909107553efffddc575084c9ded33d546b31694e22a13e783301f654f0bcc2e | 72d34b1f5b62fdc5fc52eafabc1903075e8a141f1bbbcb8846d6fe584eeeefbb |

Exact final manual contract: `8fd3a3b72f0331ccefdecbd1b0a0f37897883170f4a95724ca370a8ff5c909d3`; inner `qa_checks_v2.py`: `7dad8b00356e30d436d1a54371b7c1552c91c99dbc806fbeed038d0aa94d63d7`; outer `run_qa_v2_owned.py`: `3cb017e6cfcf183cc082b4f5688128f53e17f68ca10f51b4596ac5b685f600da`. The derivative retains the reviewed trusted native bootstrap, four executable runtime pins, source holds, hidden suspended child assignment before resume, shared 600000 ms hard deadline, bounded output pipes and final rechecks. No additional helper framework or runtime dependency was introduced. Node checks are n/a for this unchanged frontend; no broader graph PASS is claimed.

Senua created no disposable scratch output. Frozen source and failed/successful receipts remain their owners' retained evidence; this report is the review artifact.

## Verdict

- Total Critical: 0
- Total Major: 0
- Total Minor: 0
- Always-blocking safety floor: intact within the certified patch.

**Verdict:** RELEASE CLEAR
