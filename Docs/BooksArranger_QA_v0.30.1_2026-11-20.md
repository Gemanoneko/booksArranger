# Books Arranger 0.30.1 delta QA

**Verdict:** GO

Release source commit: f658d2ecbbd0c938b911715b3becac7300474ac9
Release artifact manifest SHA256: 54468fbe13d1a9d160f1d3f98bfee22d749b9c2e8c4c77ff3298118634c7ae73

Futaba, 20 November 2026. Delta from released 0.30.0. The isolated source checkout was clean at the commit above. I verified all three upload assets against the manifest by length and SHA-256 and checked the installer SHA-512 against latest.yml. The installer is 209,985,256 bytes, SHA-256 bf386538e357e140e750ff2650fa47dcbec6cac13c93918b8f12fe7b523c7172. Build ID 5986017e-17a2-487a-a4d0-f087e4f70de6. Packaged app and backend versions both read 0.30.1. All 13 desktop JavaScript files in the ASAR matched the candidate. The packaged audio_jobs.py, manual_conversion.py, audio_pipeline.py and web/app.js also matched.

## Independent checks

Four Python tests passed using the unpacked installer's backend, Python and FFmpeg with private two-part AAC fixtures.

| Case | Observed result |
| --- | --- |
| Manual internal repair error | The failed draft kept both originals. A retained working file prevented Retry. Once the attempt closed, the draft allowed Retry. |
| Confirmed damage in a manual join | Corrupting most of one part's audio stopped conversion. The named part got replacement guidance, with Retry unavailable. |
| Automatic join, internal error and confirmed damage | An error in working-copy repair gave the named part the "couldn't finish" message. Retry accepted the current revision and refused a stale revision. The real corrupt-audio control gave replacement guidance and refused Retry. Neither case published output. |
| Repaired copy fails verification | The conversion stopped and identified the affected part. |

The manual and automatic failure checks compared each source's SHA-256, length and modification time before and after the attempt. The packaged renderer passed the repair DOM test, including the draft message and automatic-row Retry action. The project-local update test passed its exact M-1 case using the real desktop code and private engine/installer doubles. Native tray testing was omitted.

Pattern alerts: none.

## Entry identity

Read the passing replacement receipt from e031c/ender-entry.log. Its raw SHA-256 is d0c4ec088900c8f13ac643ac684233a04a3205f27828bbfac230e9b45e6938e4. QA ran only delta checks.

~~~text
Entry-check receipt v2: books-arranger v0.30.1 @ f658d2ecbbd0c938b911715b3becac7300474ac9 (dirty: N) [source:32b2730fe52896449ba2ca57f57dda97fa6cafa9724313443cbd9c9f415ff915; harness:8f63aa0e901bc9c14012066668fb24127ed2f286d77b266e0c32597a07d65a45; runtime:29c21c40220ffbf6ebcece9308cb3b017fda708a25362b04c8902b95b052646c; checker:4bae2cde4e4cdd2f22fb3060571730ec32fec1dd5403ea070086973b18b695e4] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a; personal-folders clean
~~~
