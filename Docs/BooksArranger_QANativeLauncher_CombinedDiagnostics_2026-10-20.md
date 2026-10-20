# Combined finite diagnostics source checkpoint

Source implementation under pinned entropy ruling b9f9a9271478fd02c3d5db8680b6dd79c306ea2f and image-query ruling a545c86bf6c6b3f349cf46d823c167c4ea6d2d24. No native operation/process/probe/compiler was executed. Five of21 source files changed; all other source/runtime/case/deadline contracts remain fixed.

## Exact one-call owner-ID instrumentation

Controller validates original remaining time, then checkpointOwnerId persists owner-id-start in the existing creation-owned evidence directory before exactly ONE supplied unchanged newOwnerId call. Start failure means zero calls. The catch encloses only that call; safe owner-id-error is best effort and the SAME original thrown value is rethrown even if error serialization/write/readback/close/reserve fails. No fallback/random-provider/cache/environment change. Successful return continues existing inner-start/owner creation. Inner budget is recomputed from SAME absolute deadline after these added writes, so their delay consumes existing time.

Fixed new files per kind nested-final,linger-root,flood,wait: evidence/diagnostic-owner-id-start-<kind>.json and evidence/diagnostic-owner-id-error-<kind>.json. Both retain outer_owner_id as provenance and deliberately omit owner_id before the inner identity exists. Fixed allowlist/CREATE_NEW prevents path escape or overwrite. No record grants closure.

## Image-query failure context

queryImageOrThrow executes existing synchronous QueryFullProcessImageNameW once, and on false immediately calls previously bound synchronous kernel32.GetLastError before cleanup, formatting, additional native queries or logging. No query retry, access change, cached identity, wait reorder, PID reopening rule change or error-code acceptance special case. Error0/missing/malformed/throw is explicitly unknown (win32_error:null with unknown-zero/unknown-malformed/unknown-capture-threw); a positive uint32 is labelled preserved-koffi-sync. Native behavior remains unrun.

Static preservation evidence: installed Koffi3.3.2 package SHA80d8fbff4730e3314f3036fefd5af0d89203ed8a01c61d134727f1d38a16d72b; pinned src/koffi/src/interp.cc SHA809a3b7e401e0446fe205257721d35060b7427720240eb04aae5f7fdb6c0b073, WRAP lines345–348 restores thread LastErrorValue from TEB EnvironmentPointer before the native expression and saves LastErrorValue back after it. Installed CHANGELOG SHAfd904cd4f1693326035d246661df95349a9fc953138c1db8fab2409f2c5fa0be records protection since2.6.10;3.2.0 adds async callback support, unused here. This corroborates [official Koffi changelog](https://koffi.dev/changelog), [misc documentation](https://koffi.dev/misc), [QueryFullProcessImageNameW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-queryfullprocessimagenamew), [GetLastError](https://learn.microsoft.com/en-us/windows/win32/api/errhandlingapi/nf-errhandlingapi-getlasterror). koffi.errno() is not used. No addon binary/source equivalence or runtime/thread observation is claimed.

Bounded diagnostic schema: schema,owner_id,phase,subphase,expected_pid,requested_access,input_capacity=1025,returned_length nullableuint32,prior_validated_identity nullable exactpid/creation/image,observed_pid nullableuint32,observed_creation_filetime nullable exactpositiveuint64,win32_error nullablepositiveuint32,error_capture_status. Phases initial-supervisor/new-member/retained-list/retained-final/close-sample; fixed subphases initial/new-member/retained-list/retained-final/reuse-check. Initial observations are explicitly observations, never prior authority. Prior identity is allowed only when actually already validated; strict contexts/known two access masks/getter/proxy/unknown fields refuse. No native handle/pointer is serialized.

The actual owner retains the FIRST valid typed image_query_failure; a later close_image_query_failure is separate, never replaces it. Malformed/unavailable context sets image_query_diagnostic_unavailable and original generic query failure still propagates. Terminal evidence and16MiB diagnostic serializer explicitly whitelist these three optional descriptive fields; original native acceptance shape/membership/kill eligibility/cleanup/closedfalse uncertainty remains unchanged.

## Pure controls and limits

Passed in-process exported checks: owner52, diagnostic59, plan14, existing49. Native API fakes exercise every phase, immediate last-error ordering before a deliberately clobbering cleanup,0/negative/overflow/fractional/missing/string/throw capture, inconsistent context, first failure plus different close failure, rejected-supervisor no-kill, and success unchanged. Entropy fakes cover one-call order/count, all start refusals→zero calls, identical original rethrow across diagnostic failures/unsupported error values, fixed paths/collision and consumed delay. Serializer/fence/quota/reserve/overrun and old cleanup controls continue. A negative assertion was corrected because a later separately VALID close-sample failure may be retained after refusing an invalid assignment diagnostic; no acceptance floor was relaxed. Pure checks do not prove native behavior.

Pure receipt: C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/qa-native-fixture-plan-v1-VzIVqp/combined-diagnostics-pure-receipt.json SHAc25f08ec9a94737581be8f3b394b8be5b8184d39b600c9f12814dc272af2c353.

Original total600000/outer570000, original inner reserves, strict598000 capture admission and16MiB quota unchanged. Late OS/IO remains refusal; no whole-invocation startup bound or formal QA claim.

## Frozen new candidate

Candidate C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/qa-native-fixture-plan-v1-VzIVqp/native-fixture-combined-diagnostics-candidate-plan.json SHAd38c846de31ebd55163a5504c326823d9532c4d5716564ffbb394767e60be592, UUID2f4cb056-1538-49f1-b827-b570f725a61f, controller C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/native-fixture-2f4cb056-1538-49f1-b827-b570f725a61f, diagnostic C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/native-fixture-diag-2f4cb056-1538-49f1-b827-b570f725a61f. execute_reviewed=false, admission=zeros; compiler/new_binary/global_changes/reuse remain false. Review actual source then separately review an enabled-plan delta/exact argv and obtain Jane instruction before any future group.

Exact SOURCE-REVIEW-ONLY defaultPowerShell proposal (shell omitted):

```json
{
  "cmd": "& 'C:/Program Files/nodejs/node.exe' 'C:/Antigravity Projects/Worktrees/Books Arranger/electron-m1/scripts/qa-native/native-fixture-observer.mjs' --plan 'C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/qa-native-fixture-plan-v1-VzIVqp/native-fixture-combined-diagnostics-candidate-plan.json' --plan-sha d38c846de31ebd55163a5504c326823d9532c4d5716564ffbb394767e60be592",
  "workdir": "C:/Antigravity Projects/Studio Illuminati",
  "login": false,
  "yield_time_ms": 10000,
  "max_output_tokens": 2000
}
```

Old actual bc2a diagnostic C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/native-fixture-diag-bc2a3b11-0186-416c-93f7-2a7d483ca903/owner-result.json SHA074ae4c4f2ad5062eaf96044ee0af8a17c1301da130a74e82220c7f72d33a150 and terminal receipt176bdd54b69aa1c3210b90dd3c8e0f7539aa2c3393071d048dab67ca4acf22ce are preserved. bc2a and earlier0980 native closure remain UNKNOWN; old compiler NORESULT unchanged. Neither diagnostic guesses a cause or retroactively proves closure. No old arena reuse/cleanup. Bound f528/c194 reviews stay unchanged.
