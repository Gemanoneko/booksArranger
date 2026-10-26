# Books Arranger 0.22.2: UX spec (Judy, 2026-10-26)

Basis: the "0.22.2" parts of `Docs/BooksArranger_0.22.1_Backlog.md`; rulings 27 to 31 (`Team/Docs/BooksArranger_Rulings_2026-10-24.md`); my 0.22.1 spec (`Docs/BooksArranger_0.22.1_UX_2026-10-25.md`, called "0.22.1 spec"); the to-do spec (`Docs/BooksArranger_AttentionTodo_UX_2026-10-24.md`); Futaba's 0.22.1 QA (m-12, m-13, m-14). Read-only look at v0.22.1 on main: `web/app.js` (`rowState`, `askText`, `askFieldPlan`, `buildAskFields`, `updateAskRow`, `renderRows`, `deleteConfirm`), `web/desktop-ui.js`, `web/style.css`, `desktop/main.js` (tray, `installUpdate`, `restartEngineAfterUpdate`, `chooseCatalog`, `handleCommand`), `desktop/update-controller.js`, `desktop/setup.*`, `merge_service.py` (`ask_payload`, `approval_preview`, `answer_same_author`), `organization.py`, `author_rules.py`. Nothing launched, no rects measured: geometry is target geometry for Futaba. Titles and paths in mockups are examples, not live rows. Spec only: no code, not committed. Only what is new or changed since the 0.22.1 spec is here; everything else stands.

## In brief

1. **Editing (section 1).** An "Edit names" button on every book row opens an editor in the row: Title, Author, Series, Number, Universe, Collection. **Save** records and remembers; **Approve** records and approves. A queued job follows the correction or is cancelled, and never runs under the old names. A running job blocks the edit. Corrections are lasting rules with a count before saving and a "Forget" to take them back.
2. **Collections in a series (section 2).** One "Place" line on the row: `Collection · Series: … · No. …`. The Goes to line is the planner's path, verbatim.
3. **Universes (section 3).** Same Place line (`Universe: … · Series: … · No. …`). Confirm by Approve, change in the editor, with a pick-list of existing universes so a typo can't make a new folder.
4. **Waiting for the original title (section 4).** A new row state with its fallback stated, two ways out (Approve, or type the English title), and a fact in the details panel afterwards.
5. **Delete (section 5).** The row leaves in the same render as the answer, and a stale list can't bring it back.
6. **Updater (section 6).** A failed install keeps the app open with the existing line plus a tray tooltip; Cancel update answers within 1 s and keeps its focus; the confirm names an approval and tells the truth about what comes back.
7. **First run (section 7).** Hidden start shows no form (tray only); `--quit` leaves nothing running; the form's controls get tooltips.
8. **m-13 and m-14 (section 8).** The Same author? card shows names without underscores; Latin "Given Surname" prefill is one yes/no for Sergei.

---

## 1. Editing on every row

### 1.1 Decisions

1. **One button on every book row:** "Edit names", in the Actions cell after the row's own buttons and before View metadata. The Files view has none (a file is not a book). A row with no file left shows it inert.
2. **One editor, in the Review status cell**, in the slot where the question fields already sit. Title and Author are the same inputs and the same draft as the ask fields, never shown twice. On Author unclear and Same author? rows the Author control stays the radio group (its "Other" is the typed name). The editor adds Series, Number, Universe and Collection.
3. **Save records. Approve records and approves.** Save never converts, moves, queues or removes a file. Approve is unchanged and still saves what is typed.
4. **Entered values are Sergei's** (ruling 6a, "Entered by you") **and lasting** (1.5). The editor says how many books a name fix reaches before he saves.
5. **A job that has not started follows the correction. A running one blocks the edit. A finished one only remembers** (1.4).
6. **He can take a correction back** from the same editor (Forget).
7. **Values load when the editor opens**, one read for one row, not for every row of the page (the preview costs about 0.3 s per row).

### 1.2 Where it goes

The worked example is Sergei's «Пртоколы SCP» row, "Waiting for retry checks", which has no fields today. Editor open:

```
[ ] Пртоколы SCP. Сейф №1  ·  Разные авторы  ·  1 audio file
    Waiting for retry checks                                 [ Edit names ] [ View metadata ]
    The book is checked again before it runs.                [ Source folders ]
    Title    [ Сейф №1                 ]  Author  [ Разные авторы     ]
    Series   [ Протоколы SCP           ]  Number  [ 1                 ]
             New series: nothing is filed there yet.
    Universe [ None                    ]  [x] Collection of stories
    Saved values are remembered, so a new scan of these files uses them. Applies to 3 books.
    Place    Collection · Series: Протоколы SCP · No. 1
    Goes to  Audiobooks Sorted\Сборники\Протоколы SCP\Протоколы SCP - 1 - Сейф №1 - Разные авторы.m4b
    [ Save ] [ Discard ]
    Remembered for this book
      Series: «Пртоколы SCP» → «Протоколы SCP»                                      [ Forget ]
```

Closed again (a saved row, still queued):

```
[ ] Пртоколы SCP. Сейф №1  ·  Разные авторы  ·  1 audio file
    Waiting for retry checks                                 [ Edit names ] [ View metadata ]
    Saved. The queued job uses these names.                  [ Source folders ]
    Collection · Series: Протоколы SCP · No. 1
    Entered by you: series, number, collection.
    Goes to  Audiobooks Sorted\Сборники\Протоколы SCP\Протоколы SCP - 1 - Сейф №1 - Разные авторы.m4b
```

- **Cell order, top to bottom** (0.22.1 spec 3, extended): Status, reason sentence or hint, Also, editor or ask fields, basis lines, missing or hold list, **Place** (new), **Entered by you** (new), Goes to, recording marker.
- **Place and Entered are `p.field-help`** (muted, 8.92:1) and the only new lines on a closed row. While the editor is open, Place and Goes to follow the draft.
- The path pattern in the mockup is the planner's existing `Series - Number - Title - Author`. The backlog example reads `Протоколы SCP 1 - Сейф №1 - Разные авторы.m4b`; Ender confirms the pattern, and the row shows whatever the planner returns. The Goes to line is never composed by the page.
- **Layout:** the fields use the existing `.ask-grid` (auto-fit, minimum 200 px, gap 8), so they stack in a narrow cell. Inputs are 32 high with visible labels above; the checkbox box is 24 x 24 in a 32 high row; Save and Discard in a wrapping `.row-actions`-style row under the fields. Nothing is absolutely positioned; the only overlay is the browser's own pick-list.
- **The list window grows with the viewport while any editor is open**, in every filter (the `tall` rule that Output needs attention already has), so an open editor is never clipped by the fixed 430 px window.
- Rows are never rebuilt while a control inside has focus (existing rule); values update in place.

