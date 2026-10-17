# Books Arranger — M4B "needs attention" refusals: support and repair (2026-10-17)

Author: Ender. Part 1 is the 0.16.7 implementation, uncommitted in this worktree. Part 2 is the earlier read-only investigation it is based on.

# Part 1 — 0.16.7 implementation

## My files

| File | sha256 |
|---|---|
| `m4b_preservation.py` | `c83e42e8fefb7c384cfe672e7861dd335789fe80a2308118756590139dd63d4a` |
| `m4b_repair.py` | `60b4a3c3f435d7d1ffa7d35612bcdad71c211616e6289fb461efac3a03c2d28f` |
| `m4b_readmission.py` (new) | `7efdb690c06ea59453f2d51a636fb8036cbc72b7569c673665f7a8179bcb6b33` |
| `failed_m4b_retry.py` | `66d380b11c34df48f8ee191d3011b60fd72078881c6426ed6f25c034c15ba7ae` |
| `tests/test_m4b_preservation.py` | `5a9e466e05100be9d6cc379928e9bdb29a397b86d59c2e1ff3a5cc4fa4d9cad6` |
| `tests/test_failed_m4b_retry.py` | `1c1630aa0d7dd6a23833ddbcb18390134a054af9acbd780c33013b03d1b2267f` |

**check-desktop (one run, after the last code change):** `BOOKS_INTEGRATED_CHECKS_PASS`. That is 603 Python cases, 40 Node cases and 9 frontend scripts. The new cases all ran green: WriterFamily 17, DamageRepair 9, RepairAdmissionContract 4, SilenceRepairShape 9, SilenceRepairDecode 2 (real decoder), PriorityReadmission 4, plus the retry-route reason tests. The run includes the other Ender's in-progress files as they stood.

## What changed

**1. Writer-family allowances** (exact observed shapes; each has an acceptance test and refusal tests for its neighbouring shapes):
- **A — AUDIOKNIGA / iTunes.**
  - The zero compatible-brand slot is ignored.
  - `alis` with exactly `00000001` (empty self alias) is accepted on chapter **text** tracks only.
  - Text sample-entry data-reference index 0 is accepted on text only, after the single self-contained `dref` entry is proven.
- **Q — QuickTime 7 / Audiobook Builder.**
  - `free`/`skip` are allowed directly inside `trak` only.
  - The `stsc` row cap is the proven chunk count.
  - A 52-byte text entry is accepted only when its last byte is 0.
- **N — Nero `tags`.** Accepted only with children `{meta, cvrx, tseg}`; kept verbatim.
- **B — Chapter and Verse 1.5.** Accepted only as the exact `ftyp` payload.
- **Positive control:** against the original module, every acceptance test fails.

**2. Retry route (`failed_m4b_retry.REASONS`).** It now holds: the 2 legacy remux reasons, "M4B presentation bounds cannot be verified" (Bird Box), "M4B preservation requires review: Unsupported/ambiguous brand", "…: Unsupported structural box", and "Preservation changed decoder, packets or presentation". Admission still requires a passing `plan()` proof. Neighbouring reasons stay out; damage goes to Repair.

**3. `MAX_CHUNKS` 262,144 → 524,288 (2^19).** This is a work bound, not a proof rule: every chunk is still proven inside the retained `mdat`, non-overlapping and fully mapped, and the `MAX_SAMPLES`/`MAX_MOOV` bounds are unchanged. Measured `plan()` costs:

| Case | Time | Peak memory |
|---|---|---|
| Synthetic: exactly 2^19 chunks | 23 s | 181 MiB |
| Synthetic: 2^19 + 1 chunks | refused | — |
| *Пока все дома* | 53 s | 241 MiB |
| *A Memory of Light* | 23 s | 114 MiB |

Tested at the exact boundary.

**4. Damage repair (only when the user presses Repair).** `plan(…, repair=…)` is strict unless the caller names the kind:

| Kind | Exact shape | Output | Proof |
|---|---|---|---|
| `dangling_chapter_reference` | The audio track's single `chap` names absent track IDs | Only those IDs dropped | Every other track byte identical; graph checks still apply |
| `mdat_tail_overrun` | The final `mdat` declares ≤ 4096 B past EOF; no sample reaches past EOF | Zero bytes complete the `mdat` | All original bytes at their offsets; padding re-read as exactly zero |
| `truncated_final_frames` | The final `mdat` ends ≤ 64 KiB early; only the **last k audio** frames reach past EOF; AAC-LC 1024-sample frames, mono or stereo, variable sizes; ≤ 1 s; no chapter sample cut | Zero padding plus an appended `mdat` of k silent AAC-LC frames. Only the cut samples' sizes and the final chunk's map/offsets change; all timing tables are byte-identical, so the durations are exact | Byte level: intact sizes, offsets and chunk membership are compared, the track is re-validated, everything is re-read. Decode level (`m4b_repair.prove_silenced_tail`): output decodes fully under `-xerror`; its PCM starts with **exactly** the source's intact-frame PCM; samples after the first replaced slot are exactly 0.0; intact packet timing is identical; replaced packets keep their durations |

- **Silent frame** (`silent_aac_frame`): a syntactically complete AAC-LC `raw_data_block` with `max_sfb` 0. It is 4 bytes mono and 7 bytes stereo. With the real decoder it decodes to exactly 0.0 at 16–48 kHz; this is a test.
- **Призраки белых ночей:** no audio is missing; the header overstates the `mdat` by 8 bytes, which is the tail-overrun shape.
- **Measured:** a cut source fails a strict decode (exit 183); a lenient decode yields exactly its intact frames.
- **Per-book note:**
  - In the job validation: `damage_repair = {note, repairs[...], silence_proof}`.
  - While queued: `manifest.m4b_repair.note`.

