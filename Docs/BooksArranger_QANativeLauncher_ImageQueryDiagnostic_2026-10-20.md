# Native image-query failure — bounded read-only finding

2026-10-20. No process/native/PID/RNG probe, retry, cleanup, configuration/security change or code edit. bc2a terminal exit1 is NOT native closure. Old groups and compiler NO RESULT remain unchanged.

## Exact saved evidence

C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/native-fixture-diag-bc2a3b11-0186-416c-93f7-2a7d483ca903/owner-result.json SHA256 074ae4c4f2ad5062eaf96044ee0af8a17c1301da130a74e82220c7f72d33a150. Returned code2/okfalse/closedfalse/forcedtrue/timedOuttrue, elapsed570001.4118, reason and closureError Native executable image query failed, native:null. Same-instance owner evidence closedfalse/native:null/failure same, close_errors empty. Empty close_errors is not identity or Jobzero proof. Entropy controller error is a separate earlier captured failure; no causal link to image query is proved.

## First substantive source finding

engineering-owner.mjs SHA256 f7b9db56437eca8f607e66d01ef7edd1877f586dbfac9a05d7b90b02fa384a1f. api.identity combines GetProcessId, GetProcessTimes and QueryFullProcessImageNameW. sample calls identity for already-retained handles before checking signaled status, then again for every retained member in its final identity/signal loop. close calls sample again. Thus an image query failure can occur during initial admission, new-member retention, retained resampling or final close; saved generic text cannot distinguish these phases or the affected retained object. No exit-race, buffer, rights, ABI, process-state or OS cause is established.

The native wrapper throws generic text immediately on false image return but never captures GetLastError or bounded owner phase/expected PID/prior validated identity. This is the concrete observability gap. Both member0x00101000 and supervisor0x00101101 masks contain documented PROCESS_QUERY_LIMITED_INFORMATION0x1000; the source does not support diagnosing absent required query rights. Buffer is1025 UTF16 characters with an in/out DWORD capacity; that observed source shape is not proof of successful ABI/native execution.

[Microsoft QueryFullProcessImageNameW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-queryfullprocessimagenamew) specifies query-information or query-limited access and GetLastError on failure. [Microsoft process access rights](https://learn.microsoft.com/en-us/windows/win32/procthread/process-security-and-access-rights) defines0x1000 query-limited and synchronization rights. Neither document establishes the actual cause for this saved run.

## Finite diagnostic correction proposal — review before source change

Add bounded explicit failure facts at the existing native API edge: api QueryFullProcessImageNameW, native uint32 last-error captured immediately on that failing thread before another Win32 call, input buffer capacity and available returned length, exact expected PID, requested rights, and owner phase (initial-supervisor/new-member/retained-list/retained-final/close-sample). Carry only already-validated prior creation identity when it exists; no follow-up native probe merely to fill diagnostics. Bind the failure to the original owner/invocation. Use a reviewed Koffi/native binding that preserves the failing thread error. Unknown/missing last-error must remain explicit unknown, not synthesized.

Extend only the small explicit diagnostic whitelist needed for those typed facts; preserve the original error even when capture fails. Keep existing identity/image/membership/wait/checked-close refusal unchanged. No cached-image acceptance, broader process rights, PID reopen/adoption, arbitrary process termination, error-code special-case or nativezero waiver is proposed. Any eventual behavior change about retained post-exit image validation would require a separate actual failure proof and independent lifetime/identity review.

### Meaningful source/pure fault matrix

Initial supervisor image failure → typed admission phase/rights/expected PID, rejected handle never terminated. New listed member failure → exact original private Job refused. Retained-list/final/close resampling failure → distinguish phase using prior validated identity, remain closedfalse/nativeunknown. Native last-error0/malformed/unavailable → explicit unknown/capture failure, never invented cause. Error capture/serialization failure → original query failure retained and all existing safe cleanup attempted. Successful image path → unchanged identity/evidence shape and validation. Wrong PID/image/creation/reused PID/close failure controls remain. Pure API fakes are not native proof.

After source review and final immutable pins, only a separately reviewed distinct new operation could supply actual API-edge evidence; this note authorizes none. Do not retry/reconcile old groups, mutate old artifacts or infer closure from terminal tool exit.

Only this report created. Bound f528/c194/21 source inputs, app, runtime, hooks, ACLs and scratch evidence untouched.