### 1.3 Save, Approve, and each kind of row

| Row | Its own button | Save does | Approve |
| --- | --- | --- | --- |
| A question (Title or author, Author unclear, Name taken, Part of a bigger book, Files unclear, Order unclear) | Approve | Records and remembers. The row stays listed; the Goes to line follows. | Unchanged. Records, then approves with the values shown. |
| Waiting for the original title (section 4) | Approve | Records. The title entered is used; the wait ends. | Stops the wait and files the book as shown. |
| Stopped (Retry, Repair, Convert…), Held, Paused | its own | Records. The next attempt uses these names. | none |
| Waiting for retry checks, Queued (not started) | none | Records. The job follows (1.4). | none |
| Processing (converting, creating, verifying, publishing) | none | not possible: Edit names is inert | none |
| Audiobook Ready | none | Records and remembers only. The file in Audiobooks Sorted is not touched. | none |

- Ctrl+Enter in an editor field presses **Approve where the row has one** (unchanged), else **Save**. Enter alone does nothing but refresh the Goes to line (existing rule).
- **Series and Number go together.** Series without a Number, or a Number without a Series, makes Save and Approve inert with the tooltips in 1.6 (the planner refuses an invented number).
- **Bulk "Approve as is"** leaves out a row with an unsaved editor draft, as it already does for typed text, and counts it in "left out".
- **Unsaved edits in the details panel** keep Save inert with the existing sentence (one draft, one writer).

### 1.4 A queued job

The invariant: **after Save, no job starts under the old names.** The engine does it one of two ways and answers which; the page words both.

| The book's job | Save | Row line |
| --- | --- | --- |
| None | Nothing to follow; the row's family line of 1.6 applies | 1.6 |
| A saved retry request not yet checked ("Waiting for retry checks") | The check reads the new names | Saved. The queued job uses these names. |
| A queued job that has not started | The job is re-planned with the new names and keeps its place | Saved. The queued job uses these names. |
| A queued job that cannot be re-planned | The job is cancelled, nothing runs | Saved. The queued job is cancelled. Press Retry to queue it with these names. |
| Running | Refused, nothing saved | This book is converting. Its names can't change now. |
| A Retry, Repair or Delete queued from the row (0.22.1 queue) | Edit names is inert (one queued action per row) | tooltip in 1.6 |

### 1.5 Lasting corrections

- **What is remembered:** each saved value for this book's files (title, author, series, number, universe, collection), recorded as "Entered by you". It survives a new scan, a regroup and a Retry. It is append-only: a newer entry wins, a Forget takes one back. Same shape as the author rules.
- **A name fix reaches every book that reads the same text under the same author or folder.** Series «Пртоколы SCP» typed once fixes the three Сейф books; a title is never fixed across authors (a "Сказка" by another author is untouched). Authors keep their own rules: a name fix on an author goes through the existing author rules, as a typed author does today.
- **The count is shown before Save**, under the fields: "Applies to {n} books." (only when n is more than 1). It is the books the fix would reach, this one included.
- **Forget** sits in the editor under "Remembered for this book", one line per entry: `{Field}: «{from}» → «{to}»` (or `{Field}: «{to}»` when the files said nothing). It behaves like Save with the old values (same row lines), touches no file, and the books it reached are checked again.
- **No global list this release.** The editor is where he sees and undoes a correction (offer 1).

### 1.6 Strings

New strings use "…". Accessible names start with the visible label: "Edit names: {title clue}", "Series: {title clue}", and so on.

| Control | Face | Tooltip |
| --- | --- | --- |
| Edit names | Edit names | Correct this book's title, author, series or universe. Nothing is converted or moved. |
| Edit names, converting | same, `aria-disabled` | This book is converting. Its names can't change now. |
| Edit names, queued action | same, `aria-disabled` | A retry is queued for this book. Cancel it to use this. / A repair is queued for this book. Cancel it to use this. / A delete is queued for this book. Cancel it to use this. |
| Edit names, no file left | same, `aria-disabled` | No files are left for this book. |
| Title, Author | Title, Author | existing tooltips |
| Series | Series (placeholder "None") | The series this book belongs to. Leave empty for a standalone book. |
| Number | Number | The book's number in its series. Needed when a series is set. |
| Universe | Universe (placeholder "None") | The shared universe this book belongs to, such as Warhammer 40,000. Leave empty if none. |
| Collection | Collection of stories | File this book under Сборники. Use it for story collections by several authors. |
| Save | Save | Save these values and remember them for other scans of these files. Nothing is converted or moved. |
| Save, pending | Saving… | Saving these names… |
| Save, nothing changed | Save, inert | Change a value first. |
| Save, empty title | Save, inert | Type a title first. |
| Save, series without number | Save, inert | Type the number in the series, or clear the series. |
| Save, number without series | Save, inert | Type the series name, or clear the number. |
| Save or Approve, panel edits | inert | Save or discard the edits in the details panel first. |
| Discard | Discard | Throw away these changes. Nothing is saved. |
| Forget | Forget | Take this correction back. Nothing is renamed or moved. |

**Lines in the editor** (`p.field-help`):

| Where | String |
| --- | --- |
| Under Series or Universe, a value not in the pick-list and different from the proposal | New series: nothing is filed there yet. / New universe: nothing is filed there yet. |
| Basis, when the value is a guess | Series from the folder name. / Universe from the folder name. / Universe from the file name. (a tag needs no line) |
| Scope, under the fields | Saved values are remembered, so a new scan of these files uses them. {Applies to {n} books.} |
| Remembered list heading | Remembered for this book |

**Row lines after a press** (hint; normal colour, refusals `--warning`). The strip says "Saved names for {title}." plus " Applies to {n} books." when n is more than 1.