**5. Retry and Repair run next** (Sergei: "queued after the book that is running").
- **Accepted at any time.** `m4b_readmission.request()` is accepted even while a book converts and stored durably in click order; repeat clicks keep their place.
- **Admitted by the worker.** Between books, the worker hook `next_job()` takes the head request and admits it through the **unchanged** proof route: `plan()` proof, frozen-review CAS, one child per failed parent, and the per-book working-file gate. The child runs **next**, ahead of the normal queue; several clicks run in click order.
- **Refusals are per book.** A refusal is recorded for that book only, with its reason, and the next request proceeds.
- **Deferral and interruption.** During a library scan the request keeps its place. A stop leaves it queued. Any exception from the hook falls back to the normal queue and never stops the worker.
- **The worker never takes `operation_lock`.** That avoids a deadlock with Pause/Quit.
- **State for the UI:** `{'accepted', 'queued_next', 'position', 'kind', 'state', 'parent_job_id', 'child_job_id'}`, or `{'queued_next': False, 'accepted': False, 'reason'}` after a refusal. `status()` and `describe()` are read-only.
- **The automatic run's `retry_automatic_job` is unchanged:** normal order, no priority.

## Hunks for the other Ender

**`audio_pipeline.py`: nothing left.** He has applied H1–H6, including H3b (disk check counts the silent frames), H5/H5b (no strict source decode for an approved silence repair) and H6 (`prove_silenced_tail`). This was verified in his file.

**Still to apply: `audio_jobs.py` (AJ1–AJ4) and `merge_service.py` (MS1–MS6).**
- **Anchors:** every `old` text below occurs exactly once in his current files (checked).
- **Validation:** I applied all of them to a **scratch copy** of his current files and ran 155 related tests. The only failures are 11 cases in **his** `tests/test_attention_repair.py`, all asserting the old contract: the worker-busy "allowed: False / …when the current audiobook finishes" answers; a click returning `requeued`/a child or raising `RetryRefused` at once; and admission refusals returned at click time. Update these with the hunks; worker-side refusals are now tested through `_admit_m4b_readmission` / `_repair_damaged_m4b(…, in_worker=True)`:
  - `ClassificationTests.test_m4b_reasons_from_the_module_are_can_retry_with_new_child_retry_data`
  - `ClassificationTests.test_provable_damage_is_can_repair_never_retry`
  - `RepairAdmissionTests.test_an_intact_source_has_no_repair`
  - `RepairAdmissionTests.test_button_request_rules`
  - `RepairAdmissionTests.test_one_proven_child_with_the_approved_repair_and_untouched_originals`
  - `RepairAdmissionTests.test_refusals_admit_nothing_and_change_nothing`
  - `RetryAllTests.test_the_whole_group_one_at_a_time_then_the_queue_starts_once`
  - `RetryRouteTests.test_m4b_rows_go_through_retry_automatic_job`
  - `RetryRouteTests.test_not_now_answers_are_shown_and_stale_views_refused`
- **Frontend test:** `tests/test_attention_frontend.js` also expects the 409 "Repair can start when the current audiobook finishes." message.
- **Source of truth:** `…/scratchpad/m4b/harness/hunks_his.py` (`apply_his.py` applies it to a copy).

**AJ1 (hook attribute)** — in `audio_jobs.py`, replace:
```python
        self.before_attempt = None
```
with:
```python
        self.before_attempt = None
        self.next_priority = None  # m4b_readmission hook: the job id that runs next, or None
```

**AJ2 (next-job selection)** — in `audio_jobs.py`, replace:
```python
            pending = self._rows("SELECT * FROM audio_jobs WHERE state='pending' ORDER BY created, job_id LIMIT 1")
```
with:
```python
            # Retry/Repair clicks run right after the current book, in click order (m4b_readmission).
            try:priority = self.next_priority() if self.next_priority else None
            except Exception:priority = None  # ordering only: the request keeps its place, the normal queue runs
            pending = (self._rows("SELECT * FROM audio_jobs WHERE job_id=? AND state='pending'", (priority,)) if priority else []) or self._rows("SELECT * FROM audio_jobs WHERE state='pending' ORDER BY created, job_id LIMIT 1")
```

**AJ3a (Repair accepted while converting)** — in `audio_jobs.py`, replace:
```python
                    value['repair'] = {'allowed': not worker, 'reason': REPAIR_WORKER_BUSY if worker else ''}
```
with:
```python
                    value['repair'] = {'allowed': True, 'reason': ''}  # accepted now, runs right after the current book
```

**AJ3b (M4B Retry accepted while converting)** — in `audio_jobs.py`, replace:
```python
                value['retry'] = {'allowed': not worker, 'reason': RETRY_WORKER_BUSY if worker else ''}  # M4B: new child work
```
with:
```python
                value['retry'] = {'allowed': True, 'reason': ''}  # M4B: accepted now, runs right after the current book
```

**AJ4a (ledger read inside the single summary read)** — in `audio_jobs.py`, replace:
```python
            shapes = {row['job_id']: self._retry_shape(db, row, latest) for row in rows}
```
with:
```python
            shapes = {row['job_id']: self._retry_shape(db, row, latest) for row in rows}
            import m4b_readmission
            readmission = m4b_readmission.status(db, [row['job_id'] for row in rows]) if rows else {}
```

**AJ4b (readmission on the row)** — in `audio_jobs.py`, replace:
```python
            summary[row['job_id']] = value
        return summary
```
with:
```python
            if row['job_id'] in readmission:value['readmission'] = readmission[row['job_id']]  # queued_next + position, or a refusal reason
            summary[row['job_id']] = value
        return summary
```

