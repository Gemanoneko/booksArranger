# Books Arranger QA — v0.9.1 (2026-10-11)

**Verdict: GO**

Final endpoint: frozen candidate-v2, 65 files, source digest `094c584492175ebc10fada7c800082e0544eb5e2ee823e068f1656fb3410342f`, manifest SHA-256 `6a554ed673360ac5297e1c6085459e69f9bd9a5b829039ae2243ba3f64bebce8`. Source version 0.9.0, target 0.9.1, HEAD `aea54f581d571ec308edc2bd4aa429d2069cff62`, dirty=true. QA used immutable private copies, never the shared working tree.

The original runtime exception was discarded, so its historical cause remains **UNKNOWN**. Cached Wendigo replay returned ordinary uncertainty; that replay does not reproduce or explain the exception. This patch is verified for diagnostic recording, truthful failure state and retry boundaries.

## Executed checks and evidence

| Scope | Producer | Independent receiver | Outcome |
|---|---|---|---|
| Accepted v1 full manual graph | 76 Python + 3 Node routes; 72.755 s owned | Same 8 commands; 70.404 s owned / 70.366 s manual | PASS; identical actual handoff line and identity |
| V1 independent private probes | — | 2 cases, 0.733 s test / 6.567 s owned | PASS |
| Final v2 changed checkpoint case | 1 existing case, 0.083 s test / 2.059 s owned | Identical case, 0.080 s test / 3.188 s owned / 3.152 s manual | PASS; identical actual handoff line and identity |

The v1 full graph contains 38 automatic-processing, 8 media, 10 grouping/filter, 14 HTTP and 6 merge cases, plus automatic/progress/recovery frontend Node routes. The three Node routes are VM fixtures. Private generated media uses actual FFmpeg and verifies successful output, source retirement, working-copy cleanup and registered 24-hour recovery; this is fixture conversion, not a real-library conversion or an elapsed 24-hour soak.

All executions used Senua-cleared fixed manual contracts, trusted native bootstrap, held manifest/source/runtime pins before imports, pinned media executable resolution, hidden owned process jobs, bounded output and a shared total 600000 ms deadline. Exact owned processes and drains closed, all commands exited zero, and post-run source/runtime pins remained unchanged. No paid connector, real library, production database, public network, signed-in browser, desktop focus, audio playback or Comics operation occurred.

V2 changes only `automatic_processing.py`'s nondurable failure reason and the existing checkpoint-failure assertion in `tests/test_automatic_processing.py`. All other 63 source pins match accepted v1. Its declared contract admits only the changed case; the full graph and independent probes were not repeated. This report certifies v2 through that exact delta and focused verification, with retained v1 evidence for unchanged behavior.

## Regression findings

- Unexpected research failure produces a safe record capped at 8192 bytes and eight frames. Class, time, phase, candidate and safe code location survive; untrusted raw exception text, private paths and credentials do not.
- The affected candidate and pass become **Needs attention**, current/researching state clears, and failure does not approve, enqueue or resume conversion. Existing source/job evidence remains preserved.
- Durable diagnostics and pending work survive a fixture restart. Restart stays idle; explicit retry continues saved work. Historical missing details remain accurately labelled as unrecorded.
- If checkpoint saving fails, the volatile record claims no durability; Start is disabled with **“Retry progress could not be saved; Start is unavailable.”** Retry help is absent. The existing case verifies Start refusal and no approval/conversion calls.
- Independent hostile exception formatting and a 21-frame traceback yield a durable 925-byte, eight-frame diagnostic without invoking custom formatting. Restart/retry remains safe and original fixture bytes remain unchanged.
- Independent ordinary uncertainty processes both candidates, Holds both, records no app failure and performs no approval. Normal uncertain results do not stop the pass.
- Existing confidence/evidence gates, candidate grouping, filters, verified conversion and recovery regressions pass in the accepted full graph. Interrupted work remains Paused rather than becoming an unexpected error.

**Blocker: 0 / Major: 0 / Minor: 0 open.** The reviewed v1 Minor explanation gap is resolved and verified on v2. No new layout or panel was added; existing details/copy semantics are checked by backend and unchanged frontend fixtures. No new rendered browser pass was needed for this text-only endpoint.

**Pattern alerts:** Lost diagnostic plus stale active status — **fix**, covered by this patch. Ordinary uncertainty misreported as app error — **accept existing distinction**, independently verified. Historical cause reconstruction — **defer**, insufficient original evidence; do not invent a cause.

