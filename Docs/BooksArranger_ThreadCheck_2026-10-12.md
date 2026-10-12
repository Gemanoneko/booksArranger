# Books Arranger native thread check вЂ” 2026-10-12

Ender's isolated investigation concerns stable v0.12.1 failed audio job96f89af4-c6ce-46ad-a795-bd792445c6c1, attempt0e6812bc-41a7-47a3-85d9-a1c65f791c95. Live research remains online. No live job retry, source update, shutdown, release or original deletion was performed.

## Preserved observed failure and causal hypothesis

Read-only database capture is `scratch/native-thread-check-2026-10-12/failed-job-preservation.json`. The durable row is needs attention/checking sources, output=null; journal has only a checking-sources history entry at2026-10-12T08:00:42.599185Z and a failure with exception_class=ArgumentError, retryable=false. Reason is `argument 2: TypeError: expected LP_ThreadEntry instance instead of pointer to ThreadEntry`. There is no publication_intent in this journal. The existing journal does not store a stack, so no recorded stack is claimed. These database facts do not by themselves certify current source bytes or inspect every possible retirement/recovery journal.

`native_io.resume_owned_primary` in released v0.12.1 creates a new ctypes ThreadEntry Structure class on every call, then writes the shared kernel.Thread32First/Thread32Next.argtypes with that call's pointer type. Overlapping calls can replace the shared pointer identity before another caller passes its independently created entry. Both structures have the same layout/name but ctypes refuses the different Python class identity, matching the observed error. Audio source checking uses snapshot_manifestв†’probe/decoded_durationв†’run_ownedв†’OwnedProcessJobв†’resume_owned_primary; public metadata research concurrently uses _resolveв†’OwnedProcessJobв†’resume_owned_primary. The exact historical interleaving was not recorded. The producer subsequently reproduced the exact error using deterministic simultaneous binding before actual Win32 enumeration; this verifies the interop race mechanism without inventing a historical stack.

The isolated ABI candidate moves the same seven-field,28-byte ThreadEntry structure and thread-function bindings into Windows module initialization, so concurrent calls retain one pointer identity. It explicitly binds Thread32First/Next BOOL returns. It retains suspended owned launch, exact one-thread enumeration, GetProcessIdOfThread identity check, ResumeThread==1 and handle closure; no casts, global retry or weakened ownership checks are added.

## Frozen candidate and proposed finite verification

Snapshot baseline is stable documentation child a45566237eeeb8b79a15a16f7a046dcdab14ec3c, source0.12.1, target0.12.2-candidate. Only native_io.py and tests/test_native_thread_check.py differ. `scratch/native-thread-check-2026-10-12/application-packet.json` names full source/manifest/inner/outer pins. The fixed no-argument route is C:/Python314/python.exe followed by scratch/native-thread-check-2026-10-12/run_qa_receiver_owned.py. It extends the prior reviewed owned finite receiver route with the existing pinned containment implementation, hidden suspended children, private Windows Job ownership, bounded output drains, awaited exit and600000ms total deadline. No test was executed before route review.

Twelve unique tests were planned: six new tests plus six existing safety-boundary regressions. New coverage: deterministically interleave two calls after ABI binding, invoke actual Win32 snapshot/enumeration and reproduce the baseline ctypes error; verify fixed native enumeration retains identity and refuses impossible PID-1 without any foreign thread open/resume; verify actual Windows ABI size/offsets and signatures; verify no matching thread never calls ResumeThread; finish/drain two concurrent owned private children; enqueue a private WAV audio job and exercise actual source probe/PCM decode, then deliberately reject an invalid cover before creation/publication with source/cover bytes unchanged. Counts will be reported from fully qualified executed test IDs, not assertions or planned cases.

## Separate exact legacy-job recovery proposal вЂ” not implemented

The existing supported audiobook Resume runs pending jobs only. enqueue with the same frozen manifest returns the existing failed job. retry_failed accepts only already-classified prepublication I/O failures; this actual ArgumentError is classified false. Consequently no existing supported control can recover this failed attempt. The ABI patch leaves its row/journal untouched and must not label arbitrary ArgumentError retryable.

Under standing rule17, a separate narrow transition could recover this proven prepublication defect after a verified stable fixed owner is loaded. This remains a proposal for Senua's separate safety gate, not shipped code or permission to edit SQLite directly:

