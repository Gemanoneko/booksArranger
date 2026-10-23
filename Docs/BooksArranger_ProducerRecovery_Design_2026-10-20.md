# Books Arranger — supported producer-recovery design

2026-10-20. Design for Judy/Senua review; no live recovery intent, closure, cleanup, restart or source mutation has been performed.

Measured case: candidate df1ff311-fb71-44ae-963f-ed6c8cdea04e, job 8a8a23d1-6b56-47ab-89f7-bf5e27125abb, Сказка. Current saved attention reason is “A prior producer is not durably closed; another attempt is not admitted”. Its historical working_attempts producer is active/producing and has no durable native process identity or boot proof. Process absence, old timestamps and a later application startup cannot retroactively certify closure.

## Public OS proof and finite trust boundary

Microsoft documents GetTickCount64 as milliseconds since system startup; wall-clock adjustments do not alter its resolution/counter. https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/nf-sysinfoapi-gettickcount64 . A strictly lower later 64-bit counter on the same Windows installation/catalog is therefore evidence of an intervening system startup, under the trusted Windows kernel/API boundary. This is a monotonic kernel-counter reset, not a wall-clock timestamp or PID liveness guess.

NtQuerySystemInformation(SystemBootEnvironmentInformation, class90) BootIdentifier was considered, but a stable Microsoft public guarantee sufficient for closure was not established. Do not depend solely on that undocumented class. It may be optional corroboration after review; it must not waive the supported counter-reset rule.

Bind the receipt to: native machine name (GetComputerNameW); registry Windows installation MachineGuid; system-volume identity/serial; exact native catalog identity and catalog-lock identity; frozen job ID, attempt ID, manifest SHA and candidate ID/revision/fingerprint; current kernel uptime. All values are captured by the backend; HTTP cannot submit them. Same-machine/installation/catalog checks are all required. Machine mismatch, catalog replacement, malformed values, unavailable OS APIs or non-lower uptime refuse closure and retain evidence/files. Moving a catalog to another machine must not qualify. Deliberate administrative OS/registry/volume spoofing is outside the trusted-kernel boundary; ordinary cross-machine studio handoff is explicitly detected.

Sleep/hibernation/FastStartup must never be accepted merely from user text, a new app PID or changed wall-clock. Equal/higher uptime remains unverified. This conservative proof has a practical limit: after a real restart the user must return before new uptime catches the recorded preparation uptime. If that window was missed, prepare again and perform a later ordinary Windows restart; do not claim the previous restart was not done, only that this proof did not establish closure. UX must state the factual verification result.

## Exact supported action contract

1. Prepare recovery is an explicit existing-attention action. Under normal review/operation/catalog ownership, re-read the exact failed job and unclosed attempt; refuse active current conversion, published dependency, changed source/review, ambiguous prior attempts, unsafe ownership or unsupported OS identity. Append a versioned producer_reconciliation_intent with all bindings and kernel counter; commit with FULL SQLite durability. Repeated preparation creates a separate superseding intent/history, never erases prior attempts.
2. Preparation has NO filesystem cleanup, source/audio writes, process termination, queue reset, metadata approval or conversion effect. Save/transport failure cannot display a restart instruction as a durable successful checkpoint. No automatic or scripted restart.
3. After a user-controlled Windows restart, normal app startup may DISPLAY whether the exact prepared receipt is eligible; it does not close an attempt, retry, queue, approve or delete automatically. Same binding + strictly lower trusted uptime permits an explicit subsequent Retry/recovery action. If unsupported/unchanged/mismatched, preserve state and expose the precise reason.
4. Explicit recovery atomically verifies exact intent/job/attempt/candidate/source bindings and records the new supported OS proof. It may mark the prior producer closed by that accepted boot-boundary proof, retaining the original attempt, receipt, reason and history. It then invokes the existing closed-artifact native inventory/hash checks. Unknown/unregistered files, alias/ADS changes, revised artifacts or unavailable originals stay held. No unknown artifacts are retrospectively adopted as disposable.
5. Normal existing working retirement/admission still controls any file disposal: exact original source proofs, no publication/recovery dependencies, native unique ordinary identity + full hash, durable per-file removal intent and native disposal/closure/name check. Only after those checks clear can existing Retry queue another attempt in a fresh owned directory. A confirmed boot boundary alone never authorizes deleting any file.

## Implementation ownership and acceptance

