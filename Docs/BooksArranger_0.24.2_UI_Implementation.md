# Books Arranger 0.24.2 — UI implementation

Extends the existing renderer and picker bridge under the committed scope and Judy spec at 070ec34. No CSS geometry, theme, new control or modal changes. The 0.24.1 stale-line estimate is corrected to the previously measured 39 px; this slice makes no new geometry claim.

## Owned changes

- web/app.js: truthful Start/Resume/admission/maintenance states, independent Pause while Resume is awaiting response, explicit cancellation acknowledgement, pause origin, membership activity, chapter diagnostics/checks/validated correction details, queued-name Save copy, running-job origin copy, retained-folder details and picker state.
- desktop/folder-picker.js: one native picker in flight across IPC requests; only explicit cancellation returns null, malformed/open failures reject.
- tests/test_0242_frontend.js (new), tests/test_0231_destination_frontend.js, tests/desktop-folder-picker.test.mjs, tests/test_automatic_frontend.js, tests/test_ruling37_frontend.js, tests/test_0231_rows_frontend.js, tests/test_todo_holds_frontend.js.
- This note. desktop/main.js already registers the bridge; no main/preload/backend picker edit is needed.

## Confirmed backend contract consumed

Audiobook jobs start_admission is actual checking/waiting state (other response states remain understood); maintenance exists only during actual checking/stopping and supplies phase/title/job identity. Missing counts mean phase/title only: no synthetic percentage, clock or ETA. Paused cleanup retains its own saved count and does not become a start-check measurement. Pause sends independently of a pending Resume; duplicate requests remain one flight. Existing scan waits still queue through their original mechanism.

Jobs pause and automatic_processing.pause use actual origin user/update/closing/interrupted, with neutral wording for absent old records. A supplied current non-generic automatic hold reason remains visible. Automatic cancel-start requires explicit cancelled:true before saying cancelled; false reports the started race. Start/Resume duplicate activation is inert until acknowledgement. Existing help/status is connected through aria-describedby; state updates do not move focus.

ask.membership_checking is the only active membership claim. An unresolved membership string without that flag is neutral, with incomplete_scan using its specific sentence. Global waiting counts need an actual researching worker before saying still checking.

Chapter errors consume error.body.admission_error.chapter_diagnostic and durable row.admission_error.chapter_diagnostic. File/title/ID, predicate and unbounded H:MM:SS.mmm times are kept. Recovery wording uses actual Scan again or Start over capability; otherwise it points to existing metadata details. Approval refusal text does not append Nothing was changed. row.chapter_check only produces Checking source audio while its active callback exists. row.chapter_corrections is displayed as completed only with audiobook_ready:true, in agreement with lead's output-validation gate. No source is described as rewritten.

book_converting plus job_origin selects automatic/user/unknown wording. Queued action outcomes also pass admission_error/job_origin through the same formatter when supplied. Names saved with outcome replanned explicitly require Approve. Existing backend Start over automatic/manual_draft classification remains authoritative; the renderer does not reinterpret a genuine draft.

row.creation.job.folder_cleanup supplies protected path/reason entries, retained_details and scheduled retryable/retry_at. Existing output details name library-root/direct-child boundaries and the full audio-like filename without claiming playable audio. Protective records create no new attention row or retry promise. Recovery attention uses the same actual retry fields. Uncertain absence after intent is labelled Removal outcome not confirmed.

Identity/routing display continues to use the producer's verified fields and computed destination. Tests supply Tolkien series/positions and Omen shared paths to verify display preserves title/Place/author and preview. No independent routing inference or author-credit replacement was added. Chosen folders retain existing precedence.

## Picker finding

The app-controlled path has no intentional timer or filesystem wait before dialog.showOpenDialog. The renderer previously awaited a picker with no immediate destination line, and lacked a global cross-row single flight. It now immediately shows Choosing…/Opening the folder picker…, explains another open picker, distinguishes cancellation from failure, and changes to Saving after a choice. Cancellation leaves destination untouched and restores invoking focus only when focus has not moved elsewhere. This establishes no OS/NAS timing measurement or claim about actual dialog latency. No agent opened a dialog or controlled the app.

## Validation status

Chapter proof batch chapters-3 passed all 20 methods (17 deterministic, 3 generated native media), as reported by lead with normal owned closure, native zero and unchanged postflight. UI code has not run yet. The first prepared UI batch will contain nine fixed JavaScript entries: the seven changed tests plus existing progress and odd-name tests; the retry test is copied only as the existing DOM/transport fixture. Every browser, network, IPC, dialog and window in those tests is a double. No app or media executable is in that process graph.

