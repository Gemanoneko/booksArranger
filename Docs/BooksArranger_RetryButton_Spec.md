# Books Arranger: Retry for audiobook jobs that need attention

Date: 2026-10-17. Judy UX spec for Ender. Scope: ONE new control, **Retry**, for audiobook jobs in "Needs attention". Sergei approved adding a retry. Concrete case: a job blocked by leftover working files from an old attempt; the files are now gone and the job cannot be re-run.

Basis: read-only look at `scratch/electron-2026-10-13/worktree/web/` (app.js, index.html, style.css, desktop-ui.js) and a skim of the Python backend only to learn what data exists. Nothing was launched and no rects were measured; geometry below is target geometry for Futaba to measure. Ender owns the eligibility rules; this spec assumes the API supplies, per job, `allowed` plus a short `reason` when not allowed.

## Decision in brief

- **Where:** details panel of the selected book, Automatic result section, directly under the status line and reasons list.
- **Look:** primary (accent) button, visible label **Retry**, at least 96 x 32 CSS px.
- **Unavailable:** the button stays visible and disabled; tooltip and one visible note carry the same reason.
- **Confirmation:** none. Retry is safe and the app re-checks.
- **Feedback:** local to the button (label, note, status line), never the top-of-page message.
- **Keyboard:** one Tab stop, Enter/Space, no shortcut. After success, focus moves to the panel heading.
- **Theme:** the app ships dark only; every pair below clears 4.5:1. No light theme exists to check.

## 1. Where needs-attention is shown today

| Surface | Shows | Per book? | Job's real reason? |
|---|---|---|---|
| Audiobook jobs panel (`#audio-jobs`, `renderJobs`) | Count "N need attention"; one "Current book" line "Needs attention - reason" | No: one book, and only when that job has progress | Yes, for that one book |
| Candidate table: Review status column; filter "Output needs attention" | "Needs attention - reason" per row | Yes | No (see below) |
| Details panel: Automatic result status line (`#automatic-result-status`) | Same string as the table | Selected book | No |
| Details panel: Audiobook output (`#output-status`, `#output-reasons`) | Same string plus creation reasons | Selected book | No |

**Finding.** `candidateStatus()` takes its reason from `automatic.reasons[0]`, then `creation.reasons[0]`, then `cleanup.reason`. For a book with a job, the backend appends "Audiobook job already exists; inspect its current status" to `creation.reasons`, and the job's own failure reason sits in `creation.job.reason`, which no renderer reads. So a needs-attention book can read "Needs attention - Audiobook job already exists; inspect its current status" and never say what was blocked. Without the real reason, Sergei cannot judge "is the blocker gone?" before pressing Retry. See companion change C1.

## 2. Placement and hit area

**Choice: details panel, Automatic result section.** The Retry block sits between the reasons list (`#automatic-reasons`) and the "Held books stay out..." help line (`#automatic-result-help`).

```
Automatic result                                  (h2, existing)
Needs attention - <the job's own reason>          (#automatic-result-status, existing)
  - <automatic reasons, if any>                   (#automatic-reasons, existing)
[ Retry ]                                         NEW  (#retry-job, 32px high, 8px below the list)
<why Retry is unavailable, or the result>         NEW  (#retry-note, only when it has text)
Held books stay out of the queue...               (existing, Held only)
Last attempt: ...
```

Why here:
- Per-book, state-changing actions already live in the details panel (Approve candidate, Create audiobook, Delete recovery copies); row actions are navigation only (View metadata, Open folder).
- The Automatic result section is the first section of the panel and does not sit inside the optional, collapsed Manual review, so it is where an automatic-first user already looks.
- The status line that names the problem is directly above the action that answers it (recognition over recall).

