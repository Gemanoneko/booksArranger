# Books Arranger iTunes chapter-container regression

**Verdict: scoped GO for the pinned structural repair pilot; actual iTunes import remains UNKNOWN.** No claim that iTunes rejection is fixed until an actual import succeeds.

Reported failure: iTunes **12.13.11.1** silently rejected the v0.4.2 chapter copy, despite ffprobe and full audio validation passing. Ender's diagnosis identified a 59-byte legacy QuickTime text sample-description stub without its required font-name length field, plus a changed muxer/container profile. This QA does not duplicate that diagnosis or infer import compatibility from ffprobe.

Accepted snapshot `scratch/itunes-chapters-2026-10-10/frozen-1`, **46/46 hashes verified**, manifest SHA256 **a3b67b63ef4cfb459243b6beafcce43b3359982eca12cf52091692364be7ef4c**. Complete pins retained in `scratch/itunes-chapters-qa-2026-10-10/accepted-manifest.json`.

| File | SHA256 |
| --- | --- |
| quicktime_chapters.py | fc43e381e8a228b22790c65969e5e9073f30f91bed97d37130e8726e9472f72d |
| audio_pipeline.py | ca06fc48ce809a8c1350b9f95ae51acb98213ed9e88912dc975b824cfc54abf5 |
| chapter_repair.py | 1a34feda4b9cd103901073edfc6f8cee7cc8700423189f8c325a29057659b1b8 |
| support/repair_runner.py | 4a78809c68c7cb139a56f4596388e459d7db998268c7a47cbffe9240d6e62c4e |
| tests/test_quicktime_chapters.py | 6be2aa914f508a79a41726a72bb0523f597a3189df5a88ebb572f6298c299517 |
| tests/test_chapter_repair.py | 04c846df2ec5eb6bc0a6608a414c888abb99436c06b783a29e712945a60cf552 |

**Eight targeted fixture tests passed in 5.899 s:** four supplied structural cases, two actual repair/API cases and two independent boundary cases. Additional exact frozen-runner read-only preparation succeeded against the current completed 40-source parent/review; its guard returned true and derived the separate ** - Chapters v2.m4b** path. No execute mode or write lock was entered against the live catalogue.

Structural assertions verify a **65-byte** legacy text entry, Pascal font-length byte at offset **59**, value **5**, text **Arial**, and expected reserved bytes. The 59-byte description is rejected by the layout validator. Both stco/co64 offsets relocate by the measured six-byte metadata growth while synthetic media payload stays byte-identical. Independent cases reject offset overflow at both integer widths, offsets outside payload, malformed table counts, invalid font bounds/reserved fields and excess nesting; malformed atom/header and destination collision also reject. Transformation is intentionally limited to its owned unfragmented faststart MP4 profile. The intended layout reference is [Apple's QuickTime text sample description](https://developer.apple.com/documentation/quicktime-file-format/text_sample_description); automated document retrieval was unavailable, so no additional documentation claims or quotations are made here.

The actual media repair case uses distinct beginning/end tones and Unicode/escaped chapter names. It creates a separate Chapters v2 output, preserving parent hash and original MP3 hashes, exact AAC payload/extradata/delay/packet timestamps, decoded PCM, cover bytes, core tags and two chapter names/timings. Full decoded PCM receipt is **26,624 mono frames at 44,100 Hz**, **53,248 bytes**, SHA256 **f44b5b71013e931fc74256e924d057a083c80f8937e4461c0082602a508d6b64**; before/after presentation equality is enforced by the pinned helper. The normalization receipt confirms one repaired chapter text track and its 65-byte layout. New destination collision preserves existing output. Owned-intent recovery recognizes both the new v2 suffix and a synthetic historical v0.4.2 ** - Chapters.m4b** journal association, subject to exact bytes/identity. Saved-off/default distinction remains correct.

Evidence `scratch/itunes-chapters-qa-2026-10-10/evidence.json`, SHA256 **2e53cecfa390f19a36b70412d0fd9246cbe160b2fd62f0300df31d3690426131**. Command exited code 0; generated temporary source/output/stage fixture trees self-cleaned, fixtures directory empty, media children and read connections closed. Only compact evidence/pinned snapshots/harness/report remain. No native app/user browser, live merge/scan/repair, Explorer, playback, iTunes library write, source/pilot write or Git action occurred.

Actual-import testing has no authorized route within this scope: native iTunes interaction and library writes are explicitly excluded. A later separately authorized test could import only the newly produced v2 artifact into an isolated disposable iTunes library, record success or silent rejection on the exact installed version, and close that owned session. That is an option requiring authorization, not a performed check or a request for the user to run QA. Current disposition: structural/presentation regression **passed**; actual iTunes import and iPhone chapter navigation **pending**. Separate Senua construction clearance remains independent.
