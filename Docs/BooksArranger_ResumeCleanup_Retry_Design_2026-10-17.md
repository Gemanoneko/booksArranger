# Books Arranger: resume a stuck originals cleanup, and Retry for blocked jobs (design)

Date: 2026-10-17. Author: Ender. Design only. Implementation starts after v0.16.2 is tagged.

**Basis.**
- Code was read in the release worktree `scratch/electron-2026-10-13/worktree`, HEAD `d834971` (v0.16.2 candidate). Nothing in the worktree was edited.
- The live catalog `data/inventory.sqlite3` was read only through `?mode=ro&immutable=1` with `PRAGMA query_only=ON`. The WAL file was 0 bytes before and after, so the immutable view was current.
- One timing probe ran on a private copy of the catalog in Ender's session scratchpad. That copy has since been deleted.
- Nothing touched the live app, Z:, git or the data folder. The data folder was only listed.

All `file:line` references are to the worktree at `d834971`.

---

## 0. Summary

| | Change 1: resume the stuck originals cleanup | Change 2: Retry for blocked jobs |
|---|---|---|
| New UI | None. The existing **Start automatic processing** and **Resume audiobook jobs** buttons do it. | One button, specced by Judy (`../BooksArranger_RetryButton_Spec.md`). |
| New API | None. | `POST /api/audiobook/retry` |
| Mechanism | Turn the stuck row into a normal `paused` cleanup, which the existing admission already resumes. The unchanged `CleanupJobs.run()` re-verifies everything and finishes. | Requeue the same job row when it was refused **before any attempt started** and that refusal is now cleared. |
| Old working folder | The product's own lifecycle retires it. No separate handling is needed. | n/a |
| Redesign needed? | No. | No. |
| Size | S (~0.5 day with tests) | S–M (~1 day backend with tests, plus ~0.5 day for the button) |

### Decisions (Sergei, 2026-10-17, relayed by Jane)

| # | Question | Decision | Effect on this design |
|---|---|---|---|
| Q1 | Should Resume also re-check the 14 stream-held books? | **Allowed on condition.** Sergei: "Are those books already converted? Is there a risk we'll lose their converted copies? If no — allow." The condition is met: all 14 are converted, the outputs are hash-verified on Z:, and no cleanup path can touch them (2.6.1). | **Option (i), designed behaviour kept.** 2.2 item 7 is not implemented. |
| Q2 | Should the fix also finish a60bd396? | **Yes.** | No change: the 2.3 rule already covers it. |
| Q3 | Add the short automatic retry on lock timeout? | **Yes.** | Offer C moves into scope as 2.2 item 8, with tests 4.1-10 and 4.1-11. |

---

## 1. Root-cause facts

### 1.1 Stuck cleanup: book job `11a3f395`, cleanup `2f5ad6d7`

**What the catalog shows** (read-only):

| Fact | Value |
|---|---|
| `source_cleanup` row | `2f5ad6d7-b5d9-47b7-ab98-db42cdd043d1`, state `needs_attention`, reason `database is locked`, created 2026-10-15T10:57:20Z, updated 10:58:07Z |
| Members in manifest order | tracks 1–78 `removed`, track 79 `disposition_set`, tracks 80–129 `backup_verified`. All 129 have `backup_facts`; none has a `restore_intent`. |
| `source_retirements` | 78 rows. Track 79 has none. |
| `recovery_completion`, `recovery_retention`, `storage_cleanup_jobs` for this job | none |
| Zone-marker receipts | none |
| Recovery folder `data/source-recovery/2f5ad6d7…/` | 129 files |
| Kept working folder `data/merge-cache/audio-staging/11a3f395…/d1fc0542…/` | `cover.png` + 129 `sourceNNNNN.m4b` snapshots, 637 MB. The 1,959 generated files were already removed: all 1,959 `storage_cleanup_files` receipts are `removed`. No `working_attempts` rows exist (legacy attempt). |
| Audio job | `completed`; manifest and output unchanged since enrollment |
| Review binding (the guard every resumed step re-checks) | group and context revision 4 = manifest revision 4; context equals the frozen binding. **The guard would pass today.** |
| Recovery-root identity | identical across all 43 cleanups from 2026-10-10 to 2026-10-17, so the ancestry guard passes |
| Sizes | 129 sources, 664,809,539 B. Still on Z: 50 tracks, 228,770,716 B. Output 685,930,798 B. |

**Where it stopped.**
- Track 79 was disposed. Its `disposition_set` was committed (`source_cleanup.py:254-259`).
- The next statement opens the retirement transaction: `db.execute('BEGIN IMMEDIATE')` at `source_cleanup.py:262`.
- That statement failed after the 10 s busy timeout (`scanner.py:44-49`) with `sqlite3.OperationalError: database is locked`.

**How it was recorded.** The cleanup ran inline from `MergeService._after_completed` (`merge_service.py:464-471`). Its `except` writes `self.cleanup._set(id,'needs_attention',str(error))` at `merge_service.py:469`.

**Why nothing resumes it:**
- `CleanupJobs._work` selects only `waiting`/`paused` rows, plus `needs_attention` rows whose reason is exactly the extra-stream reason (`source_cleanup.py:166`).
- `MergeService.resume` starts the cleanup worker only for `waiting`/`paused` rows (`merge_service.py:284-288`).
- At startup, only `checking`/`removing`/`pausing` rows become `paused` (`source_cleanup.py:67`).
- The only HTTP cleanup action is `start_historical_cleanup`. It is limited to `INITIAL_CLEANUP_JOBS` (`merge_service.py:318, 330-337`; `web_server.py:363-368`).
- The only other action is restore (`merge_service.py:340-345`).

**Why the 24 h clock never started.**
- `recovery_completion` is written only by `_set(...,'completed')` (`source_cleanup.py:73`).
- Retention rows are created only from completed cleanups (`recovery_retention.py:27-47`).

