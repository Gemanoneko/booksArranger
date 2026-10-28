# Books Arranger: series in the author question

Judy, 2026-10-28. EXTEND v0.22.3 (`8057ab4`); preserve the existing row, draft and approval flow. Spec only; no app launched, no screen geometry measured. Dimensions below are implementation targets for Futaba, not measured results.

## Request and boundary

Sergei wants to enter a book's series **in the same row where he answers the author question**. His supplied reference identifies «Мистер Вечный Канун. Уэлихолн» as book 1 of «Мистер Вечный Канун», credited to Олег Яковлев and Владимир Торин.

Expose the existing Title, Series and Number editing controls directly on author-decision rows (`Author unclear`, `Same author?`, and missing-author questions). No separate dialog, second editor, new Save step, automatic title splitting, author-rule change or new series inference. This spec does not decide provider reachability or matching policy.

## Row layout and one draft

Order in the existing Review status cell:

1. Existing status and reason.
2. Existing Author control, unchanged: candidate radios / Same author? choices / author text, including the existing **Other** text field.
3. **Title**, on its own full-width line.
4. **Series** and **Number**, in one wrapping grid row.
5. Existing Place / Entered by you facts when applicable, then the single **Goes to** line and existing feedback/block reason.

The existing right-hand action column stays put: **Approve**, **Edit names**, **View metadata**, **Source folders**. There is one Approve for the author, title and series values together. The default author question does not acquire Save/Discard buttons; full Edit names retains its existing commands for broader corrections.

- Reuse `.ask-field`, `.ask-grid` and current names-input styling. Fields are at least 32 CSS px high, labels above, 8 px between Series and Number, 6 px before the additional field block. Title and Series may use the cell width up to the existing 420 px input maximum. Number uses the existing input style and existing number syntax, rather than a spinner or integer-only control.
- At **408 CSS px of available cell width**, the two existing 200 px minimum columns plus 8 px gap fit. Below that, stack Series then Number. Below a 200 px cell, shrink the minimum to the available width; inputs must not force horizontal scrolling. Long names, errors and paths wrap. No absolute positioning or overlays.
- **Title must be editable here too:** the supplied source title contains both series and book title. Showing only Series would leave Sergei unable to remove that prefix without changing interfaces. Reuse the one existing title draft/control, never a duplicate. Show its existing proposed title unchanged; never strip or rewrite it when Series is typed.
- The example can be entered as Title `Уэлихолн`, Series `Мистер Вечный Канун`, Number `1`, with the existing Other author value retained. This is an example of Sergei's entry, not a hard-coded correction or parser rule.
- Opening Edit names must reuse these exact Title/Series/Number values and controls, add its existing Universe/Collection/remembered-values facilities, and never show a second copy. Closing the expanded editor must not clear the inline author-question draft. An explicit existing Discard retains its documented meaning and may discard unsaved corrections; no implicit discard on refresh, collapse or radio change.
- Prefill known current values from the row's existing metadata/ask facts. Do not overwrite an edited value when later data arrives. The list and author controls must not wait for a separate full-editor read per row. Suggestions reuse an already available series list; absence of suggestions never prevents typing a new series.

## Fields, validation and preview

| Control | Visible label | Tooltip / accessible description |
|---|---|---|
| Title | Title | The title this book is filed under. |
| Series | Series; placeholder `None` | The series this book belongs to. Leave empty for a standalone book. |
| Number | Number | The book's number in its series. Needed when a series is set. |
| Approve | Approve | Approve this book with the author, title, series and number shown. Queued work waits for Start. Ctrl+Enter in a field does the same. |

