# Books Arranger 0.23.1: review rows in "Output needs attention" (Judy, 2026-10-29)

Basis: the five screenshots in `Docs/BugEvidence/2026-10-28-post-0230/` (named here by the first 8 characters of each file: S1 `330ddca3` the 13-file Pratchett row, S2 `394f8e5a` Abnett, S3 `5945e15d` the 105-file Pratchett row, S4 `b014e7ee` the two Gene Wolfe rows, S5 `cc884e85` the Лайонс list); `Docs/BooksArranger_0.22.1_Backlog.md` section "Open reports after 0.23.0" (POST-023-01 to 05); rulings 10, 36, 40, 43, 51, 62, 68 (`Team/Docs/BooksArranger_Rulings_2026-10-24.md`, plus 14, 35, 56, 58, 59 where noted); my specs `BooksArranger_AttentionTodo_UX_2026-10-24.md` (called "to-do spec") and `BooksArranger_0.22.3_UX_2026-10-27.md` (called "0.22.3 spec"). Read-only look at `web/app.js`, `web/style.css`, `web/index.html`, `merge_service.py` (`ask_payload`, `_hold_payload`, the inspect answer, `open_folder`) and `todo_causes.py` on main at 4ae072f; line numbers below are for that commit. Nothing launched, no rects measured: geometry is target geometry for Futaba. Spec only: no code, not committed. Book titles, authors and numbers in mockups are examples from the screenshots or invented; the engine supplies the real values.

**Scope line.** This spec says how a row *shows* things. What the engine groups, which title it proposes and which chip a book lands in is Ender's diagnosis and stays his. Every line below hides when the engine sends no data for it, so the spec works with today's engine and gets better as his fix lands. Nothing needs a bigger renderer redesign: no item was stopped.

**Extension (same day).** Part B (sections 13 to 19) covers Sergei's rulings 69 and 70: choosing the destination folder on any row, moving a finished book, and "Open source folder" on converted rows. Its evidence is S6, `Docs/BugEvidence/2026-10-29-destination-override/sparse-info-rows.webp`. Sections 8 to 12 carry its engine needs, checklist, checks, questions and offers.

## 1. Red-team of the five screenshots

Class: **Blocks** = Sergei cannot do the review task from the row; **Slows** = he can, with extra steps; **Polish** = minor.

| # | Where | What gets in the way | Class |
|---|---|---|---|
| R1 | S1-S5, every row | **"Source folders" opens no folder.** By the code (`viewMetadata(row,true)`) it selects the row, scrolls the page to the details heading, reads metadata, then expands a list inside the details panel, far below the row. The Open folder buttons are in that list. Three steps and a scroll for one folder. | Blocks |
| R2 | S1-S5, every row | **The one-click "Open folder" never shows on live rows.** `web/app.js` L589 shows it only when `row.source_directory_count === 1`. That field is sent only in the details answer (`merge_service.py` L4350), never in the list row. In the live app it is `undefined`, so every row gets "Source folders", including the one-file rows of a single folder in S5. Test fixtures set the field to 1, so tests never saw it. Ender confirms. | Blocks |
| R3 | S1-S5 | **No row says where its files are** (only Missing files and Files unclear rows print an "In" line). For S1 and S3 he cannot tell whether the 13 and the 105 sit in one folder. In S5 four rows print the same folder path, and nothing says "four rows, one folder", which is exactly what ruling 68 forbids. | Blocks |
| R4 | S1-S5 | **Six stacked buttons set the row height, not the content.** S5's one-file rows leave about 180 px empty under "Goes to"; four rows fill a screen. A seventh stacked button would make it worse, so the fix must not add one. | Slows |
| R5 | S3 | **A narrator credit is the title.** The title clue and the destination title are both `исп. Капитан Абр и Nelly` ("performed by"). The real title is in the other clue column (`Терри Пратчетт. Шляпа полная небес`). Nothing marks the credit as a credit. | Blocks |
| R6 | S1 | **Both clue columns are garbled** (`èñï. Êàïèòàí…`, `Òåððè Ïðàò÷åòò…`) and the destination is readable, with the author's initial in front of the title (`Т. Пратчетт. Шляпа полная небес`). Nothing says the clues are garbled, or that the readable name is the app's own reading. | Blocks |
| R7 | S1-S4 | **The title Approve will use appears only inside the mono "Goes to" path**, which wraps mid-title (`…\Т.` / `Пратчетт. …`). Column 2 shows the raw clue under "Title clue:", a prefix that repeats the column heading. | Blocks |
| R8 | S1-S4 | **"Author / reader clues" mixes roles in one cell:** a reader alone (S4 `Антон Ческидов`), author plus title (S2, S3), garbled (S1). The author the app will file under shows only in the path (S4 files under Cyrillic `Джин Вулф`; rulings 58 and 59 say English). | Blocks |
| R9 | S2, S4 | **Cycle and position are invisible.** S4's second clue says `(Книга Нового Солнца #3)` and the first row's files start `04-`; "Goes to" has no series. Abnett shows no series or universe, not even "not known". He cannot tell whether the app saw the evidence. By the code the row's Place line (`placeText`) prints only a Universe or a Collection, never a plain "Series · No.", and its values come from the saved review, so a book not yet approved has none. Ender confirms. | Slows |
| R10 | S2 | The title clue is a folder name with an uploader tag: `… [Casper Valter]`. Shown as if it were a title. | Polish |
| R11 | S1, S3 | **"No file has a track number. The order comes from the file names."** sits above a list whose names are visibly numbered (`004-01.MP3`, `005-01.MP3`). "Track number" means the tag; he reads the numbers he can see. The sentence says nothing about the jumps in the list (`006`, `008`, `017`). | Blocks |
| R12 | S1, S3 | **The first five numbers of the two Pratchett rows interleave:** the 105-file row shows 001, 002, 003, 007, 009; the 13-file row shows 004, 005, 006, 008, 017. Each looks gapped because it holds the other's numbers. This matches the 118 = 105 + 13 note in POST-023-04. The screen shows two unrelated rows. | Blocks |
| R13 | S4 | "Track numbers skip or don't start at 1." over lists starting `04-39` and `05-01`. Skip or start? Which numbers? Is `04-` a book or disc prefix? | Slows |
| R14 | S2 | Three files numbered 05, 06, 07 (`Часть Пятая`). He asks why the group starts at 05; the row answers "No file has a track number." | Blocks |
| R15 | S5 | **"The other tracks aren't here."** is printed on three rows whose siblings are in the same folder on the same screen: a sentence the screen disproves. "Approve these files" is the first button on a 1-of-38 fragment. | Blocks |
| R16 | S1-S3 | The status is "Order unclear" and the button "Approve this order", but the real question is completeness. Approving "this order" approves the file set as the whole book (POST-023-04: never treat incomplete membership as an ordering-only issue). | Blocks |
| R17 | S6 | **Sparse rows give no identity.** Two rows read `Title clue: Mp3`, author `Unknown`. The only usable text is the Title field (`Rak_Ed_Farrer_Met_Den_Osvobogdeniy`, a folder name transliterated into Latin with underscores). Nothing says "Mp3" is a generic folder name. | Blocks |
| R18 | S6 | **The computed folder is the only destination.** `Audiobooks Sorted\Без автора\Kristofer_Dann_Krovaviy_Shpil.m4b`. To file a sparse book anywhere sensible he must invent an author. No control says "put it here" (ruling 69). | Blocks |
| R19 | S6 | "Source folders" again, on a plain four-button row (Approve, Edit names, View metadata, Source folders): the same defect as R1 and R2 on a row with no hold. A sparse row is also about 480 px tall (three input groups), so two fill the screen. | Blocks (R2), Polish |