**Why the catalog was locked.** This mechanism is strongly supported but was not reproduced live.
1. Every retired track inserts into `source_retirements` (`source_cleanup.py:268`).
2. The trigger `book_retirements_insert` then bumps `book_catalog_revision` (`groups.py:40`; trigger present in the live catalog).
3. The next status computation runs `progress_books`. That calls `groups.sync` **inside** its `with connect(...)` block (`merge_service.py:146-148`).
4. The revision changed, so `sync` regroups the whole library and issues `UPDATE`s. The first one runs for every existing group unconditionally (`groups.py:319-339`, especially `:323`).
5. The write transaction stays open until the block ends at `merge_service.py:181`. `scanner.ClosingConnection` commits only on exit (`scanner.py:37-42`).
6. Probe on a private copy of today's catalog (9,607 files, 3,327 groups): the regroup took 6.7–7.3 s. The write lock was held 2.9–3.2 s **inside `sync` alone**, before the rest of `progress_books` runs (approved-row rendering, cover-cache stats, output stats on Z:).
7. Status is polled about once a second. Source cleanup's state writes are single attempts with a 10 s busy timeout. Under encoding and hashing load, a long regroup can exceed that timeout.

**It recurred today on v0.16.1.**
- Cleanup `b50234b5` (job `a60bd396`, 1 track) failed the same way at 2026-10-17T07:13:21Z.
- Its only member is `removed` but the completion was not recorded. So it failed at `_set(id,'completed')` (`source_cleanup.py:263` → `:70-73`), right after its retirement bumped the revision.
- Its binding is also intact (revision 5 = 5, context equal).

### 1.2 Blocked job `644da7fc`

**What the catalog shows:**

| Fact | Value |
|---|---|
| `audio_jobs` row | state `needs attention`, stage `queued`, `attempt_id` `570dd759…`, reason `Working cleanup requires attention: Legacy attempt still contains working inputs; exact retirement review required before another snapshot`, updated 2026-10-16T23:58:37Z |
| Journal | `{attempt_id, history:[checking sources]}`. **No `failure`, no `publication_intent`.** `output` is NULL. |
| `working_attempts` / `working_files` / `audio_failure_history` / `audio_repair_admissions` | none |
| Candidate `421d037d` | the only job for it; group revision 4, not superseded; automatic state `Queued` |
| Integrity | manifest hash matches; `ownership.json` equals `{job_id, manifest}`, so a new attempt can reuse the job folder (`audio_pipeline.py:361-369`) |
| Old attempt folder | removed 2026-10-17 (`scratch/legacy-working-cleanup-2026-10-17/`). The job folder now holds only `ownership.json`. |
| Profile and policy | 17 MP3 sources; `cleanup_policy.enabled = true` |

**How it got there.**
1. `AudioJobs._work` calls `before_attempt`, which is `WorkingLifecycle.admit` (`merge_service.py:108`).
2. `admit` raised at `working_lifecycle.py:594`: the prior attempt folder had no receipt and was not empty.
3. `audio_jobs.py:312-316` then set `needs attention` with the prefix `Working cleanup requires attention: `.
4. It stopped the queue and fired `on_working_hold`, which also stops automatic processing (`merge_service.py:119`).
5. No new attempt started and the journal was untouched.

**Why nothing retries it:**
- `AudioJobs.retry_failed` requires `journal.failure.retryable is True` (`audio_jobs.py:227-229`).
- The M4B repair route requires one of two M4B reasons and a single M4B source (`failed_m4b_retry.py:23-34`).
- The automatic loop calls only these two (`automatic_processing.py:367-376` → `merge_service.py:756-766`).
- Create and Queue refuse a candidate that has a job (`review_backend.py:161` → `build_manifest` raises at `:489`).
- `enqueue` also deduplicates to the existing job id without touching its state (`audio_jobs.py:150-168`).

**Why it is now clear.** `admit` would pass today. The prior folder is absent (`working_lifecycle.py:590-594`) and there are no `working_attempts` rows (`:595-598`).

**Population.** 96 jobs need attention. 95 of them carry a recorded runtime `failure`:
- 51 remux timing
- 35 M4B leading gaps
- 3 unsupported brand
- 2 unsupported box
- 1 presentation bounds
- 1 preservation changed
- 1 ENOSPC (already covered by the automatic I/O retry)
- 1 legacy `database is locked`

**Only `644da7fc`** has the "refused before an attempt started" shape.

---

## 2. Change 1: resume the stuck cleanup

### 2.1 Trigger: user-triggered, through the existing cleanup admission

**Not automatic on start.**
- The module contract is "Constructors never start work" (`source_cleanup.py:5-6`).
- The brief's standing rules say a server restart never starts work and Start resumes saved work.

**Startup does only a DB-only reclassification. The work starts on the user's next:**
- **Resume audiobook jobs.** `/api/audiobook/resume` → `MergeService.resume` (`web_server.py:352-355`, `merge_service.py:276-289`) → `CleanupJobs.resume()` (`source_cleanup.py:154-158`).
- **Start automatic processing.** On Start the worker calls `merge.resume()` whenever `state()['queued']` is non-zero (`automatic_processing.py:336`; also `:321-324` in the discovery phase). A paused cleanup counts as queued (`merge_service.py:225-227`).

No new button and no new endpoint.

### 2.2 Proposed changes per file

**`source_cleanup.py`:**
1. Add `import sqlite3` and a helper `catalog_busy(error)`. It returns true only for `sqlite3.OperationalError` with an integer `sqlite_errorcode` whose primary code (`& 255`) is `SQLITE_BUSY` or `SQLITE_LOCKED`. This mirrors `audio_jobs.py:26-27`. It is typed, never message-based.
2. In `setup()`, add an append-only evidence table that keeps the reason that would otherwise be lost:
   `source_cleanup_holds(cleanup_id TEXT, at TEXT, prior_state TEXT, prior_reason TEXT, cause TEXT, PRIMARY KEY(cleanup_id, at))`.
   This is needed because `paused` rows must carry an empty reason: `app.js:379` renders any non-empty reason as "Source cleanup needs attention: …".
