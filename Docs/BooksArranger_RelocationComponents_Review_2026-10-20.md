# Books Arranger relocation consumers and worker — component review

2026-10-20, Senua. **Static component review only; no RELEASE CLEAR, live execution or deletion permission.** Consumer map at `9d40932cba1154df7831f3303b532f9af9085b6c`; protocol `10de6b5` and prior component correction checkpoints apply. Reviewed the current consumer/worker code and narrow tests, excluding active migration-operation/plan-builder/boot work, final release graph, packaged UI and deployment. No tests, app, native copy/removal, live paths, settings or iTunes actions executed by Senua.

## Findings and disposition

No new Critical or always-blocking safety-floor violation identified in this stable component slice. Native worker production old-output deletion remains **uncleared**: the inspected `_target_boundary` is readonly and `_flush_parent` separately requests GENERIC_WRITE while that share-read-only boundary is held. The acquisition conflicts, records capability-unavailable rather than unsupported-filesystem, and returns copied/verified/original-retained. This conservative limitation is real; it is not proof that Z: supports or lacks durable directory publication. The tests simulating a successful directory capability exercise a conditional branch, not a production durability acceptance.

**Major — read-view writer reservations can block unrelated catalog writes during media I/O.** At the pinned adapter, a bound `protect` uses BEGIN IMMEDIATE throughout native protection. Full NAS hash or chapter creation can therefore reserve the one SQLite writer for longer than normal write timeouts. The code avoids the previously corrected self-deadlock by sharing nested view connections and writing identity caches after exit, but that does not establish interactive responsiveness. Keep the limitation explicit; developer native fixture passes do not prove live polling/edit behavior under long media reads. A bounded design correction is specified below; it is not yet implementation acceptance.

The core ownership/provenance checks reviewed are coherent: immutable base/job/repair/replacement records remain unchanged; independently derived publications require freshly authorized journal digests in adapter lookup/guard/context exit; replacement retirement checks all former/successor generations on the actual writer connection through native close, name absence and removed-receipt CAS. Storage/working/source disposal likewise retains its own publication guard through close; the corrected source cleanup commits after absence. No separate writer is opened for receipt CAS while that writer transaction is held. Migrated interrupted removal without exact closure remains held. No old-path fallback or unknown-file adoption was found in these inspected paths.

Chapter recovery independently reconstructs the journal-derived receipt, authenticates exact parent/derived bindings and preserves native parent/journal protection. Native full hashes, relocated leaf identity and ancestor equality remain required. Ready compatibility preserves core metadata/source/cover checks while allowing the exact accepted routing proof. These are source conclusions, not verification that every live book is eligible.

## Worker proof and crash review

The worker admits only an already planned publication through supplied drained owner/generation/durability capabilities. It cross-checks actual catalog path/native identity and persistent FULL/EXTRA SQLite settings. Temporary files use CREATE_NEW and capture the creation-returned identity; a creation-before-journal gap is refused. Resuming an owned partial requires its exact journaled identity and scope; no same-name byte-identical replacement is adopted. It chains temporary/final proofs, uses no-replace native rename and reconciles the rename-before-receipt gap by exact identity/full bytes. Location binding plus caller invalidation share one stage transaction. Before old removal it revalidates final bytes/media/native proof and exact old intent, and holds the writer through disposition/closure/absence/receipt. Missing-old reconciliation requires the exact precommitted intent and prior native-owner closure callback; path absence alone is insufficient.

Typed media reuse seals immutable receipt/validation digests to full source/destination hash proofs; authoritative chapter journal digest is separately required. On completed post-removal reads the persisted original hash seal is history, not a new claim that the absent original was rehashed. The caller's actual media verifier, owner lock, durable commit and invalidation capabilities remain excluded active operation code and need independent review. A dictionary claiming native ownership is not self-authentication; the concrete owner must actually retain it. No complete operator path is cleared by reviewing the worker alone.

The19 worker cases and60 focused replacement/chapter cases are developer evidence only. Worker tests disclose simulated directory capability for removal branches. The attempted combined heavy gate returned no test result after native membership uncertainty and safe forced closure; it is not a PASS. No duplicate heavy run or weaker owner is approved by this report.

## Narrow next-step designs

### Capable parent handle opt-in

Isolated worker engineering may opt into the previously reviewed `DirectoryBoundary(..., writable_parent=True)` capability and flush that exact original retained final-parent handle. Do not retain a readonly handle and open a second writer; do not relax sharing. All existing ancestry/identity/default-false behavior and native failure retention remain. Same-parent nested read/write boundaries intentionally conflict; restructure to reuse the exact allowed handle or refuse safely, rather than weaken leases. Exercise all worker stages/restarts with actual private capable handles and all no-replace/closure faults before any production removal review. Successful local flush is not independent NAS persistence proof; no live Z: write or old-output deletion is admitted now.

