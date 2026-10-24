# Books Arranger: delete-path audit against Sergei's deletion rule (2026-10-24)

Senua, red-team, read-only. Code: `main` at `b467308` (v0.21.2), read from a detached worktree. Nothing was written to Z: or to the live `data/`.

**The rule** (`Team/Docs/BooksArranger_Rulings_2026-10-24.md`, items 2 and 1a): a book's source may be removed only after its result is verified and present in `Z:\Audiobooks Sorted`. A book that is done goes there. A book that isn't done stays unchanged.

**Answer: does the app enforce the rule today? No.**
- The copy flow keeps the rule in the installed setup.
- The in-place M4B path changes books that aren't done yet (C1).
- "Present in Sorted" depends on configuration. Nothing checks it at the moment of deletion (C2).

## Summary

| | Count |
| --- | --- |
| Paths audited | **20**: 7 act on files under a source root, 4 on published outputs, and 9 on the app's own copies (recovery, staging, repair) |
| Excluded after checking | 6 bookkeeping operations outside every library: the settings file, the web-instance record, the OpenLibrary index, Start-menu shortcuts, tool logs, and GitHub releases |
| Critical | 2 |
| Major | 1 |
| Minor | 5 |

| ID | Severity | Gap | One-line fix |
| --- | --- | --- | --- |
| C1 | Critical (conflicts with ruling 1a; Sergei decides) | The in-place M4B path edits the original at its source path before the result is in Sorted | Turn the in-place path off (`inplace_m4b.offered()` returns False), unless Sergei re-confirms the 10-22 exemption |
| C2 | Critical (depends on configuration) | Source removal accepts any verified output under the job's frozen output root. With no output root configured, that root is the source root itself | Before enrolling and before each disposal, require the effective output path to be inside a configured output root that is not a source. Refuse to start conversion when no output root is set |
| M1 | Major | The source-deletion test suites are not in the release gate, and one has already gone stale | Add `test_source_cleanup`, `test_source_folders`, `test_safety_boundaries` and `test_cleanup_scope` (after fixing its stale assertion) to `scripts/check-desktop.mjs` |
| m1 | Minor | The output is not re-checked before each original is removed. Only the held handle protects it | Before each `original.dispose()`, refresh the output's handle facts and confirm `final` still exists |
| m2 | Minor | The list of empty folders to remove reaches the source root's direct children, such as `Z:\Audiobooks\Unsorted` | Never remove a folder that is a direct child of a source root |
| m3 | Minor | The copy-flow cleanup removes a done source's download marker and never puts it back if the cleanup stops | Remove the marker just before the delete, or restore it from its receipt when the cleanup holds |
| m4 | Minor | Series backfill deletes its temp file by pathname, and it places files relative to the source root instead of the output root | Use the effective output root, and delete the temp through a verified handle |
| m5 | Minor | Producer-recovery disposal trusts database flags for the child output | Verify the child's output (`protected_output`) before disposing |

## Method

- **Finding the paths.** Grep over all non-test Python for callers of the `native_io` primitives: `.dispose(`, `dispose_empty(`, `rename_no_replace(`, `publish_no_replace(`, `.write_at(`, `.truncate(`, `restore_metadata(`, and `VerifiedFile(..., delete=True / writable=True)`. A second grep caught every pathname operation: `unlink`, `rmdir`, `rmtree`, `os.remove`, `os.rename`, `os.replace`, `shutil.move`. A third covered the `fs` deletes in `desktop/`, `web/` and `scripts/`. Each hit was read in place and traced back to its triggers. FFmpeg command lines were checked for `-y` and for output targets: every output goes to staging, a pipe or `null`, and the commands use `-n`.
- **Live catalog.** Read-only, using `mode=ro&immutable=1`, which reads only the main database file and never touches the `-wal` or `-shm` files. The counts are therefore as of the last checkpoint.
- **Live configuration.** `%APPDATA%\Books Arranger\audiobook-sources.json` = sources `Z:\Audiobooks` and `Z:\OLD_Audiobooks`, output `Z:\Audiobooks Sorted`. The Start-menu shortcut points to the installed `Books Arranger.exe`.
- **Tests.** 8 delete-path test modules were run in the worktree; results are under Tests below.

