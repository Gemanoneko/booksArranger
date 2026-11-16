# Code Review — Books Arranger, NAS legacy source removal (uncommitted, over v0.28.12)

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-11-16
Tool: Books Arranger
Release: not yet versioned (uncommitted work over v0.28.12)
Commit range: bce9e94 (v0.28.12, HEAD) .. uncommitted working tree, in-scope files only
Files changed: 9 tracked files, +125 / -18 ignoring line endings (+221 / -114 raw), plus new tests/test_nas_source_removal.py (250 lines)
  native_io.py, runtime_file_disposition.py, source_cleanup.py,
  tests/test_nas_source_removal.py (new), tests/test_source_cleanup.py, tests/test_cleanup_resume.py,
  tests/test_storage_cleanup.py, and Docs/BooksArranger_RuntimeDisposition_Contract_2026-11-13.md,
  Docs/BooksArranger_StorageCompatibility_Implementation_2026-11-13.md, Docs/BooksArranger_Relocation_CoreReview_2026-11-13.md
Out of scope (not reviewed): audio_jobs.py, automatic_processing.py, merge_service.py, pause_state.py, web_server.py,
  tests/test_automatic_processing.py, tests/test_startup_loading.py, and any Browse/Save-As location work
Stand-down dimensions: Electron security N/A (Python backend, no Electron surface touched)
```

Accepted risk, not graded: Sergei's 2026-11-16 decision. On NAS volumes, source cleanup uses the pre-0.28 delete method (FileDispositionInfo on the exact open handle, then close), and the write-during-delete race that 0.28.0 closed is open again. Only what goes beyond that race is graded below.

---

## Summary

The change types the provider's remote refusal (`RemoteProviderRefused`). It adds `remote_handle()` as positive proof that a handle is remote (FileRemoteProtocolInfo succeeds and the drive is DRIVE_REMOTE). `VerifiedFile.dispose(remote_legacy=...)` falls back to the v0.5.0 / v0.27.0 delete call only when the hardened guard refuses this handle's own volume. Source cleanup passes `_nas_checks`, which repeats three checks through the held handles: same facts, a re-hash equal to the reviewed SHA-256, and the recovery copy still present. A guarded migration adds `cleanup_members.removal_method`. At startup, `_reclassify_remote_provider_holds` revives exactly the 0.28.x "remote/unverifiable" holds as paused.

Verified sound:
- The method choice is correct.
- The pre-delete checks run in the right order.
- The startup filters only revive the intended holds.
- The migration is safe.
- The delete call and the open share mode (FILE_SHARE_READ only) match 2e898f9 and v0.27.0 byte for byte.

One Major issue is real and was reproduced with probes. A NAS check that fails after the `removal_intended` commit leaves the member in that state while its original is still present. Restore then refuses permanently with "Restore collision", and in one ordering a track that was already removed can no longer be restored through the app. Nothing is lost on disk, and the recovery copies stay. No Critical findings.

Open question for Jane to confirm with Sergei (a product decision, not graded): after this update, the first Start re-runs every cleanup held under 0.28.x and removes all of those NAS originals that still pass the checks. There is no separate prompt. The docs credit this to the ruling. Confirm that Sergei wants automatic revival rather than a per-book Retry.

---

## Focus questions — answers

1. **Can the NAS path run on a local volume or on the wrong file?**
   - **Local NTFS:** no. Three things must all hold: the provider's typed refusal of this exact handle (`runtime_file_disposition.py:61-63`), FileRemoteProtocolInfo success, and a DRIVE_REMOTE anchor (`native_io.py:24-41`). A local NTFS handle fails FileRemoteProtocolInfo. The test `test_unverifiable_local_volume_is_never_given_the_nas_method` checks this against a real local handle.
   - **Exception:** loopback SMB, see m1.
   - **Wrong file:** no. Deletion goes through the handle opened at the checking step. That open used FILE_FLAG_OPEN_REPARSE_POINT, rejected reparse points and directories, required links == 1, and matched identity against the stored and approved identity. Its share mode is FILE_SHARE_READ only, and over SMB the server enforces that against other clients. The same handle is re-checked immediately before FileDispositionInfo.
   - **Path vs handle:** if they disagree (a symlinked ancestor either way), one of the two remote checks fails, so it fails closed.
   - **Path forms:** `ordinary()` rejects `\\?\` paths, so the anchor is always `Z:\` or `\\server\share\`. Unicode is passed as UTF-16 throughout.
   - **Scope:** `context.revalidate(path)` (explicit scopes, never the journal or owner) still runs before the provider check (`runtime_file_disposition.py:268`).
   - **No leftover side effects:** the refusal is raised before `prepare_disposition`'s try block, so no journal or ACL state is left behind (the test asserts no `*.intent.json`).
   - **Callers:** only `source_cleanup.py:618` passes `remote_legacy` (grep).
2. **Are the pre-delete checks complete and in order?**
   - **Order:** guard → output-location guard → `_sorted` → `_output_present` → `single_stream` → remote proof → `_nas_checks` → FileDispositionInfo.
   - **What `_nas_checks` covers:**
     - full facts equal to the checking-step facts (identity, dev/ino, size, mtime, links, attributes);
     - a full re-hash equal to `manifest.sources[].sha256`;
     - the recovery copy's size and links == 1, read through its write handle, which has been held since its full byte check.
   - **Nothing can be skipped or reordered:** any exception before `SetFileInformationByHandle` returns means nothing is set.
   - **Output:** checked by facts, not by hash (same as the hardened path and v0.27).
3. **Startup reclassification.** A hold is revived only if all of these hold:
   - reason == `RETAINED_HOLD`;
   - the latest cause is `originals_positively_retained` with exactly `REMOTE_PROVIDER_REFUSAL`;
   - the job is `completed`;
   - no restore was started;
   - the job is not a retained migrated job (and `run()` re-checks this through `_require_unheld_job`).

   Other refusal reasons, restored jobs and migrated jobs are not revived. A failed retry carries a different reason and is never revived again (`test_held_remote_retry_with_changed_bytes_stays_held`; probe P3). The only possible loop is theoretical; see m3.
4. **Migration and leftover states.**
   - The `ALTER TABLE ... ADD COLUMN removal_method TEXT NOT NULL DEFAULT ''` is guarded by PRAGMA and idempotent.
   - Every `cleanup_members` INSERT names its columns, and every `SELECT *` reader builds a dict. So it is safe on the live DB and on a rollback to 0.28.12.
   - A crash between FileDispositionInfo and the commit leaves `removal_intended` with the path gone. That path already reads as "Interrupted removal has unknown outcome", and Restore works, same as v0.27.
   - The `removal_intended` + original-still-present state is the defect in M1.

---

## Rubric

### 1. Security
- Status: Concerns
- Findings:
  - [Minor] m1 `native_io.py:24-41` — The protocol is not pinned to SMB. `remote_handle` accepts any network-redirector handle on a DRIVE_REMOTE path.
    - Loopback SMB (`\\localhost\C$\...`, or a mapped drive to this PC) puts local-NTFS originals on the legacy method. The repo's own `LoopbackSmbSourceCleanupTests` demonstrates this; it ran here, not skipped.
    - Any other redirector that answers FileRemoteProtocolInfo would also qualify. Some (NFS- and WebDAV-style clients) implement delete-on-close as delete-by-name at close. That turns the accepted write race into a replace-at-same-name race, where a never-reviewed replacement with no recovery copy is deleted. That is beyond the accepted risk.
    - Samba checks dev/inode before it unlinks on close, so an SMB NAS is not affected.
    - Fix: also require `info.protocol == 0x00020000` (WNNC_NET_SMB), and say "SMB volume" in the contract.
  - No shell-outs, no secrets.
  - The ctypes struct is correct: 116 bytes, class 13 = FileRemoteProtocolInfo.

### 2. Correctness & Logic
- Status: Concerns
- Findings:
  - [Major] M1 — see § 5. It is filed there because its effect is on recovery state.
  - [Minor] m3 `native_io.py:499-501` — Startup revival cannot tell a refusal of the file's own volume from a refusal of the disposition owner or journal location. A `context_for` refusal reaches `_raise_retained` with the same `REMOTE_PROVIDER_REFUSAL` text. If a control root were ever remote, that hold would be revived at every app start and fail again at every Start, with a full re-hash each time. This is theoretical today because Data stays on I:. Fix: re-raise context-side refusals with a distinct message or type.
  - [Minor] m4 `source_cleanup.py:135-160` — Revived holds that are historical cleanups change what the next Start does. merge_service Start runs only paused historical cleanups when any exist, and does not hand off to the audio queue. Revived paused cleanups also block `_start_historical_cleanup` ("Unrelated pending source cleanup must be resolved first"). This matters only if historical NAS holds exist. Fix: exclude historical cleanups from revival, or document it.

### 3. Crash / Stability Safety
- Status: Pass. The startup revival is database-only. JSON parsing is guarded. Non-JSON hold causes are already tolerated by `status()` and `identity_retry()`. A failure to set FileDispositionInfo raises with nothing set (probe P4).

### 4. Performance
- Status: Concerns
- Findings:
  - [Minor] m2 `source_cleanup.py:607-618,647-654` — `_nas_checks` re-hashes the whole original over the network inside `BEGIN IMMEDIATE` and `critical(CLEANUP)`.
    - For a large single-file source on a slow link, the catalog write lock is held for tens of seconds. Other writers wait up to the 10 s busy timeout and then fail with "database is locked", and Quit waits.
    - The hardened local path also hashes inside the transaction, but at local disk speed. v0.27 did no re-hash at all.
    - The ruling ("immediately before removal") dictates where the hash goes. Either document the cost, or ask Sergei whether the hash may move just before `BEGIN IMMEDIATE` with a cheap facts re-check left inside.

### 5. State & Data Safety
- Status: Concerns
- Findings:
  - [Major] M1 `source_cleanup.py:610-611` (intent commit) vs `:618` / `:647-654` (NAS checks after the intent) vs `:709-711` (restore collision) — A NAS failure after `removal_intended` is committed leaves that member in `removal_intended` with its original still present. Restore then raises "Restore collision; existing file preserved" every time.
    - **Triggers:**
      - a hash mismatch, which is the accepted race being caught;
      - an SMB read error during the re-hash;
      - a failed recovery-copy check;
      - FileDispositionInfo being denied;
      - a failed remote proof.
    - **Reproduced on private copies:**
      - **P1:** the first track fails the check. Nothing was removed, but Restore refuses.
      - **P2:** track 1 is removed and track 2 fails. Restore brings back track 1, then refuses forever. The cleanup stays `needs_attention` with the stale reason.
      - **P5:** the manifest order differs from path order. The failing track is reached first in the restore query, so the already-removed track can never be restored through the app. Its recovery copy `source-recovery/<id>/00000.mp3` stays on disk, and retention only discards copies of completed cleanups, so no bytes are lost.
      - If the original really changed, Retry cannot complete either. That leaves the book with no action that succeeds in the app.
    - **History:** this reintroduces Senua 0.21.3 F2 (the comment at `:603-604`) for the new checks. The same leftover already comes from hardened-local refusals since 0.28.0.
    - **Fix (Ender's choice):**
      - (a) also run the same pure re-reads (facts, reviewed hash, recovery copy) before the intent commit, and keep the in-transaction re-check;
      - (b) on any failure before FileDispositionInfo succeeds, return the member to `backup_verified` while the held handle still proves the same identity;
      - (c) make `_restore` treat a `removal_intended` member whose current file has the stored identity and the reviewed hash as never removed.
    - Add a test for a multi-track partial failure followed by restore.

### 6. Input Handling
- Status: Pass. No new external input. Paths reach `remote_handle` only after `ordinary()` and the held-handle checks.

### 7. Maintainability (no Critical findings on its own)
- Status: Concerns
- Findings:
  - [Minor] m5 `native_io.py:479-535` — The NAS method's safety lives entirely in a caller-supplied free callable (`remote_legacy`). A future caller that passes a no-op gets an unchecked delete. Fix: have `native_io` take the expected facts, the reviewed SHA-256 and the recovery handle, and run the checks itself.
  - [Minor] m6 tests — Coverage gaps:
    - There is no multi-track partial-failure + restore test (M1).
    - The revival tests have no negatives for a non-completed job, a started restore, or a retained migrated job.
    - There is no FileDispositionInfo-denied test on the NAS path.
    - The three edited legacy tests are in the pre-existing failing set, so their signature changes never run green: `test_source_cleanup.py:299`, `test_storage_cleanup.py:232`, `test_cleanup_resume.py:119`.

### 8. Doc/Code Drift (no Critical findings on its own)
- Status: Concerns
- Findings:
  - [Minor] m7 `Docs/BooksArranger_Relocation_CoreReview_2026-11-13.md:74` — Three doc statements don't match the code:
    - The doc says "any failure keeps the originals". For a multi-track book, only the remaining originals are kept, because earlier tracks may already be removed with recovery copies.
    - All three docs say "NAS" or "Z:", but the code gate is any remote drive behind a network redirector (SMB or other), loopback included (m1).
    - The contract calls the method "unchanged" since v0.5.0. That is true of the delete call and the share mode. The close path now raises when CloseHandle fails (a 0.28 change, not this diff).

### 9. Build & Release Hygiene
- Status: Concerns
- Findings:
  - [Minor] m8 — `tests/test_source_cleanup.py` shows a 196-line diff for a 2-line change, because mixed LF/CRLF was normalized. Git also warns LF→CRLF for `runtime_file_disposition.py` and the three docs. Review and commit with `--ignore-cr-at-eol` in mind, or split out the normalization.
  - There is no version bump or CHANGELOG entry yet; Sully adds those at release.
  - This report's filename carries no version (per the brief), so `check_release_preconditions.mjs` cannot match it to a release by itself.
  - Pre-existing, not counted against this diff: the source-cleanup regression net is red at baseline. That includes `test_actual_removal_and_exact_restore`, which fails with `RuntimeError: Exact file removal requires one admitted native catalog owner` because the legacy fixtures predate 0.28 owner admission. Green coverage of the removal loop today comes only from `test_nas_source_removal` and `test_storage_lifecycle`.

#### Targeted test spot-check (developer's baseline claim)

Two private exports were tested:
- **Baseline:** HEAD bce9e94 plus only the 7 out-of-scope dirty files.
- **Current:** the full working tree.

Both ran under the reviewer's scratch folder with private `BOOKS_QA_FIXTURE_ROOT`/`TEMP` and a 600 s timeout. `test_storage_cleanup` and `test_cleanup_resume` must run from `tests/`; run with `-m unittest tests.X` from the repo root, they fail to import `sorted_fixture`.

| Module | Ran | Current | Baseline | Same failing set |
|---|---|---|---|---|
| test_nas_source_removal | 11 | OK (loopback SMB tests ran) | n/a | — |
| test_source_cleanup | 35 | 2F / 8E | 2F / 8E | yes (run 2). Run 1 had one extra WinError 32 setUp flake in current, gone on rerun |
| test_storage_cleanup | 27 | 1F / 7E | 1F / 7E | yes |
| test_cleanup_resume | 23 | 7F / 6E | 7F / 6E | yes |
| test_replacement_jobs | 41 | 1F / 12E | 1F / 12E | yes (run 2). Run 1 differed by one WinError 32 flake each way |
| test_storage_lifecycle | 35 | run 1: 0E, run 2: 3E | run 1: 4E, run 2: 1E | no fixed set: all are WinError 32 "Destination directory cannot be protected" flakes in both trees |

The claim holds for four of the five modules. The fifth, `test_storage_lifecycle`, has no fixed baseline set: its errors are random sharing-violation flakes in both trees. None of the failures can be traced to this change.

---

## Patterns

Restore wedged by a `removal_intended` leftover is the third appearance of the same shape: 0.21.3 F2, then the 0.28.0 hardened refusals, now the NAS checks. Every check added after the intent commit re-creates it. A structural fix belongs in `_restore` or in a failure-path rollback, not in each caller.

---

## Verdict

- Total Critical: 0
- Total Major: 1
- Total Minor: 8

First-review verdict: RELEASE CLEAR. Superseded; the single live verdict line is at the end of the last re-review below.

Advisory (first review): fix M1 before Sergei runs the first post-update Start on the held NAS backlog. The revived cleanups are exactly the population in which a mid-book check failure would leave Restore wedged. M1 has since been fixed; see the re-review.

---

## Re-review 2026-11-16 (M1 fix)

```
Reviewer: Senua (Code Reviewer)
Date: 2026-11-16
Commit range: bce9e94 (v0.28.12, HEAD) .. uncommitted working tree; this pass reviews the delta since the first review above
Delta reviewed:
  native_io.py — VerifiedFile.delete_pending(); remote_protocol() with SMB-only and loopback refused (m1);
    OWNER_LOCATION_REFUSAL for journal/owner refusals (m3)
  source_cleanup.py — any failure after the intent commit goes through CleanupJobs._withdraw_intent;
    Restore goes through CleanupJobs._never_removed
  tests/test_nas_source_removal.py (now 26 tests, 540 lines); tests/test_source_cleanup.py (one test re-based to model a crash);
  wording in the 3 docs (m7)
