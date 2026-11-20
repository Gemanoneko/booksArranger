# Code Review — Books Arranger v0.30.0

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-11-20
Tool: Books Arranger
Release: v0.30.0
Commit range: 03041ee73c8c34e222885abe2db884fc23a34c9b..2c7129f84b394e0f086f94222935e812ce3d6412
Release source commit: 2c7129f84b394e0f086f94222935e812ce3d6412
Release artifact manifest SHA256: 1deac1f34ab8cfca0f3f46baa1a6fde2356ff6c025233ccab0177ec6e3430055
Build ID: a4d64d9a-217e-4348-9d27-6280e75fd2fd
Product tree: c2e2a1691fd969cc3e1905da678523b1f7af91944a6e3362f156b481f7fab44d
Files changed: 54 files, +1649 / -170 in 22 commits including merges
Stand-down dimensions: none
```

## Summary

The candidate fixes the single-file ALAC publication failure found at `882a1d3`. I repeated the original failing conversion through publication and compared every playable sample. The accepted installer, blockmap and update metadata match the manifest. The shell and installer were assessed through static payload verification. The required updater test exercises simulated installer failure, engine recovery and tray intent. Real Windows tray behavior was outside this pass.

### Review boundary

- The earlier reports cover `v0.29.0..5dbba45..03041ee`. The four Minor findings at `03041ee` remain in the preceding delta report.
- I reviewed `03041ee..882a1d3` for launch and cleanup, persisted actions, status, safe shutdown, regrouping, sorting, damaged audio and versioning. That pass found one Major. The original clean entry log had SHA-256 `2632843c37e5f2f77769b0fab048086a180475fe6dde9dcf3fe224c36676503a`.
- I reviewed `882a1d3..2c7129f` for the ALAC fix, the Approve count and the updater gate introduced by `981be38597639aa945e5edb05d740cf5793610d9`. This part changed 20 files, +309 / -56 in five commits. Counts come from Git shortstat and rev-list on the specified endpoints. The full entry ran once on the final clean candidate. Its `q30h/ender-entry.log` SHA-256 is `20b8c70ebd84fa53ed44bba2b35123d92ad582007038ccef2377cc4b24b5b256`.

## Rubric

| Dimension | Status | Evidence |
| --- | --- | --- |
| 1. Security | Pass | The audio worker passes media and paths as separate FFmpeg arguments. Publisher credentials are acquired after payload verification, the local recovery case and asset rehashing. The local case supplies a private environment. |
| 2. Correctness and logic | Pass | The qualifying ALAC now publishes. An Approve at 6/6 retains its file count and shows 100%. The renderer test also exercises 5/6 and an ordinary conversion entering its finalization phase. |
| 3. Crash and stability safety | Pass | A safe stop signals active approvals before waiting for admissions. An unsuccessful close retries when the admission and file change end. The shell retains its bounded hold for a named approval, press or file change. The earlier unanswered-status watchdog observation remains tracked under m-d1. |
| 4. Performance | Pass | The extra ALAC encode requires both an admitted short glitch and a single ALAC source. Intact ALAC keeps its compressed packet copy. Disk reservation includes uncompressed-rate headroom for the new path. |
| 5. State and data safety | Pass | A saved Pause parks restored file-changing actions and finished-book checks. Held-cleanup admission requires a Start in this launch. Sorting rechecks the recorded placement and refuses an occupied destination. The retained audio fixture kept its original bytes after publication. |
| 6. Input handling | Pass | Part-set grouping retains unchanged protected members and checks artist, numbering and source facts. The damaged-audio checks include an intact ALAC, damage inside and outside the threshold, AAC copy/in-place and joined parts. |
| 7. Maintainability | Pass | Space estimation and conversion use the same encoding selector. The publisher and standalone gate share the exact recovery-case title and result parser. |
| 8. Doc/code drift | Pass | The updated Brief and version predicates require project-local recovery from 0.30.0 forward. Native tray verification is optional. The preceding native evidence rules still apply to the historical versions that required them. |
| 9. Build and release hygiene | Pass | Versions, manifest, entry identity, shipped shell bytes, payload hashes and asset hashes match. The recovery case must execute exactly once and pass before the publisher proceeds to authentication. |

### Closed Major — playable single-file ALAC

The original 20-second ALAC fixture has SHA-256 `b29d218dab2793f02729d3e084b2b27c72f3c348c67e7e5a2ac481209c88743b`. Its first damaged packet begins at about 4.087 seconds. On `882a1d3` the shared check accepted 0.093 seconds lost. The single-file path then copied the damaged packet and failed output validation. The same file in a two-part Join produced a strictly readable 39.915-second result.

On the final commit, I used that fixture, the packaged FFmpeg and the actual `create_private` and `publish` functions. The completed journal recorded the glitch and the output decoded strictly for **19.90712 s**. Both the ordinary source decode and strict output decode produced **877,904 native PCM frames** with identical SHA-256 `e3f83550c35a2786d7ff04ff2e0e410424c24490beaf52dd7bdf5ea4afa0a55b`. The source hash also matched after publication. The committed regression exercised preserved chapters, intact packet copying and refusal beyond the one-second threshold in the final entry.

The documented five-second silence cutoff has a reproducible consequence. Two AAC sources with the same 0.124-second loss produced opposite outcomes when one contained a genuine 5.994-second silent interval later in the recording. This follows the measured rule recorded on 20 November and is excluded from the defect count.

### Package and updater evidence

I read both version markers as **0.30.0**, rehashed all **415/415** unpacked files against the installer-equivalence manifest and compared all **13/13** desktop JavaScript files with their ASAR members. I separately hashed the following assets and checked their byte counts against the packer's verification receipt.

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| Books-Arranger-Setup-0.30.0.exe | 209987083 | `d280da9ad5ed7e8f753a641d50203de45609151bdbea6a0e6ac92aa746c0bd18` |
| Books-Arranger-Setup-0.30.0.exe.blockmap | 220358 | `a70057fe331fda629817e7fb104020b64789b8378907845e9a0aa628b70de00a` |
| latest.yml | 360 | `f89552e8dcfcb9d3c69cbc4d21485007308f8fa7b61f59edde5174e49b504de9` |

The final entry records the named recovery case passing. It attempts the failed installer start, brings the old engine back on the existing catalog, retains the hidden window, checks the failure status and observes the tray tooltip clearing on a simulated click. The ordinary publisher verifies the accepted ASAR, runs that case again and rejects missing, skipped or failed results before credentials. This review covers the code and evidence available before publication. Sully owns the publisher run.

## Verdict

- Total Critical: 0
- Total Major: 0
- Total Minor: 0

**Verdict:** RELEASE CLEAR