| Case | Hint |
| --- | --- |
| Question row | Saved. Approve uses these names. |
| Stopped row | Saved. Retry uses these names. / Saved. Repair uses these names. / Saved. The next attempt uses these names. |
| Queued, re-planned or checked later | Saved. The queued job uses these names. |
| Queued, cancelled | Saved. The queued job is cancelled. Press Retry to queue it with these names. |
| Waiting for the original title | Saved. The title is used as entered. |
| Held or paused | Saved. These names are used when it converts. |
| Audiobook Ready | Saved. The finished audiobook in Audiobooks Sorted keeps its name. |
| Forget | Forgotten. Nothing is renamed or moved. |
| Refused | Save was not accepted. Nothing was changed. |
| Book changed | This book changed. Review its details and try again. (existing) |
| No answer | the Approve line of 0.22.1 spec 4.3: This hasn't been confirmed yet. The app is busy with background work, so it may still go through. Check this row in a moment. |

### 1.7 Keyboard and states

- **Tab order:** row, Select, editor fields in reading order (Title, Author, Series, Number, Universe, Collection), Save, Discard, Forget, then the Actions cell (primary, Edit names, View metadata, Source folders). Edit names is a native button with `aria-expanded` and `aria-controls`; pressing it while the editor is open moves focus to Title. Save and Discard are the only ways to close it.
- **Esc** closes the editor only when nothing is changed; with changes it does nothing (no silent loss of typing). The draft lives in memory per book and survives polls, paging and chip changes.
- **After Save or Discard,** focus returns to the row's Edit names (`preventScroll`). A row that leaves (it was approved, or the filter no longer lists it) hands focus on as today.
- **Fields stop clicks and keys reaching the row** (existing guard).
- **While loading (0.22.1 spec 3.6):** Edit names opens as soon as the books are on screen (it only reads). Save, Approve and Forget wait for loading, with the existing sentence.
- **Hit areas:** buttons at least 96 x 32; inputs 32 high, at least 160 wide.

---

## 2. Collections in a series

- **Rule:** a collection that belongs to a series files under `Сборники\<Series>\`, with the series and number in the file name. A collection with no number is filed as today (`Сборники\<Title> - Разные авторы.m4b`), no series folder, and the Place line is absent. Number is required with Series (1.3).
- **The Place line** (new `p.book-place`, muted, directly above Goes to) shows series and position for a collection. It is shown for **collections that have a series and for universe books** (section 3), the two cases whose first folder is not the author in the Author column. An ordinary series book keeps today's row; its series is in the editor and in Goes to.

| Case | Place line |
| --- | --- |
| Collection in a series | Collection · Series: Протоколы SCP · No. 1 |
| Collection, no series | (no line) |
| Universe, series and number | Universe: Warhammer 40,000 · Series: Horus Heresy · No. 1 |
| Universe, no series | Universe: Warhammer 40,000 |

- Parts appear in that order and only when set. The values are the stored ones; the list never researches a row for this line.
- **Entered by you** (new `p.field-help`, below Place): `Entered by you: title, series.` The fields Sergei entered, in editor order, joined by commas. It is the lasting mark that a row carries a correction; absent when none.
- The Collection checkbox is how Sergei marks or unmarks a collection. When the app already treats the book as one (it files under Сборники), the box is checked and the Author field reads Разные авторы.

## 3. Universes (ruling 30)

- **Goes to** is the planner's path in full. For a universe book the first folder is the universe, then the series, then the file: `Audiobooks Sorted\Warhammer 40,000\Horus Heresy\Horus Heresy - 1 - Horus Rising - Abnett Dan.m4b`. The page does not restyle segments; the Place line names the universe so nobody has to guess whether the first folder is an author.
- **Confirm:** a universe the app found shows on the Place line and in the editor's Universe field with its basis ("Universe from the folder name."). Approve, or no action, confirms it. Nothing is asked.
- **Change or add:** Edit names, Universe field. Type a name, pick one, or clear it to take the book out of its universe. The Goes to line follows (500 ms debounce, as the other fields). Series and Number are set in the same editor.
- **A pick-list prevents typos.** Universe and Series are text inputs with a native pick-list (`datalist`) of the names already in use. A name not in it shows "New universe: nothing is filed there yet." so a mistyped long name such as "Вселенная Дозоров - Межавторский" is visible before it makes a second folder.
- **Misses.** A book the app did not route (the Сын Дога case) gets its universe by the same editor on any row, finished ones included. On a finished book Save remembers, says "Saved. The finished audiobook in Audiobooks Sorted keeps its name.", and the later rename pass moves the file.
- Strings: all in 1.6 and section 2. No new chip, no new question.

## 4. Waiting for the original title (ruling 29)

```
[ ] Призрак дома на холме  ·  Shirley Jackson  ·  1 audio file
    Waiting for the original title                           [ Approve ] [ Edit names ]
    Looking for its English title. If none is found, it      [ View metadata ] [ Open folder ]
    converts under the Russian title.
    If none is found, goes to  Audiobooks Sorted\Jackson Shirley\Призрак дома на холме - Jackson Shirley.m4b
