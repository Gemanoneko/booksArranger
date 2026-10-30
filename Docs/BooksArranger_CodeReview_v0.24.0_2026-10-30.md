# Code Review — Books Arranger v0.24.0

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-10-30
Tool: Books Arranger (Electron desktop utility, Python engine)
Release: v0.24.0
Commit range: d8789831ab5769765bb9f372666e2fc12c3fbd84..11c20db8b0747816204b660216aaf0512961fff5
Baseline: v0.23.0 (annotated tag 06210c4e, peeled to d878983)
Files changed: 64 files, +6412 / -179
Stand-down dimensions: none
```

How the base was chosen: the last report, `BooksArranger_CodeReview_v0.23.0_2026-10-28.md`, certified `8057ab4..d115eed`. Tag `v0.23.0` peels to `d878983`, which adds one commit to `d115eed`: docs and QA evidence only (7 files, +655 lines, no product code; read at a glance). So `d878983..11c20db` covers everything since the last review.

Out of range: the pending commit that updates three Git hash pins in `scripts/build_external_tools.py`. At `11c20db` the installer build stops on those pins. This report covers the source at `11c20db` only. The pin commit needs its own delta review before Sully releases.

Method: I read the whole diff. Targeted runs used an exported copy of `11c20db` in the session scratchpad: `test_book_move`, `test_destination_override`, `test_folder_unit_grouping` and `test_folder_regroup` passed (87 cases), and the node suites `desktop-folder-picker`, `python-check-batches` and `gate-scratch` passed (34 cases). Three scratch reproductions, never committed, confirm C1, M1 and M3. I did not run the full suite or the entry check, did not launch the app and did not touch Z: or any live `data/`.

---

## Summary

The 0.24.0 batch adds four things:

- **One folder is one book** (ruling 68 with 71a, 71b, 71d and 71m): `folder_unit.py`, `groups._folder_units`, and the startup pass `regroup_partial_jobs`.
- **Mojibake repair**: `tag_text.py`.
- **Identity fixes**: narrator credit, author prefix, quoted title, `unknown_given`, ruling 59 on every Approve, and the Tolkien lookup through Wikidata, FantLab names and edition volumes.
- **Chosen folder and moving finished books** (rulings 69, 70 and 71h to 71k):
  - `destination_overrides.py` and `book_move.py`;
  - publication-binding chain hooks;
  - the native picker seam (`desktop/folder-picker.js`) and its IPC;
  - the queued `destination` and `move` actions;
  - the Explorer fallback to the converted file's folder.

The commits after the batch are the spelling override (72b), test placement and waits (72d to 72f), and the Python pins (72g).

Red-team result:

- **One Critical:** ruling 68's new regroup check ignores Sergei's own "Keep as separate books" answer and container folders. It un-approves those books and sets their jobs aside again on every Approve.
- **Four Major:** the move journal can be left open with no in-session recovery; source-folder exclusion compares strings only; a number in a file name can blow up memory on the attention list; and the strategy treats the same volume serial as the same share.

---

## Rubric

Severity definitions and the safety floor: `Team/Docs/ProcessRules.md` § Severity definitions.

### 1. Security

- Status: Concerns
- **[Major] M2**: `destination_overrides.py:101-104`, `book_move.py:386`, `source_config.py:71`. The check that a chosen folder is not inside a source root or the app's data folder is a string or `realpath` comparison.
  - A UNC alias of a mapped source root passes. For example, `\\NAS\share\Audiobooks\X` against the configured `Z:\Audiobooks`, picked through "Network" in the picker.
  - The book can then be moved into a source folder, and `require_sorted(chosen)` then treats it as Sorted for source cleanup.
  - `validate` already holds the folder's native identity chain (`DirectoryBoundary`). Compare that chain with the source roots' and the data folder's identities instead of comparing names.
- **[Minor] m6**: `desktop/folder-picker.js:19`. `defaultPath` accepts any absolute path from the renderer, UNC included. A compromised renderer could make the dialog open an SMB connection to any host. Hardening: accept drive-letter paths only, or a path the engine supplied.
- The rest passes:
  - **Electron.** The window settings are unchanged (`contextIsolation`, `sandbox`, no `nodeIntegration`). The new IPC `books:choose-folder` is answered only for `trustedSender==='app'`. It returns a path or `null` and never touches a file. The preload passes strings only.
  - **Network.** Every new request goes through `client.json` (cache, per-site bounds and pauses; a `ResearchWait` is never bypassed). Parameters are escaped with `urlencode`, Wikidata ids are checked against `Q[1-9]\d{0,11}`, and FantLab work ids are type- and range-checked.
  - **Secrets.** None added, and no credentials are logged.

### 2. Correctness & Logic

- Status: Fail
- **[Critical] C1**: `merge_service.py:3076` (`_partial_folder_job`) calls `folder_unit.verdict(items, scope_of)` without `kept` or `container`. Grouping (`groups._folder_units`) passes both: `kept_parts` and library-root/`CONTAINER_NAMES` folders.
  - **The new flow breaks.** The folder question → "Keep as separate books" → Approve one book. The claim check (`_names_stale` → `_replan_needed`) sets the job aside with REGROUP_REASON, and `_release_for_regroup` sets `approved=0, review=''` and deletes `candidate_context`.
  - **The regroup changes nothing.** It honours `kept` and rebuilds the same two books, so every later Approve is set aside again. That book can never convert.
  - **The startup pass does the same.** `regroup_partial_jobs` (`:3103`, a background thread on every engine start) applies the same wrong verdict to existing pending or needs-attention jobs of books Sergei kept separate before 0.24.0, and to loose single-file books in container folders (71a).
  - **Reproduced at `11c20db`** with the `ApproveFixture` seed of `test_raised_folder_question_and_keep_as_separate_books`, then Approve on «Альфа»:
    - `_names_stale` = True (REGROUP_REASON);
    - `regroup_partial_jobs()` = [that job];
    - `approved`/`review` afterwards = `(0, '')`;
    - the rows afterwards are `[1, 1]`;
    - a second Approve is again stale = True.
  - This breaks ruling 68 ("existing approved/job-owned/completed sources must not be silently reassigned") and 71a.
- **[Major] M3**: `merge_service.py:2459` and `folder_unit.py:304`.
  - **The cost grows with the number itself.** `numbers()` takes any digit run in a file name as a part number. `_established_gap` builds `list(range(1, start))` before keeping 500 entries, and `numbers()` builds `range(first, last+1)`. Time and memory scale with the size of the number, not with the file count.
  - **Measured:** three files named `3000001.mp3` to `3000003.mp3` take `needs_you()` 2.98 s and a 120 MB peak. The folder is listed as Missing files with 3,000,000 "missing parts" (500 kept).
  - **At scale:** a 9-digit download id gives a multi-GB allocation, or a `MemoryError` that is not caught on the attention-list read.
  - **Smaller numbers are wrong too.** A year or id in one file name ("Послесловие 2005.mp3") produces a false gap.
  - **Severity:** this is crash-class. It is Major, not Critical, only because I could not check whether such names exist in Sergei's library.
- **[Major] M4**: `book_move.py:302, 429`. The strategy treats "same volume serial number" as "same volume".
  - **Why that is wrong:** two SMB shares on the same NAS volume report the same serial. The handle-bound rename across shares is then refused by Windows (not the same device). `rename_no_replace` raises `BoundaryError`, which becomes `Failed('changed')`.
  - **Effect:** a move to a folder on another share fails every time, and the message is the misleading "This book changed".
  - **Fix:** fall back to the copy strategy when the rename is refused, or compare the share root as well.
  - **Status:** found by reading the code; not reproduced on real SMB.
- **[Minor] m1**: `merge_service.py:4878-4881`. `destination_choose` commits the chosen folder before `_queue_move`. When planning or queueing refuses, the choice stays saved while the 409 says nothing moved. Refusal cases: "being moved now", or another queued action for the same book (`enqueue` raises).
  - Result: the row shows a chosen folder the book is not in, with no move queued.
- **[Minor] m5**: `public_research.py:1727, 1762`. `series_spelling` (72b) is applied only to the Goodreads and FantLab answers. The Wikidata, publisher and Litres series adapters return the source's spelling.
  - Note: the local `local_identity.series_spelling` (ruling 46) is a different function with the same name.

### 3. Crash / Stability Safety

- Status: Concerns
- **[Major] M1**: `book_move.py:354-373, 486-549`. `Mover.run` only turns `Failed` and `Unsettled` into journal outcomes.
  - **What escapes.** Any other `OSError` escapes and leaves the move in an active state until the next engine start. Examples: `os.open` of the temporary failing with a network error at `:502` (only `FileExistsError` and `PermissionError` are typed), and a `sqlite3` error in `_write`.
  - **What the user sees.** The row shows "moving". Every further Choose folder is refused with "This audiobook is being moved now". Series backfill and offline relocation hold the book.
  - **Reproduced at `11c20db`** (copy strategy, `os.open` of the temporary raising WinError 64):
    - `run` raised `OSError`;
    - the journal stayed at `copy_intent`;
    - `view` showed `moving`;
    - a new choice was refused;
    - the old file was intact.
  - **Risk:** no data was lost (recovery at start fails it cleanly), but there is no recovery during the session.
- **[Minor] m3**: `book_move.py:568`.
  - **The false failure.** After a copy move, the old file is deleted when its held handle closes. If another process holds it with share-delete (indexer, antivirus, Explorer preview), it still exists at the `lexists` check. The move is then recorded as `partial` and the row says it failed, although the new file is committed and the old one disappears moments later.
- Pass for the rest:
  - **Interrupted-move recovery:** every journal state reconciles on restart, and the old file is removed only after a full re-hash of the same bytes.
  - **Rename:** the rename runs on the held handle with no replace.
  - **Copy:** the temporary is created exclusively, fsynced, re-read and re-hashed, then published with no replace. The location is committed before the old file is disposed.

### 4. Performance

- Status: Concerns
- See **M3**: memory and time grow with the number in a file name.
- **[Minor] m7**: `merge_service.py:326, 4722`. `_chosen_folders()` opens a catalog connection and runs two queries on every call. `require_sorted` callers evaluate it eagerly on every Sorted check, including each source-cleanup check.
- **[Minor]** `book_move.py:430-537`. A copy move reads the whole audiobook four times (hash, copy, re-hash of the temporary, and the publish hash) plus one write. Acceptable, but slow over SMB for multi-GB books.
- **[Minor]** `merge_service.py` `destination_view`: every list read runs `json_extract(manifest,'$.candidate_id')` over all completed `audio_jobs`.

### 5. State & Data Safety

- Status: Fail
- C1 (above) is also a state-safety failure: approvals and saved review values are dropped automatically at engine start on the live catalog, against Sergei's recorded answer.
- **[Minor] m2**: `destination_overrides.py:91-134`.
  - **The gap.** `validate` refuses source roots, the data folder and (in the caller) the cache folder. It does not refuse the app's own install folder (`%LOCALAPPDATA%\Programs\…`, per-user NSIS).
  - **Why it matters.** That folder is writable, and electron-builder's uninstaller removes it recursively on every update. A book moved there is deleted by the next update.
- **[Minor] m4**: `book_move.py:375-405` against the `destination_overrides.py` docstring ("never followed by name").
  - **The gap.** A queued move runs to `target_folder` by name. The identity recorded at choose time is not checked again when the move runs.
  - **Scope.** `_move_to_chosen` does check it; the direct Choose path does not. The window is the queue wait.
- **[Minor] m10**: `destination_overrides.py:3-6` and `entered_names.book_key`. A choice made before conversion is keyed by the exact file set, as names are. Any membership change drops it silently. Examples: a new file in the folder, a ruling-68 regroup, a 71d set-aside. `_override_stale` then re-plans the pending job to the computed folder, and nothing on the row says the chosen folder no longer applies.
- Pass for the rest:
  - **Deletes.** The original file is deleted only through the held exact handle after commit (71h). `tidy` (71k) uses ruling 24a's `_remove_folder`: ancestry boundary held, ordinary directory, an empty listing, then a plain `rmdir`. It never touches the output root, a source root or a drive root. Outside the output folder it removes only the one folder the book left.
  - **Paths.** Cyrillic, brackets and spaces are handled by `ordinary()`, `DirectoryBoundary` and NFC/normcase keys.
  - **Length.** The 240-character limit is checked at validate, at plan and in `chosen_folder`.
  - **Gate scratch.** `gate-scratch.mjs` removes only entries this run created, unlinks links before deleting, and never follows them.

### 6. Input Handling

- Status: Pass
- **Server.** `/api/candidate/destination` is shape-checked (`folder_value`: a string of 1 to 1000 characters, no NUL, or `null`). The engine is the only validator.
- **Paths.** `ordinary()` refuses `\\?\` paths, traversal, alternate data streams and device names.
- **Regexes.** The new identity regexes have bounded repetition and no catastrophic backtracking.
- **Renderer.** New page text is set through `textContent` (`node()`), with no HTML sinks.

### 7. Maintainability (no Critical findings on its own)

- Status: Concerns
- **[Minor] m9**: `book_move.py:388`: an `if` condition with a run of embedded spaces, a lost line break.
- **[Minor] m9**: `destination_overrides.py:202`: a no-op ternary (`book_key if not job_id else book_key`).
- **[Minor] m9**: two hand-synced Python pins (`scripts/guarded-io.mjs:6`, `scripts/build_native.py:16`).
- **[Minor] m11**: `scripts/python-check-batches.mjs:136`. `GATE_PLACEMENT` applies only if every listed module still exists. Renaming or removing one module silently sends all of them back to the old weights, which brought back the r1 to r4 imbalance.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns
- **[Minor]** `merge_service.py:236` says chosen folders "count as Sorted for those books". `_chosen_folders()` is global and append-only: every folder ever chosen, retracted ones included, counts for every book.
- Also m4 (counted under dimension 5): the `destination_overrides` docstring promises an identity check that the queued move path does not make.
- **[Minor] m8**: ruling 72e names three suites. The widened helpers (`test_automatic_media.py:52`, `test_merge_service.py:71`) are shared and also lengthen the waits in about eight other suites.
  - No assertion was weakened: both loops still return as soon as the job ends and still fail with their own message.
- Test expectations changed by ruling 68 were checked (`test_anthology_volumes`, `test_book_delete`, `test_groups_filters`, `test_identity_v5`, `test_join_parts`, `test_part_sets`, `test_todo_holds`, frontend). Each replaced a "split" expectation with a stricter "one held question" expectation. The Cyrillic-author fixtures moved to Latin have a dedicated replacement test (`test_approve_this_order_keeps_ruling_59`). No assertion was weakened.

### 9. Build & Release Hygiene

- Status: Pass
- **Python pins (72g).** The SHA-256 of `C:\Python314\python.exe` is `d718435b…a000` (version 3.14.10), which matches both pins. No old pin remains outside `dist/`.
- **Placement and gate.** `943b21f` keeps every test (it places, never drops). The five approved pins are inside it, and the limits are unchanged (540 s / 580 s / 600000 ms).
- **Versioning.** Version, lockfile and changelog are still 0.23.0, as expected before Sully bumps them.
- **Pending.** The Git pin delta in `scripts/build_external_tools.py` must be reviewed before the installer build.

---

## Patterns

**Two checks that should agree diverge.** C1 is the third time in recent reviews that two implementations of one rule disagree; 0.22.0 N1 (a saved panel protecting a set) was another. Here the grouping and the claim check each call `folder_unit.verdict`, with different inputs.

**Typed errors with an untyped gap.** M1 repeats an older shape: a journal whose failure path types only the exceptions it expects.

**Fix shape.** One shared "is this folder one book?" decision that both callers read. A move runner that ends every exception in a terminal or recoverable state.

---

## Verdict

- Total Critical: 1
- Total Major: 4
- Total Minor: 16

Verdict at `11c20db` (superseded by the delta review below; kept as plain text so the release gate reads one verdict line only): RELEASE BLOCKED

| # | Sev | Dim | file:line | Finding | Must fix before release |
|---|-----|-----|-----------|---------|--------------------------|
| C1 | Critical | 2 Correctness / 5 State | `merge_service.py:3076` (`_partial_folder_job`); also `:3103` (`regroup_partial_jobs`) | The claim check and the startup pass judge "part of a folder" without Sergei's kept-separate answers or the container rule. Kept-separate and container-folder books are un-approved, their saved review is cleared, and every new Approve is set aside again. | Give the same verdict inputs as `groups._folder_units` (`groups.kept_parts`, container folders), or read the book's own recorded `folder_unit` decision. Add regressions: (1) Keep as separate books, then Approve: `_names_stale` is False and `regroup_partial_jobs()` returns []; (2) the same for a loose file in a library-root/container folder. |

Majors M1 to M4 and all Minors are logged for Ender's next cycle. M1 and M3 are cheap and Ender may want them in the same rebuild as C1: type every `OSError` and `sqlite3.Error` into a terminal or recoverable state, and bound `numbers()` and `_established_gap` by file count, not by the value of the number.

---

## Delta review 11c20db..67b3ac4 (2026-10-30)

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-10-30
Commit range: 11c20db8b0747816204b660216aaf0512961fff5..67b3ac4af0fd65dc3c9898e753208d5cda4a8f3f
Commits: 1 (67b3ac4 "fix: Senua 0.24.0 release blockers C1 and M1-M4")
Files changed: 10 files, +499 / -53 (6 product files, 4 test files)
Out of range: the pending Git hash-pin commit in scripts/build_external_tools.py
```

