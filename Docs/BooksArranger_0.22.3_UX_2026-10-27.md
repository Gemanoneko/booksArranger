# Books Arranger 0.22.3: UX spec (Judy, 2026-10-27)

Basis: the "0.22.3" part of `Docs/BooksArranger_0.22.1_Backlog.md`; rulings 28, 35, 40, 41 (`Team/Docs/BooksArranger_Rulings_2026-10-24.md`); my 0.22.2 spec (`Docs/BooksArranger_0.22.2_UX_2026-10-26.md`, called "0.22.2 spec"). Read-only look at v0.22.2 on main: `web/app.js` (`askPanelEdits`, `namesInert`, `namesSave`, `namesDone`, `askInert`, `ladderNote`, `askNote`, `saveMetadata`), `web/index.html`, `web/style.css` (tokens only), `author_rules.py`, `merge_service.retract_author_rule`, `public_research._learn_author`. Nothing launched, no rects measured: geometry is target geometry for Futaba. Titles and paths in mockups are examples. Spec only: no code, not committed. Only what is new or changed since the 0.22.2 spec is here; everything else stands. No new colors, fonts or animation: existing tokens (`--warning`, `--muted`, `--focus`) and `.field-help`.

## Questions for Sergei (answer in a word; the spec below assumes the default)

1. **After a Take back, may the app look the author up online again?** Today a taken-back rule "decides nothing", so research runs the lookup again on that author's next book and can learn the same wrong match. Default (spec assumes it): after Take back the app does not look that author up again; it asks you once ("Author unclear", ruling 39's question). Answer "ask me" or "look up again". If "look up again", only the done-line in 4.4 changes (last sentence).
2. **"Sources disagree: which is correct?" in View metadata** also decides a title or author, by choosing between shown sources (no typing). Default: it stays where it is, as a choice among sources, because it is evidence review and not a typed edit. Answer "stay" or "move into the row box".

## In brief

1. **One editor (section 1).** View metadata stops editing names: Title, Author, Series, Number, Universe and Collection become read-only facts with one "Edit names" button that opens the row's box. Language, tag author, reader, genre and topic stay editable there. Its Save keeps only those.
2. **Save feedback (section 2).** Saving shows a running clock and the app's busy sentences in text; the result names where the book goes; if the list reload takes the book away, the strip says where it went, with a "Show it" button. Failures keep your typing and say why.
3. **A blocked Save or Approve says why (section 3).** One visible line under the control, plus a one-click fix where one exists. Tooltips repeat it; they are no longer the only place.
4. **Author rules (section 4).** A collapsed list in the top panel of rules the app learned online, with Find author and an inline "Take back" confirmation. Nothing is renamed or moved.

---

## 1. One names editor (ruling 40)

**Decision: View metadata becomes read-only for names and stays editable for everything that is not a name.** Fully read-only would strand the fields that exist nowhere else.

| Part of the book panel (candidate rows only) | After 0.22.3 |
| --- | --- |
| Canonical title, Author folder name, Universe, Series / cycle, Number in series, Short-story collection | **No inputs.** Shown as read-only facts (below). Typing here is no longer possible. |
| Original work language, Author for Artist tag, Reader / narrator, Ebook main genre, Nonfiction topic, Cycle has multiple authors | Unchanged, editable. |
| Save preview metadata | Stays. Saves **only** the fields above it. Tooltip: "Save these values as a draft and a metadata source for this book. Names are edited on the book's row." |
| Discard | There is none today and none is added. Names have no draft here, so there is nothing to discard. |
| Output folder, Check metadata, Cover, track review, Create audiobook | Unchanged. |
| "Sources disagree" and Save choices | Unchanged (question 2). |
| "Edit metadata" in Automatic result | Reads **"Edit names"** and does what the panel's Edit names does when the hold is about names (title, author, series, number, universe). It stays "Edit metadata" for any other hold. Ender checks the hold's field list. |
| A file's own panel (Files view, not a candidate) | Unchanged: a file is not a book (0.22.2 spec 1.1). |

**The names block** (top of the Metadata section, above Original work language):

```
Names                                                     [ Edit names ]
  Title        Сейф №1
  Author       Разные авторы
  Series       Протоколы SCP · No. 1
  Universe     None
  Collection   Yes
Names are edited on the book's row in the list.
```

