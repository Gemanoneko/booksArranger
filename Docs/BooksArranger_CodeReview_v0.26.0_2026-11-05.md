# Code Review — Books Arranger v0.26.0

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-11-05
Tool: Books Arranger (Electron desktop with Python backend)
Release: v0.26.0
Commit range: 90f0368ba7631659a3caafc2fa6125e9075ccf2a..d6753c69ae01468693d8c77964893b1e259c9190
Files changed: 563 files, +253282 / -332 lines, including retained documentation/evidence
Product/test/release scope: 44 files, +2350 / -312 lines
Stand-down dimensions: none
Status: source and guarded build bound; independent full/native QA pending
```

Release source commit: d6753c69ae01468693d8c77964893b1e259c9190

## Summary

This accumulated review starts at the exact source certified by the [0.25.0 review](BooksArranger_CodeReview_v0.25.0_2026-11-05.md). It covers book-local durable Save/Approve decisions, their transaction consumers and renderer reconciliation, typed curated Tolkien evidence, per-book restaging holds, truthful processing status, four editable Universe suggestions, version/build-input preparation, and the final server-startup ownership correction. The earlier bounded reviews were reconciled to the pushed source; they are evidence for this accumulated review, not separate release verdicts.

The source and exact guarded package review below are complete. The fresh canonical full-entry context and one-use outer operator were reviewed before execution. Independent full/native QA and a fresh actual native plan remain pending; a full-check execution clearance is not a test result or packaged/native acceptance. Previous 0.25.0 artifact, full-check and native approval identities are not inherited.

## Rubric

### 1. Security

- Pass. New mutations use authenticated loopback JSON routes, server-derived effect domains and catalog identities; no new shell execution, renderer Node access, remote-content authority, arbitrary filesystem disposal, or credential handling is introduced. Existing Electron context isolation, sandbox and disabled Node integration remain unchanged.

### 2. Correctness & Logic

- Concerns: **M2 [Major, unchanged carried advisory] — `public_research.py:507`: a known provider cooldown can be lost to a waiting dispatcher if persistence fails.** The successful-persistence dispatch race was fixed previously; the failed write still releases the family lock without a retained in-memory hold. Preserve a fail-closed family hold on that error path and cover it next cycle. This accumulated diff does not change that path, and no Critical or safety-floor implication is identified.
- Durable intent captures request ID, exact payload hash, predecessor and source/revision binding before worker locks. Semantic step hashes, compatible-generation fences and committed revision receipts prevent changed-input replay or an unrelated revision from silently fulfilling the request. Captured Approve arguments are checked before names, rules or job set-aside effects.

### 3. Crash / Stability Safety

- Pass. The application owner survives bounded catalog errors, exposes application failure and rereads durable state; unknown consumer failures retain a review hold. Runtime startup is the final MergeService constructor operation. BrowserServer closes an assigned service on synchronous startup failure before closing its socket, and propagates closure failure.

### 4. Performance

- Pass. Acceptance uses a short bounded SQLite transaction without operation/review/group/queue locks; later application preserves existing lock order. Per-book transient waits do not hold unrelated decisions behind worker locks. Payload, effect and unfinished-decision limits bound acceptance; no test or work deadline is increased.

### 5. State & Data Safety

- Pass. Names, review/context/evidence, tracks and final enqueue mutations share their respective request receipts' transactions. Final enqueue, approval context and the optional explicit author rule commit together. Completed payload pruning preserves compact reconciliation receipts, accepted name evidence and job/publication history. Existing source hashing, publication, recovery, native identity and destructive-cleanup guards remain required.

### 6. Input Handling

- Pass. Six durable actions have bounded, action-specific JSON validation and exact response/hash checks. Current catalog source identity is checked again before application. Renderer acknowledgment and restoration guards include ID/path/revision/fingerprint/size/modified; newer edits remain local. Curated evidence has its own allowlisted decision/source/work/field contract; generic public/manual HTTPS, retrieval-time, field and reviewer checks remain unchanged.

### 7. Maintainability

- Pass. The ledger, semantic effects, route contract and application owner have separate modules; existing mutation transactions carry the receipts. Review regressions exercise actual constructors/HTTP/SQLite consumers rather than substituting a final outer applied flag or weakening source validation.

### 8. Doc/Code Drift

- Pass. Changelog/version and the accepted durable-decision/Universe behavior agree. Historical wrong-direction patch exports are preserved with an explicit erratum and corrected committed-blob patches; original reviewed source hashes remain authoritative. Historical frontend Handler proof is explicitly distinguished from final semantic frontend QA.

### 9. Build & Release Hygiene

- Pass for the exact source/package bound below. Package and both lockfile root versions are 0.26.0. Dependencies are unchanged; `scripts/build-inputs.json` changes only the actual lockfile SHA, retaining all 2,301 other seed entries/tool pins. No runner, native adapter, ownership helper, desktop security configuration or publication implementation changes in this source range. Fresh full-entry inputs were independently checked before their one permitted invocation. Full/native QA evidence remains separate from this construction verdict.

## Findings closed in this cycle

- Consumer C1: step receipts now hash semantic mutation values, validate accepted user payloads, and require exact accepted/compatible receipted revision advancement. Direct A-versus-B, changed replay, unrelated revision, rollback and partial restart cases cover the correction.
- Runtime ownership/liveness: catalog enumeration or secondary hold-write errors no longer silently kill the sole owner. Cancellation before MergeService construction completes creates no owner. The final BrowserServer correction closes the successfully assigned service when background startup raises; its socket closes in a `finally`, the service reference is cleared only after successful close, and failure is not converted to success.
- UI-M1: delayed acknowledgments and owner restoration cannot clear/replace drafts for a changed source generation. Both restoration success and failure callbacks use the complete identity; file size/mtime changes invalidate the lookup.
- UI-M2: an explicit retry of a terminal `needs_review` decision gets a fresh current request; only accepted/applying owners are reused. Ever-uncertain requests retain their original ID and immutable payload across transport errors/reload, including 403 and later 404-to-422 sequences.
- Approval ordering: an explicitly overlapping successor no longer waits for a superseded owner that cannot become applied; disjoint predecessor effects remain required. Older Approve names can complete only their retained names projection without replaying the superseded approval. The original checked track choice is receipted before this request's own review writes, preventing self-write reinterpretation on restart.

## Evidence and limits

Read-only source, evidence and hash inspection was performed; Senua ran no tests, packaged app, native phase, live library/Z: access, focus action, build or Git mutation. The following retained results were inspected, not rerun:

| Scope | Pinned evidence | Result and review boundary |
|---|---|---|
| Restaging and status | `resume-hold_2026-11-05/core` summary `db72bcca4d56db3ec6d5f3d7dcd787934551084629e77bc1b10c7d980f35526c`; status summary `5cf45e274275f7966947f77986af939f60bfa6f9bba451f239c99c34cb797bad` | All 16/19 listed evidence hashes match; 31 lifecycle and 26 progress/status Python cases pass with complete/native-zero receipts, plus affected DOM proof. A closed, checked restaging hold retains the exact book/attempt/source bytes and allows three independent jobs; thrown unknown ownership failure still globally stops. No codec proof is inferred from the continuation fixture. |
| Curated Tolkien admission | `approve-retrieved_2026-11-05` summary `0beb853828a10b99189ebabfbdcc4701b94d4f9e932404ac1b54688f2864bb77` | Five source hashes and 74 focused cases checked. Actual three-volume and legacy approval failures are reproduced before correction; typed decision provenance and malformed/private-admission negatives pass afterward. Changed external helper input fails closed; production callers construct fresh or same-binding results. |
| Names backend | `durable-decisions_2026-11-05/names-backend-stage-r3` summary `b7f6b910b0bb05efd0d7f4e1fb4d329d8db7a0f38be92ce3af851e14f7123d10` | Seven source and 28 evidence hashes match; 40 affected cases pass. Real HTTP acceptance under all four worker locks, restart/reconcile, atomic rollback/no-op, token/action refusal and constructor cancellation are covered. |
| Transaction consumers | `consumer-transactions-stage-r2` summary `dfa2d146257b3485e9305511ac80728f8d8a3d0f0ff9da5520288c0bbc2f8ed4` | Six source/24 evidence hashes match; complete 35-case and final 21-case receipts pass/native-zero. Direct changed-value/revision negatives and actual mutation rollback/replay assertions were read. |
| Backend wiring | `approval-wiring-stage` summary `62626631b6aa2fe00067fade6deaaf482f4347e00b17213ed5192c13d4d8c24a` | Six source/18 evidence hashes match; 54 affected methods pass/native-zero. Six real Handler actions accept under worker locks; two interrupted approvals reopen and produce one pending job without another press. Native media checks here use private fixtures and queue pending work; this is not packaged native QA. |
| Final renderer | `durable-decisions-ui_2026-11-05/restoration-final` summary `72cbd13ef5579773b297faf33ee7fd36c6a7ef603200fef73dc1a1202110bcf5` | All 18 source/test pins match. Final app SHA256 `f2f2c279a91de04d40c78fc01e5172559aa389e92faaa01804808168cbf7b8eb`; index `ac82a8174b36e85c213de4b8eb81f44f6c32711ad34042feb248dee0f1b3ddb3`. Exact failing predecessor and final 32-script complete/native-zero proof were inspected. The earlier `f81a3171…` real Handler bridge is historical and does not certify final semantic guards. |
| Universe/version/build pin | `v0.26.0_2026-11-05/universe-options` summary `bc4e5a2bf10a240ba712ab30b21713028da35496badec2d2a9ee1e78ce7cf26e`; build-pin summary `c5287fc08698ed152bd264d3e31708d37771bfa7e17122e6e01104beafcd77e7` | Three source LF/12 evidence hashes match. Eight Store cases and inline DOM pass; 2,001 learned values plus a saved custom value prove the four exact options do not displace previously offered learned values or mutate rows. Lock SHA256 `4793ceb09472d3381afc1acec949e4f9506cb31b311cbab4babdcceabafadd18` matches the build pin; parsed graph differs only in two root versions. |
| Final startup owner | `v0.26.0_2026-11-05/startup-owner` summary `eb3c9a5dcffbd8e964ec9f62a3ce48436af8ca28b8fd7bca2ddee3297dad52f9`; patch `81515b0a9df5ca8537b4a1cf9058cabf42016a21fbab79cf6bbea07a15a0c89a` | Two source hashes/all nine listed proof hashes match; real orphan-owner RED becomes 3/3 construction GREEN and 17/17 startup/writer-contention PASS/native-zero. Inventory `07fc0537251ba9eb4ada4fea6c2ac77bcf457282a5357103290f9917d5f5476e` records 30 constructors in 18 test files and production factory/abort/quit/unload closure dispositions. |

The patch-only erratum SHA256 `cfd111d0bba21443556236697ec7dfa31d0de479b3255035ee43d79bec0d0533` explains the stale implementation index that exported deletion hunks for existing untracked modules. Thirteen prior integrated stage blobs were independently compared with their original frozen LF manifests; all match. Corrected Names patch `cb6be8b504d28169d806115cdc98121814c049e48616552629b30a684f548371` and consumer patch `eb6174395fc8884b41f3ab850b66fc4abe8a674792cfe0bbc462e64c52d59ec6` preserve the reviewed source rather than silently rewriting evidence. Final main source was additionally reconciled to the latest applicable consumer/Universe/startup/renderer manifests; no drift was found.

## Artifact and execution binding

```text
Release worktree: C:/Antigravity Projects/Worktrees/Books Arranger/0260-release-20261105-r1
Build ID: 7e1ce2b4-e87b-43c5-b2c1-cc5cd798c1e9
Product digest: 6ea741997a1f08b8e96696dfb5066fc2bcc15bb01902ff6ed92e8063780882e0
Release artifact manifest SHA256: 137258122f81fe9c365bbc11a7d5265c9b22354d46d6f0034b12a6baf84e125b
Runtime pointer SHA256: 04bcb999b14343f36f9e8932cb6b0d32253feb7270c4de7d15cc5019a32d28d0
Payload manifest SHA256: 32987ab61c466eae0eab7e010bfa98c5969602dce6c9c60ea66bd04748d97043
Installer: Books-Arranger-Setup-0.26.0.exe
Installer size: 174793043 bytes
Installer SHA256: d93c7dcb0b450879e6912155acc2d89892b88f1ef340c80ad989aabebdedfb22
Blockmap size: 182221 bytes
Blockmap SHA256: ee3db98bbe9b8a90e5f9d748b2a0a2f1e5d837c1fb7156ef70d2cc5706163971
latest.yml size: 360 bytes
latest.yml SHA256: eb720f8ed0968379e51a5ad591a2ea9245206515b9de01f5dd7df9fe7d5ba08b
```

The guarded build completed once in 75.007 seconds with exit 0, complete output, normal closure, native membership complete/zero, no force and no timeout. Actual pack-owned receipt SHA256 is `d16a9ab52bcb212437cb21e30c30ae1b44dd4185d7749faf980ee741cf770b1d`. The guarded installer-equivalent extraction verification passed; no installed or visible app execution is inferred. Independent read-only verification reproduced the canonical Git product digest, hashed all 332 payload files and all three release assets, and compared 105 intended backend/frontend source files plus the shell entry/preload/icon and package version. All five new root modules are packaged. The only root Python omissions are the existing explicit build exclusions `app.py` and `install_app_entries.py`. Backend/shell versions are both 0.26.0; no unexplained payload/source mismatch was found.

One guarded build execution was cleared for build plan SHA256 `b26653fb19aad4854c6722c05e94e33227967a9cc122f6d74ad2336dbae8cf08` and operator SHA256 `4463ee1b6a21d7bddcab52ae956b305ca982ced85e4dded982068c6e9de7885e` under main `scratch/0260-release-20261105`. All 2,325 tracked-source and 2,033 actual tool/config/input hashes were independently checked, including exact 87-file ownership-module and 1,927-file npm tree memberships and both empty owned npm configs. The revised operator verifies those inputs before importing the owned helper and after closure. The exact route remains installed Node/npm `run pack`, the committed native build guard and canonical outer `runOwned`, each with its existing 600000 ms bound. This is execution-plan clearance only; a result, duplicate retry, full QA, packaged/native app check or publication is not inferred from it.

### Full-check execution contract

One canonical non-app full invocation was cleared for `C:/Antigravity Projects/q26/context/context.json`, SHA256 `c9a979022a33967c5e29535c3b242f0df5af7a72bd249277bb07f6e769853365`, and one-use `q26/operator.mjs`, SHA256 `cd9384d713b1bf8adee3408079082838bf35510d1bd8cb2968e9faf68fd49716`. The context is the exact reviewed schema 3 / 900000 ms profile. The outer 930000 ms is exit/EOF collection only, with exclusive invocation creation before launch; it does not extend work. The previously proposed operator's old fixture literal was corrected before execution; reversing that sole substitution reproduces its prior hash exactly.

Independent checks matched complete manifests and membership for 2,325 source files, two harness files, 7,589 dependencies, 92 ownership files, 47 bundled-media files, one private MP3 fixture, 1,936 Node-installation files, 9,625 Git files and 898 PowerShell files, as well as all five checker/helper hashes. The source snapshot equals the clean prepared checkout and tracked membership. The single declared check is the byte-audited `node scripts/check-desktop.mjs`; its complete canonical graph keeps the 18 declared Node entries and sorted DOM/Python work, while PA-1 remains a separate mandatory native phase. No unsupported declaration is treated as n/a. The private fixture SHA256 is `3fd8b5de3da373c69eff6a0eafe42ea313c15b04952523c3c3b2515505958288`, and its actual operator path agrees with the pinned graph. The 34-file preparation freeze SHA256 `d91b6e38f88b4ab811969456b5cb79486ae342b356615a07b94b7ba7921b538c` also matches.

The [QA plan](BooksArranger_QAPlan_v0.26.0_2026-11-05.md) explicitly records the authorized one-full-invocation exception: Ender's handoff is focused readiness, not an invented sender full receipt; Futaba owns the actual full invocation/result. No repeat on this candidate is implied. A full result and a fresh actual native operator/authority/plan acceptance remain pending and cannot be inferred from these input checks.

## Verdict

- Total Critical: 0 open
- Total Major: 1 open, unchanged carried advisory M2
- Total Minor: 0 open
- Safety floor: intact in the reviewed source range

**Verdict:** RELEASE CLEAR

Source and the exact guarded package are clear. Independent full/native QA and the fresh actual native-plan review remain pending; execution-plan clearance is not publication acceptance.