Method:

- **Reading.** I read the whole diff, plus the code around it: `Mover.run`, `_rename`, `_copy`, `reconcile`, `VerifiedFile`, `validate`, `folder_unit.verdict`, `_folder_units` and the page's refusal mapping.
- **Targeted tests on an exported copy of `67b3ac4`.** `test_book_move`, `test_destination_override` and `test_folder_unit_grouping` passed (88 cases). `test_entered_names.ClaimCheckFolderTests` and `test_folder_regroup` passed (8 cases).
- **Negative control.** I ran the new tests against the `11c20db` source: 10 failures and 4 errors out of 16 cases. Every new test fails without its fix.
- **M3 comparison of old and new code.** `numbers()` at both commits gave identical output on 24,000 random cases (file names, track tags and disc, including 1,272 cases with more than 500 skipped numbers), once the old output is cut to 500.
- **Read-only checks on the real NAS.** I opened folders for attributes only and wrote nothing. Details under M2.
- **Three scratch reproductions** (never committed): D1, the plain-`OSError` version of D1, and an M1 leftover.
- **Not done:** the full suite, the entry check, an app launch, and any write to Z: or to the live `data/`.

### Original findings

| # | Status | Evidence |
|---|--------|----------|
| C1 | **Closed** | Both callers now use one decision, `groups.folder_verdict` (`groups.py:514`), and nothing else calls `folder_unit.verdict`. The claim check passes `kept_parts` and the job's own root. A job whose files Sergei kept separate returns early (`merge_service.py:3075-3076`). Both regressions I asked for exist and pass, and both fail at `11c20db`. The startup pass shares the same function. Everything else that grouping excludes (`.m4b`, Arranger output, anthology folders) the claim check also excludes or returns early on. I found no input that brings the loop back. |
| M1 | **Closed** | `OSError`, `sqlite3.Error` and `ValueError` (`BoundaryError` included) now end in `_settle` (`book_move.py:384-412`). `_settle` reconciles the move in the session, the same way a restart would. The new tests cover a network error on the temporary and catalog errors at `copied` and `old_removal_intent`. A plain `OSError` after publication now completes correctly (scratch reproduction). Leftover: any other exception type still escapes. A synthetic `KeyError` at `copied` left the journal at `copy_intent`. I found no real way to reach it, so I log no finding. |
| M2 | **Closed** for the case I reported | `validate` now compares every folder in the chosen folder's held chain, by volume serial and file index, with each source folder and the data folder. It does this before the probe writes (`destination_overrides.py:141-169, 216`). Read-only on the real NAS: `\\NAS3247BD\Public\Audiobooks` is refused as `unsafe`. `Z:\Audiobooks Sorted` and `\\NAS3247BD\Public\Audiobooks Sorted` are accepted. The default `Y:\Books\Books` (no Y: drive on this machine) is skipped, not refused. The share root has a non-zero index (`Z:\` = `2d511e03 / 0x790001`), so choosing a folder on Z: is not refused as `unchecked`. The page shows the engine's sentence for `unchecked`. Leftovers: d2 and d3. |
| M3 | **Closed** | Skipped numbers now come from neighbouring values, and only the first 500 are ever built (`folder_unit.py:266-280`, `merge_service.py:2461`). The tests limit peak memory to under 1 MB (2 MB on the attention list) for a nine-digit number. Output is unchanged for ordinary gaps (see the comparison above). No other code builds a range over `total` or `end`, and the page doesn't either. Leftover: d4, the false-gap part of M3, which was not in the fix's scope. |
| M4 | **Closed** | `RenameRefused` keeps its Windows error. On error 17 the move continues as the existing copy: `rename_intent`, then `copy_intent`, and the strategy is set to `copy`, so recovery handles it as a copy. Any other refusal fails as before (the test checks this with error 5). This is unit-tested only; a real SMB test needs writes on Z:. **Correction to my own M4:** this NAS gives every share its own volume serial. Measured read-only with `NetShareEnum` plus an attribute-only open of each share root: Web `2c541e03`, Public `2d511e03`, homes `2f4d1e05`, Multimedia `3c660815`, Download `04460816`. On this NAS a move between shares already takes the copy path, so the failure I described does not happen here. The fallback still helps a Windows-hosted share and a move within one share under two spellings (Z: and its UNC name report the same serial). Leftover: d5. |