Out of scope (not reviewed): desktop/*, web/app.js, the picker tests, Docs/BooksArranger_Brief.md, and the 7 other dirty files
Stand-down dimensions: Electron security N/A (no Electron surface touched)
```

### Summary

The M1 fix is sound. It works the same way on the NAS path and the hardened local path.

- **Withdraw:** a failure after the `removal_intended` commit puts the member back to `backup_verified`. This happens only when the still-held handle proves all of these:
  - neither method recorded a delete as set;
  - the native identity is unchanged;
  - there is one link;
  - no delete is pending;
  - the name is present.
- **Restore:** when that proof can't be made, Restore accepts the leftover only if a fresh open shows the exact checked original. Any other file is still kept and reported as a collision.
- m1 and m3 are fixed.
- The local hardened path has no regression.
- **No Critical findings.**

**M2 (new, Major): Restore over SMB has never worked on any SMB this machine can reach.**
- **What happens:** on loopback SMB it fails every time with WinError 32. Each attempt leaves a full-size temporary file in the library folder.
- **Why it matters:** NAS books depend on this Restore. The M1 fix makes the recorded state correct, and that state exists so Restore can run.
- **Origin:** the code is from v0.4.0. The NAS ruling makes it reachable again. My first review missed it.
- **No bytes are lost:** the recovery copies stay.

Two new Minors: m9 (the withdraw proof over SMB) and m10 (a test gap).

### Focus questions — answers

1. **Can `_withdraw_intent` mark a file "not removed" when it was removed or is pending deletion?**
   - **Hardened local: no.** `PreparedDisposition.mark_pending()` sets `kernel_success` before doing anything else, and withdraw refuses on it (`source_cleanup.py:676`). If `SetFileInformationByHandle` itself fails, the local kernel's answer is authoritative. While a delete is pending, NTFS reports links = 0 and DeletePending = True.
   - **NAS path, ordinary failures: no.** Every refusal (failed remote proof, `_nas_checks`, a denied delete) happens before or at the delete call. `disposition_method` is set only after the call succeeds, and nothing after it can raise (`native_io.py:556-567`).
   - **A delete that is set but reported as failed** (probe P6: the real call runs, then reports failure with WinError 64, as when an SMB reply is lost after the server applied it):
     - the member stays `removal_intended`;
     - delete-on-close removes the original;
     - Restore brings it back.
     - This holds on the NAS-simulated path and on the hardened path. Over a real loopback SMB handle the member also stays `removal_intended`.
   - **Dropped SMB session:** see m9. The three proofs (links, DeletePending, name present) are answers the SMB client can serve from its cache. A stale answer after a lost reply could therefore pass. Not reproducible here. On a real drop the held handle most likely fails, and then withdraw refuses (fails closed).
   - **If it ever happened:**
     - Restore skips `backup_verified` members (`source_cleanup.py:745`), so that track would not come back through the app.
     - Retention discards copies only when every member is `removed` (`recovery_retention.py`), so its recovery copy would stay on disk.
2. **Can `_never_removed` make Restore accept a file that isn't the original, or overwrite anything?**
   - **Overwrite:** no. It writes nothing to disk. It only resets the member row to `backup_verified` and skips that member (`source_cleanup.py:755-758`).
   - **Accepting the wrong file:** no. Acceptance needs all of these, read through a fresh `VerifiedFile` open (reparse points and directories refused) inside the library `DirectoryBoundary`:
     - the stored native identity (volume + file ID, dev/ino);
     - one link;
     - the reviewed size and timestamp;
     - a full SHA-256 equal to the reviewed hash.
   - A different file can pass only through file-ID reuse with byte-identical content and the same timestamp. Its bytes would then be the original's anyway.
   - **Probe P10:** two cases are refused as "Restore collision" and left untouched: a byte-identical replacement (new file ID, same bytes, same timestamp) and a changed timestamp. The developer's test covers changed bytes. A hard-link negative could not be built in this fixture (the held owner directories block CreateHardLink), so the `links != 1` check is confirmed by reading.
   - **Older rows:** member facts from before the identity fields existed compare as unequal, and fail closed as a collision.
3. **Does the m1 loopback refusal break the real-SMB tests' meaning? No.**
   - `smb_from_another_machine()` wraps the real `remote_protocol` and clears only the loopback bit. The SMB-protocol check and the DRIVE_REMOTE check still run on real values.
   - `assert_real_loopback` positively asserts that every answer seen was `WNNC_NET_SMB` with the loopback bit set.
   - Two tests prove that the uncleared case is refused end to end: `test_loopback_smb_original_is_never_given_the_nas_method` and `test_real_loopback_smb_handle_is_not_a_network_volume`.
   - **Probe P9:** FileRemoteProtocolInfo reports protocol 0x20000 with flags 0x31 (loopback set) for `\\localhost`, `\\127.0.0.1`, this PC's own name, and its own IPv4 address. `remote_handle` is False for all four, so the refusal does not depend on the name `localhost`.
4. **Any regression in the local hardened path? None found.**
   - Same failing sets as baseline in all four cleanup modules (table below). `test_storage_lifecycle` is 35/35 green in both trees.
   - `test_local_cleanup_still_uses_the_hardened_provider` passes, and the hardened journal records each closed removal.
   - **`dispose()` changes on the local path:**
     - the context is resolved in its own `try`, and any error there still reaches `_raise_retained`. Only a remote refusal gets the new prefix.
     - `RemoteProviderRefused` without `remote_legacy` still reaches `_raise_retained`.
     - `disposition_method` is set only after success.
   - The withdraw `try` now also covers the pre-checks (guard, output location, `_sorted`, `_output_present`, `single_stream`). All of them raise before any delete is set, so this is the intended scope (0.21.3 F2 / 0.28.0 leftover).
   - **Edited legacy test:** `test_missing_original_after_removal_intent_remains_unknown_not_adopted` now models a crash before the delete by disabling withdraw. That is the only way a `removal_intended` leftover can still arise, so the change is legitimate. It passes in both trees.

### Status of first-review findings

- **M1 — Fixed.** Verified by the tests, by mutation and by probes (below).
- **m1 — Fixed.** SMB only, loopback refused. Probe P9 above.
- **m3 — Fixed.** The control-root provider checks run in `DispositionContext.__enter__` via `_initialize` inside `context_for`.
  - `context_for` is now resolved apart from the target, and a remote refusal there carries `OWNER_LOCATION_REFUSAL`.
  - Startup revival never matches it. Covered by tests in both test classes.
- **m2, m4, m5 — Open, unchanged.**
- **m6 — Partly fixed.**
  - Added: multi-track partial-failure + Restore tests, and a denied-delete test.
  - Still missing: revival negatives (non-completed job, restore started, retained migrated job). None are in the file.
  - Also see m10.
- **m7 — Fixed,** except one sentence. "Restore brings them back" (Contract, CoreReview and StorageCompatibility NAS paragraphs) is not yet shown for NAS books; see M2.
- **m8 — Open.** `tests/test_source_cleanup.py` is still 199 changed lines raw against 9 with `--ignore-cr-at-eol`.

### New findings

- **[Major] M2 — Restore over SMB is unproven, and it fails on Windows SMB.** Code: `source_cleanup.py:748` (`DirectoryBoundary(root,path.parent)` held) and `:763-774`, then `native_io.py:240` (`publish_no_replace`).
  - **What happens:**
    - The developer's test comment says it (`tests/test_nas_source_removal.py:417-419`), and probe P7 reproduced it.
    - After a P2 partial failure over a real loopback SMB handle, every `restore()` raises `Handle-bound no-replace publication failed: [WinError 32]`.
    - Each attempt leaves the member `restore_intended`, plus a new full-size `.books-restore-<uuid>.partial` in the library folder. Two attempts left two.
    - Nothing in the code removes them. The only `owned_artifacts` 'temporary' cleanup is in `series_backfill.py`.
    - The recovery copies stayed intact.
  - **Cause (probe P7b):** the no-replace rename fails over SMB only while Restore's `DirectoryBoundary` holds the parent folder. Without those handles the rename succeeds over SMB. Locally it succeeds with them.
  - **Unknown: whether Sergei's NAS (Samba) refuses the same way.** Loopback goes to Windows' own SMB server.
    - There is some evidence it might not: `book_move` copy publication uses the same `publish_no_replace` + `DirectoryBoundary` shape, and the Storage doc records a successful no-replace publication on Z:.
    - Restore itself has never run against the NAS.
  - **Why it matters now:**
    - 0.28.x never removed a NAS original, so this path was unreachable.
    - The NAS ruling and the startup revival make it reachable for exactly the held backlog.
    - The M1 fix makes the catalog state right, but in-app recovery for NAS books still depends on this path.
  - **Why Major, not Critical:** no data loss. The recovery copies stay in `source-recovery/<id>/`. Retention never discards them for a cleanup that did not complete. The `.partial` files are themselves full verified copies.
  - **Fix (Ender's call):**
    1. Run one Restore against a private Z: fixture, as the earlier `retention-publication-…` fixture did. Writing on Z: needs Sergei's go-ahead.
    2. If it fails there, change how Restore holds the parent around the rename on SMB.
    3. Either way, make a failed Restore reuse or remove its own `.partial` when the rename provably did not happen. Note the v0.24.0 D1r4 rule: after a network error, the rename may have happened.
- **[Minor] m9 — The withdraw proof over SMB rests on answers the client can cache.** Code: `source_cleanup.py:663-687`.
  - Links and DeletePending come from the same FileStandardInformation answer, and the name check is a path lookup. The SMB client can answer all three from its cache.
  - Suppose a delete's SET_INFO reached the server but its reply was lost. A stale cached answer could then pass all three proofs, and the member would be withdrawn although the original is pending or already gone. The consequence is in Focus 1.
  - **Fix:**
    - On the NAS path, record on the `VerifiedFile` that the delete call was issued, immediately before `SetFileInformationByHandle`.
    - `_withdraw_intent` refuses whenever that record is set.
    - A denied delete then stays `removal_intended`. `_never_removed` (fresh open + full hash) and the next run already handle that state.
    - `test_denied_delete_then_restore` would then expect `removal_intended`.
  - The contract paragraph's example ("for example, the SMB session dropped") describes the case this fix would make true.
- **[Minor] m10 — The `delete_pending()` gate has no behavioural test.**
  - In the `nopend` mutation (`delete_pending` always False), every cleanup test still passes; only the gate's own unit test fails.
  - The links check reads the same FileStandardInformation and catches the pending delete first: it reads 0 while pending, both locally and over SMB (P8).
  - **Fix:** turn P6 into a test (a delete set but reported as failed must never be withdrawn), and add an identity-replacement negative for `_never_removed` (P10).

### Targeted test spot-check

Private exports under the reviewer's scratch:

| Export | Contents |
|---|---|
| `cur` | the full working tree |
| `base` | HEAD bce9e94 plus only the 7 out-of-scope dirty files |
| `pre` | `cur` with the M1 fix taken out: the withdraw call made `pass`, the `_never_removed` branch made `if False`, and `delete_pending` removed |
| `nowd` | `cur` with only the withdraw call removed |
| `nonr` | `cur` with only the `_never_removed` branch removed |
| `nopend` | `cur` with `delete_pending` always returning False |

How the runs were set up:
- A script made the mutations and required each replacement to match exactly once.
- Private `BOOKS_QA_FIXTURE_ROOT`/`TEMP`, and a 600 s limit per command.
- The working tree was never stashed or modified.
- `test_source_cleanup` and `test_storage_lifecycle` run from the repo root (`-m unittest tests.X`). `test_storage_cleanup` and `test_cleanup_resume` run from `tests/`.
- An export needs a `scratch/` folder, because some fixtures hard-code `<repo>/scratch`. Without it, every setUp errors.

`test_nas_source_removal` (26 tests):

| Tree | Result | What fails |
|---|---|---|
| cur | OK, 26/26 | none; the loopback-SMB tests ran, none skipped |
| pre | 10 F / 3 E | see below |
| nowd | 10 F | exactly the withdraw-dependent tests |
| nonr | 1 E | `test_unprovable_withdrawal_still_restores_through_the_restore_check` |
| nopend | 1 F | only `test_delete_pending_reads_the_exact_handle` (m10) |

What fails in `pre`:
- 7 of the 9 tests in `PartialFailureRestoreTests`:
  - 6 fail;
  - 1 errors: `test_unprovable_…`, because Restore raises a collision.
  - `test_restore_still_preserves_a_changed_file_it_cannot_prove` passes, as it should: it asserts the old collision behaviour.
- The M1 assertion in `test_nas_hash_mismatch_right_before_removal_keeps_every_original`.
- The 3 loopback-SMB cleanup tests.
- 2 errors only because `delete_pending` is missing.

The developer's claim holds: the M1 tests fail against the pre-fix code, and each of the two mechanisms has its own test.

Regression modules, current vs baseline (failing sets compared by test name):

| Module | Ran | Current | Baseline | Same failing set |
|---|---|---|---|---|
| test_source_cleanup | 35 | 2F / 8E | 2F / 8E | yes |
| test_storage_cleanup | 27 | 1F / 7E | 1F / 7E | yes |
| test_cleanup_resume | 23 | 7F / 6E | 7F / 6E | yes |
| test_storage_lifecycle | 35 | OK | OK | yes (no sharing-violation flakes in this run) |

The baseline failures are the same pre-existing set as in the first review (legacy fixtures that predate 0.28 owner admission).

### Probes (reviewer-only, private fixtures, removed after the run)

| Probe | Setup | Result |
|---|---|---|
| P6 | NAS-simulated volume, real local handle. The delete is really set, but the call reports WinError 64. | Member stays `removal_intended`. The original is removed at close. Restore brings both tracks back. |
| P6-h | Same on the hardened local path | Same result. `kernel_success` is False and links reads 0, so the member is not withdrawn. |
| P6-smb | Same over a real loopback SMB handle | Member stays `removal_intended`. The original is removed at close. |
| P8 | `delete_pending()` on a real SMB handle | Reads False, then True after a set, then False after clearing. Links read 0 while pending. |
| P9 | Loopback flag by host form | 0x31 for `localhost`, `127.0.0.1`, this PC's name and its IPv4 address. `remote_handle` is False for all four. |
| P10 | `_never_removed` negatives | A byte-identical replacement and a changed timestamp each give a collision, and the file is left untouched. |
| P7 | Restore over loopback SMB after a P2 failure | WinError 32 on both attempts. Each attempt leaves `restore_intended` and a new 2048-byte `.partial`. Recovery copies intact. |
| P7b | `publish_no_replace` over loopback SMB | Fails while Restore's `DirectoryBoundary` holds the parent. Succeeds without it. Succeeds locally with it. |

### Verdict (re-review)

- Total Critical: 0
- Total Major: 1 open (M2, new). M1 is closed.
- Total Minor: 7 open (m2, m4, m5, m6 partly, m8, m9 new, m10 new). m1, m3 and m7 are closed.

Re-review verdict: RELEASE CLEAR. Superseded; the single live verdict line is at the end of the restart-intent review below.

Advisory: before Sergei runs the first post-update Start on the held NAS backlog, do two things:
1. Run one Restore on a private Z: fixture (M2). That is the population in which a mid-book failure leaves earlier tracks removed, and in-app recovery for it is unproven.
2. Apply m9's one-flag hardening. It is cheap, and it closes the only remaining way for a withdraw to be wrong.

---

## Re-review 2 2026-11-16 (Restore over SMB)

```
Reviewer: Senua (Code Reviewer)
Date: 2026-11-16
Commit range: bce9e94 (v0.28.12, HEAD) .. uncommitted working tree; this pass reviews the delta since re-review 1 above
Delta reviewed:
  native_io.py — remote_drive() (:59); created_facts() (:602); delete_issued set right before the NAS delete call (:581);
    publish_no_replace attaches rename_status to its rename errors (:294)
  source_cleanup.py — RENAME_REFUSED (:40); Restore holds the library folder with rename_destination on DRIVE_REMOTE (:779);
    _discard_restore_temporary (:706-725) on a provable non-rename (:801-821) or for an earlier unknown outcome (:794-798);
    _withdraw_intent refuses on delete_issued (:681)
  tests/test_nas_source_removal.py (now 35 tests, 745 lines); contract doc, new Restore paragraph
Out of scope (not reviewed): desktop/*, web/app.js, the picker tests, Docs/BooksArranger_Brief.md, and the 7 other dirty files
Stand-down dimensions: Electron security N/A (no Electron surface touched)
```

### Summary

The M2 fix is sound, and so is the m9 fix. **No Critical findings.**

- **Restore over SMB now works.** On a network drive, the library folder is held with WRITE sharing, the same mechanism `book_move._rename` already uses everywhere. DELETE sharing stays denied, and the rename is still no-replace. The real loopback-SMB test passes. With the change taken out, it fails with the old WinError 32.
- **The `.partial` cleanup can only remove Restore's own copy.** Its safety comes from the identity check, not from the status codes. Removal needs all three: the file still at the temporary name, the native identity captured through the creating handle, and one link. A temporary that was renamed into place is therefore out of reach, even when the rename call lies about its outcome (probe P11, locally and over real SMB).
- **The new use of the NAS delete method is safe.** Reasons are under Focus 2. Sergei still has to approve it.
- **m9 closes the gap.** Once the NAS delete call is issued, the member is never withdrawn. Members are not left stuck: Restore's own check (`_never_removed`) handles an original that is still unchanged, and Restore brings back one that is gone.
- **One new Minor, m11.** It is the price of m9: a kept original that is later changed now blocks Restore of the tracks after it.

### Focus questions — answers

1. **Can `rename_destination=True` on a remote target allow an overwrite or a swapped folder? No.**
   - **Overwrite:** no-replace is part of the rename request itself (`replace=False`), so the server refuses an existing name. Folder sharing does not change that. Over real SMB, a file that arrives at the original's name before the rename stays, and the rename returns 80/183. The developer's test `test_smb_restore_never_overwrites_and_removes_its_own_temporary` covers this.
   - **Swapped folder:** DELETE sharing is still denied on the folder and on every ancestor, so the folder cannot be renamed or deleted while Restore holds it. **Probe P15:** while Restore held the SMB library folder, renaming it failed with WinError 32 both through `\\localhost\C$` and through the local path. A sibling file could still be created in the folder, which is harmless.
   - **Unchanged, not new:** over SMB the server resolves the rename target by name. A process running on the NAS itself is not bound by SMB share modes. In theory, such a process could swap the folder mid-Restore, and the file would land in the swapped-in folder, still never overwriting anything. This was equally true with the old sharing and is true for `book_move` today.
   - **What WRITE sharing allows:** others may open the folder itself for writing (add file, write attributes). Nobody can rename it, because renaming needs DELETE.
2. **Can `remote_drive` misclassify a drive in a way that matters? No.** It only chooses the folder's sharing mode and grants no removal authority. Removal still needs `remote_handle` (SMB to another machine, DRIVE_REMOTE) or the hardened local guard.
   - **Local read as remote** (loopback UNC, or a drive mapped to this PC): the folder is shared for WRITE; DELETE is still denied. A refused rename there keeps its `.partial`, because loopback never gets the NAS method.
   - **Remote read as local:** the old sharing comes back. On Windows SMB the rename fails again with WinError 32, as before the fix. The temporary is still removed, through the provider refusal and then the NAS method. That is fail-closed.
   - **A remote library reached through a local symlink:** `DirectoryBoundary` refuses it before any of this runs.
   - **Probe P16:** `C:` and `I:` read False; `\\localhost\C$` and `\\127.0.0.1\C$` read True.
3. **Can the `.partial` removal delete anything that isn't Restore's own temporary? No path found.**
   - **What removal requires, all of it:**
     - a `.books-restore-*.partial` name in the original's own folder;
     - the name still present;
     - a fresh `VerifiedFile(delete=True)` open of that name. It does not follow reparse points, it refuses directories, and it shares READ only;
     - the native identity equal to `made`, which `created_facts` read through the `open(temp,'xb')` handle that CREATE_NEW had just made;
     - one link.
   - The check runs once before dispose, and once more through `remote_legacy` right before the NAS delete call.
   - **A status code that really means the rename succeeded:** this does not matter for safety. If the rename happened, nothing is at the temporary name any more. **P11** made the rename really happen and then report 183. The discard found the name absent and removed nothing, both locally and over real SMB. The Windows SMB client did not answer "present" from its cache. The next Restore completed.
   - **The status set itself** (5/32/33/80/183) is correct for when the cleanup runs at all. Windows SMB and Samba both answer a replayed rename to the file's own name with success, not with a collision.
   - **Unknown outcomes** (for example WinError 64) keep the temporary. This is verified by the `st64` mutation below.
   - **Races:**
     - another SMB client cannot rename or delete the temporary while it is held, because the handle has DELETE access and shares READ only;
     - Samba checks the file ID before it unlinks a delete-on-close file;
     - a hard link needs FILE_ADD_FILE on the held folder. Locally, `DirectoryBoundary` blocks that, which is why the P10 hard-link negative could not be built.
   - **Worst case, even if every check above failed:** the file removed would be a copy of the recovery copy. That recovery copy was re-hashed just before the temporary was written. It is held for the whole member and stays in `source-recovery/<id>/`. Retention never discards it while the member is `restore_intended`.
   - **The new NAS-method use, judged:** safe, and lower stakes than the original-file use Sergei already accepted.
     - The accepted write race does not matter for an app-owned file with a uuid name.
     - What gets removed is a copy, never a source original.
     - Loopback and non-SMB redirectors keep the file.
4. **m9: does `delete_issued` close the dropped-session gap without leaving a member stuck forever? Yes.**
   - **Closes the gap:** the flag is set right before `SetFileInformationByHandle`, and `_withdraw_intent` refuses on it before any cached answer is read. The `noiss` mutation (flag removed) fails exactly the two m9 tests. In one of them, every cached answer passes and the member is withdrawn anyway.
   - **Not stuck:**
     - *Delete really applied (lost reply):* the original is gone at close, and Restore brings it back (test).
     - *Delete denied, original unchanged:* `_never_removed` makes a fresh open and a full re-hash, resets the member to `backup_verified`, and Restore goes on (test).
     - *Retry:* `run()` re-checks a `removal_intended` member whose original is present through `_match`. A missing one gets the existing "Interrupted removal has unknown outcome" message.
     - *Read-only originals:* `_match` already rejects any attribute other than ARCHIVE/NORMAL, so a read-only NAS file (the usual cause of a denied delete-on-close) never reaches the delete.
   - **One residual:** see m11.

### Status of earlier findings

- **M2 — Fixed.** Shown against Windows SMB, by test and by mutation. Still unproven on Sergei's Samba NAS (see the advisory).
- **m9 — Fixed.** Shown by test and by mutation.
- **m10 — Mostly fixed.**
  - The `nopend` mutation now fails `test_hardened_delete_set_but_reported_failed_is_caught_by_the_pending_delete_check` (withdrawn True), not only the unit test.
  - Still missing: an identity-replacement negative for `_never_removed` (P10: byte-identical file, new file ID).
- **m5 — Open, and wider.** `remote_legacy` now has a second caller, `_discard_restore_temporary`, which passes `same`. The first review's "only source_cleanup.py:618 passes remote_legacy" no longer holds. Both callers are correct today, but the fix proposed for m5 now covers two call sites.
- **m6 — Open, partly.** There are still no revival negatives: non-completed job, restore started, retained migrated job.
- **m2, m4, m8 — Open, unchanged.** `tests/test_source_cleanup.py` is still 199 lines changed raw.
- **m7 — Closed.** The NAS paragraphs' "Restore brings them back" is now backed by real-SMB tests. The new Restore paragraph matches the code. It says the folder is held WRITE-shared "during that rename", but it is actually held for each member's whole restore, which is harmless.

### New findings

- **[Minor] m11 — After m9, a kept original that is later changed blocks Restore of the tracks after it.** Code: `source_cleanup.py:790` (raise on the first collision), with `:681` (no withdrawal once the delete call was issued).
  - **The sequence:**
    1. A NAS delete call is issued and fails, so the member stays `removal_intended`.
    2. Sergei then edits that kept original, for example by retagging it.
    3. `_never_removed` correctly refuses it, and Restore raises "Restore collision; existing file preserved". This is right for that file.
  - **The problem:** the loop stops there. Any removed track Restore reaches later is not brought back through the app.
  - **Probe P14** shows the contrast:
    - current code: collision, and the removed track is not back;
    - the `noiss` mutation (before m9): the member was withdrawn, Restore skipped it, and the removed track came back.
  - **Impact:** no bytes are lost; the recovery copies stay. The trigger is rare: a delete denied after every check passed, plus a later edit.
  - **Fix:** let Restore go past a member collision and report every collision at the end. This is the structural fix the Patterns section already points to. Do not relax `_never_removed` to identity-only: file IDs on a Linux NAS can be reused after deletion.

**Open question for Jane to confirm with Sergei** (a product decision, not graded): approve the NAS delete method for Restore's own `.partial`.
- **My judgment:** safe (Focus 3).
- **The contract's Restore paragraph already reads as approved** ("on a NAS the NAS method").
- **If Sergei declines:** drop the `remote_legacy=same` argument at `source_cleanup.py:722` and that sentence. A failed NAS Restore would then keep its `.partial`, as it did before the fix. Restore itself still works.

### Targeted test spot-check

How the exports were run:
- Private exports under the session scratchpad: the working tree minus Docs, plus `scratch/`.
- Private `BOOKS_QA_FIXTURE_ROOT`/`TEMP` outside the repo, and a 600 s limit per command.
- The working tree was never stashed or modified.
- `test_storage_cleanup` and `test_cleanup_resume` ran from `tests/`.

Each mutation was applied by a script that requires its replacement to match exactly once:

| Export | Change from the current tree |
|---|---|
| `nord` | Restore folder held without `rename_destination` |
| `nodisc` | both `.partial` discards disabled |
| `noiss` | `delete_issued` never set (m9 off) |
| `st64` | WinError 64 added to `RENAME_REFUSED` |
| `noid` | the identity check removed from `same()` |
| `nopend` | `delete_pending()` always False |
| `pre` | `nord` + `nodisc` + `noiss` (the state at re-review 1) |

`test_nas_source_removal` (35 tests):

| Tree | Result | What fails |
|---|---|---|
| cur | OK 35/35, twice; 0 skipped | none. All 5 loopback-SMB cleanup/Restore tests and the 3 real-SMB dispose tests ran |
| nord | 2 E | both SMB Restore tests: `Handle-bound no-replace publication failed: [WinError 32]` |
| nodisc | 4 F (+1 setUp flake) | `test_failure_before_the_rename_…`, `test_local_collision_…`, `test_unknown_rename_outcome_…`, `test_smb_restore_never_overwrites_…` |
| noiss | 2 F | `test_denied_delete_then_restore` and `test_nas_delete_set_but_reported_failed_is_never_withdrawn` (withdrawn True) |
| st64 | 1 F (+1 setUp flake) | `test_unknown_rename_outcome_…`: the temporary is removed on an unknown outcome |
| noid | 1 E | `test_a_temporary_that_is_no_longer_the_file_restore_made_is_kept`: the swapped-in file was deleted |
| nopend | 2 F | the m10 behavioural test and the `delete_pending` unit test |
| pre | 5 F / 2 E | the union of `nord`, `nodisc` (local) and `noiss` |

The developer's fail-on-old-code claims hold for every mechanism checked. The two setUp flakes were `support_dispositions` → `DirectoryBoundary` WinError 32 "Destination directory cannot be protected". That is the known environmental sharing-violation flake, in tests unrelated to the mutation.

Regression modules, current vs baseline (HEAD bce9e94 plus the 7 out-of-scope files). Failing sets were compared by test name:

| Module | Ran | Current | Baseline | Same failing set |
|---|---|---|---|---|
| test_source_cleanup | 35 | 2F / 8E | 2F / 8E | yes |
| test_storage_cleanup | 27 | 1F / 7E | 1F / 7E | yes |
| test_cleanup_resume | 23 | 7F / 6E | 7F / 6E | yes |
| test_storage_lifecycle | 35 | run 1: 2E, run 2: OK | 1E | no fixed set; all are the same WinError 32 setUp flake |

These are the same pre-existing failing sets as in the first review and re-review 1.

### Probes (reviewer-only, private fixtures, removed after the run)

| Probe | Setup | Result |
|---|---|---|
| P11 | Local. The rename really happens, then reports 183. | Discard found the temporary's name absent and removed nothing. The restored file was intact, and the next Restore completed. |
| P11-smb | Same over real loopback SMB, with the NAS method reachable | Same result. The SMB client did not report the renamed-away name as present. |
| P14 | Delete denied on the first member Restore reaches, then the kept original is edited, then Restore | Current code: `removal_intended`, collision, removed track not back. `noiss`: withdrawn, removed track back. (m11) |
| P15 | Rename the SMB library folder while Restore holds it WRITE-shared | WinError 32 through SMB and through the local path. Restore then completed. |
| P16 | `remote_drive` by path form | `C:` False, `I:` False, `\\localhost\C$` True, `\\127.0.0.1\C$` True |

### Verdict (re-review 2)

- Total Critical: 0
- Total Major: 0 open. M1 and M2 are closed.
- Total Minor: 7 open (m2, m4, m5 wider, m6 partly, m8, m10 partly, m11 new). m1, m3, m7 and m9 are closed.

Re-review 2 verdict: RELEASE CLEAR. Superseded; the single live verdict line is at the end of the restart-intent review below.

Advisory:
1. Get Sergei's answer on the `.partial` NAS-method question above before commit.
2. Before the first post-update Start on the held NAS backlog, run one Restore on a private Z: fixture. Writing on Z: needs Sergei's go-ahead. Restore over SMB is now proven against Windows' own SMB server, but never against the Samba NAS. If it fails there, the fix leaves no `.partial` behind, but in-app recovery for NAS books would still be unproven.

---

## Restart-intent review 2026-11-16 (9522858)

**Status: not in 0.28.13.** Sergei took this work out of the release. On main, 0125c57 reverts 9522858, and 55b98aa bumps the version to 0.28.13. The work stays on branch `feature/restart-intent` (head 9522858) for the next version. Every R- finding below applies to that branch, not to 0.28.13. The 0.28.13 verdict is at the end of this section.

```
Reviewer: Senua (Code Reviewer)
Date: 2026-11-16
Commit reviewed: 9522858 "feat(restart): restore saved work after restart from persisted run intent" (parent 01a1901),
  now the head of feature/restart-intent
Files: pause_state.py, audio_jobs.py, automatic_processing.py, merge_service.py, web_server.py,
  tests/test_automatic_processing.py (+2 tests), tests/test_startup_loading.py (+1 test); +259 / -20
Stand-down dimensions: Electron security N/A for 9522858 (Python backend only)
```

### Summary

What changed: the app now saves whether the audiobook queue and automatic processing were running. After a restart, it starts them again by itself. Before this, a restart never started anything; Sergei pressed Start.

- **No Critical findings.**
  - Explicit stops hold. Pause, Stop and Cancel start each record "user", and nothing they stopped comes back after a restart.
  - Safety holds (disk full, working-file hold, destination review) stay held.
  - The new table is additive and idempotent, and 0.28.12 ignores it.
  - The restore can't crash startup or start a second worker.
- **Four Majors.**
  - Two concern the first launch of the version that ships this branch: it can start automatic processing by itself (R-M1), and that start can be the first run of the NAS backlog that ad28ff9 re-opened (R-M2).
  - One is a rollback hole (R-M3).
  - One is release hygiene: the commit breaks two existing tests, so a build of this branch fails its full-suite entry check until they are updated (R-M4).
- **Product note for Jane.** This reverses a written rule. The Brief says "Server restart never starts an automatic run: Start resumes saved work." (`Docs/BooksArranger_Brief.md:489`). Sergei chose to ship the commit, so the code is now the rule, but the Brief still states the old one (R-m4).

### Focus questions — answers

1. **Does work Sergei paused stay paused? Yes, within this version. Does it ever auto-start something he stopped? Nothing he explicitly stopped. It does start work he left paused under 0.28.12 (R-M1), and after a rollback it can start a queue he paused (R-M3).**
   - **Pause audiobook jobs:** `merge.pause_work` clears the intent and records "user" in one transaction (`merge_service.py:924`). The startup test's `user` subtest pins this; the `nopauseclr` mutation fails it.
   - **Pause while automatic processing runs:** the endpoint now calls `automatic.pause_jobs`, which runs `stop_work(origin='user')`, then `_pause_stopped`, then `merge.pause()`. Same result as above.
   - **Stop, Cancel start, or Pause while a restored start is still pending:** `_cancel_restart` clears `restart_paused` and records "user" (`automatic_processing.py:458`, `:510`, `:526`).
     - Probe P2: a restored start is pending on a scan, then Stop. Result: `restart_paused=0`, origin user, pending start gone, and the next launch does not restore.
     - This is correct, but no test pins it (the `nocancel` mutation passes everything; see R-m2).
   - **Safety holds:** `_hold_queue` clears the intent and records "interrupted", and automatic restore refuses on a jobs "interrupted". The `hold` subtest pins this; the `oldhold` mutation fails it.
   - **`stop_work` with no origin:** before any check, the origin is set to closing (after `close()`), interrupted (a forced safety stop) or user (the Stop button) (`automatic_processing.py:504`). So `close()` after a Quit keeps the restart flag, and the Stop button counts as Sergei's. Probe P1 confirmed both.
   - **What restarts by itself:** a queue that was running when the app closed, updated or crashed, and an automatic run stopped by Quit, update or a crash. A Windows restart counts, because session end is a Quit.
2. **DB migration (`audiobook_run_intent`).**
   - **Idempotent:** `CREATE TABLE IF NOT EXISTS` plus `INSERT OR IGNORE` of one row, inside AudioJobs' existing construction transaction.
   - **Upgrade inference:** it reads `running` rows before `_recover` resets them, and sets 1 only when no jobs pause is saved. The 0.28.12 "Restart to update" path records "update", so it infers 0.
   - **Safe on the live catalog:** one tiny table, and no existing rows are rewritten. The `restart_paused` column already existed.
   - **Rollback to 0.28.12 is safe to open.** 0.28.12 never reads the table, and every whole-schema check in the tree is a subset check (for example `desktop_catalog.py:41`).
   - **Coming back after a rollback is not safe.** 0.28.12 never writes the row, so a stale `active=1` survives the round trip, and the next upgrade resumes a queue Sergei paused under 0.28.12 (R-M3).
   - **Automatic processing gets no migration at all:** legacy `restart_paused=1` rows and legacy "closing"/"update" pauses take on the new meaning (R-M1).
3. **Transactions and locks in start and cancel-restart.**
   - **`start()`:** the run update and the attribution clear are now one transaction, which is good. The continue path lost `_update`'s busy retry (`sqlite_retry.transaction`). It is now a plain `connect()`, as the new-run INSERT already was (R-m1).
   - **`stop_work`:** `restart_paused` is written in the same guarded update as Stopping (`AND state='Running'`), so a worker that already wrote Paused is never overwritten. If a Quit loses that race, the run is left at `restart_paused=0`, and init's `elif` then sets it from the "closing" attribution on the next launch.
   - **`cancel_start` / `_cancel_restart`:** one transaction under `self.lock`. If the attribution write fails, the flag clear rolls back with it.
   - **New `with _BULK_LOCK, connect(...)` blocks** (`merge_service.py:985`, `:1037`) do catalog I/O under the global lock, which is not re-entrant.
     - No re-entry path found: `allow()`, `_start_allowed` and `pause_state` take no merge lock. This matches the existing `_authorize_automatic_cleanup` pattern.
     - A busy catalog can hold `_BULK_LOCK` for up to the 10 s busy timeout, and Pause waits behind it (R-m1).
4. **`_restore_saved_work` at startup.**
   - **Crash:** no new path. `restore()` runs inside `try/except Exception`. The `retained_runtime()` call before it is outside the try, but `_start_background()` makes the same call one line earlier, so the exposure is not new (R-m5).
   - **Double start:** no. The loader calls the restore once.
     - The queue keeps one worker: `_thread.is_alive()` and the `_resuming` token, both checked under `jobs._lock`.
     - Automatic `start()` checks its own thread under `self.lock`.
     - A press that races the restore gets "busy" and is kept (`start_when_settled`).
     - A Pause or Quit that races the restore wins, through the start generation (`_start_allowed`), the `self.closing` check and `_server_closing()`.
   - **NAS reclassification (ad28ff9):** no race. `_reclassify_remote_provider_holds` runs inside `CleanupJobs.__init__`, during MergeService construction on the same loader thread, before `_restore_saved_work`. The order is fixed, and that order is the problem: the restore can be the first start of the re-opened NAS backlog (R-M2, probe P5).
5. **Error swallowing.**
   - `_restore_saved_work` prints any failure to stderr only, and the page shows Paused with no reason. That is the safe direction (nothing starts), but Sergei can't see it (R-m5).
   - `restore_work_after_restart` drops "closing"/"stale" refusals, which is correct. It records any other refusal through `_record_start_failure`, which is good. Exceptions other than `StartRefused` reach the print above.
   - The opposite problem also exists: `_hold_queue` now writes to the catalog between `_stop.set()` and the safety callback. If that write fails, the error escapes and `on_working_hold`/`on_space_hold` is skipped (R-m1).

### New findings

- **[Major] R-M1 — The first launch of the version that ships this branch can start automatic processing by itself, from a state that 0.28.x meant as "wait for Start".** Code: `automatic_processing.py:117-126` (init) with `:420-433` (`restore_after_restart`).
  - The jobs side infers intent on upgrade only from a running job with no saved pause. Automatic processing gets no such rule, so two legacy states take on the new meaning:
    1. A run that 0.28.12 left Paused by Quit or by Restart to update (attribution "closing"/"update", `restart_paused=0`). The new init sets `restart_paused=1`, and the restore starts the run. **Probe P3** confirms this. It includes the very "Restart to update" that installs this release, if automatic processing is running when Sergei clicks it.
    2. A run that 0.28.12 marked restart-paused after a crash (`restart_paused=1`, "Paused after server restart — start to continue saved work"). It is restored as it is. **Probe P4** confirms this.
  - In both cases Sergei may have looked at "Paused" for several sessions and chosen not to press Start. 0.28.12's contract told him nothing would start without that press.
  - Neither case is a stop he made. A run he stopped records "user" and is never restored.
  - **Fix:** a one-time upgrade step that mirrors the jobs rule. On the first launch with the new table, clear legacy `restart_paused` on Paused runs, and skip the "closing/update" `elif` unless the run was Running/Stopping at that launch. Or Sergei decides this is what he wants, and the release note says so.
- **[Major] R-M2 — The startup restore removes the human Start in front of the re-opened NAS backlog.**
  - Code: `merge_service.py:1025-1040`. `_resume_guarded` runs every `waiting`/`paused` cleanup before the queue.
  - Three paths reach it:
    - the jobs restore (`merge_service.py:976`);
    - the restored automatic worker's `_resume_queue` (`automatic_processing.py:661-666`);
    - each later approval's `resume(recheck=False)`.
  - ad28ff9 turns held NAS cleanups into ordinary paused cleanups at construction, to run "on the next Start or Resume". Until now, every start traced back to a press. With this commit, the app's own launch is one.
  - **Probe P5:** saved jobs intent, one unfinished job and one paused cleanup. The startup restore called `CleanupJobs.resume` with the jobs handoff, with no press.
  - **When it fires on the first launch:** in R-M1's automatic cases, or after a 0.28.12 crash mid-conversion (a running row with no saved pause gives intent 1). After that, it fires after any restart with saved intent, including a Windows restart.
  - **Why it is not Critical:** the deletions are the reviewed NAS path. `run()` repeats every check, and the recovery copies are kept. Only the trigger changed.
  - **What it changes:** advisory 2 of re-review 2 said "Before the first post-update Start on the held NAS backlog, run one Restore on a private Z: fixture". That can no longer wait for Sergei's first Start. Two ways out:
    - run that check before Sergei installs a build of this branch;
    - or have Ender keep the restore away from cleanups: the queue restarts, and cleanups wait for a press. This is a product call for Sergei.
- **[Major] R-M3 — After a rollback to 0.28.12 and back, a queue Sergei paused restarts by itself.** Code: `merge_service.py:976-999` (`restore_work_after_restart` checks only `jobs_active`), `pause_state.py:23-38`.
  - 0.28.12 records a user Pause in `pause_attribution`, but never touches `audiobook_run_intent`. A row left at 1 by this version survives the round trip.
  - **Probes P6 / P6b:** `active=1` plus a saved "user" jobs pause. The startup restore started the cleanup backlog (P6). Without a backlog, it started the queue worker (P6b).
  - Automatic restore already refuses on a "user" jobs pause (`automatic_processing.py:430`); the jobs path does not.
  - **Fix (one line):** in `restore_work_after_restart`, return when `pause_state.read(db,'jobs')` has origin "user" or "interrupted". Add a test.
- **[Major] R-M4 — The commit breaks two existing tests, so a build of this branch fails its full-suite entry check.** Both pass on 01a1901 and fail on 9522858, in the same export and environment:
  - `test_backend_242.PauseAndMembershipTests.test_cancel_reports_whether_any_pending_start_existed` errors with `AttributeError: 'AutomaticProcessing' object has no attribute 'database'`. The test builds the object with `__new__`, and `cancel_start` now reads the run row.
  - `test_merge_http.MergeHTTPTests.test_automatic_controls_draft_token_shape_and_scanner_owner` fails. It expects `/api/audiobook/pause` to call `automatic.stop()`, which now calls `automatic.pause_jobs` (a Mock attribute) instead.
  - Both are stale fixtures for intended changes, not product bugs. The fix is test-only and needs no re-review. The commit message says "Tests cover automatic restore and startup loading", but these two existing tests fail on it.

- **[Minor] R-m1 — New catalog writes on stop and start paths have no busy retry.**
  - **`_hold_queue`** (`audio_jobs.py:1238`) writes between `_stop.set()` and `on_working_hold`/`on_space_hold`. Before, nothing there could fail.
    - A busy or full catalog skips the callback, so automatic processing is not force-stopped.
    - When the write fails inside `_work_attempt`'s `finally` (`:1579`), the new error also replaces the original one.
    - The outer `_work` handler catches the error and calls `_hold_queue` again, so one 5 s busy spell is survived. Two in a row are not.
    - Disk full (ENOSPC) is exactly when a write can fail: the merge-cache sits next to the catalog.
  - **`_save_run_intent(True)`** adds a write to every queue start, under `jobs._lock`, with a 5 s timeout and no retry. A busy catalog now fails a Start with a raw sqlite error instead of starting.
  - **`start()`'s continue path** lost `_update`'s retry.
  - **Fix:** call the safety callback first and make the record best-effort (log on failure), or use `sqlite_retry.transaction`, as `_update` does in automatic processing.
- **[Minor] R-m2 — Two of the new guards are untested.** Two mutations pass all of `test_automatic_processing`, `test_startup_loading` and `test_backend_242`, apart from the R-M4 error, which fails in every tree:
  - `nocancel`: the user's Stop/Pause no longer cancels a Paused restart run. Probe P2 shows the current code is right, but nothing pins it.
  - `nojobattr`: automatic restore no longer refuses on a "user"/"interrupted" jobs pause.
  - Also untested: R-M1's legacy states, and that the restore reaches cleanups (R-M2).
- **[Minor] R-m3 — A restore that finds nothing to do leaves the intent at 1.** A Quit during the last book drains without clearing it: `_work` clears the intent only on an empty queue with no stop or drain. This is harmless until pending work appears that no press started. Clear the intent in `restore_work_after_restart` when there is nothing to resume.
- **[Minor] R-m4 — Doc/code drift.**
  - `Docs/BooksArranger_Brief.md:489`, "Server restart never starts an automatic run: Start resumes saved work.", is now false.
  - `audio_jobs.py:566` and `:1562` set the row reason "Interrupted book restarts on explicit resume". The book now restarts by itself when an intent is saved.
  - No CHANGELOG entry describes the new behaviour yet.
- **[Minor] R-m5 — Restore failures are invisible.**
  - `_restore_saved_work` prints to stderr only. The page shows "Paused." with the previous session's attribution.
  - Nothing starts, so this is safe. But Sergei can't tell a refused restore from a deliberate pause.
  - Also: the non-deferred `BrowserServer` path (`web_server.py:279`) never restores. No app uses that path today.
- **[Minor] R-m6 — After Resume, "Paused by you." stays on screen while cleanup owns the start.**
  - `_authorize_automatic_cleanup` now clears the jobs attribution only when `jobs._stop` is clear (`merge_service.py:960`).
  - After a user Pause, `_stop` stays set until the queue worker starts. So while a Resume is in its cleanup phase, the toolbar still reads "Paused by you." (`web/app.js:672`). For as long as that attribution stays, an automatic run paused by Quit will not restore.
  - This affects the display and restore eligibility only. Confirm the intent of the guard with Ender.

### 01a1901 — safety floor and a light read (ships in 0.28.13)

This commit ships in 0.28.13, so the verdict below has to cover it. Files: `desktop/folder-picker.js`, `desktop/preload.js`, `web/app.js`, two test files and the Brief. No Critical finding and no safety-floor violation:
- **No new IPC channel.** `preload.js` adds one string field (`remembered`) to two existing channels. The sender is still checked as the app window (`sender(event) !== 'app'`).
- **The main process only runs `stat` on that folder.** The path must be in drive or UNC form, with no control characters and at most 1000 characters, and the check is bounded at 1.5 s. No write, no delete, no shell.
- **A UNC path reaching the main process is not new:** the renderer already passed `defaultPath` straight to the Windows dialog before this commit.
- **Main-process errors cannot crash the shell.** Bad or missing values fall back to Windows' default folder. Anything that throws inside `ipcMain.handle` rejects that one invoke, and `picking` is reset in `finally`.
- **Renderer side (`web/app.js`).** Every localStorage read and write is in try/catch. Only folder strings of at most 1000 characters are stored, in the Electron profile. A failure there leaves the picker at its default.

Not done: a line-by-line review, and running its tests (`desktop-folder-picker.test.mjs`, `test_picker_memory_frontend.js`). The candidate's full-suite entry check runs those tests.

### Targeted test spot-check

How the tests were run:
- Private exports of 9522858 (`cur`) and 01a1901 (`base`), made with git archive with Docs excluded, under `WIP/Books Arranger/scratch/s9r/`.
- A private TEMP and BOOKS_QA_FIXTURE_ROOT under the same entry.
- A 590 s limit and one process per module.
- The working tree was never touched.

| Module | cur (9522858) | base (01a1901) | Same failing set |
|---|---|---|---|
| test_automatic_processing | OK, 72 | OK, 70 | n/a: the 2 new tests pass |
| test_startup_loading | 14, 1 F | 13, 1 F | yes. The failure is `ColdServePendingPageTests.test_real_page_failure_…` ("Safe removal of …web-instance.json could not be verified"), environmental. The new test passes |
| test_backend_242 | 29, 1 E | OK | **no (R-M4)** |
| test_merge_http | 24, 1 F | OK | **no (R-M4)** |
| test_attempt_working_lifecycle | 39, 4 F / 10 E | same | yes ("Exact file removal requires one admitted native catalog owner") |
| test_attention_actions | 22, 1 F | same | yes |
| test_working_lifecycle | 8, 2 F | same | yes |
| test_blocked_retry, test_desktop_update, test_sqlite_busy, test_start_over, test_working_precision | OK (21, 27, 16, 32, 18) | not run | n/a |

Mutations: each was applied by a script that requires its replacement to match exactly once. Each was run against test_automatic_processing, test_startup_loading and test_backend_242.

| Mutation | Change | Caught by |
|---|---|---|
| nopauseclr | user Pause no longer clears the intent | startup test, `origin='user'` |
| oldhold | `_hold_queue` back to a bare `_stop.set()` | startup test, `origin='hold'` |
| nocancel | user Stop/Pause no longer cancels a Paused restart run | **nothing** (R-m2) |
| nojobattr | automatic restore ignores a user/interrupted jobs pause | **nothing** (R-m2) |

### Probes (reviewer-only, private fixtures, removed after the run)

| Probe | Setup | Result |
|---|---|---|
| P1 | Automatic run stopped by Quit (origin closing), now Paused; then `close()` with no origin | `close()` returns normally. `restart_paused` stays 1, origin closing. The next launch restores. |
| P2 | Restored start pending on a scan, then the Stop endpoint (`automatic.stop()`) | Pending start ended; `restart_paused=0`, origin user. The next launch does not restore. |
| P3 | 0.28.12 state: run Paused, origin "closing", `restart_paused=0` | First launch: restore True, worker started (R-M1). |
| P4 | 0.28.12 state: run Paused after a crash, `restart_paused=1`, origin "interrupted" | First launch: restore True, worker started (R-M1). |
| P5 | Real MergeService and BrowserServer: intent 1, one pending job, one paused cleanup (cleanup resume stubbed) | The startup restore called `CleanupJobs.resume` with the jobs handoff, with no press (R-M2). |
| P6 / P6b | Leftover intent 1, plus a saved "user" jobs pause (what 0.28.12 records) | The restore started the cleanup (P6) and, without a backlog, the queue worker (P6b) (R-M3). |

### Status of this section's findings

All of R-M1 to R-M4 and R-m1 to R-m6 are **open on `feature/restart-intent`**, for the next version. None of them is in 0.28.13. Before that branch merges:
1. Update the two stale tests (R-M4).
2. Add the one-line guard and its test (R-M3).
3. Get Sergei's answers on R-M1 (should the first launch pick up a run 0.28.12 left paused?) and R-M2 (should a restart restart cleanups, including NAS removal?).
4. Rewrite the Brief rule at `:489` (R-m4).
5. Ask Senua to re-review the branch's delta.

### Verdict (v0.28.13)

**0.28.13 is v0.28.12 (bce9e94) .. 55b98aa.** Every commit in it was checked as follows:

| Commit | What it is | How it was checked |
|---|---|---|
| bce9e94 | docs only | no code |
| ad28ff9 | NAS delete, retry of held NAS cleanups, Restore over SMB | first review, re-review 1 and re-review 2 above. The commit matches the reviewed tree: test_nas_source_removal.py has 745 lines and 35 tests, and native_io.py, source_cleanup.py and runtime_file_disposition.py are unchanged since |
| 01a1901 | picker remembers its last folder | safety floor and a light read (above) |
| 9522858 + 0125c57 | restart-intent work, then its revert | revert verified: `git diff 01a1901 0125c57 -- . ':!Docs'` is empty. 0125c57 touches exactly 9522858's 7 files, +20 / -259, the inverse of 9522858's +259 / -20 |
| 55b98aa | version bump | only the `version` fields of package.json and package-lock.json, 0.28.12 to 0.28.13 |

Totals for 0.28.13:
- **Critical:** 0. The safety floor is intact.
- **Major:** 0 open. The NAS review's M1 and M2 are closed. R-M1 to R-M4 do not ship.
- **Minor:** 7 open, all from the NAS review: m2, m4, m5 (wider), m6 (partly), m8, m10 (partly) and m11. R-m1 to R-m6 do not ship.

**Verdict:** RELEASE CLEAR

Advisory for 0.28.13: re-review 2's advisory stands as written. With the restart work out, only Sergei's own Start or Resume runs the re-opened NAS backlog. So "before the first post-update Start, run one Restore on a private Z: fixture" still works, and writing on Z: needs his go-ahead.
