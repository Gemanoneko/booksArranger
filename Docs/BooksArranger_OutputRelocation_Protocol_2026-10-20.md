# Books Arranger — output relocation protocol (design v1, not execution clearance)

2026-10-20, Ender. EXTEND v0.19.0; follow LibraryAudit00cbc3f and Senua's MigrationDesign review. No live movement or settings change is authorized by this document alone; the user authorizes the desired outcome, while these implementation checks must succeed first. Existing sources, publication history and failed-job evidence remain immutable.

## Persistence contract

New output_relocations rows are per publication job_id, not one global output-root replacement. Fields: migration_id, job_id, schema=books-output-relocation-v1, stage, original_output_json, original_output_sha256, original_manifest_hash, original_publication_intent_sha256, candidate_id, candidate_revision, source_fingerprint, planned_destination, target_root, routing_policy_version, accepted_routing_json, previous_location_json, destination_verification_json, generation, last_error, created_utc, updated_utc. Unique current relocation for job_id; compare-and-set generation on every transition. Append-only migration_events journal records each transition and refusal. Destination verification contains content SHA256,size,media validation receipt and native current file/parent ancestry identities. Original manifest/output/journal hashes prove provenance; they are not rewritten. Source root remains manifest.root. Recovery source paths stay unchanged.

A single publication_location(job,db) resolver returns original immutable publication plus effective current location and relocation proof. At no binding, effective equals original. Pending copy/verification cannot change effective location. At committed current-location stage, effective is destination and a current read-only verification must prove its file/ancestry. Missing/changed destination yields typed relocated_output_unavailable, preserving source/recovery data; it never silently returns old path as current after a committed location change. The old copy is available only as recorded fallback recovery, requiring explicit reconcile after destination repair. Resolver does not approve media based only on extension/path/size.

No top-level output root changes until resolver support exists at every consumer. New output policy is separate from per-source scan roots. Partial migration is expected: converted books with unconfirmed universe/cycle/collection identity remain at their old verified location with reason, and all current jobs retain identities. A path-policy version on each accepted candidate/job avoids invalidating an old Ready book just because metadata.propose now knows a newer hierarchy.

## Literal consumer mapping

| Consumer | Immutable provenance check | Effective location use |
|---|---|---|
| audio_jobs.py publication_intent, output | Frozen manifest_hash, original journal and output receipt unchanged | New jobs freeze explicit output_root separately from source root; publication guard uses output root |
| merge_service._output_valid/_identity_current | Original job/output hashes checked against relocation binding | Effective path, fresh parent/file identity; invalidate _validated_outputs, verified_outputs, progress/catalog/status/current-audiobook caches after commit |
| conversion_progress.completed_book | Existing candidate/manifest/source/cover equality unchanged; accepted routing version checked | Allow path mismatch only with exact valid relocation binding, not arbitrary root/path difference |
| current_audiobook.py CurrentAudiobooks | Preserve completed/repair lineage, immutable manifest/journal hashes | Resolve representative current output and every eligible repair-derived path via same relocation proof; no independent guessing from old path suffix |
| source_cleanup.py run + _cleanup_guard | Frozen intent.output and candidate binding retain exact original receipt equality | Verify effective output under relocation.target_root; original manifest.root remains source-containment boundary; no replacement of source path roots |
| recovery_retention.py and restore routes | Source recovery receipt/source identities unchanged | Protect effective output through same resolver before expiry/deletion/restore permission |
| storage_cleanup.py / working_lifecycle.py | Ownership and produced-artifact hashes unchanged | Verify current effective publication before retiring working/recovery copies; source root exclusion includes every configured source/output |
| replacement_media/jobs/retirement | Former/current output JSON remains historical lineage; current_output_json equality handled with exact relocation binding | Resolve each publication independently; former copy cannot become current by path-string matching |
| chapter_repair.py / repair journal | Original repair inputs, output receipt and hash lineage unchanged | New repair targets resolved publication, freeze effective root/path plus relocation generation; old repair journals resolved only via proven binding |
| merge inspection/open-folder/state/list + desktop/browser | Inspection preserves source vs created vs historical sections | Display effective path only when bound; retain old receipt in history; open-folder from resolved proof; source folders unchanged |
| scanner/groups/automatic + source cleanup boundaries | Existing candidate ID/source evidence remains source-bound | Scan all configured sources, exclude output and relocation copies; never deduplicate/delete by title or output path |

