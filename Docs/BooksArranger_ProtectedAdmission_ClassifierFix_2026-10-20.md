# Protected admission classifier — two Major fixes

Source-only response to Senua review `34f1ded592446b998adf55e4cda947f444069291ef468322a68cb01151b3a54d`, pin `830c396e1f1395d297410385e3bbd6c6b4e1c06a`. Only PRE module/checks changed; this new evidence file records the result. No existing dispatcher, host, native watchdog, package/import graph or POST module was edited.

`classifyRequest` now identifies Books before calling any strict Books admission validator. The existing `tool_input.cmd/workdir` identification tolerates absent observation fields and unrelated host metadata. Unrelated data returns the exact original input. Unknown/malformed transports return opaque fallback with `integration_stop:true`, unless finite Books identifiers establish a denial. This is no trusted transport decoder: no command/cwd alias authority was invented. Original-owned routing retains priority. `payload`/`validatePreRequest` retain the exact five-field watchdog envelope and policy checks; missing fields and host metadata still cannot admit Books.

The finite executable/argument target set now includes `run_entry_checks.mjs`, independently of context arguments. Direct absolute/relative paths, ordinary supported quotes and Windows separators deny. Search/echo/file-read mentions remain opaque data; unsupported executable syntax and Books wrappers retain denial.

## Reproduction and checks

Before edits, all four focused controls failed: unrelated echo with only cmd/workdir/login and the same request with host metadata returned deny; absolute quoted and relative direct checker paths at studio cwd returned fallback. After edits, both unrelated requests return byte-exact opaque fallback and both checker paths deny.

Existing in-process Node kernel, fresh file-module imports without reset: **71/71 pure checks PASS**, `native_executed:false`, `admission_authority:false`. Coverage includes unknown transport/alias bytes and integration STOP, original-owned priority, missing-field Books denial, metadata-wrapped Books strict refusal, direct canonical checker variants, quoted data, prior wrapper/syntax/policy/fixture-lease controls and unconditional production refusal. No OS/process/native/RNG/compiler/global/app-data action. No current owner/native behavior or formal QA claim.

## Pins and consumers

| Owned source | SHA-256 |
| --- | --- |
| scripts/qa-native/protected-admission.mjs | d9a7c09c56809a7c0fe26c5a5fc4d1b0bfc46eec8421277550d87ed31ea2148c |
| scripts/qa-native/protected-admission-checks.mjs | 411fc8e9998a2d34aba8d9a7f067baf6b0c38de74d4148b408e47226a5128f06 |

Scoped consumer map: `runAdmissionChecks(api,assert)` invokes the supplied PRE API; `validatePreRequest` invokes `classifyRequest`; fixture-only `exercisePreBoundary` invokes `validatePreRequest`; production `verifyProtectedAdmission` invokes only the unconditional missing-capability refusal. No integration consumer was added. Exact literals controlling this fix are `tool_input`, `cmd`, `workdir`, `run_entry_checks.mjs`, `opaque-fallback`, `integration_stop` and `native_contract_missing`.

Still missing: measured actual hook transport/default-shell binding and genuine native admission capability. Production continues to refuse `native_contract_missing`. Proxy-trap protection is not claimed for trusted fixture object APIs. POST framing and source/runtime policy definitions remain separately owned work; this fix grants no protected admission or deployment authority.