- Facts use the page's `dl` (180 px label column). Series shows "None" when empty and "· No. n" only with a series. Collection shows Yes or No. Values are selectable text.
- Values are the row editor's opening values (one `/api/candidate/names` read when the panel opens for the book; "Loading names…" in the value column meanwhile). If the read fails: the facts hide and the line reads "Names unavailable. Press Edit names to see them in the list."
- Names Sergei already saved through this panel stay in force; the block shows them. Ender confirms.
- **Edit names (panel):** quiet button, min 96 x 32, right of the "Names" label. Press: the list scrolls the book's row to the middle, opens its editor and focuses Title (the row's own Edit names behavior). Tooltip: "Open this book's Edit names box in the list."
- **Inert** (`aria-disabled`, keeps focus) with the cause as a visible `p.field-help` line under the block, same sentence as the tooltip: not on the current page: "This book isn't on the current page. Clear the filters or find it in the list, then press Edit names."; otherwise the row's own inert sentence (`namesButtonInert`: "A retry is queued for this book. Cancel it to use this." / "No files are left for this book.").
- "Manual review" help line becomes: "Inspect or edit this book manually. Names are edited on its row. Automatic processing does not require this step."
- **One consequence for Ender:** with no names inputs, the panel cannot hold a names draft, so typing in the row can no longer mark the panel dirty. Save then has no conflicting writer; section 3 lists panel edits as a reason for Approve and shows the Save line only if Ender finds a real conflict.

## 2. Save feedback (ruling 28)

Applies to every save that remains: the row box Save and Forget, Approve (it records names), and the panel's Save preview metadata, Save choices and Save track review. Rule: **between the press and the end there is always text on screen that changes or counts, next to the button, never only in a tooltip or the page-top message line.**

### 2.1 What shows, in order

| Phase | Where | Text |
| --- | --- | --- |
| Pressed | The face of the button | "Saving…" with `aria-disabled` (exists; keeps focus). |
| Saving | `p.names-status` directly under Save and Discard (panel: the element beside the button, see 2.5) | under 2 s: "Saving these names…" From 2 s: "Saving these names… 0:07" (m:ss, once a second). From 3 s add the existing ladder sentence ("The app is busy with background work, so this takes longer."); from 60 s the existing "Still waiting (n min). The app is busy with background work." plus "It may still go through. Don't press Save again." Forget: "Taking this correction back…" Approve keeps "Approving this book…" and gains the clock. |
| Saved | Editor closes (exists). Row hint = the 0.22.2 spec 1.6 sentence (unchanged). Strip (the polite line under the filters) = 2.2. Focus returns to Edit names (exists). | see 2.2 |
| Updating the list | Row hint, appended once the reload has run 1 s | " Updating the list…" Removed when the list answer lands. |
| Row leaves | Strip, in the same render that removes the row | 2.3 |

There is no gap: the clock covers the wait, the result is on the row at once, and "Updating the list…" covers the reload that used to be silent.

### 2.2 The result lines

Save is not filing. It records, and the planner's path says where the book will go. Copy says "Goes to", the label the row already uses, never "filed" for a book that has not been converted.

| Case | Strip (stays until the chip or filter changes) |
| --- | --- |
| Book not yet converted | Saved names for {title}. Goes to {path}. {Applies to {n} books.} |
| Finished audiobook | Saved names for {title}. The finished audiobook in Audiobooks Sorted keeps its name. |
| No path available | Saved names for {title}. {Applies to {n} books.} (existing) |

`{path}` is the planner's path, verbatim, as in the row's Goes to line (`Audiobooks Sorted\…`); the page never composes it. Ender decides whether the save answer carries it or the page reuses the preview that matches the saved values; if neither is available the sentence is dropped, never guessed.

### 2.3 When the book leaves the list

Cause: after a Save, Forget or Approve the book no longer matches the chip or filter (its question is answered, or it moved to Queued / creating), so the next list answer omits it. It must never just vanish.

