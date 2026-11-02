# Code Review — Books Arranger v0.24.4

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-11-02
Tool: Books Arranger
Release: v0.24.4
Commit range: 304b20e58465ed4e9eedf72dcc2faa44d087515f..frozen working tree identified below
Working-tree base: 163feb38f7828a8ee0fde01d897140e2323b31e9 (intervening changes are documentation)
Scope: 5 product files and 3 focused test files, +278 / -31 lines
Stand-down dimensions: none
```

Source clearance certifies the exact eight frozen file hashes below. Sully may mechanically bind the commit containing these bytes and the derived version metadata. No artifact manifest exists for this review yet; its canonical `Release artifact manifest SHA256:` field must be filled with the actual final artifact hash later, not a placeholder.

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

## Verdict

- Total open Critical: 0
- Total open Major: 0
- Total open Minor: 0

**Verdict:** RELEASE CLEAR

Source construction is clear for the frozen patch above. Final release still requires actual candidate/artifact binding, final entry and independent QA GO.
