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

---

# 0.22.0 copy check (2026-10-24, Judy)

Basis: read-only look at branch `ender/0220` (worktree `C:/Antigravity Projects/Worktrees/Books Arranger/b0220`, HEAD 83601ed): `web/app.js`, `web/index.html`, `web/style.css`, `review_backend.py`, plus `todo_causes.py`, `groups.py` and `merge_service.scan_again` to confirm what the two new causes mean. Nothing launched. The counts (41 and 33 rows) are Ender's, not re-measured. Adds to part C of the 0.22.0 review; supersedes nothing.

## 1. The two new Order unclear sentences

| Cause | Sentence | Verdict |
|---|---|---|
| `conflict` | The file names and the track tags number the files differently. | **Approved verbatim.** |
| `odd_tracks` | Some track tags aren't plain numbers. | **Approved verbatim.** |

- `conflict` in the code: every file has a track tag, the tags run cleanly, but at least one file name starts with a different number than its tag. The sentence states exactly that evidence. I add no "the list follows the track tags" line: the list shows Sergei's saved order once he has saved one, so that line could become false.
- `odd_tracks` in the code: all tags are clean sequences but at least one is not digits or digits/total (for example "1." or "01 of 12"). "Plain numbers" is accurate and short.
- Both read correctly in an "Also:" line ("Also: the file names and the track tags number the files differently." / "Also: some track tags aren't plain numbers."), and both are one sentence, so the first-sentence rule holds.
- Add both to the Order unclear table in B4 as causes 6 and 7. Ender deletes the code comment "Not in Judy's sheet ... for her review" (`holdSentence`).

## 2. Spot-check of the build against the review

**Matches verbatim, no action:** the three chip labels, tooltips, set (appended after Name taken, hidden at zero) and counting order; the Order unclear sentences (five from B4, "has"/"have" handled) and the "Playback order" list (label, `ol`, 5 names, folder in the title, "+ {n} more, listed in the details panel."); the Files unclear and Part of a bigger book sentences, `In` folder line, 3 names, flagged names first, Albums / Artists line; the Title field and basis lines on Part of a bigger book; the three Approve faces and tooltips; Change order and Choose files (tooltips, shown only on their chip, `ask-convert` at 152 x 32); Scan again (face, tooltip, pending); "Checked {time}. No change."; Retry selected hidden in every "Needs your answer" chip; bulk Approve only in the two old chips; the Other catch-all "Reason:" line; the strip's "Still checking" and "waiting to be checked" lines in both states; "On hold — see Needs attention"; the reader and Same author? "No choice" lines; "Couldn't copy. Select the text and press Ctrl+C."; the safety-refusal line. Approve does use a saved order (`track_actor` user), so the Change order and Choose files tooltips are true.

**Must-fix (1)**

1. **Empty list, automatic processing not running, books waiting.** The empty state reads "Nothing needs your attention yet. Still checking {n} books." but nothing is checking, and the strip line right above says the books are waiting. That is the build following my B5.2, which was wrong for this state. Replace in that state only (`renderRows`, `nothing`):
   - not running: **Nothing needs your attention yet. {n} books are waiting to be checked.** (n = 1: "1 book is waiting to be checked.")
   - running: unchanged, "Nothing needs your attention yet. Still checking {n} books."
   - Check 6 now reads: empty list, both states, empty state and strip never contradict each other.

**Nice-to-have (3)**

