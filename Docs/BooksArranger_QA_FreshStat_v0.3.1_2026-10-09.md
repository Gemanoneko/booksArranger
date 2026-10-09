# Books Arranger QA: opened-handle fingerprint patch v0.3.1

Date: 2026-10-09. **Verdict: GO** for the isolated scanner patch. No Blocker or Major identified. Frozen candidate marker is 0.3.0; Sully owns the forthcoming 0.3.1 bump. This is separate from unfinished merge/provider work and makes no claim that the production errors have been cleared.

Tested a copied pinned candidate from `scratch/stat-fix-2026-10-09/candidate`. Exact changed pins:

| File | SHA256 |
|---|---|
| scanner.py | 5f779b7a61eb30ac80f0ea4f18e9c1d1c21324f1e5694c64c9d50b0b2dd7f850 |
| tests/test_fresh_stat.py | d9e3af34fa4c831e8a9f05163ee3c3f466b44abc67ca46cd1e991c2aae01cc94 |

All two changed and eight unchanged runtime manifest pins matched after testing. Full preserved manifest: `scratch/stat-fix-qa-2026-10-09/accepted-manifest.json`, SHA256 13d12b57048e84a1705fc5287418e8261f4bfbafe3933150b8a1c0f41f728c59. Metadata, grouping, web backend, HTML/JavaScript/CSS and Tk app are byte-identical to the accepted v0.3.0 baseline. No new UX or screenshot check needed for this scanner-only change.

## Independent checks

**Six of six handle/cache checks passed.** A task-owned file wrapper prohibited `.read()` for fingerprint handles while verifying two opens and both closures. Initial/final fingerprint checks read no source bytes. Healthy cache reuse skipped the metadata reader, retained reviewed metadata and closed both handles. A simulated fstat exception closed its opened file; a metadata-reader exception retained a visible error and closed handles. An errored entry retried its reader and cleared only after success. Renaming the scratch source immediately afterward succeeded, providing an additional no-retained-handle check. Only designated private fixture bytes were created/changed/removed.

**45/45 frozen supplied Python checks passed**, including actual mutation during reading, replacement with equal size/nanoseconds but different file identity, review invalidation through the scan error path, exact integer nanosecond persistence, errored metadata retry, unrelated path-stat/cache regression, offline/stopped/resumed scanning, companion/type boundaries and group/filter/HTTP contracts. Ephemeral test HTTP servers were isolated from production. Three actual-script Node receipts also passed for fingerprint/form preservation, anthology role behavior, and connection/filter recovery. No native window or user's browser interaction.

## Independent read-only real-source verification

Selected exactly the 21 prior `File changed during read` rows from production SQLite in `mode=ro`; did not expand scope to the remaining empty M4B or scan a library. Copied those records into a separate private catalogue and ran the frozen patched `_file` with its actual metadata reader once per source. **21/21 succeeded**, elapsed 10.13 seconds. Every source's before/after streaming SHA256, size, exact integer modified nanoseconds, device and inode matched. Catalogue results stored the same size/mtime_ns and no read error. Fingerprint/cache code itself never streamed file bytes; the separate SHA256 passes were integrity evidence for this real-source check.

Preserved evidence: `scratch/stat-fix-qa-2026-10-09/runtime/real-proof.json`, SHA256 e5bc9676d4cac554a8ca038c1ec7c699d31c00047f2ed6e923eebe1c587934c0, plus its private catalogue and the task driver. These successful reads do not prove a physical library mutation caused the original mismatch, or that any file was corrupt. The changed-stat error guard remains strict; the fix fingerprints the opened source rather than relying on the path-stat result.

## Safety, cleanup and disposition

Own independent driver session 40331 exited code 0; the frozen regression command also exited code 0. Every opened handle in the independent fault tests was closed. Test temporary directories self-cleaned. The single remaining private source used for handle/rename checks was removed by the driver; snapshots, private catalogues, real-source hashes and unresolved diagnostic evidence are preserved. No persistent fixture service or browser lease was started for this patch. No production catalogue write, live scan/review/shutdown/restart control, source-library write, conversion, install or git operation occurred.

No new bug found. Existing general prototype tooltip polish remains **defer** to Daily Use and is unaffected. Final promotion/version proof and any authorized new discovery pass are separate Ender/Sully steps; production's 22 historical error records were not modified by QA. Future merge functionality needs its own pinned QA acceptance.