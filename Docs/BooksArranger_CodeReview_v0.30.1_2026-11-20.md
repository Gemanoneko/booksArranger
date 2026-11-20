# Books Arranger 0.30.1 delta code review

Reviewer: Senua
Date: 2026-11-20
Commit range: 2c7129f84b394e0f086f94222935e812ce3d6412..f658d2ecbbd0c938b911715b3becac7300474ac9
Release source commit: f658d2ecbbd0c938b911715b3becac7300474ac9
Release artifact manifest SHA256: 54468fbe13d1a9d160f1d3f98bfee22d749b9c2e8c4c77ff3298118634c7ae73
Build ID: 5986017e-17a2-487a-a4d0-f087e4f70de6
Product tree: 23c25240636f1c8774c4d1dd9dcc4dae04df3346dba3799295428d980bddb447

## Scope

Git reports five commits and 19 files (+1247/-24) since the previous certified source. The product patch and scan fixture correction since the released baseline at `44ffe21` span 11 files (+135/-23). Senua m-d2 is resolved for new and previously recorded repair failures. The previous report retains the unrelated m-d1 finding.

| Dimension | Result | Evidence |
| --- | --- | --- |
| Security | Pass | The diff introduces no process launches, credentials, IPC, or filesystem destinations. |
| Correctness and logic | Pass | Manual and automatic conversion distinguish an internal repair failure from confirmed damage. The renderer test passed independently. |
| Crash and stability | Pass | The scan fixture runs its real source check and joins its thread with bounded waits before removing the catalog. |
| Performance | Pass | The new cleanup lookup applies only to rows with a classified internal repair failure. |
| State and data safety | Pass | Manual retry rechecks revision, ownership, output, cleanup and retained work in its transaction. Automatic retry checks the frozen job, revision, cleanup and publication state, then conditionally requeues the same job. Repair uses a private copy and preserves the original. |
| Input handling | Pass | Retry uses typed failure fields. The source index and path bind the automatic error message to the failed file. |
| Maintainability | Pass | Both admission paths share the failure classifier. |
| Documentation and code | Concerns | Minor D1 below. The changelog describes the actual behavior. |
| Build and release hygiene | Pass | The official entry receipt pins the clean source. The package lock matches its build pin. All three upload assets match the accepted manifest. |

**Minor D1.** The docstring in `audio_jobs.py:182` enumerates four retry causes and omits the new `part_repair` cause. The comment at line 937 also describes an incomplete set. Update them together when this code is next maintained.

## Independent checks

- Ran seven in-memory journal cases against the packaged backend. A 0.30.0-shaped internal failure with its legacy false retryable flag was eligible. Existing cleanup, publication intent, and existing output each stopped automatic eligibility. An unexpected stage, another exception class, and confirmed damage each stopped eligibility on both paths. Confirmed damage produced the replacement-source remedy.
- Ran the targeted renderer DOM test using its synthetic fixtures. Reviewed the source-preservation tests and checked the official `e031c/ender-entry.log` receipt for this exact clean source. The receipt records a passing check and clean personal folders.
- Byte-compared the three changed product files to the package, hashed its installer, blockmap and update metadata, and verified the raw lockfile hash. Installer SHA-256 `bf386538e357e140e750ff2650fa47dcbec6cac13c93918b8f12fe7b523c7172`. The publisher will execute its project-local recovery check before upload.

## Verdict

**Verdict:** RELEASE CLEAR

0 Critical, 0 Major, 1 Minor in this delta. Safety floor intact.
