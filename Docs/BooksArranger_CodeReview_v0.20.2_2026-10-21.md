# Code Review — Books Arranger v0.20.2

## Header

```
Reviewer: Senua (Code Reviewer), inherited supported review tier
Date: 2026-10-21
Tool: Books Arranger (Electron / Python)
Release: v0.20.2
Commit range: dd05b66d5a5616eddbb531749d3133cf1db7e7f5..2309d8f2d71a8570e329c1010afc6dfa6ce633ba
Release source commit: 2309d8f2d71a8570e329c1010afc6dfa6ce633ba
Release artifact manifest SHA256: 522a9de2888b4d37628eaa20ba2e7cd12609b3126dca77f068031aa732157cc4
Reviewed source: C:/Antigravity Projects/Worktrees/Books Arranger/qa-0.20.0
Files changed: 14 files, +1054 / -22
Stand-down dimensions: none
```

This report is written in the original desktop Docs directory, outside the clean QA checkout. Source acceptance does not replace the required new canonical sender/receiver checks or actual packaged QA. No previous artifact or GO certifies this release.

## Summary

Reviewed the entire delta from released v0.20.1: six production modules, five test modules, matching package/lock version fields and changelog. The user requested normal Windows moves without copying. A separate journaled same-volume rename strategy now uses a retained source DELETE handle, exact native identity and no-overwrite Windows rename API; it never falls back to copying. Recovery matches durable intent to the exact intended native file and both protected parent chains. Explicit cleanup of a previously verified retained duplicate preserves the committed Sorted copy while deleting only its separately verified old output. Original conversion receipts and the existing copy protocol remain intact.

## Rubric

### 1. Security

- Status: Pass. Absolute ordinary paths, nonreparse ancestry, single-link files, native-volume checks and no-replace API remain mandatory; no shell fallback, renderer capability or credential surface was added.

### 2. Correctness & Logic

- Status: Pass. Frozen operation strategy/action/initial generation and reviewed plan digest bind the separate rename graph. Copy transitions cannot consume native-move intent; existing copy STAGES retain their meaning. Resolver/history consumers revalidate the selected protocol before using effective locations.

### 3. Crash / Stability Safety

- Status: Pass. Intent commits before rename/disposition. Restart admits source-present/destination-absent or the exact same native file at the intended destination with full hash and pinned ancestry; ambiguous or same-byte replacement files refuse. Inventory and MergeService fence unfinished native moves before producer/recovery construction.

### 4. Performance

- Status: Pass. Rename performs no byte copying. Exact job/path/hash verification cache is reused only when OS and held-native identity/size/mtime agree; otherwise a full held hash is required. Restart and explicit duplicate cleanup full-hash their protected files.

### 5. State & Data Safety

- Status: Pass. Catalog effective-location commit and consumer invalidation share the durable transaction. Source native protection spans rename through complete readback. Duplicate cleanup requires the prior retained-copy completion, original copy seal, different native files and full hashes of both; the verified destination stays protected throughout exact old-handle deletion. No unrelated source or recovery file is modified.

### 6. Input Handling

- Status: Pass. Explicit strategy, action, initial generation, content authority, ordinary path, native identity and ancestry are checked. Destination collisions and cross-volume/unsupported API failures preserve source without fallback; accepted-rename postcondition failures preserve intent rather than recreating the old name.

### 7. Maintainability

- Status: Pass. Native primitive, move worker and ledger branch are explicit; copy validators remain separate. Destination write sharing is opt-in for the exact leaf only and cannot combine with the old writable-publication capability.

### 8. Doc/Code Drift

- Status: Pass. Changelog describes journaled no-copy Windows moves and startup fencing. Native proof explicitly excludes a server power-loss guarantee; local and simulated NAS tests do not claim actual NAS capability.

### 9. Build & Release Hygiene

- Status: Pass. All eleven frozen source/test pins match the reviewed snapshot; remaining commit changes are package/lock 0.20.2 and changelog only. Dependencies and Electron configuration are unchanged. New canonical and artifact evidence remain separate required gates.

## Evidence

