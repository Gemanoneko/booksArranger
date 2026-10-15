# Books Arranger attention jobs — 2026-10-15

Owner: Ender. User authorized diagnosing held working files and fixing what is safe so conversion can finish and space can be released. This is a **source-only, untested maintenance checkpoint**. No installed code, live job/recovery state, originals, shared safety configuration or Electron candidate was changed.

## Current blocking groups and method

A separately reviewed, bounded query-only SQLite observer retained exact v0.15.0 owner PID 54960, creation FILETIME 134365295749473510 and instance 721b890bb723a4b3d22fffb3edf35f1c. It checked canonical source pins/native read handles and used a 45-second hard deadline, one-second busy timeout, query progress deadline and bounded rows/output. Query results are non-atomic observations while the app works.

The first query at 09:33:59 UTC exited 0 but its terminal result was truncated. No complete counts are inferred from it. A separately reviewed compact output query at **09:35:02.198698 UTC / 12:35:02 Jerusalem** exited 0 and retained exact group IDs/counts in canonical scratch/resume-2026-10-15/attention-groups-20261015.json:

| Exact recorded reason | Jobs | Stage | Classified retryable |
| --- | ---: | --- | --- |
| Remux changed the decoder configuration or relative audio packet timing | 50 | checking | false |
| M4B leading gaps or edit presentation require a verified preservation plan | 30 | checking | false |
| M4B presentation bounds cannot be verified | 1 | checking | false |
| database is locked | 1 | checking sources | false |

All 82 have no saved output or publication intent and match their frozen manifest hashes. The original 80 jobs owning 61.13 GB of generated pairs comprise 50 comparison holds, 29 gap/presentation holds and one bounds hold. The restarted job a0030d08-ff99-42c2-9aca-e58be379f179 added the thirtieth presentation hold; the database-lock job d9433878-5819-4e1a-a465-cd7377d2ff90 is separate. Counts then were 22 completed, 82 attention, seven pending and one running. Do not conflate these with ten completed books whose original cleanup is stream-held; those protect a different 4.32 GB snapshot set.

The broad comparison message compares the entire copied_audio_evidence dictionary, including presentation. It does not prove decoder configuration or packet timing changed. No blind retry is appropriate: every stored failure says retryable false, and the shipped receiver refuses those records.

## Actual retained and native metadata evidence

Existing bounded ordinary .stdout JSON receipts were examined for three representative failed attempts. A separately reviewed metadata-only native observer then read nine exact local source/checked/compatible files, only top-level atom headers and bounded moov metadata. It held ordinary ancestry and native file identities against write/replacement, verified expected sizes and exact live owner/generation, had no children or writes and read no mdat payload or real source-library paths. Full exit-0 result at 09:40:06.709555 UTC is preserved as canonical scratch/resume-2026-10-15/mp4-metadata-20261015.json. This establishes header facts, not whole-file hashes, audio equivalence or disposal eligibility.

- Gap representative 07d89b9c-ff57-445d-88f9-3a44c844470a: retained source probe starts at 2112/44100 seconds. Source movie clock 44100 and duration 1697128448, with no audio edit list. Generated movie clock is 1000 with duration 38483591 and a new audio edit starting at media_time 2112. Audio mdhd/sample timing table remains 44100 / 1697128448 and 1657352 packets of 1024 ticks. The generated container changes presentation; suppressing the guard would be unsafe.
- Comparison representative 139b3941-bfa4-4199-ab4e-8380a97dbd70: source movie/audio-edit duration is 14562226/600 seconds; generated is 24270378/1000 seconds. The difference is exactly 1/750 second, or 58.8 decoded samples at 44100 Hz. Both retain audio media_time 2112 and the same mdhd and stts tables. Retained decoder/extradata fields match. The remux changed movie/edit presentation even with unchanged sample table; matching payload alone cannot authorize it. The subsequent chapter-format transform retains the already altered checked-file clocks.
- Bounds representative f96f5926-74d0-4f77-8a20-7a427a4fa404: source HE-AAC output sample rate is 44100 but audio clock is 22050. The old assumption time_base == 1/sample_rate is invalid for this legitimate clock. The generated container also changes the clock to 44100 and changes its sample table from 535065 packets of 1024 ticks to 535062 packets of 2048 ticks. Decoder/demux trim semantics and full PCM must still be proved; fixing rational conversion alone does not clear this actual output.

