# Books Arranger 0.25.0 r2 correction focused QA — 2026-11-05

**Focused verdict: GO.** I tested pushed source `0ec4971169a70d57a407ae1a9ef6bf96227724d4` from a private Git archive. The eight primary correction files and one Tolkien fixture file matched their frozen source hashes before and after testing.

All previously failing full-entry modules plus the Source Folder dispatch class passed **193/193** Python tests in 62.0 s. Four affected frontend scripts passed, including the previously failing Iron/Skazka label case. Every bounded owner returned exit 0, closed/output-complete, and native zero. The Names read response was 0.143 s and folder dispatch was 0.011 s under held unrelated worker locks.

[Raw receipts, logs, runners and source hashes](Evidence/converted-duplicate_2026-11-05/futaba-r2-corrections-0ec/summary.json) are retained. This focused pass did not run a full entry, hidden check, live library, Z: drive or focus action. The r2 packaged full gate is running separately.
