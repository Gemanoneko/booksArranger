# Preliminary slice review — Books Arranger v0.25.0

Senua · 2026-11-04. Read-only review; no tests, app/focus action or live-library/Z: access.

```text
Scope: committed editor and Tolkien slice only
Commit range: 54c6919..d9c0da2c0cb47abae4c75e8d722e06268d6ee600
Product/test scope: 9 files, +346 / -15 lines, ignoring end-of-line conversion
Frozen summary SHA256: 8ef61d13c5c26fe1e257f28892be75c59d0b03cbdc3cccba5e8e6f80ba183310
Frozen patch SHA256: 32a63c8bf258a570e47ea69c0585483d6738df1460d60a47771ac9472543467c
T1 follow-up summary SHA256: f0d8ea122391014006a6d0dab0a69220eccf20be7c97c5492e71f023345b234e
T1 follow-up patch SHA256: 1581dbf83197498bad8a429f9988944431ac40ef428ddc09c0e491068709ffb0
```

Main and origin/main named the exact commit above. The initial nine files and final four-file T1 follow-up matched their respective frozen summaries after CRLF normalization, and both retained patch hashes matched. Package and lock versions both changed to 0.25.0 without dependency changes. Duplicate-cleanup core, the completed milestone, installer and final release clearance are explicitly outside this review.

## Finding

**T1 [Major, closed at d9c0da2] — a pre-existing entered Russian Series value suppressed the new English trilogy decision and its pending-job replan.** In the initial slice, adding `entered_names.fields = ['series']` while a confirmed trilogy review still contained `Властелин колец` preserved that spelling and emitted no `trilogy_routing` receipt, so `pending_changed` returned false. Ender corrected this after confirming the scope with Jane.

The follow-up carries each field's existing `saved_utc` provenance through local identity and metadata facts and distinguishes current `typed_names` from stored names. Only the exact old Russian spellings saved at or before the durable decision record, or legacy receipts lacking that provenance, are superseded. The cutoff `2026-11-04T19:52:41Z` matches decision commit `37ab171`'s recorded UTC; it is not an invented chat timestamp. Later stored choices and newly typed values remain authoritative. Editor prefill follows the same bound `names_decision` receipt for the superseded Series only, preserving Title and chosen folder. The 13-case focused receipt passes with complete owned closure and native zero and covers the old saved spelling/pending replan, later custom/Russian values and current typed values. Senua reviewed the source and receipt without running tests. No new finding arose from this four-file follow-up.

## Checked boundaries

| Dimension | Status |
|---|---|
| Security | Pass for this slice: no expanded external execution, IPC, credential or filesystem authority. |
| Correctness | Pass for the reviewed slice after T1 closure. The trilogy receipt remains bound to a confirmed work/cycle, original title/position, single Tolkien credit and source fingerprint. |
| Crash/stability | Pass: the editor uses the existing 30-second read bound; malformed replies and terminal errors close loading with an actionable retry. |
| Performance | Pass for the changed paths: one bounded editor read and catalog-only pending-job correspondence checks; no new media work. |
| State/data safety | Pass for the reviewed pending hook: only pending jobs without an attempt, output or publication intent can replan; immutable old history uses the existing set-aside/research path. The advanced-generation branch checks complete ordered paths, included order and saved hash/size/time correspondence. No finished-output migration is introduced by this slice. |
| Input handling | Pass: five text proposals plus boolean Collection are required, optional suggestions are normalized, and request generation plus current row revision/fingerprint reject stale replies. |
| Maintainability | Pass for this slice: the trilogy exception has a separate receipt producer/validator and does not become a generic title-only planner rule. |
| Doc/code drift | Pass for the reviewed slice: the superseding English spelling and later explicit choices are now distinguished. |
| Build/release hygiene | N/A for final artifacts: only this committed slice and focused receipts were supplied; the requested milestone is unfinished. Version/lock inputs are consistent. |

The pre-open names/inline draft is retained for Discard. Saved fields remain authoritative in editor proposals, and chosen-folder handling still overrides computed hierarchy. Focused evidence reports 37 unique Python cases and three frontend scripts passing; Senua reviewed those records without rerunning them. That evidence does not cover the unfinished duplicate feature or constitute full QA/build clearance.

Open findings in this slice: Critical 0, Major 0, Minor 0. Resolved findings: T1 Major. No safety-floor violation identified. This is a preliminary slice assessment, not a release verdict. The accumulated v0.25.0 source and exact build still need their final review after all requested work is complete.
