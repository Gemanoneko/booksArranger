# Books Arranger native fixture diagnostic loss — bounded finding and correction proposal

2026-10-20, Ender. READ-ONLY diagnosis; no source edit, process/native probe, rerun, PID cleanup or compiler. Old group remains **NO RESULT / native closure unknown**. Source/ruling pins are unchanged.

## Actual evidence

Approved plan SHA2564bae6efa3e8f75915d223b797d9117173b20381ffa69b18161c93c9ea6487b78. The one accepted default-PowerShell invocation ran in session5784 and ended with tool exit1 and combined output: Native fixture observer REFUSED: Owned operation failed or uncertain. This is not observed observer exit0 and not a native closure proof. No separate native Node exitcode telemetry was exposed.

Exact terminal observation C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/qa-native-fixture-plan-v1-VzIVqp/invocation-default-powershell-stop.json SHA256159290531aed5d4b204710118ad309c7a6f1fe8ceb63d65beef17204a3e5a1ef. Tool output SHA256064c167389fe9332db9e2c4a308f67e7ad7051fae429ce689516032a189694ee. Planned root contains only evidence and tmp; evidence contains only startup.json,14669B, SHA256054fc69689da271fdb0c444c73cb90b0cbeb12c43840557ddf3f17c7575e1fb1. No work/final/completion or actual nativezero/checkedclose proof is saved. Startup is explicitly nonauthoritative. Read-only source/evidence finding JSON SHA25649cb01999aa3d9c152adaf1d51769482092f39ec145380995b320483c9cfc0fb in same plan directory/readonly-diagnostic-loss.json.

## First substantive source finding — stop here

Native fixture observer line16 obtains actual runOwned result. Line17 obtains same-instance owner.evidence() and immediately calls validateOwnedResult BEFORE either is persisted. Engineering-owner line75 combines ok/closed/forced/timedOut/overflow/truncated/closureError/reason/error/signal/code into the first generic refusal observed. Observer catchline26 prints only that message. At least one first-predicate condition failed; the returned diagnostics and actual terminal snapshot then died with that process. It is impossible to distinguish a closed safe refusal from unknown/failed native closure using the surviving message.

Controller startup is written atline18, then pure phase executes without a checkpoint. Inner result/evidence atlines24–25 are validated before any per-case diagnostic record. Its uncertainty finallyline40 can retain leases while waiting for original outer termination without saving the reason/result. These are concrete observability omissions. They do NOT establish which path occurred in this run. No saved facts prove the first actual native fault, pure phase completion, nested assignment success or a specific timeout/close error. No broader cause investigation is justified from this evidence.

Source pins: observer379539ec82a834e9eadf54b3359405f4550b22fa065a7a46a85dd0965de7f11e; ownerf7b9db56437eca8f607e66d01ef7edd1877f586dbfac9a05d7b90b02fa384a1f; controller5deac1bea981fccd8a38744c303b2d88f482d50ac800d77007e25642c3ee9b48. Existing owner/lease/identity/closure floor is not weakened by the proposal below.

## Finite source correction proposal — review before implementation

Scope only current fixture observer/controller, one small shared bounded diagnostic serializer if needed, focused pure checks and this note. No owner algorithm rewrite, generic executor, protocol extension for operation authority or canonical helper change. Primary technical owner/Senua must approve/pin before edits.

1. Observer captures whitelisted actual returned runOwned fields plus same-original-instance terminal evidence BEFORE validation/throw. Preserve reason, closureError, error, code/signal, ok/closed/forced/timedOut/overflow/truncated, pid/ownership/native/elapsedMs/outputBytes and captured bounded out/err/supervisorErr. If evidence() fails or is null, record that fact, never synthesize evidence. OwnerUUID/invocation/plan/source and stage bind the descriptive record.
2. Failure data must use a native creation-owned observer diagnostic namespace whose exact root is declared in the NEW plan and held with original native ancestor/directory fences throughout. Prefer one fresh fixed-prefix native-created leaf under session shared, separate from the controller root so pre-controller failure can still be recorded. Reuse existing Leases/native FILE_CREATE/FILE_CREATED/CREATE_NEW/flush/readback; do not write by failed/untrusted wire pathname. All collision/identity/reparse/default-stream/close uncertainty refuses, no adoption or cleanup. Primary chooses exact finite namespace contract before code.
3. Controller writes fixed unique stage checkpoints within its already creation-owned evidence namespace: pure-start/pure-complete, inner-start(ownerUUID/kind), then actual returned inner result/terminal evidence immediately BEFORE closure validation or uncertainty wait. A bounded outer failure capture must not depend on this optional inner record existing. No caller JSON or preliminary checkpoint acquires authority.
4. Records are explicitly NONAUTHORITATIVE with no success/accepted grant; they describe the actual failed owner instance, never recreate a live capability or retroactively close old work. Actual original native facts remain the only source of closure. Closed-refusal may be described only if returned facts prove it; null/failed/overbudget facts stay unknown. Original inner-uncertainty lease hold and outer deadline remain unchanged.
5. Serializer uses explicit own-field/type/size whitelist and one fixed encoded byte quota (proposal16MiB covers two capped4MiB snapshots plus existing capped1MiB combined output and JSON escaping). No truncation or partial-proof claim. Unexpected/circular/nonfinite/oversize data yields explicit diagnostic-serialization/refusal metadata, never fabricated fields. The exact quota is technical-owner/reviewer choice; any changed constant returns for review.
6. Native CREATE_NEW/flush/same-held readback/checked close is required for the journal. Serialization/native write/flush/readback/close failure has an explicit bounded refusal path with stage and diagnostic error on stderr; no unfenced path fallback. Budget reserve exhaustion/overrun does not extend600000 or release uncertain leases to obtain a log. A partial/late diagnostic artifact remains evidence only, never acceptance. Trusted final ordinary OS IO limitation stays explicit.
7. All resulting source/plan/admission/invocation pins return for independent review. Future actual run must have a DISTINCT new UUID/root/immutable plan and reviewed exact invocation; this old group is never retried or claimed closed. The old failedshell record and earlier compiler NORESULT also remain untouched.

## Required negative/source check matrix

| Injected condition | Required descriptive record and control behavior |
|---|---|
| result.ok false but nativezero/checkedclose true | Save exact result/evidence before throw; label refused, never passed |
| closed false/null native/forced/timeout/error/nonzero | Save actual corresponding fields, no synthesized closure |
| evidence null or evidence() throws | Record missing/error provenance, not callerJSON ownership |
| Native same-instance snapshot mismatch | Save both bounded snapshots/digests before refusal, no correspondence grant |
| Pure phase fails or inner result uncertain | Stage checkpoint and inner returned diagnostics precede existing hold/wait; same outer owner retains bound |
| Record serialize/circular/oversize/nonfinite fault | Explicit bounded diagnostic refusal, no truncation or partial identity proof |
| Wrong/replaced diagnostic root/ancestor or CREATE_NEW collision | No redirected write/adoption; stop under native floor |
| Journal write/flush/readback/close failure | No durability claim, bounded error, no path fallback or PASS |
| Reserve exhausted or final IO overrun | No timeout extension, no success artifact, unknown/no result retained |
| Standalone checkpoint/diagnostic file | Cannot satisfy validateOwnedResult, joint actual observed exit0 or native closure |

Pure fakes verify ordering and refusal logic only. Any later native fixture/journal tests require their own reviewed source and exact invocation. No current process/PID probe, repair, new run or source edit is authorized by this proposal. The minimal finding is saved; stop diagnosis here and route the bounded correction for primary/Senua decisions.
