# Books Arranger: "Output needs attention" becomes the one to-do list

2026-10-24, Judy. UX spec for Ender. EXTEND the existing list: Status = "Output needs attention" (reason strip, candidate rows, bulk toolbar, details panel). Rulings: Sergei, 2026-10-24 (items 5, 6, 6a, 6b, 10, 11, 13; item 12 for the name screening). Inputs: `BooksArranger_Identity_Simplify_2026-10-24.md` (Judy's needs, blocking gates), `BooksArranger_MissingFiles_UX_2026-10-24.md`, `BooksArranger_AttentionActions_Spec.md`, `BooksArranger_IronSkazka_UX_2026-10-23.md`. Basis: read-only look at `web/index.html`, `web/app.js` (candidate rows L218-257, `attentionText` L1546, `candidateStatus` L1682, strip L1283-1332, Retry selected L1334-1377) and `web/style.css`. Nothing launched, no rects measured: geometry is target geometry for Futaba. Spec only: no code, not committed. Sully commits it before Ender is briefed. Names in the mockups are examples, not live rows.

## Decisions in brief

1. **One list, one row pattern.** No new page, no new Status option, no new table column. Every row shows a reason sentence, the proposed destination and its actions.
2. **A book is listed when the app cannot finish it without Sergei.** Four kinds: a question only he can answer, files only he can restore or waive, a stopped job whose next step is his press, a safety gate only he can clear. None of them may sit under another status. "Waiting for source" stops parking books.
3. **Five new reason chips**, in a new "Needs your answer" set left of the existing "Stopped" set: Missing files, Missing title or author, Author unclear, Same author?, Name taken.
4. **What you see is what gets used.** Title and Author are fields on the row. One button, **Approve**, uses everything shown. Nothing typed means "Approve as is" (ruling 6b). No note, no cover step, no order step.
5. **No author goes to "Без автора"**, and the row shows that path before he approves.
6. **Missing files:** Scan again, Convert what's there, and (when nothing is left) Remove from list. There is no Wait button, because a hidden wait is the limbo he rejected. "Not part of this book" is the same conversion as Convert what's there, so it has no button of its own.
7. **Numbered parts** show their proposed name ("Торадора! 5") with a one-line basis. The rule is applied automatically. It is not a reason by itself (question 1).
8. **Bulk "Approve as is (N)":** selected rows only, two chips only, always confirmed in a dialog that lists every destination.
9. **Stale rows are hidden** by the same predicate that builds the counts.
10. **Long technical text** becomes one plain sentence. The raw text lives in a collapsed "Technical details" in the panel, with a Copy button.
11. **After an action** the row flips to Queued, leaves at the next refresh, and its progress shows in the places Sergei already looks.
12. **Entry point:** a "Needs attention · N" shortcut next to "Read errors · N", so the list is one click from the main screen.

## 1. What is listed

**Listed** = unresolved, not superseded, and one of:

| Kind | Examples | Chip set |
|---|---|---|
| A question only Sergei can answer | missing title or author, author unclear, same author?, name taken | Needs your answer |
| Files only he can restore or waive | audio files gone from disk | Needs your answer |
| A stopped job whose next step is his press | Retry, Repair, Check again, Convert again, Convert... | Stopped (unchanged) |
| A safety gate only he can clear | Original changed, Need to reacquire, M4B not supported | Stopped (unchanged) |

**Not listed:** queued, running or researching books; waits the app ends by itself (public-source rate limits on optional fields, retry-later holds); books Sergei kept ("Files kept at your choice."); superseded books.

**Invariant (hook for Futaba):** no book in the first two kinds may show any other status. In particular "Waiting for source" is retired as a book status for identity. Waits on optional fields (series, original title, cover) never hold a book and are not shown per book.

### Stale entries

**One rule:** a book whose newest result for the same source is a verified audiobook in Audiobooks Sorted is not listed, whatever older jobs say. Examples: the 43 "Глубина" volumes and the old Сказка attempt.

- The rule is applied **before** any group test. So it also removes the book from the chip counts, the All total, the Jobs line, the shortcut count, Select this page, Retry all and Retry selected. A stale book can never be re-queued from this list.
- Silent, like gone files: no toast, no banner, no count of "hidden" rows. The old failure stays in the book's history. In All candidates the book reads "Audiobook Ready", as it does now.
- One predicate feeds every count and every list (the MissingFiles "one rule" principle). Count and list always agree.

### Order

Chips and the server sort inside All: Missing files, Missing title or author, Author unclear, Same author?, Name taken, then the Stopped set in today's order (Can retry, Can repair, Need to reacquire, Checking, Original changed, Audiobook problem, Other, M4B not supported). Missing files comes first because deleted files can be recovered only while the recycle bin keeps them.

Inside a chip: by source folder, then title with numbers in natural order, so the parts of one set sit together.

**A book with several reasons** counts once, under the first in the order above. The row shows that reason as its status and sentence, plus one muted "Also:" line for the next reason if Sergei can answer it on the same row (its fields appear too). Everything shown is used when he presses the primary button. A third reason appears after the first two are settled.

## 2. Reason chips

The strip stays under the Status toolbar row, only in this filter. Existing rules stay: native `quiet` buttons, `aria-pressed`, selected = `--row-selected` fill with a 2px `--accent` border, height 32, gap 8, `tabular-nums`, zero-count chips hidden (All and Can retry always shown), a selected chip that reaches zero falls back to All with focus on All, counts update in place each poll and buttons are never rebuilt.

```
Reason: [ All · 140 ]
Needs your answer: [ Missing files · 3 ] [ Missing title or author · 46 ] [ Author unclear · 78 ] [ Same author? · 2 ] [ Name taken · 1 ]
Stopped:           [ Can retry · 9 ] [ Can repair · 1 ]                                              [ Retry all (9) ]
```

- The two set labels are plain text, each inside a `role="group"` named "Questions for you" and "Stopped books". The outer group keeps its name "Output needs attention, by reason". Sets wrap as units; chips wrap inside a set. No horizontal scroll at 700 px or 200% zoom.
- Each book is in exactly one chip. **All = the sum of the chips = the shortcut count = the Jobs line.** The code sums a fixed key list (`attentionKeys`): the five new keys must be added there, or the Jobs line and the shortcut under-count silently.
- Chip tooltips: see the Copy sheet.

## 3. Row anatomy

No new columns. The columns stay: Select, Title clue, Author / reader clues, Audio files, Review status, Actions. The narrow bands (folded clue columns under 800 px, block rows under 600 px) are unchanged. The **Review status cell** gets these lines, top to bottom; each appears only when it has content:

1. **Status**, the first line, as today (40 characters or fewer).
2. **Reason sentence**, `p.field-help attention-hint`, one sentence.
3. **Also:** line (muted), when a second reason can be answered here.
4. **Fields or choice**, when something must be typed or chosen.
5. **Basis line** under a field whose value is a guess.
6. **Goes to** + the destination path, `.path` (mono 13 px), relative to `Audiobooks Sorted\`. Shown whenever the API returns a destination, for every group, Stopped rows included. Never "Unknown". The full path is the line's `title`.
7. The recording marker, last, as today.

**Actions cell**, in this order: primary, type-specific second, View metadata, Source folders / Open folder. `.row-actions` wraps as today (max 280 px). Row buttons stay `quiet row-retry`: with 100+ rows an accent fill on each would be a wall of buttons. Accent fill stays for toolbar and dialog buttons.

**Fields:** Title and Author side by side (`grid-template-columns:repeat(auto-fit,minmax(200px,1fr))`, gap 8, so they stack in a narrow cell). Visible labels above each input, input height 32, `maxlength` 1000, `autocomplete="off"`, `spellcheck="false"`. Prefilled with the app's proposal. Fields appear only when needed: Title when it is missing or its basis is a guess, Author when it is missing or unclear.

**Typing rules**
- No autosave, no "Save" step. The draft lives in memory per book (survives polls, paging and chip changes) and is dropped on Approve. A draft is the typed text; it is never lost to a refresh.
- **Enter** in a field refreshes the destination line and does nothing else. **Ctrl+Enter** in any field or choice of the row presses Approve. Enter alone never approves, because approval ends in file moves and, after a verified result, source removal.
- The destination line refreshes on blur, on Enter, and 500 ms after typing stops. Stale replies are ignored. The last good path stays on screen meanwhile: no flicker, no "Loading".
- The line shows the cleaned name the planner will use, so a typed `AC/DC` shows what it becomes. An empty Title is the only error (Approve inert, tooltip "Type a title first.").
- **One draft per book:** the row fields and the panel's title and author fields show the same draft. If Ender cannot share it cheaply, Approve is aria-disabled while the panel form has unsaved edits for this book, tooltip "Save or discard the edits in the details panel first."
- The row is never rebuilt while a control inside it has focus (existing rule); values update in place.

## 4. The reason rows

The Copy sheet (section 12) is the single source of every string. Mockups show the **Review status** and **Actions** cells side by side, with the clue columns folded into the first line.

### 4.1 Missing title or author (chip "Missing title or author")

Ruling 6a and 11. Four cases: title missing, author missing, both, or tags unreadable (garbled text the app cannot use). The proposal always has a title (tag, else file name, else folder name); the author may be empty.

```
[ ] Шестёрка воронов 1  ·  Author: Unknown  ·  1 audio file
    Author missing                                           [ Approve ] [ View metadata ]
    No author in the tags, file name or folder name.         [ Open folder ]
    Title  [ Шестёрка воронов 1      ]  Author [                    ]
           Set name + part number.               Empty files it under Без автора.
    Goes to  Audiobooks Sorted\Без автора\Шестёрка воронов 1.m4b

[ ] Sbornik_Deti_Primarhov  ·  Author: Unknown  ·  12 audio files
    Title and author missing                                 [ Approve ] [ View metadata ]
    No title or author in the tags, file name or folder name.[ Source folders ]
    Title  [ Sbornik_Deti_Primarhov  ]  Author [                    ]
           Title from the folder name.           Empty files it under Без автора.
    Goes to  Audiobooks Sorted\Без автора\Sbornik_Deti_Primarhov.m4b
```

- **What he types is authoritative** and is recorded as "Entered by you". Public sources are not consulted for the fields he typed, and never hold the book.
- **No author:** empty Author = "Без автора". The folder name is Sergei's (ruling 11); the file name is question 2.
- **Numbered parts (ruling 13):** the Title field is prefilled "{set name} {number}" and the basis line reads "Set name + part number." The same line style marks any guessed title: "Title from the file name." / "Title from the folder name." A title from a tag has no line.
- **Where the number rule is clear it is not a reason.** A book named by the rule appears here only when something else is wrong (this mockup), unless Sergei wants each listed (question 1).

### 4.2 Author unclear (chip "Author unclear")

Two people credited, or the tags and the folder name give different authors (identity analysis: 78 books). Sergei picks one candidate or types another.

```
[ ] Солдаты смерти  ·  Джо Шрайбер; Пухов Сергей  ·  1 audio file
    Author unclear                                           [ Approve ] [ View metadata ]
    Two people are credited. The app can't tell who wrote it.[ Open folder ]
    Author
      (•) Джо Шрайбер     artist tag
      ( ) Пухов Сергей    album artist tag · reader on 9 other books
      ( ) Other  [                    ]
    Goes to  Audiobooks Sorted\Шрайбер Джо\Солдаты смерти - Шрайбер Джо.m4b
```

- The choice is a native radio group (`fieldset` + `legend` "Author"). Arrow keys move inside it; one Tab stop for the group.
- **Preselected = the app's best guess**, so Approve means "as is". A name credited as a reader elsewhere is never preselected while another candidate exists. If the API sees a true tie, it still sends a default (the artist-tag author); Approve is never left without a value.
- Each candidate shows where it came from ("artist tag", "album artist tag", "folder name", "file name") and, when known, "reader on {n} other books".
- Choosing Other focuses its input; the destination line follows the choice.

### 4.3 Same author? (chip "Same author?")

Ruling 12. The screening is a separate piece of work. This is the room it plugs into: the chip, the row and the copy exist now and stay hidden at zero.

```
[ ] Пастушья корона 20  ·  Terry Pratchet  ·  1 audio file
    Same author?                                             [ Approve ] [ View metadata ]
    Is "Terry Pratchet" the same author as "Terry Pratchett"?[ Source folders ]
    Spelled almost like an author you have (41 books).
    Author
      ( ) Same author: use "Terry Pratchett"
      ( ) Different author: keep "Terry Pratchet"
      ( ) Other  [                    ]
    A choice is remembered for other books with these names.  Applies to 3 books.
    Goes to  Audiobooks Sorted\Pratchet Terry\Пастушья корона 20 - Pratchet Terry.m4b
```

- **Nothing is preselected.** The destination line shows the name as written until he chooses. Approve with no choice files the book under the name as written and **remembers nothing**: only an explicit choice teaches a rule (ruling 12). Choosing "Same author" or "Different author" approves the book, saves the rule, and settles every book with that name pair; those rows leave in the same refresh ("Applies to 3 books.").
- The line under the sentence says why the name looks suspicious. The app owns three kinds: translation ("Same name in another language."), near spelling ("Spelled almost like an author you have ({n} books)."), pen name ("May be a pen name of an author you have."). For any other kind the screening sends one plain sentence of 70 characters or fewer, shown as sent.
- Not eligible for bulk approval: a bulk press cannot answer a question.
- If the screening produces many books per name, the rows stay per book. If that proves noisy, re-brief Judy for one row per name.

### 4.4 Missing files (chip "Missing files")

Ruling 10. The row names the file(s), says where they were, and offers real actions. Only audio files count: a missing cover or text file does not stop a book. A drive that is offline is not "missing" (MissingFiles spec: a file counts as gone only after a complete scan).

```
[ ] Новая плоть  ·  Сборник  ·  8 audio files
    Missing files                                            [ Scan again ] [ Convert what's there ]
    1 of 9 files is missing.                                 [ View metadata ] [ Source folders ]
    In  Z:\Audiobooks\Сборники\Новая плоть (2016)\
        03 - Павлов Михаил - Засор.m4b
    Goes to  Audiobooks Sorted\Сборники\Новая плоть - Разные авторы.m4b

[ ] Iron Inferno  ·  Unknown  ·  0 audio files
    All files missing                                        [ Scan again ] [ Remove from list ]
    All 2 files are missing.                                 [ View metadata ] [ Source folders ]
    In  Z:\Audiobooks\Unsorted\WH40K\...\Бойся Чужого\
        Iron Inferno 1.mp3
        Iron Inferno 2.mp3
```

**The set, and why.** Three actions, each shown only when it applies:

| Action | Shown when | What it does | Why |
|---|---|---|---|
| **Scan again** | always | Scans this book's source folders now, then re-checks the book. Changes and deletes nothing. | "Wait for the file" in a form with a result. Files come back by restoring them from the recycle bin or a torrent; the app only sees them after a scan (a plain Continue does not scan). A wait button would hide the row; this keeps it visible and gives him the check. |
| **Convert what's there** | at least one audio file is present | Approves the book from the present files, leaves out the listed ones, then converts if needed, renames and moves it. Uses the fields shown. | One button covers "convert from what's there" and "it's not part of this book": both give the same conversion, and the app has no use for the reason. Two buttons would ask Sergei to classify something the app ignores. |
| **Remove from list** | no audio file is present | Stops listing the book. Touches no file. A later scan lists it again if its files return. | Nothing is left to convert. Needs no confirmation: it is reversible and deletes nothing. |

- **Naming the files:** the folder once on an "In" line, then each file name on its own line (`.path`). Up to 3 names show in the row, then "+ {n} more, listed in the details panel." The panel lists all of them.
- **The row stays until Sergei acts or the files return.** There is no snooze. A row he has chosen to wait on is still an honest row: the chip count tells him how many.
- **After Scan again, still missing:** the hint's last line reads "Checked 14:32. Not found." It is replaced on each scan. **Found:** the row leaves and the strip says "Files found. The book is checked again." The book then continues by itself, or returns as another reason.
- **Convert what's there** has no confirmation: the row already names what is left out and shows the destination, and the standard cleanup rule applies (an original goes only after its audiobook is verified in Audiobooks Sorted). If a second reason applies (for example no author), its fields show on this row and are used.
- Not offered in bulk: each book needs its own decision.
- Open folder: when the folder itself is gone it stays enabled and shows the path in the row, because the "In" line is what Sergei needs to restore from.

### 4.5 Name taken (chip "Name taken")

The safety gate that stays: never overwrite. It surfaces when the proposed name already exists in Audiobooks Sorted, including after Approve or a bulk approve.

```
[ ] Хроники Нарнии 2  ·  Клайв Стейплз Льюис  ·  14 audio files
    Name taken                                               [ Approve ] (inert) [ View metadata ]
    A book with this name is already in Audiobooks Sorted.   [ Source folders ]
    Title [ Хроники Нарнии 2   ]  Author [ Клайв Стейплз Льюис ]
    Already there  Audiobooks Sorted\Льюис Клайв Стейплз\Хроники Нарнии 2 - Льюис Клайв Стейплз.m4b
```

- Approve is `aria-disabled` while the typed or shown name is taken, tooltip "That name is taken. Change the title or author." The destination line (label "Already there", `--warning`) says why. Once he changes a name so the path is free, Approve works. The preview reports taken names, so the press is prevented rather than refused.
- If a race still refuses it: "Approve was not accepted. Nothing was changed." and the row returns here with his values kept.
- Real duplicates (the same recording twice) belong to the existing duplicate-recording review; this row offers a rename only (offer 3).

### 4.6 Stopped rows (existing chips) and long technical text

The Stopped set keeps its statuses, hints, buttons and bulk actions (Retry all, Retry selected). Two changes: every row also shows the **Goes to** line, and **raw text never prints**.

Today a row with no typed cause falls back to `Needs attention — {raw reason}`, which is how the ffmpeg decode wall reached the screen. The fallback ends:

```
Before:  Needs attention — Full audio decode failed: [Parsed_... Header missing ... -1094995529 ... 40 more lines]

After:   Stopped — audio check failed                        [ Retry ] [ View metadata ]
         One file failed its audio check, so the book        [ Source folders ]
         wasn't converted.
         Goes to  Audiobooks Sorted\Джон МакКрэй\Червь 19. Расплата - Джон МакКрэй.m4b
```

- The API sends a **typed cause**; the UI maps it to one sentence (Copy sheet). Unknown cause: status "Stopped — see details", sentence "The conversion stopped. Select the row to read the technical message."
- **The same rule applies wherever a reason is printed:** the Jobs panel "Current book" line, the message area, the cell tooltip. Raw text appears only inside Technical details. The cell tooltip is the first 200 characters of it, ending in an ellipsis.
- The panel's always-visible "Technical detail:" line (`#automatic-technical`) becomes a disclosure, closed by default on every selection:

```
> Technical details
v Technical details                                          [ Copy details ]
  +------------------------------------------------------+
  | Full audio decode failed ...                         |   scroll region, 240 px max,
  +------------------------------------------------------+   tabindex 0, aria-label "Technical message"
```

Text selectable, `overflow-wrap:anywhere`, never truncated. Copy details copies the whole message and sets a polite status "Copied." that stays until the selection changes (no timer).

## 5. Approve, and "Approve as is" in bulk

### Approve (single)

One press records the approval (who, when, the exact values shown), then converts if needed, renames and moves the book into its proper Audiobooks Sorted subfolder.

- It overrides every identity and confidence hold (ruling 6b). It asks for no note, no cover choice and no source-order confirmation: the cover is automatic (embedded, else neutral) and the order is the app's.
- **Safety gates stay:** changed or unreadable sources, a destination that exists (Name taken), a job that already exists, media verification. A source is removed only after its audiobook is verified in Audiobooks Sorted (ruling 2).
- Typed values are saved as "Entered by you" in the same request. Nothing typed means the proposal is approved as is.
- States follow the Retry machinery: one request at a time, `aria-disabled` while pending (keeps focus), label "Approving...", no double press, refused and connection-lost copy as in the Copy sheet. Focus after success: the next row's first working control (its first field, else its primary button), else the row now at this index, else the Status filter. `preventScroll`.
- The details panel's "Approve candidate metadata" (Manual review) is the old multi-step path. It is unchanged and not needed here.

### Bulk "Approve as is (N)"

**Is it safe? The files, yes. The names, only as safe as the guesses.**

| What could go wrong | Guard |
|---|---|
| Source removed before the result exists | Ruling 2: removal only after the verified audiobook is in Audiobooks Sorted. |
| An existing book overwritten | The never-overwrite gate stays; a collision comes back as a Name taken row. |
| Audio damaged by conversion | Media verification stays. |
| **A wrong author or title in the name** | **Not prevented.** The audio is intact and the fix is a rename or move, but the source is gone by then, so reconverting is not an option. Measured accuracy of "as is" is about 85% for confident books (Identity analysis); it is **not measured for the flagged set**, which is the harder one. |
| A reader filed as the author | Not prevented in Author unclear; the candidates show reader evidence, the dialog shows every path. |
| Wrong lasting name rule | Approve never teaches one. Only an explicit "Same author" or "Different author" choice does. |
| A mis-click on a large set | Selected rows only, one chip only, confirmation with Cancel as default. |

**Rules**
- Available only in **Missing title or author** and **Author unclear** (question 3). Never in All, Missing files, Same author?, Name taken or the Stopped set. In those chips Retry selected hides; elsewhere Approve as is hides.
- Acts on selected rows only (Select this page, or single checkboxes). There is no "Approve all".
- Rows left out, with the count in the summary: rows whose Approve is inert, and rows with unapproved typed text (a draft is never lost or silently ignored; he approves it on its row).
- Uses each row's shown proposal exactly as listed in the dialog.
- Always confirmed in a dialog. One request at a time through the same queue; the server re-checks each book and refuses per book.

```
[x] Select this page   12 selected · 10 can be approved as is · 2 left out   [ Approve as is (10) ]
Approve as is uses the names shown on each row. Books that need a different action are left out.
```

```
+-------------------------------------------------------------------+
| Approve 10 books as is?                                           |
| Each book is converted if needed, renamed and moved to Audiobooks |
| Sorted as listed below. An original is removed only after its     |
| audiobook is checked there.                                       |
| +---------------------------------------------------------------+ |
| | Audiobooks Sorted\Без автора\Тёмная комната.m4b               | |
| | Audiobooks Sorted\Шрайбер Джо\Солдаты смерти - Шрайбер Джо.m4b| |
| | ...                                          (scrolls, 40vh)  | |
| +---------------------------------------------------------------+ |
| 2 selected books are left out. They need a different action.      |
| [ Cancel ]  [ Approve 10 books ]                                  |
+-------------------------------------------------------------------+
```

- A native modal dialog in the existing pattern (560 px max, background inert, Esc cancels, Cancel is the default focus). The list is a focusable region (`tabindex="0"`, `role="group"`, name "Books to approve"). **Do not reuse the two-button Tab trap** of `#recovery-dialog`: this dialog has a third stop, so rely on the native modal's focus handling.
- The confirm button goes `aria-disabled` on press (no double press). The "left out" line shows only when the count is above zero.
- On finish, focus moves to the active chip button.

## 6. After an action

| Action | The row | Strip line (polite live region) |
|---|---|---|
| Approve | Flips to status **Queued**, hint "Approved. Converts if needed, then renames and moves it to Audiobooks Sorted.", disabled "Queued" button, no fields. Leaves at the next refresh. | "Approved 1 book. Track it under Queued / creating." |
| Convert what's there | Same flip; hint "Approved without the missing files. Converts, renames and moves it to Audiobooks Sorted." | "Approved 1 book without its missing files. Track it under Queued / creating." |
| Scan again, not found | Stays; hint's last line "Checked 14:32. Not found." | none |
| Scan again, found | Leaves | "Files found. The book is checked again." |
| Remove from list | Leaves | "Removed 1 book from the list. No files were touched." |
| Same author? choice | Leaves, with every book that has that name pair | "Remembered. {n} books continue." |
| Bulk | Rows flip, then leave | Start "Approving 10 books." End "Approved 10 books. Track them under Queued / creating." Partial "Approved 9 of 10. 1 stays listed with its reason." |

- **Progress is visible without a new surface:** the book appears under Queued / creating and then Audiobook Ready (existing filters); the Jobs panel counts it ("N converted out of M approved books", "N queued"); the strip line names where to look. The details panel keeps "Approved by you" with the date and the values used.
- Counts drop within one poll. Chips never rebuild; focus holds.
- **Refused:** the row stays, the hint turns `--warning`: "Approve was not accepted. Nothing was changed." (or "Convert was not accepted...", "Scan did not finish. Nothing was changed."). A changed book: "This book changed. Review its details and try again." Connection lost: "Connection interrupted. Check the status above before trying again." A refusal caused by a gate shows that gate's own row (for example Name taken), with his typed values kept.
- Strip line text stays until the chip or filter changes. No timers, no toasts.

## 7. Details panel

Reuses the sections that exist; changes are small.

- `#automatic-result-status` and `#output-status` show the same status and sentence as the row (they already call the same function).
- New **Names found** list for the three name reasons: Title and Author, each as `{value} - {source}` lines ("Артист: Джо Шрайбер - artist tag"). It answers "where did this come from" without opening the tag snapshot.
- The included-source list marks missing members "Not found", in playback order, so Sergei sees where the gap is.
- **Technical details** disclosure replaces the always-visible line (section 4.6).
- The existing Edit metadata path (series, number, universe, narrator, folder name, covers) stays for anything the two row fields do not cover. The row's fields are the fast path, not a replacement.

## 8. Entry point and the Jobs line

- **Shortcut** "Needs attention · N" beside "Read errors · N" in the Status toolbar, same pattern as `#error-shortcut` (quiet, `--warning` text, hidden at 0, space reclaimed). Click sets View = Book candidates, Status = Output needs attention, chip = All, and moves focus to the All chip. N is the All total. Recommended, small; the list can ship first.
- **Jobs panel:** the line "N output issues" becomes "N need attention" (many of these are not output problems), from the same total. It must equal the All chip.
- The filter keeps its name, "Output needs attention" (Sergei's).
- Empty list with no search: "Nothing needs your attention." replaces "No candidates match these filters · Output needs attention."

## 9. Keyboard, hit areas, theme

**Keyboard**
- Tab order in a row: row, Select, fields or choice, primary, second action, View metadata, Source folders / Open folder.
- Fields, radios and their labels stop `click` and `keydown` from reaching the row. The row's own handler turns Enter and Space into "select the row", so without this a space typed in a title would select the row instead.
- Ctrl+Enter in any field or choice presses Approve. Enter in a field refreshes the destination line. Esc closes the dialog.
- Buttons wrap inside `.row-actions`, nothing is absolutely positioned. The dialog is the only overlay. Rows never rebuild while a control inside has focus.

**Geometry (target; Futaba measures at 1440, 1024, 700 and 200% zoom, with and without the dialog open)**

| Element | Target |
|---|---|
| Row buttons | at least 96 x 32 (Convert what's there at least 152 x 32; labels wrap, never truncate) |
| Title and Author inputs | 32 high, at least 160 wide, full cell width up to 420 |
| Radio | 24 x 24 box, label row 32 high |
| Chips and shortcut | at least 32 high |
| Dialog buttons | at least 96 x 32 |
| Pending labels | the row's size does not change |
| List window | **grows with the viewport in this filter** instead of today's fixed 430 px (rows with fields are about 150-230 px tall). At 1440 x 900 at least three full rows show. No horizontal scroll. |

**Theme.** Dark only, tokens only, calculated not rendered:
- Input text `--text` on `--field` 15.82; placeholder `--muted` on `--field` 10.17; input border `--border` against `--field` 4.71 and against `--surface` 4.13 (needs 3).
- Sentence and basis lines (`--muted`) on `--surface` 8.92, `--row-hover` 6.63, `--row-selected` 4.97. Warning lines on `--surface` 11.18, `--row-selected` 6.23.
- **Accent text only on a button face** (`--surface` fill, 8.02). Accent text directly on the selected row is 4.47 and fails 4.5, so radio labels, "In" lines and paths use `--text`.
- aria-disabled Approve: `--disabled-text` on `--disabled` 6.07, and it differs by fill and tooltip, not by hue. If a light theme ships, recheck these pairs. Futaba measures the unchecked radio ring (at least 3:1) in the build.

## 10. Build order for Ender

Slices; each ships alone.
1. **Predicate and truth:** one listing predicate with the stale rule, new `attention_counts` keys in `attentionKeys`, the Jobs line, no raw text (typed causes, fallback, Technical details), the Goes to line on every row.
2. **Approve:** fields, destination preview, Approve with the 6b semantics, Без автора, the chips Missing title or author and Author unclear, bulk Approve as is.
3. **Missing files and Name taken:** Scan again, Convert what's there, Remove from list, the destination gate.
4. **Same author?:** when the screening delivers its questions. Chip and row copy are already specified.

## 11. What the UI needs from the API (names assumed; Ender confirms)

- **Per book, one `ask` object** or none: `kind` (`files_missing` | `title_author` | `author_unclear` | `same_author` | `name_taken`), a second `also` kind if any, `fields.title` and `fields.author` each `{proposal, basis}` where basis is `tag` | `file_name` | `folder_name` | `number_rule` | `entered`, `candidates` for the author with `{name, source, reader_count}`, `destination` `{path, taken}`, `missing` `{folder(s), files[], present, total}`, `same_author` `{new, existing, existing_books, why, count}`. The UI maps kinds to copy; it never shows the server's English for these.
- **Typed cause** for every Stopped job; the raw text in a separate `technical` string. Unknown cause is allowed and falls back as in 4.6.
- **Groups and counts:** `files_missing`, `title_author`, `author_unclear`, `same_author`, `name_taken` added to `attention_counts`, sorted as in section 1.
- **Stale rule** inside the one listing predicate, so Retry all, Retry selected and every count obey it.
- **Endpoints:** approve (book, revision, optional title, author, choice, `without_missing`), bulk approve (items, per-book results), preview destination (title, author, choice returns path and `taken`), scan again (book), remove from list (book), and the same-author answer (inside approve via `choice`, or its own route).
- **Approve semantics:** records who, when, the exact values, files and order shown; overrides identity and confidence holds; no note, cover automatic, order automatic; safety gates stay; typed values stored as "Entered by you".
- **Waiting for source** retired as a book status for identity; optional-field waits hidden per book.
- **Companion files** (cover, text) never create Missing files. Please confirm. The missing file's full path and its folder are sent even when the folder is gone.
- **No-author file name:** the planner decides; the row shows it verbatim (question 2). A typed author is treated as the display name, with the folder name from the existing naming rule; the destination line is the truth. If the app cannot derive a surname-first folder it uses the name as typed.
- **One draft per book** shared with the panel form, or the fallback in section 3.

## 12. Copy sheet (single source)

Straight apostrophes as in the app. {braces} are filled values. Status lines are 40 characters or fewer; hints are one sentence.

**Strip and shortcut**

| Where | String |
|---|---|
| Set labels | Needs your answer: / Stopped: |
| Chip + tooltip | Missing files · N / Show books with files missing from disk. |
| | Missing title or author · N / Show books with no title or no author. |
| | Author unclear · N / Show books where the author could be more than one person. |
| | Same author? · N / Show author names that may match an author you already have. |
| | Name taken · N / Show books whose name already exists in Audiobooks Sorted. |
| Shortcut + tooltip | Needs attention · N / Show every book that needs you. |
| Empty list | Nothing needs your attention. |
| Jobs line | {N} need attention |

**Status and sentence**

| Reason | Status | Sentence |
|---|---|---|
| Title missing | Title missing | No title in the tags, file name or folder name. |
| Author missing | Author missing | No author in the tags, file name or folder name. |
| Both missing | Title and author missing | No title or author in the tags, file name or folder name. |
| Tags unreadable | Tags unreadable | The tags show garbled text, so they aren't used. |
| Two people credited | Author unclear | Two people are credited. The app can't tell who wrote it. |
| Tag and folder differ | Author unclear | The tags and the folder name give different authors. |
| Same author? | Same author? | Is "{new}" the same author as "{existing}"? |
| Some files missing | Missing files | {n} of {m} files {is/are} missing. |
| All files missing | All files missing | All {m} files are missing. |
| Name taken | Name taken | A book with this name is already in Audiobooks Sorted. |
| Decode failure (example typed cause) | Stopped — audio check failed | One file failed its audio check, so the book wasn't converted. |
| Unknown Stopped cause | Stopped — see details | The conversion stopped. Select the row to read the technical message. |
| Other hold, no typed copy yet | Needs you | This book needs your decision. Select the row to read why. |
| Second reason | | Also: {sentence in lower case, for example "no author found."} |

**Row lines**

| Where | String |
|---|---|
| Field labels | Title / Author (choice legend: Author) |
| Author placeholder | Empty files it under Без автора. |
| Other option | Other / placeholder: Another author |
| Same-author options | Same author: use "{existing}" / Different author: keep "{new}" |
| Basis lines | Set name + part number. / Title from the file name. / Title from the folder name. / Author from the folder name. |
| Candidate sources | artist tag / album artist tag / folder name / file name / reader on {n} other books |
| Why suspicious | Same name in another language. / Spelled almost like an author you have ({n} books). / May be a pen name of an author you have. |
| Remembered | A choice is remembered for other books with these names. |
| Scope | Applies to {n} books. |
| Destination | Goes to / Already there (taken) |
| Missing files | In {folder} / + {n} more, listed in the details panel. |
| Scan result | Checked {time}. Not found. |

**Controls: face, tooltip, pending**

| Control | Tooltip | Pending |
|---|---|---|
| Approve | Approve with the values shown: convert if needed, rename, move to Audiobooks Sorted. Ctrl+Enter in a field does the same. | Approving... / Approving this book... |
| Approve (title empty) | Type a title first. | |
| Approve (name taken) | That name is taken. Change the title or author. | |
| Approve (panel edits open) | Save or discard the edits in the details panel first. | |
| Scan again | Look for the missing files in this book's folders. Nothing is changed or deleted. | Scanning... / Scanning this book's folders... |
| Convert what's there | Convert the files that are present and leave out the missing ones. | Queuing... / Queuing this book... |
| Remove from list | Stop listing this book. No files are touched. A scan lists it again if its files return. | Removing... / Removing this book from the list... |
| Title field | The title this book is filed under. | |
| Author field | The author this book is filed under. Leave empty to use Без автора. | |
| Each author radio | Use {name} as the author. | |
| Other radio | Type a different author. | |
| Approve as is (N) | Approve the selected books with the names shown. Each is converted if needed, renamed and moved to Audiobooks Sorted. | |
| Approve as is (none) | Select books that can be approved as is. | |
| Dialog Cancel | Close without approving anything. | |
| Dialog Approve {n} books | Approve these {n} books. | |
| Technical details | Show the technical message. | |
| Copy details | Copy the technical message to the clipboard. | |
| Bulk help line | Approve as is uses the names shown on each row. Books that need a different action are left out. | |

Accessible names: "Approve: {title clue}", "Scan again: {title clue}", "Convert what's there: {title clue}", "Remove from list: {title clue}", "Title: {title clue}", "Author: {title clue}". The visible label is at the start of each name (WCAG 2.5.3).

**Refusals and live lines**

| Case | String |
|---|---|
| Approve refused | Approve was not accepted. Nothing was changed. |
| Convert refused | Convert was not accepted. Nothing was changed. |
| Scan failed | Scan did not finish. Nothing was changed. |
| Book changed | This book changed. Review its details and try again. |
| Connection lost | Connection interrupted. Check the status above before trying again. |
| Approved (row hint) | Approved. Converts if needed, then renames and moves it to Audiobooks Sorted. |
| Approved without files (row hint) | Approved without the missing files. Converts, renames and moves it to Audiobooks Sorted. |
| Dialog title / body | Approve {n} books as is? / Each book is converted if needed, renamed and moved to Audiobooks Sorted as listed below. An original is removed only after its audiobook is checked there. |
| Dialog left out | {k} selected books are left out. They need a different action. |
| Technical details copied | Copied. |

## 13. Checks for Futaba (committed build, seeded fixture, no real library, nothing on Z:)

1. **Fixture:** one book per new reason (including a no-author and an all-files-missing book), one Stopped book with a 40-line decode message, one failed job superseded by a verified audiobook, one book waiting only on an optional source, one queued book. The list shows exactly the first six groups. The superseded, waiting and queued books are absent. Control: the superseded book is listed on the unfixed build.
2. **Counts:** chip counts, the All total, the shortcut and the Jobs line all agree, and agree after each action within one poll. The five new keys are in the sum.
3. **Copy:** every string verbatim. A search of the whole page for `Errno`, `ffmpeg`, `Header missing`, `decode`, `moov` finds them only inside the open Technical details. The row, panel status, Jobs line and tooltip show none.
4. **Approve as is:** with nothing typed, the book is approved and its path equals the Goes to line. A no-author book lands in `Без автора`. With text typed, the typed values are used and recorded as "Entered by you". Enter alone does not approve; Ctrl+Enter does. A space typed in a field does not select the row.
5. **Safety:** after Approve the source stays until the verified output is present in Audiobooks Sorted (check the fixture's order of events). A taken name leaves Approve inert with its tooltip; renaming frees it.
6. **Missing files:** names and folder shown exactly; more than 3 shows "+ n more". Scan again with the file restored removes the row; not restored shows the time and "Not found." Convert what's there queues without the file. Remove from list touches no file and a later scan lists the book again. A missing cover alone adds no row.
7. **Same author?:** no choice approves as written and records nothing; "Same author" records the rule and clears every book with the pair.
8. **Bulk:** absent in All, Missing files, Same author?, Name taken and the Stopped set; Retry selected is absent in the two eligible chips. The dialog lists exactly the eligible paths; Cancel has focus; Esc cancels; confirm runs once on a double click; a forced refusal reads "Approved 9 of 10..." and keeps its row. A row with unapproved typed text is left out and counted.
9. **Stale:** Retry all and Retry selected never include the superseded book.
10. **Rects** at the sizes in section 9, with the dialog open and closed: no two rects intersect, no horizontal scroll, no clipped focus ring, at least three full rows visible at 1440 x 900, pending labels do not resize rows.
11. **Keyboard:** the Tab order of section 9, arrow keys in radio groups, focus landing after Approve, typed text and focus survive 10 polls and a chip switch.
12. **Tooltips:** every control in the Copy sheet has its tooltip in the packaged window.
13. **Technical details:** closed by default on every selection; Copy details copies the full text; the region scrolls by keyboard.

## 14. Questions for Sergei, offers, not decided here

**Questions (one word each)**
1. Numbered parts such as "Торадора! 5": apply the rule automatically and show them here only when something else is wrong, or list every such book once for a glance? (auto / list)
2. A book with no author: name the file just the title, `Без автора\Title.m4b`, with no author suffix? (yes / other)
3. Allow bulk "Approve as is" in "Author unclear" (a reader may be filed as the author; the rate is not measured for this set), or only in "Missing title or author"? (allow / missing)

**Offers (not specced)**
1. Gaps inferred from numbering (parts 1, 2 and 4 present): a weaker signal than a known missing file, and the app cannot name a file. Say if you want it listed.
2. Up and Down arrows to move between rows, for long sessions.
3. A "Keep existing" action on Name taken for true duplicates, tied to the duplicate-recording review.
4. Copy for each remaining hold (duplicate recording, sources disagree, manual draft). Until then they use the "Needs you" fallback. Send the reasons the app can produce and I will write them.
5. The Jobs line "N need attention" could link to this list.

**Not changed here:** the Stopped set's own actions and bulk buttons; the Manual review panel; the filter's name; Files-view behaviour (MissingFiles spec).

Design basis: Hick (five chips in two labelled sets, zero chips hidden, one primary per row), Fitts (the fields and Approve sit in the row, no panel round trip), Jakob (native fields, radios, dialog, title tooltips), NN/g error prevention (confirm only where moves and removal follow; Enter never approves; a taken name blocks Approve), visibility of status (counts agree everywhere, progress stays findable), plain-language recovery (one sentence, details collapsed); WCAG 2.2 AA 1.4.3, 1.4.11, 2.1.1, 2.4.7, 2.5.3, 2.5.8, 4.1.3. Doc-only: no code, git or app launch.

---

# 0.22.0 review (2026-10-24, Judy)

Basis: read-only look at branch `ender/0220` (worktree `C:/Antigravity Projects/Worktrees/Books Arranger/b0220`): `web/app.js` (to-do code L1823-2146, `activityStep` L503), `web/index.html`, `web/style.css`, commit 43d962d, and the backend that decides what is listed and what Approve does: `merge_service.needs_you` (L1948), `ask_payload` (L2012), `approve_book` (L2105), `approve_automatic` (L2139), `source_identity.source_gate` (L56), `local_identity.PIECE_REASON` (L1461), `review_backend.tracks` (L702). Nothing launched, no live catalog opened. The counts (1,248 / 347 / 271 / 155 / 143 / 39 / 10) are Ender's and Jane's, not re-measured here. Geometry is target geometry for Futaba. Spec only: no code.

**This section supersedes, in this file:** section 4.2 last bullet ("always sends a default"), section 4.3 "Choosing ... approves the book", section 5 "no order step" (for the Order unclear rows only), check 7, and offer 4 of section 14 (answered in part B).

## A. The six departures

| # | Departure | Verdict |
|---|---|---|
| 1a | Copy: "The only name credited may be the reader. The app can't tell who wrote it." | Accept. One fix for the "Also:" line (below). |
| 1b | Copy: "The file name and the folder name give different authors." | Accept. |
| 1c | Copy: "Remove from list was not accepted. Nothing was changed." | Accept. Fills a hole in my sheet. |
| 1d | Copy: "Copy is unavailable here. Select the text instead." | **Change** to "Couldn't copy. Select the text and press Ctrl+C." |
| 2 | Reader-only rows: nothing preselected, Approve files under Без автора | Accept, plus one visible line. |
| 3 | Same author?: a choice does not approve, Approve must be pressed | Accept. My spec was wrong. |
| 4 | "Needs you" rows count under Other and offer Approve | **Change.** Not specific enough. See part B. |
| 5 | Row and panel drafts not shared, Approve inert while the panel has unsaved edits | Accept, and extend to unsaved track edits. |
| 6 | Activity line: long or multi-line reason reads "On hold — see details" | Accept the rule. **Change** the words. |

**1a.** Evidence plus consequence, in plain words. The "Also:" line is built from the same sentence (`askAlso`), so the second sentence breaks the "Also: {one sentence}" form. In an "Also:" line use the first sentence only: "Also: the only name credited may be the reader."

**1d.** "here" says nothing. The fix is to name the key. Status line only, no timer, as for "Copied.".

**2. Reader-only rows.** Ruling 14 beats my "never left without a value", and ruling 11a agrees: Без автора is the last resort, used when Sergei gives no author. The radios list the suspected reader with its evidence ("artist tag · reader on 9 other books"), so he can still pick that name on purpose. Add one line under the radio group, shown only while nothing is chosen (`field-help`): **No choice files it under Без автора.** Without it, an unselected radio group reads as "nothing will happen" and the Goes to line is the only hint. Bulk stays closed to these rows (`readerRisk`), as ruling 14 says "including bulk".

**3. Same author?** Accept. Native radios change on arrow keys, so approving on change would file a book (and later remove its source) while he is still arrowing. Approve after choosing is right. Behaviour: choose "Same author" or "Different author", press Approve: the rule is saved, the book is filed, every book with that name pair leaves in the same refresh ("Applies to {n} books." stays above Approve; the strip says "Remembered. {n} books continue."). Approve with no choice files it as written and teaches nothing. Add one line under the group, shown only while nothing is chosen: **No choice files it as written. Nothing is remembered.** Sergei expects his answer to be kept, so the row must say that pressing Approve alone is not an answer. Check 7 now reads: choose, press Approve, rule recorded, pair cleared.

**5. Drafts.** Accept (the fallback in section 3). `askInert` tests `dirty` only. Add `trackDirty` (unsaved order or include edits in the panel): same inert state, same tooltip "Save or discard the edits in the details panel first." This matters more now (part B: Change order and Choose files live in the panel). Futaba adds: save a Title in the panel, then compare the row's Title field with the panel. Both must show the saved value.

**6. Activity line.** The rule is right (no wall of text in the Jobs panel). "see details" points at nothing: the activity row is not clickable and has no details. The held book is listed under Needs attention, so point there: **On hold — see Needs attention**. Residual risk: a reason of 80 characters or fewer still prints raw ("Errno 13 Permission denied ..." fits). The real fix is the same typed cause the row uses; use it here when the API sends one, and keep the length rule as the fallback. Futaba searches the Jobs panel for the technical markers of check 3.

## B. The 347 held books

### B1. What the code does today

All four holds follow the same path and end on the same row:

| Hold (count) | Produced by | Listed as | Row today |
|---|---|---|---|
| One part of a bigger book (155) | `local_identity` piece (`identity_hold.kind='piece'`) | group `other` ("until change") | Needs you |
| Playback order uncertain (143) | `source_gate` | `other` | Needs you |
| Source membership uncertain (39) | `source_gate` | `other` | Needs you |
| Mixed recordings (10) | `source_gate` | `other` | Needs you |

The row says "Needs you / This book needs your decision. Select the row to read why." with Approve, in the **Stopped** set. The server sends `reasons`, but the UI uses them only for a tooltip and the Technical details disclosure.

### B2. Is "Needs you" under Other specific enough? No

1. **Wrong place.** Other sits in the Stopped set ("Show books that stopped for another reason"), next to Retry all and Retry selected. These books did not stop. They ask a question. Sergei looks for questions under "Needs your answer".
2. **One sentence for four different problems.** The real reason is two actions away (select the row, read the panel). Ruling 10 says "explain exactly what is wrong". 271 identical rows cannot be worked through.
3. **The only option is Approve, with nothing shown that it approves.** Approve overrides these holds (ruling 6b; `approve_automatic` keeps only the safety reasons) and converts the app's file set in the app's order. The approval note even records "in the order shown", but no order is shown. A wrong order or a stray file inside a finished audiobook cannot be repaired once the source is removed (ruling 2). Ruling 6b stays as it is: Approve still approves as is. The row must show what "as is" is.
4. **No real second option.** He cannot reorder, drop a file or re-check the folder from the row.

### B3. What is needed: three chips, specific rows, real options

**Three chips** join the "Needs your answer" set, appended after Name taken, hidden at zero:

| Chip | Tooltip | Holds |
|---|---|---|
| Part of a bigger book · N | Show books that may be only one part of a bigger book. | the 155 |
| Files unclear · N | Show books where the app isn't sure which files belong. | source membership (39) and mixed recordings (10) |
| Order unclear · N | Show books where the app isn't sure of the playback order. | the 143 |

Keys: `part_of_book`, `files_unclear`, `order_unclear`, added to `attentionKeys` and `NEEDS_KEYS`, so All, the shortcut and the Jobs line still equal the sum. Membership and mixed share one chip because they ask the same thing ("are these the right files?") and share the same options; Hick prefers three chips to four. A book with several reasons counts once, in this order: Part of a bigger book, Files unclear, Order unclear. The next reason shows as an "Also:" line when it is answered on the same row (its list shows too).

**Other** keeps the Stopped jobs. A hold the app cannot classify stays there as a catch-all, never as a mystery: status "Needs you", sentence "This book needs your decision.", and a line **Reason: {first reason}** when that reason is 80 characters or fewer and one line (the app's own short phrase). Acceptance: on a copy of the live catalog, "Needs you" rows = 0, or each one is named in Futaba's report.

**Not in bulk.** None of the three chips offers "Approve as is". A bulk press cannot confirm an order, a file set or a name. Retry selected also hides in every "Needs your answer" chip, not only the two bulk chips (today it shows a dead "Retry selected (0)" in Missing files, Same author?, Name taken and the new chips).

### B4. The rows

Layout follows sections 3 and 4: status, sentence, optional Also line, fields or list, Goes to, buttons. Face and tooltip of the primary button depend on the chip, so the press says what is being confirmed.

**Order unclear** (`order_unclear`)

```
[ ] Колесо Времени 3  ·  Роберт Джордан  ·  12 audio files
    Order unclear                                    [ Approve this order ] [ Change order ]
    3 of 12 files have no track number.              [ Scan again ] [ View metadata ] [ Open folder ]
    Playback order
      1. 01 Пролог.mp3
      2. 02 Глава 1.mp3
      3. Глава 2.mp3
      4. Глава 3.mp3
      5. Глава 4.mp3
      + 7 more, listed in the details panel.
    Goes to  Audiobooks Sorted\Джордан Роберт\Колесо Времени 3 - Джордан Роберт.m4b
```

The list is an `ol` named "Playback order": the first 5 file names (name only, folder in the title), then "+ {n} more, listed in the details panel." It is the order Approve will use.

| Cause | Sentence |
|---|---|
| No file has a track number | No file has a track number. The order comes from the file names. |
| Some have none | {k} of {n} files have no track number. |
| Tied | Some files share a track number. |
| Gap or not starting at 1 | Track numbers skip or don't start at 1. |
| Unknown | The app can't be sure of the playback order. |

**Files unclear** (`files_unclear`)

```
[ ] Дюна  ·  Фрэнк Герберт  ·  9 audio files
    Files unclear                                    [ Approve these files ] [ Choose files ]
    The tags say 12 tracks, but 9 files are here.    [ Scan again ] [ View metadata ] [ Open folder ]
    In  Z:\Audiobooks\Дюна\
        01 Пролог.mp3
        02 Глава 1.mp3
        03 Глава 2.mp3
        + 6 more, listed in the details panel.
    Goes to  Audiobooks Sorted\Герберт Фрэнк\Дюна - Герберт Фрэнк.m4b
```

| Cause | Sentence | Extra line |
|---|---|---|
| Track total differs | The tags say {n} tracks, but {m} files are here. | |
| Disc total differs | The tags say {n} discs, but {m} are here. | |
| One file of many | This file is tagged as track {x} of {n}. The other tracks aren't here. | |
| Files lack the title | {k} of {n} files don't mention this book's title. ({k}=1: "1 of {n} files doesn't mention this book's title.") | the flagged names replace the first 3 names |
| Mixed recordings | The files carry different albums or artists. They may be more than one book. | **Albums:** {A} ({a} files) · {B} ({b} files), up to 3, then "+ {n} more"; **Artists:** the same way when only artists differ |
| Parts don't number | The parts of this set don't number cleanly. | |
| Unknown | The app can't be sure which files belong to this book. | |

**Part of a bigger book** (`part_of_book`)

```
[ ] Глава 5  ·  Unknown  ·  1 audio file
    Part of a bigger book                            [ Approve as one book ] [ Scan again ]
    This file is named as one chapter.               [ View metadata ] [ Open folder ]
    Title [ Метро 2033 ]
          Title from the folder name.
    In  Z:\Audiobooks\Метро\
        Глава 5.mp3
    Goes to  Audiobooks Sorted\Без автора\Метро 2033.m4b
```

The Title field always shows here (the question is "is it a whole book, and what is it called?"), prefilled, with its basis line. Author fields follow the existing rules (section 3). Files list: up to 3 names, as for Missing files.

| Cause | Sentence |
|---|---|
| Named as a chapter | This file is named as one chapter. |
| Numbered part | The name marks this as one numbered part. |
| Same title beside it | {n} other files beside it carry the same title. (n=1: "Another file beside it carries the same title.") |
| Part of a held set | Part {i} of {n} of "{set}". |
| Folder not checked | The other files in this folder couldn't be checked. |
| Unknown | The app can't tell if this is a whole book. |

The status already says "Part of a bigger book", so the sentence gives only the evidence (copy standard: only what is crucial).

**Buttons**

| Control | Face | Tooltip | Pending |
|---|---|---|---|
| Approve (Order unclear) | Approve this order | Approve the order shown: convert if needed, rename, move to Audiobooks Sorted. | Approving... / Approving this book... |
| Approve (Files unclear) | Approve these files | Approve the files shown as one book: convert if needed, rename, move to Audiobooks Sorted. | same |
| Approve (Part of a bigger book) | Approve as one book | File what is shown as one whole book: convert if needed, rename, move to Audiobooks Sorted. | same |
| Change order | Change order | Change the playback order in the details panel. Save it there, then approve. | none (it moves focus) |
| Choose files | Choose files | Choose which files belong in the details panel. Save it there, then approve. | none |
| Scan again (any of the three) | Scan again | Check this book's folders again, for example after you rename or add files. Nothing is changed or deleted. | Scanning... / Scanning this book's folders... |

- Faces are at least 152 x 32 (as Convert what's there), labels wrap, never truncate. Accessible names start with the visible face ("Approve this order: {title clue}").
- **Change order** and **Choose files** select the row, open Manual review and move focus to the "Included audio files" heading. The panel already has Include checkboxes, Move up and Move down, and Save track review (`/api/candidate/tracks`). Order unclear shows Change order; Files unclear shows Choose files; Part of a bigger book shows neither.
- **This only works if Approve uses what he saved.** My reading of the code: `approve_automatic` ends in `reviews.tracks(..., keys, included, ...)` with `keys` taken from the row's members in catalog order, which overwrites a saved `track_order` and `included`. Ender confirms. The requirement: when Sergei saved an order or a file selection in the panel (`track_actor` user), Approve uses it. If that cannot ship in 0.22.0, drop the two buttons and add this line under the list instead: **To change it, rename the files, then press Scan again.**
- **Scan again on rows that are not missing:** the result line after an unchanged check is "Checked 14:32. No change." (replaces on each scan). If the folder changed, the row leaves and the strip says "Changes found. The book is checked again."
- Approve for a hold row keeps every other rule of section 5: safety gates stay, source removed only after the verified output is in Audiobooks Sorted.

**API (names assumed, Ender confirms).** Per book one `ask` with `kind` in `part_of_book | files_unclear | order_unclear`, `cause` (typed, from the members already in the row: no new research), `also`, `files` (the order Approve will use: `{name, folder, track, disc, flag}`, first 6) and `file_count`, `albums` / `artists` `[{name, files}]` for mixed, the numbers each sentence needs (`missing`, `total`, `tags_say`, `here`, `index`, `set`, `beside`), and `reason` (first server reason, for the Other catch-all). The UI maps cause to copy; an unknown cause uses the "Unknown" sentence.

### B5. Gaps in coverage of the 347

1. **347 vs 271.** 76 books are unaccounted for. `needs_you()` lists a held book only when its record has `until_change`, matches the book's current revision and fingerprint, and the book has no job at all (`identity in jobs` skips it). Any of the three silently drops a book. Ender names where each of the 76 sits (which chip, or which condition drops it) before the build goes to Futaba.
2. **The list is empty while the first sweep runs.** Held books saved before 0.22.0 have no `until_change`, and "Waiting for source" books are not in the list at all. Research v5 re-checks all of them once (about 3 minutes each; the 2026-10-24 diagnosis estimated about 3 days). Until then the list shows "Nothing needs your attention." while 1,200+ books are undecided: false, and ruling 10 says nothing is blocked silently. Add one line in the strip (`field-help`, hidden at zero), `n` = `automatic_processing.research.waiting + researching`:
   - running: **Still checking {n} books. More may appear here.**
   - not running: **{n} books are waiting to be checked. Start automatic processing to check them.**
   - empty list with `n` above zero: **Nothing needs your attention yet. Still checking {n} books.** (replaces "Nothing needs your attention.")
3. **Retry-later holds that repeat** are not listed (section 1: waits the app ends by itself). A hold that fails the same way on every retry (the Iron Inferno "destination unavailable" 24 h hold) does not end by itself. Offer 1 below.
4. **Refusals by the three safety gates** read "Approve was not accepted. Nothing was changed." (`askErrorText` ignores the server's reason). Minor: map "Source files changed" to the existing "This book changed. Review its details and try again." and give "Audio format needs an encoding decision" its own line: **The audio format needs a decision the app can't make yet. Select the row to read why.** Same commit if cheap.

## C. Copy sheet additions

| Where | String |
|---|---|
| Chips and tooltips | Part of a bigger book · N / Files unclear · N / Order unclear · N, with the tooltips in B3 |
| Reader-only, nothing chosen | No choice files it under Без автора. |
| Same author?, nothing chosen | No choice files it as written. Nothing is remembered. |
| Also line, reader | Also: the only name credited may be the reader. |
| Copy details failed | Couldn't copy. Select the text and press Ctrl+C. |
| Activity line | On hold — see Needs attention |
| Other catch-all | Needs you / This book needs your decision. / Reason: {reason} |
| Order list label | Playback order |
| Scan again, unchanged | Checked {time}. No change. |
| Scan again, changed | Changes found. The book is checked again. |
| Sweep line | Still checking {n} books. More may appear here. / {n} books are waiting to be checked. Start automatic processing to check them. |
| Empty, still checking | Nothing needs your attention yet. Still checking {n} books. |
| Fallback when the order cannot change in the app | To change it, rename the files, then press Scan again. |
| Safety refusal | The audio format needs a decision the app can't make yet. Select the row to read why. |

Sentences and button faces for the three chips are in B4.

## D. Checks for Futaba (committed build, seeded fixture, nothing on Z:)

1. **Fixture:** one book per cause in B4 (5 order, 7 files, 6 part, plus the unknowns), one reader-only book, one Same author? book. Each shows its own sentence, list and buttons. Control: on the as-built branch the four holds show "Needs you".
2. **End to end, not just a pressable button:** Approve one fixture each of Order unclear, Files unclear (mixed), Files unclear (track total) and Part of a bigger book. Each reaches a verified output in Audiobooks Sorted. The output's chapter order equals the row's list. The source is removed only afterwards.
3. **Saved order:** reorder in the panel, Save track review, Approve: the output follows the saved order. Control: the as-built branch ignores it. Unsaved order edits in the panel: Approve is inert with its tooltip.
4. **Counts:** All = the sum of every chip = the shortcut = the Jobs line, including the three new keys, and after each action within one poll.
5. **Coverage (read-only copy of the live catalog, no research run):** list the books per chip; "Needs you" under Other = 0 or each named; the 76 are each accounted for; every current Held book with `until_change` is listed or its drop reason is named. Report the numbers.
6. **Sweep line:** with waiting books and an empty list, the empty state and strip read as in B5.2, in both states (running, not running).
7. **Retry selected** is hidden in every "Needs your answer" chip and present in All. "Approve as is" exists only in the two bulk chips, never in the three new ones.
8. **Departure checks:** reader-only book: nothing selected, the line shows, an untouched Approve lands in Без автора, bulk never lists it. Same author?: choosing does not approve; arrow keys through the radios never press Approve; choose + Approve records the rule and clears the pair; Approve with no choice records nothing.
9. **Copy:** every string verbatim, "Also:" for a reader row has one sentence, the Copy failure line appears with the clipboard blocked, the activity line reads "On hold — see Needs attention" for a multi-line reason.
10. **Rects** at 1440, 1024, 700 and 200% zoom, with and without the dialog: the new rows (five-name lists, five buttons) do not overlap, no horizontal scroll, focus ring not clipped, buttons at least 152 x 32.
11. **Tooltips** on every new control in the packaged window.

## E. Changes Ender must make

1. Replace "Needs you" for the four holds with the three chips and rows of B3 and B4 (typed causes, file lists, the face and tooltip per chip). Other keeps stopped jobs plus the catch-all with its "Reason:" line.
2. Make Approve use the order and file selection Sergei saved in the panel; add `trackDirty` to the inert test. If that is out for 0.22.0, ship without Change order and Choose files and use the fallback line.
3. Account for the 76 (347 minus 271) and every silent drop in `needs_you()` before QA. Add the sweep line and the new empty state (B5.2).
4. Copy: "Also:" takes the first sentence; "Couldn't copy. Select the text and press Ctrl+C."; "On hold — see Needs attention"; the two "No choice ..." lines under the Author unclear radios (while nothing is chosen) and the Same author? radios.
5. Hide Retry selected in every "Needs your answer" chip.
6. Same commit if cheap: the safety-refusal lines of B5.4.
7. Update tests: `test_todo_frontend.js` has `other:0`, so "Needs you" rows were never tested. Add one fixture per cause.

Accepted as built: 1a, 1b, 1c, 2 (plus its line), 3 (plus its line), 5 (plus `trackDirty`), the rule of 6.

## F. Questions and offers

**Question for Sergei (one word)**
1. Allow a bulk "Approve as is" for "Order unclear" (143 books)? The row shows each order, but a bulk press confirms none of them, and a wrong order cannot be repaired after the source is gone. Judy's recommendation: no. (no / yes)

**Offers (not specced)**
1. List a retry-later hold that failed the same way three times, so a stuck book is never hidden behind a timer.
2. A "Join with the other parts" action for "Part of a bigger book" (same-title files beside it, a held set). The app has no manual regroup today; without it each of the 155 can only be filed as its own book or fixed on disk.
3. For "Mixed recordings": a split action. Today he can only choose files, or approve them as one book.
4. Up and Down arrows between rows (offer 2 of section 14), more useful now that 347 books are answered one by one.
