# Plan-owner IDs and terminal v2 source review

2026-10-20. Static component review plus exact normal preparation command review ONLY. Packet `9415d95e9f62b9fd0af5ae09a4aecc893c04274000a5bd9f886c793d2eab01e7`. No tests, CSPRNG generation, process/native/PID probe, compiler, app/media/global change performed by reviewer. Not formal QA or RELEASE CLEAR.

## Scoped findings

No new Critical, Major or safety-floor finding in the reviewed combined contracts. Source implements the explicit retained-terminal amendment, not a cosmetic image-query waiver: original full admission and live image checks remain, actual wait precedes retained checks, signaled+listed refuses without reopen, and only signaled+unlisted original admitted handles use fresh same-handle PID/uint64creation plus frozen admission-image provenance. No image-error fallback or error31 exception exists. Opaque handles remain lexical until checked teardown.

Native-v2 object_proof labels image_basis/wait_signaled/pid_creation_confirmed/sample_list_absent. validateNativeSnapshot checks exact own-data shapes, membership/count consistency, signals, supervisor correspondence and bounds; same-instance result/close snapshots remain equal. Serializer preserves this proof, and controller/observer validate it including expected overflow/timeout negatives. Zero still independently requires actual Jobactive0/all retained signals, EOF/actual controller joins/checked close and existing deadline. Source control-flow tests model opaque handle generations and live-to-terminal stable resampling; these do not establish actual Windows behavior.

Plan map is exact/frozen/copied, excludes invocation/outer/knownprior labels, and uses lexical fixed-order one-use consumption. Failure after consuming permanently halts; CREATE_NEW checkpoint precedes native factory, and final observer requires exactly four ordered kinds/consumed map entries with exact returned-native/SAME-instance-evidence IDs and supervisor correspondence. Public UUID equality is never a handle capability. Controller no longer generates inner IDs; outer generation is unchanged.

Developer reports274 pure checks:52owner/32terminal/66planIDs/14plan/61diagnostic/49existing. Reviewed source/fake controls cover malformed maps/provenance, ordering/consumption, creation/write/readback/close/expiry, forged/swapped/missing runs and opaque terminal failures. No actual labels/native-v2 proof exist yet.

## Exact source boundary

All25 packet source hashes matched before/after review; final sizes/dev/ino/mtime matched. Wrapper c0a50a05896dc8b7bb162118a0c0719d91ce74fb8fb93a16ba5f9f4f996bafa6, seven reviewed ruling hashes and both implementation docs matched. The immutable packet is the full boundary, not a release commit-range certification. Principal reviewed pins:

| Source | SHA256 |
| --- | --- |
| engineering-owner.mjs | `f77ffc7506e9c463c13ec43c99b0e97ec988d26c2168d13e566ce162e51091df` |
| engineering-owner-checks.mjs | `7055948175bcce847332572d2ca3a82cb215a74dc719a02c6cb1fc1c8f692ecc` |
| engineering-terminal-checks.mjs | `f3fd2225f2c7e3c242ebfa7e58eda1b8f4067093f3326680340ca2429589d2d2` |
| fixture-owner-ids.mjs | `a15b2936d82ad36d45ee8b5299e604e09e169b3dea2dd43fb20e97aa095da195` |
| fixture-owner-ids-checks.mjs | `02201f2847426e47dc0359fd5b47f55a46457b0f9b6d393b5f349f0a8785779a` |
| prepare-fixture-owner-ids.mjs | `875d46e9cdcba790513bc7f02f1a58e65a8c1fb15913535bdf60ee9784f35eb9` |
| native-fixture-controller.mjs | `83edf8aa0630e370cc6105a5b51619fa8ee347c4cd4592c3da74a8f8f12c2028` |
| native-fixture-observer.mjs | `29c1da79b54c117ec2f7a8f211fa4fd1fbc6143d48cf31f24ab7aaadbb3fa7c9` |
| diagnostic-capture.mjs | `df1546ce951353c7af94f55c8e3dfa72aaeb044048d2efdc468610d7e1c64e7f` |

