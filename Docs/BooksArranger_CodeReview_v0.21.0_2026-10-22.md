# Code Review — Books Arranger v0.21.0

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-23 (review of the 2026-10-22 release cycle; file named as briefed)
Tool: Books Arranger (Electron / Python)
Release: v0.21.0
Commit range: 004ab2a2b7732892c1be40ed3c0a535d151447be..73215173a8b5c2f8324b89c34a06e470cee4b3a3
Release source commit: 73215173a8b5c2f8324b89c34a06e470cee4b3a3
Release artifact manifest SHA256: eabc4eb15ec8c0b0ef82a430cc237a22d794fa96aafabe12513fbc96f6f9280c
Reviewed source: C:/Antigravity Projects/Worktrees/Books Arranger/inplace-m4b (branch codex/books-inplace-m4b, clean tree at HEAD 7321517)
Files changed: 20 files, +1370 / -35 (2 commits: 8ba3af9, 7321517)
Stand-down dimensions: none
```

Range start `004ab2a` is the `v0.20.3` tag. `dist/release-artifacts.json` hashes to the pinned value above (read only). Its `source_head` is 7321517, and its `product_digest` 35d15e59… equals `productTree(ls-tree 7321517)`, recomputed with the repo's own `release-contract.mjs`.

## Summary

The range adds two things:
- **The in-place single-M4B fast path** (`inplace_m4b.py`, the `inplace_edits` journal, `MergeService._publish_in_place`, `CleanupJobs._retire_moved`).
- **The attempt-scoped re-hash cut** (`source_proofs.py`).

It also contains the 7321517 fix that keeps keep-sources jobs on the copy flow. Sergei approved the trade-off itself (no decode, original modified in place) on 2026-10-22, so it is not a finding. I reviewed whether the code delivers what the design note promises, red-team style.

The core write is sound:
- The journal row is durable before the first byte.
- The append is flushed before the 4-byte type patch.
- Every in-process failure after the first byte undoes the edit or journals it as `unresolved`.
- The final byte proof runs under a deny-writers handle that is held through the rename.
- The output is the copy flow's planned bytes, which each book's own `output_sha256` proves.
- No path deletes the published output, and every deletion proof still hashes in full.

I found no Critical issue. Four Major issues should be fixed next cycle:
- **F1:** an in-place fallback lets the copy flow skip the cover gate.
- **F2:** a crash or postcondition failure after the rename leaves a book whose source cleanup can never complete.
- **F3:** recovery writes into a file it has not proven is the edited original.
- **F4:** the recovery wiring is untested and its errors are swallowed.

## Focus questions (brief items 1–6)

| # | Question | Answer |
|---|---|---|
| 1 | Journal durable before the first byte? | Yes. `inplace_m4b.py:282` commits in WAL with synchronous FULL (the bundled SQLite 3.50.4 default, measured). Mutation M9 (journal moved after the append) is caught by the gate. |
| 1 | Recovery exact and idempotent? | Bytes, size and ns mtime are exact and verified. Attributes are restored but not verified. The download marker is not restored (F6). Recovery is idempotent: a second run finds nothing open. |
| 1 | Recovery runs before any new attempt? | Yes, by reading the code (`audio_jobs.py:1076-1081`, `:371-375`). It is untested, and its startup failures are swallowed (F4). |
| 1 | Two attempts or processes on one file? | No. There is one worker thread and an exclusive catalog lock. The writer shares READ only, so a second writer gets a sharing violation and falls back. |
| 1 | Deny-writers held for the whole edit? | Yes for the write and the post-write checks. The handle is released for the marker step (`:304-310`) and reacquired before the byte proof, which re-proves the whole file. The gaps matter only to the undo (F3). |
| 1 | Half-edited original with no journal row? | None found. Every exception path after `:282` undoes or records `unresolved`, and a process death leaves `intended`/`written`. |
| 2 | Ineligible books reaching the fast path? | None found. Repair, re-encode/ALAC, keep-sources, cross-volume and replacement are all refused. I checked these keep-sources siblings: `failed_m4b_retry`'s binding (a different schema, so no repairs), the damage-repair binding (`offered()` refuses it), Retry with a checkpoint and manual M4B (cleanup frozen off), replacement (both keys, and cleanup frozen off), and Keep files (post-completion only). |
| 3 | Re-hash cut weakening a deletion? | No. `_match`, the marker validation, `_source_safety`, `_prepare`, snapshot discharge and the in-place pre-write and byte proofs all hash in full. The attempt scope closes (`audio_jobs.py:1168`) before `after_attempt`/cleanup. A same-size/mtime/ID change mid-attempt still publishes reviewed snapshot bytes, and cleanup then refuses the changed original. |
| 4 | Deleting the only copy? | No path found. `_retire_moved` deletes nothing. Retention records `deleted/in_place`. `restore()` refuses. The copy-flow cleanup branch is unreachable for `publication_mode='in_place'`, and the old path is absent anyway. A book can get stuck instead (F2). |
| 5 | Apple layout identical? | Yes. `_patches(plan)` is the type patch plus header patches, and the fast path refuses header patches. The fast path writes exactly that patch plus `appended_movie`, and the per-book byte proof binds the file to the copy flow's planned `output_sha256`. There is no atom-layout difference. |
| 6 | Tests gated and real? | Yes, both modules are in `check-desktop.mjs:40` and gate run 5 passed. Three of seven mutations are caught; four survive (F4, F5). |

## Rubric

### 1. Security

- Status: Pass. No new shell-out beyond existing argument-array `ffprobe`/`ffmpeg` calls through `run_owned`. Every new path goes through `ordinary()`. The new Win32 calls use held handles. There is no Electron, IPC or renderer change, and no secrets.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - **F1 [Major]** `audio_pipeline.py:524-525` with `inplace_m4b.py:246` and `inplace_m4b.py:109`. An in-place fallback lets the copy flow skip the job-time cover gate.
    - **Mechanism:**
      - `_edit` calls `protected_cover()`, which copies the cover into the stage, then probes it, checks dimensions (at most 16 MP) and decodes it with `-xerror`.
      - If the probe, dimension check or decode raises `ValidationError`, `_before_write` turns it into `Ineligible` and the copy flow runs in the same stage.
      - The copy flow's `protected_cover()` now returns early whenever `cover.png`/`cover.jpg` exists with the reviewed hash. It skips the probe, the dimension check and the decode.
    - **Probe** (scratch copy only): a 4100×4100 PNG (16.8 MP) cover.
      - Copy flow alone: refused "Selected cover dimensions are invalid or too large".
      - The same manifest with an in-place session: in-place falls back with that reason, then the copy flow returns `checked.m4b` with `existing_m4b_audio_stream_copy`.
      - The review-time cover check (`review_backend.py:537`) decodes the cover but never checks dimensions, so a large cover scan reaches this path.
    - **Why not Critical:** the audio is intact, and the original keeps its 24-hour recovery copy on this copy-flow path. The result is a published book with an oversized cover that 0.20.3 refused.
    - **Fix next cycle:** reuse the stage cover only after the full gate has passed (record a "validated" marker), or call `protected_cover` in `_edit` only after the cheap eligibility checks. The design note's "the copy flow runs unchanged" (`Docs/…InPlaceM4B_Design…md:40`) then becomes true.
  - **F8 [Minor]** `merge_service.py:2685-2688` vs `audio_pipeline.py:1105-1108`. The in-place path commits the durable publication intent (`checkpoint('publishing')`) before it takes the review lock and runs the locked guard. `publish()` runs the locked guard first and journals `publishing` inside the lock.
    - **Effect:** a review save or scan start between those two lines makes the locked guard fail. The edit is correctly undone, but the job now carries `publication_intent`. `_work_attempt` then marks it needs attention with "Recorded output is missing, changed, or failed validation", and Retry refuses it, because every retry binding forbids a publication intent.
    - **Recourse:** only Start over.
    - **Fix:** commit the intent inside `_review_boundary()`, after the guard and `revalidate()`, as `publish()` does. That is also what the design note claims at line 93.

### 3. Crash / Stability Safety

- Status: Concerns
- Findings:
  - **F4 [Major]** `audio_jobs.py:371-375`, `audio_jobs.py:1076-1081`. The two calls that make the crash-recovery promise are not exercised by any gated test.
    - **Mutations:** I deleted `inplace_m4b.recover_all` from `AudioJobs._recover` (M5), and separately deleted `inplace_m4b.clear` from `_work_attempt` (M4). `test_inplace_m4b` + `test_source_proofs` + `test_standing_admission` (29 cases) stayed green both times. No other test file references the feature.
    - **Why the gate misses it:** the crash tests call `recover_all()`/`clear()` directly.
    - **Silent failure:** `_recover` also wraps the call in `except Exception: pass`, with no log and no status. A programming or schema error therefore disables startup recovery silently. The design's "before any scan" (`Design:121`) then holds only by luck. The pre-attempt `clear` is the only remaining net, and it is untested too.
    - **Fix next cycle:**
      - One service-level test: crash at a fault point, construct a fresh `MergeService`/`AudioJobs`, and assert the original is restored before the job is resumed.
      - One test that a resumed attempt on an `unresolved` source goes to needs attention.
      - Narrow the startup `except` to `(ValueError, OSError, sqlite3.Error)`, and record the failure somewhere visible.

### 4. Performance

- Status: Pass. The re-hash cut reproduces in my run: full source hashes per source went from guard 5 / pipeline 5 / held 2 to guard 2 / pipeline 0 / held 1. The fast path's remaining full reads (pre-write hash, packet listings, byte proof, output checks) match the design estimate.

### 5. State & Data Safety

- Status: Concerns
- Findings:
  - **F2 [Major]** `inplace_m4b.py:362-363`, `inplace_m4b.py:397-399`, `merge_service.py:2697`, `source_cleanup.py:416`. If the rename happens but the `published` row with its `rename` receipt is never written, the book's source cleanup can never complete.
    - **When it happens:** a process death in that window, or an in-process `RenamePostconditionError`.
    - **Mechanism:**
      - Recovery finds the old path absent and a destination of the output size, and records `published` with only `recovered_move`.
      - The job itself completes, because `_settle`/`_check_output` prove the output.
      - `_retire_moved` requires `published_move()`, which needs `detail['rename']['old_absent']`. It raises "In-place move receipt is missing; nothing retired" on every run.
    - **Probe** (scratch copy only):
      - **Process death:** a faithful post-death catalog (row `publishing`, no `rename`) gives `recover_all` → `published` and `published_move` → `None`.
      - **In-process postcondition error:** the real rename, then `RenamePostconditionError`, gives the same result.
    - **Masking test:** `test_crash_after_rename_is_recognized_as_moved` hides this. It flips the state back to `publishing` after the receipt was already written.
    - **No recourse:** Start over does not apply to a completed job.
    - **Not exercised on the library share:** nothing has run the fast path on the SMB library (Z:). If the rename postcondition (`named(destination)` identity equality) ever fails there, this becomes routine instead of rare.
    - **Fix next cycle:** when recovery finds the move, prove the destination under a held handle (full hash equals `intent['output_sha256']`, old path absent). Then write a receipt that `published_move` accepts, or let `_retire_moved` accept that recovered proof. Replace the masking test with the faithful one.
  - **F3 [Major]** `inplace_m4b.py:185-197`, `inplace_m4b.py:203-209`, `inplace_m4b.py:359-360`. The undo truncates the file and writes `moov` before it proves the file is the edited original.
    - **Recovery path:** in `reconcile`, the content is proven only when the file ID changed. If the file at the path was rewritten in place after a crash (same file ID, size in `[size, output_size]`), recovery truncates it and patches 4 bytes. Only then does the final hash fail, and the row becomes `unresolved`.
    - **Undo path:** `_undo_released` reopens by path, after the held handle was released for the marker step or by `Edited.undo()`. It then calls `_undo` with `proven_identity=True` and no identity comparison at all.
    - **Corroborated:** Futaba's run (`futaba-0.21.0-s4b-xcrash.log` h6/h7, foreign same-size and output-size files written over the path) shows "foreign untouched: False".
    - **Why not Critical:** it needs a crash, then an external in-place rewrite of that exact file before the next start, with a size inside the appended-`moov` window. The damage is truncation to the original length plus 4 bytes at a known offset.
    - **Fix next cycle:** before any write, require `facts['identity']==intent['identity']` on every reopened handle. Prove the content first in every case: hash `[0,size)` with the type reverted, and, when the length equals `output_size`, check the tail against `appended_sha256`. Recovery is rare, so one extra full read is cheap.
  - **F6 [Minor]** `inplace_m4b.py:305-309`, `inplace_m4b.py:197-200`. The rollback is exact on the main stream only.
    - **Probe:** an original with a `Zone.Identifier` marker, then a guard failure before the rename. The bytes and ns mtime were restored and the row was `rolled_back`, but the streams went from `[::$DATA, :Zone.Identifier:$DATA]` to `[::$DATA]`. The marker bytes survive only as base64 in the journal.
    - **Attributes:** they are restored but not compared after the undo.
    - **Fix:** restore the marker from the journal receipt, or state the exception in `CHANGELOG.md:8` ("restores the exact original") and the design note.
  - **F7 [Minor]** `inplace_m4b.py:362`. Recovery marks a move `published` from the destination's size alone, with no identity or hash check.
    - **Probe:** the original renamed elsewhere and a zero-filled file of `output_size` at the destination gave `recover_all` → `published`.
    - **Current impact:** none, because nothing deletes on that state. It is weak evidence, though, and becomes dangerous if F2 is fixed by trusting this row. Prove the hash as in F2.
  - **F10 [Minor]** `inplace_m4b.py:63-76`. The `inplace_edits` journal relies on SQLite's default synchronous level. FULL is measured on the bundled 3.14.8 / SQLite 3.50.4. The repo's other pre-move journals assert FULL/EXTRA (`output_rename.py:209-210`). Assert it here too, so a future connection pragma cannot silently weaken "durable before the first byte".

### 6. Input Handling

- Status: Pass. Manifests are frozen server-side. Every source, root and destination path goes through `ordinary()`, and so does the journal's `path` on recovery. The journal's `destination` is used only for read-only `lexists`/`getsize`.

### 7. Maintainability (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **F9 [Minor]** `inplace_m4b.py:109`, `merge_service.py:2627`, `merge_service.py:2677`.
    - `_before_write` converts `KeyError` and `TypeError` (programming errors) into a silent `Ineligible` fallback. A bug in `_edit` would quietly turn the fast path off, visible only by counting `in_place.fallback` history entries.
    - Product code bends to the test double: `getattr(self,'_held_sources',{})` and `if not hasattr(self,'_held_sources')` exist for `SimpleNamespace` fakes.
    - **Fix:** narrow the conversion to the expected refusal types, and give the fake the attribute.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **F11 [Minor]** `Docs/BooksArranger_InPlaceM4B_Design_2026-10-22.md`:
    - :40 says "the copy flow runs unchanged". It does not (F1).
    - :93 says the fast path records "the same publication intent as `publish()`". The order differs (F8).
    - :95 says the DELETE handle "makes the file unreadable to others". The handle shares READ; it excludes only openers that do not share DELETE, which in practice is most of them.
    - :121 says recovery runs "before any scan". That holds only when startup recovery succeeds (F4).
    - :148 lists "replacement flows, which run outside attempts" as kept in full. Replacement media jobs run inside `_work_attempt`, so their revision guards do take the cut. That is harmless, because replacement sources are kept.
    - :194 says "16 tests". There are 17 since 7321517.
    - `CHANGELOG.md:8`: see F6.

### 9. Build & Release Hygiene

- Status: Concerns
- Findings:
  - **F5 [Minor]** `source_cleanup.py:209-213`, `source_cleanup.py:416`. The two cleanup-side guards of the new contract have no negative test.
    - **M6:** replacing the in-place byte-proof check in `_validation_contract` with `pass` stays green.
    - **M7:** letting `_retire_moved` proceed without a `published_move` receipt stays green.
    - Only the positive case is exercised.
    - **Fix:** add a refusal test for a missing or mismatched `original_sha256`/`source_sha256` and for a missing receipt.
- Verified, no finding:
  - **Version and lock:** `package.json` and `package-lock.json` both read 0.21.0 in 8ba3af9. The CHANGELOG entry is present.
  - **Gate list:** `scripts/check-desktop.mjs:40` adds `test_inplace_m4b.py` and `test_source_proofs.py`. Gate run 5 at 7321517 passed (1255 Python, 0 skipped, per `ba-0.21.0-check-run5-7321517.log`).
  - **Manifest:** `source_head` is 7321517 and `product_digest` equals `productTree(7321517)`.
  - **Attribution:** no Claude attribution in either commit.
  - **Mutations caught:**
    - M1: dropping the 7321517 `cleanup_policy.enabled` condition fails `test_sources_kept_by_policy_are_never_moved`.
    - M2: dropping `_byte_proof` fails `test_unprovable_original_stays_journaled_and_blocks_new_attempts`.
    - M9: journaling after the append fails `test_crash_at_each_step…` at `before_append`/`appended`.

## Patterns

The tests prove each mechanism by calling it directly (`recover_all`, `clear`, `_validation_contract`). They do not prove that the service reaches it. One test reaches the post-rename state by editing the row after the receipt exists. This is the same family as the 0.20.3 pattern: a check that has never been seen to fail. This time the gate list was updated, but four of the seven load-bearing guards I broke left it green. A mutation pass on the safety guards belongs in Ender's definition of done for any data-path feature.

## Evidence

All runs used isolated `git archive 7321517` copies, with the worktree's own build-cache runtime (Python 3.14.8 and its FFmpeg). The copies sat under the short path `C:/Users/AnGeLZzZ/AppData/Local/Temp/sn21/`, because under the deep session scratch path the app's guard refuses outputs ("Verified metadata exceeds the supported Windows output path length"; see `baseline2.log`). The fixture-root mapping was the same as in `check-desktop.mjs`. Nothing ran in the worktree, the live DB, Z:, `dist/` (except reading `release-artifacts.json`) or the installed app.

Logs and probe sources are in `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/64106cea-b39e-4987-9571-6ad97339dc8a/scratchpad/shared/senua-0210/`:
- **Baseline:** `test_inplace_m4b` + `test_source_proofs` + `test_standing_admission`, 29/29 passed (`baseline3.log`).
- **Mutations:** `mutate.py` and `mut-M1…M9.log`. M1, M2 and M9 failed as expected; M4, M5, M6 and M7 passed (survived).
- **Probes:**
  - F1: `test_senua_probe_cover.py`, `probe-cover.log`;
  - F2 and F7: `test_senua_probe_rename.py`, `probe-rename.log`;
  - F6: `test_senua_probe_marker.py`, `probe-marker.log`.
- **Durability probe:** `wal-probe.sqlite3` (journal_mode WAL, synchronous 2).
- I did not run the full `npm run check`. Gate run 5 on the committed build is the authority for that.

## Verdict

- Total Critical: 0
- Total Major: 4
- Total Minor: 7

No safety-floor item: no unsafe Electron config, no secret leakage and no source-of-truth destruction. F3's unproven write targets the managed source path, needs a third-party rewrite after a crash, and is graded Major.

**Verdict:** RELEASE CLEAR

| # | Sev | Dim | file:line | Finding | Next cycle |
|---|-----|-----|-----------|---------|------------|
| F1 | Major | 2 Correctness | `audio_pipeline.py:524` | An in-place fallback makes the copy flow reuse an unvalidated stage cover; a 16.8 MP cover that 0.20.3 refused is now published | Reuse only a fully validated cover, or call `protected_cover` after cheap eligibility |
| F2 | Major | 5 Data safety | `inplace_m4b.py:362`, `:397` | After a crash or postcondition error past the rename, recovery records `published` without a receipt; `_retire_moved` refuses forever | Prove the destination hash and write an accepted receipt; replace the masking test |
| F3 | Major | 5 Data safety | `inplace_m4b.py:185`, `:208` | Undo truncates and writes before proving identity and content (same-ID rewrite, or reopen by path) | Identity check on every reopen; content proof before any write |
| F4 | Major | 3 Stability | `audio_jobs.py:371`, `:1078` | Startup `recover_all` and pre-attempt `clear` are untested (M4/M5 survive); startup errors are swallowed | Service-level crash-restart test; narrow and surface the `except` |
| F5 | Minor | 9 Hygiene | `source_cleanup.py:209`, `:416` | The in-place cleanup contract and receipt requirement have no negative test (M6/M7 survive) | Add refusal tests |
| F6 | Minor | 5 Data safety | `inplace_m4b.py:305` | Rollback drops the Zone.Identifier marker; attributes are restored but unverified | Restore the marker from the receipt, or document it |
| F7 | Minor | 5 Data safety | `inplace_m4b.py:362` | Recovery's `published` rests on the destination size alone | Prove the destination hash |
| F8 | Minor | 2 Correctness | `merge_service.py:2685` | The publication intent is committed before the locked guard; a review change there leaves a restored original but a non-retryable job | Journal inside the review lock, after the guard |
| F9 | Minor | 7 Maintainability | `inplace_m4b.py:109` | KeyError/TypeError become silent fallbacks; product code bends to test fakes | Narrow the conversion; fix the fake |
| F10 | Minor | 5 Data safety | `inplace_m4b.py:63` | The journal does not assert synchronous FULL, unlike the other pre-move journals | Assert FULL/EXTRA |
| F11 | Minor | 8 Drift | `Docs/…InPlaceM4B_Design…md:40` | Six design-note statements and `CHANGELOG.md:8` do not match the code | Align the text |
