# Empty pinned file admission — finite implementation

SOURCE-only correction under pinned825c8c516db19fc734d034b044473400b02f4972/review50ae84356eb1332c6563d0029abd13364d6ecde10038315e46d5e81e1429c559. Only prepare-fixture-owner-ids.mjs and fixture-owner-ids-checks.mjs changed; remaining23source/native-owner contracts remain pinned. No actual preparation/generation, process/native probe, fixture, compiler, global/app/media/security change or cleanup.

Generic declared filelength is now a nonnegative safeinteger. Length0 additionally requires exact declared emptySHA e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855. Existing ordinaryfile/no-symlink/nlink1/actualsize/actualhash checks remain; preparation-source/request/manifest/node metadata remain positive as before. Cumulative declared reads remain capped at268435456B(256MiB), with safeinteger arithmetic. Distinct errors identify invalidlength, emptyhash mismatch and exceededquota; no cap increase.

preflightPreparation is the shared exported READONLY pre-RNG admission used by production prepareOwnerIds. It decodes exactrequest bytes/SHA, checks preparation source, existing95-file runtime manifest+allfiles, then all25 sourcepins using one checked reader. It has no supplied RNG/output/create capability. Main does not create output or call the unchanged four-call generator before this admission returns. No generic executor/registry/runtime alteration.

73owner-ID/preparation pure checks passed, including7newsize/ordinaryfile controls:0/exactemptyhash, negative/fraction/NaN/Infinity/unsafe,exact256MiB/+1 cumulative,wrongemptyhash/actualsize/nonordinary/symlink/nlink. Only the affected owner-ID/preparation exported checks were rerun; other unchanged exported suites were not repeated.

The ACTUAL NEW frozen request C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/qa-native-fixture-plan-v1-VzIVqp/plan-owner-ids-empty-pin-corrected-request.json SHA3eb4b2d0831395570ca7022d721387aa4b822d565ad0ce864a17c72ce2100bd4 traversed the same exported preflight with a strictly readonly IO facade.122actualreads+122stats (95runtime+25source+preparer+manifest), total108352687B, zero-length unions.md exactpin admitted. No RNG/output capability was supplied and forbidden capabilityrequests=0. This is real file admission evidence with no generation/nativeowner claim.

Historical400d9 request remains byte-for-byte unchanged and FAILS against current source with Preparation ordinary pinned file/size mismatch at its old preparation sourcepin. It was not rebased or called a pass. NEWrequest derives from400d9 only by updating the two changed source records and top-level preparation sourcepin; same e275 NEVEREXECUTED sourcecandidate/output reservation, allmaps still absent,disabledflags/runtime unchanged. Proposed output remains absent.

Receipt C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/qa-native-fixture-plan-v1-VzIVqp/preparation-empty-pin-correction-receipt.json SHAdd698a2662d2621fac3eeea179a0feaf6efd374f43284fcef9b2a5e1ccff900c.

Exact two changedsourcepins: fixture-owner-ids-checks.mjs aca9e60b8129ab06c95d19c9b568498991219a04c5e88ae5fbe6677bd83043b8; prepare-fixture-owner-ids.mjs 5fe7920ef61a58004de7131d50ac6e91abe3929e5c0787e06ba3c42d4be2a4a4.

SOURCE-REVIEW-ONLY futureprep argv (shell omitted; inheritedenv/import/OSIO remain explicit trusted normal engineering startup, not sanitized/native600000 claim):

```json
{
  "cmd": "& 'C:/Program Files/nodejs/node.exe' 'C:/Antigravity Projects/Worktrees/Books Arranger/electron-m1/scripts/qa-native/prepare-fixture-owner-ids.mjs' --request 'C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/qa-native-fixture-plan-v1-VzIVqp/plan-owner-ids-empty-pin-corrected-request.json' --request-sha 3eb4b2d0831395570ca7022d721387aa4b822d565ad0ce864a17c72ce2100bd4",
  "workdir": "C:/Antigravity Projects/Studio Illuminati",
  "login": false,
  "yield_time_ms": 10000,
  "max_output_tokens": 2000
}
```

This new request/command requires independent implementation+actualgraph+argv review and Jane instruction; no retry of400d9 is authorized. Successful future preparation still requires actualexit0,stdoutdigest,postexitreadback and separately reviewed disabledplan/provenance, then native admission. Oldfailure196457/outputabsence and native0980/bc2a/2f4c UNKNOWN closures/compilerNORESULT remain unchanged.