Real headless layout measurements at 1280/1440/960/760/600, same-plane intersection area, dark palette under light/dark preference and focus/hit-area checks remain pending a separate concrete reviewed headless-browser.mjs invocation. Fake DOM results are not geometry evidence. No build, full gate, release, git, install, live app/profile/library read or write belongs to this slice.

## UI-1 frozen preparation

Prepared only at `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/ui/ui-1`: 15-file source tree `d5bba774ce13d2852c84aaaff008ec7871d5da855c580dc0e2082b895011c499`, plan `4f22a8eac80e73f5474731e6ce80a4d18a2b524eaf1ab7bba0c66ae45ea2aeeb`, driver `73a7b0f495720fd6a91b2b042b4605c7bafa46cd76d464e77060983ffc2c9719`, invocation `4e8cc01f1976460901ef41dcb58094a597dd4b61dfe33126f1c8f5e5dfd2e1a4`. Nine fixed JavaScript entries run sequentially through the existing owned runner under one total 600000 ms deadline. No test execution yet; exact native graph and fresh runtime/ownership manifests supplied to Senua. All source/artifact inputs are frozen through the eventual reviewed invocation.

## UI-1 result and UI-2 preparation

Lead reports UI-1 completed all nine entries with normal owned closure, native zero and unchanged postflight; overall NOT ACCEPTED. Seven entries passed. The picker eight tests all passed but default Node spec output did not match the driver’s required TAP markers. The automatic lifecycle entry had one remaining old /Starting/ assertion; the renderer showed the correct approved acknowledgement. No production defect was found.

UI-2 is prepared only, for those two entries: explicit built-in --test-reporter=tap and the exact pending-acknowledgement assertion. All production files remain byte-identical. Its source15 digest is `669918707102a28162517b359c3cb10d122d5b94a4dd48c2be8a73c6a4db5a41`, plan `6eb0015b5f080475793d963efdabe6c1ebeb440bc71893722e306d6e7a1f52d0`, driver `d6eba00b31a94036a908901474fbeaaaa75babbef13e9ea8456eeb0c58d1479d`, invocation `9872966edafab15da81cb358d9e474d0525388a68c945ccb645787cd41cdfbeb`. UI-1 is retained unchanged. No duplicate nine-entry batch or global helper/output waiver.

## Accepted targeted UI result

Lead reports UI-2 accepted unchanged: outer exit 0, both fixed entries passed their exact markers, postflight unchanged, normal native complete/zero closure. Picker: eight TAP tests passed; automatic lifecycle passed. Together with the seven accepted UI-1 entries, the targeted nine-entry UI set is complete without replay. Geometry remains separately pending; no real dialog, app or live media was used.

## Geometry package prepared, not executed

The private geometry-1 package freezes eight source/frame files, full active Edge runtime927, shared runtime47 and ownership92 plus wrapper/holder/relay/system pins. It prepares160 frame measurements across eight changed states, five widths, two appearance preferences and two scroll positions. Installed runtime hardlinks are read-only inputs bound by identity and content; private files remain ordinary single-link. Actual headless execution is pending Senua review of the complete native graph and exact invocation. Browser appearance emulation does not claim Windows/native-picker verification, and stale/startup geometry does not claim real engine timing.

## Accepted geometry coverage — 2026-11-01

This receipt supersedes the earlier preparation/pending descriptions. Geometry-1 was never admitted or launched. Geometry-2 completed160 frames and10 screenshots with normal closure but remained NOT ACCEPTED:158 frames passed and two1280/dark/paused scroll frames asserted a stale pre-Tab programmatic-focus snapshot. All160 actual keyboard records already showed a solid3px outline. Geometry-3 corrected only that private fixture action/assertion pairing and passed the exact two affected frames; no product source or CSS changed. Aggregate accepted coverage is160 cases:158 original plus2 corrected, across8 states,5 widths,2 browser preferences and2 table scroll positions.

