# Code Review — Books Arranger v0.16.5

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-10-17
Tool: Books Arranger
Release: v0.16.5
Status: FINAL; lean pass focused on data-loss safety only (style and maintainability skipped by brief)
Commit range: b6cae4c21dc667eaafa27bd74a50504d7de54d13..9e1664ff50522a1afc92790f69f2efcba3240675
Last published release: v0.16.4, tagged at b6cae4c21dc667eaafa27bd74a50504d7de54d13 (its report cleared 95febcdd..b6cae4c)
  669b4d27a04a52af038841b4c9ee15418a3f9e31 Docs only (v0.16.4 review, QA and acceptance records; 3 files, +476)
Delta reviewed here: 669b4d27a04a52af038841b4c9ee15418a3f9e31..9e1664ff50522a1afc92790f69f2efcba3240675 (24 files, +2105 / -27; 22 non-Docs files, +1309 / -27)
  0be0bd01cdc5af21f04705f74f18b2ea39f9a6bc Docs only (approved design)
  18660077e698959e7758ce6e2bbbb2efed931fe8 resume stuck originals cleanups, retry blocked jobs, Retry button
  2f74e73313c389cd81e228a3386eb3618bf98999 version bump to 0.16.5 + CHANGELOG
  9e1664ff50522a1afc92790f69f2efcba3240675 build guard resolves recorded paths inside a moved worktree
