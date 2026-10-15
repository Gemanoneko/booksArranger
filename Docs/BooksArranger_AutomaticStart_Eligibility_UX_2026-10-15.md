# Books Arranger — automatic Start eligibility

Date: 2026-10-15. Owner: Judy. Model tier: Sonnet-equivalent, inherited. Small correction to the existing browser automatic-processing controls. Sully must commit and push this exact spec before Ender implements it.

## Problem and scope

The v0.15.0 screenshot shows an enabled **Start automatic processing**, **Automatic processing: Needs attention**, zero active researchers and a catalog-request failure. These facts do not prove conversion has stopped. The current status capability omits the audiobook-worker and discovery conflicts that the Start endpoint already rejects. The enabled button therefore advertises an action the server cannot accept.

Keep the existing concurrency rules. Correct the eligibility and its explanation; do not pause, stop, retry or start work merely to make Start available. No new scheduler, control, dialog, theme, retention rule, conversion policy or automatic restart. Preserve source files, recovery and live work. Viewing and inspection controls retain their existing eligibility.

Context: BooksArranger_Brief.md; BooksArranger_StandingRules_2026-10-11.md; BooksArranger_AutomaticProcessing_UX_2026-10-10.md; BooksArranger_DesktopRelease_UX_2026-10-13.md. Existing consumers: automatic_processing.py status/start, web_server.py automatic-start route, web/app.js controls/click handling, web/index.html automatic help. Ender owns technical feasibility, authoritative snapshot and race handling; report contradictory backend semantics before implementation.

## One authoritative eligibility

The server must supply whether Start is currently available and its applicable reason using the same gates as the Start operation. This includes existing automatic lifecycle/closing/failure-checkpoint gates, the existing discovery conflict, and audiobook worker **Running** or **Pausing**. The browser must not independently infer permission from zero researchers or the automatic lifecycle label. Revalidate on the server when clicked: a previously available button does not guarantee acceptance after another state changes.

Continue disabling submissions for existing disconnected, ended, pending-request and draft-protection conditions. No new permission to overlap discovery and conversion. Do not disable Stop automatic processing or audiobook Pause/Resume merely because Start is unavailable; retain their own authoritative eligibility.

## Exact existing-control presentation

Keep **Start automatic processing** as the button label and existing primary styling. Use the native disabled state while ineligible. In the existing help area immediately below the automatic buttons, show a separate short, wrapping eligibility sentence whenever a known conflict disables Start. It must be visible text, not only a tooltip: native disabled buttons cannot reliably receive keyboard focus.

| Authoritative condition | Visible eligibility explanation and matching button tooltip |
| --- | --- |
| Audiobook worker Running | **Audiobook conversion is running. Pause audiobook jobs before starting automatic processing.** |
| Audiobook worker Pausing | **Audiobook jobs are pausing. Wait for them to pause before starting automatic processing.** |
| Independent discovery conflict | **Discovery is in progress. Wait for it to stop before starting automatic processing.** |
| Automatic run Running | **Automatic processing is already running.** |
| Automatic run Stopping | **Automatic processing is stopping. Wait for it to finish stopping.** |
| Existing failure checkpoint could not be saved | **Automatic processing cannot restart because its failure record could not be saved.** |
| Server closing or stopped | **The local server is stopping or stopped. Start is unavailable.** |
| Connection/status cannot currently establish eligibility | **Start availability is unknown. Waiting for the local server.** |

Use the server's applicable reason; show one primary explanation rather than stacking speculative blockers. Existing connection notice remains the source of connection feedback and must not be duplicated verbatim. A brief in-flight Start retains the established **Starting automatic processing…** feedback and duplicate-submission protection. Preserve existing draft-protection explanation where applicable; do not mislabel it a worker conflict.

When Start is available, clear the obsolete blocking sentence and restore the established normal/resume tooltip and static discovery/research/conversion help. Retain the existing tooltip/help sentence about uncertain books staying held. Append this concise static clarification to that help: **Existing audiobook jobs must be paused before starting automatic discovery.** This explains the existing constraint without prescribing an interruption during productive conversion. Do not automatically activate Pause or move keyboard focus to it.

Associate the visible explanation and static help with Start through its accessible description. The explanation is readable in normal document order even when the button is skipped by Tab. Keep meaningful explanation changes in the existing polite status convention; announce once when a reason changes, not on every poll. Do not reconstruct buttons or steal focus during refreshes.

## Independent status and rejected-click feedback

Keep **Automatic processing: Needs attention** when it is the acknowledged automatic state, even if the audiobook worker is running. Preserve the separate actual conversion title/phase and queue counters in Audiobook jobs. Do not call the whole application stopped because research stopped; do not call automatic research Running because a previously queued conversion is active. No invented zeros or historical failure cause.

If Start becomes blocked between rendering and submission, show the matching plain-language reason above, refresh eligibility, leave real conversion running and keep the actual automatic lifecycle unchanged. Do not display **Starting** or **Running** after a rejection. A catalog-fetch failure stays separate from both the eligibility explanation and the original automatic failure. A complete successful refresh clears the corresponding stale connection/catalog feedback according to the existing connection contract; unrelated failure evidence remains visible. Never expose database implementation terminology as the user-facing explanation.

## Layout and acceptance

Use existing dark-theme text/help tokens, sizes, button dimensions and focus style; introduce no colors or decoration. Supported light rendering uses the same established tokens. Text remains at least 4.5:1 contrast, relevant component/focus boundaries at least 3:1; existing targets remain at least 24 by 24 CSS pixels. Help wraps in normal flow without a fixed height or overlay.

Futaba checks available, worker Running, worker Pausing, independent discovery, automatic Running/Stopping, failed checkpoint, disconnected, unavailable telemetry and rejection-after-state-change. In the reported combination, Start is disabled with the worker reason, automatic Needs attention remains truthful, and the separate running conversion remains visible. When that conflict ends, eligibility follows the server; no click or restart occurs automatically.

Verify keyboard reading order and accessible description with Start disabled, mouse tooltip when supported, normal and 200% zoom, 1440px and 700px widths plus narrow reflow, long book titles/Russian content, existing dark and supported light behavior. Measure actual button/help/status rectangles in relevant states; no overlapping hit areas, clipped explanation or hidden focus. No live conversion pause or library deletion is authorized by this UX acceptance checklist; use isolated fixtures for state coverage.

Design basis: NN/g visibility of system status and error prevention; WCAG 2.2 AA perceivable explanations/keyboard operation; Jakob's Law native disabled controls; existing Fitts's Law target sizes. Doc-only work. No code, browser actions, runtime changes, checks, cleanup, Git or shared configuration writes performed. Owned disposable output: none.