New boot_reconciliation.py should own OS identity capture, versioned append-only intent/proof schema, pure eligibility classifier, prepare/recover CAS and typed causes. WorkingLifecycle gets one scoped, proof-bound closure path reusing its native capture/retire routines; existing closed(stage) is not called with a fabricated producer_closed Boolean. Merge/review HTTP expose server-derived capability and the committed Judy action. No generic arbitrary job-reset endpoint or PID-kill API.

Tests: preparation no media/disk/process/queue side effects; same-boot refuses; strictly lower uptime same bound installation permits proof; wall-clock/PID changes alone refuse; higher/new-boot window remains unsupported; machine/catalog/manifest/fingerprint/revision/attempt changes refuse; stale intent conflicts; API unavailable/malformed refuses; same snapshot atomic CAS; unknown artifact retained; normal exact native cleanup and new admission only after accepted proof. Pure OS-provider doubles must be labelled synthetic. A read-only real OS identity check is permissible, but no real restart/proof acceptance or Сказка mutation is part of developer tests.

Pending technical review: whether same-machine/catalog identity set suffices for the studio handoff threat model, and whether public counter-reset proof is accepted as the closure precondition. Until Senua accepts it, this remains a design, not a claim that the current barrier is fixed.

## Measured historical-locality limitation (08:56:10 UTC)

A coherent read-only SQLite snapshot rechecked job 8a8a23d1-6b56-47ab-89f7-bf5e27125abb and attempt 095282da-b5ad-4215-99a9-467742d2cace. Manifest SHA256: 3570fdcca565fbb01bb2e08db4a36e7ce374ee87ede04303b83c72f45f1ef5b2. Job remains needs attention, attempt producer active/state producing. All 32 working_files are creation_intended with facts={} and no captured native identity/hash/size. Their lexical paths are under the current C: data/merge-cache/audio-staging tree. Journal has encoding/preservation details, no historical native staging ancestry, machine identity, boot identifier or process-owner proof.

Current native fixed-local path checks can establish locality NOW but cannot prove no earlier catalog/staging copy, clone, restore or remote-machine producer. That limitation must not be silently filled with an assumption. Jane has been asked to obtain the material user fact: did this exact 2026-10-19 Сказка conversion run on this Windows computer, with no subsequent copy/restore/clone of its catalog or staging? Any user assertion is recorded as explicit historical-locality evidence, distinct from native proof, and only accepted if Senua agrees that trust boundary. No/unknown must keep the attempt held or use a separately reviewed preserve-all quarantine route; it cannot qualify for claimed OS closure on this computer. VM memory/snapshot rollback is excluded from the supported proof contract.

## Actual retained-artifact inventory and required isolation revision

Read-only measurement2026-10-20T09:52:27.454Z: native local directory listing/lstat was compared with one coherent read-only SQLite transaction over working_attempts/working_files for job8a8a23d1-6b56-47ab-89f7-bf5e27125abb, attempt095282da-b5ad-4215-99a9-467742d2cace. All32 ledger rows remain creation_intended, facts{}, empty SHA,size0. Exactly32 regular entries were present, no unplanned names and no absent intents. Files include source00000.m4b1206080999bytes, checked.m4b1222939721bytes, cover.png1792246bytes and diagnostics/control files. This was name/metadata inventory only, not native ownership capture/full-byte verification. Full evidence: C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/fairy-producer-artifacts-readonly.json. Files/catalog/jobs were unchanged. Historical native creation identities are absent.

Later-boot proof can establish closure of the precheckpoint local producer under the reviewed assumptions; it cannot establish that current creation-intended file identities are the producer’s original artifacts. Therefore the proposed implementation must NOT call WorkingLifecycle.closed(...,True), promote these names to owned/closed files, hash them into deletion receipts, delete them, or claim normal retirement succeeds. Human locality evidence is a historical fact, never file ownership or closure authority.

### Proposed bounded supported behavior (requires independent acceptance before code)

