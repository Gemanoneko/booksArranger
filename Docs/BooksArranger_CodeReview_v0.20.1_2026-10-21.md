# Code Review — Books Arranger v0.20.1

## Header

```
Reviewer: Senua (Code Reviewer), inherited supported review tier
Date: 2026-10-21
Tool: Books Arranger (Electron / Python)
Release: v0.20.1
Commit range: d20734dddc02e8627940c41b0d0dbe49dc4d6a44..968d4cebba39b49ec8c228f6a03cb7f6b5d0bcc9
Release source commit: 968d4cebba39b49ec8c228f6a03cb7f6b5d0bcc9
Release artifact manifest SHA256: 21c988593b6ecd43719751ec8e0d0055d0e5c52505778e7034b716ef78294f0d
Reviewed source: C:/Antigravity Projects/Worktrees/Books Arranger/qa-0.20.0
Branch: codex/books-backfill-lineage-0.20.1
Files changed: 7 files, +231 / -15
Stand-down dimensions: none
```

Written in the original desktop Docs directory; the clean QA checkout is not edited. This is source acceptance. The actual artifact is bound below; actual packaged QA remains pending. No previous artifact or packaged GO certifies this patch.

## Summary

Reviewed the complete seven-file delta against the released v0.20.0 tag: two production modules, two focused test modules, the matching package/lock version fields and changelog. Completed series backfills intentionally retain the initial publication intent while updating the current receipt. The resolver now admits only a validated single completed successor, replays the producer's exact receipt transformation and freezes the complete canonical backfill record alongside original-intent, current-receipt and current-manifest digests. It never rewrites historical rows. Expected per-book binding refusals remain explicit held outcomes rather than aborting all enrollment.

## Rubric

### 1. Security

- Status: Pass. No new shell, IPC, network, credential or renderer capability; existing absolute-path and identity checks remain enforced.

### 2. Correctness & Logic

- Status: Pass. The successor must match the same completed job, original intent, root, parent ancestry, temporary namespace, review and provenance; unexplained receipt changes refuse. Existing routing consumers accept the additive internal envelope while authoritative resolution and transitions rederive its full binding.

### 3. Crash / Stability Safety

- Status: Pass. Enrollment refusals occur before mutation or roll back their own savepoint. Other errors still abort. Re-entry validates the unchanged durable lineage and completed relocation instead of reconstructing receipts or copying again.

### 4. Performance

- Status: Pass. Lineage validation performs a bounded same-job lookup and canonical metadata hashing; media hashing, verification bounds and copying behavior are unchanged.

### 5. State & Data Safety

- Status: Pass. Initial journal intent and current output remain immutable provenance. Changed DONE records invalidate enrolled bindings; native file, media, durability, generation and original-removal safeguards are unchanged. Completed-candidate accounting retains held outcomes and planned bytes count only actual enrollments.

### 6. Input Handling

- Status: Pass. Missing optional series_proof is admitted only for the historical Goodreads/FantLab producer shape with otherwise complete authority; malformed present values, new-provider absence and manifest-declared missing proof refuse. Absence is preserved in the raw-record digest and cannot silently become an empty object.

### 7. Maintainability

- Status: Pass. One explicit lineage validator serves plan, resolve and transition; the compatibility rule mirrors the existing producer without adding a parallel mutation protocol.

### 8. Doc/Code Drift

- Status: Pass. Changelog describes verified lineage admission and per-book holds; no native eligibility or live migration success is claimed from SQL-only evidence.

### 9. Build & Release Hygiene

- Status: Pass. Exact reviewed product/test pins match committed source; package and both lockfile root versions are 0.20.1 with no dependency changes. Canonical and artifact acceptance remain separate required release evidence.

## Evidence

Frozen SHA256 pins independently rechecked after commit:

- publication_locations.py: 3e857e97bf5eb77efda3fd02f54b05bf0f9b9ad307e1b44ca451c2a91b9e3e3a
- migration_planning.py: 6ad88ea2566a68a74d46f9b1b132efefa183009a8b7835e01c4dcc43e9c7e7b8
- tests/test_publication_locations.py: abbece70078c151e84f2f5cb5a0929503b1a47875acab92fc5b8318ffb27f654
- tests/test_migration_planning.py: 49816506340a06933ecb002e29e064d37a09e9e4da13deec3151fa87956ff7f7

Actual focused whole-module receipt lineage-focused-owned-result-5.json SHA256 c7d4cd4bcbd4e5bd6cb285f7cea809325284d38fea13b2ad18dbc2d84dda3282 was independently read and hashed: 50 discovered/run, zero failures/errors/skips; helper exit 0, complete output, native owner closed/complete/zero with 178 retained handles signaled, no forced termination, timeout, overflow or truncation. Includes real isolated legacy retag → enrollment → native verified relocation → re-entry → changed-DONE-record refusal. This is private fixture evidence, not live media migration proof.

Historical producer comparison establishes that commit 902d3128943544ec07772fa489e94b9559ca126d introduced optional series_proof alongside additional providers; the preceding Goodreads/FantLab producer omitted it. Immutable actual-catalog predicate checks account for 345 ordinary and 87 completed-backfill publications, but do not establish fresh native/media eligibility.

## Verdict

- Total Critical: 0
- Total Major: 0
- Total Minor: 0

**Verdict:** RELEASE CLEAR

## Actual artifact binding

Independently read and hashed the new manifest at qa-0.20.0/dist/release-artifacts.json: SHA256 21c988593b6ecd43719751ec8e0d0055d0e5c52505778e7034b716ef78294f0d, source968d4cebba39b49ec8c228f6a03cb7f6b5d0bcc9, build4630f60c-9fa4-4bde-ac70-dab9aaec43f3, product76cd92e96e18f3fb0fbf5ece3b4ca03442adeb2b8e12f9d592cb96d69f60ca28. Shell/backend0.20.1 and verified/installer_equivalent are true. Canonical sender/receiver1220 Python,57 Node,16 frontend,8 syntax PASS and closed native groups were reported separately; this source review does not replace Futaba's independent receipts. Final A/B literal binding reviewed; actual packaged behavior/closure verdict remains pending Futaba.