## Source-root paths (P1–P7)

### P1. Original removal, copy flow: `CleanupJobs.run`, `source_cleanup.py:320-409` (disposal at L403)

**Triggers**
- Automatically, right after a book completes: `MergeService._after_completed_work` (`merge_service.py:1030`) calls `enroll_cleanup`, then `run_with_retry`.
- Start or Resume, for cleanups that are waiting or paused (`_resume_guarded`, L698).
- The held-cleanup pass in the retention thread (`_finish_held_cleanups`).
- A recovery child (`_finish_recovery_child`, L284).
- `/api/audiobook/cleanup`. This is limited to 2 pinned jobs, and both are already completed.
- At startup, completed books are only enrolled, not run (`_enroll_completed_without_start`, L348).

**(a) What it removes.** Only the manifest's selected audio files: under the manifest root, with an audio extension, not under Podcasts, and no duplicates (`enroll`, L186-193). Covers, info files and folders are never removed. Each original first gets a full recovery copy in `data/source-recovery`, and every copy is verified before the first delete (L388).

**(b) Is the output checked first?**
- Yes, partly. At the start of the run the output gets a full SHA-256, a size check, a parent-identity check and, when recorded, a native file-identity check. A handle that denies delete and write is then held until the run ends (L334-337).
- Before each delete, a catalog guard runs inside a transaction: review, revision and publication generation (L394-401).
- The output is not re-checked on disk before each delete (m1).
- Nothing checks that the output is in Sorted. The run accepts any frozen output root (L322-329); see C2.

**(c) Multi-book folders.**
- The path is safe. Book groups partition the files (`groups.build`, `groups.py:230-234`), so each file belongs to exactly one book.
- The guard requires the book's current revision and included set to equal its manifest (`_cleanup_binding`, `merge_service.py:735-750`).
- Sibling books' audio, covers and info files are never in scope.
- Live evidence: in Iron Inferno's anthology folder, the app removed only the nine anthology tracks. The folder stayed `retained_nonempty`, and Iron's MP3 and `Cover.jpg` were left alone (diagnosis, section A).

**(d) Is a book that isn't done left unchanged?**
- Yes for this path. The copy flow only reads sources: `copy_owned` opens them `rb`, and the snapshots are held deny-write.
- Once the book is done, the run removes the download-marker stream (`Zone.Identifier`) from each original before backing it up (L371); see m3.

**(e) Recovery.** `restore` (L436-472) puts the originals back from their recovery copies and never overwrites a file at the target. Recovery copies are purged as soon as the output verifies (`HOURS=0`, `recovery_retention.py:21`), so in practice a restore is almost never possible.

**(f) Failure midway.**
- A crash after the removal intent is recorded but before the delete: the next run refuses with "Interrupted removal has unknown outcome" (L358-359), and the copies are kept.
- The NAS goes offline: a `BoundaryError` puts the cleanup in Needs attention, and the remaining originals and copies are kept.
- The output is deleted after verification: the held handle blocks deletes made over SMB. A delete made on the NAS itself would go unnoticed. The remaining originals would still be removed, but their copies survive, because the recovery purge re-verifies the output and keeps the copies when it fails.

### P2. Download-marker removal: `zone_identifier.remove_marker`, `zone_identifier.py:62-110`

**Callers:** `source_cleanup.py:371` (a book that is done) and `inplace_m4b.py:438` (a book that is not done yet, part of C1).

- **(a)** Removes one named stream, `:Zone.Identifier`. Any other stream refuses the operation.
- **(b)** In the copy flow, it runs after the output is verified. In the in-place path, it runs before the result is in Sorted.
- **(c)** Only the book's own files.
- **(d)** It alters a book that isn't done in the in-place path.
- **(e)** The in-place undo puts the marker back (`restore_marker`). The copy flow never restores it (m3).
- **(f)** The marker's bytes are journaled before it is removed.

### P3. In-place M4B edit: `inplace_m4b._edit`, `inplace_m4b.py:355-475` (writes at L414 and L416)

