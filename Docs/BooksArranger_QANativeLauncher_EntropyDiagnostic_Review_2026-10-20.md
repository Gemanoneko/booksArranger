# Entropy callsite diagnostic design review

2026-10-20. Design/source-placement review only; not release, native runtime, compiler, deployment or invocation clearance. Reviewed proposal SHA256 `40b76d25d8364e3cb0cb5f37d8fa99b32e35776de6ffbbc29e0cd791c3ccbd63`. The five named current source hashes match the proposal; no active source/admission input was changed. No native/process/RNG probe or test was run.

## Ruling

Accept the finite instrumentation design for local implementation ONLY AFTER the current bc2a group is terminal, Jane records its actual terminal evidence without inferring closure, and Sully pins this ruling. No new Critical/Major or safety-floor objection to the proposal under the requirements below. This is not acceptance of an underlying RNG/provider diagnosis: the saved error has no throwing callsite/stack and the first explicit randomUUID call is only a source observation. A start checkpoint proves stage reached; only the API-specific catch around that one call attributes its caught error to that invocation. No checkpoint proves kernel closure.

## Required implementation boundary

1. In the fixed controller owned(kind) flow, compute/validate the same remaining deadline, then persist the fixed owner-id-start checkpoint immediately before exactly ONE existing newOwnerId() call. Require successful start write/readback before making that call; a failed start means refuse the operation without attempting the RNG. Use the existing creation-owned evidence namespace, literal stage names and fixed per-case kind allowlist. Extend only the corresponding diagnostic stage allowlist/schema and pure controls. Use outer_owner_id/current outer owner as provenance before a new identity exists; never invent a child owner ID or treat that outer ID as the future inner owner.
2. Catch ONLY that one call. Attempt a fixed owner-id-error record with safely whitelisted actual name/message/code and the same group/plan/source-admission/per-case bindings. Rethrow the SAME original thrown value whether logging succeeds, fails, exhausts reserve, encounters unsupported error fields or native close errors. Logging must not replace the RNG error with a serialization/IO error or fabricate a native owner result. No fallback identity, alternate provider, random source, repeated call, cache option or security/environment change. Do not monkeypatch production crypto to obtain evidence.
3. Success continues the existing inner-start journal and existing createEngineeringOwner/runOwned/closure path unchanged. Do not move ownership/innerUncertain flags to pretend an owner exists before creation; do not relax the existing uncertainty hold for any already-created owner. Retain all current source/runtime/input leases and native close rules. Existing original600000 absolute envelope, outer570000, inner remaining calculation, strict598000 diagnostic admission and late-IO refusal remain unchanged. Added writes consume existing budget; no fresh deadline or extra termination grace.
4. Only fixed bounded nonauthoritative diagnostic data, no stack, environment dump, provider enumeration or dynamic paths. Start/error filenames are CREATE_NEW and bound to the literal kind; duplicate/collision refuses without overwrite/adoption. No attempt to modify/reuse old group namespaces. Absence of an error checkpoint means callsite remains unproven, not a success/closure claim.
5. After implementation, provide the exact frozen source/test packet and actual pure-control evidence for independent review. Any future native invocation requires a distinct new UUID/controller/diagnostic roots, source/runtime pins, admission bytes, candidate and enabled-plan delta plus exact argv review and Jane instruction. This ruling grants none of those execution steps.

## Required pure fault matrix

- Start record succeeds → fake one-call function succeeds → existing inner-start: exact order and call count1, same returned UUID, unchanged owner creation path.
- Start write/readback/collision/reserve fails: RNG call count0, no inner owner/process, fixed refusal.
- Fake one-call function throws known own code/message: start then API-error then identical original thrown object; no second call/inner-start/owner.
- API-error write/readback/close fails, reserve expires, getter/proxy/oversize/undefined error fields refuse: identical original thrown value still propagates and no invented child identity/proof.
- Per-kind filenames cannot escape fixed evidence root, duplicate fixed checkpoint cannot overwrite, different cases do not collide.
- Budget controls account for the added checkpoint delay, refuse at original admission floor, and preserve existing uncertain-owner lease hold/outer termination behavior. All fakes must be explicitly labelled; they do not establish actual RNG or native behavior.

## Source boundary

| Source | SHA256 |
| --- | --- |
| native-fixture-controller.mjs | `dd6c2535cdc9330302a6dc946cd42952174471b7845a81b248aa0d5c5e6fa106` |
| engineering-owner.mjs | `f7b9db56437eca8f607e66d01ef7edd1877f586dbfac9a05d7b90b02fa384a1f` |
| engineering-owner-checks.mjs | `6da1dcb92041e5072ef1dc7265b755bd3117873e40f74ba87eed066386147dfb` |
| diagnostic-capture.mjs | `75f5adce3980028c93e0e9ebbad178a4543d0d669507e91d465a21a6cf4cfaca` |
| build-worker.mjs | `8cae46c29ca034b3a3ea1681e47c89362a5a96dfc4e1e56578be74caf4e63d8d` |

The build worker is observational context only, excluded from this correction. Both bound review files f528/c194 stay immutable through the active group. Original compiler NO RESULT and prior native closure UNKNOWN are not repaired by this instrumentation or any descriptive error record.