Noticed outside the rows, not specced: the three status lines above the table in S5 use two text sizes.

## 2. Decisions in brief

1. **Open source folder (section 3).** One button with that face replaces both "Source folders" and "Open folder" on every candidate row, in the same slot. One folder: it opens it. Several folders: it opens an in-flow list where each folder has its own Open folder button.
2. **Every row names where its files are (section 3.4).** One "In {folder}" line, so "one source folder = one book" can be checked at a glance.
3. **Book identity (section 4).** The first two columns show, in labelled lines, the title Approve will use, series and number, the author, the reader. The raw clue comes second, tagged with its role (narrator credit, garbled, author and title together). Headings become "Book" and "Author / reader".
4. **Gaps and missing (section 5).** A "Numbers" line states the facts (which numbers, from the tags or the file names). A "membership" line says what is known about which files belong. The word "missing" appears only when membership is settled.
5. **One folder = one book (section 6).** A novel plus bonus stories is one row with an "Includes" line. A truly ambiguous multi-book folder is raised as a Files unclear question, "Approve as one book" first.
6. **Nothing new to learn.** No new chip, color, font, badge or overlay. Everything is a text line or an existing button.
7. **Choose folder… lives with the destination, not in the button stack (Part B, sections 14 and 15).** The Actions column stays at six buttons. The control sits on the "Goes to" line of every row that has a destination, with "Use computed folder" beside it once a folder is chosen. The line says whose folder it is and what the app would have used.
8. **Finished books already have a list: Audiobook Ready (section 16).** It lacks only a place line. The same block there reads "Now in" and moves the file, never reconverts. Moves have their own states and failure copy (section 18).
9. **"Open book folder" (section 17).** On a finished row whose originals are gone, the button's face changes and it opens the folder holding the converted file (ruling 70). Choosing a folder does not approve a book by itself (section 19; question 3).

## 3. Open source folder (requirement 1)

### 3.1 Decision: merge, not keep, not add

| Option | Verdict |
|---|---|
| Keep "Source folders" and add "Open source folder" | **No.** Two near-identical labels side by side invite the wrong press, and the old one does not do what its name says (R1). It would also be a seventh stacked button (R4). |
| Replace "Source folders" only, keep "Open folder" | No. "Open folder" is the right behavior but the live row never reaches it (R2), and it does not cover several folders. |
| **Merge both into one "Open source folder"** | **Yes.** Sergei's own words ("always add an Open source folder button on every row"). One slot, same place as today's last "look" button, so no relearning. The button count stays at six. Nothing is lost: View metadata still opens the details panel, whose own "Source folders" list (an `Open folder` button per folder) is unchanged. |

### 3.2 The button

- **Face:** "Open source folder". Always this text, on every candidate row in every chip, including Order unclear, Part of a bigger book, Same author?, Name taken, Missing files and Stopped rows. Never hidden. The one exception is a finished book whose originals are gone: the face then reads "Open book folder" (section 17, ruling 70).
- **Slot:** the last of the three "look" buttons: `… primary, second action, Scan again | Edit names, View metadata, Open source folder`. "Delete book" / "Remove this copy" keep their own line below (the `row-break` slot, ruling 23/25). Size at least 96 x 32; the label wraps, never truncates (existing `.row-actions button` rule).
- **One folder:** the press opens it in File Explorer (the existing `/api/open-folder` call, sending the folder id). The page does not scroll, no panel opens, no row selection change, focus stays on the button. While it works the existing `folder-message` span beside it reads "Opening folder…"; on failure it keeps the existing sentence ("Folder unavailable. Connect the library drive and try again.") in `--warning`. The press does not select the row (today's `select(row, …)` before open is dropped for this button: it is a look-up, not a review step).
- **Several folders:** the press toggles the **folder list** (3.3) open or closed. The button gets `aria-expanded` and `aria-controls`. Focus moves to the first Open folder button in the list when it opens; Esc inside the list closes it and returns focus to the button.
- **Folder gone or drive offline:** the button stays enabled. The press shows the failure sentence beside it. Paths are in the "In" line (3.4), so he can restore from there. It is `aria-disabled` only when the row has no source folder at all (no catalogued file and no known missing-file folder).
- **Rows are never rebuilt while a control inside has focus** (existing rule). The list's open state is kept per book across polls, paging and chip changes (same pattern as `namesOpen`).
- **Keyboard:** Tab order in the Actions cell is unchanged (… Edit names, View metadata, Open source folder, then the list items when open, then Delete book). Enter and Space on the button act on it and do not select the row (click and keydown stop at the button, as for every row button).

### 3.3 The folder list (several folders)

Appears in the Review status cell, in flow, directly under the "In {n} folders" line, so it never covers anything and has the room for long paths.

```
In 3 folders
+------------------------------------------------------------------+
| Z:\Audiobooks\Unsorted\Книга\CD 1\    12 files     [ Open folder ] |
| Z:\Audiobooks\Unsorted\Книга\CD 2\    11 files     [ Open folder ] |
| Z:\Audiobooks\Unsorted\Книга\CD 3\     9 files     [ Open folder ] |
+------------------------------------------------------------------+
```

- Each item is the panel's existing `.source-directory` markup: a `p.path` (wraps, `overflow-wrap:anywhere`), an optional muted "{n} files", the button, and its own `folder-message` status span. One shared builder feeds both this list and the details panel's list (checklist 3).
- Item buttons: face "Open folder", at least 96 x 32, 8 px gap. At a cell narrower than about 360 px the button wraps under its path.
- The box scrolls inside itself above six items (max height about 232 px, `tabindex="0"`, `role="group"`, name "Source folders"). All folders stay reachable, whatever the count. Nothing is capped to "listed in the details panel".
- Accessible name of an item button: "Open folder 2 of 3: {path}" (visible label first).

### 3.4 The source line (every row)

One line in the Review status cell: `In  {path}` (label muted, path `.path`, `--text`, full path in `title`). With several folders: `In 3 folders` (the list opens from the button). It sits directly above "Goes to", so the row reads source, then destination.

It is **omitted** when the row already prints an "In {folder}" line above its own file list (Missing files, Files unclear, Part of a bigger book lists), so no folder is printed twice. For several folders the row's own list wins in the same way. On a finished book whose originals are gone it is replaced by the "Now in" line (section 17).

Why it matters: R3. With this line, S5's four rows would print the same folder four times, which is the visible symptom of a ruling-68 violation. Futaba's check 12 fails the build if two review rows list the same source folder (except the raised multi-book question, 6.3).

### 3.5 Tooltips (born with the control)

| Control | Tooltip |
|---|---|
| Open source folder (one folder) | Open this book's source folder in File Explorer. (existing sentence) |
| Open source folder (several, closed) | This book's files are in {n} folders. Show them and open any one. |
| Open source folder (several, open) | Hide the list of source folders. |
| Open source folder (no folder) | This book has no source files to open a folder for. |
| Open folder (list item) | Open this folder in File Explorer. |

The details panel's own per-folder button today says "Open this source file's folder in File Explorer." (a Files-view sentence). Use the list item sentence there too.

### 3.6 Row states to check for overlap

Default; folder message showing; list open (3 and 12 folders, long paths); queued (Cancel beside the primary); Delete book or Remove this copy shown; Edit names editor open; a visible `block-why` line; the 700 px band (columns 3 and 4 folded) and the 599 px block layout; 200% zoom. All new elements are in-flow blocks: nothing is absolutely positioned, there is no menu or popover.

## 4. Book identity (requirement 2)

### 4.1 What changes

The two clue columns show raw evidence under the labels "Title clue" and "Author / reader clues". Sergei needs the title the app will use, clearly, then the evidence. So for every row that has a question (`row.ask`), columns 2 and 3 become labelled lines. The headings become **"Book"** and **"Author / reader"**; the old content (a raw clue) stays valid under them, so rows without a question keep today's cells and need no change. Text styles are the existing ones: body text `--text`, semibold (600, the weight the details panel's status line already uses) for the title only, `.field-help` (13 px, `--muted`) for support lines, `--warning` for one "Check this" line. Contrast uses pairs already measured for the list: `--muted` on `--row-selected` 4.97, `--warning` on `--surface` 11.18 and on `--row-selected` 6.23; no accent-colored text on a row (4.47 fails). Every flag is words, so nothing depends on hue.

