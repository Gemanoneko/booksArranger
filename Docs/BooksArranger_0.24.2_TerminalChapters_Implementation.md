# Books Arranger 0.24.2 — terminal chapter implementation

Implementation slice for the committed 2026-11-01 scope and UX spec. Extends 0.24.1; no source file is repaired or rewritten. The reported three Tolkien endpoints remain metadata evidence only: no additional reads of those four source files were made during this work.

## Files and ownership

- `audio_pipeline.py`: typed chapter diagnostics, bounded joined-part verification, fresh conversion proof and output receipt.
- `tests/test_terminal_chapters.py`: 20 authored test methods, counted with `rg -n '^    def test_'`: 17 deterministic tests and 3 explicitly enabled native fixture tests. Subtest cases are not counted as methods.
- This implementation note.

No other code, version, changelog, git, release, application, live `data/`, or Z: changes belong to this slice. Lead owns admission, recording review, renderer and surrounding integration. Routing agent owns its separate routing files.

## Contract

`source_chapters(path, stage, stop, duration)` remains the strict default and returns the existing millisecond chapter list. The 50 ms overlap and 250 ms endpoint tolerances are unchanged. No proof or correction flag can be supplied to it. Whole single-M4B preservation and its output chapter checks continue using this function.

`verified_source_chapters(path, stage, stop, duration, *, source=None, on_check=None)` is the joined-part admission/conversion helper. It returns:

```python
{'chapters': [{'start': 0, 'end': 4000, 'title': '...'}],
 'terminal_end_correction': None}  # Or an audit receipt for a proven correction.
```

`source`, when supplied, must carry exact `sha256`, `size`, and `modified` values for the file currently opened. Missing or changed values refuse correction. Admission should supply the current reviewed source facts. Conversion uses the frozen source SHA-256 and size plus the protected snapshot's own modified timestamp; a copy naturally has a different timestamp. Full hashes are fresh and taken through the leased source handle. A receipt is serializable evidence, never a token that authorizes reuse; the helper accepts no saved proof parameter.

`on_check` is called only after the terminal-end candidate and all earlier conditions/titles have passed, immediately before proof work. Its argument contains `phase: 'Checking source audio'`, `reason: 'terminal_chapter_end'`, and the diagnostic fields below. The lead maps this to Judy's current source-check activity. It must not claim completed correction from this callback.

`ChapterValidationError` remains a `ValidationError`/`ValueError`. Its `chapter_diagnostic` dictionary contains `file`, `path`, zero-based `chapter_index`, original `chapter_id` (index fallback if absent), `chapter_title`, `predicate`, `start`, `end`, and `duration`. Times are seconds, with unreadable/nonfinite input retained as JSON-safe text. Overlap also supplies `previous_chapter_title` and `previous_end`; failed audio proof supplies the specific `reason`.

Predicates are `unreadable_time`, `start_before_audio`, `end_not_after_start`, `overlap`, `start_beyond_audio`, `end_exceeds_audio`, `invalid_title`, `complete_audio_unverified`, and `source_changed`. The exception message names the actual file/chapter/condition/times; no generic overlap-or-exceeds message remains. Pause and timeout propagate as their existing transient exception types, without claiming source corruption.

## Proof and preservation boundaries

Only a finite last endpoint exceeding the supplied complete duration can enter correction. Earlier endpoints, nonfinite times, invalid spans, overlap, bad/missing starts, starts outside the audio, and invalid titles refuse before decoding. Every title and every earlier boundary is checked before expensive work. Valid small offsets, including 48.1 ms, keep their original plan and generate no correction receipt.

The helper holds `VerifiedFile`, denying source writes/replacement during the probe and proof. It then:

1. Binds fresh full SHA-256 and file identity/size/mtime to the reviewed facts when supplied.
2. Calls the existing intact `m4b_preservation.plan` with no damage-repair permissions. This checks complete container/sample extents and retains the whole-M4B safety rules; it constructs no output.
3. Requires independently read audio packet count to equal the intact audio track's declared sample count, retaining decoder configuration and source-relative packet/presentation evidence.
4. Runs the existing complete native-rate/all-channel strict decoder into its streaming PCM hash. The decoded duration must agree with the reviewed duration and audio stream duration within the existing 250 ms source-duration allowance.
5. Revalidates all chapters against that decoded duration, replacing only the final end. Titles, starts and order are unchanged. The final start must fit strictly inside the decoded end, including millisecond output precision.
6. Refreshes handle facts and rereads the full source hash before returning.