3. In `CleanupJobs.__init__`, next to the existing line 67 and in the same `with connect()`, run a **one-time legacy migration** (rules in 2.3). It inserts a `source_cleanup_holds` row and does a compare-and-set:
   `UPDATE source_cleanup SET state='paused', reason='', updated=? WHERE id=? AND state='needs_attention' AND reason='database is locked'`.
   DB only: no file IO and no thread. It checks that `audio_jobs` exists, because the unit fixtures have no such table.
4. Add a new method `hold(id, error)`, the single place a failed cleanup records its state:
   - **busy** → `paused`, reason `''`, plus a hold row with cause `catalog busy (<sqlite_errorname>)`
   - **anything else** → `needs_attention`, reason `str(error) or type(error).__name__` (the current behaviour)

   The write goes through `sqlite_retry.transaction`. It is a pure, replay-safe DB update with no file operation, so it stays inside that helper's contract. Today a busy error inside the failure handler itself would escape and kill the cleanup thread.
5. In `_work`, `except` at line 173 → `self.hold(row['id'], error)`.

**`merge_service.py`:**
6. In `_after_completed`, line 469 → `self.cleanup.hold(id, error)`. The `_enrollment_attention` branch (`:470`) is unchanged.
7. *(Only if Q1 had been "scope it". See 2.6.1 for the outcome.)* At line 287, `elif pending:self.cleanup.resume([c['id'] for c in pending])`. This is one line. Section 2.6 explains what it gives up.

**Short automatic retry before pausing (Q3 = yes):**

8. Add `CleanupJobs.run_with_retry(id)`. It runs `run(id)`. On a **typed** catalog-busy error (`catalog_busy`, 2.2-1), it waits 5 s, then 15 s, then retries `run(id)`, for at most 3 attempts in total.
   - The waits use `self.stop.wait(...)`, so Pause, Stop and Quit interrupt them immediately. An interrupted wait records `paused` through `hold()`.
   - Any non-busy error goes straight to `hold()`. After the last busy failure, `hold()` records `paused`.
   - Each attempt is a full, normal `run(id)` from durable state. That is exactly what a manual Resume does: `run()` is already restart-safe after every committed step (2.4).
   - The retry adds no new file operation and no state shortcut.
   - Each attempt writes one hold row with cause `catalog busy, attempt N`, so the history shows how often contention happened.
   - Callers: `_work` (`source_cleanup.py:171`) and `MergeService._after_completed` (`merge_service.py:467`) call `run_with_retry(id)` instead of `run(id)`.
   - Cost: at most about 20 s of waiting per failed attempt. On the inline path that time is spent on the converter thread between two books.

No change to `run()`, `recovery_retention.py`, `storage_cleanup.py`, the UI or the HTTP layer.

### 2.3 Eligibility for the legacy reclassification (all must hold)

1. `source_cleanup.state = 'needs_attention'` and `reason` is exactly `database is locked`.
   - This is SQLite's fixed text for `SQLITE_BUSY`, written before typed classification existed.
   - It matches the exact-historical-marker precedent in the Brief (daily-limit marker migration).
   - New rows never rely on text (rule 2.2-4).
2. The intent is a real enrollment: `intent.id == row.id`, `binding` non-empty, `recovery_identity` present. This excludes `_enrollment_attention` rows (`merge_service.py:131-134`), which have `binding {}` and can never pass the guard.
3. The audio job is `completed`.
4. No member is `restore_intended` or `restored`, and no member has a `restore_intent`. A started restore must never be followed by a repeated cleanup.

**Today this matches exactly two rows:** `2f5ad6d7` (job `11a3f395`) and `b50234b5` (job `a60bd396`). Sergei approved finishing both (Q2 = yes).

**Not migrated:**
- stream-held rows (they are already re-selected by `_work`)
- `Originals restored…` rows
- unknown-outcome rows (`removal_intended` with the original absent)
- enrollment-attention rows
- any other text

### 2.4 What the resume does

All of this is existing, unchanged `run()` code. It is idempotent over removed tracks.

| Step | Code | Effect for `2f5ad6d7` |
|---|---|---|
| Recovery-root and persisted ancestry identity | `source_cleanup.py:190-192` | passes (same identity since 2026-10-10) |
| Output M4B: parent identity, size, **full SHA-256** | `:193-195` | 686 MB re-hashed |
| Cover bytes | `:196-197` | re-hashed |
| Review guard | `:198-199` | passes today (1.1) |
| Free space | `:202` | needs the full 665 MB + 1 MiB on C: even though the copies exist. Passes: C: has 108 GB free. |
| Tracks 1–78 (`removed`) | `:208-213` | **recovery copy fully re-hashed**; original path must be absent; no retirement repeated |
| Track 79 (`disposition_set`) | `:208-212` | recovery copy re-hashed; original must be absent; `_retire` writes its missing retirement row. No second disposition. |
| Tracks 80–129 (`backup_verified`) | `:216-243` | Zone-marker check. Original re-opened with delete access and matched on size, timestamp, links, attributes, stored native identity, approved dev/ino and **full SHA-256**. Single stream. Existing recovery copy reused (`if not member` skips the copy), its timestamp restored, flushed and **fully re-hashed**. |
| Removal of the 50 | `:245-262` | Per track: durable removal intent → guard → native disposition → absence check → retirement |
| Completion | `:263` → `:70-73` | `recovery_completion.completed_at = now`. **The 24 h clock starts at resume time**, not on 2026-10-15. |
| Callback | `_work` `:172` → `on_completed` → `_prune_completed(job_id, source_completed=True)` (`merge_service.py:114, 437-456`) | `recovery.sync()` creates `retained`, expiring at `completed_at + 24 h` (`recovery_retention.py:27-47`). The retention loop purges it when due (`merge_service.py:391-421`, `recovery_retention.py:78-127`). |

**Safety on drift.** If any re-check fails, `run()` raises before the next removal and `hold()` records `needs_attention` with the specific reason. Examples:
- an original on Z: changed
- a recovery copy changed
- a Z: file ID changed
- a stream other than the download marker appears

