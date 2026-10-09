# Books Arranger: anthology routing and author/reader review

Date: 2026-10-09. Scope: a minimal addition to the read-only local-web and Tk review interfaces. No library writes, external matching, scan restart, service restart, visual redesign or automatic identity verification is part of this spec.

## User rules

- An audiobook containing short stories by different authors belongs under `Z:\Audiobooks\Сборники`.
- A series of those collections belongs under `Z:\Audiobooks\Сборники\Series`, for example `Сборники\Пять Вечеров`.
- This anthology routing takes precedence over generic multi-author series routing. Novels, single-author collections, ebooks and podcasts retain their existing rules.
- The future audiobook Artist tag credits the book's author(s), not its reader. Preserve the reader in comments alongside existing comments. Current source tags remain untouched.

## Minimal controls and copy

Retain the current form, theme and scan controls. Introduce the following only in an audiobook review:

| Field | Label | Tooltip and accessible help |
|---|---|---|
| `anthology` checkbox | Short-story collection by multiple authors | Place this audiobook in Сборники, or Сборники/Series when a series is entered. |
| `canonical_author` text | Author for Artist tag | Enter the verified author credit, such as Stephen King. Do not enter the reader here. |
| `narrator` text | Reader / narrator (for comments) | Preserve the verified reader in comments alongside existing comments. |

`author` remains **Author folder name (Surname Firstname)**. Do not automatically reverse or split this string, or copy embedded Artist into either author field. A saved, explicitly reviewed author identity can supply the credit when `canonical_author` is blank, preserving compatibility with earlier reviews; a nonempty `canonical_author` takes precedence. For anthologies the folder component is not used; disable it with the explanatory text **Anthologies use the Сборники folder.** Preserve its saved value so clearing the checkbox restores the ordinary routing review. Anthology filenames retain the existing naming convention, using the reviewed author credit; no additional author directory is introduced.

Place the Artist and reader fields immediately after the existing author folder field. Place the anthology checkbox next to the existing multi-author-series checkbox before Save. Use the existing input styles and label patterns. Associate help with controls programmatically; tooltip text must also be available on keyboard focus. Wrap checkbox labels; the whole label activates the checkbox.

When anthology is checked, retain the saved `multi_author` value but disable that control and show **Anthology series stay inside Сборники.** Clearing anthology restores it. A series name is optional: empty means a standalone collection; a series name selects the nested collection destination. Do not infer anthology status simply from multiple names or location inside Сборники.

Ebooks continue to use their current author-folder and multi-author-series controls. Hide audiobook-only fields for ebooks; podcast, companion, unreadable and missing-file reviews stay unavailable as they are now. Backend validation must independently enforce these library boundaries.

## Evidence and future tag preview

For audiobook inventory rows change the existing author column label to **Existing author / artist clue** (other library labels may stay unchanged). Keep the existing explanation that embedded Artist does not establish author identity. In selected-file details use **Existing Artist (role unverified)** for an extracted Artist value. Do not relabel the value as the verified author or automatically copy it into Author for Artist tag.

Add a compact text section to the selected audiobook details, outside the editable form: **Future tag preview — source tags unchanged**. Its rows are:

- **Artist:** the explicitly saved `canonical_author`, or saved reviewed `author` identity if the separate credit is blank; otherwise **Needs author review**. When the fallback is used, add **Uses reviewed author folder credit.** Do not hide this distinction by copying it into the credit input.
- **Reader / narrator:** the explicitly saved `narrator`; otherwise **Not reviewed**.
- **Comments:** the existing comments with the reviewed reader appended as a separate labelled `Narrator: ...` entry when present.

Preserve all existing comment values and reader clues in the raw tag snapshot. A missing reviewed reader is not permission to remove a source reader credit. Saving or repeatedly viewing a review must not accumulate duplicate narrator entries. If there are several existing comment fields, preserve their text and distinguish them in the preview rather than flattening away values. Do not invent 'Various authors' or a narrator identity. For a collection the Artist entry uses the explicitly reviewed credit; an unknown credit remains Needs author review even if a folder preview is otherwise available.

These additions preview a later metadata-writing milestone; they do not claim that source Artist or Comments changed. Retain **Save preview metadata** and the existing source-files-unchanged success message. Do not change current identity/language/path validation beyond excluding the unused author folder from anthology routing. Anthologies still need a reviewed title and author credit for their filename; absent credit shows Needs review, without a placeholder author. Existing reviews default to `anthology=false` and blank new role fields. Keep unsaved review values intact during scan polling, matching the current form behavior.

## Layout and verification

At a 700 CSS-pixel browser panel, use the current responsive form flow, wrapping labels without clipping. If two existing columns cannot fit complete controls and help, stack the review fields into one column. Keep Save below every field in normal document flow. Tk can grow vertically with the additional rows; keep its Save row after both checkboxes, and wrap help within the dialog. Do not reuse a fixed grid row occupied by an input.

Keep native keyboard interaction: Tab reaches each enabled control in visual order, Space toggles the checkbox, and keyboard focus remains visible. Disabled controls explain their state in adjacent text. Preserve current input/button hit areas and contrast; the checkbox label hit area must meet the studio's 24 CSS-pixel minimum without overlapping neighboring controls.

Implementation verification must cover anthology on/off, series present/absent, multi-author state retained/restored, ebook and podcast exclusions, and old saved reviews with the new fields absent. Check web and Tk saved-review reload, comments preservation, two different author/folder strings, reader-only Artist evidence, repeated saves and active scan polling.

Hit areas and wrapping require measured control rectangles at 700 CSS pixels and the normal desktop width, with each checkbox state. No live-window or browser launch was performed for this spec; measured hit-area results belong to implementation verification. Use the authorized isolated headless route when available; do not interact with Sergei's running instance or restart its server.

## Design basis and handoff

The explicit author/reader distinction applies recognition over recall and error prevention (NN/g); contextual disabling keeps invalid routing choices clear. Existing native input patterns apply Jakob's Law. Wrapping and label hit areas apply Fitts's Law and the studio WCAG baseline. Reference: `Team/Research/UX_AppBestPractices.md` and ProcessRules sections on new-control tooltips and overlapping controls.

Sully must commit and push this file before Ender's implementation brief cites it. Ender owns code/schema mapping; Judy owns this spec only. This task created no disposable probes, exports or logs, and changed no source/library files.