### New findings

- **[Major] D1** (dimensions 3 and 5): `book_move.py:585-602`. This is the defect Ender reported, rated here.
  - **What happens.** `publish_no_replace` succeeds. Then `VerifiedFile(target)` or `.facts()` raises `BoundaryError` (for example `FileInUse` from a sharing violation, or a share that drops at that moment). The `except BoundaryError` at `:600` turns this into `Failed('unavailable')`. `run` then records `failed`, because the state is still `publish_intent`.
  - **Reproduced** (scratch, copy strategy, one `FileInUse` on the published file):
    - the state is `failed`, cause `unavailable`, and the row reads "{folder} isn't available… Nothing was moved.";
    - the new file is in the target folder and the old file is kept;
    - the catalog still points at the old file;
    - `recover()` leaves the move alone (it is finished);
    - a new Choose to the same folder is refused with `target_exists`.
  - **Severity: Major, not Critical.** Nothing is lost: both files are verified to be the same bytes, and the catalog stays consistent with the old one. But the row says something false, a full-size copy sits in the library untracked for good, and moving the book again needs Sergei to delete that file by hand. The chance is low: it needs a transient error in the instant between publication and the re-open.
  - **Fix:** once `publish_no_replace` has returned, raise `Unsettled` for any failure (not `Failed`). `run` then reconciles from `publish_intent`: it proves the target, commits, and removes the old file only after proof. A plain `OSError` at the same point already takes this route through M1's `_settle` and completes (scratch reproduction). Add a regression test that raises `FileInUse` on that re-open.
