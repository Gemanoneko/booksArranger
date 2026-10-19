# Books Arranger: what a row shows after a refused Retry

Date: 2026-10-19. Judy UX spec for Ender. Build v0.18.0, branch `codex/books-electron-m1` (HEAD ebfa1bc). Scope: the candidate row (and the matching details-panel lines) in Status = "Output needs attention", for a book whose Retry was accepted and then refused. Companion to `BooksArranger_AttentionActions_Spec.md` and `BooksArranger_RetryButton_Spec.md`; their rules stay in force unless this file overrides them.

Basis: read-only look at `web/app.js`, `audio_jobs.py`, `m4b_readmission.py`, `failed_m4b_retry.py`, `merge_service.py` (`_retry_preserved_m4b`, `retry_all`), `web/style.css` tokens. Nothing launched; no rects measured (target geometry for Futaba); contrast is calculated from tokens. Ender's root-cause fix is separate. This spec holds whether or not that fix lands.

## Decision in brief

- **A refused Retry ends the offer.** "Ready to retry" is a promise that Retry will be accepted. It is shown only when no refusal is on record for the current build of the code that decided it. Until the cause changes, the row says what is true and offers no Retry that cannot work.
- **Status:** the observed case (M4B layout refused) moves to the existing group "Can't convert — M4B not supported". Other refusal causes get their own short status. Never "ready to retry" while a refusal is current.
- **Retry:** removed when only an app update can fix it (no disabled ghost, per the Attention spec); disabled with the reason as tooltip when it clears by itself; enabled when Sergei can fix the cause.
- **Selection:** the checkbox is left alone (stays tickable, stays ticked). The bulk buttons skip the row, and the count line says how many were left out.
- **Copy:** the UI owns the words, keyed by a typed cause code. Raw text ("Failed M4B retained: Unsupported structural box") appears only in the Technical detail line and the hover title.
- **After a code fix:** the row becomes retryable again automatically, with no step from Sergei, when a build with changed deciding code first runs. Running it still needs a press (or Retry all). One attempt per book per build.

## 1. What goes wrong today (traced in code)

1. Sergei presses Retry. The M4B path accepts at once: row shows "Queued — runs next" (`m4b_readmission.request`).
2. Later the worker admits the request and runs the proof (`m4b_preservation.plan`). It refuses. The refusal is stored as state `refused` with the raw text (`next_job`, `m4b_readmissions.detail`).
3. The row's group is still `retry`, because the group comes from the old failure reason via `failed_m4b_retry.eligible` (`audio_jobs.py` L600), and `retry.allowed` is still true (L615). So the status stays "Stopped — ready to retry" (`app.js` L928) and the hint prints `Retry was refused: ` + raw text (L939).
4. Pressing Retry again replaces the `refused` record (`request()` re-queues) and hits the same refusal. **Retry all** takes every group-`retry` row on the server (`merge_service.retry_all`), so it re-attempts these books too. **Retry selected** counts the row (`retrySelectable`).

Three defects: the label promises what the app cannot do; the offer loops; the words are internal ("retained", "structural box").

## 2. The row after a refusal

```
Before (today)                                        After (observed case)
Status cell                      Actions cell         Status cell                              Actions cell
[x] Stopped — ready to retry     [Retry]              [x] Can't convert — M4B not supported    [View metadata]
    Retry was refused: Failed        [View metadata]      Retry was refused: the app doesn't   [Source folders]
    M4B retained: Unsupported        [Source folders]     support how this M4B is built.
    structural box                                        Nothing to do for now.
```

How it differs from a row that really is retryable:

| | Really retryable (no refusal on record) | Refused, fix = app update |
|---|---|---|
| Status | Stopped — ready to retry | Can't convert — M4B not supported |
| Hint | Safe to retry now. | Retry was refused: the app doesn't support how this M4B is built. Nothing to do for now. |
| Hint colour | muted | `--warning` (the existing `.retry-refused` mechanism) |
| Retry | present, enabled | not rendered |
| Strip group / counts | Can retry | M4B not supported |
| Retry all / Retry selected | included | excluded |

Every refusal cause carries a typed `cause` and a `fix` value. The UI picks behaviour from `fix`, copy from `cause`. A future cause declares one `fix` and gets one copy entry; nothing else changes.

| cause | fix | Status | Hint | Group | Retry | Checked live? |
|---|---|---|---|---|---|---|
| `unsupported_file` (observed) | `update` | Can't convert — M4B not supported | Retry was refused: the app doesn't support how this M4B is built. Nothing to do for now. | M4B not supported | not rendered | no; re-offered on a new build (section 5) |
| `working_files` | none (superseded) | SUPERSEDED by Follow-up 2, section 2: the row follows the live working-files state, not this record | Follow-up 2, section 2 | Follow-up 2, section 2 | Follow-up 2, section 2 | yes, always |
| `source_changed` | `review` | Stopped — review changed | Retry was refused: the book's review or source files changed. Start over sends it back to automatic processing. (decided 2026-10-19; second wording when the pass will hold the book: Follow-up 2, section 1) | Other | not rendered; Start over in its place (Follow-up 2, section 1) | leaves when Start over is pressed |
| `file_problem` | `user` | Stopped — file problem | Retry was refused: the app couldn't read or write a file. Check the folder, then retry. | Other | enabled | no |
| unknown, or no cause sent | `update` | Stopped — retry refused | Retry was refused. Select the row to read why. | Other | not rendered | re-offered on a new build |
| stale refusal (section 5) | none | Stopped — try again | Retry was refused in v0.18.0; the app was updated since. It may work now. | Can retry | enabled | n/a |

Notes:
- If the app confirms originals are untouched for the row (open item a of the Attention spec), the `unsupported_file` hint ends with "Originals are untouched." as the existing group hint does today. Otherwise it ships without that sentence.
- The stale row uses `--muted`, not `--warning`: it is information, not an obstacle. If the record has no version, use "Retry was refused before the app was updated. It may work now."
- `file_problem` stays out of Can retry on purpose: the app cannot tell the file problem is gone, so that group's promise would repeat the bug. Retry is still offered because Sergei can fix the cause and a press costs one cheap check.
- `source_changed`: after a new review the failed job cannot be bound to the changed book anyway; Ender confirms (open item c) whether the row simply leaves the list.
- Budget: status 40 characters or fewer (longest here is 33). Refusal hints may wrap to two lines (longest is 105 characters; the old damage hints already wrap). Sentence case, final period, em dash separator.

## 3. Controls

### Retry (row and details panel)

- **Removed, not disabled,** when `fix` is `update` or `review`. Rule from the Attention spec: a disabled button needs a way out the user can take, and here the only way out is an update or a new review. Rejected: a disabled Retry with a tooltip on these rows. It keeps a dead control in every refused row, repeats the status line, and differs from the M4B-not-supported rows that already have no button. The details panel's Retry block is hidden by the same rule (`rowAction` returns null).
- **Disabled with a reason** when `fix` is `wait`. Tooltip and hint carry the same text, so keyboard users see it without hover.
- **Enabled** for `file_problem` and the stale state.
- Position, size (min 96 x 32), `quiet` style, pending and busy modes: unchanged.
- **Focus.** If the Retry that has focus is removed (the refusal lands while Sergei is on it, which the existing in-place update allows), focus moves to that row's first remaining button, never to the page or another row. `preventScroll`.
- **While on screen.** If the refusal lands for a row visible in the Can retry filter, the row stays in place showing its new status until the list next changes (same hold the Queued state uses), then leaves with the counts. It must not vanish under the pointer unexplained. If the hold is not cheap, ship the rest and tell Judy.
- No toast, no dialog, no focus theft for a refusal. The row text and the strip counts are the notice.

### Tooltips

| Control | State | Tooltip |
|---|---|---|
| Retry (row, panel) | enabled: ready, `file_problem`, stale | Check this book again and queue its audiobook job. (unchanged) |
| Retry (row, panel) | `working_files` | SUPERSEDED by Follow-up 2, section 2: Retry is enabled when the files can be cleared, removed when they cannot |
| Retry | removed (`update`, `review`) | none: no control. The text lives in the hint. |
| Status cell hover (`title`) | any refused row | Technical detail: {refusal raw}; earlier failure: {job raw}. (format in section 4) |
| Strip button "M4B not supported" | unchanged | Show M4B books the app cannot convert safely. |
| Selection checkbox | unchanged | Select this candidate for the reviewed audiobook queue. |
| Retry selected | unchanged | Check these N selected books again and queue each one, right after the current book. / Select books that can be retried or repaired. |

Accessible names stay "Retry: {title}" and "Select {title clue}". The disabled `working_files` Retry follows the existing unavailable mode (visible label, reason as note and tooltip).

### Selection and bulk

- The row stays selectable and keeps its tick. Reasons: the app never changes a choice Sergei made (user control); the tick is harmless once the bulk buttons skip the row; selection is session-only and carries no stored meaning. Rejected: auto-untick on refusal (silent change), disabling the checkbox (breaks Select this page, which already mixes eligible and ineligible rows).
- **Retry selected** and **Retry all** exclude the row: server group `retry` no longer contains it, and `retrySelectable` already requires an allowed Retry. Pressing a stale button must still be refused by the server with the existing "This book's status changed. Check the updated status above."
- **Count line** (`batchCounts`, attention filter only): `{n} selected · {k} can be retried or repaired` plus ` · {n-k} left out` when n-k is above 0. Example: "3 selected · 2 can be retried or repaired · 1 left out". It answers "why is this ticked row not queued?" The line is already a polite live region and the help line below it already says only retryable books are queued. No tooltip (not a control).

### Details panel

Same status and hint as the row (they share `attentionText`). The Retry block is hidden when there is no Retry. Last line stays "Technical detail", now with both facts (section 4).

## 4. Copy

Rules: the UI never matches English reason text; the server sends `cause` (and `fix`); one map in `app.js`, beside `attentionCopy`, holds the strings; the refusal prefix "Retry was refused: " stays (one code path with the existing `Retry`/`Repair` prefix; for Repair read "Repair was refused:"). If `cause` is missing or unrecognised, use the unknown row. Words to keep out of the main lines: retained, structural, box, brand, atom, table, extent, proof, admission, preservation, parent, child.

Replacement for the observed text:

| Today | New |
|---|---|
| Retry was refused: Failed M4B retained: Unsupported structural box | Retry was refused: the app doesn't support how this M4B is built. Nothing to do for now. |

Technical detail line (last line of the panel; also the status cell hover title):
`Technical detail: {refusal raw}; earlier failure: {job reason}`
Example: "Technical detail: Failed M4B retained: Unsupported structural box; earlier failure: M4B preservation requires review: Unsupported structural box". Selectable, wraps anywhere, never truncated. When only one fact exists, show it alone. Today the line shows only the old job reason, so the refusal text would be lost; this keeps it for support.

"Nothing to do for now." follows the existing group wording and promises no future support. The stale row says "may work now", not "will work".

## 5. After a code fix

**Answer: automatic. Nothing has to happen first except the fixed build running.** Sergei does not clear anything, press anything or reselect.

- Each refusal record carries the app version and a key of the code that decided it (for the observed case the M4B preservation module), the same pattern as the repair check: one result per job, manifest and module hash (`repair_check_key`). Key on the deciding code, not on every release; otherwise each release re-offers 100 or more books.
- On the first poll under a build whose key differs, the record is ignored for grouping and the row shows the **stale** state: "Stopped — try again", Retry enabled, group Can retry, counts move, Retry all and Retry selected include it.
- **No automatic run.** Re-running reads source files and queues disk-heavy work behind other books; Sergei starts it (single Retry, Retry selected, Retry all, each as today).
- **One attempt per book per build.** A refusal under the new build stores a new record and the row returns to its refused state. If the fix does not cover a file, the cost is one cheap refusal, not a loop, and the row never claims more than "try again".
- Records written by v0.18.0 have no cause or key. Ender converts them once, server-side: cause from the stored text, key set to the v0.18.0 code. They then go stale exactly when the fix ships and not before. Ender must not leave them keyless, or they would stay refused forever.
- Optional offer, not specced: a one-time strip line the first time rows return ("12 books can be retried again. The app was updated."). Without it, the Can retry count rising is the only signal.

```
press Retry -> Queued — runs next -> worker refuses -> Can't convert (refusal stamped: build X)
                                                        |
                              new build, deciding code changed
                                                        v
                                   Stopped — try again (Retry back, in Can retry)
                                        |  press (Sergei)                |
                              accepted -> Queued                refused again -> stamped: build Y
```

## 6. What the UI needs from the API (names assumed; Ender confirms)

- `readmission` (refused) gains `cause`, `fix` (`update`, `wait`, `review`, `user`), `app_version`, `key` (or a boolean `stale` computed server-side), `at`. Raw text stays in `reason`.
- `attention.group` is computed after the refusal record: `unsupported_file` and unknown refusals leave `retry`; stale ones return to `retry`. Rows with `fix` of `wait`, `review`, `user` go to `other`. `attention_counts` follow.
- `retry` data absent when `fix` is `update` or `review`; `{allowed:false, reason}` when `wait`; `{allowed:true}` otherwise. `retry_all` and any server-side bulk path use the same rule.
- `job.reason` stays as the old failure text for the Technical detail line.

## 7. Acceptance checks for Futaba (committed build; seeded records, no real library)

- Seed a refused `unsupported_file` record: row reads "Can't convert — M4B not supported" with the new hint; no Retry in the row or the panel; View metadata and Source folders (or Open folder) present; strip count moves from Can retry to M4B not supported. No `Failed M4B retained`, `structural` or `box` outside the Technical detail line and hover title.
- Positive control: an M4B row with no refusal still reads "Stopped — ready to retry" with Retry enabled.
- Retry all and Retry selected: the seeded refused row is not queued and is not in the count; the dialog count matches. With 3 ticked, 1 refused: "3 selected · 2 can be retried or repaired · 1 left out". The tick on the refused row is still set after refresh.
- Loop check: in one build the refused row offers no Retry; a stale button press (forced) is refused with no new attempt.
- `working_files`: SUPERSEDED. The checks are in Follow-up 2, section 6.
- Stale: swap the record's key; row reads "Stopped — try again", Retry enabled, in Can retry, muted hint. Press it and force a refusal: row returns to Can't convert with a new key.
- Legacy v0.18.0 record (no cause, no key): maps to the right cause and goes stale on a changed key.
- Focus: Retry focused, refusal lands: focus moves to View metadata of the same row, not to body.
- Rects at 1440, 1024, 700 and 200% zoom: refused row with 2-line hint and 2 buttons, and the `working_files` row with 3 buttons: no intersecting rects, no horizontal scroll, row buttons at least 96 x 32 where present.
- Contrast (calculated): `--warning` hint on `--surface` 11.18, on `--row-hover` 8.31, on `--row-selected` 6.23; `--muted` hint on the same 8.92, 6.63, 4.97. All 4.5:1 or above. The refusal is also stated in words, not colour alone.

## 8. Open items and offers

Open for Ender:
- (a) Is "Originals are untouched." true for every `unsupported_file` refusal? (Attention spec open item a.)
- (b) What clears `working_files`? ANSWERED (Ender: nothing did; Sergei 2026-10-19: Retry clears them, and a Clear working files button). See Follow-up 2, section 2. The cause no longer uses the `wait` fix.
- (c) Can a `source_changed` failed job ever be retried, or does re-review always supersede it?
- (d) Is the deciding-code key available for each cause, or only for the preservation module? Unknown causes can use the app version as the key.

