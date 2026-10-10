# Code Review — Books Arranger v0.9.0

## Header

```
Reviewer: Senua (Code Reviewer; Codex gpt-6.1-sol, xhigh)
Date: 2026-10-10
Tool: Books Arranger
Release: v0.9.0
Commit range: c10f80f0fe597167713b388f30252ee65fd923bf..exact frozen candidate-v4 overlay
Files changed: 22 files, +1843 / -94 (line comparison normalized CRLF/LF)
Stand-down dimensions: None; Electron-specific controls do not apply to this Python/local-web tool
```

The reviewed endpoint is the released v0.8.0 base plus the complete `scratch/automatic-processing-2026-10-10/candidate-v4` graph. All 65 raw file sizes and SHA-256 pins independently matched. Manifest SHA-256: `25cdf64750d66194a8ef6960b9cbd0fca0ab43070915bf7fb0db94038be5ca39`. Declared normalized source digest: `dbd2cacc10601f77a87ec48f8760e0a83dec909830a9c03f80d2504095d68084`. Source HEAD and committed UX provenance: `11786f36598d058debee2aa108b8e1c12b7a5b60`; dirty true; source VERSION 0.8.0; target 0.9.0. The diff covers 21 declared promotion paths plus the committed automatic-processing UX document.

Three declared frontend overlays come from `scratch/automatic-processing-2026-10-10/working-frontend/web/`; the canonical serving directory was restored to released v0.8 assets while review proceeded. Backend and these exact assets require coordinated promotion. Only Sully's target VERSION metadata bump is excluded from source identity; any other changed byte requires a new frozen endpoint and focused rereview. The manifest does not pin Windows or a complete distribution.

Core pins:

- automatic_processing.py: `3f390b35579daf740d6dd6e49f50ed52c2ed5a7bba63b11f1005065bb2e95045`
- public_research.py: `2914db510aefaab63a9d30855ca5d8cdc01fbeb6eef96b13b3c978bfe16c27e9`
- source_identity.py: `afcc75d8af9220aa8f0f021528c9e72395bfbcbefc2df2a02efb5729ba3f4412`
- groups.py: `504226d30baad63bc7221b2f0779d6a02c8eab0377e76e98b3e58a289b41f875`
- merge_service.py: `b89f6ed00ec8e062916e6f77da2b8d6900f450c4ab85de97d8cb9c3d17ffce9a`
- audio_jobs.py: `cf1d41f1575a3bc91253019371b6c9adec0e80ade2717515111eeb6b9eb0dfae`
- review_backend.py: `a8fd9f5f6d34e7dde702ae2bcc27d8da2f56300d49eb4b18ad8f4cb67401424b`
- web/app.js: `c6ba90792dcee02ef1fd1130f016d6652108919439ead3b5d7f3d72bf2accc5c`

## Summary

The extension partitions unapproved audio groups from local evidence, researches work and translation identity from fetched public sources, preserves active manual drafts, and admits sufficiently supported candidates through the existing frozen conversion and cleanup pipeline. Review followed source membership, author/reader roles, contradictory evidence, public transport, budgets, checkpoints, fresh protected source checks, final approval/job transaction, Converted accounting, frontend contracts and native compatibility. The frozen v4 endpoint has no open findings.

## Rubric

Severity and the always-blocking safety floor follow Team/Docs/ProcessRules.md, Severity definitions.

### 1. Security

- Status: Pass — public requests are bounded HTTPS to declared hosts with global-address validation, pinned TLS, redirect refusal and a fixed owned DNS child; UI rendering uses text content and approved source links.

### 2. Correctness & Logic

- Status: Pass — work, translation, author and reader evidence remain distinct; every provisional subgroup stays visible, and unsupported or contradictory candidates are held.

### 3. Crash / Stability Safety

- Status: Pass — explicit Start resumes saved work, Stop propagates through scan, fetch, source hashing and decoding, and unavailable sources remain pending for an explicit retry.

### 4. Performance

- Status: Pass — serial research uses per-candidate and daily request budgets, host cooldowns, bounded response/cache sizes and a shared fetch deadline with owned resolver teardown.

### 5. State & Data Safety

- Status: Pass — automatic metadata stays unapproved until the final context and frozen job are enrolled in one transaction; current source/member/order/destination checks precede the unchanged verified-output and guarded cleanup route.