## Exact manual receipts

Accepted v1 producer and receiver:

```text
BOOKS_MANUAL_QA|tool=Books Arranger|target=0.9.1|source=0.9.0|HEAD=aea54f581d571ec308edc2bd4aa429d2069cff62|dirty=true|source_digest=4436b4153232ba8d89e3a098774736aec4fdcdf741aa8f2ed8847cd0b3e1b227|manifest_sha256=98b05f7d5858225e6a0fcb5415c9343d36afc1c936f62736e46d557e7727dead|python=pass|node=pass|package=n/a(manual nonpackage contract)
```

Final v2 producer and receiver:

```text
BOOKS_MANUAL_QA|tool=Books Arranger|target=0.9.1|source=0.9.0|HEAD=aea54f581d571ec308edc2bd4aa429d2069cff62|dirty=true|source_digest=094c584492175ebc10fada7c800082e0544eb5e2ee823e068f1656fb3410342f|manifest_sha256=6a554ed673360ac5297e1c6085459e69f9bd9a5b829039ae2243ba3f64bebce8|python=pass|node=n/a(unchanged frontend; accepted v1 baseline)|package=n/a(manual nonpackage contract)
```

`package=n/a` is the honest Python-app manual contract, not a package script gate. Final Node n/a means unchanged frontend routes already passed on v1.

## Retained artifact identities

Paths below are relative to `scratch/automatic-failure-qa-2026-10-11/` unless prefixed sender; sender means `scratch/automatic-failure-2026-10-11/`.

| Artifact | SHA-256 |
|---|---|
| sender/sender-manual-receipt-v1.json | fcffad71dd8d3f8de530bbb0ade62265772ad6586cfdf145b118afb5f719d02f |
| sender/sender-owned-receipt-v1.json | 3471e974e52d4e071fac96069df067a64627f3de5d4d7a6eb05a53582e6d002f |
| receiver-manual-receipt-v1.json | bfc3f0a24bc0caa384d54dd1000f963a3092e74f77e60952c6b41433818f5d08 |
| receiver-owned-receipt-v1.json | 193df5097c38e0553b2169800be0539111c794ea718afb01b6b1b9dae0d65a39 |
| independent-check-receipt-v1.json | eb5d42bbe4464e80b1520b7d10c2889c25f9eddd1bf9aa28463836659d765f4c |
| independent-owned-receipt-v1.json | eeb49ef55e7c4eb01906273a6d9e468830ef3b98f13d9a0a95c0ca8f5bc99237 |
| sender/sender-manual-receipt-v2.json | 9d4f7ac37f72695184eb11ac6d4848e2c79a8102bceccedff7704d2eef9bb01a |
| sender/sender-owned-receipt-v2.json | 21b49acd2eaa5768a7f4515170995ff1dd84b13bfa99e63998421b14bd112260 |
| receiver-manual-receipt-v2.json | 85e34e854b8712e08af5651f4bb29165359636f64f3dbd6a32de0a1bd5129645 |
| receiver-owned-receipt-v2.json | 74556b36e12e79443c5bcc47ef4c9f808e1e9b2909ff81602470fcd992c33d6c |
| sender/manual-contract-v2.json | e29498625a80a4b153dfb2e33e01344f5cd7dfacc604e06130c994b7de27a371 |
| sender/qa_checks_v2.py | dea9f3a1c5aa3c07d1158683e5693c6af325f927980e03181a1461b690ed3505 |
| sender/run_qa_v2_owned.py | 25638a30b9a2f63a55e551a5379281d540f51665c335b7a4893774e3152d9609 |
| independent_failure_v1.py | 374cfa445fdb5c4621ce69a1de7b2e21ecc5ca3af0a865ae439cc52e9bc781da |
| independent_checks_v1.py | b0ac70d90911f24deda465c1ff65a0c37c2f313619c3b0dd9724170db78812eb |
| run_independent_v1_owned.py | a68bf9ee3a78419805ac52eed7eee2ba7b93820d26b6df107d2b0903099f344d |

Both snapshot copies, contracts, reviewed harnesses and unique receipts remain available for release consumers. Disposable cache removal is recorded separately through studio-cleanup exact native plan/check/remove/verify; cleanup does not alter this report's accepted evidence or final source identity.
