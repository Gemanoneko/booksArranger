# Books Arranger — Google human verification and source status

Date: 2026-10-13. Judy UX specification. EXTEND Books Arranger v0.14.0, browser UI only (`web/index.html`, `web/style.css`, `web/app.js`). Sergei approved the flow (Brief, Sergei decisions — search channels, 2026-10-12). Pattern source: the Google Lens flow in Comics Meta Organizer (`static/lens-control.js`, its status line and one button). This spec matches that interaction where it fits and notes each place it differs.

Scope: the notice, its one button, six states plus transitions, Stop/restart behavior, keyboard/focus rules, contrast, and one compact source-status line in the automatic status block. Not in scope: backend transport, the headed-window mechanism, network guards, profile handling (Ender), candidate status and inspector copy (unchanged), any new panel or modal. No code, no commits, no app run.

Design basis: NN/g visibility of system status, user control and freedom, error prevention; Hick's Law (one action, shown only when it applies); Fitts's Law (the button sits next to the message); Jakob's Law (native button, no custom widgets); WCAG 2.2 AA. See `Team/Research/UX_AppBestPractices.md`.

## 1. Decisions this spec enforces

- Google needing a human check never changes **Automatic processing** state, research counts (researching/waiting/held) or any candidate status. The run stays Running and other sources continue. No Needs attention, no modal, no toast, no sound, no tab-title change, no desktop notification.
- The Google window opens only from an explicit click on the button. Page load, polling, reconnect, Start, Resume, timeout and a re-challenge never open one.
- Nothing steals focus: the page moves keyboard focus only when the focused element is the verification button itself and that button changes or disappears (section 7). Opening and minimizing the window must not activate any other window.
- The wait is bounded. It starts when the window opens, not when the notice appears. With no click there is no timer: Google simply stays paused and the notice stays visible.
- Default wait limit: 10 minutes from window open (the comics tool's 600 s). One-word confirm requested from Sergei (questions below).

## 2. State map

| # | State | Google in source line | Row tone | Button |
|---|---|---|---|---|
| 1 | Not needed | `active` | row empty, zero height | hidden |
| 2 | Verification needed (Google paused) | `needs you` | attention | **Open Google verification**, enabled |
| 3a | Opening (after click, window not yet confirmed) | `needs you` | attention | **Opening Google window…**, disabled |
| 3b | Window open, waiting | `needs you` | attention | **Google window open**, disabled |
| 3c | Closing (after timeout, cancel or failure) | `needs you` | attention | **Closing Google window…**, disabled |
| 4 | Solved | `active` | quiet | hidden |
| 5 | Timed out / closed / failed | `needs you` | attention | **Retry Google verification**, enabled when restartable, else disabled |
| 6 | Unavailable | `unavailable` | quiet | hidden, or disabled if it was visible |
| P | Run paused (Stop or restart) with Google still needing a check | `needs you` | quiet | hidden |

## 3. Placement and layout

Everything lives in the existing first panel, inside `#automatic-status-block` (so it is Audiobooks-only, like the rest of automatic status). Normal document flow only: no overlay, no fixed or absolute positioning, no popover, no dialog. Order in the block, top to bottom:

1. `#automatic-status`, `#automatic-request`, `#automatic-detail` (unchanged)
2. `#research-status`, `#research-current` (unchanged)
3. **New `#search-sources`**: the one-line source status (section 4)
4. **New `#google-verification`**: the notice row (status text + button)

The panel's `Discovery only` toolbar follows. Tab order is therefore: Start automatic processing, Stop automatic processing, Open Google verification (only while present), Start scanning, and so on. The row sits directly under the source line that says `Google: needs you`, so the cause and the action are adjacent.

Row geometry (design targets; Futaba measures the real rects):

| Item | Value |
|---|---|
| Row container | flex, wrap, `align-items:center`, column gap 16px, row gap 8px, margin 8px 0, padding 8px 12px, `border-left:3px solid` (a real border, never a box-shadow, so it survives forced-colors mode) |
| Status text | `p`, margin 0, `flex:1 1 320px`, `min-width:0`, `overflow-wrap:anywhere`, 15px/1.5 |
| Button | existing `button` styling, `min-height:32px`, padding 8px 10px, `flex:none`, `white-space:nowrap` |
| Expected height at 1440px | about 48px with button, about 38px without |
| At 760px and below | status takes the full row, button wraps below it, `white-space:normal`, `max-width:100%` (same pattern as `#automatic-controls`) |
| Collapsed (state 1) | the live region stays in the DOM; container padding, border and margin go to 0 and the status text is empty with margin 0, so zero height. Never `hidden` or `display:none` on the live region (screen readers may miss text added to a hidden region). Only the button uses `hidden`. |

New utility rule needed: `.sr-only` does not exist in `style.css`. Add the standard clipped visually-hidden class (1px box, `clip`/`clip-path`, no `display:none`).

Layout shift: the row appearing or disappearing moves the Discovery controls by about 38-48px. This matches the existing dynamic lines (`#automatic-detail`, `#research-current`) and is accepted. The row never appears under a click the user just made on another control, because it appears only from backend state.

## 4. Source status line (`#search-sources`)

One compact line, 13px, text color, directly under the research lines. It names the source groups in use this run and which are paused, as the backend reports them.

Grammar: `Name[, Name]: state` items joined by ` · `. Items sort by attention: `needs you`, then `paused …`, then `unavailable`, then `active`. Groups with identical state text merge into one item. Non-active states are font-weight 600; `active` is normal weight (weight, not color alone, marks the difference).

Fixed group order and names (Ender maps real source ids to these groups and reports the mapping): **Google** (browser search), **DuckDuckGo**, **Catalogs** (Open Library, Google Books, iTunes), **Reference** (FantLab, Wikidata, Wikipedia). Show only groups enabled for this run. Four items at most.

State words:

| Word | Meaning |
|---|---|
| `active` | Group is being used. A group is active while any member is usable; routine request spacing is still active. |
| `needs you` | Only Google. Google searches are paused until a human verification passes. |
| `paused 1 h` | Backend will not call the group until its resume time. Remaining time rounds up: under 1 min `paused <1 min`; 1-59 min `paused N min`; 60 min to 23 h `paused H h` or `paused H h M min`; 24 h or more `paused N d`. Recomputed from the backend resume time each render, never from a stale duration. |
| `unavailable` | Group cannot be used (setup problem, not a timed pause). |

A merged group shows `paused` or `unavailable` only when every member is. The paragraph `title` lists members and their individual states for mouse users (convenience only; nothing essential lives there, and the paragraph is not focusable).

Examples:

```
Google, DuckDuckGo, Catalogs, Reference: active
Google: needs you · DuckDuckGo: paused 1 h · Catalogs: active          <- Sergei's example
Google: needs you · DuckDuckGo, Catalogs, Reference: active
Google: unavailable · DuckDuckGo: paused 42 min · Catalogs, Reference: active
Google: needs you · DuckDuckGo, Catalogs: paused 1 h · Reference: active
Last confirmed — Google: needs you · DuckDuckGo: paused 1 h · Catalogs: active
Source status unavailable
```

Rules: a screen-reader-only prefix `Sources: ` precedes the line. The line is `aria-live="off"`: its minute-by-minute duration changes must not be announced; meaningful changes are announced by the verification row's live region. When the page is disconnected, prefix `Last confirmed — ` like the existing automatic lines. Missing or malformed telemetry reads exactly **Source status unavailable**; never invent `active`.

## 5. States, copy and mockups

Copy standard applied: one fact per string, name the actual thing and action, no internal names, no history, and **Other sources continue.** appears only when at least one other group is actually `active` (otherwise that sentence is dropped). Times are local clock `HH:mm`, no seconds and no timezone (within the 10-minute window). The deadline text is a fixed clock time, never a ticking countdown, so nothing in the live region changes every second. If the backend gives no deadline, omit the time sentence.

Legend for mockups: `|` is the 3px accent edge (attention), `:` is the 3px quiet edge, `[ ... ]` is the button, `(disabled)` marks a disabled button. Mockups show the status block of the first panel at 1440px.

### State 1 — Not needed

Row is empty and collapsed. Source line only.

```
+--------------------------------------------------------------------------------------------+
| Automatic processing: Running                                                              |
| Metadata research: 2 researching · 1 waiting · 3 held                                      |
| Current research: Дюна — Catalogs / lookup                                                 |
| Google, DuckDuckGo, Catalogs, Reference: active                                            |
| Discovery only  [Start scanning] [Stop scanning] [Resume scanning]                         |
+--------------------------------------------------------------------------------------------+
```

### State 2 — Verification needed (Google paused)

| Item | Copy |
|---|---|
| Status (live, polite) | **Google paused — verification needed. Other sources continue.** |
| Button | **Open Google verification** |
| Tooltip and help | **Open a Google window to complete the verification. Google searches resume once it passes.** |

```
+--------------------------------------------------------------------------------------------+
| Automatic processing: Running                                                              |
| Metadata research: 2 researching · 1 waiting · 3 held                                      |
| Current research: Дюна — Catalogs / lookup                                                 |
| Google: needs you · DuckDuckGo: paused 1 h · Catalogs, Reference: active                   |
| | Google paused — verification needed. Other sources continue.   [ Open Google verification ] |
| Discovery only  [Start scanning] [Stop scanning] [Resume scanning]                         |
+--------------------------------------------------------------------------------------------+
```

The page does not move focus here, does not scroll to the row and does not play a sound. The polite live region announces the status text once.

### State 3a — Opening

Reached on click, immediately (button disabled to block double submission) and confirmed by the backend `opening` phase. If the request fails, the row returns to state 2 and the existing `#message` line reads **Could not open the Google window. Try again.**

| Item | Copy |
|---|---|
| Status | **Opening the Google window…** |
| Button (disabled) | **Opening Google window…** |
| Tooltip and help | **The Google window is opening.** |

```
| Google: needs you · DuckDuckGo: paused 1 h · Catalogs, Reference: active                   |
| | Opening the Google window…                                 [ Opening Google window… ] (disabled) |
```

### State 3b — Window open, waiting

| Item | Copy |
|---|---|
| Status | **Complete the verification in the Google window. Waiting until 14:32.** |
| Button (disabled) | **Google window open** |
| Tooltip and help | **Complete the verification in the open Google window. It closes at 14:32 if unfinished.** |

```
| Google: needs you · DuckDuckGo: paused 1 h · Catalogs, Reference: active                   |
| | Complete the verification in the Google window. Waiting until 14:32.   [ Google window open ] (disabled) |
```

Other sources keep researching while the window is open; counts and Current research lines keep updating as usual. The window itself is a separate browser window (not part of this UI).

### State 3c — Closing

Shown briefly after timeout, Stop, a closed or failed window, before the backend confirms the window is gone.

| Item | Copy |
|---|---|
| Status | **Closing the Google window…** |
| Button (disabled) | **Closing Google window…** |
| Tooltip and help | **Waiting for the Google window to close.** |

### State 4 — Solved

Quiet tone, no button. Appears when the backend confirms the check passed and Google is usable again.

| Window state | Status copy |
|---|---|
| minimized | **Google verified. Keep its window open for later searches; minimized is fine.** |
| still open on screen | **Google verified. Minimize its window and keep it open for later searches.** |

```
| Google, DuckDuckGo, Catalogs, Reference: active                                            |
| : Google verified. Keep its window open for later searches; minimized is fine.             |
```

The quiet line stays while the verified window exists, because closing that window loses the verified session. It disappears (collapses) when the window is gone. If Google challenges again, the row returns to state 2.

### State 5 — Timed out, closed or failed (with Retry)

Same row, attention tone. The button is **Retry Google verification**. Retry is explicit like the first click: it opens one new window and nothing re-opens by itself.

| Backend outcome | Status copy |
|---|---|
| timeout | **Google verification timed out. Other sources continue.** |
| user closed the window | **The Google window closed before verification finished.** |
| window could not open | **The Google window could not open. Try again.** |
| page could not load | **The Google page could not load. Try again.** |
| interrupted | **Google verification was interrupted. Try again.** |

| Button state | Tooltip and help |
|---|---|
| Enabled | **Open a new Google window to try the verification again.** |
| Disabled, window not yet confirmed closed | **Waiting for the previous Google window to close.** |
| Disabled, browser not ready | **Google verification isn't ready. Waiting for its browser to start.** |

```
| Google: needs you · DuckDuckGo: paused 1 h · Catalogs, Reference: active                   |
| | Google verification timed out. Other sources continue.      [ Retry Google verification ] |
```

### State 6 — Unavailable

Quiet tone. Two causes, two strings:

| Cause | Status copy | Button |
|---|---|---|
| Verification status unreadable (status request failed, unknown phase, backend says not alive) | **Google verification status unavailable.** | Hidden; if it was visible, it stays visible and disabled so the layout does not jump |
| Verification cannot start on this machine | **Google verification is unavailable. Research continues without Google.** | Hidden |

Disabled-button tooltip and help: **Google verification status unavailable. Waiting for the local service.**

```
| Google: unavailable · DuckDuckGo: paused 1 h · Catalogs, Reference: active                 |
| : Google verification is unavailable. Research continues without Google.                   |
```

A lost page connection is handled by the existing connection notice: the row keeps the last confirmed text prefixed **Last confirmed — ** and the button is disabled with tooltip **Connection interrupted. Waiting for the local service.** A failed poll never rewrites the row to Not needed or Solved.

### State P — Run paused (Stop or server restart)

Quiet tone, no button. Shown only when Google still needed a check when research stopped.

| Item | Copy |
|---|---|
| Status | **Google paused — verification needed. Start automatic processing to continue.** |

```
| Automatic processing: Paused                                                               |
| Paused — pending work saved                                                                |
| Google: needs you · DuckDuckGo, Catalogs, Reference: active                                |
| : Google paused — verification needed. Start automatic processing to continue.             |
```

### Narrow layout (700px, 200% zoom)

```
+-----------------------------------------+
| Google: needs you · DuckDuckGo: paused  |
| 1 h · Catalogs, Reference: active       |
| | Google paused — verification needed.  |
| | Other sources continue.               |
| | [ Open Google verification ]          |
+-----------------------------------------+
```

Text wraps, the button drops under the text at full available width, and nothing truncates with an ellipsis.

## 6. Behavior on Stop, pause, restart and other events

Stop automatic processing (acknowledged Paused), server restart, run completion and Needs attention all end the Google wait for this run. Pause audiobook jobs does not: it pauses only conversion, and verification keeps its state.

| Event | Pending request or open unsolved window | Solved window | Row afterwards |
|---|---|---|---|
| **Stop automatic processing** | Request cancelled; an unsolved window is closed by the app (state 3c while closing); no timer remains | Stays open (reused on Start) | State P if Google still needs a check, else collapsed |
| **Server restart** (restart-paused run) | Cancelled; the window dies with the process; nothing is re-requested and nothing opens on Start | Closed with the process | Backend decides whether a needs-you flag persists; recommended: cleared, so the next Google search re-detects. The row shows only acknowledged state |
| **Run completes / Needs attention** | Same as Stop | Same as Stop | Collapsed |
| **Start automatic processing** | Not applicable | Reused | If Google is still challenged, state 2 returns and waits for a click |
| **Pause / Resume audiobook jobs** | No effect | No effect | Unchanged |
| **Stop server / full Quit** | Window closed with the app; no orphan browser | Closed | Not shown |
| **Tab closed, reloaded, reconnected** | No effect on the window or timer; the page only displays acknowledged state | No effect | Repainted from state; never opens a window |
| **User closes the Google window** | Ends the wait | Closes the verified session | State 5 (closed) if unsolved; state 2 at the next challenge if it was solved |
| **Another library selected** | No effect | No effect | Row follows the status block's Audiobooks-only visibility (same limit as all automatic status) |

While the run is Paused no verification button is offered, as in the Lens flow (paused shows text only). Solving only helps research that is running.

## 7. Keyboard, focus and announcements

- The control is one native `<button type="button">`. Tab reaches it after Stop automatic processing and before Start scanning; Enter and Space activate. No custom shortcut (one rare action does not justify one) and no Escape behavior (it is not a dialog).
- The status paragraph is `role="status"`, `aria-live="polite"`, `aria-atomic="true"`, `tabindex="-1"` (programmatic focus only, never a Tab stop). Update text only when it changes, so identical polls announce nothing.
- Focus rule, adapted from the Lens flow: record whether the button had focus when it was activated. When the button becomes disabled or hidden while it still holds focus, move focus once to the status paragraph (`preventScroll`). Do nothing if focus is elsewhere, on another control, or if the page is not the foreground window. When a Retry button appears, do not focus it. Any focus move elsewhere cancels the pending "return focus" intent.
- The button has `title` and `aria-describedby` pointing at an `.sr-only` span holding the same tooltip text, updated with each state (as the Lens button does). Tooltip text for every state is listed in section 5.
- Polls do not rebuild the button or status element; update text and attributes in place so a focused button is not replaced.
- Responses requested before a click must not repaint the row as enabled afterwards. Ignore any state whose `updated` value is older than the last applied one.
- Focus ring: existing `button:focus-visible` (3px `--focus`, 2px offset). Row padding keeps the ring unclipped; no `overflow:hidden` on the row or its parents in this block.

## 8. Color and contrast

All colors are existing default-dark tokens; no new tokens. No animation, transition or pulse anywhere. Ratios computed with the same sRGB luminance method as the accepted dark-theme spec (the method reproduced that spec's 13.87, 4.13, 9.16, 6.07, 3.22, 11.18 and 9.12 values before use). Palette checks, not rendered-screen QA.

| Pair | Ratio | Requirement | Result |
|---|---:|---|---|
| `--text` on `--surface` (attention text, source line) | 13.87:1 | 4.5:1 | pass |
| `--muted` on `--surface` (quiet text) | 8.92:1 | 4.5:1 | pass |
| `--accent` edge on `--surface` | 8.02:1 | 3:1 | pass |
| `--border` edge on `--surface` (quiet edge) | 4.13:1 | 3:1 | pass |
| `--on-accent` on `--accent` (enabled button label) | 9.16:1 | 4.5:1 | pass |
| `--disabled-text` on `--disabled` (disabled label) | 6.07:1 | 4.5:1 | pass |
| `--border` on `--disabled` (disabled button edge) | 3.22:1 | 3:1 | pass |
| `--focus` on `--surface` (focus ring) | 11.18:1 | 3:1 | pass |

Attention uses the accent edge, not `--warning` or `--error`: this is expected, recoverable and not alarming. State is never carried by color alone: every state has distinct words, the button label changes, and non-active source states are bold.

Light theme: none exists. The app is explicitly dark (`color-scheme: dark`, no OS-theme detection). Use tokens only, no literal colors, so a future light theme inherits. Forced-colors mode: edges are real borders and keep their weight.

## 9. Hard rules (acceptance, not preferences)

1. **Explicit click only.** Zero windows open until the button is clicked. A click opens exactly one window. The count of windows opened by poll, load, reconnect, Start, Resume, Stop, restart and timeout is zero.
2. **No focus theft.** Detection of a challenge, the notice appearing, the window opening from a click, solving, the automatic minimize, and every later Google search through the minimized window must not change the OS foreground window or flash the taskbar entry beyond the single OS-default activation of a user-initiated open. The minimized window never restores itself.
3. **No sound.** The kept-open window and the notice must not autoplay audio.
4. **No covering.** Row, status text, button, source line, research lines and Discovery buttons never overlap in any state, at any width, at 200% zoom.
5. **No orphan.** The window and its browser end on Quit, Stop server and run end (unsolved) as in section 6.
6. **No false claim.** `Other sources continue.` only when another group is active; no `active` without telemetry.

## 10. Facts the page needs from the backend (Ender reconciles with the Lens-style phases)

| Fact | Used for |
|---|---|
| `google_verification.phase`: idle, required, opening, open, closing, verified, failed | states 1-6 |
| `window`: closed, open, minimized | state 4 copy, retry enablement |
| `failure`: timeout, closed, open, load, interrupted | state 5 copy |
| `deadline_at` (epoch), present while `open` | state 3b time |
| `restartable` (window confirmed closed and browser ready) | Retry enabled or disabled and its tooltip |
| `updated` (monotonic) | ignore out-of-order responses |
| per-group `sources[]`: group, state (`active`, `needs_you`, `paused`, `unavailable`), `resume_at` | section 4 line |
| run state, including `restart_paused` | state P and section 6 |

The click request is idempotent: a second click while `opening` or `open` is a no-op. A failed request returns the row to state 2 and shows the `#message` text from state 3a. Ender reports back before building: (a) restart persistence of a needs-you flag, (b) whether Stop can close an unsolved window without activating another window, (c) the group mapping, (d) a request and cancel contract that survives restart, and (e) any case where the 10-minute limit or the closed-window detection cannot be honored.

## 11. Verification for Futaba (after Ender builds)

- Measure actual rectangles in every state in section 2 at 1440px, 700px and 200% zoom: row, status text, button, source line, research lines, `Discovery only` buttons. No intersection; focus ring not clipped; button at least 24x24 CSS px (target 32px tall); expected row heights as in section 3.
- Contrast: computed colors on the real elements, dark theme, each tone, disabled and focused.
- Positive controls: a deliberate stub that opens a window on poll and a stub that calls `focus()` must be seen to fail the rule 1 and rule 2 checks before those checks count.
- Behavior: a mock challenge triggers state 2; click yields exactly one window; solve yields state 4 and a minimized window; timeout (shortened by a test setting) yields state 5; a closed window yields state 5 (closed); Retry opens one new window; Stop mid-wait closes an unsolved window and cancels the request; restart leaves no window and no auto-open; Pause audiobook jobs changes nothing here; disconnected shows last-confirmed text and a disabled button; source line renders each example in section 4 including merge, sort, duration rounding, long Russian title in Current research above it, and missing telemetry.
- Focus: tab order; activating by keyboard moves focus to the status paragraph once; focus elsewhere is untouched by polls.
- Safety: the real headed window and real Google are tested only with a mock challenge page and a throwaway profile (never Sergei's browser profile), and any real-input headed check runs in an away window Sergei states in chat. Headless browsers start only through `scripts/qa/headless-browser.mjs`.

## 12. Handoff

Doc-only. No code, probes, Git operations, app launch or port 5210 access; own disposable output: none. Contract ends to check: the verification state endpoint and click/cancel requests, source-group telemetry, Stop/restart/run-end handling, the browser window lifecycle, `index.html` markup, `style.css` (`#search-sources`, `#google-verification`, `.sr-only`, the 760px reflow), `app.js` rendering and focus handling, README/Brief copy that mentions Google verification. Sully commits and pushes this exact file before Ender cites or implements it; Ender reports any contradiction rather than shipping a misleading state.

Offered, not specified (Sergei decides): a Cancel button while the window is open (Stop already cancels); a desktop notification or tab-title badge when verification is needed (deliberately omitted under the no-intrusion rule); a user-set wait limit.

Questions for Sergei, one word each:
1. Wait limit once the window opens: 10 minutes (same as the comics tool). OK, or give a number?
2. After solving, keep the quiet line "Google verified. Keep its window open…" visible while the window stays open, or hide it after one minute? keep / hide

## Sergei answers (2026-10-13)

1. Wait limit after the verification window opens: 10 minutes (same as the comics tool). Approved.
2. The "Google verified…" line hides after one minute.
