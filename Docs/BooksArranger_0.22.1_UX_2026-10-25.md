# Books Arranger 0.22.1: UX specs (Judy, 2026-10-25)

Basis: backlog items 1 to 4, 6 and 7 (`Docs/BooksArranger_0.22.1_Backlog.md`); rulings 23, 24, 26, 27 and 28 (`Team/Docs/BooksArranger_Rulings_2026-10-24.md`); Ender's fail-less updater proposal (`Docs/BooksArranger_Updater_FailLess_Proposal_2026-10-25.md`; its table D is the draft this spec replaces). Read-only look at v0.22.0 on main: `web/app.js` (retry block L880-1160, connection and poll code L77-135 and L357-412, the `ASK_*` tables L1906-1929, the Delete block L2195-2420), `web/index.html`, `web/style.css`, `web/desktop-ui.js`, `desktop/main.js`, `desktop/update-controller.js`, `desktop/engine-update.js`, `desktop/setup.*`; earlier specs `BooksArranger_RetryButton_Spec.md`, `BooksArranger_AttentionTodo_UX_2026-10-24.md` (the two Delete book specs) and `BooksArranger_MissingFiles_UX_2026-10-24.md`. Nothing launched, no rects measured: geometry is target geometry for Futaba. Contrast ratios are calculated from the `style.css` tokens (on `--surface` #1B2530 unless noted). Titles and paths in mockups are examples. Spec only: no code, not committed. Reworked 2026-10-25: section 3 for ruling 28, and Sergei's answers to questions 1 to 4 applied (section 9).

## In brief

1. **Queued Retry and Delete book (section 1).** A press while another operation runs is accepted and queued, not refused. The row says "Retry queued" or "Delete queued", names what it waits for, and has its own Cancel button. Every check runs again when it runs; a delete whose book or files no longer match is cancelled with a line that says nothing was deleted.
2. **Fail-less updater (section 2).** Final wording for Check for updates, Download update and Restart to update, with one message line per operation, a confirm that names the running work, a Cancel update button, and a line for every failure, and a silent install with no installer window. "Request timed out" is gone.
3. **Startup (section 3, ruling 28).** The real window opens at once and fills in as the engine loads; there is no Starting page and no total time limit. A strip under the title shows the step, how far, and two live clocks, and always reads Working, Waiting or Stuck: Waiting after 10 seconds without progress, Stuck after 30 (with Restart engine), or after 3 and 10 seconds without an answer. Placeholders replace every number and "nothing" until data arrives. Looking works as data appears; anything that changes things waits until loading ends, and says why.
4. **Busy engine (section 4).** In the desktop window a missing answer is always "busy", never "interrupted": the shell already closes the app when the engine process dies. Three tiers of copy, controls stay usable, and no bare "Connection interrupted" or "Local server unavailable" remains in the desktop window.
5. **Delete book on "All files missing" (section 5).** The existing copy is accurate but says the same fact three times. Trimmed to three short lines, and the face "Delete book (no files)" becomes "Delete book".

## Findings that shape these specs

1. **In the desktop app, "no answer" can never mean the engine is gone.** `desktop/main.js` L211-219: when the engine process exits unexpectedly the shell shows its own "Books Arranger stopped" box and closes the app. So every "Connection interrupted" and "Local server unavailable" a user sees inside the desktop window is a false alarm.
2. **One slow press turns the whole page offline.** A press with no reply in 15 s calls `refreshFailed`, which sets `recoveryDisconnected`; every button then reads "Local server unavailable." That is Sergei's Засор and Sigma Force 9 sequence: "Connection interrupted", then "Local server unavailable" on the next press.
3. **"Another operation is in progress" is mostly a window-side lock** (one press at a time, plus bulk runs). Most waits are seconds long. The long ones are bulk runs, scans and, for Delete, the book's own processing. So a queued row must say what it waits for.
4. **Tray "Check for updates" and "Restart to update" report failure in a modal error box** (`reportError`), and the panel buttons use their own face as their tooltip (`button(label)` sets `title=label`). Both are fixed in section 2.
5. **Startup waits blind.** The shell makes Sergei wait up to 3 minutes for the engine before it shows the main window, and on first run the setup window sits on "Checking data folder…" for the whole boot. The page's own defaults also say things that are not known yet: "Select a library and start scanning. Saved results remain available after restart." is visible until data arrives. Sergei, ruling 28: "I don't know if the app started, froze or is just thinking." Section 3 covers it.

---

## 1. Queued Retry and queued Delete book (backlog 2 and 3)

### 1.1 Decisions

1. **A press while blocked is queued.** Retry, Repair and Delete book are no longer disabled for "busy". They stay disabled only when the server says they are not allowed, or in browser mode when the server is really gone.
2. **Only these three queue.** Start over, Let the app handle it, Convert…, Prepare recovery, Keep files, Clear working files, Scan again, Approve, Remove from list and Remove this copy keep the existing disabled state and "Another operation is in progress." (offer 1).
3. **One queue, first in first out, one action at a time.** A fresh press while others wait goes to the back, even if nothing is blocked at that moment. One queued action per row.
4. **The row says what it waits for, and how to cancel.** The face becomes "Retry queued" (inert), a separate "Cancel retry" button sits beside it. Cancel is not the same target as the face, so a double click on Retry can never cancel by accident.
5. **Nothing runs unchecked.** Retry's press already carries the book's revision and job; Delete's carries the confirmed paths. The server compares them at run time. A mismatch cancels the action and says so; Delete says nothing was deleted.
6. **A queued action never opens a dialog, moves focus or makes a sound when it runs.** Its outcome lands in the row, the strip and a polite announcement.
7. **The queue is held by the engine, not the page**, so a page reload, a filter change or a second look all agree. It is in memory only: Quit and updates drop it (decided, Q1: no).

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
| Quit (tray) or a restart while queued | Queued actions are dropped without a prompt (decided, Q1: no). On the next start the rows show their normal buttons. Nothing was deleted or started. |
| Update (section 2) | The update drops the queue. Its confirm says how many (2.4). |
| Another press on a row that already has a queued action | The face is inert; the press does nothing. |
| Retry all runs while Retry presses are queued | Retry all is a blocker (`retry_run`); the queued rows are left out of it ("already queued"). |
| The blocker clears but the next action is also blocked | The action stays queued; its blocker phrase updates at the next poll. |
| The engine is slow when you press | The face shows its pending state with the section 4 slow lines; it never reverts to "Retry" and never invites a second press. |
| The queue is long (12 Retry presses in a row) | Each row shows its own "{n} ahead"; the strip line shows the count. Cancel is per row (offer 2: Cancel all). |