**Trigger.** An AudioJobs attempt for a book that `offered()` accepts (L187-202): automatic profile, one `.m4b`, AAC that can be stream-copied, cleanup enabled, and no repair, replacement or retained checkpoint. 18 books in the live catalog went this way.

**(a)** Nothing is removed. The original is changed where it sits:
- A new `moov` box (the metadata and cover) is appended to the file.
- The old `moov` box's 4-byte type is changed to `free`.
- The download marker is removed (L438).
- The write time and attributes are set back.

**(b)** Not applicable: this runs before any output exists. The edited file is the future output.

**(c)** Only the single file of a single-file book.

**(d) No: this breaks ruling 1a.**
- A book that isn't done has its file changed at its source path before the result is in Sorted.
- The window runs from the first write (L414) through the probe, chapter, copied-audio and full byte-proof checks and the cover check, to the rename (`merge_service.py:2767`).
- The audio bytes (`mdat`) are never written. The byte proof checks that `[0, original size)`, with the 4 type bytes reverted, hashes to the reviewed SHA-256.

**(e)**
- The edit is journaled in `inplace_edits` before the first byte (L407).
- Any failure before the rename is undone (L461-470).
- Recovery runs at startup (`audio_jobs.py:392`) and before any attempt on that source (`clear`, L556).

**(f)**
- After a crash, the startup undo restores the original.
- If the NAS or share drops, the undo cannot run. The row becomes `unresolved` (or `offline` at startup), and the source stays edited until a start that can see the library (`test_startup_leaves_an_edit_open_only_while_its_library_root_cannot_be_seen`).
- If the undo cannot prove the file is still the edited original, it writes nothing, and the source stays edited for good (`test_unprovable_original_stays_journaled_and_blocks_new_attempts`).
- If the edited file is renamed or moved by hand while it is in that state, it is reported as "missing" and is never restored.

### P4. In-place move: `MergeService._publish_in_place`, `merge_service.py:2748-2780`

This calls `native_io.rename_no_replace` (L164-251). The retirement is recorded afterwards in `source_cleanup._retire_moved` (L410-429).

**(a)** Moves the edited original into its destination. There is no copy and no delete; the source path disappears.

**(b)**
- Before the rename: a full byte proof under a deny-writers handle, a same-volume check, a check that the destination does not exist, and the catalog revision guard.
- The destination must sit under the configured output root, which the attempt admission enforces (`merge_service.py:326-345`, `destination_admission.py:16-25`). When no output root is configured, the destination is under the source root instead (C2).
- After the rename, `CleanupJobs.run` hashes the output in full again before it records the retirement.

**(c)** Only the single file.

**(d)** The move is the publication itself, done as one atomic rename.

**(e)** A rename whose final check fails is journaled as `publishing`, and recovery proves the move by a full hash (`_prove_move`, L486-503). A name collision undoes the edit.

**(f)** An in-place book never has a recovery copy. If its Sorted file is later deleted, the book is gone. This is the same exposure the copy flow has once `HOURS=0` purges its copies.

### P5. In-place undo and recovery: `inplace_m4b._undo` (L298-323), `reconcile` (L505-531), `recover_all` (L533-540), `clear` (L556-573)

- **(a)** Writes to the source: cuts it back to its original length, puts back the `moov` type, restores the download marker, and restores the write time and attributes.
- **(c)** Only the journaled path.
- **(d)** Restores the original, and only after proving that the file is the edited original. Otherwise it writes nothing.
- **(f)** While the library root is offline, the journal row is left open. An `unresolved` row blocks attempts on that one source; other books carry on.

### P6. Restore originals: `CleanupJobs.restore`, `source_cleanup.py:436-472` (`/api/audiobook/restore`)

- Creates files at the source paths from verified recovery copies, using a rename that never replaces an existing file. A file already at the target is kept.
- It deletes nothing. It is listed here only because it writes into source roots.
- It stops working once the copies are purged, which happens immediately.

### P7. Empty source-folder removal: `StorageCleanup.run_folders` / `_remove_folder`, `storage_cleanup.py:739-802`

