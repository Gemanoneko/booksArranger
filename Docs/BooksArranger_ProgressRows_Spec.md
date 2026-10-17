# Books Arranger: Progress rows in "Audiobook jobs"

Date: 2026-10-17. Judy UX spec for Ender. Scope: how running work is shown in `#audio-jobs`. Sergei's ask: "Show the progress for the current step: write what happens and show progress. If a few tasks run at the same time, show multiple bars. It's important for the user to see the progress, not just a static window."

Basis: read-only look at `web/index.html`, `web/app.js` (`renderJobs`), `web/style.css`, and a token contrast check. Nothing launched; no rects measured. Dark theme only (the app ships no light theme).

## Decision in brief

- One **row per running activity**: activity and book, numeric detail, bar, step text, elapsed/ETA.
- Fixed order: Conversion, Originals cleanup, Identity check, Research/scan. Never reordered by progress.
- Max **4 rows** (one per kind). A 5th+ instance folds into one line "+N more running".
- **Pause/Resume move above the rows**, so no row can cover or move them.
- The rows area reserves room for **2 rows**, so the common 0/1/2 cases never shift the page.
- Every row shows **elapsed**; **ETA** only when it is trustworthy.
- Unknown amount: sliding segment plus ticking elapsed time. Paused: frozen, muted, labelled.

## 1. Panel order (top to bottom)

```
Audiobook jobs                                                      h2, unchanged
12 converted out of 40 approved books - Running - 3 queued - 0 need attention
[ Pause audiobook jobs ] [ Resume audiobook jobs ]     toolbar, MOVED UP, never moves
+---------------------------------------------------------------------------+
| Converting: The Name of the Wind                 1:12:05 of 11:03:40 audio |
| [########---------------------------------------------------------------] |
| Step 3 of 4 - Encoding audio            2:14 elapsed - about 3 min left   |
|                                                                           |
| Removing originals: Dune                                    12 of 40 files |
| [##################-----------------------------------------------------] |
| Removing original files                 0:31 elapsed - about 1 min left   |
|                                                                           |
| Checking finished books                                                   |
| [ sliding segment ======>                                               ] |
| Checking identity                                            0:09 elapsed |
+---------------------------------------------------------------------------+
The approved total grows as more books pass the checks.            help, unchanged
Pausing stops only the owned audiobook operation. ...               help, unchanged
```

The aggregate status line (`#jobs-status`) is unchanged. The old single block (`#book-progress`, `#jobs-book`, `#jobs-phase`, `#jobs-progress`) is replaced by the rows list.

Why the toolbar moves: rows grow and shrink; the buttons are the one thing Sergei aims at. Above the rows they have a fixed position (Fitts) and rows can never overlap them. Help text below the rows is static and may move.

## 2. One row (three fixed lines)

| Line | Left | Right |
|---|---|---|
| 1 | **Activity label** (600 weight, never truncated), colon, subject (book title, ellipsis) | **Detail**: numeric progress, tabular figures, no wrap |
| 2 | Bar, full width | |
| 3 | **Step text**: what is happening now (ellipsis) | **Time**: elapsed, then ETA |

- The list is `<ul id="jobs-rows" aria-label="Running activities">`, one `<li>` per row. No interactive element inside a row.
- Spacing: line 1 to bar 6px, bar to line 3 6px, row to row 14px. Line heights fixed (21px line 1, 20px line 3), so a row is about 61px tall and never changes height while running.
- Type: line 1 15px `--text`; detail 14px `--text` with `font-variant-numeric: tabular-nums`; step 14px `--text`; time 13px `--muted`.
- Subject and step truncate with an ellipsis; the right-hand parts never truncate. Truncated text carries a native `title` with the full string.
- Below 560px panel width, each right-hand part drops under its left part (no clipped numbers).

## 3. Bar

| Property | Value | Check (dark theme tokens) |
|---|---|---|
| Track | `--raised`, 8px high, radius 4px, **1px `--border` outline** | outline 4.13:1 on `--surface`, 3.38:1 on track (3:1 needed) |
| Fill, running | `--accent` | 6.56:1 on track |
| Fill, paused | `--muted`, no motion | 7.29:1 on track |
| Fill, needs attention | `--warning`, no motion, stays at last value | about 9:1 on track |
| Fill, done | `--accent`, full | 6.56:1 |

