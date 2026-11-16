# Books Arranger 0.28.13 QA

QA: Futaba. Date: 2026-11-16. Source commit: `fac11dbb0f64bb0c1d4cb6971c94fa6c79713135` (main, clean tree). Build id: `edf9a2b8-6bca-41bc-b353-c2c738006762`.

**Verdict:** GO

GO covers the tested build under Sergei's entry-check waiver (recorded below). No Blocker and no Major finding. One Minor finding (NAS recycle bin) needs Sergei's awareness and one cleanup approval; it does not block the release. What was and was not verified is listed in sections 6 and 7.

## 1. Build identity (hash verification)

| Check | Expected | Found | Result |
|---|---|---|---|
| Installer SHA-256 (`Books-Arranger-Setup-0.28.13.exe`, 209,025,500 bytes) | `685956687fbd7998f4da0248edcbd103c45332fadb6bc2e5b27a939f09a1de4c` | same, recomputed at the start and again after all testing | match |
| Manifest SHA-256 (`dist/release-artifacts.json`) | `3580c221437edbddd3f686ac68f39f307957a741b3b2a0e8cb42eb2157e952d0` | same, recomputed at start and end | match |
| Manifest `version` / `source_head` / `build_id` | 0.28.13 / fac11dbb... / edf9a2b8-... | same | match |
| Repo HEAD, tree | fac11db, clean | fac11db, `git status` empty in the tool repo before this report was written | match |
| Installer payload vs manifest | 401 files | extracted `app-64.7z` from the installer with 7-Zip (no install run): 401 files, every SHA-256 equals `payload.files`, 0 extra files | 401/401 |
| Installer payload vs `win-unpacked` | identical | all 401 files identical | match |
| Payload after all test runs | unchanged | re-hashed after testing: 401/401, 0 extra (nothing wrote into the payload) | match |
| Changed backend modules vs commit | equal | `native_io.py`, `source_cleanup.py`, `merge_service.py`, `web_server.py`, `web/app.js` equal the committed fac11db source (line endings normalised); `VERSION` = 0.28.13 | match |
| Shell files inside `app.asar` | equal | `desktop/folder-picker.js` and `desktop/preload.js` equal the commit (line endings normalised) | match |
| Entry log (`WIP/Books Arranger/scratch/qa-fac11db-entry/ender-entry.log`) | the log the builder named | SHA-256 `e4550a3e49c1796901b542b0fd7dc4a28e321275d1b6650294fbee0e505c9686`; I did not re-run the entry check | read only |

## 2. Entry log and waiver

Receipt line in the log, verbatim:

> Entry-check receipt v2: books-arranger v0.28.13 @ fac11dbb0f64bb0c1d4cb6971c94fa6c79713135 (dirty: N) [source:39c005be837502b6e951aaab7c3221773babd1c25e5fe8cceb0128784fab0c0f; harness:761babc96ba37cb4578b47d95cedf290ebbee95d7904aa43b602311df6fa047f; runtime:9485d78cb7063dd633feade58116c9ca8c42e3dcd8f19ece1a525f2dccc803c1; checker:4bae2cde4e4cdd2f22fb3060571730ec32fec1dd5403ea070086973b18b695e4] — pre-qa n/a, post-build n/a, check-electron n/a, check fail (owned check), test:smoke n/a; personal-folders clean (5 subfolder notes)

The log ends with "Entry checks failed; QA remains blocked" (the gate threw "Python batch failed or exceeded output cap" after every worker had finished and printed).

I parsed the whole log (13 Python workers, 2,644 test cases reported, 1 skipped; Node 260 tests, 260 pass, 0 fail, 0 skipped, 0 cancelled; the page-script phases passed, including "Picker memory renderer passed" and "Manual Conversion renderer passed"). It shows exactly five failing tests and no others:

