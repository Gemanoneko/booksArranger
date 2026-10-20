# Bulk/reacquire v3 — sole test-fixture correction

V2 component source review closed all four Major findings. This addendum corrects its advisory Minor only: test_pause_does_not_resume_accepted_requests initializes run.start_generation=0, matching a fresh MergeService with no prior Pause. The captured generation is now present before _retry_all_work reaches the fake accepted-request callback; the callback still sets stop and the case still asserts no resume and a paused start outcome.

Only tests/test_bulk_retry_receipts.py changed; all other 37 source/dependency pins match v2. No product code or other test changed. The fixture and all Python tests remain UNRUN; no tests/process/native/live/Git operation was invoked. Earlier 25 actual DOM assertions and syntax result are unchanged evidence, not rerun here.

Fixture SHA256: 843f202b4ac66f328720dcfc9464561f8466aa877c990454302c3247450c8e66. Exact original block versus corrected block differs only by start_generation=0 in this one method.
