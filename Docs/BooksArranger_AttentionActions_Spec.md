# Books Arranger: "Output needs attention" list, plain status, what to do, row actions

Date: 2026-10-17, amended 2026-10-17 (real counts, Retry all confirmation, Damaged) and 2026-10-18 (0.16.8 kept files). Judy UX spec for Ender. Scope: the candidate list when Status = "Output needs attention", plus the matching lines in the details panel. Companion to `BooksArranger_RetryButton_Spec.md` (details-panel Retry, already built; its states, copy rules and keyboard rules stay in force). Real counts: `BooksArranger_NeedsAttention_Breakdown_2026-10-17.md`.

Basis: read-only look at `web/app.js` (row render ~L176-206, `candidateStatus` L607, `updateRetry`/`retryJob` L468-512, filter list L10, `error-shortcut` L232/L275) and `web/style.css` tokens. Nothing launched, no rects measured; geometry is target geometry for Futaba. Ender owns classification logic and API.

Sergei's problem: 125 rows with long raw reasons and no next step. The column prints the raw reason, and the screen never says which rows need him and which need nothing.

Shape after 0.16.7 and 0.16.8: about 121 of the 125 books move to Can retry; M4B not supported falls to 0-2; Can repair, Original changed and Audiobook problem are a handful each. Design for a list that is almost all one group.

## Decision in brief

- Each row: a short plain status and a one-line hint (what to do, or "nothing to do"). Raw reason on hover and in the details panel.
- One remedy button per row, first in `.row-actions`: **Retry**, **Repair**, **Check again** or **Convert again**; kept-file rows add **Keep files**. All share the Retry machinery: one request at a time, aria-disabled while pending, row flips to "Queued", no double-press.
- Group strip above the table while Status = "Output needs attention": live counts, server-side filtering (the list is paged).
- Confirmation: **Retry all** and **Check again** yes (existing dialog pattern); everything else no. Repair all: no. Bulk actions for the kept-file groups: no.

## 1. Classes and copy

The API decides the class. The UI never matches English reason text and owns the copy below in one map. "Recovery copies" is the app's existing term (the recovery dialog and "Delete recovery copies"); Sergei says "backups", so see open item (h).

| Group (strip label) | Who | Review status line | Hint line (muted) | Row buttons |
|---|---|---|---|---|
| Can retry | temporary reasons; reasons an update fixed (the ~121 M4B books); any row whose retry is allowed | Stopped — ready to retry | Safe to retry now. | Retry |
| Can retry, cause = space (optional) | API is sure it is disk space | Stopped — not enough disk space | Free up disk space, then retry. | Retry |
| Can repair | known, provable damage | Damaged — can repair | the damage line, section 2 | Repair |
| Original changed | 0.16.8 kept files (A): the original's content no longer matches what was checked | Original changed since checked | Recovery copies are kept until you decide. | Check again, Keep files |
| Audiobook problem, cause = missing | 0.16.8 kept files (B): no converted audiobook | Audiobook missing | Recovery copies are kept until you decide. | Convert again, Keep files |
| Audiobook problem, cause = unverified | 0.16.8 kept files (B): audiobook exists but is not verified | Audiobook not verified | Recovery copies are kept until you decide. | Convert again, Keep files |
| M4B not supported | M4B the app cannot preserve safely (0-2 books) | Can't convert — M4B not supported | Nothing to do for now. Originals are untouched. | none |
| Other | everything else | Stopped — see details | Select the row to read why. | Retry only if the API sends retry data |

Rules:
- Retry status says "ready to retry", not "temporary problem": for the 121 books the old reason is stale; technical detail keeps the history.
- Rows with no action get **no button and no disabled ghost**; a disabled button needs a way out.
- "Originals are untouched." ships only if Ender confirms it for every reason in that group; otherwise "Nothing to do for now."
- No promise of future support. Em dash separator as in "Held — reason". The status no longer starts with "Needs attention"; Ender greps code, tests and strings for that prefix. The filter keeps its name (O3).
- If `job.attention` is missing (older data), fall back to today's text. Never blank.
- Budget: status 40 characters or fewer, hint 70 or fewer (damage hints may wrap to two lines), sentence case, final period on hints only.

