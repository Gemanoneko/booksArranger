# Code Review — Books Arranger v0.9.1

## Header

```
Reviewer: Senua (Code Reviewer), Codex gpt-6.1-sol xhigh
Date: 2026-10-11
Tool: Books Arranger
Release: v0.9.1
Commit range: a783061fb057307764ccce815eafbc727bab7959..aea54f581d571ec308edc2bd4aa429d2069cff62 plus the immutable candidate-v2 delta identified below
Files changed: 6 files, +204 / -11 versus the released v0.9.0 baseline
Stand-down dimensions: none; Electron and installer-specific checks are not applicable to this Python/manual tool
```

## Summary

This patch records bounded, sanitized diagnostics for unexpected automatic-processing exceptions, moves failed research out of the active Researching state, and preserves an explicit retry checkpoint without granting approval or starting work on reconstruction. Review covered the accumulated patch against released v0.9.0, including Judy's committed failure-copy addendum. The final endpoint adds one visible checkpoint-save refusal reason and its assertion to the accepted v1 source. No findings remain open.

The historical overnight exception's cause is **unknown**. Its original exception was discarded; a retained-response replay returned ordinary uncertainty. These changes repair observability and failure-state handling. Deliberate fixture faults do not establish the original cause.

## Certified endpoint and method

- Released baseline: `a783061fb057307764ccce815eafbc727bab7959`.
- Source HEAD: `aea54f581d571ec308edc2bd4aa429d2069cff62`; source VERSION `0.9.0`, target `0.9.1`, dirty `true`.
- Immutable snapshot: `scratch/automatic-failure-2026-10-11/candidate-v2`.
- Raw manifest SHA-256: `6a554ed673360ac5297e1c6085459e69f9bd9a5b829039ae2243ba3f64bebce8`.
- Source digest: `094c584492175ebc10fada7c800082e0544eb5e2ee823e068f1656fb3410342f`, computed as SHA-256 of compact JSON for the ordered manifest file entries.

All 65 source files independently matched their raw manifest sizes and SHA-256 values. Baseline comparison identified six changed graph paths: `automatic_processing.py`, `review_backend.py`, their two automatic test files, `Docs/BooksArranger_Brief.md`, and the committed UX addendum. V2 differs from accepted v1 only at `automatic_processing.py:187` and the existing checkpoint-refusal test assertion. Public research, identity, confidence, language, cover, collision, frozen conversion verification, native I/O, original cleanup, retention, and frontend implementations match the released baseline. This is a targeted patch review; it does not recertify those unchanged systems through a fresh broad audit.

| Changed source path | Final raw SHA-256 |
|---|---|
| automatic_processing.py | ffabef649b5bf3c7ccf95aaa51c7e30dd92805335eeb6adad638a9c3ed3a7bb2 |
| review_backend.py | 627846469e19da033c80e56b77b6418aa5f88d012eda1e3858309557532b0665 |
| tests/test_automatic_processing.py | 9bb7bf85e7be0e7a26a4273f3288b4134f4c8940b5b2f7825028209ab8a19261 |
| tests/test_automatic_media.py | dde8191ae6eb9169edb2136b122528b52c5a3c7726589756ebd7baf750474a17 |
| Docs/BooksArranger_Brief.md | d7028fc4ebaeefb4069018512c199a8dcc44509ddaf3d3e498e46479f6331a2c |
| Docs/BooksArranger_AutomaticProcessing_UX_2026-10-10.md | baa2fee2388d5b1891b10498d7625740e88191e5eb66c8ca0830f5647dcd75b3 |

## Rubric

Severity and the always-blocking safety floor follow `Team/Docs/ProcessRules.md` § Severity definitions.

### 1. Security

Pass — arbitrary exception values are redacted; formatting avoids untrusted `__str__`/`__repr__`, source lines and locals. Only a narrow structural-message whitelist and sanitized relative code-frame identities are retained. No new shell, network, credential or filesystem-operation route enters product code.

### 2. Correctness & Logic

Pass — unexpected faults become Needs attention; ordinary uncertainty still holds candidates and continues the pass. Interruption remains a saved pause. The exception handler never approves a candidate or bypasses admission gates.

### 3. Crash / Stability Safety

Pass — failure diagnostics and state are checkpointed together; persistence refusal retains a nondurable memory failure, disables Start and clears the active research presentation. Reconstruction is inactive and explicit retry reuses an eligible saved research checkpoint.

### 4. Performance

Pass — persisted diagnostics have an 8192-byte limit and at most eight code frames; arbitrary message retention is bounded to a digest input. No retry scheduler, unattended loop or additional provider request is introduced.

### 5. State & Data Safety

Pass — the failure transaction updates the run and matching revision/fingerprint candidate without creating approval, queue or cleanup work. Book-specific source-preservation wording is restricted to failed read-only research with no existing candidate job. The current process refuses retry when checkpoint persistence fails.