- Exact eleven-file freeze manifest native-move-v0202-source-freeze-2.json SHA256 a62ee333accf1bb22a86b42ec7711baa8afbe8151f3fec73dad43a8b17a83475 was independently hashed; every listed file matched its pin.
- Whole focused receipt move-all-focused-owned-result-3.json SHA256 58b18db601e92ef03569ba211a79dbf2d6f2d5abe58e5d6f91668a0eed8fa472 independently read/hashed: 104 tests, zero failures/errors/skips, exit 0, complete output and native owner closed/complete/zero with 383 retained handles signaled, no force/timeout/overflow/truncation.
- Native15 receipt SHA256 4299573ffd7804c4097af942c94e3ffe791e5187532914508077bad784f4c125 independently verified: real local rename, false-overwrite/collision/cross-device refusal, post-API failure recovery contract, exact-leaf sharing and parent/ancestor deletion/rename denial; simulated NAS64 identity is explicitly local-only. Source sharing remains READ only; all ordinary/default/copy and ancestor sharing guards remain unchanged.
- Private sharing matrix e60267e048f826c2e8d28a855d4d7862cee6e2778a9c7bffb3a8cfe1b1428a5e and closed-zero receipt 82739078fd41766fed3b68cbeb73f3e00cf7c2c5ed2198d837a51aa07386f2fd establish the leaf WRITE-sharing compatibility requirement while DELETE remains denied.
- Real isolated worker tests cover conversion through reviewed move, immutable job/recovery history, every durable/native crash gap, duplicate cleanup disposition gap, same-byte/different-identity rejection and configured two-source/output-root restart. Test fixes replace obsolete nonempty-recovery/indexing assumptions with actual quiescent retention state and exact owned-output exclusion; the accepted v0.20.1 packaged baseline reproduced the obsolete recovery assertion. No production retention or scanner ownership rule was relaxed.

## Verdict

- Total Critical: 0
- Total Major: 0
- Total Minor: 0

**Verdict:** RELEASE CLEAR

## Check graph coverage requirement

The committed canonical check graph explicitly discovers 1,227 Python tests (680 + 547), 57 Node tests, 16 frontend tests and 8 syntax checks. Its explicit module list omits the new 15 native rename, 8 move-worker and 2 startup-fence tests. Developer focused104 evidence covers these cases, but independent QA must run a separate exact25 supplement against the same2309d8 source with no skips and verified native closure, in addition to the unchanged canonical receiver. Counts and receipts remain separate; no1,252-canonical claim is made. Sender actualPASS was reported with final complete/closed/zero native membership; transient incomplete samples are not hidden. Independent receiver and supplement acceptance remain pending.


## Actual artifact and exact line-ending equivalence

Independently hashed/read manifest522a9de2888b4d37628eaa20ba2e7cd12609b3126dca77f068031aa732157cc4: source2309d8f2d71a8570e329c1010afc6dfa6ce633ba, build4f050b08-65c2-432a-a39b-c3ca3dab4f60, productbe5b57a02994efff13c96c40580c5b89902607a739ccf1087c144544204dcda8, shell/backend0.20.2, verified and installer_equivalent true. Final A/B commands and all frozen harness dependencies were checked; actual packaged QA verdict remains pending.

Native_io.py committed raw Git blob is LF37818B SHA0ff5967de367753aed06b6b64755707bd23b2015df2d130e4cf26aa93a10423e. Tested working and shipped payload bytes are exactly identical CRLF38330B SHA51882dd064d19d0e9b9fc5c954bcd4fe4de87173f00c26678888f8fd0ab36d3d. Independent raw-byte Git extraction proved512CRLFpairs, noCRinGit, exact working CRLF→LF equality to Git, and exact reverse Git LF→CRLF equality to working. Only that exact reversible newline conversion is admitted; no broader semantic normalization is accepted. Python source newline handling preserves this meaning, and the shipped bytes are the tested bytes. Output_rename.py retains exact tested/payload SHA d49311c52e78a553b0563d21888bd9c059e8f0afb301f0fb4a5ef06448251a72. No rebuild or source mutation was required.