### 4.2 Column "Book" (column 2, never hidden, so it carries every flag in the narrow bands)

Top to bottom; each line appears only when it has content:

| # | Line | Source and rule |
|---|---|---|
| 1 | **{title}**, semibold, wraps, never truncated | The title Approve will use: `ask.fields.title.proposal`, following the draft the same way "Goes to" does (500 ms after typing, on blur, on Enter; the last good value stays meanwhile). Approved rows keep today's "Canonical title" text. If there is no proposal, the raw clue, as today. |
| 2 | `Check this title: {why}.` (`--warning`) | Only when the engine flags the shown title: "it looks like a narrator credit" / "it looks garbled" / "it starts with the author's name". Words, not color alone. |
| 3 | Series line | Established or proposed by the engine: `Series: {name} · No. {n}`, with `Universe: {name} · ` in front when set and `Collection · ` in front for a collection (the existing Place wording, extended so a plain series shows too). Evidence only: `The title mentions a series: {text}. Not used in the file name.` Neither: no line. |
| 4 | `Title clue: {raw clue}` + ` · {role}` | Only when the raw clue differs from line 1 (after trimming spaces). The role suffix is the table below. |
| 5 | `Includes {k} stories: …` | Section 6. |

**Roles** (the engine sends them; the page never guesses): narrator credit, garbled, author and title together, uploader tag, generic name (a clue such as "Mp3" or "CD 1" that names no book, S6). The suffix is plain muted text after " · ". Garbled text is shown as it is: the readable title is line 1, the raw damage is line 4, labelled.

**If a flagged title needs correcting**, the row already has the means: when the engine flags line 1, the existing Title field appears (the same rule that today shows it for a guessed title, `askFieldPlanOf`), prefilled, with the basis line under it. Approve stays available and uses what is shown (ruling 6b); the flag and the field make it a deliberate act, not an accident.

### 4.3 Column "Author / reader" (column 3)

Labelled lines (muted label, then value; the label style is the one "Goes to" uses):

```
Author   Pratchett Terry
Reader   Капитан Абр и Nelly
Clue     Терри Пратчетт. Шляпа полная небес · author and title together
```

- **Author:** the proposal Approve will use (`ask.fields.author.proposal`), "Unknown" if none (existing word). If the engine flags it: `Check this author: it looks garbled.` Other author doubts keep their existing rows (Author unclear, English spelling, ruling 14 and 59 machinery); this spec adds nothing there.
- **Reader:** only when the engine marks a credit as a narrator (it already detects "исп.", "читает", reader counts). Never shown as the author.
- **Clue:** the raw artist text, only when it differs from the author and reader lines, with its role suffix.
- Below 800 px this column folds into column 2's second line (existing `titleFacts`): `{Author} · Reader: {name} · {n} audio files`. The title, the flags and the clue lines stay in column 2.

### 4.4 Worked examples (today's engine data, then after Ender's fix)

**S3, the narrator row, with the engine as it is today** (proposal = the clue):

```
BOOK                                            AUTHOR / READER                         FILES
исп. Капитан Абр и Nelly                        Author  Pratchett Terry                   105
Check this title: it looks like a narrator      Clue    Терри Пратчетт. Шляпа полная
credit.                                                 небес · author and title together
```

The real title is visible right next to the flag, and the Title field is in the status cell, prefilled, ready to correct. **After the fix** the same row reads `Шляпа полная небес` with no flag and a "Title clue: исп. Капитан Абр и Nelly · narrator credit" line below it; `Reader  Капитан Абр и Nelly` appears in column 3.

**S1, the garbled row:**

```
BOOK                                            AUTHOR / READER                         FILES
Т. Пратчетт. Шляпа полная небес                 Author  Pratchett Terry                    13
Check this title: it starts with the author's   Clue    Òåððè Ïðàò÷åòò Øëÿïà ïîëíàÿ íåáåñ;
name.                                                   … · garbled
Title clue: èñï. Êàïèòàí Àáð è Nelly · garbled
```

**S4, the second Wolfe row** (series evidence in the title, author flagged by the engine):

```
BOOK                                            AUTHOR / READER                         FILES
Солнце и Замок                                  Author  Джин Вулф                          70
The title mentions a series: Книга Нового       Reader  Антон Ческидов
Солнца #3. Not used in the file name.
Title clue: Солнце и Замок (Книга Нового Солнца #3)
```

The Cyrillic-author problem (rulings 58 and 59) is the engine's to raise; if it does, the existing Author unclear question and its English-spelling copy take over. This spec only makes sure the author the app will use, and the reader, are readable without opening "Goes to".

## 5. Missing files, gaps and order (requirement 3, ruling 10)

### 5.1 The rule

A row never says only "Order unclear". Under the status line it says **what the numbers do** (facts) and **what is known about which files belong** (state). Two lines are new: the **Numbers line** and the **membership line**. The sentence under the status keeps explaining the cause.

Order inside the Review status cell, top to bottom: status, sentence, Also line, `ask-why`, fields, **Numbers line**, **membership line**, the file list, source line (3.4), Edit names block, Goes to.

### 5.2 Numbers line (facts only, from the file names or the tags)

Shown when the engine sends the numbers (first, last, skipped, and whether they come from the tags or the file names). The names are printed as they appear (`04-39`, `007`), never parsed for display.

| Case | Line |
|---|---|
| Skips | `File names run from {first} to {last}. Skipped: {list}.` or `Tags run from {first} to {last}. Skipped: {list}.` |
| Starts late, no skips | `File names run from {first} to {last}.` ("not from 1" is implied; the sentence above already says "don't start at 1" when that is the cause) |
| Contiguous from 1 | no line |

`{list}` is up to 6 entries joined with ", " (ranges as "009-016"), then " + {n} more". The line says only what the present numbering does. It never says "missing" or "not here".

### 5.3 Membership: still checking vs. settled

The engine sends `membership` (name assumed): `checking`, `established` or nothing.

| State | Membership line | Sentence changes | Buttons |
|---|---|---|---|
| **Checking** | `Still checking which other files belong to this book.` | The "other tracks aren't here" half of "This file is tagged as track 36 of 38. The other tracks aren't here." is dropped: that claim is not established. | No button is switched off. Approve's tooltip says what it does: "The app is still checking which other files belong to this book. This approves only the files shown." (Rulings 6b and 35: an approval is final and nothing is refused; question 1.) |
| **Established** | `The source folder holds only these {n} files.` (several: `The source folders hold only these {n} files.`) | Sentences stay as today. Now "other tracks aren't here" is true and may stay. | Normal. |
| **Nothing sent** | no line | Neutral wording only: no sentence claims a file is missing or absent. | Normal. |

"Missing" appears in a row only in the *established* state or for files the scanner saw disappear (the existing Missing files chip). This is the "measure the thing" check: a row in the checking state contains no "missing" or "aren't here" text.

