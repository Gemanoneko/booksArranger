# Books Arranger native output migration worker — 2026-10-20

Implementation checkpoint, not QA or migration clearance. No live catalog, output, source, configuration, iTunes entry or recovery file was changed by this component's work.

## Scope and observed outcome

`output_migration.MigrationWorker` resumes an already planned `publication_locations` relocation. It does not enroll publications, discover candidates, acquire the app owner, change roots or operate original input sources. Primary Ender owns the operation lease, all-mutator drain, eligible-publication plan, consumer adapters and operator entry point.

The initial Windows fixture checkpoint copied and verified an AAC M4B and committed the effective destination, completing with **`copied_verified_original_retained`** because it could not obtain a correctly capable parent handle. That original-retained result and its access correction remain historical evidence below. The newer isolated implementation opts into the independently reviewed initial write-capable parent handle; its current fixture results are recorded in the final section. Neither checkpoint establishes live Z: or NAS durability or authorizes production removal.

Corrected access-capability finding: default `DirectoryBoundary` handles have LIST_DIRECTORY/READ_ATTRIBUTES access and deny write sharing. Flushing those read handles cannot establish filesystem support because `FlushFileBuffers` requires GENERIC_WRITE. A private local fixture probe opened a GENERIC_WRITE/READ_ATTRIBUTES directory handle and successfully flushed it when no boundary was held. With a default boundary held, the correctly capable second open refused with Windows error32 (sharing violation). That proved an access conflict, not unsupported filesystem semantics. No boundary sharing was weakened.

The current worker uses `DirectoryBoundary(..., writable_parent=True)` to acquire GENERIC_WRITE on the initial final-parent handle. It then borrows that exact retained handle for `FlushFileBuffers`, verifies the same native identity/ancestry, and leaves closure to the boundary owner. It never opens a second writer or closes a borrowed handle. Read-only/default boundaries cannot supply this proof. Failure to acquire the capable boundary gives a typed `destination_parent_capability_unavailable` refusal, preserving original and any already recorded artifacts; a held-handle flush failure completes a verified copy with original retained and an explicit reason. Successful OS flush is only evidence that that call succeeded, not an independent promise about a NAS server, hardware cache, power loss or stable remote storage.

Reviewed authority: `BooksArranger_RelocationComponents_Review_2026-10-20.md`, pinned at `905a0771b96c520f50f339e4c182e32627906191`, accepted this isolated same-handle opt-in after the prior native boundary review. Default `native_io` behavior remains read-only and unchanged by this worker slice. No operator production activation or deletion clearance follows.

There is one target boundary per worker operation scope; helpers reuse the passed boundary. Original/source and destination ancestry protections remain separate. If a source, owner or another scope already retains a read-only handle to that exact final parent (including conflicting nested ancestry), the write-capable acquisition intentionally refuses. The worker does not borrow an unproven capability, relax sharing, release source protection, or retry through a pathname waiver.

## Entry interface and owner obligations

```python
MigrationWorker(database, *, operation_lease, media_verify, invalidate,
                fault=None, stop=None).run(publication_id)
```

`operation_lease(publication_id)` is a context manager yielding:

```python
{
    'db': sqlite_connection,
    'generation_guard': callable,       # (publication_id, generation) -> literal True
    'native_owner': {
        'schema': 'books-migration-native-owner-v1',
        'invocation_id': nonempty_string,
        'catalog_identity': [volume, index_high, index_low],
        'owner_handle_proof': {
            'held': True,
            'lock_path': native_lock_path,
            'lock_identity': [volume, index_high, index_low],
            'lock_ancestry': native_ancestry,
        },
    },
    'drained': True,
    'durable_commit': callable,         # (same_connection) -> exact readback proof
    'removal_closure': optional_callable,
}
```

The provider retains and validates the actual exclusive catalog owner and all-mutator drain for the entire context, across stage commits. The worker checks the supplied connection's catalog path and native catalog identity, idle entry state, persistent journal mode and FULL/EXTRA synchronization. Owner evidence is a capability from the retained lease, not a worker-created claim based on a PID. Each stage uses `BEGIN IMMEDIATE`; generation checks run on that same supplied connection, including immediately before native rename or disposition.

