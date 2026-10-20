# Bulk Retry / reacquire — targeted component source recheck v2

**Component source verdict: ACCEPTED WITH ONE ADVISORY MINOR.** No open Critical or Major finding identified in this targeted recheck. This is not formal RELEASE CLEAR, QA, runtime proof, deployment or live-operation authority. V1 findings/evidence remain unchanged.

Exact input: preserved scratch `shared/bulk-reacquire-source-review-packet-20261020-v2.json`, SHA256 `344c365cffef477c434dea5e30ebed8f5ebf85ff18f873a672bd79131dc08635`; implementation v2 Doc SHA256 `1aa438476f20c2f0a1f35bb27d3949cba665082b3b838a7f4d5467b73b079d93`. All 38 declared source/dependency byte lengths and hashes matched at entry; all 38 hashes matched again at completion. Exactly the seven authorized files differ from v1. Review-document hashes in the v2 packet also matched.

Scope: the four Major findings in review v1 SHA256 `56f0e3e488b2888ab84cab1b210952e5526f759094e261285156c7e0ecd35cb4`, their corrected production callers/lifetimes, changed test fixtures and the authorized HTML accessibility change. This certifies that finite source snapshot, not a Git commit range or a fresh full accumulated-diff review.

## Major dispositions

1. **Cleanup caller bypass — RESOLVED.** Historical intent is captured by the public wrapper before the operation-lock/enrollment wait. Its final Cleanup.resume receives that generation and the lock-free closing/draining guard. Automatic held cleanup uses an existing authorization generation, renewed by admitted Start, with each retention sweep taking its own snapshot before slow work/admission waits. A periodic wake cannot mint post-Pause intent or borrow permission from a newer Start. Cleanup.resume still uses its own final locked admission boundary. Rejected starts do not consume `_purge_tried`. Existing keep-file/source/publication safeguards remain.

2. **Stale bulk Event installation — RESOLVED.** Bulk rechecks its originally captured generation under the short control lock before installing its run/Event, then owner/generation/stop before launching. The target loop checks generation; `_retry_one` checks again after waiting for operation_lock. A target admitted at that existing boundary may finish and is counted honestly; later stale targets stop. No delayed path recaptures a fresh generation. Pause-completion semantics remain explicit.

3. **SQLite under control lock — RESOLVED.** Initial receipt persistence occurs after a brief exclusive run reservation and outside `_BULK_LOCK`. Persistence and thread-start failures retain honest stopped/blocked receipts; matching ownership guards reservation updates and checked launch. Existing snapshot/write/bookkeeping receipt saves also keep catalog waits outside that lock. No control-lock → queue-lock/operation-lock acquisition was added; callbacks under queue locks remain read-only and lock-free.

4. **Cleanup close/start race — RESOLVED.** Cleanup.close takes its existing lock, permanently closes/stops and snapshots the exact worker, then joins outside the lock. An earlier final-start holder is included; a later resume refuses. Merge closing remains permanent before joins, and the individual cleanup-to-audio handoff retains its original generation.

## Advisory Minor — one unrun receipt fixture cannot reach its assertion

`tests/test_bulk_retry_receipts.py:72`, `test_pause_does_not_resume_accepted_requests`, constructs `run` without `start_generation`. `_retry_all_work` now indexes that key before invoking the fake accept callback. Static inspection therefore shows a KeyError path instead of the intended accepted-request/Pause case. Add the captured generation to this fixture and repin it before claiming that test passed. No test was executed here; the other written race cases are not promoted into evidence by source inspection.

## Preserved boundaries and practical limits

Sources' scanner remains SHA256 `ebdcec3cd151cf43720dbbda114ce6fd2b2544d946b080db5e97d226a1f564bf`. Independently extracted the exact 7,491-byte progress_books function region (through its final newline, excluding the separating blank line): SHA256 `e61df445787ac21e9886ca2e2a8de47bb610d1d45d47a48aeeea391470bd112e`. Those preserved components' separate review stands; their behavior is not retested here.

The HTML lifecycle counts are now readable non-live text; only the meaningful status remains in the live region. Reacquire retirement/plumbing and its frozen safety dependencies are unchanged from v1. There is still no supported positive serious-damage classifier: the category is dormant, and ordinary decoder failure/partial PCM/imported JSON does not mark a book. This acceptance does not establish working damage detection or reconstruct the missing historical startup exception.

Developer reports 25 in-process DOM assertions and app.js syntax PASS. This recheck did not rerun them. Python remains UNRUN: 19 reacquire, 10 receipt, 25 race, two added HTTP cases, 17 separate DB-contention and 12 revised Audio cases; broader updated frontend regression also remains UNRUN. No actual native/media/app/process/library/DB/queue action is authorized or inferred from source acceptance. Old QA preparation packets with older source hashes remain stale.

## Exact changed-file pins

| File | SHA256 |
|---|---|
| merge_service.py | 288c9a62d9732701559069ea8329cee0a620b5be818304def192ca7ac903e61b |
| source_cleanup.py | 54d24e44452a8f1297b121d75efa60ceb5fb45e389405a0af3187e6f32253396 |
| web/index.html | 670233a0e751f8458ac7b0491912a0349dcc4ebf3727832cf1ecf45863c12c92 |
| tests/test_bulk_retry_receipts.py | f15a7ec5ca423c20934e55bd4adbaf98b55fadcf283179cebb0977c75c9c038c |
| tests/test_retry_start_fence.py | 595a8da650c6e3fbcef35adf5e26667225a89425354ab5f7535ec50283becdd9 |
| tests/test_bulk_retry_receipts_frontend.js | de6f5017abf10ed97aa770ee9b250f1eabb8f004c6618b0aa92387e03081c353 |
| tests/test_attention_frontend.js | 791524bc3e3593030c9b5982fb8dec259ba1c7932c5b254ee2a7b1f74e9bc272 |

All remaining 31 source/dependency pins are the unchanged verified v1 entries recorded verbatim in the v2 packet. Only this report was written; no code, tests, runtime, Git, hooks, live data or scratch cleanup actions were performed.