State is never carried by colour alone: the step text always starts with "Paused - ", "Pausing - " or "Needs attention - " (existing behaviour).

**Determinate:** native `<progress max="100" value=N>`, N = `floor(done / total * 100)`. Never shows 100% before the row is done. Updated at most once per second per row.

**Indeterminate** (flag set, `total` missing or 0, or `done` greater than `total`): `<progress>` without `value`, drawn as a **hard-edged 35%-wide segment** of `--accent` sliding left to right across the track, 1.4s linear, repeating. No pulsing, no colour change. It stops when the row is paused or needs attention (segment parked at the left in `--muted` / `--warning`).
- `prefers-reduced-motion`: no sliding; the track shows static diagonal stripes (`--accent` / `--raised`, 8px bands). Liveness then comes from the ticking elapsed time.
- Indeterminate rows show no Detail text; the ticking elapsed time on line 3 is their proof of life.

**Finishing:** when a determinate step reaches `done` = `total` while still running, switch to indeterminate and keep the step text (today's "Finalizing conversion" behaviour for encoding stays).

## 4. Detail text (line 1, right)

| Unit | Format | Examples |
|---|---|---|
| files | `N of M files` (`1 of 1 file`) | `12 of 40 files` |
| bytes | `X of Y UNIT`; one UNIT (B, KB, MB, GB, 1024-based like Explorer) chosen from the total; one decimal under 10, none from 10 up | `1.2 of 6.1 GB`, `812 of 940 MB` |
| seconds of audio | `h:mm:ss of h:mm:ss audio` (`m:ss` when the total is under 1 h) | `1:12:05 of 11:03:40 audio` |
| no unit, but measurable | `N%` | `35%` |
| indeterminate | empty | |
| done | `Done` | |

Numbers use the OS locale for thousands/decimal separators. One fact per string: percent is not added to unit forms.

## 5. Time (line 3, right)

- **Elapsed**: `m:ss elapsed`, `h:mm:ss elapsed` from 1 h. It counts the current step and resets with the bar. Ticked locally once per second from `step_started_at`, so it costs the backend nothing. On every row. Freezes when paused.
- **ETA** is appended as ` - about N min left` only if the row is determinate and running, step elapsed is at least 10 s, and progress is at least 5%. Forms: `under 1 min left`, `about N min left`, `about H h M min left`. Refresh at most every 5 s from a moving average of the last 30 s so it does not jump. Hidden when paused. No ETA on indeterminate rows.

## 6. Ordering and row count

1. Conversion (current book)
2. Originals cleanup
3. Identity check of finished books
4. Research/scan

Fixed by kind, not by start time or progress, so rows never swap places. Row identity is `kind` (plus `id` if a kind ever has two). A new book in the conversion row resets it in place. Max 4 rows. If the backend sends more, show the first 4 in order and one muted 13px line `+N more running` (no bar).

## 7. Idle, paused, attention, done

| Situation | Shows |
|---|---|
| No activity | One muted line in the reserved area: `Nothing running` |
| Paused, rows exist | Rows stay, frozen; step text `Paused - <step>`; muted fill; elapsed frozen; no ETA |
| Paused, no rows | `Paused. Resume continues pending books.` |
| Pausing | Rows keep moving; step text `Pausing - <step>` |
| Needs attention | Row stays with `Needs attention - <reason>`; `--warning` fill; stays until the job state clears |
| Activity finished | Row shows a full bar and Detail `Done`, then is removed 3 s later. Only when the backend sends state `done`; a row that vanishes for any other reason is removed at once |

## 8. No layout jumping

- The rows area has a `min-height` of 2 rows (about 136px). Idle line, 1 row and 2 rows occupy the same space, so nothing below the panel moves.
- Rows 3 and 4 grow the panel by about 75px each, once, when they appear or are removed (known trade-off, far rarer than 0/1/2 rows). The table below can move then.
- Rows appear and disappear instantly: no fade, no slide.
- Text is written only when it changed; tabular figures plus right alignment keep changing digits from shifting the left column; heights are fixed (section 2). A tick must never change any rect.
- Futaba to measure (rects, not impressions): toolbar rect identical with idle/1/2/3/4 rows; top of the candidate table identical for 0, 1 and 2 rows; no row rect intersects the toolbar rect; row heights equal across ticks.

## 9. Copy (studio standard: short, specific, no memory)

Activity label and step text come from the backend if it sends them; these are the defaults the UI maps from phase keys.

| Row | Label (line 1) | Step text (line 3) |
|---|---|---|
| Conversion | `Converting: <book>` | `Step 1 of 4 - Checking source files`; `Step 2 of 4 - Normalizing audio`; `Step 3 of 4 - Encoding audio`; `Step 4 of 4 - Verifying audiobook` |
| Originals cleanup | `Removing originals: <book>` | `Removing original files`; `Removing temporary recovery and working files`; `Removing empty source folders` (existing strings, unchanged) |
| Identity check | `Checking finished books` | backend step, default `Checking identity` |
| Research/scan | `Scanning files` or `Researching books` | backend step, default `Working` |

- "Step N of 4" explains why the bar returns to 0 at each step.
- Fallback for an unknown phase: the backend's step string, else `Working` (not "Checking source files").
- No internal names, no "previously", no apologies. The reason after "Needs attention - " is the backend's own reason, one sentence.
- Existing Pause/Resume tooltips and help text are unchanged. No new control is added; truncated text gets a `title`.

## 10. Accessibility and contrast (dark)

- Each `<progress>` has `aria-label` = row label and `aria-valuetext` = `<step>, <detail>`.
- Live regions: step text `aria-live="polite"` (changes only at step changes); Detail and Time `aria-live="off"`. The existing `#jobs-status` stays the status announcement.
- Text on `--surface`: `--text` 13.87:1, `--muted` 8.92:1, `--warning` 11.18:1, `--error` 9.12:1, all above 4.5:1. No focus stops are added (rows are not interactive).

## 11. Data assumed from the backend (Ender: correct what differs)

Per activity: `kind` (`conversion` | `cleanup` | `identity` | `scan`), `label`, `subject?`, `step`, `step_index?`, `step_count?`, `done?`, `total?`, `unit?` (`files` | `bytes` | `seconds`), `indeterminate?`, `step_started_at` (epoch ms), `state` (`running` | `pausing` | `paused` | `attention` | `done`), `reason?`. If the backend has no per-row state, derive conversion/cleanup row state from `jobs.state`; research/scan is controlled by Stop/Resume scanning, not by Pause.

## Backend notes (Ender)

(Ender: append here; Judy keeps this section.)

- 2026-10-17, Ender. `/api/state.activities` follows §11, with these differences:
  - Field names: `subject`, `step` (a key), `step_text` (scan and research only), `done`, `total`, `unit`, `indeterminate`, `step_started_at` (epoch ms), `state`, `reason`, plus `step_index` and `step_count` (conversion only, always 4).
  - `label` is not sent; the UI maps labels from `kind` and `step`.
  - `unit` adds `books` (identity check, research), formatted like files: `N of M books`.
  - Measured `files` steps (source preparation) send fractional `done`, so the bar moves within a track; Detail shows the whole number.
  - Kinds: `conversion`, `cleanup` (which also covers temporary-file steps), `identity`, `scan` (which also covers research; `step` is `scanning` or `researching`).
  - State `done` is not sent; rows are removed at once.
- `step_started_at` is exact for conversion steps and the identity check. For the other kinds it is when the server first saw that step (within about 1 s while the window polls).
- Conversion steps map to "Step N of 4" as follows. Each measured sub-step resets the bar, and the step text names it:
  - Step 1: copying and checking source files, then checking source copies.
  - Step 2: checking source audio, choosing the audio format, normalizing audio, checking joined audio. Normalize-mode books only; others go from step 1 to step 3.
  - Step 3: encoding audio.
  - Step 4: verifying audiobook, then copying it to the library.
- One deviation for Judy to confirm: temporary-file and empty-folder steps read `Cleaning up: <book>`, not `Removing originals: <book>`. The temporary step also runs for books whose originals are kept.