```

| Part | String |
| --- | --- |
| Status | Waiting for the original title |
| Hint | Looking for its English title. If none is found, it converts under the Russian title. |
| Goes-to label | If none is found, goes to (the path is what Approve would file now, so the worst case is visible) |
| Approve tooltip | Stop waiting: file this book as shown. Converts if needed, renames, moves to Audiobooks Sorted. |
| Title help in the editor | Type the English title to stop waiting. |
| Details panel, new fact "Original title" | Waiting for an English title. / Not found. Filed under the Russian title. / {English title} / Entered by you. |

- **It is not in Output needs attention.** The app ends this wait by itself, and nothing is wrong. It must still be findable: by search, and under the Status filter that lists automatic waits. Ender confirms which existing filter that is and adds the state to it if none lists it. No new chip.
- **Two ways out, both Sergei's:** Approve (convert under the title shown, ruling 6b), or Edit names, type the English title, Save (his entry is authoritative; research stops).
- **When a title is found,** the row moves on to its normal state (Queued, Processing) and the Goes to label returns to "Goes to" with the new path. No message.
- **When none is found,** the book converts under the Russian title with no question, and the fact above says so.

## 5. A deleted book's row leaves at once

- **Expected:** at the answer that says the book is gone, in the same render, the row is removed, every count drops (chip, All, shortcut, Jobs line, page count, "Select this page"), and the strip says the result. No row ever shows "Deleted. The book is gone from the app." Not for one poll, not after a re-read.
- **A stale list cannot bring it back.** The page keeps the deleted book's id out of every list render until a list answer arrives without it. The engine drops its cached lists and counts before it answers.
- **Two suspects for Ender, both to be ruled out** (the Sigma Force 9 "All files missing" row): the engine's cached list, and the page's rule that a settled row which holds focus stays until the next full rebuild (`renderRows`, `!tr.contains(focused)`). For a deleted book that rule does not apply: focus moves on first (below), then the row is removed in the same render.
- **Copy, existing:** the strip line of 0.22.1 spec 1.6 and `deleteStrip` ("Deleted 1 book. No files were left on disk." and its variants). A queued delete uses "Queued delete finished: {title}. …".
- Focus: unchanged (next row's first working control, else the Status filter).
- Measured by Futaba: no row 1 s after the answer, with a stub that still lists the book.

## 6. Updater

Wording of 0.22.1 spec sections 2 and 12 stands. Only these change or are new.

### 6.1 A failed install keeps the app open (M-1)

- **Invariant:** after "Update now" the app exits only when the installer process exists. A failed start never closes the window or the tray.
- **What he sees:** the panel line "Installing {new}…" turns into the Install line at once (within 10 s, the shell's own bound): the existing "The installer couldn't start (tried {HH:MM}). Windows or your antivirus may have blocked it. Books Arranger is running again on {old}. Run the installer yourself:" with the path line and "Show installer file". The loading strip shows while the old engine loads again (3.3 of the 0.22.1 spec). "Restart to update" returns, because the update is still downloaded and verified.
- **If the old engine cannot start,** only the existing line "Books Arranger couldn't restart its engine (tried {HH:MM}). Choose Quit Books Arranger in the tray, then open it again." shows, never both. A relaunch after a failed install always opens the existing catalog (a first-run "New catalog" in the same session is not repeated).
- **Window hidden or closed to the tray at that moment:** nothing is raised and no sound. New tray tooltip: `Books Arranger — update didn't install`. It stays until the window is shown or a new update starts.

### 6.2 Cancel update answers within 1 s (m-2)

The page writes the line at the press, not at the engine's answer. Cancel stays on screen with its focus (it is hidden today, which drops focus and leaves the old counter running).

| Moment | Panel line | Cancel update | Quit tooltip and press |
| --- | --- | --- | --- |
| Press, up to 1 s | Cancelling the update… | face Cancelling…, `aria-disabled`, tooltip "Cancelling can't be stopped." | The update is being cancelled. Quit works when it finishes. |
| 3 s or more, engine still resuming | Cancelling the update… {What} is slow to resume. This can take up to {R} s. | same | same |
| Answered | the panel hides; Install line "Update cancelled. Books Arranger is running as before." (existing; the work-did-not-restart variants of 12 stand) | hidden | normal |

- {What} is the work still resuming, as the existing `what()` names it, capitalised. {R} is the engine's resume bound in seconds (25 today). With no name known, the second line reads "Cancelling the update… The engine is resuming. This can take up to {R} s."
- The "(n s of T s)" counter is dropped from the moment of the press. Controls stay inert as the existing `quitting` rule has them.
- The old Quit sentence "Books Arranger is installing an update and reopens by itself." is wrong while cancelling; the row above replaces it.

### 6.3 Restart to update under load (m-1)

- **Expected:** a conversion and an approval together reach their safe points in seconds, not the whole safe-point window. The phase line names every work still holding it, and each name leaves the line when that work stops (existing: "Stopping safely for the update. Waiting for the conversion of {Title} and an approval to reach a safe point… (12 s of 90 s)").
- **The confirm names an approval** (new line, shown only while one is running):

| Part | String |
| --- | --- |
| Approval line | An approval in progress stops, and the book is not approved. Press Approve again afterwards. / {n} approvals in progress stop, and those books are not approved. Press Approve again afterwards. |

- **The conversion lines tell the truth about what comes back** (Futaba m-11: the job comes back Paused). Ender confirms Paused; the strings replace "starts again from the beginning" and "it restarts after the update":

| Part | String |
| --- | --- |
| Confirm, conversion | Converting {Title}. It stops. Continue it with Resume audiobook jobs. |
| Forced stop, conversions only | {What} didn't reach a safe point in {T} s. Stopping it now; continue it with Resume audiobook jobs. |

- Every other phase, the confirm's other lines and the tooltips are unchanged. m-4 (a cut download) needs no new copy: the existing "the connection dropped" line is the one.

## 7. The first-run window

- **`--start-hidden`:** no form opens. The tray icon exists from the start and carries the state; nothing is raised, no sound. Tray tooltip `Books Arranger — choose a data folder`. Tray menu: **Choose data folder…** (opens the form; it is his own action, so focus is fine) and **Quit Books Arranger**. A click on the tray icon opens the form.
- **`--show-inactive`:** the form shows without taking focus.
- **`--quit`:** closes the form (hidden or shown) and ends the process. A copy started with `--quit` never shows a window or a form, and never stays running: if no copy is running it exits at once, quietly. Nothing is left running after it (Futaba m-12).
- **The form's close button and Cancel** still end the app (nothing exists yet to keep in the tray).
- **Visible copy:** the form's controls have no tooltips today. Busy and empty states use `aria-disabled`, so focus stays.

| Control | Tooltip |
| --- | --- |
| Existing folder | Use a catalog you already have. Its files stay where they are. |
| New catalog | Start an empty catalog in the folder below. |
| Data folder | The folder that holds the catalog. Press Browse… to change it. |
| Browse… | Choose the data folder. |
| Use this folder | Check this folder and open its catalog. |
| Create catalog | Check this folder and create an empty catalog in it. |
| Use this folder or Create catalog, no folder | Choose a data folder first. |
| Use this folder or Create catalog, while "Checking data folder…" | Checking the data folder… |
| Cancel | Close without choosing a folder. Books Arranger closes. |

## 8. Names: m-13 and m-14

