# Books Arranger: "Output needs attention" list, plain status, what to do, Retry and Repair in the row

Date: 2026-10-17 (amended same day: real counts, Retry all confirmation, Damaged class). Judy UX spec for Ender. Scope: the candidate list when Status = "Output needs attention", plus the matching lines in the details panel. Companion to `BooksArranger_RetryButton_Spec.md` (details-panel Retry, already built; its states, copy rules and keyboard rules stay in force). Real counts: `BooksArranger_NeedsAttention_Breakdown_2026-10-17.md`.

Basis: read-only look at `web/app.js` (row render ~L176-206, `candidateStatus` L607, `updateRetry`/`retryJob` L468-512, filter list L10, `error-shortcut` L232/L275) and `web/style.css` tokens. Nothing launched, no rects measured; geometry is target geometry for Futaba. Ender owns classification logic and API.

Sergei's problem: 125 rows with long raw reasons and no next step. The column prints the raw reason, and the screen never says which rows need him and which need nothing.

Shape of the data after 0.16.7: about 121 of the 125 books become supportable and move to Can retry. Expect roughly Can retry 123, Can repair a handful, Other 0-2, M4B not supported 0-2. Design for a list that is almost all one group.

## Decision in brief

- Each row: a short plain status and a one-line hint (what to do, or "nothing to do"). Raw reason on hover and in the details panel.
- One action button per row, first in `.row-actions`: **Retry** (can retry) or **Repair** (damaged). Same request, states and copy as the details-panel Retry; one source, two displays. This reverses the Retry spec's "no row Retry" call, at Sergei's request.
- Group strip above the table while Status = "Output needs attention": All / Can retry / Can repair / Other / M4B not supported, live counts, server-side filtering (the list is paged).
- **Retry all (N): yes, with an inline confirmation.** Repair all: **no**.

## 1. Classes and copy

The API decides the class. The UI never matches English reason text and owns the copy below in one map.

| Group | Who | Review status line | Hint line (muted) | Row button |
|---|---|---|---|---|
| retry | temporary reasons; reasons an update fixed (the ~121 M4B books); any row whose retry is allowed | Stopped — ready to retry | Safe to retry now. | Retry |
| retry, cause = space (optional) | API is sure it is disk space | Stopped — not enough disk space | Free up disk space, then retry. | Retry |
| repair | known, provable damage | Damaged — can repair | the damage line, section 2 | Repair |
| unsupported | M4B the app cannot preserve safely (0-2 books after 0.16.7) | Can't convert — M4B not supported | Nothing to do for now. Originals are untouched. | none |
| other | everything else | Stopped — see details | Select the row to read why. | Retry only if the API sends retry data |

Rules:
- The retry status says "ready to retry", not "temporary problem": for the 121 books the old reason is stale (an update fixed it), and the technical detail still carries the history.
- Unsupported and other rows with no retry data get **no button and no disabled ghost**; a disabled button needs a way out.
- "Originals are untouched." ships only if Ender confirms it for every reason in that group; otherwise "Nothing to do for now."
- No promise of future support. Em dash separator as in "Held — reason". The status no longer starts with "Needs attention"; Ender greps code, tests and strings for that prefix. The filter keeps its name (O3).
- If `job.attention` is missing (older data), fall back to today's text. Never blank.
- Budget: status 40 characters or fewer, hint 70 or fewer (damage hints may wrap to two lines), sentence case, final period on hints only.

## 2. Damaged class: Repair

Damage line = what is wrong, then what Repair does. Plain words; no atom, box, offset or track-number terms. UI map keyed by `damage.kind`; optional amounts only when the API supplies them. Illustrative strings (Ender confirms they match what Repair really does):

| Kind | Hint |
|---|---|
| dangling chapter reference | One chapter mark points past the end. Repair removes it. |
| truncated tail | The end of the audio is missing. Repair fills it with silence. |
| with an amount | The last 42 s of audio is missing. Repair fills it with silence. |
| unknown kind | The app found damage it can patch. Repair fixes it. |

