# Books Arranger 0.29.0: UX spec

Judy, 2026-11-17. For Ender. Source: Sergei's backlog "Backlog for the next version (2026-11-17)", items 1, 3, 4, 5, 7, 8. Items 2 (stuck cleanup) and 6 (restart intent) need no new spec; item 7 fixes how item 2's held row reads in the jobs panel.

Basis: read-only look at `web/index.html`, `web/app.js`, `web/load-state.js`, `storage_cleanup.py` (SAFE_LEFTOVERS), `organization.py`, and `Docs/BooksArranger_ProgressRows_Spec.md`. Nothing launched, no rects measured. Dark theme only. Copy follows the studio standard: short, specific, no memory.

## 0. One shared "check pass" (items 1, 3, 5)

Items 1, 3 and 5 are the same housekeeping pass over the catalog, so Sergei sees one behavior, not three.

| Trigger | Item 1: drop gone books | Item 3: re-check stale rows | Item 5: delete leftover-only folders |
|---|---|---|---|
| App start | yes | yes | yes |
| A scan finishes | yes | yes | yes |
| A library drive that was unavailable answers again | yes (Q4) | yes | yes |
| Window regains focus (at most once per 30 s) | no | yes | no |

Why focus re-checks rows only: Sergei deletes the clashing book in Explorer, then switches back. The row should clear within a second or two. Deleting folders on focus is not safe: he may have moved audio out of a folder for a minute.

Rule for Ender (red-team): a pass never decides from scan results. "Gone" means the book's own source path was tested and is absent while its library root answers.

## 1. Gone books leave at startup; unavailable drive keeps them