My recommendation for the chip (Ender and Sergei decide; question 2): when membership is established and numbers skip, the book is a **missing-files** case. It then takes the existing Missing files row, with Scan again, Convert what's there and Delete book (ruling 23), as part sets already do ("The track tags say there are 12 parts, but part 3 isn't here"). "Order unclear" then keeps only real order questions (ties, conflicts, no numbers anywhere).

### 5.4 Sentence and face changes

| Where | Today | New |
|---|---|---|
| Order unclear, no tags (`no_tracks`) | No file has a track number. The order comes from the file names. | **The tags have no track numbers. The file names set the order.** ("Track number" meant the tag; the new sentence says tag.) |
| Order unclear, `gaps` | Track numbers skip or don't start at 1. | Unchanged. The Numbers line gives the specifics. |
| Files unclear, one file of many, checking | This file is tagged as track 36 of 38. The other tracks aren't here. | **This file is tagged as track 36 of 38.** (the membership line says the rest) |
| Approve face and tooltip on a gap or start-late row | Approve this order / Approve the order shown: … | **Approve these files** / **Approve the files shown as one book, gaps included: convert if needed, rename, move to Audiobooks Sorted.** The face follows the cause, not the chip, so "this order" is never pressed on an incomplete set (R16). |

### 5.5 Worked examples

Values are examples; the engine supplies the real numbers.

**S1, the 13-file row, membership settled:**

```
Order unclear                                              [ Approve these files ]
The tags have no track numbers. The file names set the     [ Change order ]
order.                                                     [ Scan again ]
File names run from 004 to 017. Skipped: 007, 009-016.     [ Edit names ]
The source folder holds only these 13 files.               [ View metadata ]
Playback order                                             [ Open source folder ]
 1. 004-01.MP3
 …
 + 8 more, listed in the details panel.
In  Z:\Audiobooks\Unsorted\Терри Пратчетт - Шляпа полная небес\
Goes to  Audiobooks Sorted\Pratchett Terry\…
```

Sergei now knows what the jumps are, that the folder holds only these files, and where to look. The same row **while the app is still checking**:

```
Order unclear
The tags have no track numbers. The file names set the order.
File names run from 004 to 017. Skipped: 007, 009-016.
Still checking which other files belong to this book.
```

**S2, Abnett, three files** (answers "why does it start at 05"):

```
Order unclear
The tags have no track numbers. The file names set the order.
File names run from 05 to 07.
The source folder holds only these 3 files.
```

If the engine also detects the part marker (`Часть Пятая`), the existing "Also: the name marks this as one numbered part." line joins it.

## 6. One source folder = one book (requirement 4, ruling 68)

### 6.1 One row for a folder

A folder of a novel plus bonus stories is **one row**: one title, one count (the total of all its files), one Goes to. The row never shows the stories as separate candidates. Under the title (line 5 of the Book column):

```
Криг
Includes 3 stories: Исход, Сильные среди нас, Среди мертвецов.
2 of them credit another author.            <- only when story credits differ from the book's
```

- Up to 3 titles, then " + {n} more"; the full list with each story's credit is in the details panel, which already prints component title, author and order per file (`memberComponents`: "Author: …", "Recorded component order: …"). Nothing new there; Futaba confirms it.
- A novel plus stories never turns the Author line into a multi-author credit by itself (ruling 68). If the engine does set a multi-author credit, the Author line shows it as sent.
- Gaps and "missing" are judged on this one row, after membership is settled, with the section 5 lines. S5's four rows would become one row whose numbers line reads, for example, `Tags run from 1 to 38. Skipped: 35.` (a mock value: the screenshot does not show whether track 35 exists).

### 6.2 Why the row, not a banner

Sergei's instruction is "never divide". A row that shows the folder, one count and "Includes" is the proof that the app did not divide. The source line (3.4) makes a division visible if it ever returns.

### 6.3 A genuinely ambiguous folder is a question

When the engine cannot tell whether a folder is one book (it raises it, as ruling 68 requires), the row is an existing **Files unclear** row, not a new kind:

```
Files unclear                                           [ Approve as one book ]
This folder may hold more than one book.                [ Keep as separate books ]
Books: Book A (34 files) · Book B (12 files)            [ Scan again ]
In  Z:\Audiobooks\Unsorted\…\                           [ Edit names ] [ View metadata ]
As one book  Audiobooks Sorted\…\….m4b                  [ Open source folder ]
```

- Reuses: the Files unclear status, the `Books:` line (the `works` cause), the "Approve as one book" face, "Keep as separate books" (the existing set-row button) and the "As one book" Goes to label.
- **"Approve as one book" is first**: ruling 68's default is one book. "Keep as separate books" is the other answer.
- Tooltips: Approve as one book: "File everything in this folder as one book: convert if needed, rename, move to Audiobooks Sorted." Keep as separate books: "Keep each book on the Books line as its own book. Nothing is joined. Each is checked again."
- The raised question appears at most once per folder. It is the only case where a folder's files may appear under more than one row.

## 7. Copy sheet (single source; straight apostrophes)

| Where | String |
|---|---|
| Column headings | Book / Author / reader |
| Book column lines | `{title}` / `Check this title: it looks like a narrator credit.` / `Check this title: it looks garbled.` / `Check this title: it starts with the author's name.` / `The title mentions a series: {text}. Not used in the file name.` / `Title clue: {raw}` / `Includes {k} stories: {t1}, {t2}, {t3} + {n} more.` / `{m} of them credit another author.` (m = 1: `1 of them credits another author.`) |
| Author column lines | Author / Reader / Clue (labels); `Check this author: it looks garbled.` |
| Clue roles (suffix after " · ") | narrator credit / garbled / author and title together / uploader tag / generic name |
| Source line | `In {path}` / `In {n} folders` |
| Numbers line | `File names run from {first} to {last}.` / `Tags run from {first} to {last}.` + ` Skipped: {list}.` |
| Membership | `Still checking which other files belong to this book.` / `The source folder holds only these {n} files.` / `The source folders hold only these {n} files.` |
| Sentences changed | `The tags have no track numbers. The file names set the order.` / `This file is tagged as track {x} of {n}.` (checking only) / `This folder may hold more than one book.` |
| Faces | Open source folder / Open folder (list items) / Approve these files (gap rows) |
| Tooltips | See 3.5. Approve these files, gap row: "Approve the files shown as one book, gaps included: convert if needed, rename, move to Audiobooks Sorted." Approve, checking: "The app is still checking which other files belong to this book. This approves only the files shown." Approve as one book (folder): see 6.3. |
| Accessible names | "Open source folder: {title clue}" / "Open folder {i} of {n}: {path}" |
| Failure | "Folder unavailable. Connect the library drive and try again." (existing) |
| Part B (rulings 69 and 70) | Every string is in sections 15 to 19; none is repeated here. |

## 8. What the UI needs from the engine (names assumed; Ender confirms)

