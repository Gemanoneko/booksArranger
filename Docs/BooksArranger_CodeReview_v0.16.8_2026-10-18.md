# Code Review — Books Arranger v0.16.8

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-10-18
Tool: Books Arranger
Release: v0.16.8
Status: FINAL; red-team pass focused on deletion safety (brief items 1-6); dimensions 4, 7 and 8 read lightly
Commit range: 1e15943..65a1d144d743ef9c4c83f1759b86fd93dfb53bcd
  1e15943 docs: record v0.16.7 review and QA verdicts for 0534492 (docs only; the v0.16.7 report cleared 56c7532..0534492)
  74a78f9 feat: delete backups after verification; fast status under load; queue-next retries; kept-file groups
  65a1d14 chore: release v0.16.8 (package.json, package-lock.json, CHANGELOG in one commit)
Files changed: 42 files, +1275 / -258
Stand-down dimensions: none
Release source commit: 65a1d144d743ef9c4c83f1759b86fd93dfb53bcd
Release artifact manifest SHA256: 029546ade7b7d150efe5b0026399d1b1ea23149cd006f04c8dac8138021d9563
Release installer: dist/builds/6e8105c1-4d56-45be-a75d-65abf9c0aa49/Books-Arranger-Setup-0.16.8.exe
Release installer SHA256: c01dcde42ca03ecc4d5d80110bf280bf00f8bb4cd31d72f7ae1e55fc6fc08b3f
```

## Summary

v0.16.8 implements Sergei's 2026-10-18 rule (Brief, decision table): once a book's output is verified and its content still matches, all its backups go. Concretely:
- The recovery purge has no 24-hour wait and no idle gate. It runs right after a book's source cleanup, and on first start it covers every existing set.
- Replacement-recovery copies are purged.
- Source cleanups held only by download-marker metadata finish on their own.
- Folder jobs are settled.

The release also adds:
- a status snapshot that answers with the last result while a new one is computed;
- catalog-version caching of cleanup facts;
- queue-next for every Retry;
- kept-file attention groups with a "Keep files" control;
- a Quit exit bound.

I read every code hunk in the range, the CHANGELOG and the Brief decision.

Evidence I gathered myself:
- The installer hashes to the SHA256 above. `dist/release-artifacts.json` hashes to the manifest SHA256 above and names version 0.16.8 and `source_head` 65a1d14.
- All 51 packaged backend `.py` and `web/` files have the same content as HEAD. So do `desktop/main.js` and `desktop/quit-watch.js` inside `app.asar`.
- Nine deletion, status and quit suites ran 166 cases with 1 failure (F3); `quit-watch.test.mjs` passed 3 of 3.
- A probe that interrupts a purge at each guard checkpoint showed that every interrupted purge resumes to `deleted` with 2 of 2 copies removed.

## Release questions (deletion safety)

1. **Every deletion path re-verifies the output and the content. Yes. No path deletes on catalog state alone.**
   - **Recovery purge (`recovery_retention.purge`).** It is the gate for both the sweep and `_purge_recovery_now`. In order it checks:
     - `protected_output`: a durably completed job with a passed validation contract, the destination unchanged, the ancestry identity unchanged, and a full SHA-256 of the published output equal to the recorded one;
     - the immutable completion event;
     - `_source_safety`: source retirement completed with the same manifest and output, and every original path absent;
     - unknown-content refusal in the set folder;
     - per copy, `_prepare`: no alias, a single stream, and a full hash plus size and mtime equal to the reviewed original. The recorded native facts must also match when present.
   - Only then is the state set to `deleting` and `_dispose` run. `_dispose` re-runs the guard and revalidates ancestry before each file.
   - A copy that is already missing is only recorded (`record_absent`, which never touches a file).
   - **Replacement recovery (`replacement_retirement.purge_recoveries`).** It verifies the current replacement in full (`_current`: ancestry, links, size, full hash, guard). Per copy it checks the owned folder, recorded facts, links and full hash before disposing.
   - **Held source cleanups resumed (`_finish_held_cleanups`).** They go through the unchanged `CleanupJobs.run`: a full hash of the output, then per original `_match` (identity, size, mtime, attributes, full hash) both before and after the lease.
   - **Folder jobs.** `run_folders` starts with `protected_output`. "Already gone" only marks the job complete; nothing is deleted.
2. **First-start purge: idempotent and crash-safe. Nothing is deleted for a missing, unverified or changed output. Yes.**
   - A `deleted` row returns immediately.
   - A missing copy gets a terminal `absent_after_intent` receipt.
   - Any failure in `protected_output` raises before `deleting`, so the set is kept.
   - On Quit, the guard raises `InterruptedError` between files and the row stays `deleting`. On restart, removed files have terminal receipts and present files are re-proven and disposed. My probe interrupted at guard calls 3, 4 and 5 (0, 1 and 2 copies removed), and every case resumed to `deleted` with 2 of 2 removed.
   - Handle disposition is atomic, so a partial delete cannot corrupt a file.
3. **`zone_identifier.py` file-number change: the content is still hash-proven, and a different original is never removed. Yes.**
   - `validate` re-proves the held base by full hash and identity before persisting and after removal.
   - Removing the original needs its own deny-delete `VerifiedFile` and a second `_match`.
   - What the change loosens is the binding of the marker *stream* to the held base (m1). That concerns metadata only, and its bytes are journaled.
4. **Unknown-marker removal and folder jobs: safe.**
   - Any bounded marker (at most 8,192 bytes) is persisted, as base64 bytes plus SHA-256, under a primary key that includes `marker_sha256`, before the stream disposition.
   - Folder jobs: "already gone" is bookkeeping only. A busy-catalog folder job re-runs the verified `run_folders`.
5. **The status cache cannot drive any deletion. Yes.**
   - Every deletion trigger reads fresh rows: `recovery.due()`, `cleanup.status(job_id)`, `cleanup._rows`, `storage.folder_status()`, `replacements.rows()`. Every deletion re-verifies anyway.
   - `_catalog_cached`, the stale-answer `SharedSnapshot` and the quiet caches feed only status and pages. The update fence uses the uncached `state()`, and cached cleanup facts are never reused while cleanup work runs.
6. **The Quit watchdog cannot kill the engine mid-delete or mid-write. Yes.**
   - The engine's `_bound_exit` (`os._exit` after 20 s) is armed only after `finish_shutdown()` succeeds. `close()` joins the retention, jobs and source-cleanup threads, and raises if any is still alive; that makes the phase `blocked`, which never arms the exit.
   - The shell never kills the engine. `engineGoneExit` closes the host's stdin, which leads to the cooperative `stop_now` → `_shutdown`, and fires only after 5 s of refused connections, which come after the engine's server has closed.
   - Daemon threads that may still run (status computation, repair checks) write only atomic SQLite transactions.

## Rubric

### 1. Security

- Status: Pass
- Findings: none. `/api/audiobook/keep` sits in the trusted control path with `shape()`, `candidate_identity()` and `uuid_value()` checks, and inserts only into `kept_files`. The new attention groups are whitelisted.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - `merge_service.py:128` [Minor] When the bounded wait times out, `SharedSnapshot.get` returns the last finished answer even when it predates a control. That contradicts its docstring ("right after a control, does a reader wait … for a fresh one"). Display only.

### 3. Crash / Stability Safety

- Status: Concerns
- Findings:
  - `merge_service.py:637` [Minor] The sweep catches only `ValueError`. New calls inside it can raise `sqlite3.OperationalError` under conversion load: `replacements.rows()` in `_purge_replacement_recoveries`, `cleanup._rows` in `_finish_held_cleanups`, and `folder_status`/`_folder_set` in `_settle_folder_jobs`. That ends the retention thread for the rest of the run. It is safe in direction (nothing more is deleted until restart), but backups silently stop being purged.
  - `merge_service.py:625`, `:651` [Minor] `_post_current` is now set and cleared by both the retention thread and the converter thread, so the sweep's `finally` can clear the converter's marker. This affects only working-cleanup yielding and status, because `drained()` also requires the jobs thread to have ended.

### 4. Performance

- Status: Concerns
- Findings:
  - `merge_service.py:624` [Minor] The sweep holds `operation_lock` for one set's whole verification: a full hash of the output on Z: plus every copy. That now also happens while a book converts. On first start about 95 GB is hashed set by set, and controls that take the lock wait for the current set.

### 5. State & Data Safety

- Status: Concerns
- Findings:
  - **F1** `merge_service.py:632`, `merge_service.py:655` [Major] `purge()` records the keep-case reason with its fixed prefix (`recovery_retention.py:154`, `kept_reason`). Both automatic callers (the sweep and `_purge_recovery_now`) then overwrite it with raw `str(error)`, so `kept_files()` (`merge_service.py:880`) never sees `AUDIOBOOK_MISSING`/`AUDIOBOOK_UNVERIFIED`. As a result, case (B) books never appear under "Audiobook problem" and never get "Keep files". The Brief rule and the CHANGELOG promise ("flagged with the reason") are not met for (B). The files are kept, so the failure is in the safe direction. Fix: drop the callers' `_set` (purge already recorded the reason) or pass the reason through `kept_reason`. `test_backup_rule.py` seeds the reasons directly, so it does not catch this.
  - **F2** `recovery_retention.py:96`, `merge_service.py:632`, `merge_service.py:655` [Major] No purge consults the "Keep files" choice: `due()`, the sweep and `_purge_recovery_now` never read `kept_files`. Judy's spec says "Recovery copies are kept until you decide", that Keep files "never schedules deletion", and that copies are "present after Keep files". Yet a kept (B) set is re-tried on every start, and if its output verifies again (for example Z: was offline on the first start), its copies are deleted. Deletion still requires the full output verification and content match, which is within Sergei's rule ("in any case"), so no audio is lost. The conflict is between the rule and the button's promise. This is latent today because F1 hides (B) rows; it needs Sergei's decision before F1 is fixed.
  - `merge_service.py:667` [Minor] A replacement-recovery purge that refuses is caught and recorded nowhere, despite the comment "the relation's records say why". Those copies are kept silently, with no flag.
  - `recovery_retention.py:127` [Minor] A missing set folder is treated as "every copy already gone", and the set closes as `deleted`. If the recovery root were briefly unavailable, its copies would become untracked orphans. Nothing is deleted, and the root is local app data, so this is unlikely.
  - `zone_identifier.py:86` (with `_MarkerLease`, `:34`) [Minor] Without the index comparison, the stream opened by `path + ':Zone.Identifier'` is no longer bound to the held base, because the lease shares DELETE. A same-path rename-swap during a cleanup would remove another file's marker; its bytes are journaled, and the original's removal still re-proves identity and hash. Opening the stream relative to the base handle would restore the binding.

### 6. Input Handling

- Status: Pass
- Findings: none. The marker read stays bounded (`MAX_MARKER`, size equality), and the new `group` values are whitelisted.

### 7. Maintainability

- Status: Concerns
- Findings:
  - `zone_identifier.py:51` [Minor] `_known_marker` is now dead code.

### 8. Doc/Code Drift

- Status: Pass
- Findings: none beyond F1 and F2, which are recorded in dimension 5.

### 9. Build & Release Hygiene

- Status: Concerns
- Findings:
  - **F3** `scripts/check-desktop.mjs:19-28`, `tests/test_recovery_retention.py:73` [Major] `test_recovery_retention.py`, the deletion module's own suite, is not in the `check-desktop` gate, and at HEAD `test_cooperative_shutdown_resumes_partial_exact_purge` fails deterministically (`count` 2 != 1; 3 of 3 standalone runs). My checkpoint probe shows the behavior is correct: the purge now passes one more guard checkpoint before its first deletion, so the assertion is stale. Even so, the suite for the code that deletes about 95 GB was never run by the release gate. Add it to the gate and update the assertion.
  - The version bump and lockfile are in the same commit. The artifact and manifest hashes match the brief, and the packaged files match HEAD.

## Verdict

- Total Critical: 0
- Total Major: 3 (F1, F2, F3)
- Total Minor: 8

**Verdict:** RELEASE CLEAR

No Critical: no deletion path fires without a full output verification and a per-file content proof, and every failure mode found keeps files rather than deleting them. Before release, I recommend that Ender fix F1 and F3 and that Sergei rule on F2: should "Keep files" exempt a set from the rule?
