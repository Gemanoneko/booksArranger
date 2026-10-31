# Books Arranger 0.24.1: stale list, Start over, author column, recovery text, leftover folders (Judy, 2026-10-31)

Basis: rulings 74e, 74f, 74g, 75a, 75b and 75c (`Team/Docs/BooksArranger_Rulings_2026-10-24.md`, end of file); the copy standard (`Team/Docs/ProcessRules.md`, "Copy is short, specific, and has no memory"); `web/app.js`, `web/index.html`, `web/style.css` at HEAD `f7317a4` (read only; the app was not launched, nothing on Z: or in `data/` was touched); my specs `BooksArranger_0.23.1_UX_2026-10-29.md` (section 4: question-row columns) and the 0.22.1 busy-engine section it builds on.

**Scope line.** This spec says what the window shows. When the engine says it, and how it re-asks the list, is Ender's (75a, window side and engine side). Every line below hides when the engine sends nothing for it. No new control is added: Start over already exists and is reused, so its only new text is one tooltip. The app is dark-only (no light theme in `style.css`), so there is no light/dark check.

## Open questions (best guess written in; each answerable in a word)

1. **74g: there is no "24 hours" text in `web/` or `desktop/`.** `grep -n "24"` over both finds only code comments and CSS. The page's stale retention wording is in the Recovery copies panel: an "Automatic deletion" row showing a date, and the sentence "Automatic deletion happens while the app is running; overdue copies are checked when it starts." (`web/app.js` L1128 to L1129). The words "24 hours" live in `README.md` L51 and `Docs/BooksArranger_Brief.md` L5 (docs, not the window), and in the data field `recovery_retention_hours: 24` (`review_backend.py` L276; the page never prints it). Section 4 fixes the panel and gives the doc wording. If Sergei saw "24 hours" on a screen, ask him which one.
2. **75a timing.** I chose 5 s before the line shows and 10 min before it escalates (section 1.4). Both are tunable constants. Ender: is the engine's "long wait" before a re-ask shorter than 10 min? (The escalation clock does not restart on a re-ask, so it works either way.)
3. **75b chip.** The Start over row stays in the chip it is in today ("Other"). No new chip. Ender: does "Retry all (N)" count a row that offers only Start over? If yes it must not.
4. **75b "Nothing is deleted".** The existing Start over tooltip already says it; I reuse it for the new cause. Ender confirms it is true for a job stopped on a changed file (old working files).
5. **74f engine need.** The list row must carry the decided author apart from the artist tag, and say "decided" or "not yet". If it cannot say "not yet", the page treats a missing author as not decided.

## Decisions in brief

1. **Stale list:** one line directly above the filter chips and table: `List from 14:32. The app is busy; this updates by itself.` No Refresh button, no spinner, no dimming. It says nothing new while the list is re-asked. It escalates once at 10 min with the way out.
2. **Start over for a changed file:** same control, new reason: `Stopped — source file changed`, hint names the file, one new tooltip. The press and the "Started over" rows after it are the existing ones.
3. **Author / reader:** every candidate row shows labelled lines, the way question rows already do. Author is the decided author, never the raw tag. A missing author reads `Not decided yet`.
4. **Recovery panel:** delete the "Automatic deletion" row and its sentence. The rule is already on screen in the automatic-policy notice.
5. **Leftover folders:** no row line, no log line, no toast. Two strings that say "empty" lose the word.

## 1. Stale list (75a)

### 1.1 Today, in one paragraph

The page keeps old rows until a list read answers (`loadList` paints only on arrival), so a slow read leaves old rows with no word about it. The only talk about slowness is the page-top notice (`#connection-notice`, "The app is busy with background work and answers slowly...") and the status line `Last update HH:MM:SS`. Both are driven by the oldest request in flight, and they sit in the scan-controls panel, usually scrolled out of sight when Sergei is in the list. A filter or page change blanks the rows and shows `Loading {filter}…` in `#empty` and `#page`; nothing says the wait is the engine's.

### 1.2 Placement

A new in-flow paragraph, `#list-stale`, in the File inventory panel: **after `#attention-loading`, before `#attention-groups`**. That is directly under the filter toolbar and above everything built from the list (chips, "Select this page", Queue/Approve selected, the table).

