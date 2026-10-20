# Retained terminal identity — source implementation checkpoint

2026-10-20. Implements ONLY the independently accepted proof-contract amendment pinned3e09317b239a57b38a5576eb7fe8606081d6e6b3. SOURCE/pure-fake evidence only: no native/process/RNG probe, retry, binary/compiler, app/data/global/ACL change. Old0980/bc2a/2f4c closure remains UNKNOWN; old compiler NO RESULT unchanged.

## Actual finite source delta

engineering-owner.mjs now queries actual wait before retained identity checks. Listed+signaled refuses immediately without PID reopen. Nonsignaled listed/live members still require fresh full PID/creation/image and exact membership. Signaled+unlisted members admitted earlier on the original lexical never-closed handle use a private native terminalIdentity helper reading fresh GetProcessId/GetProcessTimes only; exact admitted PID/positive uint64creation must match. Admission image is frozen and explicitly labeled provenance. No image-query error or error31 is needed to enter the terminal branch. Nonsignaled→image failure still refuses without a second-wait fallback.

Native API keeps original rights, owner Job creation/assignment/termination and checked-close behavior. Terminal identity capability is private to the original factory/API, not exported or reconstructable. Initial/new-member image admission remains mandatory; rejected handles never gain process termination rights. Native wait results must be actual boolean state; unknown/failed native waits refuse. No native object is adopted by PID/JSON.

The nested native identity schema is books-engineering-native-owner-v2. Every observed member keeps pid/creation_filetime/image/signaled and adds EXACT object_proof fields below. Supervisor identity remains the original three-field admitted identity.

```json

{
  "schema": "books-retained-object-proof-v1",
  "image_basis": "fresh-native-query | admission-image-retained-terminal",
  "wait_signaled": "boolean: exact actual retained-handle wait",
  "pid_creation_confirmed": true,
  "sample_list_absent": "boolean: exact successfully queried sample list"
}

```

Terminal basis requires signaled/wait true and list absent true. Live basis requires signaled/wait false. validateNativeSnapshot(native,ownerId) validates exact own-data v2 shapes, unique PIDs, bounded counts/quota, signal/unsignaled/zero consistency, active count versus list-presence proof and retained supervisor correspondence. validateOwnedResult calls it and still requires actual operation success, exact original result/SAME-instance terminal snapshot equality, nativezero and checked close. Exported validator is STRUCTURAL comparison only; descriptive JSON does not establish continuity or actual owner capabilities. The lexical native owner and original caller retain that authority.

Sources separately owns serializer/controller/observer/map changes and must preserve/validate this exact basis for all normal/negative/final run paths before combined freeze. No canonical helpers or product source changed.

## Pure controls and limits

32 NEW opaque-handle-generation controls PASS in the existing in-process route. They cover successful prior admission→same retained terminal proof with NO image call; stable repeated sample/close; live→later terminal transition; listed/signaled no-reopen refusal; initial/new/live image failure; terminal PID/time/malformed/overflow/queryfailure; closed/same-numeric replacement/failed-or-malformed wait; active Job preventing zero; incomplete membership; checked-close failure; closed/other-owner refusal; missing/wrong proof basis/count/schema/supervisor/PIDreuse/proxy/getter; and exact joint result/terminal basis correspondence.

All52 preexisting owner pure controls PASS, including rejected-handle no-kill, identity/membership/PIDreuse/close, quotas, image diagnostics, exact first versus close error retention, wrong worker/owner/wire and timing controls. Existing fake API gained terminalIdentity; the former close-sample image diagnostic fixture intentionally remains LIVE to test that still-strict path. Pure bound snapshots explicitly JSON-roundtrip at the wire fixture boundary because the Node REPL structuredClone can cross realms; production strict ownData checks were NOT weakened.

These are pure native-API fakes: native_execution:false, new_processes:0, compiler_invocations:0. No actual Windows terminal native proof exists for this implementation. Aggregate consumer/serializer checks and independent source review remain required before any separately reviewed new native fixture plan/argv. All EOF/deadline/output/Job/checked-close floors remain independent requirements; these controls do not certify them by themselves.

## Frozen files

```json

{
  "engineering-owner.mjs": "f77ffc7506e9c463c13ec43c99b0e97ec988d26c2168d13e566ce162e51091df",
  "engineering-owner-checks.mjs": "7055948175bcce847332572d2ca3a82cb215a74dc719a02c6cb1fc1c8f692ecc",
  "engineering-terminal-checks.mjs": "f3fd2225f2c7e3c242ebfa7e58eda1b8f4067093f3326680340ca2429589d2d2"
}

```

No further source edits pending reviewer findings. Session scratch evidence and all old native unknown groups are preserved.