- **Trigger:** the first list answer after the action that omits the book, other than a delete or a removal (those keep 0.22.2 spec 5).
- **In the same render that removes the row** the strip reads: "Saved names for {title}. Goes to {path}. It left this list: {status}." After an Approve: "Approved {title}. It left this list: {status}." `{status}` is the status the row would show now ("Queued", "Waiting for retry checks", "Audiobook Ready" and so on). If the engine does not return it, the sentence is "It left this list. Find it under All." Ender adds the book's new row status to the Save and Approve answers (`restart_row` already exists for this).
- **Button after the sentence: "Show it".** Sets Status to All, puts the title in "Path contains", selects and focuses the book's row. Tooltip: "List this book: sets Status to All and searches for its title." The strip clears when the filter changes (existing rule).
- Focus: the next row's first working control (existing rule).
- A panel save that makes the row leave uses the same strip.

### 2.4 Failures (editor stays open, your typing is kept, Save is available again)

Shown in `p.names-status`, `--warning`, `role="alert"`, replacing the clock line.

| Case | Text |
| --- | --- |
| The engine refuses with a reason | "{reason} Nothing was changed." (existing, `serverSentence`) |
| Refused with no reason | Save was not accepted. Nothing was changed. (existing) |
| The book changed meanwhile | This book changed. Review its details and try again. (existing). The page reloads that row at once so the next press carries the new revision. |
| Closing | Books Arranger is closing. Nothing was changed. (engine sentence, existing) |
| No answer from a busy engine | This hasn't been confirmed yet. The app is busy with background work, so it may still go through. Check this row in a moment. (existing) |
| Saved, but the list could not be reloaded | Saved. The list could not be refreshed. It updates by itself. |
| Forget refused | Forget was not accepted. Nothing was changed. (existing) |

### 2.5 The panel's own saves

| Save | Status line | Result | Failure |
| --- | --- | --- | --- |
| Save preview metadata | `#review-note`, beside the button | "Saved: {fields}." naming what changed, such as "Saved: Reader / narrator, Original work language." (replaces "Saved.") | "Not saved. {reason}" with the engine's sentence, else "Not saved. Nothing was changed." |
| Save choices | `#metadata-question-status` | "Choices saved." | "Choices not saved. {reason}" |
| Save track review | **New** `p#track-save-status` under the button | "Track review saved." | "Track review not saved. {reason}" |

All three show the 2.1 clock and ladder while pending. The page-top `#message` no longer carries a panel save's result ("Metadata source saved. Review or check this book to continue." is dropped; that line sat at the top of the page, far from the button).

## 3. A blocked Save or Approve explains itself (rulings 28, 35)

Ruling 35 stands: another action running is never a reason. It queues, and the face reads Queued with Cancel (exists).

**Placement.** One `p.field-help.block-why` in `--warning`, `aria-describedby` from the button, no live region (it describes, it does not announce).
- **Save:** under Save and Discard, inside the editor.
- **Approve:** under the row's button group in the Actions cell.
- **When both are blocked by the same cause and the editor is open,** the sentence shows under both, and the fix button only under Save (where he is typing). With the editor closed the fix button sits under Approve.
- One cause at a time, the first in this order; fixing it reveals the next.
- The button's tooltip repeats the same sentence as a second channel.

| Control | Cause | Visible line | One-click fix |
| --- | --- | --- | --- |
| Save | Names still loading | Loading these names… | none (clears itself) |
| Save | Nothing changed | Nothing to save: these are the names the app already has. | none |
| Save, Approve | Title empty | Type a title first. | **Restore title** (only when the app proposed one). Tooltip: "Put the app's proposed title back." |
| Save, Approve | Series without a number | Type the number in the series, or clear the series. | **Clear series**. Tooltip: "Empty the Series field." |
| Save, Approve | Number without a series | Type the series name, or clear the number. | **Clear number**. Tooltip: "Empty the Number field." |
| Approve | Name already exists | That name is already in Audiobooks Sorted. Change the title or author. | none (changing the name is the fix) |
| Approve (Save only if Ender finds a real conflict) | Unsaved edits in the details panel | The details panel has unsaved edits for this book: {what}. Save them there, or discard them. | **Discard panel edits**. Tooltip: "Throw away the unsaved edits in the details panel for this book. Nothing is saved." |