Rejected:
- **Row Actions column.** Rows are rebuilt on every 800 ms poll unless focus is inside the table, a reason sentence has no room in a row, and it would be the only state-changing row action.
- **Audiobook jobs panel toolbar.** It shows one book and a count; a Retry there has no per-book identity (Hick's Law: two Retry-like places would be worse than one).

**Known cost.** The details panel is below the table, and selecting a row does not scroll to it (only View metadata does). Offer O1 below; not part of this spec.

**Geometry (target, border-box = hit area):**
- Button: height at least 32px (existing `min-height:32px` rule for panel buttons), width at least 96px so "Retry" and "Retrying..." do not shift the layout, padding 8px 10px from the base button rule. Always above WCAG 2.2 SC 2.5.8 (24 x 24).
- Gap: button to note 8px (base `p` margin); one `.toolbar` row for the button (10px gap rule); at least 8px between the note and the next element.
- Normal flow only: no absolute, fixed or sticky positioning, no pseudo-element hit extensions, nothing overlapping. The tooltip is the native `title` overlay, which is the dismissible-overlay class the rule allows.
- Narrow (max-width 760px rule) and 200% zoom: block stays stacked, note wraps under the button, no horizontal scroll.

## 3. States

| # | State | When | Button | Tooltip (`title`) | Note line |
|---|---|---|---|---|---|
| 1 | Hidden | API sent no retry data for this job | not rendered (no ghost control) | - | - |
| 2 | Ready | `allowed` true | **Retry**, enabled, primary | Check this book again and queue its audiobook job. | none |
| 3 | Unavailable | `allowed` false | **Retry**, disabled | the API reason | the API reason |
| 4 | Busy | any other request in flight | **Retry**, disabled | Another operation is in progress. | same text |
| 5 | Offline | server ended or connection interrupted | **Retry**, disabled | Local server unavailable. | same text |
| 6 | Closing | desktop quit under way | disabled by the desktop layer | unchanged | none (the Desktop status panel already explains) |
| 7 | Retrying | this book's request in flight | **Retrying...**, `aria-disabled`, disabled look | Checking this book... | Checking this book... |
| 8 | Refused | the app's re-check says no | back to state 2 or 3 from fresh data | per state | the server's message, verbatim, warning color |
| 9 | Connection lost | request fails with no HTTP status | back to state per fresh data | per state | Connection interrupted. Check the status above before trying again. |

Resolution order when several apply: Offline, then Retrying (this book), then Busy, then Unavailable, then Ready (same order as the existing recovery button).

Rules:
- **Disabled has a way out.** A disabled Retry must be fixable by Sergei (files present, jobs running, view stale). For failures that can never be retried, the API should omit retry data (state 1) instead of sending a permanently disabled button. Ender decides which cases are which.
- **Tooltip and note are one string.** Chromium shows `title` on a disabled button, but keyboard users never see a tooltip, so the note is the accessible copy. One source, two displays; this is the same pattern as Start automatic processing and Delete recovery copies.
- **Ellipsis** is the single character `…`, as in "Opening folder…".

## 4. Copy

| Item | String |
|---|---|
| Visible label | Retry |
| Accessible name | Retry: {book title} (title as the recovery dialog derives it: reviewed title, else title clue). Starts with the visible label. |
| Tooltip, ready | Check this book again and queue its audiobook job. |
| Label, pending | Retrying… |
| Note and tooltip, pending | Checking this book… |
| Busy / offline | Another operation is in progress. / Local server unavailable. |
| Connection lost | Connection interrupted. Check the status above before trying again. |

**Rules for API reason strings (Ender writes them, copy standard applies):** one fact, then the fix, at most two sentences, about 90 characters or fewer; sentence case with a final period; no job ids, manifest, ownership, disposal or other internal terms; no "previously" or "no longer". The note must add something the status line does not say, normally the fix. Illustrations only, Ender owns the conditions:
- "Working files from an old attempt are still present. Remove them, then retry."
- "Another audiobook job is running. Retry when it finishes."
- "The book's source files changed. Review the book again."

The existing backend string "Prior audio working files need verified disposal before another source copy" fails the standard (internal terms) and must not reach the screen as written.

Tooltip optional second sentence, "Source files stay untouched.", ships only if Ender confirms Retry never modifies or deletes source files. Otherwise omit it; the tooltip above is complete.

## 5. Confirmation

None. Reasons: Retry is not destructive; the app re-checks eligibility on the server and a refused retry changes nothing; the retry is itself the recovery path for the previous attempt (user control and freedom). A confirm dialog would add a click to every use for no protection. Duplicate submission is prevented by state 7.

## 6. Feedback after clicking

1. **Immediately:** label becomes "Retrying…", the button takes the disabled look (state 7), note reads "Checking this book…". The control keeps keyboard focus (see section 7).
2. **Success (job requeued):** the normal refresh runs; the status line flips from "Needs attention - ..." to "Queued" or "Processing"; the block disappears (state 1); the Audiobook jobs panel counts update ("N need attention" drops, "N queued" rises). The status line is already a polite live region, so assistive tech announces the new status. No toast and no extra confirmation text: the status change is the confirmation (visibility of system status).
3. **Refused:** the server's message appears in the note in the warning color; the button returns to Ready or Unavailable from fresh data.
4. **Connection lost:** the existing connection notice appears at the top; the note says to check the status before trying again, because the request may or may not have arrived.

All feedback is local to the block. Do not use the global `#message`: it sits above the panels, out of sight when the details panel is scrolled into view.

## 7. Keyboard access

- One Tab stop, in DOM order after the status line and reasons. Enter and Space activate (native button). Disabled is not focusable; the visible note carries the reason for keyboard and screen-reader users.
- No accelerator: retry is rare and a global shortcut risks accidental re-runs.
- Focus ring: the existing 3px `--focus` outline with 2px offset applies unchanged.
- While retrying, the button must keep focus: use `aria-disabled="true"`, not the `disabled` attribute, and ignore clicks while set.
- After success the button leaves the DOM; move focus to `#details-heading` (already `tabindex="-1"` with a focus style) using `preventScroll`. Do not move focus into `#automatic-result`: its render guard stops updating while focus is inside it, which would freeze the status line.
- Notes are written only when their text changes, so polling never re-announces the same message.

## 8. Contrast (dark theme; calculated from tokens, not rendered QA)

The stylesheet has `color-scheme: dark` only and no OS-theme detection (default-dark decision, 2026-10-09). The control uses tokens only, so a future light theme inherits it; if one is added, re-check the same pairs.

| Pair | Ratio |
|---|---:|
| Label `--on-accent` on `--accent` (ready) | 9.16 |
| Label on hover `--accent-hover` / pressed `--accent-pressed` | 10.56 / 7.14 |
| Disabled label `--disabled-text` on `--disabled` | 6.07 |
| Note (`.field-help`, `--muted`) on `--surface` | 8.92 |
| Refused note (`--warning`) on `--surface` | 11.18 |
| Focus ring `--focus` on `--surface` | 11.18 |
| Button fill `--accent` vs `--surface` (boundary, non-text) | 8.02 |
| Disabled border `--border` vs `--disabled` (boundary) | 3.22 |

Notes: the 3px focus ring is offset 2px, so it sits against the panel surface, not the button fill (ring on fill alone would be 1.39). Enabled vs disabled differs by fill, label color and the note text, never by hue alone; no color-only meaning for colorblind users. The refused note is identified by its words, not its color.

## 9. What the UI needs from the API (assumed; Ender confirms names)

- Per needs-attention job: `retry.allowed` (boolean) and `retry.reason` (string, required when `allowed` is false). The UI only ever shows the selected book's Retry, so Ender may supply it for the selected or inspected book only if computing it (folder scans) is costly per poll.
- Eligibility must refresh on each poll. The target case is exactly "Sergei cleans up the files, the button turns on within a poll, no restart or reselect".
- The job's own failure reason (`creation.job.reason` today) reaches the status line (C1).
- A retry request that carries the book id and revision shown on screen, so a stale view is refused like other candidate actions. Success returns plain success; refusal returns the existing error shape with a message that meets the copy rules above.

## 10. Constraints for Ender (behavior, not code)

1. **Update in place, every poll.** Drive the block from its own function called from `controls()` (the way `updateRecovery()` works), not from the keyed, focus-guarded `renderAutomaticResult`. If it does go through that key, `creation.job` must be added to it, because the key currently omits job fields. Never recreate the button on a poll.
2. **Pending and result text are scoped to one book** (candidate id plus job id, like `pendingFolders`). Selecting another book clears the other book's note and pending look. While one retry is pending, other books' Retry shows state 4.
3. **Pending uses `aria-disabled`.** Give `#retry-job[aria-disabled="true"]` the same fill, label and border tokens as `button:disabled`, no hover or active change, default cursor. The base `button:enabled:hover` rule would otherwise light it up.
4. **Add `retry-job` to the `mutating` list in `desktop-ui.js`** so it disables during Quit (state 6).
5. **Offline and busy** come from the existing `ended`, `recoveryDisconnected` and `busy` flags, in the section 3 order.
6. **Companion change C1.** `candidateStatus()` should lead with the job's own reason when the job needs attention, so the status line above the block and the block agree. It also corrects the table's Review status column. Without C1 the block shows a button under a misleading reason.
7. **Companion change C2 (one string).** The existing `#automatic-retry` line reads "Retry available after {date}; Start to continue". Two meanings of "Retry" in one section is ambiguous, so change it to "Automatic retry after {date}; Start to continue". If Ender's rules allow Retry during that wait, the button is simply shown; if not, the API reason says so.

## 11. Acceptance checks for Futaba (measured, on a committed build)

- Measure `getBoundingClientRect` for button, note, adjacent status line and next paragraph in states 2, 3 (long reason), 7, 8, 9 at 1440, 1024, 700px and 200% zoom. Pass: button at least 96 x 32; no two rects intersect; 8px gaps; no horizontal scroll; no clipped focus ring.
- With the recovery dialog open, the panel is inert and nothing else covers Retry.
- Keyboard run: Tab to Retry, Enter, focus lands on the panel heading, status line announced. Space also works. Disabled state is not focusable and its reason is visible.
- Poll test: leave focus on an enabled Retry for 10 polls; element identity and focus unchanged. Clean up the files from outside the app with the book selected; the button enables within a poll.
- Double click and click-then-switch-book: one request only; the other book's block shows no stale note.
- Quit during pending: Retry disabled, desktop status panel visible, no covered controls.
- Positive control for the tooltip claim: hover the disabled button in the packaged Electron window and see the `title` text appear (Chromium behavior is relied on, not assumed).
- Long Russian title in the accessible name: geometry unchanged.

## 12. Offers (not specced; your call) and open items

- **O1.** A "Needs attention - N" shortcut beside the existing "Read errors - N" shortcut, filtering to "Output needs attention", would save the hunt from the jobs panel to the book. It would also help find the panel below the table: select-and-scroll on needs-attention rows.
- **O2.** A "Retry all eligible" action on the Audiobook jobs panel if several books block on the same cleanup. Not needed for the stated case.
- **Open for Ender:** (a) does Retry ever touch source files (decides the optional tooltip sentence); (b) is Retry allowed during the automatic one-hour wait (C2 wording); (c) which failures omit retry data versus return a fixable `allowed: false`.
- **Process:** this spec lives in scratch. Per ProcessRules, copy it to `WIP/Books Arranger/Docs/BooksArranger_UXSpec_<date>.md` and have Sully commit it before Ender is briefed.

Design basis: Fitts (action next to the reason it answers), Hick (one placement, hidden when not applicable), Jakob (plain "Retry", native button and tooltip), NN/g visibility, error prevention, user control; WCAG 2.2 AA 1.4.3, 1.4.11, 2.4.7, 2.5.3, 2.5.8, 4.1.3. Doc-only: no code, git or app launch.
