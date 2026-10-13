# Books Arranger v0.15.0 R5 cleanup delta QA — 2026-10-13

Futaba. Final acceptance pin: **95febcdd4f4de4ffb59a3507053c4eb86f53936a**, clean committed/pushed candidate on codex/books-split-books-0.15.0. Full delta baseline: reviewed R3 d3c55261cf64e8b8040ecc4cb86d551f51bdddfa. Product code is byte-identical to corrected ea57e276968879fb481d0d0963c82cbd104b7143; final95 changes only the shared fixture completion fence and its documentation. Initial b9b corruption finding and every failed protocol run are preserved below/in scratch.

**Verdict:** GO

The critical heterogeneous-PCM concat corruption is fixed: one smallest exact codec for every job member, followed by a complete actual-concat canonical PCM hash/frame proof against the ordered original-source normalization before AAC. Published working cleanup runs before retirement; failed retirement keeps sources/snapshots/recovery and prevents full Ready. Conservative source/staging/destination space admission stops writes and parks queued work cleanly. No source verification, retirement safety or 24-hour recovery bypass was accepted.

## Final actual checks

| Check | Actual result |
|---|---|
| Sender seven-suite graph | 88/88 PASS, no skip; 287.560 seconds tests, receipt envelope288.724 seconds |
| Independent receiver identical graph | 88/88 PASS, no skip; 287.575 seconds tests, receipt envelope288.619 seconds |
| Independent mixed-codec/width regressions | 4/4 PASS, both orders of s32/f32 and s16/f64; 53.677 seconds owned envelope |
| Independent precision/lifecycle/queue/native cases | 13 executions: 12 PASS, 1 unavailable file-symlink skip; separate actual NTFS directory-junction case PASS |

The 88 graph is actual unittest discovery/execution, independently counted as 88 '..ok' log lines, not merely AST definitions: working_cleanup16 + working_precision20 + working_lifecycle4 + storage_cleanup18 + automatic_media_policy15 + automatic_media9 + standing_admission6. Independent extras are 12 tests in41.519 seconds (11 PASS, one file-symlink skip), plus the separately executed actual junction test in0.396 seconds. The skipped file symlink requires an unavailable Windows privilege (WinError1314); no privilege/OS-setting change was attempted. Thus 88 declared checks plus16 passing independent scenarios, with one unavailable extra, are evidenced. No performance benchmark is claimed.

Independent precision recipes: exact f32 shrinks to exact s24; f64 fractional low bits and subnormals stay f64; PCM32 low bits/full scale stay s32; exact stereo shrinks to s16; resampling matches the full independently decoded canonical f64 bytes and frame count. Each case emits exactly one normalized WAV, verified by observing actual producer writes; rejected candidate formats produce no speculative WAV. Original private inputs stay byte-identical. Late injected disk shortage refuses before any WAV write.

All four formerly corrupt mixed-order scenarios now use common f64, return exactly8192 canonical bytes and match every original sample/hash through the real concat demuxer; real create_private also succeeds. Shared tests additionally verify mixed integer widths in both orders and that truncating the concat plan is refused before AAC/output creation.

Private real publication/retirement-failure probes verify disposable staging gone before retirement callback, original bytes/snapshots intact, converted/Ready0, repeated explicit resume safe and construction inactive. ENOSPC checkpoints produce no snapshots/normalized/output files; restart stays inactive/Paused. A20-job queue attempts one job only, parks the other19 and remains inactive on reopen. Legacy completed proofs without the new joined-PCM fields remain admissible to exact working cleanup without full-storage completion.

The shared graph exercises real AAC/ALAC native M4B copy, chapters, multichannel layout, packet/PCM/timeline/edit proof, final-output write refusal, source/normalized substitution refusal, real Ready/retirement and retained24-hour recovery. Unknown WAV/recovery/staging names, producer mismatch, wrong ownership, actual hardlinks/ADS, new identical-byte replacements, changed publication, absence without intent and crash-resume are refused or preserved as appropriate. Working-only success does not assert retirement/full completion.

## Exact manual sender/receiver contract

Applied qa-handoff's separately reviewed nonpackage/manual route; no package-checker receipt is fabricated. Futaba separately inspected the actual final sender receipt/log and all hashes before launching the one final receiver. Protocol remained frozen through receiver closure. Source231-file manifest, private execution copy, harness and installed Python/Bash/FFmpeg/ffprobe hashes match before/after. Suspended children enter a private OwnedProcessJob before release; child550-second/tool600000 ms bounds and native descendant closure remain enforced.

Identical Bash invocation, sequential sender then receiver:

```bash
exec 'C:/Python314/python.exe' -I -B 'C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/split-books-2026-10-13/worktree/scratch/cleanup-delta-2026-10-13/full_owned.py'
```

Actual independently compared identity/result line:

```text
MANUAL BooksArranger target=0.15.0 source_VERSION=0.15.0 HEAD=95febcdd4f4de4ffb59a3507053c4eb86f53936a snapshot_dirty=false source_digest=a1c78bd624bbd1fe8ea5e7c3761fbd2e387228bed97a9e6d0d97f6ee1911ad1b focused7=PASS88 package_checker=n/a(nonpackage)
```

