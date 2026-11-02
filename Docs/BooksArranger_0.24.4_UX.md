# Books Arranger 0.24.4 — retry held source cleanup

Judy · 2026-11-02 · EXTEND existing cleanup/jobs UI. Sergei approved a safe per-book retry for `Cannot refresh protected file identity`: reopen and verify the output/recovery evidence before deletion, and expose the actual Windows error on failure. No redesign, settings, bulk retry or general cleanup bypass.

Evidence: `Evidence/v0.24.3_2026-11-02/protected-identity-diagnosis.json`. The recorded final-M4B handle-information check failed on 29 October; its Windows error was discarded. The old receipts contain 37 backup records, one removal intent and zero removed/disposition-set records. Those are historical receipts, not proof of current output, original or recovery-copy presence. Judy read source/evidence only; no app, live data or Z: access.

Confirmed with Ender: reuse the row/details primary Retry slot as a distinct cleanup action. Capability requires the existing completed job and enrolled cleanup held on this exact legacy reason or a future typed output-identity read error. Existing serialization/queued-action Cancel/Pause apply; no parallel worker. The same job, cleanup and provenance are retained. On actual start, the worker reopens the output, verifies the full output, recovery copies and original identities before deletion. Ender supplies the actual capability, states and observed diagnostics; the renderer does not infer them from error text.

## Control and states

Use the existing Output needs attention row action and details-panel Retry control, existing cleanup facts and Audiobook jobs activity. Keep their size, styles and position; replace the conversion Retry presentation for this capability. One press affects one book. No confirmation modal is added: the action continues its existing approved cleanup policy after fresh checks.

| State | Control / tooltip | Status and nearby copy |
|---|---|---|
| Eligible held cleanup | **Retry cleanup**. `Recheck this audiobook, its recovery copies and original files, then continue removing originals only if all checks pass.` | **Cleanup on hold**. `The app could not read file information for {audiobook filename}. Retry cleanup rechecks the audiobook and recovery copies before removing originals.` |
| Request in flight | **Checking cleanup…**, inert against duplicate presses. Tooltip: `Requesting this book's cleanup retry.` | `Cleanup retry requested. Waiting for the app to respond.` Do not claim verification started before acknowledgement. |
| Accepted, waiting behind work/scan | Existing **Queued** and **Cancel** affordance. Queued tooltip/status: `Cleanup retry queued. It starts when {actual blocker} finishes.` Cancel tooltip: `Cancel this queued cleanup retry.` | Keep the book's existing cleanup receipts/counts visible; no running clock/bar. On acknowledged cancellation: `Cleanup retry cancelled.` Do not claim no originals have ever been deleted. |
| Worker checking | **Checking cleanup…**, inert. Tooltip: `Checking the audiobook, recovery copies and original files before cleanup.` | Activity names this book and its actual verification phase: `Checking audiobook`, `Checking recovery copies`, or `Checking original files`. Use only the phase Ender reports. |
| Worker removing originals | Existing cleanup progress and Pause controls; duplicate Retry unavailable | Existing `Removing originals: {removed} of {total}` from current receipts. Do not use this count as verification progress. |
| Pause requested / paused | Existing **Pause audiobook jobs** and **Resume audiobook jobs** behavior and checkpoint explanations | Existing pausing/paused cleanup status. Show saved removal count without implying active progress. Resume continues this same cleanup; it does not reconvert the audiobook. |
| Retry fails a check | Restore **Retry cleanup** only if the backend still offers this capability | **Cleanup on hold** plus the specific failed file/check and observed diagnostic, as below. A different protective refusal keeps its own existing reason/action. |
| Completed | Remove Retry cleanup; adopt the existing completed cleanup/output presentation only as confirmed by the backend | `Cleanup completed.` only after the enrolled cleanup/removal records confirm completion. Do not claim recovery copies or folders were deleted unless their own state confirms it. |

While another action for this book is queued/running, follow existing one-action-per-book controls and explain that action. Closing/disconnected states use the existing unavailable explanation. A stale/refused press uses the actual admission reason and existing next action; never silently submit a conversion Retry, Start over or a new cleanup intent. This capability is per-book and is not added to Retry all/selection counts.

## Failure and evidence wording

New identity-read failure, in the row hint and details status:

`The app could not read file information for {filename} (Windows error {code}: {message}). {recovery action}`

The Windows code/message must come from the failed call. Keep the exact API, full path and raw diagnostic in existing Technical details; do not expose a stack trace as the main hint. If Windows supplied only a code, omit the message separator. If no Windows diagnostic exists, do not invent one: show the failed check and existing remedy, and state `Windows error not recorded` in Technical details. In particular, do not attach a guessed code or NAS/SMB cause to the old hold.

The second sentence follows the observed cause: a sharing error → `Close the program using this file, then Retry cleanup.`; a confirmed unavailable drive/path → `Reconnect the drive, then Retry cleanup.`; denied access → `Check access to this file, then Retry cleanup.`; other identity-read failure → `Check the file and drive, then Retry cleanup.` These map actual classified errors; do not guess that a file is open or a drive disconnected from the generic legacy message.

Output-content mismatch, missing/unverified recovery evidence or changed originals use their real protective refusal and supported remedy. Do not relabel them as a Windows handle error or promise deletion on the next retry. Keep historical removal counts labelled as recorded progress; never add a universal `Nothing was deleted`, `All originals are safe` or `Recovery copies are present` claim.

## Accessibility and focused acceptance

Reuse `.row-retry`, existing wrapping hint/details layout, dark tokens and focus treatment. Keep at least 32 px action height / 24 × 24 px hit area; the longer label may grow naturally. No overlay, toast-only explanation, extra ambient animation, guessed progress percentage or ETA. Connect the control to the current hint/status with `aria-describedby`; its accessible name is `Retry cleanup: {book title}`. Announce request/phase/failure/completion politely once; do not announce every counter tick or move focus on a status update. Restore an enabled control after failure without rebuilding the focused row unnecessarily.

Verify on a private fixture: legacy hold with no Windows code; observed code/message; queued/Cancel; duplicate press; checking/removing; Pause/Resume; admission refusal; protective verification failure; and completion. Confirm this action targets the same book/cleanup and never starts conversion. Check long Cyrillic filenames/error messages and the existing 1280/960/760/600 px bands. Measure changed control/hint rects in those states: zero same-plane intersections; no text truncation that hides the filename/error/action. Check keyboard activation/focus and tooltip/status agreement. Existing dark styling must remain readable under either OS appearance preference; no app light theme is introduced.

This is a spec, not runtime verification. No scratch or disposable output was created. Sully commits this exact file with the diagnosis/technical plan checkpoint before Ender implements or cites its UI requirements.