1. **On every list row:** `source_directories: [{id, path, files}]` (bounded, for example the first 50 with the true count in `source_directory_count`). Today only the details answer carries them (R2). Derivable from `members` with no file access; or the page fetches on first press (the "In" line then has no path until it loads, so the list-row field is preferred).
2. **Title and author roles:** per clue, a role from {narrator, garbled, author_and_title, uploader, generic}; per shown title or author, an optional `flag` from {narrator, garbled, author_in_title}. The page never infers these from text.
3. **Reader:** the narrator names behind a credit, when known.
4. **Series:** `series: {name, number, basis}` when the book's series is established or proposed (a list row carries only `place` today: saved values, and `placeText` prints no plain series); and `series_clue` (the text, for example "Книга Нового Солнца #3") when the title carries it and it is not applied.
5. **Numbers:** `{source: names|tags, first, last, skipped: [..], skipped_total}` as printed tokens. `ask.files` carries only the first 6 names, so the page cannot compute this.
6. **Membership:** `checking | established`.
7. **Folder unit (ruling 68):** `contents: {stories: [{title, author, files}]}` for a single row holding a novel plus stories; a typed cause (`folder_books`) for the raised multi-book question, with the existing `works` list.
8. **Part B, source state and the converted file:** `source_state: present | gone` on every row, and on a finished (verified) row `output: {path, absolute, folder_id}`. A list row carries only the `audiobook_ready` flag today; the converted file's path exists only in the details answer (`current_audiobook`). The open-folder route already accepts `folder_kind: 'output'`.
9. **Part B, destination:** on every row's `destination`: `override: {path} | null`, `computed: {path}` (the planner's own folder and name, ignoring the override), `outside_sorted: bool`, and `taken` evaluated at the chosen folder.
10. **Part B, requests:** set or clear the override (book, revision, folder or null), answering with the new `destination`. On a finished book the same request queues a **move** (a new queue action next to Approve, Scan again and Delete book), with optional progress, and typed failure causes: `target_exists`, `unavailable`, `not_writable`, `no_space`, `in_use`, `source_missing`, `unsafe`, `partial` (moved, old file not removed), `changed`.
11. **Part B, the picker:** a main-window bridge, for example `booksDesktop.chooseFolder({title, defaultPath, buttonLabel})` returning a path or null (cancel). Today the only folder picker is `books:browse`, answered only to the setup window (`desktop/preload.js`, `desktop/main.js` L734). The page never types or edits a path.

## 9. Implementation checklist for Ender (slices; each ships alone)

**Slice A: Open source folder (needs only item 8.1)**
1. Add `source_directories` and `source_directory_count` to the list-row payload (`merge_service.py`, where the row is assembled; the details answer at L4349-4350 keeps its own). Remove the dependency on `row.source_directory_count === 1`.
2. Replace the two buttons at `web/app.js` L589-590 with one builder: face "Open source folder", the tooltips of 3.5, `aria-label` "Open source folder: {name}", `aria-describedby="folder-help"`, click and keydown `stopPropagation`, `folderState`/`openFolder` as today. One folder: send its id and open. Several: toggle the list (3.3), `aria-expanded`, `aria-controls`, focus to the first item, Esc closes and returns focus.
3. One shared `folderLine(row, directory, i, n)` builder for the row list and `renderInspector` (L866). Item tooltip "Open this folder in File Explorer." in both places.
4. Add "Open source folder" and "Open book folder" to `lookingOnly` (L351), or the new button is gated differently from View metadata while loading (ruling 28).
5. The source line (3.4), above "Goes to", omitted when the row's own list already prints "In {folder}". Keep the list's open state per book.
6. Tests: fixtures with the **live** row shape (no `source_directory_count: 1`); one test per row kind for the button; list with 3 and 12 folders; the error message.

