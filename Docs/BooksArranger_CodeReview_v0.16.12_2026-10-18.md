# Code Review — Books Arranger v0.16.12

## Header

Reviewer: Senua (Code Reviewer)
Date: 2026-10-18
Tool: Books Arranger (Electron desktop utility)
Release: v0.16.12
Commit range: 68a7cdc..09714f2a0a607f670a14c120e32f12dad2d2158b
Files changed: 24 files, +1547 / -52 (git diff --shortstat, including review/handoff/acceptance documentation)
Release source commit: 09714f2a0a607f670a14c120e32f12dad2d2158b
Release artifact manifest SHA256: d10b4265941fc217265e2aa0f968eec1968afe45b2404eee711123d2ae6b4db6
Release installer: dist/builds/db404224-54fa-4c4a-8d50-602d5cded895/Books-Arranger-Setup-0.16.12.exe
Release installer SHA256: 5e0670fab2b26b57f8ad24ab3a7322305296a842e08c7a9715d5202d4965da3e
Stand-down dimensions: none.

## Summary

Red-team review of the series backfill, metadata rewrite proofs, queue/retry changes, catalog read transaction change, frontend controls, and version/build checks. Initial review of 68a7cdc..14eea66 found two Critical recovery/data-safety defects and blocked the old artifact. Both were corrected in 4aff686 and re-reviewed. This final clearance applies only to the rebuilt artifact bound above. No real library/catalog was opened or modified, and no installer/application was run by this reviewer.

## Rubric

### 1. Security

Status: Pass. No new shell interpolation or Electron security configuration changes were found; corrected publication and former-file removal use protected ancestry and native file handles.

### 2. Correctness & Logic

Status: Pass. Directly resumed `renamed` and `cataloged` states prove replacement identity and full bytes before catalog/destructive transitions; missing or changed files fail closed.

### 3. Crash / Stability Safety

Status: Pass. The original remains through writing/proofs/rename/catalog commit, replacement protection spans retirement, and a persisted removal-intent checkpoint permits restart after disposal but before the final done write.

### 4. Performance

Status: Pass. Series research is paced, metadata/media verification streams bounded blocks, and current catalog groups avoid a page-read write lock. Full replacement/former hashes on destructive recovery are intentional safety work.

### 5. State & Data Safety

Status: Pass. Historical parent ancestry, both file identities, expected sizes and complete hashes are checked; the former must have one link and is disposed by the exact held handle while the replacement remains protected. Catalog refusal preserves both copies.

### 6. Input Handling

Status: Pass. Destination proposals and metadata lengths are checked; recovery requires ordinary distinct paths sharing the original parent and rejects unbound legacy records.

### 7. Maintainability

Status: Pass. Backfill state transitions and proofs are localized; common protected-boundary and exact-file helpers are reused.

### 8. Doc/Code Drift

Status: Pass. The corrected implementation now supports the documented preservation claims; historical findings and evidence remain below.

### 9. Build & Release Hygiene

Status: Pass. Version and lockfile advance together, integrated checks include backfill tests, and independently computed actual installer/manifest hashes match the rebuilt source binding. Source and packaged `series_backfill.py` independently both hash to `83d2221a96f1b490dfd69a86f06fd373e340e26e5594fcea79c3924b962db100`.

## Verification and limits

- Independently inspected the accumulated product diff and correction commit, including protected-handle lifetimes, no-replace publication, missing/corrupt former/replacement handling, and the intent-before-disposal crash boundary.
- Ender's reported focused evidence: 17 backfill tests passed in 77.447 seconds; the explicit held-file/path mutation test passed in 4.124 seconds. Reviewed test source covers missing replacement at both recovery checkpoints, same-size corruption with restored time, changed old bytes/identity, successful cataloged recovery, restart after exact disposal, and denied modification of replacement/original/ancestry while held. These runs are developer evidence, not claimed as independently rerun by Senua.
- Independently hashed the actual current manifest, installer, source backfill module and corresponding unpacked module; manifest source_head was 4aff686 at that review checkpoint; the final 09714f2 rebinding is recorded below.
- No broad suite or playback/live-install test was run by this reviewer. Jane reported the canonical receipt read was denied under P9; no canonical entry receipt is asserted. This is the authorized lean handoff, with focused evidence and artifact review retained. Futaba's behavior verdict remains independent.
- No matching local Lessons/Patterns file was found by a filename search through the repository's first two levels.

