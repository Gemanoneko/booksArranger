# Books Arranger offline migration operator/planner — source review

2026-10-20, Senua. **Static component review, not release or production execution clearance.** Basis: operation checkpoint at `ffedfbf51571e5f29c7e7c966a1b024b3559f9bf` and prior resolver/consumer/worker reviews. Reviewed these stable source hashes before/after; no tests or live actions executed:

| File | SHA256 |
|---|---|
| migration_operation.py | `2f5e5e1b24e514a8a7303cccf51a822dd10351521004e0e677e12fbc58a8d89d` |
| migration_planning.py | `c887b990be1cb631d9bfdb7b7a4b8b78e33eb5e114340bcce5e99cece7d3cbbf` |
| tests/test_migration_operation.py | `63bbe79136870f1e937cb09a7b630a26e6b087c816879665f108d356d192cf13` |
| tests/test_migration_planning.py | `f65119a0531096b57017825cbb92eb8ffcab9c2466eba81556e655785de28de6` |

## Findings

**Major — current variants without cached verification are silently omitted.** `prepare` selects the current representative variant, then sets `current` only if verified_outputs already contains that variant's exact stat identity. `publications.protected` holds native identity/ancestry but does not fresh-hash it. A corrected chapter variant never previously inspected/cached can therefore make a book currently counted Ready through its base publication disappear from the plan at `if not completed_book(...): continue`, with no held reason. Other approved-candidate eligibility continuations also omit reasons. The plan cannot account for all converted books or explain incomplete scope this way.

Required correction: account explicitly for every in-scope approved/Ready candidate and selected variant, with typed exclusion/hold reasons, including missing/current verification. A supported bounded native-held full-hash preflight may establish the missing proof; cache absence is not evidence that the book does not exist. Do not turn a whole-library preflight into an unbounded operation or assume all179GiB can be rehashed in one600000ms invocation. Add a private derived-publication case with no cached derived identity and reconcile expected/planned/already/held totals. Final after-drain variant/history inventory remains required.

**Major — human-reviewable plan scope fields are not enforced by the operator.** `_scope` consumes publication_id plus frozen_binding_sha256, but does not compare the plan entry's displayed source/destination/kind/candidate_id/size with the actual frozen ledger/receipt. `_plan` also does not bind the plan roots to the constructor's root policy. An altered reviewable field can thus be displayed in the pinned plan while the operator executes different ledger values behind the opaque binding hash. Hashing the entire reviewed JSON authenticates those bytes, not their semantic correspondence to the actual action.

Required correction: reject every mismatch between plan entry and immutable publication/target facts, including candidate identity, publication kind, original path, target path and size, and validate the exact plan source/output root policy against the effective configured scope. Keep immutable binding digest and generation checks; do not replace them with path-only checks. Add negative tests independently changing each displayed field/root while leaving publication ID/frozen hash intact. No ignored placeholder fields may look authoritative to the reviewer. Primary Ender accepted both findings; implementation follows the pinned review checkpoint.

No new Critical or safety-floor violation identified in this presently uninvoked component under the reviewed owner/callback contracts. These findings remain open until revised source is independently checked. No live planning enrollment or per-publication run is cleared here.

## Reviewed authority and remaining proof

Both CLI/planner and operation acquire the same actual catalog_lock used by the live app; planner additionally checks ACTIVE_CATALOG before catalog schema/enrollment writes. The operation creates no app/queue/cleanup workers and refuses running audio or active source cleanup. Frozen scope checks bind candidate/source/context revision, review digest, source membership/order/hash evidence, cover and required cleanup. CAS callbacks act on the same retained stage connection and source row; durable stage commit returns read-back row/event digests with persistent FULL/EXTRA SQLite mode. Binding commit and persisted verification/ownership invalidation share the writer transaction. Interrupted old-removal closure deliberately supplies no capability and stays held.

Planner selects one current importable variant per eligible book; superseded base/chapter variants and recovery remain outside the final import tree. That is disclosed, not a claim that every owned historical artifact was moved. The final physical/publication inventory must explain what remains and why before migration/iTunes completion instructions are given.

Sealed-media reuse is concrete and publication/digest-bound; the worker separately full-hashes native-held original/destination. Derived reuse reconstructs the authoritative journal and matches its accepted digest and receipt. However the actual derived planner→operator path is not covered by the current three planning/five operator cases. Add that private complete case and negative changed-journal/parent-generation controls; do not extrapolate the base-only fixture into derived clearance. Native owner/source/receipt and durability guarantees still require the actual reviewed bounded invocation and production-volume capability evidence.

Developer reports5 operator and3 planner cases passing, including an actual private base conversion→plan→operator move with unchanged historical receipt. This is engineering evidence, not independent execution or a formal canonical receipt. Final immutable input plan/config/decisions, all live after-drain counts, source/output collisions/space, no-focus app drain/reopen, observed NAS durability, concrete process ownership and final release/QA remain pending.

Only this review document created; no code, Git, process, catalog, settings, media, restart, iTunes or scratch action. Sully should pin this review before correction briefs cite it; this document does not authorize live work.
