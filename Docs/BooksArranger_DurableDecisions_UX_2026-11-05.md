# Books Arranger: Save and Approve record immediately

Judy · 2026-11-05 · EXTEND the existing 0.25.0 audiobook candidate decisions and save controls. Sergei's new instruction: **Approve or Save cannot be cancelled; when the app cannot do the later work immediately, keep the decision durably and finish safely afterwards.** This supersedes the queued names Save section of [the earlier queue-status spec](BooksArranger_QueueStatus_UX_2026-11-05.md). Ender owns the temporary/durable storage, ordering, recovery and protected application mechanism. This document specifies only what the existing interface says and does. No app, live files, source drive or focus was used.

## Scope and invariant

Apply the same acceptance rule to existing audiobook review decisions: row **Approve**, **Edit names → Save**, **Save preview metadata**, **Save choices**, **Save track review**, and existing equivalent book-local Save/Approve presses. Keep each control's current meaning and validation. A press records the decision for that exact book/revision promptly, even while another book converts, scans or holds cleanup. Conversion, source cleanup, file movement and research still follow their own safety gates; a saved decision is not a completed audiobook. No new control, modal, settings option, bulk action or generic background queue page.

**No decision queue UI:** after a valid press, do not show `Approve queued`, `Save queued`, `Your choices are saved` for a memory-only action, a queued-action **Cancel** for that decision, `n ahead`, or `It runs when {blocker} finishes.` An accepted decision is durable, not a cancellable request waiting for its turn. The existing Cancel controls for genuinely separate operations keep their own behavior.

## Existing row/panel states and exact copy

| State | Existing status/feedback slot | Control behavior |
|---|---|---|
| Ready with valid draft | Existing **Approve** or **Save** label and tooltip. | One press sends the current exact decision. |
| Press sent; durable acceptance not yet confirmed | `Saving decision…` for Approve; `Saving…` for Save. | Keep focus and make repeat presses inert. Do not claim success or show a decision Cancel. A slow or lost reply moves to the reconciliation state below rather than an indefinite spinner. |
| Names Save durably accepted | `Saved names for {book}.` | The saved values and revision appear on row reopening and after restart. **Save** returns to its normal state for later edits. |
| Other Save durably accepted | `Saved {specific values} for {book}.` Use the current specific receipt where one already exists, such as `Choices saved.` or `Track review saved.` | Keep draft and saved values aligned. Do not call conversion complete. |
| Approve durably accepted | `Approval saved for {book}.` | Remove the approval question from active to-do counts only when the recorded decision resolves it. The accepted book's later work appears through the existing job status, not as an unaccepted or cancellable approval. |
| Decision accepted; later work is blocked | `Approval saved for {book}. Audiobook work is on hold: {specific reason}; {supported next step}.` For a Save, say `Changes saved for {book}. {later work and reason}` only when later work is actually expected. | Keep the accepted decision visible. Use only the backend's typed current blocker and supported action. An unrelated book's hold is not this book's reason. |
| Validation fails before durable acceptance | `{Action} not saved: {specific field/check}. {supported fix}`. | Retain the unsaved draft, focus and enabled control for correction. Do not record or display an accepted decision. Protected media/source/destination checks remain active. |
| Response lost; acceptance unknown | `{Action} not confirmed. Checking this book's saved decision…` while the app reconciles from durable state. If it cannot read that state: `{Action} status unavailable. Check this book before trying again.` | Never convert silence into `saved` or `not saved`. Reopening/refreshing must show the authoritative result. A repeat press cannot create two approvals or two saved decisions for the same revision. |

`{Action}` is the visible verb for the pressed control (for example `Approval` or `Names`). Use the app's existing in-row hint, selected-book status, polite announcement and ordinary error line. The button tooltip for a pending press says `Recording this book's decision…`; after success, revert to its normal tooltip. The old queued Cancel button and tooltip must not appear for a Save/Approve decision. No focus movement or page scroll on a background status update. Exact book titles and paths wrap; raw storage or exception details stay in Technical details.

An explicit **Discard** still discards an *unsaved draft* through the existing editor behavior. It is not a Cancel for an already accepted Save or Approve. Any existing explicit action that later changes or withdraws a saved review keeps its own warning and safeguards; this spec adds no new reversal path. A system restart, app update or a different book's long conversion must not erase an accepted decision. On reopen, show the saved values and the real subsequent job/hold state, never a stale `Saving…` or `Approval queued` state.

## Focused acceptance

Private fixtures: press Count Zero's names Save while another book converts; receive a durable receipt promptly, close/restart, and find the saved names with no queued Cancel. Do the same for Approve and the other existing Save controls; later conversion may remain pending or held without undoing approval. Exercise validation refusal, protected conversion hold, lost reply with durable success, lost reply with no acceptance, double press, restart during later work and explicit Discard of an unsaved draft. The UI's saved/approved claims must match durable backend records in every case. Verify decision controls have no waiting-for-other-book or `n ahead` copy, while separate conversion/cleanup work keeps truthful status.

Measure changed row hint, button and adjacent action rectangles at 1280/960/760/600 CSS pixels and 200% zoom in pending, accepted, held and error states: **0 px²** same-plane intersections; all controls remain keyboard operable, focus visible, and text readable in the current dark theme under both Windows appearance preferences. This is a spec, not runtime verification. No disposable output was created. Sully commits this exact file before Ender cites its UI requirements.

## Addendum: Start means Resume for a paused automatic pass

Sergei sees **Automatic processing: Paused** beside **Start automatic processing** and cannot tell whether that button resumes the saved whole workflow. Keep the existing `start-automatic` control, action and position. Match its face, tooltip and nearby instruction to the backend state; no new button or separate resume operation.

| Automatic state | Existing control and nearby copy |
|---|---|
| Idle or a completed pass that can begin again | **Start automatic processing**. Keep the existing discovery/research/conversion tooltip. This starts the whole automatic workflow, subject to current admission checks. |
| Paused saved pass, resume available | **Resume automatic processing**. Tooltip: `Continue saved discovery, metadata research and pending audiobook jobs.` Detail/help: `Automatic processing is paused. Resume automatic processing to continue.` One press resumes that saved whole workflow; it is not a per-book Retry or a new approval. |
| Paused saved pass, resume temporarily unavailable | Same **Resume automatic processing** face, disabled with the actual backend reason visible beside it and in its tooltip. Do not fall back to **Start** or imply that pressing it is available. |
| Resume request in flight | Same **Resume automatic processing** face, inert against a second press; `Resume requested. Waiting for the app to respond.` When the backend confirms Running, use the existing running status; on refusal show its specific reason and restore the correct paused-state control. |
| Stopping, running, disconnected or other existing states | Keep their current control availability, Stop behavior and truthful status; no new transition is authorized here. |

Where a row hint or help currently directs the user to press **Start automatic processing** specifically while the saved automatic pass is Paused, use **Resume automatic processing**. Keep keyboard focus and accessible name aligned with the visible face. The existing scheduled-start cancellation, if present, remains a separate action and must not be confused with cancelling a saved Save/Approve decision. On private fixture states Idle, Completed, Paused available/unavailable, resume pending, Running and Stopping, check face, tooltip, `aria-describedby` text, one-press result and zero same-plane hit-area intersections at the existing widths/zoom. No live automatic pass was started for this spec.