**MS1 (wire the worker hook)** — in `merge_service.py`, replace:
```python
        self.jobs.before_attempt=self.working.admit
```
with:
```python
        self.jobs.before_attempt=self.working.admit
        self.jobs.next_priority=self._next_m4b_readmission
```

**MS2 (click request, worker hook, worker-side admission)** — in `merge_service.py`, replace:
```python
    def retry_automatic_job(self,job_id,now,resume=True):
```
with:
```python
    def _request_m4b_readmission(self,job_id,kind):
        """A Retry/Repair click is accepted at once and runs right after the current book, in click order."""
        import m4b_readmission
        with self.jobs._db() as db:return m4b_readmission.request(db,job_id,kind,time.time())

    def _next_m4b_readmission(self):
        """audio_jobs worker hook, between books (no operation lock): the job id that runs next, or None."""
        import m4b_readmission
        return m4b_readmission.next_job(self.jobs._db,self._admit_m4b_readmission,time.time())

    def _admit_m4b_readmission(self,parent_job_id,kind):
        """Worker thread, between books: the same proof routes as an idle click, minus the worker-busy refusal."""
        if self.inventory.worker and self.inventory.worker.is_alive():return {'defer':True}  # after the scan
        parent=next(iter(self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(parent_job_id,))),None)
        if not parent:return {'requeued':False,'reason':'The failed book is no longer in the queue.'}
        if kind=='retry':return self._retry_preserved_m4b(parent,time.time(),in_worker=True)
        return self._repair_damaged_m4b(parent,time.time(),in_worker=True)

    def retry_automatic_job(self,job_id,now,resume=True):
```

**MS3a (retry route callable from the worker)** — in `merge_service.py`, replace:
```python
    def _retry_preserved_m4b(self,parent,now):
```
with:
```python
    def _retry_preserved_m4b(self,parent,now,in_worker=False):
```

**MS3b (no worker-busy refusal inside the worker)** — in `merge_service.py`, replace:
```python
        if self.jobs._thread and self.jobs._thread.is_alive():return result
```
with:
```python
        if not in_worker and self.jobs._thread and self.jobs._thread.is_alive():return result
```

**MS4a (Repair: API entry queues; admission body callable from the worker)** — in `merge_service.py`, replace:
```python
    @operation
    def repair_damaged_m4b(self,job_id,now):
        """Repair button only, never automatic: admit one child job that applies the user-approved,
        proven M4B damage repair (m4b_repair). The failed parent row is kept unchanged; the child is
        verified like every preserved M4B before publication, and originals then follow the normal
        cleanup and recovery policy."""
        import m4b_preservation,m4b_repair
        from source_cleanup import single_stream
        from audio_jobs import REPAIR_WORKER_BUSY
        self._no_scan()
        result={'requeued':False}
        parent=next(iter(self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,))),None)
        if not parent or not m4b_repair.eligible(parent):return result|{'reason':'This book cannot be repaired.'}
        if self.jobs._thread and self.jobs._thread.is_alive():return result|{'reason':REPAIR_WORKER_BUSY}
```
with:
```python
    @operation
    def repair_damaged_m4b(self,job_id,now):
        """Repair entry point, never automatic: accepted at once and admitted by the worker right after the
        current book (m4b_readmission), through _repair_damaged_m4b."""
        import m4b_repair
        self._no_scan()
        parent=next(iter(self.jobs._rows('SELECT * FROM audio_jobs WHERE job_id=?',(job_id,))),None)
        if not parent or not m4b_repair.eligible(parent):return {'requeued':False,'accepted':False,'reason':'This book cannot be repaired.'}
        result=self._request_m4b_readmission(job_id,'repair');self.resume()
        return result|{'requeued':False}

    def _repair_damaged_m4b(self,parent,now,in_worker=False):
        """Admit one child job that applies the user-approved, proven M4B damage repair (m4b_repair). The
        failed parent row is kept unchanged; the child is verified like every preserved M4B before
        publication, and originals then follow the normal cleanup and recovery policy."""
        import m4b_preservation,m4b_repair
        from source_cleanup import single_stream
        from audio_jobs import REPAIR_WORKER_BUSY
        result={'requeued':False}
        if not m4b_repair.eligible(parent):return result|{'reason':'This book cannot be repaired.'}
        if not in_worker and self.jobs._thread and self.jobs._thread.is_alive():return result|{'reason':REPAIR_WORKER_BUSY}
```

**MS4b (no resume() from the worker thread)** — in `merge_service.py`, replace:
```python
        self.resume()
        return result|{'requeued':True,'job_id':child,'parent_job_id':parent['job_id'],'damage':diagnosis['damage'],'reason':'Repair admitted as new work'}
```
with:
```python
        if not in_worker:self.resume()
        return result|{'requeued':True,'job_id':child,'parent_job_id':parent['job_id'],'damage':diagnosis['damage'],'reason':'Repair admitted as new work'}
```

**MS5a (Retry click queues)** — in `merge_service.py`, replace:
```python
            result=self.retry_automatic_job(job_id,time.time())
            if not result.get('requeued'):raise RetryRefused(result.get('reason') or RETRY_WORKER_BUSY)
            return {'job_id':job_id,'requeued':True,'child_job_id':result.get('job_id'),'audiobook_jobs':self.state()}
```
with:
```python
            # Accepted at once, even while a book converts; it runs right after that book (m4b_readmission).
            result=self._request_m4b_readmission(job_id,'retry')
            return {'job_id':job_id,'requeued':False,**result,'audiobook_jobs':self.resume()}
```

