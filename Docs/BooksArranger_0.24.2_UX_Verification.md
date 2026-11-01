# Books Arranger 0.24.2 — independent UX verification

Judy · 2026-11-01. **UX result: accepted for the saved renderer snapshot, within the limits below.** No new product usability defect found in this pass. This is not packaged-app QA or a release GO.

Reviewed against UX spec `070ec34` and shared scope `3d4f0d2`. Read saved source, all geometry records and 12 PNGs; launched no app, browser, process, dialog or test. Only this report was written. No git, live profile/catalog/audio, Z:, registry, input or OS-setting access. No scratch created; existing evidence remains intact.

## Evidence identity and coverage

Current files match both geometry packages' saved `frame/inputs/` files byte for byte by SHA-256. These are pre-version-bump source snapshots, not an installer/payload certification.

| File | SHA-256 |
|---|---|
| `web/app.js` | `e5c5e43311ba39423808a86dd6c928ee1a4c727b3875a7c3b4221ad972c309e7` |
| `web/style.css` | `91e47d7c8e74770dd3c625b4be78ba53e126a018288cde7675637ff3bda52d3d` |
| `web/index.html` | `8b392bcd4b84e6c5666398d800a24689355db75d712e02e73be062d7b0150ad5` |
| `desktop/folder-picker.js` | `9dcd4cfacaa74e0f80ac7933406cfeab02d8daa9ed5ed97a41c8c75295bcd78e` |