## 2. Damaged class: Repair

Damage line = what is wrong, then what Repair does. Plain words; no atom, box, offset or track-number terms. UI map keyed by `damage.kind`; amounts only when the API supplies them. Illustrative strings (Ender confirms they match what Repair really does):

| Kind | Hint |
|---|---|
| dangling chapter reference | One chapter mark points past the end. Repair removes it. |
| truncated tail | The end of the audio is missing. Repair fills it with silence. |
| with an amount | The last 42 s of audio is missing. Repair fills it with silence. |
| unknown kind | The app found damage it can patch. Repair fixes it. |

- Repair replaces Retry for that row; a damaged book never shows both.
- Same states, order and shared busy/pending state as Retry. Pending "Repairing…", note "Repairing this book…". Tooltip: "Patch the damage found in this book, then queue its audiobook job." Accessible name "Repair: {title clue}".
- **No confirmation for a single Repair**, on one condition: Repair works on a working copy and never writes the original files. The hint states the change, so the click is informed. **If Repair can ever write to an original, STOP and re-brief Judy.**

After repair (visible, persistent): row hint "Repaired: {first patch}" plus " +N more" in any status; details panel "Repaired" line with one bullet per patch ("Removed 1 chapter mark that pointed past the end." / "Filled the missing last 42 s with silence."); strip status line "Repaired. Removed 1 chapter mark that pointed past the end." until the group or filter changes. Focus as in section 5.

**Repair all: no.** Each repair changes content and the cases differ; counts are a handful. Revisit past about 10.

## 3. Kept files: Original changed and Audiobook problem (0.16.8)

Rule from Sergei: a verified book whose originals still match has all its recovery copies deleted automatically. The copies are kept only when (A) the original changed since it was checked, or (B) the converted audiobook is missing or unverified. These books are mostly completed jobs, so the "Output needs attention" filter must include them (section 9).

| Button | Tooltip | What it does | Pending label / note | After |
|---|---|---|---|---|
| **Check again** (A) | Verify the current files and convert this book again. | Re-verifies the changed original and queues a new conversion from the current content. | "Checking…" / "Checking this book…" | Row flips to "Queued" and leaves the filter. If the new result verifies and the originals match, the 0.16.8 rule deletes the old recovery copies. |
| **Convert again** (B) | Convert this book again and verify the result. | Queues a conversion (the Retry request). Never deletes anything itself. | "Converting…" / "Queuing this book…" | Row flips to "Queued" and leaves the filter. Recovery copies go only through the 0.16.8 rule after a verified result. |
| **Keep files** (A and B) | Keep this book's files and stop flagging it. Nothing is deleted. | Marks the files as kept at Sergei's choice. No job. | "Keeping…" / "Keeping these files…" | Row leaves the groups and counts. Hint elsewhere: "Files kept at your choice." Never schedules deletion. |

- "Keep files", not "Keep originals": what the app would otherwise delete is the recovery copies, so "originals" would mislead. "Files" covers both without a second noun.
- **Reversible.** For a kept book the details panel shows "You chose to keep these files." and still offers Check again or Convert again. The existing "Delete recovery copies" stays the manual way to remove them. No separate Kept group.
- Order in the row: remedy first, Keep files second, then View metadata and Open folder; `flex-wrap` may use a second line. Both are `quiet`. Min-width 104 for the remedy, 96 for Keep files.
- All three go through the Retry machinery: shared `busy`/pending key, `aria-disabled` while pending (keeps focus), ignore clicks while set, other buttons disabled meanwhile, same refused and connection-lost copy, success flips the row.
- **Confirmation, my call:**
  - **Check again: yes.** Original changed means the content may be damaged or tampered with, and the old recovery copies can be the only good copy. A "verified" new result is checked against that same changed content, and then the old copies are deleted and cannot be restored.
  - Convert again: no. It deletes nothing itself, and the rule only deletes after a verified result against matching originals.
  - Keep files: no. Nothing is deleted and it is reversible.