**MS5b (Repair click queues)** — in `merge_service.py`, replace:
```python
        result=self.repair_damaged_m4b(job_id,time.time())
        if not result.get('requeued'):raise RetryRefused(result.get('reason') or 'Repair was not admitted.')
        return result|{'audiobook_jobs':self.state()}
```
with:
```python
        result=self._request_m4b_readmission(job_id,'repair')  # runs right after the current book
        return {'job_id':job_id,'requeued':False,**result,'audiobook_jobs':self.resume()}
```

**MS5c (Retry all queues)** — in `merge_service.py`, replace:
```python
                    return bool(self.retry_automatic_job(job_id,time.time(),resume=False).get('requeued'))
```
with:
```python
                    return bool(self._request_m4b_readmission(job_id,'retry').get('accepted'))
```

**MS6 (book status carries queued_next/position)** — in `merge_service.py`, replace:
```python
                value['attention']=attention
        repaired=repair_record(job)
```
with:
```python
                value['attention']=attention
        import m4b_readmission
        with self.jobs._db() as db:readmission=m4b_readmission.describe(db,job['job_id'])
        if readmission:value['readmission']=readmission  # queued_next + position, or the refusal reason
        repaired=repair_record(job)
```

**web/\* (his):**
- The Retry, Retry all and Repair responses carry `queued_next` and `position`. Show "Queued next (#n)" in the row and panel.
- After a refusal, show `readmission.reason`.
- Rows read `attention.readmission`; the book status reads `readmission`.
- Drop the worker-busy 409 path for M4B.
- Copy belongs to Judy.

**CHANGELOG (suggested):**
- "Retry and Repair now work while a book is being created: the book runs right after it."
- "Repair fills a cut-off final audio frame with silence of the same length, keeping every complete frame unchanged."
- "Books written by Audiobook Builder/QuickTime 7, Chapter and Verse, fre:ac (Nero) and iTunes-style taggers, very long books, and books without their own cover now keep their audio byte-for-byte."

## End-to-end re-check (scratch copies; Z: read-only; live 0.16.6 backend + all hunks; app's bundled ffmpeg 8.1.3)

Each source was copied from Z: (opened read-only) and its sha256 checked against the frozen manifest. Then the real `create_private()` ran:
- snapshot, hash proof and encoding;
- `plan` and stream;
- independent re-read;
- packet/decoder evidence;
- full PCM;
- chapters and tags.

The "cut final frames" rows are scratch copies truncated on purpose; no library book has that damage. Repair rows were bound from the parent row in the catalog.

**Correction:** round 1 of this harness ran WinGet ffmpeg 8.1.1, because an MSYS `PATH` entry `C:/…` split on its colon. Everything below was re-run on the bundled 8.1.3 except one pristine control.

| Book | Shape | Backend | Outcome | ffmpeg | Proof |
|---|---|---|---|---|---|
| Чудовищ.net | A (AUDIOKNIGA/iTunes) | fixed | **PASS** | 8.1.3 | PCM equal, 902,593,536 samples; 14 chapters |
| Чудовищ.net | Repair: cut final frames (100 B, scratch copy) | fixed | **PASS** | 8.1.3 | PCM equal, 902,593,536 samples; 14 chapters; truncated_final_frames (+100 B); 17 frames silenced, 902,576,128 intact samples identical |
| Гурман | N (Nero tags) | fixed | **PASS** | 8.1.3 | PCM equal, 1,472,439,296 samples; 13 chapters |
| Mass Effect: Revelation | Q (QuickTime 7) | fixed | **PASS** | 8.1.3 | PCM equal, 1,542,646,784 samples; 24 chapters |
| Закон фронтира | B (Chapter and Verse) | fixed | **PASS** | 8.1.3 | PCM equal, 2,107,646,976 samples; 3 chapters |
| Сборник рассказов | F (coverless) | orig | **REFUSED** | 8.1.3 | ValidationError: Preservation changed decoder, packets or presentation |
| Сборник рассказов | F (coverless) | fixed | **PASS** | 8.1.3 | PCM equal, 984,346,560 samples; 8 chapters |
| Сборник рассказов | Repair: cut final frames (10 B, scratch copy) | fixed | **PASS** | 8.1.3 | PCM equal, 984,346,560 samples; 8 chapters; truncated_final_frames (+10 B); 3 frames silenced, 984,343,488 intact samples identical |
| Storm of the Century | Repair: dangling chapter (+Q) | orig | **REFUSED** | 8.1.1 | ValidationError: M4B preservation requires review: Unsupported structural box |
| Storm of the Century | Repair: dangling chapter (+Q) | fixed | **PASS** | 8.1.3 | PCM equal, 1,042,130,944 samples; 21 chapters; dangling_chapter_reference |
| Призраки белых ночей | Repair: mdat tail overrun | orig | **REFUSED** | 8.1.3 | ValidationError: M4B preservation requires review: Top-level extent invalid |
| Призраки белых ночей | Repair: mdat tail overrun | fixed | **PASS** | 8.1.3 | PCM equal, 1,529,014,144 samples; 15 chapters; mdat_tail_overrun (+8 B) |
| Bird Box | Bird Box (REASONS) | fixed | **PASS** | 8.1.3 | PCM equal, 1,095,806,976 samples; 43 chapters |
| Алкоголь | Legacy remux (retry route) | fixed | **PASS** | 8.1.3 | PCM equal, 1,010,273,216 samples; 12 chapters |
| Пока все дома | Chunk cap (322,966 chunks; coverless) | fixed | **PASS** | 8.1.3 | PCM equal, 7,275,771,840 samples; 63 chapters |
| A Memory of Light | Chunk cap (307,392 chunks) | fixed | **PASS** | 8.1.3 | PCM equal, 2,518,149,056 samples; 51 chapters |

