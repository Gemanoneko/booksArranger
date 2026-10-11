# Books Arranger — windowless launch and restart status

Date: 2026-10-11. Judy UX specification. EXTEND the existing local Python/browser app at 127.0.0.1:5210. Scope: normal entrypoint naming, existing startup/restart/automatic status and native failure wording. Preserve the automatic retry UX spec, confidence gates, saved queue, verified completed identities and 24-hour recovery policy. No Electron rewrite, console managed by the user, new update-download feature, library/runtime actions or Comics changes.

## Normal entrypoint

Use Ender's proposed **launch-web.pyw** as the normal browser entrypoint; app/window/message identity is **Books Arranger**. Document it as **Open Books Arranger with launch-web.pyw**. Keep any existing command entrypoint as a developer alternative; no normal instruction asks the user to leave a terminal open, use Ctrl+C or answer a batch-file termination prompt. Ender owns the Pythonw/association/ownership implementation and must prove that it works before promotion. Do not create Desktop/Start-menu shortcuts or change file associations without an applicable user request.

The launcher reuses a verified healthy Books Arranger owner, then shows that owner's existing browser UI without restarting it or changing its automatic-processing state. An unrelated process on the address is a startup failure, never an app to terminate. For a new owner, establish readiness and identity before showing the browser page. Repeated opens must not duplicate workers or silently resume paused work. Do not open a browser error page and call that successful startup. Launcher progress must never take the form of a persistent command window.

## Restart and explicit continuation

Ordinary fresh launch/server restart preserves the existing pause contract. Use the existing acknowledged status **Paused after server restart — start to continue saved work** when restart recovery applies, with the existing **Start automatic processing** action. Merely opening the launcher or reconnecting the page does not authorize Start. Reusing an already running owner displays its actual Running/waiting/Paused/Needs attention state without a fabricated restart notice.

For this explicitly authorized **apply update and resume automatic processing** operation, Ender may invoke one supported Start after the new owner/version and protected saved-state checks succeed. Existing status text during that acknowledged transition: **Update applied — resuming automatic processing…**. Then show actual Running/waiting status only after Start acknowledgement. No promise that a specific held book converts. On a failed resume, keep actual Paused or Needs attention and use **Update applied; automatic processing could not resume.** followed by the recorded plain-language reason and actual existing Start eligibility. Do not label a merely started process Update applied before its loaded version is verified.

Any user-facing restart action must save/checkpoint owned work and wait for safe shutdown before launching its replacement. Existing **Stop server** remains a complete stop. Do not relabel it Restart if it only exits. A new in-web restart control is **not specified by this doc**: Ender's owned restart route is still being proved. Report that feasibility receipt to Judy before adding or naming such a control; do not invent a broker, scheduler, shell fallback or new app framework from this UX request. No routine future restart auto-resumes unless its user-selected action explicitly requests continuation.

## Failure wording without a console

Use Ender's existing proposed small native message surface, title **Books Arranger**, and one conventional **OK** dismissal. Show a bounded plain-language cause and the appropriate next action; do not expose raw traceback, credentials, internal roles or source filenames in the main message. A diagnostic log receipt may remain available as selectable text in that same surface if supported; no new diagnostics panel or upload flow.

Approved cause-specific messages:

- Missing required runtime: **Books Arranger could not start. Python 3.12 or later is required.** Only use this when that is the detected cause.
- Address occupied by an unverified process: **Books Arranger could not start because another program is using its local address. Close that program, then open Books Arranger again.** Do not suggest killing a process or assume it is Books Arranger.
- Existing app still safely stopping: **Books Arranger is still stopping. Open it again after shutdown completes.** Only use after a confirmed owned shutdown, not for an unknown lock owner.
- Startup exception: **Books Arranger could not start: [plain-language cause].** Add **Open Books Arranger again to retry.** only when retry is safe and the failed owner has actually ended. If no cause was recorded: **Books Arranger could not start. Failure details were not recorded.**
- Ownership/update verification failure: **Books Arranger could not verify the app to restart. The restart was cancelled.** Preserve the existing owner and files; do not claim it was stopped.

A failed startup/restart must not leave the page saying Running or leave an indefinite Connecting/resuming message. Existing browser connection notices remain truthful during an owned restart and clear only on a complete current-owner poll. Do not claim source files, recovery sets or pending work were preserved unless their existing backend receipts establish that fact.

## Handoff

Ender checks normal launcher, verified-owner discovery/readiness/version, safe shutdown/restart, native startup messages, existing browser connection/automatic status and README launch instructions. Test with isolated state through approved tooling; user runtime/library actions are outside this doc. No visible console/browser automation or probes were used to produce this spec; owned disposables: none. Sully commits/pushes this file before implementation citation. Technical startup/restart route proof remains Ender's prerequisite; this doc freezes naming/copy only and grants no unsupported restart mechanism.

## Normal Start-menu restart action — 2026-10-11

