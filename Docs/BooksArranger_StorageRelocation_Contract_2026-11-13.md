# Storage relocation compatibility contract — 2026-11-13

Status: **implementation contract, not migration/release clearance**. Sergei has explicitly authorized the complete compatibility update before moving Books Arranger. Earlier separate-storage/NAS work was cancelled; this authorization covers shared C:→I: compatibility plus the subsequently requested installer data selection and uninstall keep/cleanup choices. No live move, pause, install or uninstall is authorized by this document. Judy owns lifecycle UX. The separate chat owns the shared folder move.

## Safety model

Preserve immutable historical receipts, full metadata/history/settings and source/recovery bytes. Never replace a native identity in an old receipt or globally resolve/allow reparse paths. Current handles and returned native facts always remain actual facts. A separately verified explicit relocation generation may bridge an **expected historical** file/directory identity to a copied native identity at exactly the same managed logical path. It does not prove a producer closed, establish its boot/locality/origin, reset request limits or approve a book.

## Manifest v1, byte-pinned external selection

The pure validator is `storage_relocation.parse_manifest(raw_bytes, expected_sha256)`. Strict UTF-8 JSON, duplicate keys/NaN/unknown fields refused, maximum 64 MiB and 100,000 file+directory entries. Arrays are bounded and native facts are immutable after parsing. No filesystem action or runtime authority is granted by parsing.

```json
{
  "schema": "books-storage-relocation-v1",
  "generation": "canonical-lowercase-UUID",
  "catalog_id": "canonical-lowercase-UUID",
  "source_root": "C:\\Antigravity Projects",
  "target_root": "I:\\Antigravity Projects",
  "scopes": ["Studio Illuminati\\WIP\\Books Arranger\\data"],
  "source_snapshot_sha256": "64-lowercase-hex",
  "directories": [
    {"relative": "", "source_identity": [1,0,1], "target_identity": [2,0,1]},
    {"relative": "Studio Illuminati", "source_identity": [1,0,2], "target_identity": [2,0,2]}
  ],
  "files": [
    {
      "relative": "Studio Illuminati\\WIP\\Books Arranger\\data\\example",
      "source_facts": {"size":1,"modified":1,"dev":1,"ino":3,"identity_method":"FileIdInfo128","identity_api_error":0,"identity":[1,0,3],"links":1,"attributes":32},
      "target_facts": {"size":1,"modified":1,"dev":2,"ino":4,"identity_method":"FileIdInfo128","identity_api_error":0,"identity":[2,0,4],"links":1,"attributes":32},
      "sha256": "64-lowercase-hex",
      "receipt_classes": ["working-file"]
    }
  ]
}
```

Example omits required intermediate directory entries for brevity: actual manifests require complete directory ancestry and the native parent of every file. Roots are non-overlapping absolute local Windows drive paths, never drive roots/UNC/device paths. Relative paths reject traversal, ADS, device names, ambiguous trailing dots/spaces and case-normalized duplicates. Managed scopes are explicit, non-overlapping and cannot include arbitrary sibling projects merely because the shared root is aliased.

Native file fact keys are exactly those returned by `VerifiedFile.facts`: size, modified, dev, ino, identity_method, identity_api_error, identity, links, attributes. Links must equal one, identities nonzero, no reparse/directory attribute on files. Receipt classes: working-file, staging-artifact, cleanup-file, recovery-copy, retained-source, index-leaf, index-journal, repair-copy; storage-directory is reserved for directory comparisons. **Producer/process/boot/origin closure is not a relocatable receipt class.** Extra file-copy ownership inventory must remain distinct from authorization to bridge an historical receipt.

## Explicit per-installation selection and leases

Proposed desktop settings field `storage_relocation: {manifest: absolutePhysicalPath, sha256: exactDigest}` is opt-in. Absence preserves second-computer/current legacy behavior. No global I:/Z: default. Malformed selection, absent target/manifest, wrong SHA or unavailable storage fails closed before backend or default fallback state is admitted. The shell passes only its explicitly validated descriptor selection to backend, read-only checker and updater-integrity children; an arbitrary inherited relocation environment cannot authorize a child.

