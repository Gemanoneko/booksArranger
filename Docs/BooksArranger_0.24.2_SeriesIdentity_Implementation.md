# Books Arranger 0.24.2 — series identity implementation

Owner: Ender, adjacent identity slice, 2026-11-01. Authority: scope `3d4f0d2` and UX `070ec34`. Exact evidence comes from `BooksArranger_SeriesPreview_Diagnosis_2026-11-01.md` and the committed `BooksArranger_DiagnosisEvidence_2026-11-01.json`. The diagnosis's former approval caveats are superseded by the committed full 0.24.2 scope.

## Implementation status

| Item | Implementation | Verification |
| --- | --- | --- |
| Successful research lost after HTTP cache eviction | `PublicResearch.approved(..., retained=None)` validates a current retained result, then supplies durable catalog/title/series evidence to the existing metadata rebuild; it does not copy an old approval | New targeted tests authored; execution pending |
| Matthew Corbett rejected as a person's name | Full McCammon identity, the two confirmed work-title aliases and exact positions 1/2 allow this specific eponymous series through the existing folder veto; unrelated person folders retain the veto | Positive and negative cases authored |
| Queen's four internal sections treated as separate novels | `part_sets.confirmed_edition(row)` recognizes only the four named M4Bs, same parent/book album, matching real author-role credits and nonconflicting track numbers; returns the existing ask/approve-as-one-book state with ordered paths | Exact-set and missing/mixed/explicit-keep controls authored; lead owns regrouping existing automatic volume decisions |
| Tolkien world and exact cycle | Work IDs `fantlab:1668` / `fantlab:1669`, matching original titles, exact cycle `Властелин колец` at positions 2/3, stable cycle `fantlab.ru/work1693` and Tolkien credit carry the confirmed Middle-earth relationship | Included in cache-loss approval tests; typed/saved universe including empty remains authoritative |
| General shared series/world routing | `attach_shared_routing(result, peers=())` aggregates independently current accepted peers by stable series/world identity, with complete work IDs and author teams. Explicit Omen membership is additionally bound to the two confirmed titles/authors | General non-Omen series/world, unrelated same names, book-page rejection, Omen/wrong-author and override controls authored |

## Ownership and boundaries

Owned implementation files: `public_research.py`, `local_identity.py`, `part_sets.py`. New tests: `tests/test_series_identity_242.py`. This document is the only new identity implementation note. The earlier planner slice remains in `organization.py` / `shared_routing.py` and its two dedicated test files; its first pinned snapshot passed 45/45 tests and is not changed here.

Lead owns `merge_service.py`, `review_backend.py`, `automatic_processing.py` and all regroup/retry/queue/renderer integration. Chapter repair remains the separate chapter worker's responsibility. No existing manifest/binding, release, version or Git operation is changed by this slice.

## Retained research contract

The new optional argument to `PublicResearch.approved` is:

```python
retained = {
    'candidate_id': current_row['id'],
    'revision': current_row['revision'],
    'fingerprint': current_row['fingerprint'],
    'result': saved_successful_identity_result,
}
```

Lead supplies it from the current automatic-candidate row and first applies dependency-aware `rules_changed_for`. `retained_gap_fields(row, local, envelope)` independently checks the exact current binding, supported research/source-gate version, standing metadata validation, work identity, current full author and title aliases, saved-name digest, absence of conflicting holds, catalog receipt hashes/timestamps and cycle-number agreement. Old current Tolkien results remain eligible without a newly invented digest: absent saved-name proof means the existing `entered_names.NONE`, matching a current book with no entered names. A genuine saved-name change invalidates the retained result.

Accepted retained data are inputs to `_local_lookup`, carrying their actual receipts and work aliases. Current rules, typed names, selected author, source gates and naming policy still rebuild the output. A typed title wins; typed series/number and an explicit universe clear win. Wrong candidate/revision/fingerprint, conflicting current series, mismatched work receipts, changed rules, missing author credit and non-piece identity holds are not silently reused. Internal Books 3–6 never supply trilogy positions; the source-bound catalog cycle supplies 2/3.

Both preview and Approve must call the same lead-owned `_approval_result` using this argument. No HTTP body is required to replay a durable accepted identity; ordinary evidence receipts are preserved as provenance rather than relabelled as freshly fetched.

## Shared routing producer contract