**Slice B: identity (works on today's proposal; flags and roles arrive with 8.2 to 8.4)**
7. Headings "Book" and "Author / reader" (`renderRows`, L546). Update the tests that assert the old headings.
8. Build columns 2 and 3 for rows with `row.ask` from the lines of 4.2 and 4.3 instead of `td.textContent`. Line 1 follows the draft preview. Narrow bands: fold Author and Reader into `titleFacts` (L2245); keep title, flags and clue lines in column 2.
9. Show the existing Title field when line 1 is flagged (extend the guess rule in `askFieldPlanOf`, L2518). Approve is not blocked.
10. Move the Place line from the status cell into column 2 (line 3) and extend `placeText` (L2889) so a plain `Series: {name} · No. {n}` prints too, fed by 8.4. If moving it proves costly in `buildNamesBlock` (L2973), fall back: leave it in the status cell, directly above the source line. Say which.

**Slice C: numbers and membership (needs 8.5 and 8.6)**
11. The Numbers and membership lines above the file list in `buildAskCell` (L2694); the `no_tracks` and `one_of_many` sentence changes in `holdSentence` (L2450); the gap-cause Approve face and tooltip in `askLabel`/`askTip` (L2493-2497), and the checking tooltip.
12. Every new line hides when its data is absent. Nothing shows "undefined", "0" or an empty label.

**Slice D: one folder = one book (needs 8.7 and Ender's grouping fix)**
13. The Includes lines (line 5 of 4.2). The raised-question row reuses the Files unclear rendering, the `Books:` line, the `separate` button and the "As one book" label (`setCause` generalised to the new cause), with the tooltips of 6.3.

**All slices**
14. No new color, font, token or animation. Reuse `.field-help`, `.goes-to` label styling, `.source-directory`, `.path`, `--warning`, `--muted`. Only one new rule is needed: the folder list box (max-height about 232 px, own scroll).
15. Strings only from section 7 (and, for Part B, sections 15 to 19).

**Slice E: destination override, finished rows, converted-row folder (Part B; needs 8.8 to 8.11; items 14 and 15 apply)**
16. The picker bridge: a main-window `chooseFolder` in `desktop/preload.js` and `desktop/main.js` (the existing `books:browse` answers only the setup window). Title, confirm-button label and start folder come from the page (15.3). No bridge (browser launch): the control is `aria-disabled` with its tooltip.
17. The engine request of 8.10 (set or clear a folder) and the `destination` fields of 8.9. The page sends a path it got from the picker and never lets Sergei type one.
18. One destination block builder (15.1) replacing `renderGoesTo`, `stoppedGoesTo` and the names editor's own Goes to line, so ask rows, Stopped rows, queued rows and finished rows share it. Labels "Goes to", "Now in", "Moving to", "Already there".
19. The move as one more queued action through the existing queue (`ASK_QUEUE`, `queueCancelButton`, queue words), with the clock and busy ladder of `clockNote`, the states of 18.1 and the failure copy of 18.2. A failed move leaves the audiobook where it was.
20. Finished rows (16): show the block on `audiobook_ready` rows from `output`; no new filter, column or panel control.
21. The Open source folder face and target by `source_state` and `output` (17); `folder_kind: 'output'` for the converted file's folder.
22. Approve tooltips, "done" hints and the Name taken sentence read "the folder you chose" instead of "Audiobooks Sorted" while an override is set (19.2).
23. Tests: the live row shape; one test per state of 18.1 and per failure cause of 18.2; override on an ask row, a Stopped row, a queued row and a finished row.

## 10. Checks for Futaba (committed build, seeded fixture, the live list payload shape, nothing on Z:)

1. **Button on every row.** One fixture per row kind (Order unclear, Files unclear, Part of a bigger book, Missing files, Same author?, Name taken, a Stopped row, a no-title row): each has exactly one control with the face "Open source folder" and none has "Source folders" or "Open folder" in its Actions cell. Control: on 0.23.0 every row shows "Source folders".
2. **One folder.** Press: one open-folder request with the folder id (stub dispatcher), the page does not scroll, no panel opens, focus stays, the message span is empty on success and shows the existing sentence on a stubbed failure.
3. **Several folders.** Press: the list appears in flow under "In 3 folders", focus on the first item, each item opens its own folder id, Esc closes and focus returns, the state survives 10 polls and a chip switch. With 12 folders the list scrolls inside its box; every folder is reachable by keyboard.
4. **Live shape.** The fixtures use the list payload as the engine really sends it, not a hand-written row with `source_directory_count: 1`.
5. **Loading.** During the load gate "Open source folder" behaves like View metadata (inert until the books are on screen).
6. **Identity.** For each of the five screenshot shapes: line 1 equals the proposal; the clue line appears only when it differs; flags, roles, Reader and Check lines appear only when the engine sends them; the Title field appears for a flagged title and Approve still works. The page text of a row identifies the book without reading "Goes to".
7. **Narrow bands.** At 700 px and 599 px the Author and Reader values still show (folded) and the flags stay visible.
8. **Numbers line.** A fixture with a known gap prints exactly the first, last and skipped tokens. Control: contiguous numbering prints no line.
9. **Membership.** Checking: the line shows, Approve works with the checking tooltip, and the page text of that row contains neither "missing" nor "aren't here". Established: "holds only these n files". Nothing sent: no line.
10. **Gap rows.** The Approve face reads "Approve these files", never "Approve this order".
11. **Ruling 68.** A fixture folder with a novel plus three stories is one row with the total count and an Includes line; the details panel lists each story with its credit. The ambiguous fixture shows the raised row (Books line, "Approve as one book" first, "Keep as separate books").
12. **Same folder, two rows.** Across the whole fixture list, no two review rows print the same source folder, except the ambiguous question. Control: a deliberately split fixture (the S5 shape) fails this.
13. **Rects** at 1440, 1024, 700 and 200% zoom, in each state of 3.6: no two new elements intersect, buttons at least 96 x 32, list items 32 high, no horizontal scroll with a 200-character unbroken path, focus ring not clipped, pending labels do not resize the row.
14. **Tooltips** on every control of 3.5 and the Approve tooltips of section 7, in the packaged window.
15. **Part B, button budget.** In every row kind the Actions column holds at most six buttons and none is "Choose folder…". Every row with a destination or a converted file has exactly one "Choose folder…" in its destination block; a row with neither (all files missing, no output) has none.
16. **Part B, picker.** Press opens the picker (stub bridge) with the title, confirm label and start folder of 15.3; cancel changes nothing and returns focus to the button; no bridge gives an `aria-disabled` control with its tooltip; the page offers no text box for a path.
17. **Part B, display.** With an override: the path is the chosen folder plus the computed file name, "Folder chosen by you." and "The app would use {computed folder}" show, "Use computed folder" is present. Without one: neither line nor button. The "outside Audiobooks Sorted" line follows question 4. A Name taken at the chosen folder shows "Already there" and a working-but-inert Approve with the sentence of 19.2.
18. **Part B, reset.** Not finished: one press clears it, no confirmation, no file moves. Finished: the inline confirmation appears in flow, focus on "Keep it here", Esc keeps, "Move book" queues the move.
19. **Part B, move states.** Each state of 18.1 shows its text in order (queued, moving with a clock after 2 s, moved, failed); one fixture per failure cause of 18.2 shows its sentence and leaves "Now in" unchanged; "Choose folder…" is available again after a failure. Control: a stub move that fails after the picker leaves no row claiming it moved.
20. **Part B, finished rows.** In the Audiobook Ready list every row shows "Now in" with the converted file's folder; a book moved by the app shows the new folder after the next poll.
21. **Part B, folder face.** Finished row with originals present: "Open source folder" opens them. Finished row with originals gone: the face reads "Open book folder" and opens the folder named on the "Now in" line. A row that is not finished and has no originals keeps "Open source folder" and the failure sentence.
22. **Part B, Approve.** Choosing a folder on a waiting row does not queue anything or change its status; the saved line says so; Approve then files the book in the chosen folder. Control: the same press on a finished row queues a move and never a conversion.
23. **Part B, rects.** Destination block states: not overridden, overridden, taken, picking, queued, moving, failed, reset confirmation; at 1440, 1024, 700 and 200% zoom, with the editor open and a 200-character path: no overlap, buttons at least 96 x 32, no horizontal scroll, focus ring not clipped.

## 11. Questions for Sergei (one word each; the spec assumes the default)

1. While the app is still checking which files belong to a book, should **Approve** stay available (its tooltip warns it approves only the files shown), or wait until the check ends? Default: **stay** (rulings 6b and 35). Answer "stay" or "wait". Only the Approve line of 5.3 changes.
2. A book with numbering gaps, in a folder the app has settled as the whole book: list it under **Missing files** (with Scan again, Convert what's there and Delete book to reacquire), instead of Order unclear? Default: **missing**. Answer "missing" or "order".
3. When you choose a folder for a book that is **waiting for your approval**, should that choice also approve it? Default: **no**: the folder is saved and Approve stays your separate press, as for Title and Author (rulings 6b and 56). Answer "no" or "yes". If "yes": the picker's confirm button reads "Select and approve", the saved line becomes "Approved. {title} goes to {path}." and the row flips to Queued. Nothing else changes. A finished book is not affected: choosing a folder there moves the file, because it is already approved.
4. When you choose a folder **outside Audiobooks Sorted**, may the app remove the original files once the converted book is verified in that folder? Default: **keep** (ruling 2 names Audiobooks Sorted), and the row says "Originals stay: this folder is outside Audiobooks Sorted." Answer "keep" or "remove". If "remove", that line goes and the existing cleanup rule applies to the chosen folder.
5. When a finished book is moved out of Audiobooks Sorted, should the app remove the author or series folder it leaves empty? Default: **keep**: nothing is deleted that you did not press. Answer "keep" or "remove".

## 12. Offers (not in this release)

1. Put Edit names, View metadata and Open source folder on one line (about 3 x 96 px). It cuts about 110 px from every review row (R4).
2. Use the same Book and Author / reader layout on every candidate row in All candidates, not only rows with a question.
3. Up and Down arrows between rows (earlier offer), more useful with long review sessions.
4. **Choose folder for the selected books**, in the bulk bar: one picker for many sparse rows like S6. It would reuse this section's rules per book and the bulk dialog's path list.
5. An **Open folder** button on the "Now in" line while the originals still exist, so the converted file's folder is one press away (today: View metadata, then "Open output folder").
6. **Forget my choice** on a finished book: drops the override and leaves the file where it is (the reset in 15.4 moves it back).

---

# Part B: rulings 69 and 70 (added 2026-10-29)

Basis: rulings 69 and 70 (`Team/Docs/BooksArranger_Rulings_2026-10-24.md`); screenshot S6; a read-only look at `web/app.js` (`filterOptions` L10, `candidateStatus` L2309, `renderGoesTo`, `stoppedGoesTo`, `buildNamesBlock`, `buildAskActions`, `queueCancelButton`), `merge_service.py` (`open_folder` already takes `folder_kind='output'`; `current_audiobook`; list rows carry only `audiobook_ready`) and `desktop/preload.js` plus `desktop/main.js` L734 (the only folder picker, setup window only). Nothing launched. Geometry is target geometry. Same rule as Part A: this says how it is shown; what the engine moves, validates and refuses is Ender's.

## 13. What the rulings and S6 add

- **Ruling 69:** on any row, the Windows folder picker chooses the destination folder. It beats every computed destination. After the book is finished the app moves the converted file there; changing only the destination never reconverts.
- **Ruling 70:** "Open the source folder" opens Explorer on every row. When the originals are gone because the book was converted and moved, it opens the folder that holds the converted file.
- **S6** (R17 to R19) is the case behind 69: rows with nothing to compute from, filed under `Без автора` with an underscore title. The app cannot do better, so Sergei must be able to say where.

Best practice applied: (1) a control sits with the thing it changes, as Windows Settings shows a path with a "Change" button beside it (Jakob, Fitts); (2) the OS picker is the commit, so its confirm button names the consequence; (3) an override must be visible, attributable and reversible: the row says whose folder it is, shows what the app would have used, and clears in one press (NN/g visibility of status, user control and freedom, recognition over recall); (4) a move never destroys: a failure leaves the file where it was and nothing is ever overwritten (the existing never-overwrite gate); (5) choosing a place is an edit, not an approval (section 19).

## 14. Placement and the six-button budget

**Decision: "Choose folder…" is not an Actions-column button.** It sits directly under the destination line, in the Review status cell, in flow. The Actions column keeps its ceiling of six.

| Row kind | Actions column (after Part A) | With Part B |
|---|---|---|
| Hold rows: Order unclear, Files unclear | Approve (face by cause), Change order or Choose files, Scan again, Edit names, View metadata, Open source folder: 6 | 6 |
| Set rows (parts of a bigger book) | Approve as one book, Keep as separate books, Scan again, Edit names, View metadata, Open source folder: 6 | 6 |
| Missing files | Scan again, Convert what's there or Remove from list, Edit names, View metadata, Open source folder: 5 (Delete book on its own line) | 5 |
| Title or author, Author unclear, Same author?, Name taken (S6) | Approve, Edit names, View metadata, Open source folder: 4 | 4 |
| Finished (Audiobook Ready) | Edit names, View metadata, Open source or book folder: 3 | 3 |

Why not a button in the stack:
- A seventh stacked button on hold rows deepens R4 (the column, not the content, sets the row height).
- The Actions column acts on the book. This changes one property of it, and the destination line is where Sergei reads that property. The editor already works this way: Save and Discard sit under the Goes to line, not in the column.
- Sergei judges the path and then wants to change it: the control belongs at the end of the path.

**Where it appears.** On every row that has a destination or a converted file: question rows, Stopped rows, held, queued and processing rows (label "Goes to"), finished rows (label "Now in"). A row with neither, meaning all files missing and no converted file, has no control: nothing will be written and nothing exists to move. Its Actions are Scan again and Remove from list. A row whose destination cannot be computed yet shows "Goes to  Not decided yet." and the control, so a folder can be chosen before the title is.

**Order in the cell.** `… file list, source line, Edit names block, Goes to line, folder controls`. When the names editor is open, its Save and Discard come after the folder controls. The folder choice is not part of the editor's draft: it takes effect through the picker at once, and Discard never undoes it.

## 15. The destination block

### 15.1 Anatomy and states

Reuses `.goes-to`, `.path`, `.field-help`, `--warning` and the `quiet row-retry` button (at least 96 x 32). No new token.

```
Goes to  Audiobooks Sorted\Без автора\Rak_Ed_Farrer_Met_Den_Osvobogdeniy.m4b
[ Choose folder… ]
```

With a folder chosen by Sergei:

```
Goes to  D:\Books\Horror\Rak_Ed_Farrer_Met_Den_Osvobogdeniy.m4b
Folder chosen by you. The app would use Audiobooks Sorted\Без автора\
Originals stay: this folder is outside Audiobooks Sorted.        <- question 4, default
[ Choose folder… ] [ Use computed folder ]
```

On a finished book:

```
Now in   Audiobooks Sorted\Pratchett Terry\Шляпа полная небес - Pratchett Terry.m4b
[ Choose folder… ]
```

| State | Label | Path shown | Line under the path | Controls |
|---|---|---|---|---|
| Not finished, no override | Goes to | the planner's path, relative to Audiobooks Sorted (as today) | none | Choose folder… |
| Not finished, override | Goes to | the chosen folder plus the computed file name, full path | `Folder chosen by you. The app would use {computed folder}` (+ the question 4 line) | Choose folder…, Use computed folder |
| Name taken in the chosen folder | Already there (existing label) | same | as above | same; Approve inert with the sentence of 19.2 |
| No destination yet | Goes to | `Not decided yet.` | none | Choose folder… |
| Finished | Now in | the converted file's current path | as above when overridden | Choose folder…, Use computed folder when overridden |
| Move queued / moving | Moves to / Moving to | the target path | the state line of 18.1 | face changes, see 18.1 |

The full path is in the line's `title`, as for every path.

### 15.2 Rules

1. **It beats everything computed:** the planner's folder, Без автора, universe, series, author and collection folders, the English-author folder rule, a Name taken alternative. The file goes **directly into the chosen folder**: the app adds no author or series folder inside it. The line shows exactly where.
2. **Only the folder is the user's.** The file name stays the computed one (`Title - Author.m4b`) and follows Edit names, so a corrected title renames the file inside the chosen folder.
3. **Per book.** It persists across scans, restarts and name edits until cleared. There is no "Applies to n books" line: unlike a name, a folder is not learned for other books.
4. **Never typed.** The page offers no text box for a path. The path comes from the OS picker and goes to the engine, which validates it (section 18.2 for what it can refuse).
5. **Visible, attributable, reversible:** "Folder chosen by you." (attribution), "The app would use …" (what resetting gives), "Use computed folder" (one press).
6. **Outside Audiobooks Sorted:** while the override is outside it, the row says "Originals stay: this folder is outside Audiobooks Sorted." This is question 4's default. It is a visible line under the destination and goes away if Sergei answers "remove".

### 15.3 The picker

- Press opens the Windows folder picker. The face shows "Choosing…" (`aria-disabled`, keeps focus) while it is open. The row is not rebuilt (a control inside has focus); polls continue.
- **Dialog title:** "Choose a folder for {title}". **Confirm button:** "Select folder" for a book not yet finished, "Move here" for a finished one, so the dialog itself says what happens. If the host cannot set those labels, the system defaults stay and the row says the rest.
- **It starts in:** the book's chosen folder; else the last folder Sergei chose; else the nearest existing folder above the computed destination; else Audiobooks Sorted. Repeated picks for similar sparse rows then land one click from the right place.
- **Cancel:** nothing changes, no message, focus returns to the button.
- **No desktop bridge** (browser launch): the control is `aria-disabled` and its tooltip says "Choosing a folder works in the desktop app."
- After the pick the page sends the request. For a book not finished it saves at once; for a finished book it queues the move (18.1). The standard pending clock and busy ladder (0.22.3 spec 2.1) apply if the answer is slow.

### 15.4 Clearing

"Use computed folder" is present only while an override is set.

- **Not finished:** one press clears it. No confirmation: no file moves, and the line shows the computed path at once. Line: "Folder reset. This book goes to {path}." Focus moves to Choose folder…, because the pressed button disappears.
- **Finished:** it moves the file back, so it is confirmed inline, in flow, in place of the two buttons (nothing is covered):

```
Move the audiobook back to Audiobooks Sorted\Pratchett Terry\Шляпа полная небес - Pratchett Terry.m4b? Nothing is converted again.
[ Move book ] [ Keep it here ]
```

Focus goes to **Keep it here** (the safe default); Esc is Keep it here. "Move book" queues the move (18.1). The choice flow needs no such step because the picker's confirm button is the commitment.

## 16. Where finished books live

**Today a finished-book surface exists; its place line does not.** The Audiobook Ready filter is the default Status of the Book candidates list (`filterOptions.candidates`, first entry `converted`). A finished book is an ordinary candidate row with status "Audiobook Ready" and three buttons (Edit names, View metadata, Source folders or Open folder). By the code, such a row says nothing about where the converted file is: a list row carries only `audiobook_ready` (a flag), and the file's path exists only in the details panel ("Current audiobook" and "Open output folder"). So the override cannot reach a finished book from the row today.

**Smallest addition:** the destination block of section 15 on finished rows, labelled "Now in", fed by the verified output (`output`, 8.8). No new filter, column, page or panel control. The details panel keeps its read-only "Current audiobook" path and "Open output folder"; there is no second place to choose a folder (the same one-editor rule as ruling 40: the row is the place).

## 17. Open source folder on converted rows (ruling 70)

| Row state | Face | Opens | Tooltip |
|---|---|---|---|
| Originals present (any row) | Open source folder | the source folder or the folder list (section 3) | as 3.5 |
| **Finished, originals gone** | **Open book folder** | the folder holding the converted file: the folder named on the "Now in" line | The original files are gone. Open the folder that holds the converted audiobook. |
| Not finished, originals gone (Missing files) | Open source folder | the old folder if it still exists; else the failure sentence | as 3.5 |
| Finished, originals still present | Open source folder | the originals. The converted file's folder: View metadata, then "Open output folder" (offer 5) | as 3.5 |

**Why relabel.** The face is the last thing Sergei reads before he clicks. "Open source folder" that opens Audiobooks Sorted misleads the first time it happens. Ruling 70's model, that the converted file is now the book's current source, stays in the engine; the face tells the plain truth. Slot, size, behavior, message span, accessible-name pattern and tooltip pattern do not change, so nothing is relearned. Accessible name: "Open book folder: {title clue}". The "In {folder}" line is dropped on such rows (it would name a folder that no longer exists); "Now in" replaces it. After a move the face stays "Open book folder" and opens the new folder. The button calls the existing open-folder route with `folder_kind: 'output'`. A converted file that was moved or deleted outside the app gives the existing failure sentence.

## 18. Moving a finished book

### 18.1 States

Rule from rulings 35 and 56: nothing is refused for being busy; the request is accepted, shown as queued with Cancel, and re-checked when it runs. Everything else on the row queues behind a move with the existing "is queued for this book" hints.

| State | Label and path | Line (polite, under the controls) | Choose folder… face | Other |
|---|---|---|---|---|
| Picking | unchanged | none | Choosing… (aria-disabled) | picker open |
| Saved (not finished) | Goes to, new path | A row with an Approve button: "Folder saved. Approve converts the book and files it there." Any other row: "Folder saved. This book goes to {path}." | Choose folder… | Use computed folder appears |
| **Queued** (finished) | Moves to {target} | Move queued. It runs when the app is free. | Queued (aria-disabled) | **Cancel** beside it, the existing queued-action Cancel; "Move" joins its queue words |
| **Moving** | Moving to {target} | Moving the audiobook… 0:07 (clock from 2 s; "· 41%" when the engine sends progress; the existing busy-ladder sentence from 3 s) | Moving… (aria-disabled) | no Cancel: a move in progress is not stopped half way |
| **Moved** | Now in {new path} | Moved. The audiobook is now in {folder}. | Choose folder… | Use computed folder appears; Open book folder opens the new folder |
| **Failed** | Now in {unchanged path} | the sentence of 18.2, `--warning`, `role="alert"` | Choose folder… (available again) | the audiobook is where it was |

The lines stay until the next press or change: no timers, no toasts. A failed move says where the audiobook is ("still in …") or "Nothing was moved."

### 18.2 Failures

Typed causes from the engine; the page maps them to these sentences and never shows the engine's English. `{name}` is the file name, `{folder}` the chosen folder in full.

| Cause | Sentence |
|---|---|
| `target_exists` | A file named {name} is already in {folder}. Nothing was moved. |
| `unavailable` | {folder} isn't available. Connect the drive or choose another folder. Nothing was moved. |
| `not_writable` | The app can't write to {folder}. Choose another folder. Nothing was moved. |
| `no_space` | There isn't enough free space on that drive. Nothing was moved. |
| `in_use` | The audiobook is open in another program. Close it and try again. Nothing was moved. |
| `source_missing` | The audiobook isn't where the app expects it. Nothing was moved. |
| `unsafe` | That folder holds this book's original files. Choose another folder. |
| `partial` (copied, old file not removed) | Moved to {folder}. The old file in {old folder} couldn't be removed. Delete it yourself. |
| `changed` | This book changed. Review its details and try again. (existing) |
| refused, no reason | Move was not accepted. Nothing was moved. |
| closing | Books Arranger is closing. Nothing was moved. (existing) |
| no answer from a busy engine | This hasn't been confirmed yet. The app is busy with background work, so it may still go through. Check this row in a moment. (existing) |

The never-overwrite rule is the first row: a file with the same name is a refusal with its reason, never a replacement. For a book not finished, the same causes appear as a refusal of the request or on the Name taken row (19.2). Every failure leaves "Choose folder…" available.

## 19. Approve, tooltips and overlap

### 19.1 Does choosing a folder approve? No (question 3)

**Default: choosing a folder is an edit, not an approval.** Reasons: rulings 6b and 56 make approval an explicit press that overrides every hold and later leads to source cleanup, and a mis-pick in a folder dialog should not start that. Title, Author, Series and Number do not approve either, and Approve uses what is shown ("what you see is what gets used"), so it files the book in the chosen folder, even over the Без автора fallback. The saved line names the next step, so the state is never hidden: "Folder saved. Approve converts the book and files it there."

| Row | Choosing a folder |
|---|---|
| Waiting for approval (question rows, S6) | Saves the folder. Status, reason and Approve are unchanged. |
| Queued, processing, Stopped | Saves the folder. The engine applies it when the file is written, or moves the file afterwards (ruling 35: it accepts and does it when it can). |
| Finished | Queues a move. Never converts. The picker's confirm button says "Move here". There is nothing to approve. |

If Sergei answers "yes" to question 3, only the waiting-row line and the picker's button label change (see question 3).

### 19.2 Copy that changes while an override is set

| Where | Today | With an override |
|---|---|---|
| Every Approve tooltip ending "move to Audiobooks Sorted." (including the re-encode set tooltip) | …move to Audiobooks Sorted. | …move to the folder you chose. |
| Approved row hint | Approved. Converts if needed, then renames and moves it to Audiobooks Sorted. | Approved. Converts if needed, then renames and moves it to the folder you chose. |
| Name taken, Approve inert | That name is already in Audiobooks Sorted. Change the title or author. | That name is already in the folder you chose. Change the title, the author or the folder. |
| Bulk "Approve as is" dialog | lists each path as computed | lists each path as it will be, the chosen folders in full |

### 19.3 Tooltips (each control born with its own)

| Control | Tooltip |
|---|---|
| Choose folder… (not finished) | Choose the folder this book is filed in. Your choice replaces the folder the app computed. The file goes straight into it. |
| Choose folder… (finished) | Choose a new folder for this audiobook. The file is moved there. Nothing is converted again. |
| Choose folder… (picker open) | Waiting for the folder picker. |
| Choose folder… (queued or moving) | the existing "is queued for this book" hint / Moving the audiobook. Choose another folder when it finishes. |
| Choose folder… (no bridge) | Choosing a folder works in the desktop app. |
| Use computed folder (not finished) | Stop using your folder. The book goes to the folder the app computes. |
| Use computed folder (finished) | Move the audiobook back to the folder the app computes. Nothing is converted again. You confirm first. |
| Move book | Move the audiobook to the folder shown now. Nothing is converted again. |
| Keep it here | Leave the audiobook where it is and keep your folder. |
| Cancel (queued move) | the existing queued-action Cancel tooltip |
| Open book folder | The original files are gone. Open the folder that holds the converted audiobook. |

Accessible names start with the visible face: "Choose folder: {title clue}", "Use computed folder: {title clue}", "Move book: {title clue}", "Keep it here: {title clue}", "Open book folder: {title clue}".

### 19.4 No element covers another

Every new element is an in-flow block in the Review status cell: the line under the path, the control group, the state line, the reset confirmation. Nothing is absolutely positioned; there is no popover or menu; the picker is an OS window, not page content. The reset confirmation replaces the two buttons in the same flow space (they are hidden while it shows, not overlaid). In the narrow bands the group wraps under the path and stays at least 96 x 32. Row states to measure (check 23): not overridden, overridden, taken, picking, queued, moving, moved, failed, reset confirmation; each with the names editor open, with a 200-character path, at 1440, 1024 and 700 px and at 200% zoom.