The worker does not treat ordinary `commit()` as a durability certificate. `durable_commit(db)` must commit and return `books-migration-durable-commit-v1` with `committed: True`, `publication_id`, current `generation`, canonical SHA256 of the actual relocation row and latest event row (`relocation_sha256`, `event_sha256`), actual lowercase `journal_mode`, integer `synchronous` (2 or 3), and the retained `owner_invocation_id`. The worker independently reads back all these fields and requires no active transaction. Allowed journal modes are WAL, DELETE, TRUNCATE and PERSIST. Unsupported durability stops progress before original removal.

`invalidate(db, original_receipt, effective_location)` runs within the `location_committed` transaction. It must not commit independently. Its changes and the location event roll back together on failure.

## Full-content media interface

`media_verify(path, original_receipt, stop)` must return a fresh supported typed proof:

```python
{
    'kind': 'sealed_media_proof_reused', # or fresh_full_media_verified
    'supported_validation_contract': 'books-audio-output-v1',
    'immutable_receipt_sha256': exact_original_receipt_digest,
    'validation_sha256': exact_original_validation_digest,
    'full_content_sha256': immutable_output_sha256,
    'size': immutable_output_size,
    'passed': True,
    'details': nonempty_actual_validation_facts,
}
```

The owner must establish the supported validation contract from the durable completed publication or authoritative authorized chapter receipt. A dictionary containing only `passed: True` is refused. Sealed reuse is valid only when that durable receipt seals this exact full output hash and size; it is not reuse based on a stat result or guessed compatibility.

The worker independently computes complete SHA256 and size from held source and destination handles, checks equality to the immutable receipt, retains native identity/ancestry proof, and attaches both full-content proofs plus the frozen manifest and publication-intent digests. The final location is rehashed and freshly verified before commitment and before any original disposal. A source seal used after a completed original removal is explicitly the durable full-content proof captured while the original was held, not a claim that the removed file was freshly reopened.

For `Chapters`/`Chaptersv2`, the contract must instead be `books-authorized-chapter-output-v1`. Frozen accepted routing must contain `repair_journal_sha256`; the fresh verifier must return the equal `authoritative_repair_journal_sha256`. A parent base-publication validation does not authorize a chapter output. The caller remains responsible for the resolver's authoritative repair-journal precondition.

## Native stages and crash boundaries

The resolver's immutable original receipt and stage proof chain remain authoritative. Before location commitment, effective location remains original; after commitment, missing/unverifiable destination is refused without fallback.

1. `copy_intent` binds the exact original full-content/native proof, target root/ancestry and unique temporary pathname.
2. Native `CREATE_NEW` creates the temporary without replacement. An additional append-only `artifact_created` event durably records its exact identity, ancestry, owner invocation and copy-intent digest **before any bytes are written**. A crash between creation and that receipt leaves an unknown file, which is preserved and refused. A recognized partial can be recopied only through the exact original native identity and exclusive writable handle.
3. `copied` requires complete native writes, file flush, full readback SHA256/size and the linked created-artifact receipt. Unknown streams, hardlinks, reparse points, replacement identities and destination collisions refuse.
4. `temporary_verified` records supported media proof for the complete held copy; `final_publish_intent` binds the exact temporary verification, identity and no-replace final pathname.
5. `publish_no_replace` runs within the stage write transaction. Its acquired native temporary identity/hash/size and generation are checked immediately before rename. A rename-before-receipt crash can resume only if exactly one temporary/final exists and the final has that recorded temporary's exact native identity and full content.
6. `final_published` and then `location_committed` require fresh held final identity, full content, ancestry, supported media proof, file flush and explicit directory-flush result. Consumer invalidation commits with the location binding.
7. Unproven directory persistence, including unavailable correctly capable parent handle, completes with `copied_verified_original_retained`. Original sharing denial also retains the output with a reason.
8. Conditional removal requires successful actual destination-parent flush on that same initially acquired write-capable handle, fresh final verification, an exact held original DELETE lease and full hash, then a durably committed `old_removal_intent`. A new stage transaction checks the generation immediately before disposing that exact handle. `original_removed` is recorded only after the old native handle closes and its name is absent; then completion is `moved`.
9. If a crash occurs after disposition but before its receipt, pathname absence alone is insufficient. Optional `removal_closure(intent)` must return `books-migration-removal-closure-v1`, the exact `removal_intent_sha256`, `native_owner_closed: True` and the matching `prior_owner_invocation_id`. The provider must prove closure of that exact prior native owner. Missing capability refuses. An unrelated file appearing at the old name is retained and refused.