**Rule.** A book is dropped only when every source file or folder of the book is gone and the library root it lives in answers with content. A book with some files left stays as today ("Missing files", Convert what's there). A finished book whose originals the app itself removed is not a candidate for this (it stays as today).

**Startup.** The check is part of loading, before the list appears, so the list never shows ghosts. It is a named load step: `Step 4 of 5: Checking source folders`, then `Step 5 of 5: Loading your books`. The load strip's detail shows the count the strip already prints: `120 of 412 books`. A slow drive uses the strip's existing wait text (`Waiting for the source drive Z:\Audiobooks (4 s)`).

**Unavailable root.** The root does not answer, or answers with nothing in it (an empty library root is a failed mount until proven otherwise). Its books stay. Nothing is removed under it.

Where: a notice block `#library-notices` directly under the `Source 1: …` lines in the "Library scan controls" panel. That is where Sergei already looks to see which drives the app uses. One line per root, warning color, text carries the meaning (no color-only).

| State | Line | Control |
|---|---|---|
| Unavailable | `Z:\Audiobooks isn't available. Its 412 books stay on the list. Check that the drive is connected.` | **Check again** |
| Answers but empty | `Z:\Audiobooks answers but is empty. Its 412 books stay on the list. Check that the drive is connected.` | **Check again** |
| Checking | `Checking Z:\Audiobooks…` | button disabled (`aria-disabled`) |
| Still not | `Z:\Audiobooks still isn't available. Its 412 books stay on the list.` | **Check again** |

- Book count is the books under that root. If unknown: `Its books stay on the list.`
- Tooltip, Check again: `Check whether Z:\Audiobooks answers now. Nothing is removed while it doesn't.`
- Clears: the app re-checks by itself every 30 s while a line shows, and on Check again. When the root answers with content the line disappears at once (no "available again" line) and the pass runs for that root.
- More than 3 roots: first 3 lines, then `+N more`, full list in its `title`.
- Row side: while a root is unavailable, **Open source folder** on its rows says `Z:\Audiobooks isn't available. Check that the drive is connected.` instead of "Couldn't open … Check that this folder is available."
- `role="status"`, `aria-live="polite"`. No sound, no focus move. Button 96x32 minimum like the other row buttons.

**What Sergei sees when books are dropped.** One line under the notices, only when something was removed:

- `Removed 3 books whose files are gone. No files were touched.`
- With item 5 deleting folders in the same pass: `Removed 3 books whose files are gone. Deleted 2 source folders that held only leftover files.` ("No files were touched" is never printed when a folder was deleted.)
- Buttons: **Details** (quiet) opens a list, up to 10 lines `Title` then its path, then `+ N more`; **Dismiss**. Tooltips: Details `List the books and folders this pass removed.` Dismiss `Hide this line.`
- It stays until Dismiss or the next start. It does not announce itself repeatedly.

Red-team notes:
- A folder Sergei renamed in Explorer looks gone. The row drops, and the next scan finds the folder as a new book. Remembered names stay (they belong to the files); approvals do not. The Details list is how he finds out why. This is the reason for the line and the list.
- A NAS that mounts half-populated would drop good books. Q5 is the guard.
- Never one line per book; never a toast.

## 3. Stale rows clear when their error no longer applies

Applies to rows whose cause depends on the outside world. Spec'd case: **Name taken**. The pass re-checks them (section 0 triggers).

**What Sergei sees**
- The row leaves the list in place, instantly, no animation (the ProgressRows rule). `Needs attention · N` and the chip counts drop at the same moment, never before the row leaves.
- In the Needs attention view the existing strip line (`#retry-all-status`, under the chips) says why. That strip lives only in that view. Elsewhere the counts change and nothing else.
- One book: `«Неисповедимый путь 2» left this list: the name is free now. The book is checked again.` plus the existing **Show it** button (tooltip unchanged: `List this book: sets Status to All and searches for its title.`).
- Several books at once: `3 books left this list: their problem no longer applies. They are checked again.` No Show it.
- Cause clauses: Name taken `the name is free now`; anything else `the problem no longer applies`.
- If the cause changed to a different one, the row stays and its status text changes in place. No strip line.
- If the book was converted by automatic processing meanwhile, the existing "left this list: <status>" form is used.

**Never under his cursor.** A row stays until Sergei is done with it when its Edit names editor is open, it has unsaved edits, or it is the selected row with panel edits. Its status line becomes `The name is free now. This row leaves the list when you close this editor.` The counts keep it until it leaves. If a focused row leaves, focus moves to the next row's first control, else the previous row, else the **Needs attention** shortcut.

Tooltips: no new control. Show it unchanged.

## 4. Light novel checkbox

Mirrors Short stories by placement and wording, not by routing: Short stories changes the file name and the folder (`Сборники`); Light novel adds a top folder `Light Novels` in front of the usual hierarchy. Both boxes can be ticked (Q2). The Goes-to preview shows the result.

Label: **Light novel** (singular; names the book, like "Short-story collection").

**Place 1: Manual Conversion window** (asked). In Metadata, directly after the Short-story collection box, same `check` style.
- Tooltip: `Mark this audiobook as a light novel. Save As starts in Audiobooks Sorted\Light Novels.`
- Pre-ticked when the loaded source path has a folder named `Light Novels` (any case) below the library root. Line under the box (`field-help`): `Light novel from the folder name.` Untick is Sergei's value and wins on reload.
- Effect: stored with the draft like Short stories. While ticked and no export path is chosen yet, Save As opens in `<Audiobooks Sorted>\Light Novels\`. A path he already chose is never rewritten.

**Place 2: row Edit names editor** (needed: Q1). The pre-tick for scanned books has nowhere visible or undoable otherwise. Directly after **Collection of stories**, same `check ask-radio` markup.
- Tooltip: `File this book under Light Novels, then by author and series as usual. Use it for light novels.` (existing pattern: `File this book under Сборники. Use it for story collections by several authors.`)
- Pre-ticked from a source `Light Novels` folder. Line under the box, same style as "Series from the folder name.": `Light novel from the folder name.`
- Goes-to line and Place line follow the draft. Example: `Goes to Audiobooks Sorted\Light Novels\Ayatsuji Yukito\Иная\Иная - 1 - … - Ayatsuji Yukito.m4b`. The Place line gains a lead: `Light novel · Series: Иная · No. 1`.
- Saved like the other fields: `Entered by you: light novel.` and in Remembered `Light novel: «No» → «Yes»` (Yes/No like Collection). Applies-to count line unchanged.
- Finished book (already in Audiobooks Sorted): Save changes the record only. `Saved names for {title}. The finished audiobook in Audiobooks Sorted keeps its folder. Use Choose folder to move it.`

**Place 3 (Ender):** the details-panel Metadata form (`name="anthology"`) is the third home of Short stories. Wherever `anthology` exists, `light_novel` exists, same order. No extra copy.

Red-team: a pre-tick Sergei cannot see or undo is a trap; hence Place 2. The folder match is the exact segment `Light Novels`, never a substring (Q3 for `Ранобэ`).

## 5. Source folder removed when no audio is left; kept with a reason

Removed: the folder and only its SAFE_LEFTOVERS (images, `.txt .nfo .diz`, cue and playlists, checksums, `.log`, `.url`, Thumbs.db, desktop.ini, .DS_Store). Anything else keeps the folder.

**Where Sergei sees "kept".** On the book's existing **All files missing** row (status `All files missing`, hint `All 12 files are missing.`). The row stays while its folder is kept (Q7), so the reason has a place. Item 1 does not drop it, because the folder is not gone. Added below the existing `In <folder>` block, same style as that block (`path` lines, `+ n more`):

| Cause | Text |
|---|---|
| One file | `Folder kept because of Notes.pdf.` then `Delete that file and the app removes the folder on its next check.` |
| 2 to 3 files | `Folder kept because of:` then one `path` line per file |
| More | the 3 lines, then `+ 4 more, listed in the details panel.` |
| Subfolder or link | `Folder kept because it holds a subfolder: Extras.` |
| Directly inside a library folder | `Folder kept: it is directly inside a library folder.` (Q6) |

- Buttons unchanged: **Scan again**, **Remove from list**. Remove from list leaves the folder and files alone (existing copy: `Removed from the list. No files were touched.`).
- Details panel keeps the existing `Source folder retained — …` facts. This row line is the short form of the same fact.
- When the folder is deleted, the row leaves through the item 1 pass and the line in section 1 reports it (`Deleted 2 source folders that held only leftover files.`) with the folder paths and file names in Details.
- Tooltip: no new control.

Red-team:
- Pass timing (section 0): folders are deleted only at start, after a scan, or when a drive returns, never on window focus.
- Recommended for Ender: delete only a folder found audio-free by an earlier pass at least 10 min before. Sergei moving audio out of a folder for a minute must not cost him the covers.
- A folder whose listing fails is not deleted and not reported as kept; the drive notice (section 1) covers it.

## 7. Always say what is running

**Principle.** Every item is in exactly one of four states, and only one shows a bar.

| State | Bar | Elapsed | Word on the row |
|---|---|---|---|
| Running | yes, always (measured, else the sliding segment) | yes | the verb: `Converting`, `Scanning files` |
| Waiting | no | no | `Waiting`, then for what and until when |
| On hold | no | no | `On hold`, never the verb |
| Paused | frozen, muted | frozen | existing `Paused - <step>` |

Finding: today `updateActivity` hides the bar for `phase_only` rows (source-audio check, start checks, finished-book checks). That breaks "always show a bar". These rows get the sliding segment.

**Panel order.** Status line, Pause/Resume, Running rows, Waiting line, On hold rows, help text. Pause/Resume stay above the rows (ProgressRows rule). The Running list keeps its reserved height of 2 rows.

**Status line** (`#jobs-status`) starts with what is running, replacing the engine's state word:

| Situation | First part |
|---|---|
| One running row | `Converting: Dune` (that row's first line) |
| Two or more | `2 tasks running` |
| Nothing running, items on hold | `Nothing running · 1 on hold` |
| Nothing running | `Nothing running` |
| Paused | `Paused` |

The rest stays: `· 329 need attention · 12 converted out of 40 approved books`. A zero `0 queued` is omitted; otherwise `3 books waiting to convert` replaces `3 queued` (say what is queued).

**What each kind of work shows.** Label and subject on line 1, step on line 3, detail right of line 1. Existing rows keep their copy; new text in bold-free plain below.

| Work | Line 1 | Step (line 3) | Bar and detail | Where it also shows |
|---|---|---|---|---|
| Start-up | load strip | `Step n of 5: <step>` | segments, `120 of 412 books` | load strip only |
| Scan | `Scanning files` | `Reading files` | measured `N of M files`, else sliding | `#status`, `#current` unchanged |
| Research | `Researching books: <title>` | `<source> / <stage>` | `N of M books`, else sliding | `Research:` counts line unchanged |
| Conversion | `Converting: <book>` | `Step 3 of 4 - Encoding audio` | measured, existing | unchanged |
| Cleanup | `Removing originals: <book>` | existing step names | `12 of 40 files` | unchanged |
| Source folders | `Removing source folders` | `Checking leftovers` | sliding | section 1 line afterwards |
| Move | `Moving: <book>` | `Copying to <folder name>` | `45%` when the engine reports it, else sliding | row keeps `Moving the audiobook… 0:12 · 45%` |
| Queued action or bulk run (Retry, Repair, Delete, Approve, Retry all, Remove copy) | `<Action>: <book>` or `Retrying books` | `Working` | bulk: `12 of 80 books`; single: sliding | row keeps its own text |
| Check pass (section 0) | `Checking source folders` | `Checking 412 books` | `120 of 412 books` | shown only if it runs longer than 1 s |

The move and action rows are new row kinds. Order: conversion, cleanup, source folders, move/action, identity, series, scan/research, checks. Cap stays 4 rows plus `+N more running`.

**Waiting** is its own line under the Running list (not a row, no bar). Examples: `Waiting for metadata sources. Next try 14:05.` `Waiting for Z:\Audiobooks to answer.` `Waiting: Retry cleanup: Dune, Delete: Foo and 1 more. They run one at a time.` (queued actions are named here, not only counted).

**On hold.** A separate list `On hold` under Waiting (`<ul aria-label="On hold">`). The held item leaves the Running list, so the word "running" never sits beside it.

```
On hold
On hold: Похититель детей                                [ Show in list ]
Cleanup stopped. The app couldn't read one file's information.
```

- Line 1 is `On hold: <book>`, never `Removing originals`. Line 2 is the plain cause, not the engine's text. Mapped now: protected-file-identity read failure becomes `Cleanup stopped. The app couldn't read one file's information.` Any cause not mapped: `Stopped. See Needs attention.` (a reason over 80 characters or with line breaks is never printed, as today.)
- No bar, no clock.
- Button **Show in list** (quiet, 96x32 minimum) does what Show it does. Tooltip: `List this book: sets Status to All and searches for its title.` This is the one interactive element allowed in the panel's rows, because a pointer without a link costs him a search.
- 3 held at most, then `+N more on hold` that opens Needs attention.

**The three strings Sergei saw**

| Before | After |
|---|---|
| `Running · 0 queued · 329 need attention` | `Nothing running · 1 on hold · 329 need attention` |
| `Removing originals: Похититель детей` / `On hold — Cannot refresh protected file identity` | the On hold block above |
| `Stop automatic processing queued. It runs when the current action finishes.` | If it must wait: `Stop automatic processing queued. It runs when Converting: Dune finishes.` Otherwise it acts at once: `Stopping automatic processing…` |

Queued-line rule: the wait names the blocker. An unnamed blocker says `when the app is free` (Judy 14.6), never `the current action`. A held item is never a blocker.

Red-team:
- The seen Stop is likely stuck: the held cleanup counts as "the current action", so a Stop waiting for it never runs. Q8 asks to make Stop act at once; that is also the exit NN/g asks for.
- A running row whose detail has not moved for 5 min is shown as `No progress for 5 min` in the step line (warning). Elapsed ticking alone makes a frozen job look alive. Optional; Ender needs a progress timestamp.
- Two meanings of "queued" exist (conversion jobs, page actions). Section 7 words them differently.

## 8. Say plainly when only Sergei can move things on

Shown when all are true: nothing running, nothing waiting, no queued action, no retry check or timed retry scheduled, no books waiting to be checked, automatic processing not running or paused, and Needs attention is above 0.

Where: the Audiobook jobs panel, in the place of the idle line (the Running list's reserved area). It is the one place that answers "what is the app doing".

```
Nothing running.
Waiting for you: 329 books need attention. The app can't do more until you review them.   [ Review them ]
```

- First line plain text. Second line `--text`, 15px, with `Waiting for you:` in 600 weight.
- **Review them** (quiet, 96x32 minimum) does what the `Needs attention · N` shortcut does. Tooltip: `Show every book that needs you.`
- The count is the same number as `Needs attention · N`; one source.
- Not shown, and the existing line stays, when books are waiting to be checked: `3 books are waiting to be checked. Start automatic processing to check them.`; when automatic processing is stopped or paused with work left; when a retry or timed retry is scheduled (the app will act by itself).
- When Needs attention is 0 and nothing runs: `Nothing running` only.
- Not repeated in the automatic-processing block. Its `Automatic pass complete — 12 converted · 329 held` detail keeps its counts.

Red-team: do not say "nothing more can happen" while a cleanup retry or a 14:05 metadata retry is scheduled. Ender needs one engine flag (`needs_you_only`) so the page does not guess.

## Notes for Ender

- Data the page needs: per-root `available` and `empty`; per-root book count; dropped-book titles and paths; kept-folder reason with file names; held item cause code; blocker identity for queued waits; scan/research counts; move progress; `needs_you_only`.
- New strings to map: NAMES_LABELS `light_novel`; Place line lead; the `Check again` flow; the section 1 lines.
- Verify with measured rects (Futaba): `#library-notices` never overlaps Source lines or the scan controls at 1280/960/760/600 and 200% zoom, with a long Cyrillic path; no row rect intersects Pause/Resume; the On hold list adds height once, never per tick.
- Keyboard: Check again, Details, Dismiss, Show in list and Review them are plain buttons in tab order after their line. Focus is never moved by a pass.

## Open questions for Sergei (one word each)

1. Light novel box also in a row's **Edit names** editor (needed so the folder pre-tick can be seen and undone)? I specced yes. yes / no
2. May one book be both Light novel and Short-story collection? I allow both. both / one
3. Also pre-tick for a source folder named `Ранобэ`? yes / no
4. When a drive that was away answers again, drop its gone books then, or only at next start? I recommend then. then / start
5. If a pass would drop more than half of a library's books at once, ask first instead? I recommend yes. yes / no
6. Folders directly inside a library folder (such as `Z:\Audiobooks\Robert R. McCammon`) are never removed today. Keep that rule for item 5? keep / remove
7. Keep a book's "All files missing" row while its folder is kept for a non-leftover file, so it can say why? yes / no
8. Should **Stop automatic processing** always act at once and never wait behind another action? yes / no
