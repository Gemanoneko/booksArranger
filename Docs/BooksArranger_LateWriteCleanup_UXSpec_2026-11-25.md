# Books Arranger 0.31.3: UX spec, the late-write clean-up (Judy, 2026-11-25)

Spec only. No code written. Builds on `BooksArranger_ProgressRows_Spec.md` (rows in "Audiobook jobs"), `BooksArranger_StuckLoad_UXSpec_2026-11-24.md` section 8 (the status-line parts) and the 0.31.3 decision log in the Brief (branch `ender/0.31.3-late-writes`, including commits `212a278` and `b589a86`, the temporary-file clearing). Numbers in mockups are examples.

## Sergei's rulings (2026-11-25)

Earlier the same day: clean all 115 books; clear the 2 temporary files; show a progress line during the clean-up (about 40 minutes). Then, on this spec's questions:

1. **"74 GB freed" stays in the done line.** Yes.
2. **A kept book keeps both files until a later version.** Enough: no try-again button, no advice to delete by hand.
3. **Reword the nine neighbouring hold reasons too.** Yes: section 5.2.
4. **Card «Сага теней» 1 and Hobb «Сага о живых кораблях» 2: retry.** Their three tries were used up by the NAS bug, not by the names. Once their temporary file is cleared, 0.31.3 gives each one fresh try at writing the English names. If it succeeds, the book leaves the held list. If it fails, the book stays as it is with the section 6 text. This overrides section 6's "leave" assumption.

## In brief

1. **During: one Running row** in "Audiobook jobs", the app's existing place for work with progress. Label "Removing old files", the book in hand, `42 of 115 books`, a bar, elapsed and ETA by the existing rules. No new surface, no new control.
2. **It counts books**, not files or GB: the 115 sent back for the clean-up, fixed at the start. A book counts as done when its old file is removed or when a check keeps both files. A kept book adds `· 1 kept` to the count.
3. **After: two plain parts at the end of the status line** for 1 hour: `110 old files removed, 74 GB freed` and `5 old files kept: a check failed`. They are the "N moved books found" pattern. A kept book stays visible for good in its own list entry.
4. **Thirteen hold reasons are reworded** (section 5): the four first asked about and the nine neighbours, in plain "old file" and "new file", with no "rewritten", "former", "identity", "bytes" or "alias". One of them stopped claiming "both files kept" when the new file is missing. The engine's prefix "Series recovery could not verify the files; remaining copies kept:" is not shown with any of them.
5. **The temporary-file clearing shows nothing when it works.** The 2 books it leaves held (Card, Hobb) show **The names could not be written; the audiobook is unchanged.** in place of the hold text that said "The file was kept", now false (section 6). The leftover-file proofs' failure reasons are worded there too.

## 1. What goes wrong without a line

Nothing on the page says the clean-up exists. In the code the resume loop that finishes the held books sets no progress (`series_backfill._pass` and `name_write._pass` set `self.progress` only for new writes), so the existing "Writing the series..." and "Renaming finished audiobook" rows would not appear, and the removal is the long part: about 235 GB read over the NAS. Forty minutes of NAS traffic with no sign on screen, and then a row that vanishes without a word, is the exact "static window" Sergei objected to in the progress-rows ask (2026-10-17).

## 2. During: the Running row

**Surface.** One row in `#jobs-rows` (Running activities), by the rules of the progress-rows spec: three fixed lines, fixed height, no layout jump (the area reserves room for 2 rows; this plus a conversion is 2). A new row kind (name for Ender, for example `late_cleanup`), placed in `WORK_ORDER` after `finished_check` and before `series`.

```
Removing old files: The Name of the Wind                         42 of 115 books
[##############################-----------------------------------------------]
Checking both files, then removing the old one.     12:40 elapsed - about 25 min left
```

With a kept book (section 4):

```
Removing old files: The Name of the Wind                42 of 115 books · 1 kept
```