- `{what}` lists the changed panel fields by their labels ("Reader / narrator", "Original work language", "Author for Artist tag", "Ebook main genre", "Nonfiction topic", "Cycle has multiple authors") and "the track order or included files"; if it cannot be listed, "edits".
- **Discard panel edits** drops the panel's draft for this book (the metadata draft and the track draft), at once, no dialog (it is unsaved typing and the line names it). The line becomes "Discarded the unsaved edits in the details panel." until the next change; focus moves to the control that was blocked, now working.
- The engine's `draft` refusal ("Edits in the details panel hold this book. Save or discard them, then approve.") now carries the same Discard panel edits button. The other post-press refusal lines of 0.22.2 spec 13.4 are already visible text and are unchanged.
- **Edit names stays as is** when inert: the row's queued or missing-files line already states the cause, and the panel button follows section 1.

## 4. Learned author rules, with "Take back" (Senua M5)

**What is listed:** rules the app learned online (`actor = assistant`): a Cyrillic credit filed under its English spelling (`same_as`), or an author found to write in Russian and kept as written (`keep`), still in force. Not listed: Sergei's own answers and the 2026-10-24 seeds (see the offers). Ender adds a read route for these; the retract route exists.

### 4.1 Where it lives

A collapsed `<details id="author-rules">` in the top "Library scan controls" panel, directly after the Research lines (`#research-current`) and before the discovery controls. It is where research reports, it is on screen at launch with no scroll, and closed it costs one 32 px line. The summary shows the count: **"Author rules learned online · 3"**. It loads after the screen (ruling 28): "Author rules learned online · loading…"; on failure "Author rules learned online · unavailable" and, inside, "The list couldn't be read. It tries again by itself."

```
v Author rules learned online · 3
  Names the app found online. It uses each one for every book by the same author.
  Find author  [ _________________ ]
  +----------------------------------------------------------------------+
  | Страуд Джонатан  →  Stroud Jonathan                    [ Take back ] |
  | Found on fantlab.ru · Learned 2026-10-27 · First seen on «Лестница…»  |
  |----------------------------------------------------------------------|
  | Бром Джеральд stays as written. The author writes in Russian.        |
  | Found on fantlab.ru · Learned 2026-10-27 · First seen on «Крампус…»   |
  |                                                        [ Take back ] |
  +----------------------------------------------------------------------+
```

- The list is a box inside the panel: `max-height` 320 px, scrolls on its own, newest first. Nothing overlaps; the box is in flow.
- **Each rule is two text lines and one button.** Line 1: `{credit} → {English name}`, or `{credit} stays as written. The author writes in Russian.` Line 2 (`.field-help`): `Found on {host}` as a link (opens the source in the browser, `rel="noopener noreferrer"`, tooltip "Open this source in your browser."), then ` · Learned {yyyy-mm-dd} · First seen on «{book title}»`. A source that is not a URL shows "Source: {source}". The button sits right of line 1 and wraps under the text in a narrow panel (container under 560 px).
- **Find author:** search input, 32 high, min 200 wide, filters on the credit or the English name, as you type, case-insensitive. Tooltip: "Show only rules whose name contains this text." No match: "No rule matches «{text}»."
- More than 200 rules: the newest 200 show with the line "Showing the newest 200 of {n}. Find author searches all of them."
- Empty: "No author rules learned yet. When research finds a foreign author's English name online, it is listed here."
- Summary tooltip: "Names the app found online and now uses for every book by the same author. Take one back if it is wrong."

### 4.2 Take back, confirmation (inline, no dialog)

Press **Take back**: the button and line 2 stay; below them, in the same box and in flow, the confirmation appears and the Take back button hides (so nothing covers anything):

```
Take back this rule? The app stops filing Страуд Джонатан as Stroud Jonathan and asks about this name again. Books already filed keep their folders.
[ Take back rule ] [ Keep rule ]
```

- `keep` rule wording: "Take back this rule? The app stops treating Бром Джеральд as a Russian-writing author and asks about this name again. Books already filed keep their folders."
- Focus moves to **Keep rule** (the safe default). Esc = Keep rule. Opening a second confirmation closes the first. Min 96 x 32 buttons.
- Tooltips: Take back: "Stop using this rule. Nothing is renamed or moved." / Take back rule: "Take this rule back now. Nothing is renamed or moved." / Keep rule: "Keep this rule and close this question."
- Accessible names start with the visible label: "Take back: {credit}", "Take back rule: {credit}", "Keep rule: {credit}".