| # | Test | Kind | Worker | Waiver reason |
|---|---|---|---|---|
| 1 | `test_desktop_host.StartupBoundaryIntegrationTests.test_actual_stale_callback_runs_before_inventory_mutation_and_preserves_unknown_record` | FAIL | 0 | failed at v0.28.12, test setup |
| 2 | `test_storage_relocation_integration.RelocatedWorkingIntegrationTests.test_real_approved_conversion_runs_after_copy_and_restart_keeps_verified_output` | ERROR | 2 | failed at v0.28.12, test setup |
| 3 | `test_backup_rule.HeldCleanupTests.test_replacement_recoveries_of_a_kept_book_stay` | ERROR | 2 | failed at v0.28.12, test setup |
| 4 | `test_source_cleanup.OutputIdentityRetryTests.test_legacy_intent_retry_reopens_and_verifies_every_copy_before_first_delete` | FAIL | 3 | labelled flake |
| 5 | `test_storage_lifecycle_controls.ControlTests.test_terminal_selection_removes_data_package_controls_and_registry_last` | ERROR | 6 | parallel-run flake (passes 5/5 alone) |

Matches the waiver exactly: five, no more. Waiver text, recorded verbatim from the QA brief:

> WAIVER (Sergei, 2026-11-16, in chat, option "a"): the entry check failed on 5 tests, and none come from this release's changes. Three already failed at v0.28.12, because they're test-setup issues: test_desktop_host stale_callback, test_storage_relocation_integration real_approved_conversion, and test_backup_rule replacement_recoveries. One is a parallel-run flake (test_storage_lifecycle_controls terminal_selection; passes 5/5 alone). The last is the labelled flake test_source_cleanup legacy_intent_retry. Sergei waived these for this candidate.

## 3. Method and limits

