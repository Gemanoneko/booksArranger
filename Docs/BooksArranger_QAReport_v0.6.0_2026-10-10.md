# Books Arranger QA — v0.6.0 — 2026-10-10

**Verdict:** GO

Current clearance applies only to final candidate-v3, digest a83f0ad64bc67b4c26d655f3fc02bfa737678c9bee8720d919417668af4d3f8f. The original data-loss repro now fails closed and preserves the unique replacement. No open Blocker or Major from this bounded QA pass.

## Initial pass history — NO-GO

The initial pinned candidate passes its declared fixture checks but deletes a substituted, unique checked.m4b file merely because it has a recognized staging filename. This blocks cleanup of existing copies until corrected and regression-tested.

## Build and manual handoff identity

- Target version: 0.6.0; candidate VERSION: 0.5.0 (version bump is pending).
- Source HEAD: 205a16d96e27aa207ac250a8e88c1ce3d8ea30ec; dirty: true. This is a pinned prerelease snapshot, not a committed release.
- Source snapshot: scratch/retention-cleanup-2026-10-10/candidate.
- Complete manifest: 96 files; digest 1ed431958fb9c25af1560e2ccda615fa3b13571dad99cf7687398ed7ba67cff7. Independently rederived as SHA256(JSON.stringify(files)).
- Manual contract SHA256: e122082becaf4d04c9f5d17f9655f18c5356cc2bc90b419c27541e5c033f0159.
- Python, Node, ffmpeg and ffprobe byte hashes match the manual contract. All 96 source hashes and four runtime hashes were independently checked before and after testing, with zero mismatches.
- Actual receiver manual receipt: scratch/retention-qa-2026-10-10/manual-receipt-initial.json. The five declared checks all pass; the additional native substitution probe fails. No package checker or formal package receipt was fabricated for this non-package Python tool.

## Results and method

Tests ran sequentially through actual Git Bash, against a private exact 96-file copy under scratch/retention-qa-2026-10-10/candidate-run. The source snapshot was never edited. Fixture deletion used actual Windows handles and disposable files only. The five declared checks finished in approximately 13.4 seconds within one 600000ms total deadline; no timeout, duplicate invocation or background test was required.

| Check | Observed result |
| --- | --- |
| Retention/storage cleanup | 14 Python tests pass |
| Source removal/recovery | 13 Python tests pass |
| Exact cleanup scope | 5 Python tests pass |
| Merge/service regression | 5 Python tests pass |
| Cleanup frontend | Fake-DOM check passes, including existing frontend regressions |
| Independent known-name substitution probe | FAIL: unique replacement deleted; cleanup reported completed |

Count method: Python unittest's completed test counts (14 + 13 + 5 + 5 = 37), plus the separate Node fixture result. These checks cover completed output preservation, source/output tampering, pending/failed audio, paused source cleanup, recovery removal only after completed exact retirement, unknown filenames, hardlink aliases, nested Git content, crash after native disposition, crash before disposition and changed replacements, missing files without verified intent, exact selected cleanup scope, and status/copy for pending/success/failure/historical-retained states. The merge test also closes/reopens its private service and validates restart reuse.

## Bug reports

### Blocker — recognized staging name permits unique-content deletion

Status: open; surfaced immediately to Jane. Candidate: digest 1ed431958fb9c25af1560e2ccda615fa3b13571dad99cf7687398ed7ba67cff7.

Repro: create the existing RetentionTests private fixture (valid completed output and ownership.json), overwrite the stage's checked.m4b with unique bytes, then call StorageCleanup.run(job_id).

Expected: preserve the replacement and report cleanup needs attention because its bytes are not a proved owned output copy.

Actual: native deletion removes the replacement and cleanup reports completed. The final published audiobook remains hash-identical. Replacement SHA256: fb9e02bb37bfe3163272addff41d246e09b665c33350e4ccfee6d256ef9bbe31. Evidence: scratch/retention-qa-2026-10-10/recognized-name-result.json and recognized-name-probe.py.

The declared tests detect unknown filenames and substitutions after recorded intent, but lack a replacement-before-first-intent case at an accepted filename.

Major findings: none independently reproduced. Minor findings: none.

**Pattern alerts:** none.

## Scope and limits

No production library paths were deleted; no real conversion was enrolled; no current service was restarted; no desktop focus, signed-in browser or native UI was opened. Tests generated their own small synthetic media fixtures. Native/UI close-button testing is outside this cleanup-only pass; private worker/service shutdown was exercised by the fixtures. Existing real-data eligibility preview is a separate pass and is not certified by these fixture results.

Current implementation user copy matches the retention addendum in the fake-DOM states checked; this is not a visual layout test. This report does not clear an eventual commit, version bump or changed candidate: any refreshed snapshot needs a new receipt and targeted regression.

## Hygiene

Own private executable candidate copy is disposable and removed after this pass; declared-check logs, manual receipt and the unresolved substitution repro are preserved as evidence. The original candidate and another agent's scratch files remain untouched.

## Fixed snapshot regression — candidate-v2

Date: 2026-10-10. Regression is recorded against an immutable dirty snapshot based on commit 205a16d96e27aa207ac250a8e88c1ce3d8ea30ec; there is no separate fix commit yet. Target version remains 0.6.0; candidate VERSION remains 0.5.0 pending Sully's bump.