1. An explicit user-origin fact is append-only, exact job/attempt/manifest/candidate fingerprint/native catalog/staging ancestry/OS-machine bound. Actual production fact is absent until Sergei answers. Unit fixtures may explicitly supply accepted human input. No inferred or automatically written production attestation; no new origin checkbox/control is invented.
2. Prepare recovery only durably saves a versioned checkpoint after exact current failed/unpublished job, current attempt/frozen manifest and local fixed-volume/native ancestry checks. It records trusted uint64GetTickCount64, OS/machine/system-volume identity and scope digest. It changes no file bytes, job queue, approval, producer state or working-file receipt. Current producer/changed binding/unsupported locality refuses.
3. A later explicit Retry may reconcile only if the trusted current OS/machine/native catalog/attempt identity and saved human fact still match, uptime is strictly lower than checkpoint, current producer is not active in the new lifetime, and full current SQL scope passes CAS. Equal/higher uptime waits; changed machine/native identity/restore ambiguity refuses. No PID absence, wall-clock subtraction or automatic restart/retry supplies proof.
4. In one FULL-durable BEGINIMMEDIATE transaction, persist exact typed closure proof and mark only the old attempt producer=closed,state=isolated_retained. Keep every working_files row, intent and byte untouched. The proof pins original attempt/manifest, origin/checkpoint/native scope and exact state transition. A retained old attempt is not called retired/cleaned. This is zero adoption or filesystem mutation, including no directory rename. Unknown old members are preserved, never followed or used as inputs by this operation.
5. WorkingLifecycle.admission_clear/admit may recognize isolated_retained ONLY after verifying that exact durable proof and unchanged attempt/native directory scope. They never pass this state to deletion retirement. Retire, Clear working files and any later cleanup must explicitly refuse removal of isolated old artifacts. Existing native/source-survival/reference guards remain unchanged for every other attempt. Old source/cover snapshots remain available as evidence; they are not substituted for unavailable original sources.
6. Existing Retry then performs its ordinary source/current review/identity/order/cover checks and starts a distinct newly generated job/attempt UUID/path. Old paths are disjoint and never overwritten/reused. If original sources are unavailable/changed, Retry still refuses; preservation is not a source-recovery bypass. No new conversion is automatically approved/queued just by Prepare or restart.
7. Attention reports the distinction truthfully: prepared/waiting for possible restart capability; after accepted closure, old working files remain retained and Retry starts a new attempt subject to ordinary checks. No Clear promise. A UI wording amendment to Judy§8 is required before rendering this revised semantics. Unsupported/save/transport/stale-binding failures preserve all state/files and show factual reasons.

### Proposed implementation/consumer boundary

New producer_recovery.py owns explicit origin records, immutable checkpoint/proof schema, trusted Windows identity/uptime acquisition, prepare/status and typed closure+isolation CAS. It exposes no automatic origin creation. WorkingLifecycle adds exact isolation-proof recognition and explicit no-retirement/no-clear guards, keeping existing normal runner closed() separate. MergeService owns operation lock, current-producer gate, attention capability and explicit Prepare/Retry integration. Existing HTTP action /api/audiobook/prepare-recovery accepts job_id only; no submitted boolean proof/attestation from that endpoint. UI follows committed Judy§8 plus the isolation amendment, using existing inline status/Retry controls. Any operator origin-recording entry must require the actual separately supplied direct user fact; no production invocation while answer is pending.

### Required private tests

Absent origin fact cannot Prepare or reconcile; sameboot/equal-or-higheruptime stays waiting; changed machine/systemvolume/catalog/attempt ancestry/manifest/fingerprint/ledger or current producer refuses; stale checkpoint/proof and replay refuse. Prepare leaves bytes/intents/producer/queue unchanged. Explicit accepted simulated fact+strictlower trusted fixture uptime yields only isolated_retained with every old file/intended receipt/hash unchanged, including an intentionally unknown old file. Retire/Clear refuses retained old artifacts. Normal source-revalidated newattempt uses a fresh UUID/path and preserves the complete old directory byte-for-byte; missing/changed originals still refuse. Save/CAS failure leaves producer/queue unchanged. Restart never queues a book. No test treats human input or source filename as native file ownership.

This revision is a design proposal only at this checkpoint. No producer_recovery implementation, production fact, reboot, old-file adoption/isolation/deletion or automatic Retry has occurred.

## 0.21.1 amendment: no-restart proof and verified removal (Sergei, 2026-10-23, rulings 4-7)

This changes the reviewed proof rule above, so Senua reviews it. Code: `producer_recovery.py` (`windows_boot`, `attempt_times`, `boot_basis`, `_isolate_after_boot`, `dispose`, `verify_retained`), `merge_service.confirm_origin_and_convert` and `_finish_recovery_child`.

