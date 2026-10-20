# Bulk Retry / reacquire — correction packet v2

SOURCE review only. Supersedes v1 implementation pins; original evidence and findings remain preserved. No QA/release/deployment/live-operation authority.

## Four frozen v1 findings corrected

1. Every Merge cleanup start now supplies a captured admission generation. Explicit historical cleanup captures before operation-lock/enrollment waits and can only start that finite saved action. The automatic held-cleanup policy keeps its existing authorization generation; Pause invalidates it, and only an admitted explicit Start renews it. Each retention sweep snapshots that authorization BEFORE slow work/admission waits; an old sweep cannot borrow a newer Start. Periodic wakes do not create a fresh intent. Other retention purge/folder policy and native/source/publication safeguards remain unchanged.
2. Bulk captures before summary, rechecks under _BULK_LOCK before installing run/Event, rechecks owner/generation before launch, checks generation per target and after its operation-lock wait. Targets already admitted at the in-progress boundary remain honestly counted; subsequent stale targets stop.
3. Initial bulk receipt persistence is outside _BULK_LOCK: reserve one owner briefly, release control lock for snapshot/write/commit, then checked launch. Failure/paused reservation cannot submit requests, thread-start/persistence failures are visible, and only the matching owner's state is released. UUID/time preparation is also outside that lock.
4. Cleanup.close sets permanent closed/stop and snapshots the exact worker under its existing lock, then joins outside it. A prior guarded start is included in that snapshot; a later start refuses. Merge closing/draining permanence and guarded cleanup-to-audio handoff remain.

Pause still means completed-Pause semantics, not zero activity between click and response. New Start during incomplete Pause is explicitly busy; delayed stale generations cannot clear its completed stop. Overlapping stale _resume_pending/_resuming does not silently consume a fresh request. No new scheduler or long-I/O lock was introduced.

Judy's final accessibility correction: all six lifecycle counts are readable non-live text in retry-all-count; aria-hidden was removed. Meaningful request/phase/failure/unavailable changes remain in the existing live status. No controls/layout/focus behavior added.

## Exact evidence and limits

ACTUAL: 25 focused real-app DOM/HTML assertions ran in-process; app.js syntax PASS. Includes readable non-live counts, same-phase count updates without live reannouncement, shared newest all/selected result, no duplicate/network resubmit, pending request versus actual job distinction and stale blockage suppression. No process/native/RNG/media/API/library operation was invoked.

Python remains UNRUN: 19 reacquire, 10 bulk receipt, 25 deterministic race cases, two added HTTP cases in the existing 21-case file, 17 separate DB-contention cases and 12 revised Audio cases. Updated broader frontend suites also remain UNRUN. There is no admitted Books Python QA route; no wrapper was invented. Race cases cover original intent capture, delayed enrollment/sweep, old sweep after renewed Start, blocked persistence while Pause completes, per-target operation wait, synchronized close/start and existing v2 conditions. These are written counterexamples, not runtime proof.

Reacquire safety/category plumbing remains dormant: there is NO supported positive serious-damage producer. Ordinary decoder failure/partial PCM/JSON never marks a book. Iron Inferno's zero-loss ID3 trailer repair is separate. No real marker or historical origin fact was persisted. Historical 69 startup exception was not recorded; it is not reconstructed or blamed on an unproved writer.

All unchanged source/dependency pins are retained from the 38-file v1 ledger. Exactly seven authorized files changed: Merge, Cleanup, index, bulk Python test, race Python test, bulk DOM test, existing attention DOM fixture. Sources' scanner ebdcec3c… and progress_books region e61df445… remain byte-identical. Audio tag sources unchanged. Test patterns remain declaration-only; all old preparation packets with obsolete source hashes are stale.

The complete JSON packet includes exact pins, authorized deltas, dependencies/callers, test counts, and preserved parallel regions. Updated callers: public start_historical_cleanup → operation-locked helper → guarded Cleanup.resume; retention loop's pre-admission captured authorization → guarded _finish_held_cleanups; public retry_all → owner reservation → external persistence → checked launch → per-target operation-lock generation guard. All Merge audio/cleanup resume calls now pass admission_check/token, and the per-worker handoff retains that token.