- **[Minor] d2** (dimension 1): `destination_overrides.py:141-169`.
  - **The gap.** The identity is (volume serial, file index), and this NAS gives each share its own serial. So a source folder reached through *another* share, or through a server-side link, does not match, and it passes.
  - **Exposure today.** None of the NAS's current share roots is the source or a folder above it (their indexes differ from `0x790001` and `0x7b0323`), so nothing is exposed now.
  - **Possible hardening:** for a chosen folder on a server that also hosts a source, compare file indexes across that server's shares, or refuse a folder that is not on the source's own share.
- **[Minor] d3** (dimension 1): `merge_service.py:4884`. The cache folder is still compared by path text, and only after `validate`'s probe has already written into the chosen folder. This is now inconsistent with the identity check for sources and the data folder. Move it into `validate`'s place list.
- **[Minor] d4** (dimension 2): `folder_unit.py:291-312`. Carried over from M3 ("Smaller numbers are wrong too"). One file name carrying a year or an id, beside `01…10`, still produces a false run of skipped numbers. The impact is limited: `_established_gap` only relabels a book that is already held as `order_unclear`, now under Missing files with up to 500 phantom parts.
- **[Minor] d5** (dimension 2): `book_move.py:469, 568`. During the M4 fallback, progress goes to 100 % (the hash share is picked before the rename is refused), then drops back to 50–95 % for the copy.

### Delta verdict

- Open Critical: 0. C1 is closed and the safety floor is intact.
- Open Major: 1 (D1). M1 to M4 are closed.
- Open Minor: 20 (the 16 from the first review, which this range did not touch, plus d2 to d5).
- Still required before Sully releases: the pending Git hash-pin commit in `scripts/build_external_tools.py` gets its own delta review. When it is appended, this section's verdict line is updated in place, because the release gate refuses a file that has two verdict lines.
- Report bookkeeping: I changed the first review's verdict line (above) to plain text, so this line is the only one the release gate reads.

Verdict at `67b3ac4` (superseded by the final delta review below; kept as plain text so the release gate reads one verdict line only): RELEASE CLEAR

---

## Delta review 67b3ac4..4b7c8fe (2026-10-30)

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-10-30
Commit range: 67b3ac4af0fd65dc3c9898e753208d5cda4a8f3f..4b7c8fe82a276f4eaa82821d1f3d1a343ba44f11
Commits: 4
  d6b1285 fix: Senua 0.24.0 D1 and Judy's refusal copy for chosen folders
  4b1d3ca fix: Judy's copy for each case a chosen folder can't be checked
  35bc4b6 fix: re-pin Git for Windows hashes to installed 2.56.0.windows.4 (ruling 73a)
  4b7c8fe fix: a year or an id in a file name is not a part number (ruling 73f)
