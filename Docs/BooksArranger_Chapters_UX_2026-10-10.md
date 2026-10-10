# Books Arranger — preserve source-track navigation

Date: 2026-10-10. EXTEND of the existing metadata and track review. This addendum supersedes only the chapter-option default, eligibility and copy in `BooksArranger_MetadataMerge_UX_2026-10-09.md`. All source review, ordering, metadata, approval, queue and output safety requirements remain in force.

## Actual problem

Sergei verified that the merged *The Eye of God* plays on his iPhone, but its original MP3 track navigation is absent. The pilot deliberately omitted markers because the original specification required proof that each file represented a publisher chapter. That requirement discarded useful navigation even though original file boundaries were known. This is a functional defect in the requested workflow, rather than a theme preference.

One M4B file can still offer chapter navigation. Retaining an original track boundary as a chapter marker does not certify that it matches a literary chapter or publisher track list. The app must make that distinction without requiring a new panel or extra confirmation.

## Existing control and defaults

Reuse the native `add-chapters` checkbox in track review, its associated `chapters-control` label and `chapters-help` paragraph. Label: **Keep source tracks as chapters**. Tooltip: **Keep a chapter marker at the start of each included audio file, in the reviewed playback order.** Help: **Preserves source track names when available. Unnamed tracks use Track 01, Track 02, and so on. These markers may differ from the book's written chapters.**

For a new multi-MP3 review with no saved chapter choice, the option defaults checked when source boundaries can be established. It is visible without requiring proof that one source file equals one publisher chapter. Source selection and playback-order confirmations are still required before creation. A default is a proposed draft value until that review is saved; opening or refreshing a candidate must not silently save it.

A saved chapter choice, including explicit false, remains authoritative. Do not convert an old false into true by treating it as a missing value. Existing approved reviews, queued/running jobs and completed output records are immutable under this default change. Correcting an old output requires a new explicit review revision/output job; the old artifact remains unchanged. The user can uncheck the option on a new or explicitly revised review.

No new controls, panels, settings matrix, repair button or automatic approval is introduced. Existing one-file inspection and podcast/ebook exclusions remain unchanged. Availability depends on Ender's ability to establish the exact ordered included audio boundaries, rather than a metadata claim about publisher chapters. A disabled or unavailable state identifies a concrete cause, for example **Chapter boundaries unavailable: source durations need checking.** It must not say that missing literary chapter names prevent source-track navigation. Unknown titles alone never disable markers.

## Names and order

Preserve meaningful existing source track titles, their Unicode text and recording language. The English canonical book title rule does not authorize translating or inventing source chapter titles. A genuine descriptive title derived from an existing filename may be used when no embedded title exists; technical filenames or duplicate whole-book titles must not be presented as independently verified chapter names. Ender owns the bounded title selection and validity checks; the review must expose the names actually planned for output.

For absent or unusable titles use **Track 01**, **Track 02**, and so on, numbered in the reviewed included playback order. Use enough zero padding for the included count. This is a navigation label, not a claim about a publisher chapter number. Preserve legitimate repeated descriptive names; do not omit a track because its title repeats. Introductions, disc boundaries, short tracks and zero-numbered original files remain subject to the existing inclusion/order review, never automatic removal.

The ordered source-track table remains the review surface. Make the chosen marker name readable alongside each included track using the existing text area/cell; do not require another modal. Source title evidence remains distinguishable from a generated Track label. Reordering or changing inclusion regenerates fallback positions and invalidates the existing source/order confirmations as before. Timing and codec decisions belong to Ender.

## Summary and saved evidence

In the existing output summary use **Chapter markers: 40 — one per included source track** (with the actual count) when enabled, and **Chapter markers: none** when explicitly disabled. Readiness, job and created-file inspection must reflect the saved job plan and actual validated output, rather than displaying a newly calculated default for a historical job. A generated plan is not described as chapters already written.

The existing source review must distinguish retained descriptive names from generated Track labels. Saved output evidence records the exact ordered marker names and source membership. Existing technical output checks verify marker count, order, names and boundaries against that plan before publication. The actual iPhone test confirms navigation separately; a successful earlier playback test without markers does not certify chapter navigation.

## Design basis and bounded verification

This retains the existing control and placement under Jakob's Law and Hick's Law, makes the output plan recognizable under NN/g recognition over recall, and preserves saved decisions under NN/g user control and error prevention. Keep the current dark theme, spacing, visible focus and minimum 24 by 24 CSS-pixel interactive targets. Longer copy wraps in normal flow; no overlay or new layout region.

Futaba checks new-draft checked default; saved false preserved across reopen/restart; explicit toggle and save; known source titles; unnamed/duplicate book-title fallback; repeated legitimate chapter names; inclusion/reorder; unknown title versus unknown boundary; old completed/queued plan unchanged; truthful summary/created inspector; and keyboard access. At wide and narrow existing review widths, measure that the checkbox label/help and neighboring controls do not overlap. Ender verifies marker timing/media compatibility; Sergei's iPhone verifies that the corrected audiobook exposes navigation. No native user-session interaction is authorized by this spec.

No probes or disposable output were created for this doc-only handoff.