### Read-only WAL view correction

Primary's proposed correction is acceptable as design under this exact authority contract:

- Every supported relocation plan/write operation is offline under the **same actual catalog_lock**; the live app retains that owner throughout startup, view and chapter operations. A normal live view therefore cannot overlap a legal relocation writer. This must be enforced at actual entry points, not an advisory comment.
- Read-only `protect`/`protect_parent` may use an explicit coherent WAL read snapshot with retained native file/journal proofs, yielding no deletion authority. Require observed WAL or retain the existing conservative behavior with its limitation; do not silently change journal mode to obtain this property.
- Before accepting a result/cache entry, compare generation plus immutable job/receipt and authoritative journal provenance through a fresh different connection outside the old snapshot. Looking up again on the same read transaction cannot detect another connection's committed change. Nested base/derived scopes must preserve coherence and independently reject relevant drift. Native/hash and fresh journal checks remain; a read snapshot is not a disposal lease.
- All actual source/storage/working/recovery/replacement removal paths retain BEGIN IMMEDIATE and generation/native guards through close/absence/CAS. None may reuse the read-only view as destructive authority.
- Add actual private tests showing an unrelated metadata writer can commit while a view is held; an injected illegal generation/provenance writer makes view exit refuse using the fresh read; nested parent/derived guards stay consistent; and the live catalog owner blocks the supported offline writer. Do not claim performance corrected until the revised code/tests are independently reviewed.

Sully must pin this ruling before an implementation brief cites it. No operator/worker production activation follows from either narrow design.

## Stable source identity

First/last reads matched for all twelve product files below. MergeService's active boot/operator regions were excluded; only named relocation/progress/replacement integration was inspected.

| File | SHA256 |
|---|---|
| publication_locations.py | `a02c9e47e146bbf41aa7e358d5e45f8b44c2483be316c89db2e81e81a8d2cf94` |
| publication_binding.py | `e2120d0381999c63bc3e4d2bf9c3e7795fb1e6b2297ef33c9fcd91cc49f782ab` |
| current_audiobook.py | `6d7532581bc6eeaf16d338ca2bbd61f7cf7391ef85578e9fb185a26e74d0bc4d` |
| conversion_progress.py | `c2eaf3340e036d1e1956c121fbcf769b89eec10fcf70e972886cebb4eb65ccbd` |
| source_cleanup.py | `1d14cbfe20e29f025daf5c6075be739c7278471178980a315448d34a41be7a3d` |
| storage_cleanup.py | `720f9e8cca0a1118204f0f7f73a28afc79b28dfa8d80e5c6fe63b07a4379de67` |
| working_lifecycle.py | `46ce8bb0bf188a571625aa2ae6067dbceaeb7d60d0905dc124126282b6fd3221` |
| chapter_repair.py | `68bc5325a5f6363aca572d877293ec8def4e6610bfd5642421b5acb1f0de3df9` |
| replacement_media.py | `e916cc81eea3c16f990332c17dcb8795cd2856a90eac8da8475b04f3e2593f99` |
| replacement_retirement.py | `894674d09b7e62908973cf0692cf0290358a4bf12314a5a57891912f20f27790` |
| replacement_jobs.py | `bd136ddc9d1f3df281cb871599e5f2fb0a7cfe25e7b51d83c0660b9431e1328d` |
| output_migration.py | `596f4ad42bf82f034fe8c2c60dc8170dec045200cecbfe2da070e375c6b90371` |

Reviewed test pins: output_migration `141078153ea71fa21ade8a351da189a35c6d2eab0775c4640e7fa03062ea9d0e`; relocated_replacement `804d8298446a4c6737bd47456ab1c127b9e0124b213490dca88bf802cc6448b3`; relocated_chapter_repair `0277421693f94da6c8171d1ce0b9e845dc8e421af2ef2404514d6d0743d7f3e3`; publication_binding `3882be88b0d85f4a8b0cd67669c3f36727504b763cd84dd67e762b645fb45876`; publication_consumers `d79713bd1964f967f197840d09fa7afd80a08d3d977a9bd945c3727770d649d5`; relocation_progress `7b9f899732e98033dc3238fb90a19c578773e9878d6d9ca0d17e87d680a279f5`. These pins do not certify execution.

Only this review document created; no disposable/scratch output. Session evidence remains for Sergei's manual deletion. Native worker/operator, whole-product QA, runtime admission and final release review remain separate gates.