Files changed: 10 files, +318 / -58 (6 product or build files, 4 test files)
Out of range: nothing pending. Ruling 73h says the batch is complete at 4b7c8fe.
```

Method:

- **Reading.** I read the whole diff. I also read the code around it: `Mover.run`, `_settle`, `_copy`, `reconcile`, `_prove`, `_remove_old`, `publish_no_replace`, the `__exit__` of `DirectoryBoundary` and `VerifiedFile`, `_inside_by_identity`, `numbers()` and its two callers, the `needs_you` call site of `_established_gap`, the queue's `run_queued`, and every place the page writes a move sentence.
- **Targeted tests on an exported copy of `4b7c8fe`.** These passed: `test_book_move` (25), `test_destination_override` (30), `test_folder_unit_grouping` (45), and the node suites `test_0231_destination_frontend` and `test_0231_rows_frontend`.
  - `test_folder_regroup` and `test_part_sets` could not run from the scratch export. All 7 errors are the same: "Verified metadata exceeds the supported Windows output path length". The export's folder is too deep for those fixtures, and each error is raised at Approve, before any numbering assertion. Their gap fixtures use numbers below 1000 (`01`, `02`, `04`), which 73f returns unchanged by construction. The coming gate run covers both suites.
- **Two scratch probes, never committed:** the D1 re-open failing twice (FileInUse, then a share drop), and `numbers()` at `67b3ac4` against `4b7c8fe` on seven numberings.
- **Pins.** I read the SHA-256 and link count of every pinned Git file on this machine (read-only).
- **Not done:** the full suite, the entry check, a build, an app launch, and any write to Z: or the live `data/`.

### Earlier findings

| # | Status | Evidence |
|---|--------|----------|
| D1 | **Fixed only when the error clears at once.** Still open as D1r (below). | Any exception from the re-open of the placed copy becomes `Placed` (`book_move.py:615`). `run` settles it from `publish_intent` (`:395`), and that path never deletes before proof: `_prove` re-hashes the placed file in full, the move commits, and `_remove_old` re-hashes the old file before `dispose()`. The held old handle is closed before `_settle` runs (`_run`'s `finally`), and neither `__exit__` deletes anything. Scratch probe with one failure: `complete`, a single file in the target folder, the old file removed, the catalog moved. But the new test raises only once. |
| d4 | **Closed** by 73f | One file name with a year or an id beside `01…10` no longer makes a false gap (`test_a_year_beside_the_parts_is_not_a_part`; probe case D). |
| d2, d3, d5 | Open, not touched by this range | d3 is now at `merge_service.py:4885`. |
| First review's 16 Minors | Open, not touched by this range | |

### The three areas the brief named

**1. D1 recovery path: can a copy be lost, or a delete happen before verification?** No.
- **Nothing is lost.** `publish_no_replace` raises nothing after its rename (only `CloseHandle` follows it). `_discard_temp` removes only an existing name that starts with `TEMP_PREFIX`, and the published name is not one. The old file is removed only by `_remove_old`, and only after `_prove` has re-hashed the target and `_remove_old` has re-hashed the old file.
- **But the move can still end with the wrong answer.** If the error lasts longer than a moment, D1's result comes back (D1r).

**2. The page and the engine's sentences: is the text escaped?** Yes.
- **Where the text goes.** The engine's `unsafe` and `unchecked` sentences reach the page in three ways: `view()['message']`, the 409 body's `error`, and a queued outcome's `error`. All three end in `setLine` or `queueAnnounce`, and both use `textContent`.
- **No HTML sinks.** There is no `innerHTML`, `insertAdjacentHTML`, `outerHTML` or `document.write` anywhere in `web/`. The sentence never goes into an attribute.
- **The engine side.** `{place}` is put in with `str.format`, which inserts the path once and never reads it as a template.
- **Electron.** Nothing under `desktop/` changed in this range.
- **Result:** a source folder named `<img src=x onerror=…>` would show as literal text.

**3. The 73f outlier rule: can it hide a real missing part?** It cannot release a held book. In unusual numberings it can stop naming a gap (d6).
- **It only changes labels.** `folder_unit.numbers()` has two callers: `_established_gap` and the Numbers line. Both only describe a book. `_established_gap` runs only for a book whose research already holds it as `order_unclear` (`merge_service.py:2308-2315`). When it returns None, the row stays listed under its own hold. So 73f can never let a book with a missing part convert.
- **Probe, old and new `numbers()`:**
  - Unchanged: an ordinary gap, a numbering that climbs past 1000 (`0001–1500` without `0700`), and disc-and-track numbers below 1000.
  - Fixed: Sergei's example (`01–03` plus `Интервью 2019`), and an id placed before the part number (`3000001_01`…). That one now reads the real gap 3 instead of 3000003.
  - Lost, see d6: two numberings stop naming a real gap.

### New findings

- **[Major] D1r** (dimensions 3 and 5): `book_move.py:735-740` (`reconcile`, `publish_intent`) and `:757` (`_prove`). The D1 fix settles the move from `publish_intent` at once, because the first entry of `SETTLE_PAUSES` (`:399`) is a pause of 0.
  - **Why the fix misses.** `_prove` opens the same placed file within microseconds of the failed re-open. It swallows `BoundaryError` and `OSError` and returns None. `reconcile` then records `failed` with "The move was interrupted before the file moved", even though the file is in the target folder. `_settle` retries only when an exception escapes, so its 0.5 s and 2 s pauses never run.
  - **When it happens.** The causes the fix names itself (a file "in use for a moment", "the share dropped") usually last longer than microseconds. For those causes the fix does not change D1's result.
  - **Reproduced at `4b7c8fe`** (scratch, copy strategy, the re-open failing twice, once with `FileInUse` and once with "network name is no longer available"):
    - the state is `failed`, its cause is empty, and the row reads "Move was not accepted. Nothing was moved.";
    - the verified copy is in the target folder, and the old file is kept;
    - the catalog still points at the old file;
    - a new Choose to the same folder fails with `target_exists`;
    - `recover()` never looks at the move again, because it is finished.
  - **Same D1 shape.** Nothing is lost and nothing is deleted. The row says something false, and an untracked full-size copy stays in the folder.
  - **The docs claim more.** The module docstring (`:28-30`) and the `Placed` docstring both say it is never reported as "nothing moved".
  - **The test can't see it.** `test_a_failure_after_the_copy_is_placed_finishes_the_move_and_leaves_no_stray_copy` raises only once.
  - **Fix:**
    - In `reconcile`'s `publish_intent` branch, a target that exists but cannot be opened now should raise, not return None. `_settle` then retries after its pauses.
    - If it still can't be opened, leave the journal at `publish_intent` for `recover()`, or end in a state that tells the truth ("a copy is in {folder}; the original was kept"). Fail with "nothing moved" only when the target is absent, or opens and is not the same bytes.
    - Add regressions that raise `FileInUse`, and the share drop, on two or more re-opens.
- **[Minor] d6** (dimension 2): `folder_unit.py:294-304, 321-323`. 73f goes further than the ruling's example, and a real gap can stop being named in two numberings:
  - **(a) Every number in a place is 1000 or more.** That place counts as having no part numbers. Probe: `1001…1012` without `1005`, and no track tags. Old: skipped `1005`. New: no Numbers line and no Missing files row.
  - **(b) A gap of more than half a numbering that passes 1000.** Probe: `0001–0400` plus `1000–1500`. Old: `401…` listed. New: None. The 501 files above 1000 also drop out of the numbering.
  - **Impact:** labelling only. The book stays held as `order_unclear` (see area 3).
  - **Ruling:** 73f covers "far larger than the folder's other part numbers". Case (a) has no other part numbers. Whether such names are parts is Sergei's call, not mine.
  - **Suggestion:** keep 73f as it is, and in case (a) let the track tags decide, as they already do when tags exist (probe case B2: tags `1…12` without `5` are reported).

Pass for everything else in this range:

- **Copy split (`4b1d3ca`).** `_inside_by_identity` behaves exactly as before. A volume serial of 0 still refuses every choice, a missing file index still refuses only on the same volume, and a chain with no index still refuses. Only the sentence changed. The new tests pin each sentence, including the case where the data folder's drive reports serial 0 (`UNCHECKED_NO_SERIAL_APP`).
- **`view()` message.** It is set only for a failed `unsafe` move, and an empty message falls back to "Move was not accepted." Every `unsafe` the engine raises now carries one of the three fixed sentences. The fallback copy in `MESSAGES['unsafe']` is now reached only by an `unsafe` refusal with no message.
- **Pins (`35bc4b6`).** Git is 2.56.0.windows.4. All seven pinned hashes match the installed files:
  - the wrapper: `cmd/git.exe`, with `git-lfs.exe` (2 links);
  - the core: `ucrt64/bin/git.exe` and its three `git-*-pack/archive` names (4 links);
  - the four DLLs in both `bin` and `libexec/git-core` (2 links each).
  - No old pin is left outside `dist/`. Ruling 73a pins whatever is installed, so the pins prove the build uses the same Git binaries as this machine, not that the binaries are genuine. That is accepted by the ruling.
- **Security floor.** No Electron setting or IPC change, no secrets, and nothing writes outside its scope.

### Final verdict

- Open Critical: 0. The safety floor is intact.
- Open Major: 1 (D1r, the remaining part of D1).
- Open Minor: 20 (the 16 from the first review, plus d2, d3, d5 and d6; d4 is closed by 73f).
- Report bookkeeping: I changed the verdict line of the `11c20db..67b3ac4` delta (above) to plain text, so the line below is the only one the release gate reads.

Verdict at `4b7c8fe` (superseded by the delta review below; kept as plain text so the release gate reads one verdict line only): RELEASE CLEAR

---

## Delta review 4b7c8fe..790af0b (2026-10-30)

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-10-30
Commit range: 4b7c8fe82a276f4eaa82821d1f3d1a343ba44f11..790af0b5f3ba7c9fe9f731f919112d5a3bed5e9a
Commits: 3
  8444a21 fix: a placed copy still in use is retried, never "nothing moved" (Senua 0.24.0 D1r)
  0b67a80 fix: numbers all 1000 or more are part numbers and name their gap (ruling 73i)
  790af0b feat: a move whose retries ran out reads "Move not finished" (ruling 73k)
Files changed: 9 files, +446 / -59 (5 product files, 4 test files)
```

