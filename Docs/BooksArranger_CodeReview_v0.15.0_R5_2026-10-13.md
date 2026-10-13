# Code Review — Books Arranger v0.15.0 round 5

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-13
Tool: Books Arranger
Release: v0.15.0
Commit range: d3c5526..95febcdd4f4de4ffb59a3507053c4eb86f53936a
Files changed: 18 files, +1279 / -20 (git diff --numstat)
Product: 5 files, +369 / -17; tests: 4 files, +353 / -1; docs: 9 files, +557 / -2
Critical correction: b9b1166..ea57e27; final fixture-only correction: ea57e27..95febcd
Stand-down dimensions: none; Electron absent from this delta
```

## Summary

Full cleanup-delta review now covers retirement-independent working disposal, explicit-resume retry, read-only scheduling hints, complete-stream exact job-wide PCM selection and actual concat proof, conservative staging/destination space admission and ENOSPC queue/controller parking. R3 covers earlier grouping/spelling through d3c5526; unchanged urgent helper/caller and actual A operation retain R4 clearance. R4 is not substituted for full release review. Product modules at 95febcd are byte-identical to ea57e27; the final commit changes only the private test wait and explanatory documentation.

R5-C1 is closed by the committed correction and actual independent reproduction/regression evidence. No open findings were introduced by the cleanup delta. Earlier R3 advisories remain outside this delta and are not silently resolved here. This report certifies code construction and private evidence; it does not claim v0.15.0 was applied, launched, resumed, or accepted against live-library conversions. B stream/original-retirement changes are excluded; native/source/publication and 24-hour safeguards remain unchanged.

## Closed Critical — R5-C1

At b9b1166, each source chose its own PCM codec. The unchanged concat demuxer interpreted later packets using the first codec configuration. An actual private s32/f32 fixture produced a wrong full PCM hash with identical 4800 samples and 38400 canonical-double bytes; duration-only downstream checks could miss corruption before source retirement. Original immutable evidence is retained in scratch/senua-cleanup-2026-10-13/mixed-concat-b9b/repro.json and mixed-concat-log.txt.

The corrected path proves every held original source against ONE smallest exact job-wide codec, emits one WAV per source in that shared configuration and verifies each complete PCM stream. It independently accumulates the expected ordered aggregate from ORIGINAL source normalization streams, then checks the ACTUAL concat-demuxer full canonical PCM hash/count before AAC while native source/normalized/plan leases stay held. The validation record retains normalized_joined_pcm and normalized_pcm_codec.

Senua's original reproduction rerun on immutable ea57e27 selected f64 for both sources and matched the original expected SHA-256 c559503841bc75b185ad64dc2e6eeea557c4ecb11e56e984b2b795b599023fc1, all 4800 samples and 38400 bytes. Evidence: mixed-concat-ea57/repro.json and mixed-concat-fixed-log.txt. Actual mixed s32/f32 and s16/s24 regressions in BOTH orders, complete create_private verification against independently expanded original samples, and refusal of a truncated concat plan before checked.m4b creation passed. Product bytes are unchanged at final 95febcd.

## Method and exact acceptance evidence

- Read complete committed product/test/doc changes across the certified range and the relevant unchanged native/source/publication/recovery/Ready/queue/controller consumers. Literal tracked-source searches cover joined_pcm, verify_normalized_concat, normalized_joined_pcm and normalized_pcm_codec. Additional validation evidence is optional to unchanged AudioJobs._validate_record and CleanupJobs._validation_contract; earlier completed records remain compatible. Native/source/retention modules and protected-plan checkout policy have no delta in this range.
- Independently archived and hashed final 95febcd: all 231 tracked-file proofs exactly match the frozen source map; source digest a1c78bd624bbd1fe8ea5e7c3761fbd2e387228bed97a9e6d0d97f6ee1911ad1b. Context bd3d8fdd256e62e196267f5482a3a80101ceac31e98194de7edcb332b347f1a1; full_owned.py 438958235e978f6786108db0c94e9631ed2185fea674d4786fa46e4b6f36cdc3; full_inner.py af071e334c90817104a29c0473c5029da86ad975fe4c73f38e738e7f7d6986c2. Pinned Python, Bash, FFmpeg and FFprobe hashes were independently checked by the route.
- Separately reviewed manual route: fixed reparse-rejected owned scratch/qa015 parent, fresh UUID private source copy, explicit missing private fixture-parent creation, CREATE_SUSPENDED isolated child, existing OwnedProcessJob, 550-second child/600-second caller envelope, complete immutable source/runtime/harness and copied tracked-file checks before/after. This is a separately reviewed manual contract, not an automated package qa-handoff receipt. No live app, data, Z:/Y:, external media or desktop action is executed.
- Graph counts are fully qualified unittest case IDs, not assertions or subcases: working cleanup 16; precision 20; lifecycle 4; storage cleanup 18; automatic media policy 15; automatic media 9; standing admission 6; total 88. Fixtures cover integer sign/low bits/widths/endian expansion, signed zero/subnormals/NaN payloads/infinity, incomplete chunks/frames, resampling/channels, existing AAC/ALAC/multichannel M4B preservation, source snapshots/24-hour recovery, producer/native identity refusal, actual joined PCM, disk holds and Ready/source-retirement independence.
- Final sender actual receipt full-receipt-r-919a7b81616f4efe8d5f02dcf789e28a.json independently read and SHA-256 verified c574fb07736206fd6e2f9acc8b3d7c94a5e5db78788742679ba59d6f769d08be. Log full-log-r-919a7b81616f4efe8d5f02dcf789e28a.txt SHA-256 6732fa1b501d4fbe7f85ccc049397cc5331fe81529d42231605dfcff07d2955d: 88 actual ok lines, zero skips/errors/failures, 287.560 seconds tests; receipt owned elapsed 288.724 seconds.
- Independent Futaba receiver: `full-receipt-r-398ee93b11224c1fb12452ecf5233cc0.json`, SHA-256 `c232cf4a1d6ad6d37e195bfe9c07ad3f8620048305ffe594bc8c39aca3cf7d39`; `full-log-r-398ee93b11224c1fb12452ecf5233cc0.txt`, SHA-256 `e850aaaa09f595b05309f67470fc585c9fcc1f064471a5130d9c9742f311629c`. Independently read receipt and complete log: 88 actual test IDs PASS, zero errors, failures or skips; tests 287.575 seconds, owned receipt 288.619 seconds. Run followed the successful sender sequentially. Candidate HEAD, source map/digest, runtime, frozen context, runner, inner driver and graph match the sender; post-run context hash remains unchanged.
- Senua independently executed final six focused cases after the fixture correction: 6/6 PASS, tests 50.032 seconds, owned 51.107 seconds. Exact diagnostic context dc8494bbec5997ecb972ac5d46412a773eb63af7525276510a98aef087667cbf; owned runner 1e88466015cd4f63135b217953d539950825639d4ea37e4af62bc8157ddf696c; inner d6bf4f87ec4f9db9b1375098fbfcfbb0702925df8c4be0e9448fb844cc09ca66. Evidence diagnostic-log-r-c7eaf85ed9744a62a64ede9688346e8e.txt/receipt. These are focused independent cases, not another claimed full-88 run.

## Preserved failed-run history and fixture correction

Senua's first ea57 full graph produced 73 passes/15 path-limit errors from an overly deep private UUID copy. The shorter-path run produced 82 passes/3 missing fixture-parent errors/3 intermittent readiness assertions. Six-case diagnostics captured a failed unknown-file injection assertion while the actual audio worker was still Running, source retirement had completed and full storage/folder receipts had not yet been created. The old wait helper queried three separate state snapshots and could exit across enrollment/postprocessing transitions; its mock scope ended too soon. Final 95febcd uses one snapshot and requires both real audio/source-cleanup workers inactive, retaining the original 30-second test deadline. The runner prepares the private archive-excluded fixture directory. Product path/Ready/safety guards were not changed. All failed logs/receipts and the b9 Critical reproduction remain preserved; they are not relabelled as passing acceptance. No extra product fixes or duplicate full Senua run were needed after the narrow fixture correction.

## Rubric

Severity and safety floor follow Team/Docs/ProcessRules.md § Severity definitions.

### 1. Security

- Status: Pass. Argument-list owned subprocesses, finite bounded telemetry, native ancestry/file leases and exact producer receipt/stream/link checks prevent shell/path-delete expansion; no credentials or Electron security changes.

### 2. Correctness & Logic

- Status: Pass. Shared job-wide codec plus original-source aggregate versus actual concat hash/count closes R5-C1; cancellation/malformed/precision proofs and producer correspondence fail closed.

### 3. Crash / Stability Safety

- Status: Pass. Partial dispositions reconcile only durable exact intent; ENOSPC records failure and parks the remaining queue/controller; explicit resume retries pending working receipts while construction remains inactive.

### 4. Performance

- Status: Pass. PCM/concat proofs stream bounded chunks; already disposed names avoid repeated media hashes; full-book throughput is unmeasured and no speedup is claimed.

### 5. State & Data Safety

- Status: Pass. Publication-gated working cleanup precedes retirement without completing full storage/Ready/folder obligations, removing snapshots/recovery, resetting audio success or weakening native/source/publication/24-hour checks.

### 6. Input Handling

- Status: Pass. Complete source hash/profile/duration admission, smallest common exact PCM proofs, finite positive space estimates and initial/midstage/destination checks retain original evidence on unsupported/changed/short-space input.

### 7. Maintainability

- Status: Pass. Existing native/CAS cleanup is reused; scheduling hints remain separate from authorization; corrected mixed-format integration and truthful worker fences cover the affected boundaries.

### 8. Doc/Code Drift

- Status: Pass. Action-to-cleanup map, exact urgent inventory, scope exclusions, Critical closure and fixture failure causes match committed behavior; old failed evidence remains auditable.

### 9. Build & Release Hygiene

- Status: Pass. Final source/test/context/runtime and finite manual graph match actual sender/receiver evidence; VERSION is 0.15.0; stopped-app Git fast-forward preserves the tracked LF protected plan and excludes the obsolete copy/normalization route.

## Verdict

- Total open Critical: 0
- Total open Major: 0
- Total open Minor: 0

**Verdict:** RELEASE CLEAR

The prior b9 result is superseded only for the corrected certified range. Existing R3 advisories are unchanged outside this delta. Release/application still belong to Sully; this report grants no live source retirement, app launch or automatic Start.