## Closed findings and initial evidence

| # | Original severity | Original location | Finding | Resolution in 4aff686 |
|---|-------------------|-------------------|---------|----------------------|
| F1 | Critical | `series_backfill.py:397-416` at 14eea66 | Recovery could trust a persisted renamed/cataloged state and delete the only complete former copy when the replacement was absent or damaged. | Both recovery entry states now acquire exact identity/full-hash replacement proof and hold it through former disposal; uncertainty preserves remaining files. |
| F2 | Critical | `series_backfill.py:412-416` at 14eea66 | Former deletion checked historical size only and unlinked an unprotected pathname. | Protected historical ancestry, full old content and identity checks, single-link requirement, and native exact-handle disposition replace pathname deletion. |

Initial bounded reproduction imported `SeriesBackfill`, constructed a private instance without opening a catalog, and supplied a `cataloged` entry with a private original-file stand-in and absent replacement. Actual old `resume()` returned:

```json
{"old_survives": false, "new_exists": false, "final_states": ["done"]}
```

This was a state-machine deletion reproduction, not an audio/playback test; it used no actual book bytes and did not claim the app itself caused the replacement to disappear. Evidence directory retained: `C:/Users/AnGeLZzZ/AppData/Local/Temp/books-codex-20261018/senua-cataloged-recovery-6m231iz8`.

Historical rejected artifact: source `14eea665728116a6f89d0ebd3d365c1b627f9a17`, manifest SHA256 `86f602de252e600b99afc80c7358c9e68abfc9bf158094be728ac211273613ac`, installer SHA256 `b17d3276d4ae9c4c31a4e44a572932e5105b508fa36480055ffebe35bc3cf584`. It is not covered by this clearance.

## Verdict

- Open Critical: 0 (2 closed)
- Open Major: 0
- Open Minor: 0

**Verdict:** RELEASE CLEAR

## Scoped isolated-smoke harness review

Source-only review of the fixed QA-v01612 harness (no run performed by Senua): owner `smoke-owned.mjs` SHA256 `d145578af33b22e23e5440a9477783bc4d1e885ee55aa9574cc31efb9a468f78`, smoke payload `smoke-empty.mjs` SHA256 `8fee445bb06c136bdf7ff281e3e7f58a982d5fcdfca3c6e62613c56b8948ba14`, and `smoke-owner-pins.json` SHA256 `96e95bd5ae83b7c3ba9cb80683130411bb68b00af1eb41837bd223dd118502eb`, under the retained session `shared/tools` folder. No new blocking source finding in this narrow harness. It checks the fixed inventory, leases and rehashes executable/harness/payload inputs, delegates to unchanged canonical runOwned with the remaining 600000ms budget, and accepts success only with closed ownership, zero descendants, no unsignaled processes, no forced termination, no timeout and no output overflow. The smoke requires empty private catalog/profile and private empty library roots, uses windowsHide and inactive display, and quits its bound page rather than killing arbitrary PIDs/names. Synthetic controls cancel before retry submission.

Limits: canonical supervisor implementation/ownership-before-release is inherited from the unchanged reviewed route described by Ender, not newly inspected or independently proved here; the denied canonical receipt-read operation was not rerouted. The bootstrap's JavaScript timer cannot preempt a synchronous filesystem read, so the whole-invocation deadline also depends on the host guard and canonical owner behavior. Passing source review is not runtime closure evidence, a QA GO, or global guard enrollment; the actual transparent invocation still requires its ordinary guard evaluation and an observed closure result. This paragraph changes no product verdict or artifact binding.


## Final Retry correction and rebuilt-artifact review

