# Books Arranger v0.15.0 R5 cleanup delta QA — 2026-10-13

Futaba. Initial full candidate: b9b1166492b40e22fe9dc1a01607b57d5c065467. Delta baseline: reviewed R3 d3c55261cf64e8b8040ecc4cb86d551f51bdddfa. Immutable git archive: own scratch/futaba-cleanup-final-2026-10-13/pin-b9b1166. Shared mutable worktree code was not executed.

**Verdict:** NO-GO

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