- Not in the page-top notice: it is far from the rows it qualifies.
- Not inside `#page`: that span is the pager's text and is replaced by the loading text on a filter change.
- Style: 15 px body text, `--text` on `--surface` (13.87:1). Not `.field-help`: this line qualifies every row below it and must not read as fine print. No box, no icon, no dismiss (it is bound to a state, not an event). `margin:8px 0`, `overflow-wrap:anywhere`.
- Escalated state (1.3, S3): `--warning` (11.18:1 on `--surface`). The color means "you can do something now"; it comes with the sentence that says what. Words carry the meaning, not color.
- `role="status"`, `aria-live="polite"`. It is announced when it appears and when its text changes (S1 to S3). It clears silently. Focus never moves to it. `#inventory` gets no `aria-busy` while old rows are readable.
- Desktop window only, like the busy notice. In a browser (launch-web) the old connection words keep working.

### 1.3 States

"Painted list" = the last list read that was answered and drawn. `waitingSince` = the start of the first list ask made after it; a cancel and re-ask does **not** reset it.

| # | State | Rows | `#list-stale` |
|---|---|---|---|
| S0 | Fresh: the list answers within 5 s of `waitingSince`, or nothing is waiting | the answer | hidden |
| S1 | A list read for the current filter, page and search is unanswered after 5 s; status answers | old rows stay, fully usable | `List from 14:32. The app is busy; this updates by itself.` |
| S2 | The list is cancelled and asked again (75a) | unchanged: no blink, no empty frame | **unchanged**, same text, same time |
| S3 | Still unanswered 10 min after `waitingSince`; status answers | unchanged | `List from 14:32; the app has been busy for over 10 minutes. If it goes on, quit from the tray and open Books Arranger again.` in `--warning` |
| S4 | The status read is also silent past 3 s (the page-top notice shows) | unchanged | `List from 14:32.` only. The page-top notice carries the cause and the way out, so no sentence is said twice. |
| S5 | The list answered with an error that is not "busy" (any HTTP error but 503) | unchanged | `List from 14:32.` only; the error text keeps its existing place in `#message` |
| S6 | Filter, page, view, library or search changed and the new list is slow | blank (existing: `showListLoading`), skeleton shows | hidden. The wait text in `#empty` gets the cause after 5 s: `Loading Held… The app is busy; this updates by itself.` After 10 min: `Loading Held… The app has been busy for over 10 minutes. If it goes on, quit from the tray and open Books Arranger again.` `#page` keeps `Loading Held…` |
| S7 | The list answers | repainted | hidden at once. No toast, nothing left in `#message`. |
| S8 | Startup load strip is up | the load strip's own placeholders | never shown (the strip owns silence while it is up) |

S2 is deliberately invisible. What would Sergei do differently if told "asking again"? Nothing. A spinner or a changing line would be ambient motion with no decision behind it.

### 1.4 Rules

- **The time** is when the page received the painted list, 24-hour local `HH:MM` (the `askClock` format). A list from an earlier calendar day reads `30 Oct, 23:48` instead of `23:48`. It never changes during S1 to S5, so the live region speaks only on a real change.
- **5 s** is above an ordinary slow read on a big catalog, so a normal 1 to 4 s read never moves the table. **10 min** is when waiting is no longer plausible work; it matches the busy notice's "quit from the tray" way out.
- **No control is disabled** because of the line. Presses already send the row's revision, and a press on a row that changed gets the existing "This book's status changed. Check the updated status above."
- **Layout shift.** The line moves the table down by its own height (about 30 px with margin), once when it appears (after at least 5 s) and once when it clears, which is also when the rows repaint. Reserved blank space was rejected: a 30 px empty band in the view Sergei works in all day costs more than one occasional shift.
- **One source of truth for "the engine is silent."** The busy notice and `Last update` must key on the **status read** only. If the list read still counts in `oldestWait()`, a slow list with a healthy status would print "No answer for 2 min ... quit from the tray" at 2 min while the line says the app answers. Ender: list reads leave that clock.
- **The rest of the window while the list is stale** is unchanged and shows no flag: the chips' counts and the Jobs line come from the status and keep updating; `Showing 1–50 of 312` stays true of the rows shown; Select, Queue selected and the row buttons stay as they are.

### 1.5 Hit areas

The line adds no control and overlays nothing: it is a block paragraph in the panel's flow, above the chips. Nothing in the filter toolbar, chip strip or batch bar changes size. Measured on the committed build by Futaba (section 8), not by me: the app was not launched.

## 2. Start over for a changed source file (75b)

### 2.1 What exists