- Check again dialog (existing recovery-dialog pattern, section 6): title "Check again?", body "The original changed since it was checked. If the current files verify, the old recovery copies are deleted and cannot be restored.", buttons **[ Check again ]** primary and **[ Cancel ]** (default focus). Esc cancels. Condition: the new conversion replaces any existing audiobook only after it verifies; if Ender cannot guarantee that, STOP and re-brief.
- Row hint during pending, refused and connection-lost follows section 4. After Check again or Convert again the row's strip status line says "Queued." (live region).

No bulk actions here (no "Check all", "Convert all" or "Keep all"): each Original changed case needs a look, and counts are expected to be a handful. Revisit Convert all if Audiobook problem passes about 10.

## 4. Row layout

```
Review status cell                                 Actions cell
Stopped — ready to retry                           [ Retry ] [ View metadata ] [ Open folder ]
Safe to retry now.                (13px, --muted)

Original changed since checked                     [ Check again ] [ Keep files ] [ View metadata ] [ Open folder ]
Recovery copies are kept until you decide.

Can't convert — M4B not supported                  [ View metadata ] [ Open folder ]
Nothing to do for now. Originals are untouched.
```

- Status first line (`candidateStatus(row)`), hint second line as `p.field-help` (the recording-marker pattern); that marker stays last. Status cell `title` = "Technical detail: {raw reason}", hover only.
- Row remedies are **`quiet`**, first in order. With about 120 rows an accent fill on every row would be a wall of buttons; the accent fill is reserved for the strip's Retry all and the details panel button. Height 32, **min-width 96** (104 for Check again and Convert again) so pending labels never shift the row.
- Contrast (calculated): hint `--muted` on `--row-selected` 4.97:1, on `--row-hover` 6.64:1, on `--surface` 8.92:1.

## 5. Actions in the row

Reuse `retryKey`, `retryPending`, `retryResult`, `retryJob`; generalize key, label and endpoint. No new state.

- Click: `select(row,false)` (no scroll to the panel), then run the action. `stopPropagation` on click and keydown.
- Modes and order: Retry spec section 3. Button hidden when the job has no data for it.
- The row has no note line, so the hint carries the text: ready = class hint; unavailable = the API reason; pending = the note in the section 3 and 2 tables; refused or connection lost = the server message, or "Connection interrupted. Check the status above before trying again.", in `--warning`. Busy and offline: tooltip only; never rewrite 120 hints because one request is running.
- Success: row flips to "Queued" (existing `queuedByRetry`) or, for Keep files, shows "Files kept at your choice."; it leaves this filter on the next refresh and the counts drop. No toast.
- Focus after success: move to the row for the same book if still listed, else the row now at the same index (or the last), else `#filter`. `preventScroll`.
- No confirmation for single Retry (safe, the server re-checks); confirmations are listed in the Decision.

## 6. Group strip, counts, Retry all

Under the Status toolbar row, above the table, only while Status = "Output needs attention". Leaving the filter or "Clear filters" resets it to All.

```
Reason: [ All · 128 ] [ Can retry · 121 ] [ Can repair · 2 ] [ Original changed · 2 ] [ Audiobook problem · 1 ] [ Other · 2 ]      [ Retry all (121) ]
```

- Native `quiet` buttons, `aria-pressed`, in a `role="group"` named "Output needs attention, by reason". Each a Tab stop. Selected: `--row-selected` fill, `--text` label (about 7.7:1, calculated), 2px `--accent` border (8.02:1 vs surface); not by hue alone. Height 32, gap 8.
- Seven groups would be too many, so **a group at zero is hidden**, except All and Can retry (always shown). A group stays visible while it is selected or has focus; if the selected group reaches zero the strip falls back to All and focus moves to the All button.
- `flex-wrap`; `tabular-nums`; counts may reach 4 digits. Retry all sits at the right end and drops to its own line under about 1024px; never overlapping. No horizontal scroll at 700px or 200% zoom.
- Counts update in place each poll from the server; buttons are never rebuilt (focus holds).
- Order, also the server sort inside All: Can retry, Can repair, Original changed, Audiobook problem, Other, M4B not supported.
- Empty list and page text reuse current strings with the label "Output needs attention · {group}". "Showing 1-50 of 121" tells Sergei the group is larger than the page; Retry all always acts on the whole group.
- Tooltips: "Show all 128 books that need attention." / "Show books you can retry now." / "Show books with damage the app can repair." / "Show books whose original changed after the check." / "Show books whose audiobook is missing or not verified." / "Show books that stopped for another reason." / "Show M4B books the app cannot convert safely." (128 is the live total.)