Results:
- All 13 runs on the fixed backend pass.
- The pristine controls refuse exactly as the live app does.
- Repaired-length checks:
  - Сборник рассказов cut by 10 bytes: 3 frames (0.070 s) are silenced, and the output is 984,346,560 samples, exactly the undamaged book's length.
  - Чудовищ.net cut by 100 bytes: 17 frames (0.544 s), 902,593,536 samples, again exactly undamaged.
- Not exercised here: publication, cleanup and recovery. Those are unchanged paths that run only after this verified result. The cleanup contract reads `source_pcm_frames`/`decoded_duration` from the same output PCM record.

# Part 2 — Investigation (read-only, earlier today)

## Answer

- **121 of the 123 M4B refusals can be supported safely without loosening any tolerance.** 2 should stay refused.
- **The biggest lever is not new format support.** 86 books (51 "Remux changed…" + 35 "leading gaps…") failed on 10-14/15 in the old ffmpeg-remux path, before v0.16.0 added byte-exact preservation. **80 of the 86 already pass today's `m4b_preservation.plan()` unchanged.** v0.16.0 also shipped a repair route for exactly these two reasons. These books are stuck only because nothing re-admits them.
- The 30 brand/structural refusals come from **4 writer families**, each needing 1–4 narrow, exact-shape allowances. Every one of them passes `plan()` once its allowances are in. None of the allowances touches audio-track bytes.
- The 5 "Preservation changed…" refusals are a **verifier false positive**: adding a cover to a coverless source adds an attached-picture stream, which shifts ffprobe's *movie-level* `start_time` by 2 µs. The audio evidence is identical.

| Fix | What | Books unlocked | Effort |
|---|---|---|---|
| **T** | Re-admit legacy failures through the **existing** repair route (trigger only) | 78 (+1 Bird Box with REASONS widened) | S |
| **F** | Movie-level evidence ignores the added cover stream | 5 + 2 coverless legacy (+1 with C) | S |
| **A** | AUDIOKNIGA/iTunes-style: zero brand, `alis` self-ref, text dref index 0 | 25 | S |
| **Q** | QuickTime 7 / Audiobook Builder: `free` in trak, big `stsc`, 52-byte text entry (+`alis`) | 6 | S |
| **N** | Nero `tags` box in `moov/udta` retained verbatim | 1 (+1 in A) | XS |
| **B** | Chapter and Verse 1.5 exact ftyp signature (`M4A\0`, `3gp5`) | 1 | XS |
| **C** | Raise `MAX_CHUNKS` 262,144 → 1,048,576 | 2 | XS (perf note) |
| — | Stay refused: Storm of the Century (dangling chapter ref), Призраки белых ночей (truncated mdat). *Superseded in Part 1: both are repairable with Repair.* | 0 | — |

**Size:** about 60–80 changed lines across `m4b_preservation.py` (A/Q/N/B/C, about 25 lines), `audio_pipeline.py` (F, about 15), `failed_m4b_retry.py` (REASONS, 2) and the trigger wiring (about 20–40, plus UI if it surfaces). Add 12–15 tests on the existing fixture builders. **About 1.5–2 Ender days**, then a full Senua review (the safety proof is touched) and a Futaba pass on one real book per group.

## Method (all read-only)

- Catalog opened as `file:…inventory.sqlite3?immutable=1`. The `-wal` was 0 bytes, so the snapshot is current.
- Sources on Z: were read for top-level box headers and the `moov` only, within the module's own 32 MiB read bound. No full reads or copies, and file sizes match the manifests.
- `m4b_preservation.py` was copied to scratch. Its sha256 `d68a37bb…c09ff2` is identical in the worktree and in all 9 `dist/builds/*` and 2 `build-cache` copies, so the live refusals came from this exact code. The scratch copy was instrumented to name the offending box, and each gate could be relaxed one at a time, so each file's **full refusal chain** was recorded, not just the first refusal.
- **Positive control:** the unrelaxed probe reproduced the catalog's exact reason for all 31 "requires review" jobs.
- Bundled `ffprobe` n8.1.3 was run header-only on samples. For the 5 post-preservation failures, the ffprobe stdout already stored in `working_diagnostics` was decoded; nothing was re-run.

---

## Group 1 — Legacy remux failures: 86 (51 "Remux changed the decoder configuration or relative audio packet timing" + 35 "M4B leading gaps or edit presentation require a verified preservation plan")

**Root cause:** every one of these jobs last ran on 2026-10-14/15 in copy mode through the old ffmpeg remux, before v0.16.0 (CHANGELOG: "Preserve supported AAC M4B media, chapters and presentation timing … avoiding a remux that changed otherwise valid books"). The remux genuinely changed packet timing or edit presentation, so the old refusals were correct. Today, `_encode_inputs` routes single AAC `.m4b` sources to byte-exact `_preserve_single_m4b`, which keeps edits and gaps verbatim.

**Today's `plan()` result on these sources:**

| Outcome | Count | Samples |
|---|---|---|
| Pass unchanged, source has cover | 78 | Алкоголь, Альтернативная история, The Talon of Horus, Black Legion, False Gods |
| Pass unchanged, **no cover** → would hit F | 2 | Пока все дома. Новогодняя серия; ТЁМНЫЕ АЛЛЕИ 2.1: Жестокость |
| Family A chain | 2 | Сборник фантастики. Рассказы; Тайная история человечества. Сборник |
| `stco` above `MAX_CHUNKS` (C) | 2 | Пока все дома (322,966 chunks; also coverless → F); A Memory of Light (307,392) |
| Family Q chain | 1 | О призраках безобидных… и не очень |
| **Stay refused** (*Part 1: repairable*) | 1 | Storm of the Century — audio `tref/chap` = `[3, 2]`, but track 2 does not exist |

