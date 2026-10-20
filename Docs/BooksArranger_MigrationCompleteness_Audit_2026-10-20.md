# Migration completeness source audit — 2026-10-20

READ-ONLY source assessment; no planning, NAS/media IO, catalog write or migration was run. Audited desktop migration_planning.py, migration_operation.py and CurrentAudiobooks.publication/protected in current_audiobook.py, plus saved current-book evidence c313cc98fae579477e043662dfd053ca80cd5c40f5c127a48262d6910b3ee131.

## Finding

The planner does **not** use the running app's in-memory Ready384 set. It enumerates current nonsuperseded candidates across configured sources (planning54), then revision-bound approved contexts (64–75). The captured407 distinct current completed candidates all have current approved contexts. Each therefore reaches the planner's eligibility evaluation; it is enrolled/already-at-destination, or receives an explicit held/deferred reason. This is a source-path conclusion, not an actual407 native inventory result.

Publication selection is independent: CurrentAudiobooks.publication79–93 selects the representative base/replacement or authoritative current chapter variant; ambiguous/invalid lineage refuses. protected124–158 requires effective location/provenance, native held file size/link/ancestry and fresh derived journal binding. planning85–100 checks persisted stat verification and otherwise performs bounded full-byte SHA256, rather than treating cache absence as exclusion. planning104–108 uses immutable parent destination for completion eligibility when metadata/revision agree, avoiding newly proposed routing as an accidental old-path veto. Outcomes are explicit held/deferred128, collision-held131, already119, or enrolled141–143. The operator executes only reviewed enrolled publication entries; it does not discover or silently add missing books.

## Completeness limit and finite next proof

No actual reason for the numeric407−384 difference was established. No new subset should be inferred from that subtraction. After the supported drain, the existing coherent current-completed-candidate census must be reconciled by candidate ID against **all** planner outcomes (enrolled, already, held/deferred). Every one of the actual drained completed candidates must occur exactly once, including the selected active variant and concrete reason for any hold. Keep historical/base/chapter alternatives separately retained; do not silently import them twice. Fresh native validation, immutable receipts, journal/lineage, routing, collisions, copy and removal proofs remain mandatory.

A general future-snapshot accounting gap is visible: planning68 increments not_approved without an individual ID/outcome, and context-unavailable outcomes do not carry the candidate's completed-publication census. Thus aggregate scope_counts alone is not a machine-checked assertion that every successfully completed candidate was accounted. It does not exclude any of the measured407 by the metadata-approved flag; all407 passed it in the saved snapshot. Minimal source change **if an enforced completeness receipt is required**: migration_planning.py only, add an independent current-completed-candidate census and exact per-ID outcome reconciliation (including unapproved/context-missing holds); preserve all eligibility/native checks. Do not change the operator's move authority or broaden enrollment.

Finite verification: completed candidate with absent in-memory cache remains hash-eligible; mismatched current review/source scope is explicit held; completed-but-unapproved candidate is explicit held rather than count-only; one outcome per census ID; no lost/duplicate outcome; base/derived/replacement variant; budget-deferred candidate remains accounted. Existing actual native base/derived fixtures can be reused after independent source approval.

## Pins

migration_planning.py SHA256 c59903d054227656a22ff6ef0fbe0f88d9dfa6392ccf04a9f10af983fa910bfb
migration_operation.py SHA256 5d20571a9f44f26c57091f316d0627aad6a7f9de7a180a905a25691a60bc4470
current_audiobook.py SHA256 6d7532581bc6eeaf16d338ca2bbd61f7cf7391ef85578e9fb185a26e74d0bc4d
