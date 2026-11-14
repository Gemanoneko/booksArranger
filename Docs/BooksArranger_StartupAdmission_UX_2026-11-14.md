# Books Arranger startup admission UX — 2026-11-14

Owner: Judy. Final direction: expose the existing backend admission in the existing first-frame load strip, eliminating a duplicate preliminary scan only if Ender and Senua prove the backend's full admission still precedes catalog mutation and normal workers. This supersedes the initial unimplemented standalone-window draft. No new window, dashboard redesign or new startup control is requested. User forbids opening the installed app or changing the live installation/library; all implementation validation is isolated/offscreen.

## Visible behavior

The ordinary first frame opens promptly through the existing `startConfigured` path; it keeps normal library placeholders and disabled unavailable actions. During the backend's actual storage admission the load strip shows:

`Working · Step 1 of 4: Checking data folder`

Next line: the actual phase, followed where known by a truthful count:

`Checking retained source files · 1,234 of 8,134 files`

Existing detail line: `running 1:23 · check updated 0 s ago · check budget 9 min 57 s` (values here are examples; format the configured bound and actual timestamps).

Keep the four normal startup steps. Admission is a subphase of Step 1, not a fifth numbered step or a second panel. After successful admission, Step 1 returns to `Starting the engine` until the normal health/startup protocol advances it. Admission success alone never means the catalog is loaded, never enables catalog actions, and never renders `Ready`.

If no phase/count is available yet, use `Checking installation and data folder…` with elapsed time and the configured check budget. Do not create an ETA, percent or timer-driven phase sequence. A count means completed validations in the current named stage, against that stage's actual known total; retained members and fence items must not be combined into one invented denominator.

Suitable labels only when backed by corresponding work are `Checking installation records`, `Checking retained source files`, `Checking folder access`, and `Checking the database`. Ender maps actual backend events to this short vocabulary; unknown/internal stage names display the generic status. Never expose internal Python module names in the ordinary status line.

## Progress event contract

Ender owns transport; the UI contract requires an admission record with active/failed/complete state, real phase identifier, elapsed start time, configured deadline, last worker-event time, last true progress time, and optional completed/total/unit. Validated progress travels from the existing owned backend to the shell startup record and the existing `books:startup` consumer. The backend is not an HTTP-ready service just because this record arrived.

- Phase change or increased completed work advances last true progress; repeated same-value events and heartbeat updates do not.
- A heartbeat can prove the process is reporting but cannot imply that a file check advanced. Display `check updated` during admission; do not falsely claim an HTTP `engine answered` event before one exists.
- Keep the existing Waiting/Stuck distinction based on quiet time, not total elapsed. A long check with advancing work remains Working past 15 seconds. If an individual native operation cannot report for a prolonged interval, Waiting/Stuck communicates that honest absence; it must not auto-kill at 15 seconds.
- Worker progress must not reset the cooperative admission budget. For 597 seconds show `check budget 9 min 57 s`. Give that text the tooltip and accessible description `If this time is exceeded, startup stops after the current check returns.` This is not an independent wall-clock kill: the budget is checked between native operations, and a blocked native call may return later. When elapsed time exceeds the budget but termination is not yet confirmed, append the visible status `Waiting for the current check to return.` Do not claim Stopped, show a zero countdown or enable retry until actual termination is confirmed. Do not extend unrelated Python operations or display an unmeasured ETA.
- The Step 1 bar can show only the current stage's real fraction when a denominator is available. On a new stage it may restart that stage's fraction; label the stage alongside it. Otherwise keep the existing indeterminate treatment. Do not imply a current-stage fraction estimates total startup completion. `aria-valuetext` names `Step 1 of 4, Checking data folder, <stage>, <count>`, without a whole-startup percentage.
- A late event from a failed/cancelled/restarted generation must not resurrect the earlier state.

## Failure, retry and quitting

Reuse the existing Stopped/Copy details controls and the engine's owned process shutdown path. During admission failures use `Stopped · Data folder check failed.` and the concise actual reason. After a confirmed budget refusal: `The data folder check exceeded its time budget.` For a verification refusal: `Stopped · Data folder needs verification.` Keep details selectable and stable after stopping.

Do not use the existing generic promise `Your files are not touched` for admission, because read-only SQLite may have shared-memory side effects. The UI must describe the stage/result rather than guarantee absence of writes.

Keep existing Restart engine/Try again only where the backend/shell can positively establish the retry boundary and prior process closure. During an in-progress admission whose cancellation safety is unknown, preserve the disabled state and tooltip `Wait for the data folder check to stop before restarting.` Do not claim the catalog is being changed merely because restart is unavailable. Never auto-retry. A verification-required failure must not present Retry as a bypass or conceal its actionable error.

No new Quit button is needed: the existing tray Quit and app exit path remain available. Preserve the established tray-app native Close behavior; do not change it as part of startup repair. The main window already uses 1280 × 860 with minimum 950 × 650. Honor `--start-hidden` and `--show-inactive`; progress/failure events never raise or refocus it. No sound or Explorer opening.

Tooltips for existing controls in admission context:
- Copy details: `Copy the data folder check details to the clipboard.`
- Restart engine / Try again, only when actually allowed: `Start the data folder check again.`
- Unavailable restart: `Wait for the data folder check to stop before restarting.`

## Layout and accessibility

Use the existing `#load-strip` panel, 15px load line, theme tokens and existing toolbar/button dimensions; add at most one wrapping phase/count line. All text stays in normal flow with existing 4px paragraph margins; no absolute-positioned badge or overlay. Long paths belong in the selectable diagnostic disclosure, not a full-width unbroken status label. Keep at least 8px between toolbar targets and at least 32px target height, existing 2px visible focus outline, and native keyboard operation.

Maintain existing light/dark tokens and reduced-motion behavior. Phase changes use the existing polite announcement region. Do not announce elapsed ticks or every member count; announce changed phase, stuck/working transitions and terminal result. Screen-reader status must not say Try again is available when the control is disabled or unsafe.

This follows visibility of system status, error prevention, user control and WCAG focus/contrast guidance in `Team/Research/UX_AppBestPractices.md`. No additional theme feature is introduced.

## QA acceptance

Use an isolated offscreen first-frame fixture; never open the installed app. At minimum 950 × 650 and default 1280 × 860, inspect dark/light supported themes and 200% text scaling. Measure rectangles for strip text, progress bar, phase/count/detail and action controls: no overlap or clipped button targets. Cover no first event, >15-second progressing admission, unchanged heartbeat, phase/count reset, stalled native operation, safe/unsafe restart, timeout, verification refusal, cancellation and transition to normal startup.

Verify that owned-backend events reach the visible strip before HTTP is ready, counters reflect actual completions, elapsed/cooperative-budget copy is truthful, an overdue still-running native call says `Waiting for the current check to return.` rather than Stopped, no Ready/library control is enabled from admission success alone, and normal four-step startup resumes. Verify no focus change from hidden/inactive modes, tooltip coverage, event-only announcements and stable selectable diagnostics. No screenshots or native live interaction are required; an offscreen rendered fixture is sufficient for visual QA.

## Provenance

This specification describes implementation, not permission to run the app. Jane/Sully must preserve it with candidate provenance before the implementation handoff per the studio spec-commit rule. Judy owns only this specification and does not commit or edit code.