- Repair replaces Retry for that row; a damaged book never shows both (Retry would fail again on the same damage).
- Repair is the Retry control with another label, tooltip and endpoint: same states (hidden, ready, unavailable, busy, offline, pending, refused, connection lost), same order, same shared `busy`/pending state, one action at a time. Pending label "Repairing…" with note "Repairing this book…".
- Tooltip ready: "Patch the damage found in this book, then queue its audiobook job." Accessible name "Repair: {title clue}".
- **No confirmation for a single Repair**, on one condition: Repair works on a working copy and never writes the original files. The hint already states the change, so the click is informed. **If Repair can ever write to an original, STOP and re-brief Judy:** that needs its own confirmation.

After repair (visible, and it persists):
- Row hint, any status (Queued, Processing, Audiobook Ready): "Repaired: {first patch}" plus " +N more" when there are several.
- Details panel, Automatic result, under the status: a "Repaired" line and one bullet per patch. Patch copy, illustrative: "Removed 1 chapter mark that pointed past the end." / "Filled the missing last 42 s with silence."
- Strip status line while the strip is visible (the row leaves this filter): "Repaired. Removed 1 chapter mark that pointed past the end." Stays until the group or filter changes.
- Focus after success: same rule as Retry (section 4).

**Repair all: no.** Each repair changes the content (removed marks, inserted silence) and the cases differ; Sergei should see what each does. Counts will be a handful, so a bulk action saves almost nothing. Revisit if the group passes about 10.

## 3. Row layout

```
Review status cell                                 Actions cell
Stopped — ready to retry                           [ Retry ] [ View metadata ] [ Open folder ]
Safe to retry now.                (13px, --muted)

Damaged — can repair                               [ Repair ] [ View metadata ] [ Open folder ]
One chapter mark points past the end. Repair removes it.

Can't convert — M4B not supported                  [ View metadata ] [ Open folder ]
Nothing to do for now. Originals are untouched.
```

- Status first line (`candidateStatus(row)`), hint second line as `p.field-help` (the existing recording-marker pattern); that marker stays last.
- Status cell `title` = "Technical detail: {raw reason}". Hover only; the details panel is the keyboard path.
- Row Retry and Repair are **`quiet`**, like their neighbours, first in order. With about 120 rows, a filled accent button on every row would be a wall of buttons; the accent fill is reserved for the strip's Retry all and the details panel button. Height 32, **min-width 96** so "Retry", "Retrying…" and "Repairing…" never shift the row. `flex-wrap` may drop View metadata to a second line; fine. Normal flow only.
- Contrast (calculated): hint `--muted` on `--row-selected` 4.97:1, on `--row-hover` 6.64:1, on `--surface` 8.92:1.

## 4. Retry in the row

Reuse `retryKey`, `retryPending`, `retryResult`, `retryJob`; generalize the key and label to Repair. No new state.

