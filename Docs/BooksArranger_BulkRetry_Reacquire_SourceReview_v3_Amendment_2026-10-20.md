# Bulk / reacquire — v3 fixture-only source amendment

**Component source verdict: ACCEPTED.** The sole advisory Minor from v2 is resolved in source. No open Critical/Major/Minor finding remains from this finite review. This is not QA, runtime proof or formal release clearance.

Verified packet SHA256 `e226aead0c591f981aec3ca2ada64accd10f4fdd4594692b3b9ff6df7303be5b`, `shared/bulk-reacquire-source-review-packet-20261020-v3.json`. All 38 declared file hashes/lengths match. Relative to v2 there is exactly one file delta: `tests/test_bulk_retry_receipts.py`, SHA256 `843f202b4ac66f328720dcfc9464561f8466aa877c990454302c3247450c8e66`. All 37 other source/dependency pins are unchanged; no product delta.

The named fresh-service `test_pause_does_not_resume_accepted_requests` now supplies `start_generation=0`, matching MergeService's default generation. Its accepted callback still sets stop; the case still asserts no resume and paused outcome. Removing only this new field from that exact method reconstructs the complete v2 file hash `f15a7ec5ca423c20934e55bd4adbaf98b55fadcf283179cebb0977c75c9c038c`, proving no additional fixture edits.

Implementation v3 addendum hash verified: `e5738765e0fa38b25b5ba331a32363090623fc820a93149e6b41eb136c5ee48f`. V2 review SHA256 `610ecd622335b7abb3ba12297cc016fdb94da492a61cea41bb6dad1849d25e67` is preserved unchanged; its four Major closures and limits carry forward. The positive serious-damage classifier remains unsupported/dormant.

All Python tests remain UNRUN. This amendment verifies the fixture binding only, not that the test passes. No full audit, tests, processes, native/app/media/library/DB operations, hooks, Git actions or scratch cleanup were performed. Only this amendment was added.