Offers (not done; Sergei decides):
- O1. The "ready to retry" label is still unearned for a book never tried: 121 books got it in 0.16.7 and the first press found the refusal. A cheap read-only check that runs the same proof Retry runs, cached per job and code key like the repair check, would make "ready" true before the press. That is Ender's design call.
- O2. A one-time strip line when refused rows return after an update (section 5).
- O3. The checkbox tooltip names "the reviewed audiobook queue", which is wrong in this filter, where the tick feeds Retry selected.

Process: this file sits in `WIP/Books Arranger/Docs/`, uncommitted. Per ProcessRules, Sully commits it before Ender is briefed.

Design basis: NN/g visibility of system status, error prevention, user control and freedom, plain-language recovery; Hick (one honest state, no dead controls); Jakob (native buttons, title tooltips, unchanged selection); WCAG 2.2 AA 1.4.3, 2.4.7, 3.3.1, 4.1.3. Doc-only: no code, git or app launch.

---

## Follow-up 2026-10-19: Ender's stop points (build `eb999a9`)

Judy, UX spec for Ender. Scope: the three points Ender stopped on, plus the pre-check states Sergei approved. Everything above stays in force unless this section overrides it. Basis: read-only look at branch `codex/books-electron-m1` at `eb999a9` (the sections above were written against `ebfa1bc`): `audio_jobs.py` (`attention_summary`, `_retry_shape`, `retry_admission_hold`), `merge_service.py` (`candidate_status`, `attention_summary`, `_check_repairs`, `_repair_check_work`, `_retry_preserved_m4b`, `_m4b_working_clear`, `retry_all`), `m4b_repair.py`, `retry_refusal.py`, `review_backend.py`, `web/app.js` (`attentionText`, `rowAction`, `updateRowRetries`, `retrySelectable`). Nothing launched, no rects measured (target geometry for Futaba). Contrast is calculated from the tokens already used above.

### F. What the code does that the brief or the first spec did not say

1. **The stuck job is real.** `candidate_status` returns the book's last job in any state and never compares revisions (`merge_service.py` L891-894). `review_backend.py` L165 turns that into "Audiobook job already exists" with `can_create` false; the automatic path repeats it (`merge_service.py` L1290). Retry cannot take it either: rule E9 in `retry_admission_hold` needs the job's frozen `candidate_revision` to equal the book's current one. After any new review neither route is open, so the `source_changed` hint ("Review the book again.") promises a fix that does not exist. The hint changes under every option in point 1.
2. **The pre-check state never reaches the UI.** `jobs.attention_summary` sets `repair_check`, but `merge_service.attention_summary` pops it (L928) before the API sends it. Pending needs a typed field (section 2).
3. **Two pre-check outcomes have no end.** (a) `m4b_repair.check` caches the "unavailable" result in the process-wide `_CACHE` and `classify` returns it, so the source is not opened again until the app restarts (the saved table skips it, so a restart does re-check). (b) A check that throws is added to `_repair_skipped` and "stays unchecked" for the rest of the run, which would read as "checking" forever. Both must display as state (b) in section 2, never as a permanent pending row.
4. **A refused Repair leaves the Repair group.** Any current refusal moves the row to `other` or `unsupported` (`attention_summary`). "Repair group" in the brief means a row whose refusal kind is repair.
5. **Retry wording leaks into refused Repair rows.** The unknown cause's status is fixed text, and two hint tails and the server's disabled reason say "retry" whatever the kind (point 3b).
6. **A disabled Retry shows the server's reason as the hint**, replacing the cause's hint (`updateRowRetries`, mode `unavailable`). So a `working_files` row reads "Working files from an earlier attempt are still present. Retry after they are cleared." with no "Retry was refused:" prefix. Accepted: one text for hint and tooltip, and the status line carries the context. The pending state below uses the same mechanism.
7. **No actor for leftover working files (open item b of the first spec, still unanswered).** `_retry_preserved_m4b` refuses on working files before anything runs, and the idle `reconcile` only handles receipt-owned `closed` and `published` attempts. A leftover folder with no receipt (an older attempt) has no code path that clears it, so "waiting for cleanup" could wait forever. Ender to confirm; see point 3c.

### 1. A `source_changed` job is stuck — DECIDED (Sergei, 2026-10-19): option 1, with automatic re-processing

**Decided: option 1. After Start over the book goes back to the automatic pass, not to manual review.** The "reviews and queues it with the existing controls" wording below, and every string that said so, is replaced in Follow-up 2, section 1; the strings in this section that Follow-up 2 changes are marked.