Method:

- **Reading.** I read the whole diff. I also read the code around it: `Mover.run`, `_settle`, `reconcile` (every state), `_prove`, `_remove_old`, `rename_no_replace`'s postcondition block, `recover`, `_start_move_recovery` and where it is called, `run_move`, `_move_running`, `_unfinished_move`, the queue's `run_queued`, and every place the page writes the new move text.
- **Targeted tests on an exported copy of `790af0b`.** These passed: `test_book_move` (29), `test_destination_override` (32), `test_folder_unit_grouping` (47), and the node suite `test_0231_destination_frontend`.
- **Two scratch probes, never committed.** The first runs four move cases (A to D below). The second compares `numbers()` at `4b7c8fe` and at `790af0b` on eight numberings.
- **Not done:** the full suite, the entry check, a build, an app launch, and any write to Z: or the live `data/`.

### Earlier findings

| # | Status | Evidence |
|---|--------|----------|
| D1r | **Closed for a placed copy that is in use.** Still open for a share that drops (D1r2). | `reconcile`'s `publish_intent` branch now calls `_prove(..., placed=True)` (`book_move.py:801`). An open or read error raises `Unopened`, which is a `ValueError`. `_settle` then tries again after 0.5 s and 2 s. If the error outlasts both pauses, `Unfinished('copy')` is raised (`:487`) and the journal stays at `publish_intent` with both files kept. `recover()` finishes the move at the next start. The new test covers 2, 3 and 4 failures in a row, and the end state of each. The share-drop case in that test keeps the file visible (`lexists` is True), but a real dropped share hides it. See D1r2. |
| d6 | **Closed** by ruling 73i, as worded (`1001…1012` without `1005` now lists `1005`) | What remains is in d8. |
| d2, d3, d5 and the first review's 16 Minors | Open, not touched by this range | |

### The four areas the brief named

**1. Is D1r closed? Can an unrecorded copy be left behind, or a delete happen before the move is verified?**
- **No delete before verification.** `_remove_old` still re-hashes the old file before `dispose()`, and it runs only after `_prove` has re-hashed the target and the move has committed. `Unopened` and `Unfinished` only raise. Nothing new deletes anything.
- **An unrecorded file can still be left behind, in two ways:**
  - a copy, when the share drops (D1r2);
  - a renamed file, on the same-volume path (D1r3).

**2. The `unfinished` state end to end. Is the new text escaped?** Yes.
- **How the state flows:**
  - **Engine:** `view(move, unfinished=…)` turns a journaled move that nothing runs into `unfinished`, with cause `copy` or `catalog` and the raw error in `detail`.
  - **Queue:** `run_queued` returns `refused` with cause `unfinished`, the folder and the move line.
  - **Page:** the outcome replaces `row.move`. The row shows the copy or catalog sentence, the button reads "Needs restart" with Judy's tooltip, and the raw error goes only into Technical details.
  - **Reload:** every list read asks `_unfinished_move` again, so the page shows the same state after a reload. After a restart, recovery decides again.
- **Escaping:** every new string reaches the page through `setLine`, `queueAnnounce` or `setText`, and all three use `textContent`. `web/` still has no `innerHTML`, `insertAdjacentHTML`, `outerHTML` or `document.write`. The tooltip is a fixed string.
- **Gaps:** d7 (a move that ran out of retries while still queued) and d9 (`$` patterns).

**3. Can running-move tracking during start-up recovery race?** Not in the tracking itself.
- **The tracking holds up:**
  - The recovery thread is created and started in `MergeService.__init__` (`merge_service.py:238`), before the server answers anything.
  - While that thread is alive, `_move_running` is True for every move. Rows read "moving", and a new choice is refused with "being moved now".
  - The thread copies `mover.unfinished` into `_move_unfinished` in a `finally` that runs before the thread ends, so no read sees "not running" without the reason.
  - `run_move` records the reason before it drops the move from `_moves_running`.
  - The set and the dict are only touched by single operations, which are safe across threads in Python.
- **One race that the tracking does not close (d10):** recovery itself does not skip moves that this session is running.

**4. 73i: can a real gap still be hidden?** Yes, in three numberings (d8). Labels only: a held book stays held.
- **Measured, 73f against 73i:**
  - Sergei's 73i example: `1001…1012` without `1005` now lists `1005`.
  - The id-before-part case (`3000001_01`…) still reads the real gap 3.
  - `0001–0400` plus `1000–1500` still names nothing, which is the shape of 73j's option A.

### New findings

- **[Major] D1r2** (dimensions 3 and 5): `book_move.py:801`. The branch decides "absent" with `os.path.lexists(target)`, and `lexists` returns False for *any* error. A path on a share that has dropped reads as absent, so the move fails with "nothing moved" before `_prove(placed=True)` can raise `Unopened`.
  - **Probe A** (copy placed, then the share drops: the target is unreachable and `lexists` is False):
    - the state is `failed`, its cause empty, and its reason "The move was interrupted before the file moved";
    - there was no retry (no pause was taken);
    - the copy stays in the target folder unrecorded, the old file is kept, and the catalog stays on the old file.
  - **Probe B** (the in-use case correctly ends `Unfinished('copy')` at `publish_intent`; at the next start the NAS share is not reconnected yet): `recover()` gives the same result, `failed`, with the copy left unrecorded.
  - **Same D1 shape.** Nothing is lost and nothing is deleted. The row says "Move was not accepted. Nothing was moved.", and a new Choose to that folder is refused with `target_exists`.
  - **Fix:** treat the target as absent only when `os.lstat` raises `FileNotFoundError` and the target's parent folder opens (`destination_overrides._absent` already makes this distinction). Any other error raises `Unopened`. Add a probe-A test that makes the target unreachable, not just unopenable.