All temporary, old and final access is bounded with production `DirectoryBoundary`/`VerifiedFile`; source cleanup/recovery APIs are never invoked. Original manifest source paths cannot be treated as migrated owned output. Cancellation checks retain owned artifacts for a later exact resume.

## Focused test evidence

Historical Windows fixture checkpoint: **19 tests passed, 25.195 seconds** after correcting the invalid read-handle capability probe (prior checkpoint: 19 passed in 25.285 seconds). These earlier removal-branch cases used an explicitly simulated directory capability. Reviewed bounded runner: `ok=true`, `closed=true`, `forced=false`, `timedOut=false`, private native job `active=0`, `unsignaled=0`, `zero=true`. No formal handoff or installed filesystem acceptance was implied.

The suite creates/reuses one tiny AAC fixture, obtains actual ffprobe and full PCM decoder validation, and uses actual native handles/copy/hash/no-replace publication/disposition against private fixture paths. It covers each durable-transition interruption, creation-before-identity receipt, exact partial resume, disk-write failure, rename-before-receipt reconciliation, same-byte replaced temporary, same-size final corruption, destination collision, unknown ADS, hardlinks/root alias, weak SQLite policy, malformed media and commit readbacks, actual sealed reuse and bad validation digest, transactional invalidation rollback, original sharing denial, final missing after commitment, generation refusal immediately before disposal, delete-before-receipt closure requirements and replacement old-name protection. Original input and recovery marker bytes remain unchanged.

The fixture owner uses an actual retained catalog lock, WAL/FULL connection and native identities; generation guards check both the retained fixture owner and active same-connection transaction. Tests honor `BOOKS_QA_FIXTURE_ROOT`; default session evidence remains under `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/output-migration`. Session scratch is retained for Sergei's manual cleanup.

## Same retained capable parent checkpoint

The updated coherent worker suite passed **21 tests in 27.478 seconds** through the unchanged reviewed native-owned runner (`timeoutMs=600000`). Result: `ok=true`, `closed=true`, `forced=false`, `timedOut=false`; native `active=0`, `unsignaled=0`, `zero=true`, retained224. No combined heavy command was retried, and no ownership uncertainty occurred in this run.

All 19 prior scenarios remain, including each durable stage interruption/resume, no-replace/identity/hash refusals, exact generation guards, durable SQLite proof checks and deletion-gap native-owner closure requirements. Their successful parent-flush/deletion branches now use the actual initially acquired write-capable parent; no successful directory capability is simulated. Only the explicit unavailable-flush fallback is failure-injected. That case retains the original with a precise unproven-persistence reason.

One new actual test forbids **any** second `CreateFileW` while `_flush_parent` executes, verifies the borrowed handle remains unchanged/open and retains the same native parent identity, and requires the actual OS flush result. It reaches native copy/full hash, exclusive final publication, fresh final identity/typed media, transactional location binding, exact durable old-removal intent, actual old-handle disposition and confirmed native closure. The final outcome is `moved`; original input and pre-existing recovery bytes remain unchanged. A second new test proves a default read-only boundary never calls `FlushFileBuffers` to certify durability, and that a conflicting nested read-only parent lease causes a typed refusal with the original and planned state retained.

This establishes the private local native path, not a remote NAS persistence guarantee, production eligibility, live migration completion, formal QA or release clearance. The concrete operation owner, all-mutator drain, publication enrollment, source/recovery consumers, NAS behavior and complete production command still require their separate review and runtime admission. A successful OS directory flush must never be presented as a hardware-backed promise.