### 4.3 While it runs, and when it fails

- Pending: the button face "Taking back…" (`aria-disabled`, keeps focus), line "Taking this rule back…" with the 2.1 ladder and clock. It follows ruling 35: a busy app makes it wait, never refuse; if Ender queues it, the 0.22.2 spec 13.3 queued line applies ("Take back queued. It runs when the app is free.") with Cancel.
- Failure keeps the rule on the list, the confirmation closes, Take back is available again. Text under the line, `--warning`, `role="alert"`: the engine's sentence ("This author rule was already replaced or taken back. Nothing was changed." / "There is no such author rule. Nothing was changed."); no reason: "Take back was not accepted. Nothing was changed."; no answer: "This hasn't been confirmed yet. The app is busy with background work, so it may still go through. Check the list in a moment." After "already replaced" the list reloads and the row drops or updates.

### 4.4 After a Take back

1. The rule's lines leave the list in the same render; the count in the summary drops; no ghost row.
2. No file is renamed or moved. Books already filed keep their folders. (Existing: the route touches no file.)
3. Held books the rule decided are researched again and come back asking (the route's `requeued` count). The book lists refresh (`lastKey = null; refresh(true)`), so "Needs your answer" counts may rise.
4. Strip: **"Took back the rule for {credit}. {n} waiting books are checked again."** (n = 1: "1 waiting book is checked again."; n = 0: "Took back the rule for {credit}. The app asks about this name the next time it meets it." This last sentence is question 1's default.)
5. Focus: the next rule's Take back, else the previous one's, else Find author, else the summary.

## 5. Changes Ender must make

1. A read route for the learned rules in force: credit as seen, kind, target, source, saved date, the book title it was first seen on (the rule's `question`), rule id. Wire the existing `/api/author-rule/retract` to the Take back button.
2. Save and Approve answers carry the book's new row status; Save also carries the planner's path (or the page reuses the matching preview).
3. The strip's "left this list" line, "Show it", and the "Updating the list…" suffix.
4. The m:ss clock on every pending face of 2.1, using `ladderNote`.
5. The block lines and fix buttons of section 3, with `aria-describedby`; Ender's own fix removes the false panel lock.
6. Remove the six names inputs from the candidate panel, add the names block and Edit names, relabel "Edit metadata" per section 1. The Files view panel is untouched.
7. Every new control has its tooltip from this spec: Edit names (panel), Restore title, Clear series, Clear number, Discard panel edits, Show it, Find author, the source link, Take back, Take back rule, Keep rule, the summary.

## 6. Checks for Futaba (committed build, seeded fixture, nothing on Z:)

1. Row box, slow answer (stub, 8 s): the line under Save reads the clock and the ladder sentence at 3 s; the face is "Saving…"; the DOM shows no moment longer than 2 s with the same text from press to result.
2. Save result: strip text matches 2.2 exactly; a stub list answer that omits the book gives the 2.3 strip in the same render, and Show it lists and selects the book.
3. Each cause row of section 3: the sentence is in the DOM as visible text (not only `title`), the fix button works in one click, and the blocked button works at once.
4. A saved edit with the editor closed on a "Same author?" row: Approve is not blocked unless a panel draft exists.
5. The candidate panel has no input named title, author, series, number, universe or anthology; Save preview metadata saves only the rest; the Files-view panel is unchanged.
6. Author rules: summary count equals the list; Find author filters; Take back needs the confirmation; after it the count drops, the line is gone, no file changed; a stubbed "already replaced" failure shows 4.3.
7. Measured rects: no two new elements overlap in any state; buttons at least 96 x 32; inputs 32 high; the list box scrolls inside its own 320 px.

## 7. Offers (not in this release)

1. List Sergei's own rule answers ("Same author?", the English-spelling question) and the seeds in the same list, so a wrong answer of his can be taken back too.
2. A pointer on a book row ("Author from an online match: Take back") so a wrong folder leads straight to its rule.
