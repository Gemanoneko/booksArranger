# Books Arranger 0.24.2 — UX implementation spec

Judy · 2026-11-01 · EXTEND 0.24.1. Preserve the existing panels, table columns, row actions and naming editor. This specifies presentation; Ender owns state production, scheduling, verification and routing. No new top-level control, modal or feature is required.

Authority: Sergei approved all backlog and diagnosed bugs, then the shared multi-author series/world routing addition. Scope: `BooksArranger_0.24.2_Scope_2026-11-01.md`, base approval committed at `e8a56f2`, shared-container amendment committed at `3d4f0d2`. Evidence: the two 2026-11-01 diagnosis reports and `BooksArranger_DiagnosisEvidence_2026-11-01.json`; 0.24.1 UX, QA and code-review reports. The older diagnosis reports' proposed deferrals are superseded by that approval.

Rules applied: ProcessRules § Copy is short, specific, and has no memory; § A new control is born with its tooltip; § No UI element may cover another; § Our tooling must not intrude on Sergei's machine. Use existing recognition-based labels and nearby actions (NN/g); retain familiar controls (Jakob's Law); retain 32 px minimum action height and visible keyboard focus (Fitts's Law/WCAG AA). This pass read source and supplied screenshots only. No app, browser, live data or Z: access; no measured runtime/hit-area claim by Judy.

## 1. Start, Resume, housekeeping and pause attribution

Affected: Automatic processing panel; Audiobook jobs summary, buttons and activity rows; existing queued-start messages. Do not label a real check as merely `Paused` or `Removing originals · 0 of 19`. The paused cleanup remains paused until its own worker resumes. Old finished-book housekeeping is independent work; never say Start waits for it when it does not.

Ender's confirmed contract: existing `start_admission` states `running`, `checking`, `waiting`, `stale`, `closing`; concurrent presses share one owner. Existing `published_check` has `kind`, `completed`, `total`, `started`. Optional `maintenance` exists only during actual housekeeping, with phase, job/book, `checking`/`stopping`, optional counts and cancellation flag. The page uses the actual phase and capabilities; it does not infer activity from pending cleanup rows.

| Actual state | Visible status / response | Control behavior and tooltip |
|---|---|---|
| Start/Resume press sent, no answer yet | Existing pending button face; `Start requested. Waiting for the app to respond.` or `Resume requested. Waiting for the app to respond.` in its existing status area | One request. Disable duplicate submission while the press is in flight; retain the button's purpose in its tooltip. Do not start a second catalog pass. |
| Admission `checking` | Summary `Checking pending audiobook work`; use an existing activity row for the actual check, with the actual book title if supplied | Existing Pause/Stop action remains available where the backend can stop this admission at a safe checkpoint. Tooltip: `Pause the start checks and keep pending work. The current read may finish before stopping.` |
| Admission `waiting`, reason pause/start | Keep the existing queued request and cancellation affordance. `Resume queued. It starts when the pause finishes. Press Resume again to cancel.` / `Resume queued. It starts when the earlier start finishes. Press Resume again to cancel.` Automatic Start uses its existing pending-start Cancel control and names its real blocker | Same state in the control tooltip. A queued cancellation says `Resume cancelled. Pending work is kept.` / `Start cancelled. Pending work is kept.` Only say it was cancelled after acknowledgement. |
| Admission `running` | Show the actual resumed cleanup/conversion/research activity in its existing place | Existing running Pause/Stop behavior. An admission check must not remain as a second running activity. |
| Cancellation requested, checkpoint pending | `Pausing start checks…` for admission; maintenance uses `Stopping finished-book checks…` | The stop action is inert while its request settles. Tooltip: `Stopping at the next safe checkpoint. Pending work is kept.` Do not claim stopped, show a completion tick, or clear the active phase early. |
| Admission `stale` after pause/cancellation | `Start checks stopped. Pending work is kept.` | Restore the normal Start/Resume eligibility supplied by the engine. No automatic re-submission of the cancelled press. |
| Admission `closing` | `Books Arranger is closing. Pending work is kept.` | Start/Resume disabled; tooltip repeats the reason. No restart advice during the safe-stop request. |
| Actual background maintenance `checking` | Existing activity row label `Checking finished books`; step describes the real operation, e.g. `Checking the audiobook before source-folder cleanup` | Do not make it the requested book's conversion progress. Show title only if supplied. Stopping capability follows Ender's mapping; do not invent a separate Cancel control. |
| No active check | Remove its activity row | No ticking check elapsed time, moving bar or `Still checking` text remains. Durable refusals belong to the book's details/attention state. |

Progress is evidence. Show `{completed} of {total} books` only for a current, valid book count; file counts/bytes require those actual units. Missing/invalid totals mean phase and title only, with no percentage or ETA. Reuse the existing activity geometry and accessible labels; a phase change is announced politely, counts and clock ticks are not. Current admission/foreground work takes visual priority over housekeeping and any paused cleanup row. Do not turn a saved `0 of 19 removed` into a measure of a different check. A paused row's count is a saved count, with no motion or running clock.

Pause attribution uses the confirmed optional `{origin, at, reason}`. Place the concise reason in the existing Automatic processing detail / Audiobook jobs help immediately after the paused status, rather than a toast that disappears:

| Origin | Copy |
|---|---|
| `user` | `Paused by you. Resume continues pending work.` |
| `update` | `Paused for an update. Resume continues pending work.` |
| `closing` | `Paused when Books Arranger closed. Resume continues pending work.` |
| `interrupted` | `Paused after an interruption. Resume continues pending work.` |
| absent/unknown historical origin | `Paused. Resume continues pending work.` |

For automatic processing, the action sentence is `Start automatic processing to continue.` Show a supplied current plain-language hold/error reason instead of falsely attributing it to the user. Do not infer updater involvement from timestamps. A timestamp, if shown in existing details, is local time and labelled `Paused at`.

Disabled Start/Resume/Pause retains a state-specific tooltip and nearby existing status explanation: already checking, waiting for pause, stopping, closing, disconnected, or no pending books. A disabled element's native `title` is not the sole explanation; use the existing help/status as `aria-describedby`. No generic `Busy` where the known action can be named.

## 2. Start over and transient recovery

Affected: stopped candidate row, Started over filter, existing action feedback; cleanup status in details.

- Keep 0.24.1's `Stopped — source file changed`, named file hint, `Start over`, pending face and tooltip. Show the offer as soon as fresh source evidence establishes it; no artificial UI delay, reload or restart step. The page does not guess that a source changed.
- Accepted Start over goes to automatic processing with actual user choices retained. `Started over — waiting its turn` / `Started over — researching` remain. The response may say automatic processing started only when the backend confirms that; a pending start names the real blocker. A retained approved review alone must not display `Held — Manual draft retained` on this automatic-return path.
- Preserve a genuine unsaved/saved user choice and its existing release confirmation. A real retained draft still says why processing is held. Do not offer the automatic-return wording for a capability that only sets the old job aside.
- If it is researching/queued, show that state; do not tell Sergei to press Approve and Start to complete a successful automatic Start over.

Retryable recovery/folder/output waits use Ender's `retryable` classification and supplied cause. In the existing cleanup/attention details, use the actual subject and action: `Cleanup waiting — {folder} cannot be reached. The app will retry automatically.` / `Cleanup waiting — {file} is open in another program. Close it; the app will retry automatically.` A known next retry may be shown as `Next retry: {local time}`; omit it when unknown. Do not promise a guessed delay. Do not say the audiobook is ready before output and cleanup requirements pass.

A protective refusal has no automatic-retry promise: `Source folder retained — {specific reason}.` Keep the actual available recovery action alongside the reason. Preserve unresolved evidence/receipts and show `Removal outcome not confirmed` for an unresolved removal record; do not claim a file removed merely because a retry began. Recovery after a transient fault updates the existing row and clears the obsolete wait without requiring a restart.

## 3. Series, universe, grouping and shared destinations

Affected: Book and Author / reader columns; existing Place line; grouping title input, Playback order and As one book/Goes to preview; Edit names; approval payload. Use the same current verified identity and current user edits everywhere. A cache miss is not an empty title, series or universe. Do not show implementation/cache text to the user.

1. Tolkien grouping rows show `The Two Towers` / `The Return of the King`, exact series `Властелин колец`, positions 2 / 3, and the confirmed Middle-earth relationship using the existing universe naming policy. Preserve the exact approved series spelling; do not invent a spelling from the user's shorthand. The title clue may retain the Russian edition title as it does today. Internal Books 3–6 stay in file/playback detail; they are not series positions.
2. Matthew Corbett uses verified original titles, series and positions 1 / 2 from the narrowly supported identity result. Queen's Маскер, Безумие, Послание and Методы убийства are internal sections for the confirmed edition. If grouped, the existing file count and Playback order list include all four actual files. An explicit saved Keep as separate books decision remains authoritative. No generic merge of similar sibling filenames is implied.
3. Keep the existing Place wording: `Universe: {name} · Series: {series} · No. {number}`; omit genuinely absent facts. Do not repeat an identical series line in the Book cell. The title input, Book label, Place, preview and accepted destination must agree. When evidence is insufficient, retain the existing honest not-decided/question state; never fill a missing position from a disc or internal book number.
4. The approved shared-container routing changes only the computed folder. A multi-author series uses `Audiobooks Sorted\Omen\{computed book filename}` without an author directory. A world/universe containing multiple series and/or authors uses `Audiobooks Sorted\{world}\{series}\{computed book filename}`; a world book without a series omits that level. Preserve the existing computed filename and real author credit. The Author column and metadata still name David Seltzer/Joseph Howard or the actual author. Do not replace a credit with `Omen` or the world name.
5. These routes appear in existing `Goes to` / `As one book` / chosen-folder comparison lines. No extra shared-world badge, toggle or folder button. A user-chosen destination stays authoritative; `Folder chosen by you. The app would use {computed folder}` may show the corrected computed route as it does today. Normal single-author routing outside the approved shared cases stays unchanged.

Membership wording and Approve tooltip follow actual state, not merely the existence of siblings:

| Evidence | Membership line | Approve tooltip |
|---|---|---|
| A membership check is actively running | `Checking which other files belong to this book.` | `Approve only the files shown as one book. Other files are not included.` |
| Siblings remain unresolved; no active check | `Other files in this folder may belong to this book.` | Same, with no claim that a check is running |
| Folder scan incomplete; no active check | `The source folder has not been fully checked.` | Same; the existing Scan again action is available where its actual scope can complete this check |
| Established membership | Existing `The source folder holds only these {n} files.` / plural folders | Existing cause-specific Approve tooltip |

Do not disable a valid explicit grouping answer merely because membership is unresolved. Preserve the existing narrowly scoped action and its clear consequence. If admission cannot safely include all shown files, use its real disabled/refusal reason rather than suggesting that approval silently includes other groups.

## 4. Chapter timing, bounded correction and refusal

Affected: grouping approval response in Review status; existing audiobook/checking activity; View metadata's chapter/technical details. Reuse Approve, Scan again, View metadata, and any existing source-replacement/Start over capability; no separate generic Repair button is introduced by this spec.

When the approved bounded final-end correction can proceed, Approve enters the real source-audio verification activity. Phase `Checking source audio`; where the backend confirms this specific reason, the adjacent row note is `Checking the complete audio before correcting the final chapter end.` No repair-success claim is made before proof and output validation. After successful preparation, the existing detail record may say `Final chapter end corrected in the audiobook. Chapter names and start times are kept.` Do not imply the source file was rewritten. Other boundary conditions retain their safeguards.

An uncorrectable refusal names the actual condition. Row response is at most two sentences; the second gives the available next action. For an invalid terminal endpoint:

`Approve not accepted: {file}, chapter “{chapter title}”, ends at {reported end}; the audio ends at {duration}. Replace this source file, then Scan again.`

Use this recovery sentence only where Scan again can re-read the replacement; for a stopped job that actually offers Start over, use `Replace this source file, then Start over.` If the safe correction was attempted but complete-audio proof failed, say `The complete audio could not be verified` with that file's actual read/decode reason and the existing recovery action. Do not call the audiobook corrupt or incomplete based on chapter metadata alone. Do not append `Nothing was changed` to approval refusals that may refresh incidental metadata.

Other structured conditions translate to a specific fact: `starts before the audio`, `has an end before its start`, `overlaps chapter “{previous title}”`, `starts beyond the audio`, or `has an unreadable time`. Use chapter ID only when there is no title; label it `chapter {id}` without assuming numbering starts at 1. The existing details show file/path, chapter ID/title, start, end, audio duration and failed condition. Show time as unbounded `H:MM:SS.mmm` (hours may exceed 24); exact seconds can remain in Technical details. Avoid a generic “overlap or exceeds” message when the predicate is known.

Long file/chapter names wrap within the status cell and details. Keep the full name as text; never truncate away which source needs replacement. The full raw structured reason is in the existing details, not a new modal. A failed check leaves the grouping question and current names/destination visible.

## 5. Small copy and folder-picker corrections

| Finding / surface | Required presentation |
|---|---|
| Senua/Futaba m1: Approve during a running job | Automatic origin: `This book is already converting with the automatic names. Your new names were not applied.` User-approved origin: `This book is already converting with your approved names. Your new names were not applied.` Unknown origin: `This book is already converting. Your new names were not applied.` No false automatic attribution. |
| Futaba m2: Save of names replans a queued book | On accepted saved names: `Names saved. Approve to queue this book with these names.` Held reason: `Names saved — waiting for your approval.` Use a different real source-membership reason only when that uncertainty independently exists; do not reuse it as a default for a manual edit. Save tooltip retains its existing distinction between saving names and Approve. |
| Futaba m3: library root/direct-child retention | In existing folder-cleanup details: `Source folder retained — it is a library folder.` / `Source folder retained — it is directly inside a library folder.` This is a protective boundary, not a cleanup error or an invitation to delete it manually. No extra routine toast or table row. |
| Futaba m4: audio-like leftover | `Source folder retained — audio may remain in {filename}.` The same full filename appears in the durable detail/receipt. Other unknown leftovers continue to name their file. A file such as `bonus.mp3.txt` is not described as proven playable audio. |
| Futaba m5: stale-list geometry | Accept the existing in-flow paragraph and correct the 0.24.1 estimate: QA measured 23 px line + 8 px upper/lower margins = **39 px** one-line table displacement. This is an estimate correction, with no observed overlap or stolen target; no permanent blank band, overlay, animation or new control is warranted. Preserve existing state/timing copy; narrow wrapping may need more height and stays in flow. |

Choose folder uses the existing action and destination status area. On press, set the pending state immediately, before awaiting the native bridge; pending button face `Choosing…`, tooltip `Waiting for the folder picker.`, and visible status `Opening the folder picker…`. Keep a single in-flight native picker across repeated presses/rows; a second press does not open another. Other rows' Choose folder actions explain `A folder picker is already open. Finish or cancel it first.` No countdown, guessed NAS blame or ETA.

Cancellation restores the normal button and preserves the destination without a success/failure toast. A native bridge/open failure must be distinguished from user cancellation when the API can distinguish them: `The folder picker could not open. Try Choose folder again.` After an actual chosen folder, use the existing save/move states; do not keep `Opening the folder picker…` during destination validation or move. Preserve existing focus return to the invoking action without scrolling the table. The user-invoked dialog keeps native keyboard/Escape behavior. This spec authorizes no agent-controlled app/dialog launch.

## 6. Acceptance and handoff

Ender maps the confirmed contract to the copy above and reports any missing capability before implementing dependent UI. On the committed implementation, Futaba checks the changed states; no duplicate whole-gate run is requested here.

- **State truth:** slow Start/Resume, repeated presses, queued cancellation, cancellation race, stopping during a read, actual stopped state, and each known/unknown pause origin. No requested book shows another book's progress. An unavailable status is labelled last-confirmed rather than asserted current. Foreground work can proceed while unrelated housekeeping is pending. Protective holds and retryable waits remain distinct; transient recovery clears its old status when recovered.
- **Identity/routing:** Tolkien title/series/2–3 and universe survive grouping/cache eviction; preview equals accepted destination. Internal Books 3–6 do not become series positions. Queen's four actual section files appear in playback order for the supported edition; user separation remains. Omen and shared world/series examples have no author directory, while Author and filename credits stay correct. An explicit folder override still wins. Test both ordinary and edited-name approval.
- **Chapter behavior:** three demonstrated terminal-end cases enter only the proven correction path; valid small-offset case stays valid. Unproven proof, earlier overlap, bad start, missing title/ID fallback and very long names get the actual file/condition/action. Success preserves titles, starts, order and audio. Source originals are not described as edited.
- **Geometry:** check supported wide layout (1280 px and 1440 px), the existing compact band (960 px), and narrow layout (760 px and 600 px). Controls remain at least 32 px high with at least 24 × 24 px hit targets. Long Cyrillic names, 3-digit hours, status wrapping, expanded names/source folders, grouping both answers, stale warning, picker pending, move confirmation and stopped/paused activities must remain readable and operable. Existing scrolling may continue; new text must not cover another control or table cell.
- **Measured hit areas:** capture `getBoundingClientRect()` for changed controls and their adjacent text/controls in each affected state above. Report `{x,y,width,height}` and pairwise same-plane intersection area; expected **0 px²**, excluding deliberate native dialog/modal overlays. Screenshot appearance is not a hit-area measurement. Preserve focus ring visibility and keyboard order through pending/disabled/restored controls; no state update steals focus. Tooltip and nearby explanation agree.
- **Color/theme:** the app explicitly declares dark-only CSS; no light theme is added. With Windows dark **and** Windows light, the page remains the existing dark palette and native picker remains OS-native. Check text/control contrast in normal, selected, warning, disabled and focus states; WCAG AA normal text ≥4.5:1, control/focus boundary ≥3:1 where applicable. Reuse current tokens: text/muted/warning; no new color-only state. A test of an unavailable app light theme is N/A, not a fabricated pass. Reduced-motion mode retains phase/progress without unnecessary motion.
- **Stale/startup/list load:** reproduce S8 with startup strip visible: no duplicate stale line; an actual slow list re-ask preserves rows/timestamp; measured 39 px one-line flow shift has no overlap. Record separate engine-load measurements and exact folder/recovery fault results in QA, not as UX timing claims.

This doc adds no runtime evidence or tests. No scratch/output files were created. Supplied screenshots and unresolved evidence remain untouched. Sully commits this exact spec file before Ender implements/cites it; the parent supplies the final scope/spec pins in the handoff.