- Nothing was installed. Installing would have written the app's uninstall registration over Sergei's installed Books Arranger, so I extracted the installer payload to a scratch folder (section 1) and ran the shipped Python, FFmpeg and backend from it. No QA install exists, so there was nothing to uninstall.
- Every backend run used its own data folder and port 5231 (Sergei's app owns 5210), driven only through the local HTTP API (the same routes the page calls). No window, no focus, no mouse.
- Library roots, the sorted output folder and the catalog were set through the backend's own options (`--roots-json`, `--audiobook-output-root`, `--database`). Z: use was limited to `Z:\_BooksArranger_QA_20261116\`, with small generated MP3 books (3 tracks, 3 s, 24 KB each). Z: is a real SMB share (`\\NAS3247BD\Public`).
- To get genuine 0.28.x NAS holds, I ran the v0.28.12 backend (exported from git tag v0.28.12, run on the packaged Python) against the same catalog, then opened that catalog with 0.28.13: the real upgrade path.
- Two failure cases cannot be produced by hand, so they used a thin wrapper around the shipped backend that changes nothing unless a flag file exists. It replaces only two functions: the NAS pre-delete check (raises "Original bytes differ", as a late NAS writer would cause) and Restore's publish step (raises before the rename). Everything else in the cleanup and Restore paths is the shipped code. Steps 14, 15 and 17 used it; all others ran unpatched.
- Native Browse and Save As dialogs were not opened (no mouse or focus checks while Sergei is at the machine). The picker was verified through the shipped module's unit seams and a probe with a fake dialog, see section 4B.

## 4. Steps and results

### A. Identity and gate

1. Recomputed installer and manifest SHA-256 and compared source head: match (section 1).
2. Extracted the installer payload, verified 401/401 file hashes against the manifest, identical to `win-unpacked`, no extra files: pass.
3. Compared the changed backend modules and the two shell files with commit fac11db: equal.
4. Parsed the entry log: exactly five failures, all on the waiver list (section 2): pass.

### B. Pickers (change 1), through the shipped code

5. Ran the repo test `tests/desktop-folder-picker.test.mjs` against the shipped `folder-picker.js` taken from `app.asar`: 21 of 21 pass.
6. Ran `tests/test_picker_memory_frontend.js` against the shipped `web/app.js`: "Picker memory renderer passed".
7. Wrote my own probe against the shipped module with a fake dialog and the real filesystem, including the real SMB share. 10 of 10 pass:
   - Folder mode, remembered `...\QA Author\QA Book Three`: dialog opens at `...\QA Author` (one level up).
   - Files mode, same remembered folder: opens in that folder.
   - Save As, remembered export folder: opens there with the suggested name `QA Book Three.m4b`.
   - Folder gone: Folder mode opens at the nearest existing ancestor, Files mode at the Windows default, Save As keeps just the suggested name. No error in any case.
   - Drive not mounted (W:): Windows default in about 1 ms, no wait. A request with no `remembered` (Choose folder on a book row) is unchanged.
8. "Remember across restart": verified at renderer level only (the page stores the places under localStorage key `books-picker-places-v1`, read back after a simulated restart in the repo test). Real Electron profile persistence was not exercised (section 7).

### C. NAS cleanup (change 2)

9. Ran the v0.28.12 backend on the share. Book Two converted, then its cleanup held: "The audiobook is verified, but safe removal of the remaining originals could not be verified. The remaining originals were kept." Cause: "Unsupported disposition provider: remote/unverifiable native volume". Originals untouched (SHA-256 identical); member 01 was left in `removal_intended` with its file still present (the 0.28.x leftover).
10. Stopped it and started 0.28.13 on the same catalog. At startup the cleanup moved to `paused` and the hold history gained "remote provider hold; retried with the NAS removal method". The app showed "Source cleanup paused: 0 of 3 removed". Nothing was removed at startup (all files still on the share). The `removal_method` column was added by the migration.
11. Approved a second book (Book One) and pressed Start: Book Two's cleanup finished, Book One converted and cleaned. All six originals were deleted from Z:. The two M4B outputs are valid (ffprobe: 9.000 s, 3 chapters, title and artist tags correct). The database records `removal_method = nas_legacy` for all six members, including the revived `removal_intended` one. Both cleanups ended "Originals removed; recovery copies deleted".
12. Local-volume regression: a book on I: converted and cleaned on 0.28.13. `removal_method = hardened_local`, output valid, NAS method not used.
13. Revival negative control: after step 15 the backend was restarted with two other-reason holds present. Both stayed `needs_attention`, nothing was revived or run (database state identical before and after).
14. Failed final check (injected, Book Three): the NAS check failed on track 02. Track 01 was removed (`nas_legacy`); tracks 02 and 03 stayed on the share with SHA-256 identical to the generated files. Cleanup held with the reason "Original bytes differ from reviewed sources (QA injected)". Member 02 went back to `backup_verified`, not stuck in `removal_intended` (the M1 fix). `restore_available` was true.
15. Same with the check failing on track 03 (Book Four): tracks 01 and 02 removed, 03 kept, cleanup held.

### D. Restore over SMB (change 3)

16. Reproduction note: Restore is only possible while recovery copies exist. After a fully successful cleanup they are purged at once (recovery retention `HOURS=0`, unchanged since 0.28.12), so Restore applies to paused, held or partial cleanups. That is why the flows below restore from held states.
17. Failed Restore (injected before the rename, Book Three): the temporary `.books-restore-*.partial` existed at the moment of failure. Afterwards the share folder holds no `.partial` and member 01 is unchanged (`removed`). The API answered 500 with the generic text "Local control failed; inspect saved job and source cleanup status" (see finding 3).
18. Restore again, unpatched, real SMB rename (Book Three): 200, track 01 back, `.partial` absent, member `restored`. SHA-256 of all three originals equals the generated files.
19. After a backend restart, Restore on Book Four (two removed originals): both back, all three files SHA-256 identical to before conversion.
20. Restore on a revived 0.28.x hold before pressing Start (Book Five: held by 0.28.12 with member 01 in `removal_intended`, file present; revived to `paused` by 0.28.13): 200 with "Originals restored; recovery copies retained." No "Restore collision". Member 01 returned to `backup_verified`; all three files SHA-256 identical.

### E. Safety and cleanup

21. Sergei's running app was untouched: the same four `Books Arranger.exe` processes and the python process listening on 5210 were present before and after (PIDs recorded). All my backends were stopped through the app's own shutdown route; no QA process or listener remains.
22. I started the packaged Electron shell once, hidden, with an isolated profile, data folder and port. It refused to start ("Required installation settings are missing ... Repair the installation") because a copy outside an installation has no installer-written configuration. It exited at once; I checked the default Electron profile folder for changes in that window and found none.
23. Removed `Z:\_BooksArranger_QA_20261116\` (14 files, 9 folders). The delete script is literal-path, checks every file name against what this QA generated, deletes files one by one and then empty folders; it aborts untouched on any unexpected name. The Z: root listing is identical to the one taken before, apart from the removed folder and the root's own modified time. The folder is confirmed gone.
24. Removed the scratch workspace `I:\AI Projects\Worktrees\Books Arranger\qa-futaba-01313\` (744 MB, extracted payload, old-backend export, generated audio, data folders, probes) with `node scripts/studio-sweep.mjs --apply --path`. Confirmed gone.

## 5. Findings

No Blocker. No Major.

| # | Severity | Status | Finding |
|---|---|---|---|
| 1 | Minor | open, needs Sergei | **The NAS recycle bin keeps what the NAS method deletes, and my test residue is in it.** Z: is a QNAP share with a network recycle bin (`Z:\@Recycle`). Every original removed by the NAS legacy delete, the injected failed Restore's `.partial`, and my final folder removal were moved into `Z:\@Recycle\_BooksArranger_QA_20261116\` (24 files, about 1 MB). Two consequences. (a) Originals removed from the NAS do not free space until that bin is emptied or ages out; Z: is 90% full (364 GB free), so a large cleanup will not give the space back at once. This is the same as the pre-0.28 method Sergei ruled on, not a regression. (b) The residue is outside the one folder Sergei approved for writes, so I did not touch it. Repro: run any NAS cleanup and list `Z:\@Recycle`. Needs: Sergei's yes to purge exactly `Z:\@Recycle\_BooksArranger_QA_20261116\`, or his own emptying of it. |
| 2 | Minor | open, for Ender | **Waived test 4 sits in the path this release changed.** `test_legacy_intent_retry...` fails on `assertEqual(sorted(states),['backup_verified','removal_intended'])` and got `['backup_verified','backup_verified']`. The new `_withdraw_intent` returns a member to `backup_verified` when a check fails after the removal intent but before any delete, and the test's setup (a hold at the second output check) appears to go through that same path. It is labelled a flake and waived; I did not re-run it (outside the brief). Whether it is timing or an expectation the M1 fix made stale is not established. Steps 9 to 11, 14, 15 and 20 exercise the same state transitions end to end and passed. |
| 3 | Minor | open, for Judy only if Sergei meets it | **A Restore that fails with an unexpected error shows only a generic line.** Seen with the injected generic error: "Local control failed; inspect saved job and source cleanup status". Not tested with a real-world failure, so it may be fine for the usual ones. Not a regression. |

## 6. Not verified

- Native Browse and Save As dialogs: not opened. Start-folder logic is verified through the shipped module with a fake dialog; where Windows places the dialog on screen is not.
- Remembered places across a real app restart: verified in the renderer test with a storage double; not in a real Electron profile.
- The packaged Electron shell with a library, the tray, Quit, and the installer or uninstaller wizards: not run. The shell refuses to start outside an installation (step 22), and running the installer would have touched Sergei's installed app registration. `desktop/main.js` is unchanged since v0.28.12 (the release diff has only `folder-picker.js` and `preload.js` under `desktop/`).
- A real NAS-side writer racing the delete (the accepted risk Sergei ruled on): not tested; the check failure was injected.
- Real-world Restore failures other than the injected one.

## 7. Cleanup and personal folders

- Created and removed: the scratch workspace on I: (swept) and the Z: throwaway folder (removed, confirmed). No installer was run, no install to remove, nothing written into Sergei's app data (his catalog on 5210 was never opened).
- Left, by design of the NAS: `Z:\@Recycle\_BooksArranger_QA_20261116\` (finding 1). Everything else is gone.
- Personal-folder listing, copied from the builder's entry log (list only; I deleted or moved nothing here):

```
Entry-check personal folders: clean (5 subfolder notes) (7 folders, 10 drive roots watched)
  SUBFOLDER D:\SteamLibrary | changed below the depth checked
  SUBFOLDER E:\SteamLibrary | changed below the depth checked
  SUBFOLDER F:\SteamLibrary | changed below the depth checked
  SUBFOLDER H:\SteamLibrary | changed below the depth checked
  SUBFOLDER I:\SteamLibrary | changed below the depth checked
```

## 8. Pattern alerts

- **PA-1: the same entry-check failures recur across builds.** Three of the five waived tests already failed at v0.28.12 and are repeated here; two more are flakes. Each build now needs a waiver. Disposition for this candidate: ACCEPT, by Sergei's waiver. Disposition for the failures: DEFER to Ender as maintenance (fix the three test-setup failures, stabilise the two flakes; test 4 first, finding 2). If the same set appears on the next candidate it escalates to a blocking item.