Contract/receipts under worktree scratch/cleanup-delta-2026-10-13:

| Evidence | SHA-256 |
|---|---|
| full-context.json | bd3d8fdd256e62e196267f5482a3a80101ceac31e98194de7edcb332b347f1a1 |
| full_owned.py | 438958235e978f6786108db0c94e9631ed2185fea674d4786fa46e4b6f36cdc3 |
| full_inner.py | af071e334c90817104a29c0473c5029da86ad975fe4c73f38e738e7f7d6986c2 |
| Sender receipt r-919a7b81616f4efe8d5f02dcf789e28a | c574fb07736206fd6e2f9acc8b3d7c94a5e5db78788742679ba59d6f769d08be |
| Receiver receipt r-398ee93b11224c1fb12452ecf5233cc0 | c232cf4a1d6ad6d37e195bfe9c07ad3f8620048305ffe594bc8c39aca3cf7d39 |
| Receiver full log | e850aaaa09f595b05309f67470fc585c9fcc1f064471a5130d9c9742f311629c |

Runtime pins: Python434b361fe0c5960d404974feed493db47f2603a1ace2574312104fbed0182c6f; Git Bash6cc575e9112efe6253b6a6999c12aa0240cb3f511aeda3480ae026edc0dc5280; FFmpeg09948d4cdd0650da6ff5a87577469f2a218dc2615ae379f8f734d24c49de0f73; ffprobea6618e99bb58869ded3c6f37b53aa1a8d701c3591dbb7b5b317d47369c112be2.

## Independent evidence, scope and limits

Own scratch/futaba-cleanup-final-2026-10-13 commands (Git Bash, timeout600000, each finite suspended child/OwnedProcessJob): run_corrected_probe_owned.py, run_independent_final_owned.py, run_junction_owned.py via C:/Python314/python.exe -I -B. Independent product archive digest8f1309132725cee5733b83c376ae5be006f927526b817c756765fce28f878d44 at ea57; unchanged product bytes reused after final95f fixture-only diff verification. Exact original12-case executed harness is retained separately after adding junction coverage.

| Independent evidence | SHA-256 |
|---|---|
| precision_fixtures.py | 03e81ef91eaf0791b1fcfa8689be50fabae8f4dcab473616c6185574402e5f54 |
| mixed_concat_corrected.py | c6c6f51de6f6d5a7a9cc5d50615b5ce6c2d6f80868925a8fe10b254d132edcca |
| mixed-concat-ea57-results.json | b4e54385a3f9020f05a5e94d23ecf4c2b2cf8990103d21909c08aa76bcb14c59 |
| mixed-probe-ea57.log | 99a1a2e6a1ebbbca5d1d34256da9869d34daeb6064048565e8904fdace383c23 |
| independent_final-12case-executed.py | 86fd07514229ca81145ff2c7b2e7d812789b013a16bb8e941feffd747d2b927e |
| independent-final-ea57.log | c6d4d34ea22fc72e42c04e3cf411bb2b90aa60f2a9be825740305d215d328828 |
| junction_probe.py | 1aaecd04654fe7b05da849d453dc02f6df1e84e0a348be94db32c40fb6c837a1 |
| junction-probe-ea57.log | cced0f7d67a8703142a75aaf426d166f9317c165e0980d89450673fbb1b17a34 |

Grouping/source identity/spelling/native boundary/source retirement/recovery retention/recording classification files are byte-identical to R3 (git diff checked); their prior R3 proof is reused. No full610-test rerun or new real-library chapter survey is claimed. Native M4B/changed media/cleanup boundaries are actually exercised by the final88 graph. Existing R3 inherent-limit dispositions remain unchanged.

No live data/Z:/Y:, real app/GUI, HTTP Start/Stop/POST, actual-library conversion/retirement, packaging or user restart was exercised by QA. Private MergeService fixtures are backend tests, not a live app launch. No Git/version/code edits by Futaba. Full GUI/packaged/live application remains the separate release/apply operation.

## Failed attempts and explicit disposition

Initial b9b NO-GO below: actual mixed-codec PCM corruption. Disposition: FIXED and independently regressed at ea57/final95f.

Long-copy sender runs had15 unchanged metadata output-path refusals; QA's earlier long receiver subsequently failed closed with Harness drift when the shared protocol was corrected. QA initially reported receipt presence as PASS before separately reading its contents; that claim was explicitly corrected, and no GO depended on it. The final sender was independently read/hashed and passed88 before the final receiver invocation.

Short-copy attempts had3 setup errors from an absent private fixture parent; Senua also saw3 assertion failures. Exact diagnostic captured real audio worker still Running when the old three-poll fixture wait returned across postprocessing transitions. Final95f fixes only test completion observation: one state snapshot plus real worker-inactive fences, preserving the original30-second deadline. Harness prepares the known private parent. Final sender/receiver88 both pass all former failure cases; no product behavior failure was excused as timing. Isolated junction probe first failed an -I import-path setup, then passed after adding the owned module directory; failure log retained.

