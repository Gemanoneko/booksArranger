# Protected Books admission — finite design, STOP before implementation

Design only; no Sources31/native/runtime change or execution. `dispatch-books.mjs:25–26` still refuses. Engineering-owner-v3 does not automatically apply to the C++ watcher.

## Exact future source ownership

After review/freeze, Ender admission owner: new `scripts/qa-native/protected-admission.mjs` (fixed validation), new `protected-admission-native.mjs` (native proof consumer, no arbitrary executor), and only `dispatch-books.mjs::verifyBooksGuard(raw,{policySHA})`. Primary owns provisioning; Sully later pins. No current ownership changes.

Return existing `{status,stdout,stderr}` only after the flow below; missing/unknown/drift/unresolved denies Books only. No submitted proof boolean, imported unverified module or default allow.

| Stage / proposed private API | Accepted evidence; fail-closed boundary |
| --- | --- |
| `validateFixedRequest(raw,heldPolicyBytes)` | Existing exact command/registry SHA, studio cwd, Git Bash, login false, no TTY/extra envelope; entry only. Other operations remain disabled. |
| `freezeAdmissionInputs(policyPin)` | Hash and parse **same native-held manifest bytes**; bounded schema, full identity/ancestry/streams retained. No reopen/hash-then-parse substitution. |
| `verifyFreshProtectedInstall(heldInputs)` | Fresh protected-root birth/owner/DACL/full IDs, ordinary streams/links, complete enumeration and binary/runtime/bootstrap/registry hashes. Descriptive install JSON is not a capability. |
| `bindFixedEntry(heldInputs)` | Existing registry/guardian validators: exact source/run-parent, context/plan, Node/Koffi/five helpers and canonical `run_entry_checks.mjs --context ABS --context-sha HEX --run-root ABS` graph. Reviewed source/npm/Git loader/config closure remains required; PATH/shim alone is insufficient. |
| `verifyOwnedAdmissionClosure(...)` | Proposed **POST-execution result** acceptance: actual original ownership/invocation/inputs/pipes; complete Job zero, retained waits signaled, bounded output/EOF/result and closed leases. JSON/PID absence is insufficient; no image/birth-v3 inheritance. |
| `emitExactHostDecision(...)` | Proposed **PRE-tool fixed-launch** admission only after applicable frozen/protected-input proofs; preserve original host/stdio/cwd/timing/fallback. It cannot claim future native closure or admit raw canonical/npm commands. Phase separation requires Senua's ruling. |

## STOP: native closure versus pre-execution allow

Current C++ accepts fixed **entry** and runs QA; running it inside PreToolUse would run QA twice. Proposed option for Senua review: PRE admits **only the fixed protected watchdog/direct protected entry**, after applicable input/bootstrap/command proofs; the actual tool command owns **one** QA execution; POST independently accepts its actual native closure/result. PRE does not prove POST. Reject raw/unwrapped canonical/npm commands; no hook rewriting, consumed-command semantics or extra verify-only mode. This is a **new phase-contract proposal**, not an approved reading of NativeLauncher. Until Senua resolves the ownership/result-correlation boundary, the verifier stays denied.

Primary's boundary: `inspectAndFreezeInstallManifest` → `createFixedProtectedLeaf` → `copyCreateNew` → `finalizeDisabledInstall`; receipt is descriptive, never execution authority. Companion provisioning design SHA `b4d587977a502f4e6826fdebe45ff7a0f3e8fb2fb32d904bbfcbbf794af215a3`. Native backend/quiescence remain unbuilt; no automatic global CAS/rollback. Builds/native fixtures can prepare a pinned **disabled** bootstrap packet, not replace fresh root/runtime/Git/host-equivalence proofs or this missing verifier. Privileged quiescent host patch remains separate.

Negatives: swapped manifest/root/ancestor; split hash/parse; ACL/ID/stream/link/pin drift; wrong context/argv/env/graph; replayed invocation/pipe; incomplete membership/unsignaled/non-EOF/overflow/deadline/close failure; malformed host result; unchanged non-Books fallback. Pure and later native evidence remain separate.

Sources: current NativeLauncher doc §§Implemented source/remaining gates; dispatch/operation contracts; `launch-books-qa.mjs` validators/main; previously read C++64–75. No execution/deployment authorization.
