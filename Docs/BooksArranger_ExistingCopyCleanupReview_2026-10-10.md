# Books Arranger — existing-copy cleanup caller safety review

Date: 2026-10-10. Reviewer: Senua. Target runtime: v0.6.0. This is a bounded actual-caller audit, separate from the nine-dimension source review.

**Verdict:** CLEAR

Open findings: 0 Critical, 0 Major, 0 Minor. Actual execution is cleared for the exact caller and finite scope below after independent QA GO for the same pins. This report does not assert that production deletion has happened.

## Exact binding

- Caller: `scratch/retention-cleanup-2026-10-10/execute_verified_copies.py`, SHA256 `2d187a4338a9b8589a72f27dac4501198a947af2f5ab2d3b7f8f12f057e28fab`.
- Reviewed helper/runtime snapshot: `candidate-v3`, 99 files, source digest `a83f0ad64bc67b4c26d655f3fc02bfa737678c9bee8720d919417668af4d3f8f`; manual contract SHA256 `7a087010a570204d12b69e7a8e6a8e45b60cc73d421de52bb0b4607aa41663b1`. Recomputed all 99 candidate file sizes/hashes again: zero mismatches. Main source verdict remains in `BooksArranger_CodeReview_v0.6.0_2026-10-10.md`.
- Finite legacy contract SHA256 `75dfebae93844db9179391ded2fca1f6c1349f46d554d0be2656b6ba081df5aa`; read-only emitter SHA256 `185deb18f70766727342e4adef402eb24c1094ad6cdb0e096a02a2a21b6f0ca5`; evidence index SHA256 `00e7ac9eff9623bc9da2bec5b7db7b24fb691ad9950b76ea667ec9697dd0a895`. Independently hashed all nine indexed source/proof records with zero mismatches.
- Final no-disposition rehearsal receipt: `finite-caller-plan-verified.json`, SHA256 `3816b6dd660b1507d4e3e4496d8e5f4aeddc7225994c5cdcc84b456b73f9532f`. Independently read: execute=false, no_disposition_called=true, 95 verified receipt rows, 4,727,806,769 verified bytes, zero removed bytes, about 47.6 seconds. This is producer rehearsal evidence, not this reviewer's execution or independent QA.
- Parent reports accepted runtime commit `79eb2e7f5ab34b637166eb15eb504560dd273754`. VERSION/release documentation changes are permitted; actual executable .py/web files and runtime binaries must continue matching candidate-v3 pins. The caller checks and holds those executable bytes itself. Proof contract metadata originally names v2; its exact artifact proofs are compatible because v3 leaves storage deletion/normalization/receipt mechanisms unchanged and the executing caller independently pins v3.

## Finite ownership and proof

Only job IDs `9e04e700-ecf8-4807-8195-01a7a1d73bd6` (Eye of God), `0b6fedcc-2d95-46a9-a4a3-4192da37ff72` (MirrorMask) and `dc4874af-e132-47cd-93ab-85e5b0fbeea7` (Snapshot), plus repair `fc9c5525-5110-451c-bbe3-040f0e9950cb`'s single checked.m4b, can be invoked. Exactly three hash-bound legacy authorizations are inserted. Ordinary helper preparation additionally verifies the matching owned source snapshots, cover/final duplicates and completed recovery members for these jobs; unproved diagnostics/chapters and unique evidence remain preserved. No directory, recursive sweep, new conversion, other job or other project is admitted.

The four raw checked-copy hashes are independently anchored: Eye equals its immutable published final; MirrorMask, Snapshot and repair are reconstructed from their immutable full final bytes by reversing the six-byte chapter normalization and restoring an independently produced exact 59-byte FFmpeg entry. The inverse covers enclosing atom lengths and every stco/co64 relocation. Source inspection confirmed full raw equality, full forward normalized equality, saved media-atom equality, exact historical transform measurements and expected chapters. The overwritten 43-byte producer body is independently fixed by the pinned FFmpeg fixture, rather than adopted from the observed candidate. All 43 erased-body corruptions in the saved adversarial evidence normalize identically but fail the exact producer-entry guard; two changed offset tables fail final equality. Thus the authorized raw SHA256 values are not hashes of arbitrary observed contents merely relabelled as disposable.

The four checked files total 2,971,737,618 bytes; the broader 95-file rehearsal includes independently proved source staging, covers/metadata, temporary recovery and those four copies. Removal accounting must use the actual final per-file receipts and absence checks, not assume the rehearsal total was freed.

