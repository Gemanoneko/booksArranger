# Native operator review — Books Arranger v0.24.5

Reviewer: Senua. Date: 2026-11-04.

This bounded review certifies the exact Docs-only operator and fresh plan below for one previously authorized PA-1 hidden check. It does not execute that check or grant its behavior verdict. Product source, build and canonical harness remain unchanged; the accumulated product code review remains `BooksArranger_CodeReview_v0.24.5_2026-11-04.md`.

## Exact binding

```text
Product source: bf4425de09c355d2a0743771ca4209b24c8f0de1
Build ID: c2d002ed-118f-47c1-8364-39a8f6d91352
Product digest: 509fcca6bf4c909827bd815cd6c6b3bcce4aa111e085f9eec0186e4bb6c7b156
Artifact manifest SHA256: 0c01cb73b9ed7b4adc7e6eeccdbb30b1c933a99ccf554af5fbf0aca4b0a09133
Operator: Docs/Evidence/v0.24.5_2026-11-04/native-recipe/native-once.mjs
Operator SHA256: 3de1a8b3f15f6390cf6ed64e461478be542219af38b51a31bd209658201bd3c3
README SHA256: 812837dcfd3e3adfc305cbf014e2149caa963c1919d09620fd1647dbb521168b
Plan: C:/Antigravity Projects/qa-native-0245-bf4425d-20261104-r2/plan.json
Plan SHA256: 28c75f6affd1c3ef4b2cad87001e3238e1b8bc9ebbff426a717aa8167b92370e
Plan bytes: 512730
Authority SHA256: f73091370ee27d1c210417360d28940fbe90b683360dbf1b4bd5c73a5c1b4c43
Original full PASS receipt SHA256: 863a9308de6de34f32fea6ac1a14b3abca46243d9146ab303f5c2df549fcedb5
Canonical phase contract SHA256: 63fbc25237be6b9a548a6cb5d0d83ba53b473b86a8d00d6b265beb5fa3f00e3f
```

Senua independently read and hashed the operator, README, actual plan, authority and original full PASS receipt. The four canonical phase/support/test code hashes matched the operator's fixed pins. The actual stored operator path uses forward slashes, names this exact operator, and satisfies the admission path comparison. The plan binds this source/build, has no recovery mode, and confines the fixture to `qa-native-0245-bf4425d-20261104-r2/pa1-c2d002ed-118f-47c1-8364-39a8f6d91352`. At pre-admission inspection only `plan.json` and `authority.json` existed in the fresh arena; the launch marker and fixture were absent.

## Review

| Dimension | Status and evidence |
|---|---|
| Security | Pass. `execFile` uses a fixed executable and argument array, without a shell. The operator checks its own hash and exact plan, candidate and full-receipt bindings. Canonical input verification checks file identity, ordinary ancestors, hashes, complete source/runtime trees and payload membership before native admission. Multiple hard links are admitted by preparation only for the five named Windows DLLs, with exact identity/link count pinned for canonical verification. |
| Correctness | Pass after the resolved path finding below. `run` invokes the unchanged canonical `--run`; `accept` uses unchanged `evidenceSummary` and `validateNativeEvidence`. No output is rewritten into a synthetic PASS. |
| Crash/stability | Pass. The real outer callback records raw Buffer streams, errors and bindings. The outer call has a 600000 ms timeout and 32 MiB cap. Canonical work retains the original finite deadline and kill-on-close Windows Job ownership. A timeout, missing result, incomplete output, force, or unknown closure cannot pass acceptance. |
| Performance | Pass for this bounded operator. Metadata/input verification precedes native admission; no new workload, wait increase or test graph is introduced. |
| State/data safety | Pass. Writes use exclusive creation. The one-use marker precedes launch, and canonical fresh-fixture handling refuses an existing fixture. The operator has no deletion or recovery path. Registry cleanup remains the unchanged canonical same-handle deletion of one exact newly created own leaf after normal closure; preexisting leaves and prior history bytes are checked unchanged. UIOrderList is never written, and only the authorized one added 8-byte ID reference remains. |
| Input handling | Pass. The actual plan has exact fixed roots, private profile/cache/TEMP paths and fixed PA-1 identity. Launch re-verifies all pinned inputs. Acceptance binds twelve original roles, actual callback hashes and stream bytes, normal inner/controller native zero, ordered functional assertions, postflight and cleanup proof. |
| Maintainability | Pass. The Docs operator wraps existing canonical preparation/admission/evidence contracts rather than changing them. |
| Doc/code drift | Pass. The README names the corrected operator and fresh plan hashes and supplies matching one-use commands, failure behavior and scope. |
| Build/release hygiene | Pass. This is a Docs-only operator review for the already verified r3 artifact. Full QA passed on the exact source; native behavior remains Futaba's separate result. |

## Resolved finding and limits

**NO1 [Major, resolved before launch].** The initial operator at SHA256 `d72fc2d2acff775dffcff62dbd7923c6c6ea93b1b30ade877cd932591b01d057` stored the operator pin with Windows backslashes but compared it with a forward-slash path in `readPlan`. The actual old plan therefore would refuse with `Operator differs` before writing the launch marker. Senua immediately held the invocation and notified Jane, Ender and Futaba. Ender normalized stored pin paths and prepared the separately named fresh `-r2` arena. The final operator/plan above satisfy the exact comparison. No hidden invocation was consumed by this preflight finding.

The old arena contains its two preserved metadata files. Its cleanup planner refused that target, so no deletion or alternate deletion route was used. The fresh arena does not adopt or modify that old metadata. This review does not authorize removing the old arena or shared `q` inputs.

The existing user authorization, relayed explicitly in Jane's review brief, covers one hidden private app, the deliberately invalid installer attempt, exact own new HKCU tray-leaf cleanup, and one added 8-byte numeric history reference while preserving the old bytes. The authority records those effects and labels its timestamp as preparation time rather than inventing an old approval timestamp. No further user authorization is required by this review.

Senua performed read-only code, hash and metadata inspection only: no operator preparation/run/accept, native adapter, application launch, test, focus or live-library action. Futaba received the exact final operator/plan clearance before this report was written. Any invocation failure must stop, preserve the original evidence and be reported; this review grants no second invocation or recovery. Raw foreign registry baseline values stay private and are excluded from portable evidence.

## Verdict

Open Critical: 0. Open Major: 0. Open Minor: 0. Safety floor intact.

**Verdict:** OPERATOR CLEAR

Clearance applies only to the exact final hashes above and one canonical hidden invocation. The subsequent native evidence must pass the unchanged consumer before any behavior GO or publication.
