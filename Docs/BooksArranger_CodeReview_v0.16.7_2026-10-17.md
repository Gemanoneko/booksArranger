# Code Review — Books Arranger v0.16.7

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-10-17
Tool: Books Arranger
Release: v0.16.7
Status: FINAL; lean red-team pass focused on data safety (brief items 1-5); dimensions 4, 7 and 8 read lightly
Commit range: 56c7532221f42b755ed4c30080d2dae790fa28ac..0e95a41494963a37aa9e9607a40bfc7b9a2479a1
  56c7532 = v0.16.6 tag (its report cleared 9e1664ff..7619d12; 56c7532 is docs only)
  c654593 feat: M4B support, repair, retry-next and bounded working space
  0e95a41 chore: release v0.16.7 (package.json, package-lock.json, CHANGELOG in one commit)
Files changed: 34 files, +3593 / -348 (code only, excluding Docs/ and tests/: 21 files, +1630 / -266)
Stand-down dimensions: none
Release source commit: 0e95a41494963a37aa9e9607a40bfc7b9a2479a1
Release artifact manifest SHA256: 5a53f11e158b41b325e2e37911cd74cf67323f49d2091fd865b678d2a0635f8a
Release installer: dist/builds/d6836509-e229-4cf7-94e2-c26f7b7d8fe1/Books-Arranger-Setup-0.16.7.exe
Release installer SHA256: 8514d776223b0ffc9081c5fe9cb0fcf0ea272f73ac9a06e6d715bd377095c3a2
```

## Summary

v0.16.7 adds four things: exact writer-family allowances in `m4b_preservation`, user-pressed damage repair (`m4b_repair`, `plan(repair=...)`), a "runs next" re-admission ledger for M4B Retry/Repair (`m4b_readmission`), and Retry for busy-catalog and full-disk failures. It also streams normalized audio straight into the encoder, with no WAV intermediate. I read every code hunk in the range and the CHANGELOG. From `Docs/BooksArranger_M4B_UnsupportedBrands_Report_2026-10-17.md` I read Part 1 and the end-to-end table.

Evidence I gathered myself:
- The installer hashes to the SHA256 above. `dist/release-artifacts.json` hashes to the manifest SHA256 above and names `source_head` 0e95a41.
- All 47 packaged `resources/backend/*.py` files are byte-identical to the worktree checkout at HEAD, and their content equals HEAD (the only difference is CRLF from autocrlf). The 4 changed `web/` files are identical too.
- Six focused suites (m4b_preservation, attention_repair, failed_m4b_retry, attention_actions, blocked_retry, working_precision) ran 155 cases with the build-cache ffmpeg: all green, 0 skipped.

## Release questions (data safety)

1. **M4B allowances: narrow, still byte-proven, chunk cap bounded. Yes.**
   - Every allowance only relaxes a parse or profile gate:
     - the zero brand is dropped from the brand set, and the major brand must still be in `MAJOR_BRANDS`;
     - `EXACT_FTYP` is one whole payload;
     - `alis` is accepted only with payload `00000001`, and only on `text`;
     - data-reference index 0 is accepted on `text` only;
     - a 52-byte text entry is accepted only with a trailing 0;
     - `free`/`skip` are allowed directly in `trak`;
     - Nero `tags` is accepted only with children `{meta, cvrx, tseg}` and is kept verbatim.
   - The proofs are unchanged:
     - `verify_candidate` re-reads every source byte (`m4b_preservation.py:523`);
     - whole-`trak` byte equality (`:481`);
     - on the non-repair path, full decoder/packet evidence and full native PCM equality.
   - The coverless fix narrows only the movie `start_time` input to non-attached-picture streams, on the `source_relative` branch only. PCM equality still follows.
   - `MAX_CHUNKS=524288` (`:22`) is bounded three ways: by the global `remaining_chunks` budget, by `table()` extent checks inside `MAX_MOOV` (32 MiB), and by the unchanged `MAX_SAMPLES` per-sample loop. The `stsc` cap of `nchunks` is bounded by the same count.
2. **Repair: narrow, proven, never writes originals. Yes.**
   - **Overrun shape.** An overrun is accepted only on the final top-level `mdat`, with its header present (`:419`). The tail-overrun path never lets a chunk end past EOF.
   - **Silence bounds and frame proof.**
     - Silence requires the cut samples to be exactly the last `k` audio samples by index (`:273`), at most 1 s by `stts` ticks (`:283`), with the file at most 64 KiB short.
     - The frames must be plain AAC-LC mono/stereo with 1024-sample frames, and no chapter sample may be cut.
     - All timing tables stay byte-identical, and intact sizes, offsets and chunk counts are compared.
     - The repaired `trak` is re-validated against the new `mdat` extent.
   - **Byte proof.** The zero padding and the silent frames are re-read exactly (`:527`, `:531`).
   - **Decode proof (`m4b_repair.py:166-213`).**
     - Intact packet timing must be identical.
     - Source damage must equal the approved damage.
     - The output decodes strictly, with `-xerror`.
     - The output PCM prefix must equal the lenient intact-source PCM (`:207`), and the samples after the overlap slot must be exactly 0.0 (`:208`).
   - **Dangling chapter.** Only absent IDs are dropped. It needs exactly one `chap` box, and every other `trak` child stays byte-identical (`m4b_preservation.py:320`, `:462`).
   - **Approval binding.** `confirm()` requires applied == approved, kinds and facts.
   - **Read-only originals.** Detection opens the source `rb` (`m4b_repair.py:47`). The candidate is written only to the stage. Verification completes inside `_preserve_single_m4b` before the output is returned, so publication and cleanup come after it.
   - **Recoverability.** Every byte of the damaged source survives in the output at its original offset, apart from the 4-byte `moov`→`free` type patch. Cleanup removing that original therefore loses nothing.
3. **Streaming decode→encode: still a complete-audio proof. Yes.**
   - `stream_normalized` checks every fed byte. Each track must match its own reference (`audio_pipeline.py:576`), and the whole stream must match the joined proof (`:577`).
   - Both checks run inside the encoder's `owned_stream` body, and stdin is closed only after the body returns (`:236`). So any mismatch, decoder failure, Pause or deadline kills the encoder before it gets a clean EOF.
   - The decode arguments are identical to the reference pass. The filter forces the encode rate and layout, so the raw `-ar`/`-ac` reading matches.
   - After the encode, `validate()` and its duration/decoded-sample checks are unchanged.
   - A failed stream leaves a partial `checked.m4b` (`-n`, planned-generated) and small `.stderr` files in the attempt stage. Working-lifecycle disposal handles them, and they block M4B re-admission until they are disposed. Originals are untouched.
4. **Re-admission: one child per parent, no double admission. Yes.**
   - `request()` assigns `seq` under `BEGIN IMMEDIATE`. It is idempotent while queued, and re-queues at the back after a refusal.
   - The hook runs in the worker thread between books, with no `operation_lock` held.
   - Admission goes through the unchanged CAS in `enqueue`, which holds `jobs._lock` with `BEGIN IMMEDIATE`. It requires:
     - an identical parent row;
     - the parent to be the newest job for the book;
     - unchanged `book_groups` and `candidate_context`;
     - a binding to the parent's manifest hash;
     - an `audio_repair_admissions` insert.
   - So a concurrent automatic retry, Retry all, or a second click cannot admit twice.
   - Repair children and retry children are outside both eligibility rules, so there is no repair of a repair. The `_ORDER` precedence is correct.
   - Liveness has a gap: see F1.
5. **Busy/space Retry: safe. Yes.**
   - `failure_cause` is typed (`sqlite_errorcode`, `errno`), and only two exact legacy shapes are accepted.
   - `_retry_shape` still refuses anything with `publication_intent`, any replacement or repair child, superseded jobs, and an E7 history mismatch.
   - E8 (working files absent) and the space check are re-run when Retry is pressed.
   - The worker's own `check_working_space` still applies the exact requirement before any copy.

## Rubric

### 1. Security

- Status: Pass
- Findings: none.
  - The new routes (`/api/audiobook/repair`, `/api/audiobook/retry-all`) sit in the existing trusted control path with `shape()` and `uuid_value()` checks. The `group` query value is whitelisted.
  - Media commands are argument lists with `shell=False` and protocol/format whitelists (`pipe` + `f64le` for the encoder feed).
  - New UI text goes through `textContent` and `node()`. There are no new `innerHTML` sinks.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - `audio_pipeline.py:848` [Minor] `m4b_repair.confirm()` is enforced only inside `_preserve_single_m4b`. If a manifest carrying the damage-repair binding were routed to the remux or transcode path (for example a legacy-profile job), it would run without its approved repair, and `repair_record` would show it as approved but not applied. Today the reachable set is close to empty: `plan()` refuses non-`mp4a`, and the manual profile refuses non-MP3. Refusing a damage-repair manifest outside the preservation path would make this a rule.
  - `m4b_readmission.py:76-87` [Minor] The child enqueue and the ledger update are two transactions. A crash between them makes the next admission refuse with "Candidate already has newer work", so the ledger shows a refusal while the child runs normally. This is cosmetic; there is no double admission.

### 3. Crash / Stability Safety

- Status: Concerns
- Findings:
  - **F1** `m4b_readmission.py:72-87`, `audio_jobs.py:718`, `audio_jobs.py:775` [Major] The readmission hook does admission proof work in the worker thread: `build_manifest`, then `plan()` once or twice (the report measures up to 53 s each on the largest books). One call loops through every refusal. Neither `_stop` (Pause) nor `_drain` (Quit) is checked, and before starting the runner the worker re-checks only `_stop`. A Quit pressed while the hook runs therefore starts and finishes a whole new book before the app can exit, and a Pause waits for the whole hook. There is no data risk, because journaling and publication are unchanged. Fix: check `_stop` and `_drain` in the `next_job` loop and again before the runner, and pass the jobs stop into the admission reads.
  - `m4b_readmission.py:80`, `audio_jobs.py:721` [Minor] A `defer` (a scan is running) with an empty normal queue makes the worker exit, and the queued request waits for the next `resume()`. The same happens when a click lands while an exiting worker is still alive. Pressing Retry or Repair again recovers it.
  - `audio_pipeline.py:254-257` (raised from `:574`) [Minor] When the encoder dies mid-stream (for example a full disk on the stage drive), the failed pipe write surfaces in the decoder's `owned_stream`. That context reports the decoder's empty stderr ("Media operation failed"), and the outer context re-raises it. The encoder's real diagnostic is lost, so the row shows "Stopped — see details" instead of the cause. This is diagnostic only; nothing is published.

### 4. Performance

- Status: Concerns
- Findings:
  - `merge_service.py:694` [Minor] Every status poll queues repair checks for unchecked eligible M4B rows. Each check runs `plan()` twice on a background Python thread. The CPU phase has no stop check, so on the largest books it holds the GIL for about a minute while a conversion's feed loop runs, and `close()` waits up to 30 s for it. The checks are bounded, cached, and run once per row per session.

### 5. State & Data Safety

- Status: Pass
- Findings: none. Release questions 1-5 above cover this; nothing found writes, moves or deletes an original before a verified output exists.

### 6. Input Handling

- Status: Pass
- Findings: none.
  - Box parsing stays inside the existing read and box bounds: `MAX_MOOV`, `MAX_BOXES`, the descriptor-length loop capped at 4 bytes, and `need()` on every `esds` offset.
  - `_Packets` caps a partial line at 4 KiB, and `_Pcm` handles partial samples with a carry.

### 7. Maintainability

- Status: Concerns
- Findings:
  - `audio_pipeline.py:501-526` [Minor] `ExpandedPcmHash` and the `kind` branch of `normalized_pcm_evidence` are dead code now that the format search is gone.

### 8. Doc/Code Drift

- Status: Concerns
- Findings:
  - `m4b_preservation.py:500` [Minor] The receipt's `track_sha256` lists the source `trak` hashes even when a repaired `trak` was written. The silence repair records no hash of its repaired `trak`, while the dangling repair records `repaired_trak_sha256`. Nothing reads the field today.
  - `CHANGELOG.md` v0.16.7 [Minor] It says the working space needed is "about twice the size of the book's source files". The gate is source + 3 × output + 64 MiB, and `output_space_required` is at least the source size, so that is about 4× the source for a transcode. The Retry space check uses 6×. The measured peak in the same entry is correct.

### 9. Build & Release Hygiene

- Status: Pass
- Findings: none.
  - The version bump and lockfile are in the same commit (0e95a41).
  - The installer and manifest hashes match the brief, and `source_head` = 0e95a41.
  - The packaged backend matches HEAD, and the new modules `m4b_repair.py` and `m4b_readmission.py` are packaged.
  - `check-desktop.mjs` adds the new suites to the gate.

## Patterns

Proof rigor stays high and every relaxation is exact. The recurring weak spot is the same as in v0.16.6: work done between books, or alongside them, that does not observe Pause or Quit (F1). That is liveness, not data.

## Verdict

- Total Critical: 0
- Total Major: 1
- Total Minor: 8

**Verdict:** RELEASE CLEAR
