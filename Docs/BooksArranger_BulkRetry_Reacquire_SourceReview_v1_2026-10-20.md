# Bulk Retry / reacquire — component source review v1

**Component verdict: CORRECTIONS REQUIRED.** Critical: 0 identified; Major: 4 open; Minor/limitations below. This is a frozen component source review, not RELEASE CLEAR, QA, execution, activation or deployment authority.

Input packet: `shared/bulk-reacquire-source-review-packet-20261020-v1.json`, SHA256 `b38635e6aa474d85872c97be1088ff0dbd3bcf721234ca34986de6768dbb5d62`, under the preserved session scratch directory. All 38 declared file byte lengths and SHA256 values matched on entry. Implementation Doc SHA256 `be26ef32813c7548353c3699485a1a274f69b0ebf685dce9e0801dd84b1a2e8c`; Pause/start design v2 `9cea14498d618997d5a6c0105be5333cd2c2f8d3caca7429010c54da6e2ffe58`, review `c4818da18cac445ce239c180846759cca66aa18720f8172a70e5ee05ad819567`.

The packet's complete 38-entry ledger defines this review's exact source/dependency snapshot; no Git range is certified. Primary's subsequent authorized corrections need a new frozen packet and targeted recheck. Concurrent Sources' DB implementation is separately reviewed; it is not recertified here.

## Major 1 — default cleanup callers bypass completed Pause and closing

`merge_service.py:start_historical_cleanup` (~711) and `_finish_held_cleanups` (~857) call `cleanup.resume(..., follow_audio=False)` without admission_check/token. That method clears its stop Event. A historical request delayed by operation/enrollment work can therefore launch after a later completed Pause. The automatic retention sweep can also restart source cleanup without a new Start. Both bypass Merge's permanent closing predicate until the cleanup component itself closes. Their disclosure in the implementation Doc does not establish safe admission.

Required finite correction: capture historical intent before its operation-lock/enrollment wait; propagate its generation and closing/draining predicate through final cleanup admission. For the automatic held-cleanup action, retain the authorized retention-start intent, invalidate it on Pause, and renew only through an admitted explicit Start. Each sweep must retain that intent before waiting for retention admission; it cannot borrow a newer generation after waiting. Merely capturing a fresh token every 60-second sweep after Pause recreates this defect. Preserve existing explicit historical intent and keep-file/publication/source guards. Do not change unrelated retention purge policy. Test completed Pause, incomplete Pause, close, delayed enrollment, delayed sweep, and a fresh explicit Start separately.

## Major 2 — stale bulk request installs a new uncancelled Event

`retry_all` captures its generation before `attention_summary`, then installs a new `_retry_all_stop` under `_BULK_LOCK` without rechecking the captured generation. If Pause completes during the summary, it stops only the prior Event. The new worker's target loop checks its Event/draining but not its captured generation, so stale submission proceeds after Pause. Its eventual queue start refuses; that does not cancel the preceding stale submission.

Required finite correction: owner/generation-check the run/Event installation and thread launch; retain the captured generation through each target's operation-lock wait and check before admission. Do not recapture a fresh generation. A target already admitted before Pause reaches its boundary remains honestly counted/durable; stop later targets. Tests must cover Pause between capture and Event installation and while a target waits on operation_lock, not only Pause after an Event already exists.

## Major 3 — catalog persistence holds the control lock

`retry_all` executes initial `save_bulk` and connection commit inside `_BULK_LOCK` (~1700). A SQLite busy wait therefore blocks Pause generation invalidation/stop delivery and Start capture. This violates the reviewed short-control-lock/no-long-SQLite condition and matters directly to the catalog-contention failure being repaired.

Required finite correction: reserve a single run owner under the short lock, persist its submission receipt outside that lock, then perform an owner/generation-checked launch. Handle persistence/thread-start failure truthfully and release only that owner's reservation; retain actual accepted requests. `_save_bulk_receipt` already demonstrates the bounded snapshot → catalog I/O → brief bookkeeping shape. A deterministic busy barrier must show Pause can complete while receipt persistence waits.

