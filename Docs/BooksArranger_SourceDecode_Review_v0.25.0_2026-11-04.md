# Books Arranger 0.25.0 — source-decode diagnostic review

Reviewer: Senua. Date: 2026-11-04.

Reviewed commit range: `a1fd80c793db137c50ba75d2990f22ec0f022698..a4e43d05e8a456dc3999b309b4f767dc45fc31e3`. Source/test scope: `audio_pipeline.py` and `tests/test_mp3_tag_repair.py`, +99 / -12. Open findings: Critical 0, Major 0, Minor 0. No safety-floor violation identified. This is a completed source-slice assessment, not final release clearance.

The change adds `SourceDecodeError`, a `ValidationError` subtype with a plain `source-decode-failed-v1` diagnostic. The two production callers pass their explicit included-playback index to `_source_duration()`. Before wrapping a completed native decode failure, that helper requires an integer index in the frozen source list and exact original path/hash correspondence. The displayed source identity therefore comes from the manifest rather than the private staging alias. Detail is bounded to 2,000 characters; native failure and completed MP3-repair-check flags and the causal exception chain survive. The manifest is not rewritten.

The existing finite MP3 tag-repair attempt precedes classification. A successful verified repair still returns its duration; an unsupported repair preserves the original decode failure as the cause. Pause, timeout, incomplete native ownership/drain, unmarked error strings, working-copy integrity failures and output validation retain their existing behavior. This patch adds no broad damaged-audio repair, discarded samples or weaker output proof.

| Dimension | Status for this slice |
|---|---|
| Security | Pass: no new execution, path mutation, IPC or credential surface. |
| Correctness and logic | Pass: exact included-source index/path/hash binding and preserved repair/error semantics. |
| Crash and stability | Pass: invalid/ambiguous indices retain the original exception; native lifetime and timeout handling are unchanged. |
| Performance | Pass: bounded diagnostic metadata only; no extra decoder invocation. |
| State and data safety | Pass: original and snapshot bytes remain unchanged; successful repair retains its existing verification. |
| Input handling | Pass: boolean, missing, out-of-range and mismatched indices cannot invent a source identity. |
| Maintainability | Pass: one shared classification boundary supplies both production source-decode paths. |
| Doc/code drift | Pass: diagnostic schema and zero-based included index are explicit; presentation uses one-based positions. |
| Build/release hygiene | Source scope passes: only two source/test files, no dependency/build-graph changes; final package pending. |

Verified summary SHA256 `0019246f3dce4cff2a6062884453189fcc614d37c9b08393ba0edaf7562ef95e` and implementation patch SHA256 `b272e2ce0944e7a3200021ca2af3e130bb4f14d584c9b3fb337e2b0c74b8d061` under `Docs/Evidence/converted-duplicate_2026-11-04/source-decode-diagnostic`. Both source/test files and every listed evidence file match their exact frozen hashes. The actual final receipt records 119/119 tests passing in 6.859 seconds, comprising 17 MP3/diagnostic cases and the 102-case preservation cohort, with complete owned closure, native zero, no force and no timeout.

The private native bad-input case binds position 12 of 57 to the original source, retains the native decode detail after finite tag-repair refusal, and asserts unchanged source/alias bytes and no derived repair output. Other cases cover JSON roundtrip, causal flags, successful repair, M4B classification without MP3 repair, invalid indices, spoofed prefixes, pause, timeout and drain failure. Senua read the source and receipts without running tests or native probes or accessing live sources.

Job-store persistence, source-remedy eligibility, attention reporting and UI consumers are not part of this commit and are not cleared by this review. Their eventual implementation must bind stored diagnostics to the current frozen manifest/index/count/path and preserve failure-stage eligibility. The pending folder/media consumer changes, full milestone QA and exact source/build binding remain necessary before the final accumulated release verdict.