Stand-down dimensions: 7 and 8 skipped by brief (data-loss focus)
Release source commit: 9e1664ff50522a1afc92790f69f2efcba3240675
Release artifact manifest SHA256: 1c08d7c10f02af7064a1c6b3b89ddc64d0f8e547c2070e2b2c89eda71f2376a3
Release installer: dist/builds/6b286397-be7e-4d5c-a420-41104061deac/Books-Arranger-Setup-0.16.5.exe
Release installer SHA256: 5bbf9bb91d9e94c6c8cc0b225ac6279e9e4198961e8b4017723e4d8dc820df5b (172,961,175 bytes)
```

What carries forward unchanged: everything cleared in `Docs/BooksArranger_CodeReview_v0.16.4_2026-10-17.md` (`95febcdd..b6cae4c`), with its open Major and Minor findings.

## Release questions (data-loss safety)

The resume path is `run_with_retry()` → `run()`. `run()` itself is unchanged in this delta. What is new is that it is now reached again for cleanups that previously stopped for good: a busy catalog now pauses instead of needing attention, legacy `database is locked` rows become paused at startup, and each run gets up to two automatic re-runs.

1. **Converted output verified first: yes.** Every attempt starts at the top of `run()` (`source_cleanup.py:288`). The output is checked for location and `.m4b` suffix, parent identity, size and full SHA-256, and its handle stays open. The cover hash and the review guard are checked too. All of this happens before any member is touched. `ob.revalidate()` and the guard under `BEGIN IMMEDIATE` run again before each disposal.
2. **Each original fully re-verified before deletion: yes.** For every member that is not already removed, each run re-opens the original with a delete handle. `_match` checks size, timestamp, link count, attributes, stored and reviewed file identity, and the full SHA-256 against the manifest. The recovery copy is fully re-hashed against the same SHA-256 and size. Both pass for every track before the first disposal (`held` list). `single_stream` and the guard are rechecked right before `dispose()`. An existing recovery file is never re-copied over: the copy uses `xb`, and a `backup_pending` member reuses its copy only after full verification.
3. **Idempotent over already-removed tracks: yes.**
   - `removed` and `disposition_set` members get their recovery copy re-hashed, and the original path must be absent; an existing file there is preserved and refused.
   - `removal_intended` with the original absent stops with needs-attention. It does not guess.
   - Every other state goes back through the full verification in point 2.
   - I traced a typed busy error at each catalog write in the removal loop. The worst case is a busy `COMMIT` after `dispose()`. That leaves `removal_intended` with the original gone. The next attempt then stops with a non-busy needs-attention, and the verified recovery copy stays. No path deletes an original without a verified copy.
4. **Recovery retention starts correctly: yes.** `recovery_completion` is written only by `_set(id,'completed')`, with `INSERT OR IGNORE`. `recovery_retention.py:30-37` enrols only `state='completed'` rows, and line 105 refuses if the completion time ever changes.
   - A resumed or legacy-reclassified cleanup starts its clock when it actually completes, never at the time it stalled.
   - A paused or needs-attention cleanup never enters retention.
5. **Legacy reclassification (`source_cleanup.py:95`).** It only changes the database; no file is opened. It requires:
   - the exact SQLite reason text;
   - an intent whose id and job match the row, with a binding and a recovery identity;
   - a `completed` audio job;
   - no restore intent or restore state.

   It uses a compare-and-set and keeps the old reason in `source_cleanup_holds`. Any deletion afterwards goes through the full `run()` above.
6. **Retry eligibility and the compare-and-set.**
   - `_retry_shape` (`audio_jobs.py:340`) accepts only jobs refused at admission: `needs attention`, no output, no publication intent, no recorded failure, a matching manifest hash and job id, no replacement or repair, and the latest job for its book.
   - The book revision must match both the manifest and `book_groups` (E9).
   - `admission_clear` is a read-only pre-check of `admit()` (`working_lifecycle.py:583`). The revision guard re-reads the sources (E10).
   - The compare-and-set (`audio_jobs.py:429`) requires the whole row to be exactly as it was read: state, output, attempt, journal, manifest, hash, reason, stage and `updated`. It only sets `pending`. Nothing on Z: is touched, and the worker's own admission and revision guard run again before any work.
   - Retry is serialised with create, queue and replace by `operation_lock`, and with review edits by `_review_boundary`.
7. **Build guard (`scripts/build_fs_guard.py:337`).**
   - A recorded path is either used as recorded inside the checkout, or mapped by its tail after `build-cache\builds` into this checkout. Nothing outside the checkout is opened. The next check (`relative_to` …, 2 parts, a UUID, `runtime`) bounds it to `<checkout>/build-cache/builds/<uuid>/runtime`.
   - **A copy is refused:** `verify()` compares every runtime and payload file with its native receipt (volume, file id, timestamp, size and SHA-256). The new test `test_copied_checkout_is_refused_by_native_identity` has a positive control.
   - **A swapped build folder is refused:** the producer's `build_id` must equal the manifest and pointer identity, and the producer pins the manifest's and pointer's native receipts.
   - The `owned_root` check now compares recorded against recorded. Both values come from the same build at the same location, so the trust model is unchanged.

**Measured:** `python -m unittest tests.test_cleanup_resume tests.test_blocked_retry tests.test_build_guard` ran 65 tests, all OK, at `9e1664f`. The worktree was clean before and after (bytecode writing disabled).

## Artifact binding (lean, 2026-10-17)

This was read-only. Nothing was installed, launched or extracted.

- `sha256(dist/release-artifacts.json)` = `1c08d7c1…6a3`, equal to the brief.
  - Manifest: version `0.16.5`, `source_head` `9e1664ff50522a1afc92790f69f2efcba3240675`, `build_id` `6b286397-be7e-4d5c-a420-41104061deac`.
- The installer's SHA-256 and size equal its manifest entry and the brief.
- The six changed backend modules in `win-unpacked/resources` equal the `9e1664f` git blobs (`git hash-object --path`): `audio_jobs.py`, `merge_service.py`, `review_backend.py`, `source_cleanup.py`, `web_server.py` and `working_lifecycle.py`.
- `desktop/main.js` is not in the delta.
- **Not redone in this lean pass:** the 7z carve and payload extraction, the product-digest recompute and the ASAR comparison done for v0.16.4.

## Rubric

Severity tags and the always-blocking floor are those in `Team/Docs/ProcessRules.md`, Severity definitions.

### 1. Security
Pass. There is no new shell-out and no Electron change. The new `/api/audiobook/retry` route uses the existing shape, identity and UUID validation, the merge-admission count and the scan refusal.

### 2. Correctness & Logic
Concerns.
- u2 (Minor): see Finding rollup.

### 3. Crash / Stability Safety
Pass. Every failure lands in `hold()`, and an interrupted retry wait pauses. Quit's drain cuts the wait short through `interrupt`.

### 4. Performance
Pass (focus-limited). Retry status is read once per page and does no media reads.

### 5. State & Data Safety
Concerns.
- u1 (Minor): see Finding rollup.
- Release questions 1–6 above all pass.

### 6. Input Handling
Pass. The retry body is shape-checked: the identity goes through `candidate_identity`, and `job_id` through `uuid_value`.

### 7. Maintainability
Skipped by brief.

### 8. Doc/Code Drift
Skipped by brief.

### 9. Build & Release Hygiene
Pass.
- The guard change is safe, per question 7.
- The artifact is bound to `9e1664f` as stated above.
- The version bump and lockfile are in one commit (`2f74e73`).

## Finding rollup

- **u1 (Minor), `source_cleanup.py:276` and `:115`.** `hold()` updates `WHERE id=?` without a condition on the current state. If `on_completed` raises a typed busy error after a successful `run()`, a `completed` cleanup flips to `paused`. It was `needs_attention` before v0.16.5.
  - Data is safe: the next run only re-hashes the recovery copies of removed members, and `recovery_completion` keeps the first completion time.
  - If retention has already deleted the recovery copy by then, the re-run ends in a confusing needs-attention. A fix would be to guard the update with `AND state!='completed'`.
- **u2 (Minor), `audio_jobs.py:429`.** The Retry compare-and-set re-checks the job row, but not E5 (repair admissions), E6 (latest job for the book) or the `book_groups` revision.
  - This is safe today only because every writer of those is serialised with Retry by `operation_lock` and `_review_boundary`, and because the worker re-runs admission and the revision guard.
  - A future writer outside those locks would get past it silently.
- Open Critical: 0.
- Open Major: 4, all carried from v0.16.4: t1, s3, r1 and `working_lifecycle.py:228`. None is touched by this delta.
- Open Minor: 19, all advisory: new u1 and u2, plus the 17 carried from v0.16.4.
- **Always-blocking floor: intact.**
  - No original can be deleted without a fully verified recovery copy and verified output.
  - There are no new writes outside the library, the recovery root and the catalog.
  - No Electron change and no secret exposure.
  - No risk to repo history.

Major and Minor findings are logged for Ender's next cycle and do not gate this release.

## Verdict

- Total Critical: 0
- Total Major: 4
- Total Minor: 19

**Verdict:** RELEASE CLEAR

This clearance covers `b6cae4c21dc667eaafa27bd74a50504d7de54d13..9e1664ff50522a1afc92790f69f2efcba3240675` and the installer `Books-Arranger-Setup-0.16.5.exe` (SHA-256 `5bbf9bb91d9e94c6c8cc0b225ac6279e9e4198961e8b4017723e4d8dc820df5b`), bound by the manifest hash in the header.

It covers construction only. Futaba's QA GO is the independent behaviour gate.

A rebuild, or any product-file change after `9e1664f`, voids this artifact binding.