### 6. Input Handling

Pass — custom unsafe exception formatters, deep traces, long Unicode and fixture secret/path values are handled without exposing their values. Safe built-in structural diagnostics retain factual detail; unavailable historical detail is explicitly identified as unrecorded.

### 7. Maintainability

Pass — diagnostic construction, eligible research retry and job-presence checks are small named helpers. Focused tests distinguish uncertainty, interruption, historical missing evidence and persistence refusal.

### 8. Doc/Code Drift

Pass — Brief and committed UX copy preserve the unknown historical cause and explicit retry behavior. The v1 advisory copy finding is closed by `automatic_processing.py:187`: “Retry progress could not be saved; Start is unavailable.” The existing fixture asserts that reason and empty retry help; the unchanged frontend displays the run reason.

### 9. Build & Release Hygiene

Pass — frozen source and execution identities match, and the owned test route remains bounded. Source VERSION is intentionally still 0.9.0 before Sully's 0.9.1 release metadata change. This clearance permits that metadata bump; other source changes require endpoint reconciliation. There is no installer/package build for this manual tool.

## Verification evidence

Senua inspected source and independently verified the receipts below; Ender and Futaba executed the checks. All declared commands exited zero, reported PASS, and completed with unchanged held source/runtime pins, owned descendant closure and no truncated streams. No production library, database, queue, live service, public provider, account or browser operation was performed by this review.

The accepted v1 graph has digest `4436b4153232ba8d89e3a098774736aec4fdcdf741aa8f2ed8847cd0b3e1b227` and manifest `98b05f7d5858225e6a0fcb5415c9343d36afc1c936f62736e46d557e7727dead`. Both parties ran its same eight fixed commands: 76 Python tests and three Node frontend checks. Futaba separately ran two necessary private cases: a hostile exception formatter/deep trace with durable Needs attention, inactive restart, explicit retry to Held and preserved sources; and ordinary uncertainty continuing across two candidates without a failure or approval. The diagnostic was 925 bytes with eight frames.

| Evidence | Actual result | Manual receipt SHA-256 | Owned receipt SHA-256 |
|---|---|---|---|
| V1 Ender producer | 76 Python + 3 Node PASS; owned 72.755s | fcffad71dd8d3f8de530bbb0ade62265772ad6586cfdf145b118afb5f719d02f | 3471e974e52d4e071fac96069df067a64627f3de5d4d7a6eb05a53582e6d002f |
| V1 Futaba receiver | 76 Python + 3 Node PASS; owned 70.404s | bfc3f0a24bc0caa384d54dd1000f963a3092e74f77e60952c6b41433818f5d08 | 193df5097c38e0553b2169800be0539111c794ea718afb01b6b1b9dae0d65a39 |
| V1 independent private probes | 2 PASS in 0.733s; owned 6.567s | eb5d42bbe4464e80b1520b7d10c2889c25f9eddd1bf9aa28463836659d765f4c | eeb49ef55e7c4eb01906273a6d9e468830ef3b98f13d9a0a95c0ca8f5bc99237 |
| V2 Ender focused producer | 1 checkpoint-refusal test PASS in 0.083s; owned 2.059s | 9d4f7ac37f72695184eb11ac6d4848e2c79a8102bceccedff7704d2eef9bb01a | 21b49acd2eaa5768a7f4515170995ff1dd84b13bfa99e63998421b14bd112260 |
| V2 Futaba focused receiver | 1 checkpoint-refusal test PASS in 0.080s; owned 3.188s | 85e34e854b8712e08af5651f4bb29165359636f64f3dbd6a32de0a1bd5129645 | 74556b36e12e79443c5bcc47ef4c9f808e1e9b2909ff81602470fcd992c33d6c |

The exact v2 manual contract is `e29498625a80a4b153dfb2e33e01344f5cd7dfacc604e06130c994b7de27a371`; inner `qa_checks_v2.py` is `dea9f3a1c5aa3c07d1158683e5693c6af325f927980e03181a1461b690ed3505`; outer `run_qa_v2_owned.py` is `25638a30b9a2f63a55e551a5379281d540f51665c335b7a4893774e3152d9609`. The audited derivative runs only the existing nondurable-failure fixture through its fixed `-k` command. Its trusted native bootstrap, four runtime pins, source holds, hidden suspended child assignment before resume, shared 600000 ms deadline, bounded pipes and final rechecks remain unchanged. Frontend checks were not rerun on v2; their unchanged source and accepted v1 results are the stated evidence.

Senua created no disposable scratch output. Other agents' frozen sources and verification receipts remain owned evidence; this report is the retained review artifact.

## Verdict

- Total Critical: 0
- Total Major: 0
- Total Minor: 0
- Always-blocking safety floor: intact within the certified patch.

**Verdict:** RELEASE CLEAR