`attach_shared_routing(result, peers=())` returns a detached result, rebuilding `metadata_facts.shared_routing` for the new accepted review. Peer results must already have current source, rule and saved-name bindings established by the caller. Membership uses a canonical FantLab cycle URL or Goodreads series ID; an arbitrary matching display name or Goodreads book URL supplies no membership. Conflicting credits for one work are refused. Equivalent complete author-credit spellings do not create another writer team.

For a generic explicit world, `work.verified_world` contains `{id, name, basis: 'catalog'|'user', evidence: [receipt IDs]}`. Only the same stable world identity combines peers; each member carries its separately established series ID, or no series for a standalone. Accepted universe labels already use the existing root/World/Series hierarchy. The helper does not discover relationships from those labels.

The Omen user decision is scoped to The Omen / David Seltzer / 1 and Damien / Joseph Howard / 2 in the accepted Omen series. Each book retains its real author and computed filename. The Tolkien relationship is separately scoped to the exact retained work/cycle identities. No author is inferred from composer/narrator metadata.

Lead calls the helper after final accepted review assembly with its eligible peers. A changed review gets a new validated proof; an old queued or published manifest is immutable. Explicit per-book destination facts remain untouched and take precedence in the planner. No migration is started here; existing publication locations and receipts retain their own proof.

## Queen regroup integration

`part_sets.confirmed_edition(row)` returns `None` or an ask decision with `basis='confirmed_internal_sections'`, `ordered_paths`, `parts=4`, the confirmed book/series/number and a user-decision identity. `PublicResearch._part_set` checks it before the generic distinct-work-title heuristic. The function performs no media reads, filesystem operations or database writes.

Lead must use the same predicate when re-evaluating previously automatic `part_volumes` records, and only when they are `kept=false` and the exact current set is unreviewed/unowned. Actual Keep as separate books choices, already reviewed groups and job ownership remain authoritative. Approval still uses existing complete M4B/chapter preservation and admission checks; this exception does not establish audio completeness or repair chapters.

## Check status and local lessons

`tests/test_series_identity_242.py` currently declares 19 test methods (counted with anchored `def test_` declarations, not an execution result), with parameterized negative controls. It reads only the committed compact evidence file; fixture member paths are replaced with private synthetic C paths. It starts no app, network request, database read or media process.

Execution is pending a concrete source/runtime/runner-pinned owned-process batch reviewed for this graph. The prior routing-1 admission is not blanket permission for the new graph. No full entry check is run here. The required whole deadline is 600000 ms with descendant closure; a timeout is reported without duplicate firing.

Applicable lessons: exact whole-author/work identity before membership; current names/rules outrank cached proposals; no same-name merging; positive controls and nonzero pass/total counts; one final full gate; preserve immutable publication receipts and explicit separation. No new source audio read or live-data write occurred.

## Concrete series-1 preparation (not executed)

Frozen scratch: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/series-1`. The exact fixed19-method batch was copied from the admitted routing-1 shape with unchanged runtime/owner helpers. Source includes90 frozen root Python files (only the3 owned producers replaced), one test and one committed evidence fixture:92 files. All source/runtime/ownership files were read and hashed; single-link ordinary files required. Actual runtime47-file digest and ownership92-file digest match routing-1. Work is empty; output leaves absent. Source/helper/runtime inputs remain frozen pending the separate admission.

| Artifact | SHA-256 |
| --- | --- |
| `driver.mjs` | `63e543f3fb39940c4bfb1ec8be89f7a91f08994f1a0d96a433176db75a24fc29` |
| `plan.json` | `6d2d8ced8bed5b5ca8d240c569943b223abab19a5eb08885b2e1d150d99a9f89` |
| `invocation.json` | `d3cbce86b3639570c2136d611eaddbfb621cc12eebdc68f2a145d0c9e8537da1` |
| `run-targeted.py` | `89969b5f6a3d7d36c5cd7f89f9abf2d952229feaeb015894fdd26234fb872b57` |
| Source tree | `9b2bd07ed78ed910a228a9626823688285a0a1ca0b4e97f3d3cc272058060324` |
| `preparation.json` | `51eab737039dfbfb92f187a50966b09ee26876c41470467eef390f6f1579009d` |

`graph.md` declares the exercised import/call graph and mocked boundaries. No test, media, network, database or application process was launched during preparation. Existing routing-1 result remains45/45; this new batch has no pass/fail result yet.
