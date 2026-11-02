# Code Review — Books Arranger v0.24.4

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-11-02
Tool: Books Arranger
Release: v0.24.4
Commit range: 304b20e58465ed4e9eedf72dcc2faa44d087515f..reviewed runner-budget working tree after 3c45da40c82043379351fa60aac4e000a02ca172
Working-tree base: 163feb38f7828a8ee0fde01d897140e2323b31e9 (intervening changes are documentation)
Scope: 5 product files and 3 focused test files, +278 / -31 lines
Stand-down dimensions: none
```

Source clearance certifies the original patch, public-capability correction and separately reviewed runner-budget repair. Both earlier artifact bindings remain historical and do not contain the runner repair. A new source/build binding, fresh final entry and independent behavior QA remain required.

## Summary

The per-book Retry cleanup action reuses the completed job, enrolled cleanup and existing queued-action/cleanup worker. It admits only the exact legacy protected-file identity reason or a persisted typed error from opening/re-reading the final output. It does not enroll, reconvert, extend Retry all or launch automatic processing. The worker reopens and fully checks the output, original sources and durable recovery copies before any new disposition, retaining review/location guards and interrupted-removal reconciliation.

Reviewed the five product changes and their focused tests against the released 0.24.3 source, using the committed technical plan and UX. No code changes, test execution, app controls, Git mutations, live data or Z: access were performed by this reviewer. Existing evidence and other agents' documents were preserved; no reviewer scratch was created.

## Rubric

1. **Security — Pass.** Existing authenticated control admission and strict request shape/UUID validation remain in place. No new shell, executable launch, IPC, guard mode or delete primitive.
2. **Correctness & Logic — Pass.** Candidate revision, completed job/candidate association and exact cleanup/job enrollment are checked again at admission. Existing queued work dispatches to the separate cleanup retry method; conversion retry is not used.
3. **Crash / Stability Safety — Pass.** Worker ownership remains singular. Start-generation checks, Pause/closing admission and existing safe file checkpoints remain intact. The initially missing intent-query column was corrected and covered through the real status/capability path.
4. **Performance — Pass.** Reuses the existing serial cleanup worker and cached status paths; no extra conversion, periodic full recheck or parallel cleanup service is introduced.
5. **State & Data Safety — Pass.** Full output bytes, source identities/hashes, recovery durability/bytes, frozen membership and review/location transactions still precede native source disposition. Missing originals after an unproved removal intent remain held; no absence is adopted as successful deletion.
6. **Input Handling — Pass.** Retry capability comes from the enrolled cleanup's exact legacy reason or typed current-output failure history matching its current reason. Numeric Windows error, API, system message and affected path are captured at the failed native call; old holds do not invent a diagnostic.
7. **Maintainability — Pass.** Adds a narrow typed diagnostic wrapper and action to existing worker/queue paths; no parallel retry framework or new persistence schema.
8. **Doc/Code Drift — Pass.** Distinguishes requested, queued, checking and removing states, preserves historical counts, and keeps exact diagnostics in Technical details. Final accessibility additions connect the changed controls to their existing hints.
9. **Build & Release Hygiene — Pass.** No build/release infrastructure changes in the reviewed product scope. Final version metadata, candidate artifact, entry check and independent behavior QA remain separate pending release work.

## Admission limits and review resolution

An unavailable final output can still offer retry after a typed `CreateFileW` failure, including file-not-found. This is an output-read failure permitted by the committed plan, not evidence that the output exists. Every subsequent attempt must reopen and fully verify it before any deletion. Output-content mismatch and missing/changed recovery or source evidence retain their generic protective refusal and do not inherit eligibility from an earlier identity failure. No generic `BoundaryError` is automatically retried. The real diagnostic wrapper is confined to the final-output context; source and recovery failures are not laundered into this capability.

During review, `identity_retry()` selected only `state,reason` and then accessed `intent`, which broke eligible status/admission. Ender corrected the actual query to include `intent`, restored the unrelated hold query, and added legacy/typed status execution to the focused tests. This finding is resolved in the frozen bytes; no open finding remains.

## Focused evidence and limits

Portable focused evidence is `Docs/Evidence/v0.24.4_2026-11-02/focused-results.json`, SHA256 `025ab8efefe7d589dab84874410ae671d3be44e016988858ff4c97e1d618b1cb`. Its eight source pins match the frozen source and all twelve referenced raw files independently match their declared hashes and sizes, including retained earlier failures. Ender reports the six focused safety cases passing in 2.831 seconds with normal owned closure (four retained, zero remaining), the API/DOM check passing in 0.848 seconds (eight retained, zero remaining), and final accessibility DOM check passing in 0.267 seconds (four retained, zero remaining). Cases cover fresh full verification before deletion, actual Windows invalid-handle error 6, no retry inheritance after a different refusal, changed/missing output/recovery/source proofs, interrupted removal, single owner/Pause, exact admission and queued dispatch, renderer states and no conversion mutation. No full entry, packaged-app proof or final QA GO is claimed here.

## Frozen reviewed source

SHA256 values are actual working-copy bytes, measured by Senua and confirmed frozen by Ender. Normal checkout CRLF/LF changes may be mechanically compared without changing source meaning; final evidence must use the actual candidate bytes.

| File | SHA256 |
|---|---|
| `native_io.py` | `ca2fa12c4352d55708dcc20a3ab911858045b81cbd1dab87f137225d3d426603` |
| `source_cleanup.py` | `3f4604dabb6d8d4f747cc8b3674867ee989d83437ae5250965096eb791ce9712` |
| `merge_service.py` | `c9625287ecfa81a5361883fa58e92d6fe89bdd3c52e3b70914bb6b5cfe5931f4` |
| `web_server.py` | `503be578a20f83fefb0879ea1ddbb9ea8ab5cf400400f7380f97c0b8d9883ca1` |
| `web/app.js` | `8cc976236d23102610f85c6d4d5a80abd1e4d749997e24485352641643b4e711` |
| `tests/test_source_cleanup.py` | `e957b76a394acd1a3de66d52d643b21841582992483772f0e3e5ffa729ae6cf8` |
| `tests/test_cleanup_scope.py` | `203b46dd2791b53010df9990a0ec8338319ba1de43a69b371b099c271bd9e8fb` |
| `tests/test_cleanup_frontend.js` | `67052d61e6ddc62610e3f477f50d4315e4c64951cfd5bfc18d941a1b3875e437` |

## Historical source and artifact binding — superseded for acceptance

Historical source commit: 1ab490b1fb5852edfd88ca689c0d340842a5ee1d

Historical artifact manifest SHA256: 6fee5b0552f636030003bfa12321dbaae2dbdbea18c2524b42abe7e1529cc9b5

Candidate: `C:/Antigravity Projects/Worktrees/Books Arranger/books-0242-candidate-20261101`.

All eight main-source files retain their exact reviewed SHA256 values. Each candidate counterpart equals the reviewed source after CRLF-to-LF normalization only. The candidate HEAD and artifact source both equal the commit above; no application or test-content drift was found. Package/lockfile root versions are `0.24.4`; the actual lockfile SHA256 `b3b03db6a1c44a8464a33849de51dee2c52aa43058ed8cc1a7d3ed3da5c03aa7` equals the derived build-input lock pin.

The measured `dist/release-artifacts.json` identifies version `0.24.4`, build `46a8983e-8529-4efd-a91d-01b46d46fe3a`, product digest `67f89e514c18ab25f6725b83826f5719837f383af6a55203a6903465f7e108ea`, verified payload and installer equivalence. All three actual release files match its hashes and sizes:

| Artifact | Bytes | SHA256 |
|---|---:|---|
| `Books-Arranger-Setup-0.24.4.exe` | 174670970 | `e472d681e2edf2e5ccb0352aa49337a441c1b4592f26f66629a74f552e8ef12e` |
| `Books-Arranger-Setup-0.24.4.exe.blockmap` | 182241 | `1d7b16c395eddd2482fd1636d34f0d46e3ad04a58fdb957bc27a35a8f7641b87` |
| `latest.yml` | 360 | `0c50086f7ea8b0ee7cf5889532161f820fe03810ad931b196c7f07340822b897` |

Actual runtime-pointer SHA256: `245e0baa411fc653304802f541da51520e8eaa25b9d4568bf832ac057a2a59a4`. Ender reports the packaging operation passed in 94.06 seconds with normal owned closure (60 retained, zero remaining, zero incomplete observations). No full final-entry or fresh candidate-native PASS is claimed here; those gates remain pending. Other agents' QA drafts and evidence were preserved without modification.

## Public cleanup capability correction

The full entry for the historical artifact failed: the new attention-summary code assumed every cleanup collaborator exposed the private `_rows` API, including existing lightweight collaborators which do not. The original failure remains a failure. This review covers only the corrective two product files and two focused test files (+35/-6 lines); it does not repeat the previous source review or claim the old artifact contains the correction.

`CleanupJobs.identity_attention(job_ids=None)` now owns exactly the previous completed-job/enrolled-state query, subset filtering and call to `identity_retry`. `MergeService.attention_summary` consumes that optional public capability. Absent/noncallable legacy capability contributes no cleanup identity action; actual method failures still propagate, with no exception suppression. No eligibility, deletion proof, worker ownership, cancellation, conversion, schema or policy behavior was relaxed.

The real public-capability test checks the completed enrollment, unchanged retry capability, job subset and non-completed exclusion. The consumer contract checks absent capability, a real raised error and a positive result whose conversion Retry remains disabled. No new finding remains open.

Frozen correction pins, independently measured and confirmed by Ender, supersede the earlier pins for their respective files:

| File | SHA256 |
|---|---|
| `source_cleanup.py` | `1fb4e55c199f44f61c1082c144cb2ce4f3dd3456b86cdaf5b09edb7f5d5d106c` |
| `merge_service.py` | `ba4a057b351e3457f48fe61a3ec7041f66c9218690d75e001cb7279f9ba189ea` |
| `tests/test_source_cleanup.py` | `748fa4a3b6097fc9481f1418f57a20c21ce55e252d2774fdbc0384dc796b5e2e` |
| `tests/test_attention_repair.py` | `00a5ce62e31e75d0c5836e62f4f16810fb945bd7c221dfdc0bfd8885cae8d9d1` |

Actual affected regression receipt: 120 tests passed in 66.102 unittest seconds (66.870 seconds owned elapsed), normal owned closure with eight retained/zero remaining and zero incomplete observations; SHA256 `32e9bff106e5e5522987489e7a91400ade723183b9c615f6cffaeb9adcf4cf4b`. Original callback SHA256 `57f69c8db77ac79f5556431c0f0de3f4f4ac568fd263f1be6d63dd033611222c` has no error. The separately selected original Start over case passed (one test, 0.261 unittest seconds, normal four retained/zero remaining); owned receipt SHA256 `02fd681113072f762224d3c7644f000bbecdafe30fa296b7aac9d845d6cea948`, callback SHA256 `137864b757814ec1fb95ae1973a25a8f0ad01a13d1146e2f6a92fc837c72e79a`. These are retained under `C:/Antigravity Projects/codex-books-20261102-0244/public-capability`. Neither run was forced or timed out. No tests were run by this reviewer.

Portable correction evidence is `Docs/Evidence/v0.24.4_2026-11-02/public-capability-correction/results.json`, SHA256 `886c5e88f7833e6767dbe0a82c2db8737e7ff1abebd97992d8b552e73c1afbab`. Its five raw/pin references match their declared hashes and sizes; original failed-full evidence remains explicitly failed. No claim is made that this correction alone resolves the separate deadline workers.

Source construction is clear for these frozen bytes. Historical build `46a8983e-8529-4efd-a91d-01b46d46fe3a` remains tied to its own failed acceptance and is not rebound to the corrected source.

## Historical corrected source and artifact binding — superseded by runner repair

Historical corrected source commit: 3c45da40c82043379351fa60aac4e000a02ca172

Historical corrected artifact manifest SHA256: 0c85b34b48ff0c81fbae5b0b40254b94e15252051e692f41494c46e84f97f78b

Candidate: `C:/Antigravity Projects/Worktrees/Books Arranger/books-0242-candidate-20261101`, clean at the exact source above.

All nine distinct reviewed product/test files match their latest reviewed main-source hashes, using the correction pins in preference to superseded initial pins. All nine candidate counterparts equal those reviewed bytes after CRLF-to-LF normalization only. No source drift was found. Package and both root lockfile version fields remain `0.24.4`; actual lockfile hash `b3b03db6a1c44a8464a33849de51dee2c52aa43058ed8cc1a7d3ed3da5c03aa7` still equals the build-input lock pin.

Measured `dist/release-artifacts.json` binds corrected source above, version `0.24.4`, build `3c395d29-d3fc-4ddd-ac3d-e708bfbb9063`, product digest `ebebcac3e553da209f66694839a19be6f4311cd5489567f562e426ff78556924`, verified payload and installer equivalence. Each actual release file was independently hashed and sized:

| Artifact | Bytes | SHA256 |
|---|---:|---|
| `Books-Arranger-Setup-0.24.4.exe` | 174671440 | `b8db65c4a9ca0f2119c90cb65d2d13669e9eb821d6f6d7565fb585b740a35744` |
| `Books-Arranger-Setup-0.24.4.exe.blockmap` | 182213 | `21b8a705636afa1327fa234969f6c9ebf44ae53d7fec36addd03983e75437262` |
| `latest.yml` | 360 | `d97bf29148235e4d320db5eb8f8f0d7dccfca9fdf3438cd9f1f70396d1907e1b` |

Actual corrected runtime-pointer SHA256: `b8a79ed895a443d62a8236fc6fc9f1cf928844aa84322403dab63a18055910a8`. Ender reports corrected packaging passed in 131.404 seconds with normal owned closure (60 retained, zero remaining). Corrected full entry and both approved hidden checks remain pending; no pass for those gates is claimed by this mechanical binding. No tests, app runs or unrelated QA-document changes were made by this reviewer.

## Shared runner budget repair

Source construction for the eight-file shared/tool runner-budget repair is separately certified in [the shared runner review](../../../Team/Docs/BooksArranger_0244_SharedRunner_CodeReview_2026-11-02.md). It records the exact Studio and Books ranges/pins, approved finite profiles, retained ownership and source guards, and focused real-process evidence. No additional application behavior changes are introduced.

That review is source-clear only: the failed full runs remain failures, and build `3c395d29-d3fc-4ddd-ac3d-e708bfbb9063` remains tied to source `3c45da40c82043379351fa60aac4e000a02ca172`. It is not rebound to the runner patch. Canonical current release source/artifact fields must be added only for the actual newly committed and built candidate. Full entry and both approved hidden checks remain pending.

## Verdict

- Total open Critical: 0
- Total open Major: 0
- Total open Minor: 0

**Verdict:** RELEASE CLEAR

Source construction is clear for the reviewed application corrections and separately pinned runner repair. Final release requires the new source/artifact binding, completed fresh-context entry, approved candidate-native checks and independent QA GO.
