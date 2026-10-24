# Code Review findings — Books Arranger 0.22.0, early pass (no verdict)

**Not a release clearance.** This is an early red-team pass while Ender finishes the last 0.22.0 feature (M4B part joining, ruling 19a). The final review of the full 0.22.0 diff carries the verdict line. This file has none, and the release gate must not read it as one.

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-24
Tool: Books Arranger
Release: 0.22.0 (in progress; package.json still says 0.21.3)
Commit range: origin/main d0e6962 .. origin/ender/0220 bc3362d (24 commits)
Files changed: 60 files, +4947 / -223 (git diff --stat)
  Product code: local_identity.py +765, merge_service.py +392, author_rules.py +294 (new), todo_causes.py +149 (new),
  groups.py +102, public_research.py +87, review_backend.py +65, source_cleanup.py +42, source_config.py +31,
  scanner.py +30, web_server.py +32, source_identity.py +29, automatic_processing.py +29, smaller edits in 6 more.
  Frontend: web/app.js +507, index.html +17, style.css +36. Tests: 34 files. Gate scripts: 2 files.
Not covered: M4B part joining (ruling 19a), still in progress on b0220.
Stand-down dimensions: none
```

Rulings checked against: `Team/Docs/BooksArranger_Rulings_2026-10-24.md` (2, 1a, 5, 6, 6a, 6b, 10, 11a, 12, 13-15, 18-20) and `Team/Docs/BooksArranger_AuthorRulings_2026-10-24.md`. UI spec: `Docs/BooksArranger_AttentionTodo_UX_2026-10-24.md`.

---

## Summary

The safety floor holds. Every delete in this range still happens only after a verified result is in Sorted, and Approve keeps the no-overwrite check, media verification and the Sorted-only cleanup. The weak point is the **grouping**: three new ways to put two different books into one group. When that group's numbering looks clean, it converts on its own, and both books' originals are removed. No audio is lost, because both books are inside the one output. But two books end up as one file under a wrong name, and their originals are gone (recovery copies are purged as soon as the output is verified, `recovery_retention.HOURS=0`). I graded these Major because no audio is lost and the skill says to default to Major when unsure. They are the closest findings to the Critical line, and I recommend fixing them before 0.22.0 ships.

**Answers to the eight questions.**

1. **Can identity v5 misidentify, convert and then delete?** Yes, through grouping (G1, G2, G3) and one guard-1 hole (G4). Probe A ran end to end: it converted on its own and its four originals were removed. In the other probes research raised no hold, so an automatic run approves them the same way. The deletion rule holds literally, because the audio is in Sorted, but the books were not correctly done. A reader filed as the author: guard 1 works for readers the library already knows, and for brackets and "читает". An "Author - Reader" tag with an unknown reader is filed whole as the author (G4).
2. **Approve as is.** It overrides only identity and confidence holds. Kept: unreadable or changed files, the encoding decision, an existing job, never overwriting (a taken name refuses, tested), media verification, and removal only after the result is verified in Sorted (tested end to end with a separate Sorted folder). It uses the saved order and files: my probe compared the order shown on the row with the converted order, and `test_todo_holds` covers a saved order. Two gaps. Approve does not check that the identity it computes at press time is the one the row showed (m1). A typed author skips Sergei's same_as rules (m2).
3. **author_rules.** Append-only by triggers, and the seeds are content-keyed. The answers are applied in `identify()`, but not to typed or entered values (m2). A wrongly seeded rule can never be removed, only overridden (m6). I found no seed that maps one author onto a different person. The library-wide reader seeds include common names (for example "Андрей Кузнецов"); a real author with such a name is held as a question, not misfiled.
4. **Stuck without a row?** Yes, two ways. A book refused at the approval step is held on a backoff timer, counted as "Still checking" and never listed (G5). Any new author rule moves every listed row to "Still checking" until a full automatic pass re-researches all held books (G6).
5. **Can two different books be joined?** Yes (G3): two books of one series in one folder, with the same album and author, different readers, and disc numbers giving each book its own disc. The two other new joins (G1, G2) do the same.
6. **Book-list speed.** No wrong action. The 30 s caches (`converted_ids`, `cleanup_statuses`) and the lock-free page feed only the display (`audiobook_ready`, the converted filter, `stale_attention`). Every action re-reads its row at its revision, and the to-do list's `with_job` comes from the database each time. The lock-free page reads one consistent WAL snapshot.
7. **Four workers.** Every pattern still runs exactly once (96 patterns, 96 unique placements, all reports required complete; checked with the gate's own `pythonBatches`). The projection check is a proxy (m5): it projects about 385 s per worker, while my concurrent run took 493–569 s per worker. The deadline still fails closed.
8. **F1–F8.** All fixed (table below). The F1 and F8 tests catch their mutants.

---

## Rubric

### 1. Security

- Status: Pass
- Findings: none.
  - The four new routes (`approve`, `approve-preview`, `scan-again`, `dismiss`) go through `shape()`, take one-line text of at most 1000 characters, and accept a boolean only for `without_missing` and only same or different for `choice`. `scan-again` uses the existing scan guards.
  - The rule a Same author? answer writes comes from the stored research record, not from the request.
  - The frontend diff adds no `innerHTML` or other HTML sinks. Nothing new shells out, and no secrets are in the diff.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - **G1 [Major]** `groups.py:265`. **Guard 2's own exception fails: an author folder of "NN Author - Title" files is joined into one book.**
    - What happens: `looks_like_person(parsed['author'])` is called without the catalog index, so a surname alone ("Сапковский") or a first name missing from `GIVEN_NAMES` is not a person.
    - Probe: `01 Сапковский - Последнее желание.mp3` and `02 Сапковский - Меч предназначения.mp3`, no album and no track tags.
    - Result: one group titled **"Сапковский"**, with no hold. It would be filed as `Сапковский Анджей\Сапковский - Сапковский Анджей.m4b`.
    - The Brief says this case "stays separate books".
    - Live catalog (read-only, files that are still a book of their own): 3 such numbered sets, none whose file names and title tags name different books, so there is no live hit today.
    - **Fix:** pass the catalog index to `looks_like_person` here, and never join a set whose members' file-name titles name different books.
  - **G2 [Major]** `groups.py:259`, `local_identity.py:1680,1685`. **A junk title tag joins different books and becomes their title.**
    - What happens: `_same_title_sets` keys on any title tag, including `JUNK_TITLES`, and `identify()` takes the set name without the junk check it applies to tags (`:1661`).
    - Probe: `Кинг - Оно.mp3` and `Кинг - Мизери.mp3`, both tagged title "Аудиокнига", artist "Стивен Кинг", tracks 1 and 2.
    - Result: one book, "Аудиокнига", with no hold. It converts on its own.
    - Live catalog (read-only): 5 sets, 20 files, each file still a book of its own and tagged "Без имени", in Сборник folders. They would be joined into five books, each titled "Без имени".
    - **Fix:** skip junk and garbled title keys in `_same_title_sets`, and run the `JUNK_TITLES` check on the set name in `identify()`.
  - **G3 [Major]** `groups.py:283-308`, `source_identity.py:114-129`. **The same-album join merges different books of one series read by different people.**
    - Probe: one folder, album "Ведьмак", artist "Анджей Сапковский", album artist a different reader per book, disc 1 or 2 per book, tracks 1-2 on each.
    - Result: one group, research gave no reasons, and it converted into `Сапковский Анджей\Ведьмак - Сапковский Анджей.m4b`. The cleanup completed and **all four originals were removed**.
    - Why nothing held it: the one-source gate checks album and artist only, never the members' own title tags (here "Последнее желание N" against "Меч предназначения N").
    - Before this range, the different album artists put the two books in separate groups.
    - **Fix:** don't join, or hold it as Files unclear, when the members' title tags (part numbers removed) name two or more different works.
  - **G4 [Major]** `local_identity.py:1572-1576`. **An "Author - Reader" tag is filed whole as the author when the reader is not already known (ruling 14).**
    - What happens: `_clean_credit` splits on the dash only when exactly one piece is a known reader. Otherwise it keeps "A - B", and v5 accepts that one source.
    - Probe: artist "Александр Варго - Иван Сидоров". Result: author "Александр Варго - Иван Сидоров", accepted, no question.
    - v4 held this, because no second source agreed. The Brief's guard 1 row claims this exact case.
    - **Fix:** when a dash splits a tag credit into two names that both look like people, ask (`author_unclear`, `two_people`) instead of keeping the whole string.
  - **G5 [Major]** `automatic_processing.py:691`, `merge_service.py:2012`. **A book refused at the approval step is never listed (rulings 10 and 5).**
    - What happens: an admission refusal (a `ValueError` from `approve_automatic`) is recorded Held with a backoff `retry_at` and no `until_change`. `_todo()` counts it as "Still checking", and it is researched again on a backoff timer (15 min, doubling up to a day), hitting the same refusal each time.
    - Probe through a real automatic run: a 260-character title gave 'Verified metadata exceeds the supported Windows output path length'. Result: Held, `until_change` False, listed 0, `still_checking` 1.
    - Other refusals that only happen at approval and are not "name taken" or "Manual draft retained" (cover not verified, the recording review) take the same path.
    - **Fix:** in `_todo()`, list an exact Held record with reasons under Other whether or not it has `until_change`. Or record admission refusals with `until_change`.
  - **G6 [Major]** `merge_service.py:1979,2012`, `author_rules.py:97`. **One new author rule removes every row from the to-do list.**
    - What happens: `rules_generation` is global, so any new rule (a single Same author? answer) makes every held record "not settled".
    - Probe: 3 listed rows. After one unrelated `keep` rule: 0 listed and 3 still checking, and the page total is 0.
    - The rows come back only after a full automatic pass re-researches every held book. With automatic processing stopped, the list stays empty, with only the "waiting to be checked" line.
    - **Fix:** keep listing rows whose recorded generation is older, marked as being checked again, and re-research only the books whose credits match the new rule's key.
  - **m1 [Minor]** `merge_service.py:2189-2218`, `public_research.py:462-475`. **Approve recomputes identity and rules at press time, without checking against what the row showed.**
    - A rule saved meanwhile, or the bulk dialog's list, can file the book somewhere other than the Goes to line said. The Brief says "the path shown is the path used".
    - **Fix:** send the previewed relative path with the press and refuse on a mismatch.
  - **m2 [Minor]** `local_identity.py:2037` (`settled`), `public_research.py:475`. **A typed or entered author skips Sergei's same_as rules.**
    - Probe: typed "Терри Пратчетт" goes to `Пратчетт Терри\…`, while the same name from a tag goes to `Pratchett Terry\…`. This makes the duplicate folders ruling 12 merges.
    - **Fix:** apply `rules.same_as()` to typed and entered authors.
  - **m3 [Minor]** `merge_service.py:2198`. A Same author? choice is passed as `author`, so it is saved as typed ("Entered by you"). That is the wrong provenance. **Fix:** pass it as a choice, not as a typed value.

### 3. Crash / Stability Safety

- Status: Concerns
- Findings:
  - **m4 [Minor]** `merge_service.py:2218`, `web_server.py:180`, `web/app.js:972`. **Approve runs the whole admission inside the HTTP press, with a stop event that is never set.** That admission is a SHA-256 of every file, the recording review and the cover checks.
    - A large book on the NAS takes longer than the 15 s press timeout. The row then says "Connection interrupted" while the job is still being created.
    - Shutdown waits for `merge_admissions`, so Quit waits behind it and cannot cut it short.
    - **Fix:** pass a stop event that closing and draining set, or hand the approval to the worker and answer at once.

### 4. Performance

- Status: Pass
- Findings: none.
  - One uncached `_todo()` on the live catalog (read-only, 3 runs) took 0.33-0.36 s: 1,938 groups and 2,950 research records (31.5 MB of JSON). The `author_rules` manifest read took 0.07 s. It is recomputed on each status poll during a run, which is acceptable.
  - Not measured: the to-do page runs `approval_preview` (identify and the local lookup) for every shown row. Please time a page of 100 rows on a live copy.

### 5. State & Data Safety

- Status: Concerns
- Findings:
  - G1, G2 and G3 are the data-safety side of the grouping findings: a wrong group converts and its originals are removed.
  - **The safety floor is intact.**
    - No new delete path. `dismiss_attention` writes only a table row.
    - `Без автора` paths go through `safe_name` and the 240-character limit.
    - A taken name refuses, both at publication (`audio_pipeline.py:1098`, `merge_service.py:3116`) and through Approve (tested).
    - Cleanup still removes only the manifest's sources, and the manifest holds only the included files (`build_manifest`). Convert what's there and Choose files never remove a file that was left out.

### 6. Input Handling

- Status: Pass
- Findings: none. Typed values are bounded (1000 characters, one line), and an empty title refuses ("Type a title first.").

### 7. Maintainability (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **m6 [Minor]** `author_rules.py:51-62`. A seed removed from `SEEDS` stays in the table forever, and there is no kind that cancels a rule. A wrong seed can only be overridden by a contrary rule (`keep` over `not_author`). **Fix:** add a `retract` kind.
  - **m7 [Minor]** `scripts/check-desktop.mjs`. 25 test modules are outside the gate.
    - 8 of them fail identically at d0e6962 and bc3362d: 28 cases, run both ways, nothing new. For example, `test_start_over` fails 11 cases because its fixtures have had no output folder since 0.21.3.
    - `test_split_books` and `test_collection_identity` changed in this range and pass, but are not gated.
    - **Fix:** gate those two, and fix or retire the suites that are rotting.
  - **m9 [Minor]** `merge_service.py:2299`. Approve's second safety filter, inside `approve_automatic`, has no test of its own. The mutant that drops every source-gate reason there survives, because `approve_book`'s earlier check (`:2205`) refuses first in every test. The filter is the only guard when a file becomes unreadable between that check and the gate. **Fix:** add one test that calls `approve_automatic` with `approved_by` on a row whose member is unreadable, and assert the refusal.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **m8 [Minor]** `Docs/BooksArranger_Brief.md`, 0.22.0 rows. Three claims do not hold:
    - Guard 2's "NN Author - Title stays separate books" (G1).
    - Guard 1's dash-joined reader (G4).
    - Ruling 6b's "the path shown is the path used" (m1).

### 9. Build & Release Hygiene

- Status: Concerns
- Findings:
  - **m5 [Minor]** `scripts/python-check-batches.mjs:20-21`, `tests/python-check-batches.test.mjs:35`. **The 80 % projection uses module times measured alone.**
    - My concurrent run took 493 / 499 / 538 / 569 s for the four gate workers. That was system Python and a fifth worker running alongside, so it is not like-for-like. The projection says 384-386 s, and one worker passed 540 s.
    - Placement and completeness are right, and the deadline fails closed.
    - **Fix:** print each worker's real seconds in the gate output, and record one real four-worker gate time on the pinned runtime in the Brief.
  - Not yet (expected for an early pass):
    - No version bump and no 0.22.0 CHANGELOG entry.
    - The CHANGELOG still presents the cancelled v0.21.3 as a release.
    - No commit in the range carries a Claude attribution trailer.

---

## F1–F8 (0.21.3 findings, fixed in 4d89eb1)

| # | Status | Evidence |
| --- | --- | --- |
| F1 | Fixed | `CONFIGURATION_REFUSALS` are retried in `_work`; startup enrolment parks nothing for them. The mutant that drops the retry fails `test_source_cleanup`. Nothing can change the output folder while the app runs (`scanner.py:108` is the only writer), so the next start enrols the book. |
| F2 | Fixed | `_sorted` and `_output_present` run before the intent commit and again inside it; tested. |
| F3 | Fixed | An `OSError` from `realpath` reads as UNAVAILABLE in both `sorted_problem` and `require_sorted`; tested. |
| F4 | Fixed | `_stale_markers` puts back a killed run's markers at every run start; tested. |
| F5 | Fixed | `published_root` names books relative to the output root; series backfill is on in Sorted (ruling 17). |
| F6 | Fixed | `test_sorted_wiring.py` uses the real `output_policy` with a separate Sorted folder; it is in the gate. |
| F7 | Fixed | The CHANGELOG wording is corrected. |
| F8 | Fixed | The mutant that offers the in-place session outside Sorted fails `…destination_outside_the_sorted_folder…`. |

---

## Tests run

All runs were on a detached worktree of bc3362d at `C:/Antigravity Projects/Worktrees/Books Arranger/review-0220`, never in `WIP/` or in b0220. Runtime: system Python 3.14.9 and WinGet FFmpeg 8.1.1. The gate's pinned runtime is not on this machine.

| Run | Result |
| --- | --- |
| The 96 gate modules, with the gate's own batch code, partition and fixture map, 4 workers | 1462 run, 0 failures, 0 errors, 1 skipped. The skip is `ActualPrivateStagingTests`, which is opt-in. |
| The 25 ungated modules (fifth worker) | 339 run: 14 failures and 14 errors in 8 modules. The same 28 fail at d0e6962, which I ran too (m7). |
| `node --test`, the 10 gate node suites | 63 pass |
| `tests/test_*.js`, 20 frontend scripts | 20 pass |
| Probes A-H (`ApproveFixture`: a separate Sorted folder, the production policy, offline research) | G1 (probe G), G2 (E), G3 (A, end to end with cleanup), G4 (F), G5 (H, a real automatic run), G6 (B), m2 (C). D: the order shown is the order converted. |
| Live catalog, read-only (`mode=ro`) | The G1 and G2 pattern counts, and the `_todo()` and `author_rules.load` cost |

## Mutants

10 mutants, applied one at a time to a copy of bc3362d. The named suites ran, then the file was restored. **9 caught, 1 survived.**

| Mutant | Caught by |
| --- | --- |
| F8: the in-place session is offered outside Sorted | `test_inplace_m4b` (…destination_outside…) |
| F1: configuration refusals are not retried | `test_source_cleanup` |
| Approve ignores the saved order | `test_todo_holds` |
| `shown()` proposes a suspected reader (ruling 14) | `test_attention_list` |
| The until_change skip is off (held books researched every pass) | `test_automatic_processing` / `test_attention_list` / `test_todo_holds` (1 failure) |
| `author_rules` UPDATE allowed (trigger not created) | `test_author_rules` |
| Same-title sets join "NN Person - Title" files | `test_identity_v5` / `test_join_parts` / `test_todo_holds` (1 failure) |
| Same-album parts join several authors | `test_join_parts` / `test_identity_v5` (1 failure) |
| A name credited as a reader on other books may be the author | `test_identity_v5` / `test_attention_list` / `test_author_rules` (4 failures) |
| **The safety filter inside `approve_automatic` keeps no source-gate reason** (`merge_service.py:2299` → `reasons=[]`) | **Survived** `test_approve_as_is`, `test_todo_holds`, `test_sorted_wiring` (18). See m9 |

## Totals (no verdict: early pass)

- Critical: 0
- Major: 6 (G1-G6)
- Minor: 9 (m1-m9)

**For Ender, in this order:** G3, G1 and G2 (grouping), then G4, G5 and G6.

**The final 0.22.0 review** will:
- re-check these findings;
- review M4B part joining (ruling 19a);
- re-grade G1-G3 if the live catalog shows them;
- check the 0.22.0 build manifest.
