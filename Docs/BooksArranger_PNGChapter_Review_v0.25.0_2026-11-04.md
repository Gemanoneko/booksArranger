# Books Arranger 0.25.0 — PNG chapter-image source review

Reviewer: Senua. Date: 2026-11-04.

Reviewed commit range: `87b568143a5f803154c2564cae0487cc83fe0f6c..a1fd80c793db137c50ba75d2990f22ec0f022698`. Product/test scope: `m4b_preservation.py` and `tests/test_m4b_preservation.py`, +147 / -9. This is a source-slice assessment; the remaining folder/media changes, complete milestone QA and exact final build are outside it.

Open findings: Critical 0, Major 0, Minor 0. No safety-floor violation identified.

## Checked boundaries

| Dimension | Status for this slice |
|---|---|
| Security | Pass: parsing uses bounded byte reads and CRC calculation, with no new shell, IPC, credential or filesystem authority. |
| Correctness and logic | Pass: only the exact `png ` sample entry joins the existing JPEG entries; PNG samples must have the checked static envelope. Unknown entries remain refused. |
| Crash and stability | Pass: every sample has checked extents/short reads, finite chunk counts and complete chunk framing before field access. |
| Performance | Pass: at most 8 MiB per PNG sample and 32 MiB cumulative image reads, separately from the unchanged metadata budget; no image decompression or dimension-based allocation. |
| State and data safety | Pass: the original sample tables/references and complete track bytes remain immutable; the existing full retained-byte and audio preservation proofs remain required. |
| Input handling | Pass: signature, chunk type/reserved bit, CRC, legal IHDR values, PLTE rules, contiguous IDAT and exact terminal IEND are checked; animation/unknown critical chunks refuse. |
| Maintainability | Pass: static PNG-envelope checking is isolated and the image reader is explicitly supplied by the existing preservation planner. |
| Doc/code drift | Pass for the source contract: this proves a bounded static envelope and byte preservation, not decoded image validity or device compatibility. |
| Build/release hygiene | Source scope passes: two pinned source/test files only, no runner/build-graph or dependency changes; final package remains pending. |

The track validator still requires mapped nonoverlapping samples inside retained `mdat`, valid unchanged chapter references and exactly one audio track. PNG samples are checked only after their table-derived extents are established. The rewrite retains the full `trak` bytes and media payload; no chapter is dropped or synthesized by this extension. The real production-pipeline test also requires compressed audio/configuration/presentation equality, complete native PCM verification and unchanged source bytes. JPEG field-extension/reference restrictions are unchanged.

The parser's critical-chunk order and envelope checks agree with the [W3C PNG specification, sections 5 and 11](https://www.w3.org/TR/2025/REC-png-3-20250624/). FFmpeg's primary codec-tag table identifies the exact [`png ` QuickTime tag](https://www.ffmpeg.org/doxygen/8.1/isom__tags_8c_source.html). Ancillary payloads are retained as opaque bytes after framing/CRC checks; image pixels and ancillary semantics are not decoded. This does not weaken the audio integrity or retained-byte proof.

## Evidence checked

Verified summary SHA256 `510a50874008eac7ff151990b6aa574774f2f969f25c211d683f9b825d590c18` and patch SHA256 `7dce44913fe86a2d143fe94a06410541841c38d93c04968c63b3eddc7f40565c` under `Docs/Evidence/converted-duplicate_2026-11-04/png-chapters`. Both committed source/test files and every listed retained evidence file match their exact hashes.

The baseline receipt records both positive PNG fixtures refusing the old unsupported image entry. The corrected final module receipt records 102/102 passing in 6.677 seconds, including JPEG retention; unknown image entries; each PNG sample; short reads; per-image/total budgets; malformed CRC/header/chunk order/extents; and unchanged container/reference guards. The separate real AAC-LC 44.1 kHz stereo test with two PNG samples and a text chapter passes the production preservation path in 1.641 seconds and asserts identical `mdat`, identical tracks and unchanged source bytes. These receipts close with native zero, complete output, no force and no timeout.

Senua ran no tests, native probes or apps and accessed no live library paths. No full-gate result or release-artifact clearance is claimed. The final accumulated review must cover `bf4425de09c355d2a0743771ca4209b24c8f0de1..` the final pushed source and bind the exact packaged build.
