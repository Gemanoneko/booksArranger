# Books Arranger 0.22.1: UX specs (Judy, 2026-10-25)

Basis: backlog items 1 to 4, 6 and 7 (`Docs/BooksArranger_0.22.1_Backlog.md`); rulings 23, 24, 26 and 27 (`Team/Docs/BooksArranger_Rulings_2026-10-24.md`); Ender's fail-less updater proposal (`Docs/BooksArranger_Updater_FailLess_Proposal_2026-10-25.md`; its table D is the draft this spec replaces). Read-only look at v0.22.0 on main: `web/app.js` (retry block L880-1160, connection and poll code L77-135 and L357-412, the `ASK_*` tables L1906-1929, the Delete block L2195-2420), `web/index.html`, `web/style.css`, `web/desktop-ui.js`, `desktop/main.js`, `desktop/update-controller.js`, `desktop/engine-update.js`, `desktop/setup.*`; earlier specs `BooksArranger_RetryButton_Spec.md`, `BooksArranger_AttentionTodo_UX_2026-10-24.md` (the two Delete book specs) and `BooksArranger_MissingFiles_UX_2026-10-24.md`. Nothing launched, no rects measured: geometry is target geometry for Futaba. Contrast ratios are calculated from the `style.css` tokens (on `--surface` #1B2530 unless noted). Titles and paths in mockups are examples. Spec only: no code, not committed.

## In brief

