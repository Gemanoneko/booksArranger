# Books Arranger 0.24.2 — release phase tests

Status: authored and frozen, not executed. Only tests/release-contract.test.mjs and tests/release-flow.test.mjs changed, plus this note. No production scripts, runtime, controller, native support, release state, credentials or existing evidence were changed.

## Test inventory

- release-contract.test.mjs: 18 top-level tests. All seven original version, report, product digest, artifact, remote receipt, keep-four and acceptance-index cases remain. Eleven added cases cover mandatory native evidence from 0.24.2 onward, historical reader compatibility with current-version rejection, exact QA evidence hash line, valid in-memory proof, every candidate binding, authority and functional assertions, phase inventory, all ten raw roles, path/hash/size bounds, normal inner/outer closure, original execution totals/markers, callback/postflight/cleanup.
- release-flow.test.mjs: 17 top-level tests. All six original release-success, missing-candidate preparation, changed acceptance, remote hash failure, special Git entry and cleanup cases remain. Their release fixture now uses 0.24.2 with a complete coherent fake-native bundle, so the original assertions still reach their intended step after the new prerequisite. Eleven added cases exercise actual releaseFlow ordering and refusals through injected in-memory adapters.

Total: 35 top-level tests; nested mutation matrices are additional assertions, not separately counted test runs. Expected zero skipped tests. No pass claim is made. Static git diff --check returned zero with normal LF/CRLF notices; no parser, test process or native command was launched for validation.

## Contracts exercised

The production imports are scripts/release-contract.mjs, scripts/release-flow.mjs, scripts/qa-phase-contract.mjs and scripts/cleanup-releases.js. The flow must read the same-version native summary, verify the exact Native QA evidence SHA256 report line, validate all raw references and bytes, and accept source/version/product/build/artifact/runtime/phase bindings before verifyPayload or authenticate.

The fake bundle contains authority, plan, owned, controller_owned, callback, stdout, stderr, functional, postflight and cleanup records. Each reference hashes its actual in-memory bytes. Downstream cross-hashes are rebuilt after semantic mutations, so ownership/callback/cleanup negative cases fail on their intended condition rather than merely stale outer hashes. Plan data includes the lead's expected_tray_types field. The exact eight ordered PA-1 assertion identities are retained. The unit authority text explicitly says it is inert test data and supplies no actual native permission; no such record is persisted or passed to a native runner.

Negative flow checks require no payload verification, credential acquisition, remote API, publishing, preparation or cleanup call and no mutation of any fixture byte. They cover absent summaries/records; prose GO without the exact verifiable evidence hash; duplicate/stale hashes; changed raw records; traversal/absolute/cross-version/duplicate references; oversized records and summary; stale candidate fields; forced/timed-out/overflow/truncated/nonzero or incomplete owner closure; incomplete callback; changed postflight; partial/failed cleanup; wrong or missing authority; skipped/replaced/duplicated functional proof. Historical artifacts/reports remain parseable by their historical readers but cannot replace current publish prerequisites. Positive flow ordering proves all evidence reads precede payload verification, which precedes authentication and the injected publisher.

## Pure execution boundary

Before any production import, each test file replaces child_process spawn/spawnSync/exec/execSync/execFile/execFileSync/fork and ChildProcess.spawn, HTTP/HTTPS requests/servers, net/TLS connections/servers, sockets/agent connection methods, DNS calls, datagram sockets, Worker construction, global fetch/WebSocket/EventSource, os.userInfo and process.dlopen with counted throwers. syncBuiltinESMExports synchronizes named builtin imports before dynamically importing the release modules. The after hook restores every patched function, synchronizes bindings again and requires the native-attempt count to remain exactly zero.

Every release IO method is an injected recorder operating on in-memory strings/Buffers; no gh, authentication, registry, CIM, Windows API, installer, shell, app, network, library, tray or profile call is made. No private fixture files or directories are created by the tests. Path strings in fake records point under the allowed shared/release-tests arena but are never opened. The cleanup test injects a fake API and verifies its call sequence only.

## Execution handoff

Execution remains blocked pending a new concrete source/runtime/ownership pinned batch and specific reviewer admission. Existing geometry or previous release-native approvals are not reusable execution authority for these changed tests. The lead owns preparation of the new batch and all production fixes found by it. No source/helper/runtime changes are authorized by this test handoff. Normal owned closure and the unchanged 600000 ms hard deadline remain required; no full entry, build, release, credential or publication action is performed here.

## Lead follow-up: PURE-2 actual result

The original 35 release cases were retained. Two additional wrong-stream-layer regressions bring release-contract to 19 and release-flow to 18; their fixtures now bind twelve raw roles and deliberately distinct inner/controller streams. Both suites passed in the exact PURE-2 invocation on 2026-11-01 (37/37, no skips or failures), together with 26 phase-contract and 6 assembler cases (69 total). Their pre-import native/network/process guards and zero-attempt after-hooks passed. Full postflight and original normal complete-zero ownership passed; this is pure targeted evidence, not actual PA-1 or release permission. Exact plan, source and raw receipt hashes are in BooksArranger_0.24.2_TargetedEvidence.json.