Pattern alert: immutable-export fixture scaffolding did not match execution assumptions (path length, required private parent and multi-poll completion fence). Disposition: FIX — reviewed short owned-copy route, explicit private-parent preparation and committed single-snapshot/worker-inactive fence; final88/88 sender and receiver verify the disposition. No additional product-friction pattern found.

Routine hygiene: all generated tiny fixture media/databases were removed by fixture teardown. Verified empty owned fixture directories were removed after final closure; routine-hygiene.json records exact targets/counts. Compact receipts/logs/repros, immutable source/context and the final receiver execution copy remain review evidence until release. Other agents' outputs and live data were untouched.

## Initial failure evidence (preserved)

# Books Arranger v0.15.0 R5 cleanup delta QA — 2026-10-13

Futaba. Initial full candidate: b9b1166492b40e22fe9dc1a01607b57d5c065467. Delta baseline: reviewed R3 d3c55261cf64e8b8040ecc4cb86d551f51bdddfa. Immutable git archive: own scratch/futaba-cleanup-final-2026-10-13/pin-b9b1166. Shared mutable worktree code was not executed.

Initial verdict (superseded): NO-GO

## Blocker R5-B1 — heterogeneous normalized PCM is misread by concat

The new precision selector chooses a codec independently per source. The existing concat demuxer applies the first stream's codec to later raw WAV packets. Complete per-file precision checks therefore pass even when concatenation changes later audio. The final duration/sample-count checks can also accept this. This violates exact media preservation and can subsequently permit retirement of originals. Senua surfaced the construction risk; Futaba independently confirmed actual behavior.

Four real private native-media probes (all on the fixed committed source, no live operations):

| Normalized order | Complete canonical source bytes | Concat-decoded bytes | Equal PCM | create_private outcome |
|---|---:|---:|---|---|
| pcm_s32le → pcm_f32le | 8192 | 8192 | No | Accepted |
| pcm_f32le → pcm_s32le | 8192 | 8192 | No | Refused with NaN/Inf encoder error |
| pcm_s16le → pcm_f64le | 8192 | 20480 | No | Accepted |
| pcm_f64le → pcm_s16le | 8192 | 5120 | No | Accepted |

For the same-width s32/f32 case, original canonical hash 80498ef5eee4e0b11c3ebb0d09187c7ef62d165897d0a100644d0f1f04cd99af differs from joined hash 5865c932a8721571ac1f7bac58c98f591c7eb460776fd6438bec37414cce2aa5 despite unchanged byte count. The independent raw comparison fixes identical 48000 Hz mono encoding for both inputs and compares every original decoded f64 sample to the exact normalized WAV concat decode. The app attempt separately invokes its real automatic manifest/policy/create_private flow; it returns a validated private output in three cases. No destination publication or retirement was performed.

## Exact method and evidence

Own harness mixed_concat_probe.py generates two tiny WAVs per scenario, using precision_fixtures.py; calls frozen normalize_sources; runs pinned FFmpeg concat decode through the frozen run_owned process containment; compares full f64 bytes/hashes; invokes create_private with a private automatic manifest. Each temporary directory is torn down afterward.

Command via Git Bash, timeout600000:

    /c/Python314/python.exe -I -B 'WIP/Books Arranger/scratch/futaba-cleanup-final-2026-10-13/run_probe_owned.py'

The outer runner starts a suspended private child, establishes OwnedProcessJob before release and uses a 580-second child bound. Actual run exit0, 54.319seconds; exit0 means the diagnostic completed, not acceptance. Source manifest hashes are checked before/after and match, digest23aa115afcaee55edf5c51b6d22b11b86f97836b609c9525713e0e7a7d8a6735. Native module SHA46affe8d8ba8304944c5a2f0e4ad7ca2db79566c40016ab694b366b3dbf5becd; Python SHA434b361fe0c5960d404974feed493db47f2603a1ace2574312104fbed0182c6f; probe SHA2116247f7fdc8d22ec987051cadccd46bf2b9bb6cfe3734d64b139931866c149. Evidence under own scratch/futaba-cleanup-final-2026-10-13: mixed-concat-b9b-results.json and mixed-probe-b9b.log.

## Pending acceptance

No full sender/receiver receipt or GO is claimed for this blocked source. Await fix commit, committed immutable source, final matching manual graph and independently executed receiver, then rerun mixed codecs/widths in both orders plus precision, lifecycle, disk holds/Paused checkpoints, source/recovery/Ready safety and native M4B regressions. No package checker receipt is fabricated for this Python tool. Prior urgent cleanup GO covers its separately pinned subset only.

No live data/Z:/Y:, app launch, HTTP Start/Stop/POST, desktop input, Git/VERSION changes or live deletion. Disposable fixture directories were removed; small failure evidence and source archives retained.

Pattern alerts: none.
