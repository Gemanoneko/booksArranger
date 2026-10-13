# Code Review — Books Arranger v0.15.0 round 5

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-13
Tool: Books Arranger
Release: v0.15.0 candidate
Commit range: d3c5526..b9b1166492b40e22fe9dc1a01607b57d5c065467
Files changed: 15 files, +1038 / -14 (git diff --numstat)
Full cleanup implementation round: 6b46136..b9b1166; 8 files, +385 / -12
Stand-down dimensions: none; Electron absent from this delta
```

## Summary

The full cleanup candidate adds retirement-independent published working cleanup, explicit-resume retry, read-only scheduling hints, ENOSPC queue/controller holds, conservative staging/destination admission and exact adaptive PCM precision proofs. The urgent helper/caller and actual A operation remain certified by the separate R4 report against unchanged code. R3 covers earlier grouping/spelling through d3c5526. Source cleanup, native I/O, publication correspondence and the 24-hour policy are unchanged.

Red-team review found a Critical format-boundary defect: independently choosing each normalized WAV codec feeds different codecs into a concat demuxer using the first input's codec configuration. Equal-width integer/float inputs corrupt audio while preserving sample count and duration. Per-file proofs do not prove the complete concat input stream; lossy final validation can miss this before original retirement. This candidate is blocked. Ender is implementing a correction; no uncommitted correction is certified here.

## Method and evidence

Read the complete committed product/test/doc delta and relevant unchanged source/native/publication/queue/controller/Ready boundaries. Independently archived b9b1166 under scratch/senua-cleanup-2026-10-13/pin-b9b1166. Reviewed full_owned.py/full_inner.py finite private-only route: suspended isolated child, existing OwnedProcessJob, 550-second child envelope, pre/post source/runtime/harness and copied tracked-file checks. The pinned seven-suite shared graph has 84 AST-defined test methods; it was deliberately not executed for acceptance after the independently reproduced Critical was found.

A small reviewer-owned private child exercised actual normalized files and the actual FFmpeg concat demuxer on immutable b9b1166. No app, live data, Z:/Y:, original retirement or mutable candidate execution occurred. Evidence: scratch/senua-cleanup-2026-10-13/mixed-concat-b9b/repro.json and mixed-concat-log.txt; own probe source mixed_concat_probe.py and suspended-child supervisor mixed_concat_owned.py. The fixture chooses pcm_s32le for integer low-bit samples and pcm_f32le for float signed zero/subnormal samples. It checks the independently decoded full joined PCM reference against concat decoding:

- Expected SHA-256: c559503841bc75b185ad64dc2e6eeea557c4ecb11e56e984b2b795b599023fc1.
- Actual concat SHA-256: a8b0855893f5ed02fe9bd2b69e0121324655b03ba7a7fddf604b115e045cf4d4.
- Both proofs contain 4800 samples and 38400 canonical double bytes.

Prior R4's urgent operational tests/evidence are reused only for matching unchanged helper/caller code. This report does not duplicate that actual operation or count its private tests as newly executed full-delta tests.

## Rubric

Severity and safety floor follow Team/Docs/ProcessRules.md § Severity definitions.

### 1. Security

- Status: Pass. No new shell execution or pathname-delete bypass; producer receipt/native deletion checks remain unchanged, as do original stream/link/reparse guards.

### 2. Correctness & Logic

- Status: Fail.
- **[Critical] R5-C1 — mixed PCM codecs corrupt the concat stream without changing sample count.** audio_pipeline.py:379 selects a codec per source; :536 supplies all normalized WAVs to the unchanged concat demuxer. Actual equal-width s32/f32 fixture above proves a different full decoded PCM hash with identical count/duration. Choose one exact codec compatible with the whole job, prove every source against that choice and prove the actual joined concat stream before encoding; add mixed codecs/widths in both orders.

### 3. Crash / Stability Safety

- Status: Pass. ENOSPC durably records failure and parks the remaining queue; the callback uses existing stop(force=True) without joining the current audio thread; per-file cleanup intents remain resumable.

### 4. Performance

- Status: Pass. Proofs stream bounded chunks and disk estimates retain worst-case f64/output reservations; full-book throughput is not measured and acceptance must not imply a measured speedup.

### 5. State & Data Safety

- Status: Fail. R5-C1 can feed wrong decoded samples into a valid-duration final audiobook before unchanged source retirement runs. Working-only cleanup itself preserves snapshots/recovery and never grants full storage/Ready/folder obligations.

### 6. Input Handling

- Status: Pass. Endian-aware expansion and final frame/count guards, complete source hashes/profiles/durations, conservative admission and unchanged destination/source ancestry checks fail closed; R5-C1 is the cross-input configuration failure recorded above.

### 7. Maintainability

- Status: Pass. Cleanup reuses existing native/CAS primitives and read-only pending hints; mixed-codec integration coverage must accompany R5-C1's fix.

### 8. Doc/Code Drift

- Status: Pass. Scope, action-to-cleanup map, source preservation, explicit resume and stopped-app apply constraints are documented. The defect in the promised complete-source verification is recorded under correctness/data safety.

### 9. Build & Release Hygiene

- Status: Pass. Candidate pin is committed/pushed; VERSION remains 0.15.0; full source/runtime/manual graph is pinned and finite. No release or live apply is cleared while R5-C1 is open.

## Verdict

- Total Critical: 1
- Total Major: 0
- Total Minor: 0

**Verdict:** RELEASE BLOCKED

| # | Sev | Dim | file:line | Finding | Must fix before release |
|---|-----|-----|-----------|---------|--------------------------|
| R5-C1 | Critical | 2 Correctness / 5 Data | audio_pipeline.py:379; :536 | Per-source PCM format choice breaks concat decoding; equal-width s32/f32 corrupt audio with unchanged sample count. | Use one fully proven job-wide compatible codec and prove the actual joined concat PCM stream; mixed-codec/width/order tests and independent corrected-pin QA/review. |