These observations explain representative failure mechanisms, not a newly measured root cause for every member of each group. No tolerance was enlarged and no edit/gap or alternate stream was discarded.

## Narrow source checkpoint

Sully created the isolated worktree canonical scratch/resume-2026-10-15/maintenance-worktree, branch codex/books-attention-fixes, exact clean canonical-main base **ef04a26482895948bad9213e0c64d12b73c49fcf**. The installed canonical main and separate Electron branch were preserved.

1. audio_jobs.py adds typed prepublication failure details: real sqlite3.OperationalError with an integer native primary/extended SQLITE_BUSY or SQLITE_LOCKED code is future-retryable. Message-only, missing/bool/string codes and permanent SQLite errors remain held. Native code/name and actual checkpoint stage are recorded. Existing no-output/no-intent, one-hour backoff, busy-worker, frozen revision and exact old-attempt history gates remain. sqlite_retry.transaction remains BUSY-only and unchanged. **No legacy retryable:false row is reclassified.** This does not repair the old database-lock job.
2. audio_pipeline.py converts positive rational stream ticks to exact integer decoded-sample boundaries using Fraction, supporting HE-AAC clocks without assuming one tick per decoded sample. Missing/malformed clocks, fractional sample endpoints, nonpositive durations and nonzero starts remain held. Decimal movie fields are converted exactly; the existing one-sample duration bound remains. Raw decoder time_base/configuration, complete compressed payload, relative packet timing including skip/padding, native multichannel PCM and source/output equality checks remain. **This does not approve the observed HE-AAC remux or unblock the other 80 media jobs.**
3. tests/test_attention_failure_policy.py supplies 13 focused deterministic methods for typed primary/extended codes, permanent/message-only refusal, legacy/output/intent preservation, backoff/worker/revision gating, exact attempt history and failed-history-write behavior; rational HE-AAC/equivalent clocks, malformed/fractional/offset/drift refusals; retained raw decoder clock and packet timing/trim differentiation. No test launches media children. Test fixtures use private temporary SQLite only.

Actual tests executed: **0**. No syntax-check execution, imports of the modified application, regression suite, build, release, installation or live application occurred. Futaba's independent QA scenario/readiness record is separate; source review is not a GO or a deployed fix.

## Complete repair strategy for the 81 media holds

This is a separate bounded preservation milestone; implementing it blind while the proof route is unavailable is not an acceptable patch.

The smallest safe direction is a metadata-only source-container writer, reusing the existing bounded MP4 atom parsing/relocation infrastructure: retain original audio sample descriptions, timing tables, exact movie/audio clocks and edit lists, and retain verified source chapters without millisecond re-timing. Change only approved metadata and cover fields; relocate chunk offsets by an exact measured moov-size delta while preserving media payload bytes. Existing sources differ from the current writer's strict ftyp/moov/free/mdat output profile (some omit free or use wide, and one contains a vide track). Each accepted profile/track relationship must be positively parsed and supported; arbitrary tracks cannot be blindly dropped or retained. Fragmented/unknown layouts stay held.

Proposed implementation boundaries after executable proof exists: a bounded MP4 presentation/metadata module plus quicktime_chapters.py reuse; audio_pipeline.py selection/evidence producer; every output-validation/source-cleanup contract consumer; private fixtures and focused safety/media tests. Before changing contracts, enumerate every reader of copied_audio_evidence and related validation data and freeze the versioned proof schema.

