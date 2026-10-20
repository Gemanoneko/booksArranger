# Catalog contention fix: source implementation checkpoint

SOURCE candidate only; no live catalog change or worker restart. The user approved fixing Retry all and database locking. This slice fixes the catalog transaction boundaries from accepted design cb6e387b…54ae / Senua37d683f9…79b5; primary owns the disjoint bulk admission/UI changes. Actual historical lockholder remains unknown.

`progress_books` now acquires group_lock→_progress_lock. A current grouping revision/algorithm stays read-only; stale grouping is rechecked in the existing bounded fresh IMMEDIATE DB transaction. Approval/context/retirement, replacement relations plus exact structural_guard(db=caller), publication binding lookup and retry guard results are frozen from one read snapshot. Every connection closes before cover is_file/output stat; there are no replacement get/representative new-connection calls in the filesystem phase. Counts remain descriptive snapshot observations, not new publication/deletion/admission authority.

Scanner claims/completion/stops/failure checkpoints and captured file/directory SQL now use bounded replay-safe transactions. Whole metadata reads/enumeration/hash/native reacquisition never replay. Root/generation/task direction and row, file, group/context review, retirement, owned output, relocation and reacquisition markers are compared before applying captured data. Catalog CAS holds are a distinct RuntimeError type, never a source-read ValueError. Outcome, checked/reused/error counter and task completion commit together, so retry cannot double-count. An obsolete generation cannot overwrite a new scan state.

Existing primary hooks are retained: original root_scan_lease, zero-error reconcile_scan exactly ONCE outside SQL replay before missing updates, forced-fresh marked paths and original lease teardown. Reconciliation is not re-executed after DB contention. SQLite busy retries use unchanged existing30seconds/60attempts and<=250msconnection waits; SQLITE_BUSY primary-code family only, no message-text/SQLITE_LOCKED retry. Exhaustion preserves pending work and fails visibly, without inventing media errors/clearing reviews. No WAL/timeout workaround.

If even the bounded failure-checkpoint save exhausts BUSY, a per-root volatile hold is projected only after worker exit and after rereading the same saved generation; explicit failure_durable=false. Other source/generation rows are not overridden. If the generation cannot be read, a typed CatalogHold reports status unknown and does not fabricate zero counts or durable failure. The RAM-only fact disappears on restart; it is not a recovered durable receipt.

Changed ownership: progress_books only in shared merge_service.py; scanner source_status narrow projection, _run_sources/_run and _directory/_file SQL boundaries; NEW catalog_contention.py and tests/test_catalog_contention.py. Primary reports adding the test pattern to check-desktop; no other Merge region was replaced. Shared files were reread before each bounded edit.

17focused regression methods are WRITTEN_UNRUN: transient rollback without duplicate counters, real private cross-connection release, bounded persistentbusy, nonretryLOCKED/untyped errors, stop, obsolete generation, metadata/enumeration once, concurrent manual review preserved, once-only native-hook seam, RAM-only/unknown generation status and progress guards/snapshot-close-before-filesystem. No Python compile/import/test process was launched; no PASS or native result is claimed. The current formal/engineering route must be reviewed separately.

|File|Bytes|SHA256 at checkpoint|
|---|---:|---|
|catalog_contention.py|5025|70cf0a3eeefab4b670fe9a1f35590e85b3c0188028c6a2899706344e43fc174b|
|scanner.py|48163|ebdcec3cd151cf43720dbbda114ce6fd2b2544d946b080db5e97d226a1f564bf|
|merge_service.py|208336|a85ac47b7789ab5a6d03fb9ad69e62f95d55d6ff5dbc010dfb771deeb7225705|
|test_catalog_contention.py|17505|5ff724fe0581594f1ddc62d3bf18952bd37915a3f507bb87c62d474914e018e7|

`merge_service.py` may change in primary-owned bulk regions after this observation. The exact owned progress function SHA is `e61df445787ac21e9886ca2e2a8de47bb610d1d45d47a48aeeea391470bd112e`; final combined-source freeze is still required. Packet `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/catalog-contention-implementation-source-20261020.json` SHA `37119894cc5fccda3251722d35b74a52deb1d2edc6f58a9250213a484800b6c4` contains each owned region hash and explicit test limits.

No live DB edits/API POST/scan/retry/research/queue/start-stop, NAS enumeration/move, native/process/RNG/compiler/global hooks/QA infrastructure/Git actions occurred. Independent source review and actual appropriate QA remain before any deployment or supported live continuation.