Facts in F1. Retry stays removed on these rows (the first spec's rule); the question is how the book gets out.

| # | Option | What Sergei does | Risk |
|---|---|---|---|
| 1 | **Start over button** on the row (recommended; CHOSEN, with automatic re-processing) | Presses Start over. The failed job is set aside and the book goes back to the automatic pass, which researches, approves and queues it with no further press on the book (Follow-up 2, section 1). | One extra press per stuck book. A new job can appear without a manual queue. A book whose review was changed by hand is held by the pass and nothing in the app queues it (Follow-up 2, section 1). |
| 2 | **A new review replaces the job automatically** | Saves a review. Saving sets the stuck job aside. | Hidden side effect: any saved review, including one written by an automatic pass, retires a job with nothing on screen saying so. |
| 3 | **"Retry with new review" button**: sets the job aside and queues a new job from the current review in one press | One press. | Starts a conversion from a review he may not have re-checked (the normal queue gates still apply); a repeat failure creates a new stuck job per press. |

**Recommendation: option 1.** It separates "set the dead job aside" from "queue", so queuing stays the one control it is today. It is explicit, shows what happened, and follows the first spec's rule that the app never changes a book without Sergei's press. Option 3 can be added later on top of it if one press per book proves too slow. Not recommended: option 2 (silent).

**Rules that hold for any option** (Ender confirms they are possible; if not, report back):
- The old job row, its journal and its working files are kept, not deleted; it is only no longer the book's current job. The tooltip below says "Nothing is deleted" and must stay true.
- Server side, set aside only a job that needs attention, has no output and no publication record, is the book's newest job, and has a current `source_changed` refusal. Compare-and-set on the row as read. A press from an outdated view is refused with the existing "This book's status changed. Check the updated status above." and changes nothing.
- No confirmation dialog: the job can no longer be retried, nothing is published, no original is touched. The tooltip states the effect.

**Copy for the `source_changed` row (status unchanged: "Stopped — review changed").** The prefix "Retry was refused: " (or "Repair was refused: ") stays.

| Option | Hint after the prefix | Control |
|---|---|---|
| 1 | SUPERSEDED. Now: the book's review or source files changed. Start over sends it back to automatic processing. (Second wording: Follow-up 2, section 1.) | Button **Start over** |
| 2 | the book's review or source files changed. Review the book again; saving the review sets this job aside. | none |
| 3 | the book's review or source files changed. Retry with the new review, or review the book again first. | Button **Retry with new review** (disabled with "Review the book first." until its review is complete) |

**Spec for option 1 (options 2 and 3 reuse the same action mechanics).**
- **Where:** in the Retry slot of the row and of the details panel (first action button), only when the current refusal is `source_changed` (fix `review`). Same size (min 96 x 32), `quiet` style, same position; nothing else on the row moves. New action kind `startover` in `rowActions`.
- **Strings:**

| Item | Text |
|---|---|
| Button | Start over |
| Accessible name | Start over: {title} (same pattern as "Retry: {title}") |
| Tooltip (ready) | SUPERSEDED by Follow-up 2, section 1 (the old text said the book is reviewed and queued by hand). "Nothing is deleted." stays. |
| While pressed | button "Starting over…" (aria-disabled, keeps focus), note "Setting this job aside…" |
| Result note (panel) | SUPERSEDED by Follow-up 2, section 1 (three variants). |
| Not accepted | Start over was not accepted. Check the status above. |

- **After the press:** SUPERSEDED in part. The hold, the leaving with the counts, no toast, no dialog and the focus rule stand; what the row says during the hold, and where the book goes, are in Follow-up 2, section 1 (the book is not left at "Needs metadata review" or "Ready to create": it goes to the automatic pass).
- **Bulk:** none. Retry all and Retry selected skip the row, because its Retry is not rendered (unchanged). No "Start over selected" in this pass; offered below if there are many such books.
- **Known gap:** a `source_changed` refusal can also come from a change that landed mid-proof ("Reviewed candidate changed during source proof"). Such a job might have been retryable again. Accepted: the cost is one Start over and a new automatic pass, and the typed cause cannot tell the two apart.

### 2. Pre-check states (a row says "ready to retry" only after the dry run passes)

Applies only to rows whose Can retry place comes from an M4B failure reason (`m4b_retry`), the rows the pre-check covers. Other retry rows and Repair rows are unchanged. Precedence when several facts hold: **current refusal, then pre-check unavailable, then pre-check pending, then stale refusal, then ready.**

| | (a) Check not finished | (b) Check could not open the source |
|---|---|---|
| Status | Stopped — checking the M4B | Stopped — can't open the M4B |
| Hint | The app is checking this M4B before offering Retry. The row updates itself. | The app couldn't open this M4B to check it. Check that the library drive is connected, then retry. |
| Hint colour | `--muted` (information; clears by itself) | `--warning` (Sergei can fix it) |
| Retry | Present, **disabled**. Tooltip and hint carry the same text (the existing disabled mode): "The app is checking this M4B before offering Retry. The row updates itself." | Present, **enabled**. Tooltip unchanged: "Check this book again and queue its audiobook job." A press does the real read and answers. |
| Strip group | **Checking** (new, below) | Other (with `file_problem`) |
| Retry all | Excluded (not in Can retry) | Excluded (group Other) |
| Retry selected | Excluded (Retry not allowed) | Included when ticked: Sergei chose it, and the press is the real check. A refusal then follows the normal refusal rules. |
| Technical detail | job reason only | `Technical detail: Source unavailable: {error}; earlier failure: {job reason}` (the check's raw text, same format as a refusal) |
| Ends when | the check finishes: passed -> "Stopped — ready to retry" in place; refused -> M4B not supported; repairable -> Can repair | Sergei presses Retry (accepted, or refused with a typed cause), or a re-check passes (only if Ender adds one) |

Why disabled for (a) and enabled for (b): (a) clears by itself in minutes, the same class as `wait`, and a disabled Retry there keeps the "ready" promise honest; (b) will not clear by itself and Sergei can act on it, the same class as `file_problem`.

**Checking group (new strip button).** Label **Checking**, shown as "Checking · N", placed after Can repair, hidden at zero (the existing rule for Original changed). Tooltip: "Show books the app is still checking before it offers Retry." Why a group and not a status inside Can retry: after an update every M4B re-checks, so Can retry would again count about 121 books that are not yet ready, and Retry all would offer them. A separate group makes the Can retry count and the Retry all dialog true, and the falling Checking count is the progress signal (no spinner, no per-row animation). Order: Can retry, Can repair, Checking, Original changed, Audiobook problem, Other, M4B not supported. When Checking empties while selected, the view moves to Can retry instead of All (the books he waited for are there), with the existing focus rule. No toast when the checks end.

**Interaction with the stale state (first spec section 5).** A new build changes the preservation module hash, which makes the refusal stale and the check unchecked at the same moment. While the check is pending the row reads Checking. Then: check passes -> status "Stopped — ready to retry", hint "Retry was refused in v{version}. The app was updated, and this M4B now passes its check." (muted; drop the version clause if none is stored); check refuses -> M4B not supported (as built); check cannot open -> state (b). "Stopped — try again" remains only for rows the pre-check does not cover.

**What the UI needs from the API (names assumed; Ender confirms).**
- `attention.precheck`: `"pending"` or `"unavailable"`, absent when the check passed or does not apply; `attention.precheck_reason` (raw text for Technical detail). Do not pop it.
- `attention.group`: `"checking"` for pending (a new key in `attention_counts`, the group filter whitelist, `ATTENTION_ORDER` and `attentionKeys`); `"other"` for unavailable.
- `retry`: `{allowed:false, reason:<pending text>}` for pending; `{allowed:true}` for unavailable.
- A check that errored or was skipped (`_repair_skipped`), or whose unavailable result is older than Ender's re-check bound, reports `"unavailable"`, never `"pending"`. Whether the unavailable result is re-checked on a timer while the app runs is Ender's call; the copy holds either way (it promises no automatic re-check).
- A forced Retry press on a pending row is refused with the existing "This book's status changed. Check the updated status above." and queues nothing.

### 3. Smaller points

**(a) Hold in place for books queued by Retry all or Retry selected: acceptable, not required.** The hold exists so a row does not vanish under the pointer after Sergei pressed that one row. In a bulk run he has pressed no row, and accepted books already leave the list the same way when their child is admitted, so the list shrinking is the normal behaviour of a bulk run. The group counts and the strip carry the notice. Condition: counts are conserved; Futaba checks that the sum over all groups stays constant while rows move from Can retry to M4B not supported and Other. Optional, not required: append " A book the app then refuses moves to its own group." to the Retry selected result line ("Queued N of M. They run one at a time, right after the current book.").

**(b) Unknown status in a refused Repair row: wrong, fix it.** Make the verb follow the refusal kind. Status for the unknown cause: `Stopped — retry refused` or `Stopped — repair refused`. The hint already says "{Verb} was refused. Select the row to read why." The same leak, fixed together:

| Place | Today (any kind) | Should be |
|---|---|---|
| `working_files` hint tail and disabled reason (server `RETRY_FILES_PRESENT`) | SUPERSEDED: this text no longer appears. Follow-up 2, section 2 replaces it and keeps the verb rule (a Repair row says Repair) | |
| `file_problem` hint tail | ...Check the folder, then retry. | ...Check the folder, then {verb}. |

Rule: the verb comes from the refusal kind in the UI copy map; the server's English reason is never matched. `source_changed` and `unsupported_file` copy has no verb to change.

**(c) Name the leftover working folder: not in the hint, yes in Technical detail only.**
- Not in the hint. The row has no way to open it (the open-folder control knows only source and output folders), the path is long and wraps badly in a cell, and deleting files in it by hand skips the verified disposal the app requires.
- Yes in the Technical detail line (panel and hover title), for `working_files` only, if the server can send the **absolute** path (the relative `data/merge-cache/audio-staging/<job id>` is not openable by Sergei). Format: `Technical detail: {raw}; earlier failure: {job reason}; working folder: {absolute path}`. Selectable, wraps anywhere, never truncated.
- Conditional on F7: if nothing clears an older attempt's folder, "waiting for cleanup" is a false promise for that book. ANSWERED: nothing cleared it; Sergei decided on Retry-clears plus a Clear working files button. The folder stays in Technical detail only (this rule stands, and now applies to the blocked state); the controls and the words are in Follow-up 2, section 2.

### 4. Acceptance checks for Futaba (committed build; seeded records, no real library)

- **Pending:** seed an M4B row with no saved check. It reads "Stopped — checking the M4B" in the Checking group (strip count, hidden at zero); Retry present and disabled, tooltip exactly as in section 2; the hint is the same text. It is in neither the Can retry count nor the Retry all dialog; a ticked pending row counts under "left out". When the check passes, the row becomes "Stopped — ready to retry" with Retry enabled and the counts move; when it refuses, it moves to M4B not supported.
- **Positive control:** an M4B row whose saved check passed still reads "Stopped — ready to retry" with Retry enabled, in Can retry and Retry all.
- **Unavailable:** seed an M4B row whose source path does not exist. "Stopped — can't open the M4B", warning hint, Retry enabled, group Other, not in Retry all; ticked, it is in Retry selected; Technical detail starts "Source unavailable:".
- **Checks with no end:** force the check to throw, and separately keep an unavailable result past the re-check bound. Neither shows "checking"; both read can't-open.
- **Stale + check:** a stale refusal with a pending check reads Checking; with a passed check it reads ready to retry with the "app was updated" hint; with a refused check it reads M4B not supported.
- **Start over:** SUPERSEDED. Option 1 was chosen with automatic re-processing; the checks are in Follow-up 2, section 6.
- **Repair verb:** a refused Repair with unknown cause reads "Stopped — repair refused"; a `working_files` Repair row says "Repair after they are cleared"; no "retry" in a repair row's main lines.
- **Bulk conservation:** Retry selected with 5 rows ticked, 2 refused later by the worker: the group counts sum to the same total before and after.
- **Rects at 1440, 1024, 700 and 200% zoom:** a pending row (2-line hint, disabled Retry and its other buttons) and an unavailable row: no intersecting rects, no horizontal scroll, buttons at least 96 x 32 where present; the strip with the new Checking button does not clip or push the retry-all line out of place.
- **Contrast (calculated, same tokens):** `--muted` hint on `--surface` 8.92, `--row-hover` 6.63, `--row-selected` 4.97; `--warning` hint 11.18, 8.31, 6.23. All 4.5:1 or above. Every state is also stated in words.

### 5. Open items and offers

Open for Ender:
- (e) F7: what clears a leftover working folder that has no receipt. ANSWERED by decisions A and B; what stays open for Ender is which folders count as cleanable (Follow-up 2, section 2).
- (f) Can the set-aside rules in point 1 hold (old row, journal and working files kept)? If not, the tooltip loses "Nothing is deleted."
- (g) Can a check that errored or was skipped surface as `unavailable`?

Offers (not done; Sergei decides):
- O4. Option 3 on top of option 1 (one press: set aside and queue), if one press per stuck book is too slow.
- O5. "Start over selected" for many stuck books; the Other count shows how many there are.
- O6. The one-line note after a bulk run (point 3a).

Process: appended to this file, uncommitted; Sully commits it before Ender is briefed. Doc-only: no code, git or app launch. Design basis: NN/g visibility of system status, error prevention, user control and freedom, plain-language recovery; Hick (one honest state per row, one transient group, no dead controls); Jakob (native buttons, title tooltips, hide-at-zero strip as for Original changed); WCAG 2.2 AA 1.4.3, 2.4.7, 3.3.1, 4.1.3.


---

## Follow-up 2 — 2026-10-19: Start over goes to the automatic pass, leftover working files, and Futaba's three Minors

Judy, UX spec for Ender. Build `de3e2b2`, branch `codex/books-electron-m1`. Scope: Sergei's two decisions of 2026-10-19 and the three Minors from Futaba's interim QA (`BooksArranger_QA_RefusedRetry_de3e2b2_2026-10-19.md`). Everything above stays in force unless this section overrides it. Basis: read-only look at `automatic_processing.py` (`_work`, `manual_draft`, `start`, `status`), `review_backend.py` (creation status, the automatic status line), `merge_service.py` (`candidate_status`, `approve_automatic`, `_m4b_prior_audio`, `_m4b_working_clear`, `_check_repairs`, `_repair_check_work`, the quiet-state reuse), `audio_jobs.py` (`attention_summary`), `working_lifecycle.py` (`retire`, `admit`, `reconcile`), `storage_cleanup.py`, `retry_refusal.py`, `web/app.js`, `web/style.css`, `web/index.html`. Nothing launched; no rects measured (target geometry for Futaba); contrast is calculated from the tokens already used above.

**Earlier text changed because these decisions made it false** (everything else is as it was): first spec: the `working_files` and `source_changed` rows of the cause table, the disabled working-files Retry tooltip row, the working-files acceptance check, open item (b). Follow-up 1: the section 1 heading and the option-1 rows (what Sergei does, risk, copy, tooltip, result note, after-the-press, known-gap wording), the section 3(b) `working_files` row, the last bullet of 3(c), the Start over acceptance check, open item (e). Each is marked SUPERSEDED or ANSWERED and points here.

### 0. What ships, in one table

| Decision | What Sergei gets |
|---|---|
| Start over, with automatic re-processing | A **Start over** button in the Retry slot of a "review changed" row. It sets the failed job aside (kept) and sends the book to the automatic pass. The row says which of two outcomes follows, before and after the press (section 1). |
| A: Retry clears leftovers | On a row whose leftovers can be cleared, Retry stays enabled. Its tooltip and hint say it clears them first. After a successful press nothing more is said about the files (section 2.4). |
| B: Clear working files | A new button next to Retry. It exists only while the server says cleanable files are present. Never disabled, no confirmation (section 2.5). |
| Minor 1 | The Checking count and each row follow every finished check, within 10 seconds, 20 at most (section 3). |
| Minors 2 and 3 | The row is right the moment the files are gone. The cleared-state text is defined (section 2.6). |

### 1. Start over, with automatic re-processing

#### 1.1 What the code does that the decision does not say

1. **The pass is not a background service.** Automatic processing runs only after Sergei presses **Start automatic processing**, pauses when the app restarts ("Paused after server restart — start to continue saved work"), and visits each book once per run (a visited book sits in the run's `done` list). A set-aside book is picked up by the next pass, not by one that already visited it. So "no further press" is true for the book and not for the pass: Start over does not start the pass. SUPERSEDED by Follow-up 3, section 1 (Sergei, O9: Start over also starts it when it is not running).
2. **Two outcomes can be told apart before the press** (`manual_draft(row)` is a read-only test).
   - **(a) Automatic.** The pass researches the book and, if it approves it, queues it with no press. It can still hold it with a reason; those rows already read "Held — {reason}".
   - **(b) Manual draft.** A book that carries a review the pass did not write (Ender's finding: a manual save, or a rescan that left the review without its automatic approval; the test is `automatic_processing._manual_draft`) is held as "Manual draft retained", re-checked every 5 minutes with the same result. A single audiobook file cannot be queued by hand ("Single audiobook file" is the app's own reason). I found nothing in the app that releases that hold. SUPERSEDED by Follow-up 3, section 4 (Sergei, O7: the "Let the app handle it" button releases it; the rescan facts are in section 4.1). For these books "processed automatically" is not true, and the words below say so.
3. **"Pending" is the app's own word** for a book the pass has not reached (the last fall-through of the row status). An old automatic record that says Queued or Approved, with no job, would make the row read "Queued" (the status line takes the automatic state when no job exists). The set-aside must leave no such record for this revision (open item g).
4. **The prediction can be stale.** The book list may be up to 5 minutes old and Sergei may edit the book meanwhile. The words shown after the press follow the server's answer to the press, not the earlier prediction.

#### 1.2 Words before the press

Status stays "Stopped — review changed". The prefix "Retry was refused: " (or "Repair was refused: ") stays. The hint is the one text in the row and in the details panel.

| Server `attention.startover` | Hint after the prefix | Tooltip of Start over |
|---|---|---|
| `automatic` | the book's review or source files changed. Start over sends it back to automatic processing. | SUPERSEDED by Follow-up 3, section 1.2 (the old text did not say Start over also starts automatic processing) |
| `manual_draft` | the book's review or source files changed. Start over sets this job aside, but automatic processing will hold the book. (SUPERSEDED for a single M4B with no editor open: Follow-up 4, section 3.2, where one button does both) | SUPERSEDED by Follow-up 3, section 1.2 (the old text did not say Start over starts automatic processing, and "manual review" is not always what holds the book) |
| absent or unknown | as `automatic` | as `automatic` |

Hint colour `--warning` for both (a stop that needs Sergei's press). Button, size (min 96 x 32), `quiet` style, slot, accessible name "Start over: {title}", pending face "Starting over…" and pending note "Setting this job aside…": unchanged from Follow-up 1, section 1. "Nothing is deleted." must stay true (the old job row, its journal and its working files are kept).

#### 1.3 Words after the press, and where the book goes

The result text is shown in the details panel note (`#retry-note`, already a polite live region) and, for as long as the row is held in place, as the row's hint (SUPERSEDED in part: the row shows its Started over state and the whole table below is replaced; Follow-up 3, sections 1.3 and 1.4). It is chosen by the server's **answer** (`outcome`) and by the automatic-processing state the page already holds (`state.automatic_processing.state`).

| Answer | Automatic processing | Text | Colour |
|---|---|---|---|
| `automatic` | `Running` | SUPERSEDED by Follow-up 3, section 1.3 | `--muted` |
| `automatic` | `Idle`, `Paused`, `Stopping`, `Completed` or `Needs attention` | SUPERSEDED by Follow-up 3, section 1.3 | `--muted` |
| `automatic` | unknown or disconnected | SUPERSEDED by Follow-up 3, section 1.3 | `--muted` |
| `manual_draft` | any | SUPERSEDED by Follow-up 3, sections 1.3 and 4 (the old text claimed "changed by hand", which a rescan alone can make false) | `--warning` |
| refused | any | Start over was not accepted. Check the status above. (outdated view: the existing "This book's status changed. Check the updated status above.") | `--warning` |

**The row during the hold** (the existing held-row mechanism; same lifetime as a pressed Retry): the status cell shows the book's own new status, taken from the answer (SUPERSEDED in part by Follow-up 3, section 1.4: the answer carries the refreshed row and its status is the Started over state, never "Pending"; the held copy must not keep the old job, or it would still read "Needs attention"). The hint is that state's hint (Follow-up 3, section 2.2); the result text goes to the panel note only. Buttons: the row's remaining buttons (View metadata, Source folders or Open folder). No Retry, no Start over. No toast, no dialog. Focus moves to the row's first remaining button, `preventScroll` (Follow-up 1 rule).

**Where the book goes.**

```
press Start over
   |  job set aside (kept); book has no current job
   v
held row: "Started over — ..." + state hint   (SUPERSEDED: was "Pending" + result text; Follow-up 3)   (Output needs attention count: Other -1 when the list next changes)
   |  the pass reaches the book (the press starts it if it is not running, unless the start is blocked; Follow-up 3)
   +--> (a) Researching / Processing --> Queued --> a new job --> normal flow
   |          or  Held — {reason}           (Held filter; reasons as today)
   +--> (b) Held — Manual draft retained    (Held filter; re-checked every 5 min; SUPERSEDED "no exit in the app": the "Let the app handle it" button, Follow-up 3, section 4)
```

SUPERSEDED by Follow-up 3, section 2 (Sergei, O8): after the press the book carries a Started over marker, its own status words, and appears under Status: Started over until automatic processing has queued it.

#### 1.4 Reservation about (b), not a change to the decision

Sergei chose automatic and the spec follows it. For (b) the press turns a stop that has a button into a hold that has none, and the only words that say so are the hint and the result note. The honest copy above is the fix I can make from the UI. A way out for these books (release the manual draft, or let a single audiobook file be queued by hand after a manual review) is a product decision; offered as O7. ANSWERED (Sergei, option A): the "Let the app handle it" button, Follow-up 3, section 4.

### 2. Leftover working files

#### 2.1 What the code does that the decision does not say

1. A leftover is the working folder of an earlier attempt, `data/merge-cache/audio-staging/{job id}/{attempt id}/`. It holds only files the app made (copies of the sources, converted audio, cover, check files; one real case was 637 MB). Originals are never in it.
2. Retry and Repair of an M4B refuse before anything runs when that folder holds `.m4b` or `.wav` files (`_m4b_prior_audio`). Nothing cleared them (Ender). The app's verified disposal (`working_lifecycle.retire`) clears an attempt it owns by receipt: it hash-checks every file, keeps anything it cannot prove (an unknown member, a changed file), and keeps the source copies when the originals cannot be reached. An older attempt without a receipt is not covered.
3. So there are three honest states, typed by the server, not two: **none**, **cleanable** (the app's verified disposal would remove all of it now) and **blocked** (files are present and the app cannot remove them safely now). The old text "waiting for cleanup" promised a fourth, "will clear itself", that no code delivers.

#### 2.2 The rule that replaces the `wait` fix

The server sends `attention.working` = `{state: 'cleanable' | 'blocked', bytes, reason}` for any attention row whose job folder holds leftover audio files, and nothing otherwise. A `working_files` refusal record no longer decides the row's group, status or hint: the live `working` state does. A record whose files are gone (or can be cleared) leaves the row as if no record existed, so a row never reads "waiting for cleanup" again. The record stays in Technical detail only. The `working_files` cause stays in `retry_refusal` for old records; its `wait` fix is not used for display.

#### 2.3 What each row shows

| `working` | Group | Status | Hint | Retry | Clear working files |
|---|---|---|---|---|---|
| absent | natural | natural | natural | natural | not rendered |
| `cleanable` | natural (it is not a stop) | natural | the natural hint, then " Retry clears leftover working files first." (added only when Retry is enabled) | enabled; tooltip below | rendered |
| `cleanable`, Repair row | SUPERSEDED by Follow-up 3, section 3 (Sergei, O10: Repair clears first, like Retry) | | | | |
| `blocked` | Other | Stopped — can't clear working files | Working files from an earlier attempt are still present, and the app can't clear them safely right now. | not rendered (no disabled ghost: nothing Sergei can press fixes it) | not rendered |
| `blocked`, typed cause "originals unreachable" (optional) | Other | as above | Working files from an earlier attempt are still present, and the app can't clear them while the original files can't be reached. Check that the library drive is connected. | not rendered | not rendered |

Notes:
- "Natural" means exactly what the row would show with no record and no leftovers: "Stopped — ready to retry" with "Safe to retry now.", the Checking and can't-open states, the stale text, and so on. Precedence in Follow-up 1 section 2 is unchanged; a current refusal of another cause still decides the row, and Clear working files still appears on it when the files are cleanable (it frees disk and costs nothing).
- Blocked is live. When the cause goes away (the drive is back) the row becomes `cleanable` on its own, with no step from Sergei.
- The blocked hint is `--warning`, the clause and the Repair hint are `--muted`. Blocked has no verb in it, so a Repair row needs no variant.
- Technical detail (hover title and panel) for any row with `working`: `Technical detail: {working.reason}; earlier failure: {job reason}; working folder: {absolute path}` (the existing format and the existing rule: the path lives there and nowhere else).
- Budget: status 35 characters (limit 40). Blocked hint 104 characters, two to three lines in the cell.

#### 2.4 A: Retry clears first

- **Before the press (this is how A is communicated).** Three places, all from the table above: the hint clause, the Retry tooltip, and the Retry all and Retry selected dialogs.

  | Where | Text |
  |---|---|
  | Retry tooltip, `cleanable` and enabled (row and panel) | Clear the leftover working files, then check this book again and queue its audiobook job. |
  | Hint clause | Retry clears leftover working files first. |
  | Retry all and Retry selected dialogs | the existing question, then " {k} of them have leftover working files, which are cleared first." (k from the server; shown only when k is above 0) |

- **During the press.** Face "Checking…" (unchanged). Panel note and row hint: "Clearing working files, then checking this book…". The existing pending mode keeps focus.
- **After a successful press.** Silent about the files. The row reads "Queued — runs next" as today. Reason: the press said what it would do; a second mention is noise.
- **If the clear fails.** Nothing is queued. Note and row hint, `--warning`: "Retry was not accepted: the working files weren't cleared. Nothing was queued." The row then re-reads its state (usually blocked, with its own text). The cause words of section 2.5 go to Technical detail.
- **Rows where Retry cannot clear.** If Ender finds a kind of row whose Retry cannot take the clearing step, that row keeps Retry disabled with "Working files from an earlier attempt are still present. Clear them first, then retry." and the Clear button as its way out. Tell Judy which kind.
- **Bulk fallback.** If the server cannot supply k when the dialog opens (open item h), Retry all and Retry selected skip the cleanable rows and the count line says so (" · {k} left out: leftover working files"). It must not clear files in a bulk run with nothing on screen saying so.

#### 2.5 B: the Clear working files button

| Item | Spec |
|---|---|
| Exists when | `attention.working.state` is `cleanable`. In no other state, not even disabled. |
| Label | Clear working files (19 characters) |
| Accessible name | Clear working files: {title} (same pattern as "Retry: {title}") |
| Tooltip | Delete the working files an earlier attempt left behind. Originals are not touched. Frees about {size}. (the last sentence only when `bytes` is known) |
| Style and size | `quiet`, min 96 x 32, width follows the label. No red: the files are the app's own copies. Visible focus ring as every row button (3 px `--focus`). |
| Confirmation | **None.** The files are the app's own working copies, the app removes them itself for finished books without asking, Retry (A) removes them as a side effect, and Retry re-makes them when needed. The tooltip states the effect and the result line states what was removed. The safety is in the server: it deletes only files it can verify as its own, never a source copy unless the originals are verified, and keeps the rest. A dialog would add a step and no protection. |
| While pressed | Face "Clearing…", `aria-disabled` with the disabled look, keeps focus (its own press only). Note "Clearing working files…". |
| If this window has another request in flight | The button is not disabled. The press is answered in the note: "Another operation is in progress. Try again in a moment." |
| Success | The button leaves. Note and row hint (`--muted`): "Cleared {size} of working files." when `bytes` is known, "Working files cleared." when not, "Working files were already cleared." when nothing was left. The row's natural hint follows in the same line, for example "Cleared 637 MB of working files. Safe to retry now." |
| Success, the row | Held in place until the list next changes (it may move from Other to Can retry; it must not vanish under the pointer after Sergei pressed it). Focus moves to the same row's Retry when it is enabled, otherwise to the first remaining button, `preventScroll`. |
| Failure | Note and row hint in `--warning`, from the typed `cause` (table below). The button stays when the files are still cleanable and goes when the row is now blocked, with focus moving as above. |

Failure words (typed cause from the server; the UI never matches English):

| `cause` | Text |
|---|---|
| `busy` | Working files weren't cleared. The app is busy; try again in a moment. |
| `changed` | This book's status changed. Check the updated status above. |
| `not_safe` | Some working files weren't cleared. The app keeps any file it can't confirm is safe to delete. |
| `file_problem` | Some working files weren't cleared. A file couldn't be removed; try again in a moment. |
| missing or unknown | Working files weren't cleared. Select the row to read why. |

"Some" in two rows is deliberate: verified disposal can remove part of an attempt before it stops. The raw reason goes to Technical detail.

**Placement (no element covers another).** Slot order is Retry, Clear working files, View metadata, Source folders (or Open folder and its message span). Reason: Retry is the frequent control and stays first (Fitts); Clear acts on the same job and sits beside it; navigation controls stay last and where they are. The container is the existing wrapping flex row (gap 8 px, min-width 260 px); no absolute positioning, no new row.

```
Cleanable row, wide:     [Retry] [Clear working files] [View metadata] [Source folders]
Cleanable row, wrapped:  [Retry] [Clear working files]
                         [View metadata] [Source folders]
Blocked row:             [View metadata] [Source folders]
Ready row, no leftovers: [Retry] [View metadata] [Source folders]

Details panel (#retry-block):  [Retry] [Clear working files]
                               note line (polite live region)
```

Candidate rows with one source folder show "Open folder" and a message span instead of "Source folders"; that span must not be used for Clear's result.

#### 2.6 After clearing (Futaba's Minors 2 and 3)

**Timing. A row must never read its old state for minutes after the files are gone.** The 300 s page reuse is correct for a quiet catalog and wrong for this state.

| How the files went | The row updates |
|---|---|
| Clear working files, or Retry (A) | At once. The press answer carries the new state, and the server counts the press as a control (the generation bump every other control already does), so the next poll is a fresh read. |
| The app's own background cleanup | On the first poll after it commits (a catalog write already ends the quiet reuse; Ender confirms). |
| Removed outside the app | Within 60 s while the row is listed. Rows that carry a `working` state are re-read on a short timer and never held by the 300 s reuse. Rows with no `working` state need nothing. |

A short listing of a handful of folders is the whole cost. If Ender cannot do the 60 s bound, say what bound is possible; the copy does not change.

**The cleared-state text.**

| Situation | Status | Hint | Retry |
|---|---|---|---|
| Just cleared by Clear working files | natural | "Cleared {size} of working files." + natural hint (for example "Cleared 637 MB of working files. Safe to retry now.") until the held row is rebuilt | enabled |
| Files gone by any other route, or an old `working_files` record with no files left | natural: "Stopped — ready to retry" | Safe to retry now. | enabled; the normal tooltip |

The second row is the answer to Minor 3: no sentence about the earlier refusal, because the record no longer decides the row (section 2.2). "Waiting for cleanup" and "working files still present" appear nowhere once the files are gone. Group and counts: the row is in Can retry, in Retry all and Retry selected.

### 3. The Checking count follows each check (Futaba's Minor 1)

Expected behaviour: **the strip's "Checking · N" and each row's state follow every finished check, within 10 seconds of it, while the window is open.** Today everything waits for the end of the pass.

- Cadence, not per check: the server may batch. One refresh per interval, only when at least one check finished since the last, is enough. The pass-end refresh stays as the last one. If one status recompute costs more than a second on the real library, Ender may stretch the interval to 20 seconds and tell Judy.
- The count is the progress signal; no spinner, no per-row animation (unchanged).
- **Counts are conserved:** at every refresh the sum over all groups is the same as before it. A row that finishes moves to Can retry, Can repair, M4B not supported or Other (can't-open).
- **In the Checking view the list shrinks as checks finish.** No hold: Sergei pressed nothing on those rows, the same reasoning as the bulk runs (Follow-up 1, point 3a). The selected row, if its check finishes, stays selected and its panel updates in place.
- No announcement per change: the count is a button label, not a live region. The existing rule stays: when Checking reaches zero while it is the selected view, the view moves to Can retry, with the existing focus rule.
- A row never reads "checking" after its own check has finished (Futaba's P01).

### 4. What the UI needs from the API (names assumed; Ender confirms)

- `attention.working`: `{state: 'cleanable'|'blocked', bytes: int|null, reason: raw text, cause?: 'originals_unreachable'}`; absent when no leftover audio files. `working_folder` stays as it is (Technical detail only). The `working_files` refusal record no longer decides group, status, hint or `retry` (section 2.2); `attention.group` is `other` only for `blocked`.
- `retry`: `{allowed:true}` for `cleanable` rows whose Retry clears first; absent for `blocked`. `repair`: SUPERSEDED (Follow-up 3, section 3): `{allowed:true}` for a `cleanable` Repair row, which clears first.
- `POST /api/audiobook/clear-working` `{library, id, revision, job_id}`. Answer `{cleared:true, bytes, row}`; refusal 409 with `cause` (`busy`, `changed`, `not_safe`, `file_problem`) and the refreshed row. It uses the existing verified disposal, deletes nothing it cannot verify, never removes a source copy unless the originals are verified, and bumps the status generation.
- `POST /api/audiobook/retry` clears first when `working.state` is `cleanable`; on a clear failure it queues nothing and answers with the same typed cause. `retry-all` and Retry selected apply the same rule; the dialog count `working_cleanable` (cleanable rows among the rows about to be queued) is computed when the dialog opens, not on every poll.
- `attention.startover`: `'automatic'|'manual_draft'`, present only for a current `source_changed` refusal.
- `POST /api/audiobook/startover` `{library, id, revision, job_id}`. Answer `{set_aside:true, outcome:'automatic'|'manual_draft', status, row}`; refusal 409 with the existing "This book's status changed…" text. Server rules from Follow-up 1 stand (newest job, needs attention, no output, no publication record, compare-and-set on the row as read). New: the set-aside leaves no automatic record for this revision that would read Queued or Approved without a job; `candidate_status` ignores a set-aside job.
- Checking: a throttled status refresh while a repair-check pass runs (section 3).

### 5. What cannot be expressed as decided (reported, not invented)

1. **"No further press" for Start over.** True for the book. Not true for the pass: automatic processing must be running or be started by Sergei, and a book the current run already visited waits for the next run. The copy says "next pass" and "Start automatic processing". Start over does not start the pass; making it do so would be new behaviour, offered as O9. ANSWERED and SUPERSEDED by Follow-up 3, section 1 (Sergei: yes, it starts the pass when it is not running).
2. **"Processed automatically" for a book with a manual review.** Not true: the pass holds it as "Manual draft retained", and a single audiobook file cannot be queued by hand. The copy says so (section 1.2, 1.3). The decision is expressed as a hold, not as processing. SUPERSEDED in part by Follow-up 3, section 4: the hold now has a way out, and "its review was changed by hand" is not always true.
3. **"Clear working files only when cleanable files are present"** needs a server test for "cleanable" that does not exist today. Folders the app owns by receipt can be tested (the existing verified disposal). Older attempts with no receipt, and attempts it cannot verify, cannot be shown as cleanable truthfully; they read as blocked, with no button. The decision holds as long as the button follows the server's test and never its own guess.

### 6. Acceptance checks for Futaba (committed build; seeded records and folders, no real library)

Start over:
- A seeded `source_changed` row with prediction `automatic`: **Start over** (not Retry) in the row and the panel; hint and tooltip exactly as in section 1.2. Same with `manual_draft`: the second wording.
- SUPERSEDED by Follow-up 3, section 8 (the press now starts automatic processing; the result texts are new).
- After the press: the old job row, its journal and its working folder still exist; `candidate_status` is empty; the held row reads its Started over state (SUPERSEDED: it was "Pending"; Follow-up 3), never "Queued" without a job or "Needs attention"; after the list changes the row is out of Output needs attention and Other is one lower.
- (SUPERSEDED in part: the press starts the pass, Follow-up 3) With the pass running: an `automatic` book is researched and reaches Queued or "Held — {reason}". A `manual_draft` book reads "Held — Manual draft retained" (SUPERSEDED for a single M4B with a saved review: "Held — saved review kept", Follow-up 3, section 4) in the Held filter and stays so across two pass cycles until "Let the app handle it" is pressed.
- Prediction `automatic`, then change the book by hand before the press: the result follows the answer (`manual_draft`).
- A second press from an outdated view is refused with the existing message and changes nothing.

Working files:
- **Cleanable row** (folder with a receipt-owned attempt, originals present): status natural, hint clause present, Retry enabled with the section 2.4 tooltip, Clear working files present with its tooltip, group Can retry, counted in Retry all, whose dialog carries the k clause.
- **Clear:** press it. The folder is empty on disk, originals unchanged (hash compare), the old job row and journal intact; note "Cleared {size} of working files. Safe to retry now."; the button is gone; focus is on the row's Retry; the row stays in place until the list changes. Press with the files already gone: "Working files were already cleared."
- **Retry (A):** press Retry on a cleanable row: the folder is cleared first, then "Queued — runs next"; no sentence about the files after the press. Force the clear to fail: nothing is queued, the text of section 2.4 shows, the row re-reads.
- **Blocked row** (an unknown file in the folder, or originals unreachable): status "Stopped — can't clear working files", the section 2.3 hint, group Other, no Retry, no Clear working files; Technical detail has the reason and the absolute folder; nothing is deleted.
- **Never disabled:** inspect every row in Can retry and Other: Clear working files is either absent or enabled; the only `aria-disabled` state is its own "Clearing…".
- **Failure:** make removal fail (hold a file open). The matching failure text appears in warning colour, partial removal reads "Some", the row's state updates, focus stays or moves per section 2.5.
- **Repair row, cleanable:** SUPERSEDED by Follow-up 3, section 8 (Repair clears first).
- **Old record:** seed a `working_files` refusal with no folder: the row reads "Stopped — ready to retry" and "Safe to retry now.", Retry enabled, in Can retry. "Waiting for cleanup" and "still present" appear nowhere (Minor 3).
- **Timing (Minor 2):** after Clear or Retry, the next poll shows the new state with no wait. Remove a folder outside the app: the row updates within 60 s, not 5 minutes. The app's own background cleanup: the next poll.

Checking (Minor 1):
- With about 50 unchecked M4B rows: the server count and the strip label fall at least every 20 s (target 10 s), rows flip as their checks end, the sum over all groups stays constant at every poll, focus is not moved, nothing is announced per change; at zero the existing move to Can retry happens once.

Geometry and contrast:
- Rects at 1440, 1024, 700 and 200% zoom: a cleanable row (four buttons, wrapped to two lines at narrow widths), the panel toolbar with two buttons and the note, a blocked row (two buttons, three-line hint): no intersecting rects, no covered buttons (`elementFromPoint` per button), buttons at least 96 x 32 where present, the Open folder span clear of Clear's note.
- Contrast (calculated, same tokens): `--warning` text on `--surface` 11.18, `--row-hover` 8.31, `--row-selected` 6.23; `--muted` text on the same 8.92, 6.63, 4.97. All 4.5:1 or above. Every state is also stated in words.

### 7. Open items and offers

Open for Ender (answer by reporting back; none blocks the copy):
- (g) After a set-aside, does the book read "Pending" (SUPERSEDED in part: it reads its Started over state, Follow-up 3), with no automatic record that says Queued or Approved? Does `candidate_status` ignore the set-aside job everywhere (the queue gate, `approve_automatic`, the book list)?
- (h) Can the Retry all and Retry selected dialogs get `working_cleanable` when they open? If not, the section 2.4 fallback applies.
- (i) Which folders count as cleanable: receipt-owned attempts with verified originals, certainly. Older attempts with no receipt: can the app prove them safely, or do they read as blocked? Any class that cannot be proven is blocked, never cleanable.
- (j) Can rows carrying a `working` state be re-read on a short timer, and what bound is possible (target 60 s)?
- (k) Which row kinds can take the clearing step inside Retry (M4B rows certainly; the older non-M4B retry path)?
- (l) How long does a clear take on a 600 MB folder? If it can exceed the 15 s press timeout, the row keeps "Clearing…" and re-reads instead of reporting a failure.
- (m) A throttled refresh for the repair-check pass: the interval that keeps one recompute under about 10 percent of the time.

Offers (not done; Sergei decides):
- O7. ANSWERED (Sergei 2026-10-19: option A, the "Let the app handle it" button; Follow-up 3, section 4). Was: a way out of "Manual draft retained" for a single audiobook file: release the manual draft so the pass can approve it, or allow a manual queue after a manual review. Without it, every book Start over sends into (b) ends in a permanent hold.
- O8. ANSWERED (Sergei 2026-10-19: yes, with the condition that the status says what to do; Follow-up 3, section 2). Was: a marker or filter for books the pass has not reached yet, so a set-aside book is findable between the press and the pass ("Set aside — waiting for automatic processing"). Today it is one of all candidates, "Pending".
- O9. ANSWERED (Sergei 2026-10-19: yes; Follow-up 3, section 1). Was: Start over starts automatic processing when it is not running, or the result note offers a Start button. Today the note only says to start it.
- O10. ANSWERED (Sergei 2026-10-19: yes; Follow-up 3, section 3). Was: Repair also clears first (A is decided for Retry only; a Repair row with cleanable files shows a disabled Repair and the Clear button).
- O11. A "Clear working files" action for a whole filter (many books, one press), if the Other and Can retry counts show many leftovers. Disk space on the real library is the likely reason.

Process: appended to this file, uncommitted; Sully commits it before Ender is briefed. Doc-only: no code, git or app launch. Design basis: NN/g visibility of system status, error prevention, user control and freedom, plain-language recovery; Hick (one honest state per row, no dead controls, one button that exists only when it can work); Jakob (native buttons, title tooltips, hold-in-place as for Retry); Fitts (Retry first, Clear beside it); WCAG 2.2 AA 1.4.3, 2.4.7, 3.3.1, 4.1.3.


---

## Follow-up 3 — 2026-10-19: Start over starts the pass, the "Started over" marker, Repair clears first, "Let the app handle it", and the narrow table

Judy, UX spec for Ender. Build `de3e2b2`, branch `codex/books-electron-m1` (worktree `Worktrees/Books Arranger/electron-m1`). Scope: Sergei's answers of 2026-10-19 to O7 (option A), O8, O9 and O10, and the older Minor (the table scrolls sideways below about 950 px). Everything above stays in force unless this section overrides it. Basis: read-only look at `automatic_processing.py` (`start`, `_start_block_reason`, `_work`, `_manual_draft`, `manual_draft`), `groups.py` (`sync`, `save`), `review_backend.py` (`_context`, `_write`, `save`, `enrich`, `_page`), `merge_service.py` (`approve_automatic`, `candidate_status`, quiet reuse), `scanner.py` (refresh guard), `retry_refusal.py` (`stale`), `web/app.js` (`candidateStatus`, `renderRows`, `attentionText`, `rowAction`, `renderAutomatic*`, `filterOptions`), `web/style.css`, `web/index.html`, `desktop/main.js` (window minimum 950), and Futaba's interim QA (`BooksArranger_QA_RefusedRetry_de3e2b2_2026-10-19.md`, finding 4: table minimum 895 px, scrollWidth 895 against clientWidth 627 at 700 px). Nothing launched; no rects measured (target geometry for Futaba). Widths below are calculated from the CSS; Futaba confirms them. Contrast uses tokens already used above and no new colour.

**Earlier text changed because these answers made it false** (each is marked SUPERSEDED or ANSWERED in place, and points here): Follow-up 2: section 1.1 item 1 (last sentence) and item 2(b) (last sentence, "nothing releases that hold"); section 1.2 tooltips of both outcomes; section 1.3 intro, all four result texts, and the "row during the hold" paragraph; the section 1.3 diagram (first box, pass line, `manual_draft` box); the "gap is real" paragraph; section 1.4 closing sentence; section 2.3 row "cleanable, Repair row"; section 4 line for `repair`; section 5 items 1 and 2; section 6 checks for Start over (first line, the "Pending" clause, "Start the pass", the `manual_draft` status) and the "Repair row, cleanable" check; section 7 open item (g) and offers O7, O8, O9, O10.

### 0. What ships, in one table

| Decision | What Sergei gets |
|---|---|
| O9: Start over starts the pass | One press sets the failed job aside and, when automatic processing is not running, starts it. If it cannot start (conversion running, scan running), the set-aside still happens and the note and the row say why and what to press (section 1). SUPERSEDED in part by Follow-up 4, section 1 (Sergei, O12): for a running conversion, scan or stop the app now starts it by itself when that clears. |
| O8: marker, filter and plain status | Every book Sergei sends back to automatic processing carries a **Started over** marker until it is queued: its own status words, a one-line hint that says whether he must do anything, a **Started over** entry in the Status list, and a one-line summary above the list (section 2). |
| O10: Repair clears first | Repair on a row with cleanable leftovers is enabled and clears them first, exactly like Retry (section 3). |
| O7, option A: "Let the app handle it" | A button on a single-M4B book held for its saved review. After one confirmation it discards the saved review (hand edits included), starts the pass if needed, and the book joins the Started over marker (section 4). |
| Narrow table | Nothing scrolls sideways: three width bands; the two low-value columns fold into the title cell; below 600 px a row becomes a stacked block (section 5). |

### 1. O9: Start over also starts automatic processing

#### 1.1 What the code does that the answer does not say

1. **Start can be refused, and often will be.** `start()` is the Start button's call. It raises while audiobook conversion is Running or Pausing, while a library scan runs, while the run is Stopping, when a failure record could not be saved, and when the app's own state is unknown. Conversion running is the likely one. The set-aside must stand either way: Start over never fails because the start was refused. SUPERSEDED in part by Follow-up 4, section 1 (a conversion, scan or stop in progress no longer ends as a refusal: the start waits and happens by itself; only a blocker that cannot clear shows the refusal). The server sends the refusal text and the page shows it verbatim (it is the app's own sentence, already shown beside the Start button).
2. **Starting is the whole run, not one book.** A finished or failed run (or none) begins a new run: queued conversions finish first, then the library is scanned, then every book not yet done is researched. A paused run (after Stop or an app restart) continues from its saved list with no new scan. So "starts automatic processing" means "this book may wait a long time", and the copy says so. Two outcomes, `started` and `continued`, read differently.
3. **A visited book is not visited again in the same run.** The stuck book was counted done when the pass saw its job. For the pass to take it, Start over must put it back on the run's pending list (for a run that will be resumed or is running). If the run is already past research, the book waits for the next run. Ender reports which (open item n). Both outcomes have copy below, so the words stay true whichever he can do.
4. **The press starts the pass even for a book it will only hold.** The decision is blanket, so a book with a saved review (section 4) starts a whole pass to be held. Observation, not a change; Jane can exempt it if wanted.
5. **The page must take the fresh pass state from the answer** (as `automaticAction` does for the Start button), so the top status line and the hints below do not wait for the next poll.

#### 1.2 Words before the press

The row hint before the press (Follow-up 2, section 1.2) stands. Only the tooltip changes.

| Server `attention.startover` | Tooltip of Start over |
|---|---|
| `automatic` | Set this failed job aside and send the book back to automatic processing. Starts automatic processing if it isn't running. Nothing is deleted. |
| `manual_draft` | Set this failed job aside. Starts automatic processing if it isn't running. The book has a saved review, so automatic processing will hold it; "Let the app handle it" can then release it. Nothing is deleted. |

Pending face "Starting over…", pending note "Setting this job aside…", the accessible name and the placement are unchanged.

#### 1.3 Words after the press

Shown in the details panel note (`#retry-note`, polite live region). The server's `pass.action` and `pass.visit` choose the sentence; the page's own state is only the fallback.

| Answer | Text | Colour |
|---|---|---|
| `started` | Started over. Automatic processing has started. It scans the library first, so this may take a while. | `--muted` |
| `continued` | Started over. Automatic processing continued where it paused. | `--muted` |
| `running`, `visit` this run (or absent) | Started over. Automatic processing is running and will reach this book. | `--muted` |
| `running`, `visit` next run | Started over. Automatic processing is running but has already passed this book. Press Start automatic processing above after it finishes. | `--warning` |
| `blocked` | SUPERSEDED for a blocker that clears (Follow-up 4, section 1.2). Kept only for a blocker that cannot clear: Started over, but automatic processing did not start. {server reason} | `--warning` |
| no `pass` in the answer | Started over. The book goes back to automatic processing. | `--muted` |
| refused | unchanged: "Start over was not accepted. Check the status above." (outdated view: "This book's status changed. Check the updated status above.") | `--warning` |

Rules: every success text ends with " Find it under Status: Started over." (recognition over recall: the row leaves Output needs attention). For `manual_draft`, insert before that sentence: " Automatic processing will then hold this book because it has a saved review; Let the app handle it appears once it is held." and use `--warning` (a decision is waiting). No toast, no dialog, no focus theft (unchanged).

#### 1.4 The held row after the press

Replaces Follow-up 2, section 1.3, "The row during the hold". The answer carries the refreshed row, which now has the Started over marker (section 2). The held row shows that state's status and hint (section 2.2), normally "Started over — waiting its turn" or "Started over — waiting for you". It never reads "Pending", never "Needs attention", never the old job. The result text above goes to the panel note only. Hold lifetime, remaining buttons, no toast and the focus rule (first remaining button, `preventScroll`) are unchanged.

### 2. O8: the Started over marker, filter and plain status

#### 2.1 What the code does that the answer does not say

1. **Nothing marks the book today.** After the set-aside it has no job; its row falls through the status chain in `candidateStatus` (generic "Pending", or "Candidate changed" if its status text contains "changed", which a book whose files changed can). Held lists only books the pass has recorded as held, so a waiting book is in All candidates only. The marker must come from the server and must be checked before those rules.
2. **The pass moves a book through recorded states:** none or Pending, Researching, Waiting for source, Held (with reasons), Needs attention (an error), then a new job. A pause or an app restart resets Researching to Pending, so a book can go back from "researching" to "waiting". The UI follows it.
3. **Held books retry only while the run is Running** (15 minutes, doubling to 24 hours). A held book is not "finished" in the sense Sergei means; it is waiting for a later try. The held hint says so.
4. **A failed book (an error on that book) is retried by pressing Start.** The server already sends the matching retry help; the hint names the same press.

#### 2.2 The states: status, hint, and what Sergei does

Marker lifetime: from the press until the book's new job exists. While it lasts, the marker also covers a book Sergei released with "Let the app handle it" (section 4). The server sends `restart.state`; the page composes the sentence with the live pass state (`state.automatic_processing`). Status budget 40 characters (longest here 35). Sentence case, final period, em dash separator. "Press" and "Nothing to do" tell Sergei what to do in words; colour only repeats it.

| `restart.state` and pass | Status | Hint | Sergei | Colour |
|---|---|---|---|---|
| waiting, pass Running | Started over — waiting its turn | Nothing to do. Automatic processing will research this book and queue it if the match is safe. | nothing | `--muted` |
| waiting, pass Running, `visit` next run (fallback) | Started over — next run | Automatic processing has already passed this book. Press Start automatic processing above after it finishes. | press Start later | `--warning` |
| waiting, pass not Running, `can_start` | Started over — waiting for you | Press Start automatic processing above. It will then research this book and queue it if the match is safe. | press Start | `--warning` |
| waiting, pass not Running, start blocked by a blocker that cannot clear (SUPERSEDED for a conversion, scan or stop: Follow-up 4, section 1.3) | Started over — waiting for you | Automatic processing can't start yet. {`start_block_reason`, verbatim} | follow that sentence | `--warning` |
| waiting, `expect` hold (section 4), pass Running | Started over — waiting its turn | Nothing to do yet. Automatic processing will hold this book because it has a saved review. Then Let the app handle it appears here. (SUPERSEDED in part by Follow-up 4, section 2: the last sentence only when the book is a single M4B) | nothing yet | `--muted` |
| waiting, `expect` hold, pass not Running | Started over — waiting for you | Press Start automatic processing above. It will then hold this book because it has a saved review, and Let the app handle it appears here. (SUPERSEDED in part by Follow-up 4, section 2: that clause only when the book is a single M4B) (blocked: the "can't start yet" hint above) | press Start | `--warning` |
| waiting, pass state unknown or disconnected | Started over — waiting | Reconnecting to the app. This row updates when it is back. | nothing | `--muted` |
| working: researching (pass Running) | Started over — researching | Nothing to do. Automatic processing is looking this book up now. It queues the book if the match is safe. | nothing | `--muted` |
| working: waiting for a source (pass Running) | Started over — waiting for a source | Nothing to do. A metadata source is busy. Automatic processing tries again by itself. | nothing | `--muted` |
| working, pass not Running | shown as "waiting, pass not Running" (a paused run resets it) | | | |
| held (not a saved-review hold) | Held — {reason} (existing) | Nothing to do. Automatic processing couldn't approve this book safely. It tries again after {date}, while it is running. (no date: "It tries again later, while it is running.") | nothing | `--muted` |
| held for a saved review, release allowed (section 4) | Held — saved review kept | A saved review keeps this book held. Let the app handle it discards that review, including any hand edits, and lets automatic processing take the book. | decide: press, or leave it | `--warning` |
| held for a saved review, editor open (lease) | Held — Manual draft retained (existing) | You are editing this book. Automatic processing waits until you stop. | nothing | `--muted` |
| held for a saved review, no release (other books) | Held — Manual draft retained (existing) | Automatic processing holds this book because it has a saved review. | nothing in this app | `--muted` |
| failed (an error on this book) | Needs attention — {reason} (existing) | Automatic processing hit an error on this book. Press Start automatic processing above to try again. | press Start | `--warning` |
| failed, start blocked | as above | Automatic processing hit an error on this book. It can't start again yet. {`start_block_reason`, verbatim} | follow that sentence | `--warning` |
| queued (new job Queued or Creating) | existing job status | Queued by automatic processing after Start over. Nothing to do. | nothing | `--muted` |

Notes:
- The "Held — saved review kept" status replaces the app's own reason text "Manual draft retained" only in the release-allowed state; "draft" is jargon and the word "manual" is not always true (section 4.1). The other two saved-review rows keep the existing status. The Follow-up 2 sentence "its review was changed by hand" must not be shown anywhere.
- Status text for `waiting` and `working` is supplied by the marker; for held, failed and queued the existing status chain supplies it and the marker adds the hint only.
- Precedence in `candidateStatus`: attention, then a queued-next readmission, then the marker, then the existing chain. A book with a failed new job is an attention row and the marker has ended.
- The row hint is the same text in the panel (`#automatic-result-hint`), plus a fact line "Started over: {date}" in the panel list. No new control in this section.

#### 2.3 The Started over filter and the summary line

- **Filter.** One new entry in the candidate Status list, after "Output needs attention": **Started over**. Always listed (no counts in this list, and options that appear and disappear would move the list under the pointer). Option title: "Show books you started over that automatic processing has not queued yet." It lists books whose marker is waiting, working, held or failed, sorted failed, waiting, working, held (the ones that need him first), then by scope. A book leaves it when its new job exists; it then shows under Queued / creating with the queued hint.
- **Empty text:** "No books are waiting after Start over. Books you start over appear here until automatic processing queues them."
- **Summary line.** One plain paragraph (`field-help`, not a live region) under the filter row, shown only in this filter. Format: `{T} book(s) started over: {parts}. {tail}` with parts in this order, zero parts omitted: "{n} waiting", "{n} being processed", "{n} held", "{n} stopped on an error". Tail, all that match joined in this order: needs a start (pass not Running and any waiting, working or failed): "Press Start automatic processing above." (blocked: "Automatic processing can't start yet. {reason}"; SUPERSEDED for a conversion, scan or stop: Follow-up 4, section 1.3); any book in `visit` next run: "Press Start automatic processing above after this run finishes."; any held for a saved review with release allowed: "{r} held for a saved review: press Let the app handle it on a book to release it, or leave it held."; none of these: "Nothing for you to do."
  Examples: "12 books started over: 9 waiting, 2 being processed, 1 held. Nothing for you to do." / "12 books started over: 12 waiting. Press Start automatic processing above." / "1 book started over: 1 held. 1 held for a saved review: press Let the app handle it on a book to release it, or leave it held."
  The counts are global (not the page's 100 rows), from the server.
- **Live update.** Hints that depend on the pass (waiting, waiting for a source, failed, held with a date) and the summary line are recomputed when `automatic_processing` changes, in place, as `updateRowRetries` does: no row rebuild, no focus move, no announcement. Each row follows the pass within one poll (800 ms) of the pass recording its result.

```
press Start over (or Let the app handle it)
   |  server: marker "waiting"; pass started / continued / already running / blocked
   v
Started over — waiting its turn   (pass off or blocked: "— waiting for you" + what to press)
   |  the pass reaches the book
   +--> Started over — researching / waiting for a source
   |         |--> queued (a new job)         marker ends; Queued / creating; later Audiobook Ready
   |         |--> Held — {reason}            stays under Started over and Held; retries by itself while running
   |         |--> Needs attention — {reason} stays; press Start to retry
   +--> Held — saved review kept             press "Let the app handle it", or leave it (section 4)
```

### 3. O10: Repair also clears leftover working files first

Same rule as Retry (Follow-up 2, section 2.4), with the verb following the row.

| Where | Text |
|---|---|
| Repair tooltip, `cleanable` and enabled (row and panel) | Clear the leftover working files, patch the damage found in this book, then queue its audiobook job. |
| Hint clause, after the damage hint | Repair clears leftover working files first. |
| During the press (note and row hint) | Clearing working files, then repairing this book… (face "Repairing…" unchanged) |
| Clear fails (note and row hint, `--warning`) | Repair was not accepted: the working files weren't cleared. Nothing was queued. |
| After success | Silent about the files; the row reads "Queued — runs next". |
| Retry selected dialog | The existing clause; k counts Retry and Repair rows alike (Retry selected already takes both). |
| Clear working files button | Unchanged: still rendered on a cleanable Repair row, same tooltip, same results. |
| Blocked | Unchanged (the blocked row has no Retry or Repair). |

Fallback, only if Ender finds a Repair that cannot take the clearing step (tell Judy which): that row keeps Repair **disabled** with the tooltip and reason "Working files from an earlier attempt are still present. Clear them first, then repair.", the hint clause " Clear the working files, then repair.", and the Clear button as its way out (the superseded Follow-up 2 row).

### 4. O7, option A: the "Let the app handle it" button

#### 4.1 Facts from the code (answers Ender's question about a rescan)

**Yes: a rescan alone can land a book in "Manual draft retained", with no hand edit involved.** The chain, all in the code:

1. A scan that changes a file row (path, size, modified time, kind, metadata, error flag or missing flag) bumps the catalog. `groups.sync` then recomputes the book's evidence; if the fingerprint differs it sets `revision+1, approved=0, changed=1`. The saved review (`book_groups.review`, written by the automatic pass or by Sergei) is kept.
2. The approval record lives in `candidate_context` at the revision it was made. `_context(row)` returns `{}` when the stored revision is not the book's current one. So the new revision has no `automatic_approval` and no `automatic_pending`.
3. `_manual_draft(row)` is true when the book has a review and its current-revision context has neither of those. That is now true, though nobody edited anything. The pass visits the book (a book with a job is skipped first, so this applies once it has no job) and records Held, "Manual draft retained", re-checked every 5 minutes with the same result.
4. A scan that changes nothing does nothing. A scan during a drive outage flags files missing, the next one flags them found: each flip changes the evidence, so one outage can send many reviewed books into this hold at once (from the code path; Futaba can reproduce it).

Other causes: Sergei saved a review or confirmed tracks by hand (actor `user` removes the approval record); the browser editing lease (an open editor, expires 5 minutes after it stops being renewed, then the hold ends by itself). `manual_draft_active` is read but never written outside tests.

**What this means for how often Sergei sees it.** A stuck "review changed" book is stuck because its revision moved after the job was frozen, so its approval record is orphaned. After Start over (the job is set aside) the book is tested as a saved-review book. I expect this to be the usual outcome for those books, not a corner case, unless the revision did not move. I cannot count them without data. So the sequence Start over, wait for the pass to hold the book, press "Let the app handle it", confirm is the normal path: see offers O13 and O14. ANSWERED by Follow-up 4 (O13: one press for a book known to hold; O14: the bulk release).

**What it means for wording.** The app cannot tell a hand edit from an automatic review kept across a rescan. Copy never says "you edited" or "changed by hand"; it says "saved review, including any hand edits".

#### 4.2 When the button appears, and only then

Server-typed `row.release.allowed`, true only when all of these hold; otherwise the button is not rendered (no disabled ghost: Sergei can fix none of them from the row):
1. The pass has recorded the book as Held for a saved review ("Manual draft retained"), at the book's current revision. Not before the pass has visited it.
2. The hold comes from the saved review, not from the editing lease alone (a lease-only hold ends by itself; row text in section 2.2).
3. The book is exactly one included source file, and it is an `.m4b` (the case Sergei decided; a multi-file book can still be queued by hand).
4. The book has no current job, no release or set-aside in progress, and no editing lease is active now.

It shows in the Held filter, All candidates and Started over alike (it follows the book, not the filter), in the row and in the details panel.

#### 4.3 The button

| Item | Spec |
|---|---|
| Label | Let the app handle it (21 characters; Sergei's wording) |
| Accessible name | Let the app handle it: {title} (same pattern as "Retry: {title}") |
| Tooltip | Discard this book's saved review, including any edits you made by hand, and let automatic processing take the book. Starts automatic processing if it isn't running. This can't be undone. Your audio files are not touched. |
| Style, size | `quiet`, min 96 x 32, width follows the label; the label may wrap to two lines in a narrow Actions cell (never truncated). No red. Visible focus ring as every row button. |
| While pressed | Face "Discarding review…", `aria-disabled` with the disabled look, keeps focus. Note "Discarding the saved review…". |
| Placement | First slot of the Actions cell (this row has no Retry), then View metadata, then Source folders (or Open folder and its message span). Details panel: the first button of the same toolbar slot Retry and Start over use, the note line below it. Existing wrapping flex row (gap 8 px); no absolute positioning; nothing moves another control. |

#### 4.4 Confirmation: yes, recommended

Discarding the saved review loses metadata, cover and track choices Sergei may have made by hand, and there is no restore. One step before an irreversible loss is the rule (error prevention). Use the same pattern as the recovery-copies dialog: a native modal `<dialog>`, Cancel first and focused, the confirm button named for what it does. Rejected: an inline confirm inside the table row (it changes the row height under the pointer and crowds a narrow Actions cell); no confirm with an undo (there is nothing to undo from).

| Item | Text |
|---|---|
| Title | Discard this book's saved review? |
| Book line | {title clue} |
| Body 1 | This deletes the metadata, cover and track choices saved on this book, including any you made by hand. It can't be undone. |
| Body 2 | Automatic processing then researches the book again and queues it if the match is safe. It starts if it isn't running. Your audio files are not touched. |
| Buttons | [Cancel] (default focus) and [Discard review] |
| Cancel tooltip | Keep the saved review and leave this book held. |
| Discard review tooltip | Delete this book's saved review, then let automatic processing take the book. This can't be undone. |

Width `min(560px, calc(100vw - 24px))`, scrolls if short, Esc and Cancel close with no change, focus returns to the row's button. Confirm closes the dialog at once; the button then shows its pending face (it keeps focus). If Ender can tell the saved review was written by the app and never by Sergei (open item r), the confirm may be skipped for that book and the tooltip's second clause changed to "The saved review was written by the app." That is a refinement; the baseline always confirms.

#### 4.5 After the press: result and status

The marker (section 2) starts at once, so the book joins Started over. The result note (panel, polite) is built like section 1.3 with "Review discarded." in place of "Started over.":

| Answer | Text |
|---|---|
| `started` | Review discarded. Automatic processing has started. It scans the library first, so this may take a while. Find it under Status: Started over. |
| `continued` | Review discarded. Automatic processing continued where it paused. Find it under Status: Started over. |
| `running` | Review discarded. Automatic processing is running and will reach this book. Find it under Status: Started over. |
| `running`, next run | Review discarded. Automatic processing is running but has already passed this book. Press Start automatic processing above after it finishes. (`--warning`) |
| `blocked` | (SUPERSEDED for a blocker that clears: Follow-up 4, section 1.2) Review discarded, but automatic processing did not start. {server reason} (`--warning`) |
| no `pass` | Review discarded. The book goes back to automatic processing. |
| refused, outdated view | This book's status changed. Check the updated status above. (`--warning`) |
| refused, editor open | This book is being edited. Finish editing, then try again. (`--warning`) |
| refused, busy | The review wasn't discarded. The app is busy; try again in a moment. (`--warning`) |
| refused, unknown | The review wasn't discarded. Select the row to read why. (`--warning`) |

The row is held in place for the usual lifetime and reads "Started over — waiting its turn" (or "waiting for you" with the section 2.2 hint when the pass is blocked or off), never "Held". Focus moves to the row's first remaining button, `preventScroll`. From there the book follows section 2.2 (researching, queued, held for another reason, failed). It cannot return to "saved review kept" unless a review exists again.

#### 4.6 Not specced

No bulk release (offer O14), no restore, no change to the multi-file case, no change to when the pass tests a book.

### 5. The narrow table (older Minor: Futaba finding 4)

#### 5.1 Why it scrolls (calculated from `style.css`, matches Futaba's 895 px)

- Candidate columns: Select, Title clue, Author / reader clues, Audio files, Review status, Actions. Rules written for the Files view still apply: `td:nth-child(3), td:nth-child(4)` hold 170 px each, so "Audio files" (a bare count) claims 170 px; `td:last-child` holds 240 px and `.row-actions` holds 260 px, so Actions needs about 280 even when one button per line would fit; `th` is `nowrap`, so headers set widths. Minimum about 895 px.
- Page chrome takes 82 px (24 px page padding each side, 16 px panel padding each side, borders; 12 px page padding below 760 px), plus a 15 px page scrollbar and a 15 px scrollbar inside the table box when rows exceed 430 px. So the box is wide enough only above about 990 px, and the window's own minimum is 950: the table probably scrolls at the smallest allowed window. Futaba: confirm at 950.
- The columns that fall off-screen are the last ones: Retry and View metadata, the controls.
- Scope: "the review table" means the book list. The track table inside Manual review has its own scroll box and is not changed. The same rules cover the Files view (section 5.4).

#### 5.2 The three bands

Bands follow the width of the table's own box (a container query on the box; the page already uses one on `#audio-jobs`), not the window, so a side panel or zoom cannot put a row between bands. Design minimums add up below each band's lower edge, so nothing needs to scroll.

| | Wide (box 800 px and up) | Medium (600 to 799) | Compact (under 600) |
|---|---|---|---|
| Select | own column, 64 | own column, 56 | top-left of the row block |
| Title clue | own column, min 140 | own column, min 160, with a second line (below) | block title, wraps, as today |
| Author / reader clues | own column, min 120 | hidden; shown in the title cell's second line | hidden; second line |
| Audio files | own column, 72 (header wraps "Audio / files") | hidden; second line | hidden; second line |
| Review status | own column, min 180 | own column, min 180 | block under the title, full width |
| Actions | own column, min 170, max 280 (two buttons per line) | own column, min 170 (one button per line where two do not fit) | block under the status; buttons wrap in a row |
| Header row | sticky as today; headers may wrap | sticky; four headers | visually hidden, still exposed to assistive technology |
| Design minimums | 746 | 566 | n/a |

Second line in the title cell (medium and compact): "{author / reader clues, or Unknown} · {n} audio files" ("1 audio file"), `--muted`, 13 px, wraps. It is the same text as the two folded columns. The folded cells and the second line are `display:none` in the bands where they are not shown, so a screen reader reads each fact once.

Calculated equivalents (page padding 24 px, or 12 px up to 760): the wide band holds down to a viewport of about 912; at the 950 minimum the box is about 838 (38 px spare). At 720 and 700 the box is about 632 and 612 (medium). At 640 it is about 552 and at 475 about 387 (compact). Futaba measures `clientWidth` at each.

```
Wide (950+):
[ ] Title clue ........ | Author / reader ..... | 12 | Status          | [Retry]  [Clear working files]
                                                        hint text wraps    [View metadata] [Source folders]
Medium (about 700):
[ ] Title clue ........  | Status             | [Retry]
    Author · 12 audio     | hint text wraps    | [View metadata]
    files                 |                    | [Source folders]
Compact (about 475 and 200% zoom):
+------------------------------------------+
| [ ] Title clue (wraps)                    |
|     Author · 12 audio files               |
|     Status                                |
|     hint text wraps, full width           |
|     [Retry] [View metadata]               |
|     [Source folders]                      |
+------------------------------------------+
```

#### 5.3 Rules (what wraps, collapses, hides; nothing covers anything)

- **Wraps:** headers (wide, medium), title, second line, status, hint, and the buttons of the Actions cell. Every cell takes `overflow-wrap:anywhere` (today only the last column has it), so a long unbroken title or path cannot widen the table.
- **Collapses:** Author / reader clues and Audio files fold into the title cell's second line at medium and compact.
- **Hides:** the two folded cells and their headers (medium, compact), and the header row (compact, visually only).
- **Drops:** the 170 px minimums on columns 3 and 4, the 240 px on the last cell and the 260 px on `.row-actions`; the Actions box keeps a 280 px cap in the wide band so two buttons still sit on a line.
- **Buttons:** order unchanged (action first, Clear working files, View metadata, Source folders or Open folder and its message span), gap 8 px, each min 96 x 32; long faces ("Let the app handle it", "Clear working files") may wrap to two lines, never clip.
- **No overlap:** no absolute positioning for the checkbox or the buttons; in compact the checkbox has its own 40 px column; the 24 x 24 checkbox target and the 32 px row-button height are kept; the focus ring (3 px, inset on the row) is not clipped.
- **Table meaning:** if Ender changes `display` on rows or cells for the compact block, add explicit `role` values (`table`, `rowgroup`, `row`, `columnheader`, `cell`) so the table keeps its meaning for a screen reader. Futaba reads the accessibility tree.
- **Order and keyboard:** Tab order is the same in every band (checkbox, then the row's buttons); Enter or Space on the row still selects it.
- **Sticky header:** wide and medium only; in compact it is gone, so it cannot cover a row.

#### 5.4 The Files view

Its seven columns (Type, Arrival, title, author, Preview status, Proposed destination, Actions) have design minimums of 918. Wide at box 1000 and up; below that it uses the compact block: title first, then "Type · Arrival · author", Preview status, the proposed destination (path style, wraps anywhere), then the buttons. There is no medium band.

### 6. Ender's non-UI bug: a catalog with no `audio-staging` folder

No new copy for the fix itself. One visible state is involved: rows refused under the bug are recorded as `file_problem`, whose fix is `user`, and `retry_refusal.stale()` only ever makes an `update` fix stale. So after the fix those rows keep reading "Stopped — file problem … Check the folder, then retry." (wrong: there is no folder to check), sit in Other, and are left out of Retry all, until each Retry is pressed. Recommended: a one-time conversion, as `convert_legacy` does, that marks those records stale when the fix ships, keyed on their raw text. They then read the existing stale text ("Stopped — try again": "Retry was refused in v{version}; the app was updated since. It may work now.") and return to Can retry. If Ender prefers not to, no copy changes: one Retry press per row clears it. Tell Judy which.

### 7. What the UI needs from the API (names assumed; Ender confirms)

- `row.restart`: `{state:'waiting'|'working'|'held'|'failed'|'queued', source_wait?:bool, visit?:'this_run'|'next_run', expect?:'hold', at}`; absent when no marker. Keyed by book, not by revision. Created by Start over and by release; ends when the new job is `Audiobook created` or needs attention. On page rows and on every answer's `row`.
- `row.automatic.hold`: `'manual_draft'` when the pass recorded the saved-review hold. `row.release`: `{allowed:bool}` (section 4.2). `row.restart.expect:'hold'` when a waiting book will be held (the same read-only `manual_draft` test, run at list time).
- `POST /api/audiobook/startover` answer gains `pass:{action:'started'|'continued'|'running'|'blocked', visit?, reason?}` and a fresh `automatic_processing`. `reason` is `start_block_reason` verbatim. The press is never refused because the start was.
- `POST /api/audiobook/release` `{library, id, revision}`. Does: discard the book's saved review and its context (notes, evidence, cover and track choices) and any editing lease; reset its automatic record to Pending; put it on the run's pending list; keep its sources and any older job; start the pass as Start over does. Compare-and-set on the revision and review as read. Answer `{released:true, pass, automatic_processing, row}`; refusal 409 with `cause` (`changed`, `editing`, `busy`) and the refreshed row.
- Candidate list: `status='restarted'` (the filter), ordered failed, waiting, working, held; response carries `restart_counts:{waiting, working, held, failed, next_run, release}` (global), only for this filter.
- `POST /api/audiobook/repair` and the bulk paths clear first when `working.state` is `cleanable` (section 3); `repair:{allowed:true}` for those rows.
- Hints that depend on the pass read `automatic_processing.state`, `can_start` and `start_block_reason` from the polled state.

### 8. Acceptance checks for Futaba (committed build; seeded records and folders, no real library)

Start over and the pass:
- Pass Idle, nothing blocking: press Start over. `pass.action` is `started`; the top line shows Running; the panel note is the `started` text exactly; the held row reads "Started over — waiting its turn" with its hint; no "Pending", no "Needs attention". Same with a paused run (`continued`), and with the pass already Running (`running`).
- SUPERSEDED for a running conversion or scan by Follow-up 4, section 6 (the start waits and happens by itself); holds only for a blocker that cannot clear. Conversion Running: the set-aside still happens; the note is the `blocked` text with the server's sentence verbatim; the row reads "Started over — waiting for you" with "Automatic processing can't start yet. …". Pause the jobs: within one poll the hint becomes "Press Start automatic processing above. …" with no row rebuild and no focus change. Press Start: the row moves through waiting its turn, researching, then Queued.
- `visit` next run (if Ender cannot reopen the book): the next-run texts, warning colour.
- Disconnected answer: the neutral text. Outdated view: the existing refusal, nothing changes. Old job row, journal and working folder still exist.
- A `manual_draft` book: the press starts the pass; the note has the saved-review sentence in warning colour; the row reads the `expect` hint.

Marker, filter, summary:
- The Started over entry is in the Status list after Output needs attention, with its tooltip. A seeded mix of 12 (9 waiting, 2 working, 1 held): rows ordered failed, waiting, working, held; the summary line exact ("12 books started over: 9 waiting, 2 being processed, 1 held. Nothing for you to do."); singular forms; with the pass off the tail is "Press Start automatic processing above."; blocked, the tail carries the reason; with a release-allowed held book the release tail shows.
- Every state in section 2.2 reads exactly; every status 40 characters or fewer; "Nothing to do" rows are `--muted`, "Press" and decision rows `--warning`.
- A seeded row whose status text contains "changed" reads its marker state, not "Candidate changed" or "Pending".
- A book whose new job is Queued or Creating leaves the filter, reads "Queued by automatic processing after Start over. Nothing to do.", and the hint is gone at Audiobook created. A book whose new job needs attention is an attention row with no marker.
- The Other count falls by one on the press; the sums over all attention groups are conserved. The marker survives an app restart (the pass reads Paused, so rows read "waiting for you").
- Empty text exact.

Repair clears first:
- A cleanable Repair row: Repair enabled, tooltip and hint clause exact, Clear working files present. Press: note "Clearing working files, then repairing this book…", folder cleared, then "Queued — runs next" with nothing said about the files. Force the clear to fail: the Repair text, nothing queued. The Retry selected dialog's k includes the Repair row.

"Let the app handle it":
- Seed a single-M4B book with a saved review, no approval record at its current revision, the pass's Held "Manual draft retained", no lease: status "Held — saved review kept", hint exact, button first in the Actions cell and in the panel, tooltip exact.
- Negative controls, each with no button: a multi-file book with the same hold; a single M4B with an active editing lease (hint "You are editing this book…"); a book with a job; a book held for another reason; a single M4B with an approval record at its current revision, not held.
- Rescan control (frequency evidence): an app-approved single M4B, no job; change one file's modified time; rescan; the book is held as "saved review kept" with no hand edit.
- Press: the dialog opens and nothing else happens; Cancel has focus; Esc closes with no change and focus returns to the button. Confirm: pending face, then the result note exact for each pass variant; the saved review and context are gone; audio files unchanged (hash compare); older job row intact; the automatic record is reset; the row is held in place reading the Started over state; the pass takes it with no further press (researching, then Queued, or Held for another reason).
- Refusals: lease active, outdated view, busy: texts exact.
- The dialog at 475 px and 200% zoom fits, buttons at least 96 x 32, nothing covered.

Narrow table (rects and `scrollWidth` at 1440, 1024, 950, 720, 700, 640, 475, at the box widths 800 and 799 and 600 and 599, and at 200% zoom of the 950 and 1440 windows):
- `scrollWidth` is at most `clientWidth` on the table box at every width; no page-level horizontal scroll.
- Band per width as in section 5.2; the Author and Audio-files text appears once per row in the accessibility tree; headers present in the tree at compact.
- No intersecting rects among checkbox, title, second line, status, hint and every button; `elementFromPoint` finds each button at its centre; buttons at least 96 x 32; checkbox target at least 24 x 24; Retry and View metadata on screen without scrolling at 950 and 700.
- A 60-character title with no spaces and a 200-character hint at 475: no overflow. A row with four buttons wrapped in the compact block, and a row with "Let the app handle it" in a 170 px Actions cell: the label wraps, nothing clips.
- Tab order is the same in every band; focus ring not clipped. The strip, the filter row, the summary line and the batch controls wrap with no overlap at 475.
- Files view: wide at 1000, compact block below.

Contrast (calculated, same tokens, no new colour): `--warning` text on `--surface` 11.18, `--row-hover` 8.31, `--row-selected` 6.23; `--muted` text on the same 8.92, 6.63, 4.97. All 4.5:1 or above. Every state is also stated in words.

### 9. What cannot be expressed as decided, open items and offers

Reported, not invented:
1. **O9, "starts automatic processing when it isn't running":** expressible, with three limits the copy states: the start can be refused (conversion or a scan running), so "no further press" is not always true (SUPERSEDED in part by Follow-up 4: it is true across a conversion, scan or stop, which the app now waits out); the start is a whole run (queued conversions, then a library scan, then research), not one book; and a book already visited by a run is not visited again unless the server puts it back (open item n; the `next run` words are the fallback).
2. **O8:** expressible, but not from today's row data. The row cannot say "waiting" or "researching" for a set-aside book, and the status chain may read "Candidate changed". The server marker in section 7 is required.
3. **O7, "drops Sergei's hand edits":** the hold is not always caused by hand edits (section 4.1). The words say "saved review, including any hand edits". What the button discards can be the app's own earlier review.
4. **How often:** the hold is probably the usual outcome for "review changed" stuck books (4.1). Recommended with it: O13.

Open for Ender (report back; none blocks the copy):
- (n) After Start over, can the book be put back on the saved run's pending list for a run that will be resumed or that is running, and for a run still before the end of research? If not for a Running run in its last phase, report; `visit` next run applies. For release the book is already on the deferred list; only its Held record must be reset.
- (o) Is `pass` returned from the same call, and does a refused start never undo the set-aside?
- (p) The marker's storage, the `restarted` filter, the global counts, and the sort.
- (q) The release rules in section 7, including the lease check and compare-and-set.
- (r) After a revision change, is the old `candidate_context` row still readable, so the server can say whether the saved review came from Sergei (`metadata_actor`, `track_actor`)? If yes: `release.hand_edits` and the confirm refinement in 4.4.
- (s) The marker follows the pass within one poll; the quiet-state reuse (300 s) must not hold a marker row while the pass runs.
- (t) The narrow table: the second line in the title cell, the explicit roles, and the container query.
- (u) The `file_problem` one-time conversion (section 6).

Offers (not done; Sergei decides):
- O12. ANSWERED (Sergei 2026-10-19: yes; Follow-up 4, section 1). Was: Start over remembers its intent and starts the pass when a block clears (conversion finished), instead of leaving the press to Sergei. Today the row says what to press.
- O13. ANSWERED (Sergei 2026-10-19: yes; Follow-up 4, section 3). Was: for a stuck row whose prediction is `manual_draft`, one button "Start over and let the app handle it": one confirmation, then the set-aside, the release and the start together. Today it is two presses, a wait for the pass, and a confirmation, for an outcome known before the first press.
- O14. ANSWERED (Sergei 2026-10-19: yes; Follow-up 4, section 4). Was: a bulk "Let the app handle all {r}" in the Started over summary line, one confirmation for all, if many books sit in the saved-review hold. Disk and time cost on the real library is the likely reason.
- O11 (whole-filter Clear working files) is unchanged and still open.

Process: appended to this file, uncommitted; Sully commits it before Ender is briefed. Doc-only: no code, git or app launch. Design basis: NN/g visibility of system status, error prevention, user control and freedom, plain-language recovery, recognition over recall; Hick (one honest state per row, one filter, no dead controls); Jakob (native dialog and buttons, title tooltips, the recovery-dialog pattern); Fitts (the action first, the row's buttons together); WCAG 2.2 AA 1.4.3, 1.4.10 (reflow), 2.4.7, 3.3.1, 4.1.3.


---

## Follow-up 4 — 2026-10-19: the pass starts by itself, "Start over and let the app handle it", and bulk "Let the app handle selected"

Judy, UX spec for Ender. Build `de3e2b2`, branch `codex/books-electron-m1`. Scope: Sergei's approval of O12, O13 and O14 (2026-10-19). Everything above stays in force unless this section overrides it; what it makes false is marked SUPERSEDED in place (Follow-up 2: the `manual_draft` hint row of section 1.2; Follow-up 3: the O9 row of section 0, section 1.1 item 1, the `blocked` rows of sections 1.3 and 4.5, the "start blocked" row, the two `expect` rows and the summary tail of section 2, section 4.1's closing sentence, the "Conversion Running" check of section 8, the first reported item and offers O12, O13, O14 of section 9). Basis: read-only look at `automatic_processing.py` (`_start_block_reason`, `start`, `_work`), `web/app.js` (`renderAutomaticEligibility`, `renderRetrySelected`, `batchCounts`, the Retry selected confirm), `web/index.html` (`#automatic-controls`, `#batch-controls`), `desktop/main.js` (every window `show()` and `focus()` call). Nothing launched; no rects measured. Contrast uses tokens already used and no new colour.

### 1. O12: the pass starts by itself when its blocker clears

#### 1.1 What the code does that the answer does not say

1. `_start_block_reason` has three kinds of blocker that clear by themselves: **conversion** (jobs Running or Pausing; clears at Idle, Paused, Completed or Needs attention, so pausing the jobs clears it too), **scan** (a library scan is running; clears when it ends or is stopped) and **stopping** (the run is Stopping; clears at Paused). Three do not: the server is stopping or closed, a failure record could not be saved, and an unknown state. Only the first three get a pending start.
2. **A start after a pause resumes queued jobs.** `start()` runs `_work`, which resumes saved queued conversions before it does anything else. So when pausing the jobs is what clears the blocker, the automatic start restarts them, exactly as the Start button does. The notice says so (1.4).
3. **Focus.** In `desktop/main.js` the only `show()` and `focus()` calls are at launch and for a second instance or the tray. Nothing reacts to a status change, and the start must not reach them.

#### 1.2 The rule, and the notes after a press

- **Who asks.** Start over, Start over and let the app handle it (section 3), Let the app handle it and Let the app handle selected (section 4): each, when the start is blocked by a conversion, scan or stop, leaves one pending start. One for the whole app, not one per book.
- **When it fires.** Within 15 seconds of the blocker clearing, with exactly what the Start button does. If another blocker has appeared by then it keeps waiting, and the rows and the notice change to the new kind. No second press, no confirmation.
- **When it ends.** It starts the pass; or Sergei presses Cancel automatic start (1.4); or the blocker becomes one that cannot clear (the Follow-up 3 refusal text then shows). It is held by the server only: it does not survive an app restart, because a start nobody is watching must not come back. After a restart the pass is Paused and the rows read "waiting for you" with the existing "start to continue" wording.
- **The notes.** These replace the `blocked` text of Follow-up 3 sections 1.3 and 4.5 for a blocker that clears; `{Lead}` is "Started over." (Start over), "Review discarded." (Let the app handle it), "Started over. Review discarded." (section 3) or the plural of section 4.4 below. `--muted`: there is nothing for Sergei to do.

| Blocker | Text |
|---|---|
| conversion | {Lead} Audiobook conversion is running, so automatic processing will start by itself when it finishes or is paused. Find it under Status: Started over. |
| scan | {Lead} A library scan is running, so automatic processing will start by itself when the scan ends or is stopped. Find it under Status: Started over. |
| stopping | {Lead} Automatic processing is stopping, so it will start again by itself once it has stopped. Find it under Status: Started over. |
| cannot clear | unchanged from Follow-up 3: "{Lead, with 'but automatic processing did not start'} {server reason}" in `--warning` |

#### 1.3 The row and the summary line while it waits

For a book with a marker in `waiting` and a pending start. It replaces the "waiting for you" rows for these three blockers (the cannot-clear row and the Cancel result keep the Follow-up 3 text).

| Pending kind | Status | Hint | Colour |
|---|---|---|---|
| conversion | Started over — waiting to start | Nothing to do. Automatic processing starts by itself when audiobook conversion finishes or is paused, then takes this book. | `--muted` |
| scan | Started over — waiting to start | Nothing to do. Automatic processing starts by itself when the library scan ends or is stopped, then takes this book. | `--muted` |
| stopping | Started over — waiting to start | Nothing to do. Automatic processing starts again by itself once it has stopped, then takes this book. | `--muted` |

A book with `expect` hold reads "…then holds this book because it has a saved review." in place of "…then takes this book." (and the section 2 rule for the last clause). The status is 31 characters. When the pass starts the row moves to "Started over — waiting its turn" on the next poll, in place, with no announcement and no focus move.

Summary line (Follow-up 3, section 2.3): while a start is pending the tail is "Nothing for you to do. Automatic processing starts by itself when {audiobook conversion finishes or is paused | the library scan ends or is stopped | it has stopped}." It replaces "Press Start automatic processing above." and the blocked tail.

#### 1.4 The notice and the Cancel control (user control)

- **Notice.** The existing line under the Start button (`#automatic-start-reason`, polite live region) shows, in place of the block reason: conversion: "Automatic processing will start by itself when audiobook conversion finishes or is paused. Starting also resumes any queued audiobook jobs." / scan: "Automatic processing will start by itself when the library scan ends or is stopped." / stopping: "Automatic processing will start again by itself once it has stopped." The Start button stays disabled (it cannot succeed yet) and its tooltip carries the same sentence.
- **Cancel automatic start.** One new `quiet` button in `#automatic-controls`, after Stop automatic processing, min 96 x 32, shown only while a start is pending (hidden at zero, as Original changed). Tooltip: "Don't start automatic processing by itself. Books you started over keep waiting. Press Start automatic processing when you want it to run." Accessible name is its label. It exists because a start that resumes conversions after Sergei paused them for some other reason needs a visible way out. Press: the pending start ends; the notice returns to the block reason; the rows read "waiting for you" with the Follow-up 3 blocked hint; focus moves to the notice (`tabindex=-1`, `preventScroll`), because every other button in the toolbar is disabled. No toast.

#### 1.5 The window never steals focus

When the pending start fires: no window activation of any kind (no `show`, `focus`, `moveTop`, taskbar flash or tray balloon), no OS notification, no sound, no dialog, no toast, no page navigation. A window hidden to the tray stays hidden and the pass still starts. The page changes text in place only: the top line "Automatic processing: Running", the notice and Cancel leaving, the row and summary hints. The one allowed focus movement is the rule above for a Cancel button that was focused when it left.

### 2. Correction to the `expect` rows of Follow-up 3, section 2.2

They said "Then Let the app handle it appears here." for any book expected to be held. That is false for a multi-file book or one with an editor open, which never gets the button (4.2). The server sends `restart.release_expected` (single `.m4b`, saved review, no lease). The last sentence ("Then Let the app handle it appears here.", "and Let the app handle it appears here.") is shown only when it is true; otherwise the hint ends at "…because it has a saved review."

### 3. O13: "Start over and let the app handle it"

#### 3.1 When it replaces the separate buttons

On a `source_changed` row where the server says both `attention.startover` is `manual_draft` (the book is already known to be held for its saved review) and `attention.release_ok` is true (exactly one included `.m4b`, a saved review, no editing lease now). The combined button takes the Start over slot, in the row and in the panel. It never sits beside Start over, and "Let the app handle it" does not appear on that row (the book has no hold yet). Every other stuck row is unchanged: `automatic` prediction, or `manual_draft` that is not `release_ok`, keeps plain Start over with the Follow-up 3 section 1.2 tooltip.

What Sergei gives up on these rows: setting the job aside while keeping the saved review. That choice leads to a book held by its review with nothing in the app able to process it, and "Let the app handle it" remains for books that arrive at the hold another way. If Sergei wants the choice, keep a plain Start over beside the combined button; say so.

#### 3.2 The button

| Item | Spec |
|---|---|
| Label | Start over and let the app handle it |
| Accessible name | Start over and let the app handle it: {title} |
| Hint on the row (after the "Retry was refused: " prefix; replaces the `manual_draft` hint) | the book's review or source files changed. One press sets this job aside, discards its saved review, and sends the book to automatic processing. (`--warning`) |
| Tooltip | Set this failed job aside, discard this book's saved review (including any edits you made by hand), and let automatic processing take the book. Starts automatic processing if it isn't running. This can't be undone. The failed job and your audio files are kept. |
| Style, size, placement | `quiet`, min 96 x 32; the label wraps to two lines in a narrow Actions cell, never truncated; Retry and Start over slot, first; no other control moves. |
| While pressed | Face "Starting over…", `aria-disabled`, keeps focus. Note "Setting this job aside and discarding the saved review…". |

#### 3.3 Confirmation (one, hand edits discarded)

Same modal `<dialog>` pattern as Follow-up 3, section 4.4, one dialog for both effects.

| Item | Text |
|---|---|
| Title | Start over and discard this book's saved review? |
| Book line | {title clue} |
| Body 1 | This sets the failed job aside, then deletes the metadata, cover and track choices saved on this book, including any you made by hand. The deleted review can't be restored. |
| Body 2 | Automatic processing then researches the book again and queues it if the match is safe. It starts if it isn't running. The failed job and your audio files are kept. |
| Buttons | [Cancel] (default focus) and [Discard review and start over] |
| Cancel tooltip | Keep everything as it is. |
| Confirm tooltip | Set the failed job aside, delete this book's saved review and let automatic processing take the book. This can't be undone. |

#### 3.4 After the press

All or nothing: the server does both steps in one transaction. If the review cannot be discarded the job is not set aside, and the note says "Start over was not accepted. Nothing was changed." (outdated view: the existing "This book's status changed. Check the updated status above."; editor open: "This book is being edited. Finish editing, then try again."). Success note: "Started over. Review discarded." then the pass sentence of Follow-up 3 section 1.3 (or the O12 text of section 1.2 above), then " Find it under Status: Started over." The row is held in place and reads "Started over — waiting its turn" (or "waiting to start" or "waiting for you"), never "Held", with no `expect`. Focus: first remaining button, `preventScroll`. If Ender cannot make it atomic (open item x): the fallback note after a set-aside that could not discard is "Started over, but the review wasn't discarded. Let the app handle it can discard it once the book is held."

### 4. O14: "Let the app handle selected"

#### 4.1 Where it lives

In the batch bar (`#batch-controls`), in the slot Retry selected uses, after Queue selected books. Retry selected itself is shown only in Output needs attention, where no held book ever appears, so "next to it" would never be seen. The new button is shown only in the **Held** and **Started over** filters and hidden everywhere else. Selection is unchanged (the checkbox and Select this page).

#### 4.2 The count text, the button and what is skipped

| Item | Spec |
|---|---|
| Count line (`#batch-count`), Started over filter | {n} selected · {k} can be handled by the app · {x} left out ("· {x} left out" only when x is above 0) |
| Count line, Held filter | the existing line, plus " · {k} can be handled by the app" only when k is above 0 |
| Help line (`#batch-help`) | Only selected books held for a saved review can be handed to the app. The others stay as they are. |
| Button | Let the app handle selected ({k}); `quiet`, min 96 x 32; disabled (`aria-disabled`) when k is 0, while a run is in progress, busy, ended or disconnected |
| Tooltip, k above 0 | Discard the saved reviews of these {k} selected books, including any edits you made by hand, and let automatic processing take them. Starts automatic processing if it isn't running. This can't be undone. |
| Tooltip, k is 0 | Select books held for a saved review. |

k counts the selected, listed rows whose `release.allowed` is true. **Skipped, and why:** a book the pass has not yet held (waiting, researching, failed, queued, held for another reason: there is no saved-review hold to release); a multi-file book (it can be queued by hand); a book with an editing lease (Sergei is in it); a book with a job. Skipped books stay selected and unchanged and are counted in "left out". The server re-checks every book when it runs, so one that changed meanwhile is refused alone.

#### 4.3 One confirmation, with the count

A modal `<dialog>` of the same pattern (not the inline confirm Retry selected uses: that one does not delete anything). For k of 1 the single dialog of Follow-up 3, section 4.4 is used.

| Item | Text |
|---|---|
| Title | Discard {k} saved reviews? |
| Body 1 | This deletes the metadata, cover and track choices saved on these {k} books, including any you made by hand. It can't be undone. |
| Body 2 | Automatic processing then researches each book again and queues it if the match is safe. It starts if it isn't running. Your audio files are not touched. |
| Body 3 (only when x is above 0) | {x} other selected books are not included. They stay selected and unchanged. |
| Buttons | [Cancel] (default focus) and [Discard {k} reviews] |
| Cancel tooltip | Keep the saved reviews and leave these books held. |
| Confirm tooltip | Delete the saved reviews of these {k} books, then let automatic processing take them. This can't be undone. |

The dialog lists the count, not the titles (the selection is on screen).

#### 4.4 While it runs and after

- **Running.** The button face is "Discarding…"; the progress "{done} of {k}" sits beside it, outside the live region, as Retry all does. Controls that Retry selected blocks while it runs stay blocked.
- **Result** (the status span after the buttons, `tabindex=-1`, focus moves there with `preventScroll`, polite): "Discarded {r} of {k} saved reviews. {pass sentence} Find them under Status: Started over." plus " {f} were not changed. Check their status." when f is above 0. Pass sentence, plural: started "Automatic processing has started. It scans the library first, so this may take a while." / continued "Automatic processing continued where it paused." / running "Automatic processing is running and will reach these books." / running, next run "Automatic processing is running but has already passed these books. Press Start automatic processing above after it finishes." / pending (section 1.2) "Automatic processing will start by itself when {audiobook conversion finishes or is paused | the library scan ends or is stopped | it has stopped}." / cannot clear "Automatic processing did not start. {server reason}". `--muted`, except `--warning` when f is above 0 or the pass sentence is a next-run or cannot-clear one.
- **The list.** No hold in place (Sergei pressed no single row; as the bulk runs of Follow-up 1, point 3a). The books leave Held and join Started over as the list changes; counts are conserved (Held falls by r, Started over rises by r). Ticks stay on rows still listed.

### 5. What the UI needs from the API (names assumed; Ender confirms)

- `automatic_processing.start_block`: `{kind:'conversion'|'scan'|'stopping'|'closing'|'failure'|'unknown', clears:bool}` or null; `automatic_processing.start_pending`: `{kind}` or absent.
- `pass.action` gains `'pending'` with `pass.pending_kind`; `'blocked'` stays only for a blocker that cannot clear. `POST /api/automatic/cancel-start` answers a fresh `automatic_processing`.
- `attention.release_ok` (stuck rows), `restart.release_expected` (waiting rows).
- `POST /api/audiobook/startover` accepts `discard_review:true`, refused unless `release_ok`, one transaction, same answer plus `released:true`.
- Bulk: either `POST /api/audiobook/release-selected` `{library, items:[{id, revision}]}` answering `{released, refused:[{id, cause}], pass, automatic_processing}`, or one `release` call per book as Retry selected loops; Ender's choice. The pass is started once, after the last book is reset, if it is one call.

### 6. Acceptance checks for Futaba (committed build; seeded records and folders, no real library)

O12:
- Conversion Running: press Start over. The note is the conversion text exactly; the row reads "Started over — waiting to start" with its hint; the notice and Cancel automatic start are visible with their tooltip; Start stays disabled. Pause the jobs: within 15 s the pass is Running with no press, the notice and Cancel are gone, queued jobs resumed, the row reads "waiting its turn". The same when the jobs finish instead. Same with a scan (Start scanning) and with a Stopping run.
- Cancel: the notice returns to the block reason, rows read "waiting for you" with the Follow-up 3 hint, focus is on the notice, and the pass does not start when the blocker clears.
- A blocker that cannot clear (server closing, failure record unsaved): no pending start; the Follow-up 3 refusal text, warning colour.
- A second press while pending leaves one pending start. An app restart with a pending start: no start after restart; rows read "waiting for you". A new blocker when the first clears: it keeps waiting and the hint changes kind.
- No focus: the foreground log shows no event at the moment of the start, `document.hasFocus()` is unchanged, a tray-hidden window stays hidden and the pass still starts, no sound, no notification, no dialog, no toast.

O13:
- A seeded stuck single-M4B row predicted `manual_draft`, no lease: the combined button replaces Start over (no plain Start over beside it), in the row and in the panel; hint and tooltip exact. A multi-file row, an editing lease, and an `automatic` prediction each keep plain Start over.
- Press: the dialog opens and nothing else happens; Cancel has focus; Esc closes with no change. Confirm: the job is set aside (old row and journal kept) and the review and context are gone in one transaction (force the discard to fail: the job is still attached, nothing changed, the "Nothing was changed" text); the note leads "Started over. Review discarded."; the row reads a Started over state, never "Held", with no `expect` hint; audio files unchanged (hash).

O14:
- Held filter, 5 selected (3 releasable, 1 multi-file, 1 with a lease): the count line is the existing line plus " · 3 can be handled by the app"; the button reads "Let the app handle selected (3)". Started over filter with the same mix: "5 selected · 3 can be handled by the app · 2 left out". k of 0: the button is disabled with its tooltip. Hidden in every other filter.
- Press: the dialog shows 3 and the "2 other selected books are not included" sentence; Cancel has focus; confirm runs with "Discarding…" and "x of 3"; the result line is exact; the 3 joined Started over, the 2 are unchanged and still selected; focus is on the result; Held fell by 3 and Started over rose by 3.
- One of the 3 changed (its revision bumped) after the dialog opened: refused alone, the result reads "Discarded 2 of 3 … 1 were not changed."
- With the pass blocked by a conversion: the pending text of section 4.4.
- Rects at 1440, 950, 700 and 475: the batch bar wraps, nothing overlaps, buttons at least 96 x 32; the dialogs fit at 475 and at 200% zoom.
- Contrast (calculated, same tokens): `--warning` text on `--surface` 11.18, `--row-hover` 8.31, `--row-selected` 6.23; `--muted` 8.92, 6.63, 4.97. Every state is also stated in words.

### 7. Open items and offers

Open for Ender, new (report back; none blocks the copy):
- (v) The pending start: kind typing, the 15 s bound, one intent for the app, in-memory only, and no window or notification call on firing.
- (w) That the start after a pause resumes queued jobs exactly as the Start button does (the notice states it); if it does not, the clause goes.
- (x) Is the combined press one transaction? If not, report; the fallback note is in 3.4.
- (y) The bulk as one call or a loop, and the per-book compare-and-set.
- (z) `release_ok`, `release_expected`, `start_block` and `start_pending` as named.

Still open from Follow-up 3 and earlier: (n) putting a Start-over book back on the run's pending list, (o) the `pass` answer, (p) the marker storage, filter and counts, (q) the release rules, (r) whether the old context row can tell the app wrote the review, (s) marker follows the pass within one poll, (t) the narrow table, (u) the `file_problem` one-time conversion; and from Follow-up 2 (g) to (m).

Offers (not done; Sergei decides):
- O5. Start over selected, for many stuck rows. With O13 a stuck row predicted to hold costs one press and one confirmation each; O5 would make a whole batch one press. Still open.
- O11 (whole-filter Clear working files) is unchanged and still open.

Question for Sergei: keep a plain Start over beside the combined button on those rows (3.1), or only the combined button? The spec ships only the combined button.

Process: appended to this file, uncommitted; Sully commits it before Ender is briefed. Doc-only: no code, git or app launch. Design basis: NN/g visibility of system status, user control and freedom (Cancel), error prevention (one confirmation for an irreversible discard), plain-language recovery; Hick (one combined button, no duplicates); Jakob (native dialog, title tooltips, hide-at-zero control); Fitts (the action stays in the first slot); WCAG 2.2 AA 1.4.3, 2.4.7, 3.3.1, 4.1.3 and the studio rule that our tooling never steals focus.
