# Code Review — Books Arranger v0.22.2

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-27
Tool: Books Arranger (Electron / Python)
Release: v0.22.2
Commit range: d50a05f9606af8a2fc08f55684b1b14340700e51..4b9fdba5ebf3a3825348e118b1b44918af9b9cca (tag v0.22.1 .. origin/main 4b9fdba, 42 commits: 36 reviewed in full up to 7dcb4bc, then the 6-commit delta 7dcb4bc..4b9fdba below)
Release source commit: 4b9fdba5ebf3a3825348e118b1b44918af9b9cca
Release artifact manifest SHA256: 9c7867859a47800b70c67844b66870bd4fe97b6cec5047bbc9b620497fe5c37d
Reviewed source: the main checkout at 4b9fdba (clean, read only). No worktree was needed.
Files changed: 101 files, +6613 / -538 (git diff --shortstat). Product code and scripts: 33 files, +3090 / -396. Tests: 62 files, +2850 / -139. Docs and CHANGELOG: 4 files, +670. package.json and package-lock.json: version only.
Method: LEAN (ProcessRules § Lean verification). I read the diff. I ran only the targeted tests behind the Xtra question and two throwaway probes behind M1 and M2. No suite, no mutation sweep.
Stand-down dimensions: none
```

**Artifact pin (4b9fdba, the final candidate).** I recomputed every value myself, read only, with the repo's own `release-contract.mjs` (`productTree`, `artifactContract`) and `release-flow.mjs` (`gitEntries`) from `C:/Antigravity Projects/Worktrees/Books Arranger/cand-0222c`:
- The manifest SHA-256 is `9c786785…5c37d`, over 57,747 bytes with no BOM. It matches the expected value.
- `version` is 0.22.2, and `package.json` at 4b9fdba reads 0.22.2. `source_head` is 4b9fdba5ebf3…. `build_id` is 4f1680bc-4970-4273-aa32-41970cd702cf. `latest.yml` reads `version: 0.22.2`.
- `product_digest` `9f79443e…67e33` equals `productTree(ls-tree -rz --full-tree 4b9fdba)`.
- `artifactContract(manifest, {version: '0.22.2', productTree})` accepts the manifest: three artifacts; payload `backend_version` and `shell_version` 0.22.2; `verified` and `installer_equivalent` true.
- Each artifact matches its manifest size and SHA-256:
  - `Books-Arranger-Setup-0.22.2.exe`: 174,204,274 bytes, `e19fefe1fcf747ff0c7f72144f8d18dcc96e8a09f66a51ef97b69f744cb4f4ab`. This is the expected value.
  - the `.blockmap`: 181,639 bytes.
  - `latest.yml`: 360 bytes.
- The `cand-0222c` checkout is at 4b9fdba with a clean tree.

**Superseded artifact pin (7dcb4bc, kept as history).** I recomputed every value myself, read only, with the repo's own `release-contract.mjs` (`productTree`, `artifactContract`) and `release-flow.mjs` (`gitEntries`) from `C:/Antigravity Projects/Worktrees/Books Arranger/cand-0222b`:
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

## Delta 7dcb4bc..4b9fdba

Six commits: faf2172 (M1, M2), 7b554fd (M4), 311014a (Futaba M-1; ruling 38), 3ee505b (Futaba m-1), 647b720 (ruling 39), 4b9fdba (Judy's copy). 25 files, +866 / -334; product code 11 files. Method: LEAN. I read the whole product diff. I ran only the delta's targeted suites: `test_entered_names`, `test_ruling35`, `test_identity_0222`, `test_original_title_wait`, `test_live_cases_0222` (71 tests, OK), `update-controller.test.mjs` (30 pass) and `test_original_title_frontend.js` (PASS). Each new test has a negative control or a before/after case in it.

**(1) M1, M2 and M4 are closed.**
- **M1, closed.** `entered_names._same()` (line 63) compares casefolded text with digits kept. An empty value never matches. `_word_fix` refuses a change whose numbers differ ("Том1" to "Том2" stays a whole value). The `_live` slot key uses `_same` too. The tests cover «01» against «1408», "Книга 1" against "Книга 12", and the "Applies to n" count.
- **M2, closed.** A field set back to the files' text now writes a `book` entry with scope `files` (`plan`, line 268). It is the newest entry for that slot, so no older value comes back. It also stops any fix from reaching that field of this book. It is never listed or "Entered by you". It also closes **m3**: a `files` entry is a live book row, so `_names_take_back` takes it back when the Approve is refused.
- **M4, closed.** `ActionQueue.blocker(..., held)` returns `operation` for a queued scan while `merge_admissions > held`. `run_queued` passes `held=1` both under the control lock and in its `ValueError` path, because the worker holds its own admission there. The worker's pre-admission look (held 0) and `blocker_after` (after `_release`) are right too.
- **M3** is closed by ruling 38 (the wait is gone; see 3).

**(2) Ruling 39.**
- **Never transliterates. Pass.** The name comes from a source only: FantLab `name_orig`, the Wikidata English label, or a Goodreads credit. Each is checked `script == 'latin'`. A CJK FantLab name with no Latin form fails that check and moves on to the next source. `surname_first` only reorders words. `compare_names` is used to match, never to make a name.
- **Uses the per-site limits. Pass.** Every request goes through `self.client.json` or `self.client.read` with research's own `stop` and `budget`. A closed source or a spent budget (`ResearchWait`) counts as inconclusive. So do a busy catalog and malformed evidence (`EvidenceConflict` is a `ValueError`).
- **Approve makes no request. Pass.** `approved()` sets the author state to `approved`, so `sergei` is true and the ruling 39 block (`not sergei`) never runs. `_answer_english_spelling` writes one local rule and calls `_continue_after_rule`, which only calls `requeue`. The only `research.lookup` caller is the automatic run thread.
- **Can a wrong match make a bad lasting rule? Yes, but it takes a two-key match.**
  - FantLab needs exactly one search hit by title and author, a work with exactly one author, and that author's name matching. Wikidata needs exactly one single-author work. Goodreads needs exactly one distinct Latin credit on results titled as this book.
  - A false hit is a same-titled work by a homonymous author. A "true" hit can also give a spelling Sergei would not choose (a middle initial, for example).
  - The rule is `same_as` for the credit, library-wide, actor `assistant`. Every not-yet-converted book of that credit then converts under it automatically, with no question.
  - Already filed books are not moved. Only the automatic run calls `lookup`, and `_continue_after_rule` skips books with jobs.
- **How is it undone? In practice, it isn't (M5).** The Brief names `retract_author_rule` as the undo. But no page calls `/api/author-rule/retract` (Brief, carried Minors: "no page uses it yet"; `web/app.js` has no caller). Sergei never sees a question for that author again. His only fix is Edit names on each book.
- **No loop.** If `_learn_author`'s write is swallowed as busy, the rules generation does not change. `changed_for` is then false, and nothing is put back. The automatic lock is an `RLock`, so `requeue` from the run thread is safe.

**(3) Ruling 38: no new indefinite wait. Pass.**
- The `original_title` wait is removed, with its table code, gap-fill lane, wake, `requeue` hook, Held listing and page copy. Nothing in product code still refers to them; only `translation()` is left.
- An inconclusive ruling 39 lookup returns an `author_unclear` ask with `wait: None`. That is a question with an Approve path, not a timed wait.
- The M4 scan wait lasts only as long as other admissions, which are per request.
- In the m-1 fix, Cancel after the park throws `cancelled`; the old engine restarts and the installer is never started. There is no `await` between that check and `phase: 'installing'`, so no late Cancel can slip in.
- Note (Sergei's ruling, not a finding): when a source is closed, the book gets the question instead of a later retry.

**(4) Nothing new deletes or moves a file wrongly. Pass.**
- The product diff adds no unlink, rmtree, replace, move, rename or child process.
- Futaba M-1 changes the destination only when Sergei typed or picked the author.
- Ruling 39 changes the destination of unconverted books by design. When the rule is wrong, the cost is wrong folder names (M5), not lost or overwritten audio.

**New findings in the delta**
- **M5 [Major]** `public_research.py:1661-1672` (`_learn_author`) with `web_server.py:1153`. A learned ruling 39 rule has no undo Sergei can reach. A catalog spelling that is wrong, or that he would not choose, files every not-yet-converted book of that credit under it without asking. `retract_author_rule` exists only as an HTTP route that no page calls. Fix direction: list the learned author rules with a Take back control (Judy specs it). Or show the learned spelling with its source on the first book it filed.
- **m7 [Minor]** `merge_service.py:2869-2890, 2962`. `_answer_english_spelling` saves Sergei's author rule and puts his other books back on the run before `_approval_result`. If that Approve is then refused (the path changed, or the destination is taken), the rule and the requeue stay. Edit names on the same Approve are taken back. His answer is probably still what he meant, so the impact is low.

**Status of the earlier findings:** M1, M2, M3, M4 and m3 are closed. m1, m2, m4, m5 and m6 are still open (`action_queue.py:144` still reads "Only Retry, Repair and Delete book are queued").

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

Open findings at 4b9fdba (the whole range, delta included):
- Total Critical: 0
- Total Major: 1 (M5)
- Total Minor: 6 (m1, m2, m4, m5, m6, m7)

Closed in the delta: M1, M2, M3, M4 and m3.

**Verdict:** RELEASE CLEAR

No Critical finding, and the safety floor is intact. Nothing in the range deletes or moves a file outside the checks it already had. The artifact pin above is verified for 4b9fdba. M5 is the open finding most likely to touch Sergei's library: wrong author folder names, never lost audio. I recommend a Take back control for learned author rules in 0.22.3.

| # | Sev | Dim | file:line | Finding | Status / fix direction |
|---|-----|-----|-----------|---------|---------------|
| M1 | Major | 2 | `entered_names.py:56-58, 95` | A digit-blind `_norm` made a whole-value fix rename the wrong books | **Closed** in faf2172 (`_same`, numbers kept) |
| M2 | Major | 2 | `entered_names.py:78-88, 247-249` | Setting a field back to the files' value brought back an older correction | **Closed** in faf2172 (a `files` book entry) |
| M3 | Major | 2 | `public_research.py:1242`, `gap_fill.py:166-176` | A ruling 29 wait had no automatic fallback | **Closed** in 311014a (ruling 38: no wait) |
| M4 | Major | 5 | `web_server.py:459-466` | A queued scan start ignored other merge admissions | **Closed** in 7b554fd (`blocker(held=1)`) |
| M5 | Major | 5 | `public_research.py:1661-1672`, `web_server.py:1153` | A wrong or unwanted learned ruling 39 author rule files every unconverted book of that credit, and no page can take it back | A Take back list for learned author rules (Judy specs it) |
| m7 | Minor | 5 | `merge_service.py:2869-2890, 2962` | The english-spelling rule is saved before the Approve that carries it can be refused | Save it after `_approval_result`, or take it back as names are |