**m-14, the Same author? card on an underscore credit.** Underscores become spaces everywhere the card shows or files the name: the question, both radio labels, the author line in Names found, the preview, the destination, and the remembered rule (its name is the cleaned one, so "Robert_Heinlein" and "Robert Heinlein" are the same credit).

| Part | String |
| --- | --- |
| Question | Is "Robert Heinlein" the same author as "Heinlein Robert A"? |
| Radios | Same author: use "Heinlein Robert A" / Different author: keep "Robert Heinlein" |
| Different author, files under | the cleaned name, with the app's usual surname-first rule for it |

**m-13, Latin "Given Surname" order.** Today `Ilya_Marchenko` files as `Ilya Marchenko\…` while `Robert Heinlein` files as `Heinlein Robert\…`, because only a known given name is flipped. The library is surname first. If Sergei says yes (question in section 12):

- A two-word Latin name, both words capitalised, is **proposed surname first**: the Author field is prefilled `Marchenko Ilya`, and Goes to reads `Marchenko Ilya\Звезда - Marchenko Ilya.m4b`. What the field shows is what is filed.
- The basis line reads `Author from the folder name, surname first.` (when the name came from the folder name; a tag credit needs no line).
- **Only the proposal changes.** Typed names keep today's rules (a known given name flips, an unknown one is used as typed), so typing `Marchenko Ilya` files `Marchenko Ilya\`, and a typed name is never flipped back.
- If he says no, nothing changes.

---

## 9. What the page needs (names assumed; Ender confirms)

- **List rows:** `place: {universe, series, number, collection}` and `entered: [field…]`, stored values only, no research per row. A Waiting row carries `original_title: {state: waiting | none | found | entered, title}`.
- **Editor read:** one call per opened row: `fields.{title, author, series, number, universe, collection}` each `{proposal, basis}`, `remembered: [{id, field, from, to}]`, `applies: n`, `universes: […]`, `series: […]` (the pick-lists).
- **Preview and Approve** accept `series`, `number`, `universe`, `collection` beside title and author.
- **Save** answers `outcome`: `saved`, `replanned`, `cancelled` (a queued job taken out) or `ready_only` (finished), with `applies`; 409 codes `changed`, `converting`, `queued`. **Forget** takes a remembered id.
- **Rules:** name fixes key on the text plus the author or folder, append-only, newest wins, retractable (the author-rule shape).
- **Delete:** the engine drops cached lists and counts before it answers.
- **Updater:** `install.cancelling`, `install.resuming: [{kind, title}]`, `busy.approvals` (count) in the shell and desktop status.
- **Shell:** the hidden first-run tray, `--quit` with no second copy, the "didn't install" tooltip.

## 10. Changes Ender must make

1. `web/app.js`: Edit names, the editor, outcomes (1.4 to 1.6), the Place and Entered lines, the Waiting row and its fact, the held-back deleted ids, the m-14 cleaning, Series and Number pairing, the `tall` window while an editor is open.
2. `web/desktop-ui.js`: Cancel line and keeping its focus, the Quit sentence while cancelling, the approval line, the two conversion sentences.
3. `web/style.css`: no new tokens; `.book-place` and the editor reuse `.ask-grid`, `.field-help`, `.goes-to`.
4. `desktop/main.js`, `desktop/setup.*`: hidden first-run tray, `--quit`, the "didn't install" tooltip, the form's tooltips and `aria-disabled`.
5. Engine: the names store and rules, re-plan or cancel of a queued job, the Waiting state, series-of-collections routing, universe routing and its lists, the Delete cache drop, m-13 and m-14.
6. Tests: every string above; each new control has its tooltip; no two rects intersect with an editor open at 1440, 1024, 700 and 200% zoom.

## 11. Checks for Futaba (committed build, seeded fixture, nothing on Z:)

1. **Edit names** is on a row of each kind in 1.3, inert on Processing, on a queued Retry, Repair or Delete, and on a row with no file left, each with its exact tooltip.
2. **Save is not Approve:** after Save no job, no move, no queue entry, sources unchanged (SHA-256). Approve still approves.
3. **The SCP fixture:** three "Waiting for retry checks" rows with the same misspelled series. Typing the series once shows "Applies to 3 books."; Save fixes all three; a rescan keeps it; a book by another author with the same title is untouched (control); Forget restores and touches no file.
4. **Queued job:** the job never runs under the old names, in both outcomes of 1.4, each line verbatim. A running conversion refuses with its line.
5. **Number rules:** Series without Number, and the reverse, make Save and Approve inert with the tooltip.
6. **Place and Goes to:** a collection in a series, a universe book and the same book after a change of universe show the planner's path and the Place line; a mistyped universe shows "New universe…".
7. **A finished book:** Save says the audiobook keeps its name; the file in Sorted is byte-identical.
8. **Waiting for the original title:** status, hint, label and Approve tooltip verbatim; Approve converts; typing the English title and Save ends the wait; a stub with no English title converts under the Russian one and the fact reads "Not found. Filed under the Russian title."
9. **Delete:** against a stub that still lists the book, the row is gone within 1 s, every count dropped, no "Deleted." row.
10. **Updater, real shell, hidden window,** an installer that cannot start: the process stays, the Install line and path show, the tray tooltip reads "didn't install", Restart to update returns. Cancel update: the line within 1 s, the button keeps focus, Quit says the cancelling sentence, with a stalled worker the second line names it. A conversion and an approval together: stop in seconds, and the confirm shows the approval line.
11. **First run:** `--start-hidden` shows no window and the tray carries the tooltip; "Choose data folder…" opens the form; `--quit` leaves no process (control: 0.22.1 leaves a second copy); every form control has its tooltip.
12. **m-14 and m-13:** the card for `Robert_Heinlein - Dver_v_leto` has no underscore anywhere, including the destination; with Sergei's yes, `Ilya_Marchenko` reads `Marchenko Ilya`.
13. **Layout:** the editor open and closed, in every row kind: no intersecting rects, no horizontal scroll, focus rings not clipped.

## 12. Question for Sergei, offers

**Question (one word)**
1. Latin "Given Surname" names such as `Ilya_Marchenko`: file them as `Marchenko Ilya`, like the rest of the library? (yes / no)