**Trigger:** `_prune_completed` (`merge_service.py:1001`), after the source cleanup and the temporary-file cleanup have both completed.

- **(a)** Removes only empty folders that held the removed sources, walking up to (but not including) the source root (`storage_cleanup.py:662-674`). It never removes contents. It refuses on any filesystem that supports named streams.
- **(b)** Requires a full-hash check of the output, the recorded source retirement, and a completed temporary-file cleanup (`_folder_obligations`, L637-660).
- **(c)** Any folder that still holds a file is kept (`retained_nonempty`).
- **Live result:** 731 folders kept because they were not empty, 119 kept because the NAS reports NTFS with named streams, 0 removed. On Z: this path never removes anything. See also m2.

## Output and app-copy paths (O1–O4, R1–R9)

None of these touches a source root's audio, so (c) and (d) do not apply to them.

| ID | Path | Trigger | (a) What it removes | (b) What is verified before the delete |
| --- | --- | --- | --- | --- |
| O1 | `MigrationWorker._remove_or_retain`, `output_migration.py:322-372` (disposal L358) | Operator command line: `migration_operation.py` (the 0.20.1 move) | An old output, after its copy in Sorted is verified | Full hash, media proof and directory flush of the Sorted copy; if the flush can't be proven, the old output is kept. Refuses any source file (L396) |
| O2 | `RenameWorker._rename` / `_duplicates`, `output_rename.py:99-190` (disposal L171) | Operator command line: `migration_operation.py` (the 0.20.2 move) | An old output, moved by rename; a verified duplicate deleted | Full hash of both files for a duplicate. Refuses any source file (L214) |
| O3 | `SeriesBackfill._resume_protected`, `series_backfill.py:525-575` (disposal L563; pathname unlink at L657 and L665) | The retention thread's series backfill, automatic when the app is idle | A published output, after a retagged copy replaces it | Full hash and identity of the new file. See m4 |
| O4 | `ReplacementRetirement.run`, `replacement_retirement.py:136-211` (disposal L200) | Post-processing of the one pinned Eye of God replacement | Exactly 3 former outputs | Full hash of the replacement. Its sources must stay (`replacement_jobs.py:71`) |
| R1 | `RecoveryRetention.purge`, `recovery_retention.py:136-185` (rmdir L179) | Right after source cleanup (`_purge_recovery_now`, `merge_service.py:901`); the retention sweep every 60 s (L857); the manual Delete recovery copies (L843) | Recovery copies of removed originals | Full hash of the output under a handle held through the delete (`protected_output`, `storage_cleanup.py:137-157`). A missing or changed output keeps the copies. Keep files skips the automatic purge |
| R2 | `StorageCleanup.run`, `storage_cleanup.py:571-614` | `_prune_completed` | Staging snapshots and working files | Full hash of the output, and the originals either retired with a record or verified unchanged (`_source_safety`, L286-318) |
| R3 | `StorageCleanup.working_files`, L509-569 (including the command-line `cleanup_published_working.py`, 8 pinned jobs) | Post-processing and a one-off command | Disposable working names only, never snapshots | Full hash of the output |
| R4 | `StorageCleanup.discard_repair_copy`, L804-844 | An explicit one-off caller | The checked copy in `data/chapter-repairs` | Full hash of the corrected published file |
| R5 | `WorkingLifecycle.retire`, `working_lifecycle.py:321-440` | The Retry/Repair pre-clear, Clear working files, the reconcile sweep | Files of an unpublished attempt in staging | Snapshots go only while the originals are verified present |
| R6 | `WorkingLifecycle._discharge_published`, L520-612 | After publication or cleanup | A published attempt's source snapshots | `protected_output` and `snapshot_source_safety` |
| R7 | `ProducerRecovery.dispose`, `producer_recovery.py:289-337` | After a recovery child completes | The interrupted attempt's fenced files | Database flags only (m5). The original is still present at that point |
| R8 | `ReplacementRetirement.purge_recoveries`, L213-241 | The retention sweep | Recovery copies of the replacement's former outputs | Full hash of the replacement |
| R9 | Automatic-approval diagnostics, `merge_service.py:2090-2097` | The end of each automatic approval | Pinned diagnostic files in `data/merge-cache` | Hash pin |