**The second proof basis.** A producer process cannot outlive a Windows startup. So a startup that happened after every recorded activity of the attempt proves its producer is gone, with no checkpoint taken before the restart.
- **The startup instant.** It is the wall clock now minus `GetTickCount64`. The counter is read before and after the clock, and the larger uptime is used, which gives the earlier startup.
- **What cannot pass as a startup.** Sleep, hibernation and Fast Startup's kernel resume do not reset the counter, so none of them can pass. They only make the proof fail.
- **The attempt's own times.** These are its `working_attempts` row, every `working_files` ledger row, the job's stage history, and every old file's write time from the native fence. File times count because the Сказка producer wrote files five minutes after its last catalog write.
- **The margin.** The startup must follow the latest of these times by at least 10 minutes (`BOOT_MARGIN_MS`, slack for NTP corrections).
- **When the proof fails.**
  - No later startup gives `waiting_restart`/`restart_unproven` (R1a).
  - An unreadable time, a malformed reading, or a recorded time later than the clock now gives `unsupported`/`startup_unavailable` (R1b).
  - Both keep every file.

**Residual trust, stated plainly.** This proof trusts the Windows clock.
- **When it is wrong.** It is wrong in one case only. Within the same Windows session, the clock was moved forward after the attempt's last activity by more than the time between the real startup and that activity. Then the app would take a startup that happened before the attempt for one after it, and would treat a producer that may still be running as ended.
- **What is not affected.**
  - A clock change before the attempt shifts both sides equally.
  - A backward change only makes the proof fail.
  - Sleep, hibernation and Fast Startup cannot pass.
- **The app cannot detect that clock change.** No independent record of the startup or the clock is checked. That is the trust added beside Sergei's origin statement, and it is the point for Senua to accept or refuse.
- **What still holds if it is wrong.**
  - The new conversion runs in its own attempt folder.
  - The old files are held deny-write and deny-delete while it runs, so a live producer could not change them.
  - Removal re-checks each file's identity and full hash against the isolation record, so a file a live producer changed is kept.
- **For Сказка** the last write was 2026-10-19T09:55Z and the current startup 2026-10-22T05:07Z, 67 hours later.

**Every other gate is kept.**
- The origin statement still goes through `record_origin` (`actor: user`, the exact claim), now with Sergei's two statements verbatim.
- The machine identity, the native fence and full hash at isolation, the same-scope compare-and-set, the current-producer check and the write-deny lease while the child runs are unchanged.
- The proof is stored in the checkpoint (`basis: boot_after_attempt`, the boot reading, `started_ms`, `last_activity_ms`, `margin_ms`). `verify_retained` re-derives it from the saved reading and the saved scope and fence, so a tampered proof is refused.
- The checkpoint path is unchanged. Without a boot provider (unit tests) Prepare is still offered. The app always passes `windows_boot`, so a new book never needs Prepare.
- The statement is kept when the proof fails (UX spec R1a), so after a restart a plain Retry is enough (K3).

**Removal after verification (ruling 5).** A recovery child admitted on the boot basis is bound with `retained_disposal: true`, and its source cleanup stays enabled.
- **Copy flow only.** The child keeps the copy flow (`inplace_m4b.offered`). Its original stays a protected dependency of the retained attempt until the old files are removed, so it is never edited or moved in place.
- **When removal runs.** When the child completes, `_finish_recovery_child` calls `dispose` right after the child's write-deny lease on the old files ends. The checkpoint-basis path never removes anything.
- **What `dispose` checks.** A file is removed only when:
  - the child is completed, its validation passed, and its saved retry relation binds this checkpoint;
  - the folder is exactly `stage_root/<job>/<attempt>`, with no library root inside it or around it;
  - the folder holds no name the ledger does not list, and its ownership marker matches the job;
  - the file is a ledger name, held deny-write/delete while checked, with the same single-link native identity, attributes and full hash as at isolation.
- **Interrupted removal.** The intent (`disposing`) is durable before the first removal, so an interrupted removal resumes. Only a file missing after that intent is accepted as already removed.
- **Then normal cleanup.** `disposed` releases the original's protection, and the child's own source cleanup runs as for any converted book. As for every book since v0.16.8 (Sergei, 2026-10-18), its recovery copy is deleted as soon as the new book is verified; there is no 24-hour window.
- **Any refusal** keeps every old file and the original, and records the reason on the child's source cleanup.
- **Records left as isolated.** The ledger and attempt rows stay as they were isolated, so the proof chain stays verifiable. `retry_intent.guard` accepts `disposing`/`disposed` only for a disposal-bound child.
- **The details panel.** "Old working files kept" adds "They are deleted once the new conversion is verified." only for such an attempt (`removed_after_verification`).
