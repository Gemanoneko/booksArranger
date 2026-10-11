# Books Arranger — ready audiobooks and automatic list updates

Date: 2026-10-11. Judy UX specification. EXTEND v0.11.3, existing candidate View/Status/list/normal status display only. Sergei explicitly requested internal approval/creation stages to be transparent, completed audiobooks by default, and no Search button. Preserve metadata/source/order/cover confidence gates, automatic-run authorization, app completion provenance, overall progress, existing layout, manual exception access and other libraries. No new panel/framework, metadata algorithm, runtime/library action or Comics change.

## Default and filter labels

**Book candidates** remains the default audiobook View. Rename visible candidate Status option **Converted by this app** to exactly **Audiobook Ready**, retaining stable value **converted** and the exact authoritative Converted predicate. Fresh candidate View defaults to converted. Preserve an explicit user-selected filter for the current session and any already-supported saved preference; polling, new completions and reconnect never reset it. Do not add preference storage. Libraries without candidate View remain Files.

Hide these candidate dropdown options from the normal UI: **Needs review** (review), **Metadata approved** (approved), **Ready to create** (ready), **Audiobook created** (created). Their internal predicates/gates may remain. Visible options, in order: **Audiobook Ready**, **All candidates**, **Queued / creating**, **Held**, **Source read errors**, **Candidate changed**, **Output needs attention**. Keep existing values/semantics for retained options and all existing source-file filter meanings. Normalize a hidden/invalid candidate filter to converted on entry so it cannot produce an invisible selected value or crash its summary.

Use **Audiobook Ready** consistently in selected-filter/page summaries, accessibility text and empty states. Readiness means the existing app-owned validated output plus cleanup required by its frozen job policy; it does not include an unrelated existing M4B, metadata-only approval, published output with required cleanup unfinished, or stale/changed output. Keep existing best-effort folder housekeeping and retained 24-hour backup completion exceptions. Do not imply an Apple device import/sync test passed.

Default-empty candidate list: **No audiobooks are ready yet. Automatic processing progress appears above; choose All candidates or Held to inspect unfinished books.** If a nonempty text query has zero results, use the existing query-empty behavior with the correct selected label; do not falsely claim the whole library has no ready books. Existing **Clear filters** remains an explicit choice to clear the query and show All candidates/all files as its tooltip says, rather than silently changing that action to the new default.

## Normal candidate status display

Reuse the existing status cells/selected-book automatic-result/output summary; hide approval mechanics from the normal lifecycle wording. Do not expose **Needs review**, **Metadata approved**, **Approved automatically/manually**, **Ready to create**, or **Audiobook created** as a normal candidate lifecycle state. Keep detailed verification evidence and existing optional Manual review controls available; hiding a state never removes a gate or evidence.

Use authoritative facts, with failure/changed-source attention taking precedence over stale success:

- Complete under converted predicate: **Audiobook Ready**. Ender's receipt: add **audiobook_ready** from the same authoritative **merge.progress_books()[converted_ids]** set used by the filter/count. Expected retained 24-hour recovery copies do not block true. Never infer readiness from a created/completed substring. If an older backend omits this fact, use **Ready status unavailable** where completion cannot be established; do not restore hidden approval/created wording or fabricate false/true.
- Not active or fully completed, including discovered/approved/eligible-but-not-queued: **Pending**. No implied required review/create action.
- Actual queued job: **Queued**; active research/conversion/verification/required cleanup: **Processing**. Overall progress keeps its existing detailed phases.
- Actual source wait: **Waiting for source**; paused operation: **Paused**. These do not appear to be active research or completion.
- Uncertain match/source/order/cover: **Held — [actual short reason]**. Errors retain **Needs attention — [actual reason]**, source read errors and changed-source facts. Do not classify an app error as uncertainty.

Do not obscure existing automatic-run state, research/wait/held counts, current book phase/progress, conversion counter or errors above the list when the default finished-only filter excludes processing rows. Keep **[X] converted out of [Y] approved books**; this aggregate denominator remains truthful even though individual approval stages are internal.

Already-authorized automatic processing must take fully eligible approved books through its existing queue/conversion pipeline without a user selecting Ready to create or pressing a per-book Create/Queue action. Mere metadata approval is insufficient. Opening/changing View/filter, displaying Pending or loading the page never starts/resumes automatic processing or approves/queues a candidate. Explicit Stop/restart Paused and confidence-held books retain their existing behavior.

## Immediate list interaction

Remove the Search button from the existing shared list toolbar; retain its labels, input, select, Clear filters and pagination. Library/View/Status selection immediately refreshes the list and resets page offset to zero, using the latest visible search text. Candidate/file filters keep their respective meanings. Search text input refreshes after **250ms** without further typing; clearing the input refreshes immediately. Enter flushes the pending text update immediately and prevents form navigation. No extra Apply/Search step.

Cancel/coalesce pending text refresh when a select/clear action applies it. A late response must not replace results for newer controls/query/library; bind responses to the current request/context. Loading/result announcements remain in existing polite status; preserve input focus/caret, selected explicit controls and unsaved manual edits during updates. Do not poll-reset filters or rebuild a focused select. Pagination works on the currently applied query and uses existing empty/error handling.

## Handoff and verification

Contract consumers: web/index.html shared search form/button; web/app.js candidate defaults/options/summaries/status mapper/inspector/output summary/list event/debounce/request ordering; authoritative backend converted row/filter/count semantics and existing authorized approval-to-queue worker; frontend fixtures and README/Brief if they describe the removed user step/labels. Ender owns exact implementation and reports consumer checks. UI hiding alone is not evidence that auto queue/conversion already works.

Verify fresh default, every retained filter, switching libraries/views, manual filter choice surviving polls/new completion, incomplete cleanup/stale output excluded, ready list matching converted counter for an unsearched coherent snapshot, progress visible with empty ready list, automatic eligible-book queue without manual Create, paused/held/no-authorized-run safety, query typing/clear/Enter, selection during debounce and out-of-order responses. Retain existing keyboard/focus/hit areas and measured no-overlap checks; no new layout. Docs only, no code/Git/runtime/library/browser/probes; owned disposables: none. Sully commits/pushes this file before Ender cites/implements it.