The unknown-outcome guard (`:214-215`) is unchanged, so a `removal_intended` track whose original is missing stays in attention and its copy remains restorable.

### 2.5 The old working folder: the product's lifecycle retires it

After completion, `_prune_completed` reaches `storage_cleanup.run(job_id)` (`merge_service.py:446-451`). That function:
- verifies the completed output (`storage_cleanup.py:525`)
- requires the exact completed retirement of all 129 tracks with originals absent (`_source_safety`, `:236-260`)
- selects the files in `audio-staging/11a3f395…/d1fc0542…/` (`_staging`, `:358-427`):
  - the 129 `sourceNNNNN.m4b` by manifest hash and size (`:366, :393`)
  - `cover.png` after a byte check against the reviewed cover (`:388-397`; the cover cache file exists)
- prepares and disposes them with per-file receipts (`:549-558`)
- marks `storage_cleanup_jobs` `completed`

The 24 h recovery copies are not touched (`include_recovery=False`).

**No separate handling is needed.**
- What remains is the empty attempt folder and `ownership.json`. That is the same residue every finished book has today (observed for `1969bd85`, `382fe0d6`, `a60bd396`). It is out of scope here.
- If that storage step itself hits a busy catalog, it records `needs_attention` in `storage_cleanup_jobs`. Every Resume already retries it (`merge_service.py:282-283` → `_prune_completed`; transition `needs_attention → checking` is allowed at `storage_cleanup.py:70`).

### 2.6 Side effect Sergei must know about: 14 stream-held books (Q1)

`_work` re-selects every `needs_attention` row whose reason is exactly the extra-stream reason (`source_cleanup.py:166`).
- This is designed v0.16.1 behaviour: commit `841d637`, 2026-10-15, "clean verified download markers".
- It has a test: `tests/test_zone_identifier.py:105-110`, "normal cleanup resume rechecks previously stream-held book".
- It is Sergei-approved policy B: retire only when the extra stream is solely `Zone.Identifier`.

On the real library it has **never run**:
- 14 rows: 10 from 2026-10-13, 4 from 2026-10-15
- none updated since
- 0 zone-marker receipts in the catalog
- 331 tracks, 6.23 GB

Any Resume that starts the cleanup worker with `selected=None` will also process them. That includes the Resume that finishes `11a3f395`.
- Each book either finishes normally (marker removed, originals removed, 24 h recovery copies) or stays held with the same reason.
- 10 of them are ordered before `2f5ad6d7` (`ORDER BY created`), so `11a3f395` waits behind them.

Options:
- **(i) Keep as designed.** No extra code. The next Start/Resume also runs the first real-library pass of the download-marker path on 14 books.
- **(ii) Scope it.** One line (2.2-7): Resume continues only `waiting`/`paused` rows. This removes the only product trigger for re-checking stream-held books, so that feature would need its own trigger later.

Technically both are safe, because every removal re-verifies and keeps 24 h copies. The choice is Sergei's.

#### 2.6.1 Q1 evidence and decision: **allow** (option i, no extra code)

Sergei's condition: "Are those books already converted? Is there a risk we'll lose their converted copies? If no — allow."

**Method** (read-only, 2026-10-17):
- Catalog read through an immutable read-only open.
- On Z:: `stat` and a **full SHA-256** read of every converted output (6,085,036,771 B in total).
- Source streams listed with the app's own `zone_identifier.streams`.
- Each download marker's bytes read and checked with the app's own `_known_marker`.
- Nothing was written. The probe scripts were deleted afterwards.

| # | Book (job) | Tracks | Converted | Output verified | Risk to output |
|---|---|---|---|---|---|
| 1 | Последняя легенда — Обухова Лена (`4db85341`) | 28 | yes | yes | no |
| 2 | A Head Full of Ghosts — Tremblay Paul (`846deacf`) | 29 | yes | yes | no |
| 3 | Лезвие Эры — Райбер Влад (`a8ab6b6b`) | 10 | yes | yes | no |
| 4 | Летний лагерь — Райбер Влад (`b324a55e`) | 11 | yes | yes | no |
| 5 | Мясорубка — Райбер Влад (`71c8534e`) | 13 | yes | yes | no |
| 6 | Попробуй уснуть — Райбер Влад (`3b299c69`) | 12 | yes | yes | no |
| 7 | Страна вечного детства — Райбер Влад (`a8d51f2c`) | 17 | yes | yes | no |
| 8 | Четыре стеклянных бокса — Райбер Влад (`b55f0216`) | 16 | yes | yes | no |
| 9 | Самая страшная книга 2022 — Разные авторы (`09fcaf1f`) | 22 | yes | yes | no |
| 10 | Reborn — Wilson F. Paul (`89276319`) | 36 | yes | yes | no |
| 11 | Хранительница болот — Тимошенко Наталья (`19c56029`) | 31 | yes | yes | no |
| 12 | Гадючий Яр — Тимошенко Наталья (`03e6fbfa`) | 31 | yes | yes | no |
| 13 | Devil's Creek — Keisling Todd (`56d635a2`) | 26 | yes | yes | no |
| 14 | Пока мой труд не завершен — Лиготти Томас (`effa5745`) | 49 | yes | yes | no |

**What the columns mean:**
- **Converted** = the audio job is `completed`, and its saved output record equals the one frozen in the cleanup intent.
- **Output verified** = all of the following hold:
  - the validation record passed: `passed`, `checks = Output checks passed`, and its hash and size equal the record's
  - the final path equals the reviewed destination
  - an `owned_artifacts` output row exists with the same hash
  - the file exists on Z:
  - its size equals the record's
  - **the full SHA-256 of the file on Z: equals the catalog hash**

  All 14 pass every check.
- **No other version exists:** none of the 14 has a replacement relation or a chapter-repair publication.