Any container, packet, decode, read, identity, duration or chapter contradiction refuses the correction. There is no audio trimming, missing-packet allowance, new damage repair, tolerance widening, or chapter deletion. Correction does not assert whether the original bad endpoint arose on disk or during demuxer interpretation.

The receipt carries schema `terminal-chapter-end-v1`, source hash/facts, chapter identity, original/corrected end, decoded duration, native PCM evidence, packet/configuration evidence, and source audio-track hash. `_encode_tagged` re-proves every joined part from its protected snapshot and compares the resulting chapter plan with the frozen manifest. Only after existing output validation passes does it attach `terminal_end_corrections` to the final validation record, with each original `source_path`.

Standalone whole M4Bs remain strict: their byte-exact preservation branch cannot change chapter timing without a separately proven container change. The reported cases are joined M4B parts, so no such standalone rewrite is part of this slice. Existing joined-part normalization and full-output validation remain in force.

## Consumer list and integration ownership

Literal search of `source_chapters`, `verified_source_chapters`, `ChapterValidationError`, and `terminal_end_correction` identified:

- `audio_pipeline.py`: strict default; standalone copy/preservation source and output checks; joined `_encode_tagged` reproof; final validation receipt. Implemented here.
- `review_backend.py`, `build_manifest`: single source chapter plan stays strict; joined `part_chapters` planning uses the new helper. Lead-owned integration.
- `merge_service.py`, `_recording_review`: joined-part recording chapter hashes use the helper with current source facts, while single whole-M4B classification stays strict. Lead-owned integration.
- Existing approval/error serialization and renderer chapter/technical details consume the typed diagnostic and completed receipt; lead owns those ends. No UI code is changed here.
- Existing media/preservation tests call the strict default; their contract is retained. New tests exercise both helpers.

Admission and conversion must both use the corrected plan. A saved receipt or earlier metadata probe must never replace fresh conversion proof. Current reviewed source byte identity is still checked by the surrounding manifest/snapshot flow.

## Verification status and exact private fixture route

**Tests have not been executed.** At handoff the reviewed targeted runner was not admitted for this suite; no naked Python/native subprocess, unsupported guardian operation, global guard change, app control, or duplicate full gate was used. `git diff --check -- audio_pipeline.py` passed. This is a whitespace check, not runtime validation.

The deterministic methods cover strict-default refusal, unchanged valid offset, exact identity/timing diagnostics, invalid earlier predicates, absent title fallback, long titles, untouched probe data, all titles/starts/order, intact-container refusal, missing packets, decoder failure, unknown/disagreeing duration, final start outside the actual decode, stale reviewed size/mtime/hash, same-size/same-time changed bytes, proof freshness, and pause/timeout behavior.

Native cases require an explicit runner environment:

```text
BOOKS_TERMINAL_FIXTURE_ROOT=C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/chapters
```

The class creates one `native-<uuid>/` child under that root per suite run. It generates one shared 2-second AAC M4B with two distinct QuickTime chapter timing runs and one small PNG cover. It changes only that private fixture's terminal text duration and matching text media clock, leaving source audio bytes/offsets, starts/titles and movie clock intact. Three methods reuse it: full proof/source-identity preservation; private truncated-tail refusal; two-part full conversion and output chapter validation. The join case adds one copied part and owned conversion staging output. No heavy fixture is recreated per method, no personal directory is selected, and no live source is used.

All native descendants are FFmpeg/FFprobe through existing `run_owned`/pipeline ownership, suspended admission, `CREATE_NO_WINDOW`, and owned process closure. The actual runner must pin this source/test snapshot and those runtime binaries, declare the entire native graph and scratch root, and enforce the reviewed 600000 ms hard deadline with descendant closure. There are no browser, application, tray, dialog, `mklink`, install, or network operations in this test file.

No fixture/output files were generated by the implementation work itself. The named per-session scratch folder is left for Sergei's manual removal after reviewed testing, consistent with the per-session scratch exception. Unresolved evidence, source files and other agents' work are preserved.

## Reviewed chapters-1 execution and fixture correction

