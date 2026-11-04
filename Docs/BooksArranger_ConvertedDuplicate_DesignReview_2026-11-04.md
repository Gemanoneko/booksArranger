# Converted duplicate cleanup — destructive-boundary design review

Senua · 2026-11-04 · Design review only; no implementation or tests run.

Reviewed baseline: `e8f42b160e1a2bbc1cea883f41679bdf745579c1`, product source `bf4425de09c355d2a0743771ca4209b24c8f0de1`, with Sergei's decisions in `37ab171` and Judy's spec in `e8f42b1`. This clearance concerns duplicate sources only. Finished outputs are not migrated, renamed or retagged by this path.

**Verdict:** DESIGN CLEAR WITH REQUIRED CONSTRAINTS

The backend can safely reuse the existing publication while creating a new protected duplicate-source cleanup. The direct route is an explicitly typed verification/cleanup task in the existing queue, with its own durable completion receipt referencing the unchanged parent publication. It must bypass ordinary publication completion and publication postprocessing. Ender may implement that route under the constraints below; no further design-review round is required before implementation. Code and behavior clearance still apply before release.

## Keep the two owners distinct

| Fact | Owner |
|---|---|
| Immutable producer manifest, output validation, publication ID, location generation and output file | Existing completed parent job |
| Current duplicate source manifest/review, task/attempt identity, cleanup intent, source-member receipts, recovery copies and retirements | New verification/cleanup task |
| Ready audiobook count and output mutation authority | Parent publication only; the child grants neither a second publication nor move/rename/replace authority |

Use one typed resolver/capability at the boundary between these owners. It must return distinct parent-publication proof and child-cleanup proof; a generic `(manifest, output)` pair must not silently mean different owners in different consumers. The relation and evidence are derived and checked by the backend, never accepted as self-asserted `complete: true` authority.

## Direct integration route and required guards

1. **Recognize the entire recording.** Bind the exact parent job, frozen manifest hash and output-record hash to the current candidate/revision and complete ordered source set. Fresh full hashes/sizes, chapter structure and available work/edition evidence must agree. A subset, reordered set, filename/Unicode resemblance, destination collision, or unrelated M4B is insufficient. Conflicting explicit user choices, ambiguous parents, changed/retired/replaced output, unsupported lineage or a reuse chain must retain the sources rather than select a convenient parent. Resolve supported current location through the parent publication identity, not a pathname lookup.

2. **Complete verification truthfully.** The existing queue may schedule a new pending/running task, but its typed result means “existing publication verified”; it does not publish. Preserve the original parent record and `job_id`. Do not replace its `job_id` with the child ID, synthesize a publication intent, invent a producer/staging ledger, or generally relax existing identity checks. Pause/crash recovery must recognize this task kind and reverify the relation rather than replay a publication operation.

3. **Enroll a fresh child cleanup.** Validate the old output against its own producer manifest and validate the current duplicate sources separately against the child review/binding. Keep the parent row and old cleanup/recovery/retirement records unchanged. Even when the parent's validation says `publication_mode == in_place`, this separate duplicate uses the ordinary verified-backup/native-removal path: it was not renamed into the output and must never use `_retire_moved` or fabricate no-copy receipts.

4. **Re-prove at the destructive boundary.** The cleanup must freshly hash and retain the current parent output with its native identity/ancestry and the exact current source handles/facts. Reject output/source aliases and protected dependencies. Preserve the existing recovery-space, metadata/stream, backup verification and current Sorted/output-policy rules. In the same retained write transaction immediately before each disposition, revalidate the parent row/receipt, reuse relation, current duplicate review/source binding and parent location generation using `publication_bindings.guard(..., require_transaction=True)`. `PublicationBindings.protect` is a read observation, not sufficient disposal authority. No cached early verification may replace these checks.

5. **Restrict postprocessing authority.** The child must not register a new output, call publication move/rename/series-backfill/replacement/reacquire operations, or treat parent `owned_temp`/staging/recovery as child artifacts. Storage cleanup and retention may protect the parent publication while disposing only the child's independently owned recovery/temporary records. Keep restore mappings, backup facts and folder cleanup obligations tied to the child's exact sources; restoration preserves existing replacements and does not automatically repeat deletion.

6. **Make retries and counts exact.** Atomically admit at most one task/cleanup for a given current source generation and parent receipt. Repeated recognition must return that task, not create competing removals. Resume partial cleanup through the existing per-file intent/disposition/retirement receipts; changed sources or unknown removal outcomes remain held. One completed publication stays Ready; only durable new child receipts count as extra sources removed, and the old parent's removal is never counted again.

## Concrete existing contracts that must be routed explicitly

- `audio_jobs.py:536`, `:1368` and `:1384` require ordinary output ownership and a durable publication intent. `conversion_progress.py:65` likewise treats `output.job_id == current job_id` as publication identity. Keep those normal guarantees; add the narrow task-kind result path rather than weakening them globally.
- `source_cleanup.py:226` validates the output against its manifest, and `:457` selects the in-place no-copy branch. For reuse, parent publication validation and child duplicate-cleanup operation mode are separate facts.
- `storage_cleanup.py:166` requires the completed output owner, while `protected_output` at `:182` checks that owner's frozen provenance. A child cleanup must resolve its parent protector explicitly while retaining child receipt ownership.
- `merge_service.py:1443` performs generic working/storage cleanup and then `_move_to_chosen`. The reuse task must not enter publication-mutating hooks. Its cleanup guard still needs the current child review and the parent generation under the existing destructive transaction.

Consumer coverage includes enqueue/work/recovery/published verification, cleanup enrollment/guards, publication binding/locations, storage cleanup/retention/restore and ownership, output move/rename/replace/reacquire, and candidate/job/counter presentation. Ender owns the precise implementation and records the resolved ownership mapping with the change. Required negative coverage is limited to those boundaries: different/partial/reordered recording, stale parent/source/location, aliases and dependencies, in-place parent, cancellation and per-file crash/unknown outcome, duplicate admission, child recovery/restore/retention, and unchanged parent output/receipts/counts.

No live Z: access, source removal, focus change, code edit or test was performed for this review. This document grants no weaker file operation or live-data verification; implementation and private-fixture verification remain within Sergei's existing authorized scope.