Across the saved measurements there are zero positive non-ancestor rectangle intersections, zero controls below the specified hit-size checks, and no page/runtime/async/disallowed-network errors. Measured palette ratios meet their thresholds (minimum reported text pair6.07:1, border/surface4.13:1). Visible stale-line reserve is38.5px, consistent with the accepted approximately39px. Geometry-3 keyboard focus reaches the enabled visible Approve as one book button, remains through controls(), matches :focus-visible, and shows solid3px with5700px² viewport intersection in both cases. Requested geometry scroll and actual before/after-Tab scroll are recorded separately; its screenshots depict the after-keyboard phase.

| Receipt | Geometry-2 | Geometry-3 |
| --- | --- | --- |
| UTC interval | 14:57:34.810–14:57:53.930 | 15:10:34.665–15:10:44.675 |
| Result |158 valid;2 fixture failures; original overall failure retained |2/2 pass;2 screenshots |
| Wrapper close |stop-requested;verified:true;remaining:0 |stop-requested;verified:true;remaining:0 |
| Native ownership |complete/zero;42 retained;1048 complete queries |complete/zero;37 retained;460 complete queries |
| Postflight / outer callback |unchanged;exit1 reflects fixture failure |unchanged;exit0;full output hashes match |

Both invocations had no force, timeout, overflow or incomplete native query. Read-only window observations recorded no owned visible/foreground hit or monitor error (111 and29 samples respectively); metadata hygiene was clean. The root helper prerequisite was46f6cb26f625dab20f409ee5055a907de7aecb9d. These receipts are scoped headless evidence, not a full build/release/engine-load or native-app QA verdict.

Current source matches the accepted snapshots:

- web/app.js: `e5c5e43311ba39423808a86dd6c928ee1a4c727b3875a7c3b4221ad972c309e7`
- desktop/folder-picker.js: `9dcd4cfacaa74e0f80ac7933406cfeab02d8daa9ed5ed97a41c8c75295bcd78e`
- web/style.css: `91e47d7c8e74770dd3c625b4be78ba53e126a018288cde7675637ff3bda52d3d`
- web/index.html: `8b392bcd4b84e6c5666398d800a24689355db75d712e02e73be062d7b0150ad5`
- Geometry-2 source/frame8 tree: `4ddbadf40fcb02b529b009015397f63c5d1dc5e10306a7863bd9c0bbe030ed83`; geometry-3 frame8 tree: `b2cda76eb8fecaed5c5b2ae3585601e9f72385e9863533d6e52ce915b2fd3300` (private fixture only).

Saved evidence root: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/ui`. Keep both complete packages for independent Judy review; no cleanup yet. Each includes plan/native-graph/source frame, measurements.json, summary.json, closure.json, window-observation.json, owned-result.json, outer-result.json and full logs. Geometry-3 also includes focus-diagnosis.json.

- `geometry-2/measurements.json`: `e4bc2e72a8168b12e0fab3493c456908c56cf6efc2df10dc90af893ebe8e38af`; `geometry-2/summary.json`: `f50b444c83736e7a639f3311245789615f791bcd9abf11e439a668bb521dfddb`.
- `geometry-3/measurements.json`: `47b057056646024719945edbadc5d06297393ea0c6215c6aa1fb005c97190cfb`; `geometry-3/summary.json`: `619a3245dbd7d134c17864f3ebf438fb240f087aad4b4ee9d3ee3f24b3c84ec2`.
- `geometry-3/outer-result.json`: `7799e2b1fbfba0065b21783d46064ec0bd911fb036c2416ade722586748acf30`; `geometry-3/closure.json`: `ba280b9a5b053d1c33d9f460f33f85fa179faa5fd5111f9c0d7daee176b9bd5d`.

Selected PNGs (all12 saved images remain available):

- `geometry-2/screenshots/1440-dark-chapter-refusal.png`
- `geometry-2/screenshots/1280-light-chapter-refusal.png`
- `geometry-2/screenshots/760-dark-chapter-refusal.png`
- `geometry-2/screenshots/600-light-chapter-refusal.png`
- `geometry-3/screenshots/1280-dark-paused-top-left-after-keyboard.png`
- `geometry-3/screenshots/1280-dark-paused-bottom-right-after-keyboard.png`

Limits remain explicit: browser color-scheme preference emulation does not verify actual Windows light-theme or native-picker appearance; S8 stale/startup geometry does not measure engine load or startup timing. Window metadata sampling is finite, not a continuous OS event trace. No native app/tray/picker, actual user profile/library/audio, external service or user input was used. Independent Judy review of these saved metrics/images against UX070ec34 is pending; this implementation receipt does not substitute for her verdict.
