# Code Review — Books Arranger v0.16.0

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-10-15 (source review); 2026-10-16 (build-fix range and artifact binding, final)
Tool: Books Arranger
Release: v0.16.0
Status: FINAL; source, build-fix range and actual installer artifact reviewed
Commit range: 95febcdd4f4de4ffb59a3507053c4eb86f53936a..8d6272593645226af711e2eb21a2c0d731d6d3d3
Accumulated committed diff: 108 files, +12972 / -206
Build-fix sub-range: 841d637b1024f44f3ce712a9b9f16c29058d4c18..8d6272593645226af711e2eb21a2c0d731d6d3d3 (code: 5 files, +255 / -25; no app/product runtime file changed)
Stand-down dimensions: none
Release source commit: 8d6272593645226af711e2eb21a2c0d731d6d3d3
Release product tree SHA256: 3ea85ac7eb3727daf0f6e04fbcaba3d3a8b9ea8c6faf659802f10db47b0e9709
Release artifact manifest SHA256: 1a2f49cee6eaba6a3a0a7dd8d91c19a707dcaf7db01435cceb2694164d470a19
Release installer: dist/builds/46781019-c587-4ba3-9e0c-4c6161be11b4/Books-Arranger-Setup-0.16.0.exe
Release installer SHA256: b556f61062d2d48b70581ac4c76be04304f7c3c6a9b0797e185c7d276119c15e (172,929,911 bytes)
```

This is the accumulated release review, including the earlier Electron M1/M2 reviews and their corrections, rather than a review of only today's last patch. The 2026-10-15 source review (through `841d637`) is retained below unchanged in substance; the 2026-10-16 sections add the build-fix range through `8d62725` and the actual installer/manifest binding, and close the report with its machine-readable verdict.

## Build-fix range 841d637..8d62725 (2026-10-16)

Commits: `7dae809` (CHANGELOG only), `5d7f9df`, `1ba3dfa`, `1843d9e`, `8d62725`. Only build tooling changed: `scripts/build_external_tools.py` (new), `scripts/build_fs_guard.py`, `scripts/build_native.py`, `scripts/build_phase.py`, `tests/test_build_external_tools.py`. No file under `desktop/`, `web/`, root `*.py`, `package.json` or `package-lock.json` changed, so the shipped application source is the reviewed `841d637` product plus nothing.

| Path at 8d62725 | SHA256 |
|---|---|
| scripts/build_phase.py | 21981726ff4e04adf4e6136b611f6affb9f6fbbef8952ff784a1c9a10f97e5c6 |
| scripts/build_native.py | 776071e34933e5e48522ff4ae6de07d149eb0eb25ceb83d6c94689c1ef99599c |
| scripts/build_external_tools.py | 646db1af7ed1b37c412dfb706e51790016d0daf3f9e4ddeaed49683506f96b22 |
| scripts/build_fs_guard.py | 72a78b905fa6b6f5c6ffd84d60e3418a14c55c8f21776ce3867a6ab65044ed6a |
| tests/test_build_external_tools.py | 252235a1e2c4734a67c80e0be62f5e31dea9ccf084eb06661c35c195818d7df3 |

- **Git alias/DLL profile (`5d7f9df`, `1ba3dfa`).** The generic external-tool `links==1` rule is relaxed only for literal constants: wrapper `cmd/git.exe` (2 names), backend `ucrt64/bin/git.exe` (4 names) and four backend DLLs (exactly 2 names each, in two literal folders). Each requires pinned SHA256, exact native alias membership via `FindFirstFileNameW`, identical facts on every name, re-check after acquiring holds, and deny-write/delete holds on every name and folder. Other source/output/Node/Python/GH hardlink checks stay strict (`test_build_input_output_hardlink_policy_remains_strict`). Unknown versions or layouts refuse. Strengthens, not weakens, the prior wrapper-only hold.
- **Output-folder share (`1843d9e`).** `dist/builds/<uuid>` is now held READ|WRITE so electron-builder can rename `win-unpacked.tmp` inside it; DELETE sharing is still never granted and any other share value refuses. The output tree is still hashed under holds and verified after the build.
- **Job-empty grace poll (`1843d9e`).** Bounded 3-second poll for *positive* zero active processes; a query failure now raises explicitly; a survivor past 3 seconds still fails. Closure is still required before `closure_verified`.
- **Error tails (`1843d9e`).** Separate 4000-character stderr/stdout tails. The worker environment already strips `GH_TOKEN`/`GITHUB_TOKEN`/enterprise tokens (`build_native.py` env filter), so no new credential exposure.
- **Embedded-7z offset carve (`8d62725`).** The reduced `7zip-bin` 5.2.0 `7za` has no NSIS handler; it opens the installer as the embedded 7z. The new code requires a single archive section with `Type = 7z`, `Offset > 0`, `Physical Size > 0` and `Offset + Physical + Tail == held installer size`, then carves exactly `[offset, offset+physical)` from the **held** (deny-write) installer handle into a fixed name in a fresh UUID folder, checks the size and 7z signature, and requires the carved listing to equal the installer listing. Member path/link/duplicate refusal and the `build-manifest.mjs` verifier are byte-for-byte unchanged. **Payload equality is not weakened:** the verifier still requires the full sorted `{path: sha256, size}` map of the extracted NSIS payload to equal `win-unpacked` exactly (no subset, hardlinks/reparse refused), and refuses without `nsis_payload`. Note that the size-sum and listing checks are mostly self-consistency of 7za's own output; the load-bearing proofs are the held-handle carve, the signature and the unchanged full-map equality (see Minor m1).

## Artifact binding (independent, 2026-10-16)

All checks below were read-only on the artifact, with private scratch copies only; nothing was installed, launched, packed or rebuilt.

- `sha256(dist/release-artifacts.json)` = `1a2f49ce…0a19` (full value in header); equals the build's own `metadata-rotation-complete.json` manifest receipt.
- Manifest: schema `books-desktop-artifacts-v1`, version `0.16.0`, `source_head` `8d6272593645226af711e2eb21a2c0d731d6d3d3`, `build_id` `46781019-c587-4ba3-9e0c-4c6161be11b4`, `payload.verified true`, `installer_equivalent true`, 219 payload files / 581,921,453 bytes, `payload.manifest_sha256` `b60d69a7…3902` recomputed and equal.
- `product_digest` `3ea85ac7…0e9709` recomputed with the tool's own `productTree` from `git ls-tree` at `8d62725` (both the `-z` release-flow parser and the build-manifest parser): equal. The worktree is clean at `8d62725`.
- Installer, blockmap and `latest.yml` hashes and sizes equal the manifest's three artifact entries. The `latest.yml` sha512 equals the installer's actual sha512.
- Independent structural check of the installer bytes, with no 7za involved: exactly **one** 7z signature with valid start-header and next-header CRCs, at offset 171,345; physical size 172,366,751; tail 391,815. The four bytes before it are the NSIS data-block length = 172,366,751 with the compressed bit clear. NSIS therefore stores exactly these bytes as one uncompressed file. Carved SHA256 `2bd65858…1e8b` equals the build's own retained `nsis-archive/.../app-64.7z` receipt.
- Extracting that carved archive privately gives 219 files, **byte-identical** to `payload.files` (no missing/extra/differing). `win-unpacked` is likewise identical.
- Source binding of the packaged payload: all 51 non-cache backend files equal the `8d62725` git blobs; all 10 ASAR application files equal `8d62725` blobs; ASAR and backend version `0.16.0`; shipped `desktop/main.js` keeps `contextIsolation:true`, `nodeIntegration:false`, `sandbox:true`. The packaged `app-update.yml` feed is `Gemanoneko/booksArranger` (release), matching the publisher config and `origin`.
- Build native receipt `build-cache/builds/7e37a389-…/native-operation-result.json`: mode `build`, `root_exit_code 0`, `native_job_closed true`, `active_processes_after 0`.

Behaviour of the installed app (install, first run, update, Quit) is Futaba's packaged QA, not part of this verdict.

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

Pass. Renderer sandbox/context isolation and restricted IPC, exact native owner/runtime checks, argument-based process launches, leased Git/GH and credential handling were reviewed; no open Critical or safety-floor finding identified. Build-fix range: every new process launch is an argv list (no shell strings); the Git exception is limited to pinned literal paths/hashes/alias sets; the carve writes only a fixed name inside a fresh owned UUID folder; the error tails cannot carry the stripped GitHub tokens. The shipped `main.js` security flags are confirmed in the actual packaged ASAR.

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

Concerns (Minor only). The separate preservation module and lifecycle ledger concentrate their invariants; retry admission uses the production plan/manifest contracts. Native guard and release orchestration remain substantial maintenance surfaces, with focused failure-path tests reviewed.

- [Minor m2] `scripts/check-desktop.mjs:19-22`: `tests/test_build_external_tools.py` is not in the ordinary checker's pattern list, so the Git alias/DLL negative fixtures never run in the standard integrated check. The new carve refusal branches (`scripts/build_phase.py:103-118`: non-7z type, `Offset` 0/missing, size-sum mismatch, bad signature, short carve), the `allow_child_rename` share (`scripts/build_fs_guard.py:94-104`) and the Job settle loop (`scripts/build_native.py:167-174`) have no automated test. Full04 integrated evidence predates these commits (it ran at `841d637`). The real build at `8d62725` exercises the success path only. Enrol the file and add fail-closed negatives next cycle.
- [Minor m3] `scripts/build_phase.py:99-107`: the carve depends on the reduced `7zip-bin` 5.2.0 `7za` *lacking* an NSIS handler. A 7za that recognises NSIS would report `Type = Nsis` and the build would refuse. That is fail-closed and the comment documents it, but it is an implicit version coupling worth a pin or a note next to the 7zip-bin lock entry.

### 8. Doc/Code Drift

Pass for reviewed documentation scope. The `8d62725` comment "Member checks and the payload-equality verifier below are unchanged" is accurate (verified against the diff and the untouched `scripts/build-manifest.mjs`). This report distinguishes source review, actual component/real-book evidence, integrated checks, and the actual artifact binding. Historical 137-Python/29-Node declarations are not treated as executed evidence. Full04 actually ran 366 Python and 29 Node cases plus seven frontend and six syntax checks. Neither this report nor the genuine private whole-product graph claims a canonical protocol-2 handoff receipt. The user's explicit procedural waiver and narrow transport issue are recorded in the operation-review Doc. Shared Gate07 source review SHA256 `450668f459044db069aef3dda13e99d0ebdcf000b57be0168dc5ecd2b7704045` was independently read after the authorized shared-hook transition; its source acceptance is not inferred to be Books host-enforcement proof.

### 9. Build & Release Hygiene

Pass with Minor concerns. Reviewed existing `npm run pack` -> `node scripts/build-step.mjs pack` and existing direct `node scripts/release.mjs` primary publication entry, including complete source/runtime holds, 600-second native deadline, owned descendant closure, UUID staging, payload equality, fixed Git/GH, clean named pushed tag, artifact hashes and keep-four ordering. The actual installer is now built from clean `8d62725` and bound by the manifest (see Artifact binding). Payload equality was independently reproduced from the installer bytes, not only from the build's own receipt. This review does not claim the publication run.

- [Minor m1] `scripts/build_phase.py:103-121`: two of the new carve checks prove less than they appear to. 7za derives `Tail Size` from file size minus offset and physical size. The carved listing is the same archive 7za already opened. So the size-sum check and the listing check are self-consistency, not independent evidence. The code does not check the NSIS framing: the 4-byte uncompressed data-block length immediately before `Offset` should equal `Physical Size`. Nor does it confirm that exactly one 7z signature exists. Both hold for this artifact; I checked them independently. Adding them would bind "the bytes NSIS stores" rather than "the first 7z 7za finds". This does not weaken payload equality and does not affect this release.

Release-path requirements observed in the tool's own contract (`scripts/release-contract.mjs:24-36,68-76`, `scripts/release-flow.mjs:38-46`), for Sully and Futaba. These are not findings; each one fails closed.
- Only Docs-only/CHANGELOG descendants of `8d62725` may be released with this installer. Any version, lock or product-file change alters the product digest, and the release refuses. `package.json` and the lockfile are already `0.16.0`, so no bump is needed.
- `Docs/BooksArranger_ReleaseAcceptance_v0.16.0.json` must name this report and a QA report matching `^Docs/BooksArranger_QA_v0\.16\.0_YYYY-MM-DD\.md$`. A `_QAReport_` name is refused by the tool's contract, although the studio precondition script accepts both.
- Each accepted report needs exactly one line starting with `**Verdict:**`, exactly one `Release source commit: 8d6272593645226af711e2eb21a2c0d731d6d3d3` line, and exactly one `Release artifact manifest SHA256: 1a2f49cee6eaba6a3a0a7dd8d91c19a707dcaf7db01435cceb2694164d470a19` line.

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

## Finding rollup

- Open Critical: 0.
- Open Major: 1 (advisory, carried from the source review): `working_lifecycle.py:228` reference rescans scale with catalog size.
- Open Minor: 3. m1 `scripts/build_phase.py:103-121`: the carve checks are partly self-consistency, and NSIS framing is not checked. m2 `scripts/check-desktop.mjs:19-22` and the build-fix negatives: the new build-tooling tests are not enrolled or are missing. m3 `scripts/build_phase.py:99-107`: an implicit coupling to the reduced 7za.
- Always-blocking floor: intact. No machine harm, no out-of-scope writes (the carve writes only into a fresh owned UUID folder), no secret exposure, no repo-history risk.

Major and Minor findings are logged for Ender's next cycle and do not gate this release.

## Verdict

**Verdict:** RELEASE CLEAR

Scope of this clearance: the accumulated range `95febcdd4f4de4ffb59a3507053c4eb86f53936a..8d6272593645226af711e2eb21a2c0d731d6d3d3` and the installer `Books-Arranger-Setup-0.16.0.exe`, SHA256 `b556f61062d2d48b70581ac4c76be04304f7c3c6a9b0797e185c7d276119c15e`, bound by manifest SHA256 `1a2f49cee6eaba6a3a0a7dd8d91c19a707dcaf7db01435cceb2694164d470a19`. This clearance covers construction only. Futaba's packaged-QA GO is the independent behaviour gate. A rebuild, or any product-file change after `8d62725`, voids this artifact binding and needs a fresh binding check.
