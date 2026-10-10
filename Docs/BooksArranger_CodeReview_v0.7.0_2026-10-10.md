# Code Review — Books Arranger v0.7.0

## Header

```
Reviewer: Senua (Code Reviewer; Codex gpt-6.1-sol xhigh)
Date: 2026-10-10
Tool: Books Arranger
Release: v0.7.0
Commit range: c9617e90bff45c6e56eae2504861f786ef5a4203..f7cb9d8fe0062ec15592fd78e21cfb227fb63dc9, plus exact final candidate-v3 overlay
Files changed: 17 files, +918 / -36 (accumulated range plus overlay)
Stand-down dimensions: None; Electron-specific controls do not apply to this Python/local-web tool
```

The reviewed endpoint is the base commit plus the frozen source manifest, not dirty HEAD alone. Final snapshot: `scratch/progress-folders-2026-10-10/candidate-v3`. Its manifest is inside the directory at `candidate-v3/manifest.json`. All 52 entries were independently checked for size and SHA-256; the final focused delta changed only the fixture decorator compared with reviewed candidate-v2.

- Final source digest: `b7e8b35d692202018109c915fb9cb766954f0e541bc22b7b7e188e77f0b3cd46` (SHA-256 of the compact JSON files array).
- Final manifest SHA-256: `a4773a9dfed840cbed78d2defb07f326a8cd4a48cc6129fc8c7483334b293a67`.
- Target version: 0.7.0; frozen source VERSION: 0.6.0, pending Sully's release metadata bump.
- Final native_io.py: `5bc7bfaf137e6eea29a5c4e829f6ae1fd604b2152fe8fdd61f139ab84215855e`.
- Final storage_cleanup.py: `23cc47a0753197a27a0cffb4727ea0ee5fdaa018ae2e373aa81cb699c7648865`.
- Final conversion_progress.py: `44afb0c4770ce0ee19e8784a550e32b5a43c76e5cd0f9de41335ba08850fd7b5`.
- Final tests/test_source_folders.py: `54bed87f1e4eadacbea86ad0c24b5705d41121a3bfe4c036e303b3feaab93b70`.

The snapshot includes all 18 root first-party Python modules and their complete local import graph, all web files, existing tests, and four new source/test files. Its 52-entry manifest is a source identity; it does not pin a complete Python distribution, standard library, Windows kernel/provider, or packaged installation. The separate manual runtime/check contract below governs fixture execution.

## Summary

The accumulated change adds transient measured encoding progress, a phase-scoped current-book bar, distinct revision-valid approved/Converted counts, a matching candidate filter, and exact source-parent folder housekeeping. Review covered the progress pipe and child closure, approval-cache invalidation, filtering/pagination, frozen cleanup policy compatibility, directory disposition and durable recovery. The native data-loss finding and two integration Majors were corrected and narrowly rereviewed against the final immutable identity. There are no open findings.

## Rubric

Severity and the always-blocking safety floor follow `Team/Docs/ProcessRules.md` § Severity definitions.

### 1. Security

- Status: Pass — new FFmpeg options use the existing shell-free argument list and owned suspended child; no new path API, secret logging, renderer privilege, or broad delete operation was introduced.

### 2. Correctness & Logic

- Status: Pass — the shared counter/filter predicate binds the current approved revision, output record and required payload receipts, deduplicates by candidate, and now excludes best-effort folder state from completion.

### 3. Crash / Stability Safety

- Status: Pass — each attempt resets transient measurement, ticks avoid durable per-second journal writes, and the encoding pipe is drained and closed under existing process-job ownership before producer diagnostic receipts are recorded.

### 4. Performance

- Status: Pass — settled completed/unsupported folder receipts return before hashing or disposal; progress polls use the catalog approval cache and validated output stat identity, with bounded transient telemetry rather than media decoding or per-tick journal writes.

### 5. State & Data Safety

- Status: Pass — named-stream and unknown-provider/identity cases cannot reach native directory deletion; exact retirement/output proof, ancestry binding, replacement/Git/reparse refusal, candidates below the source root, and durable intent/absence reconciliation remain enforced when disposition is attempted.

### 6. Input Handling

- Status: Pass — malformed numeric progress is rejected or ignored, encoding time is finite/monotonic/clamped, absent denominators remain indeterminate, and Converted uses the existing status/search/pagination controls with filtering before paging.

### 7. Maintainability

- Status: Pass — approval/completion predicates are centralized and shared by the counter/filter; the native capability gate remains inside the disposition primitive as well as the storage caller.

### 8. Doc/Code Drift

- Status: Pass — the final housekeeping addendum is implemented, retained-folder wording follows authoritative evidence, and the unsupported automatic removal on actual Z: is explicitly documented.

### 9. Build & Release Hygiene

- Status: Pass — the dirty source has 52 exact pins, the separate manual Python fixture contract has an exact reviewed owned runner, and VERSION/release metadata plus receiver QA remain Sully/Futaba responsibilities; no installer/package receipt is applicable.

## Finding history and closure

### F0 [Critical, CLOSED] — late directory alternate stream was erased

The initial v0.7 helper checked emptiness/streams and then issued FileDispositionInfo. A late 27-byte directory alternate stream passed that gap and was destroyed when disposition completed. Negative proof remains at `scratch/progress-folders-2026-10-10/empty-folder-fixtures/late-ads-proof.json`, SHA-256 `76185bf3615953d3f734c248f0054670ed14a3d969eddb698c5bb1ba786c78d8`; blocked native_io.py SHA-256 `85d3c00beacad98ad03ce106ce992d00fa201656abcc14288cb962b278958cf0`.