**Risk to output = no, for every book, for these reasons:**
1. **The output is only ever opened read-only.**
   - `VerifiedFile(final)` without `delete` or `writable` asks for read access only and shares read only, so other writers are blocked while it is held (`native_io.py:171`).
   - The places that open it: the cleanup run (`source_cleanup.py:193`), the storage step and folder step (`storage_cleanup.py:134`, via `protected_output`), and the 24 h purge (`recovery_retention.py:102`).
2. **Only three kinds of path can ever get a delete-capable handle or a disposition:**
   - **Manifest source paths**, and only after size, timestamp, link count, attributes, stored native identity, approved dev/ino and full SHA-256 all match the reviewed original (`source_cleanup.py:177-184, 228-229`). A converted M4B can never pass this hash check.
   - **Paths under the app's private staging or recovery roots** (`storage_cleanup.py:150-152` refuses anything else).
   - **Empty source-parent directories** (`storage_cleanup.py:717-742`). These are unsupported on Z: and therefore retained.
3. **The marker step** removes only the `<source path>:Zone.Identifier` stream (`zone_identifier.py:78`), and only on source files.
4. **For all 14 books:**
   - the output path is not any source path
   - the output folder is not any source folder
5. **Fail-safe.** Before the first removal, the run re-hashes the output (`source_cleanup.py:193-195`). If the converted copy were missing or changed, no original would be removed.

**What will happen on the next Start/Resume.** All 331 source tracks pass the app's stream and marker checks:
- 314 have an accepted download marker.
- 17 have no extra stream.
- None is refused.

So all 14 books are expected to finish:
- 331 originals (6.23 GB) are removed from Z:.
- 6.23 GB of recovery copies are kept on C: for 24 h (108 GB free).
- The 14 converted audiobooks stay where they are.

Restored originals would come back without their download-marker stream. That is the expected result of policy B.

**Decision: allow (option i).** Item 7 of 2.2 is **not** implemented.

### 2.7 What Sergei sees (existing UI, no change)

- **Before resume:**
  - jobs panel: "Paused — Removing originals — 78 of 129" (`merge_service.py:225-226, 239`; `app.js:333, 339-344`)
  - book: "Source cleanup paused: 78 of 129 removed" (`source_cleanup.py:135`)
  - candidate status: "Paused" (`app.js:507`)
  - Resume tooltip: "Paused cleanup resumes without recreating the audiobook." (`app.js:353`)
- **During resume:** "Removing originals: N of 129".
- **After:** "Originals removed; recovery copies kept until <time>" (`source_cleanup.py:148`).

---

## 3. Change 2: Retry for blocked jobs

### 3.1 Approach: requeue the same job row

The job never started a new attempt, so its frozen manifest, job id and candidate binding are still the reviewed ones. Requeueing it (`needs attention` → `pending`) is the smallest safe path:

- The worker's own admission runs again, unchanged: `before_attempt` = `admit` (`audio_jobs.py:309-316`). It re-proves the old folder is gone or empty.
- The old attempt's journal is archived to `audio_failure_history` before the new attempt (`audio_jobs.py:311`, `:207-218`).
- The revision guard runs again before any work (`:347-348`).

Why not a child job like the M4B repair? A child needs a new manifest relation (`audio_repair_admissions`) and a new job id. It also leaves the parent permanently in attention. That is justified for the M4B route because the parent's output plan was wrong. Here nothing about the plan was wrong.

### 3.2 Eligibility rules

Rules E1–E8 are cheap: DB reads plus at most one folder listing. They are computed on every poll for the per-job `retry` field. E9–E10 are checked only when Retry is pressed.

| # | Rule | If it fails |
|---|---|---|
| E1 | `state = 'needs attention'` | no retry data (hidden) |
| E2 | `output IS NULL` and the journal has no `publication_intent` | hidden |
| E3 | The journal has **no `failure`**. Only `audio_jobs.py:313` produces `needs attention` + no failure + no output + no publication intent; every other writer either records a failure (`:372`) or concerns a published or completed row (`:118, :167, :250, :366`). This is structural, not message matching. | hidden. Runtime failures belong to `retry_failed` or the M4B repair. |
| E4 | `sha256(packed manifest) == manifest_hash` and `manifest.job_id == job_id` | hidden |
| E5 | Not a replacement job (`replacement_id`), not an M4B repair child (`m4b_repair`), and not the parent of a repair child (`audio_repair_admissions`) | hidden |
| E6 | It is the newest job for its candidate | hidden |
| E7 | No `audio_failure_history` row exists for `(job_id, attempt_id)` with a different record. Otherwise the worker's archive step would refuse (`audio_jobs.py:215`) and re-hold the queue. | hidden |
| E8 | **The admission is clear now**, checked read-only exactly as `admit` checks it: (a) `stage_root/job_id/attempt_id` is absent or empty, under `DirectoryBoundary` (`working_lifecycle.py:587-594`); (b) every `working_attempts` row for the job is `retired`. | `allowed:false` with a fixable reason |
| E9 | Pressed with the candidate id and revision on screen. They must equal `manifest.candidate_id`/`candidate_revision` and the current group revision; the job id must still be the candidate's newest. | 409 "This book changed. Refresh and try again." |
| E10 | `revision_guard(manifest) is True` (`MergeService._guard`, `merge_service.py:904-916`: frozen review, sources and cover still current; no scan). Plus: queue not closed, not draining for Quit, no scan running. | 409 with a reason; nothing changes |

Then a compare-and-set:

```sql
UPDATE audio_jobs SET state='pending', stage='queued', reason=?, updated=?
WHERE job_id=? AND state='needs attention' AND output IS NULL
  AND attempt_id IS ? AND journal=? AND manifest_hash=? AND reason=?
```

`rowcount` must be 1, otherwise 409 "This job changed. Refresh and try again." The journal and `attempt_id` are deliberately kept, so the worker archives them on admission. After the update, `MergeService.resume()` runs, the same pattern as Create audiobook (`merge_service.py:871-878`).

**Retry needs no idle queue.** A `pending` row simply joins the queue in `created` order, and the worker re-reads pending rows every loop (`audio_jobs.py:304`).