- **[Major] D1r3** (dimensions 3 and 5): `book_move.py:777-784`, the `rename_intent` branch. This code is from before this range, but it is the same question.
  - **How it happens.** `rename_no_replace` re-opens the renamed file by name after the OS accepts the rename. When that open is refused (the same "in use" that D1 starts from), it raises `RenamePostconditionError`. Then `run` reconciles at once. `_prove` is not called with `placed=True` here, so the second refusal returns None, and the move is failed as `partial`.
  - **Probe C**, same-volume rename:
    - the state is `failed`, cause `partial`, reason "The moved file could not be proven";
    - the old file is gone (it was renamed), the file is in the target folder, and the catalog still names the old path, where no file is left;
    - the row reads "Moved to {folder}. The old file in {old folder} couldn't be removed. Delete it yourself." That is false: there is no old file.
  - **Severity: Major, not Critical.** No bytes are lost: the file exists at the target. But the book's recorded output points at a missing file, and the move is finished, so `recover()` never looks at it again.
  - **Fix:** the same as D1r. In `rename_intent`, when the new name exists and the old one is gone, an open or read error raises (retry, then `Unfinished`), and `partial` is used only when the file opens and its bytes differ. Add a regression for a postcondition error with the re-open in use.
- **[Minor] d7** (dimensions 3 and 2): `book_move.py:487` with `merge_service.py:4951`.
  - **How it happens.** A move whose catalog stays locked while it is still `queued` ends `Unfinished('catalog')` with the journal still `queued`. Probe D: a lock while resolving its start, then every write refused. `view()` then gives `queued`, not `unfinished`, and `run_queued` answers `done`.
  - **What the row shows.** "Move queued. It runs when the app is free." and a disabled Choose folder… that says to cancel the queued move. But no queue item exists, so nothing can be cancelled. This lasts until a restart cancels it.
  - **Fix:** treat a `queued` journal that nothing runs as unfinished, or have `_settle` cancel it when the catalog answers again.
- **[Minor] d8** (dimension 2): `folder_unit.py:304, 334, 356`. Ruling 73i still hides or invents gaps in three numberings, measured against 73f. These are labels only (73j).
  - **(a) A missing first part is never named.** `1002…1012` (no `1001`) reads as whole: the numbering counts from its first number.
  - **(b) Track tags are no longer read.** Download ids `3000001…3000003`, contiguous, with track tags `1, 2, 4`: 73f named 3 from the tags, 73i names nothing. This is the download-id case 73f was written for.
  - **(c) A year can invent a gap.** `1001…1012` plus `Интервью 2019` names `1013–2018` (2019 is less than double 1012).
  - **Separately, 73j's own example.** For `0998, 0999, 2500–2510` the ruling says "no gap is named". The attention list still lists 1–500 as missing through the "starts after 1" rule. That is the same as before (73j says to keep the current behaviour), but the ruling's wording and the result differ. Jane may want to confirm it with Sergei.
- **[Minor] d9** (dimension 6): `web/app.js:2917` (`unfinishedLine`) and `:3984` (the queue line), the same pattern as the older `moveFailure`. A folder path or book title is inserted with `String.prototype.replace` and a replacement string, so `$&`, `` $` ``, `$'` and `$$` in it are expanded. The result is garbled text only, never markup (`textContent`). Fix: pass a function, `.replace('{folder}', () => folder)`.
- **[Minor] d10** (dimension 3): `book_move.py:751-758` with `merge_service.py:4998`.
  - **The gap.** `recover()` reconciles every non-finished move in its snapshot, without asking `_moves_running`.
  - **When it matters.** The snapshot may be taken late, for example when the catalog is busy at start (a 10 s busy timeout). A move Sergei planned in that window can then be cancelled while it is queued ("The app closed before the move ran"). If it is already copying, its temporary can be discarded and the move failed.
  - **Risk.** Nothing is lost: a failed copy keeps the old file, and the copy cannot publish because of the journal's expected-state checks. The window is small.
  - **Fix:** take the recovery snapshot before the engine accepts requests, or skip moves in `_moves_running` and moves created after this engine started.

Pass for the rest of this range: Electron settings, preload and IPC are unchanged. There are no secrets. The new queue outcome carries only engine-made strings and the move line. `Unfinished` keeps both files in every case I probed.

### Final verdict

- Open Critical: 0. The safety floor is intact.
- Open Major: 2 (D1r2 and D1r3; D1r is closed for a copy in use).
- Open Minor: 23 (the 16 from the first review, d2, d3, d5, and d7 to d10; d6 is closed by 73i).
- Report bookkeeping: I changed the verdict line of the `67b3ac4..4b7c8fe` delta (above) to plain text, so the line below is the only one the release gate reads.

Verdict at `790af0b` (superseded by the delta review below; kept as plain text so the release gate reads one verdict line only): RELEASE CLEAR

---

## Delta review 790af0b..797cc95 (2026-10-30)

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-10-30
Commit range: 790af0b5f3ba7c9fe9f731f919112d5a3bed5e9a..797cc951a69642cfc08483b0973ec5b5a7a40137
Commits: 4
  36c2653 fix: a placed copy behind a dropped share is never "nothing moved" (Senua 0.24.0 D1r2)
  bb61ff7 fix: parts beside more ids than parts name no gap (ruling 73j)
  78cdd80 fix: a renamed audiobook the app couldn't check is unfinished, never partial (Senua 0.24.0 D1r3)
  797cc95 fix: a rename behind a dropped share waits for it, never fails (Senua 0.24.0 D1r2, ruling 73l)