### 6. Input Handling

- Status: Pass — strict public JSON, ignored script/style content, typed author-credit rejection, bounded URLs, source disagreements and protected manual drafts preserve candidate isolation and prevent automatic admission.

### 7. Maintainability

- Status: Pass — public transport, source identity and automatic orchestration have separate modules and reuse the existing review, frozen-job, converted-state and native disposal boundaries.

### 8. Doc/Code Drift

- Status: Pass — current docs describe the conservative public-source pilot, held cases, explicit Start after source cooldown and the superseding 24-hour recovery policy.

### 9. Build & Release Hygiene

- Status: Pass — the complete immutable source graph and staged frontend overlays are declared; only Sully's target-version metadata bump is outside this source certification. Exact promotion and independent QA remain release requirements.

## Corrections verified during this review

Earlier candidates exposed omitted provisional subgroups, contradictory translator credits treated as authors, approval leaking before a rejected destination, stranded source-waiting state, provenance rendering drift, and Stop gaps at cover decoding or the last source check. The final graph preserves subgroup coverage, rejects explicit non-author roles, keeps pending metadata outside approved/ready scope, atomically commits final approval with job enrollment, retains deferred candidates for explicit Start, and propagates interruption through owned work. Fresh held-source tags and hashes are rechecked. DNS resolution moved into a fixed hidden owned child. V4 differs from v3 only in `automatic_processing.py` and its test: an actual 300-CJK title exceeding the bounded URL limit becomes Held, and the next eligible candidate proceeds. The guard catches ValueError only; ResearchWait and InterruptedError retain their existing handling.

## Verification and limits

Senua performed source review and independent identity/delta verification, and audited the fixed manual supervisor; Senua did not execute tests, public network requests, live library scans, conversions or deletion. Producer v3 receipts record 69 Python checks and three frontend checks passing. The verified producer v4 focused receipt records one actual long-query regression passing in 0.913 seconds, SHA-256 `37810d62ec6b90c6889c8a31493192b02b6b78f1b42338a092b058209707c730`. These are producer execution results, not independent Senua runs.

The final manual graph declares 70 Python checks and three frontend checks in the same eight fixed commands. Audited v4 contract SHA-256: `308b40f14998a643cea209ecb293eb0e04f24db0049280b64cabbbc1479eb377`; inner harness: `2b49c20b1e997e0cf3beccf0b8cd676d342cda29a1f649ef2069e213fe28de56`; outer supervisor: `9770e1f5df0fced1ca5b9e83d2902ccc1f455e357601290add4d97246e362b2b`. It retains the previously reviewed native supervisor and four exact runtime pins, verifies media executable resolution from the private fixture directory, holds/rechecks manifest and source/runtime identities, and covers all descendants with one 600000 ms budget. V4 harness changes are source pins, declared counts and declared delta only. Matching sender/receiver results and the independent behavior verdict belong in Futaba's v0.9.0 QA report; this source clearance does not substitute for that gate.

Public lookup is broader than the two seeded work records: it makes per-candidate catalog queries and discovers links from search and Wikipedia to approved publisher/journal sites. The two `public_source_leads.json` records are leads whose pages must still be fetched and checked. Search snippets, co-occurrence, article language, nationality and model scores are not approval evidence. Original language comes from the structured work field; a non-Russian canonical title needs the supported published-title/credit bridge. Japanese name-order uncertainty, conflicting roles, ambiguous collections/series, unsupported formats, missing or differing cover images and destination collisions can remain held. Exact local track consistency does not establish completeness of an external commercial recording.

Producer actual public-source receipts and synthetic media conversion fixtures are separate evidence. Successful fetched identity evidence alone does not demonstrate automatic conversion eligibility for the real book. Senua certifies neither a new live public smoke nor real-library automatic conversion from those receipts. The verified-output publication, native source disposal, required working cleanup and 24-hour recovery implementations remain inherited from v0.8.0; their admission through the new automatic path was reviewed. Native app construction remains passive.

No code, git, version, runtime or library mutation was performed by Senua. Senua created no scratch output; candidate snapshots and other agents' receipts remain with their owners, including historical failure evidence.

## Verdict

- Total Critical: 0
- Total Major: 0
- Total Minor: 0

**Verdict:** RELEASE CLEAR