- Snapshot: scratch/retention-cleanup-2026-10-10/candidate-v2.
- Manual contract: manual-contract-v2.json; independently rederived SHA256 761b1a1c1955a17aaaca7095950813e76cdba2e26237f54d1c7bd2a92de026dd.
- Complete source manifest: 98 files, independently rederived SHA256 0e866850e130e7e2ecb1a69bca11f44ca2a2fa4cb024492c828ecf5966c10f56.
- Before/after: all 98 source hashes and four pinned runtime hashes match. Candidate unchanged.
- Actual receiver manual receipt: scratch/retention-qa-2026-10-10/manual-receipt-v2.json. All six contract-declared checks pass. This is a non-package manual receipt, not automated package-checker output.

| Fixed check | Observed result |
| --- | --- |
| Retention/storage cleanup | 18 Python tests pass |
| Source removal/recovery | 13 Python tests pass |
| Exact cleanup scope | 5 Python tests pass |
| Actual-media merge/service | 5 Python tests pass |
| QuickTime normalization | 4 Python tests pass |
| Cleanup frontend | Fake-DOM check passes |
| Exact original independent known-name substitution | PASS: blocked, unique bytes preserved, final output and originals unchanged |

Count method: completed unittest counts (18 + 13 + 5 + 5 + 4 = 45), one separate Node fixture, and one independent original-repro probe. The six declared checks finished in approximately 15.1 seconds with a 600000ms aggregate deadline. These are relevant cleanup, recovery, ownership, and normalization regressions; no unrelated suite was added.

The actual-media fixture generates two tiny MP3 tracks, creates and validates an M4B, automatically removes its included originals and temporary recovery/staging payloads, confirms recovery_bytes=0 and restore_available=false, then closes/reopens the private service and confirms output reuse. Completed attempts have no retained payload files. The published output still passes its recorded validation.

The original UNIQUE USER CONTENT repro used the same replacement bytes (SHA256 fb9e02bb37bfe3163272addff41d246e09b665c33350e4ccfee6d256ef9bbe31) at checked.m4b. Cleanup now raises Owned copy differs from approved bytes, reports needs_attention, and preserves the exact replacement, originals, and final output. The added candidate tests also preserve changed inputs.txt/compatible.m4b, refuse unregistered accepted output names, retain recovery after metadata substitution following retirement, and verify complete preflight-failure recovery remains restorable.

### Findings disposition after regression

- Original Blocker: resolved on candidate-v2; exact independent repro verified. Historical evidence remains above and in scratch.
- Blocker: none open. Major: none open.
- Minor, reported by Senua: completed text broadly says working files were removed, while legacy unproven tiny diagnostics may be retained conservatively. Current generated fixture payload cleanup is complete. Copy correction is pending in the live tree and is outside this frozen identity; any changed artifact needs its own matching identity/copy verification. This advisory wording finding does not block the bounded behavior clearance.
- Pattern alerts: none.

No production deletion, conversion enrollment, service restart, desktop focus or browser interaction occurred. The fixed private candidate-run copy was removed after testing. Receipt, test logs and before/after repro evidence are preserved. This GO is not a certification of an untested later snapshot or release artifact.

## Final status/copy delta — candidate-v3

Final behavior verdict: GO for this exact immutable snapshot.

- Source HEAD: 205a16d96e27aa207ac250a8e88c1ce3d8ea30ec, dirty: true; target 0.6.0, candidate VERSION 0.5.0 pending bump.
- Snapshot: scratch/retention-cleanup-2026-10-10/candidate-v3.
- Complete source manifest: 99 files; rederived SHA256 a83f0ad64bc67b4c26d655f3fc02bfa737678c9bee8720d919417668af4d3f8f.
- Manual contract SHA256: 7a087010a570204d12b69e7a8e6a8e45b60cc73d421de52bb0b4607aa41663b1.
- Actual receiver focused manual receipt: scratch/retention-qa-2026-10-10/manual-receipt-v3.json. Before/after hashes match for all 99 files and four runtimes.

Delta was independently compared with tested v2: source_cleanup.py adds display-only regular-file evidence counting and truthful verified-copy completion text; web/app.js renders that text/count; corresponding frontend and one existing status assertion change. Docs/reports change. No files removed. storage_cleanup.py, producer hash recording, native disposition, original retirement, restore, conversion and QuickTime normalization implementations are byte-identical to v2. The 45 completed Python checks and frontend check from v2 therefore remain the behavior evidence; the full 45 were deliberately not repeated for this status-only delta. This is a focused manual delta receipt, not a fabricated full-v3 suite pass.

Focused results:

- Existing completion/retirement/status Python check: pass.
- Actual app.js fake-DOM frontend: pass, including verified-copy completion, pending/failure states, historical retained sources and Unverified legacy evidence retained: 3 files.
- Independent backend status probe: pass. One present regular evidence file counts as 1; a missing record and directory count as 0; removing the present fixture evidence changes the live count to 0. Completion retains recovery_bytes=0 and restore_available=false.

The advisory wording Minor is resolved on v3: status now says verified temporary recovery and working copies removed and separately displays any unverified legacy evidence retained. No open Blocker, Major or Minor in the bounded QA scope. Pattern alerts: none.

No production action or UI session was used. Private v3 executable copy, temporary diff inputs and completed probe scripts were removed after recording results. Small identity receipts, check logs and historical/final observed-result evidence are preserved. Clearance remains snapshot-specific and does not certify a changed artifact.