**Retry all (N): yes, with confirmation, always.** For N around 120 a mistaken click queues a long, disk-heavy run behind the books already queued, with no known one-click undo; the label count is too easy to skim past. It is a rare action, so one extra click costs almost nothing, and a size threshold would make it behave differently day to day. Single Retry and Repair stay unconfirmed.

- Button "Retry all (121)", primary, 32 high, only while group = Can retry and N is 2 or more. Never in All. Tooltip: "Check these 121 books again and queue each audiobook job."
- **One confirmation pattern for the whole spec: the existing recovery dialog** (title, one paragraph, primary confirm, Cancel with default focus, Esc cancels, background inert). Rows have no room for an inline confirm, so Retry all uses the dialog as well; if the component cannot take a custom title and body, Ender builds a second one in the same pattern. Retry all dialog: title "Retry 121 books?", body "They run one at a time, after the 276 already queued. Originals stay untouched.", buttons **[ Queue 121 books ]** and **[ Cancel ]**. "after the N already queued" only if the status payload carries the queued count; "Originals stay untouched." only if Ender confirms. The confirm button goes aria-disabled on click (no double-press).
- On confirm: acts on every book in the group (server count, not the visible page), one at a time through the existing queue, never in parallel; the server re-checks each book.
- Feedback in the strip status line. The live region announces only the start ("Retrying 121 books.") and the end ("Queued 119 of 121. 2 could not be retried."); the running counter ("37 of 121") updates in an `aria-hidden` span. Refused books stay listed with their reason in the hint. The end line stays until the group or filter changes; no timers.
- While running: Retry all and every row button are disabled (busy). On finish focus moves to the "Can retry" group button.
- If Ender finds no cheap bulk path, ship rows and strip first and add this after.

## 7. Details panel

- `#automatic-result-status` and `#output-status` show the same short status (they already call `candidateStatus`).
- Directly under the status: the same hint. The Retry block becomes the action block: it shows the group's buttons (Retry, Repair, Check again, Convert again, plus Keep files); the accent fill is allowed here. The unavailable reason stays in the existing note, not duplicated in the hint.
- Repaired line and bullets (section 2) and "You chose to keep these files." (section 3) are permanent.
- Last line: "Technical detail: {raw reason}", `.field-help`, `overflow-wrap:anywhere`, never truncated, selectable.
- Add `job.attention`, the repair record and the kept flag to the render key (L629 omits them), or the hint goes stale.

## 8. What the UI needs from the API (names assumed; Ender confirms)

- Per book: `attention.group` = `retry` | `repair` | `changed` | `audiobook` | `unsupported` | `other`; `attention.cause` = `space` | `missing` | `unverified`; `attention.damage` = { kind, optional amounts }; action objects (`retry`, `repair`, `recheck`, `convert`, `keep`) each with `allowed` / `reason`; `repair_result.patched[]`; `kept` flag, persisted. Raw text stays in `job.reason`. Every action carries book id and revision like Retry.
- Group rule: `repair` when the damage is provable and Repair is offered; `retry` for temporary reasons, reasons an update fixed, and any row whose retry is allowed; `changed` and `audiobook` from the kept-files check; `unsupported` for the M4B reasons that remain; `other` for the rest.
- Filter: `output_attention` is today a job-state test (backend L229). It must now also include completed books whose recovery copies are kept for (A) or (B), excluding books marked `kept`, plus a group parameter and the sort above.
- Status payload: `attention_counts` { retry, repair, changed, audiobook, other, unsupported } and the queued-job count if available.
- Endpoints: repair, recheck, keep, and a bulk retry returning per-book result counts.

