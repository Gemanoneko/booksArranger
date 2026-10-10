# Code Review — Books Arranger v0.8.0

## Header

```
Reviewer: Senua (Code Reviewer; inherited Codex model)
Date: 2026-10-10
Tool: Books Arranger
Release: v0.8.0
Commit range: 41119fb063bc895a12b78459b7424b5d7ac17643..exact frozen recovery-retention candidate overlay
Files changed: 19 files, +538 / -107 (line comparison normalized CRLF/LF)
Stand-down dimensions: None; Electron-specific controls do not apply to this Python/local-web tool
```

The reviewed endpoint is the published v0.7.0 commit plus the exact `scratch/recovery-retention-2026-10-10/candidate` overlay declared by `manifest-frozen-2.json`. Manifest SHA-256: `4cd2099b00860704fe88394c31719c1da18851e15e355c0218e8a86e4df198da`. All 113 raw source pins independently matched before review. The 19 promotion paths include source, frontend, tests and current documentation. The VERSION file remains the v0.7.0 baseline; only Sully's target v0.8.0 metadata bump is excluded from this source identity. Any other changed byte requires a new frozen endpoint and focused rereview.

Core pins:

- recovery_retention.py: `d785fc67ca548677fedc26090a8ff1c567780a70ef5238f5a3d806e385ea1969`
- source_cleanup.py: `095d833445d25d116602e4f8fafdfdd3feaf16dabdc423ae408df91a47fcde20`
- storage_cleanup.py: `7985d0b241d9741154c5e19bd0ca301b8a52e5e9303a88cefaf0b86739e00be9`
- merge_service.py: `ecd585b85eafc9b68bf0eaa83f2e8bee7d6ff2e9b56acdc6f4df56d4ffc8883d`
- web_server.py: `4d279122e33e04cfa9fa0cb5a7fb0a52ef873cb2021035e94c221214b5dd75f7`
- web/app.js: `1d0eae4b4716f7f7ce3c2d417220f8f4191b12bd5cc3f3cb201f8958f165150b`

The committed UX/design provenance is cb1167a91ddeeda77b7f393cc5f04278398a2773. Native file/disposition machinery and the refusal to remove directories on an alternate-stream-capable filesystem remain unchanged from the reviewed base. This manifest does not pin Windows, Python, Node or a complete distribution.

## Summary

The change separates immediate verified working-artifact cleanup from recovery copies retained for 86,400 seconds after successful original removal. It adds an immutable completion event, native producer backup identity, startup/periodic idle checks and a selected-book token/count/bytes-confirmed manual action. Review followed deletion admission, output/source/member correspondence, containment, replacement and unknown-content preservation, restoration exclusion, disposition crash reconciliation, cooperative shutdown and shared Converted accounting. Three early mutable-candidate concerns were corrected before freeze: mutable legacy completion timestamps, pre-gating crash reconciliation and loss of resumable state during cooperative shutdown. No Critical or Major findings remain.

## Rubric

Severity and the always-blocking safety floor follow Team/Docs/ProcessRules.md, Severity definitions.

### 1. Security

- Status: Pass — the new POST reuses same-origin/token protection, accepts only bounded identity and observed scope, and exposes no client path, shell command or recursive deletion.

### 2. Correctness & Logic

- Status: Pass — the final frontend targets the actual creation.job.job_id contract, preserves the confirmed selected-book scope and distinguishes retained-but-busy from an actual attention state.

### 3. Crash / Stability Safety

- Status: Pass — exact disposition journals reconcile after restart, cooperative interruption preserves the deleting state, and the owned non-daemon retention worker is stopped/joined before service closure.

### 4. Performance

- Status: Pass — ordinary status reads use registered per-file facts without media hashing/decoding, expiry runs once a minute while admitted idle, and purge hashes the protected output and exact selected copies only.

### 5. State & Data Safety

- Status: Pass — immutable terminal completion anchors expiry, uncertain legacy age preserves files, held native identities and full hashes precede disposition, unknown content and changed output/source correspondence block deletion, and partial purge disables restoration.

### 6. Input Handling

- Status: Pass — stale token/count/bytes and malformed HTTP identity/scope are rejected; reparse points, additional streams, aliases, unregistered files and missing pre-intent names retain the existing fail-closed guards.

### 7. Maintainability

- Status: Pass — retention is isolated in one module and extends existing guarded storage disposal; the existing operation boundary and authoritative Converted predicate remain shared.

### 8. Doc/Code Drift

- Status: Concerns.
- F1 [Minor] `Docs/BooksArranger_Brief.md:110`: the older immediate-purge section is still headed "Current retention policy", although the opening and v0.8 extension correctly describe the superseding 24-hour policy; label that historical section as superseded in the next documentation pass.

### 9. Build & Release Hygiene

- Status: Pass — isolated candidate and raw full-source identity are supplied; no live recovery purge, library mutation, native app interaction or product/Git change was performed during review. Release still requires independent QA, exact promotion, Sully's metadata bump and matching runtime verification.

## Verification and limits

Independent review execution: `C:\Python314\python.exe -B -m unittest discover -s tests -p test_recovery_retention.py -v`, from the frozen candidate: 12 tests passed. This used owned tiny candidate scratch fixtures and controlled clocks; fixture teardown removed them. It covered exact expiry, restart without reset, immutable completion, missing/foreign recovery entries, changed output, incomplete retirement, manual scope, unknown legacy age, native crash disposition, cooperative partial-purge restart and basic admission/worker closure. Focused frozen-2 rereview verified that only README.md, web/app.js and tests/test_recovery_frontend.js changed from frozen-1, and all 113 final raw pins matched. The README immediate-disposal wording and busy-state label are corrected. The actual API creation.job.job_id fallback is now covered by the minimal VM assertion; independently running `node tests/test_recovery_frontend.js` passed. No backend or native pin changed. Producer reports 93 distinct Python cases and four frontend routes; those broader claims remain subject to Futaba's independent receipt, rather than being presented as Senua-run tests. Source inspection also covered HTTP admission, restore exclusion, native missing-folder receipts and the unchanged shared Converted predicate.

No real recovery set was deleted for review. No new audiobook encoding or phone/iTunes validation was required or claimed. Empty recovery UUID directories are preserved; the retained-copy payload is the purge scope. No historical already-purged backups are revived.

## Verdict

- Total Critical: 0
- Total Major: 0
- Total Minor: 1

**Verdict:** RELEASE CLEAR

The remaining Minor finding is advisory and does not block this release. Clearance applies only to the frozen endpoint above and intact safety floor; it is not authorization to bypass runtime guards or delete an arbitrary historical directory.