The lead executed the one admitted `chapters-1` invocation. It ran all 20 methods: the 17 deterministic methods passed; the three native methods produced two assertion failures and one missing-receipt error. The outer owner closed cleanly with complete native zero, no force or timeout, and matching postflight pins. This was a failed test run, not a passing chapter verification. Its complete logs, frozen source and private generated media remain unchanged under `shared/chapters-1/`.

Read-only examination of those retained JSON probe outputs and synthetic container bytes identified the fixture defect. The fixture enlarged the final text `stts` delta and matching `mdhd` clock to 1,800,000,750 ticks, but its generated text `tkhd` duration and single `elst` segment still ended at 2,000 movie ticks. FFprobe consequently reported the last chapter ending at 2.000 seconds, exactly the audio duration. The valid-chapter early return was correct; neither correction nor its complete-audio checks were reached. The truncated fixture similarly failed to exercise the intended candidate branch. No further FFprobe invocation was needed for this diagnosis.

The test-only correction extends that synthetic text track's header duration and sole zero-origin edit segment to the same exact text endpoint, converted into the movie clock. It leaves every audio byte, audio clock, chapter start/title/order, movie clock and file offset unchanged. The fixture now also asserts that its initial real probe actually exposes an end beyond audio plus 250 ms, so a capped fixture stops explicitly before claiming proof-path coverage. No product validator, tolerance or complete-audio safeguard changed in response to these failures.

The corrected test is to be verified in a new `chapters-2` snapshot with a new concrete delta review, not by replaying or modifying the admitted `chapters-1` batch. Preparation and source inspection are not execution evidence; the corrected native tests remain unexecuted until that review and run.

## Chapters-2 actual failure and chapters-3 preparation

The admitted chapters-2 log reports 18 passing methods and two errors. This is not an accepted test run: the supervisor rejected a final-versus-streamed diagnostic byte mismatch and forced closure; native descendants were reported complete/zero. Both product errors reached the real preservation planner with an empty metadata dictionary, which the planner correctly refuses. The previous mock did not enforce that requirement.

The fix follows the existing m4b_repair.diagnose read-only contract: provide an in-memory check title, consume only validated intact track facts, and never stream the candidate. No source metadata is written and no repair flag or tolerance changes. The deterministic fake now invokes the real approved_items validator, while the existing native full-proof and join cases exercise the real planner.

Chapters-3 is prepared only at `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/chapters-3`; no tests/probes/decode ran during preparation. It freezes 91 source files (tree `d65b77594e0d82970e305bd30aa5a9a2403fb8bf8836f5c4e0ba63ee5f9dbcc8`), with only audio_pipeline.py (`2650ea70ef839aad200bca5f4bd2f2d507a8046d7722d73f55cbbcbe4057985d`) and tests/test_terminal_chapters.py (`8266b5b3681199a9c477418a0ac4fb876fab51c34b917b7e35563df3bc51d039`) replacing the prior snapshot. Its plan is `14dd645acc6a0f32cae55e32279cdd91d8548e3b77b9bc6f8bbb824f1cfce612`, driver `ca3f05703f147db4abca34a822e85d3074080ea3376596267c343e0718093d7a`, invocation `101cf9c0e6bc4a80000b909af8e69adf3fa898f59eb743f1f05a0c1bf6fcbd59`. Complete runtime/ownership/helper pins and native graph are supplied for Senua review before lead execution.

The runner explicitly reconfigures stdout/stderr to ASCII with backslash escapes before loading tests, because isolated Python ignores PYTHONIOENCODING. A Unicode diagnostic marker must round-trip as ASCII on both streams; the unchanged supervisor still compares exact bytes and the driver requires the marker after unchanged closure/postflight. Prior logs show replacement characters at diagnostic curly quotes; the original raw non-UTF8 bytes/code page were not retained, so the exact legacy encoding is inferred. No global ownership helper is modified. Both prior failure snapshots and generated private media remain retained for review.

## Chapters-3 execution result

Lead reported the one reviewed chapters-3 invocation passed all 20 methods with no skips (17 deterministic and 3 native), outer exit 0, normal owned closure with native complete/zero, matching diagnostic markers and unchanged postflight. This agent did not execute or replay it. Frozen source/test hashes above are unchanged. Prior failed batches remain retained as unresolved-history evidence; no actual source media was read.
