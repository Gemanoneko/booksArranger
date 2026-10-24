# Code Review — Books Arranger v0.21.2

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-24
Tool: Books Arranger (Electron / Python)
Release: v0.21.2
Commit range: 64a6daaf85546aa980f0d79a359c378cba7f79be..139d2c681c5a91beebfc5ec1c53efa73eed8336b
Release source commit: 139d2c681c5a91beebfc5ec1c53efa73eed8336b
Release artifact manifest SHA256: 6694313ca1816fd1f746ea9fae075c676799925938d56082407213cdeafee9fa
Reviewed source: C:/Antigravity Projects/Worktrees/Books Arranger/review-0212 (detached worktree at 139d2c6, level with origin/main; removed after the review)
Files changed: 19 files, +352 / -20 (git diff --numstat). Product code: review_backend.py +20, automatic_processing.py +12/-2, scripts/build_external_tools.py +11/-10, scripts/check-desktop.mjs +9/-1, scripts/gate-source-guard.mjs +16 (new), merge_service.py +4/-1, .gitignore +2. Tests: +128/-3 in 7 files. Docs and CHANGELOG: +145. package.json and package-lock.json: version only.
Stand-down dimensions: none
```

**What this report certifies.** The range runs from the `v0.21.1` tag (64a6daa) to 139d2c6, 15 commits:
- 7ecfeca (gitignore `private-fixtures/`, Brief note)
- 585cbb3 (one converted set per approval)
- 656f402 (a Start racing Quit or Pause pauses the run)
- 5f2101c and 28df88b (the attention diagnosis)
- 34a44b5, c858b30, 0cf4376 and d2ff261 (test fixes)
- 381f058 (Git re-pin, cleared earlier; re-checked here only against the installed Git)
- 126c73c (the Git core names itself in a refusal)
- 3b1b848 (two modules join the gate)
- b5f6cbd (the flaky one-approval test)
- c5651b7 (the gate refuses a live checkout)
- 139d2c6 (the version bump)

**Artifact pin (added 2026-10-24, after Ender built the candidate).** The Header now names the candidate's manifest, `C:/Antigravity Projects/Worktrees/Books Arranger/cand-0212/dist/release-artifacts.json`. I recomputed every value below myself, read-only:
- Manifest SHA-256 `6694313c…fee9fa`: the same over the file's bytes and over the UTF-8 string `release-flow.mjs` hashes (ASCII, no BOM).
- Manifest content:
  - `version` 0.21.2;
  - `source_head` 139d2c681c5a91beebfc5ec1c53efa73eed8336b;
  - `product_digest` `fd76dfe49522ae5095c172feaa38c7171d7d515c6c0c24d015e262dc3fa27922`;
  - `build_id` a04c17e9-4513-49e4-a8b3-275cc5836ea1.
- The product digest recomputes to the same value as `productTree(ls-tree 139d2c6)` with the repo's own `release-contract.mjs`. That tool also reproduces 7110748's published digest `6ff3d3e5…` exactly.
- The repo's own `artifactContract(manifest, {version: '0.21.2', productTree})` accepts the manifest. It returns three artifacts, and the payload is verified with shell and backend at 0.21.2.
- Each artifact's bytes match the manifest's size and SHA-256:
  - `Books-Arranger-Setup-0.21.2.exe`: 173,708,952 bytes, `64f4e6732137b636d0d920d9889e1327b31ee1f3b1a4ca25cd4b04a79487c6ab`, matching Ender's figure;
  - the `.blockmap`;
  - `latest.yml`.
- `payload.manifest_sha256` matches its own file map.
- The `cand-0212` worktree is at 139d2c6 with a clean tree.

## Summary

There is no Critical finding, and the safety floor is intact. There is one new Major finding (F31) and four new Minor findings (F32–F35). F26 (Major) and fifteen Minor findings are carried.

**585cbb3 changes how often the converted set is computed, not what is approved or written.**
- The converted set feeds exactly one thing in `enrich()`: the display flag `audiobook_ready` (`review_backend.py:241`).
- Nothing in the approval reads that flag:
  - `build_manifest`, `save`, `tracks` and `_write` decide from `creation.can_create`, the context and the files.
  - `_write` persists the context only.
  - `_record` keeps the returned row's id, revision and fingerprint.
- Probe P3 tells the approval that its own book is already converted. The approval still queues the same candidate, and the job completes.
- Without the fix the approval reads the set 7 times (mutant A1); with it, once.
- **Stale data: none that matters.**
  - The cached set lives on the approving thread only (`threading.local`), and only for the `with` block.
  - The book cannot become converted during its own approval. Its job is queued at the very end, and the converter's revision guard waits for `reviews.lock`, which the approval holds.
- **One side effect is dropped.** `progress_books()` also ran `synchronize_groups` for every root. That is harmless: every `_row()` in the approval goes through `inventory.candidate()`, which runs `groups.sync` for the book's own root (`scanner.py:662`).

**656f402 does not label a real failure as Paused.**
- `closing` and `stale` are raised only in these cases:
  - the start generation moved, which only `pause()`, `drain()` and `close()` do (`merge_service.py:653`, `:667`, `:2896`);
  - the queue is draining or closing;
  - the queue's own stop or drain flag is set;
  - a stop-checking loop raised `InterruptedError`.
  - (Every `StartRefused` site checked: `merge_service.py:679-730`, `audio_jobs.py:935-976`, `source_cleanup.py:272-282`.)
- The `or stop_event.is_set()` clause turns other refusal kinds into a pause only after a stop was already requested. `_work` does the same for `ValueError`/`OSError` at `automatic_processing.py:649` and `:655`.
- A persistent cause comes back at the next Start, when no stop is set, and is recorded then.
- A `blocked` refusal with no stop still records a failure (shipped test; mutant B4 caught).
- Two clauses have no test (F34).

**Ender's flaky-test claim: confirmed.**
- In 19 probe runs, the approving thread read the set exactly once.
- The only other reader in the whole flow is `BooksArrangerAudioJobs → _work_attempt → _guard → build_manifest → enrich`, the converter's own revision guard.
- It got there before `approve_automatic` returned in 1 of 16 runs, which is the race the old process-wide count tripped on.
- Nothing reads twice for one approval.

**Ender's unfixed observation: confirmed, and it is the same bottleneck (F31).** Each converted book costs 4 more full converted-set reads, all through `_guard`. Each read takes `group_lock`, which the status poll and the book list wait on. The CHANGELOG's "no longer stalls" claims more than this range delivers (F32).

**The gate guard: sound.**
- `check-desktop.mjs` refuses a root that has a `data` entry of any kind, before it reads, copies or writes anything.
- An unreadable entry fails closed.
- All four guard mutants (D1–D4) are caught, including moving the guard after the runtime read.
- Gaps: the two modules added to the gate carry no weights (F33), and the runtime override checks only three executables (F35).

## Focus questions

| # | Question | Answer |
|---|---|---|
| 1 | Does 585cbb3 change what gets approved or written, or only how often totals are computed? Any stale-data risk? | **Only how often.** The approval decides nothing from `audiobook_ready`, and persists nothing from it (Summary, probe P3). **Stale risk: none.** The set is per-thread and per-approval. Nobody else can recompute it during the approval (`group_lock`). The book cannot turn converted during its own approval. Mutants A1–A5 (no snapshot, set kept after the scope, set not stored, nesting guard removed, scope flag leaked) are all caught. |
| 2 | Does 656f402 mislabel a real failure as Paused? | **No.** `closing` and `stale` exist only for a Pause, drain or close, and other kinds become a pause only once a stop was requested. A genuine refusal is still a recorded failure (B4 caught). Untested: the stop-requested clause (B3) and the discovery-phase call site (B5), F34. |
| 3 | Is the second reader in the flaky test the conversion worker's revision check, not a double approval? | **Yes.** P1/P2, 19 runs: one approver read each time. Every other enrich read is on `BooksArrangerAudioJobs` through `_guard`, and 1 of 16 landed before the approval returned. The fixed test asserts exactly that (approver reads == 1, other readers ⊆ {`BooksArrangerAudioJobs`}), and A1 still fails it with 7 reads. |
| 4 | The worker re-reads the whole catalog under `group_lock` 4 times per book? | **Yes, 4 in the copy flow** (P2, 19/19 runs): at the attempt's start (`audio_jobs.py:1166`), twice through `publish`'s guard callback (`merge_service.py:2744`), and at the publishing checkpoint (`audio_jobs.py:1153`). The in-place path adds `merge_service.py:2765`. F31. |

## Rubric

### 1. Security

- Status: Pass.
  - No new shell-out, no Electron change, no secret.
  - The new gate guard only reduces exposure of the live catalog.
  - `BOOKS_QA_RUNTIME_ROOT` must be absolute and goes through `path.join`, not a shell.
  - The new Git pin test holds the installed Git read-only.

### 2. Correctness & Logic

- Status: Pass (new), Concerns (carried).
  - Both fixes are correct for what they claim (Focus 1 and 2).
  - The re-pin matches the installed Git: `cmd/git.exe` `3b64043b…` and `ucrt64/bin/git.exe` `9c131f30…`, Git 2.56.0.windows.3. `test_fixed_real_git_aliases_retained_without_mutation`, which runs the full `retain_git` with the DLL pins, passes here.
  - Carried, still open:
    - **F26 [Major]**: `producer_recovery.py` is unchanged.
    - **F28 [Minor]**: `audio_jobs.py:55-81`, unchanged.
    - **F8 [Minor]**: now at `merge_service.py:2762`.
    - **F23 [Minor]**: `inplace_m4b.py:516`, `:520`, `:522`, unchanged.

### 3. Crash / Stability Safety

- Status: Pass (new), Concerns (carried).
  - `ready_snapshot` clears its scope and the set in `finally`, so an exception inside the approval leaves no stale set on the thread (A2, A5 caught).
  - The new pause path is the existing `InterruptedError` path, already used for every stop.
  - Carried: **F21 [Minor]** (`inplace_m4b.py:318-322`, `zone_identifier.py:113`).

### 4. Performance

- Status: Concerns
- Findings:
  - **F31 [Major]** `review_backend.py:237-241`, reached from `merge_service.py:2694-2716` (`_guard`), `audio_jobs.py:1153`, `:1166`, and `merge_service.py:2744`, `:2765`. The converter still reads the whole catalog's converted set 4 times per book in the copy flow (probe P2, 19/19 runs). It does this to build a flag that the guard never uses.
    - **The cost:** each read is `progress_books()` with `group_lock` held for its database and render part. The diagnosis measured 10–25 s per read on the live catalog. So a conversion adds about 40–100 s of the same freeze 585cbb3 removes from an approval: the status poll, the book list and the next approval's catalog reads all wait.
    - **Not a regression:** this range does not touch the path.
    - **The approval's one remaining read is unneeded too.** P3 shows nothing in the approval consumes the flag.
    - **Fix (next cycle):** have `build_manifest` (and with it the approval and `_guard`) skip the converted-set read, for example an `enrich(..., ready=False)` that leaves `audiobook_ready` unset. Keep it for the inspector and the page. Then measure an approval and a conversion on the live catalog, which no one has done since the fix (F32).

### 5. State & Data Safety

- Status: Pass (new), Concerns (carried).
  - 585cbb3 writes nothing new, and 656f402 writes only the run's Paused checkpoint, through the existing `_paused_checkpoint`.
  - The gate guard closes the path that copied `data/inventory.sqlite3` into worker folders. No copy remains: `WIP/Books Arranger/scratch/` holds no `0`, `1` or `2` worker folder, checked read-only.
  - There are no new file deletes. The guard test removes only its own `mkdtemp` folders.
  - Carried, still open: **F27**, **F22**, **F6** (attribute half) and **F10 [Minor]**, all in unchanged code.

### 6. Input Handling

- Status: Pass.
  - `getattr(refused,'start_state',None)` tolerates a refusal without a kind.
  - The guard treats a file, a folder or a link named `data` the same, and rethrows anything but `ENOENT`.
  - The runtime override refuses a relative path.

### 7. Maintainability (no Critical findings on its own)

- Status: Pass (new), Concerns (carried).
  - `ready_snapshot` keeps a page's own set and nested scopes (A4 caught).
  - `_resume_queue` replaces both former call sites.
  - Carried: **F9 [Minor]**, `inplace_m4b.py:211`.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **F32 [Minor]** `CHANGELOG.md:7`. "Automatic processing no longer stalls on an approval" claims more than the range delivers.
    - **What changed:** the approval's own converted-set reads drop from 7 to 1 (A1).
    - **What did not:**
      - The approval still holds `reviews.lock` and `group_lock` through hashing, probes and covers, the ~4 min the diagnosis lists as not measured.
      - The converter adds 4 reads per book (F31).
    - No live timing was taken after the fix.
    - **Fix:** word it as what was measured ("an approval reads the converted set once instead of seven times"), or measure a live approval first.
  - Otherwise accurate:
    - The Brief's gate and runtime paragraphs.
    - The diagnosis's fix descriptions. Its "7 recomputations" control is reproduced by A1.
    - The CHANGELOG's re-pin and test-fix lines.
  - The diagnosis's "committed …, not pushed" heading is a dated snapshot; leave it.
  - Carried, still open: **F24 [Minor]** (now `CHANGELOG.md:22`) and **F11 [Minor]** (`inplace_m4b.py:216`).

### 9. Build & Release Hygiene

- Status: Concerns
- Findings:
  - **F33 [Minor]** `scripts/python-check-batches.mjs:8-13`, `scripts/check-desktop.mjs:49`. 3b1b848 adds `test_local_admission.py` and `test_catalog_paging.py` to the gate with no measured weight, so each counts as 2 s.
    - **Measured here, each module alone:** 20 s and 15 s. `test_automatic_media.py` now takes 103 s against its weight of 76, after the new one-approval test.
    - **Why it matters:** this narrows F30's headroom on whichever worker gets them. The slowest worker was at 440 of 540 s.
    - **Fix:** add measured weights for both modules, and refresh `test_automatic_media`'s.
  - **F34 [Minor]** `automatic_processing.py:517`, `:527`. Two clauses of 656f402 survive mutation (`test_automatic_processing`, all 63 cases, still green):
    - B3: dropping `or self.stop_event.is_set()`.
    - B5: the discovery-phase site calling `self.merge.resume()` directly.
    - **Fix:** add a `busy` refusal with stop already set (expect Paused), and run the racing case from a `discovery` run with queued work.
  - **F35 [Minor]** `scripts/check-desktop.mjs:13-17`, `scripts/qa-runtime.json`. The runtime override only checks three files.
    - With `BOOKS_QA_RUNTIME_ROOT`, the gate runs on any folder whose `python.exe`, `ffmpeg.exe` and `ffprobe.exe` match the pins.
    - Python's DLL and standard library, and FFmpeg's DLLs (a shared build, 540 KB `ffmpeg.exe`), are not checked. So "the hashes are still checked" (Brief) covers three files, not the runtime.
    - Before 34a44b5 the folder was fixed, a build-cache made from the pinned archives. Now it is hand-assembled.
    - **Fix:** pin a manifest of every file in `python/` and `ffmpeg/`, or say plainly in the Brief what is pinned.
  - Carried, still open:
    - **F29 [Minor]**: `tests/test_iron_skazka*`, unchanged.
    - **F30 [Minor]**: `tests/test_desktop_host.py:26-33` and `scripts/check-desktop.mjs:20` (was `:13`); the port and token are unchanged.
    - **F25** and **F18 [Minor]**: `tests/test_inplace_m4b.py`, unchanged.
    - **F19 [Minor]**: `scripts/release-contract.mjs:73`, unchanged.
- Verified, no finding:
  - **Version:** `package.json` and both lockfile version fields read 0.21.2. There is no `v0.21.2` tag yet.
  - **Attribution:** none of the 15 commits in the range has Claude attribution.
  - **Packaging:** `private-fixtures/` is gitignored. The backend staging copies top-level `*.py`, two JSON files and `web/` only (`scripts/build_phase.py:62-68`), so the Brief's "not in the installer" holds.
  - **Gate composition:** both new patterns name a real file. `test_local_admission` reaches its fixture root through the mapped `test_automatic_processing.AREA`. Its public client is an offline fake, so no network is used.

## Patterns

The diagnosis sampled one stack, the approval's, and the fix closed exactly that stack. The converter's revision guard goes through the same `build_manifest → enrich → progress_books` path four times per book, and it was noted but left. The release note then generalises from the sampled path to "no longer stalls". This has the same shape as F29 in the last report: the check reaches as far as the fixture or sample and no further. The cheap guard against it is to fix the shared callee (`enrich`'s converted-set read), not one caller, and to time the live result before writing the claim.

## Evidence

**Setup.**
- All runs used my detached worktree at 139d2c6 (`C:/Antigravity Projects/Worktrees/Books Arranger/review-0212`, no `data/`).
- Runtime: system Python 3.14.9 and WinGet FFmpeg 8.1.1, not the gate's pinned runtime.
- Nothing ran in `WIP/Books Arranger`, `cand-0212` or `qa-run-0212`. In `WIP/Books Arranger` I only made read-only `git` calls and listed `scratch/` and `data/`. The worktree registration is the only other write, and it was removed with the worktree. This report is the only file written in `WIP/Books Arranger`, and it is uncommitted.
- I did not run the full gate: the pinned runtime lives only in folders that were out of bounds. Futaba's pass covers it.
- Logs and scripts lived in session scratch (`shared/senua-0212/`) and were deleted at the end, as the brief asked. The results are recorded here.

**Focused modules on 139d2c6:** all pass.

| Module | Result |
|---|---|
| `test_automatic_processing` | 63 OK, 31 s |
| `test_automatic_media` | 10 OK, 103 s |
| `test_build_external_tools` | 11 OK, 1 s |
| `test_catalog_paging` | 3 OK, 15 s |
| `test_local_admission` | 3 OK, 20 s |
| `test_standing_admission` | 6 OK, 43 s |
| `node --test tests/gate-source-guard.test.mjs` | 4 pass, 0 skipped |

**Probes** (`probe_0212.py`, subclassing `AutomaticMediaTests`; real approval, real conversion on private fixtures):

| Probe | What it measures | Result |
|---|---|---|
| P1 | Converted-set reads while `approve_automatic` runs, by thread and call chain | 19/19 runs: the approver reads once. 1/16: the worker's `_guard` read lands before the return |
| P2 | Converted-set reads by the converter for one book | 19/19 runs: 4, all `_work_attempt → (_run_media → publish →) [checkpoint →] _guard → build_manifest → enrich`. No other reader |
| P3 | The approval with its own book reported as already converted | Same candidate queued, `audiobook_ready` True on the returned row only, the job completes |

**Mutants** (one exact edit each, refused unless it applies exactly once; target module re-run; the tree was restored with `git checkout` and checked clean after each):

| Mutant | What it breaks | Result |
|---|---|---|
| A1_nosnapshot | Approval without `ready_snapshot` | Caught: 7 reads != 1 |
| A2_keepset | The set outlives the scope | Caught: "the set does not outlive the approval" |
| A3_nostore | `enrich` does not cache inside the scope | Caught: 7 reads != 1 |
| A4_nonest | No nesting / page-owned guard | Caught: the nested scope deletes the outer set |
| A5_scopeleak | `ready_scope` left True | Caught |
| B1_nostale | `stale` not treated as a stop | Caught: Needs attention != Paused |
| B2_noclosing | `closing` not treated as a stop | Caught |
| B3_nostopclause | `or stop_event.is_set()` dropped | **Survives** (F34) |
| B4_everyrefusal | Every refusal becomes a pause | Caught: Paused != Needs attention |
| B5_discoveryraw | Discovery phase calls `merge.resume()` directly | **Survives** (F34) |
| B6_researchraw | Research phase calls `merge.resume()` directly | Caught |
| C1_corelabel | Core refusal names the wrapper | Caught |
| D1_guardoff | Guard never refuses | Caught |
| D2_dironly | Guard ignores a `data` file | Caught |
| D3_guardlate | Guard after the runtime read | Caught |
| D4_guardgone | Guard removed from the gate | Caught |

**Totals:** 16 mutants; 14 caught and 2 survive (F34).

## Verdict

- Total Critical: 0
- Total Major: 2 (F31 new; F26 carried)
- Total Minor: 19 (F32, F33, F34 and F35 new; F21, F22, F23, F24, F25, F27, F28, F29, F30, F6 attribute half, F8, F9, F10, F11, F18 and F19 carried)

No safety-floor item applies: there is no unsafe Electron config, no secret leakage and no source-of-truth destruction. The one data-exposure path in the range, the gate copying the live catalog, is closed by c5651b7, and its test proves the refusal comes before any copy or write.

**Verdict:** RELEASE CLEAR

The artifact manifest line is in the Header, and the candidate matches it (Artifact pin). This verdict covers installer build a04c17e9 only. A rebuild produces a new manifest and needs a new line.

| # | Sev | Dim | file:line | Finding | Next cycle |
|---|-----|-----|-----------|---------|------------|
| F31 | Major | 4 Performance | `review_backend.py:237-241`; `merge_service.py:2694`, `:2744`, `:2765`; `audio_jobs.py:1153`, `:1166` | The converter's revision guard reads the whole converted set under `group_lock` 4 times per book (10–25 s each live), to build a flag it never uses. It is the same freeze 585cbb3 removes from the approval | `build_manifest` skips the converted-set read (approval and guard); measure live afterwards |
| F32 | Minor | 8 Drift | `CHANGELOG.md:7` | "No longer stalls on an approval" overstates a 7→1 read reduction. Locks are still held through hashing, F31 remains, and nothing was measured live | Word it as measured, or measure first |
| F33 | Minor | 9 Hygiene | `scripts/python-check-batches.mjs:8`, `scripts/check-desktop.mjs:49` | Two new gate modules weigh 2 s but take 20 s and 15 s; `test_automatic_media` takes 103 s against its weight of 76 | Add and refresh the measured weights |
| F34 | Minor | 9 Hygiene | `automatic_processing.py:517`, `:527` | The stop-requested clause (B3) and the discovery-phase site (B5) survive mutation | Two cases: `busy` with stop set; the race from a discovery run |
| F35 | Minor | 9 Hygiene | `scripts/check-desktop.mjs:13-17` | The runtime override checks 3 executables, not the runtime's DLLs or standard library | Pin every file, or state the limit in the Brief |
| F26 | Major | 2 Correctness | `producer_recovery.py:48-75` | Carried from the v0.21.1 report (boot proof trusts an unchecked clock) | Carried |
| F27 | Minor | 5 Data safety | `merge_service.py:284-309`, `:244` | Carried | Carried |
| F28 | Minor | 2 Correctness | `audio_jobs.py:55-81` | Carried | Carried |
| F29 | Minor | 9 Hygiene | `tests/test_iron_skazka*.py/js` | Carried | Carried |
| F30 | Minor | 9 Hygiene | `tests/test_desktop_host.py:26`, `scripts/check-desktop.mjs:20` | Carried (line moved from `:13`) | Carried |
| F21 | Minor | 3 Stability | `inplace_m4b.py:318-322` | Carried | Carried |
| F22 | Minor | 5 Data safety | `inplace_m4b.py:99-107` | Carried | Carried |
| F23 | Minor | 2 Correctness | `inplace_m4b.py:516` | Carried | Carried |
| F24 | Minor | 8 Drift | `CHANGELOG.md:22` | Carried (line moved from `:9`) | Carried |
| F25 | Minor | 9 Hygiene | `tests/test_inplace_m4b.py:630` | Carried | Carried |
| F6 | Minor | 5 Data safety | `inplace_m4b.py:322` | Carried (attribute half) | Carried |
| F8 | Minor | 2 Correctness | `merge_service.py:2762` | Carried (line moved from `:2759`) | Carried |
| F9 | Minor | 7 Maintainability | `inplace_m4b.py:211` | Carried | Carried |
| F10 | Minor | 5 Data safety | `inplace_m4b.py:62` | Carried | Carried |
| F11 | Minor | 8 Drift | `inplace_m4b.py:216` | Carried | Carried |
| F18 | Minor | 9 Hygiene | `tests/test_inplace_m4b.py:858` | Carried | Carried |
| F19 | Minor | 9 Hygiene | `scripts/release-contract.mjs:73` | Carried | Carried |

Closed in this range: none of the carried findings. This range does not touch their code; only the line numbers of F8, F24 and F30 moved.

## Addendum: the QA entry-context script (2026-10-24)

**What was reviewed.** Ender's `C:/Antigravity Projects/Worktrees/Books Arranger/qa-run-0212/context/assemble-entry-0212.mjs` (100 lines, SHA-256 `3b32855d…fd1a7`). It is not in the repo and not in the release range, so its findings below (E1–E5) are not counted in the totals above and do not affect the release verdict. I also reviewed the context it built and the wrapper that runs the check:
- `context.json`, SHA-256 `2ddec73d…1fee`;
- `run-entry.sh`, SHA-256 `56546712ec053ac743ce4860ccba37881e65b596e0af82400f681453ad811489`.

I compared these against the studio checker (`.claude/skills/qa-handoff/scripts/`, `entry-main.mjs` and `entry-identity.mjs`) and the stale `scripts/qa-context-assembly-v2.py`.

**Entry-receipt verdict:** TRUSTED

Futaba's receipt is trusted on three conditions, which together are the normal receipt match plus one wrapper check:
1. Her receipt line equals Ender's exactly: the four digests below and `check pass`.
2. She ran `run-entry.sh` unchanged, at the hash above (E1).
3. Her evidence shows the same gate counts: 1307 Python cases, 63 node cases, 17 frontend scripts and 8 syntax files.

**Why the receipt cannot check less than the real gate.**
- The checker takes the check list from the snapshot's own `package.json`. At 139d2c6 that declares only `check` (`node scripts/check-desktop.mjs`), and the test list lives in that pinned file.
- The script controls three things, and none of them can shrink the gate:
  - `auditedNodes` only permits a route; leaving one out blocks the check.
  - The ports list only adds a pre-check.
  - `harness/graph.json` is never read by the checker, so it is documentation only.
- Both environment variables fail closed when unset:
  - without `BOOKS_QA_RUNTIME_ROOT`, the gate falls back to a dead pinned path and refuses;
  - without `BOOKS_MP3_REAL_FIXTURE`, the MP3 test skips, and any skip fails its batch.

**Evidence** (read-only, run against the files as they are now):

| Check | Result |
|---|---|
| `context.json` hash vs the pin in `run-entry.sh` | Match |
| Every pinned ref (source, harness, 5 runtime manifests) vs disk | 7/7 match |
| Source snapshot vs commit 139d2c6 | 753 files, the same list as `ls-tree`. 6 are byte-identical to the blobs; 747 differ only by CRLF (`cand-0212` has `core.autocrlf=true`); 0 differ otherwise. The snapshot folder holds no extra file |
| Snapshot vs the installer payload | All 77 shipped files that have a source counterpart are byte-identical. The other 194 are Electron or runtime files |
| The on-disk script vs its outputs | `graph.json` and `context.json` rebuilt byte-for-byte from the script's logic. All 5 trees' file lists equal their manifests (7589 / 92 / 47 / 1 / 1936 files) |
| Ender's sender receipt vs this context | The 4 digests recomputed from the context alone match exactly: source `7c92b842…`, harness `de19d6f1…`, runtime `ad8f25b1…`, checker `8af6c258…` |
| The full gate ran (sender evidence) | Exit 0; 1307 Python / 63 node / 17 frontend / 8 syntax, no skips. The same counts as Ender's direct in-worktree gate run. The private MP3 test ran |
| QA runtime vs the shipped runtime (manifest `runtime.files`) | 47 of 48 files identical, including every executable, DLL and `python314.zip`. The shipped `ffmpeg/BUILD.txt` is missing from QA; it is text only. The three gate pins match |
| Checker | The 5 tooling hashes equal the committed checker files |
| koffi, loaded by the checker | `koffi.node` `dcb3048b…` is byte-identical to QuickLaunch's koffi 3.3.2 |

**Findings** (most severe first):

| # | Sev | Where | Finding | Fix (before committing) |
|---|-----|-------|---------|-------------------------|
| E1 | Major | `run-entry.sh:8-9`; `assemble-entry-0212.mjs:71`; checker `entry-main.mjs:102-103` | The runtime folder the gate uses (`BOOKS_QA_RUNTIME_ROOT`) and the fixture come from an unpinned shell wrapper, not from the context. The checker passes the caller's environment straight through, and the receipt does not record it. `graph.json` declares both values, but nothing reads them. So a run whose variable points at another folder that passes the three-file pin (F35) prints the same receipt: the runtime digest names `qa-runtime` while the gate used other DLLs and another stdlib. The sender log does not name the folder used | Generate the wrapper into `harness/`, so the harness digest covers it. Have the gate print its resolved runtime root, or that folder's manifest digest, in its pass line. Binding the environment from the context inside the checker is a qa-handoff change for that owner |
| E2 | Minor | `assemble-entry-0212.mjs` (file dates) | The copy in `context/` is dated 03:39, after its outputs (03:31:10–16), and line 48 refuses to run while `context/` exists, so it did not run from there. The question is settled on evidence: Ender's session-scratch copy (`shared/assemble-entry-0212.mjs`, dated 03:31:05) is byte-identical (`3b32855d…`), and the byte-for-byte rebuild above agrees. What remains is that nothing in the context pins the assembler, so this took a search to prove | Commit it, and record the assembler's commit or hash in `graph.json` |
| E3 | Minor | `:78-86` | Trust on first use: each tree is pinned as found at assembly time. v2 refused unless every tree matched reviewed digests. Nothing checks `qa-runtime` against the shipped runtime or the source's pins, or `node_modules` against the lockfile. I checked the runtime by hand here (47/48, `BUILD.txt`) | Refuse unless bundled-media equals the candidate manifest's `runtime.files`, or at least `scripts/qa-runtime.json` |
| E4 | Minor | `:23` | Git runs with the caller's `GIT_*` variables and optional locks: `git status` can refresh `cand-0212`'s index, and a stray `GIT_DIR` would point the identity checks at another repo. The checker re-verifies HEAD, the dirty state, the file list and the bytes with a cleaned environment, so a wrong binding is refused at check time | Mirror the checker's `gitOut`: strip `GIT_*`, set `GIT_OPTIONAL_LOCKS=0` and `core.fsmonitor=false` |
| E5 | Minor | `:8-19` | The worktree, run parent, HEAD, fixture and runtime paths are literals for this one run | Take them as arguments, and refuse unless the expected HEAD is given |

**Note, not a finding.** v2's assembly-time checks of the gate's shape, and its readable graph, are gone. The checker never read that graph, so nothing the receipt certifies is lost. But the receipt line carries no case counts, which is why condition 3 exists.

**Commit recommendation.** Commit it as the replacement for v2, not alongside it.
- v2 cannot run: its context, run and Git roots (`codex-books-2026-10-20/…`) no longer exist, and it refuses the current gate. A dead assembler next to a live one invites the wrong one.
- Before committing, Ender should:
  - fix E1, E3 and E4;
  - parameterise it (E5);
  - have the context record the assembler's hash (E2);
  - add `node --test` cases for the refusals: existing folder, dirty tree, wrong HEAD, a link in a tree, runtime mismatch.
- Whether `scripts/qa-context-assembly.py` (v1) is also dead was not checked here; Ender should check it in the same pass.

**How this addendum was checked.**
- **`cand-0212` and `qa-run-0212`:** read-only. I used hashing, file reads, directory listings and `git --no-optional-locks` reads only, and touched no lock, log or run folder. Futaba's entry run (pid 47968) was in progress throughout.
- **`WIP/Books Arranger`:** read-only `git` calls only.
- **Scratch:** the probes lived in session scratch (`shared/senua-0212b/`) and were deleted at the end.
