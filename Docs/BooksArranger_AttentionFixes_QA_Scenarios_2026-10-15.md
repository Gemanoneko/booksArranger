# Books Arranger attention fixes — QA scenarios, 2026-10-15

Scope: isolated maintenance branch codex/books-attention-fixes, requested base ef04a26482895948bad9213e0c64d12b73c49fcf. Design/readiness only; no code fixes or execution.

**Verdict:** NO-GO

Actual tests executed: 0. Imports/discovery/probes, builds, app controls, installation and cleanup: 0. This is not a release report or evidence that candidate behavior passed. The installed canonical app and Electron candidate are outside this pass.

## Evidence boundary

Jane relayed diagnosis of 82 needs-attention jobs: 50 generic remux dictionary mismatches that may be presentation-only; 30 gap/rounding cases needing proof; one legitimate HE-AAC clock rejection; one SQLite lock failure. The relayed jobs had no output/publication intent and false retry flags. Futaba has not independently inspected live jobs. Counts and diagnoses do not authorize retry, delete working files, override existing false classifications or declare the 80 remux/gap cases fixed.

Static reads covered audio_jobs.py retry/failure/history fences, audio_pipeline.py copied-audio evidence, and the October 12 SQLite candidate/QA records. The earlier transaction replay helper intentionally retries BUSY only; the proposed audio-job failure classification must not broaden that helper or replay media work automatically.

## Required HE-AAC behavior cases

| Scenario | Required observable result |
| --- | --- |
| Legitimate HE-AAC clock at half decoded sample rate, zero audio/movie origins, exact integral tick-to-sample conversion | Clock evidence accepted while packet timing/payload and decoded PCM proofs still independently pass. Include unchanged canonical-clock baseline. |
| Equivalent valid rational clock representation | Same exact sample bounds; no floating-point rounding used to invent an integral endpoint. |
| Clock yielding fractional decoded-sample endpoint; missing/malformed/zero/negative denominator; invalid rate; unknown or incompatible profile | Refuse unverifiable evidence. Do not generalize one legitimate HE-AAC case to arbitrary clocks. |
| Missing, nonfinite, negative, malformed or inconsistent stream/movie duration/bounds | Refuse. Existing permitted movie-end rounding stays bounded; test its boundary and just beyond it. |
| Nonzero audio or movie origin, leading gap/edit offset | Refuse; accepting rational clocks must not normalize away offsets. |
| Matching presentation but altered decoder extradata/profile/channels/rate | Refuse changed decoder configuration. |
| Changed packet count, relative timing/duration, skip/discard padding or packet payload | Refuse even if displayed duration and clock compare equal. |
| PCM truncation, appended samples, altered channel samples or digest | Refuse even if packet metadata appears equal. |
| Source changes during verification or destination collision | Preserve existing fail-closed source/publication rules; no source retirement or payload adoption. |

A mocked probe-positive case establishes parser arithmetic only. Native real-media acceptance requires an owned private HE-AAC fixture, pinned FFmpeg/ffprobe, complete retained logs and exact packet/PCM evidence on the fixed source. No live source library fixture is authorized here.

## Required SQLite failure/retry cases

| Scenario | Required observable result |
| --- | --- |
| Real sqlite3 exception with native integer primary BUSY/LOCKED or a valid extended code retaining that primary | Persist typed primary/extended identity for a newly observed failure; preserve stage/time/class and failed attempt evidence. Explicit retry eligibility is separate from automatic retry. |
| Message contains database locked/busy but type/code is absent, invalid or unrelated; bool/string/malformed code | Remains unclassified/held. Text alone never enables retry. |
| Native CORRUPT, NOTADB, IOERR, FULL, READONLY, constraint or other permanent/unknown code | No BUSY/LOCKED classification; preserve failure evidence and existing space-hold behavior. |
| Existing legacy failure retryable:false, including message suggestive of SQLite contention | Remains false; never infer a missing native code retrospectively. |
| Output present or publication_intent present, including malformed/partial intent | Existing publication fence prevents blind reset; no original/working cleanup follows from classification. |
| Retry requested before due time, active worker, changed source/review revision, wrong job/state | Existing gate remains effective; no new worker, media retry or rewritten manifest. |
| Explicit eligible retry after due time on unchanged frozen manifest | Prior journal/attempt recorded exactly once before requeue; no loss of diagnostic evidence. Retry must not happen merely by construction/status read/restart. |
| History insertion or subsequent queue update hits DB failure | Fail visibly without silently losing old journal/attempt or claiming a durable requeue. Partial state must be recoverable and cannot authorize publication/cleanup. |
| Repeated explicit request/concurrent request, next failure or eventual success | No duplicated worker or erased old attempt; new failure keeps its own native code/stage and prior history remains unchanged. |

No current safe endpoint for retrying the historical attention jobs was supplied. Classification changes alone cannot be represented as user-visible retry completion. Any proposed endpoint/application is separate scope needing review and QA before live use.

## Entry and actual QA readiness

Read qa-handoff SKILL.md. On actual build handoff, use the supported reviewed immutable input contract and identical sequential sender/receiver invocation; independently derive the receiver result, never copy the sender receipt. Pin the complete committed maintenance source (not this shared working tree), runtime/native dependencies, checker, harness, actual finite check graph, private roots and total 600000ms owned-process deadline with descendant closure. A historical manual Books route cannot be adopted solely because its old report passed.

Before any execution: safety owner must verify a supported Books route and Senua must clear the exact operation and pins. Current reported shared hold/absence of Books entry remains blocking. No test/import/native fixture generation is allowed through alternate transport. Guard refusal means stop and report, no route evasion. Actual case IDs/counts/outcomes, receipts and failure logs must be read after execution; declarations are not passes. Senua covers construction; Futaba covers independent behavior and does not duplicate that review.

## Pattern alerts

- Historical errors lacking typed provenance cannot safely be reclassified from message text. Disposition: preserve old false decisions and raw evidence; defer any recovery workflow pending a separately reviewed explicit retry design.
- Broad remux mismatch text hides whether evidence differs only in presentation or actual media. Disposition: record the distinction and defer each case until exact bounded evidence proves it; no mass retry or cleanup based on the diagnostic count.

No disposable output created. This intentional scenario record is retained. Originals, unfinished work, recovery and unresolved evidence remain preserved.