Final source 09714f2 adds a narrow correction to the already cleared backfill build: transient desktop phase `unavailable` formerly satisfied phase-not-running and disabled Retry controls every second; only explicit finishing/parking/updating/blocked phases or the quit flag now do so. Genuine shutdown remains guarded, and server stopping/draining checks independently reject forbidden mutations. A delayed state poll begun before bulk acceptance could also replace the new retry ledger in the renderer; accepted bulk requests now increment retryEpoch and refresh checks that epoch before assigning state. The existing list guard uses the same epoch. No backend admission or backfill safety checks were weakened.

Reviewed the exact five-file correction and regression tests. Developer evidence supplied: three frontend suites passed and 21 blocked-retry Python cases passed, including actual single/bulk AudioJobs and WorkingLifecycle queue positions remaining 1/2 over 20 polls while the fixture's current worker stays active. These are developer test results, not an independent Senua rerun. No new open finding.

Independently recomputed the final manifest and installer hashes in the header and verified manifest source_head 09714f2a0a607f670a14c120e32f12dad2d2158b. Reviewed source and unpacked payload hashes match exactly: app.js `f2c02ced31dd895b8c2325efb9277ce8bec36f1029c8ff7b8725be92b15aec47`, desktop-ui.js `920e2961fb0ca5fd2d1ca0b91384c5eac4afa5653350cf9718d3001c6dca80ee`, and unchanged corrected series_backfill.py `83d2221a96f1b490dfd69a86f06fd373e340e26e5594fcea79c3924b962db100`. The earlier rebuilt binding (source 4aff686, manifest 334de7d785a30aa57285d61468f52a885cdd101eb9ca34d4b03bde94144741bf, installer f18300fb13ef86cbc573fee0c56f41eb331adb5951f334df2e8b34973628221d) is superseded by the final header binding.

Frozen r2 scratch harness source review is clear for the same narrowly fixed isolated smoke: owner SHA256 `5325d22701f2b5dd791e82ff0d92401f928b7a05c4c639b0c4fc14b5dd2b84d9`, smoke SHA256 `4c05f593047eafb6d7328056d7aaa7f56bbbb1e02ef56d8bd8c32ed154bc5e89`, pins SHA256 `536c367a45adfada577c7bb261d84272e32d832f7a88bdc11c17936900373852`. All three were independently hashed. The owner delta changes only private QA directory to qa-v01612-r2. The smoke delta exercises actual shipped single/selected/bulk handlers using renderer-only synthetic IDs and intercepted 202 responses; every non-GET fetch is intercepted/refused before native fetch, delayed preacceptance state and repeated polls are checked, duplicate retry presses remain disabled, and the shipped desktop script is checked against a detached DOM for unavailable versus genuine Quit. The genuine app Quit listener remains untouched. All previous canonical ownership/deadline/guard limitations still apply. This source review is not an execution result, QA GO, or global enrollment approval; no smoke was launched by Senua.

### Scratch-only CSP probe correction

The first r2 smoke attempt failed because its detached desktop-script probe used `new Function`, which the shipped Content Security Policy rejected. That failed attempt is retained under session history and is not QA clearance. Jane reports its graceful native closure was zero and real catalog fingerprints were unchanged; these execution observations belong to QA, not an independent Senua rerun.

Reviewed the exact minimal harness delta: outer Node now reads the already inventoried/pinned payload desktop-ui.js and inserts its literal source into a normal function over the detached Document/fake API inside the existing debugger Runtime.evaluate expression. Renderer fetch/new Function are removed. No CSP policy, security flag, iframe, product file, ownership setup, private-root check, mutation interception, or genuine Quit listener is changed. Narrow corrected-harness source review is clear, subject to all earlier execution/guard limitations. Independently verified owner remains `5325d22701f2b5dd791e82ff0d92401f928b7a05c4c639b0c4fc14b5dd2b84d9`; corrected smoke SHA256 `9937111c6e63be281f69fcb798312e9379e13acfd0db48f25e6bb6c4daff26ce`; refreshed pins SHA256 `c276eb0b82ad71a14017d4f621888e9f51a7961cb4104d658ec284290eb56f9b`. This supersedes only the prior scratch harness identities, not the final product artifact binding or its single verdict. No corrected smoke execution was performed by Senua.