## Findings

### C1. Critical: the in-place M4B path changes a book that isn't done (P3, P2, P5)

**What happens**
- `inplace_m4b._edit` writes into the original at its source path, usually in a seeded torrent folder under `Unsorted`. It appends a `moov` box (L414) and changes the old box type to `free` (L416).
- It then removes the download marker (L438) and resets the write time.
- All of this happens before the rename into Sorted (`merge_service.py:2767`).
- If the undo cannot run (the NAS drops, the share reconnects, or the process is killed mid-undo) or cannot prove the file, the source stays edited until a later start settles it, or for good. Two passing tests show exactly this: `test_unprovable_original_stays_journaled_and_blocks_new_attempts` and `test_startup_leaves_an_edit_open_only_while_its_library_root_cannot_be_seen`.

**What is not at risk.** The audio frames are never written, and the byte proof guarantees that the original extent is intact.

**Why it is Critical.** This was Sergei's explicit trade-off on 2026-10-22 (brief, "In-place single-M4B edit"). Ruling 1a of 2026-10-24 says a book that isn't done stays unchanged, so the two now conflict.

**Disposition (Sergei, 2026-10-24, ruling 2b, recorded by Ender).** Option (b): the exemption is re-confirmed. The in-place M4B fast path stays: it may rewrite tags inside an original that is not done yet and then move it into Sorted, because the audio is never changed. Future reviews should not raise this as a finding again. The residual risk stated in (b) remains: an undo that cannot run or cannot prove the file leaves the original edited (tags only). 0.21.3 adds one guard from C2 to this path: the in-place edit is offered, and its rename made, only when the destination is inside the configured output folder, outside every source.

**Fix.** This is Sergei's call:
- (a) Turn the path off: `offered()` returns False, and the copy flow already handles these books with the same checks, only slower and using staging space; or
- (b) Re-confirm the exemption in writing. The finding then drops to Major, because the residual risk remains: an undo that cannot run leaves the original edited.

### C2. Critical (depends on configuration): nothing checks "present in Sorted" (P1, P4, R1)

**What happens**
- `CleanupJobs.run` accepts any verified output under the job's own frozen output root (`source_cleanup.py:322-329`).
- That root becomes the source root whenever the backend runs without an output root:
  - `_output_root()` falls back to the source root (`review_backend.py:151-154`).
  - The admission check then targets `output_root or source` (`destination_admission.py:22`).
- With no output root, a newly approved book converts into `Z:\Audiobooks\<Author>\…`, and its sources are then removed while its result is not in Sorted.
- The 146 old Needs-attention jobs that are still frozen to `Z:\Audiobooks` would be admitted on Retry and handled the same way. In the normal setup the admission check holds them.

**When it can happen**
1. `audiobook-sources.json` is missing, for example on another PC or after a profile reset. `desktop/main.js:93-103` then starts the engine silently with no output root.
2. The repo launchers are used: `launch-web.pyw`, `launch.cmd`, `launch-web.cmd` or `python web_server.py`. They start `web_server.main([])` with the default roots and no output root (`scanner.py:12`, `app_launcher.py:19,220`), and their default database, `<repo>/data/inventory.sqlite3`, is the live catalog on this machine.
3. Any `--roots-json` launch.

**Why it is Critical.** By the brief's definition: a done book's source can be removed while its output is not in Sorted.

**Reachability today.** Not reachable in the current installed configuration.

**Evidence.** The passing test `test_source_cleanup::test_actual_removal_and_exact_restore` removes both originals while the verified output sits inside the source library itself.

**Fix.** At enrollment and before each disposal, require the effective output path to be inside the configured output root, and require that root to be set and not a source. Refuse to start conversion or cleanup when no output root is configured.

### M1. Major: the source-deletion suites are outside the release gate

- `scripts/check-desktop.mjs` runs `test_storage_cleanup`, `test_backup_rule`, `test_recovery_retention`, `test_inplace_m4b` and `test_zone_identifier`.
- It does not run:
  - `test_source_cleanup.py` (13 tests, the original-removal suite)
  - `test_source_folders.py` (24 tests)
  - `test_safety_boundaries.py` (6 tests)
  - `test_cleanup_scope.py` (5 tests)
