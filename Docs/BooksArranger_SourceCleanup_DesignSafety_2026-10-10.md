# Books Arranger: source cleanup design safety

2026-10-10. Senua. Red-team review of the snapshot-backed original-track removal design, before implementation. Prototype safety-floor audit; no live source deletion was performed or cleared by this design review alone.

**Verdict:** CLEAR — design only

**Open findings:** 0 Critical, 0 Major, 0 Minor. Actual deletion remains held until exact implementation/caller pins, independent QA and focused code/native-operation safety review pass.

## Exact design binding

Reviewed `Docs/BooksArranger_SourceCleanup_Design_2026-10-10.md`, independently measured SHA256 `50044739a3013aadfae46718d690fe1e76d10c730fec8cb427fc3f38ed207fe7`. Existing protected handle/directory/publication baseline in `native_io.py` was read for boundary context. No new removal primitive exists in that baseline; rename support is not evidence that disposition works on mapped Z:.

The first real scope is exactly completed jobs `0b6fedcc-2d95-46a9-a4a3-4192da37ff72` and `dc4874af-e132-47cd-93ab-85e5b0fbeea7`: eleven MirrorMask sources and ten Snapshot sources, 358,293,739 bytes from their selected manifests. No Eye of God, folder/sibling/cover/podcast/ebook/library-wide removal is included. Future cleanup is limited to explicitly selected completed conversions under the user-authorized workflow.

## Why the design satisfies the safety floor

Before the first destructive source operation, all selected originals must have separately registered, app-owned persistent recovery copies, full byte hashes/sizes verified under held protection, flushed contents and an explicit supported storage/flush contract. A preexisting cache snapshot, pathname, historical proof or free-space estimate alone cannot satisfy this condition. Reparse/alias escapes, hard-link ambiguity, unsupported extra streams/attributes, collisions and failed copying/flush/verification stop before deletion. Recovery ownership excludes these assets from routine cache cleanup and automatic expiry; permanent purge is outside authorization.

The replacement M4B must still match the exact full hash/size of its complete validation result, and be held against mutation/deletion throughout source removal. Review/source order/coverage/cover and completed-parent identity are independently rebound, rather than weakening the ordinary creation guard. This preserves a usable validated replacement and exact recoverable originals while Z: names are removed; a changed output or review stops the remaining work.

Each native source removal uses the already verified exact READ/DELETE handle and protected ancestor identities, not a later path lookup or shell deletion. The final guard must consume handle-derived identity/hash evidence without conflicting reopen share flags. Per-file mutation intent is durable first; a short final review transaction excludes catalog drift during disposition/checkpoint. The delete handle is closed, name state inspected and result accurately recorded before moving on. Failures and unexpected delayed removal do not trigger a weaker fallback. Directory recursion is explicitly prohibited.

Crash recovery is member-specific and bound to owned intent, exact backup/output hashes and current source-name identity. Absence alone does not certify that the app successfully deleted a source. A replacement appearing at a source name is preserved and flagged. Partial counts remain accurate; pausing finishes only the current atomic member boundary and resumes the remaining members without reencoding or discarding the completed audio record. This design requires a durable deletion journal independent of catalog commit so a crash between disposition and retirement remains reconcilable.

Restoration copies verified recovery bytes to an exclusive original-side temporary and uses exact-handle no-replace publication. Supported original timestamps/attributes are restored; collisions preserve existing content. Recovery files remain persistent after restoration. Retirement is exact-object provenance rather than a permanent path blacklist: new/reappearing files must still be discovered and inspected, and unrelated files remain visible. No missing/read error or implicit reconversion is substituted for intentional removal.

## Implementation audit requirements

The design's protections are requirements, not implemented facts. The next review must check their actual mechanisms and caller: recovery registry/journal durability and complete backup-before-first-delete ordering; source/output/backup handle lifetimes; supported stream/alias/storage checks; exact native disposition and close/result semantics; authoritative final review transaction; restart reconciliation; collision-safe restoration; cleanup worker stop/join ownership; intentional retirement and fresh same-name file discovery; and exclusion of persistent backups from every cleanup/hygiene path.

Required evidence includes an owned disposable mapped-Z positive control for the new native disposition and sharing behavior, plus tamper/collision/reparse checks and faults around backup intent, disposition and catalog checkpoint. A local synthetic success, preexisting rename test or Linux unlink result cannot certify the live mapped-Z primitive. Test artifacts must be bounded and explicitly owned; neither originals nor recovery assets may serve as disposable fixtures. Actual 21-source execution must use the cleared pinned caller and freshly revalidated assets.

This review makes no guarantee of hardware survival outside the implemented Windows/storage flush contract; unsupported durability must stop cleanup rather than be described as recoverable. C: recovery retention and Z: reclaimed bytes must be reported separately, with no claim that originals occupy no storage anywhere.

## Actions and limits

Senua read the exact design and existing native baseline only. No media/catalog writes, native applications, tests, deletion/restore operations or Git mutation were performed. No disposable probes were generated; unique evidence and all originals remain untouched. This durable report is the only reviewer-created artifact.