**Offers (not specced)**
1. One "Corrections" list for everything remembered (these and the author rules), with Forget on each.
2. Show Series on every row, not only collections and universe books.
3. A count of books waiting for their original title in the Jobs line.
4. An update pressed soon after start waits silently on the engine's recovery pass (Futaba m-3, 150 s at 8,000 books). A line for it: "Waiting for the engine to finish its start-up check. This can take a few minutes."

Design basis: NN/g user control and freedom (Discard, Forget, Esc that never loses typing), error prevention (the pick-list, Series with Number, nothing runs under old names), visibility of status (Place and Entered lines, the 1 s Cancel line, the Waiting row's stated fallback), recognition over recall (every row editable the same way), Fitts (Save beside the fields), Jakob (native pick-list, inline edit, tray tooltip); WCAG 2.2 AA 1.4.3, 2.1.1, 2.4.7, 2.5.3, 2.5.8, 4.1.3. Doc-only: no code, git or app launch.

---

## 13. Ender's notes and questions for Judy (2026-10-26, branch `ender/0222`)

What the build does where this spec asked Ender to confirm, and the provisional copy that rulings 35 and 36 needed. Every string marked "provisional" is in the build until you replace it.

### 13.1 Confirmed

1. **Collections in a series (section 2).** The planner files `Сборники\<Series>\<Series> - <N> - <Title> - <Author>.m4b`, the series naming of every book (the backlog's `Протоколы SCP 1 - …` form is not used). Without a number, a collection files as before.
2. **Paused after an update (6.3, Futaba m-11).** The new engine leaves a stopped conversion waiting for Resume audiobook jobs. Your two sentences are in: "Converting {Title}. It stops. Continue it with Resume audiobook jobs." and the forced-stop one.
3. **Waiting for the original title (section 4)** rows are listed under the Held filter (the Status filter that lists automatic waits). Not in Output needs attention.
4. **Ruling 34.** The "Pause audiobook jobs before starting automatic processing" refusal is gone with nothing in its place, and so is the panel help sentence "Existing audiobook jobs must be paused before starting automatic discovery."
5. **Cancel update, second line (6.2).** "{What} is slow to resume" for one piece of work, "are" for several.
6. **Ruling 33's Author unclear sentence**, as drafted: "The author's name is in Latin letters. The app can't tell if they write in Russian."

### 13.2 Where the build differs from the spec, and why (please confirm or correct)

1. **Edit names while a book converts.** Ruling 35 (every action is accepted and queued) came after this spec. Edit names is no longer inert on a converting book: the editor opens, and Save waits for the conversion and runs then ("Save queued. Your choices are saved. It runs when this book's processing finishes."). The finished audiobook keeps the name it was made with ("Saved. The finished audiobook in Audiobooks Sorted keeps its name."). Edit names stays inert while a retry, repair or delete is queued on the row (one queued action per row), with your tooltips.
2. **"Re-planned" (1.4).** A queued job's manifest is frozen and cannot be rewritten safely, so a Save on a book with a queued job sets that job aside (kept, as Start over does) and sends the book back to automatic processing, which researches it with the new names and queues a new job. The row says "Saved. The queued job uses these names." The new job does not keep the old one's place in the queue. The "cancelled" outcome ("The queued job is cancelled. Press Retry…") is never produced.
3. **A Stopped row.** Save leaves the stopped job as it is. When Retry or Repair is pressed, the queue checks the names the job was planned with against the names now in force and re-plans it if they differ, so "Saved. Retry uses these names." is true.
4. **A fix for a collection is found in its folder**, and a fix for anything else under its author. In Sergei's live «Пртоколы SCP» books the series is not read at all (the title reads "Пртоколы SCP. Сейф №1"), so "Applies to 3 books" appears when he respells the title's word, not when he types a series.

### 13.3 Provisional copy for you to replace (ruling 35)

| Where | Provisional string |
| --- | --- |
| A queued row press (Approve, Keep as separate books, Scan again, Remove from list, Save, Forget) | "{Action} queued[, n ahead]. Your choices are saved. It runs when {blocker} finishes." |
| Its Cancel | "Cancel {action}"; tooltip "Take this {action} out of the queue. Nothing was started." |
| A queued press refused when it ran | "{Action} cancelled: {reason}" |
| New blocker words | "Books Arranger is still loading" / "loading"; "Audiobook conversion is running" / "the conversion"; "Automatic processing is running" / "automatic processing" |
| Replacing "Another operation is in progress" / "the current operation" everywhere | "The app is working on another action" / "the current action" |
| A press the page holds until its other press ends (Start over, release, Clear working files, Convert, Keep files, Prepare recovery) | "{Action} queued. It runs when the current action finishes." (while loading: "when loading finishes"), face "Queued", with Cancel |
| A toolbar or panel button pressed while the page is busy or loading | the same line plus " Press it again to cancel." in the message line and as the tooltip; pressing again takes it back |
| Start or Resume scanning while conversion or automatic processing runs | "Start scanning queued. It starts when {the conversion / automatic processing} finishes." |
| Bulk Approve as is, all queued | "Queued {n} books for approval. Each is checked, then converted. Each row shows its outcome." |
| Remove this copy while something else runs | tooltip "Remove this copy. {Blocker sentence}, so the removal is queued after you confirm." |
| Delete book or Remove this copy pressed while another book's dialog is being prepared | face "Checking...", tooltip "Checking another book's files. This book's opens right after." |
| Approve while closing, with names typed | "Books Arranger is closing. Your names are saved; approve again after it restarts." |
| Recovery copies panel while deleting | "Deleting the recovery copies…" |

### 13.4 Approve refusals by gate (the «Спящие красавицы» fix; provisional)

Each gate now has its own code and the row says the gate and the next step; a gate with no line shows the engine's sentence, never "Approve was not accepted. Nothing was changed."

| Code | Provisional row line |
| --- | --- |
| name_taken | An audiobook with this name is already in Audiobooks Sorted. Change the title or author, then approve. |
| job_exists | This book already has an audiobook job. Find it under Queued / creating. |
| profiles | The files are different recordings (their audio differs). Choose the files that belong in the details panel, then approve. |
| chapters | The parts carry chapters of their own. Approve them as one book on the set row, or keep them as separate books. |
| cover | The cover couldn't be checked. Choose a cover in the details panel, then approve. |
| sources | A file of this book can't be read. Check that its drive is connected, then approve again. |
| draft | Edits in the details panel hold this book. Save or discard them, then approve. |
| binding | The collection files changed since they were checked. Scan again, then approve. |
| closing | Books Arranger is closing. Approve again after it restarts. |
| identity (engine) | Approve was not accepted: the app couldn't read this book's identity from its files ({reasons}). Type its title and author, then approve. Nothing was changed. |

### 13.5 Ruling 36: copy removed, replacements wanted

Removed with nothing in their place: the Manual evidence field, its help and "View evidence"; "Enter verified identities. No translated title, author or genre is invented automatically."; "Matches prepare drafts; they do not approve metadata or the recording."; "Surname first when verified; otherwise the full verified name."; the "Only when verified" placeholder; "Saved values are evidence. Conflicting sources still need review."; "See View evidence." after the disagreement count. Still say "verified" and may want your words: the Author for Artist tag help ("Enter the verified author credit…"), the reader help ("Preserve the verified reader…"), the cover help ("Use available artwork when verified…"), the Edit metadata tooltip ("…save it as evidence for this book."), and Approve candidate metadata's refusal with no author, now "Confirm the author first."

Save preview metadata (the "Save does nothing" fix): "Saving…" on the button, "Saved.", "Not saved.", "Saving after the current operation finishes…", and "Unsaved local review." for edits typed during a save.

### 13.6 Kept as real safety refusals (please confirm)

Quit while an update installs or is being cancelled (desktop), a destination that already exists, a missing or offline drive, a source that changed, damaged audio, and the update's own Cancel once the installer has started.

## 14. Ender's notes for Judy: the rest of ruling 35 and ruling 37 (2026-10-26, branch `ender/0222`)

Sergei's ruling 37: every remaining "can't X while Y" goes before release, and names change in two places. Everything below is built. Every string marked "provisional" is in the build until you replace it.

### 14.1 Names (ruling 37, no new copy)

1. **Вселенная Дозоров.** The folder «Сергей Лукьяненко\Вселенная Дозоров - Межавторский цикл» is the universe «Вселенная Дозоров», and inside it the one numbered series «Межавторский цикл». A numbered book goes to `Вселенная Дозоров\Межавторский цикл\Межавторский цикл - 16 - Севастопольский дозор - Недоруб Сергей.m4b`. A book with no number in its name goes to `Вселенная Дозоров\Корона - Каплан Виталий.m4b`. The Place line and Edit names show the universe as read from the folder.
2. **«11/22/63»** is filed as `11.22.63 - King Stephen.m4b`. The title tag keeps its slashes.

### 14.2 Provisional copy: presses that now wait (ruling 35's rest)

| Where | Provisional string |
| --- | --- |
| Resume audiobook jobs pressed while jobs pause (no longer disabled while Pausing) | message and tooltip: "Resume audiobook jobs queued. It starts when {the pause / the earlier start} finishes. Press it again to cancel." |
| The same button pressed again | "Resume audiobook jobs cancelled. Nothing was started." / too late: "Too late to cancel: Resume audiobook jobs has already started." |
| Pause pressed after a start (the start is dropped) | "Pause or closing stopped this start. Press Resume audiobook jobs to start again." (was "…Retry Start after pending checks stop.") |
| Retry all, Retry selected and Convert pressed while a scan runs | "{Retry all / Retry selected / Convert} queued. It runs when the scan finishes." and, on the toolbar, " Press it again to cancel." Row: face "Queued", Cancel. |
| Start over, the combined press or Let the app handle it while the catalog is busy | row and panel: "Start over queued. It runs when the catalog is free." (sent again every 5 s), with Cancel |
| Clear working files while the app is busy | "Clear working files queued. It runs when the app is free." (a scan: "…when the scan finishes.") |
| Clear working files while another program holds a file open | "Clear working files queued. It tries again when the file is released." Tried 6 times, 10 s apart. Then: "Some working files weren't cleared: a file is open in another program (an antivirus scan can hold one). Close it, then press Clear working files again." |
| Delete recovery copies during a scan, a source cleanup or another book's deletion (the button was disabled with the engine's sentence) | button tooltip: "…Keep the finished audiobook. A scan is running, so the deletion is queued after you confirm." (or "A source cleanup is running, …"). Status: "Deletion queued. It runs when the scan finishes." / "…when the source cleanup finishes." / "It runs after the deletion before it." / "It starts shortly." Button: "Cancel deletion", tooltip "Take this deletion out of the queue. Nothing was deleted." Cancelled: "Deletion cancelled. Nothing was deleted." Too late: "Too late to cancel: the deletion has already started." |
| Historical cleanup and restore (no page sends them) | queued in the engine during a scan or audiobook work; no copy |

### 14.3 Provisional copy: real refusals now say their cause (S5, S6, S9, S10)

| Case | Provisional string (was) |
| --- | --- |
| S5 Start over, the combined press, closing | "Books Arranger is closing. Start over after it restarts. Nothing was changed." (was "Start over was not accepted. Check the status above." / "…Nothing was changed.") |
| S5 Let the app handle it, closing | "Books Arranger is closing. Let the app handle it after it restarts. Nothing was changed." (was "…Select the row to read why.") |
| S6 a folder on the way is a link or junction | "A folder on the way to these files is a link or a junction, so the app can't prove what deleting would reach. Nothing was deleted." |
| S6 the working folder holds an item the app didn't make | "The app's working folder for this book holds something it didn't make (a link or an unknown item), so it can't list what to delete. Nothing was deleted." |
| S6 a listed file is the Sorted audiobook | "A listed file is the finished audiobook in Audiobooks Sorted itself. Nothing was deleted." |
| S6 no files left | "This book has no files left in the catalog, so there is nothing to delete." |
| S6 Remove this copy on a book with its own job | "This copy has an audiobook job of its own, so it isn't a spare copy. Nothing was deleted." |
| S6 Delete book no longer offered / copy no longer proven | "Delete book isn't offered for this book any more: the app can still fix it. Nothing was deleted. Check its row." / "This book is no longer a proven copy of a finished audiobook. Nothing was deleted. Check its row." |
| S6 outside the library folders or in Sorted | "A listed file isn't an audio file in your library folders, or it's in Audiobooks Sorted. Nothing was deleted." |
| S6 a link or a second name (hard link) | "A file of this book is a link or has a second name on disk (a hard link), so deleting it wouldn't remove it safely. Nothing was deleted." |
| S6 malformed request | "The delete request was incomplete. Nothing was deleted. Reload the page and try again." |
| S9 M4B Retry or Repair from an outdated view (was "This book's status changed. Check the updated status above." for all of them) | "{Retry} was not accepted: the app doesn't support how this M4B is built. Nothing was queued." / "…the book's review or source files changed. Start over sends it back to automatic processing." / "…working files from an earlier attempt are still present. {Retry} after they are cleared." / "…working files from an earlier attempt are still present, and the app can't clear them safely. The row says what to do." / "Retry was not accepted: the app's read-only check of this M4B says it can't be converted as it is. The row shows why." / the check still running: "The app is checking this M4B before offering Retry. The row updates itself." |
| S10 Clear working files, a file the app can't prove it made | "Some working files weren't cleared: {the app's reason}. The app keeps them in {folder}. If you don't need this earlier attempt, delete that folder in File Explorer; the row then offers Retry." (was "…The app keeps any file it can't confirm is safe to delete.") |

### 14.4 Questions for Judy

1. S10 sends Sergei to File Explorer for files the app refuses to delete. Is that the right next step, or do you want an "Open working folder" button (a new control, Sergei's call)?
2. "Start over queued. It runs when the catalog is free." Is "the catalog" a word Sergei knows, or should it say "when the app is free"?

### 14.5 Two fold-ins Sergei asked for (2026-10-26)

1. **«The Little Sisters of Eluria»** ("Can't convert — M4B not supported") now converts. Its file carries Windows Explorer's star rating in an Xtra box; the app drops that box like the empty one of ruling 32, and the drop is listed in the receipt. No new copy.
2. **A media check that runs past its deadline** («Потаённое окно в потаённый сад», «Регуляторы») is no longer "Needs you". Provisional copy:

| Where | Provisional string |
| --- | --- |
| The waiting row (status "Waiting for source"), its reason in the details | "The library drive answered slowly while the app checked this book. It tries again by itself." Tried again after 2, 4, 8 and 16 minutes; the details show "Automatic retry after {time}". |
| After the fifth deadline in a row (Held) | "The library drive answered too slowly 5 times while the app checked this book. Check that the drive is connected and not busy, then press Scan again." |
| A record saved before this build | shown as the waiting sentence, never "Owned media operation exceeded its deadline" |

Question: is "the library drive" right for Sergei's Z: share, or should it name the drive ("Z:")?

### 14.6 §14 decisions (Judy, 2026-10-26)

**Answers to 14.4 and the 14.5 question**

1. **S10: File Explorer, no button.** The case is rare, the sentence already names the exact folder, and a button is a new control (IPC, tooltip, focus handling) for one refusal. Condition: `{folder}` is the full path, shown as selectable text in the row or the details, never only in a toast that disappears, so Sergei can copy it into File Explorer's address bar.
2. **"The catalog is free" is not clear.** "Catalog" is where the data lives (the setup window, "Opening the catalog"), not a busy state. Every queued line says "the app is free", matching "The app is working on another action".
3. **"The library drive", no "Z:".** It is the app's existing term ("Connect the library drive and try again."), and the library folders are configurable, so a fixed letter would be wrong for another root.

**Exact strings that replace section 14's provisional copy** (everything else in 14.2, 14.3 and 14.5 is approved as written; the replacements below drop history and legality talk and keep two sentences for an error, with "Nothing was deleted." kept on delete refusals because it states the outcome of a destructive press)

| Where | String |
| --- | --- |
| 14.2 Start over, the combined press, Let the app handle it, while the app works | "Start over queued. It runs when the app is free." (Cancel as written; the 5 s resend stays internal.) |
| 14.2 Clear working files, a file held open | "Clear working files queued: a file is open in another program. It tries again every 10 s." |
| 14.2 After the 6th try | "Some working files weren't cleared: another program, often an antivirus scan, still has a file open. Wait a minute or close that program, then press Clear working files again." |
| 14.3 S5 Start over / combined press, closing | "Books Arranger is closing. Start over after it restarts." |
| 14.3 S5 Let the app handle it, closing | "Books Arranger is closing. Let the app handle it after it restarts." |
| 14.3 S6 a folder on the way is a link or junction | "A folder on the path to these files is a link or a junction, so the app can't tell what deleting would reach. Nothing was deleted." |
| 14.3 S6 a listed file is the Sorted audiobook | "A file on the delete list is the finished audiobook in Audiobooks Sorted. Nothing was deleted." |
| 14.3 S6 no files left | "This book has no files left to delete." |
| 14.3 S6 Delete book not offered | "Delete book doesn't apply: the app can still fix this book. Check its row. Nothing was deleted." |
| 14.3 S6 copy not proven | "The app can't prove this book is a copy of a finished audiobook. Check its row. Nothing was deleted." |
| 14.3 S6 outside the library folders or in Sorted | "A file on the delete list is outside your library folders, isn't audio, or is in Audiobooks Sorted. Nothing was deleted." |
| 14.3 S6 link or hard link | "A file of this book is a link or a hard link (a second name for one file), so deleting it isn't safe. Nothing was deleted." |
| 14.3 S9 read-only check says it can't convert | "Retry was not accepted: the app's check says this M4B can't be converted as it is. The row shows why." |
| 14.3 S10 a file the app can't prove it made | "Some working files weren't cleared: {reason}. If you don't need this earlier attempt, delete {folder} in File Explorer; the row then offers Retry." `{reason}` must be a plain-language clause, never an engine code. |
| 14.5 waiting for a slow media check | "The library drive answered slowly while the app checked this book. It tries again automatically." The details keep "Automatic retry after {time}". |

**Approved as written:** 14.1 (no copy); in 14.2 the Resume queued, cancelled and too-late lines, the Pause-after-start line, the Retry all / Retry selected / Convert line and the Delete recovery copies strings; in 14.3 the S6 working-folder, spare-copy and malformed-request lines and the other five S9 lines; in 14.5 the five-deadline Held line and the record-saved-before-this-build rule.