This table is a design checklist, not proof code has been changed. Implementation grep must enumerate all literal final_path,destination,root,parent_identity,publication_intent,current_output_json,verified_outputs consumers and tests before activation.

## Drain and fault matrix

Migration uses a durable catalog-exclusive operation lease. Acquiring it refuses active scan, automatic research/admission, audio worker/checker/readmission, source/working/storage/recovery cleanup, repair/replacement and shutdown mutations. Existing owner must cooperatively drain its current safe work, not be killed. The migration must run through the supported engine or an offline catalog owner after normal Quit proves closure; bypassing stale owner/native locks is prohibited. Catalog file backup is captured only under consistent SQLite snapshot/lock, with no running copied catalog startup.

| Durable stage | Mutation allowed | Crash/restart action |
|---|---|---|
| planned | None to media; freeze ids/hashes/routes/ancestry/free space/collision set | Recheck complete lease and immutable rows before any copy |
| copy_intent | Create owned no-replace temporary destination under held target ancestry | Identify exact created artifact from journal; never delete an unrecognized same-name file |
| copied | Flush copy; retain original | Resume destination hash+media verification; failed/partial copy cannot bind catalog |
| verified | Store complete destination proof; original still retained | Revalidate both files and frozen catalog rows; drift refuses commit |
| location_committed | One catalog transaction installs resolver binding and invalidates persisted verification state; old receipt immutable | Both copies retained; current path is new; verify effective output before resuming any cleaner |
| old_removal_intent | Journal exact old native identity/hash and already committed destination proof | If both survive, reacquire ancestry+leases and reverify before removing old owned file |
| original_removed | Only exact old owned output deleted; never any source/recovery/companion based on extension | Missing old file accepted only with own durable removal proof; unrelated file now at old name preserved |
| complete | Record moved only after proven deletion; or copied_verified_original_retained with reason | Recheck effective file on normal startup; source cleanup/recovery resolution remains valid |

Fault tests: interruption before/after each durable transition, DB commit refusal, changed candidate/revision, changed manifest/receipt, replaced parent, junction/symlink/ADS ambiguity, destination same-size different bytes, collision, disk full midcopy, media validation fail, source disappears/changes, cleanup concurrently starting, native owner absence uncertainty, postcommit old-delete failure, restart with both copies and missing destination. Assert source/recovery bytes unchanged, old copy never removed before verified durable binding, no falsely Ready path, duplicate/copy counts honest.

## QA handoff context plan

Protocol2 context must be separately reviewed after source milestone commit. Source snapshot complete, full HEAD/dirty state, harness/runtime manifests and all5 checker helper digests. Declared package check graph currently only check=node scripts/check-desktop.mjs; it expands fixture/runtime/node checks and Python test patterns (read exact current script; no inferred n/a). Each transitive route must be classified pure-node or renderer-offscreen. Native ownership addon+Node+Python+ffmpeg pinned from existing installed/staged runtimes, no download/install. RunRootParent is session scratch/shared/qa-runs (absolute path), not legacy C:/b16. The legacy guardian hardcodes C:/b16 and old context roots, so it cannot be reused with renamed args without review; do not edit/deploy global guards as part of library work. Existing runOwned can enforce native private-job600000ms for narrow unit tests (already used), but unit output is not a handoff receipt.

QA fixture has fresh synthetic Inventory, tiny owned audio/artwork generated once beneath session scratch/shared. Every persisted source/root/destination/staging/recovery/receipt/intent points inside that fixture. Before app startup, recursively inspect every saved JSON/path column and manifest; refuse any real Z:/ or real dataDir path. No startup copy of real catalog; the2026-10-18 deletion lesson remains binding. No focused Electron or signed-in browser. Headless browser only through studio approved helper with offscreen renderer contract. Sender/receiver exact same reviewed context invocation sequentially, compare actual receipts. Unsupported declared route stays blocked. Packaged payload and same manifest acceptance required before release, with no focus-taking packaged QA launch.

This is an input design for context assembly and Senua review; no receipt or migration clearance yet.
