# Books Arranger native thread check QA — v0.12.2 candidate — 2026-10-12

**Verdict: GO for the exact isolated two-file candidate.** Independently passed **12 unique Python cases in one owned invocation: 6 native-thread cases + 6 existing safety cases**. No production application, live app launch, job recovery, or release was performed by QA.

## Identity and execution

Baseline commit `a45566237eeeb8b79a15a16f7a046dcdab14ec3c`, source version 0.12.1, target 0.12.2-candidate, dirty=true. Changed paths: `native_io.py` and `tests/test_native_thread_check.py`. Snapshot area `scratch/native-thread-check-2026-10-12/candidate`; source digest `83cb44b8b5f079358cc6e70815c044015c00f3a74a11b1a1327ab9de5603d4fa`; manifest `77c5145ac68837ca65d91a26174dce8e4fbf3bab4e64e124bf70fe36853241e2`.

Applied qa-handoff's separately reviewed manual nonpackage contract. No package checker or stale 181/86-case route was used. Senua explicitly cleared the exact separate receiver route after the PID=-1 amendment. Futaba independently verified the producer's actual 12-case PASS receipt and the four receiver/source pins before execution:

- Receiver contract: `d04397b22ac2599b009df375289873a32053cec018ca75521a99ea59318a0d1b`.
- Outer: `bd9604a962ebdc9e4747293a49b6156f335c47638434be182f78a31aa0c228e6`.
- Inner: `59b477cc618134608e8f2d29e80db2f0c13d5ff3968dcb54aefb9d8403a6dbb7`.
- Manifest: `77c5145ac68837ca65d91a26174dce8e4fbf3bab4e64e124bf70fe36853241e2`.

Fixed command: `C:/Python314/python.exe` followed by `C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/native-thread-check-2026-10-12/run_qa_independent_receiver_owned.py`, no arguments. The 600000ms total wall deadline, pinned native ownership module/runtimes, suspended child launch into owned kill-on-close Windows Jobs, bounded output drains, child-exit waits and pre/post input verification were retained. Outer **10.6453752s**, inner **10.5979994s**, exit **0**. Both suites exited 0 with no runtime error, warnings or retained-stream truncation. Owned private children completed/drained; early descendant cancellation was verified. No failed ownership/timeout/closure condition was bypassed.

Receiver evidence (same scratch area): `receiver-check-receipt.json` SHA256 `ab97202383ca00ca5dbe2b0cbfdc31bf5f13797a08fd1497bb09bb3ca7d75be2`; `receiver-owned-receipt.json` SHA256 `75b08dc8dc491b0295491d9b2a49a19aacdddc058a4d4dccced2a84131868c79`. Source HEAD/dirty/digest/manifest and pass result match the producer receipt; producer output was not reused as receiver evidence.

Actual manual receipt, identical identity/result to producer:

```text
BOOKS_MANUAL_QA|tool=Books Arranger|target=0.12.2-candidate|source=0.12.1|HEAD=a45566237eeeb8b79a15a16f7a046dcdab14ec3c|dirty=true|source_digest=83cb44b8b5f079358cc6e70815c044015c00f3a74a11b1a1327ab9de5603d4fa|manifest_sha256=77c5145ac68837ca65d91a26174dce8e4fbf3bab4e64e124bf70fe36853241e2|python=pass|node=n/a(unchanged frontend; released v0.12.1 baseline)|package=n/a(manual nonpackage contract)
```

## Actual case IDs and count method

Futaba independently parsed fully qualified verbose unittest IDs ending `... ok` from actual receiver outputs, checked distinct IDs and the two `Ran 6 tests`/`OK` records. **12 distinct cases**, not assertions/subtests, producer repetitions, or reused SQL/interface checks. Native suite 4.493s; safety suite 0.781s.

```text
test_native_thread_check.NativeThreadChecks.test_baseline_race_reproduces_exact_native_ctypes_error
test_native_thread_check.NativeThreadChecks.test_candidate_concurrent_actual_native_enumeration_keeps_abi_identity
test_native_thread_check.NativeThreadChecks.test_no_matching_owned_thread_refuses_without_resume
test_native_thread_check.NativeThreadChecks.test_private_audio_admission_source_check_advances_without_publication
test_native_thread_check.NativeThreadChecks.test_two_owned_private_children_finish_and_drain
test_native_thread_check.NativeThreadChecks.test_windows_threadentry_layout_and_native_signatures
test_safety_boundaries.Boundaries.test_cache_junction_is_rejected_before_write
test_safety_boundaries.Boundaries.test_directory_guard_denies_reparse_write_handle
test_safety_boundaries.Boundaries.test_directory_guard_rejects_ancestor_rename
test_safety_boundaries.Boundaries.test_handle_rename_is_exclusive_and_preserves_collision
test_safety_boundaries.Boundaries.test_modified_destination_temp_cannot_be_published
test_safety_boundaries.Boundaries.test_suspended_job_cancels_its_early_descendant
```

## Behavioral conclusion and limits

Actual concurrent Windows thread enumeration reproduced the old differing ctypes Structure identity failure (`expected LP_ThreadEntry instance instead of pointer to ThreadEntry`). The fixed module-level ABI avoided that failure on concurrent native snapshots. ThreadEntry is 28 bytes with offsets 0,4,8,12,16,20,24 and Thread32First/Next pointer type and BOOL return bindings matched. An unmatchable PID=-1 refused before OpenThread/ResumeThread; this proves no matching-owner refusal, not a direct runtime test of the unchanged returned-PID mismatch branch. No foreign process was opened or resumed.

Two real owned private Python children completed concurrently and drained correctly. A private WAV underwent actual ffprobe/source PCM checks and then held on deliberately invalid cover, with no output/publication intent, no destination, and identical source/cover hashes. Existing native tests retained junction/reparse protections, held directory identity, no-replace collision bytes, changed-temp refusal and descendant cancellation. No cast bypass or owner-suspension weakening was used.

This is native boundary regression coverage, not full media publication/retirement acceptance or a live real-book completion. The verified-original deletion requirement and 24-hour recovery policy remain unchanged and required; no originals or recovery evidence were retired. The previous 78-case SQL candidate proof remains separate baseline evidence and contributes zero cases to this 12-case count. No UI/browser/app controls, automatic Start/Stop, catalog, actual library, Comics/Comix, Open Library, unrelated prototypes, Git, version or release actions were taken. Known-failed-job recovery is excluded from this candidate and requires its own reviewed guard/fixture proof; this report authorizes no generic ArgumentError reset.

No open QA bug or new pattern alert in this candidate pass. Unique evidence/source snapshots are retained; finite owned processes exited and disposable temporary fixture contents were cleaned by their test contexts. **Current scoped verdict: GO.**
