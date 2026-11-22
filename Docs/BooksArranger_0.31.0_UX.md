# Books Arranger 0.31.0: UX spec (honest status)

Judy, 2026-11-22. For Ender. Source: `BooksArranger_0.31.0_Scope.md` (`d134484`): Sergei's report, rulings R1 to R7, step 4 ("Honest status") and the part of step 1 that shows on the page. Sergei, 2026-11-22: "How do I know that the app finished its queue and have nothing to do anymore? ... But what is 'Updating Metadata'? Is it re-researching old books? Or is it still a first pass?"

**This is an EXTEND of `BooksArranger_0.30.0_UX.md`.** The jobs panel, the Waiting list, the freshness cue, the blocker sentence and every string not named here stay as built. Where this spec replaces a 0.30.0 line it says so.

Basis: read-only look at `web/app.js` (`jobsFirstPart`, `renderWaitingForYou`, `WORK_LABELS`, `workStep`, `waitingLines`, `renderAutomatic`, `holdSentence`, `HOLD_APPROVE`, `destPlan`, `placeText`, `scopeBasisText`), `web/index.html`, `web/style.css`, `background_work.py`, `series_backfill.py`, `gap_fill.py`, `sorting_moves.py`, `merge_service.py` (`sorting_moves`, `sorting_moves_apply`), `web_server.py` (`needs_you_only`, the two sorting routes). Nothing was launched and no rect was measured (Sergei's copy was converting). The app has one theme, dark (`color-scheme: dark`, no light tokens), so contrast is checked against the dark tokens only.

## Decisions in brief

- **Three finished states, one badge.** When no job runs, waits or is queued, the status line starts with a badge: `All done`, `Waiting for you` or `Background look-ups only`. The badge is there only when the queue is finished, so its presence alone answers Sergei's question; its words say which of the three.
- **The engine decides the state.** The page never works it out from rows (the 0.29.0 rule for `needs_you_only`, kept).
- **Bare `Nothing running` goes from the status line.** It read as "done" while work waited. With work waiting it says `Continues by itself`.
- **Two background look-ups get plain names** that say which books they are for and whether a file changes. Their bar counts the whole look-up, not one pass, so `691 of 903 books` answers "how much is left".
- **A look-up between tries is a Waiting item**, grouped, with the next try time.
- **Series moves get a dialog**: the list he approves is the list he sees (the engine's existing gate). Selected books move with one press, `Move N books`; a wrong one is refused on its own line with `Keep here`. A kept book can be offered again from the same dialog, so no second confirm is needed.
- **Two books with one name** read `Same name as another book` and are offered a name change. Never `Part of a bigger book`, never `Approve as one book`.
- **Section 5 is the next version.** It is specced here so the words match; nothing in it is built in 0.31.0.

## 1. "All done" and the other finished states

### 1.1 The states

"Main work" is everything the 0.30.0 Running and Waiting lists show (conversions, cleanups, checks, queued actions, moves, scans, research of books not converted yet, automatic processing running, stopping, start pending or between tries, timed retries, saved decisions). "Background look-ups" are the two jobs of section 2 only. "Waits for you" is: books that need attention, books on hold, series moves to approve, a drive that is not answering.

| State | True when | Status line starts with |
|---|---|---|
| Working | at least one main job runs | as 0.30.0: `Converting: Dune`, `3 tasks running`, `Paused · …` |
| Paused | paused and nothing runs | `Paused` (0.30.0) |
| Continues by itself | nothing runs, main work waits to run | `Continues by itself` **new** (was `Nothing running`) |
| **Waiting for you** | no main work runs, waits or is queued; something waits for you | badge `Waiting for you` |
| **Background look-ups only** | no main work; nothing waits for you; a background look-up runs or waits for its next try | badge `Background look-ups only` |
| **All done** | no main work; no background look-up left; nothing waits for you | badge `All done` |
| Not readable | a source is unread (0.30.0 section 3.3) | `Nothing running that could be read` (no badge) |

- **Both at once** (things wait for you and background look-ups remain): the badge is `Waiting for you`. His action is the one thing he can miss at a cost; the look-ups need nothing from him and stay visible as a row or a Waiting item, and as the status part `212 background look-ups left`.
- **`All done` invariant, checkable:** when the badge reads `All done`, the Running list, the Waiting list, the On hold list and the Waiting-for-you block are all empty. Any item in any of them means another state.
- **Paused is never a finished state.** A pause can hold work the app has not counted yet.
- **Loading:** no badge until the jobs part has loaded.

### 1.2 The badge

`<strong id="jobs-state">`, the first thing in `#jobs-status`, followed by the 0.30.0 status parts. Not a control: no hover change, no focus stop. It has a tooltip (`title`).

| Badge | Look | Tooltip |
|---|---|---|
| `All done` | filled: background `--notice`, text `--notice-text`, 1 px border `--notice-border` | `Nothing is running, queued or waiting, background look-ups included. Nothing waits for you.` |
| `Waiting for you` | outlined: background `--surface`, text and 1 px border `--warning` | `No conversion, cleanup or other job is running or queued. The items under Waiting for you need your answer.` |
| `Background look-ups only` | filled: background `--raised`, text `--text`, 1 px border `--border` | `No conversion, cleanup or other job is running or queued, and nothing waits for you. Only online look-ups are left.` |

- Size: 15 px, weight 600, padding 0 8 px, radius 4 px, one line, never wraps inside (`white-space: nowrap`). The longest badge is about 210 px.
- The words carry the state; fill against outline is the second cue; colour is the third. No glyph, no animation, no sound, no toast.
- The border is 1 px, never 3 px, so the amber badge is not mistaken for the focus ring (same token value).
- **No layout shift:** `#jobs-status` has the same height with and without the badge when it fits on one line (reserve the badge's height as the line's minimum). The toolbar rect (Pause, Resume) does not move when the badge comes or goes (0.30.0 check 11).
- **No flicker:** the badge shows once its state has been reported for 3 s in a row, and goes once another state has been reported for 1 s (the same 1 s that gives a job its row).
- **Counts behind** (0.30.0 section 3.2): from 30 s, ` (as of 14:03:21)` follows the badge as plain text, as it follows the other stale counts.

### 1.3 Status line and idle line

Status parts, in order (new parts marked): badge or first part, books waiting to convert, cleanup phrase, actions waiting, `N need attention`, **`55 series moves to approve`** (new, zero left out), `N converted out of M approved books`, `N waiting for retry checks`, **`212 background look-ups left`** (new, zero left out; series and detail look-ups together).

Examples:
- `[All done] · 0 need attention · 1,510 converted out of 1,510 approved books`
- `[Waiting for you] · 329 need attention · 55 series moves to approve · 1,181 converted out of 1,510 approved books · 212 background look-ups left`
- `[Background look-ups only] · 0 need attention · 1,510 converted out of 1,510 approved books · 212 background look-ups left`
- `Continues by itself · 3 books waiting to convert · 329 need attention · …`

`· N on hold` stays as a part after the badge (it was glued to `Nothing running`).

The idle line `#jobs-idle` (shown, as today, only when the Running list is empty):

| When | Line |
|---|---|
| `All done`, or `Waiting for you` with no look-up left | `Nothing is running, queued or waiting.` |
| a look-up waits for its next try, or `Continues by itself` | `Nothing is running right now.` |
| paused, unread | unchanged (0.30.0) |

**Supersedes:** 0.30.0 section 4 "otherwise `Nothing running` plus its counts"; the idle strings `Nothing running` and `Nothing running.`.

### 1.4 The Waiting-for-you block

Shown, as today, only in the `Waiting for you` state. It becomes a short list: heading `Waiting for you` (the look of `Waiting` and `On hold`), then one line per kind that has a count, each with its button at the right (96 x 32 minimum).

```
Waiting for you
 329 books need attention.                                        [ Review them ]
 55 series moves wait for your approval.                          [ Review moves ]
```

- Line 1 and **Review them** are the 0.29.0 line and button (tooltip `Show every book that needs you.`). The as-of suffix stays: `329 books need attention (as of 14:03:21).`
- Line 2 and **Review moves** are new (section 3). Singular: `1 series move waits for your approval.`
- The sentence `The app can't do more until you review them.` goes: the badge says it, and it was untrue while look-ups ran.
- A drive that is not answering and a book on hold keep their own homes (the Waiting item with its instruction, the On hold list). They make the badge `Waiting for you` but add no line here. If they are the only reason, the block is hidden and the badge sits above the item that explains it.
- Order is fixed: need attention, then series moves. A line with a zero count is left out.

### 1.5 The window title (offered, Question 6)

If Sergei says yes: the window title ends with the state, so the taskbar answers without opening the window. `Books Arranger: all done`, `Books Arranger: waiting for you`, `Books Arranger: background look-ups`, otherwise `Books Arranger`. No flashing, no focus, no sound.

## 2. Plain names for the background look-ups

Each row answers four things in a fixed place: what it is and whose books (the label), how much is left (the detail), what it does this second and whether a file changes (the step).

### 2.1 Running rows

Replaces the `series` and `gap_fill` lines of 0.30.0 table 1.5. Row anatomy is unchanged (label and subject, detail, bar, step, elapsed).

| Kind, step | Label: subject | Step line | Detail and bar |
|---|---|---|---|
| `series`, looking up | `Finding series for finished audiobooks: <book>` (was `Metadata: Updating series`) | `Asking online sources. No file is changed.` | `691 of 903 books`, determinate |
| `series`, writing | the same label | `Writing the series into the file and renaming it. Audio unchanged.` | the same |
| `gap_fill` | `Finding original titles and author names: <book>` (was `Looking up book details`) | `For books you already approved. Recorded only, no file is changed.` | `40 of 71 books`, determinate |

- **The count is the whole look-up:** done = books settled (a series found, none found, or given up), total = every book that needed the look-up. It only grows and ends at the total. It is never the count of one pass, which starts again every ten minutes and reads as no progress.
- **No time estimate** on these two rows. Their pace is set by how often the sources may be asked; a guess would be wrong. The elapsed time stays.
- **Step tooltip** (the step line's `title`, as the chapter check uses it):
  - `series`: `Finished audiobooks without a series are looked up online, one by one. A book moves into a series folder only after you approve it.`
  - `gap_fill`: `Books approved without an original title or a full author name are looked up online, one by one. The answers are recorded. No audiobook is renamed.`
- The step and the label are one line each with an ellipsis (the 0.30.0 row); at widths where the step is cut, its `title` holds the full sentence.
- These rows count in `tasks running` only beside main work. Alone, the badge leads the status line and the row shows below it.
- `Researching books` (books not converted yet), `Looking up metadata` (a Find metadata press) and `Re-checking finished audiobooks` (a file check, nothing online) keep their names. Read beside the two labels above, they no longer look like the same job.

### 2.2 Between tries: the Waiting list

A look-up that waits for its next try showed nowhere. It is a Waiting item, one per look-up, grouped (the cleanups precedent). Engine order: after `metadata_sources`, before `drive`.

| What waits | Line 1 | Line 2 | Button |
|---|---|---|---|
| series look-ups between tries | `Finding series for finished audiobooks: 212 books` | `Waiting for online sources. Next try 14:05. No file is changed.` | none |
| detail look-ups between tries | `Finding original titles and author names: 31 books` | `Waiting for online sources. Next try 14:05. No file is changed.` | none |
| a series found, its write held by a job | `Write series into audiobook: <book>` | the 0.30.0 blocker sentence: `It runs when Converting: Dune finishes.` (a cleanup or a scan the same way) | Show in list |

- The count is the books waiting for a later try. Books due in the running pass are in the row, not here, so no book is counted twice.
- `Next try 14:05.` is left out when the engine has no time.
- Line 2 tooltip, the two grouped items: `A book that gets no answer after 5 tries is left as it is. The app stops asking about it.` (the number is the engine's).
- A look-up that pauses inside one book for a source's pacing leaves the Running list and waits here. The row's `No progress for 5 min` text must never show on a look-up that is only being polite to a source.
- These items do not make the state "Working": with only them left, the badge is `Background look-ups only`.

### 2.3 After approval, and at the end

- An approved series move runs as two rows in turn: `Finding series for finished audiobooks: <book>` with the writing step, then the 0.30.0 `Moving: <book>` row.
- When every book is settled there is no row and no item. `All done` is the signal. No summary line is built (Question 4 offers one).

## 3. Series moves: the approval control

The 55 finished audiobooks with a series found, and any found later. The engine's gate stays: he approves the list he saw; if the list changed, nothing moves.

### 3.1 Where it lives

| Entry | Place | Face | Shown |
|---|---|---|---|
| `#moves-shortcut` | list toolbar, right after `Needs attention · N` | `Series moves · 55` (quiet) | Audiobooks library and count above 0, in every state |
| **Review moves** | the Waiting-for-you block (1.4) | `Review moves` (quiet, 96 x 32 minimum) | with its line |

Both open the same dialog. Tooltip, both: `List the finished audiobooks that wait for your approval to move into series folders.`

### 3.2 The dialog

A modal `<dialog id="moves-dialog">`, built like `join-dialog`: Cancel has `autofocus`, Escape cancels, no form (Enter in the list confirms nothing). Width `min(880px, 100vw - 24px)`: two paths per book do not fit 560. It opens at once with `Checking the list…` while the engine answers.

```
Move 55 finished audiobooks into series folders?
Each book has a series found online. A book you approve gets the series written into its file,
a new name and its series folder. The audio is not changed. The app can't undo a move.

[x] Select all

[x] Граф Ноль · Gibson William · Series: Sprawl Trilogy · No. 2 · found on FantLab     [ Keep here ]
    Now in    Gibson William\Граф Ноль - Gibson William.m4b
    Moves to  Gibson William\Sprawl Trilogy\2 - Граф Ноль - Gibson William.m4b
[x] Мона Лиза овердрайв · Gibson William · Series: Sprawl Trilogy · No. 3 · found on FantLab  [ Keep here ]
    Now in    Gibson William\Мона Лиза овердрайв - Gibson William.m4b
    Moves to  Gibson William\Sprawl Trilogy\3 - Мона Лиза овердрайв - Gibson William.m4b
 ...
> Left where they are (3)

[ Cancel ]                                                             [ Move 55 books ]
```

- Title, singular: `Move 1 finished audiobook into its series folder?` While loading: `Series moves`.
- The list is a `role="group"`, `aria-label="Books to move"`, and scrolls inside the dialog (`max-height: 50vh`); the title, the body and the buttons stay in view. The button row is outside the scrolling list, in normal flow.
- Every book starts selected, each time the dialog opens. `Select all` is a checkbox (mixed when some are selected).
- Order is the engine's (by current path), so one author's books sit together.

### 3.3 Per book

Three lines. The checkbox's label is line 1, so the whole text of the line is its target; **Keep here** is a separate button at the line's right end (flex row, 12 px gap, the button never shrinks), not inside the label.

1. `Title · Author · Series: <name> · No. <n> · found on <source>`. Title in weight 600. The series part is the Place line's form. Source names: `FantLab`, `Goodreads`, `Wikidata`, `Litres`, `the publisher's site`; unknown: `found online`. The source's address is the `title` of that text.
2. `Now in` and the current path under Audiobooks Sorted (labels and path style of the row's destination block; the full path is the `title`).
3. `Moves to` and the new path. The leading folders it shares with line 2 are `--muted`; the new folder and file name are `--text`, so the eye lands on what changes. Both pass 4.5:1; the labels carry the meaning without the colour.

A book that was approved and then could not move comes back to this list with a fourth line in `--warning`: `Approved, but not moved: its file changed. Check it and approve again.` or `Approved, but not moved: its new place changed. Check it and approve again.` It counts in `Series moves · N` again. An approved move never fails in silence.

If Question 1 is answered "all", line 1's reason part is, per kind: `Author folder: <name>` and `Series name: <name>`; a book with two reasons shows both, ` · ` between.

### 3.4 Left where they are

A `<details>` under the list, closed by default, summary `Left where they are (3)`, tooltip `Books with a series found that the app does not move, and why.` Hidden when empty. Each entry: `Title · Author`, the `Now in` line, and one reason sentence. These books do not wait for him and do not hold back `All done`.

| Reason (the engine sends a key, never the sentence) | Sentence |
|---|---|
| kept by him | `Kept here by you.` with **Offer again** |
| a file with the new name exists | `A file with the new name is already in that folder.` |
| two listed books, one target | `Another book on this list would get the same name.` |
| he chose its folder | `You chose its folder.` |
| not in Audiobooks Sorted | `Not in Audiobooks Sorted.` |
| name is not the app's | `Its file name isn't the one the app gave it.` |
| file not where recorded | `The file isn't where the app left it.` |
| a newer version or a replacement | `It has a newer version.` |
| files kept at his choice | `You chose to keep its files as they are.` |
| data folder move unfinished | `Waits for the data folder move to finish.` |
| sources disagree | `Sources disagree about its series.` |
| no name can be built, or it could not be planned | `The app can't work out its new place.` |
| any other key | `The app leaves it where it is.` |

### 3.5 Approve all, approve some, refuse

One pass down the list: a right book stays selected, a book to decide later is unselected, a wrong book gets **Keep here**. The dialog is the confirm: it is opened on purpose, shows the exact list, and the one bulk button says what it does and to how many.

| He wants | He does | Result |
|---|---|---|
| approve all | **Move 55 books** | dialog closes |
| approve some | unselects the ones to leave for later, **Move 52 books** | dialog closes; the 3 stay waiting |
| refuse | **Keep here** on that book | it goes to Left where they are at once; the dialog stays open |

- **Move N books** (default button, right end; the count is the selected books). Tooltip: `Write the series into each selected book, rename it and move it into its series folder. The audio is not changed. The app can't undo a move.`
- **Keep here** (quiet, 96 x 32 minimum, one per book; `aria-label` `Keep here: <Title>`). Tooltip: `Keep this book where it is and take it off this list. Its series is not written. Offer again brings it back.` While it is sent the face is `Keeping…`. Then focus goes to the next book's Keep here (the previous one for the last book; Cancel when the list is empty).
- **Offer again** (quiet, 96 x 32 minimum, on a kept book). Tooltip: `Put this book back on the list of moves.` The book returns to the list, selected.
- **Cancel** (quiet). Tooltip: `Close without moving anything.` A book already kept stays kept; the tooltip is about moves.
- Keep here needs no second confirm: it touches no file, and Offer again undoes it at any time. There is no bulk refuse, so no single press can empty the list.
- Until a kept book exists in the engine (Notes for Ender), **Keep here** and **Offer again** are not shown at all (no disabled ghost). They are needed before release: without a refusal, a wrong series waits for ever and `All done` can never show.

**Result line**, one string, shown beside the control that opened the dialog (`role="status"`, in normal flow: under the Waiting-for-you block, or under the list toolbar like `#restart-summary`). It stays until the dialog is opened again. No toast.

| Outcome | Line |
|---|---|
| all accepted | `52 moves approved. Each book gets its series written into the file, then moves.` |
| some refused | `50 moves approved. 2 books were not accepted: open Series moves to see why.` (`--warning`) |
| none accepted | `No move was accepted. Open Series moves to see why.` (`--warning`) |
| kept (inside the dialog, above the buttons, `role="status"`) | `«Граф Ноль» kept where it is.` |
| offered again (the same line) | `«Граф Ноль» is back on the list.` |

After **Move**, focus returns to the control that opened the dialog; if it is gone (the count reached 0), to the Status select `#filter`.

### 3.6 Loading, a changed list, refusals

| Moment | The dialog shows | Buttons |
|---|---|---|
| loading | `Checking the list…` | Move `aria-disabled`, tooltip `The list is still loading.` |
| nothing selected | the list | Move `aria-disabled`, face `Move books`, tooltip `Select at least one book.` Keep here stays enabled (it does not use the selection). |
| sending a Move | Move's face `Approving…` | Move, Cancel, every Keep here and Offer again `aria-disabled`, tooltip `Sending your answer.`; Escape does nothing until it returns |
| sending a Keep or an Offer | that button's face `Keeping…` / `Offering…` | Move and the other Keep here and Offer again buttons `aria-disabled`, tooltip `Sending your answer.`; Cancel stays enabled |
| the list changed since it was shown | the new list in place, selections kept for books still listed, and above the buttons, in `--warning`, `role="status"`: `The list changed. Check it, then press Move again. Nothing was moved.` | enabled |
| the app is closing | `Books Arranger is closing. Nothing was moved.` (`--warning`) | Move, Keep here and Offer again `aria-disabled`, tooltip `Books Arranger is closing.` |
| the list could not be loaded | `The list couldn't be loaded. Close this and try again.` | Cancel only, face `Close` |
| nothing waits | `No books wait for a move.` and Left where they are, if any | Cancel only, face `Close` |

## 4. Two books, one destination

### 4.1 The held rows

When two rows, or a row and a queued book, would get the same name, both are held. Each row:

- **Status:** `Same name as another book`. It is counted and listed under the existing **Name taken** chip (the same question: this name cannot be used, change it). Chip tooltip becomes `Show books whose name is already used, in Audiobooks Sorted or by another book here.`
- **Sentence** (the row's hint): what holds the name, then the fix.

| The other is | Sentence |
|---|---|
| one row | `Another book would get this file name: «03-Мона Лиза овердрайв». Change a title, author, series or number so they differ.` |
| a book waiting to convert | `A book waiting to convert has this file name: «03-Мона Лиза овердрайв». Change a title, author, series or number so they differ.` |
| several | `2 other books would get this file name. Change a title, author, series or number so they differ.` |

The quoted text is the other book's own folder or file name, never its title: the titles are the same, which is the problem.

- **Destination line:** label `Both go to` (three or more: `All 3 go to`), in the warning style `Already there` uses, then the shared path.
- **Fields:** Title and Author on the row, as a Name taken row; Series and Number through **Edit names**, as today.

### 4.2 What he is offered

| Control | State and words |
|---|---|
| **Approve** | `aria-disabled` while the names are the same. The line under the buttons: `Another book would get this name. Change the title, author, series or number.` Enabled as soon as this row's `Goes to` differs. |
| **Show both books** (new, quiet, 96 x 32 minimum; `Show all 3 books` for more) | Sets Status to All and searches for the shared title, so the rows sit together. Tooltip: `List the books that would get this name: sets Status to All and searches for this title.` |
| the other row actions a Name taken row has | unchanged |

- **Never on these rows:** the status `Part of a bigger book`, the face `Approve as one book`, `Keep as separate books`. Two books with one name are already separate books. No Join hint either (Sergei's answer 10, 2026-11-18).
- When one row's name changes and the clash ends, the other row leaves by the 0.29.0 rule and strip line: `«Title» left this list: the name is free now. The book is checked again.`
- If the clash appears only at the press, Approve answers: `Another book would get this name. Change the title, author, series or number, then approve.` The row's `Goes to` line refreshes, as for Name taken.

### 4.3 A volume named from its own tags (R4)

The book is filed without asking, so the row carries no question. It says where the series came from, on the Place line of the status cell:

`Series: Sprawl Trilogy · No. 2 · from the file's tags`

- The same suffix slot serves the other origins: ` · entered by you`, and from the next version ` · found on Wikidata` (the source names of 3.3).
- Details panel, the `Book metadata` basis line of a `volume` (0.30.0 section 10), gains two sentences after `Kept as a separate book: …`: `Title from this file's own title tag. Series and number from its tags.`
- The title cell shows the volume's own title (`Граф Ноль`), never the album.

## 5. Waiting for the online answer (next version, not built in 0.31.0)

R2: a book may wait a few tries for the online answer before it converts; then it converts as before. Specced now so the words match sections 1 and 2.

| Place | Words |
|---|---|
| Row status | `Waiting for an online answer` (replaces `Waiting for source`) |
| Row hint | `Asking online for its English title and series: try 2 of 3, next at 14:05. Nothing to do.` The asked part follows the book: `its English title`, `its series`, `its English title and series`. |
| Jobs panel, Waiting item, several books | `Waiting for an online answer: 3 books` / `Next try 14:05. After 3 tries a book converts with the names from its files.` No button. |
| Jobs panel, one book | `Waiting for an online answer: Тёмный лес` / the same line 2 / Show in list |
| Jobs panel, while it asks | the 0.30.0 row `Researching books: <book>`, unchanged |
| Automatic block detail (`Waiting for metadata sources; …`) | `Waiting for an online answer. Next try 14:05.` |
| Tries ran out, it converts anyway: row note under the status, while Queued or Processing | `No online answer after 3 tries. Named from its files.` |
| The same, details panel | `Original title: No online answer after 3 tries. Filed under the Russian title.` and `Series: No online answer after 3 tries.` |
| An answer came and found nothing (R3) | `No English title found online. Filed under the Russian title.` (the existing `Not found.` fact). No note for a missing series. |

- This is main work: while a book waits, the state is `Continues by itself`, never a badge.
- The Waiting item replaces 0.30.0's `Metadata sources` item (`3 books wait for a source to answer. Next try 14:05.`).
- "No answer" (the sources did not reply) and "nothing found" (they replied) are different sentences and are never merged.
- The numbers (`3`) are the engine's.
- No new control (Question 5 offers one).

## 6. Other places this touches

- **Automatic block**, `Automatic pass complete — 12 converted · 3 held` (`app.js` 2913 to 2916): it speaks of one pass and read as "all done". It gains a suffix from the state: main work left: ` Other jobs are still running or waiting.`; only look-ups left: ` Background look-ups continue.`; otherwise nothing.
- **Busy notice** (`Busy with: …`): uses the row labels, so it takes the two new names.
- **`needs_you_only`**: the page stops reading it; the finished state replaces it.
- **0.30.0 spec**: mark as superseded: table 1.5 rows `series` and `gap_fill`; section 4 "First part when only cleanups wait"; and, when section 5 ships, table 1.6 row `metadata_sources`.
- **Unchanged:** Pause and Resume, the freshness cue, the unread line, On hold, every other row and Waiting item, the review table's columns, the chips other than Name taken's tooltip, themes and colours.

## 7. Controls: tooltip, disabled state, keyboard

| Control | Tooltip | Disabled when, and what it says | Keyboard |
|---|---|---|---|
| `Series moves · N` | 3.1 | never disabled; hidden at 0 or outside Audiobooks | in the toolbar's tab order after Needs attention; Enter or Space |
| **Review moves** | 3.1 | never disabled; shown with its line | tab order after Review them |
| Select all | `Select or unselect every book in this list.` | while loading or sending | Space |
| a book's checkbox | none of its own: its label is the book's line 1; `aria-label` is `Title, Author` | while sending | Space; focus scrolls it into view |
| Left where they are | 3.4 | never | Enter or Space opens and closes |
| **Keep here** (per book) | 3.5 | while anything is being sent, app closing (3.6) | Enter or Space; follows its book's checkbox in tab order |
| **Offer again** | 3.5 | the same | Enter or Space |
| **Cancel** / `Close` | `Close without moving anything.` | while a Move is being sent | Escape, Enter or Space |
| **Move N books** | 3.5 | nothing selected, loading, sending, app closing (3.6) | Enter or Space; never Enter from the list |
| **Show both books** | 4.2 | never | in the row's action order after Approve |

- Dialog tab order: Cancel (focused on open), Move, then round to Select all, each book (its checkbox, its Keep here), Left where they are. Cancel and Move are one or two presses from the start in either direction, whatever the list's length.
- A reload of the list in place never moves focus off the dialog and never resets the scroll position.
- Hover-only texts on things that are not controls: the badge (1.2), the two step lines (2.1), line 2 of the grouped look-up items (2.2), the source name (3.3). None carries anything that is not also on screen in short form.
- Every `aria-disabled` button keeps its focus stop and says why in its tooltip (the app's existing pattern).

## 8. Layout, overlap and contrast

**Narrow layouts.** No string differs by width.
- Review table: every new row text is in the status cell or the destination cell, which the medium (600 to 799) and compact (under 600) bands never hide. Nothing new goes into columns 3 and 4, which they fold.
- Jobs panel under 560 px: rows stack as built; labels and steps keep their one-line ellipsis and full `title`. The status line wraps; the badge stays whole on the first line.
- Dialog under 600 px: the label (`Now in`, `Moves to`) sits above its path; paths wrap anywhere; a book's Keep here drops to its own line under the paths, left-aligned; Cancel and Move keep one row.

**No element covers another.** By construction, not by measurement: everything new is in normal flow (no absolute, fixed or sticky positioning), so it can only wrap or push. The dialog is the one overlay, modal and dismissible, which is the allowed class. States walked through on paper: each of the seven first parts of 1.1 with 0, 1, 2 and 5 rows; the badge with and without the as-of suffix; the Waiting-for-you block with one and two lines; the freshness cue and the unread line shown; the list toolbar with the error, attention and moves shortcuts all shown at 600 px; the dialog loading, with 1, 55 and 200 books, with Left where they are open and closed, with the warning line, while sending; the same-name row in the wide, medium and compact bands with Edit names open; the Place line with a long series name. Futaba measures the rects (check 12).

**Contrast, dark tokens (the only theme).** Computed ratios, text against its background:

| Use | Pair | Ratio |
|---|---|---|
| `All done` badge text | `--notice-text` on `--notice` | 10.8:1 |
| `All done` badge edge against the panel | `--notice-border` on `--surface` | 5.0:1 (needs 3:1) |
| `Waiting for you` badge text and edge | `--warning` on `--surface` | 11.2:1 |
| `Background look-ups only` badge text | `--text` on `--raised` | 11.3:1 |
| its edge against the panel | `--border` on `--surface` | 4.1:1 (needs 3:1) |
| dialog text, titles, paths | `--text` on `--surface` | 13.9:1 |
| muted path folders, labels, result line | `--muted` on `--surface` | 8.9:1 |
| warning lines | `--warning` on `--surface` | 11.2:1 |
| quiet button text | `--accent` on `--surface` | 8.0:1 |
| default button text | `--on-accent` on `--accent` | 9.2:1 |
| disabled button text | `--disabled-text` on `--disabled` | 6.1:1 |
| focus ring | `--focus` on `--surface` | 11.2:1 |

Nothing new relies on colour alone: each state, warning and disabled reason is also words.

## 9. Acceptance checks (Futaba)

1. **All done is true.** Force every other state in turn (a conversion, a queued action, a timed cleanup retry, automatic processing between tries, a series look-up between tries, a detail look-up running, one book needing attention, one series move waiting, a drive not answering): the badge never reads `All done`. Positive control: with all of them cleared it does, within 3 s, and the four lists are empty.
2. **Three badges.** Each of `All done`, `Waiting for you`, `Background look-ups only` shows for its state, and `Waiting for you` wins when both apply while the look-up item stays on screen.
3. **No bare `Nothing running`** in the status line in any state.
4. **No flicker.** A job under 1 s does not remove the badge.
5. **Counts behind.** At 45 s the badge is followed by `(as of …)`.
6. **Names.** A running series look-up reads `Finding series for finished audiobooks: <book>`, its step says no file is changed, and its count is the whole look-up (it does not start again at the next pass). Writing shows the writing step.
7. **Between tries.** With look-ups deferred and none running: a grouped Waiting item with a count and a next try time; the badge is `Background look-ups only`; no row carries `No progress for 5 min`.
8. **Dialog.** Opens from both entries. 55 books, all selected. Unselect 3, Move: the engine receives exactly 52 and the digest shown. The result line shows beside the opener.
9. **Changed list.** Change the plan while the dialog is open, press Move: nothing moves, the warning line shows, the list is the new one.
10. **Keep here and Offer again.** Keep here on 3 books: each goes under Left where they are with `Kept here by you.`, the shortcut count drops by 3, the scroll position holds, and the look-up does not list them again. Offer again brings one back, selected.
11. **Same name.** Two rows with one destination: both read `Same name as another book`, each names the other's folder or file, Approve is disabled with its reason, and neither row shows `Part of a bigger book` or `Approve as one book`. Changing one title frees both.
12. **Layout, measured rects.** At 1280, 960, 760, 600 px and 200% zoom, long Cyrillic names: the toolbar rect is identical with and without the badge; no rect of the badge, block lines, shortcut buttons, dialog buttons or row buttons intersects another; the dialog's buttons stay in view with 200 books.
13. **Keyboard.** The dialog is fully usable without the mouse; focus returns as 3.5 says; Escape cancels except while sending.
14. **R4 row.** A volume with its own title tag and a series in its tags shows its own title and `· from the file's tags`, and carries no question.

## Notes for Ender

What the page needs from the engine, in plain words. How is yours.

**Section 1**
- One finished-state value per poll, decided by the engine from live facts: working, paused, continues by itself, waiting for you, background look-ups only, all done; and "not known" while a source is unread. The truth rules are table 1.1 and its bullets.
- For every row and Waiting item: whether it is a background look-up (so the page never guesses which work is "main").
- Counts: series moves waiting for approval; background look-ups left (series and detail, apart and together); drives not answering; books on hold (existing).
- The reasons something waits for him, as keys (attention, moves, hold, drive).

**Section 2**
- For the series and the detail look-up rows: done and total over the whole look-up (settled books, all books that needed it), and the step (looking up, writing).
- For each look-up between tries: how many books wait, the time of the next try, the tries limit.
- For a series write held by a job: the book, and a blocker object of the 0.30.0 shape.
- A look-up that waits on a source's pacing is not a running row.
- A real end: each book is settled after a limited number of tries (the limit is a product number, not mine).
- If Question 4 is yes: how many books ended with a series, without one, and given up.

**Section 3**
- The count of series moves waiting.
- The list: per book, its id, title, author, series, number, source name and address, current and new path (shown under Audiobooks Sorted, and whole), which kinds of move it is, and whether it was approved and then not moved, with a reason key. The list's fingerprint (the existing digest).
- The books left where they are: per book a reason key (table 3.4), never a sentence, and whether he kept it.
- New: keep a book where it is (it leaves the plan and the count, and the look-up never offers it again), and take that back (Offer again).
- The approve answer per book: accepted, or refused with a reason key.
- An approved move that then fails comes back to the list or to Left where they are. Today such a book drops out of the plan (`series_backfill` holds it with a reason the plan does not read).

**Section 4**
- The new hold as its own reason on a row: the shared destination, how many others, and for each other book its id, whether it is a row or a queued book, and a name that tells it apart (its folder or file name, different from this row's).
- A code for Approve refused by a late clash.
- Its count under Name taken (or its own key the page adds to that chip).
- For R4: where a row's series and number came from (file tags, a named online source, entered by him), and for the details line, that the title came from the file's own title tag.

**Section 5 (next version)**
- Per waiting book: tries made, the limit, the next try time, what is being asked (title, series).
- How the wait ended, per field: answered, nothing found, no answer after the limit.
- The Waiting item's count, next try and limit; with one book, its id and title.

**Strings**
- Every label, step, sentence and tooltip above is final copy. The engine sends keys; the page words them (the 0.30.0 rule).

## Assumptions

- A1. Read-only look at code and docs; nothing launched, no rects measured.
- A2. The page control covers the moves the app's own look-up found (55 today). R6's re-check of already-sorted books is a studio job and has no page surface.
- A3. A drive that is not answering and a book on hold count as "waits for you" (Question 7 asks).
- A4. A paused queue with nothing pending still reads `Paused`.
- A5. `showInList` with the shared title lists both same-name rows (it searches by title in the candidates view). If it cannot, the engine's ids of the other books are used.
- A6. The detail look-up records answers and renames no finished audiobook (`gap_fill.py` docstring; Scope: "92 finished books have a recorded English title never applied").
- A7. The `Finding series…` copy is true whether or not a series can be written without approval: it says only that a book moves into a series folder after approval (open question F1).
- A8. One theme (dark). A light theme, if added, uses the same tokens and needs its own ratios.

## Open questions (facts the docs and code did not settle)

- F1. Can the series look-up still write a series into a finished file without approval (the branch where the series folder is the book's own folder)? If it never happens under the current folder layout, the writing step shows only after approval.
- F2. How many tries before a look-up gives up on a book, and before a waiting book converts (R2 says "a few"). The copy prints the engine's number.
- F3. Does the Electron shell take its window title from the page? (Question 6 depends on it.)
- F4. Whether the series look-up of finished books keeps running after R6's job (Scope: not ruled). If it stops, section 2's series row and item simply never appear.

## Questions for Sergei (one word each)

1. The approval list: **series** moves only, or **all** moves the 0.30.0 plan holds (author folders and series names too)? I recommend series: R1 changes how series folders of translated books are named, so the other moves may change again.
2. `Keep here` on a wrong series: stop asking about that **book** for good, or only about that **series**? I recommend book. `Offer again` takes it back either way.
3. Translated books from Chinese or Japanese among the 55: R1 names their series folder in English from the next version. **Hold** them out of the list until then, or let them move **now** and again later? I recommend hold.
4. When the look-up gives up on a book (no source answered), show how many gave up, with a Try again button? I recommend **no**: R6's job re-checks old books. no / yes
5. Next version: a `Convert now` button on a book that waits for the online answer? I recommend **no**: it converts by itself after a few tries. no / yes
6. Offer: show the state in the window title (`Books Arranger: all done`), so the taskbar answers without opening the window? I recommend **yes**. yes / no
7. A drive that is not answering: does it hold back `All done` (the panel says `Waiting for you`)? I recommend **yes**: its books cannot be reached. yes / no
