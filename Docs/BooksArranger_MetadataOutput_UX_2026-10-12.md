# Books Arranger: current audiobook metadata

Date: 2026-10-12. Judy UX specification. EXTEND the existing Book metadata details panel; correct the distinction between a reviewed destination and the current verified created audiobook. This is a small correction to an existing daily-use feature. No new buttons, output history browser, encoding policy, source changes, or manual-file adoption.

## Problem and evidence

The supplied screenshots show three Eye of God M4B files in Explorer, including `Sigma Force - 9 - The Eye of God - Rollins James - Chapters v2.m4b`. Book metadata instead presents the original base filename as “Output destination” under “Automatic result”. Ender's supplied investigation identifies a successful approved chapter-repair publication recorded separately from the original AudioJobs output. Explorer modification time or a similar filename does not establish that a file is this candidate's current verified output.

This is a visibility-of-system-status and error-prevention problem (NN/g): a proposed destination appears to describe the actual current file. Preserve the reviewed preview as review evidence while naming the current created artifact precisely. Recognition over recall requires the complete filename and path, not an instruction to infer which variant is correct.

## Exact presentation

Keep the existing Book metadata heading and source-candidate location. Label the top proposed-path paragraph **Reviewed destination preview:** followed by its saved path. Keep its existing preview explanation; that explanation belongs only to this preview. Do not present this path as the file whose tags or artwork are being inspected.

In the existing Automatic result definition list:

- Rename **Output destination** to **Reviewed destination**, retaining its reviewed/planned destination value and existing unavailable-state value.
- Insert **Current audiobook** immediately after Reviewed destination. Show the full path returned by the backend's verified current publication resolver. For Eye of God, when that resolver certifies the chapter-repair publication, this is the full `...Chapters v2.m4b` path. This fact is read-only.
- Before any verified publication exists, show **No verified audiobook created yet**. For a recorded output that cannot currently be verified, show **Current audiobook unavailable** plus the backend's concrete safe failure explanation. Do not use a planned path or an arbitrary sibling file to fill this value.

The current created inspector section heading is **Current audiobook metadata**. Its path, embedded tags, duration, artwork and existing **Open output folder** action must all refer to the same resolved verified artifact. Preserve ordinary created-output status wording. For a verified chapter-repair derivative, use **Verified chapter update** as the short section status; this indicates why the filename differs without exposing journal internals.

A saved snapshot or unavailable output remains explicitly labelled as a saved/unavailable record, never “Current audiobook metadata” with an implied fresh verification. Preserve source metadata and approved preview sections independently. Do not relabel approved canonical metadata as tags read from a file.

Keep the existing output-folder tooltip: **Open the folder containing this created audiobook.** Its contextual accessible name includes the resolved actual path. The folder endpoint must resolve the same backend-selected artifact; a correct visible filename with an original-job-only folder action is an incomplete correction. No new clickable path, shell launch, or additional button is required.

## Refresh and uncertainty

Existing automatic polling updates the read-only current-output fact and inspector when the verified current publication changes. Include publication identity/state in the existing inspector refresh key as needed; do not require a selection change or browser reload. Do not reset drafts, move focus, scroll, open Explorer, or interrupt a user's active inspector interaction during polling. Preserve the existing deferral while focus is inside the inspector and apply the update when it is safe.

Backend selection and verification are Ender's responsibility. Select a trusted successful publication linked to the same candidate/current revision, including the approved chapter-repair result where valid. Do not rank arbitrary files by modification time or filename suffix. If a later recorded derivative fails verification, report that failure explicitly rather than silently calling an older output the current derivative. QA must distinguish that failure from a candidate with no publication.

## Layout and accessibility

Reuse the existing definition-list, `.path`, inspector-section, typography and theme tokens. Full paths wrap at available width (`overflow-wrap: anywhere`), remain selectable, and are not ellipsized. At the existing narrow breakpoint the label and path stack in normal flow. Preserve section spacing and cover dimensions from the 2026-10-09 ViewFolder specification. No color-only distinction between preview and actual output.

No control geometry change is specified. Existing Open output folder and disclosures retain visible keyboard focus, at least 24 by 24 CSS-pixel targets, and the established comfortable 32px minimum button height. Paths and status text must not overlay controls, artwork, or the source metadata section. The app currently explicitly uses a dark color scheme; retain it even with Windows light appearance. Verify existing text contrast (4.5:1 minimum) and focus visibility under Windows dark and light settings without introducing an unimplemented light theme.

## QA acceptance

Use isolated fixtures and mocked folder opening; no real desktop interaction or audio playback. Check an ordinary completed output, a verified chapter-repair derivative differing from the original job filename, an unverified/missing derivative, a saved snapshot, and a candidate with no created output. In the derivative fixture, visible Current audiobook, inspector path/tags/artwork, and folder resolver all identify the same latest verified publication; Reviewed destination still shows the original review evidence.

Check a publication update while the same candidate is selected, with and without focus inside the inspector, and with a dirty manual draft. At 1440 and 700 CSS pixels measure output-folder button/disclosure rectangles and verify targets meet the minimum and do not overlap, long filenames wrap, and no new page-wide horizontal overflow appears. These are required future checks, not measured results from this spec. No browser session or scratch output was created by Judy.

Commit and push this exact spec through Sully before Ender's implementation brief cites it. Implementation and release verification remain owned by Ender, Futaba and Senua.
