# Preparation empty-pin correction — source checkpoint

2026-10-20. Narrow static review of two changed files and exact NEW preparation request/argv under design825c8c516db19fc734d034b044473400b02f4972. Packet `b0d3dcda8308ea28fb7f0639f96043fd02f46a92ecdd3bafc5b87abd882de4a7`. No tests/process/RNG/native/probe/compiler performed by reviewer. Not formal QA/release or native fixture admission.

## Scoped result

No new Critical, Major or safety-floor finding. Generic per-file lengths now require nonnegative safeinteger; zero requires exact empty SHA. Actual ordinary/noSymlink/nlink1/size and byte-length/hash checks remain. Same268435456 cumulative limit is enforced before stat/read; invalid-length, hash, quota and actual-file/drift errors are separated. Preparation-source/node/manifest metadata still require positive sizes. No changed native/runtime/security contract.

Production calls the same exported preflightPreparation over exact decoded request/source/runtime95/full25source graph before parent/output/RNG operations. Its capability surface has only read/stat; no generation/write/open callback is supplied. Actual implementation evidence receipt `dd698a2662d2621fac3eeea179a0feaf6efd374f43284fcef9b2a5e1ccff900c` reports122 real pin reads+122stats/108352687B, including exact declared empty unions.md, no RNG/output capability requests. Historical400d9 correctly refuses changed source/size.73 affected pure controls include invalid sizes/emptyhash/cap/cap+1/type/link/hash refusal and existing plan/output/generation failure controls; unchanged suites were not rerun or newly certified. This is pin-admission evidence only.

All25 current source hashes and final size/dev/ino/mtime match the packet. Other23 source hashes match the previous reviewed9415 packet. Relevant pins:

- prepare-fixture-owner-ids.mjs `5fe7920ef61a58004de7131d50ac6e91abe3929e5c0787e06ba3c42d4be2a4a4`
- fixture-owner-ids-checks.mjs `aca9e60b8129ab06c95d19c9b568498991219a04c5e88ae5fbe6677bd83043b8`

Implementation note SHA85045c837ac9225dcdbbefb0c299661625bd06420fb0ae6235ebddcb7220a093 and prior ruling hashes matched. Full native-v2/owner-ID contract is inherited from the prior scoped review, not re-certified by these two-file checks.

## Conditional exact NEW preparation command

After Sully pins this ruling and Jane instructs it, accept ONE exact preparation-only invocation below. NEW request SHA256 `3eb4b2d0831395570ca7022d721387aa4b822d565ad0ce864a17c72ce2100bd4` at its literal path. Independently compared with failed400d9: only the two changed source size/hash/mtime pins plus matching preparer metadata changed. Invocation e275/roots/runtime/forbiddenlabels/disabledflags remain unchanged. All25 current graph pins agree with request. The exact output remains absent. Reusing this neverexecuted group reservation remains disclosed; the failed preparation created no output or labels, and no native group was launched there. This is a new reviewed changed-source command/request, not retry of old400d9.

```json
{
  "cmd": "& 'C:/Program Files/nodejs/node.exe' 'C:/Antigravity Projects/Worktrees/Books Arranger/electron-m1/scripts/qa-native/prepare-fixture-owner-ids.mjs' --request 'C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/qa-native-fixture-plan-v1-VzIVqp/plan-owner-ids-empty-pin-corrected-request.json' --request-sha 3eb4b2d0831395570ca7022d721387aa4b822d565ad0ce864a17c72ce2100bd4",
  "workdir": "C:/Antigravity Projects/Studio Illuminati",
  "login": false,
  "yield_time_ms": 10000,
  "max_output_tokens": 2000
}
```

Shell omitted; installed Node/fixedpreparer only, studio cwd/login=false/yield10000/max2000. Normal trusted engineering imports/inherited environment/ordinary OS IO remain explicit; there is no private native ownership or600000 bounded-work claim for this preparation. No provider/RNG/cache/environment/security changes. The source creates one wx+ output before exactlyfour normal randomUUID calls; collision or any failure STOP without retries/cleanup/overwrite. Old400d9/failure196457 evidence stays unchanged.

Observed exact command exit0 plus completion digest/size/request/map bindings and independent post-exit exact output readback/provenance are required before generated-plan review. Output alone or claimedcall_count is insufficient; partial/capturefailure remains failure. Poll only any returned session, stop on tool/entry refusal or uncertainty. This ruling accepts no nativefixture/compile/global/app/media action. Later native admission requires actual prepared output review, final enabled-plan delta and exactargv review plus Jane instruction. Old native closures UNKNOWN and original compiler NO RESULT remain untouched.