Byte pin authenticates the explicitly selected generation, not a forever-frozen mutable catalog. A persistent per-catalog activation record binds catalog_id, generation, descriptor digest, source snapshot digest and lifecycle state. The full database SHA is the offline source-snapshot proof only. After normal database writes it is not recomputed as a launch identity.

Activation must require both source and target ownership fences, source process/worker closure, the complete verified transfer and a durable compare-and-set transition. Copied `.lock` pathnames are independent locks and cannot prove mutual exclusion. New backend holds its actual target catalog owner plus the active generation lease through a historical comparison and its final disposition/CAS. A pure predicate cannot replace this lease. An ancestry bridge receives explicit operation path, catalog_id and generation, not just arrays to translate.

Source fencing must prevent the original pre-update binary from reopening an independent preserved database. A table flag understood only by the new version is insufficient. The operator must establish and verify a reversible native write fence (including original database and all sidecars/recovery state), retain the original security descriptors/owner and fail if the requested fence cannot be proved. The shared-folder coordinator must account for the original root's later backup name/identity. No destructive operation on a target begins before source fence readback and target activation commit. Rollback cannot blindly remove the source fence while target has new unreconciled writes.

## Exact junction access

The alias is allowed only within configured managed scopes, never for arbitrary paths under C:\Antigravity Projects. Before allowing the single configured mount-point ancestor, retain its actual OPEN_REPARSE_POINT handle denying WRITE/DELETE, parse a bounded native FSCTL_GET_REPARSE_POINT response, require the mount-point tag and exact expected local substitute target, and separately retain every ordinary physical target ancestor/root. All other reparse entries keep the existing refusal. The alias and target leases last through the operation's final use, disposition and durable CAS; both are revalidated. Real competing deletion and SetReparsePoint attempts must fail in private fixtures; names/flags alone are not proof.

If a caller chooses physical I: directly, historical references still require their explicit path/location binding; changing dataDir alone does not reauthorize copied artifacts. Native APIs, freshly created files, runtime/process proof images and kernel-internal raw identity checks stay strict. No global `ordinary().resolve()`, recursive JSON identity substitution, fake native facts or overloaded equality is permitted.

## Historical comparison contracts

`historical_facts_match(logical_path, actual, expected, receipt_class=..., catalog_id=..., generation=...)` is a pure predicate only. It requires the exact scoped file entry, receipt class, catalog/generation, complete old expected facts and complete new actual facts. Callers must still perform their existing hashes through the same retained native handle; a bridge cannot skip full content verification at delete/reuse. Ordinary exact comparisons remain sufficient for post-migration freshly captured receipts.

Directory identity/ancestry bridges require all existing continuity/root/final-parent checks and actual held directories, plus explicit per-path old/new directory entries. In-place repair/locality/origin records use typed adapters or remain safely held. A file-location binding never rewrites immutable whole-proof hashes or turns an old uncertain producer into a closed producer.

## Offline operator transactions (implementation responsibilities)

1. **Prepare source:** acquire actual catalog ownership, verify supported graceful closure and no active producer/repair/cleanup writer; capture existing schema/history/pending decisions and source security/native identities. Refuse unknown formats or ownership. Install reversible source write fence and verify it before releasing anything that could admit an old writer. Create a consistent closed/backup-API catalog snapshot and full file hashes under managed scopes. Preserve WAL/SHM originals and all recovery state.
2. **Coordinate copy:** the shared-folder owner performs its authorized tree copy/move. Operator never moves the shared studio. No second migration runs concurrently. Source tree and rollback original stay intact; unknown/reparse/hardlinked/ADS entries refuse or are explicitly held, never silently skipped and called complete.
3. **Seal target:** acquire target ownership, verify schema/history/state against frozen source, file membership/full hashes and actual new native identities. Capture all directory mappings and typed receipt classes, including both separate OpenLibrary DB/journal leaves. Seal a CREATE_NEW immutable descriptor and independent verification receipt. Partial/crashed operation is not activation authority.
4. **Activate:** verify source fence and target leases again; append/CAS the exact catalog generation and publish per-install selection atomically. Verification admission initially suppresses cleanup/conversion so copied work is independently inspected before destructive maintenance can run. Only an explicit verified activation opens normal admissions. Restart recovery recognizes exact completed phase receipts; it cannot replay a copy or activation under a different target.
5. **Rollback:** fence/close target, capture any new-state backup, reconcile new decisions/jobs/publications/source deletions/recovery obligations, then restore source protection/configuration via exact retained security descriptors. No stale snapshot overwrite. After normal new writes, rollback may require a reviewed reverse-transfer or repair forward.