`Start over` already exists in the Retry slot of a "Stopped — review changed" row (`rowActions.startover`): face `Start over`, pending face `Starting over…`, note `Setting this job aside…`, then `Started over.` and the `Started over — …` row states (`restartText`). 75b adds a second cause for the same control: no new button, no confirmation (nothing is discarded; the saved-review variants keep the confirmation they have). Today the row for such a book is `Stopped — see details` with `The conversion stopped. Select the row to read the technical message.`, which tells Sergei nothing and offers nothing.

### 2.2 The row, before the press

The row carries one button in the Retry slot: **Start over**. Retry is not shown (it would fail on the same file; the app keeps "no disabled ghost" for refusals). Size, position and style are the existing `.row-retry` (min 96 × 32 px; WCAG 2.2 minimum is 24 × 24).

| Part | Text | Notes |
|---|---|---|
| Status | `Stopped — source file changed` | Several files: `Stopped — source files changed` |
| Hint (`--warning`, like "review changed") | `{name} is not the file this job started with. Start over sends the book back to automatic processing.` | Several: `{n} files are not the ones this job started with.` The engine cannot name one: `A source file is not the one this job started with.` |
| Hint, saved review, no release offered | `{first sentence} Start over sets this job aside, but automatic processing will hold the book.` | existing second sentence |
| Hint, saved review, combined press | `{first sentence} One press sets this job aside, discards its saved review, and sends the book to automatic processing.` | existing second sentence; the combined face and confirmation stay as they are |
| Button | `Start over` | existing face; the combined face stays `Start over and let the app handle it` |
| Tooltip, plain | `Set this stopped job aside and send the book back to automatic processing with the files as they are now. Starts automatic processing if it isn't running. Nothing is deleted.` | new. "with the files as they are now" is the reason this cause differs from the old tooltip. |
| Tooltip, saved review | the existing `STARTOVER_HELD_TIP`, unchanged | |
| `aria-describedby` | the row hint (existing) | |