- `test_cleanup_scope` already fails: `start_historical_cleanup` now passes `admission_check` and `admission_token`, and the test still expects the old call. Nothing noticed, because nothing runs it.
- **Fix.** Fix that assertion and add all four modules to the gate.

### Minor findings

- **m1.** `source_cleanup.py:391-408` does not re-check the output before each original's delete; it relies on the held handle. A delete made on the NAS itself (not over SMB) would not stop the remaining deletes. The copies survive, because the purge re-verifies the output.
- **m2.** `storage_cleanup.py:662-674` lists every ancestor folder below the source root, so an emptied `Z:\Audiobooks\Unsorted` or author folder qualifies for removal. It is never removed on Z: today.
- **m3.** `source_cleanup.py:363-371` removes a done source's download marker before the backup. If the cleanup then stops, the marker is not put back; `restore_marker` is used only by the in-place undo. This affects a done book and a metadata stream only.
- **m4.** Series backfill has the only pathname deletes inside library folders (`series_backfill.py:657,665`). It also bases naming and folder checks on `manifest['root']`, the source root (L376, L592). As a result:
  - Every output in Sorted is held as "name does not follow", so the feature is silently off.
  - A legacy output still inside a source root would get its temp file, rename and old-file delete inside the source tree.
- **m5.** `producer_recovery.py:303-307` decides on database flags alone (child completed, validation passed). This is safe today only because the original is still present until `CleanupJobs.run` re-verifies.

## Not gaps, but worth knowing

- **No safety net after cleanup.** Recovery copies go as soon as the output verifies (Sergei, 2026-10-18; `HOURS=0`), and in-place books never have one. After cleanup, the file in Sorted is the book's only copy. The startup check can report it missing but cannot bring it back.
- **Half-emptied folders.** Partial cleanup of a multi-book folder leaves the unfinished book in a half-emptied folder. That was Iron Inferno's shape on 10-23: nine tracks were gone, and its MP3 and `Cover.jpg` remained. The app kept the rule; the folder just looked finished. If Sergei wants, Judy could name such books in the attention list.
- **Two computers sharing Z:.** Each machine has its own catalog. Nothing keeps two of them from working on the same library. No delete-rule breach was found from this, apart from C2 if the second machine has no output root.

## Live catalog snapshot (read-only)

| Item | Count |
| --- | --- |
| Source cleanups | 504, all completed |
| Cleanups whose recorded output is outside Sorted | 431, all with a completed relocation into Sorted |
| Cleanups still pending | 0 |
| Recovery sets | 504, all deleted |
| In-place edits | 18 published, 0 open |
| Jobs completed | 506 |
| Jobs in Needs attention | 148 (146 frozen to output root `Z:\Audiobooks`, 2 to Sorted) |

No live record breaks the rule today. The two Critical findings are about what the code allows.

## Tests run (in the worktree, `python -B -m unittest discover -p <module>`)

| Module | Result |
| --- | --- |
| test_source_cleanup | 13 OK |
| test_cleanup_scope | 5 run, 1 failure (M1, stale expected call) |
| test_backup_rule | 12 OK |
| test_recovery_retention | 20 OK |
| test_safety_boundaries | 6 OK |
| test_source_folders | 24 OK |
| test_storage_cleanup | 18 OK |
| test_inplace_m4b | 40 OK |

The full gate was not run, because this is a read-only audit.

## Excluded after checking

These operations stay outside every library:
- `desktop_settings.py:25` (an unfinished settings file)
- `web_server.py:828` (the web-instance record)
- `desktop_backend.py:334` (a stale owner record, renamed aside within `data/`)
- `openlibrary_index.py:133,352` and `install_app_entries.py:119` (no-replace publishing, with no delete)
- `series_backfill.py:646-647` (tool logs in `data/`)
- `scripts/cleanup-releases.js` (GitHub releases)

The QA scripts under `scripts/qa-native/` refuse Z: roots by test.