## Preparation-only command ruling

Conditionally ACCEPT ONE exact preparation invocation below after Sully pins this ruling and Jane instructs it. This is normal trusted engineering plan preparation, not a native fixture, ownership probe, compiler build, formal immutable sandbox or600000 owner-enclosed work. Installed Node/imports/inherited environment and ordinary filesystem preparation operate within the explicitly trusted startup/quiescence boundary; there is no sanitized-environment/native process-creation identity or hard-bounded OS IO claim. The source launches no child/native Job and changes no provider/environment policy. This boundary cannot be repurposed for runtime deployment or native test execution.

Exact request path `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/qa-native-fixture-plan-v1-VzIVqp/plan-owner-ids-preparation-request.json`,11812bytes,SHA256 `400d9cad47252b878ff025d663e4a86d30749d3122ca28880bb550539400f029`. It has all25 reviewed source pins, the fixed95-file manifest f44f4b51513bd4a50cdaacdd2167a66766beaf79292a9e653724ce01c8642b98 and exact installedNode hash1a14457b043fe82fd2fc027959595e91d138a8185c7ca6c02c15c16632b51aa4. Actual prep rechecks its declared sources/runtime before four calls.

The disclosed e275bbfc-db1a-42fd-ae91-907ba2848c27 invocation ID comes from NEVEREXECUTED disabled b22 candidate, not fresh generation; this is acceptable namespace reservation reuse because no group was launched there. Its controller/diagnostic/output paths remain absent on this read-only check. No actual0980/bc2a/2f4c namespace is reused; all three plus their known saved outer labels are excluded. No claim of complete runtime-ID history or mathematically guaranteed uniqueness. If evidence contradicts neverexecuted/absent status STOP; do not adopt or clear an existing path.

Preparation opens ONE exact output with wx+ before RNG, so output collision stops with zero calls; success makes exactly four unchanged node:crypto.randomUUID calls, then complete held-descriptor writes/fsync/readback/checked close. Malformed/entropy/duplicate/exclusion/IO failure stops, preserves any partial file and does not retry/delete/overwrite. Plan remains execute_reviewed=false/admissionzeros; generation metadata is descriptive, never self-authenticating capability. No weakened generator, alternate source/cache/provider or runtime fallback.

Literal exec_command input, shell OMITTED (default Windows PowerShell), no wrappers/probes:

```json
{
  "cmd": "& 'C:/Program Files/nodejs/node.exe' 'C:/Antigravity Projects/Worktrees/Books Arranger/electron-m1/scripts/qa-native/prepare-fixture-owner-ids.mjs' --request 'C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/qa-native-fixture-plan-v1-VzIVqp/plan-owner-ids-preparation-request.json' --request-sha 400d9cad47252b878ff025d663e4a86d30749d3122ca28880bb550539400f029",
  "workdir": "C:/Antigravity Projects/Studio Illuminati",
  "login": false,
  "yield_time_ms": 10000,
  "max_output_tokens": 2000
}
```

Observe only returned session through ordinary write_stdin polling. Any tool/entry/generation/IO failure=>STOP/no retry or alternate command; do not infer success from an output file. Required success before further review: exact observed entry exit0, completion stdout digest/size/request/map binding, independently read post-exit output bytes matching that digest, exact four canonical fresh labels and request/source/runtime/process provenance, disabled flags and all unchanged candidate fields. Actual inherited startup remains trusted; metadata alone is not proof that random generation occurred.

This command acceptance grants NO native group. After actual output review, separately pin admitted source-review bytes, review only permitted enabled-plan delta and exact new private-group argv, then obtain Jane instruction. Freeze that eventual admission review through terminal. Old native closure UNKNOWNs/compiler NO RESULT and all original evidence remain unchanged. No source/runtime/ACL/hooks/app/media/iTunes operation is included.
