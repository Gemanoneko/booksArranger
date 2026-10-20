# Books Arranger — release preparation sequence

2026-10-20, Sully. Procedural preparation only; no execution, QA or release clearance. Intended candidate is v0.20.0, currently uncommitted application changes over released v0.19.0. Native QA infrastructure remains unfinished; existing source/component reviews do not replace final acceptance.

## Canonical route and ordering gap

The Brief's desktop release contract and package.json name one local route: guarded npm run pack prepares an installer; guarded npm run release publishes the already-built, QA/review-accepted artifacts without rebuilding. There is no .github/workflows directory in this checkout. This is not a CI release.

The generic release-pipeline skill requires clean state, an already bumped version and version-named QA in Step 1, before its Step 2 describes bumping/committing. Treat candidate preparation and final release admission as separate phases: atomic versioned source checkpoint first, exact QA afterward, strict release preconditions before tagging. Never run a known-failing gate as approval, skip QA, or bump after accepted QA. ProcessRules remains authoritative; this document records the concrete tool sequence rather than changing the shared skill.

## Required sequence

1. Finish and freeze QA infrastructure. Independently review its final source and execution context. Unfinished QA files remain excluded from a candidate; no final clean candidate can coexist with unrelated dirty infrastructure in the same checkout.
2. Sully prepares package.json version 0.20.0, regenerates package-lock.json with npm install --package-lock-only, and updates CHANGELOG.md. Any lockfile dependency/integrity/membership change is STOP-and-report. Commit the complete milestone source, tests, version, lockfile and changelog atomically using exact file paths; push the branch immediately. This is a candidate checkpoint, without a tag or release claim.
3. Pin clean source HEAD H. Ender and Futaba run identical reviewed protocol-2 argv sequentially, binding v0.20.0, H and complete source/harness/runtime/checker manifests. No version bump follows these receipts. Any product/test/checker/runtime change requires renewed affected evidence and a new exact candidate identity.
4. Senua completes full release review of the accumulated product changes. Earlier component/source-only findings are inputs, not RELEASE CLEAR for the final candidate.
5. Build once with supported guarded npm run pack. Futaba tests the actual packaged artifact, displayed version 0.20.0, tray-close and explicit full-Quit behavior, and required behavior checks without taking focus. Senua and Futaba accept the same dist/release-artifacts.json SHA256 and source/product identity. No rebuild after acceptance.
6. Commit/push acceptance prose only: Docs/BooksArranger_QA_v0.20.0_<date>.md, Docs/BooksArranger_CodeReview_v0.20.0_<date>.md and Docs/BooksArranger_ReleaseAcceptance_v0.20.0.json. Publisher productTree excludes Docs/ and CHANGELOG.md, allowing these descendant prose commits while binding every other tracked product/config/test file. Reports require exactly one appropriate GO/RELEASE CLEAR verdict, Release source commit and Release artifact manifest SHA256 line; acceptance index must match the publisher schema.
7. With a clean checkout and no existing local/remote v0.20.0, run strict release preconditions before creating the tag. No --skip-qa. Separately verify real dual verdicts, exact receipts and manifest bindings: the generic script only checks a QA filename. Check both lockfile version fields and remote freshness. A failed unskipped precondition stops release.
8. Create/push only v0.20.0, then invoke guarded npm run release. The publisher requires that pushed tag at HEAD, verifies exact source/artifacts/acceptance, authenticates via gh CLI and publishes without rebuilding. Verify remote asset hashes, keep-four retention and local tag parity. Use the supported reviewed owned deadline/closure route; a missing route blocks execution.

If QA finds fixes, repeat candidate preparation and affected review/receipts on corrected v0.20.0 before tagging. Do not claim release while evidence is incomplete. Nothing here authorizes an invocation, focus-taking QA, live migration, settings activation or iTunes action.

## Ownership and final scope

Ender owns application/backend/frontend changes, feature fixtures and final implementation docs. The QA infrastructure owner separately owns scripts/check-desktop.mjs, provision/context/guardian scripts, scripts/qa-native files and QA-native/runtime tests. Their current source and execution admission are tracked in BooksArranger_QANativeLauncher_Review_2026-10-20.md and BooksArranger_QANativeLauncher_DiagnosticLoss_Review_2026-10-20.md. Preserve bound review/input identities while their operations are active.

Sully owns package version, lockfile sync, changelog, exact Git commits/pushes/tags and release commands. Jane assembles the exact owner-approved final file list. Before any source checkpoint, capture a fresh git status --porcelain --untracked-files=all and reconcile every path with its owner; the earlier read-only path inventory is a starting point, never staging authority. Never stage directories/add-all, sweep parallel work, stash/reset/rewrite history, or commit unfinished QA source merely to make the tree appear clean. Docs-only checkpoints remain separate from code milestone versioning.

Read-only basis: .agents/skills/release-pipeline/SKILL.md and its check_release_preconditions.mjs; desktop CLAUDE.md, package.json, Brief desktop build/release contract; scripts/release.mjs, release-flow.mjs and release-contract.mjs; qa-handoff protocol-2 requirements. No gate, build, runtime probe or release was executed to prepare this sequence.
