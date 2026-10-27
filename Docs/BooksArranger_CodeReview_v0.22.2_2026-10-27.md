# Code Review — Books Arranger v0.22.2

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-27
Tool: Books Arranger (Electron / Python)
Release: v0.22.2
Commit range: d50a05f9606af8a2fc08f55684b1b14340700e51..7dcb4bc1c6217406c883c91bc87397630a9e2fe5 (tag v0.22.1 .. origin/main 7dcb4bc, 36 commits)
Release source commit: 7dcb4bc1c6217406c883c91bc87397630a9e2fe5
Release artifact manifest SHA256: 3b7d119897d2a1d422f93c3a54b7d4f8214c0bbc3231cc8b47269944e940128a
Reviewed source: the main checkout at 7dcb4bc (clean, read only). No worktree was needed.
Files changed: 101 files, +6613 / -538 (git diff --shortstat). Product code and scripts: 33 files, +3090 / -396. Tests: 62 files, +2850 / -139. Docs and CHANGELOG: 4 files, +670. package.json and package-lock.json: version only.
Method: LEAN (ProcessRules § Lean verification). I read the diff. I ran only the targeted tests behind the Xtra question and two throwaway probes behind M1 and M2. No suite, no mutation sweep.
Stand-down dimensions: none
```

**Artifact pin (7dcb4bc).** I recomputed every value myself, read only, with the repo's own `release-contract.mjs` (`productTree`, `artifactContract`) and `release-flow.mjs` (`gitEntries`) from `C:/Antigravity Projects/Worktrees/Books Arranger/cand-0222b`:
- The manifest SHA-256 is `3b7d1198…40128a`, over 57,748 bytes with no BOM. It matches the expected value.
- `version` is 0.22.2. `source_head` is 7dcb4bc1c621…. `build_id` is 6d611429-0003-4a2a-bfd3-d2f71cb7025c. `latest.yml` reads `version: 0.22.2`.
- `product_digest` `1db4b4fe…6303e` equals `productTree(ls-tree -rz --full-tree 7dcb4bc)`.
- `artifactContract(manifest, {version: '0.22.2', productTree})` accepts the manifest: three artifacts; payload `backend_version` and `shell_version` 0.22.2; `verified` and `installer_equivalent` true.
- Each artifact matches its manifest size and SHA-256:
  - `Books-Arranger-Setup-0.22.2.exe`: 174,204,825 bytes, `3ace03a087a014ae91eb0a4a556938e1c3728e7d0ff26b9fa4602b3b3a3e883a`. This is the expected value.
  - the `.blockmap`: 181,654 bytes.
  - `latest.yml`: 360 bytes.
- The `cand-0222b` checkout is at 7dcb4bc with a clean tree.

---

## Summary

0.22.2 adds the following:
- Ruling 35/37 queueing. Approve, Convert, Keep separate, Scan again, Remove from list, Remove this copy, Edit names Save and Forget, Start and Resume scanning, historical cleanup and restore go through `ActionQueue` and `Server.run_queued`. Delete recovery copies has its own queue in the retention worker. A Resume that is still settling is kept (`start_when_settled`).
- Edit names: `entered_names.py`, lasting corrections, "Applies to n books", and a names-stamp claim check in `AudioJobs`.
- The SQLITE_BUSY fixes: cache reads no longer expire (no write); `groups.presync` builds groups outside the write transaction; a busy catalog becomes a per-book wait.
- Ruling 29: `original_titles.py` and the gap-fill lane.
- The rating-only Xtra admission.
- Ruling 36: the evidence note is gone, and the refresh protection now keys on `manual_metadata_sources`.
- Updater fixes: M-1/W16, the approval stop and recovery hold for updates, and the first-run form flags.
- The identity changes in `local_identity.py`.

I read every product file in the diff, with depth on the eight red-team questions in the brief.

**Red-team answers, in brief:**
1. **Queued actions.** Every queued press runs the same engine call at run time, with the revision taken when it was pressed. Stale input is refused as `changed`. Delete, Remove this copy and recovery deletion re-check their confirmed file list or token. Cancel cannot race the run: the worker pops the head under the lock only after it re-checks `items[0] is head`, and `_claim_manual` runs under `_MANUAL_LOCK`. One gap: M4.
2. **The updater.** A failed spawn now keeps the app (the `autoUpdater.app.quit` override). The shell exits only after the installer process exists. A late engine exit during the lease close is deferred and handled; it can only fire while `quit === 'none'`, so never during an install. **W16 is fixed.** Cancel and the bound clear `_update_hold`. Queued waiting presses are dropped on update (Q1, as designed). I found no half-install path.
3. **Lasting names.** **Yes, one correction can rename the wrong books** (M1). Forget undoes its own press, but has two side effects (M2, m1).
4. **SQLITE_BUSY.**
   - The cache read no longer writes. Expiry moved into `cache_fetched`'s retried transaction, and expired rows are still never returned.
   - A busy book becomes "Waiting for source" for 60 s and the run goes on. Nothing is deleted or marked done falsely.
   - `presync` re-checks the revision and every input under `BEGIN IMMEDIATE` before writing. It falls back to the old in-transaction `sync()` when it is busy or the inputs moved. Sound.
5. **Xtra and rating boxes.** Both shapes are byte-exact:
   - The empty Xtra box is 8 bytes.
   - The rating box is exactly 53 bytes: one WM/SharedUserRating entry, type 0x0013, a value of 0 to 99.
   - At most one of the two, and only directly in moov/udta.

   The PCM proof is real: mdat and trak are untouched by construction. I also re-ran the three targeted tests in `test_inplace_m4b` (empty Xtra, rating Xtra, Xtra with content refused). They pass and compare decoded audio.
6. **Ruling 29.** There is **no automatic fallback** while a lookup never gets a final answer (M3). Sergei's Approve on the Held row is the only way out.
7. **Evidence removal.** The background refresh is still protected. It keys on a `manual_metadata_sources` row (Sergei's "Entered by you" values) or `metadata_actor == 'user'`, and the start-up migration back-fills rows for user drafts. Edit names entries are not part of this protection, and their key can be orphaned (m5).
8. **No new delete or move code.** The new product code has no unlink, rmtree, replace or move. Book delete changed only its refusal texts. The new `Сборники\<Series>\` path goes through `safe_name`, which strips separators and maps `..` to `_`.

---

## Rubric

### 1. Security

- Status: Pass
- Findings: none. Nothing new shells out. Electron `webPreferences` are unchanged (contextIsolation, sandbox, no nodeIntegration), and the new first-run flags only change `show`. New page code adds no `innerHTML`. No secrets.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - **M1 [Major]** `entered_names.py:56-58, 95`: a fix can rename the wrong books.
    - `_norm()` is `local_identity.words()`, which drops digits. So a whole-value title, series or universe fix matches any value in the same scope with the same letters.
    - Probe, confirmed: correcting King's book whose files read "01" to "Misery" also puts "Misery" in force for «1408» by the same author. Correcting "Книга 1" also renames "Книга 12".
    - The `relevant()` prefilter does not stop this, because "01" is a substring of nearly every path.
    - Those books would then be filed, tagged and named as another book. The audio is intact and nothing is overwritten (a name collision is refused). But the docstring promises "reads the same text", and the release itself special-cases digit titles («1408», «11.22.63»).
    - "Applies to n books" shows the count before Save, which is the only guard.
    - Fix direction: compare `_text()`/casefold for whole-value fixes. Never match an empty normalised value.
  - **M2 [Major]** `entered_names.py:78-88, 247-249`: setting a field back to the files' value brings back an older correction.
    - The set-back writes a `forget` of the newest entry only. `_live()` then drops it and the older entry for the same slot takes over again.
    - Probe, confirmed: titles saved in order "A", then "B", then the files' "Orig" leave "A" in force for the book.
    - The fix from press "B" stays live for the other books in scope.
  - **M3 [Major]** `public_research.py:1242-1249`, `gap_fill.py:166-176`, `original_titles.py:139-151`: ruling 29 says "if no English title can be found: use the Russian title and convert". A lookup that never reaches a final state has no cap and no age limit, so the book waits indefinitely. That happens when it is offline, when a source keeps answering `wait`, when it raises every time (`deferred` every 600 s), or when any one source stays closed with no catalog answer. The Brief's offline measurement had 513 books waiting this way. Sergei's Approve on the Held row ends the wait. Suggest falling back to the Russian title after N deferred attempts or an age limit (Sergei's call on N).

### 3. Crash / Stability Safety

- Status: Pass
- Findings: none. The new background threads poll, are daemon or bounded, and end on cancel, generation or closing: `_settle_then_start`, the 2 s retention re-look. `_claim`'s five-try loop ends in `gone` and the worker picks the job again. Nothing is lost.

### 4. Performance

- Status: Concerns
- Findings:
  - **m2 [Minor]** `entered_names.py:124-137` with `merge_service.py:2804`.
    - The names digest (`relevant()`) is a substring test on the raw source that ignores scope. So a Save whose fix source is short or common ("01") changes the digest of every pending job whose paths contain it.
    - At its claim, each such job is set aside ("needs attention"), re-researched, and automatic processing is started. It is churn on unrelated books, and it amplifies M1.
    - The "Applies to n" count is built differently: it uses `_fix_applies` over an `instr(evidence)` prefilter capped at 200, so it can differ from what is applied.

### 5. State & Data Safety

- Status: Concerns
- Findings:
  - **M4 [Major]** `web_server.py:459-466`: a queued Start or Resume scanning skips a guard the direct route keeps.
    - The direct route refuses while `merge_admissions` is non-zero (line 1294, "Pause audiobook work before starting a scan").
    - The queued path checks only automatic processing, the scan and `jobs_active()`. It cannot see other admissions, because its own worker holds one.
    - So a queued scan can start beside another request's Delete, Approve or Retry, or beside the retention worker's recovery purge.
    - The engine guards (`_no_scan`, delete under `group_lock`, the retention guard) catch the destructive cases today. But the invariant the route enforces is broken. Fix direction: refuse or wait while `merge_admissions > 1`.
  - **m3 [Minor]** `merge_service.py:2796` (`_names_take_back`): when an Approve with names is refused, it forgets only the live book and fix rows of its press. A `forget` row written by the same press (a field set back to the files' value) stays in force, so the refused Approve still leaves a change.
  - **m4 [Minor]** `web/app.js:788`: Save preview metadata answers "Candidate changed" by saving Sergei's values again on the new revision without a look. This is a draft-only save (approve false, no file effect). But it skips the revision guard, so values reviewed against one member set can bind to another.
  - **m5 [Minor]** `entered_names.py:50-53`: Edit names book entries are keyed on the exact member paths. A regroup that adds or drops a part leaves Sergei's saved title and series silently unused. The docstring says they "survive a regroup". They are also outside the refresh protection of item 7.

### 6. Input Handling

- Status: Pass
- Findings: none. `names_value`, `text_value` and `entered_names.check` bound every field (1000 chars, one line). `queue_press` validates exactly as the direct press does, and reads nothing from the engine while loading.

### 7. Maintainability (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **m1 [Minor]** `entered_names.py:271-287`: Forget pressed on a book that a fix reached also takes back the originating book's own correction, because it is in the same press and field. The docstring documents this, but Forget shows no "Applies to" count (`web/app.js:3052`). So from book B it silently changes book A.
  - **m6 [Minor]** Drift from the 0.22.1 queue vocabulary: `action_queue.py:144` still says "Only Retry, Repair and Delete book are queued", the `book_action` docstring is the same, and `NAMES_QUEUED` names only those three. Behaviour is still right, because the one-action-per-row refusal in `enqueue` covers the rest.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns
- Findings: the `entered_names` module docstring ("the same text") and the `book_key` claim ("survives a regroup") do not match the code. Both are filed under M1 and m5.

### 9. Build & Release Hygiene

- Status: Pass
- Findings: none.
  - package.json and package-lock.json move to 0.22.2 together (568712e), and the CHANGELOG has a 0.22.2 entry.
  - The gate lists the new suites, and `real-shell-update.test.mjs` is in the node list.
  - 7dcb4bc only changes PA-1's fake version to package version +1 patch.
  - The artifact pin is verified above.

---

## Verdict

- Total Critical: 0
- Total Major: 4
- Total Minor: 6

**Verdict:** RELEASE CLEAR

No Critical finding, and the safety floor is intact. Nothing in the range deletes or moves a file outside the checks it already had. M1 is the finding most likely to hurt Sergei's library: wrong names, not lost audio, and "Applies to n books" shows it before Save. I recommend fixing it first in 0.22.3, or before shipping if Sergei prefers.

| # | Sev | Dim | file:line | Finding | Fix direction |
|---|-----|-----|-----------|---------|---------------|
| M1 | Major | 2 | `entered_names.py:56-58, 95` | A digit-blind `_norm` makes a whole-value fix rename the wrong books ("01" fix renames «1408»; "Книга 1" renames "Книга 12") | Exact casefolded comparison for whole values; never match an empty normalised value |
| M2 | Major | 2 | `entered_names.py:78-88, 247-249` | Setting a field back to the files' value brings back an older correction; that press's fix stays live | Set-back retracts every book entry for the slot, or writes an explicit "files" entry |
| M3 | Major | 2 | `public_research.py:1242`, `gap_fill.py:166-176` | A ruling 29 wait has no automatic fallback when no final answer ever arrives | Convert under the Russian title after N deferrals or an age limit |
| M4 | Major | 5 | `web_server.py:459-466` | A queued scan start ignores other merge admissions, which the direct route refuses | Wait while `merge_admissions > 1` |