## Actual execution boundary

Caller lines 74-98 bind/hold the exact source/runtime/proof files, three staging ownership manifests, all three full final output hashes/parent identities, the repair journal and the corrected final. It probes the exact 40 chapter titles/boundaries using the pinned FFprobe binary under a suspended owned process job; no shell or UI is launched. These outer native handles remain open through the entire deletion sequence.

Actual mode acquires the existing exclusive `app.catalog_lock` before production catalog mutation. Lock failure stops; the caller never terminates unrelated processes. Under that ownership it refuses every unfinished audio/source/storage job, checks the three completed manifest/output-record hashes against the pinned proofs, and invokes only the cleared v3 StorageCleanup helpers. Each deletion still reacquires exact candidate handles, rejects reparse/junction/symlink/hard-link/extra-stream/unknown-content/Git cases, full-hash checks approved bytes, commits removal intent before disposition and records confirmed absence. Retained originals for Eye are protected and checked before its staging removal; the other jobs require exact durable retirement proof before any recovery purge.

The repair call uses the proof's exact raw hash/size, while the original parent, corrected final and completed repair journal remain held. The v3 helper independently derives the allowed corrected destination and checks its recorded full hash/size before disposing the exact retained copy. This closes the original parent-only protection defect at both helper and real caller ends.

Default rehearsal replaces disposition with a no-op and writes only a private minimal catalog. Its final correction changed only that rehearsal's repair preparation root; the --execute helper branch remains unchanged. It never records default mode as real removal. Actual completion requires every recorded file state to be removed and each name absent; any drift/error stops immediately and remaining files/provenance survive.

## Execution conditions and limits

Independent QA GO must name this final caller SHA256 and candidate-v3 digest. Run the exact --execute caller only after the existing Books service is stopped by its owner; successful exclusive catalog_lock is mandatory. Use an owned runner enforcing the total 600000 ms deadline and descendant closure: the script's block/checkpoint deadline is cooperative between blocking native I/O, while FFprobe has a bounded owned-process timeout. Do not replace a refused native operation with a weaker delete, rerun against an existing receipt, expand the three-job/one-repair scope, or change source/proof pins during the run. Stop on any pin, native, catalog, chapter or receipt mismatch; recovery/source state must be reassessed before another attempt.

Senua performed source/proof/receipt/hash inspection only. No actual/default caller run, media process, real deletion, restore, catalog write, app/focus, Git operation or disposable probe occurred. This separate report preserves the source review while Sully commits it. All caller/proof/rehearsal evidence remains available for independent QA and actual accounting.


## Approved execution runner — final pin

Runner `scratch/retention-cleanup-2026-10-10/run_owned_cleanup.py`, 2723 bytes, SHA256 `1aeef5503db89461dd6075fcbc578fb7222564fa0ed086cddeff1130556f6834`, is CLEAR for this exact caller. It accepts only default rehearsal or `--execute`; pins the Python binary, native module and caller; executes the native module from the exact checked bytes; holds all dependencies under native ancestor/file protection; starts only the fixed Python child suspended and hidden; assigns the reviewed kill-on-close Windows job before resuming. Its 600000 ms timer starts at wrapper startup, polls every50 ms, limits owned stdout to4 MiB/stderr to2 MiB, and waits for exact child exit. OwnedProcessJob checks/terminates only its assigned descendants and closes them before success is printed. The fallback after assignment failure terminates only the newly created process handle. No taskkill, PID/name scan, unrelated-process operation, UI or production-path deletion is added. Both temporary streams are scoped to the named scratch directory and automatically removed on close.

Approved QA invocation: `C:/Python314/python.exe "C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/retention-cleanup-2026-10-10/run_owned_cleanup.py"`. Actual mode adds `--execute` only after matching independent QA GO and service-owner shutdown; the caller still enforces its exclusive catalog lock and all proof/output guards. A wrapper failure, timeout, containment error or missing exit-confirmation is a failed run and must be reported without a weaker execution/deletion fallback. Native-job closure retains its reviewed three-second teardown check.

Senua inspected both wrapper versions and verified the final update changes only TemporaryFile placement into this task scratch. No runner, caller, QA test, probe or actual cleanup was executed by this reviewer. Final source/caller/proof pins above remain unchanged.