Closure is bound to final native_io.py above. `require_empty_disposition` queries GetVolumeInformationByHandleW on the held target directory, checks nonzero matching volume identity, refuses FILE_NAMED_STREAMS, and requires a strict nonzero local volume GUID path. `dispose_empty` calls that gate before deletion regardless of caller checks. Storage gates before removal intent and native disposition repeats the gate. Unknown/UNC/unmapped/provider cases retain folders. The gate code is unchanged by the later terminal-receipt optimization.

The initial 23-check producer receipt remains at `empty-folder-fixtures/check-receipt.json`, SHA-256 `56076684eaab6e77866b5a8e1807b69438de6e8345631052b12a192d732e86f0`; the final 24-check receipt is separately preserved at `final-native-check-receipt.json`, SHA-256 `64f50bcef17475d9aea1cb72a9559f2c3e2b803e077a750d023f6c901d381461` (24 tests in 9.699 seconds). The late 27-byte stream survives even with a stale-empty result. Ordinary child/disposition/recovery fixtures explicitly simulate streamless capability; they do not certify an actual streamless filesystem.

The actual read-only Z: query reported NTFS with FILE_NAMED_STREAMS. Its empty-folder removal is therefore unsupported and retained. Automatic removal on that drive is not delivered. `Docs/BooksArranger_EmptyFolders_Safety_v0.7.0_2026-10-10.md` preserves the original blocked finding, native fix reasoning and primary Windows references.

### F1 [Major, CLOSED] — folder state withheld Converted

Candidate-v1 `conversion_progress.py:41` required a completed/unsupported folder receipt even after all required output/original/temporary-copy proofs succeeded, contradicting the final committed housekeeping addendum (`Docs/BooksArranger_ProgressUI_2026-10-10.md:58`). Its test explicitly expected exclusion for missing/needs_attention folder state. In candidate-v2/final-v3 that folder obligation is removed entirely; output, approval, source-retirement and temporary-copy requirements remain. Corrected assertions cover absent, checking, needs_attention, unsupported and completed folder states without changing required payload failures.

### F2 [Major, CLOSED] — settled folder housekeeping rehashed all outputs

Candidate-v1 Resume/Create called run_folders for every completed enrolled job and reached protected_output/full-M4B hashing before checking a terminal folder receipt. Final `storage_cleanup.py:435` returns completed/unsupported folder receipts before that read and before any new disposition. Replacement folders remain untouched. Actual destructive attempts still hold and hash the output and verify exact retirement/ancestry obligations. Existing AudioJobs output validation remains independent.

First combined candidate history: source digest `dfe00876429e900e77a3934e469a40c35e953faae01dc243cb0104743da57609`, manifest `ab022d5b167bae028c8aa4a5b3601de9f1f164c6db3323e1a4dcda01dabd9576`; then focused candidate-v2 digest `6e4e5ef1e7c58aad5afa3d1128c650c8314a1b02cb708056b1a59528f9584b4d`, manifest `c0a27e02c943a2e8eec74a398b6ab1f7261e613a76d4ab07411bff11d31860b5`. Final-v3 additionally restores the unrelated-sibling fixture's omitted decorator. Only four source/test entries differ from v1; only the decorator differs from v2. No broader source change was accepted implicitly.

## Exact manual QA runner clearance

The following bundle was independently read and hashed and is CLEAR for its fixed private fixture checks only:

- `scratch/progress-folders-2026-10-10/manual-contract-v3.json`: `e8ff11d3f357b96a5b8090b98adc04319391e44755a07fcd98531ef5fd63cc65`.
- Outer `run_qa_v3_owned.py`: `4e4868f75a099a6b47b016b194c50abd0419ae63602aeeb0855c4a43c6c32234`.
- Inner `qa_checks_v3.py`: `60b140d4859a348d654ff5ddfd43c022cab96fb4bc66607bf1c002bc6245cf0d`.
- Invocation: `C:/Python314/python.exe` with the absolute outer-runner path and no additional arguments.
- Private source: `scratch/progress-qa-2026-10-10/candidate-run`, with all 52 entries and final manifest held and verified.

The fixed graph is 7 progress + 6 merge + 24 native Python checks, plus progress and cleanup JS checks (cleanup also invokes metadata coverage). The outer runner starts a shared 600000ms monotonic budget before identity work, assigns the suspended inner child to the previously reviewed kill-on-close OwnedProcessJob before resume, and encloses heavy source/runtime hashing and all fixed descendants. Inner children receive their own contained ownership. Expired budgets cannot start new children; output is retained up to 2 MiB per stream and drained; exit/descendant closure is awaited with teardown reserve. Only exact newly created handles/processes are terminated.

The checked manifest bytes are parsed once while its native file/parent guards stay held. Source and the four contract executable pins remain held through checks. FFmpeg/FFprobe resolution is checked from the same private cwd used by tests, with the pinned binary directory first in PATH. Python/Node commands are exact fixed paths. The pinned old containment module is `scratch/retention-cleanup-2026-10-10/candidate-v3/native_io.py` SHA-256 `9939de63b3448e02f0c664d43242fe46e728a2f4f77ad21ed62f0bf98c7fad44`; it is used for process ownership, not the new folder-disposition behavior under test. This approval contains no real-library cleanup, service restart or desktop operation.

Producer checks and receipts were reviewed as evidence, not rerun by Senua. Deletion gate placement and final source changes were inspected independently; passing tests alone do not establish deletion correctness. Receiver QA execution and its final receipt remain independent of this source verdict.

## Verdict

- Total Critical: 0
- Total Major: 0
- Total Minor: 0
- Closed this cycle: 1 Critical, 2 Major

**Verdict:** RELEASE CLEAR

Clearance certifies the stated range plus final 52-file candidate-v3 overlay. Source changes beyond the approved VERSION/release-report metadata require a narrow rereview and updated exact identity.