**Why it is safe:** v0.16.0 already ships the admission route for exactly these two reasons: `failed_m4b_retry.REASONS`, used by `merge_service.retry_automatic_job` → `_retry_preserved_m4b`. That route requires a `plan()` profile proof and an identical frozen manifest, creates a new child job, and preserves the parent row. The preservation path has completed **45 books today** (2026-10-17 completed jobs carrying `metadata_preservation`). No job dir under `merge-cache/audio-staging` holds leftover attempt media for any of the 86, so the "prior working files" gate will not block.

**What blocks them:** that route is reached only when an automatic run visits a candidate in "Output needs attention". All 125 candidate ids are already in the live run's checkpoint `done` list (2,777 done). Their `automatic_candidates` rows are `Queued` with `attempted` dates of 10-13/15, and `audio_repair_admissions` has **0 rows**. The UI **Retry** (`retry_blocked_job` → `retry_admission_hold`) covers admission holds only.

**Fix T:** give these jobs a trigger into the existing `retry_automatic_job`. For example, route REASONS-eligible jobs from the Retry button there, or have a fresh automatic pass revisit "Output needs attention". How it surfaces is **Sergei's call** (and Judy's if visible). Risk: none new, since the code path and gates are unchanged. Effort: S.

## Group 2 — "M4B preservation requires review: Unsupported/ambiguous brand": 24

## Group 3 — "M4B preservation requires review: Unsupported structural box": 6

Every job, plus the one "Top-level extent invalid":

| # | Book | File | Exact reason | Brand / box | Group | Writer tag (©too/©enc) |
|---|---|---|---|---|---|---|
| 1 | Призраки белых ночей | Призраки белых ночей.m4b | Top-level extent invalid | mdat ends 8 B past EOF | X (refuse) | for AUDIOKNIGA.LIB & AUDIOKNIGA.ORG |
| 2 | Mass Effect: Retribution | Дрю Карпишин - Mass Effect - Книга 3 - Возмездие.m4b | Unsupported structural box | `moov/trak/free` (audio trak) | Q | для библиотеки WWW.AUDIOKNIGA.ORG (Ivanson) |
| 3 | Mass Effect: Revelation | Дрю Карпишин - Mass Effect - Книга 1 - Открытие.m4b | Unsupported structural box | `moov/trak/free` (audio trak) | Q | для библиотеки WWW.AUDIOKNIGA.ORG (Ivanson) |
| 4 | Восхождение | Дрю Карпишин - Mass Effect - Книга 2 - Восхождение.m4b | Unsupported structural box | `moov/trak/free` (audio trak) | Q | для библиотеки WWW.AUDIOKNIGA.ORG (Ivanson) |
| 5 | Выбраковка | Выбраковка.m4b | Unsupported structural box | `moov/trak/free` (audio trak) | Q | Audiobook Builder 1.5.3, QuickTime 7.7.3 |
| 6 | Гурман | Александр Варго - Гурман.m4b | Unsupported structural box | `moov/udta/tags` (Nero) | N | fre:ac v1.1.7 |
| 7 | Пищеблок | Пищеблок.m4b | Unsupported structural box | `moov/trak/free` (audio trak) | Q | Audiobook Builder 1.5.7, QuickTime 7.7.3 |
| 8 | Галерея последних портретов | Галерея последних портретов.m4b | Unsupported/ambiguous brand | major `M4B `, compat `M4B ` `mp42` `isom` `\0\0\0\0` | A | for AUDIOKNIGA.LIB & AUDIOKNIGA.ORG |
| 9 | Город засыпает | Город засыпает.m4b | Unsupported/ambiguous brand | same as #8 | A | for AUDIOKNIGA.LIB & AUDIOKNIGA.ORG |
| 10 | Город мёртвых отражений | Город мёртвых отражений.m4b | Unsupported/ambiguous brand | same as #8 | A | for AUDIOKNIGA.LIB & AUDIOKNIGA.ORG |
| 11 | Город теней | Алексей Атеев - Город теней.m4b | Unsupported/ambiguous brand | same as #8 | A+N | — |
| 12 | Добровольно проклятые | Добровольно проклятые.m4b | Unsupported/ambiguous brand | same as #8 | A | for AUDIOKNIGA.LIB & AUDIOKNIGA.ORG |
| 13 | Дом безликих теней | Дом безликих теней.m4b | Unsupported/ambiguous brand | same as #8 | A | for AUDIOKNIGA.LIB & AUDIOKNIGA.ORG |
| 14 | Дорогой несбывшихся снов | Дорогой несбывшихся снов.m4b | Unsupported/ambiguous brand | same as #8 | A | for AUDIOKNIGA.LIB & AUDIOKNIGA.ORG |
| 15 | Закон фронтира | Закон фронтира.m4b | Unsupported/ambiguous brand | major `M4A\0`, compat `3gp5` `isom` | B | Chapter and Verse V 1.5 |
| 16 | Иллюзии чистого холста | Иллюзии чистого холста.m4b | Unsupported/ambiguous brand | same as #8 | A | for AUDIOKNIGA.LIB & AUDIOKNIGA.ORG |
| 17 | Легенды древнего озера | Легенды древнего озера.m4b | Unsupported/ambiguous brand | same as #8 | A | for AUDIOKNIGA.LIB & AUDIOKNIGA.ORG |
| 18 | Лукавый морок | Лукавый морок.m4b | Unsupported/ambiguous brand | same as #8 | A | for AUDIOKNIGA.LIB & AUDIOKNIGA.ORG |
| 19 | Месть кровавого жнеца | Месть кровавого жнеца.m4b | Unsupported/ambiguous brand | same as #8 | A | for AUDIOKNIGA.LIB & AUDIOKNIGA.ORG |
| 20 | Мёртвым вход разрешён | Мёртвым вход разрешён.m4b | Unsupported/ambiguous brand | same as #8 | A | for AUDIOKNIGA.LIB & AUDIOKNIGA.ORG |
| 21 | Ненастоящие | Ненастоящие.m4b | Unsupported/ambiguous brand | same as #8 | A | for AUDIOKNIGA.LIB & AUDIOKNIGA.ORG |
| 22 | Нечто из Блэк Вудс | Нечто из Блэк Вудс.m4b | Unsupported/ambiguous brand | same as #8 | A | — |
| 23 | Нечто из Норт Ривер | Нечто из Норт Ривер.m4b | Unsupported/ambiguous brand | same as #8 | A | — |
| 24 | Проклятие пражской синагоги | Проклятие пражской синагоги.m4b | Unsupported/ambiguous brand | same as #8 | A | for AUDIOKNIGA.LIB & AUDIOKNIGA.ORG |
| 25 | Симбионты | Симбионты.m4b | Unsupported/ambiguous brand | same as #8 | A | — |
| 26 | Сотканная из тумана | Сотканная из тумана.m4b | Unsupported/ambiguous brand | same as #8 | A | for AUDIOKNIGA.LIB & AUDIOKNIGA.ORG |
| 27 | Тайна таёжной деревни | Тайна таёжной деревни.m4b | Unsupported/ambiguous brand | same as #8 | A | for AUDIOKNIGA.LIB & AUDIOKNIGA.ORG |
| 28 | Тишина старого кладбища | Тишина старого кладбища.m4b | Unsupported/ambiguous brand | same as #8 | A | for AUDIOKNIGA.LIB & AUDIOKNIGA.ORG |
| 29 | Хозяин гиблого места | Хозяин гиблого места.m4b | Unsupported/ambiguous brand | same as #8 | A | for AUDIOKNIGA.LIB & AUDIOKNIGA.ORG |
| 30 | Холод туманного замка | Холод туманного замка.m4b | Unsupported/ambiguous brand | same as #8 | A | for AUDIOKNIGA.LIB & AUDIOKNIGA.ORG |
| 31 | Чудовищ.net | Чудовищ.net.m4b | Unsupported/ambiguous brand | same as #8 | A | — |