- Click: `select(row,false)` (no scroll to the panel), then run the action. `stopPropagation` on click and keydown like the other row buttons.
- Modes and order: Retry spec section 3. Button hidden when the job has no retry or repair data. Tooltip ready (Retry): "Check this book again and queue its audiobook job."
- The row has no note line, so the hint carries the text: ready = class hint; unavailable = the API reason replaces the hint; pending = "Checking this book…" / "Repairing this book…"; refused or connection lost = the server message, or "Connection interrupted. Check the status above before trying again.", in `--warning`. Busy and offline: tooltip only; never rewrite 120 hints because one request is running (other rows' buttons just disable).
- Success: row flips to "Queued" (existing `queuedByRetry`), leaves this filter on the next refresh, counts drop. No toast.
- Focus after success: the forced rebuild removes the button. Move focus to the row for the same book if still listed, else the row now at the same index (or the last), else `#filter`. `preventScroll`.
- No confirmation for single Retry (safe, server re-checks).

## 5. Group strip and counts

Under the Status toolbar row, above the table, only while Status = "Output needs attention". Leaving the filter or "Clear filters" resets it to All.

```
Reason: [ All · 125 ] [ Can retry · 121 ] [ Can repair · 2 ] [ Other · 2 ] [ M4B not supported · 0 ]            [ Retry all (121) ]
```

- Native `quiet` buttons with `aria-pressed` in a `role="group"` named "Output needs attention, by reason". Each is a Tab stop. Selected: `--row-selected` fill, `--text` label (about 7.7:1, calculated), 2px `--accent` border (8.02:1 vs surface); not by hue alone. Height 32, gap 8.
- Strip is `flex-wrap`; counts use `tabular-nums` and may reach 4 digits. Retry all sits at the right end and drops to its own line under about 1024px, never overlapping. No horizontal scroll at 700px or 200% zoom.
- Counts update in place each poll from the server; never rebuild the buttons (focus holds). All five stay visible even at 0 (no layout shift; "M4B not supported · 0" is good news).
- Order: Can retry, Can repair, Other, M4B not supported, also the server sort inside All, so actionable books land on page 1.
- Empty list and page text reuse current strings with the label "Output needs attention · {group}". With about 120 rows the page text ("Showing 1-50 of 121") is what tells Sergei the group is larger than the page; Retry all always acts on the whole group.
- Tooltips: "Show all 125 books that need attention." / "Show books you can retry now." / "Show books with damage the app can repair." / "Show books that stopped for another reason." / "Show M4B books the app cannot convert safely." (125 is the live total.)

## 6. Retry all (N): yes, with confirmation

**My call: confirm, always, inline.** For N around 120 a mistaken click queues a long, disk-heavy run (remuxing large M4B files, behind the books already queued) with no known one-click undo. The label count alone is too easy to skim past. It is a rare action, so one extra click costs almost nothing. Single Retry and single Repair stay unconfirmed. (Without a confirm it would be defensible only for small N; a threshold would make the control behave differently day to day, so confirm at every N.)

- Button "Retry all (121)", primary, 32 high, right end of the strip, only while group = Can retry and N is 2 or more. Never in All; never an equivalent for Repair.
- Tooltip: "Check these 121 books again and queue each audiobook job."
- Click swaps the button, in place and in the same strip (no dialog, nothing covers anything), for: "Queue 121 books to be checked again? They run one at a time, after the 276 already queued. Originals stay untouched." then **[ Queue 121 books ]** primary and **[ Cancel ]** quiet. Focus lands on **Cancel** (safe default); Esc cancels and returns focus to Retry all; the count in the label repeats. Polls never rebuild this block. "after the N already queued" is shown only if the status payload carries the queued count; "Originals stay untouched." only if Ender confirms.
- On confirm: acts on every book in the group (server count, not the visible page), one at a time through the existing queue, never in parallel; the server re-checks each book.
- Feedback in the strip's status line. The live region announces only the start ("Retrying 121 books.") and the end ("Queued 119 of 121. 2 could not be retried."). The running counter ("37 of 121") updates in an `aria-hidden` span so it does not flood screen readers. Refused books stay listed with their reason in the hint. The end line stays until the group or filter changes; no timers.
- While running: Retry all, the confirm pair and every row button are disabled (busy); focus stays on the status line target. On finish focus moves to the "Can retry" group button.
- If Ender finds no cheap bulk path, ship rows and strip first and add this after.

## 7. Details panel

- `#automatic-result-status` and `#output-status` show the same short status (they already call `candidateStatus`).
- Directly under the status: the same hint. The existing Retry block becomes the action block: its button reads Repair for the repair group; the unavailable reason stays in the existing note, not duplicated in the hint.
- After repair: the "Repaired" line and bullets (section 2), permanent.
- Last line of the block: "Technical detail: {raw reason}", `.field-help`, `overflow-wrap:anywhere`, never truncated, selectable.
- Add `job.attention` and the repair record to the render key (L629 omits them today), or the hint goes stale.

## 8. What the UI needs from the API (names assumed; Ender confirms)

- Per job: `attention.group` = `retry` | `repair` | `unsupported` | `other`; optional `attention.cause` = `space`; `attention.damage` = { kind, optional amounts }; `retry` and `repair` objects each with `allowed` / `reason`; `repair_result.patched[]` ({ kind, amount }) kept permanently. Raw text stays in `job.reason`.
- Group rule: `repair` when the damage is provable and Repair is offered; `retry` for temporary reasons, reasons an update fixed, and any row whose retry is allowed; `unsupported` for the M4B preservation reasons that remain; `other` for the rest.
- Status payload: `attention_counts` { retry, repair, other, unsupported } beside `unresolved_errors`, and the queued-job count if available.
- List request: existing `output_attention` filter plus a group parameter, and the sort above.
- Endpoints: repair, and a bulk retry returning per-book result counts. Repair carries book id and revision like Retry.

## 9. Acceptance checks for Futaba (measured, committed build)

- Copy: every row in every group shows the section 1 and 2 strings verbatim; none shows `Errno`, "database is locked", "brand", "box" or "decoder" outside the Technical detail line and hover title.
- Counts: strip counts equal the server's and change within a poll after an action; All equals the Jobs panel "N need attention".
- Rects at 1440, 1024, 700 and 200% zoom: row Retry/Repair at least 96 x 32; strip buttons at least 32 high; no two rects intersect (strip with 3-digit counts, confirm text and both buttons included); no horizontal scroll; no clipped focus ring; "Retrying…" and "Repairing…" do not change row size.
- Keyboard: Tab to a row button, Enter; focus lands per section 4; group buttons toggle and announce pressed; leave focus on a row button for 10 polls: same element, nothing lost.
- Retry all at about 120 books: label shows the whole-group count while the page shows 50; click shows the confirm with focus on Cancel; Esc cancels; confirm runs; screen reader announces start and end only; one forced refusal reads "Queued 119 of 121" and that book keeps its reason; Quit during the run disables everything.
- Repair: a seeded damaged book shows the damage line and Repair, no Retry; after Repair the row shows "Repaired: …", the details panel lists each patch, the strip line appears, and the record survives a restart. Original files unchanged (hash before and after).
- Double click, two rows quickly, click then Quit: one request, no stale hint on the wrong row.
- Tooltip positive control in the packaged window; unsupported and other rows without retry data have no button.

## 10. Offers and open items (not specced)

- **O1.** A "Can retry · N" shortcut beside "Read errors · N" (hidden at 0), same pattern as `error-shortcut`.
- **O2.** The Audiobook jobs panel "Current book" line still prints the raw reason; give it the same short status.
- **O3.** Rows read "Stopped" / "Can't convert" while the filter and Jobs panel say "needs attention". Consider renaming the filter later.
- **Open for Ender:** (a) "Originals are untouched." true for every unsupported and retry reason; (b) Repair never writes originals (if it does, see section 2); (c) bulk retry path and whether queued jobs can be paused or cancelled in bulk (if yes, the confirm text can say so); (d) queued count in the status payload; (e) can the API tell `space` apart; (f) where the two M4B leftovers land ("Top-level extent invalid" looks malformed, so likely Other; "presentation bounds cannot be verified" likely M4B not supported); (g) can class retry ever have `retry.allowed` false, and why.
- **Process:** this file is in the worktree. Per ProcessRules it is copied to `WIP/Books Arranger/Docs/` and committed by Sully before Ender is briefed.

Design basis: Hick (five groups, one action per row), Fitts (action beside the hint that explains it), Jakob (native buttons, title tooltips, pressed toggles, safe-default confirmation), NN/g visibility of status, error prevention and plain-language recovery; WCAG 2.2 AA 1.4.3, 1.4.11, 2.4.7, 2.5.3, 2.5.8, 4.1.3. Doc-only: no code, git or app launch.
