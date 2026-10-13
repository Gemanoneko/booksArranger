# Books Arranger Electron build/release preflight

Reviewer: Senua. Date: 2026-10-13. Exact scoped range: e827b5bf866be2690279c155bb729afbf73c9d1d..fb9038abdd3c6c5aef3b16bc7bb7eb6c88c1664f. Diff: 20 files, +1174/-229. Read pinned Git blobs; concurrent desktop/CAS edits excluded. This is early construction review, not full installer clearance.

## Findings

**E1 — Critical, scripts/release.mjs run():** actual subprocess selection uses bare PATH git and independently resolved ghExecutable() rather than the exact natively retained proof.executables. A preexisting earlier PATH executable can run outside the proved tool identity. The documented trusted Node/Python bootstrap assumptions do not authorize arbitrary Git/GH fallback. Use only the retained fixed executable paths, validate correspondence with the lease, and refuse all fallback. At this pin E2 below refuses release before these subprocesses; fix E1 before correcting that admission bug.

**E2 — Major, scripts/release.mjs ownedRelease():** it requires ownedRoot equal checkout root, but build_native always publishes a fresh build-cache/builds/UUID ownedRoot. Genuine release capability is rejected. Fail-closed, not a successful release path. Validate the exact lease's fresh child path without broadening authority.

**E3 — Major, scripts/build_native.py bootstrap():** desktop_host.py is imported/held but absent from fb9038. The frozen supervisor cannot bootstrap; any success relying on the dirty desktop helper is not evidence for this pin. Include the reviewed dependency at a new pin before sender/receiver execution.

## C4 progress and unresolved cleanup contract

Original M1 recursive deletion routes are removed: fetch/stage call one guarded transaction; clean-dist preserves existing output. Native BuildTree protects ordinary ancestry, rejects existing intermediate junctions, creates fresh directories relative to retained parent handles and writes CREATE_NEW; no old folder is recursively adopted/deleted. The six committed guard cases directly include the original preexisting intermediate-junction refusal, hardlinks, traversal preflight, collisions and retained-parent swap. This statically addresses the original C4 path. No independent execution on fb9038 was claimed because E3 prevents the complete frozen native route; original C4 closure needs the corrected pin's actual owned proof.

Known previous-pointer refusal remains fail-closed and exact archival/CAS is actively being implemented; not duplicated as a new finding. The presently uncalled remove_manifest_files helper matches only SHA256/size and lacks prior native producer identity and hidden-stream checks. Any future destructive caller must supply/verify those receipts and refuse identical-byte replacement/ADS; this note is not acceptance of the unfinished archival path. No speculative hostile future builder-descendant insertion or documented trusted bootstrap pre-spawn window is claimed closed.

## Evidence and limits

Reviewed all scoped scripts and guard/release tests, pinned docs, and native VerifiedFile/DirectoryBoundary/disposition consumers. Exact retained-source/UUID lease, fixed supervisor generation/image/command line, nonce, native lease retention, job containment/deadlines, ZIP preflight, actual NSIS extracted payload comparison, packaged backend/runtime/raw protected JSON and three-artifact hashing were traced. Release flow binds product/source ancestry, report pins, exact manifest acceptance and post-upload remote digests before keep-four deletion. No rebuild-after-acceptance fallback occurs. No private tests, live app/data/source libraries/Z:/Y:, credential acquisition, network publication, process termination, Git mutation or installer execution performed.

## Nine dimensions

1. Security — **Fail**: E1 bypasses retained external executable identity; explicit bootstrap trust limits remain documented.
2. Correctness & Logic — **Concerns**: E2 rejects authentic release; final candidate/CAS workflow incomplete.
3. Crash / Stability Safety — **Pass**: suspended child enters native job before release; finite owned deadlines and unknown-output preservation inspected.
4. Performance — **Pass**: streamed archive/hash operations and bounded ZIP staging; no build duration claim.
5. State & Data Safety — **Concerns**: C4 source route repaired, actual closure proof pending corrected dependency; future archival identity/ADS checks unaccepted.
6. Input Handling — **Pass**: ordinary native ancestry, one-link files, ZIP traversal/duplicate/special member/size refusal and exact argument arrays inspected.
7. Maintainability — **Pass**: shared guard and pure release contracts separate authorization from orchestration.
8. Doc/Code Drift — **Concerns**: frozen source omits a required dependency despite supervisor-probe claims; historical evidence cannot certify dirty helper.
9. Build & Release Hygiene — **Concerns**: E2/E3 prevent complete pinned release/build proof; full candidate/artifact QA and final review remain outstanding.

Canonical severity/safety floor: Team/Docs/ProcessRules.md § Severity definitions. Scoped open counts: Critical 1, Major 2, Minor 0. Earlier M1 C1–C3 are outside this early guard-only correction and retain their original blocking verdict until separately reviewed.

**Verdict:** RELEASE BLOCKED

Must fix E1 before enabling release; fix E2/E3 and obtain exact new-pin owned evidence. This does not supersede M1 history or constitute full v0.16 installer acceptance.