1. **Mixed recordings, files with no tag.** The line reads "Albums: (none) (3 files) · Дюна (6 files)". Show **No album (3 files)** and **No artist (3 files)** (the UI maps the server's "(none)").
2. **Scan again, a file renamed while a scan runs** (`ASK_DONE.later`): "Changes found. The next library scan catalogues them." is not in my sheet, uses a spelling the app doesn't (it says "cataloged") and a word Sergei doesn't use. Replace with **Changes found. The next library scan will pick them up.**
3. **Strip line with one book, not running:** "1 book is waiting to be checked. Start automatic processing to check them." Say **... to check it.** for n = 1.

---

# 0.22.0 part-sets copy check (2026-10-25, Judy)

Basis: read-only look at branch `ender/0220` at ac08aa2 (worktree `C:/Antigravity Projects/Worktrees/Books Arranger/b0220`, matches `origin/ender/0220`): `web/app.js` (`holdSentence` L1846, `buildHoldList` L2024, `askText`, `askErrorText`, L180), `part_sets.py`, `groups.py` (`_part_sets`, `_works`, the `grouping` and `conflicts` strings), `todo_causes.py`, `merge_service.py` (`ask_payload`, `approve_book`, `scan_again`), `public_research.py` (`lookup`, `_part_set_hold`). Nothing launched. Rulings 19, 19a, 19b. Adds to the 0.22.0 review and the earlier copy check; supersedes nothing. The earlier copy check's fixes (empty state, "No album / No artist", "will pick them up", "to check it") are in the build and confirmed.

**Result:** item 1 approved. Item 2: all six sentences replaced. Item 3 approved, with two small fixes. One must-fix found outside the three items. Seven nice-to-haves (N1 to N7), one offer.

## 1. Files unclear, "The title tags name more than one book."

| String | Verdict |
|---|---|
| The title tags name more than one book. | **Approved verbatim.** |
| Books: {A} ({a} files) · {B} ({b} files) · {C} ({c} files) + {n} more | **Approved verbatim.** One file reads "(1 file)". |

- The sentence is one fact, it is true by construction (`_works` returns two or more works or nothing), and it follows the row pattern of the other Files unclear causes: evidence only ("The tags say 12 tracks, but 9 files are here."). The consequence is carried by the row: the **Books:** line below names the books, and the buttons are **Approve these files** and **Choose files**, which is the real action here (pick the files of one book). "Books:" matches "Albums:" and "Artists:".
- It reads correctly in an "Also:" line ("Also: the title tags name more than one book.").
- **Nice-to-have N1.** The server sends at most 8 works (`todo_causes.files_cause`, `works[:8]`), so "+ {n} more" can never exceed 5 and undercounts a disc set with more than 8 works. Send the full list, or the total, so "+ n more" is exact.

## 2. The six "Part of a bigger book" sentences for the ask cases

The six causes are all of `part_sets.decide`'s ask outcomes. I found no seventh: "one part" cannot occur (a set has at least two files) and maps to the "unclear" sentence anyway. All six are **replaced**. Why:

1. All six are two sentences. The row pattern is one. In three of them the second sentence is an instruction ("Check that they are one book." / "Approve them as one book only if they are one.") that tells Sergei nothing the status ("Part of a bigger book") and the button ("Approve as one book") don't. In two the first sentence restates the status ("These files may be the parts of one book."). The sixth (book words) carries a real consequence but in a second sentence.
2. Two state a guess as a fact. "The files are seasons of a series" fires on any season or episode number in a file name, title tag or chapter title. "Named as books of a series" fires on any "Книга I" or "Book 2" and says nothing about a series.
3. "Joined, these 4 files would run 32.2 hours." opens with a dangling "Joined,".

Form of every replacement: **the evidence, then what it makes uncertain, in one sentence.** The status already says what kind of row it is.

| Cause (code) | Built | Replace with |
|---|---|---|
| Seasons (`set_seasons`) | The files are seasons of a series. Approve them as one book only if they are one. | **Season or episode numbers in the names or chapters suggest separate books.** |
| Over 30 hours (`set_long`) | Joined, these {n} files would run {h} hours. Check that they are one book. | **Together these {n} files run {h} hours, which is long for one book.** |
| Book words (`set_book_words`) | The files are named as books of a series. They may be one book or several. | **The names or chapters number the files as books, so they may be separate books.** |
| Several authors (`set_authors`) | The files credit different authors or readers. Check that they are one book. | **The files credit different authors or readers, so they may be separate books.** |
| Chapters don't settle it (`set_unclear`) | These files may be the parts of one book. Their chapters don't settle it. | **The chapters don't show whether these files make one book.** |
| Chapters unreadable (`set_unreadable`, the sixth, not in your list) | These files may be the parts of one book. Their chapters couldn't be read. | **The chapters couldn't be read, so the app can't tell whether these files make one book.** |

- `{n}` is at least 2, so no singular case. `{h}` is the server's value rounded to one decimal, over 30 ("41.3 hours", "31 hours"); the word "hours" stays spelled out as everywhere else in the app.
- The first four end in "separate books" on purpose: that is the doubt each one raises. "Book words" says "number the files as books" so it does not assert a series.
- First-sentence rule for "Also:" lines: every replacement is one sentence, so it stands alone if it ever appears there (it cannot today: Part of a bigger book is first in the order).

**Row pattern, checked for the six causes:**

| Part of the pattern | Result |
|---|---|
| One sentence | As built: no (two each). After the replacements: yes. |
| File list in order | **Yes.** `groups._part_sets` orders the members by track tag, else by the numbers in the file names, and the row lists them in that order: "In {folder}", 3 names, "+ {n} more, listed in the details panel." (the panel's Included audio files lists all of them, so that pointer is true). The list is not labelled as the join order: see N2. |
| Faces | **Yes.** **Approve as one book** (ruling 19b's own words) and **Scan again**, 152 x 32, no Change order or Choose files. Tooltip: see N3. |
| Status, Title field, "Goes to" | Unchanged and consistent. |

## 3. Missing files, "Part 3 of 3" (incomplete part sets)

| String | Verdict |
|---|---|
| In {folder} / Part {n} of {total} (one line per missing part, up to 3) | **Approved verbatim.** |

- It names the exact thing that is missing (ruling 10) in the vocabulary of the rest of the chip ("Part {i} of {n} of ..."). The missing file was never catalogued, so its real name is unknown, and a number is the only true name. The lines agree with the sentence "{k} of {n} files {is/are} missing." because the server builds both from the same numbers.
- Row pattern: one sentence, the list in ascending order, **Scan again** and **Convert what's there** (shown because at least one part is present). Both tooltips stay true: Convert uses the present members only (`approve_book`, `without_missing`).
- **Nice-to-have N4.** The sentence reads like a file that vanished, but this one was never here and the app knows from the track tags. Sergei cannot judge a bad tag ("1/3" on a two-part book) without knowing where the claim comes from. For part-set rows only (`missing.parts` present), replace the sentence with **The track tags say there are {total} parts, but part {n} isn't here.** (several: **The track tags say there are {total} parts, but {k} aren't here.**). `{total}` is the declared total, else the highest track number.
- **Nice-to-have N5.** More than 3 missing parts shows "+ {n} more, listed in the details panel." The panel lists catalogued members only, and a missing part is not one, so the pointer is false. For part-set rows use **+ {n} more.** (Reachable with four or more missing parts, for example 3 of 12 present.)

## 4. Found outside the three items

**Must-fix (1)**

1. **Names and rule numbers on screen.** The details panel's evidence line (`#candidate-evidence`, `app.js` L180) prints the group's `grouping` text for every selected candidate, joined with " · ". Three new strings in `groups.py` break the copy standard (no names, no history, no doc references):
   - L545: `One book (Sergei 2026-10-24, parts stay together): files of one folder with the {basis}`
   - L550: `One book (Sergei 2026-10-24, ruling 19): files of one folder with the {basis}`
   - L478: `Parts of one folder that share their album and artist: their chapters decide whether they are one book (ruling 19)`

   Replace with:
   - L545 and L550: **One book: files of one folder with the {basis}.** For L550 also drop the parenthesis from the basis, so it reads "...with the same album and one author." (the words "the parts of one book" repeat "One book").
   - L478: **Parts of one folder that share their album and artist. Their chapters decide whether they are one book.**

   Ender checks that stored groups pick up the new text: `groups.current` compares revisions only, so an existing group may keep the old string until it is regrouped. The older line "Per-file embedded/filename identity partition; recording remains unverified" is not new and is not touched here.

**Nice-to-have (N2, N3, N6 and N7 here; N1, N4 and N5 are above)**

- **N2. The join order is not labelled.** Ruling 19 says the app asks "with the proposed joined order". The three unnumbered names under "In {folder}" don't say they are that order, and a set can have up to 30 parts. For the six set causes use the Order unclear list: label **Playback order**, a numbered `ol`, the first 5 names, then "+ {n} more, listed in the details panel." (`buildHoldList`: the same branch as `order_unclear`, keyed on a cause that starts with `set_`.) A wrong order cannot be repaired after the source is removed (ruling 2).
- **N3. Approve tooltip for the six set causes.** Built: "File what is shown as one whole book: convert if needed, rename, move to Audiobooks Sorted." A join always re-encodes (ruling 19a, method A, a cost Sergei accepted), so "if needed" understates it. Use **Join the files shown, in this order, into one book: re-encode the audio once, rename, move to Audiobooks Sorted.** Face unchanged. Other Part of a bigger book rows keep the built tooltip.
- **N6. Chip tooltip.** "Show books that may be only one part of a bigger book." is wrong for a row of seven files. Use **Show books that may be parts of a bigger book.**
- **N7. Refusal when the destination moved** (Senua m1: the shown path travels with the press). It maps to the "changed" code and reads "This book changed. Review its details and try again." The book didn't change, its destination did, and the row has already re-read its Goes to line. Give it its own code and line: **The destination changed. Check the Goes to line and try again.**

## 5. Offer (not specced)

1. **A "Keep as separate books" press on these rows.** Seasons, book words and several authors all say "may be separate books", but the only press is **Approve as one book**. If Sergei decides they are separate, the row has no answer for him and stays listed. The backend already records separate volumes for the automatic decision (`groups.record_volumes`), so the action may be cheap. Ruling 19b names only "Approve as one book", so this is Sergei's call: one word, yes or no.

## 6. Changes Ender must make

1. The six sentences of section 2 (`holdSentence`, `set_*`). Update `tests/test_todo_holds_frontend.js` L119-121, which asserts the old text.
2. The three `grouping` strings of must-fix 1, and confirm stored groups pick them up.
3. If taken: N1 (works total), N2 (numbered list), N3 (tooltip), N4 and N5 (part-set missing sentence and pointer), N6 (chip tooltip), N7 (destination refusal).

## 7. Copy sheet additions (verbatim once built)

| Where | String |
|---|---|
| Files unclear, works | The title tags name more than one book. / Books: {name} ({n} files) · ... + {n} more |
| Part of a bigger book, sets | the six sentences of section 2 |
| Missing files, part set, line | Part {n} of {total} |
| Missing files, part set, sentence (N4) | The track tags say there are {total} parts, but part {n} isn't here. / ... but {k} aren't here. |
| Missing files, part set, more (N5) | + {n} more. |
| Approve tooltip, sets (N3) | Join the files shown, in this order, into one book: re-encode the audio once, rename, move to Audiobooks Sorted. |
| Chip tooltip (N6) | Show books that may be parts of a bigger book. |
| Destination moved (N7) | The destination changed. Check the Goes to line and try again. |
| Details panel, grouping | One book: files of one folder with the {basis}. / Parts of one folder that share their album and artist. Their chapters decide whether they are one book. |

## 8. Checks for Futaba (add to part D of the 0.22.0 review)

1. **Fixture:** one set per cause (six), one works book (three or more works), one part set missing one part, one missing four or more. Each shows its own sentence, list and buttons verbatim.
2. **Panel:** select each fixture. A search of the whole page text for `Sergei` and `ruling` finds nothing. Control: the unfixed branch shows both.
3. **Order:** each set row's list matches the order of the joined output's chapters (the existing end-to-end check D2).
4. **Missing parts:** the sentence's total, the "Part n of m" lines and the "+ n more" line agree; Scan again with the part restored removes the row; Convert what's there queues from the present parts.
5. **Rects and tooltips** as D10 and D11 for the new rows (a set row with five names and two buttons; a Missing files row with three "Part n of m" lines).

---

# Keep as separate books — spec (2026-10-25, Judy)

Basis: Jane's call under ruling 10 ("clear options to act upon"), taking offer 1 of the part-sets copy check. Sergei sees it in the morning and can veto it. Read-only look at branch `ender/0220` (worktree `C:/Antigravity Projects/Worktrees/Books Arranger/b0220`, HEAD ac08aa2): `web/app.js` (`buildAskActions`, `askMode`, `askInert`, `askPress`, the `ASK_*` tables, `renderGoesTo`), `web/style.css` (`.ask-convert`), `part_sets.decide`, `groups.py` (`record_volumes`, `volume_parts`, `build`, the four grouping steps), `public_research._part_set_hold`, `merge_service` (`_todo`, `scan_again`), `local_identity` L1757-1770. Nothing launched. Geometry is target geometry for Futaba. Spec only: no code. It adds a button to the set rows of the part-sets copy check, section 2, and supersedes nothing.

**If Sergei vetoes it:** delete the button, the route and the strings of section 9. Nothing else depends on it.

## 1. In brief

1. A set row that says "may be separate books" gets a second answer, **Keep as separate books**, beside Approve as one book.
2. It shows on all six set causes and nowhere else (section 4).
3. It records the files as separate books and touches no file. Each file becomes its own book and is checked like any other. **It approves nothing.**
4. The answer is remembered per file until the file changes.
5. The row leaves on the press. The strip says how many books it became. The existing "Still checking" line carries the progress.
6. No dialog, no bulk, no accelerator.

## 2. The control

| Part | String or rule |
|---|---|
| Face | Keep as separate books |
| Tooltip | Make each file shown its own book. Nothing is joined. Each book is checked again. |
| Pending face / hint | Keeping... / Keeping these files separate... |
| Accessible name | Keep as separate books: {title clue} (the visible face comes first, WCAG 2.5.3) |
| Refused | Keep as separate books was not accepted. Nothing was changed. |
| Other refusals | Existing lines: "This book changed. Review its details and try again." (a file changed or was added since the row was listed), "Connection interrupted. Check the status above before trying again." |
| Panel edits open | `aria-disabled`, tooltip "Save or discard the edits in the details panel first." Only that test of `askInert` applies: the Title-empty and Name-taken tests belong to the join, and Keep does not use the Title field. |
| Style | `quiet row-retry ask-convert`, like its neighbours. No accent fill. |

- The tooltip names the contrast with the button beside it ("Nothing is joined", where the other tooltip says the audio is re-encoded once) and says the press is not an approval ("checked again").
- A press is one request at a time. While it runs, the row's other buttons are `aria-disabled` with the existing "Another operation is in progress."

## 3. Where it sits

Order in `.row-actions`: **Approve as one book, Keep as separate books, Scan again, View metadata, Open folder.**

```
[ ] Тёмная башня 1-4  ·  Стивен Кинг  ·  4 audio files
    Part of a bigger book                      [ Approve as one book ] [ Keep as separate books ]
    The names or chapters number the files     [ Scan again ] [ View metadata ] [ Open folder ]
    as books, so they may be separate books.
    Title  [ Тёмная башня               ]
           Title from the folder name.
    Playback order
      1. Книга 1 - Стрелок.m4b
      2. Книга 2 - Извлечение троих.m4b
      3. Книга 3 - Бесплодные земли.m4b
      4. Книга 4 - Колдун и кристалл.m4b
    As one book  Audiobooks Sorted\Кинг Стивен\Тёмная башня - Кинг Стивен.m4b
```

- The two answers to one question are neighbours (Fitts, Hick). Approve stays first: it is the app's proposal, and the list and path shown are what it would do. Scan again follows, because it is a re-check, not an answer.
- **Tab order of the row:** row, Select, Title, Approve as one book, Keep as separate books, Scan again, View metadata, Open folder. A native `button`: Enter and Space press it once, and `keydown` stops at the button as on its neighbours.
- **No accelerator.** Ctrl+Enter stays Approve only: one shortcut, one meaning.
- **Geometry:** at least 152 x 32. The face wraps to two lines and never truncates (`ask-convert`). Five buttons wrap inside `.row-actions` (max 280 px), as on the Order unclear rows. Nothing is absolutely positioned, there is no dialog and no popover, so nothing covers anything. "Keeping..." is shorter than the face, so the row does not resize.

## 4. Which causes show it

**Rule: the row asks whether these files are one book, and "no" is a real answer.** All six set causes (`ask.cause` starts with `set_`, so two or more `.m4b` files; `setCause`). One rule, no per-cause exceptions.

| Cause | Shows | Why |
|---|---|---|
| Seasons | yes | The sentence says "separate books". |
| Book words | yes | Same. |
| Several authors | yes | Same. |
| Over 30 hours | yes | "Long for one book" is the doubt. A real 31-hour book is why Approve stays. |
| Chapters don't settle it | yes | Only he knows. Both answers are fair. |
| Chapters unreadable | yes | The app can't tell, so he needs both answers. The press reads no chapters. Scan again is the re-read. |

**Not shown** (hidden, not disabled: an action with nothing to act on is noise):
- Single-file Part of a bigger book rows (chapter, numbered part, same title beside it, part of a held set, folder not checked). There is nothing to separate, and Approve as one book already files that one file as its own book.
- Missing files rows of a part set. They have Convert what's there.
- Files unclear (mixed recordings, title tags name more than one book) and Order unclear. Those are not whole `.m4b` sets, so this store does not cover them. The split action stays an offer (offer 2).

## 5. What the press does

1. **Records the set as separate books.** Per file: its size and modified time, basis "Kept separate by you", with the date. This is the store the automatic "separate volumes" decision already writes (`groups.record_volumes`, `volume_parts`). The catalog regroups by itself and each file becomes its own candidate (scope "Volume of a series"). No file is moved, tagged, re-encoded or deleted.
2. **It approves nothing.** Ruling 6b makes Approve final for the one book he approves. This press only answers "one book or several?". Each new book goes through normal identity and the automatic queue:
   - Title from its own tag, else its file name. A file with no title of its own is named set name + part number (rulings 13 and 15), with the basis line "Set name + part number."
   - Author as always. A missing title or author, an unclear author, a taken name or a safety gate puts that book in this list under its own reason.
3. **A "no" must not come back as four questions.** None of the files returns as "Part of a bigger book" for the question he just answered (named as a numbered part, same title beside it, part of a held set). My reading of `local_identity` L1757-1770: the numbered-part naming covers a single `.m4b` only when its file name ends in a part number. A kept-separate file needs the same treatment whatever its name. Ender confirms. A file still held for its own reason (its name is only a chapter label, say) returns under that reason, for example Missing title or author with the Title field filled in.
4. Refusals and the busy rule are those of Scan again: the row's revision must match, and the press waits while a library scan runs (`scan_active`).

## 6. Remembered

Yes, and per file, not per row.
- A file's fact holds while it keeps its size and modified time. All four grouping steps leave a recorded file alone (`_part_sets`, `_split_plan`, `_same_title_sets`, `_same_album_parts`), so the set is not formed again and not asked again. A restart, a library scan or a poll changes nothing.
- A file that changes (re-tagged, replaced) or is renamed loses its fact and is judged alone. The other files stay separate. The set is asked again only if two or more unrecorded files of the folder form a set again, for example new parts that arrive together.
- Nothing shows "remembered": no banner, no count, nothing to clear. It shows as the absence of the question.
- **No way back in this build.** Until a book is filed nothing on disk has changed, so an undo is cheap to add later (offer 1). Once a book is filed, a merge belongs to the later rename pass (ruling 21), as for Имаджика and Зелёная миля.

## 7. The row's exit and progress

| Moment | Row | Strip line (polite live region) |
|---|---|---|
| Press | Face "Keeping...", hint "Keeping these files separate...", the row's other buttons `aria-disabled`, row size unchanged | none |
| Done | Hint "Kept as separate books. Each is checked again." Fields, list and path hide. The row leaves at the answer or the next poll (the old candidate is no longer current). | Kept as {n} separate books. Each is checked again. |
| Refused | Row stays, hint turns `--warning` with the refusal line, nothing recorded | none |

- **Focus** after success is as after Approve: the next row's first working control, else the Status filter, `preventScroll`.
- **The Title typed on this row is dropped with the row.** Keep does not use it, and a title for something that is no longer one book has no meaning. It does not block the press.
- **Counts drop within one poll:** the Part of a bigger book chip, All, the shortcut and the Jobs line each lose the set. They change again only as new books need him.
- **Progress needs no new surface.** The {n} new books count as "still checking" until researched, so the strip's existing line carries them: "Still checking {n} books. More may appear here." (running) or "{n} books are waiting to be checked. Start automatic processing to check them." (not running). A book that needs him appears in this list under its own reason. The rest are filed by the app and show under Audiobook Ready like any book. Ender confirms the new candidates count in that n at the next poll. The empty state "Nothing needs your attention yet. Still checking {n} books." stays true.

## 8. Knock-on: the destination line

On a row that offers Keep, the line's label reads **As one book** instead of "Goes to" (`renderGoesTo`). The path is true only for Approve as one book, and with two buttons "Goes to" reads as a promise for both. "Already there" (taken) is unchanged and every other row keeps "Goes to". The Title field and the "Playback order" list stay: they belong to the join.

## 9. Copy sheet additions (verbatim once built)

| Where | String |
|---|---|
| Face | Keep as separate books |
| Tooltip | Make each file shown its own book. Nothing is joined. Each book is checked again. |
| Pending face / hint | Keeping... / Keeping these files separate... |
| Row hint, done | Kept as separate books. Each is checked again. |
| Strip line, done | Kept as {n} separate books. Each is checked again. |
| Refused | Keep as separate books was not accepted. Nothing was changed. |
| Accessible name | Keep as separate books: {title clue} |
| Destination label, rows with Keep | As one book |

## 10. Changes Ender must make

1. `app.js`: add `separate` to `ASK_LABELS`, `ASK_TIPS`, `ASK_PENDING`, `ASK_DONE` (status null) and `ASK_REFUSED`. `buildAskActions`: kinds `['approve','separate','scan']` when `setCause(ask)`. `askMode`: for `separate`, inert on the panel-edit test only (split it out of `askInert`). `askPress`: a branch for `separate` that sends no values, drops the row's draft and sets the strip line with n. `renderGoesTo`: the "As one book" label.
2. Route `/api/candidate/keep-separate` with `{library, id, revision}`, answering `{kept: n}`. It re-reads the row at that revision (`changed` as Approve), refuses a row that is not a set hold, calls `groups.record_volumes` with the basis, clears `_needs_cache` as Scan again does, and follows Scan again's busy rule.
3. Section 5.3: a kept-separate file never returns as Part of a bigger book for this set.
4. Tests: one fixture per cause (the six of the part-sets check, 8.1), the press, the leave, the no-return, the per-file memory.

## 11. Checks for Futaba (committed build, seeded fixture, nothing on Z:)

1. **Fixture:** the six set causes, plus one single-file numbered-part row, one part set missing a part, one Order unclear and one Files unclear row. Keep is in second place on the six and nowhere else. Control: absent on the unfixed build.
2. **Press on a four-file seasons set:** the four sources keep their size and time, nothing new appears in Audiobooks Sorted at the press, the row leaves within one poll, the strip line is verbatim with n = 4, and the chip, All, shortcut and Jobs line agree.
3. **Four books:** four candidates, each with its own proposal. The "Still checking" count rises by 4 at the next poll, in both automatic states. A file with no title shows "{set} {number}" with "Set name + part number." Control: Approve as one book on a sibling fixture still joins.
4. **No return:** none of the four comes back as Part of a bigger book. Fixture names with a trailing number and without.
5. **Remembered:** after an app restart and a library scan with the files unchanged, the set is not listed again. Change one file's size or time: that file is judged alone, the other three stay separate, and no row for the set appears.
6. **Refused:** a forced refusal reads the verbatim line, the row stays and nothing is recorded (the store is unchanged). A file added to the folder after the row was listed gives "This book changed...".
7. **Pending and edits:** "Keeping..." shows, the other row buttons are `aria-disabled`, the row does not resize. With an unsaved panel edit Keep is inert with its tooltip. A Title typed on the row does not block it and is not used.
8. **Keyboard, tooltip, rects:** Tab order of section 3; Enter and Space press once; the tooltip is present in the packaged window. At 1440, 1024, 700 and 200% zoom with five buttons: no two rects intersect, no horizontal scroll, focus ring not clipped, button at least 152 x 32, face wraps and never truncates.
9. **Not in bulk:** Part of a bigger book has no bulk button (Retry selected and Approve as is are both absent).

## 12. Offers (not specced)

1. **Join again:** an undo on kept-separate books before they are filed (remove the file facts, regroup). Cheap now, impossible after filing.
2. **The same answer for Files unclear** (mixed recordings, title tags name more than one book): these are not whole `.m4b` sets, so they need a split plan, not this store. Offer 3 of the 0.22.0 review.

---

# Delete book — spec (2026-10-25, Judy)

Basis: ruling 23 (`Team/Docs/BooksArranger_Rulings_2026-10-24.md`, Sergei, 2026-10-25) and Futaba's interim QA on b946ee7. Read-only look at local branch `ender/0220c` at 55d664b (`origin/ender/0220c` is not a fetched ref here, and I did not fetch): `web/app.js` (the `ASK_*` tables, `buildAskActions`, `askMode`, `askPress`, `askLeave`, the row builder L225-290, `rowAction` L796, `attentionText` L1587, `sizeText`), `web/style.css` (tokens, `.quiet`, `.row-actions`, the dialogs), `web/index.html` (the four existing dialogs), `audio_jobs.attention_summary` L719 and `source_remedy` L54, `reacquire_sources.py`, and `Docs/BooksArranger_DeletePaths_Audit_2026-10-24.md`. Nothing launched, no rects measured: geometry is target geometry for Futaba. Contrast ratios are calculated from the tokens. Names in the mockups are examples, not live rows. Spec only: no code, not committed.

**Supersedes:** for the two broken-audio rows only, the Reacquire UX line "no Delete files button" and the advice "Keep this original" (`BooksArranger_Reacquire_UX_2026-10-20.md`). Ruling 23 is Sergei's explicit exception to ruling 2. Remove from list, Scan again and Convert what's there stay as specced.

## 1. In brief

1. **Delete book** is a row action on three kinds of row only: Missing files, Need to reacquire, Source audio needs replacement (section 2).
2. Danger style: outlined red on the row, solid red in the dialog. It is the last button of the row, on its own line, apart from every other button.
3. It always asks first, in a native dialog that lists every file by path, with the count and the total size. It says the app can't undo it and that nothing in Audiobooks Sorted is touched. Cancel has focus; Enter never confirms.
4. It deletes the listed files and nothing else. Only when every listed file is gone does it delete the app's records of the book. Records go last, so nothing is half-forgotten.
5. Success: the row leaves and one strip line confirms. Partial failure or refusal: the dialog names exactly which files and why, and the book stays listed.
6. No bulk, no accelerator, not in the details panel, no context menu.
7. Duplicate-recording rows and Files unclear rows do not get it (section 2).

## 2. Which rows show it

**Rule: the server decides.** It sends a typed `delete` offer only when the app itself holds a verdict that the book is incomplete, or broken beyond its own repair. The UI never infers it from copy. No offer means no button (hidden, not disabled: an action with nothing to act on is noise).

| Row | Shows | Why |
|---|---|---|
| Missing files, some files present (includes part sets, "Part 2 of 3") | **yes** | Sergei: "parts are missing". The files that are present are deleted. |
| Missing files, none present ("All files missing") | **yes**, beside Remove from list | Nothing is on disk, so it only forgets the book. Remove from list is the reversible one (the book returns if its files do); Delete book is not. |
| Need to reacquire (analysed unsafe damage) | **yes** | The app analysed the audio and cannot repair it safely. |
| Source audio needs replacement (a single MP3 failed its full audio check, and the app's own repair or Retry already ran) | **yes** | This is the Iron-style decode failure after repair failed. |
| Can retry, Can repair, and the MP3 "Retry checks it again" row | no | The app can still fix it. Repair comes first. |
| Stopped — see details, Other, Needs you | no | No verdict. A multi-file audio failure has none today. When the app can say "not repairable" it sends the same offer and the button appears (offer 4). |
| Original changed, Audiobook problem | no | A finished audiobook may exist; recovery copies are kept. |
| M4B not supported, Name taken, every "Needs your answer" chip | no | Not broken. |
| Files unclear ("The tags say 12 tracks, but 9 files are here.") | no | Evidence, not a verdict: the tags may be wrong (offer 3). |
| Duplicate-recording rows ("Identical verified recording already arranged", "Possible duplicate recording") | **no** | See below. |

**Duplicates: no.** (1) Neither is broken or incomplete, and Sergei already has the book, so "reacquire" has no meaning. (2) "Possible duplicate recording" may be a different reading, the only copy of it. (3) Removing a verified duplicate is a different act with a different guarantee: it falls under ruling 2 (a source goes only after its result is verified in Sorted), so it needs its own action that shows the Sorted copy as proof. That is offer 1 and question 2, not specced here. Futaba's m-3 dead end stays open until then.

Also hidden once the row has flipped to Queued (Convert what's there). Inert (`aria-disabled`) with the existing "Another operation is in progress." or "Local server unavailable." while a press runs or the server is gone. On Need to reacquire with some originals already gone, the list holds only those still there; with the source drive offline the preview refuses (section 4).

## 3. The button

```
[ ] Новая плоть  ·  Сборник  ·  8 audio files
    Missing files                                          [ Scan again ] [ Convert what's there ]
    1 of 9 files is missing.                               [ View metadata ] [ Source folders ]
    In  Z:\Audiobooks\Сборники\Новая плоть (2016)\
        03 - Павлов Михаил - Засор.m4b                     [ Delete book ]
    Goes to  Audiobooks Sorted\Сборники\Новая плоть - Разные авторы.m4b

[ ] Червь 19  ·  Джон МакКрэй  ·  1 audio file
    Need to reacquire                                      [ View metadata ] [ Open folder ]
    The audio is damaged and cannot be repaired safely.
    Delete the book, then get a new copy.                  [ Delete book ]
```

| Part | String or rule |
|---|---|
| Face | Delete book |
| Tooltip, files on disk | Delete this book's files from disk and remove the book from the app. You confirm first. |
| Tooltip, none on disk | Remove this book from the app for good. No files are left to delete. You confirm first. |
| Pending face / hint | Checking... / Checking this book's files... |
| Accessible name | Delete book: {title clue} (visible face first, WCAG 2.5.3) |
| Style | `quiet row-retry danger`: `--surface` fill, `--error` text and 1px `--error` border (9.12:1 on `--surface`, 6.78 on `--row-hover`), hover fill `--row-hover`. Never an accent fill. It differs from its neighbours by word, position and hue, so greyscale and colour-blind users still read "Delete". |
| Disabled / pending | `aria-disabled` with the existing `--disabled` look; focus kept. |

**Position (Fitts: the farthest, hardest target; Hick: out of the answer group).**
- Last in `.row-actions`, after View metadata and Source folders / Open folder, on a line of its own: a zero-height flex break (`flex-basis:100%;height:0`) and `margin-top:8px` on the button, so at least 16 px of clear space above it. It is never on the primary's line, so Scan again, Convert what's there, Remove from list and Approve are never its neighbours.
- Tab order: row, Select, fields, primary, second action, View metadata, Source folders / Open folder, **Delete book**. Native `button`; Enter and Space press once; `keydown` stops at the button like its neighbours. **Ignore `event.repeat`** on it, so a held Enter cannot open the dialog twice.
- At least 96 x 32; the face never truncates. Nothing is absolutely positioned.
- The two Stopped rows have no primary button today (`rowAction` returns null for Need to reacquire, and Source audio needs replacement carries no Retry), so this button is built beside View metadata, not through `rowAction`.

## 4. The confirmation

A native modal `dialog` in the approve-dialog pattern: 560 px max, background inert, `aria-labelledby` the title, `aria-describedby` the body. It is the only overlay, and every state below is inside it, so nothing else is ever covered.

```
+-------------------------------------------------------------------+
| Delete this book?                                                 |
| Новая плоть — Сборник                                             |
| 1 of 9 files is missing.                                          |
|                                                                   |
| These 8 files (1.4 GB) will be deleted from your disk. The app    |
| can't undo this.                                                  |
| +---------------------------------------------------------------+ |
| | Z:\Audiobooks\Сборники\Новая плоть (2016)\01 - ... .m4b       | |
| | Z:\Audiobooks\Сборники\Новая плоть (2016)\02 - ... .m4b       | |
| | ...                                          (scrolls, 40vh)  | |
| +---------------------------------------------------------------+ |
| Other files in the folder stay.                                   |
|                                                                   |
| The app forgets this book. If you get it again, it's found as a   |
| new book. Nothing in Audiobooks Sorted is touched.                |
|                                                                   |
| [ Cancel ]                      [ Delete book and 8 files ]       |
+-------------------------------------------------------------------+
```

| Part | String |
|---|---|
| Title | Delete this book? |
| Book line | {title} — {author} (just {title} when the author is unknown) |
| Reason line | the row's own sentence, verbatim: "1 of 9 files is missing." / "All 2 files are missing." / "The audio is damaged and cannot be repaired safely." / "The app cannot repair this damage without risking missing audio." / "The MP3 failed its full audio check and can't be repaired by the app." |
| Files line | These {n} files ({size}) will be deleted from your disk. The app can't undo this. / This file ({size}) will be deleted from your disk. The app can't undo this. |
| No files | No files are left on disk. Only the app's record of this book is deleted. |
| List | `.path` lines, the full absolute path of each file, `tabindex="0"`, `role="group"`, name "Files to delete", 40vh scroll. Shown when n is above 0. |
| Folder line | Other files in the folder stay. (shown when n is above 0) |
| Forget line | The app forgets this book. If you get it again, it's found as a new book. Nothing in {Audiobooks Sorted} is touched. ({Audiobooks Sorted} is `outputName()`.) |
| Cancel | Cancel / Close without deleting anything. |
| Confirm | Delete book and {n} files / Delete book and 1 file / Delete book (no files) |
| Confirm tooltip | Delete this book and its {n} files. The app can't undo this. / Delete this book and its file. The app can't undo this. / Remove this book from the app. No files are touched. |

**Danger in the dialog.** The confirm button is the only filled one: `--error` fill, `--on-accent` text (10.42:1), border `--error`; hover `--error-hover` #FFC7C7 (12.02), pressed `--error-pressed` #F09A9A (8.26). Two new tokens, no new hue. The focus ring has a 2 px offset, so it is read against the dialog's `--surface` (11.18), not the red fill.

**Enter must not confirm.**
1. Cancel has `autofocus` and is the only default. Confirm never has `autofocus`.
2. No `form method="dialog"`, no default or submit button: Enter in the body or the list does nothing.
3. Confirm is reached only by Tab or a click. The Enter that pressed Delete book cannot reach it, because focus is on Cancel when the dialog opens.
4. Ignore `event.repeat` on both buttons. On press Confirm goes `aria-disabled` at once, so a double press runs once.
5. Esc and Cancel close it and return focus to the row's Delete book button (`preventScroll`). If the row is gone, focus goes to the Status filter.

**States, all in this dialog.** The press on the row reads "Checking..." while the server builds the list; the dialog opens when the answer arrives. A refusal found then opens the dialog in its refusal state, so Sergei never confirms something that will be refused.

| State | Title | Body | Buttons |
|---|---|---|---|
| Confirm | Delete this book? | as above | Cancel (focus), Confirm |
| Deleting | unchanged | Confirm face "Deleting..." (`aria-disabled`); a polite status line: "Deleting {n} files..." / "Deleting 1 file..." / "Removing this book..." | Cancel `aria-disabled`, tooltip "Deleting can't be stopped."; Esc ignored |
| Refused | Can't delete this book | the refusal line (below), plus its file list when it has one | Close (focus) |
| Partial | Not everything was deleted | "Deleted {k} of {n} files. {f} could not be deleted:" then one block per file: the path, and under it the cause in `--muted`; then "The book stays listed. Press Delete book to try these again." | Close (focus) |
| Outcome unknown | Delete may not have finished | the unknown-outcome line | Close (focus) |

Close: face "Close", tooltip "Close this message."

| Cause line (under each failed path) | When |
|---|---|
| In use by another program. | locked by another process |
| Access denied. | permission |
| Can't reach the drive. | share offline or dropped |
| Couldn't delete it. | anything else (raw text only in Technical details) |

| Refusal | Line |
|---|---|
| A file also belongs to another book (one) | "{file}" also belongs to "{other}". Nothing was deleted. |
| Several | {n} of this book's files also belong to other books. Nothing was deleted. (List: each path, with Also in "{other}" under it.) |
| A finished audiobook exists | A finished audiobook of this book is in {Audiobooks Sorted}. Nothing was deleted. |
| Source drive not reachable | Can't reach {root}. Nothing was deleted. |
| Book is being processed | This book is being processed. Nothing was deleted. |
| Book changed (revision) | This book changed, so nothing was deleted. Review its details and try again. |
| Folder differs from the list | The folder doesn't match the list, so nothing was deleted. Press Delete book to see the current list. |
| Any other typed refusal | Delete was not accepted. Nothing was deleted. |
| Connection lost | Connection interrupted, so the delete may have gone through. Check the list before trying again. |
| Untyped server error | Delete did not finish. Check the list before trying again. |

**"Nothing was deleted" is said only for a typed refusal that the server issues before it touches the first file.** Every other failure is outcome unknown and says so (the pattern alert in Futaba's QA: a message must report outcome, not intent). The NAS may keep deleted files in its own recycle folder; the app can neither see nor empty it, so no string says "permanently".

## 5. What the press does

1. **Preview.** The first press asks the server for the delete list. It is built from the disk now: each of the book's catalogued audio files that exists, under a configured source folder and not under the output folder, with its size. The same call runs every refusal check, so a refusal shows before he confirms.
2. **Confirm.** The press sends the revision and the paths the dialog showed, nothing else. The server deletes only if the list it builds now equals the list shown; otherwise it refuses ("Folder differs from the list").
3. **Delete.** One file at a time, through the same verified-handle and boundary checks as source cleanup. **No recovery copy is made:** ruling 23 says fully removed, and a copy under `data/source-recovery` would keep the broken audio on disk. A file that fails does not stop the others: one locked file must not keep the other seven.
4. **Records last.** Only when every listed file is confirmed gone (a file already absent counts as gone) does the app delete everything it holds about the book, in one catalog transaction: its candidate group and context, reviews, saved track order and manual drafts, research records and evidence, jobs with their journals and set-aside marks, the reacquire marker, its kept-separate file facts, the file inventory rows and read errors of its files, its working files on the app's own drive, and the in-memory caches. It keeps every other book, the author rules and aliases Sergei taught, the settings, and finished audiobooks in Sorted with their records.
5. **If a file fails, no record is deleted.** The book stays listed. The deleted files are gone, so the next poll reads the row as Missing files ({k} of {n}) and the next Delete book lists only what remains. A crash between 3 and 4 ends the same way. Nothing is forgotten while its files are on disk.
6. **Reacquire.** A new copy, at the same path or elsewhere, is a new book: new identity, fresh research. Nothing of the old book is carried: no approval, review, hold, hash, marker, draft, "Kept separate" fact or read error. The archived-marker hold ("Damaged-source entry archived; use the newly discovered replacement") must not outlive the book.
7. **Never touched:** anything under Audiobooks Sorted, another book's files in the same folder, covers, text and other files, the folder itself (the existing empty-folder cleanup handles a folder left empty, by its own rules), a source root.

## 6. After the press

| Outcome | Row | Strip line (polite live region) |
|---|---|---|
| Success | Hint "Deleted. The book is gone from the app." Buttons hidden. The row leaves at the answer or the next poll. Its selection, draft, "Checked" time and details panel go with it. | Deleted 1 book and {n} files ({size}). / Deleted 1 book and 1 file ({size}). / Deleted 1 book. No files were left on disk. |
| Partial | Stays. Hint turns `--warning`: "Deleted {k} of {n} files. {f} still on disk." (f = 1: "... 1 is still on disk.") The dialog showed exactly which. | Deleted {k} of {n} files. The book stays listed with the {f} that could not be deleted. |
| Refused | Stays. Hint turns `--warning` with the refusal line. Nothing recorded. | none |
| Outcome unknown | Stays. Hint turns `--warning` with the line. | none |

- **Gone from every list and count within one poll:** its chip, All, the shortcut, the Jobs line, All candidates, Held, the Files view, and the Read errors count if it had any. A fresh page load and an app restart agree. Count and list always agree (one predicate).
- **Focus after success** as after Approve: the next row's first working control, else the Status filter, `preventScroll`. After partial, refusal or outcome unknown: the row's Delete book button.
- The hints use the mechanism that carries the existing refusals (`askResults`) and, on the Stopped rows, the one that carries Retry's refusal. Strip text stays until the chip or filter changes, no timer.
- **Scan again** keeps its honest lines ("Checked 14:32. Not found.", "Files found. The book is checked again.") and is not touched by this action. Futaba's open M-2 (a false "Files found" on a missing part) is a separate defect: this action neither relies on it nor hides it.

## 7. Knock-on copy

Three strings now contradict the button.

| Where | Was | Now |
|---|---|---|
| Need to reacquire, row hint, second sentence (both variants) | Put an intact replacement in an unsorted source, then scan it. | Delete the book, then get a new copy. |
| Need to reacquire, details and cell tooltip | You can remove these damaged originals yourself. After a completed scan confirms they are gone, their active source entry is cleared. | Delete book removes these files and the book. If you remove the originals yourself, the book is cleared after a completed scan confirms they are gone. |
| Source audio needs replacement, row hint | The MP3 failed its full audio check. Keep this original, replace the source with a sound copy, then rescan this source. The affected file is listed in the details. | The MP3 failed its full audio check and can't be repaired by the app. Delete the book, then get a new copy. |

The first sentences of the two Need to reacquire hints stay. The "Some original files remain" and "Source unavailable" additions stay. Remove from list, Scan again and Convert what's there keep their tooltips.

## 8. Copy sheet additions (verbatim once built)

Strings of sections 3, 4 and 7 are verbatim there. Those with no other home:

| Where | String |
|---|---|
| Row hint, done | Deleted. The book is gone from the app. |
| Strip, success | Deleted 1 book and {n} files ({size}). / Deleted 1 book and 1 file ({size}). / Deleted 1 book. No files were left on disk. |
| Strip, partial | Deleted {k} of {n} files. The book stays listed with the {f} that could not be deleted. |
| Row hint, partial | Deleted {k} of {n} files. {f} still on disk. / Deleted {k} of {n} files. 1 is still on disk. |
| Accessible name | Delete book: {title clue} |
| Code tables | `ASK_LABELS.delete`, `ASK_TIPS.delete` (two variants), `ASK_PENDING.delete`, `ASK_DONE.deleted` (status null), `ASK_REFUSED.delete` |

## 9. What the UI needs from the API (names assumed; Ender confirms)

- **Offer:** `ask.delete` on Missing files rows, `attention.delete` on the two Stopped rows: `{kind:'files_missing'|'audio_damaged', present:n}`. No offer, no button. `present` picks the tooltip variant without a call.
- `POST /api/candidate/delete-preview` `{library,id,revision}` returns `{files:[{path,size}], bytes, refusal:null|{code, files?:[{path,other}], root?}}`.
- `POST /api/candidate/delete` `{library,id,revision,paths}` returns `{deleted, bytes, failed:[{path,cause}], forgotten}` with `cause` in `in_use|denied|unreachable|other`. Typed refusals are HTTP 409 with `code` in `changed|files_changed|shared|sorted|offline|busy|refused`.
- **Guarantee:** a refusal code is sent only when no file was touched; anything else reads as outcome unknown. `forgotten:true` only after the records transaction committed.

## 10. Changes Ender must make

1. `app.js`: add `delete` to the `ASK_*` tables. Build the button last in `.row-actions`, after the folder buttons and behind a flex break, for ask rows with `ask.delete` and for the two Stopped rows with `attention.delete` (outside `rowAction`). Ignore `event.repeat`.
2. `index.html` and `style.css`: `delete-dialog` (approve-dialog pattern, `autofocus` on Cancel, no form) with its five states; `button.danger`, `button.danger.solid`; tokens `--error-hover` and `--error-pressed`.
3. Backend: the two routes and the guards of section 5 (the same verified-handle checks as source cleanup; refuse any path under the output folder); **no recovery copy**; records last, in one transaction; idempotent (a path already gone counts as gone); typed results. This overrides the retain-history stance of the Reacquire contract for this action only. If a dependency (a published output, replacement lineage) makes full removal unsafe, refuse up front with the "finished audiobook" line, never half done.
4. A new copy at the same path is found as a new book (5.6), including the archived-marker hold.
5. The three knock-on strings of section 7.
6. Tests: one fixture per row kind and per negative of section 2; the press; every refusal; a partial failure (a file held open); records last (stop between 3 and 4); no recovery copy; reacquire as a new book; a front-end test that the button is last and has its tooltip.

## 11. Checks for Futaba (committed build, seeded fixture on a scratch library, nothing on Z:)

1. **Fixture:** Missing files (some present, a part set, all missing), Need to reacquire, Source audio needs replacement, plus the negatives: Can repair, Can retry, the MP3 "Retry checks it again" row, Stopped — see details, Original changed, Name taken, Order unclear, a duplicate "Needs you" row. Delete book is on exactly the first five. Control: absent on the unfixed build.
2. **Position and style:** the button is the last Tab stop of its row, on its own line, at least 16 px below the line above and never on the primary's line, at 1440, 1024, 700 and 200% zoom. No two rects intersect, no horizontal scroll, focus ring not clipped. Contrast measured in the build: text 9.12, solid face 10.42. In greyscale it still reads "Delete".
3. **Dialog:** Cancel has focus on open. The list equals the fixture's present files for that book and no other file, with the right count and size. Enter in the body or the list does nothing; Enter on Cancel cancels; Esc cancels; Confirm works only by Tab or click, then Enter or Space; a held Enter opens it once; a double press runs once. Control: a build with Confirm focused on open deletes on Enter.
4. **Delete:** the listed files are gone from the fixture disk. A sibling book's file and a cover in the same folder are untouched. Audiobooks Sorted is identical before and after (listing with sizes and times). No recovery copy appears under `data/source-recovery`.
5. **Records:** the row is gone; chip, All, shortcut and Jobs line agree; All candidates, Held and the Files view have nothing for it; the Read errors count drops if it had one. After an app restart all of that holds. Control: query the catalog for the book's id and paths: zero rows.
6. **Reacquire:** copy the same files back under the same names and scan. It is a new book with fresh research and none of the old approval, hold, review, draft or marker.
7. **Partial:** hold one file open. The dialog lists exactly that file with "In use by another program.", the others are gone, the book stays listed as Missing files, no record was deleted. Release the file and press again: the list holds only that file, and the delete completes.
8. **Refused, each verbatim, nothing deleted** (Sorted and sources listed before and after, records unchanged): a shared file; a finished audiobook in Sorted; a source folder not reachable; a changed revision; a file added after the dialog opened. Controls: the same press without the shared file deletes; without the added file it succeeds.
9. **Outcome unknown:** stop the backend during the confirm. The dialog reads the connection line and never "Nothing was deleted". After a restart the list shows the true state.
10. **Not in bulk, no accelerator:** no Delete in Select this page or the bulk bar; Ctrl+Enter on a Missing files row deletes nothing.
11. **Strings and tooltips:** every string above verbatim in the packaged window; every control has its tooltip; a search of the page for `WinError`, `Errno` and `PermissionError` finds nothing outside Technical details.
12. **Scan again** on a Missing files row still reads "Checked {time}. Not found." when nothing is found, before and after a partial delete.

## 12. Questions and offers

**Questions for Sergei (one word each)**
1. Cover and text files in a deleted book's folder: leave them, or delete them too when the folder held only this book? The default is leave, so nothing you didn't expect is removed. (leave / delete)
2. Verified duplicate copies ("Identical verified recording already arranged"): add a separate "Remove this copy" action that deletes the duplicate only after showing the copy in Audiobooks Sorted? (yes / no)

**Offers (not specced)**
1. **Remove this copy** for verified duplicates, as in question 2. It is the way out of Futaba's m-3 dead end.
2. Bulk delete for Missing files once the count is large. Today it is a handful, and each book wants its own look.
3. The same button on Files unclear rows that say "The tags say N tracks, but M files are here", once the app can tell a wrong tag from a missing file.
4. A "not repairable" verdict for multi-file audio failures (Stopped — see details), so those rows get the button too.

Design basis: Fitts (the destructive button is the farthest target and never beside a primary), Hick (one button, three row kinds, no menu), Jakob (native dialog, the file list a user expects from "Delete"), NN/g error prevention (the confirm lists exactly what goes, Cancel is the default, Enter never confirms, a refusal shows before the confirm), visibility of status (outcome stated, never intent) and plain-language recovery (every failure names the file and the cause); WCAG 2.2 AA 1.4.3, 1.4.11, 2.1.1, 2.4.7, 2.5.3, 2.5.8, 4.1.3. Doc-only: no code, git or app launch.

---

# Delete book update and Remove this copy — spec (2026-10-25, Judy)

Basis: rulings 24, 25 and 26 (`Team/Docs/BooksArranger_Rulings_2026-10-24.md`, Sergei, 2026-10-25), the "Delete book — spec" above, and Futaba's m-3 (interim QA on b946ee7). Read-only look at branch `ender/0220d` at 4d9e687 (worktree `C:/Antigravity Projects/Worktrees/Books Arranger/fx0220d`): `web/app.js` L2193-2332 (the Delete block: `showDeleteState`, `DELETE_*`, `deleteConfirm`), `web/index.html` L152-165, the delete rules in `web/style.css`, `book_delete.py` (`plan`, `remove`, `delete`, `forget`), `recording_classification.py`, `merge_service._recording_review` and `_output_valid`. Nothing launched, no rects measured: geometry is target geometry for Futaba. Contrast is calculated from the `style.css` tokens, all on `--surface`: `--muted` 8.92:1, `--warning` 11.18:1, `--error` 9.12:1. Names and paths in the mockups are examples. Spec only: no code, not committed.

**Supersedes**, in the Delete book spec above: section 4's Folder line "Other files in the folder stay." (now 2.2); section 5.7 "Never touched: covers, text and other files, the folder itself" (now ruling 24; still never touched: anything in Sorted, another book's file, a source folder); section 12 questions 1 and 2 (answered by rulings 24 and 25) and offer 1 (done: section 3). The "Duplicates: no" paragraph of section 2 stands for **Delete book**: a verified duplicate gets its own button, not that one.

## 1. In brief

1. **Delete book** now also removes the book's other files that belong only to it, the app's own working files for it, and each folder left empty (except one directly inside a source folder). The dialog lists all of it by path in labelled groups and says what stays.
2. When the working files are the last copy of the audio (the originals are already gone), the dialog says so in one line above the count. It is the only case where the app deletes a last copy, and only on this press.
3. **Remove this copy** is a second danger button in the same slot as Delete book. It shows only where the app holds proof that the files are an exact copy of an audiobook already in Audiobooks Sorted. Its dialog shows that audiobook (path, size, verified time) above the files that go.
4. One dialog serves both, with the same states and safety rules: Cancel has focus, Enter never confirms, a refusal shows before the confirm, "Nothing was deleted" only for a typed refusal before the first file.
5. Files go first, records last (unchanged). A folder that cannot be removed never keeps a book listed.

**Vocabulary.** "Copy" always means the files being removed. The thing in Sorted is always "the audiobook". The app's own temporary files keep the name the app already uses: "working files".

## 2. Delete book: what changes (rulings 24 and 26)

### 2.1 What the press removes now

| # | What | Rule | Counts as a file |
|---|---|---|---|
| 1 | The book's audio files | as before | yes |
| 2 | Other files in its folder (cover, text, anything not audio) | only when the app can show they belong to this book alone: the folder holds no other book. Otherwise they stay. | yes |
| 3 | The app's working files for it, on the app's own drive | always listed. Includes the last copy of the audio when the originals are gone (ruling 26). | yes |
| 4 | Folders left empty by this press | the book's folder, then each parent that is now empty, up to but never including a folder directly inside a source folder. Never a source folder. A folder that was already empty is not touched. | no |

Example: the book is in `Z:\Audiobooks\Сборники\Новая плоть (2016)\` and `Z:\Audiobooks` is the source folder. Its audio, `cover.jpg` and `info.txt` go, and `Новая плоть (2016)` is removed. `Сборники` is directly inside the source folder, so it stays.

Unchanged: records go last, only when every file of rows 1 to 3 is gone. A folder is housekeeping, so one that cannot be removed is reported in the strip and never keeps the book listed. Nothing in Audiobooks Sorted, no other book's file and no source folder is ever touched.

### 2.2 The dialog

```
+-------------------------------------------------------------------+
| Delete this book?                                                 |
| Новая плоть — Сборник                                             |
| 1 of 9 files is missing.                                          |
|                                                                   |
| These 10 files (1.4 GB) will be deleted from your disk. The app   |
| can't undo this.                                                  |
| +---------------------------------------------------------------+ |
| | Audio files (8)                                               | |
| | Z:\Audiobooks\Сборники\Новая плоть (2016)\01 - ... .m4b       | |
| | ...                                                           | |
| | Other files in this book's folder (2)                         | |
| | Z:\Audiobooks\Сборники\Новая плоть (2016)\cover.jpg           | |
| | Z:\Audiobooks\Сборники\Новая плоть (2016)\info.txt            | |
| | Folders left empty are removed (1)                            | |
| | Z:\Audiobooks\Сборники\Новая плоть (2016)                     | |
| |                                              (scrolls, 40vh)  | |
| +---------------------------------------------------------------+ |
| The app forgets this book. If you get it again, it's found as a   |
| new book. Nothing in Audiobooks Sorted is touched.                |
|                                                                   |
| [ Cancel ]                       [ Delete book and 10 files ]     |
+-------------------------------------------------------------------+
```

The last-copy case (ruling 26), changed lines only, with a stay line:

```
| Червь 19 — Джон МакКрэй                                           |
| The audio is damaged and cannot be repaired safely.               |
|                                                                   |
| The originals are already gone. The app's working files are the   |
| last copy of this book's audio.                  (--warning text) |
| These 6 files (1.2 GB) will be deleted from your disk. The app    |
| can't undo this.                                                  |
| +---------------------------------------------------------------+ |
| | The app's working files (6)                                   | |
| | C:\...\working\Червь 19\part01.m4a                            | |
| | ...                                                           | |
| +---------------------------------------------------------------+ |
| 2 other items stay where they are. They belong to other books, or |
| the app can't tell whose they are.                                |
```

Changed strings (everything else in the Delete dialog stands):

| Part | String |
|---|---|
| Group subhead, audio | Audio files ({n}) |
| Group subhead, other files | Other files in this book's folder ({n}) |
| Group subhead, working files | The app's working files ({n}) |
| Group subhead, folders | Folders left empty are removed ({n}) |
| When subheads show | when the list holds anything but audio files. With audio files only, the dialog is exactly as before (no subheads, no stay line). |
| Last-copy line, all originals gone | The originals are already gone. The app's working files are the last copy of this book's audio. |
| Last-copy line, some originals gone | Some originals are already gone. The app's working files hold the last copy of that audio. |
| Stay line (replaces "Other files in the folder stay.") | {k} other items stay where they are. They belong to other books, or the app can't tell whose they are. / 1 other item stays where it is. It belongs to another book, or the app can't tell whose it is. Hidden when k is 0. |
| List name (`aria-label`) | Files to delete (no folders listed) / Files and folders to delete |
| Files line, No files line, Forget line, Cancel, Confirm, tooltips | unchanged. {n} and {size} count every file listed (audio, other, working), never folders. |

**Placement and style.**
- Order in the list: audio, other files, working files, folders; each group sorted by path; a group with nothing in it is absent. The subhead is a `p.delete-group` inside the existing scroll box: 13px, weight 600, `--muted` (8.92:1), 8px above, 2px below, no icon. The first one has no space above.
- The last-copy line sits directly above the Files line, in `--warning` text (11.18:1). Its words carry the meaning, so colour is not the only carrier.
- The stay line sits directly below the list, where the old folder line was. "Items" is deliberate: a subfolder the app cannot place also stays.

### 2.3 After the press and when something fails

| Outcome | String |
|---|---|
| Strip, success, no folder listed | unchanged: Deleted 1 book and {n} files ({size}). / Deleted 1 book and 1 file ({size}). / Deleted 1 book. No files were left on disk. |
| Strip, success, folders removed | Deleted 1 book, {n} files ({size}) and 1 folder. / Deleted 1 book, {n} files ({size}) and {m} folders. / Deleted 1 book, 1 file ({size}) and 1 folder. |
| Strip, a listed folder stayed | the sentence above, then: 1 folder stayed. / {s} folders stayed. (After the plain success line when none was removed.) |
| Partial, dialog and strip | unchanged. {n} is every file listed. Any failed file, including a cover or a working file, keeps every record: the book stays listed. |
| Failed working files, the "path" shown | The app's working files (replaces "Working files of an earlier attempt (job N)"; the cause line under it is the usual one) |

The row's Delete book tooltip variants stand. `present` now counts every file the press would delete, so "No files are left to delete" stays true.

## 3. Remove this copy (ruling 25)

### 3.1 Which rows show it

**The server decides.** It sends a typed offer only when it holds all of: the row's recording review is "identical verified" (every file matches, in order, a source of one audiobook); that audiobook is arranged and passed its output check; and the audiobook's file exists in Sorted. No offer, no button (hidden, not disabled).

| Row | Shows | Why |
|---|---|---|
| Identical verified recording already arranged | **yes** | The app has the proof (ruling 2: a source goes only after its result is verified in Sorted). |
| Possible duplicate recording / Held — Possible duplicate recording | no | Nothing proves it is the same recording. It may be a different reading, the only copy of it. |
| Identical, but the arranged audiobook is unfinished or fails its check | no | There is nothing in Sorted to show. |
| Distinct recording verified | no | Not a duplicate; it is arranged under its own name. |
| Every other row | no | Delete book where its table says so. |

A row never carries both Remove this copy and Delete book (a book with a missing file has no complete proof). Also hidden once the row is done, and inert (`aria-disabled`) with "Another operation is in progress." or "Local server unavailable." while a press runs or the server is gone. **Never automatic, never bulk, no accelerator, not in the details panel, no context menu** (standing rule: no automatic duplicate-source deletion).

**The row's own sentence.** These rows say "This book needs your decision." today, which gives the button no referent. For these rows only (the chip stays "Needs you"; own chip is offer 2):

| Where | String |
|---|---|
| Row hint | This recording is already in {Audiobooks Sorted}. The audio files here are exact copies of the files it was arranged from. |
| Row hint, done | Removed. The copy is gone from the app. |

### 3.2 The button

```
[ ] Inferno  ·  Dan Brown  ·  12 audio files
    Needs you                                         [ Approve ] [ View metadata ]
    This recording is already in Audiobooks Sorted.   [ Source folders ]
    The audio files here are exact copies of the
    files it was arranged from.
                                                      [ Remove this copy ]
```

| Part | String or rule |
|---|---|
| Face | Remove this copy |
| Tooltip | Delete this copy's files from disk. The app shows the audiobook in {Audiobooks Sorted} first, and you confirm. |
| Pending face / tooltip | Checking... / Checking the audiobook in {Audiobooks Sorted}... |
| Accessible name | Remove this copy: {title clue} (visible face first, WCAG 2.5.3) |
| Style | the Delete book style, `quiet row-retry danger`: outlined `--error`, 9.12:1 on `--surface`; solid only in its dialog. It differs from its neighbours by word, position and hue. |
| Position | The Delete book slot: last in `.row-actions`, behind the zero-height flex break, on a line of its own, `margin-top:8px` (at least 16 px clear above), last Tab stop. It is never on the primary's line, so **Approve** (inert on these rows today) and Source folders are never its neighbours. Ignore `event.repeat`. At least 96 x 32; the face wraps, never truncates. |

### 3.3 The confirmation

The Delete book dialog in a second mode: same element, same 560 px, same focus and Esc rules (1 to 5 of "Enter must not confirm" apply unchanged; focus returns to Remove this copy, else the Status filter). It adds one block between the reason line and the files line. Stacked, not in columns: the paths are long and columns would not fit at 200% zoom.

```
+-------------------------------------------------------------------+
| Remove this copy?                                                 |
| Inferno — Dan Brown                                               |
| This recording is already in Audiobooks Sorted. The audio files   |
| here are exact copies of the files it was arranged from.          |
|                                                                   |
| Stays in Audiobooks Sorted                                        |
| Z:\Audiobooks Sorted\Dan Brown\Inferno.m4b                        |
| 612 MB. Verified 14:32: the file is there and unchanged since     |
| the app arranged it.                                              |
|                                                                   |
| These 12 files (640 MB) will be deleted from your disk. The app   |
| can't undo this.                                                  |
| +---------------------------------------------------------------+ |
| | Z:\Unsorted\Inferno\01 - ... .mp3                             | |
| | ...                                          (scrolls, 40vh)  | |
| +---------------------------------------------------------------+ |
| The app forgets this copy. If the same files turn up again,       |
| they're found as a new book. Nothing in Audiobooks Sorted is      |
| touched.                                                          |
|                                                                   |
| [ Cancel ]                    [ Remove this copy and 12 files ]   |
+-------------------------------------------------------------------+
```

| Part | String |
|---|---|
| Title, confirm and deleting | Remove this copy? |
| Book line | {title} — {author} (as Delete book) |
| Reason line | the row hint, verbatim |
| Sorted block | a `role="group"` named by its heading. Heading (`.delete-group` style): Stays in {Audiobooks Sorted}. Then the file's full absolute path (`.path`). Then: {size}. Verified {time}: the file is there and unchanged since the app arranged it. ({time} is the clock time of this check, `HH:MM`, like "Checked 14:32".) |
| Files line, list, groups, stay line | as in 2.2. The last-copy line never shows here: a copy that is also in Sorted is not the last copy. |
| Forget line | The app forgets this copy. If the same files turn up again, they're found as a new book. Nothing in {Audiobooks Sorted} is touched. |
| Cancel | Cancel / Close without deleting anything. |
| Confirm | Remove this copy and {n} files / Remove this copy and 1 file |
| Confirm tooltip | Delete this copy's {n} files. The audiobook in {Audiobooks Sorted} stays. The app can't undo this. / Delete this copy's file. The audiobook in {Audiobooks Sorted} stays. The app can't undo this. |
| Deleting | Confirm face "Deleting..."; status "Deleting {n} files..." / "Deleting 1 file..." (as Delete book) |

"Verified" is shown only for a check made in this same preview, never from a stored flag. If either check fails, the dialog opens in its refusal state instead, so the Sorted block never appears next to a failed proof.

### 3.4 Success, refusal and partial failure

Same table of states as Delete book. Titles that differ:

| State | Title |
|---|---|
| Confirm, Deleting | Remove this copy? |
| Refused | Can't remove this copy |
| Partial | Not everything was deleted (unchanged) |
| Outcome unknown | Removal may not have finished |

| Outcome | String |
|---|---|
| Strip, success | Removed 1 copy and {n} files ({size}). / Removed 1 copy and 1 file ({size}). With folders: Removed 1 copy, {n} files ({size}) and {m} folders. Then "{s} folders stayed." as in 2.3. |
| Partial, dialog body | Deleted {k} of {n} files. {f} could not be deleted: then the path and cause per file (causes as Delete book). Status line: The copy stays listed. The row offers to delete what is left. |
| Partial, strip | Deleted {k} of {n} files. The copy stays listed with the {f} that could not be deleted. |
| Partial, row hint | Deleted {k} of {n} files. {f} still on disk. / Deleted {k} of {n} files. 1 is still on disk. (as Delete book) |
| Connection lost | Connection interrupted, so the removal may have gone through. Check the list before trying again. |
| Untyped server error | Removal did not finish. Check the list before trying again. |

The partial status line names no button because the next poll reads the half-removed copy as Missing files, whose button is Delete book. Either button lists only what is left and never touches Sorted.

Refusals (each only for a typed refusal before the first file; every line ends "Nothing was deleted."):

| Refusal | Line |
|---|---|
| The audiobook is gone from its place | The audiobook is not where the app put it in {Audiobooks Sorted}. Nothing was deleted. |
| The audiobook fails its check | The audiobook in {Audiobooks Sorted} has changed since the app arranged it. Nothing was deleted. |
| A file of the copy no longer matches | These files no longer match the ones the audiobook was arranged from. Nothing was deleted. |
| Drive not reachable (source or Sorted) | Can't reach {root}. Nothing was deleted. (as Delete book) |
| Shared file, being processed, book changed | as Delete book, verbatim |
| Folder differs from the list | The folder doesn't match the list, so nothing was deleted. Press Remove this copy to see the current list. |
| Any other typed refusal | Remove was not accepted. Nothing was deleted. |

## 4. What the UI needs from the API (names assumed; Ender confirms)

- **Preview** (both actions): each file gains `kind: 'audio'|'other'|'working'`; new `folders:[path]` (the folders that would be removed), `stay:{items:k}`, `last_copy: null|'all'|'some'`. The offer's `present` counts every file the press would delete.
- **Confirm:** sends every file path shown plus `folders`. The server rebuilds the plan and deletes only if both lists are equal, else `files_changed`. Result adds `folders:{removed:m, stayed:s}`; `deleted` and `bytes` count every file.
- **Remove this copy:** offer `ask.copy {kind:'verified_duplicate'}` on the row's hold payload; a preview and a remove route, or `mode:'copy'` on the delete routes. The preview returns `sorted:{path, size, verified_at}` or a typed refusal: `sorted_missing`, `sorted_changed`, `not_identical`.
- **Guarantee:** the preview re-checks both sides now (the Sorted file exists, has its recorded size and checksum; each file of the copy matches a source of that audiobook, in order). The press checks the Sorted file again before the first file goes. A refusal code is sent only when nothing was touched.

## 5. Changes Ender must make

1. `index.html`: `delete-dialog-last` (hidden `p`) above `delete-dialog-files`; a hidden Sorted group between the reason and files lines. `style.css`: `.delete-group` and `.delete-last` only; no new tokens.
2. `app.js`: `showDeleteState` builds the groups, the last-copy line, the stay line and the folders group; one mode table (delete, copy) holds the title, forget, confirm, tooltip and refusal strings; `buildDeleteButton` takes the mode; strip variants with folders; `ASK_LABELS.copy`, `ASK_TIPS.copy`, `ASK_PENDING.copy`, `ASK_DONE.removed`, `ASK_REFUSED.copy`.
3. Backend (rows 2 to 4 of 2.1): list other files only when the folder holds no other book; the cascade rule for folders; enumerate working files by path and size, and delete them as part of this press even when their originals are gone, for this action only. Working files used to be cleared silently before the originals; they are now listed and counted.
4. Remove this copy: the proof checks of section 4 and the refusals of 3.4. Refuse when a listed file is, or links to, the Sorted file. The same boundary checks as Delete book (nothing under the Sorted folder), no recovery copy, records last in one transaction.
5. The failed working-files label of 2.3.
6. Tests: one fixture per row of 2.1 (including a shared folder and a folder directly inside a source folder); last copy with all and some originals gone; every string above; a cover held open; a folder that stays; each refusal of 3.4; Cancel focus and Enter in copy mode; the button is last and has its tooltip.

## 6. Checks for Futaba (committed build, seeded fixture on a scratch library, nothing on Z:)

1. **Delete book, 24:** a book alone in its folder with a cover and a text file, one folder shared with another book, one directly inside the source folder. With audio only the dialog is as before. The list equals the fixture's files and nothing else; the count and size include the extras and exclude folders. After the press the extras and the folder are gone, the parent directly inside the source folder stays, and Sorted is identical before and after (listing with sizes and times). In the shared folder the cover stays and the stay line gives the right k.
2. **Last copy, 26:** a book with working files and no originals: the last-copy line (all), the files listed under "The app's working files", all gone after the press, the records gone, a reacquired copy found as a new book. Repeat with some originals gone (the "some" line) and with originals present (no last-copy line).
3. **Partial and folder:** hold a cover open: the dialog lists exactly it with "In use by another program.", the audio is gone, the book stays. Put a new file in a listed folder after the dialog opened: refused as "files_changed". Make a listed folder unremovable after the files are gone: the strip says "1 folder stayed." and the book is forgotten.
4. **Remove this copy, rows:** the button is on the verified-identical row only. Absent on Possible duplicate, identical with an unfinished or failed audiobook, Distinct recording, Missing files, Need to reacquire. Control: absent on the unfixed build.
5. **Position and style:** last Tab stop, own line, at least 16 px below the line above, never beside Approve, at 1440, 1024, 700 and 200% zoom. No two rects intersect, no horizontal scroll, focus ring not clipped. In greyscale it still reads "Remove".
6. **Dialog:** Cancel has focus on open; Enter in the body or the list does nothing; Enter on Cancel cancels; Esc cancels; a held Enter opens it once. The Sorted block shows the fixture's path, size and a time within a minute of the press. The list equals the copy's files. Sorted is identical before and after; no recovery copy appears.
7. **Refusals, verbatim, nothing deleted:** delete the Sorted file after the offer shows; change one byte of it; change one byte of a copy file; make the Sorted drive unreachable. Controls: restore each and the press succeeds. In none of them does the Sorted block show "Verified".
8. **Outcome and reacquire:** stop the backend during the confirm: the connection line, never "Nothing was deleted". Copy the same files back: found as a new book and flagged as a duplicate again.
9. **Not in bulk or automatic:** no Remove this copy in Select this page, the bulk bar or any automatic pass; Ctrl+Enter on the row does nothing.
10. **Strings:** every string above verbatim in the packaged window; every control has its tooltip; a search of the page for `WinError`, `Errno` and `PermissionError` finds nothing outside Technical details.

## 7. Questions and offers

**Question for Sergei (one word)**
1. Should Remove this copy also delete the copy's cover and text files and empty folders, by the same rule as ruling 24? The spec assumes yes, so the copy disappears as completely as a deleted book. (yes / audio only)

**Offers (not specced)**
1. Approve is inert on verified-duplicate rows and its tooltip says "That name is taken." (Futaba m-3). Hide it there, or give it its own tooltip.
2. A chip of its own for verified duplicates ("Already arranged") instead of "Needs you". It changes the counts, so it needs your word.
3. Bulk "Remove copies" once the count is large. Each copy would still be proven and listed.
4. A specific refusal for working files the app cannot prove are its own. Today that case reads the generic "Delete was not accepted. Nothing was deleted."
5. Treat the NAS's own index or thumbnail folders as empty when deciding whether a folder is left empty, if the share makes them. Until then such a folder stays and the stay line says so.

Design basis: Fitts (the destructive button stays the farthest target, alone on its line), Hick (one extra button on one row kind, no menu), Jakob (a native dialog that lists what goes and what stays), NN/g error prevention (proof shown before the confirm, Cancel the default, Enter never confirms, a refusal before the confirm) and visibility of status (the outcome is stated, never the intent; "Verified" only for a check made now); WCAG 2.2 AA 1.4.3, 1.4.11, 2.1.1, 2.4.7, 2.5.3, 2.5.8, 4.1.3. Doc-only: no code, git or app launch.