## Consumer inventory and exact ownership split

Method: literal grep for `facts()`, parent_identity, backup_facts, old_identity and new_identity across production Python, excluding tests/Docs/scratch/build-cache/dist/node_modules, found 35 modules. This is a review inventory, **not** an assertion all 35 require edits.

| Boundary | Candidate integration modules | Required treatment |
|---|---|---|
| Common native access | storage_relocation.py, native_io.py | Strict immutable parser; scoped alias/physical leases; explicit comparison bridge; raw actual identities unchanged. |
| Catalog/startup | catalog_owner.py, desktop_catalog.py, desktop_backend.py, web_server.py, desktop/main.js | Per-install selection, finite trusted child environment, ownership/generation admission, no silent storage fallback. |
| Working and published staging | working_lifecycle.py, storage_cleanup.py, audio_pipeline.py, merge_service.py | Raw row/CAS key preserved; resolve exact physical operation path/facts through typed binding; closed producer and same-handle hashes unchanged. |
| Recovery/source deletion | source_cleanup.py, recovery_retention.py, replacement_retirement.py, reacquire_sources.py | Map only moved recovery artifacts; Z source/output identities stay strict. No new deletion authority. |
| Repair/retained provenance | producer_recovery.py, inplace_m4b.py, chapter_repair.py, current_audiobook.py, replacement_media.py | Keep whole-proof origin/boot/locality hashes immutable; typed physical-storage evidence or explicit safe hold. |
| Native index stores | openlibrary_index.py | Explicit owner/completion receipts for DB **and journal**; immutable ready generations distinct from mutable import state. |
| Publication/move paths | publication_locations.py, migration_operation.py, migration_planning.py, output_migration.py, output_rename.py, series_backfill.py, book_move.py | Existing user library paths unchanged. Unmapped publication identity strict; bridge only a specifically classified moved app-owned location. |
| Remaining surveyed consumers | scanner.py, book_delete.py, manual_conversion.py, desktop_update_lease.py, zone_identifier.py | Review actual path/receipt usage; new runtime/credential/source identities are not historical storage aliases. |
| Engineering | scripts/build_native.py, scripts/build_fs_guard.py, scripts/build-nsis-generator.py, scripts/build_external_tools.py and active Node runtime/checker pointer producers/consumers | Operate from physical canonical source checkout, regenerate verified location pointers; preserve source pins, lease generation, fingerprints and Git identity. Do not rewrite historical evidence. |

Ender core owner: new parser/native integration, shell/catalog lease, historical consumer adapters and core tests. Separate Ender operator owner (after prerequisite contract commit): NEW offline operator/transaction modules and adversarial/operator tests; do not modify core/native/shell modules without coordination. Both preserve other edits; neither commits, bumps or releases. Sully owns commits/push/version. Judy owns active installer/uninstaller UX and Senua/Futaba retain independent review/behavior clearance.

## Verification already observed; acceptance still required

Private baseline with actual local C:/I: volumes and installed Python: ordinary `desktop_catalog.inspect_folder` accepted I:; same call through real C junction→I refused. copy2 preserved bytes but native identity changed; actual `StorageCleanup._prepare` refused old facts and accepted actual new facts positive control. Actual pending `WorkingLifecycle.retire` similarly refused copied old facts and retired only same-identity positive control. Originals retained. These prove the problem, not the update.

Five initial pure parser tests passed, including adversarial schema/path/native facts/catalog/generation/class negatives and immutable parsed maps. No runtime bridge/native alias/activation/operator exists yet. Required acceptance: real cross-volume+junction constraints/attacks, same-handle mutation controls, pending/attention/retained/repair/index obligations, representative conversion, restart/resume, unavailable target, legacy installation, crash-phase replay, source/target write fencing, installer existing/new selection and keep/cleanup uninstall (including C-junction alias of active I data), actual filesystem write attribution, packaged build and final independent dual clearance.