Files changed: 8 files, +346 / -30 (4 product files, 4 test files)
Not raised again (already in the backlog, per the brief): the converted set during the wait, and the copy-line mismatch in the rare case before the rename.
```

Method:

- **Reading.** I read the whole diff. I also read the code around it: `_rename`, `_copy`, `rename_no_replace`'s error handling, `publish_no_replace`, `reconcile` (every state), `_remove_old`, `_after_old_closed`, `destination_overrides._absent` and `_network_drive`, the new `open_folder` branch, the rows override, and the page's `unfinishedLine`, `destPlan` and the queue announcement.
- **Targeted tests on an exported copy of `797cc95`.** These passed: `test_book_move` (32), `test_destination_override` (33), `test_folder_unit_grouping` (49), and the node suite `test_0231_destination_frontend`.
- **Three scratch probes, never committed:**
  - `_absent` on a drive letter that is not there (read-only);
  - seven move cases (A, U, C, E, F, G, H below);
  - `numbers()` at `790af0b` against `797cc95` on five numberings.
- **Not done:** the full suite, the entry check, a build, an app launch, and any write to Z: or the live `data/`.

### Earlier findings

| # | Status | Evidence |
|---|--------|----------|
| D1r2 | **Closed for a network share.** Still open in two narrower ways (D1r4, d12). | `_absent` (`book_move.py:121`) returns True only when `lstat` says "not found" (2 or 3) and a folder above opens. Any other error raises `Unopened`. **Probe A:** a copy is placed, then the target answers WinError 64. The move is retried after 0.5 s and 2 s, ends `Unfinished('copy')` at `publish_intent` with both files kept, and recovery finishes it once the share is back. The rename path behaves the same way (`:800-801`). |
| D1r3 | **Closed for a rename whose check finds the file in use, or whose share drops.** Still open when the rename call's reply is lost (D1r4). | `rename_intent` no longer writes `partial`. A renamed file that cannot be opened raises `Unopened('renamed')` (`:808`). Bytes that differ fail it as `changed` (`:810`). **Probe C:** the postcondition fails and the re-check is in use. The move ends `Unfinished('renamed')`, the row reads `renamed`, and recovery later records `complete`, with the file at the target, the old name gone and the catalog moved. |
| 73j mismatch | **Closed** | `0998, 0999, 2500–2510` now names nothing (`folder_unit.py:345`). An ordinary gap beside more ids than parts is still named (`01, 02, 04` plus 5 ids lists 3). |
| d2, d3, d5, d7 to d10 and the first review's 16 Minors | Open, in the backlog (ruling 73l) | **d8 grows by one case:** a missing first part beside more ids than parts (`02–04` plus 5 ids) is no longer named. Before this range it was. **d9's `$` pattern** also applies to the new `renamed` sentence. |

### The three areas the brief named

**1. Are D1r2 and D1r3 closed? Can any path still leave an unrecorded file, record `partial` with the old file gone, or delete before verification?**
- **Unrecorded file:** yes, still possible.
  - A rename or publish whose reply is lost (D1r4, Major).
  - A placed copy on a local drive that is unplugged at the next start (d12).
  - A duplicate old file when its share is away during recovery from `committed` (d13).
- **`partial` with the old file gone:** no. Every path that writes `partial` now runs only while the old file is held or was just found, apart from a microsecond race between `lexists` and the open in `_remove_old`.
- **Delete before verification:** no. Nothing in this range deletes anything. `_remove_old` still re-hashes the old file before `dispose()`, and the copy path's `dispose()` still comes after the commit.

**2. The new absent check: can it misread a real absence as present forever, so a move is stuck?** Yes, in a narrow case, and in the other direction too.
- **Stuck forever (d14).** Any error that is not "not found" (2 or 3) and never clears keeps the move unfinished on every start. Examples: a share deleted or renamed (53/67), a host that is gone, or access denied (5).
  - Probe G shows the mechanism with WinError 64.
  - `plan` then refuses every new choice with "Close and reopen Books Arranger…", which never helps, and the page offers no way out. Nothing is lost.
- **The opposite direction (d12).** `destination_overrides._absent` counts a missing local drive letter as proof of absence. Read-only probe: `Q:\Books\Author\Book.m4b` gives `lstat` 3, and `Q:\` gives 3, so `_absent` returns True. That rule was made for source folders, where it is safe. It is not safe for a file the journal says was placed.

**3. The `renamed` IPC end to end, and escaping.** Consistent and escaped. One wrong statement when nothing can be checked (d11).
- **Engine.** `view` passes `renamed` through. `run_queued` sends it as an unfinished outcome with the move line. The rows override shows the book as finished and "Now in" the target (catalog facts only). `open_folder` opens the target folder from the journal, inside a `DirectoryBoundary`. The page never sends that path.
- **Page.** `unfinishedLine` reaches `setLine`, the queue line reaches `queueAnnounce`, and "Now in" is built with `node()`. All three use `textContent`. `entry.line.title` is a property assignment, not HTML.

### New findings

- **[Major] D1r4** (dimensions 3 and 5): `book_move.py:607-609` (rename) and `:680-684` (copy publish). Code from before this range, the last path in the D1 family. When the single rename call fails with a network error (`RenameRefused` with WinError 64, 59, 121 or 1236, or `publish_no_replace`'s `BoundaryError`), the result is unknown: the server may have done the rename and lost the reply. Both are mapped to `Failed('changed')`, a terminal "nothing happened".
  - **Probe E (rename):**
    - the state is `failed`, cause `changed`;
    - the file is at the target, and the old name is gone;
    - the catalog still names the old path, where no file is left;
    - `recover()` never looks at it again.
    - This is D1r3's end state with the "This book changed" message.
  - **Probe F (copy publish):**
    - the state is `failed`, cause `changed`;
    - the copy is in the target folder, unrecorded, and the old file is kept.
    - This is D1r2's end state.
  - **Related, rarer:** a renamed file whose bytes changed before the check also fails as `changed` while the catalog names the old, now missing path (`:810`).
  - **Fix:** treat a rename or publish error as definite only for codes that prove nothing happened (5, 32, 17, 80/183). For any other code, raise `Unsettled` so `reconcile` decides from what is on disk, through `_absent`, which already waits for a share that is away. Add regressions for E and F.
- **[Minor] d11** (dimension 2): `book_move.py:800`. When the share is away, `_absent(old, 'renamed')` raises `Unopened('renamed')` before anything shows that the rename happened.
  - **Probe G:** the rename never ran. Recovery records cause `renamed`, and the row says "The audiobook is in {new folder}". It shows "Now in" the new folder, and Open book folder targets the new folder, while the file is still at the old path.
  - It corrects itself once the share is back and the app restarts.
  - **Fix:** use cause `catalog` (or a neutral "can't reach the folder" cause) when neither name could be checked.
- **[Minor] d12** (dimension 5): `destination_overrides.py:140`, as used by `book_move._absent`. A placed copy on a local drive that is not present at the next start (an unplugged USB drive) reads as definitely absent.
  - **Probe U** (a crash right after placing, then recovery with the drive letter missing): `failed` with "The move was interrupted before the file moved". The copy stays on that drive unrecorded, and choosing the same folder later fails with `target_exists`.
  - **Fix:** for a placed file, count it absent only when a folder above it on the same drive opens, never when the walk ends at a missing drive.
- **[Minor] d13** (dimension 5): `book_move.py:839`. Recovery from `committed` or `old_removal_intent` still uses `os.path.lexists(old)`.
  - **Probe H:** a copy move crashes at `committed`, and at the next start the old file's share is away. The move is recorded `complete` without removing the old file. When the share returns, a full unrecorded duplicate sits in the old folder (often under Audiobooks Sorted).
  - The row ("Moved") is true and nothing is lost.
  - **Fix:** use `_absent` here too, and let an away share wait.
- **[Minor] d14** (dimension 3): `book_move.py:121-133`. A move whose target or old path keeps failing with an error other than "not found" stays unfinished on every start, and there is no exit in the app (see area 2).
  - For a copy move, the old file is recorded and intact, so failing it is safe.
  - **Fix:** after a few recoveries, or on Sergei's action, fail such a copy move once the old file proves intact. A rename move needs the share.

Pass for the rest of this range: Electron settings, preload and IPC surface are unchanged. There are no secrets. The new `open_folder` branch opens only a folder the engine journaled, and only inside a `DirectoryBoundary`.

### Final verdict

- Open Critical: 0. The safety floor is intact.
- Open Major: 1 (D1r4; D1r2 and D1r3 are closed for the cases they named).
- Open Minor: 27 (the 16 from the first review, d2, d3, d5, d7 to d10, and d11 to d14).
- Report bookkeeping: I changed the verdict line of the `4b7c8fe..790af0b` delta (above) to plain text, so the line below is the only one the release gate reads.

**Verdict:** RELEASE CLEAR
