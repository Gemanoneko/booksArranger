# Books Arranger — approved-book progress

Date: 2026-10-10. Scope: browser Audiobook jobs status area only (web/index.html, web/app.js and existing theme styles), plus the minimal backend progress/count fields required by Ender. No queue, approval, encoding-policy, source-retention-policy, scan, service or unrelated UI changes. Do not interact with or restart a live conversion.

## Placement and appearance

Reuse the existing Audiobook jobs panel. In its existing status line, lead with **[X] converted out of [Y] approved books**; retain queue/paused/error facts alongside it, wrapping naturally. Below that line and above the existing Pause/Resume toolbar, show **Current book: [reviewed title]**, a short phase label and one progress bar. Reuse the current title/stage information rather than repeating it elsewhere in the panel. No new buttons, panels, tabs, confirmations or layout redesign.

The bar is full available panel width, 8 CSS pixels high, with 8 CSS pixels of vertical spacing. Inherit current body text size, font, dark-theme panel/text/accent roles and focus styles. Keep text readable at normal desktop width and 700 CSS pixels; long titles wrap without covering controls. Fill/track boundaries need at least 3:1 nontext contrast, normal text 4.5:1. No saturated new palette or decorative animation.

## Approved and converted counts

Y is the authoritative number of distinct audiobook candidate IDs with a revision-valid fully approved book: metadata identity, selected cover, exact source membership/coverage/order/hash and current member context. Include approved-ready unqueued, queued, running and valid completed books. Mere discovery, selected rows, partial review and stale approvals do not count. Y updates as additional books receive valid approval; finding an unapproved book alone does not change it. No frozen initial batch denominator.

X counts each distinct approved candidate once after a matching frozen revision has a verified published output and every cleanup required by that job has succeeded. Cleanup-enabled jobs must finish original removal, verified temporary recovery/working-file removal and applicable empty-source-folder cleanup before X increases. Verification alone or source removal with temporary cleanup still pending is insufficient. A historical job with cleanup disabled counts after verified publication: do not enroll it in new deletion merely to satisfy this metric. Existing source-retention details remain authoritative. Retries, restore artifacts and repeated status polls never increment X twice. Both values come from one coherent backend snapshot, with X never exceeding Y.

Exact count strings: **[X] converted out of [Y] approved books**; empty approved set: **0 converted out of 0 approved books**. Invalid/missing count data: **Approved book progress unavailable**; do not fabricate zeros. With approved books but no active job, show **No book currently processing** and hide the current-book bar. An idle queue is not **All approved books converted** while X is below Y.

## Current-book phase and bar semantics

| Actual phase | Exact visible label | Bar |
| --- | --- | --- |
| Source preparation/checks without a measured denominator | Checking source files | Indeterminate |
| Encoding with valid measured progress | Converting audiobook — [P]% | Determinate for encoding only |
| Encoding with absent/invalid measurements | Converting audiobook | Indeterminate |
| Encoder reaches duration while still finishing | Finalizing conversion | Indeterminate until next confirmed phase |
| Output validation | Verifying audiobook | Indeterminate unless Ender exposes exact validated measured progress |
| Exact original removal | Removing originals — [removed] of [total] | Determinate only from confirmed removal count |
| Verified temporary-file purge | Removing temporary recovery and working files | Indeterminate unless a trustworthy exact denominator exists |
| Applicable empty source-folder cleanup | Removing empty source folders | Indeterminate unless a trustworthy exact denominator exists |
| All required work succeeds | Complete | 100%, only for that confirmed completed book |
| Safe pause requested | Pausing — [current phase] | Keep confirmed value; stop movement only when pause is acknowledged |
| Pause acknowledged | Paused — [current phase] | Keep last confirmed value; no ambient animation |
| Any blocked phase | Needs attention — [specific reason] | Keep confirmed value; no ambient animation and no success presentation |

The bar is explicitly phase-scoped; never label its value as a percentage of the whole workflow. Do not weight stages, estimate elapsed-time completion or show a general 100% book-complete value before required cleanup. Reset phase measurement when the backend confirms a new phase; reset current-book state when its job identity changes. If a measured stage finishes before the next state arrives, show the next pending/finalizing label with an indeterminate bar rather than carrying a full bar as whole-book success. Do not reuse the previous book's percentage. A restarted interrupted conversion reports that current attempt's actual progress; completed outputs are not recreated.

Ender's feasibility receipt: current API exposes title/stage/completed/queued/failed/cleanup_active; cleanup exposes removed/total. Encoding currently has no percent telemetry. Ender can add bounded FFmpeg progress using out_time_us divided by the protected exact decoded duration, throttled approximately once per second. Verification may use consumed PCM frames against exact expected frames if implemented reliably; otherwise its bar remains indeterminate. Temporary purge and folder cleanup remain indeterminate through successful completion. Numeric measurements must be tied to the current job/phase and validated as finite and bounded.

## Accessibility and verification

Use native progress semantics with accessible name **Current book progress** and phase-specific value text. An indeterminate bar has no fabricated numeric aria value. Put phase/counter changes in the existing polite status mechanism; do not announce every one-second percentage tick or move keyboard focus. Text always communicates status independently of bar color. Honor reduced-motion preferences for indeterminate movement.

Verify 1440 and 700 CSS-pixel widths, long titles, 0 approvals, approved-ready unqueued additions, unapproved discoveries, changed/stale approval, phase transitions, encoding telemetry absence, partial cleanup, cleanup failure, pause/resume, restart and duplicate completed records. Measure group/bar/status/button rectangles for overlap; retain existing control hit areas. Assert X advances only after the applicable success receipt; Y changes only for valid approval membership. Historical cleanup-disabled jobs remain countable without retroactive deletion. No probes or live app operations were performed for this spec.

Design basis: NN/g visibility of system status and plain-language error recovery, WCAG status/progress semantics, and reuse of established desktop controls. Sully must commit and push this spec before Ender implements it.

## Converted status filter addendum

User-requested addition: in the existing **Status** dropdown for **Book candidates**, add one option with visible label **Converted** and stable value **converted**, using the current native option styling. Place it immediately after **Audiobook created** and before **Output needs attention**. Retain the existing options; no new control or layout region.

**Converted** returns the same distinct candidate set eligible for X in the progress counter: revision-valid approved book, matching verified published output, and every cleanup required by its frozen job policy completed. Do not include encoding/verification in progress, successful output with required cleanup pending or blocked, stale approvals, or duplicate jobs/artifacts. Historical verified cleanup-disabled books remain eligible without retroactive deletion. **Audiobook created** retains its existing output-created semantics; the new option expressly includes applicable cleanup success.

Selecting **Converted** follows the existing filter behavior: preserve the current path search, reset pagination to its first page, and use existing search/clear-filter and empty-state handling. Display the label **Converted** in the existing page/filter summary. The backend predicate and counter must share authoritative completion semantics so, with no path search, the unpaginated Converted candidate total equals X for the same snapshot. Verify pending cleanup is excluded, final cleanup admits the candidate once, retained-source historical completion remains included, and changed approval is excluded. No file-view filter, scan control, service restart or queue mutation is part of this UI addition. Sully must commit and push this addendum before implementation.