**Eligible today:** exactly one job, `644da7fc`.

### 3.3 Proposed changes per file

**`audio_jobs.py`:**
- `class RetryRefused(ValueError)`.
- `admission_holds()`: one query for rows matching E1–E3.
- `retry_status(row, admission_clear)` → `None` (hidden) or `{'allowed': bool, 'reason': str}` (E4–E8).
- `retry_admission_hold(job_id, candidate_id, revision, admission_clear)`: E1–E10 under `self._lock` (same locking as `retry_failed`, `:223-234`), then the compare-and-set.

**`working_lifecycle.py`:**
- Move the legacy-prior check out of `admit` (`:587-594`) into `_legacy_prior(row)`. `admit` keeps its behaviour.
- Add a read-only `admission_clear(row)`: `_legacy_prior(row)`, then refuse if any `working_attempts` row for the job is not `retired`. Raises `BoundaryError`; no file is opened for write.

**`merge_service.py`:**
- `retry_statuses()` → `{job_id: status}` (one query plus E8 per eligible-shape row).
- `candidate_status` (`:558-563`) adds `'retry'` when not `None`.
- New `@operation retry_blocked_job(library, identity, revision, job_id)`:
  1. `_no_scan()`; refuse while `draining`.
  2. Inside `_review_boundary()`: `jobs.retry_admission_hold(..., self.working.admission_clear)`.
  3. `self.resume()`.
  4. Return `{'job_id', 'requeued': True, 'audiobook_jobs': self.state()}`.

**`review_backend.py`:** in `page()` (`:205-210`), compute `retry_statuses()` once per page and attach `retry` to each `page_local.jobs[...]` entry. `enrich` already passes the job through as `row.creation.job` (`:171`), so the UI reads `row.creation.job.retry`.

**`web_server.py`:** add the route (3.4) in `merge_request`, add it to `merge_routes` (`:427`), and add it to the scan-refusal set (`:460`).

