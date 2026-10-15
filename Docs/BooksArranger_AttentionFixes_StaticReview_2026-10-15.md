# Books Arranger attention fixes — static checkpoint review, 2026-10-15

**Checkpoint:** ACCEPTED FOR SAVING ONLY — unfinished and untested. This is not release clearance, execution clearance, deployed repair or acceptance of existing backlog jobs.

## Exact scope and identity

Reviewed the semantic changes to audio_jobs.py and audio_pipeline.py, the complete new tests/test_attention_failure_policy.py, and the AttentionJobs, QA_Scenarios and SourceInputs records. Isolated branch codex/books-attention-fixes; supplied clean base ef04a26482895948bad9213e0c64d12b73c49fcf. The review certifies the following working source bytes pending Sully's explicit-file commit, not an unrecorded future commit range:

- audio_jobs.py: 003a19aa91bdec73e0fb94ff30ae9706da2509185c528794a35cc4d6512d2877.
- audio_pipeline.py: a6c45781f756da03a615eec9a5503c595d30cfcd1ad7190cc78a125c4bdf3227.
- tests/test_attention_failure_policy.py: 6cc19fae2264a987c1a73623a5c951b79bb848c73dddfbf6f658df235174c45d.
- Docs/BooksArranger_AttentionJobs_2026-10-15.md: f6144508a5c5828956ff46c2a6f094c515d7308c6a9921520e0f7ffdaa44892c.
- Docs/BooksArranger_AttentionFixes_QA_Scenarios_2026-10-15.md: 33d02c197859c9295a2651369c2ddfcf576fcedcf7b9ba6d450231fe11ffc89a.
- Docs/BooksArranger_AttentionFixes_SourceInputs_2026-10-15.json: e2d8fc6443127be8b580dc0554f811f3917c62f3d84662de7b17c20210ab48a8.

Independently read and SHA-256 checked every one of the source map's 40 declared files; zero mismatches. The map expressly leaves import/runtime/helper/environment closure incomplete. It is not a frozen execution capsule. Method count: 13 explicit test method definitions in the new file, counted statically; actual discovered/executed tests: 0.

## Construction findings and disposition

Two review findings were corrected and their exact revised bytes inspected:

1. The new retry-history test compared sqlite3.Row values directly with tuples, which would fail independently of retry behavior. It now explicitly converts each row to a tuple.
2. The typed SQLite classifier initially accepted negative integers whose low byte resembled BUSY/LOCKED. It now requires a nonnegative integer; focused negative lookalike cases -251/-250 were added.

No remaining Critical construction finding was identified in this narrow static delta. That statement does not establish runtime correctness or clear a release.

The failure helper changes future classification only: real sqlite3.OperationalError with nonnegative native BUSY/LOCKED primary or extended code, recording native identity and actual checkpoint stage. Message-only and invalid/permanent errors stay held. Existing output/publication-intent refusal, hour backoff, active-worker and frozen source/revision gates and exact attempt history remain. The BUSY-only transaction replay helper is unchanged. Existing retryable:false history is never reinterpreted; the old database-lock job is not repaired by this checkpoint.

The presentation helper uses exact positive rational tick-to-decoded-sample conversion with integer endpoints. Nonzero origins, unverifiable bounds and the existing one-sample movie-end tolerance remain guarded; sub-sample nonzero movie starts are now explicitly refused. Full decoder configuration including raw time_base, compressed payload, packet timing/skip/discard, native all-channel PCM and source/output equality gates remain in place. This arithmetic correction does not erase actual edit/timing changes or make the observed HE-AAC remux safe.

## Actual repair coverage and current operation

The observed 82 attention jobs remain unresolved: 50 broad remux-evidence mismatches, 30 gap/presentation holds, one bounds hold and one database-lock failure. The original 80 large generated-file jobs are a subset. Ten completed jobs with original-stream cleanup holds are separate and remain protected.

Retained metadata proves real representative remux changes: 139's movie/edit span extends by 1/750 second; 07 acquires an edit starting at media_time 2112; HE-AAC's legitimate 22050 clock becomes 44100 with three fewer sample-table entries. A rational helper or matching extradata cannot authorize those outputs. The documented source-container preservation milestone must retain actual original sample/decoder/timeline/edit/ctts/chapter semantics and relocate only validated offsets for metadata changes, with explicit source-layout/track policies. Unknown layouts remain held. Fresh private media proof and a supported app-owned, exact old-attempt-to-new-attempt recovery contract are still required; no raw reset, flag flip or adoption of failed output is acceptable.

At 09:43:24 UTC the exact read-only cohort observation found current ccee8c71-bd1b-4df9-94de-f09d19222657 checking 135 M4B inputs, and seven pending jobs: three single M4Bs and four multi-input M4B sets. The single-file copy defect does not establish failure of the current/multi-input normalization path. Leave current user-authorized processing undisturbed; this review clears no pause, repeat Start, retry or deletion. The heartbeat stays paused.

## Execution and preservation limits

No modified Python module, discovery, syntax check, regression, media analysis subprocess, build or packaging was executed by this review. The focused tests remain written contracts, not passes; Futaba records NO-GO. The shared safety work has not deployed or cleared a Books analysis/check route. Ordinary previously reviewed read-only status/header observations do not clear that graph. Before execution, complete and independently review the actual input/runtime/import/environment and owned-output capsule, supported guard-evaluated invocation, total 600000 ms private Job deadline and descendant closure, and actual positive/negative enforcement in the Books context. A refusal stops the path; no alternate transport or encoding is authorized.

No live source/runtime, queue/catalog, originals, recovery, hooks/config/trust or Electron candidate was edited by the reviewer. No file was deleted or space reclaimed. Unresolved raw evidence and failed attempts stay preserved. This intentional report is the reviewer's only file output and has no disposable counterpart. Sully may save the six exact checkpoint files above plus this report and push immediately through the ordinary scoped Git route; no version bump, tag, release, installation or current-job migration is implied.