Box positions (`ftyp moov free mdat` unless noted):
- A: `ftyp moov free mdat`.
- Q (Audiobook Builder): `ftyp moov wide mdat`.
- Q (Mass Effect ×3): `ftyp free wide mdat mdat moov`.
- B: `ftyp moov mdat`.

### Family A — AUDIOKNIGA / iTunes-style M4B (23 here + 2 in Group 1 = 25)

Each file hits three gates in a row. After all three, `plan()` passes (Город теней also needs N). Sample files: Чудовищ.net, Город теней, Симбионты.

1. **Zero compatible brand.** `ftyp` compat = `M4B ` `mp42` `isom` **`\0\0\0\0`**. This is a padding slot that iTunes-style writers emit, and it asserts nothing.
2. **`alis` data reference on the chapter text track.** The `dref` holds one entry, `alis` with version 0, flags `0x000001`, and **no alias record** (exact payload `00000001`). In QuickTime that means "media is in this file", the same meaning as `url ` with flags 1, which is already accepted. The audio track's `dref` is an ordinary `url `.
3. **Text sample entry `data_reference_index = 0`.** The bytes are `0000` where `0001` is required. With exactly one self-contained `dref` entry, which `dref()` already proves, index 0 can only resolve to "this file". ffmpeg falls back to the file itself here (`dref_id-1` underflows its bounds test).

**Fix:**
- Discard `\0\0\0\0` before the brand subset test. The major brand must still be one of `M4A `/`M4B `/`isom`/`mp42`.
- Accept `alis` only with the exact 4-byte payload `00000001` in a single-entry `dref`.
- Accept index 0 only on a `text` handler track, after `dref()` has proven the single self entry. Audio stays strictly at 1.

**Still refused:** an `alis` carrying an alias record, `url ` with flags 0, more than one entry, and index 0 on audio.

**Risk:** low. All three allowances apply to bytes that are retained verbatim, and none touches audio samples or offsets. **Effort:** S (about 10 lines; 3 refusal-boundary tests and 1 pass fixture built with the existing `add_chapter_graph` helper).

### Family Q — QuickTime 7 writers (5 here + 2 in Group 1)

Writers: Audiobook Builder 1.5.x with QuickTime 7.7.3, and the AUDIOKNIGA "Ivanson" releases. Sample files: Выбраковка, Пищеблок, Mass Effect: Revelation.

1. **`free` inside the audio `trak`**, 12 or 24 bytes, between `edts` and `tref`. ISO BMFF allows `free` at any level and every reader skips it. In Пищеблок it holds non-zero leftovers (a renamed box), which is still ignorable.
2. **`stsc` with 115k–183k rows**, well over the hard 4096 cap. The table is properly compacted (no redundant adjacent rows); chunk sizes simply alternate every chunk (for example 14, 10, 14, 7). The cap is a resource bound, not a correctness rule. The existing map check (first chunks strictly increasing and ≤ `nchunks`) already bounds the row count by the proven chunk count.
3. **`alis` self-reference on the text track** (same as A.2).
4. **Mass Effect ×3 only:** the text sample entry is **52 bytes**, the standard 51 plus one trailing `0x00` (an empty font-name Pascal string).