Evidence root: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/ui/`. Read `geometry-2` and `geometry-3` measurements, summaries, closure records and fixture source; the implementation note retains the execution receipts. Root helper prerequisite is recorded as `46f6cb26f625dab20f409ee5055a907de7aecb9d`; this review did not run it.

The count method was to enumerate `measurements.frames`, form unique state/width/preference/scroll keys, and sum saved rect/issues/keyboard records. Geometry-2 contains exactly **160 distinct cases**: 8 states × 5 widths (1280, 1440, 960, 760, 600) × 2 browser appearance preferences × 2 table scroll positions. States: paused, checking, stopping, membership, chapter_refusal, picker_pending, expanded_move, stale_startup. Each state has 20 cases. Geometry-3 contains only the two corrected 1280/dark/paused cases.

**Failure history is retained.** Geometry-2 is `ok:false`, exit 1: 158 cases have no issues; two paused cases report `focus outline missing` because their assertion read a stale pre-Tab programmatic-focus snapshot. All 160 separate actual keyboard records already show solid 3 px outlines. Geometry-3 corrected the private fixture's action/assertion pairing, without changing product files, and passed 2/2. Accepted case coverage is **158 original + 2 corrected = 160**, not an assertion that the first run passed completely.

## Layout, hit areas, focus and readability

The measurement fixture obtains `getBoundingClientRect()`, clips through scroll/overflow ancestors, and checks positive intersections between non-ancestor control/text elements. Across Geometry-2's 3,360 control rect records and 5,434 text rect records: **0 recorded positive intersections; 0 undersized controls; 0 frame/runtime/async errors**. Every measured control has a tooltip. Minimum measured button width/height is 90.96875 / 37.5 px; checkboxes are 24 × 24 px. These exceed the spec's action-height and minimum-target requirements.

Representative rects (`x,y,width,height`, CSS px):

| Case / element | Rect | Result |
|---|---|---|
| 1280/dark/chapter_refusal/top-left, long refusal hint | `569.234375,563.796875,449.484375,214.5` | wraps in flow; zero recorded intersection |
| 960/dark/chapter_refusal/top-left, same hint | `476.09375,560.296875,228.921875,448.5` | retained full height; normal table scrolling exposes the remainder |
| Corrected 1280/dark/paused actual keyboard target, Approve as one book | `1034.828125,481.296875,152,37.5` | 5,700 px² in viewport; enabled, visible, retained, `:focus-visible`, solid 3 px outline |
| 1280/dark/stale_startup stale line | `41,354.296875,1183,22.5` | plus 8 px top/bottom margins = **38.5 px** flow height, consistent with the accepted approximately 39 px |

Original `focus.retained:true` in 160 records proves the programmatically focused element survived `controls()`. The separate original `keyboard` records prove the actual Tab outline, but do not record that target's visibility/retention. Geometry-3 explicitly records actual Tab visibility, enabled state, viewport area, `:focus-visible` and retention for the two corrected cases. Keep those evidence claims distinct. Geometry-3 records requested geometry scroll separately from the scroll after Tab; both PNGs depict the latter. Tab's normal scroll-to-focus is not a state-update focus steal.

Inspected all ten `geometry-2/screenshots/{width}-{dark,light}-chapter-refusal.png` images and both Geometry-3 paused after-keyboard images. Long text/path wrapping, the shared Omen destination, retained author credit, stacked narrow actions and the corrected keyboard focus remain readable. The 600 px band uses the existing stacked row presentation; wider bands retain columns. No geometry change is warranted by this evidence. The ten chapter-named PNGs were captured after focus/scroll and largely show the later synthetic Omen row: they do **not** independently show the refusal body. Refusal wrapping is supported by its saved rects and source; this is a screenshot-coverage limit, not a product failure.

Both preference sets retain `color-scheme:dark`. All nine recorded palette pairs pass their supplied thresholds: lowest normal-text pair is disabled text/background **6.07:1**, border/surface **4.13:1**, focus/surface **11.18:1**. Words carry state meaning; existing warning/focus tokens are reused. This verifies the measured dark palette under browser preference emulation, not an app light theme or actual Windows/native-picker appearance.

## Copy, hierarchy and control-state check

Read the changed producer-consumer presentation in the pinned source; geometry uses synthetic payloads, so these findings concern renderer presentation rather than proof that production workers emit every state correctly.

| Surface | Spec check / evidence |
|---|---|
| Start/Resume/Pause and housekeeping | `web/app.js:466–503,1016–1060`: acknowledgement/check/wait/stale/closing states are explicit; Pause has its own in-flight request, so it can be sent while Resume awaits a response. Saved records show Pause enabled while checking, inert while stopping, with the safe-checkpoint tooltip. Resume names the active check. Help/status supplies `aria-describedby`; no duplicate new control. Admission precedes maintenance in activity order; absent counts produce phase only and no bar/clock/ETA (`:1033–1042,1113–1136`). |
| Pause attribution | `web/app.js:462–487,2231–2232`: actual user/update/closing/interrupted origins map to the specified text; historical absence stays neutral. Automatic paused state uses Start automatic processing; a supplied hold reason remains visible. No timestamp-based attribution. |
| Start over / recovery | Existing action classification remains producer-authoritative. Accepted automatic return is not reinterpreted as a manual draft in the renderer. Retry text is conditional on `retryable:true`; protected retention and unconfirmed removal have distinct details (`:1240–1253,2360`). Actual disk detection and recovery timing require backend/QA evidence. |
| Membership and grouping | `web/app.js:3322–3328`: active `membership_checking` alone produces checking language. Unresolved siblings/incomplete scan are neutral; valid grouping controls remain. Existing file lists and Place/Goes to surfaces are retained. The fixture includes four internal-section names, Middle-earth/Властелин колец/2 and Omen without an author directory; this tests display, not identity research or grouping correctness. Mixed synthetic title/author clues in the fixture are not evidence of an actual book misidentification. |
| Shared routing and explicit folder choice | Existing destination presentation preserves the computed path and separate actual author credit. Omen's synthetic saved path is visible without an author directory; Middle-earth Place is visible in the corrected PNGs. Existing chosen-folder comparison and move confirmation remain in flow. No extra world/series controls or invented names. Upstream route/preview agreement belongs to routing verification. |
| Chapter diagnostics / correction | `web/app.js:2509–2514,3006–3008,3061–3090`: durable and immediate refusal use file, chapter title/ID, predicate and unbounded `H:MM:SS.mmm`; recovery names actual Start over/Scan again capability, otherwise metadata details. Complete-audio checking appears only with its active reason; success text is gated by `audiobook_ready:true`. Approval refusals omit the false “Nothing was changed” claim. Full names wrap; no source rewrite claim or generic new Repair control. Audio proof/preservation is outside this UX pass. |
| Minor copy / retention | `web/app.js:3080–3082` distinguishes automatic/user/unknown conversion origin. `:3724–3725` says accepted replanned names need Approve. `:1240–1250` explains library/direct-child protection, names audio-like leftovers without asserting playable audio, and labels unconfirmed removal. The actual saved-name hold reason remains a producer contract. |
| Choose folder feedback | `web/app.js:3394–3398,3446–3465`: immediate Opening/Choosing, cross-row already-open explanation, then Saving; cancellation preserves destination and focus return is conditional, so it does not seize focus from another control. Failure differs from cancellation. `desktop/folder-picker.js` permits one picker request at a time and uses native dialog behavior. No guessed delay/NAS cause. Actual Windows dialog response/appearance was not exercised. |

## Retained limits

- The saved matrix uses private synthetic payloads and source pages, not a committed packaged candidate or real app. Pending targeted/backend/full-entry/native QA outcomes are not replaced by this acceptance.
- `stale_startup` deliberately forces both saved layout elements visible to measure geometry; it does not test S8 suppression, list/engine load, actual startup timing, disk-change detection or fault-retry timing. No behavioral pass for those is claimed.
- Browser appearance preference emulation leaves Windows settings and the native folder picker untouched. No actual Windows light/dark picker check, OS/NAS latency measurement or unsupported app light-theme pass is claimed. No reduced-motion runtime was supplied; existing CSS/source behavior was inspected only.
- The 160-case fixture exercises the listed combinations, not every possible app modal/mode. Rect tests cover their declared selectors and normal scrolling; zero recorded intersections is not an unbounded whole-app no-overlap certificate. Corrected actual keyboard visibility/retention is explicit for two cases; a full keyboard traversal of every control is not claimed.
- Saved closure records for both packages say `stop-requested`, `verified:true`, `remaining:0`; summaries retain complete/zero native closure and unchanged postflight. Personal-folder records are `clean`, with empty listed lines. Those are the originating runs' receipts, not new monitoring performed by Judy.

## Durable evidence pins

Paths below are relative to the evidence root above; SHA-256 was re-read independently in this pass.

| Artifact | SHA-256 |
|---|---|
| `geometry-2/measurements.json` | `e4bc2e72a8168b12e0fab3493c456908c56cf6efc2df10dc90af893ebe8e38af` |
| `geometry-2/summary.json` | `f50b444c83736e7a639f3311245789615f791bcd9abf11e439a668bb521dfddb` |
| `geometry-2/closure.json` | `d7b95fda130a8fbade74bb20eb93bd08ae48c63c421bab7f79e9adbe568a85bf` |
| `geometry-3/measurements.json` | `47b057056646024719945edbadc5d06297393ea0c6215c6aa1fb005c97190cfb` |
| `geometry-3/summary.json` | `619a3245dbd7d134c17864f3ebf438fb240f087aad4b4ee9d3ee3f24b3c84ec2` |
| `geometry-3/closure.json` | `ba280b9a5b053d1c33d9f460f33f85fa179faa5fd5111f9c0d7daee176b9bd5d` |
| `geometry-3/focus-diagnosis.json` | `7a68b22af046dd7ea44cf028e788aecbe4139dac768b5b0b70de7d05a165556e` |

No source fix or product-scope change requested. Preserve both original and corrected packages until the parent finishes QA/release evidence retention.