No names, no hash or size talk (what differed is the engine's business), no "previously". The status word is the one fact; the hint says which file and what the button does.

### 2.3 After the press

All existing text; nothing new to write.

| Moment | Row | Panel note |
|---|---|---|
| Pressed | button `Starting over…` (inert) | `Setting this job aside…` |
| Accepted, automatic processing running | `Started over — waiting its turn`, then `Started over — researching`. Hint: `Nothing to do. Automatic processing will research this book and queue it if the match is safe.` | `Started over. Automatic processing is running and will reach this book. Find it under Status: Started over.` |
| Accepted, automatic processing idle | `Started over — waiting for you`. Hint: `Press Start automatic processing above. It will then research this book and queue it if the match is safe.` | `Started over. Automatic processing has started. It scans the library first, so this may take a while. Find it under Status: Started over.` (or the `pending` variants) |
| Refused or closing | existing refusal words (`This book's status changed...`, `Books Arranger is closing. Start over after it restarts.`) | same |

The row leaves "Output needs attention" and lives under **Status: Started over** until the book is queued. Sergei does nothing else: no catalog edit (75b).

**Example, Салимов удел** (file name illustrative): before, `Stopped — source file changed` / `01.mp3 is not the file this job started with. Start over sends the book back to automatic processing.` / **Start over**. After the press and a short wait, `Started over — researching`; later the book is queued and converts like any other.

## 3. Author / reader column (74f)

### 3.1 Rule

The column shows what the app decided, never the raw tag. Today every non-question candidate row prints `row.artists.join('; ') || 'Unknown'` (`web/app.js` L554, `titleFacts` L2259), and that tag can be the reader (the Gene Wolfe row in 0.23.1 S4). Question rows already print labelled lines (0.23.1 section 4.3); **every candidate row now does**, so the same column never looks different from row to row.

Source of the decided author, in order (Ender confirms the field names): the saved review's author, the open question's proposal, the author the automatic pass settled on. **Never `row.artists`.**

### 3.2 What the column shows (wide band)

Labels are the existing muted `.goes-label`; values are `--text`; `Not decided yet` is `--muted` (8.92:1 on `--surface`; 4.97:1 on a selected row) so it reads as an absence, not a name.

| Decided author | Reader | Column |
|---|---|---|
| yes | yes | `Author  Pratchett Terry` / `Reader  Капитан Абр и Nelly` |
| yes | no | `Author  Pratchett Terry` (no reader line; nothing says "unknown") |
| no | yes | `Author  Not decided yet` / `Reader  Антон Ческидов` |
| no | no, a raw tag exists | `Author  Not decided yet` / `Clue  {raw tag}` (muted; the raw tag is evidence, so it is labelled as one) |
| no | no, no tag | `Author  Not decided yet` |

- **The Clue line shows only in the "no author, no reader, a raw tag" case** (fourth row of the table: the tag is the only name there is), and on question rows as today (0.23.1 4.3 rule: only when it differs from the author and reader lines). On a decided row the raw tag is one click away (View metadata: "Existing Artist (role unverified)"). Putting it on every row is noise for a fact the decision has replaced.
- **"Not decided yet" replaces "Unknown" everywhere in this column**, including question rows (`updateBookCell` L3067, `titleFacts` L2258 and L2259). One phrase for one state. A book Sergei approves with no author is filed under `Без автора`, and that name then shows as the decided author.
- **Reader** appears only when the engine marks a credit as a reader (it already does for question rows).
- Row height grows by one line only where a reader line exists.

### 3.3 Narrow bands (column folds into the Book cell, `titleFacts`)

`{Author} · Reader: {name} · {n} audio files`, with the same rules: no reader, no reader part; no decided author, `Author not decided yet · 3 audio files`. The Clue line does not fold.

### 3.4 Not changed

The Files view column `Existing author / artist clue` is raw evidence by name and stays. The column heading stays `Author / reader`. No tooltip: nothing in the column is interactive.

## 4. Recovery copies text (74g)

**Delete, don't reword.** In the Recovery copies panel (`makeRecoveryPanel`, `updateRecovery`):

1. Remove the `Automatic deletion` row (label and value). Its value is a date computed from a deadline; with deletion right after verification the date is the completion time, so it reads as overdue. The `Completed` / `Not applicable — copies already deleted` values go with it.
2. Remove the sentence `Automatic deletion happens while the app is running; overdue copies are checked when it starts.` and its hide rule.

Why no replacement sentence in the panel: the panel shows only while copies exist, which means something is holding them. The Status row already says what (`Deleting after the audiobook check`, `Recovery copies waiting to be deleted. {reason}`, `Recovery cleanup needs attention: {reason}`). A sentence saying "deleted right after verification" beside a reason it has not happened would explain nothing.

**The rule stays on screen once, where it already is** and is already correct: `#automatic-policy`, "Verified audiobooks replace their included originals. Once a book is verified, its backup copies are deleted right away." No change to it or to the other backup wording (`Removes ... their backup copies`).

**Doc wording** (not window text; Ender for the README, Jane for the Brief):
`Recovery copies of removed original tracks are deleted as soon as the audiobook is verified. A selected book's Delete recovery copies button deletes them by hand when verification keeps them.` Replaces README L51 and the 24-hour sentence in Brief L5. CHANGELOG entries are history and stay.

## 5. Leftover folders (74e)

**Nothing new is shown: no row line, no log line, no toast.** Reasons, one each:

1. Sergei ordered it ("you can delete folders automatically if no audio files are left"). A message about doing what was asked is noise.
2. The non-audio files that usually remain are covers, and the verified audiobook already carries its cover. Most converted books would print the same line.
3. The row already tells the outcome: once the folder is gone, the source button becomes `Open book folder` (ruling 70).
4. A folder that cannot be removed is already told: `Source cleanup needs attention: {reason}` in the book's panel, and the jobs-help note for drives where removal is unavailable.

**Two strings say "empty" and are now false** (a folder holding a `.jpg` is removed):

| Where | Now | New |
|---|---|---|
| `cleanupSteps.folders`, L908 (the progress row's step) | `Removing empty source folders` | `Removing source folders` |
| `jobs-help` note, L903 | `Empty source folders retained: safe automatic removal is unavailable on this drive.` | `Source folders retained: safe automatic removal is unavailable on this drive.` |

## 6. Copy sheet (single source; straight apostrophes; em dash as in the app)

| Id | String |
|---|---|
| 75a-1 | `List from {HH:MM}. The app is busy; this updates by itself.` |
| 75a-2 | `List from {HH:MM}; the app has been busy for over 10 minutes. If it goes on, quit from the tray and open Books Arranger again.` |
| 75a-3 | `List from {HH:MM}.` |
| 75a-4 | `Loading {filter}… The app is busy; this updates by itself.` |
| 75a-5 | `Loading {filter}… The app has been busy for over 10 minutes. If it goes on, quit from the tray and open Books Arranger again.` |
| 75a-t | `{HH:MM}` today; `{D Mon}, {HH:MM}` on another day |
| 75b-1 | `Stopped — source file changed` / `Stopped — source files changed` |
| 75b-2 | `{name} is not the file this job started with. Start over sends the book back to automatic processing.` |
| 75b-3 | `{n} files are not the ones this job started with. {second sentence}` |
| 75b-4 | `A source file is not the one this job started with. {second sentence}` |
| 75b-5 | tooltip: `Set this stopped job aside and send the book back to automatic processing with the files as they are now. Starts automatic processing if it isn't running. Nothing is deleted.` |
| 74f-1 | labels `Author`, `Reader`, `Clue`; value `Not decided yet`; fold: `Author not decided yet · {n} audio files` |
| 74e-1 | `Removing source folders` |
| 74e-2 | `Source folders retained: safe automatic removal is unavailable on this drive.` |

Words used on purpose: "the app" (as the busy notice says), never "engine" (the load strip's word, hidden after loading); "job", "Start over", "automatic processing" as the screens already say them. Copy-standard check: one fact per string; no roles, tickets or rulings; no "previously/no longer"; no legality talk; the way out appears only where the user can act (75a-2, 75a-5).

## 7. What the UI needs from the engine (names assumed; Ender confirms)

- **75a:** nothing beyond the window-side and engine-side items in the ruling. Window-side: `waitingSince`, the painted list's receive time, list reads out of `oldestWait()`.
- **75b:** on the stopped job's attention data, a typed cause for the changed source and the changed file names (count and up to one name). The existing `attention.startover` values (plain, saved review, combined) keep deciding the variant.
- **74f:** per list row, the decided author (a string, may be empty), the reader (string, may be empty), and whether the author is still being decided. The raw artists stay as they are.
- **74g, 74e:** nothing.

## 8. Checklist for Ender (slices; each ships alone)

1. **74g and 74e strings** (no engine change): sections 4 and 5. Tests that read `Automatic deletion` or the two strings change with them. Add a grep gate: no `24 hours`, `overdue copies` or `empty source folders` in `web/` and `desktop/`.
2. **74f column:** section 3, wide and folded. Remove every use of `row.artists` as an author in the list (see section 9, item 1).
3. **75b row:** section 2. Tooltip ships in the same commit as the new reason (ProcessRules, "A new control is born with its tooltip").
4. **75a line:** section 1, after the window-side fix. The line and the `oldestWait()` change ship together.

## 9. Checks for Futaba (committed build; headless; a mock engine that delays `/api/inventory`; nothing on Z:; no mouse or focus while Sergei is at the machine)

**75a**
1. Delay the list 4 s: no line, table does not move.
2. Delay it 6 s with status answering: `List from {time of last paint}. The app is busy; this updates by itself.` above the chips; rows unchanged; `#status` keeps its normal text; the page-top notice does not show.
3. Cancel and re-ask during the stall: line text and time identical before and after; no empty rows at any frame.
4. Silence status too past 3 s: line becomes `List from {time}.`; the page-top notice shows; no sentence about the app being busy appears twice.
5. Fake clock to 10 min: the escalated sentence in `--warning`; announced once.
6. Change the filter during a stall: rows blank, the line hidden, `Loading … The app is busy; this updates by itself.` after 5 s, in `#empty` only.
7. Answer arrives: line gone, rows repainted, `#message` empty.
8. List from yesterday: date shown. Load strip up: no line.
9. Measure the filter toolbar, chip strip and batch bar rects with the line shown and hidden: none overlap the line; list the shift in px.

**75b** 10. Seed a stopped job whose source file differs: status, hint, one button `Start over`, no Retry, exact tooltip; press: `Starting over…`, then the `Started over` row; saved-review variants keep their confirmation. 11. "Retry all" count excludes it (open question 3).

**74f** 12. The five rows of the table in 3.2 in the wide band, and the fold in the narrow bands; a decided author that differs from the tag shows the author; the Files view is unchanged.

**74g, 74e** 13. A recovery panel with copies retained shows no `Automatic deletion` row and no helper sentence; the grep gate passes; the cleanup progress row reads `Removing source folders`.

## 10. Noticed, not specced (offers, not in this release)

1. **The delete-book dialog has the same defect as 74f.** `showDeleteState` (L4229) falls back to the first raw artist tag as "the author", so it can name the reader on a confirmation that deletes files. Offer: one line in the 74f slice.
2. **A leftover-files line** (`Also removed with the source folder: booklet.pdf`) for unusual non-audio files only, if Sergei ever loses one. It needs the engine to record the names at removal.
3. **A clock in the stale line's S3 state** (`12 min`) is not offered: it would change the live region every minute.