**Fix:**
- Allow `free`/`skip` in the `trak` profile only, which is where they were observed.
- Set the `stsc` maximum to `nchunks`.
- Accept a 52-byte text entry only when its last byte is `0x00`.

**Risk:** low. **Effort:** S. **Perf:** `plan()` on Пищеблок (182,637 `stsc` rows) took 20 s with a 116 MiB peak in the scratch probe. Downstream PCM hashing takes minutes, so this is not the bottleneck.

### Family N — Nero `tags` box in `moov/udta` (Гурман [fre:ac 1.1.7]; Город теней)

The 437 KB / 78 KB box holds `meta` (Nero key/value pairs: YEAR, TITLE, …) and `cvrx` (a second cover copy). ffprobe does not expose it: every format tag comes from `ilst`.

**Fix:** allow `tags` in the `udta` profile. It is then retained verbatim, as already happens for `chpl`, `©lyr` and freeform `----` items.

**Caveat:** its old title and cover stay stale for Nero-aware readers; Apple Books and ffmpeg ignore it. The alternative is to keep these 2 books refused, which is Sergei's call. **Effort:** XS.

### Family B — Chapter and Verse 1.5 (Закон фронтира)

Major brand `M4A\0` (NUL instead of space); compat `3gp5`, `isom`. Everything else passes as-is, including the JPEG chapter-image track.

**Fix:** allow this **exact** `ftyp` signature, not `3gp5` in general. `ftyp` is never rewritten, and the box structure is fully proven. **Effort:** XS.

### X — Призраки белых ночей: stay refused

*Superseded in Part 1. Measured later: no sample reaches past EOF, so the user-triggered `mdat_tail_overrun` repair completes the declared `mdat` with 8 zero bytes **before** the new `moov`, which removes the corruption risk described below.*


Layout is `ftyp moov wide mdat`, and the `mdat` header declares 266,456,689 B, ending **8 B past EOF**. Preservation appends the new `moov` at EOF, which would sit inside the declared `mdat` extent and produce a corrupt output. Options are normalize/re-encode or replace the source; that is Sergei's call.

## Group 4 — "Preservation changed decoder, packets or presentation": 5 (fix F)

Books: Сборник рассказов, Культ, Мухи, Клювы, Порча.

**Root cause, from the stored ffprobe outputs (`working_diagnostics`):**
- The audio-stream evidence is **identical**: codec, profile, rate, channels, layout, time base, extradata hash, `start_pts`, `duration_ts`, and packet timing.
- The only differences are at format level: `nb_streams` goes 2 → 3 and `format.start_time` goes 0.047891 → 0.047889.
- All 5 sources have **no embedded cover** (`ilst` has no `covr`). Preservation adds the approved cover as `covr`, and ffmpeg exposes it as an attached-picture stream.
- `format.start_time` is the minimum over all streams. Inferred mechanism: the audio starts at pts 2112/44100 (iTunes priming), and the new stream's start rounds down in a 1/90000 base to 4310/90000 = 0.047889, which is 2 µs earlier.

The audio did not change.

**Fix F:** in the `source_relative` branch of `copied_audio_evidence`, take the movie-level bounds from non-attached-picture streams. Alternatively, drop `format.start_time` from the movie evidence, because `plan()` plus `verify_candidate` already prove `mvhd` and every `trak` byte-identical. This adds no tolerance: the comparison stays exact and simply excludes the cover we added.

**Effort:** S (about 15 lines and 1 coverless test). These 5 also need a trigger: their reason is not in `REASONS` and their failure is `retryable: false`. Adding the reason is XS.

F also covers 3 coverless Group 1 books, all with the same signature (`start_pts` 2112 at 44100, 2 streams): Пока все дома. Новогодняя серия; ТЁМНЫЕ АЛЛЕИ 2.1: Жестокость; Пока все дома.

## Group 5 — "M4B presentation bounds cannot be verified": 1 (Bird Box)

This came from the old remux path's `_copy_presentation`, which the preservation path does not use (`source_relative=True`). `plan()` passes and the source has a cover. **Fix:** add the reason to `REASONS`, then the trigger T. Effort: XS.

## Not M4B (for completeness)

- Horus Rising ("database is locked"): `plan()` passes; a plain retry should work.
- The Lost Symbol (multi-source, out of working space): needs free working space.

## Recommendation

Order by books per effort:
1. **T** (+ `REASONS`: Bird Box, and "Preservation changed…" once F lands): 79 books.
2. **F**: 7 books.
3. **A**: 25 books.
4. **Q**: 6 books.
5. **N**: 1 book (Гурман; Город теней is counted under A but needs N too).
6. **B**: 1 book.
7. **C** is optional. In the probe, `plan()` on Пока все дома took 52 s with a 241 MiB peak, and A Memory of Light took 23 s with 114 MiB; 2 books.

Keep Storm of the Century and Призраки белых ночей refused.

**Caveats:**
- The PASS results come from scratch relaxations, which in places were **broader** than the fixes above (for example any text entry of 51+ bytes, and `free`/`tags` allowed at every level). The final code must be the narrow form and must be re-run against these files.
- The downstream gates (PCM hash, packet evidence, chapters, tag readback) were **not** run for the new families, because that needs full source reads. Futaba should do that on real books.

## Evidence (scratch)

All in `C:/Users/AnGeLZzZ/AppData/Local/Temp/claude/c--Antigravity-Projects-Studio-Illuminati/3c1cc2ef-43a9-4b2a-b1fa-8a242d8fded6/scratchpad/m4b/`:
- `na_jobs.json` (125 jobs)
- `na_trees.json` (124 box trees)
- `na_chains.json` (full refusal chains)
- `m4b_probe.py` (instrumented module copy)
- `iterprobe.py`, `boxdump.py`
