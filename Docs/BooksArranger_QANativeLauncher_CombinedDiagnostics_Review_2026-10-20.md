# Combined entropy and image-query diagnostic source review

2026-10-20. Static component review only; not RELEASE CLEAR, formal QA, compiler, deployment or production authorization. Packet SHA256 `8453335bf8016c1c83a1eaa9542bfd868a10f8a0cccf3acd303b9768b04133f4`. Reviewed the five changed source/test files under entropy ruling b9f9a9271478fd02c3d5db8680b6dd79c306ea2f and image-query ruling a545c86bf6c6b3f349cf46d823c167c4ea6d2d24. No tests/process/native probe/compiler executed by reviewer. All21 source hashes were stable before/after; final size/dev/ino/mtime matched. Wrapper and all four bound/design review hashes matched; installed Koffi evidence hashes matched.

## Scoped result

No new Critical, Major or safety-floor finding in this finite diagnostic delta. The one-call helper persists fixed owner-id-start before invoking the unchanged supplied newOwnerId exactly once; start refusal prevents the call. Only that call is caught; safe error recording is best effort and the SAME original thrown value propagates even when describing/logging fails. Pre-ID checkpoints omit an inner owner_id and keep outer provenance. The controller recomputes remaining budget after checkpoint writes, without changing its owner creation/uncertainty hold. No RNG provider/cache/environment/security change or cause inference is introduced.

The image wrapper makes the existing image query once and immediately calls previously bound synchronous GetLastError on false. Static installed Koffi3.3.2 interp.cc `809a3b7e401e0446fe205257721d35060b7427720240eb04aae5f7fdb6c0b073` WRAP saves/restores LastErrorValue across its native expression. This supports the intended synchronous mechanism; it is not addon/source equivalence or runtime/thread proof. Positive uint32 codes are descriptive preserved-koffi-sync;0/malformed/missing/throw remain explicitly unknown. No subsequent native call fills diagnostic fields.

Phase/subphase, expectedPID/access/inputcapacity, returnedlength, observed creation facts and optional actually validated prior identity are bounded and checked against the exact owner call context. Initial queried facts remain observations. The FIRST valid image failure survives separately from later close-sample failure and diagnostic-unavailable status. The terminal evidence carries only typed descriptive fields, with explicit serializer whitelist and quotas. Original failure/closedfalse/nativeunknown and checked cleanup survive malformed/capture errors. Successful image queries make no last-error call; native snapshot acceptance, image validation, membership completeness, validated-supervisor kill eligibility, wait ordering and existing PID reuse refusal remain unchanged.

Developer reports owner52/diagnostic59/plan14/existing49 in-process pure passes. Reviewed controls cover each image phase, capture-before-clobber, unknown error values, malformed context, first failure plus distinct close failure, rejected-supervisor cleanup, one-call order/count, same-original error propagation, collisions, budget consumption and serializer refusal. They are fake/API-contract checks, not native evidence.

## Exact source boundary

| Changed source | SHA256 |
| --- | --- |
| engineering-owner.mjs | `a9e97eb32bc65d17512d660f8250f368826d9117136b768e2f87d6361daca803` |
| engineering-owner-checks.mjs | `a767ea2721ea0f9ccad23047ec5209b34e779b71a62b339eb9e6e91784d0f798` |
| diagnostic-capture.mjs | `09bbff4589a175e6ec11d7c67ab029e2066d133db55d20e090329fb00ffcef63` |
| diagnostic-capture-checks.mjs | `4c59ab748dffedece25e4c0e5f61d98034c3a20e75c73aa5881f86c5f0c8f48b` |
| native-fixture-controller.mjs | `44603521b5fef137ec54c7fff0e234581b120c87d14046323c97a80edff37012` |

The remaining16 source pins and wrapper52234f6645b3ed9c80edf5f025821c4efe9334aac38fe47c732a87236d060f50 are unchanged. Exact full boundary is the packet; no wider accumulated release diff is certified.

## Conditional single next private group

Candidate SHA256 `d38c846de31ebd55163a5504c326823d9532c4d5716564ffbb394767e60be592`, UUID `2f4cb056-1538-49f1-b827-b570f725a61f`, has the exact21 source pins, execute_reviewed=false/admissionzeros, compiler/new_binary/global_changes/reuse=false. Its distinct controller and diagnostic roots are absent at the read-only checkpoint. Same95-file trusted-base manifest f44f4b51513bd4a50cdaacdd2167a66766beaf79292a9e653724ce01c8642b98, cases and600000 deadline remain.

One coherent NEW private fixture group is conditionally acceptable after Sully pins this review and a separate final enabled-plan delta/exact argv check: only execute_reviewed=true, source_admission_sha256=exact pinned review bytes, and descriptive purpose may differ. Freeze these admission bytes and allsource/runtime pins through terminal. Use literal installed Node/fixed observer/approved --plan and --plan-sha, defaultPowerShell with shell omitted, studio cwd/login=false/yield10000/max2000, only after Jane instruction. Poll the returned session; on any failure/uncertainty/refusal stop with evidence, no retry, PID probe/cleanup, compiler or old namespace reuse. This source review itself authorizes no execution.

The existing570000 outer stop, same absolute600000 envelope, inner reserve,598000 diagnostic admission and16MiB quota remain. Late OS/IO can refuse; pre-Job startup remains explicitly trusted and unbounded engineering startup, not formal QA or whole-invocation boundedness. Actual callsite/native error/thread/identity/Job closure/cross-close facts remain unproved until accepted native evidence. No cached-image acceptance, rights expansion, RNG workaround or closure waiver is allowed. Old0980/bc2a closure UNKNOWN and original compiler NO RESULT are unchanged. Bound f528/c194 reviews were verified unchanged and are not edited.
