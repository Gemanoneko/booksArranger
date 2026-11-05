# Durable decisions: focused QA

**Verdict:** PASS for pinned source `c567adbaa8e7b57109ac9a5c979aee228fd7c3b1`.

The private bounded run passed 54 backend Python tests, 32 affected DOM scripts, and six actual production JavaScript to HTTP Handler actions: names, review, tracks, metadata choices, approve and file review. All three owners exited 0, closed with complete output and zero native residue. The archived app and index files are line ending normalized identical to the reviewed committed blobs. [Raw results, route records and hashes](Evidence/durable-decisions_2026-11-05/futaba-final/summary.json) are preserved.

The backend cohort covered acceptance while unrelated worker locks were held, restart and apply-once behavior, mid-Approve crash boundaries, and strict book/source/head binding. The DOM cohort covered source change acknowledgments, newer unsaved drafts, non-text and file path/size/modified identity guards, 403/404 recovery through the 422 conflict path, explicit retry after a terminal `needs_review` hold, overlay reopen and pending intent deduplication. The actual bridge sent one request per action through the committed renderer helper and Handler, then checked its receipt, status and book head; all six payload hashes matched and used distinct request IDs.

The bridge proves HTTP acceptance and reconciliation under private lock contention. It does not visually inspect a window or prove that every accepted action fully applies. This was source, DOM and private loopback verification; no packaged build, full entry check, installed app, live library or Z: source was used. This is not release clearance.
