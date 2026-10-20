# Native fixture entropy error — bounded read-only diagnosis

2026-10-20. No process/native/RNG probe, retry, config/security change or source edit. Original group bc2a remains under its original observed owner until Jane/Sources records terminal evidence; this note grants no closure or further invocation. Bound f528/c194 source and21 inputs are untouched.

## Saved fact

The controller-error record is C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/native-fixture-bc2a3b11-0186-416c-93f7-2a7d483ca903/evidence/diagnostic-controller-error-controller.json; independently rehashed SHA256 51de6574ee6bb403109c299ba3e40afe233f760b57c018fb8a81f8a3b98fa649. It contains ERR_OSSL_ENTROPY_SOURCE_STRENGTH_TOO_WEAK and message error:1C8000BA:Provider routines::entropy source strength too weak. It contains no stack, result or owner evidence. The reported prior pure-complete checkpoint says33 passed and no inner-start was observed. These facts do not prove an underlying entropy/provider cause or native closure.

## First substantive source finding

Immediately after the pure-complete journal, controller calls owned(nested-final). Before its inner-start journal it performs fixtureInnerRemaining(deadline)/date arithmetic and then newOwnerId(). engineering-owner.newOwnerId is exactly crypto.randomUUID(). Creation of the native inner owner and runOwned happen after inner-start. Thus the first explicit random API on this code path is before the first inner-stage checkpoint. The saved error is consistent with that API failing, but without stack or API-specific stage recording the actual throwing callsite is not proven.

The inspected engineeringOwnerChecks body mutates local fake owner/API objects and reads source bytes; it contains no crypto API monkeypatch, environment modification or global security setting change. No state-contamination cause is established. This is a bounded source observation, not proof of all native provider state. The journal write path uses SHA256 hashing and native record IO; no second explicit randomUUID/randomBytes call was found in that inspected pre-inner-start path.

## Smallest next proof proposal — review before edits

After terminal evidence and a pinned source correction ruling, add a fixed owner-id-start checkpoint immediately before newOwnerId, then an API-specific owner-id-error diagnostic on a thrown error, preserving its actual whitelisted name/message/code and rethrowing the original error. Use the existing creation-owned controller evidence namespace and original deadline; no standalone RNG probe, retry loop or alternate random source. Keep innerUncertain false until an actual inner owner can exist; preserve all existing closure/lease-finally behavior. This narrows API-site observability without changing the RNG/provider/security policy or weakening owner identity.

If that source-only change is independently accepted, any future invocation requires a distinct reviewed group/UUID/root and exact plan/admission; no old group retry or source mutation while its owner is active. Underlying provider/environment diagnosis requires separately authorized proof after the callsite is established. Do not infer that a randomUUID option, disabled FIPS/provider setting, alternate UUID source, RNG cache change or reduced security is a remedy.

## Read source pins

```json

{
  "native-fixture-controller.mjs": "dd6c2535cdc9330302a6dc946cd42952174471b7845a81b248aa0d5c5e6fa106",
  "engineering-owner.mjs": "f7b9db56437eca8f607e66d01ef7edd1877f586dbfac9a05d7b90b02fa384a1f",
  "engineering-owner-checks.mjs": "6da1dcb92041e5072ef1dc7265b755bd3117873e40f74ba87eed066386147dfb",
  "diagnostic-capture.mjs": "75f5adce3980028c93e0e9ebbad178a4543d0d669507e91d465a21a6cf4cfaca",
  "build-worker.mjs": "8cae46c29ca034b3a3ea1681e47c89362a5a96dfc4e1e56578be74caf4e63d8d"
}

```

Only this documentation file created. No app, bound source, runtime, ACL, global hook or scratch evidence was changed.