| Part | Spec |
| --- | --- |
| Label (line 1 left) | **Removing old files**, then the title of the book in hand (existing subject rules: ellipsis, full text in `title`). Between two books the subject is empty and the row stays. Not "Removing originals": that is the source-file cleanup, a different job |
| Detail (line 1 right) | `{done} of {total} books` (existing `books` unit, `toLocaleString()`), then ` · {kept} kept` only when kept is 1 or more. Tabular figures, no wrap, never truncated |
| What `total` and `done` count | `total` = the books sent back for the clean-up, series writes and name writes together (115 on Sergei's catalog). Fixed once the retry has queued them; it never grows during the run. `done` = books settled: old file removed, or both files kept by a failed check. `kept` = the second kind. The 2 leftover temporary files are not books and not in any number |
| Bar | Determinate `<progress>`, `floor(done / total * 100)`, never 100% before the row ends (progress-rows spec 3). Settled, not removed, drives it, so a kept book never leaves the bar stuck short of full |
| Step text (line 3 left) | **Checking both files, then removing the old one.** One sentence; says what happens this second and that nothing is removed unchecked |
| Time (line 3 right) | Elapsed and ETA exactly as progress-rows spec 5 (ETA only from 10 s and 5%, moving average). No new rule |
| Tooltip (on the label, as the series row's `lookupTip`) | **These books still have their old file beside the updated one. The app checks both files, then removes the old one.** |
| Status line's first part | The row's own name, as for any single running row: `Removing old files: The Name of the Wind`. With two or more running rows: "2 tasks running" (existing) |

**It is main work.** While the row (or the Waiting item below) exists, the state is working or continues, never "All done" and never "Nothing running": the badge must not say finished while 40 minutes of work runs. Same standing as a series write or a rename.

**Pause does not stop it** (Brief: a begun write finishes through a Pause, `_may_finish`). The row keeps moving; with the queue paused the status line reads `Paused · Removing old files: ...`, as for any such work today. No Pause tooltip change.

**A quit or a crash mid-run.** The numbers come from the ledger, not from a counter in memory, so the next launch shows the same total and the same done count, and the row returns when the first book is in hand again. Elapsed restarts (existing rule: it counts from when the page first saw the step).

**Before it starts.** The retry begins about 2 minutes after the app starts. Until the first book is in hand there is no row, no countdown, no placeholder.

## 3. Waiting: a library scan is running

The books wait while a library scan runs (`_may_finish`: "A library scan is running", tried again every 60 s). A scan on a large library can be long, and a row that disappears for that time would look like the clean-up vanished. One item in the existing **Waiting** block (`#jobs-wait`), in the form of its neighbours:

```
Removing old files · 73 books
Waiting for the library scan to finish.
```

- `73 books` = the books still to do (total less settled), not the 115.
- Same tooltip as the row. No "Show in list" button (a count, not one book).
- Shown only while no book is in hand. When the scan ends the item is replaced by the row in the same update; the two never show together.
- Any other short wait (the catalog busy for a moment) shows no Waiting item: the row simply stays.

## 4. After: what it says when done, and what a kept book shows

Rows leave at once when their work ends (existing). A 40-minute job that ends with no word is the failure case, so two parts take over **in the same update** that removes the row, using the pattern of section 8.1 of the stuck-load spec ("N moved books found, new locations saved").

| | Removed | Kept |
| --- | --- | --- |
| Copy, several | **110 old files removed, 74 GB freed** | **5 old files kept: a check failed** |
| Copy, one | **1 old file removed, 612 MB freed** | **1 old file kept: a check failed** |
| Shown when | the count is 1 or more | the count is 1 or more |
| Size | existing `byteText` (1024-based, one decimal under 10, none from 10 up). Sergei's ruling 1: it stays | none |

- **Where.** The last parts of the status line, after "missing books removed", removed first, kept second. Example:

```
[All done] · 0 need attention · 1,506 converted out of 1,506 approved books · 110 old files removed, 74 GB freed · 5 old files kept: a check failed
```

- **Look.** Plain text like its neighbours: same size, colour and weight. No icon, not `--warning` (nothing for him to press), no notice box, no toast, no sound, no tray text, no window-title change. The kept part is a cue, not an alarm: the app refused to delete on purpose.
- **Never merged.** Two parts, each with its own count. A merged "110 removed, 5 kept" would hide the one number he may care about.
- **How long.** 1 hour after the last book settles, both parts, the same hour the "missing books removed" part gets: a cue he may need to see after coming back to the window. Not dismissible. Not carried into a later session. Hidden while the line reads "Last confirmed —".
- **All kept.** `115 old files kept: a check failed` alone (the removed part is hidden at 0).
- **Nothing to clean.** A catalog with no held books shows no row, no Waiting item, no part.
- **Announcer.** The line's own polite region, as for any part that changes. No extra announcement, no tooltip (not a control).
- **"Old file", not "old copy" or "old version".** "Copy" is the app's word for recovery copies (backups); "former audiobook versions" is a different cleanup step. "Old file" is Sergei's own word and the one in the existing "The old file in {folder} couldn't be removed."

**A kept book, everywhere it shows.**

| Place | What it says |
| --- | --- |
| The running row | `· 1 kept` after the count (live, so a run that keeps every book shows early) |
| The status line, after | `N old files kept: a check failed`, for 1 hour |
| Its entry in "Could not be renamed or moved" (Ender confirms a kept book is listed there) | The reason line reads **The old file was not removed.** instead of "The rename or move did not finish." That sentence is false for these books: the rename happened, the new file is in place and named. New cause key for Ender (for example `old_file_kept`) beside `did_not_finish` in `COULD_NOT_REASONS`. This line is the durable record; the status parts are only the cue |
| Technical details / the engine log | The specific reason of section 5 |

**No try-again button and no advice to delete by hand** (Sergei's ruling 2). A kept book keeps both files until a later version. The line says what is kept and why. In the existing partial-move line ("Delete it yourself.") the app knows which file is right; here three of the first four reasons mean it does not.

## 5. The hold reasons: thirteen sentences

These show only when a check fails (the old file is then not removed). All are one fact plus the outcome, in the house form of their neighbours ("The audiobook was moved meanwhile; the catalog is unchanged"). Screen sentences end with a period (as `COULD_NOT_REASONS` does); the stored form may omit it.

**What is unclear to Sergei, found in the four first asked about.**
- **"rewritten" and "former"**: two words for the two files that appear nowhere else on screen. He says old file and new file; so does the page ("The old file in...").
- **"verified identity and bytes"**: engine words. Plain: the file is not the one the app checked.
- **"does not name"**: "name" reads as file name. The check compares the catalog's entry (path, size, SHA-256) with the new file.
- **"or has another name"**: in the code a second hard link to the same file. On screen it reads as "was renamed". The cause he can act on is simply that the file changed.
- **"before the former file was removed"**: a sequence nobody asks about.
- **"kept" alone, or "both files kept"**: the subject is missing in one, and the other is **not always true** (the third check also fires when the new file is gone; then only the old file is left). Truth beats brevity.
- **The prefix.** The engine stores every hold raised in a write's resume as `Series recovery could not verify the files; remaining copies kept: ` + the reason. For a name write there is no series, "recovery" is the app's word for backups of originals, and "kept" is said twice. Shown with the prefix, the first sentence Sergei reads is wrong and misleading before the useful one starts.

### 5.1 The four first asked about

| # | Today | New |
| --- | --- | --- |
| 1 | The catalog does not name the rewritten file; both files kept | **The catalog does not match the new file; both files kept.** |
| 2a | The former file no longer matches its verified identity and bytes; kept | **The old file changed since the app checked it; both files kept.** |
| 2b | The rewritten file no longer matches its verified identity and bytes; kept | **The new file changed since the app checked it; both files kept.** |
| 3 | The rewritten file changed or is gone before the former file was removed; both files kept | **The new file changed or is missing; the old file is kept.** |
| 4 | The temporary file changed or has another name; kept | **The temporary file changed since the app made it; it was left in place.** |

- **2a and 2b are one sentence for each file, at both places that raise it.** The first check (`_protected`) already says "The old/new file no longer matches its verified identity and bytes" with no "; kept"; the NAS check (`_last_checks`) says "former/rewritten ... ; kept". Same meaning, two vocabularies. Both sites use rows 2a and 2b. "Changed since the app checked it" is the app's own idiom ("Original changed since checked").
- **3 drops "both files" on purpose.** It is true in every case the check covers.
- **4** is the app's own leftover from an unfinished update, not a book. The file's path and size go in the engine log line, not in the reason.
- **"Missing"** is the page's word ("Audiobook missing", "All files missing"), so row 3 uses it, not "gone".

### 5.2 The nine neighbours (Sergei's ruling 3)

| # | Raised when | Today | New |
| --- | --- | --- | --- |
| N1 | the old file has a second hard link (`_protected`) | The former file has another filesystem alias; kept | **The old file is also stored under another name; both files kept.** |
| N2 | the temporary file has a second hard link (`remove_owned`) | The temporary file has another filesystem alias; kept | **The temporary file is also stored under another name; it was left in place.** |
| N3 | old and new are the same file object | The old and new names identify the same file | **The old and new files are the same file; nothing was removed.** |
| N4 | the held folder is not the one recorded | The audiobook parent identity changed | **The book's folder changed since the app checked it; nothing was removed.** |
| N5 | the recorded old, new and temporary paths are not in one folder | The recorded series paths do not share their original parent | **The old and new files are not recorded in the same folder; nothing was removed.** |
| N6 | the removal ran and the old file is still there | Former-file disposition has not completed; copies kept | **The old file is still there after removal; both files kept.** |
| N7 | the old file is missing and the app never started removing it | The former file is missing without a removal receipt | **The old file is missing, and the app did not remove it.** |
| N8 | the temporary file is still there after its removal | The temporary file could not be removed | **The temporary file is still there after removal; it was left in place.** |
| N9 | the book was moved meanwhile and the new file cannot be withdrawn (`_withdraw`) | The catalog could not record the series; copies kept: The audiobook was moved meanwhile; the catalog is unchanged (The rewritten copy could not be removed) | **The audiobook was moved meanwhile; the catalog is unchanged. The new file could not be removed; both files kept.** |

- **N9 is a whole sentence, not the inner part.** Its wrapper "The catalog could not record the series; copies kept:" carries the same two faults as the prefix (series for a name write; "kept" twice) and is dropped. For consistency the success variant of the same path reads **The audiobook was moved meanwhile; the catalog is unchanged; the new file was removed.** (it says "the rewritten copy was removed" today). Here the new file is the extra one: the catalog still names the old, so the new is the one that goes.
- **N7 says who did not do it.** Only the "app did not remove it" half is knowable (no removal was ever started); it is the fact Sergei needs if he deleted it himself or something else did.
- **N8 and the "still there" lines (N6) state what was seen**, not a cause nobody can name.

### 5.3 Rules for all thirteen

- **No prefix, anywhere they are printed** (list entry, Technical details, log). **Do not edit the `RECOVERY_HOLD` constant**: the retry selects the 115 holds by matching the stored 0.31.2 text exactly (`_removal_retained`), so changing the constant would select none. Only new holds are written without it. A raw operating-system error that reaches the same `except` keeps whatever prefix Ender chooses; not specced.
- **No fix is named** (section 4).
- **Dependency.** `sorting_moves.NOT_MOVED_KEYS` finds the key `file_changed` by the phrase "no longer matches". Rows 2a and 2b no longer contain it; Ender moves the mark to "changed since the app checked" and its test. The key `tags_not_written` keeps working because section 6 keeps "The names could not be written". The page does not read `file_changed` today.

## 6. The temporary-file clearing, and the two books it leaves held

**Built** (`212a278`): after the proofs (the book's own file matches the catalog; the leftover's audio is byte-for-byte the book's; no other record names it; not written since the hold; one link; same file when reopened) the app removes the leftover temporary file of the two unfinished name writes: Orson Scott Card «Сага теней» 1 (612 MB) and Robin Hobb «Сага о живых кораблях» 2 (1.2 GB). **The hold stays**: their names were not written, and both books have used the rules' three tries. The code keeps the stored hold text as it was: "The names could not be written; the audiobook is unchanged: Safe removal of “{path}” could not be verified. The file was kept." After the removal its last sentence is false, and the rest is engine speech.

**A successful clearing shows nothing on the page.** Two app-owned leftovers, not books; no number that fits "N of 115 books"; nothing for Sergei to decide or check. It is the same call as the background sweep in section 8.1 of the stuck-load spec ("the app tidying its own leftovers; the engine log keeps its lines"). Not in `total`, `done` or `kept`, and in neither part of section 4. Engine log, one normal-level line per file: `Removed a leftover temporary file of an unfinished update: {title} ({size}): {path}`.

**What the two books show after the removal.** They stay where they are today, in "Could not be renamed or moved" (Ender confirms), with one sentence changed everywhere the hold is printed:

| Place | After the temporary file is removed | If a proof failed and the file stays |
| --- | --- | --- |
| Hold reason (ledger, Technical details, anywhere the page prints it) | **The names could not be written; the audiobook is unchanged.** | **The names could not be written; the audiobook is unchanged. A temporary file is still there: {path}** |
| Their entry in "Could not be renamed or moved" | The same sentence on the reason line, in place of "The rename or move did not finish." (that line is for an entry whose last try's cause is `tags_not_written`; no other entry changes) | The first sentence only |
| Status line, running row, Waiting, the parts of section 4 | Nothing. They are not among the 115 | Nothing |
| Why it was kept | not applicable | Technical details and the log: the sentence of the table below |

- **One sentence, two places.** The hold reason and the list line are the same words, so they cannot disagree. "The names could not be written" is the engine's own opening (`NAMES_FAILED`); keeping it keeps `tags_not_written` working.
- **Ender writes the new reason in the same `_set` that records the outcome** (`temp_removed` or `temp_kept`), never earlier: `_leftover_temporary` finds these two books by matching the old stored text exactly. The record keeps `temp_removed` (path, size, SHA-256, time), so the fact is not lost.
- **The original cause of the failed write is not known** (the second try overwrote it). If the record still holds it, Ender may append it after the sentence; the page does not invent one.
- **No button and no advice** (ruling 2 applies the same way). Sergei's question 1 below asks only whether 0.31.3 should try the names once more.

**The reasons a proof keeps the file** (record `temp_kept`; new strings of `212a278`, shown only when a check fails):

| Engine text today | New |
| --- | --- |
| Another record names the temporary file; kept | **Another record of the app uses this file; it was left in place.** |
| The catalog no longer names the book's own file; the temporary file was kept | **The catalog does not match the book's file; the temporary file was left in place.** |
| The book's own file does not match its record; the temporary file was kept | **The book's file changed since the app checked it; the temporary file was left in place.** |
| Atom layout changed / An atom other than the movie atom changed size / Track structure or sample tables changed / Media bytes changed (the four media-proof errors, shown raw) | **The temporary file's audio differs from the book's; it was left in place.** One sentence for all four; the exact error goes to the log |
| The temporary file was written after the app kept it; kept | **The temporary file changed after the app last handled it; it was left in place.** |
| The temporary file changed during the checks; kept | **The temporary file changed while the app checked it; it was left in place.** |
| The temporary file is still there after its removal | **The temporary file is still there after removal; it was left in place.** (the same sentence as N8) |

## 7. Ender confirms during implementation

1. A row for the new kind in `work.rows` with `subject`, `done`, `total`, `unit: 'books'`, a new integer `kept` (0 when none), `step_started_at` and `state`. Counts come from the ledgers (rows retried with `removal_retry`), summed across the series and name passes. The row stays from the first book to the last; it is removed in the same state update that first carries the outcome below.
2. A Waiting item of the same kind while a library scan holds the books: `count` = books left, a blocker for the scan. The label, subject and tooltip are the page's.
3. In `/api/state`, one object for the outcome, like `relinked` and `removed`: `{removed, kept, freed_bytes, last_age_ms}` (an age, not a timestamp). The page hides each part at 0 or from 3,600,000 ms (a named constant beside `REMOVAL_SHOW_MS`), and under "Last confirmed —". `freed_bytes` is the sum of the removed old files' recorded sizes.
4. Main-work standing for the row and the Waiting item, so the state never reads "All done" while either exists.
5. The thirteen sentences of section 5 at every place that raises them, without the prefix; the nine of 5.2 and the kept-file reasons of section 6 likewise; `old_file_kept` (or Ender's name) for the list entry of section 4.
6. Where each of these reasons reaches the page today. The could-not list prints only a key sentence, and I found no page element that prints a ledger reason. If they are in the ledger and the log only, they stay there, in these words.
7. Whether a kept book (section 4) is listed in "Could not be renamed or moved"; whether the 2 temporary-file books are listed there today and carry cause `tags_not_written`.
8. The new reason of section 6 is written in the same `_set` as `temp_removed` / `temp_kept`.
9. The two parts in `statusParts`, last, with the existing `plural` helper.

## 8. Noticed, not specced

- **Two counts for the same books.** `work.filing.left` ("Filing N finished audiobooks under the names found for them.", shown above 5) probably includes these books while their writes are active, and the "Moving" rows follow as each book's approved move runs. The numbers can differ (115 and 93) and each is true for its own job; the row's label says what it counts. Futaba looks at both together in check 8; Ender says if `left` double-counts a book that is mid-removal.
- **Two more strings in the same code, not reworded** (outside the thirteen and the section 6 table): "Not a series-update temporary file; kept" and "Not a name-write temporary file; kept". They fire only on a file the app never named, so no book shows them in practice. Offered if Sergei wants every string of this family done.

## 9. Checks for Futaba (seeded fixture library, nothing real, no real NAS; slow the removal with a stub so rows can be watched)

1. Seed about 12 held books with the 0.31.2 reason, start the app: for about 2 minutes nothing shows. Then the row: label, the book in hand, `0 of 12 books`, empty bar. Text exactly as section 2.
2. Counts rise; the bar moves; no ETA before 10 s and 5%; elapsed ticks. Rects: the toolbar rect is identical with no row, this row and this row plus a conversion row; row heights equal across ticks (progress-rows spec 8).
3. The status line starts `Removing old files: {title}`; the badge never reads All done or Nothing running while the row exists.
4. Make books fail: catalog mismatch (row 1), old file changed (2a), new file changed (2b), new file deleted (3), old file with a second hard link (N1), old file already missing (N7). Each keeps its files. The detail reads `· 1 kept`, `· 2 kept` and so on; the bar still ends at full; each reason reads exactly as sections 5.1 and 5.2, with no prefix, wherever it shows. Where a fixture cannot cause one (N3, N4, N5, N6, N9), Ender's engine tests read the exact string.
5. Last book settles: the row is gone and both parts show in the same update, no frame with neither. With 9 removed and 3 kept: `9 old files removed, {size} freed` then `3 old files kept: a check failed`. One of each: the singular forms. All kept: only the kept part. All removed: only the removed part.
6. After the part's hour (clock stub) both parts are gone; a relaunch inside the hour does not show them; under "Last confirmed —" neither the row nor the parts show.
7. A kept book's entry in "Could not be renamed or moved" reads "The old file was not removed." (or Ender reports it is not listed).
8. A library scan running: the Waiting item with the books left; the scan ends: the row replaces it; both never show together. Both numbers of section 8 are read together with the Moving rows and the filing notice.
9. Press Pause audiobook jobs mid-run: the row keeps moving; the line reads `Paused · Removing old files: ...`.
10. Quit mid-run, relaunch: same total, done count kept, the row returns.
11. Leftover temporary files, two seeded books held on `NAMES_FAILED` + the refused removal: after the pass the file is gone, no page text mentions it, one log line; both books' hold reason and list line read **The names could not be written; the audiobook is unchanged.** Seed one with a changed audio byte: the file stays and the hold reads the kept variant with its path; Technical details or the log carries "The temporary file's audio differs from the book's; it was left in place." Seed one with a second hard link: the file stays, the log carries N2.
12. Hover the row label: the tooltip of section 2, exact. Narrow width and 200% zoom: lines wrap, nothing overlaps, no horizontal scroll; no new tokens, no new control, no new hit rect.

## 10. Question for Sergei

1. **Card «Сага теней» 1 and Hobb «Сага о живых кораблях» 2 stay without their English names after the temporary files go (their three tries are used). Leave them until a later version, or let 0.31.3 try their names once more now that the files are gone?** Default in this spec: leave them (word: "leave" or "retry").