Acceptance must demonstrate on private fixtures:
- identical exact rational audio/movie presentation mapping, including nonzero initial offset, edit media_time/rate, leading empty edits, trailing trim and audio/chapter association;
- complete compressed payload/order, decoder configuration, relative rational packet timing and skip/discard sample semantics, full native all-channel PCM/hash/count and chapter boundaries retained;
- strict unknown/overflow/truncated atom, offset, stco/co64, version and track-layout refusal; original bytes and failed attempts unchanged;
- proposed output has required approved Unicode metadata, correct cover and supported Apple chapter format, with no unintended duplicate/missing cover or removed auxiliary track;
- no media rewrite, quality reduction or unsupported growth hidden as metadata repair.

An app-owned retry admission must then bind an exact old job/manifest/attempt and classified failure to the newly reviewed policy and fresh source/output evidence. Preserve the entire old journal/attempt, reject changed manifests or publication intent/output, enforce queue admission/backoff and record a new attempt. This is **not** a general conversion of retryable:false to true and cannot be applied through a raw database reset. Old failed artifacts remain protected until a new validated publication and exact cleanup receipts authorize disposal.

## Proof and execution capsule status

Analysis, focused regression, native media proof and packaging are separate operations. No blanket Books operation route has been deployed or cleared by the shared safeguard repair. The ordinary reviewed read-only queries/header inspection above do not clear an application/checker/media graph.

Prepared focused logical regression operation (NOT executed): pinned C:/Python314/python.exe -I -B -m unittest discover -s tests -p test_attention_failure_policy.py -v, cwd equal to the exact isolated maintenance worktree. Environment must be explicitly frozen before execution (not inherited invisibly), with bytecode disabled and no app profile/library/port. The 13 method definitions are a static count, not discovered/executed tests. No live catalog, Z:/Y:, browser, FFmpeg or app launch belongs to this focused operation.

The source input map accompanying this checkpoint lists all top-level application Python sources and the focused test. Before execution it must be expanded/rechecked for the actual import closure, complete interpreter/standard-library/native dependency bytes, exact runner/helper imports and environment values. A guard-evaluated logical operation and exact owned private output root are still prerequisites. A new immutable owned-process wrapper must enforce total timeout 600000 ms with a private Windows Job and verified descendant closure; a polling/yield interval is not that deadline. The input map does not claim a deployed runner or complete runtime freeze.

Concrete pass/fail evidence must retain exact inputs, runtime, complete argv/cwd/env, discovered test IDs/counts, stdout/stderr/exit, start/end/deadline, private output inventory, final Job/descendant closure and cleanup/protected-state results. Senua and the shared safety reviewer must separately validate a harmless host enforcement positive/negative prerequisite in this exact Books context, then enroll/clear the literal operation before it runs. Any unsupported API, guard/P9/AV refusal or missing prerequisite means STOP; no transport/encoding workaround. Futaba reruns the identical cleared graph against the exact saved checkpoint before any release or application.

## Current run and final operational recommendation

A separately reviewed suffix/count-only saved-manifest query at **09:43:24.777416 UTC** retained the same exact owner and found:
- current ccee8c71-bd1b-4df9-94de-f09d19222657 checking sources, 135 M4B inputs;
- seven pending jobs: three single M4Bs and four multi-input sets of 155, 129, 108 and five M4Bs.

The current and four multi-input jobs use complete-source normalization rather than the single-M4B copy validator. Their success is not established, but the observed single-file copy defect does not prove they will all fail. Leave the current job undisturbed; no blanket pause, repeated Start or new unsupported retry was issued. The three pending single M4Bs may reach the affected copy path if AAC/ALAC and remain guarded. Raw format observation is canonical scratch/resume-2026-10-15/pending-formats-20261015.json.

No observed backlog book was repaired, no safe retry was forced, no file was deleted and no reclaimed space is claimed. Current processing can create new snapshots, so earlier 98.03 GB totals remain point measurements. The heartbeat remains paused. Preserve all raw/derived evidence, originals, recovery, failed attempts and old builds. This checkpoint contains intentional source/tests/docs and unresolved evidence; it created no verified disposable media output.