---

## 2. Fail-less updater (backlog 1, ruling 27)

Behaviour (gates, bounds, cancel, install) is Ender's proposal, section 5. This section is wording, states, layout and controls. Decided by Sergei (2026-10-25): the install is silent, with no installer window (Q2: yes), and there is no "After this book" option (Q4: no). T (the safe-point wait, proposed 90 s) and B (the overall bound, proposed 3 minutes) are parameters of the strings: whatever Ender and Sergei settle on is substituted.

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

Enabled whenever an update is downloaded and verified (the idle gate is gone), except while Books Arranger is still loading: then it waits, unless loading is Stuck or Stopped (section 3.6). If work is running, it confirms first; if not, the press starts the update at once.

| Part | String |
| --- | --- |
| Face | Restart to update |
| Tooltip, idle | Install version {new} now. Books Arranger closes, updates and reopens by itself. No installer window opens. |
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
- No "After this book" button (decided, Q4: no): the update stops work safely anyway, so there are two buttons, Cancel and Update now.

### 2.5 While it updates

The `.desktop-status` panel (existing) shows the line; all mutating controls are disabled by the existing `quitting` rule. The seconds counter is its own `span` outside the live region, so a screen reader hears each phase once, not every second.

| Phase | Panel line | Visible buttons |
| --- | --- | --- |
| Request sent | Starting the update… | Cancel update |
| Waiting for a safe point | Stopping safely for the update. Waiting for {what} to reach a safe point… ({s} s of {T} s) | Cancel update |
| A file change is in progress | Finishing {thing} first, so nothing is left half-done. This takes a few seconds. | Cancel update |
| Forced stop | {What} didn't reach a safe point in {T} s. Stopping it now; {restart}. | Cancel update |
| Ending the engine (last resort) | Stopping the engine now. Saved work is kept. | none |
| Installing | Installing {new}… No installer window opens. Books Arranger reopens by itself and shows its loading progress. | none |

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