## 9. Acceptance checks for Futaba (measured, committed build)

- Copy: every row in every group shows the section 1-3 strings verbatim; none shows `Errno`, "database is locked", "brand", "box" or "decoder" outside the Technical detail line and hover title.
- Counts: strip counts equal the server's and change within a poll after an action; All equals the server total (see O2 for the Jobs panel count); a zero group disappears except All and Can retry; a selected group reaching zero falls back to All with focus on All.
- Rects at 1440, 1024, 700 and 200% zoom: row buttons at least 96 x 32; strip buttons at least 32 high; no two rects intersect (strip with 3-digit counts and 6 groups, row with 4 buttons wrapped); no horizontal scroll; no clipped focus ring; pending labels do not change row size.
- Keyboard: Tab to each row button, Enter; focus lands per section 5; group buttons toggle and announce pressed; focus on a row button for 10 polls: same element, nothing lost.
- Retry all at about 120 books: label shows the whole-group count while the page shows 50; dialog opens with focus on Cancel; Esc cancels; confirm runs once (double click, one request); announces start and end only; one forced refusal reads "Queued 119 of 121" and keeps its reason; Quit during the run disables everything.
- Repair: seeded damaged book shows the damage line and Repair, no Retry; afterwards the row hint, details bullets and strip line show the patch and survive a restart. Original files unchanged (hash before and after).
- Kept files: seed (A) and (B). (A) shows Check again and Keep files; Check again opens the dialog with focus on Cancel; Cancel leaves everything as it was. Convert again queues without a dialog. Keep files removes the row from the groups, deletes nothing, shows "Files kept at your choice." in All candidates, and the details panel still offers the remedy. Recovery copies on disk: present after Keep files, present until verification after Convert again, deleted only after a verified match.
- Double click, two rows quickly, click then Quit: one request, no stale hint on the wrong row.
- Tooltip positive control in the packaged window; rows without actions have no button.

## 10. Offers and open items (not specced)

- **O1.** A "Can retry · N" shortcut beside "Read errors · N" (hidden at 0), same pattern as `error-shortcut`.
- **O2.** The Jobs panel "N need attention" counts jobs only and its "Current book" line prints the raw reason. Recommend the same server total and the same short status, otherwise Sergei sees 125 there and 128 in All.
- **O3.** Rows read "Stopped" / "Can't convert" while the filter says "needs attention". Consider renaming the filter later.
- **Open for Ender:** (a) "Originals are untouched." true for every unsupported and retry reason; (b) Repair never writes originals; (c) bulk retry path, and whether queued jobs can be cancelled in bulk (if yes, the dialog can say so); (d) queued count in the payload; (e) can the API tell `space` apart; (f) where the two M4B leftovers land ("Top-level extent invalid" looks malformed, likely Other; "presentation bounds cannot be verified" likely M4B not supported); (g) can Can retry ever have `retry.allowed` false, and why; (h) Sergei says "backups", the app says "recovery copies"; this spec keeps the app term, and a rename would be app-wide; (i) does Check again replace an existing verified audiobook only after the new one verifies (section 3 condition), and in (B) do the originals still exist or are the recovery copies the only source; (j) the two existing "Download marker native identity differs" cleanup rows look like (A), map them there if so; (k) the existing "Candidate changed" filter is a different, earlier state: keep "Original changed" wording distinct from it.
- **Process:** this file is in the worktree. Per ProcessRules it is copied to `WIP/Books Arranger/Docs/` and committed by Sully before Ender is briefed.

Design basis: Hick (hide empty groups, one remedy per row), Fitts (action beside the hint that explains it), Jakob (native buttons, title tooltips, pressed toggles, safe-default confirmation), NN/g error prevention (confirm only where deletion can follow), visibility of status, plain-language recovery; WCAG 2.2 AA 1.4.3, 1.4.11, 2.4.7, 2.5.3, 2.5.8, 4.1.3. Doc-only: no code, git or app launch.