## Major 4 — cleanup close does not share final-start boundary

`source_cleanup.py:close` writes closed/stop and snapshots the thread without `cleanup.lock`, unlike resume/pause. A resume holding that lock can pass its final callback, then close can set stop and inspect an older/absent thread and return, and resume can create a new unjoined thread afterward. The Event should prevent new source work, but does not prove thread teardown; the new thread can still enter its initial catalog read after close returns.

Required finite correction: under the existing lock set closed/stop and retain the exact worker reference; release the lock before joining. Keep self-join handling truthful if relevant. Exercise the final-check/thread-install interleaving with close; do not use stop=True as closure evidence. This is a narrow existing component-lifetime correction.

## Other source findings and limits

- No additional retirement safety defect was identified in the bounded reacquire path. Enrollment requires an internal typed assessment, exact job/source snapshot and same-attempt durable producer closure. Reconciliation requires the accessible retained root, complete zero-error generation/queue, every frozen member absent or different by full held-file SHA, final reappearance checks, unchanged marker/context/whole-job state, publication/dependency/overlap guards and atomic archive/scope release. It deletes only confirmed-missing inventory rows; it performs no filesystem deletion. Same-path replacements retain inventory and receive a new candidate identity without inherited approval. Anthology parent folders are not deletion ownership.
- The positive damage classifier is deliberately **unsupported/dormant**: `mp3_tag_repair.assessment` always refuses. Ordinary decoder errors, JSON receipts and callback booleans cannot activate it. Thus this source supplies guarded plumbing/category projection, not functioning serious-damage detection. Iron Inferno is not evidence for this category. Any future positive producer requires its own source-specific evidence and review.
- The core guarded Start path captures before waits, uses a lock-free generation/draining/closing callback under queue locks, retains the per-worker cleanup-to-audio handoff, reports old-checker/pending-owner conflicts as retryable busy, and invalidates close before joins. The accepted guarantee concerns completed Pause; an already-admitted current operation may reach its existing checkpoint while Pause is in progress.
- Bulk accepted-request counts are separated from actual target progress. Pending requests leave Can retry; selected/all share the latest receipt; typed/stale errors remain distinguishable and HTTP selection fields are checked. The v1 defects above prevent a complete component pass despite those changes.
- Advisory Minor: the source's post-assessment persistence error handling still has no exercised production positive path. Do not describe a future classifier/marker as verified merely because mocked typed inputs exercise the bridge.

## Evidence and exact pins

Core v1 pins: Merge `b242440be7a6495bdc26a8e3280d2796f02062b1d92b75ce8e46bf62410207e2`; AudioJobs `c3af1f9805b0ba49fa485830502905fd0126bbad39df52870bba370186f03a0b`; Cleanup `8e08e2824dc56d0bf38a498ad1201b9b1d0c80826a807985cc1b761e16aade37`; reacquire `a798b1fc12af460eb627e695da2a8f6e9aab55894aa2afdf90f74026742dc1d5`; groups `b28826c07cfe8c8a5b2cffb157b815c6a967a8e9cc0cd736b2e75312d345760f`; readmission `24cb3517dcd2042be2070dad88109dba7984de3c555afe7f0008b66b73fd4ec1`; scanner `ebdcec3cd151cf43720dbbda114ce6fd2b2544d946b080db5e97d226a1f564bf`. All remaining renderer/server/test/native/dependency pins are in the verified packet.

Read the relevant production callers, retirement/scan/group/review/native consumers and written race/receipt/reacquire tests. Tests were not executed. The supplied packet reports 23 in-process DOM assertions and app.js syntax success; this review did not independently rerun or upgrade those into QA evidence. Modified/new Python suites and broader frontend regression remain unrun. A new frozen corrected packet must retain all unchanged pins or identify each authorized delta.

Only this report was written. No tests, processes, native/media actions, live DB/API/library operations, hooks, Git changes or scratch cleanup were performed.