- **Menu:** "Check for updates" (unchanged); "Restart to update" (shown when an update is downloaded and verified, no idle gate; disabled until loading is finished, or Stuck or Stopped, see 3.8); while an update runs, a disabled "Updating…".
- **Tray "Check for updates" and "Restart to update" show the window and run into the panel.** The modal error boxes "Update check failed" and "Update could not install" are removed; the panel lines are the only place failures appear. (A click on the tray is Sergei's own action, so showing the window is not an intrusion.)
- **Tooltip while updating:** "Books Arranger — updating".

### 2.8 Keyboard, hit areas, theme

- Every button is a native button in the existing toolbar: one Tab stop each, in the order Check, Download, Restart, Cancel update, Show installer file. The dialog traps focus natively; Esc and Cancel return focus to "Restart to update" (`preventScroll`).
- No accelerator. All contrast uses existing tokens: text 13.87:1, `--muted` 8.92:1, `--warning` 11.18:1 on `--surface`.
- No two rects intersect in any state: panel lines stack, buttons wrap, the dialog is the only overlay.

---

## 3. Startup (backlog 4, ruling 28)

Ruling 28 replaces the first draft of this section (a Starting page, then the app, with a 3 or 10 minute limit). Sergei: show the screen first, load after, and always show whether the app is working, waiting or stuck. Numbers in the mockups are examples.

### 3.1 Decisions

1. **The real window opens at once and fills in.** From the first frame the window shows its real layout. Each panel shows a placeholder until its data arrives and shows the data the moment it does. There is no separate Starting page and no total time limit.
2. **One strip says what is happening.** The load strip sits under the title and shows the step, how far, and two live clocks. It always reads **Working**, **Waiting** or **Stuck**, or **Stopped** when the engine process is gone.
3. **The states come from silence, never from total time.** A load that keeps moving can take ten minutes and stays Working. A load that goes quiet turns Waiting after 10 seconds without progress and Stuck after 30 (or after 3 and 10 seconds without any answer from the engine), and Stuck offers an action. The page never gives up by itself and never ends the engine by itself.
4. **Looking is free; changing waits.** Read-only controls work as soon as their data is on screen. Everything that starts, stops, changes or deletes waits until loading ends, and says why.
5. **A placeholder is never a value.** No zero, "Nothing running", "unavailable" or empty-list text shows for data that has not arrived (3.5).
6. **Gone from the first draft:** the Starting page, its Slow and Hard-limit states, the "Keep waiting" button, the 3 or 10 minute limit and the startup error box.

### 3.2 The window, from the first frame

- **Target:** the main window is visible within 2 seconds of the process start, on the 706 MB catalog, before the engine has answered anything. The shell creates it at app ready.
- **The first frame is the real layout.** The engine's web server does not exist for the first second or two, so for that moment the window shows the same screen built locally: the title row, the load strip at Step 1 and every placeholder of 3.5, on `#121820`. When the engine answers, the page it serves takes over. Whether Ender does that as one document or as a swap, Sergei sees no change of window size, position, background, strip position or running clock (the shell passes its launch time), and no white or blank frame.
- **Two channels.** The engine answers the page over HTTP: step, counts, ages, parts. The shell tells the page, through the preload, what only it can know: launch time, the process has exited, the port is taken, the last load's duration. The page merges both. If the process has exited, the shell's word wins: Stopped.
- **Quit is live from the first frame.** It closes at once, with no confirmation: nothing is running but loading. The engine is stopped the way a failed start stops it (its input pipe is closed); Ender confirms that is clean while the catalog is still opening.
- **Window rules unchanged:** `--start-hidden` opens nothing (the tray carries the state, 3.8); `--show-inactive` shows it without focus; the close button hides to the tray; a second launch shows this window. No state change takes focus, makes a sound or raises a hidden window.
- **First run:** after "Use this folder" the setup window closes and the main window opens at Step 1. A folder that cannot be used is refused on the setup form before it closes (Ender validates first); a failure after that is a Stopped state.

### 3.3 The load strip

`section.panel#load-strip`, directly under the header and above the desktop hint. It exists from the first frame until Ready (3.7). Working, mid-load:

```
+-------------------------------------------------------------------------------+
| Working · Step 3 of 4: Checking the last session                              |
| [##############][#######-------][--------------][--------------]              |
| 12,400 of 52,311 files · running 1:12 · engine answered 1 s ago ·             |
| last load took 1 min 39 s                                                     |
+-------------------------------------------------------------------------------+
```

Waiting (quiet for 14 s; the bar stands still):

```
| Waiting · Step 3 of 4: Checking the last session. Nothing new for 14 s.       |
| The engine is still answering.                                                |
| [##############][#######-------][--------------][--------------]              |
| 12,400 of 52,311 files · running 1:26 · engine answered 0 s ago               |
```

Stuck (quiet for 34 s; the current segment is `--warning` and still; the action row appears):

```
| Stuck · Step 3 of 4: Checking the last session. No progress for 34 s. The     |
| engine is answering, but this step has not moved.                             |
| [##############][#######-------][--------------][--------------]              |
| 12,400 of 52,311 files · running 1:46 · engine answered 1 s ago               |
| [ Restart engine ] [ Copy details ]   > Technical details                     |
```

Stopped (the engine process exited):

```
| Stopped · The engine stopped while loading. Your files are not touched.       |
| [##############][#######-------][--------------][--------------]              |
| [ Try again ] [ Copy details ]   > Technical details                          |
```

| Part | Content | Rules |
| --- | --- | --- |
| State line | The state word, then `Step {n} of {N}: {step}`, then the state's own sentence (3.4) | 15 px; the state word is 600 weight; `--warning` for Stuck and Stopped, `--text` otherwise; wraps, never truncates. It is the strip's only live region |
| Bar | One segment per step, equal width, 8 px high, 1 px `--border` outline | Done segments `--accent`. The current segment fills with `done / total`, or, when the step cannot count, shows a moving stripe. Later segments are empty (`--raised`). In Waiting the current segment stands still; in Stuck and Stopped it is `--warning` and still. Equal widths are honest because the line above says "Step 3 of 4"; the bar never claims a percentage of the whole load |
| Detail line | `{done} of {total} {unit}` · `running {m:ss}` · `engine answered {s} s ago` · `last load took {m} min {s} s` | 14 px; parts wrap between, never inside (each part `white-space: nowrap`). `{done} of {total} {unit}` shows only when the step counts; `{done} {unit} so far` when it has no total; omitted when it has neither. "Last load took" is omitted on a first start. Outside the live region |
| Action row | Buttons of 3.4 | Only in Stuck and Stopped. It is the one height change during loading |
| Technical details | `details#load-details`, closed | Only in Stuck and Stopped. Holds the step id, counts, the answer and progress ages, the time loading started, and the last lines of engine output (the text `lastLines` collects now). Raw engine text appears nowhere else |

**The two clocks, and why both.** "Running" is the page's own clock since launch: it always ticks, so on its own it proves nothing. "Engine answered {s} s ago" is the real heartbeat: it bounces between 0 and 1 while the engine replies and climbs when it stops. "Nothing new for {x}" and "No progress for {x}" are the progress clock. Between them Sergei can tell an engine that is moving, an engine that is answering but quiet, and an engine that is silent.

| Format | Rule |
| --- | --- |
| running | `m:ss`; `h:mm:ss` from one hour. From the shell's launch time; never reset by a state change. Restart engine starts a new launch |
| durations ({x}, "ago") | `{s} s` under a minute; `{m} min {s} s` from a minute; `{h} h {m} min` from an hour |
| counts | `toLocaleString()`, as the app does elsewhere. {unit} is `files`, `books` or `items` (an unknown unit reads `items`) |
| clocks | Updated once a second, `font-variant-numeric: tabular-nums`, so digits never reflow the line |
| before the first answer | "engine answered … ago" reads "no answer from the engine yet" |

| Step | Words | Counter, if the engine counts |
| --- | --- | --- |
| 1 | Starting the engine | none (the shell's step: the process is launching) |
| 2 | Opening the catalog | none, or `items` |
| 3 | Checking the last session | `items` |
| 4 | Loading your books | `books` or `files` |

{N} is what the engine reports (4 today). An unknown step id reads "Step {n} of {N}: Loading…". Steps are the engine's order of work; the parts of 3.5 are what the panels show. A part can arrive during any step.

### 3.4 Working, Waiting, Stuck, Stopped

**Thresholds.** The state is the worse of two signals, recomputed every second from timestamps. The page asks the engine at least once a second.

| Signal | Working | Waiting | Stuck |
| --- | --- | --- | --- |
| The engine answers (any reply counts, including "still updating") | last answer under 3 s ago | 3 to 10 s ago | 10 s or more |
| Progress (the step or its counter changed; the engine reports the age) | under 10 s ago | 10 to 30 s ago | 30 s or more |

- **Time alone changes nothing.** A load that keeps moving stays Working for ten minutes. Only silence moves the state.
- **Stuck is not a verdict.** Any new answer or progress recomputes it at once. If loading moves again the strip returns to Working and announces it. The page takes no action by itself.
- **Stopped** is the fourth word and the only one the shell sets: the engine process has exited. It is a fact, not a guess, so it names no threshold.
- **Sleep guard.** A gap of more than 5 seconds in the page's own clock (sleep, a frozen page) restarts both clocks instead of counting the gap. Waking a laptop never shows Stuck.
- **Before the first answer** the engine-silence row applies from the launch: an engine that never answers reads Waiting at 3 s and Stuck at 10 s.
- **The thresholds live in one place in the code** (3 s and 10 s for answers; 10 s and 30 s for progress), so they can be retuned without touching the copy.

**State line.** {x} is the quiet time. The word and the sentence do the work; colour is only a second signal.

| State | State line |
| --- | --- |
| Working | Working · Step {n} of {N}: {step} |
| Waiting, no progress | Waiting · Step {n} of {N}: {step}. Nothing new for {x}. The engine is still answering. |
| Waiting, no answer | Waiting · Step {n} of {N}: {step}. The engine hasn't answered for {x}. |
| Waiting, named cause | Waiting · Step {n} of {N}: {step}. Waiting for {cause} ({x}). |
| Stuck, no progress | Stuck · Step {n} of {N}: {step}. No progress for {x}. The engine is answering, but this step has not moved. |
| Stuck, no answer | Stuck · Step {n} of {N}: {step}. The engine hasn't answered for {x}. It may have stopped responding. |
| Stuck, named cause | Stuck · Step {n} of {N}: {step}. Still waiting for {cause} ({x}). {hint} |
| Stopped, engine exited | Stopped · The engine stopped while loading. Your files are not touched. |
| Stopped, port taken | Stopped · Another copy of Books Arranger is running (process {pid}). Quit it from the tray, then try again. |

A named cause (shown only if the engine reports `waiting_for`) changes the wording, never the thresholds.

| Named cause | {cause} | {hint} |
| --- | --- | --- |
| `drive` | the source drive {root} to answer | Check that the drive is connected. Loading continues by itself when it answers. |
| `file_lock` | another program to release the catalog | Close other programs that use the catalog. Loading continues by itself when it lets go. |

**Actions.** Only in Stuck and Stopped. None asks for confirmation: loading changes nothing, so starting it over loses only time.

| Control | Shown in | Tooltip |
| --- | --- | --- |
| Restart engine | Stuck (desktop only) | Stop the engine and start it again. Loading starts over. Your files are not touched. |
| Restart engine, inert (`restart_safe` false) | Stuck | Not safe right now: the engine is changing the catalog. Wait for it to finish. |
| Try again | Stopped | Start the engine again. |
| Copy details | Stuck, Stopped | Copy the technical message to the clipboard. |
| Technical details (summary) | Stuck, Stopped | Show the technical message. |
| Quit Books Arranger (the existing button, while loading) | always | Stop loading and close Books Arranger. Your files are not touched. |

- Restart engine returns the strip to Step 1, restarts the running clock and keeps "last load took". Try again does the same.
- Update still works from Stuck and Stopped (3.6), so an update can be the way out.
- **Browser mode** (`launch-web`): the strip runs from the engine's own answers; there is no shell channel, no Stopped by exit and no Restart engine button. Copy details stays.

**Announcer** (the state line's live region, polite; never assertive, never a focus move; the counts and clocks are not announced):

| Event | Text |
| --- | --- |
| A step starts | Step {n} of {N}: {step}. |
| Stuck | Loading is stuck. No progress for {x}. Restart engine is available. / Loading is stuck. The engine hasn't answered for {x}. Restart engine is available. |
| Moving again | Loading is moving again. |
| Restart engine pressed | Restarting the engine. |
| Stopped | Books Arranger stopped loading. Try again is available. |
| Ready | Books Arranger is ready. |

Waiting is not announced: it is often brief, and the line is on screen.

### 3.5 Before data arrives

**Parts.** The engine marks five parts ready one by one, in any order. A part arrives whole. Until it does, every place that shows it keeps its placeholder; when it does, only those places change.

| Part | Holds |
| --- | --- |
| library | version, source folders, the Status filter's options |
| status | scan state and the file counts |
| books | the first page of the list, its page count, and whether it is empty |
| attention | the "needs attention" counts and the reason groups |
| jobs | audiobook jobs, automatic processing, research, the operation state |

**Placeholders.** While Working, Waiting or Stuck the words are "loading…"; in Stopped they become "not loaded" (the truth then). Nothing here is a number.

| Place | While loading | Stopped |
| --- | --- | --- |
| Version badge `#version` | hidden | hidden |
| Source folders `#root` | Source folders: loading… | Source folders: not loaded. |
| Library status `#status` | Library status: loading… | Library status: not loaded. |
| Library select `#library` | shows Audiobooks, inert (3.6) | same |
| Automatic processing `#automatic-status`, `#research-status` | Automatic processing: loading… / Research: loading… | …: not loaded. |
| `#automatic-start-reason` | Automatic processing can start when loading finishes. | hidden |
| Audiobook jobs panel (Audiobooks library) | Shown at its reserved height (`#jobs-activity` keeps its 136 px). `#jobs-status` "Jobs: loading…", `#book-candidate-counts` "Book candidates: loading…". `#jobs-idle` is hidden: "Nothing running" appears only after the engine says so. Pause and Resume inert | "Jobs: not loaded." and "Book candidates: not loaded." |
| Status filter `#filter` | one option, "Loading…" | one option, "Not loaded" |
| Reason groups `#attention-groups` | one muted line in its slot: "Output needs attention: loading…". No chips, no "All · 0" | "Output needs attention: not loaded." |
| Book list `#inventory`, `#empty`, `#page` | `#empty` and `#page` read "Loading your books…" (the loading text a filter change already shows); four static bars below it (`--raised`, `aria-hidden`, no shimmer); `aria-busy="true"` on the body | "Your books are not loaded." and no bars |
| Bulk counts ("Select this page", "Retry selected (0)", "Approve as is (0)") and `#error-shortcut`, `#attention-shortcut` | hidden until a count exists. A zero shows only when the engine says 0 | hidden |
| Details `#details` | hidden until a row is opened | hidden |
| Update panel | live; its version comes from the shell | live |

- **Removed outright:** "Connecting to the local catalog…", "Select a library and start scanning. Saved results remain available after restart." (visible by default today, and untrue for a catalog that is full), "status unavailable", "unavailable" for anything not yet loaded, and "Nothing running" before the engine has reported jobs. "Unavailable" is for a failure; "loading…" is for waiting.
- **Rule for Ender:** a missing field is never read as `0`, `''`, `[]` or "empty". Test: answer `/api/state` with each part withheld in turn; no digit appears for it.
- **Running counts** live in the strip only ("12,400 of 52,311 files"). A panel never paints a partial count.
- A part with nothing to show (no reason groups when nothing needs attention) removes its placeholder when it arrives.

### 3.6 What works while loading

Two moments matter: **books on screen** (the books part has arrived) and **loading finished**. Inert controls use `aria-disabled="true"`: still focusable, in the existing disabled look (`--disabled-text` on `--disabled`, 6.07:1), never the `disabled` attribute. A text field is `readonly` with `aria-disabled`.

| Control | Works | Until then: tooltip |
| --- | --- | --- |
| Quit Books Arranger | from the first frame | live (tooltip in 3.4) |
| Check for updates, Download update, Show installer file | from the first frame (they talk to GitHub and the shell, not the catalog) | live (tooltips of section 2) |
| Restart engine, Try again, Copy details, Technical details | in Stuck or Stopped | (3.4) |
| Restart to update (panel and tray) | when loading is finished, or in Stuck or Stopped | Not yet: Books Arranger is still loading. You can update when it finishes, or if loading gets stuck. |
| View, Path contains, Status, Clear filters, Previous, Next | books on screen | Not yet: your books are still loading. This works as soon as they appear. |
| Open a row (its details), View metadata, Open folder, Source folders | books on screen, and the row exists. The details panel opens read-only: every button in it that changes something follows the next rows | Not yet: your books are still loading. This works as soon as they appear. |
| Library | loading finished | Not yet: Books Arranger is still loading. You can switch library when loading finishes. |
| Start scanning, Stop scanning, Resume scanning, Start and Stop automatic processing, Cancel automatic start, Pause and Resume audiobook jobs | loading finished | Not yet: Books Arranger is still loading. This works when loading finishes. |
| Select this page, row checkboxes, Queue selected books, Retry selected, Approve as is, Let the app handle selected | loading finished | the same sentence |
| Every row or details button that changes something: Retry, Repair, Delete book, Scan again, Convert…, Keep files, Start over, Clear working files, Prepare recovery, Approve, Remove from list, Save preview metadata, Find metadata, Create audiobook, Resolve metadata | loading finished | the same sentence |

- **Why this split.** Looking cannot hurt anything and needs only its own data. Changing needs the operation state (is a scan running, is a book queued, what blocks what), which is the last part to be sure of. One rule, easy to explain: look now, change when loading ends.
- **A press on an inert control is answered.** It writes the same sentence into the message line (`#message`, existing `role="status"`) and moves no focus. The sentence is cleared when loading finishes. No sound.
- **No dialog can open** while loading: every control that opens one is inert.
- **Section 1's queue does not apply.** A press that waits for loading is refused with the sentence above, not queued. Retry and Delete book queue behind a running operation, not behind the page's own loading.

### 3.7 Settling

When the engine reports every part ready (or sends no `loading` object):

1. **One render pass.** All placeholders become data; every control inert for loading goes live with its normal tooltip; `aria-busy` is removed; any "Not yet" sentence leaves the message line. No control goes live a moment before its data is there.
2. **The strip becomes one quiet line:** "Ready · Loaded in {m} min {s} s" (or "Loaded in {s} s"), `--muted`, no bar, no clocks, no buttons. It stays for the session. The engine keeps `took_ms`, so a page reload shows the same line.
3. **The announcer says once:** "Books Arranger is ready."
4. **Layout:** the strip shrinking is the only layout change, once, upward, by no more than 48 px. The placeholders were pre-sized (the jobs panel at its reserved height, the book list's bars), so nothing else jumps; a placeholder that has nothing to show leaves a gap of at most one line. If Futaba measures more, the fallback is to reserve the strip's height.
5. **Focus and scroll do not move.** If focus was on a strip button that disappears, it goes to the Status filter (the standing fallback of 1.7). The list growing below the viewport does not scroll the page.
6. **Nothing intrudes:** no sound, no toast, no raised window. A hidden window stays hidden; the tray tooltip returns to "Books Arranger".
7. **The shell saves the load time** as "last load took" for the next start. Only a completed load counts.
8. **After the settle,** section 4 owns slow answers. The strip never returns, except through a new launch (Restart engine, a restart for an update).

### 3.8 Tray

- **Tooltip,** refreshed every 5 seconds (not every second, so a hovered tooltip does not flicker): Working "Books Arranger — loading, step {n} of {N}"; Waiting "Books Arranger — waiting, step {n} of {N}"; Stuck "Books Arranger — stuck at step {n} of {N}"; Stopped "Books Arranger — stopped"; Ready "Books Arranger".
- **Menu:** "Open Books Arranger" shows the real window, at its current state. "Quit Books Arranger" is immediate while loading. "Check for updates" stays live. "Restart to update" (shown when an update is downloaded) is live once loading is finished, or in Stuck or Stopped; before that it is disabled and reads "Restart to update (after loading)".
- A load that turns Stuck while the window is hidden shows only the tooltip. A tray notice is offer 4.

### 3.9 Keyboard, hit areas, theme, motion

- Window title and page title stay "Books Arranger"; one `h1`. The strip is `aria-label="Loading progress"`. Its state line is `role="status"`, `aria-live="polite"`, and is rewritten only when the state or the step changes. The bar is `role="progressbar"` with `aria-valuemin="0"`, `aria-valuemax="{N}"`, `aria-valuenow="{n - 1 + fraction}"` and `aria-valuetext` such as "Step 3 of 4, Checking the last session, 24%" (no percentage when the step cannot count). The detail line and its clocks are outside any live region.
- **No control has initial focus**, as today, so a stray Enter after launch cannot quit. Tab order: Quit and the existing controls in page order; the strip's action buttons directly after the strip's text, then Technical details. No accelerator.
- Buttons are native, at least 96 x 32, wrap, and never sit on top of another element; nothing is absolutely positioned and no overlay exists, so no two rects intersect in any state or at 700 px and 200% zoom. At narrow width the strip's lines wrap between parts and its buttons stack; no horizontal scroll.
- **Contrast on `--surface`:** text 13.87:1, `--muted` 8.92:1, `--warning` 11.18:1. The bar: `--accent` on `--raised` 6.56:1, `--warning` on `--raised` 9.14:1, the `--border` outline on `--surface` 4.13:1 (1.4.11). The skeleton bars are decoration (`aria-hidden`) and carry no information.
- **Motion:** the only motion is the stripe of a step that cannot count, only in Working, and only because the engine reported progress in the last 10 seconds. In Waiting it stops, so a moving bar always means real movement. Under `prefers-reduced-motion` it is a static hatch (as the activity rows already do) and the clocks carry the signal. No shimmer, no spinner, no fade.

---

## 4. Busy-engine feedback (backlog 7)

### 4.1 The rule

**In the desktop window, a missing answer means "busy", never "interrupted".** The shell closes the app itself, with its own message, when the engine process exits (finding 1), so the page never needs to guess. The old strings stay for browser mode (`launch-web`), where the server really can disappear. The page is in desktop mode when `window.booksDesktop` exists, as `desktop-ui.js` already assumes.

- A slow answer sets **no** page-wide offline flag. Buttons stay usable on the last known state; a press goes out and follows the ladder in 4.3.
- "Local server unavailable." is not used in the desktop window.

### 4.2 The top of the page

When the status read (or any request) has had no answer for 3 seconds, after loading has finished (while the load strip of section 3 is up it owns the message, and none of this shows):

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
- The installer runs silently: no installer window, no focus taken, no second window (decided, Q2: yes). The "installer would not start" row of 2.6 still applies if Windows or an antivirus blocks it.

**Startup (section 3)**
- **The engine answers at once** and loads in the background. `GET /api/state` (or a light `GET /api/loading`; Ender's choice) carries `loading: {step, n, of, done, total, unit, progress_age_ms, waiting_for, restart_safe, parts, took_ms}` (names assumed). `step` is `engine`, `catalog`, `session` or `books`. `done` and `total` are `null` when the step cannot count. `progress_age_ms` is the time since the step or the counter last changed (an age, not a clock, so a clock change cannot fake progress). `waiting_for` is `null` or `{kind: 'drive' | 'file_lock', root}`. `restart_safe` is `false` only while the engine is changing the catalog. `parts` says which of `library`, `status`, `books`, `attention` and `jobs` are ready. `took_ms` is set when loading ends and kept for the session. No `loading` object means loaded.
- **A part that has not arrived is absent** from the answer, never `0`, `[]` or `''`. A part arrives whole: no half-filled list, no partial count. A "still updating" 503 counts as an answer.
- **A step changes `done` (or the step) at least every 5 seconds, or reports `waiting_for`.** A step that cannot is a defect to report to Judy; its quiet stretch shows as Waiting. No threshold is lengthened to hide it.
- **Shell to page:** a `books:startup` push and a `startup()` read: `{phase: 'launching' | 'running' | 'stopped', startedAt, lastLoadMs, exited: {code, lastLines} | null, portPid}`. Page to shell: `restartEngine()`. The shell stores the last completed load time (an aborted or restarted load does not count). `quit()` during loading closes at once.

**Busy (section 4)**
- The page keeps the time of the last answer per library and its last status text (today it keeps only the text).

## 7. Changes Ender must make

1. `app.js`: Retry, Repair and Delete book are enabled while blocked and send `queue: true`; the queued face, Cancel, siblings inert, hint, tooltips and strip line of 1.3 and 1.4; read queue state from `/api/state`; the outcome table of 1.6. The details-panel pair in `#retry-block`.
2. `index.html`: `#delete-dialog-blocked`, `#delete-dialog-recheck`, the Queuing state; `p#queue-line`; `p#queue-announce`; `update-dialog`; the three update lines and the Cancel update and Show installer file buttons; real tooltips on every update button.
3. `style.css`: no new tokens. `#queue-announce` is visually hidden (1 x 1 px, clipped, placed after the footer, intersecting nothing); `#delete-dialog-blocked` uses `--warning`.
4. Delete dialog: n = 0 copy of 5.2. Preview `blocked` handling (1.5).
5. `desktop-ui.js`: the update panel of section 2, `aria-disabled` on busy buttons, the phase table of 2.5 and the counter outside the live region. The shell channel for the load strip (launch time, exit, port) reaches the page here too.
6. `desktop/main.js`: create the main window at app ready, without waiting for the engine, and show the first frame of 3.2; the 3-minute deadline in `waitForBackend` and `showErrorBox` for startup are gone (the shell waits only for the engine's first answer, then watches); push `books:startup` and add `restartEngine()`; Quit during loading closes at once; Stopped for an exited engine or a taken port (Technical details holds `lastLines`); tray tooltip and menu of 3.8; the tray's "Check for updates" and "Restart to update" show the window; the first-run setup window closes and the main window opens at Step 1; remove `showErrorBox` for update failures.
7. `app.js` connection code: desktop mode never sets the offline flag for a slow answer; the notice, status line and ladder of section 4; keep the old strings for browser mode. While the load strip (section 3) is up, the notice, the status prefix and the ladder stay off.
8. Tests (front end): the queued state for each of the three actions; Cancel; "too late"; every cancel line; the blocked Delete dialog; every Check, Download, Install line; the load strip's states from answer times and progress ages with a fake clock (3 s and 10 s without an answer, 10 s and 30 s without progress, the sleep gap, Stopped); every part withheld in turn renders no digit; every control that waits for loading has its tooltip; the ladder; no `Connection interrupted` or `Local server unavailable` in the desktop build; every new control has a tooltip.
9. `app.js`, `index.html`, `style.css` (loading, section 3): `section#load-strip` with its live line (`role="status"`), segmented bar (`role="progressbar"`), detail line, buttons and `details#load-details`; the state evaluator (two clocks from answer times and progress ages, the thresholds of 3.4, a one-second tick, the sleep-gap rule); the part model, so every panel renders its placeholder until its part arrives and never falls through to `0` or empty-list text (3.5); one `loading` condition feeding `controls()` for the inert states of 3.6 (`aria-disabled`, the two tooltip sentences, the message-line feedback on a press); the settle render of 3.7. No new colour tokens.

## 8. Checks for Futaba (committed build, seeded fixture, no real library, nothing on Z:)

1. **Queue Retry:** hold an operation open (a bulk run or a stub-slowed press), press Retry on a Stopped row. The face reads "Retry queued", Cancel retry appears beside it, the hint names the blocker, the tooltips match 1.4. Release the blocker: the row runs ("Checking…", then the existing queued states). Control: on the 0.22.0 build the button is disabled with "Another operation is in progress."
2. **Order and count:** queue three rows. "{n} ahead" reads 0, 1, 2 (first reads without it); the strip line says "3 actions queued."; they run one at a time in order; a fourth press while idle but queued goes behind.
3. **Cancel:** Cancel retry returns the row to Retry, nothing starts, focus is on the restored button. Cancel pressed as it starts: "Too late to cancel: the retry has already started." A double click on "Retry queued" does nothing.
4. **Queue Delete:** on a Missing files row with a scan running, press Delete book. The dialog shows the blocked line, the "when it runs" Files line, the re-check line and "Queue delete of {n} files". Cancel is focused; Enter on it cancels; Enter in the body does nothing. Confirm: dialog closes, "Delete queued", siblings inert with their tooltip, focus on the face.
5. **Run:** end the scan: the files go, the record goes, the strip reads "Queued delete finished: {title}. …", the row leaves, and **no dialog opens and focus does not move** if it was elsewhere. SHA-256 of a sibling book's file and Sorted unchanged.
6. **Run-time cancel, each verbatim, nothing deleted:** change the book's revision; add a file to the folder; make one file shared; place a finished audiobook in Sorted; take the source drive offline; remove the row while queued. Each shows its line of 1.6. Control: the same queue without the change deletes.
7. **Partial:** hold one file open while queued. The row names it with "In use by another program.", the other files are gone, the book stays listed, and Delete book returns.
8. **Quit with a queue:** Quit, reopen: rows show their normal buttons; nothing was deleted or started; no prompt appeared at Quit.
9. **Updater, each state verbatim:** local feed per Ender's section 5E. Check: idle, checking, retrying, up to date, available, no answer (black-holed GitHub, 3 tries), no internet, GitHub error. Download: progress, ready, dropped, checksum. Restart: idle (no dialog), work running (dialog lists the right lines and the queue line), Cancel, Update now (no installer window opens and focus does not move), each phase line, Cancel update during the wait, the bound, installer blocked (with the path and Show installer file), changed file. No "Request timed out" anywhere (search the page and the tray). Tooltips are sentences, not copies of the face.
10. **Tray:** "Check for updates" and "Restart to update" open the window and show their result in the panel; no modal error box appears.
11. **Startup (ruling 28),** committed build, on the 706 MB copy, with a stub engine that can be stalled, silenced or killed. Control for the whole item: the same launch on 0.22.0 shows no window until the engine answers, then "Connecting to the local catalog…".
    - **First frame:** the window is visible within 2 s of the process start with the real title, the load strip at Step 1 and every placeholder of 3.5. No blank or white frame. Quit Books Arranger works at once and closes with no prompt.
    - **Hand-over:** when the engine answers, the running clock does not reset; window size, position and background do not change; the rect of Quit Books Arranger and of the strip do not move.
    - **No false values:** withhold each part of the state in turn (library, status, books, attention, jobs). While it is missing no digit, "0", "Nothing running", "unavailable" or "Select a library and start scanning…" appears; its placeholder reads exactly as 3.5.
    - **Controls (3.6):** each inert control shows its exact tooltip; pressing it writes the same sentence in the message line and moves no focus; read-only controls go live when the books appear; every control that changes something stays inert until loading ends.
    - **Working to Stuck:** freeze the stub's progress while it still answers. Working for 10 s, then Waiting ("Nothing new for {x}. The engine is still answering."), then at 30 s Stuck with Restart engine, Copy details and Technical details. Resume the progress: Working again and the announcement "Loading is moving again." Silence the stub instead: Waiting at 3 s, Stuck at 10 s with the engine-quiet line. A named cause (drive, file lock) shows its own wording and hint.
    - **Time alone changes nothing:** a stub that keeps reporting progress for 10 minutes stays Working the whole time. Jump the page's clock by 60 s (sleep): no Stuck.
    - **Restart engine:** Step 1 returns, the running clock restarts, "last load took" is unchanged, nothing else moves. With `restart_safe` false the button is inert with its tooltip.
    - **Stopped:** a stub that exits shows the Stopped line, its last lines in Technical details, Try again and Copy details; a taken port shows the process line. Placeholders read "not loaded".
    - **Settle:** one render. Every control is live with its normal tooltip; the strip reads "Ready · Loaded in {m} min {s} s" (or "{s} s"); the layout shifts once, upward, by no more than 48 px (measure Quit Books Arranger before and after); focus and scroll do not move; no sound, toast or raised window. With the window hidden nothing appears and the tray tooltip returns to "Books Arranger".
    - **Memory:** "last load took" is right on the second start and absent on the first.
    - **Window rules:** `--start-hidden` shows nothing; closing hides to the tray; Open Books Arranger returns to the current state; a second launch shows this window.
    - **First run:** the setup window closes and the main window opens at Step 1; an unusable folder is refused on the setup form.
    - **Browser mode (`launch-web`):** the strip works from the engine's own answers; there is no Restart engine button.
12. **Busy engine** (after loading ends; while the load strip is up it owns the message and no section 4 notice shows): start the three background passes (re-check, series, research) on the real-catalog copy. The notice, "Busy with:" line and "Last update {time}" appear after 3 s; at 2 min the second notice. Presses show the ladder; none says "Connection interrupted", "Local server unavailable" or "Retrying…". Controls stay usable. Control: the same run on 0.22.0 shows the old strings. Browser mode still shows the old strings.
13. **Delete on All files missing:** the dialog reads exactly 5.2; the face is "Delete book"; the row leaves; Remove from list is untouched.
14. **Layout, every state above (the load strip in Working, Waiting, Stuck, Stopped and Ready):** no two rects intersect at 1440, 1024, 700 and 200% zoom; no horizontal scroll; focus rings not clipped; `#queue-announce` intersects nothing; contrast measured in the build matches the ratios cited.

## 9. Decided, and offers

**Decided by Sergei (2026-10-25, with ruling 28)**
1. **Queued actions do not survive closing the app** (Q1: no). Nothing is deleted or started while he is away; the rows return to normal. Applied in 1.1 and 1.8.
2. **Updates install silently, with no installer window** (Q2: yes). The installer window would take focus. Applied in 2.4, 2.5 and section 6.
3. **The startup limit is gone** (Q3, replaced by ruling 28). He rejected both 3 and 10 minutes: "Why such huge limits? Show me the screen and load whatever you want after." The screen opens at once, there is no total limit, and the states come from silence (section 3).
4. **No "After this book" button on Restart to update** (Q4: no). The update stops work safely anyway. Applied in 2.4.

**Questions for Sergei:** none open. The stated thresholds in 3.4 (3 and 10 seconds without an answer, 10 and 30 seconds without progress) are my call; each is one constant, so Ender can retune them without touching the copy.

**Offers (not specced)**
1. Queue the other actions too (Approve, Remove this copy, Scan again) with the same mechanism.
2. "Cancel all queued" in the strip, shown from 2 queued actions.
3. One "Delete all {n}" for All files missing rows, with one confirm listing the titles, if there are many.
4. A tray notice when a queued delete or an update step ends, or loading turns Stuck, while the window is hidden.
5. Copy audit: the Delete family uses "..." in its pending faces ("Checking...", "Deleting...") while the rest uses "…". New strings here use "…".
6. Typical step times on the load strip ("usually about 40 s") once several launches have been measured. Section 3 shows only live facts until then.

Design basis: Doherty and NN/g visibility of system status (the window answers at once; every wait shows live progress and one of three states, decided by silence, not by total time), Fitts (the destructive button stays the farthest target; Cancel is a different target from the face), Hick (one queue, two cancels, no menu), Jakob (Windows "Restart to update", native dialogs, tray behaviour), NN/g visibility of status (every wait says what it waits for), error prevention (re-check at run time, Cancel default, Enter never confirms), plain-language recovery (every failure names the cause and the fix), and truth over reassurance ("Nothing was deleted" only for a refusal before the first file; "may still go through" for a press with no answer); WCAG 2.2 AA 1.4.3, 1.4.11, 2.1.1, 2.2.2, 2.4.7, 2.5.3, 2.5.8, 4.1.3. Doc-only: no code, git or app launch.
