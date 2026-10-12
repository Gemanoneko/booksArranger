# Books Arranger: metadata disclosure target correction

Date: 2026-10-12. Judy narrow addendum to `BooksArranger_MetadataOutput_UX_2026-10-12.md`. EXTEND the existing metadata inspector disclosures only. No label, current-output selection, button, color, font, encoding, or product behavior change.

## Evidence and problem

The owned private candidate geometry run reports `Small target All source tags` at the 1440px stage. The candidate uses the established 15px/1.5 text baseline; metadata inspector summaries currently have focus styling but no minimum target height or vertical padding. The report exited before adding any completed viewport measurements (`viewports: []`), so it does not establish the exact observed height or a passing 700px result. Preserve this failed evidence; do not call it a completed geometry pass.

## Exact correction

Apply the same target treatment to every native disclosure summary inside the existing metadata inspector (`#metadata-inspector summary`), covering All source tags, Different values across source tracks, Other source artwork, and Source folders:

- Minimum border-box height: **32 CSS px**.
- Vertical padding: **4 CSS px** above and below; horizontal padding: **0**.
- Pointer cursor on the summary.
- Preserve the native list-item disclosure marker, keyboard toggle behavior, existing visible focus outline and tooltip/help associations. Do not change the summary to flex or replace its native arrow.

Keep the target in normal document flow. No absolute positioning, invisible overlapping hit area, fixed-height clipping, or overlay. Long summary text may wrap and increase the height beyond 32px. Do not pad the entire details container: collapsed content must remain collapsed and expanded content keeps its current spacing.

Reuse the existing font and dark theme tokens. No color or full-path-wrapping adjustment is needed for this failure. Existing manual-review and Automatic result summary rules remain unchanged. The original metadata-output spec's labels and verified artifact semantics remain unchanged.

Design basis: WCAG 2.2 minimum 24 by 24px targets; 32px is the existing comfortable desktop disclosure/button baseline. Fitts's Law supports increasing this undersized existing target without introducing a larger toolbar or new interaction.

## Required verification

Ender updates the isolated candidate CSS only, creates fresh pinned source/contract receipts, and reruns the owned geometry check at **1440 and 700 CSS px**. Record each visible inspector summary and output-folder button's actual rectangle; assert width and height at least 24px and nonoverlap. Verify the new summary minimum height is 32px, native markers are visible, keyboard focus remains visible, and expanded/collapsed content does not cover the adjacent controls. Preserve long full-path wrapping and no page-wide horizontal overflow. Keep browser network interception, owned process closure and finite 600000ms deadline unchanged.

Futaba receives the newly pinned candidate and repeats the layout check; earlier Python functional results may be explicitly reused when unchanged, but the failed geometry invocation cannot count as passed. This document specifies the correction, not an observed post-fix pass. No live browser, app, source library, code file or scratch output was changed by Judy.

Sully commits/pushes this addendum before an implementation brief cites it. Ender owns the CSS change; Futaba owns verification; Senua reviews the final changed candidate.
