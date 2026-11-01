# Books Arranger 0.24.2 — shared routing implementation

Owner: Ender, shared-routing slice, 2026-11-01. Authority: [approved scope](BooksArranger_0.24.2_Scope_2026-11-01.md), committed at `3d4f0d2`, and [Judy's UX spec](BooksArranger_0.24.2_UX.md), committed at `070ec34`. This extends the existing hierarchy planner.

## Cause and bounded change

The existing hierarchy-v2 planner already places an accepted universe directly under the output root and omits the author directory when the review explicitly says `multi_author=True`. Automatic `build_policy` initializes that choice to false and does not retain a general identity-bound proof of a shared series. The missing input must be supplied by the research/review owner; matching display names is insufficient.

`shared_routing.py` introduces a frozen, source- and accepted-name-bound membership receipt under `metadata_facts.shared_routing`. `organization.plan` validates that receipt and omits the author directory for a confirmed shared series. It does not set `review.multi_author`, replace the real author, change the filename, or infer a narrator's role. Existing universe hierarchy, explicit multi-author choices, numbered anthology exception, recording suffixes and chosen destinations retain their policies. There is no filesystem operation, background migration or receipt rewrite in this slice.

Owned files:

- `organization.py`
- `shared_routing.py` (new)
- `tests/test_organization.py`
- `tests/test_shared_routing.py` (new)
- This document.

## Producer/consumer contract

Producer API: `shared_routing.build(review, facts, series=authority, universe=authority)`. At least one authority is supplied. Attach its return value as `facts['shared_routing']` after final accepted name choices. Do not alter the frozen facts of an existing job/publication.

An authority has exactly these keys:

```python
{
    'id': 'https://provider.example/series/123',  # stable identity, never the name
    'name': 'Omen',                            # exact accepted series/world spelling
    'basis': 'catalog',                        # or 'user'
    'evidence': ['citation-or-durable-decision-receipt'],
    'members': [
        {'work_id': 'provider:book-1', 'authors': ['David Seltzer']},
        {'work_id': 'provider:book-2', 'authors': ['Joseph Howard']},
    ],
}
```

For `basis='user'` the stable identity begins `user:` and identifies the actual durable decision. World members additionally have `series_id`: the stable identity of their series, or `None` for a standalone. A world's current member must agree with the book's accepted series/standalone state; when both authority types are present their current series identities must agree.

The producer must establish each member's work identity, complete canonical author credits and membership independently through accepted catalog evidence or an explicit user decision. The helper validates this contract; it does not fetch evidence, establish author aliases, discover membership or turn a citation into verification. A Goodreads book-page URL alone is not a series identity. A provider's parent-cycle ID or canonical series URL can identify a series only after the current work's membership has been established. Aliases and worlds stay with the upstream identity owner.

Every current `facts.work_ids` entry and complete `facts.authors` team must appear in the authority. The frozen binding contains source fingerprint, work IDs, authors, and title/author/canonical_author/series/number/universe. Stale or malformed proof raises `RoutingEvidenceError` (`code='shared_routing_identity'`) with an Edit names remedy. It must produce an honest held/question state, never silent name-based joining. Missing proof preserves the old route. An authorized name decision may rebuild the proof against still-valid memberships; a changed identity needs fresh evidence.

A shared series requires at least two distinct work IDs and different complete author teams. One coauthored book, the same coauthor team on several books, duplicate work IDs, narration or author case/spacing differences do not establish it. A shared world requires at least two distinct works and either different complete author teams or different stable series IDs. Witnesses may be a bounded subset; this is not a library census.

Consumer API: `shared_routing.resolve(review, facts)` returns `{'multi_author_series': bool, 'shared_world': bool}` after validation. The planner uses the series result only for author-folder omission. Accepted universe fields already have the required root/World/Series policy.

## Boundary audit for lead integration

Literal searches for `from organization`, `organization.plan`, `metadata_facts` and `automatic_facts` identified these ends:

1. `standing_metadata.build_policy` / `public_research` produce accepted review and facts. Public research must assemble verified memberships and retain them with a successful result, independently of evictable HTTP bytes.
2. `merge_service` routes naming/grouping preview, accepted approval and chosen-folder overlays. Its ordinary and edited-name paths must carry or deliberately rebuild valid proof from the same accepted identity; it must not rewrite old manifests.
3. `review_backend.routing_preview/save` passes facts to `metadata.propose`, stores them in candidate context, then copies them into the new frozen manifest.
4. `metadata.propose` calls `organization.plan`. `chosen_folder` remains the last planner step; a destination inside the output root replaces the computed folder. An external chosen folder keeps the existing publish-then-reviewed-move flow.
5. `organization.frozen_plan` uses only the manifest's own facts. Consumers include `destination_admission`, `retry_intent`, `conversion_progress`, `migration_planning` and `migration_operation`. Old manifests without the new receipt reproduce their old paths.

Explicit reviewed relocation currently passes an alternate review to `frozen_plan` and stores its separate user evidence. An alternate universe conflicts with a newly frozen shared-proof binding. If relocation of such a new publication needs a changed universe, its owner must explicitly validate/rebind the routing decision without changing the original manifest; this slice does not relax that check or modify the excluded manifest/binding modules. Existing old-publication relocation remains unchanged.

## Verification and applicable lessons

The bounded test selection is `test_shared_routing.py` and `test_organization.py`, currently 45 test methods (19 + 26, measured by anchored `def test_` declarations; not an execution result). It covers Omen books and individual credits, distinct/same coauthor teams, narrator exclusion, two-series and multi-author worlds, conflicting membership, stale/malformed receipts, custom destinations, recording suffixes, unchanged anthology naming, preview/frozen-plan parity and immutable legacy routes.

Execution status: routing-1 passed **45/45 tests** under the exact reviewed, pinned owned runner (lead execution receipt: outer exit 0, native descendants complete/zero, source/runtime/helper postflight passed, no force or timeout, outer elapsed 898 ms). No app, audio read or live-data access occurred. This certifies that pinned routing snapshot only. `git diff --check -- organization.py tests/test_organization.py` passed; Git reported the repository's normal LF-to-CRLF conversion notice for the extended test file.

Applied local lessons: ProcessRules verification discipline requires positive controls and nonzero pass/total reporting; matching names alone are not identity evidence (Brief's exact-series and complete-author rules); full gates run once per final candidate, and targeted checks use the audited owned supervisor with the whole 600000 ms deadline and descendant closure. The QA-source guard remains intact. No source, runtime or guard admission bypass is authorized.

No disposable output has yet been created by this slice. The named task scratch is `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/routing/`; runtime logs/snapshots, when created by the coordinated runner, remain owned by that runner until its durable evidence is recorded.
