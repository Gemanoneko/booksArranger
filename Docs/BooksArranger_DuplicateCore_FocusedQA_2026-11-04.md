# Books Arranger 0.25.0 duplicate-core focused QA — 2026-11-04

**Verdict for this slice: GO.** No Blocker, Major, or Minor defect was found in the duplicate-core focused pass. This is not a packaged-build or release verdict.

Source: committed and pushed `87b568143a5f803154c2564cae0487cc83fe0f6c` (`main = origin/main`). I tested a private `git archive` of that commit. All 18 changed source/test files matched the frozen implementation evidence by LF-normalized SHA256 before and after the runs. The implementation summary SHA256 is `3d57f8c57182ab4a57c021b01727c4537a49131d695c9e3ad9e0964e84843594`.

## Results

- Affected modules `test_automatic_media`, `test_storage_cleanup`, and `test_progress_rows`: **54/54 PASS** in 116.1 s. The normal automatic media test ran the first real codec conversion, then admitted byte-identical extra sources as a separate cleanup child; no second conversion or publication occurred. Child source removal, unchanged parent database row and output bytes, and one converted publication were asserted. The NFC/NFD single-M4B in-place case, changed-output/source refusals, cancellation and recovery, parent mismatch matrix, concurrent admission, partial retry, unknown removal outcome, startup inert receipt, and typed activity rows passed.
- Independent private historical-hold probe: **1/1 PASS** in 16.0 s. It seeded the prior same-generation `Held` duplicate reason without the new policy marker, pressed the normal automatic `Start`, and observed completed child cleanup of two sources, unchanged parent row/output, no second converter, and publication count one.
- Both `runOwned` executions returned exit 0, `closed=true`, `outputComplete=true`, no force or timeout, native `complete=true` and `zero=true`, with zero active or unsignaled processes at closure. The first run reported two transient incomplete sampling polls; its final native closure was complete and zero.

The private fixture map used short paths (`f/<number>`) so the existing 240-character output path guard was not exercised by the test harness. [Raw receipts, logs, private probe, and source hash manifest](Evidence/converted-duplicate_2026-11-04/futaba-duplicate-core-87b/summary.json) are retained. No product source was edited.

Scope remaining: the separately developing Open Source Folder latency and Koontz/4-M4B issues, followed by a new committed build, packaged QA, code review, and release gates. This pass made no full, hidden, live-library, Z: drive, or focus action. No new pattern alert arose.
