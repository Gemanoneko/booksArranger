# Books Arranger 0.30.0: UX spec

Judy, 2026-11-18 (revised the same day to match Ender's backend round, `a6cd33b` and `8a03ef9`). For Ender. Source: Sergei's ask (2026-11-18): "If there is a conversion (or any other job) running, I need to see all the running jobs with clear explanation of what they are and status bars." Follows 0.29.0 item 7 and the backlog bullet "Every running job visible, named, with a progress bar" (Ender's diagnosis).

Basis: read-only look at `background_work.py` (the `work` contract and `explain`), `web_server.py` (`state`), `web/app.js` (`renderJobs`, `checkActivities`, `renderActivities`, `waitingLine`, `queueHint`, `QUEUE_WORDS`, `pageBlocker`, `pressBlocker`), `web/index.html`, `web/style.css`, `merge_service.py`. Nothing launched, no rects measured. Dark theme only. Consistent with `BooksArranger_0.29.0_UX.md` section 7 and `BooksArranger_ProgressRows_Spec.md`; where this spec overrides them it says so.

## What Sergei saw, and what is already fixed

1. **Two clocks.** Conversion and cleanup rows came from a status snapshot that was seconds to minutes old; research and the queue were read fresh. **Fixed in the engine:** `work.rows` and `work.waiting` are read at every poll (lag under a second). Only the counts (need attention, converted, candidates) are still as old as the last full computation; `work.snapshot_age_ms` says how old.
2. **Hidden work.** One row per kind, 4 at most, the rest in an unlabeled `+N more running`; research hidden during a scan; a running queued action hidden behind a conversion; about 20 kinds with no row. **Fixed in the engine** (every job is a row with its own id). The page still hides them; this spec changes that.
3. **Wrong blocker name.** The engine said only `jobs`; the page turned every `jobs` into "the conversion". **Fixed in the engine:** `queued_actions[].blocker` is `{kind, cause, title, book_id, count}` with ten causes under `jobs`. The page still words it from a fixed table; this spec replaces that.

## Decisions in brief

- **The page draws `work`, nothing else.** It renders `work.rows` and `work.waiting` in the order the engine sends them (no page-side sorting, no rows built from the book list or the queue). The old `activities` field is not read.
- **Every running job gets a row with a bar. No cap, no "+N more running".** Row key is the job's `id`.
- **Waiting is a list**, not a sentence. Each item says what it is, what it waits for, and what Sergei can do.
- **One blocker sentence**, built in one function from the blocker object, used by the book row, the Waiting list, the queue strip, tooltips and dialogs.
- **Freshness cue** in the toolbar row, about the counts only. When the counts are 30 s old, they say `(as of 14:03:21)`. Rows are live, so they are never parked or hedged. A source the engine could not read is said plainly (`unread`).
- **Counts are split**: waiting conversions, paused or waiting cleanups and waiting actions are separate numbers, never one.

## 1. One panel, every job

### 1.1 Order (top to bottom)

```
Audiobook jobs
Converting: Dune · 3 books waiting to convert · 1 action waiting · 329 need attention · 12 converted out of 40 approved books
[ Pause audiobook jobs ] [ Resume audiobook jobs ]                  Counts updated 24 s ago
 Converting: Dune                                      1:12:05 of 11:03:40 audio
 [#######-------------------------------------------------------------------]
 Step 3 of 4 - Encoding audio                                      2:14 elapsed
 Researching books: Foo                                              4 of 30 books
 [###-----------------------------------------------------------------------]
 Example source / searching                                        0:41 elapsed
Waiting
 Retry cleanup: Похититель детей                                  [ Show in list ]
 It runs when the whole conversion queue (5 books) finishes.
On hold
 ...unchanged from 0.29.0...
```

Status line, toolbar (Pause/Resume plus the freshness cue), the `unread` line when it applies (3.3), Running rows, Waiting list, On hold list, Waiting-for-you block (when nothing runs), help text. Pause/Resume stay above the rows and never move. The Running list keeps its 2-row reserved height (about 136 px); rows 3 and up grow the panel once each (about 75 px per row), as already accepted (ProgressRows 8). Rows and items appear and disappear instantly, no animation.

**Supersedes:** 0.29.0 section 7 "Cap stays 4 rows plus `+N more running`" and "Waiting is its own line (not a row)"; ProgressRows 6 "Max 4 rows" and "Row identity is `kind`"; the page's own `activityOrder` and `priority` sort.

### 1.2 States and bars (unchanged principle, extended)

| State | Bar | Elapsed | Shown in |
|---|---|---|---|
| `running` | always. Determinate when the engine reports `done`/`total`/`fraction`; otherwise the sliding segment | ticks | Running list |
| `pausing` | keeps moving; step starts `Pausing - ` | ticks | Running list |
| `paused` | frozen, muted | frozen | Running list |
| Waiting item | none (nothing moves) | none | Waiting list |
| On hold | none | none | On hold list |

"Sliding" means: work is happening, the amount is unknown; the ticking elapsed time is its proof of life (ProgressRows 3). A sliding row never prints a made-up percentage. A determinate row's detail says the unit (`12 of 40 files`). A row with no amount but a `count` prints the count as its detail (`3 books waiting`, `5 books left`, `12 files`) and keeps a sliding or frozen bar.

### 1.3 How many rows show at once: all of them

- Every running, pausing or paused job has its own row. No folding, no `+N more`.
- Order is the engine's: fixed by kind (the `KINDS` order, table 1.5), then oldest first inside a kind, with a paused row after the running ones of its own kind. Never reordered by progress. The page does not sort.
- Expected in daily use: 2 to 4 rows. Plausible worst case: about 8.
- Defensive only: the Running list gets `max-height: 600px` (8 rows) with `overflow-y: auto` and a visible scrollbar, `role="region"`, `aria-label="Running activities"`, `tabindex="0"`. Beyond 8 rows the status line still counts every task (`work.counts.tasks_running`, `11 tasks running`). Many paused cleanups (the engine lists every started one) can reach this; the status line then says `Cleanup paused for 12 books` (section 4). Futaba force-feeds 12 fake rows to check it.
- Status line first part, 2 or more running: `3 tasks running`. This replaces the current `Converting: Dune and 2 more` (an unlabeled count, the same flaw as `+N more`). With no cap the count is exact and every task is on screen below it.

### 1.4 Which work gets a row: all of it, after 1 s

- **Rule:** the page draws a row once `now - started` is 1 s or more (the 0.29.0 rule for the check pass, now for everything). The engine always sends `started` (its own start, or the first poll that saw the row). Shorter jobs never show. This is the only exemption; no kind is exempt in principle.
- **One exception:** a row that a waiting sentence names as its blocker is drawn at once, so the sentence never quotes a row that is not on screen (acceptance check 3). Example: a queued scan that waits for `Checking source folders` shows that row even in its first second.
- Kinds that in practice rarely reach 1 s, so rarely show: saving one name or choice, Approve, Remove from list, Keep as separate books, `drive_check` on a healthy drive, the start check on a short queue. Why no row: a flash of 0.3 s is noise, and the book row already says `Saving…`. If one of them is slow or waits in the queue, the rule gives it a row or a Waiting item with no special case.
- **Never rows, because they have another home:** start-up loading (the load strip), and a press's own `Pending…` face for up to 3 s (the ladder).

### 1.5 Running rows: every kind

Line 1 is `Label: subject` and the detail on the right; line 2 the bar; line 3 the step on the left and the elapsed time on the right. The first column is the engine's `kind` (`label_key` when it differs); the table is in the engine's order. The engine sends step keys, never copy: the page words every label and step below. Existing copy stays unless marked **new** or **changed**.

| Kind / label_key | Work | Label: subject | Step line | Bar and detail |
|---|---|---|---|---|
| `conversion` | Conversion | `Converting: <book>` | `Step 3 of 4 - Encoding audio`; a damaged part: `Step 1 of 4 - Repairing a damaged part` (section 9) | audio seconds, else `fraction`; repairing: `1 of 2 parts` |
| `chapter_check` | Chapter check (every book, not the current page only) | `Checking source audio: <book>` **changed** | `Checking the complete audio before fixing the last chapter's end`; `step_text` (the file name) goes in the tooltip | sliding = reading the audio |
| `cleanup` | Cleanup, one row per book. Other books' started cleanups are `paused` or `pausing` rows | `Removing originals: <book>`; other phases `Cleaning up: <book>` | running `Removing original files`; paused `Paused - Resume audiobook jobs to continue` **new**; pausing `Pausing - Removing original files` | `12 of 40 files` for originals and recovery copies, else sliding; a paused row is frozen at its count |
| `queue` | Paused queue with books waiting | `Conversion queue` **new** | `Paused - Resume audiobook jobs to continue. Next: Dune.` (pausing: `Pausing - 3 books waiting.`) | frozen, muted, no fill; detail `3 books waiting` (`count`; the queue has no total) |
| `source_folders` | Source folders | `Removing source folders` | `Checking leftovers` | sliding = reading folder contents |
| `move` | Move | `Moving: <book>` | `Copying to <folder>` when the page knows the target, else `Copying the audiobook to its new folder` | `45%` (`percent`), else sliding |
| `move_recovery` | Unfinished-move recovery | `Finishing interrupted moves` **new** | `Finishing moves the last restart interrupted` | sliding (the engine has no count) |
| `action` (`label_key` = the action) | A queued action now running. Never hidden by a conversion or cleanup row | `<Action>: <book>` | table 1.5a | sliding; detail `count` where sent (Delete: `12 files`) |
| `bulk` (`retry_all`, `retry_selected`) | Retry all, Retry selected | `Retrying all books` / `Retrying selected books` **changed** | `One book at a time` | `12 of 80 books` |
| `start_check` | Start or Resume check | `Checking books before conversion` **changed** (was `Checking pending audiobook work`) | `Checking each waiting book is ready to convert`; pausing `Pausing start checks…` | `N of M books` when counted, else sliding = reading the queue |
| `retry_check` | Retry check | `Checking retry: <book>` **new** | `Checking this book can be converted again` | sliding = reading the book |
| `maintenance` | Check before cleanup | `Checking audiobook before cleanup: <book>` **changed** (was `Checking finished books`) | `Checking the finished audiobook before removing originals`; stopping `Stopping finished-book checks…` (the engine's own `step` sentence is not shown) | sliding = reading the output file |
| `finished_check` | Re-check of finished books | `Re-checking finished audiobooks` **changed** (had the same label as `maintenance`) | `Checking each finished file is still the right one` | `N of M books` |
| `series` | Series update | `Metadata: Updating series: <book>` | `Looking up the series` / `Writing the series into the audiobook` | `N of M books` |
| `gap_fill` | Optional-field lookups | `Looking up book details: <book>` **new** | `Asking sources for the original title and full author name` | `N of M books` when counted, else sliding = waiting on a source |
| `lookup` (`find_metadata`) | Find metadata | `Looking up metadata: <book>` **new** | `Asking metadata sources` | sliding = waiting on a source |
| `decisions` (`decision_<action>`) | A saved decision being applied | `<Decision label>: <book>`, table 1.5b **new** | `Applying your answers` | sliding |
| `repair_check` | M4B repair checks | `Checking M4B for repair: <book>` **new** | `Reading the M4B file to see if it needs repair` | sliding; detail `5 books left` (`count`) |
| `recovery_delete` | Deleting recovery copies | `Deleting recovery copies: <book>` **new** | `Removing the temporary copies of the original files` | sliding |
| `regroup` | Regrouping | `Regrouping split books` **new** | `Putting a folder's files back into one book` | sliding (no count) |
| `scan` | Scan | `Scanning files: <library>` | the file being read | `N of M files`, else sliding |
| `research` | Research (its own row, also during a scan) | `Researching books: <book>` | `<source> / <stage>`; stopping `Pausing - …` | `N of M books`, else sliding |
| `discovery` | Automatic processing, finding books (only when no scan runs) | `Automatic processing: finding books` **new** | `Reading the library folders for new books` | sliding = reading folders |
| `source_check` | Check pass (0.29.0) | `Checking source folders` | `Checking 412 books` | `120 of 412 books` |
| `drive_check` | Drive probes | `Checking drives` **new** (the engine sends no path) | `Waiting for the drives to answer` | sliding = waiting for a drive |

**Page-owned rows (assumption A9).** The engine keeps no record of `Approve selected` and `Let the app handle selected`: they are loops in the page. The page draws their rows itself from its own run state (the same clock as the press that started them): `Approving selected books` and `Handing selected books to the app`, step `One book at a time`, `N of M books` when the page counts, else sliding. They are placed after the `bulk` row. They exist so the sentence `It runs when Approving selected books finishes.` has a row above it.

**No row, and nothing to build (gap G2).** `Find local covers` and `Check metadata` presses: the engine keeps no record, so the panel cannot show them. Sergei still sees the pressed book's own `Checking…` text. Sergei accepted this (2026-11-18, answer 7; Question 6).

**1.5a Step line of a running queued action** (`action` rows). Where the book row already has a running sentence, the step line uses the same words (one string, two places). Defaults:

| Action (`label_key`) | Step |
|---|---|
| `cleanup` (Retry cleanup) | `Rechecking the audiobook and recovery copies` |
| `retry` | `Checking this book can be converted again` |
| `repair` | `Checking the audiobook file for repair` |
| `delete`, `copy` (Delete, Remove this copy) | `Deleting files`; detail `12 files` when `count` is sent |
| `approve` | `Saving the approval` |
| `convert` (Convert what's there) | `Queuing the files that remain` |
| `separate` (Keep as separate books) | `Splitting the folder into separate books` |
| `scan_again` | `Reading this book's files again` |
| `dismiss` (Remove from list) | `Removing this book from the list` |
| `names`, `names_forget` | `Saving the names` / `Forgetting the saved names` |
| `join` (Join into one book, section 8) | `Joining 5 books into one book` (`count` = parts). Label `Join into one book: <title>`; Waiting label the same |
| `destination`, `move`, `scan_start`, `scan_resume` | their own rows (`move`, `scan`) |

**1.5b Saved decisions** (`decision_<action>`; actions are the engine's: names, approve, review, tracks, metadata_choices, file_review). The same label names the row while it applies and the Waiting item while it waits (1.6).

| Key | Row label | Waiting label |
|---|---|---|
| `decision_names` | `Saving names` | `Save names` |
| `decision_approve` | `Saving approval` | `Approve` |
| `decision_review` | `Saving review` | `Save review` |
| `decision_tracks` | `Saving track review` | `Save track review` |
| `decision_metadata_choices` | `Saving choices` | `Save choices` |
| `decision_file_review` | `Saving file review` | `Save file review` |

An unknown action key reads `Saving your answers` / `Save your answers`.

**Fix for hidden research, hidden action and the 4-row fold:** all are engine-side and done (`background_work`); the page must stop dropping duplicates by kind in `renderActivities` and stop suppressing the `action` row in `checkActivities`.

### 1.6 Waiting list

`<p class="jobs-hold-heading">Waiting</p>` and `<ul aria-label="Waiting">`, same look as On hold. No bar, no clock. Each item: line 1 `label: subject` (label 600 weight), line 2 the plain wait, **Show in list** where there is a book (96x32 minimum). Order is the engine's (`WAITING_KINDS`). Every item shows, with one exception (waiting cleanups, below).

| Kind / label_key | Line 1 | Line 2 | Button |
|---|---|---|---|
| `action` | `Retry cleanup: Похититель детей` | `{ahead}{blocker sentence}` from section 2 | Show in list |
| `conversions` (queue not paused) | `Waiting to convert: 3 books` | `Next: Dune. They convert one at a time.` (the book list has the others) | none |
| `cleanup` (one per book, not started) | `Cleanup waiting: <book>` | `Waiting for the output checks.` | Show in list |
| `retry_checks` | `Retry checks: 3 books` | `They run one at a time.` | none |
| `cleanup_retry` | `Retry cleanup: <book>`; with a key: `Retry cleanup of working files: <book>`, `...of temporary files: <book>`, `...of the source folder: <book>` (`cleanup_retry_working`, `_temporary`, `_folder`) | `The app tries again by itself at 14:12.` (`at`) | Show in list |
| `recovery_delete` | `Delete recovery copies: <book>` | `It runs after the deletion before it.` (the existing `RECOVERY_WAITS` line) | Show in list |
| `decisions` (`decision_<action>`) | `Save names: <book>` (table 1.5b) | `Your answers are recorded. They apply one at a time.` | Show in list |
| `metadata_sources` | `Metadata sources` | `3 books wait for a source to answer. Next try 14:05.` (`count`, `at`; omit a part that is null) | none |
| `drive` / `drive_empty` | `Drive not answering: Z:\Audiobooks` / `Drive answers but is empty: Z:\Audiobooks` | `Its books stay on the list. Check that the drive is connected, then press Check again in Library scan controls.` | none |
| `resume` | `Resume audiobook jobs` | `It starts when the pause finishes.` | none |
| `automatic_start` (no blocker object; the page reads `start_pending.kind`) | `Start automatic processing` | `conversion`: `It starts when Converting: Dune finishes or is paused.` (quote the one conversion row; else `when audiobook conversion finishes or is paused`). `scan`: `It starts when the library scan ends or is stopped.` `stopping`: `It starts when automatic processing has stopped.` | none |
| `automatic` (`automatic_conversion`, `automatic_waiting`) | `Automatic processing` | conversion: `Waiting for audiobook conversion to finish. It continues by itself.` waiting: `Waiting between tries. It continues by itself.` | none |

- **Waiting cleanups, the one cap.** The engine lists up to 100 waiting cleanups, and a NAS backlog can hold hundreds. With 5 or fewer, each is its own item. With more, one grouped item replaces them: line 1 `Cleanup waiting: 40 books` (`work.counts.cleanups_waiting`, the full number), line 2 `Next: Foo. They run one at a time.`, button Show in list for Foo. This is a labeled summary, not `+N more`. The book a blocker sentence names (`cleanup_waiting`) is always the first waiting one, which is the `Next:` book.
- A paused queue is not a Waiting item; it is the `queue` row in the Running list, with the Resume instruction.
- Tooltip, Show in list on an `action` item: `List this book: sets Status to All and searches for its title. Its row has Cancel.` Other Show in list buttons keep the 0.29.0 tooltip.
- Keyboard: Show in list is a plain button in tab order after its item. A refresh never moves focus.
- An item that expires (a timed retry that fires) becomes a Running row at once, never both.
- **No "lost on restart" note.** Sergei answered Question 4 "remember" (2026-11-18): the app keeps queued actions across a restart (Ender's work), so no note is built.

## 2. Waiting wording: name the blocker

### 2.1 One builder

One function builds the sentence from the engine's blocker object. Every site below uses it; no site words a blocker itself. Names come from the blocker object (`title`, `count`), never from a lookup in the page's book list.

Blocker object (built): `{kind, cause, title, book_id, count}`. For `jobs` the cause is one of `own_conversion`, `own_cleanup`, `conversion`, `conversion_queue`, `queue_paused`, `cleanup_running`, `cleanup_waiting`, `cleanup_paused`, `checking`, `unknown`; `operation` splits into `action`, `source_check`, `operation`; `retry_run` carries `count` (books left); the other kinds (`scan`, `automatic`, `book`, `loading`, `approve_run`) are their own cause. `title` and `book_id` are set for `conversion`, `cleanup_*` and `action`. A press the page itself holds (`pressBlocker`) has no engine object; the page builds one of the same shape.

Two sentence shapes:
- a wait that ends by itself: `It runs when {X} finishes.`
- a wait that does not end by itself: `It can't run while {X}.` and then what Sergei does.

Rule: when the blocker has a Running row in the same `work`, `{X}` quotes that row's label and subject, so Sergei can match the sentence to the row above it.

### 2.2 By blocker

| Cause | Sentence | What Sergei can do (appended, only if there is something) |
|---|---|---|
| `own_conversion` | `It runs when this book's conversion finishes.` | |
| `own_cleanup` | `It runs when this book's cleanup finishes.` | |
| `conversion` (one book converts, none waits; `title`) | `It runs when Converting: Dune finishes.` | |
| `conversion_queue` (`count` includes the running book; a cleanup waits for the whole queue, not one book) | `It runs when the whole conversion queue (5 books) finishes.` | |
| `queue_paused` (`count` = books waiting) | `It can't run while the conversion queue is paused (3 books waiting).` | `Press Resume audiobook jobs.` |
| `cleanup_running` (`title`) | `It runs when Removing originals: Foo finishes.` | |
| `cleanup_waiting` (`title`; Foo is a Waiting item, not a row) | `It runs after the cleanup of Foo, which goes first.` | |
| `cleanup_paused` (`title`) | `It can't run while the cleanup of Foo is paused.` | `Press Resume audiobook jobs.` |
| `checking` (start or retry checks) | one check row shows: `It runs when Checking books before conversion finishes.` / `...Checking retry: Foo finishes.`; otherwise `It runs when the book checks finish.` | |
| `unknown` | `It runs when the app is free.` | |
| `action` (`title`: the running queued action) | `It runs when Delete: Foo finishes.` | |
| `operation` (another press holds the engine, unnamed) | `It runs when the app is free.` | |
| `source_check` (a scan waits for a check pass) **new** | `It runs when Checking source folders finishes.` | |
| `retry_run` (`count` = books left) | `It runs when Retrying all books finishes (12 books left).` (or `Retrying selected books`, from the `bulk` row's label) | |
| `approve_run` (page-owned row) | `It runs when Approving selected books finishes.` | |
| `book` | `It runs when this book's processing finishes.` | |
| `scan` | `It runs when the library scan finishes.` | `Stop scanning to run it sooner.` |
| `automatic`, running (the page reads `automatic_processing.phase`: discovery, research, conversion) **new, O-r2-2** | `It runs when automatic processing stops.` | `Press Stop automatic processing to run it now.` |
| `automatic`, between tries (phase `waiting`) **new, O-r2-2** | `It can't run while automatic processing waits between tries.` | `Press Stop automatic processing to run it now.` |
| `loading` | `It runs when Books Arranger finishes loading.` | |

- `automatic` replaces "It runs when the app is free" for a queued Start scanning or Resume scanning. That sentence was untrue while automatic processing sat between retries and the panel read `Nothing running` (O-r2-2). The panel now also shows the `automatic` Waiting item (`Waiting between tries`), so it no longer reads as idle while that wait stands.
- `unknown` and `operation` are fallbacks for a failed read or an unnamed press, never for a known cause. Futaba treats `It runs when the app is free.` as a defect when it shows for any other cause.
- `{ahead}`: `2 ahead. ` in front when the item is not first in the queue (the existing `, 2 ahead`; the same number in both places).
- Cancel is always possible and is not repeated in the sentence: the book row has its own Cancel beside the hint; the Waiting item's button tooltip says where it is.
- The `conversion_queue` row is the answer to the Brom case: a Retry cleanup behind one book's conversion with 4 more queued says `the whole conversion queue (5 books)`, not "the conversion".
- Tooltip (`title`) on the `conversion_queue` sentence: `Cleanup never runs beside a conversion, so it waits for every queued book.`

### 2.3 Where this one sentence is used (book row = Waiting line)

The text after `queued.` is the same string in both places.

| Site (current code) | New text |
|---|---|
| Book row hint, `queueHint` (4889-4900) | `Retry cleanup queued. {ahead}{sentence}` for every action; the `Starts when`, `Choices are waiting in memory…` and `until … finishes` variants fold into this one form (the memory note stays as a second sentence for Save names) |
| Retry button queued face, `retryQueueFace` (1951) | title `Retry cleanup is queued. {sentence}`; label and aria unchanged |
| Retry button before pressing, `retryBlockedTip` (1954) | `Queue this retry. {sentence}` (the sentence it would get now) |
| Waiting list (section 1.6) | line 2 |
| Queue strip `#queue-line` (2529) | one: `1 action waiting. {sentence}`. Several: `3 actions waiting, one at a time. First: Retry cleanup: Foo. {sentence}` |
| Page-held press, `laterLine` (4697) and toolbar tooltips | `Stop automatic processing queued. {sentence} Press it again to cancel.` |
| Scan start queued message (654) | `Start scanning queued. {sentence}` |
| Delete dialog (5113, 5118, 5052) | `{sentence without "It"}, so this delete waits its turn.` Example: `Converting: Dune is running, so this delete waits its turn.` Confirm tooltip: `Queue this delete. {sentence} The app checks the book and files again first. The app can't undo it.` |

Replace `QUEUE_WORDS`, `queueS`, `queueP` with the builder. `waitingLine()` is replaced by section 1.6.

## 3. Freshness

### 3.1 What is live and what is old

| Live (read at this poll) | As old as `snapshot_age_ms` |
|---|---|
| every row, every Waiting item, On hold, `work.counts` (tasks running, waiting conversions, cleanups waiting or paused, actions waiting, retry checks) | `N need attention`, `N converted out of M approved books`, `N book candidates found · M not approved`, the attention chips and the Needs attention shortcut count |

The page's own busy notice and `Last confirmed — ` prefix stay as they are, for the page not hearing the engine at all. They are not used for engine lag any more.

### 3.2 The cue

**Data.** `work.snapshot_age_ms` (age of the counts) plus `now - received` (so the page's own polling gap counts), and `work.refreshing` (a newer computation runs now). When `snapshot_age_ms` is null the cue stays hidden (the engine cannot tell).

**Cue.** `#jobs-fresh`, a span at the right end of the toolbar row (`margin-left: auto`), 13 px, `aria-live="off"`. Hidden while the page's own busy notice shows (no double warning).

| Age of the counts | Cue | The counts in the panel |
|---|---|---|
| under 10 s | nothing | normal |
| 10 to 29 s | `Counts updated 24 s ago`, muted | normal |
| 30 s or more | `Counts updated 45 s ago`, warning color (`2 min` from 120 s, `over 1 h` from 60 min). Text carries it; color is extra | each stale count says `(as of 14:03:21)`: the status line tail, the candidates line and the Waiting-for-you count. Chips and the shortcut carry no suffix (too narrow); the cue explains them |

- `Refreshing…` is added (`Counts updated 45 s ago. Refreshing…`) only while `work.refreshing` is true and the cue shows.
- Tooltip: `Need attention, converted and candidate counts were last computed at 14:03:21. The running jobs below are live.`
- The cue text changes once a second at most. The live status line changes only when a suffix appears or goes, never on the tick.
- Back under 30 s: the suffixes go at once, no message.
- Rows never park and clocks keep running: they are live, so a moving bar is true.

Example, 45 s behind: `Converting: Dune · 3 books waiting to convert · 329 need attention · 12 converted out of 40 approved books (as of 14:03:21)`.

Waiting-for-you block when behind: `Waiting for you: 329 books need attention (as of 14:03:21). The app can't do more until you review them.` The block still follows the engine's `needs_you_only`.

No Refresh button (not asked; the engine decides when to recompute).

### 3.3 A source the engine could not read (`work.unread`)

`unread` lists the sources whose rows are missing this poll (`jobs`, `checks`, `actions`, `workers`, `automatic`). The engine never invents them. The panel must not read as complete then.

- A line directly above the Running list, `#jobs-unread`, warning color, `aria-live="off"`: `Could not read just now: conversion and cleanup, queued actions. Some work may be missing below.` Names: `jobs` = `conversion and cleanup`, `checks` = `checks`, `actions` = `queued actions`, `workers` = `background lookups and repairs`, `automatic` = `scan and automatic processing`.
- Shown only when the same source is unread for 3 s or more (one failed poll never flashes).
- With no rows and a non-empty `unread`, the idle line is `Nothing running that could be read.` instead of `Nothing running`, and the Waiting-for-you block is hidden. An absence is not claimed while a source is unread.

## 4. The paused-cleanup miscount

Cause: `queued` in the jobs fields still adds the pending cleanups (waiting, checking, removing, pausing, paused) when no book converts. The page printed it as `N books waiting to convert` (`queuedPart`). Three paused cleanups plus one real conversion read as "4 books waiting to convert".

**Three numbers, three phrases.** The engine now sends them apart in `work.counts`: `queued_conversions`, `cleanups_waiting`, `cleanups_paused`, `actions_waiting`. The page uses only these; it never reads `jobs.queued` and never subtracts.

| Number | Phrase in the status line | Also shown as |
|---|---|---|
| `queued_conversions` | `1 book waiting to convert` / `3 books waiting to convert` | Waiting item `conversions`, or the `queue` row when paused |
| `cleanups_paused` | `Cleanup paused for 3 books` | one paused `cleanup` row each |
| `cleanups_waiting` | `Cleanup waiting for 2 books` | one Waiting item each (grouped above 5) |
| both | `Cleanup paused for 3 books, waiting for 2` | |
| `actions_waiting` | `1 action waiting` / `3 actions waiting` | one Waiting item each |

A zero is left out. Status line parts, in order: first part (1.3), books waiting to convert, cleanup phrase, actions waiting, `N need attention`, `N converted out of M approved books`, `N waiting for retry checks` (`counts.retry_checks_waiting`).

Before and after (the same data):
- Before: `Paused · 4 books waiting to convert · 329 need attention · …`
- After: `Paused · 1 book waiting to convert · Cleanup paused for 3 books · 329 need attention · …`

**First part when only cleanups wait:** `Paused` if any paused row exists and nothing runs; otherwise `Nothing running` plus its counts. `Running` is still never printed (0.29.0). Held cleanups (state needs attention) are not counted here; they are On hold and unchanged.

## 5. Other places this touches

- **Status line** `#jobs-status`: sections 1.3, 3, 4. The current `and N more` goes.
- **Idle and paused lines**: `Paused. Resume continues pending books.` is replaced by the `queue` row when books wait; with nothing waiting it stays.
- **Candidates line** `#book-candidate-counts`: takes the `(as of …)` suffix at 30 s (3.2).
- **Busy notice** (`busyPasses`, `Busy with: …`): reads `work.rows`, uses the same labels as the rows (`re-checking 12 finished books` becomes `Re-checking finished audiobooks`), and lists every kind running, not three kinds.
- **Automatic processing block** (`PENDING_NOTICE`): its start-pending sentence is the `automatic_start` line of 1.6 (names the conversion). Its own counts stay.
- **Book row queued hints and Retry face**: section 2.3.
- **Details panel**, Source cleanup status for a book with a queued Retry cleanup: same sentence as the row.
- **Delete dialog**: section 2.3.
- **Help text** `#jobs-help`: unchanged. A row whose work Pause does not stop (scan, research, lookups) keeps moving when Pause is pressed; the status line already says `Paused · Researching books: Foo` for that. No new copy.
- **ProgressRows spec**, "Decision in brief" and section 6: mark the 4-row cap, `+N more running` and kind identity as superseded by this document. Section 11 (data assumed from the backend) is replaced by the `work` contract in `background_work.py`.

## 6. Acceptance checks (Futaba)

Order is the replay of what Sergei saw, then layout.

1. **Replay.** Start a conversion with 4 more books queued. Press Retry cleanup on another book. Within one poll: the panel has the conversion row and a Waiting item `Retry cleanup: <book>` whose sentence reads `It runs when the whole conversion queue (5 books) finishes.`; the book row hint has the same sentence after `queued.`; the queue strip has the same sentence.
2. **Same text.** For each cause in 2.2, force the cause and compare the book row tail and the Waiting line tail as strings. Equal.
3. **Blocker has a home.** For every sentence that names a job, the same `work` has a Running or paused row for it, an On hold item, or (for `cleanup_waiting`) a Waiting item for that book. A page-held blocker (`Approving selected books`) has its page-owned row. A blocker row younger than 1 s is drawn anyway (1.4).
4. **All rows.** Run a scan, research, a conversion, a series update and a finished-book check together: 5 rows, none folded; the status line says `5 tasks running`.
5. **Scan plus research.** Both rows show at once.
6. **Action beside conversion.** A running queued action has its row while a conversion row shows.
7. **Counts.** Three paused cleanups and one queued conversion: `1 book waiting to convert`, `Cleanup paused for 3 books`, 3 paused rows, 1 Waiting item. Never `4 books`.
8. **Counts behind.** Hold `snapshot_age_ms` at 45 s. Cue reads `Counts updated 45 s ago` (warning); the status line tail, candidates line and Waiting-for-you count say `(as of …)`; a running row still slides and its clock still ticks (positive control: rows are live). At 9 s: no cue. With `refreshing` true at 45 s: `Refreshing…` added; false: not added.
9. **Unread.** Make `workers` unread for 3 polls: the `Could not read just now` line shows and an empty panel says `Nothing running that could be read.`; for 1 poll: neither shows.
10. **Backlog.** 100 waiting cleanups: one grouped item `Cleanup waiting: 100 books`, not 100 items; with 4: four items.
11. **Layout (measured rects, not impressions).** At 1280, 960, 760, 600 px and 200% zoom, with a long Cyrillic title: the toolbar rect is identical with 0, 1, 2, 5 and 12 rows; no row, Waiting item, the cue or the `unread` line intersects Pause or Resume; with 12 fake rows the list scrolls inside 600 px and the status line says `12 tasks running`; Show in list never overlaps its text; a tick changes no rect.
12. **Short jobs.** A job under 1 s never creates a row (no flash).
13. **O-r2-2 replay.** Automatic processing between tries, press Start scanning: the book strip, the Waiting item and the panel say `It can't run while automatic processing waits between tries. Press Stop automatic processing to run it now.`; the panel shows the `Automatic processing` waiting item and does not read as idle.

## 7. Saving an Author unclear book with no author (Futaba O-r3-2)

**Answered (Sergei, 2026-11-18, answer 6): leave.** Saving takes the book out of Needs attention, as today. Build the `leave` copy below; the `stay` branch is not built. Kept for the record:

Seen: **Save preview metadata** on an Author unclear row answers `Saved.`, the book becomes `Needs review` and leaves Needs attention, with the author still blank. It stays in All candidates. A book that still needs his author answer is no longer in the list that asks for it. This was a rule question (Question 5).

If the answer is **stay** (recommended):
- The row stays in Needs attention, in its Author unclear chip, until an author is entered. Counts do not change on Save.
- The Save line reads `Saved. The author is still blank, so this book stays in Needs attention.`
- When an author is entered and saved, the row leaves by the 0.29.0 item 3 rule (the strip line `«Title» left this list: …`).

If the answer is **leave**: the row leaves, and the Save line says it, so he is not surprised: `Saved. «Title» left Needs attention. Its author is still blank.` The row stays in All candidates with its author blank.

Futaba repeats the O-r3-2 repro (two edits: Light novel ticked; a Series typed) for the chosen answer.

## 8. Join into one book

Sergei (2026-11-18, backlog "Found 2026-11-18"): the app sometimes splits named parts of one novel into separate books. Real case: «Впусти меня», 5 single-file M4B parts, one shared album, tracks 1/5 to 5/5, each with its own part title. They list as series «Впусти меня» No. 1 to 4 plus «Впусти меня 5». He needs to select the wrongly split rows and join them. "Join" here means: record them as one book. The audio is joined later, when the book is converted (assumption A12).

### 8.1 Where it lives, and how he selects

In the bulk bar (`#batch-controls`), after **Let the app handle selected**: a quiet button `#join-selected`, **Join into one book (5)**. Same 96x32 minimum and the same wrapping as its neighbours.

- He ticks the part rows' checkboxes, or searches the album name and presses **Select this page** (the search narrows the page; the existing control). Selection across pages counts.
- The button shows as soon as one row is selected (so he can find it) and is disabled until the selection can be joined. The engine settles everything else when the dialog opens (8.3).

| Selection | Button | Tooltip |
|---|---|---|
| 1 row | disabled | `Select at least 2 books to join them.` |
| includes a finished audiobook (the page knows `rowFinished`) | disabled | `«Title» is already a finished audiobook. Join books that are not converted yet.` |
| 2 or more candidates | enabled | `Join the selected books into one audiobook. You choose the order, title and author first. Nothing is converted yet.` |

Works in every view where the checkbox column shows (All candidates, Needs attention, the chips). Rows may come from different folders: it is his explicit act (ruling 68 forbids the app splitting a folder, not him joining).

### 8.2 The confirm dialog

A modal `<dialog id="join-dialog">`, built like `approve-dialog`: Cancel has `autofocus`, Escape cancels, focus returns to **Select this page** (the Join button is gone by then). Enter in a field does not submit; only the button does. It opens at once and shows `Checking these books…` while the engine answers the preview.

```
Join 5 books into one book?
These files become one audiobook, in the order below. Nothing is converted until you approve it.
Your files are not touched.

Parts, in play order
 1  Впусти меня. Часть 1                 1 file · 4:12:03 · track 1 of 5   [Move up] [Move down]
 2  Впусти меня. Часть 2   Queued        1 file · 3:40:10 · track 2 of 5   [Move up] [Move down]
 3  Впусти меня. Часть 3   Repair asked  1 file · 3:02:44 · track 3 of 5   [Move up] [Move down]
 ...
Order from the album track numbers: 1/5 to 5/5. All 5 parts are here.

Title   [ Впусти меня                                       ]
Author  [ Lindqvist John Ajvide                            ]
Goes to Audiobooks Sorted\Lindqvist John Ajvide\Впусти меня - Lindqvist John Ajvide.m4b

What happens
 - 2 queued conversions are taken off the queue.
 - 1 Repair request is cancelled. The conversion repairs damaged parts itself.
 - Approvals on these books are removed. Approve the joined book when it looks right.
 - The series «Впусти меня» No. 1-4 on these rows is dropped. It came from the part names.
Damaged M4B parts are repaired automatically when the book is converted.
Each part keeps its title as a chapter name.

[ Cancel ]                                              [ Join into one book ]
```

- The part list is an `<ol>` in a `role="group"` with `tabindex="0"`; above 8 parts it scrolls inside the dialog (`max-height`), the buttons stay in view.
- A part line: position, its title (repaired text, ellipsis, full text in `title`), then `N files · h:mm:ss`, then `track n of N` when the tags say so, then a plain word when the part has something the join changes: `Queued`, `Failed`, `Repair asked`, `Approved`. Move up and Move down are 32 px high, plain buttons (no drag), as in Track order.
- Lines under "What happens" appear only when their count is above zero; there are at most 5 kinds, so nothing is folded.
- Buttons: **Cancel** (quiet) and **Join into one book** (default). While the preview is not back, or a refusal shows, Join is `aria-disabled` with the reason as its tooltip.

### 8.3 Part order

The page shows the engine's order and never reorders it after the dialog opens. Basis, strongest first, said in one line under the list:

| Evidence | Line |
|---|---|
| every part has an album track `n/N`, no duplicates | `Order from the album track numbers: 1/5 to 5/5. All 5 parts are here.` |
| same, but the album total is larger than the parts | `Order from the album track numbers. The album has 5 parts; part 3 is not selected.` |
| two parts claim one track (warning color) | `Two parts claim track 2. Check the order.` |
| every part has a number in its file name or title | `Order from the file names. Check it.` |
| nothing | `No order evidence. The parts are in file-name order. Check it.` |
| he moved a part | `Order set by you.` |

A missing part warns; it does not refuse. He may join what he has. After a Move, focus stays on the same button of the moved part (the Track order behaviour).

### 8.4 Resulting title and author

- **Title** is required. Proposed: the album shared by all parts (repaired text) when there is one; otherwise the words the part titles share once part numbers are dropped (`Впусти меня 5` and `Впусти меня` give «Впусти меня»); otherwise empty, and Join says `Type a title first.` (the existing refusal sentence).
- **Author** is optional. Proposed by the same rule that names a single book (shared credit, English name, surname first). If the parts name different authors it is empty with `The parts name different authors: A, B. Type the author.` If left empty the joined book is Author unclear and needs one before approval; the dialog says `No author yet. The book needs one before it can be approved.`
- **Series and number are cleared.** A series that came only from the part names is dropped (the line in 8.2 says so, and only when the rows had one). A series every part's own tags agree on is kept (assumption A14).
- **Goes to** follows the two fields, from the same preview as the Edit names editor.
- Tooltips: Title `The title of the joined book.` Author `The author of the joined book, as it is filed.` Move up `Move this part earlier in the book.` Move down `Move this part later in the book.` Cancel `Close without joining. Nothing changes.` Join `Join these 5 books into one book. Nothing is converted yet.`

### 8.5 Queued conversions, failed jobs, approvals and Repair requests

All or nothing: if any step cannot be done, nothing is joined (`Join cancelled: … Nothing was joined.`).

| A part has | Join does | Dialog line |
|---|---|---|
| a queued conversion (not started) | takes it off the queue; the record stays in history | `2 queued conversions are taken off the queue.` |
| a conversion or cleanup running now | waits: the join queues (2.2, `book`/`conversion`), so it is not refused as busy | the sentence, `so this join waits its turn`, and the button reads **Queue the join** |
| a failed job (Needs attention) | sets the failed job aside; its entry leaves Needs attention and the counts; the joined book is checked from the start | `1 failed attempt is set aside. Its entry leaves Needs attention.` |
| a queued Retry or Repair (action queue, not yet accepted) | cancels it | counted with the next line |
| an **accepted** Repair or Retry (the saved job waits next in line; no Cancel exists today) | withdraws it. Needs a new engine withdraw (Notes for Ender). The join does the repair itself when it converts | `1 Repair request is cancelled. The conversion repairs damaged parts itself.` (`2 Retry or Repair requests are cancelled…` for several) |
| an approval | removes it; the joined book is not approved | `Approvals on these books are removed. Approve the joined book when it looks right.` |

Why not leave the Repair on its part: the part stops existing as a book, and a second repair of the same file would race the join's own. Why not approve the joined book at once: the joined book still goes through its own checks (metadata, order, cover); approving hides a failure. Question 8 asks.

If an accepted Repair has already started (it is the running conversion), Join waits for it like any running conversion; it never aborts it.

### 8.6 After he presses Join

- The dialog closes. The selection clears. Focus goes to **Select this page**.
- The part rows leave the list; one row for the joined book appears. It is an ordinary candidate, not approved, in All candidates.
- `#join-status` (a `role="status"` span in the bulk bar, like `release-selected-status`) says what happened, with **Show it** (the 0.29.0 button, tooltip `List this book: sets Status to All and searches for its title.`):
  - `Joined 5 books into «Впусти меня». Approve it when it looks right.`
  - with effects: `Joined 5 books into «Впусти меня». 2 queued conversions taken off the queue. 1 Repair request cancelled. 1 failed attempt set aside.`
- Queued join (a part is converting): each part row shows `Join queued: «Впусти меня», 5 books. {2.2 sentence}` with **Cancel** (cancels the whole join; tooltip `Cancel the whole join. Nothing is changed.`). The Waiting list has one item, `Join into one book: Впусти меня`, with the same sentence and **Show in list** (first part). When it runs it checks every part again; a changed part ends it: `Join cancelled: «Впусти меня 2» changed. Nothing was joined.`
- While it runs: an `action` row in the jobs panel, `Join into one book: Впусти меня`, step `Joining 5 books into one book`, sliding bar (table 1.5a).
- Undo before approval: **Keep as separate books** (the existing action) on the joined book splits it again (assumption A15).

## 9. Manual conversion with a damaged part

The engine now repairs a damaged M4B part before joining it, in a manual conversion and in an automatic one. Sergei does nothing. The window says what is happening, in the words of the jobs panel (one string, two places: the manual job block reads the same `work` row).

| Moment | Manual Conversion window | Jobs panel and book row |
|---|---|---|
| Before queueing | a second sentence on the track count line, only when an included file is an `.m4b`: `Damaged M4B parts are repaired automatically when this book is converted.` (assumption A17: damage is found during conversion, not at load) | |
| Repairing | job block stage `Step 1 of 4 - Repairing a damaged part`; measure `1 of 2 parts`; bar fills by parts repaired, slides until the engine knows how many parts are damaged. The stage's tooltip names the file: `Repairing Впусти меня 3.m4b` | `Converting: <book>`, same step and detail (table 1.5 `conversion`, step key `repairing`, unit `parts`) |
| Paused while repairing | `Paused - Step 1 of 4 - Repairing a damaged part`. Resume starts that part's repair again (A19) | same |
| Repaired, conversion goes on | the stage moves to `Step 2 of 4 - …`. When the job ends, the status line adds `Repaired 1 damaged part.` and ` Original kept.` only when the engine says the originals are untouched | the book's Repaired list in its details (the existing `Repaired:` lines) |
| Cannot be repaired safely | status `Conversion stopped. Впусти меня 3.m4b is damaged and can't be repaired safely.` + ` Original kept.` (when true) + hint `Replace that file, then press Retry. Or press Reopen draft to leave it out.` **Retry** and **Reopen draft** show (existing buttons, existing tooltips) | Needs attention row with the same sentence |
| Repaired part failed its check | `Conversion stopped. The repaired part Впусти меня 3.m4b failed its check.` + ` Original kept.` + `Press Retry to try again, or Reopen draft.` | same |

- Plural: `Repairing 2 damaged parts` is not used; the detail `1 of 2 parts` carries the count and the step stays singular.
- An automatic book that is repaired shows the same step and the same Repaired list. The manual window is not special.
- A conversion the strict chapter check used to refuse (a last chapter that runs past its audio) is now repaired first; its refusal copy stays for the cases the repair cannot handle (the "Cannot be repaired safely" row).
- No new control. No sound, no focus move.

## 10. The "Book metadata" line

Today the line under the **Book metadata** heading in the details panel (`#source`, `app.js:734`; `app.js:740` before this round) prints `row.scope`: the internal grouping key, a path, a `\x1f`, then Album and Artist tags read as Latin-1 (cp1251 shows as garbage). It is never shown again.

**Two lines replace it** (candidates only; a file row still shows its path):

```
Book metadata
Z:\Audiobooks\Unsorted\Линдквист - Впусти меня
Kept as a separate book: each file names its own work. Album «Впусти меня», track 2 of 5.
```

- **Line 1, `#source` (path style): where the files are.** One folder: its path. Several: `Z:\…\first folder and 2 more folders`; the `title` holds every path, one per line. No folder known: the line is hidden.
- **Line 2, new `#source-basis` (field-help): why these files are one book, or a separate book.** One or two sentences from the table. Text is the repaired text (the engine sends it); quotes are `«…»`. A missing artist is left out, never `Unknown`.

| Engine `scope_view.kind` | Sentence |
|---|---|
| `album` | `Grouped by album «Впусти меня» and artist «Линдквист Йон Айвиде».` |
| `single_file` | `One audiobook file.` then the album sentence below |
| `volume` | `Kept as a separate book: {basis}.` then the album sentence, then `If these files are one book, select them and use Join into one book.` |
| `split_book` | `Parts of one book, grouped by the file names.` |
| `filename_work` | `Grouped by the file names: «Автор» - «Название».` |
| `numbered_set` | `Numbered files in one folder. The order comes from the file names.` |
| `standalone` | `One file with no album or numbering.` |

- `{basis}` is the engine's own reason in plain words: `each file names its own work`, `each file starts again at chapter 1`, `each file ends with its own afterword`, `there are no chapters to compare`.
- **Album sentence** (when the tags carry them): `Album «Впусти меня», track 2 of 5.` or `Album «Впусти меня».` when there is no track.
- When the engine repaired the text: add ` The tag text was repaired from an old encoding.` as the last sentence. The raw tag snapshot lower in the panel stays raw (it is the file's own text); this sentence explains the difference.
- Never printed: the `\x1f` key, a raw tag value, a path inside the key. `#source-basis` has no tooltip (not interactive).
- The page cannot repair text. The engine sends the decoded values (`tag_text`); the page prints them. No other place in `app.js` prints `row.scope`.

## Notes for Ender (page round)

- **Read `work`, drop the rest.** Render `work.rows` and `work.waiting` in the order sent, keyed by `id`. Remove the page-side assembly in `checkActivities` (chapter check from the book list, move, bulk, queued action, check pass), the `activityOrder` sort, the one-per-kind dedupe and the `+N more running` line. Keep page-owned rows only for `Approving selected books` and `Handing selected books to the app` (A9).
- **Blockers:** read `queued_actions[].blocker` (the same object as `work.waiting[].blocker`). Replace `QUEUE_WORDS`, `queueS`, `queueP`, `LATER_WHY` (the blocker part) and `RECOVERY_WAITS` with the builder in 2.2; `pressBlocker` and `pageBlocker` return the same object shape.
- **Strings to add or change:** every **new** and **changed** label in 1.5, 1.5a, 1.5b, 1.6; the builder; status line parts; the freshness cue; the `unread` line; the `(as of …)` suffixes. The page words `step` keys; it never prints an engine `step` as text (`maintenance` sends a sentence; ignore it).
- **Label keys needing copy (Ender's list):** `retry_all`, `retry_selected` (1.5); `decision_<action>` (1.5b); `cleanup_retry_<working|temporary|folder>`, `drive_empty`, `automatic_<phase>` (1.6).
- **Tooltips:** Show in list (Waiting) and the freshness cue are the only new interactive or hover elements. No other new control.
- **Keep:** no animation on row entry, no focus move, no sound, no toast.
- **New engine data for sections 8 to 10 (Ender, next round):**
  - **Join:** a preview call (like `routing-preview`) that takes the selected ids and returns the parts in play order (`id, title, files, hours, track, track_total, state, has_queued_job, has_failed_job, has_repair_request, has_approval`), the order basis (`album_tracks`, `file_names`, `none`; `missing`, `duplicate`), the proposed title and author, the Goes-to path, per-part refusals (finished, changed, gone) and the effect counts. A join action that is queue-capable (`QUEUE_PRESSES`, label key `join`) and does everything in one transaction.
  - **Withdraw** an accepted Repair or Retry (`m4b_readmission` has none today). Join needs it; Question 9 asks for a row Cancel that uses it.
  - **Set aside** a failed or queued job of a joined part (as `regroup_partial_jobs` does with its reason), so it leaves the Needs attention counts.
  - **Conversion step** `repairing` (Step 1 of 4), unit `parts`, `done` parts repaired, `total` damaged parts, and the file name; plus `originals_untouched` for the repaired and stopped copy.
  - **`scope_view`** on every candidate: `{kind, album, artist, track, track_total, basis, repaired}` from `tag_text` (repaired text), kinds as in section 10. The page never reads `row.scope`.
- **Engine gaps, offered not built:** `Find local covers` and `Check metadata` have no record (G2); move recovery, regroup and M4B repair checks have no done-count (they slide; repair shows `count` left).

## Assumptions

- A1. Read-only look at code; nothing launched, no rects measured.
- A2. Plain names for the kinds come from Ender's list plus a read of `gap_fill.py`, `regroup_partial_jobs`, `_start_move_recovery`, `_maintenance_book` and `background_work.py`.
- A3. Resolved by Ender's code: "applying saved decisions" are the durable decisions (names, approve, review, tracks, metadata_choices, file_review) the engine accepts and then applies one at a time (`decisions` rows and items).
- A4. Resolved: the engine sends `snapshot_age_ms` (counts only) and `refreshing`. A null age hides the cue.
- A5. Resolved by Sergei's answer 4 ("remember"): queued actions survive a restart (Ender's work). Until that ships they are held in the engine's memory and lost on restart; no panel note either way.
- A6. A cleanup in state `waiting` waits for the audiobook's output checks (`cleanupFacts` words it so).
- A7. The Resume button resumes paused cleanups too (its existing tooltip says so), so `Press Resume audiobook jobs` is true for paused cleanups.
- A8. Dark theme only; contrast uses the existing tokens (`--muted` for the 13 px cue and time text, `--warning` for the behind cue and the `unread` line).
- A9. The page can supply done and total for its own Approve selected and Let the app handle selected loops. If it cannot, their bars slide. Ender to confirm.
- A10. `Saved.` after Save preview metadata is the existing line; its exact code site was not read for section 7.
- A11. `checking` (start or retry checks) cannot tell the two apart from the cause alone, so the page reads the check rows in the same `work` to quote one.
- A12. "Repaired automatically during the join" means during the audio join at conversion. The Join action records one book and repairs nothing. If Ender repairs at join time, the `join` action row shows `Repairing part 2 of 5` as its step and the dialog line `Damaged M4B parts are repaired when the book is joined.`
- A13. Part titles become chapter names in the joined book (the earlier ruling: preserve chapter and story names; POST-023-05). Ender confirms how a part's own chapters nest under it.
- A14. A joined book starts unapproved. Series and number from the part names are dropped; a series all parts' tags agree on is kept.
- A15. The existing **Keep as separate books** undoes a join before approval. If it does not, a Split is needed (not specced).
- A16. A Repair request on a part is a saved job waiting next in line (`readmission.kind === 'repair'`, `queued_next`), and the engine can withdraw it once Ender adds that.
- A17. A damaged part is found while the conversion checks its sources (the strict chapter check), so the manual window cannot flag it at load.
- A18. The raw tag snapshot (`#tags`) stays raw on purpose; only the Source line is decoded.
- A19. Pause during a repair stops it, and Resume starts that part's repair again.

## Open questions for Sergei (one word each)

1. A Waiting item has **Show in list** only, and Cancel stays on the book's row. Add a **Cancel** button on each Waiting item? I recommend no, because the ask is to see, and Cancel has its own race handling on the row. no / yes
2. The freshness cue (about the counts: need attention, converted) shows only when they are 10 s or more old. Always show `Counts updated 14:03:21` instead? I recommend only when behind (a quiet panel when all is well). behind / always
3. A Retry cleanup waits for **every** queued conversion, which can be hours with a long queue. The new wording says so plainly. Keep that rule? It is the engine's safety rule (originals are never removed beside a conversion). I recommend keep. keep / change
4. Waiting actions are lost if the app restarts. Say so in the panel (a one-line note while an action waits), or have the app remember them across restarts (Ender's work)? I recommend say. say / remember
5. (Futaba O-r3-2) Saving the details panel on an Author unclear book takes it out of Needs attention while its author is still blank. Keep it in Needs attention until an author is entered? I recommend stay: a book leaves the list that asks for it only when the question is answered (the 0.29.0 item 3 rule, in the other direction). stay / leave
6. Two presses leave no record the panel can read: **Find local covers** and **Check metadata** (the engine keeps none). The panel cannot show them; the book's own row still says `Checking…`. Accept that, or have Ender add a record? I recommend accept: they are presses on the book he is looking at. accept / add

Questions 1 to 6 are answered below (the answers are numbered as relayed: answer 5 is a separate question about held counts; answers 6 and 7 are Questions 5 and 6 above). New for the Join, damaged-part and metadata-line sections:

8. After Join, should the joined book be **approved at once**, or stay a candidate for him to approve? I recommend review: the joined book still passes its own checks (metadata, order, cover), and approving at once would hide a failure. review / approve
9. An accepted Repair has no Cancel today. Join will withdraw it itself. Also add a **Cancel** button on the row of a book whose Repair is accepted but has not started? I recommend yes: today a mistaken Repair can only be held with Pause. yes / no
10. Offer, not built: a hint on rows whose files share an album with tracks 1/N to N/N (`Part 2 of 5 of the album «Впусти меня». Select the parts and use Join into one book.`). Add it? I recommend no: the real fix is the grouping rule (Ender), and the details panel already points to Join for these rows (section 10). yes / no

## Sergei's answers (2026-11-18)

1. Cancel on each Waiting item: **No**. The Waiting list keeps Show in list only; Cancel stays on the book's row.
2. Freshness cue: **only when behind**.
3. A Retry cleanup waits for the whole conversion queue: **keep** the engine rule. The wording says so plainly.
4. Queued actions lost on restart: **remember**. The app keeps queued actions across a restart (Ender's work), so no "lost on restart" note is needed.
5. Gone books also leave the "N held" count: **yes**, as built in `9418a8b`.
6. O-r3-2, an Author unclear book saved with a blank author: **leave**. Saving takes it out of Needs attention, as today.
7. Find local covers and Check metadata get no jobs-panel row: **accept**.

## Sergei's answers, round 2 (2026-11-18)

8. After Join: **review**. The joined book stays a candidate for Sergei to approve.
9. Cancel on a row whose accepted Repair has not started: **yes**.
10. Join hint on rows that share an album with tracks 1/N–N/N: **no**.

## Sergei's ruling on damaged parts (2026-11-19)

- **A damaged file that the app can't repair, where the damage blocks conversion or the audio itself is damaged:** the row tells Sergei plainly to re-acquire the book (get a fresh copy). No Retry, and no "Reopen draft to replace that file or leave it out".
- **The damage doesn't block conversion and the audio is intact** (for example, metadata or container damage the app works around): the file isn't treated as damaged. No damaged label, no hold, no repair prompt. It converts normally.
- **Sergei, 2026-11-20 (minor audio damage):** if a file plays through with only a short glitch, the app publishes it as a good file and may add a note that it has minor damage. Only damage beyond a short glitch says "get a new copy".