- Accept only an exact requested job/attempt identity with a preserved full failed-row digest, native ctypes ArgumentError signature above, needs attention/checking-sources state, checking-sources-only history and no output/publication intent. Refuse other ArgumentError, unknown history, changed attempt or partial/missing provenance.
- Verify the current loaded implementation uses the fixed stable ThreadEntry/binding contract, together with the coordinator's exact stable owner/version/source proof. On-disk VERSION alone is insufficient.
- Require idle audio work and independently inspect publication, cleanup/retirement and recovery records for that exact job. Any output/publication/retirement intent refuses replay; ambiguous or inaccessible evidence remains held.
- Revalidate exact current candidate/review revision and every frozen source path, native identity, fingerprint and full hash with the existing source guards; current bytes are not inferred from the historical failure. Revalidate again through the ordinary runner before any publication.
- Archive the complete original failed row/journal under its exact job/attempt identity before an atomic compare-and-swap to pending; never clear or overwrite historical evidence. Bound the transition to one exact job and preserve normal destination collision, output validation, verification before originals retirement and24-hour recovery.
- No automatic broad failure classification, native-process restart loop, direct database reset, altered publication/deletion policy or new GUI is proposed. If reliable defect provenance or native fresh-source proof cannot be established, retain this failed job and report the missing guard.

The concrete recovery implementation and its unrelated-error/source-change/intent-conflict/attempt-change adversarial fixtures are not part of the frozen ABI packet. ABI review/QA/release can proceed independently; recovery awaits its own reviewed concrete design.

## Producer result and independent receiver handoff

Senua rejected the initial PID0 fixture assumption because System Idle may enumerate threads. Before any execution, Ender corrected both enumeration/no-match fixtures to pid=-1, which cannot equal a native DWORD PID, and made OpenThread/ResumeThread fail-if-called mocks with never-called assertions. Original pre-review fixture/manifest/routes remain in pre-review-v1. Senua explicitly cleared corrected exact outer cf1fc2bfc06d53a1122f963dc3d72bc91faacd3988b4bba5dafd050faea62157, inner835d40776d48e525b9ddc7bcc20c804566b015c1393e7afad7c3347d4f7cdc9d, manifest77c5145ac68837ca65d91a26174dce8e4fbf3bab4e64e124bf70fe36853241e2 and source83cb44b8b5f079358cc6e70815c044015c00f3a74a11b1a1327ab9de5603d4fa before producer execution.

Actual producer passed12 distinct fully qualified test IDs:6 new native-thread tests plus6 existing safety-boundary cases, each suite Ran6/OK and exit0. Outer elapsed10.0184762s, inner9.9734818s. Native ctypes race reproduction, fixed concurrency refusal, ABI layout, two actual owned children and private WAV source admission/probe/decode then prepublication invalid-cover hold all passed. No streams were truncated; pre/post pins matched; owned processes exited and drained. Actual receipts are producer-check-receipt.json and producer-owned-receipt.json. No repeats were run.

Limit: the foreign-thread tests prove refusal before OpenThread/ResumeThread; GetProcessIdOfThread returning a mismatched PID is unchanged code reviewed statically, not directly exercised by a new fixture. Private tests do not certify current real-library sources, actual failed-job recovery, media publication/retirement or uninterrupted processing.

Applying the qa-handoff skill manual nonpackage contract: independent receiver uses identical source/runtime/test graph with separate receipt paths; receiver-contract.json names inner59b477cc618134608e8f2d29e80db2f0c13d5ff3968dcb54aefb9d8403a6dbb7 and outerbd9604a962ebdc9e4747293a49b6156f335c47638434be182f78a31aa0c228e6. Receiver awaits Senua exact-route clearance and Futaba independent execution.

Actual producer receipt:

```text
BOOKS_MANUAL_QA|tool=Books Arranger|target=0.12.2-candidate|source=0.12.1|HEAD=a45566237eeeb8b79a15a16f7a046dcdab14ec3c|dirty=true|source_digest=83cb44b8b5f079358cc6e70815c044015c00f3a74a11b1a1327ab9de5603d4fa|manifest_sha256=77c5145ac68837ca65d91a26174dce8e4fbf3bab4e64e124bf70fe36853241e2|python=pass|node=n/a(unchanged frontend; released v0.12.1 baseline)|package=n/a(manual nonpackage contract)
```