This addendum supersedes the deferred-control paragraph above. Ender's supported minimal route uses ordinary user-launched windowless Pythonw processes: the launcher itself runs the web service, without a separate daemon/supervisor child. The restart process must prove its own eligibility and the exact existing owner before requesting shutdown; it waits for the exact old owner to exit and the port/catalog lease to be available, then becomes the replacement. A failed preflight leaves the existing app in place. No tool-host launch bypass, web Restart endpoint/button, new panel, Desktop shortcut, administrator action or file-association change.

### Entry names and normal flow

Use the per-user Start-menu folder **Books Arranger** with two searchable entries:

- **Books Arranger** — opens the normal launch-web.pyw route. Shortcut help: **Open Books Arranger or show its running app.** Reuse a verified healthy owner without changing processing state; otherwise establish readiness before showing the existing browser UI.
- **Restart Books Arranger** — opens restart-web.pyw. Shortcut help: **Restart Books Arranger when it is idle. Saved automatic work stays paused.** This is the actual app restart action, not an instruction to close a console.

README normal instructions: **Open Books Arranger from the Start menu. To restart it, stop or pause active work in the app, then choose Restart Books Arranger.** Keep launch-web.pyw as the direct-file alternative. Existing **Stop server** remains a complete stop, and existing browser processing controls retain their meanings. No extra web Restart button or confirmation dialog is required.

An ordinary restart must finish with the acknowledged existing Paused state and its **Start automatic processing** action; it does not automatically resume scanning, research, conversion or cleanup. Existing browser message, once replacement readiness/current-owner polling is verified: **Books Arranger restarted. Automatic processing is paused.** If no saved automatic pass exists, use **Books Arranger restarted.** and actual Idle state rather than inventing a paused pass. Keep the separate explicit current-update resume contract above: one guarded Start after loaded version/protected state verification, with actual Running/waiting acknowledged before claiming continuation.

### Eligibility and failure feedback

Restart requires an authenticated exact owner, an eligible ordinary replacement process, and no active scan, metadata research, encoder, source cleanup or recovery operation. Reject before shutdown when any prerequisite fails. Never use an unverified process/address as a replacement target. Ender owns detection and race guards; the native message reports the actual failing activity without changing it.

Use existing small native **Books Arranger** failure messages with **OK**, plus the applicable action:

- Scan active: **Books Arranger is scanning. Stop scanning in the app, then choose Restart Books Arranger.**
- Automatic metadata research active: **Books Arranger is researching metadata. Stop automatic processing in the app, then choose Restart Books Arranger.**
- Audiobook conversion/source cleanup active: **Books Arranger is processing an audiobook. Pause audiobook jobs in the app, then choose Restart Books Arranger.** If automatic processing is also active, use **Stop automatic processing and pause audiobook jobs in the app, then choose Restart Books Arranger.** as the action sentence.
- Recovery operation active: **Books Arranger is working with recovery copies. Wait for it to finish, then choose Restart Books Arranger.** Do not suggest cancelling permanent deletion or interrupting its checkpoint.
- Replacement process ineligible: **Books Arranger cannot restart from this session. Use Restart Books Arranger in the Start menu.** Do not expose native Job/process details in the main message or offer a bypass.
- Owner verification fails: retain **Books Arranger could not verify the app to restart. The restart was cancelled.**
- Verified old app has not exited: **Books Arranger is still stopping. Wait for shutdown to finish, then open Books Arranger.** No second restart/duplicate-owner instruction.
- Old owner ended but replacement startup failed: **Books Arranger stopped, but could not restart: [plain-language cause]. Open Books Arranger to retry.** Show retry only after the failed replacement is closed and a fresh launch is safe; otherwise use the authoritative remaining ownership/operation reason.

If Restart has no existing owner, use the startup behavior only if Ender's route explicitly supports it; otherwise say **Books Arranger is not running. Open Books Arranger to start it.** Do not display restart success without a verified replacement. No generic busy message that hides the action, silent failure, guessed cause or indefinite Connecting status.

Restart opens the normal browser UI only when ready. Do not close existing browser tabs or overwrite their unsaved manual edits. The new page/current-owner connection must obtain its own valid session context; an old page cannot label stale old-owner state as replacement success. Repeated Open/Restart actions must remain duplicate-safe.

### Bounded handoff

Ender checks the two Start-menu shortcut targets/labels/help, normal launcher and restart process eligibility, exact-owner preflight/shutdown/lease/readiness, native busy/failure messages, loaded version/current-owner browser status and README instructions. Verify idle restart, each rejected active phase, repeated launch/restart, old-owner exit timeout, failed replacement startup, no-owner path and ordinary Paused versus the one explicitly authorized update continuation. Use isolated approved tooling; do not launch the user's live app as part of this spec. Sully commits/pushes this exact addendum before implementation/installation citation. Docs only; no runtime/library/provider/Comics/code/Git actions or probes; owned disposables: none.