**UI (after Judy's spec is committed):** `web/app.js`, `web/index.html`, `web/style.css`, `web/desktop-ui.js`. This is Judy's spec, not part of this backend design.

### 3.4 API endpoint

```
POST /api/audiobook/retry
Body (exact keys): {"library":"Audiobooks","id":"<candidate uuid>","revision":<int>,"job_id":"<job uuid>"}
202 {"job_id": "...", "requeued": true, "audiobook_jobs": {...merge state...}}
409 {"error": "<one short user-facing sentence>"}   eligibility/staleness/guard refusal, nothing changed
400 malformed body (existing shape/uuid/revision validators)
409 scan running / server closing (existing do_POST gates)
```

- Validation reuses `uuid_value`, `candidate_identity` and `shape` (`web_server.py:288, 300-310`).
- `RetryRefused` is caught in `merge_request` and returned as 409. Without that, `do_POST` maps every `ValueError` to 400 (`:468-469`).
- The token check, `control_lock`, the `merge_admissions` count and status invalidation are all inherited from `do_POST`.

### 3.5 Facts for Judy

Her spec is at `scratch/design-2026-10-17/BooksArranger_RetryButton_Spec.md`. Her assumed API matches with these names: **`row.creation.job.retry.allowed`** and **`row.creation.job.retry.reason`**. The field is absent when Retry does not apply. It refreshes on every `/api/inventory` poll.

**Eligible jobs today.** One: `644da7fc` (candidate `421d037d`, 17 MP3 tracks). All 95 other needs-attention jobs have a recorded runtime failure, so they get **no retry data** (her state 1, hidden). Those are handled by the automatic I/O retry or the M4B repair, or need review.

**States and labels:**
- Job states: `pending` / `running` / `completed` / `needs attention`.
- UI labels: **Queued / Creating / Audiobook created / Output needs attention** (`merge_service.py:562`, `review_backend.py:207`).
- After a successful Retry: Output needs attention → Queued → Creating → Audiobook created.
- The job's own reason is in `row.creation.job.reason`. No renderer reads it today. Her C1 finding is correct: the visible status falls back to "Audiobook job already exists; inspect its current status" (`review_backend.py:161`; `app.js:500`).

**Where needs-attention jobs show today:**
- **Audiobook jobs panel** (`index.html:48`): "· N need attention" (`app.js:328`). The count includes cleanup, storage and replacement errors (`merge_service.py:229-235`).
- **Candidates filter** "Output needs attention" (`app.js:10`; `review_backend.py:199, 229`).
- **Selected book:**
  - Automatic result (`index.html:63`)
  - Audiobook output `#output-status` / `#output-reasons` (`index.html:100`; `app.js:373, 376, 498-514`)
  - Create audiobook stays disabled, because `can_create` is false while a job exists (`index.html:98`; `app.js:96`).

**Reason strings** when `allowed:false`. These are proposals; Judy owns the final copy:
- E8a/E8b: "Working files from an earlier attempt are still present. Retry after they are cleared."

**409 strings** (shown verbatim in her refused note):
- "This book changed. Refresh and try again."
- "The book's review or source files changed. Review the book again."
- "Books Arranger is closing. Retry after it restarts."
- Scan running, existing gate: "Stop scanning before queueing or resuming audiobook jobs". This fails her copy rules, and Judy may reword it. It is shared with Resume and Create.

**Her open items:**
- **(a) Does Retry touch source files?** The request itself does not. **But the requeued job will**: after a verified audiobook, it removes the book's included originals under its saved cleanup policy, with 24 h recovery copies, like every queued book. **The tooltip sentence "Source files stay untouched." must not ship.**
- **(b) Retry during the automatic one-hour wait?** That wait applies only to jobs with a recorded classified failure (`audio_jobs.py:230-231`), and those never get retry data. The new Retry is never shown during the wait. Her C2 wording change is independent.
- **(c) Hidden vs. disabled:** hidden for E1–E7 (not fixable from the UI). Disabled with a reason for E8 (fixable once the files are cleared). E9–E10 are refusals at press time.

**Change 1 needs no UI work.** One optional copy issue: while a cleanup is paused, Restart and update say "Pause audiobook jobs in the app…" even though it is already paused (`app_launcher.py:164-166`).

---

## 4. Tests to add

### 4.1 Change 1 (`tests/test_source_cleanup.py`, `tests/test_merge_service.py`, `tests/test_automatic_processing.py`)

1. **Legacy migration, positive.**
   - Fixture: a cleanup stopped mid-removal (first tracks `removed`, one `disposition_set` with the original disposed, the rest `backup_verified`); `needs_attention` / `database is locked`; completed job row.
   - Constructing `CleanupJobs` makes it `paused` with an empty reason and writes one hold row.
   - **No thread starts and no file is opened** (positive control: patch `VerifiedFile` to count opens and assert 0).
2. **Legacy migration, negative.** Each stays `needs_attention`:
   - extra-stream reason
   - `Originals restored…`
   - enrollment-attention row (`binding {}`, no `recovery_identity`)
   - row with a `restored` member or a `restore_intent`
   - job not completed
   - `database is locked` with different case or trailing text
3. **Resume completes idempotently.**
   - After 1, `run()` disposes only the `backup_verified` originals.
   - The `disposition_set` track gets its retirement row with no second disposition (assert the disposition count).
   - Every recovery copy is hashed (count `sha256` calls = number of members).
   - `recovery_completion.completed_at` is at or after the resume start, not the fixture's original time.
   - `RecoveryRetention.sync()` gives `retained` with `expires_at = completed_at + 24 h`.
4. **Re-verification refuses.** One recovery copy changed after 1 → `BoundaryError` before the next disposal, then `needs_attention` via `hold`, and the remaining originals stay. Same with one remaining original changed.
5. **Typed busy at the failure points.**
   - Patch `_retire` and, separately, the final `_set(...,'completed')` to raise `sqlite3.OperationalError` carrying `sqlite_errorcode = SQLITE_BUSY` (and `SQLITE_LOCKED`, and an extended busy code) → `paused` plus a hold row.
   - **Positive control:** an `OperationalError('database is locked')` with **no** error code → `needs_attention` (typed only, same as `test_sqlite_busy.py:94-104`).
   - A busy error inside `hold` itself is retried by `transaction` and never escapes the thread.
6. **Inline path.** `MergeService._after_completed` with the cleanup raising typed busy:
   - the audio row stays `completed` and the cleanup is `paused`
   - the next `MergeService.resume()` finishes it
   - `on_completed` → `storage_cleanup.run` removes the staging snapshots and cover, leaves `ownership.json` and the 24 h copies, and sets `storage_cleanup_jobs` `completed`
7. **Automatic Start.** A paused cleanup plus queued books: Start calls `merge.resume()` and the cleanup completes before the next book starts.
8. **Existing guard kept.** Re-run `test_unknown_disposition_restorable_without_false_success` and `test_normal_cleanup_resume_rechecks_previously_stream_held_book` unchanged.
9. *(Only with option ii)* Resume with a paused row plus a stream-held row → only the paused row runs.
10. **Short retry (Q3).**
    - Patch the retirement step to raise a typed `SQLITE_BUSY` once, then succeed → the cleanup completes on the next attempt.
    - Assert that each track was disposed exactly once.
    - Assert that one hold row was written and that the state was never `needs_attention`.
    - With a fake clock or patched `stop.wait`, assert the waits are 5 s then 15 s.
11. **Short retry, exhausted or interrupted.**
    - Busy three times → `paused`, with 3 hold rows.
    - `stop` set during the first wait → returns at once and records `paused`; the wait is never slept in full (assert elapsed < 1 s).
    - A non-busy error on attempt 2 → `needs_attention` with that error and no third attempt.
    - Positive control: an `OperationalError('database is locked')` with no error code is **not** retried.

### 4.2 Change 2 (new `tests/test_blocked_retry.py`; `tests/test_merge_http.py`)

1. **End to end.**
   - A pending job whose prior attempt folder holds a file with no receipt → the worker sets `needs attention` with no `failure` and stops (the existing hold).
   - `retry.allowed` is false with a reason **while the file exists**; delete it and the next status read gives `allowed: true`.
   - Retry → `pending` → the worker archives the old journal to `audio_failure_history` exactly once and starts a new attempt id.
2. **Hidden cases (E1–E7)** each give `retry is None` and a refused POST:
   - recorded failure, both `retryable` true and false
   - output present
   - `publication_intent`
   - manifest hash mismatch
   - replacement job
   - M4B repair child
   - parent with a repair child
   - not the newest job
   - archive conflict
3. **E8b.** A non-`retired` `working_attempts` row → `allowed: false`.
4. **E9/E10.** Stale revision, different job id, guard false, draining, closed queue → 409. **The row is byte-identical afterwards** (positive control: compare the whole row before and after).
5. **Compare-and-set.** Change the journal between the read and the update (patch `revision_guard` to mutate the row) → 409, nothing requeued.
6. **No idle requirement.** Retry while the worker runs → the row is picked up after the current book, with no second worker thread.
7. **`page()` cost.** The retry statuses add one query and no `revision_guard` or hash calls per poll (count the calls).
8. **HTTP.**
   - extra or missing key → 400
   - bad uuid or revision → 400
   - query string → 400
   - ineligible → 409 with `error`
   - scan active → 409
   - success → 202 with `requeued: true`
   - no token → refused (existing `trusted`)

### 4.3 QA notes for Futaba

- Fixtures only, on the committed build.
- The real resume on Z: is the product action Sergei approved (option A). It happens when he, or automatic processing, presses Start after the release is installed.
- Positive control for "24 h starts at resume": check `recovery_completion.completed_at` against the resume time.

---

## 5. Risks

1. **The lock contention is not fixed by this design** (1.1, measured 2.9–7.3 s regroups).
   - With 2.2-4, a future busy failure pauses the cleanup instead of stranding it.
   - The automatic worker continues the queue. When its research list is empty it waits for idle, sees `Paused` and stops (`automatic_processing.py:347-349`) until the next Start.
   - So a busy failure during an overnight run costs the rest of the night.
   - Two events in three days, the second today on v0.16.1.
   - **Mitigated by the short retry (Q3 = yes, 2.2-8).** A pause now needs three busy failures in about 20 s. The 2.9–7.3 s regroups measured here would have to keep landing back to back. The root cause is still offer D.
2. **A paused cleanup blocks Restart and update** (`app_launcher.py:164`). It also defers **all** recovery-copy deletion, both the automatic 24 h purge and manual deletes (`merge_service.py:364-371`), until it finishes.
   - After installing the version with Change 1, both migrated rows are `paused`.
   - Until Sergei presses Start or Resume once, the next update cannot install and expired recovery copies stay on C:. This is the safe direction.
3. **The resume also sweeps the 14 stream-held books.** Sergei allowed this (Q1, 2.6.1).
   - Their converted outputs are hash-verified and cannot be touched.
   - All 331 originals are expected to go, with 6.23 GB of recovery copies on C: for 24 h (108 GB free).
   - This is the first real-library run of the download-marker path.
   - `11a3f395` is queued behind 10 of them, so the first Resume takes longer: about 6.2 GB copied plus hashing.
4. **Re-verification can refuse** if Z: or the recovery copies drifted since 2026-10-15. That is the intended outcome. **I did not inspect Z:** (per the brief), so the 50 remaining originals and the absence of the 79 removed ones are taken from the catalog and Jane's numbers.
5. **Resume cost.** About 1.6 GB of reads (129 copies, 50 originals, output), then about 1.3 GB more in the storage step (snapshots and output). Minutes.
6. **Legacy text match.** Exact literal only, limited by 2.3 rules 2–4, with precedent. New rows are typed.
7. **Retry leads to original removal.** Retrying `644da7fc` converts it and then removes its 17 originals under its saved policy (24 h copies). Expected, but Sergei should know (3.5a).
8. **A retry can re-hold the queue.** If the admission fails again, the existing hold path stops the queue **and automatic processing** (`audio_jobs.py:312-316`; `merge_service.py:119`). E8 pre-checks the same conditions to make this unlikely. It cannot rule out a race with a concurrently created file.
9. **Free-space pre-check** counts all 665 MB even though the copies exist (`source_cleanup.py:202`). Harmless today; it could false-refuse on a nearly full C:. Left unchanged to stay minimal.
10. **Residue.** The empty attempt folder and `ownership.json` stay after cleanup, like every finished book. Not addressed.

---

## 6. Size estimate

| Item | Code | Tests | Effort |
|---|---|---|---|
| Change 1 incl. the short retry (source_cleanup ~50 lines, merge_service ~2) | ~55 lines | ~200 lines, 11 cases | **S**, ~0.5–0.75 day |
| Change 2 backend (audio_jobs ~50, working_lifecycle ~15 incl. refactor, merge_service ~30, review_backend ~3, web_server ~12) | ~110 lines | ~250 lines, 8 groups | **S–M**, ~1 day |
| Retry button per Judy, incl. her C1/C2 (app.js ~40, index/style/desktop-ui ~6) | ~45 lines | frontend ~60 lines | ~0.5 day |
| **Total** | | | **~2 days**, one release. Bump type is Sully's call; Change 2 adds a feature. |

Senua should red-team the migration predicate (2.3), `hold()` and E3/E8/compare-and-set. These touch the always-blocking safety floor: file deletion and original removal.

---

## 7. Offers (not in this design; Sergei's call)

- ~~C. Bounded in-place retry before pausing~~ — **accepted (Q3 = yes)**; it is now 2.2 item 8.
- **D. Root contention fix** (M, separate design). Commit `groups.sync` in its own short transaction before `progress_books` renders, or skip regrouping in status polls while a cleanup is running. This removes the cause in 1.1.
- **E. Legacy locked audio job `d9433878`.** A `database is locked` runtime failure recorded in the old format (`retryable:false`, no error code). Covered by neither change.
- **F. Restart/update copy** when a cleanup is already paused (5-2). For Judy.
- **G. Automatic retry of cleared admission holds** in the automatic loop, instead of only the button.

---

## 8. Questions for Sergei: answered 2026-10-17

1. Should Resume also re-check the 14 stream-held books? **Allowed**, on condition that the converted copies are safe. The condition is met (2.6.1).
2. Finish the second stuck book `a60bd396` too? **Yes.**
3. Add the short automatic retry? **Yes** (2.2 item 8).

No open questions remain for this design.

---

## Appendix: evidence method

- Catalog reads: Python `sqlite3` with `file:...inventory.sqlite3?mode=ro&immutable=1` and `PRAGMA query_only=ON`. Queries covered `source_cleanup`, `cleanup_members`, `source_retirements`, `recovery_*`, `storage_cleanup_*`, `working_*`, `audio_jobs`, `audio_failure_history`, `audio_repair_admissions`, `automatic_candidates`, `book_groups`, `candidate_context`, `source_zone_marker_intents` and `sqlite_master` triggers. The WAL was 0 bytes before and after.
- Timing probe: the SQLite backup API copied the catalog from the immutable connection into Ender's session scratchpad. `groups.sync` from the worktree ran on that copy with `python -I -B` (no bytecode written to the worktree), after one `book_catalog_revision` bump, timed from the first write statement. The copy and the probe scripts were deleted afterwards.
- Filesystem: directory listings only, under `data/merge-cache/audio-staging` and `data/source-recovery`, plus one read of `audio-staging/644da7fc…/ownership.json`. **Z: was not accessed.**
- Q1 follow-up (read-only on Z:, method in 2.6.1):
  - `stat` and a full SHA-256 of the 14 converted outputs
  - stream listing and marker-byte check of their 331 source tracks
- **Not verified:**
  - the current state of the 50 remaining `11a3f395` originals on Z:
  - what `enrich` currently returns as `creation.reasons` for candidate `421d037d`, because it stats Z:
  - rendered UI
