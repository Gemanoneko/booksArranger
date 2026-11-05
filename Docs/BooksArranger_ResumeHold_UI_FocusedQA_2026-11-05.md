# Resume hold status UI: focused QA

**Verdict:** PASS for the committed UI regression only.

Source commit: `885264ef7568fb94b1797a861ba9866a4a85d4af` (matches origin). All seven changed source/test files matched the frozen byte hashes. The private, bounded run passed 26 Python progress/quiet status tests and the three affected DOM scripts (`test_progress_frontend.js`, `test_0242_frontend.js`, `test_ruling35_frontend.js`). All four owners exited 0 with complete output, normal closure and zero native residue. [Raw results and hashes](Evidence/resume-hold_2026-11-05/futaba-ui/summary.json) are preserved.

The page keeps **Paused · 418 queued · 65 need attention** separate from **Metadata: Updating series · 0 of 292 books**. It does not infer the pause cause from an older, unrelated cleanup hold. While a real worker has claimed pending audiobook work without a durable running job, the page says **Checking pending audiobook work** and does not invent conversion progress. Queued Save says the edits are waiting in session memory; the tests also cover queue position, confirmed Cancel with the draft intact, refusal, lost reply and a durable success before showing Saved.

This verifies committed source with private SQLite fixtures and DOM doubles. It does not test a packaged build, a real window, codec work or live library data. The prior core boundary check is recorded separately. This is not release clearance.
