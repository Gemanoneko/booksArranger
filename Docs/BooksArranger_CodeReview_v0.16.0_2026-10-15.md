# Code Review — Books Arranger v0.16.0

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-10-15
Tool: Books Arranger
Release: v0.16.0
Status: SOURCE REVIEW COMPLETE; integrated04 passed, installer binding pending
Commit range: 95febcdd4f4de4ffb59a3507053c4eb86f53936a..841d637b1024f44f3ce712a9b9f16c29058d4c18
Accumulated committed diff: 105 files, +12573 / -206
Stand-down dimensions: none
Release source commit: 841d637b1024f44f3ce712a9b9f16c29058d4c18
Release product tree SHA256: d7b85fe605d4539949adc44e1ce3826096ab77ad27c3cf9535202683de7d92d7
Release artifact manifest SHA256: pending new verified installer
```

This is the accumulated release review, including the earlier Electron M1/M2 reviews and their corrections, rather than a review of only today's last patch. This preliminary document deliberately has no machine-readable release verdict. It must be completed against the final committed source and real validation evidence before it is consumed as release clearance.

## Summary

Reviewed the Electron shell and native engine ownership, existing-catalog startup, normal Quit and update shutdown, working-file lifecycle and source retirement, retry admission, source-preserving M4B metadata repair, and the complete native-owned packaging/publication graph. The review followed the Brief, standing rules, desktop UX record, build-guard record and accumulated release diff. Shared QuickLaunch/hooks/settings, unrelated chats, live app controls and product implementation are outside this reviewer's ownership.

## Exact working-source inventory

Before final source save the tracked dirty paths were `audio_pipeline.py`, `scripts/check-desktop.mjs`, and `tests/test_web.py`. Untracked final product/test paths were `m4b_preservation.py`, `tests/m4b_native_preservation_fixture.py`, `tests/test_m4b_dispatch.py`, and `tests/test_m4b_preservation.py`; the M4B evidence Doc was also untracked. Independently rechecked the final commit: `0c67862e0bf0a15ff7b7d0506b25f45f3b3adb66..f56739b0911da133cef759fbfa71d6110bbbf941` contains exactly those eight paths, matching the reviewed source inventory. At that point only this documentation-only report was dirty. All final source is now included in the accumulated committed range above.

| Path | Actual SHA256 at review |
|---|---|
| audio_pipeline.py | c8d16b61b1ed3ecb7f522ace082a5dda04603d96ef2168bd24f6f37a37e4a09c |
| m4b_preservation.py | d68a37bbfd851a7fa08f9d23faad75584daa3252ac34e8549452c044c7c09ff2 |
| scripts/check-desktop.mjs | 3cd84c8ecb78991419ed29c8139f75a505ebce5be18fb4af73446d0eeb8f4c8a |
| tests/test_web.py | b4e310eac6a8d472a80b6a97c38320cbe8252c111cc605661afe97c3c85979ae |
| tests/test_m4b_preservation.py | ba06289d4d1eee9444ed93899b0730ef7413b472f356144b8d897e8cd7b87970 |
| tests/test_m4b_dispatch.py | b2a42d1eeab0499f6888eb6aa2cea03b0d1bf89f7068632e5e2ba74046499b46 |
| tests/m4b_native_preservation_fixture.py | a850398f28d9e2880e8b418db0691f5bde6b17356db5430964c368790a0e30b8 |

Seven subsequently reviewed source/test changes are now committed at `841d637b1024f44f3ce712a9b9f16c29058d4c18`. Independently checked that `0887b4e0bca783431e667fc97c5a246110e1c727..841d637b1024f44f3ce712a9b9f16c29058d4c18` contains exactly these seven paths and no extra product change; only independently owned documentation remained dirty afterward. Sully reports the existing product-tree function's digest above. The new marker module and source-cleanup integration were reviewed separately; the remaining changes correct the five full03 regressions and enroll the marker fixtures in the ordinary checker. Actual full04 copies contain these exact bytes:

| Path | Actual final SHA256 |
|---|---|
| scripts/check-desktop.mjs | eafd05a1d681cdd9172c452bd7ff51c786efdc64bf2cb5fef4b10d7a071bd5ac |
| source_cleanup.py | 7fe68f5924bd8e7c8c636f20e1fd4bfdf7999c572a5e9b52be9911192ef7968e |
| tests/test_automatic_media_policy.py | c1961acf4b5b2dfee32388479a80033493b8c47a39c8d2f2c9baa4a8949f6cc8 |
| tests/test_standing_admission.py | 8b191a585766d29606b7215639f7e6e674c158d40966dae7d643aefb7c2e7df0 |
| tests/test_web.py | d0f010231df5c69ac51620b10a41252e20f234833cf69fb02e31852df810bb1c |
| tests/test_zone_identifier.py | dd582306f6a91b65158de096b8a757f7d12769f1e322931eb0f419986fc09d8b |
| zone_identifier.py | a4a8086ba176cd918a65bfe2c4af128b8816ccee39342e25db76c85233369141 |

## Rubric

Severity tags and the always-blocking floor are those in `Team/Docs/ProcessRules.md`, Severity definitions.

### 1. Security

Pass. Renderer sandbox/context isolation and restricted IPC, exact native owner/runtime checks, argument-based process launches, leased Git/GH and credential handling were reviewed; no open Critical or safety-floor finding identified.

### 2. Correctness & Logic

Pass for reviewed source. AAC single-source preservation is separately dispatched; ALAC keeps the existing strict route. Unknown structural layouts are refused. Complete retained-byte reread, source-relative packet/configuration/chapter and PCM checks preserve the 139 chapter-linked MJPG track and f96 HE-AAC clock. Repair admission retains the failed parent and CAS-binds one new child to the unchanged reviewed manifest; it does not reset legacy failure rows.

### 3. Crash / Stability Safety

Pass for reviewed source. Native ownership spans engine startup and lifetime, interrupted-exit recovery distinguishes an ended generation from an unknown owner, Quit drains the current book before releasing ownership, and update failure restores shell retry state without releasing a live engine fence. The old installed app's exit cause remains unestablished.

### 4. Performance

Concerns. [Major, advisory] `working_lifecycle.py:228`: `_references` rescans relevant catalog tables during reconciliation and again before individual deletion (`:411`), so large multipart attempts multiply catalog work by disposable-file count. No new measured user-facing regression is asserted. Preserve the last-moment reference check if optimizing this path; measure representative large attempts before choosing an index/cache strategy.

The preservation route removes the old remux-plus-compatible pair and normalized-WAV path for supported single-source AAC M4Bs. It retains complete verification; this review does not claim the earlier 61–69% pre-encoding cost has been eliminated for other books.

### 5. State & Data Safety

Pass for reviewed source. New lifecycle intent precedes generated writes; only closed, identified, unreferenced generated artifacts are disposed using retained native handles and durable receipts. Publication/source-survival proofs precede retirement of published snapshots. Changed, linked, streamed, unknown or unresolved files remain held. Legacy debt blocks another copy set for that parent. The remaining 77 legacy snapshots and original diagnostic pairs are not declared disposable by this review. A Zone.Identifier-only exception is not inferred from ordinary stream enumeration.

Supplemental marker review: only a bounded, recognized literal Zone.Identifier stream may be removed after current reviewed-source native/full-hash validation and a durable receipt containing its exact bytes. Unknown streams refuse. Normal source cleanup reacquires its original deny-delete lease and repeats the existing review/fingerprint/hash/recovery checks. Actual native integration fixtures passed. Enumeration followed by disposition is not an atomic proof excluding every newly arriving stream; this exception does not claim to solve the pre-existing whole-file stream-arrival window or weaken original matching.

### 6. Input Handling

Pass. Existing-root/catalog validation, canonical paths, held ancestor boundaries, link/stream checks and conservative structural parsing were reviewed. Empty metadata is accepted only as an omitted empty tag; nonempty metadata comparisons and full-byte proof remain strict.

### 7. Maintainability

Pass. The separate preservation module and lifecycle ledger concentrate their invariants; retry admission uses the production plan/manifest contracts. Native guard and release orchestration remain substantial maintenance surfaces, with focused failure-path tests reviewed.

### 8. Doc/Code Drift

Pass for reviewed documentation scope. This report distinguishes source review, actual component/real-book evidence, integrated checks, and the still-unbuilt artifact. Historical 137-Python/29-Node declarations are not treated as executed evidence. Full04 actually ran 366 Python and 29 Node cases plus seven frontend and six syntax checks. Neither this report nor the genuine private whole-product graph claims a canonical protocol-2 handoff receipt. The user's explicit procedural waiver and narrow transport issue are recorded in the operation-review Doc. Shared Gate07 source review SHA256 `450668f459044db069aef3dda13e99d0ebdcf000b57be0168dc5ecd2b7704045` was independently read after the authorized shared-hook transition; its source acceptance is not inferred to be Books host-enforcement proof.

### 9. Build & Release Hygiene

Concerns pending actual build and independent QA. Reviewed existing `npm run pack` -> `node scripts/build-step.mjs pack` and existing direct `node scripts/release.mjs` primary publication entry, including complete source/runtime holds, 600-second native deadline, owned descendant closure, UUID staging, payload equality, fixed Git/GH, clean named pushed tag, artifact hashes and keep-four ordering. This is source/operation assessment, not a claimed package or publication run. Final source commit, exact installer manifest, Futaba behavior/identity evidence and final release binding remain outstanding.

## Actual evidence and limits

- Parent reports final native QA06: 36 cases passed, no failures/errors/skips; native PID 88140 exited 0 with zero active descendants. Header05 accepted all three retained source profiles unchanged. These are component scopes, not whole-product or publication claims.
- Independently read the three bundled-runtime real-book native receipts and full proof stdout. All three exited 0, zero active descendants, owned cleanup finalizer completed; one test and 13 codec children per graph. Runtime was the release bundle `n8.1.3-9-g29e619e767`, with all 11 runtime files and archive pinned.
- 07d: 17 chapters; mono PCM 1,697,126,336 frames SHA256 `8e3015d2888a481fb4a254d7dae82825813e4de7d94b1cb9938742381ffe33a4`; native PID 101372, 82.697 seconds.
- 139: 8 chapters; stereo PCM 1,070,323,648 frames SHA256 `0b5dc7c17e628d9da5ec9263dc91b3405ad64287ae87c5657ade71223794886d`; native PID 77084, 75.461 seconds. All original tracks, including chapter-linked MJPG, retained.
- f96: 43 chapters; HE-AAC stereo PCM 1,095,806,976 frames SHA256 `21733f23e62a4641380eed7e5708ff3aed570b45fb872feeb7b32692787a5df7`; native PID 8620, 69.066 seconds. Original decoder/container clock retained.
- All three source native facts and full hashes were unchanged; complete retained bytes/configuration/packets and decoded PCM matched. These graphs wrote only private `checked.m4b` candidates; they did not publish outputs, retry real jobs or retire originals.
- Integrated01 failed before any product test because runtime membership used inconsistent string ordering; exact membership and file hashes were unchanged. Fresh02 corrected ordering, then actually passed 29 Node cases but failed its strict TAP reader because Node26 selected the spec reporter; Python/frontend were not reached. Fresh03 explicitly selects TAP without weakening the zero-fail/skip/cancel assertions. Its actual result is pending.
- Integrated03 actual result supersedes that pending status: Node 29 passed; Python ran 354 cases in 414.556 seconds with one failure and four errors; frontend did not run. Native PID 57416 exited 1, zero active descendants, 430.271 seconds. Packaging was stopped. Reported issues are two stale packet-proof schema assertions, the old gap-rejection expectation now routed through exact preservation, a private-TEMP fixture path exceeding its bound, and a native catalog-lock sharing exception expectation. No passed whole-product claim is made.
- Semantic review of the gap failure: preserving a source-existing gap is allowed only by the separate exact-byte branch, which compares original/output presentation, packet/configuration, PCM and chapters. The ordinary remux guard `_copy_presentation` remains strict. A valid test correction must prove a real nonzero source gap survives exactly, retain strict ordinary-route rejection on that gap, and reject independently contradictory output presentation. No global guard relaxation or timing-tolerance increase is accepted.
- Focused regression actually passed all six methods, seven frontend scripts and six syntax checks: native PID 100532 exited 0, zero active descendants, 66.290 seconds. This included the five corrected failures and the new contradictory-presentation negative. Production search confirmed no publication/history/completion/cleanup consumer requires the removed flat `audio_packet_sha256` key; existing common validation fields remain supplied.
- Zone01 failed 11 tests with two failures and one error; failed evidence remains preserved. Fresh Zone02 passed all 11 native fixtures, zero skips: PID 87492 exited 0, zero active descendants, 17.829 seconds. Printed native facts proved marker creation changed only the private fixture's modification time; restoring only its own timestamp modeled a marker already present at approval and preserved the complete production `_match` checks. In-place changed-byte mutation explicitly retained the marker before the negative hash check. These were fixture-only corrections.
- Independently read and hashed full04 native receipt `d1daae6c68201dc89bb69a9a9beace7f510721494c273082358d774f6fbae498`: actual 366 Python cases in 455.668 seconds, 29 Node cases, seven frontend scripts and six syntax checks all passed; no skips/errors/failures. Native PID 102796 exited 0, zero active descendants, 474.373 seconds, owned finalizer returned. The exact 600-second graph used immutable final inputs and bundled runtimes. This supersedes the earlier failed suite, without erasing those failures or claiming all legacy repository tests/canonical handoff execution.
- The first legacy snapshot disposal batch was separately reviewed and executed with fresh held original/cache native identities, complete hashes, unchanged failed job/context/marker and current reference closure. Independently hashed receipt `6e88a387ce088d8e4912cd8b0657846b87cd07a3387af25568d84286325a67a6` records 28 removed entries, no refusal reasons and `in_progress:false`; parent reports 10,688,638,960 bytes, with originals unchanged. Later batches remain separately sequenced and are not declared completed here.
- Original diagnostic pairs, failed graph evidence and unique recovery records remain preserved. The separately reviewed fixed-hash helper `459928b08635af1bbb1f332f39e0ee07d5bb3cc993fe1875cf105ec7e750000c` was executed once by the parent: exit 0, three new private proof candidates removed, 923,016,616 bytes, final phase `complete_after_native_release`. It accessed no original/source/catalog/app. This is additional QA-generated space, separate from the earlier 59,306,533,081-byte cleanup of user working files.

## Preliminary finding rollup

- Open Critical: 0 identified in reviewed source.
- Open Major: 1 advisory performance finding.
- Open Minor: 0.
- Always-blocking floor: no violation identified in reviewed source.

Final committed source comparison and actual integrated validation are complete. Zero open Critical findings or safety-floor violations were identified in this accumulated source review. Final machine-readable release verdict awaits the actual installer manifest binding; this source-complete report is not an artifact acceptance or a Critical-based release rejection. Docs-only acceptance descendants are permitted by the reviewed source ancestry/product-tree contract and do not require rebuilding unchanged product bytes.