1. **Queued Retry and Delete book (section 1).** A press while another operation runs is accepted and queued, not refused. The row says "Retry queued" or "Delete queued", names what it waits for, and has its own Cancel button. Every check runs again when it runs; a delete whose book or files no longer match is cancelled with a line that says nothing was deleted.
2. **Fail-less updater (section 2).** Final wording for Check for updates, Download update and Restart to update, with one message line per operation, a confirm that names the running work, a Cancel update button, and a line for every failure. "Request timed out" is gone.
3. **Startup (section 3).** The main window opens at once on a Starting page (elapsed time, the last start's duration, Quit), then swaps to the app. It has a slow state and a failed state with Try again, so a boot past the limit is never a bare error box.
4. **Busy engine (section 4).** In the desktop window a missing answer is always "busy", never "interrupted": the shell already closes the app when the engine process dies. Three tiers of copy, controls stay usable, and no bare "Connection interrupted" or "Local server unavailable" remains in the desktop window.
5. **Delete book on "All files missing" (section 5).** The existing copy is accurate but says the same fact three times. Trimmed to three short lines, and the face "Delete book (no files)" becomes "Delete book".

## Findings that shape these specs

1. **In the desktop app, "no answer" can never mean the engine is gone.** `desktop/main.js` L211-219: when the engine process exits unexpectedly the shell shows its own "Books Arranger stopped" box and closes the app. So every "Connection interrupted" and "Local server unavailable" a user sees inside the desktop window is a false alarm.
2. **One slow press turns the whole page offline.** A press with no reply in 15 s calls `refreshFailed`, which sets `recoveryDisconnected`; every button then reads "Local server unavailable." That is Sergei's Засор and Sigma Force 9 sequence: "Connection interrupted", then "Local server unavailable" on the next press.
3. **"Another operation is in progress" is mostly a window-side lock** (one press at a time, plus bulk runs). Most waits are seconds long. The long ones are bulk runs, scans and, for Delete, the book's own processing. So a queued row must say what it waits for.
4. **Tray "Check for updates" and "Restart to update" report failure in a modal error box** (`reportError`), and the panel buttons use their own face as their tooltip (`button(label)` sets `title=label`). Both are fixed in section 2.
5. **First run:** after "Use this folder" the setup window shows "Checking data folder…" for the whole engine boot, up to 3 minutes (`startConfigured` is awaited inside `books:select`). Section 3 covers it.

---

## 1. Queued Retry and queued Delete book (backlog 2 and 3)

### 1.1 Decisions

1. **A press while blocked is queued.** Retry, Repair and Delete book are no longer disabled for "busy". They stay disabled only when the server says they are not allowed, or in browser mode when the server is really gone.
2. **Only these three queue.** Start over, Let the app handle it, Convert…, Prepare recovery, Keep files, Clear working files, Scan again, Approve, Remove from list and Remove this copy keep the existing disabled state and "Another operation is in progress." (offer 1).
3. **One queue, first in first out, one action at a time.** A fresh press while others wait goes to the back, even if nothing is blocked at that moment. One queued action per row.
4. **The row says what it waits for, and how to cancel.** The face becomes "Retry queued" (inert), a separate "Cancel retry" button sits beside it. Cancel is not the same target as the face, so a double click on Retry can never cancel by accident.
5. **Nothing runs unchecked.** Retry's press already carries the book's revision and job; Delete's carries the confirmed paths. The server compares them at run time. A mismatch cancels the action and says so; Delete says nothing was deleted.
6. **A queued action never opens a dialog, moves focus or makes a sound when it runs.** Its outcome lands in the row, the strip and a polite announcement.
7. **The queue is held by the engine, not the page**, so a page reload, a filter change or a second look all agree. It is in memory only: Quit and updates drop it (question 1).

### 1.2 What a row can wait for

One table feeds the row hint, the tooltips, the strip line and the Delete dialog. The engine names the kind; the page maps it. An unknown kind reads as `operation`.

| Kind | Sentence (S) | Phrase (P), used as "when P finishes" |
| --- | --- | --- |
| `operation` | Another operation is in progress | the current operation |
| `scan` | A scan is running | the scan |
| `retry_run` | A retry run is in progress | the retry run |
| `approve_run` | A bulk approval is in progress | the bulk approval |
| `book` | This book is being processed | this book's processing |

### 1.3 Row anatomy

Retry (a Stopped row; the face sits in the Retry slot):

```
[ ] Лабиринты Ехо 3  ·  Макс Фрай  ·  1 audio file
    Stopped — ready to retry                           [ Retry queued ] [ Cancel retry ]
    Retry queued. Starts when the scan finishes.       [ View metadata ] [ Open folder ]
```

Delete book (a Missing files row; the pair sits on the Delete line, as today):

```
[ ] Новая плоть  ·  Сборник  ·  8 audio files
    Missing files                                      [ Scan again ]* [ Convert what's there ]*
    Delete queued, 1 ahead. Nothing is deleted yet.    [ View metadata ] [ Source folders ]
    It runs when the scan finishes.
    In  Z:\Audiobooks\Сборники\Новая плоть (2016)\
        03 - Павлов Михаил - Засор.m4b
                                                       [ Delete queued ] [ Cancel delete ]
* inert (aria-disabled), tooltip below
```

- The queued line **replaces the row's hint** while queued (the mechanism pending and results already use). The status line above it ("Stopped — ready to retry", "Missing files"), the "In" list and the "Goes to" line stay. After Cancel or a run, the normal hint returns.
- The face keeps keyboard focus (`aria-disabled`, never `disabled`). Pressing it does nothing.
- **Siblings on a row with a queued Delete** (Scan again, Convert what's there, Remove from list, Approve, Keep as separate books) go inert: `aria-disabled`, tooltip "A delete is queued for this book. Cancel it to use this." View metadata and the folder buttons stay live. On a row with a queued Retry nothing else is inert; Clear working files may still help the retry.
- **Details panel:** the same pair in `#retry-block`: `[ Retry queued ] [ Cancel retry ]`, and `#retry-note` carries the hint.
- **Bulk:** a row with a queued action is left out of Retry selected, Approve as is and Retry all, and counted in the existing left-out line as "{n} already queued".

### 1.4 Strings

{title} is `row.title_clue`, else the reviewed title, else "Book" (as the existing accessible names). {S} and {P} are from 1.2. "Repair" uses the Retry strings with the word changed.

| Part | Retry | Delete book |
| --- | --- | --- |
| Face, queued | Retry queued | Delete queued |
| Face, Repair | Repair queued | n/a |
| Face while the press is sent | Checking… (existing) | Checking… (existing; the dialog follows) |
| Accessible name, queued | Retry queued: {title} | Delete queued: {title} |
| Cancel button | Cancel retry (Repair: Cancel repair) | Cancel delete |
| Cancel accessible name | Cancel retry: {title} | Cancel delete: {title} |
| Hint, first in line | Retry queued. Starts when {P} finishes. | Delete queued. Nothing is deleted yet. It runs when {P} finishes. |
| Hint, others waiting | Retry queued, {n} ahead. Starts when {P} finishes. | Delete queued, {n} ahead. Nothing is deleted yet. It runs when {P} finishes. |
| Tooltip, queued face | Retry is queued. It starts when {P} finishes. | Delete is queued. Nothing is deleted until it runs, when {P} finishes. |
| Tooltip, Cancel | Take this retry out of the queue. Nothing was started. | Take this delete out of the queue. Nothing was deleted. |
| Tooltip, ready but blocked (button enabled) | Queue this retry. {S}; it starts when {P} finishes. | Delete this book. {S}, so the delete is queued after you confirm. |
| Tooltip, ready, not blocked | unchanged ("Check this book again and queue its audiobook job.") | unchanged |
| Tooltip, siblings inert | n/a | A delete is queued for this book. Cancel it to use this. |
| Face while it runs | Checking… (existing) | Deleting… (`aria-disabled`; tooltip "Deleting can't be stopped."; Cancel hidden) |
| Hint while it runs | Checking this book… (existing) | Deleting {n} files… / Deleting 1 file… / Removing this book… |

Examples of the blocked tooltip: "Queue this retry. A scan is running; it starts when the scan finishes." and "Queue this retry. Another operation is in progress; it starts when the current operation finishes."

**Strip line** (one polite line in the attention strip, new `p#queue-line.field-help`, after `#attention-sweep`; hidden when the queue is empty):

| Queue | Line |
| --- | --- |
| 1 action | 1 action queued. It runs when {P} finishes. |
| n actions | {n} actions queued. They run one at a time when {P} finishes. |

{P} is the first blocker's. It exists so a queued row that is off screen (other filter, other page) is still visible as a count.

**Announcer** (new visually hidden `p#queue-announce`, `role="status"`, `aria-live="polite"`, the last element in `main`, outside every row; 1 x 1 px, clipped, intersects nothing):

| Event | Text |
| --- | --- |
| Queued | Retry queued: {title}. / Repair queued: {title}. / Delete queued: {title}. |
| You cancel | Retry cancelled: {title}. / Delete cancelled: {title}. |
| It runs and ends | {title}: followed by the row's outcome line from 1.6 |

### 1.5 Delete book: the confirm comes first, then it queues

The press, the preview and the dialog work as today (Cancel has focus; Enter confirms nothing; a refusal found at preview opens the refused state). Two changes when the only obstacle is a blocker:

1. **The preview does not refuse "busy" any more.** It returns the list plus `blocked: {kind}`. The dialog opens in the blocked variant below. Refusals that are real (shared file, a finished audiobook in Sorted, drive offline, changed revision) still refuse at preview, with the existing lines.
2. **Confirm queues instead of deleting.** The face says so.

```
+-------------------------------------------------------------------+
| Delete this book?                                                 |
| Новая плоть — Сборник                                             |
| 1 of 9 files is missing.                                          |
|                                                                   |
| A scan is running, so this delete waits its turn.   (--warning)   |
| These 8 files (1.4 GB) will be deleted from your disk when it     |
| runs. The app can't undo this.                                    |
| +---------------------------------------------------------------+ |
| | Z:\Audiobooks\Сборники\Новая плоть (2016)\01 - ... .m4b       | |
| | ...                                          (scrolls, 40vh)  | |
| +---------------------------------------------------------------+ |
| The app checks this book and these files again first. If         |
| anything differs, nothing is deleted.                             |
| The app forgets this book. If you get it again, it's found as a   |
| new book. Nothing in Audiobooks Sorted is touched.                |
|                                                                   |
| [ Cancel ]                         [ Queue delete of 8 files ]    |
+-------------------------------------------------------------------+
```

| Part | String |
| --- | --- |
| Blocked line (new `#delete-dialog-blocked`, `--warning` text 11.18:1, directly above the Files line) | {S}, so this delete waits its turn. |
| Files line, queued | These {n} files ({size}) will be deleted from your disk when it runs. The app can't undo this. / This file ({size}) will be deleted from your disk when it runs. The app can't undo this. / No files will be deleted from your disk. |
| Re-check line (new `#delete-dialog-recheck`, directly below the list, in the stay line's place when there is none; with a stay line, below it) | The app checks this book and these files again first. If anything differs, nothing is deleted. / (no files) The app checks this book again first. If it differs, nothing is deleted. |
| Confirm face | Queue delete of {n} files / Queue delete of 1 file / Queue delete |
| Confirm tooltip | Queue this delete. It runs when {P} finishes, after the app checks the book and files again. The app can't undo it. / (no files) Queue removing this book from the app. No files are touched. |
| While the confirm is sent | Face "Queuing…" (`aria-disabled`), status line "Queuing this delete…". Cancel `aria-disabled`, tooltip "Queuing can't be stopped." (it takes a moment) |
| Title, Cancel, list, forget line, stay line | unchanged |

- Same danger style, same Enter rule, same `event.repeat` guard as the Delete dialog today. The blocked variant adds no control.
- **The answer decides.** If the blocker cleared between the preview and the confirm, the server deletes at once and answers with the result; the dialog then shows the existing Deleting, partial or refused states. If the dialog opened unblocked but the engine became busy, the face says "Delete book and 8 files" and the answer is "queued": the dialog closes and the row shows "Delete queued". Both outcomes are covered; the face is the best guess, the answer is authoritative.
- **After "queued":** the dialog closes, focus goes to the row's "Delete queued" face (`preventScroll`), the announcer says "Delete queued: {title}."

### 1.6 When it runs, and when it does not

**Retry and Repair.** The press runs as today: the face reads "Checking…", then the existing states ("Queued — runs next" and its siblings, with the existing strip line "{title} queued — runs after the current book"). A refusal uses the existing typed causes, with this lead. The row hint turns `--warning` and stays until the next press, the filter changes or the book's status changes (the existing `retryResult` lifetime).

| Cause | Row hint |
| --- | --- |
| Status differs from what you saw | Retry cancelled: this book needs another look. Check its status above. |
| Server refuses with a typed cause | Retry cancelled: {the existing refusal sentence}. e.g. "Retry cancelled: working files from an earlier attempt are still present. Retry after they are cleared." |
| Not accepted, no cause | Retry cancelled: it was not accepted. Check the status above. |
| No answer yet (section 4) | The retry hasn't been confirmed yet. The app is busy with background work, so it may still run. Check this row in a moment. |

**Delete book.** The dialog does not reopen. Every outcome is in the row and the strip, and the server re-checks everything the dialog listed.

| Outcome | Row hint (`--warning` unless noted) | Strip line | Row |
| --- | --- | --- | --- |
| Done | Deleted. The book is gone from the app. (normal colour) | Queued delete finished: {title}. {the existing success sentence, e.g. "Deleted 1 book and 8 files (1.4 GB)."} | leaves at the answer or the next poll |
| Book differs from what you confirmed | Delete cancelled: this book doesn't match what you confirmed. Nothing was deleted. Open its details and try again. | none | stays; Delete book returns |
| Files differ from the list | Delete cancelled: the files don't match the list you confirmed. Nothing was deleted. Press Delete book to see the current list. | none | stays; Delete book returns |
| A file also belongs to another book | Delete cancelled: a file also belongs to another book. Nothing was deleted. / {n} files also belong to other books. | none | stays; Delete book returns |
| A finished audiobook is in Sorted | Delete cancelled: a finished audiobook of this book is in Audiobooks Sorted. Nothing was deleted. | none | stays |
| Source drive not reachable | Delete cancelled: can't reach {root}. Nothing was deleted. | none | stays |
| The book is not listed | (no row) | Delete cancelled for {title}: the book isn't listed. Nothing was deleted. | none |
| Not accepted, no cause | Delete cancelled: it was not accepted. Nothing was deleted. | none | stays |
| Partial | Deleted {k} of {n} files. {f} still on disk. (f = 1: "1 is still on disk.") then up to 3 `.path` lines, each followed by its cause in `--muted` (the existing cause lines), then "+ {m} more." if there are more, then "The book stays listed. Press Delete book to try again." | Deleted {k} of {n} files. The book stays listed with the {f} that could not be deleted. | stays |
| No answer yet (section 4) | The delete may not have finished. The app hasn't confirmed it. Check the list before trying again. | none | stays |

- "Nothing was deleted" is said only for a typed refusal issued before the first file, as in the Delete spec.
- The cause lines are the existing `DELETE_CAUSE` strings ("In use by another program.", "Access denied.", "Can't reach the drive.", "Couldn't delete it."). The partial lines replace the Partial dialog, which a queued delete cannot open.
- A queued delete of a book whose last copy is the app's working files (ruling 26) re-checks that too: if the originals have come back, the list differs and it cancels.

### 1.7 Cancel, keyboard, focus

- **Cancel** is a native button, no confirmation (nothing started, nothing is lost). The row returns to its normal hint and buttons at the answer; focus goes to the row's restored Retry or Delete book button (`preventScroll`), else the Status filter.
- **Too late.** If the server answers that the action already started: hint "Too late to cancel: the retry has already started." / "Too late to cancel: the delete has already started." (normal colour), Cancel is hidden, and the run states of 1.4 follow.
- **Tab order:** the face, then Cancel, directly after it; Delete's pair stays last in the row, on its own line. No accelerator and no context menu for either (Delete's standing rule stands). Esc does nothing on the row.
- **Focus is never taken.** When a queued action starts or ends, focus moves only if it was on that row's own face or Cancel: then to the row's next working control, else the Status filter. Otherwise it stays where Sergei is.
- **Hit areas:** each button at least 96 x 32, labels wrap, never truncate. The pair shares `.row-actions` (flex, wrap, 8 px gap); nothing is absolutely positioned. In the narrow single-column layout the pair stacks. Disabled-look tokens: `--disabled-text` #ADB9C6 on `--disabled` #2B3745 (6.07:1, from the Retry spec); Cancel is a `quiet` button (`--text` on `--surface`, 13.87:1).
- **Colour is never the only signal.** The queued face differs from "Retry" by its words. Warning hints open with "cancelled" or a plain fact.

### 1.8 Edge cases

| Case | Behaviour |
| --- | --- |
| Row leaves the list while queued (status change, filter, page) | The queue is unaffected. The outcome reaches the row if it is listed, else the strip line (Delete) or the existing strip line (Retry). The queue line still counts it. |
| Filter or page change, reload, window hidden to the tray | The state is read back from the engine; nothing is lost. A hidden window gets no toast, no sound. |
| Quit (tray) or a restart while queued | Queued actions are dropped without a prompt (question 1). On the next start the rows show their normal buttons. Nothing was deleted or started. |
| Update (section 2) | The update drops the queue. Its confirm says how many (2.4). |
| Another press on a row that already has a queued action | The face is inert; the press does nothing. |
| Retry all runs while Retry presses are queued | Retry all is a blocker (`retry_run`); the queued rows are left out of it ("already queued"). |
| The blocker clears but the next action is also blocked | The action stays queued; its blocker phrase updates at the next poll. |
| The engine is slow when you press | The face shows its pending state with the section 4 slow lines; it never reverts to "Retry" and never invites a second press. |
| The queue is long (12 Retry presses in a row) | Each row shows its own "{n} ahead"; the strip line shows the count. Cancel is per row (offer 2: Cancel all). |

---

## 2. Fail-less updater (backlog 1, ruling 27)

Behaviour (gates, bounds, cancel, install) is Ender's proposal, section 5. This section is wording, states, layout and controls. T (the safe-point wait, proposed 90 s) and B (the overall bound, proposed 3 minutes) are parameters of the strings: whatever Ender and Sergei settle on is substituted.

### 2.1 Panel layout

The existing `section.desktop-update` ("App updates"). Three message lines, one per operation, then the buttons. A line is hidden when empty, except Check, which always shows. Each line is its own polite live region and is written only when its text changes.

```
App updates
Check      Version 0.22.2 is available (checked 21:04).
Download   Version 0.22.2 is downloaded and verified. Ready to install.
Install    (empty until used)
[ Check for updates ] [ Download update ] [ Restart to update ] [ Cancel update ]
```

- Line labels ("Check", "Download", "Install") are `span.field-help`, 13 px, `--muted`; the text is normal colour; a failure turns the text `--warning`.
- A new Check clears only the Check line. A failed install can never show up as a check result (Ender's section 5A).
- Times are 24-hour `HH:MM`, as the app's other clocks. Success reads "(checked 21:04)", failure "(tried 21:04)".
- Buttons: at least 96 x 32, wrap, one row. "Download update" shows only when an update is available; "Restart to update" only when one is downloaded and verified; "Cancel update" only while an update is stopping the engine (2.5). Busy buttons use `aria-disabled` and keep focus; the old `disabled` attribute dropped focus.
- The panel is not an overlay and sits in normal flow above the app. The `.desktop-status` panel above it (existing) carries the live progress in 2.5.

### 2.2 Check for updates

| Part | String |
| --- | --- |
| Face | Check for updates |
| Tooltip | Ask GitHub whether a newer version is available. Nothing is downloaded. |
| Face, busy (`aria-disabled`) | Checking… |
| Tooltip, busy | Checking for updates… |
| Check line, idle | Books Arranger {v}. Not checked yet. |
| Check line, checking | Checking for updates… |
| Check line, retrying | Checking for updates… no answer yet, trying again (try {k} of 3). |
| Check line, up to date | Books Arranger {v} is up to date (checked {HH:MM}). |
| Check line, available | Version {new} is available (checked {HH:MM}). |
| Check line, no answer after 3 tries | Couldn't check for updates: GitHub didn't answer after 3 tries (tried {HH:MM}). Check your internet connection, then try again. Nothing changed. |
| Check line, no internet | Couldn't check for updates: no internet connection (tried {HH:MM}). Connect, then try again. Nothing changed. |
| Check line, GitHub error | Couldn't check for updates: GitHub returned an error, {code} (tried {HH:MM}). Try again later. Nothing changed. |
| Check line, any other failure | Couldn't check for updates (tried {HH:MM}). Try again later. Nothing changed. |
| Dev build (not installed) | Updates work only in the installed app. |

The raw error text goes to the shell's own log, never to the screen. "Request timed out" appears nowhere.

### 2.3 Download update

| Part | String |
| --- | --- |
| Face | Download update |
| Tooltip | Download version {new} and verify it. Books Arranger isn't changed until you press Restart to update. |
| Face, busy (`aria-disabled`) | Downloading… {n}% |
| Tooltip, busy | Downloading version {new}… |
| Download line, downloading | Downloading version {new}… {n}% |
| Download line, ready | Version {new} is downloaded and verified. Ready to install. |
| Download line, connection dropped | Couldn't download version {new}: the connection dropped (tried {HH:MM}). Press Download update to try again. |
| Download line, checksum | Couldn't use the download: it failed its checksum check, so it was discarded (tried {HH:MM}). Press Download update to try again. |
| Download line, disk full | Couldn't download version {new}: not enough disk space (tried {HH:MM}). Free some space, then press Download update. |
| Download line, any other failure | Couldn't download version {new} (tried {HH:MM}). Press Download update to try again. |

### 2.4 Restart to update

Enabled whenever an update is downloaded and verified (the idle gate is gone). If work is running, it confirms first; if not, the press starts the update at once.

| Part | String |
| --- | --- |
| Face | Restart to update |
| Tooltip, idle | Install version {new} now. Books Arranger closes, updates and reopens by itself. |
| Tooltip, work running | Install version {new} now. Running work stops safely and restarts afterwards. Your source files are not touched. You confirm first. |
| Face, busy (`aria-disabled`) | Updating… |
| Tooltip, busy | Updating Books Arranger… |
| Install line, ready | (empty; the Download line says "Ready to install.") |

**Confirm dialog** (new `update-dialog`, the approve-dialog pattern: native modal, 560 px max, Cancel has `autofocus`, no form, Enter confirms nothing, `event.repeat` ignored, background inert, it is the only overlay):

```
+-------------------------------------------------------------------+
| Update to 0.22.2 now?                                             |
| Books Arranger stops its work safely, installs 0.22.2 and         |
| reopens by itself.                                                |
|                                                                   |
| Converting Лабиринты Ехо 3. It stops and starts again from the    |
| beginning.                                                        |
| Scanning the library. It stops. Continue it with Resume scanning. |
| Automatic processing stops. Press Start automatic processing to   |
| continue.                                                         |
| 2 queued actions are dropped. Press them again afterwards.        |
|                                                                   |
| Your source files are not touched.                                |
|                                                                   |
| [ Cancel ]                                        [ Update now ]  |
+-------------------------------------------------------------------+
```

| Part | String |
| --- | --- |
| Title | Update to {new} now? |
| Lead | Books Arranger stops its work safely, installs {new} and reopens by itself. |
| Conversion line | Converting {Title}. It stops and starts again from the beginning. |
| Scan line | Scanning the library. It stops. Continue it with Resume scanning. |
| Automatic line | Automatic processing stops. Press Start automatic processing to continue. |
| Queue line | {n} queued actions are dropped. Press them again afterwards. / 1 queued action is dropped. Press it again afterwards. |
| Closing line | Your source files are not touched. |
| Cancel / tooltip | Cancel / Close without updating. Nothing stops. |
| Confirm / tooltip | Update now / Stop work safely, install {new} and reopen Books Arranger. |

- A line shows only for work that is running. The scan and automatic lines state today's behaviour (footer: "after server restart, Start continues it"); Ender confirms each before it ships and corrects the sentence if it differs.
- No "Update after this book" button by default (question 4). If Sergei wants it: a third button "After this book", tooltip "Let the current book finish, then update. No new book starts."

### 2.5 While it updates

The `.desktop-status` panel (existing) shows the line; all mutating controls are disabled by the existing `quitting` rule. The seconds counter is its own `span` outside the live region, so a screen reader hears each phase once, not every second.

| Phase | Panel line | Visible buttons |
| --- | --- | --- |
| Request sent | Starting the update… | Cancel update |
| Waiting for a safe point | Stopping safely for the update. Waiting for {what} to reach a safe point… ({s} s of {T} s) | Cancel update |
| A file change is in progress | Finishing {thing} first, so nothing is left half-done. This takes a few seconds. | Cancel update |
| Forced stop | {What} didn't reach a safe point in {T} s. Stopping it now; {restart}. | Cancel update |
| Ending the engine (last resort) | Stopping the engine now. Saved work is kept. | none |
| Installing | Installing {new}… Books Arranger reopens by itself. The first start can take a couple of minutes. | none |

| Placeholder | Values |
| --- | --- |
| {what} | the conversion of {Title} / the library scan / research / automatic processing / an approval / a delete. Two or more: the first two joined with " and ", then " and {n} more". |
| {What} | {what} with the first letter capitalised |
| {thing} | a tag edit / a cleanup / a delete / a file rename |
| {restart} | for a conversion: it restarts after the update. For anything else: start it again after the update. |

| Cancel update | String |
| --- | --- |
| Face | Cancel update |
| Tooltip | Stop the update. Books Arranger keeps running as before. |
| Hidden from | the moment the engine process is being ended (Ending the engine) |
| After you press it | Install line: Update cancelled. Books Arranger is running as before. |

### 2.6 When it does not install

Each is the Install line, `--warning`, with a time stamp. None needs a bare error.

| Situation | Install line |
| --- | --- |
| The overall bound ran out | Update cancelled: {what} did not stop within {B} (tried {HH:MM}). Books Arranger is running as before. Press Restart to update to try again, or choose Quit Books Arranger in the tray, then run the installer. |
| The installer would not start | The installer couldn't start (tried {HH:MM}). Windows or your antivirus may have blocked it. Books Arranger is running again on {old}. Run the installer yourself: |
| The downloaded file is missing or fails its checksum | Update cancelled: the downloaded installer is missing or doesn't match its checksum (tried {HH:MM}). Check for updates, then download it again. |
| The file could not be verified in time | Update cancelled: the downloaded installer couldn't be verified in time (tried {HH:MM}). Press Restart to update to try again. |
| The old engine could not be restarted | Books Arranger couldn't restart its engine (tried {HH:MM}). Choose Quit Books Arranger in the tray, then open it again. |

- **One new control, "Show installer file"** (`quiet`, after "Restart to update"), shown with the first two rows only: the bound ran out, and the installer would not start. In both the installer file is on disk and Sergei may run it himself. Tooltip: "Open the folder that holds the downloaded installer." It opens the folder with the file selected. In the installer-blocked row the line ends "Run the installer yourself:" and the full path follows on a `.path` line under it. If Ender declines the button, the `.path` line stays and the sentence ends "Run the installer yourself: {path}".
- The button is hidden once the update succeeds, a new check runs, or the installer file is gone.

### 2.7 Tray

- **Menu:** "Check for updates" (unchanged); "Restart to update" (shown when an update is downloaded and verified, no idle gate); while an update runs, a disabled "Updating…".
- **Tray "Check for updates" and "Restart to update" show the window and run into the panel.** The modal error boxes "Update check failed" and "Update could not install" are removed; the panel lines are the only place failures appear. (A click on the tray is Sergei's own action, so showing the window is not an intrusion.)
- **Tooltip while updating:** "Books Arranger — updating".

### 2.8 Keyboard, hit areas, theme

- Every button is a native button in the existing toolbar: one Tab stop each, in the order Check, Download, Restart, Cancel update, Show installer file. The dialog traps focus natively; Esc and Cancel return focus to "Restart to update" (`preventScroll`).
- No accelerator. All contrast uses existing tokens: text 13.87:1, `--muted` 8.92:1, `--warning` 11.18:1 on `--surface`.
- No two rects intersect in any state: panel lines stack, buttons wrap, the dialog is the only overlay.

---

## 3. Startup (backlog 4)

### 3.1 Decision

**One window, open at once.** The main window is created at app ready, before the engine starts, and loads a local Starting page. When the engine is ready, the same window loads the app. A second window would flash and re-open; this one swaps content on the same size, position and `#121820` background.

- **Window rules unchanged:** `--start-hidden` opens nothing (the tray carries the state); `--show-inactive` shows it without focus; the close button hides to the tray. A second launch while starting shows this window.
- **No focus is taken at the swap.** If the window is hidden when the engine is ready, it stays hidden; the tray tooltip returns to "Books Arranger". No toast, no sound.
- **First run:** after "Use this folder" the setup window shows the same Starting view instead of "Checking data folder…" for the whole boot. A data-folder error still shows on the setup form.
- **Target:** window visible within 2 seconds of the process start, on the 706 MB catalog.

### 3.2 The page

```
+-----------------------------------------------------------+
| Books Arranger                                    _  []  X |
|                                                           |
|              Starting Books Arranger                      |
|              Opening your catalog…                        |
|              0:42 · last start took 1 min 39 s            |
|                                                           |
|              A large catalog takes a couple of minutes.   |
|              You can close this window. Books Arranger    |
|              keeps starting in the tray.                  |
|                                                           |
|                    [ Quit Books Arranger ]                |
+-----------------------------------------------------------+
```

A centred card, 480 px max, on `--canvas`. No animation: the elapsed time is the sign of life (a counter that changes every second, in normal colour; progress bars that stall are the thing to avoid).

### 3.3 States and strings

| State | Heading | Status line | Detail | Buttons |
| --- | --- | --- | --- | --- |
| Starting | Starting Books Arranger | Opening your catalog… | {m:ss} · last start took {m} min {s} s (omitted on a first start) | Quit Books Arranger |
| Starting, with steps (only if the engine reports them) | Starting Books Arranger | Step {n} of 4: {step}… | as above | Quit Books Arranger |
| Slow (after the larger of 3 minutes and twice the last start) | Starting Books Arranger | This is taking longer than usual. Books Arranger is still working; it's safe to wait. | {m:ss} | Quit Books Arranger |
| Hard limit reached ({L}) | Books Arranger is slow to start | Books Arranger didn't finish starting in {L}. It may still be working. | {m:ss} | Keep waiting, Quit Books Arranger |
| Engine stopped while starting | Books Arranger couldn't start | The engine stopped while starting. Your files are not touched. | Technical details (collapsed) | Try again, Quit Books Arranger |
| Another copy holds the port | Books Arranger couldn't start | Another copy of Books Arranger is running (process {pid}). Quit it from the tray, then try again. | Technical details (collapsed) | Try again, Quit Books Arranger |

| Step (only if reported) | Words |
| --- | --- |
| 1 | Starting the engine |
| 2 | Opening the catalog |
| 3 | Checking the last session |
| 4 | Loading your books |

| Control | Tooltip |
| --- | --- |
| Quit Books Arranger | Stop starting and close Books Arranger. |
| Keep waiting | Wait another {L} for the engine. |
| Try again | Start the engine again. |
| Technical details (summary) | Show the technical message. |
| Copy details | Copy the technical message to the clipboard. |

- **The limit.** Today the shell gives up at 3 minutes and shows a modal error box. The catalog keeps growing, so {L} should be 10 minutes (question 3). If it stays 3 minutes, the same strings apply with {L} = "3 minutes", and the Slow state never shows (its threshold is the limit).
- **Technical details** holds the last lines of engine output (the text `lastLines` collects now). Raw engine text appears nowhere else, and the old `showErrorBox` is replaced by this state.
- **Quit during start** closes at once with no confirmation: nothing is running except the boot. The engine is stopped the way a failed start stops it (its input pipe is closed); Ender confirms that is clean while the catalog is still opening.
- **Step lines** are optional. They need the engine to report a phase while it is not yet ready (offer: Ender's call). Without them the page is complete as it stands.

### 3.4 Tray while starting

- Tooltip: "Books Arranger — starting (0:42)", refreshed every 5 seconds (not every second, so a hovered tooltip does not flicker). Ready: "Books Arranger".
- Menu: "Open Books Arranger" shows the window, which is the Starting page until the engine is ready. "Quit Books Arranger" as above. "Check for updates" and "Restart to update" are disabled until ready.

### 3.5 Keyboard, hit areas, accessibility

- Window title "Books Arranger"; page title "Books Arranger — Starting". One `h1`. The status line is `role="status"` and `aria-live="polite"`; it changes only when the state or step changes, and once at the Slow state. The elapsed counter is outside the live region.
- Initial focus is the heading (`tabindex="-1"`), never a button: a stray Enter after launch must not quit. Tab reaches the buttons in the order above; buttons are at least 96 x 32 and wrap.
- Contrast on `--canvas` #121820: text 15.95:1, `--muted` 10.26:1, `--warning` 12.86:1. Nothing overlaps; the page has no overlay.
- The page loads from a local file with `connect-src 'none'` (as `setup.html`); the shell pushes the state to it through the preload.

---

## 4. Busy-engine feedback (backlog 7)

### 4.1 The rule

**In the desktop window, a missing answer means "busy", never "interrupted".** The shell closes the app itself, with its own message, when the engine process exits (finding 1), so the page never needs to guess. The old strings stay for browser mode (`launch-web`), where the server really can disappear. The page is in desktop mode when `window.booksDesktop` exists, as `desktop-ui.js` already assumes.

- A slow answer sets **no** page-wide offline flag. Buttons stay usable on the last known state; a press goes out and follows the ladder in 4.3.
- "Local server unavailable." is not used in the desktop window.

### 4.2 The top of the page

When the status read (or any request) has had no answer for 3 seconds:

| Part | Desktop string |
| --- | --- |
| Notice (`#connection-notice`), 3 s to 2 min | The app is busy with background work and answers slowly. This page refreshes by itself. |
| Second line, only if the last update named the passes (max 3, joined with ", ") | Busy with: re-checking {n} finished books, updating series on {n} books, researching {n} books. |
| Notice, from 2 min | No answer for {m} min: the app is busy with background work. Your files are not touched. If it goes on, quit from the tray and open Books Arranger again. |
| Status line (`#status`) | Last update {HH:MM:SS} · {the last status text} |
| Jobs line prefix | Last confirmed — (unchanged) |

- {m} is whole minutes, updated once a minute. The notice is `role="status"`, polite, rewritten only when its text changes.
- The old "Connection interrupted; automatic processing may still be running. Retrying…" is browser mode only. "Retrying…" is gone from desktop: it implies a failure, and the page's refresh is not a retry.
- The notice clears at the first answer, as the existing one does.

### 4.3 What a click shows

Every press keeps its normal pending face and note. Time adds a sentence; the button never reverts to its ready face and never invites a second press. Engineering removes the 15 s abort; the ladder is the copy for the rare slow case.

| Elapsed since the press | Note (row hint, details note, dialog status) |
| --- | --- |
| under 3 s | the normal pending note, e.g. "Checking this book…" |
| 3 s to 1 min | {normal note} The app is busy with background work, so this takes longer. |
| 1 min and more | {normal note} Still waiting ({m} min). The app is busy with background work. |
| no answer after 10 minutes | the "not confirmed" line below; the button returns to its ready face |

| Press | "Not confirmed" line (replaces every "Connection interrupted…") |
| --- | --- |
| Retry, Repair, Keep files, Convert…, Start over, Clear working files | This hasn't been confirmed yet. The app is busy with background work, so it may still go through. Check this row in a moment. |
| Retry all, Retry selected | The retry requests haven't been confirmed yet. They may still go through. Check the list in a moment. |
| Discard review | The review may not have been discarded. The app hasn't confirmed it. Check the book before trying again. |
| Approve, Scan again, Remove from list | This hasn't been confirmed yet. The app is busy with background work, so it may still go through. Check this row in a moment. |
| Delete book | The delete may not have finished. The app hasn't confirmed it. Check the list before trying again. |
| Remove this copy | The removal may not have finished. The app hasn't confirmed it. Check the list before trying again. |
| Queued Retry or Delete | the rows of 1.6 |

The destructive rows never say "Nothing was deleted" here: no answer is an unknown outcome.

### 4.4 Delete's dialog, slowly

The Deleting state's status line gets the same sentences: "Deleting {n} files…" then, after 3 s, "Deleting {n} files… The app is busy with background work, so this takes longer." The face stays "Deleting…" (`aria-disabled`) and Cancel stays inert ("Deleting can't be stopped.").

### 4.5 What is left of the old strings

| Old string (desktop window) | Becomes |
| --- | --- |
| Connection interrupted; automatic processing may still be running. Retrying… | 4.2 |
| Last received: {text} | Last update {HH:MM:SS} · {text} |
| Connection interrupted. Check the status above before trying again. (every press) | 4.3 |
| Connection interrupted. Wait for the local server to reconnect. | not shown (presses go out) |
| Connection interrupted, so the delete may have gone through. Check the list before trying again. | 4.3 |
| Local server unavailable. (tooltips) | not used |
| Another operation is in progress. | queued for the three actions of section 1; unchanged for the others |

---

## 5. Delete book on an "All files missing" row (backlog 6)

### 5.1 Verdict

**Mostly right, three small fixes.** The facts are correct and the Cancel-first dialog should stay. What the current dialog (n = 0) reads:

| Line | Today |
| --- | --- |
| Reason | All 2 files are missing. |
| Files line | No files are left on disk. Only the app's record of this book is deleted. |
| Forget line | The app forgets this book. If you get it again, it's found as a new book. Nothing in Audiobooks Sorted is touched. |
| Confirm face | Delete book (no files) |

Problems for someone who "just wants those lines gone":

1. **Three lines state one fact.** "All 2 files are missing", "No files are left on disk" and "Only the app's record… is deleted" say the same thing; the forget line then repeats the record part.
2. **"(no files)" is a hedge on the face.** It reads as jargon; the line above already says nothing on disk is touched.
3. **The failure Sergei saw was not copy.** The row hint "Connection interrupted…" and then "Local server unavailable." came from the slow-click behaviour of section 4, which this release fixes. The queue (section 1) covers the other cause: a press while another operation runs.

### 5.2 Final copy for n = 0

```
+-------------------------------------------------------------------+
| Delete this book?                                                 |
| Iron Inferno                                                      |
| All 2 files are missing.                                          |
|                                                                   |
| No files will be deleted from your disk.                          |
| The app forgets this book. If you get it again, it's found as a   |
| new book. Nothing in Audiobooks Sorted is touched.                |
|                                                                   |
| [ Cancel ]                                  [ Delete book ]       |
+-------------------------------------------------------------------+
```

| Part | String |
| --- | --- |
| Title, book line, reason, forget line | unchanged |
| Files line (replaces "No files are left on disk. Only the app's record of this book is deleted.") | No files will be deleted from your disk. |
| Confirm face (replaces "Delete book (no files)") | Delete book |
| Confirm tooltip | Remove this book from the app. No files are touched. (unchanged) |
| Row tooltip | Remove this book from the app for good. No files are left to delete. You confirm first. (unchanged) |
| Queued variant | section 1.5 (face "Queue delete", Files line "No files will be deleted from your disk.") |

- The first three lines read: what is wrong, what happens on disk, what happens in the app. Each is one fact.
- The danger style stays (solid red confirm, Cancel focused, Enter confirms nothing): the record, with its research and approvals, cannot be brought back.
- "Remove from list" next to it keeps its tooltip ("Stop listing this book. No files are touched. A scan lists it again if its files return."). The two tooltips already say how they differ; no new copy is needed.
- Ruling 26 case: an All-missing row whose app working files still exist opens with n above 0 and the last-copy line, unchanged.

---

## 6. What the UI needs from the engine and shell (names assumed; Ender confirms)

**Queue (section 1)**
- `POST /api/audiobook/retry`, `/api/audiobook/repair` and `/api/candidate/delete` accept `queue: true`. They answer 200 with the result if they ran, or 202 `{queued: true, id, position, blocker: {kind}}`.
- `POST /api/candidate/delete-preview` returns `blocked: {kind}` instead of a `busy` refusal when a blocker is the only obstacle.
- `POST /api/queue/cancel {id}` returns 200 `{cancelled: true}` or 409 `{code: 'started'}`.
- `/api/state` carries `queued_actions: [{id, action, book_id, position, blocker: {kind}}]` and `queue_outcomes: [{id, book_id, title, action, result, code, deleted, failed, bytes, folders}]`, kept until the page acknowledges them or 24 h pass, so a reload still shows the outcome.
- At run time the engine re-checks: the revision, the confirmed paths and folders, shared files, Sorted, source-drive reachability, and the book's still being listed.

**Updater (section 2)**
- Shell status adds `check`, `download` and `install` objects (phase, time, typed error cause), `cancelUpdate()` and `showInstaller()`, and `work: [{kind, title}]` for the confirm dialog.
- Typed causes for 2.2, 2.3 and 2.6; no raw text in the page.

**Startup (section 3)**
- A `books:startup` push to the page: `{state, step, of, elapsedMs, lastBootMs, limitMs, message, details}`. The shell stores the last successful boot time. Optional: the engine reports a startup phase while not ready.

**Busy (section 4)**
- The page keeps the time of the last answer per library and its last status text (today it keeps only the text).

## 7. Changes Ender must make

1. `app.js`: Retry, Repair and Delete book are enabled while blocked and send `queue: true`; the queued face, Cancel, siblings inert, hint, tooltips and strip line of 1.3 and 1.4; read queue state from `/api/state`; the outcome table of 1.6. The details-panel pair in `#retry-block`.
2. `index.html`: `#delete-dialog-blocked`, `#delete-dialog-recheck`, the Queuing state; `p#queue-line`; `p#queue-announce`; `update-dialog`; the three update lines and the Cancel update and Show installer file buttons; real tooltips on every update button.
3. `style.css`: no new tokens. `#queue-announce` is visually hidden (1 x 1 px, clipped, placed after the footer, intersecting nothing); `#delete-dialog-blocked` uses `--warning`.
4. Delete dialog: n = 0 copy of 5.2. Preview `blocked` handling (1.5).
5. `desktop-ui.js`: the update panel of section 2, `aria-disabled` on busy buttons, the phase table of 2.5 and the counter outside the live region.
6. `desktop/main.js`: create the window at app ready and load the Starting page; swap to the app URL when ready; the failed and slow states; remove `showErrorBox` for startup and for update failures; tray tooltip, menu and "Check for updates" and "Restart to update" showing the window; the first-run setup window shows the Starting view.
7. `app.js` connection code: desktop mode never sets the offline flag for a slow answer; the notice, status line and ladder of section 4; keep the old strings for browser mode.
8. Tests (front end): the queued state for each of the three actions; Cancel; "too late"; every cancel line; the blocked Delete dialog; every Check, Download, Install line; the Starting page states; the ladder; no `Connection interrupted` or `Local server unavailable` in the desktop build; every new control has a tooltip.

## 8. Checks for Futaba (committed build, seeded fixture, no real library, nothing on Z:)

1. **Queue Retry:** hold an operation open (a bulk run or a stub-slowed press), press Retry on a Stopped row. The face reads "Retry queued", Cancel retry appears beside it, the hint names the blocker, the tooltips match 1.4. Release the blocker: the row runs ("Checking…", then the existing queued states). Control: on the 0.22.0 build the button is disabled with "Another operation is in progress."
2. **Order and count:** queue three rows. "{n} ahead" reads 0, 1, 2 (first reads without it); the strip line says "3 actions queued."; they run one at a time in order; a fourth press while idle but queued goes behind.
3. **Cancel:** Cancel retry returns the row to Retry, nothing starts, focus is on the restored button. Cancel pressed as it starts: "Too late to cancel: the retry has already started." A double click on "Retry queued" does nothing.
4. **Queue Delete:** on a Missing files row with a scan running, press Delete book. The dialog shows the blocked line, the "when it runs" Files line, the re-check line and "Queue delete of {n} files". Cancel is focused; Enter on it cancels; Enter in the body does nothing. Confirm: dialog closes, "Delete queued", siblings inert with their tooltip, focus on the face.
5. **Run:** end the scan: the files go, the record goes, the strip reads "Queued delete finished: {title}. …", the row leaves, and **no dialog opens and focus does not move** if it was elsewhere. SHA-256 of a sibling book's file and Sorted unchanged.
6. **Run-time cancel, each verbatim, nothing deleted:** change the book's revision; add a file to the folder; make one file shared; place a finished audiobook in Sorted; take the source drive offline; remove the row while queued. Each shows its line of 1.6. Control: the same queue without the change deletes.
7. **Partial:** hold one file open while queued. The row names it with "In use by another program.", the other files are gone, the book stays listed, and Delete book returns.
8. **Quit with a queue:** Quit, reopen: rows show their normal buttons; nothing was deleted or started; no prompt appeared at Quit.
9. **Updater, each state verbatim:** local feed per Ender's section 5E. Check: idle, checking, retrying, up to date, available, no answer (black-holed GitHub, 3 tries), no internet, GitHub error. Download: progress, ready, dropped, checksum. Restart: idle (no dialog), work running (dialog lists the right lines and the queue line), Cancel, Update now, each phase line, Cancel update during the wait, the bound, installer blocked (with the path and Show installer file), changed file. No "Request timed out" anywhere (search the page and the tray). Tooltips are sentences, not copies of the face.
10. **Tray:** "Check for updates" and "Restart to update" open the window and show their result in the panel; no modal error box appears.
11. **Startup:** on the 706 MB copy, the window is visible within 2 s with the Starting page; the counter runs; "last start took" is right on the second start; Quit works; closing hides to the tray and Open brings the page back; `--start-hidden` shows nothing; at the swap, focus does not move. Slow and hard-limit states with a stalled stub engine; the failed state with an engine that exits (Technical details holds its last lines); port taken. First run: the setup window shows the Starting view.
12. **Busy engine:** start the three background passes (re-check, series, research) on the real-catalog copy. The notice, "Busy with:" line and "Last update {time}" appear after 3 s; at 2 min the second notice. Presses show the ladder; none says "Connection interrupted", "Local server unavailable" or "Retrying…". Controls stay usable. Control: the same run on 0.22.0 shows the old strings. Browser mode still shows the old strings.
13. **Delete on All files missing:** the dialog reads exactly 5.2; the face is "Delete book"; the row leaves; Remove from list is untouched.
14. **Layout, every state above:** no two rects intersect at 1440, 1024, 700 and 200% zoom; no horizontal scroll; focus rings not clipped; `#queue-announce` intersects nothing; contrast measured in the build matches the ratios cited.

## 9. Questions for Sergei (one word each) and offers

**Questions**
1. Should queued actions survive closing the app? I recommend no: nothing is deleted or started while you are away, and the rows return to normal. (yes / no)
2. Should the update install silently, with no installer window? I recommend yes: the installer window would take focus, and the Starting page shows the new version coming up. (yes / no)
3. Should the startup limit go from 3 minutes to 10? I recommend yes: the catalog keeps growing. (yes / no)
4. Should Restart to update also offer "After this book"? I recommend no: the update stops work safely anyway. (yes / no)

**Offers (not specced)**
1. Queue the other actions too (Approve, Remove this copy, Scan again) with the same mechanism.
2. "Cancel all queued" in the strip, shown from 2 queued actions.
3. One "Delete all {n}" for All files missing rows, with one confirm listing the titles, if there are many.
4. A tray notice when a queued delete or an update step ends while the window is hidden.
5. Copy audit: the Delete family uses "..." in its pending faces ("Checking...", "Deleting...") while the rest uses "…". New strings here use "…".

Design basis: Fitts (the destructive button stays the farthest target; Cancel is a different target from the face), Hick (one queue, two cancels, no menu), Jakob (Windows "Restart to update", native dialogs, tray behaviour), NN/g visibility of status (every wait says what it waits for), error prevention (re-check at run time, Cancel default, Enter never confirms), plain-language recovery (every failure names the cause and the fix), and truth over reassurance ("Nothing was deleted" only for a refusal before the first file; "may still go through" for a press with no answer); WCAG 2.2 AA 1.4.3, 1.4.11, 2.1.1, 2.2.2, 2.4.7, 2.5.3, 2.5.8, 4.1.3. Doc-only: no code, git or app launch.