- Accessible field names are `Title: {title clue}`, `Series: {title clue}` and `Number: {title clue}`. Keep visible labels; placeholder is not the label.
- **Series and Number stay paired.** Both empty is valid for a standalone book. A Series without Number blocks Approve with the existing visible sentence: `Type the number in the series, or clear the series.` Number without Series: `Type the series name, or clear the number.` Empty Title: `Type a title first.` Reuse current number validation and its error wording; no new numeric policy.
- Incomplete or invalid pair: retain all text and the author choice. Reuse the existing visible block-reason line and `aria-disabled` approval treatment, with the same reason in its tooltip; associate the line with the affected field(s) and Approve. A blocking line is text as well as color.
- **Untouched blank fields are not answers.** Merely displaying empty Series/Number must not send an explicit clearing value, suppress a later series question or change existing names. User edits and intentional clearing use the existing draft semantics. Existing nonempty Series/Number are displayed, retained and included as appropriate.
- Existing Other text, both credited names, author radio selection and Title remain intact while Series/Number change. Selecting another author never resets the series draft. Adding a series must not implicitly choose a different author.
- Preview and Approve carry the **same combined draft**, including the selected/Other author and edited title/series/number. Display the backend planner's path verbatim; do not construct a filename in the page. For a valid series pair, the preview includes its series folder and numbered filename according to existing organization rules.
- Keep the existing preview schedule: 500 ms after typing stops, on blur, and on Enter; reject stale responses. Never replace a newer draft or field focus with a delayed result. Preserve the existing unresolved-English empty-destination/reason behavior and author-language requirement.
- These entries apply only to **this book**. No set-wide release, alias or correction to sibling books. Approve records/queues without starting or resuming a stopped run or conversion queue. If another answer is still needed, retain all values and show that question in this same row. Nothing starts without the existing authorized Start action.

## Keyboard, focus and display

- DOM/Tab order follows the visual order: existing Author group/Other, Title, Series, Number, then existing row actions. Native arrow keys stay within a radio group. Clicks, Space and typing in controls must not select the whole row.
- Enter refreshes the preview only. Ctrl+Enter invokes the same guarded Approve; if blocked, keep focus and show the reason. No approval on blur. No new shortcut or automatic focus movement is introduced.
- Background row refresh, author selection and opening/collapsing Edit names retain the active input, caret, radio state and values. Grow the row/list area naturally; an inline form must not be clipped by the list's fixed-height mode. Focus indicators and the right-hand actions must never overlap or cover controls.
- Use only current `--field`, `--text`, `--muted`, `--border`, `--focus`, `--warning` and disabled tokens. Current app is explicitly dark (`color-scheme: dark`), including under a light Windows theme; this change does not add a light theme. Preserve its 3 px visible focus outline. Verify normal text contrast at least 4.5:1 and control/focus contrast at least 3:1 on ordinary, hover and selected rows. No new colors, animation or font sizes.

## Litres presentation, if the provider is added

Reuse existing provider/source attribution and evidence links. Show provider name **Litres** in those existing generic surfaces; link to the actual matched source, not a new modal or panel. Reuse generated source-link tooltip conventions (`Open this source on Litres.` only if a new tooltip string is needed). No new provider-specific control is required by this inline-series change. Reachability, matching, failure handling and provider configuration belong to the separate implementation/research brief.

## Focused acceptance for Ender/Futaba

1. Reproduce the supplied two-credit row. Keep `Other = Олег Яковлев, Владимир Торин`, enter Title `Уэлихолн`, Series `Мистер Вечный Канун`, Number `1` without pressing Edit names. One preview and one Approve use all four values; current author normalization remains authoritative. No series/title duplication introduced by the UI.
2. Blank untouched pair preserves existing approval/held behavior. Half-filled pair blocks visibly; completing it refreshes the path and enables the existing action. Clearing an edited pair does not clear Author or Title.
3. Open/collapse full Edit names, change author choice, and apply an asynchronous row refresh: one copy of each field, all draft text/caret intact. Confirm ordinary approval preserves the book-only scope and stopped state.
4. Check ordinary/selected/hover rows, validation/loading/queued states and narrow/wide cells: fields and actions do not overlap; all controls remain keyboard-reachable with visible focus. Verify with the current dark app under light and dark OS appearance. No claim of measured hit rectangles until Futaba has the implemented artifact.

Design basis: Jakob's Law (reuse the existing names editor), proximity (series pair beside the author decision), recognition over recall (visible fields rather than another action), error prevention (paired validation and literal path), WCAG 2.2 AA keyboard/focus/contrast. Local reference: `Team/Research/UX_AppBestPractices.md`.
