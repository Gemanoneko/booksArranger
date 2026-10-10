# Books Arranger: focused iTunes chapter safety review

2026-10-10. Senua. Prototype safety-floor review of the bounded chapter sample-description normalization, explicit MP4 muxing, and separate chapter correction caller. This is not a formal release review or a claim of successful iTunes import.

**Verdict:** CLEAR

**Open findings:** 0 Critical, 0 Major, 0 Minor. Actual distinct-output write is clear after independent QA GO and deployment of matching source pins.

## Source identity

Reviewed immutable `scratch/itunes-chapters-2026-10-10/frozen-1/`. Manifest SHA256 `a3b67b63ef4cfb459243b6beafcce43b3359982eca12cf52091692364be7ef4c`; independently recomputed all 46 listed file hashes with zero mismatches. This certifies those bytes, not an unspecified working tree or subsequent commit range.

| Source | SHA256 |
|---|---|
| quicktime_chapters.py | fc43e381e8a228b22790c65969e5e9073f30f91bed97d37130e8726e9472f72d |
| audio_pipeline.py | ca06fc48ce809a8c1350b9f95ae51acb98213ed9e88912dc975b824cfc54abf5 |
| chapter_repair.py | 1a34feda4b9cd103901073edfc6f8cee7cc8700423189f8c325a29057659b1b8 |
| support/repair_runner.py | 4a78809c68c7cb139a56f4596388e459d7db998268c7a47cbffe9240d6e62c4e |
| tests/test_quicktime_chapters.py | 6be2aa914f508a79a41726a72bb0523f597a3189df5a88ebb572f6298c299517 |
| tests/test_chapter_repair.py | 04c846df2ec5eb6bc0a6608a414c888abb99436c06b783a29e712945a60cf552 |

## Container and offset boundary

The new normalizer runs on private generated files only. It requires a distinct same-directory output, ordinary protected source/directory handling, exclusive creation, cancellation checks during streamed copying, and fsync. It accepts only the generated unfragmented `ftyp/moov/free/mdat` faststart layout. Extended-size atoms, malformed lengths, unsupported profiles, metadata over 64 MiB and nesting beyond 16 fail closed; this is deliberately not a general MP4 editor.

Exactly one `text` handler/sample-description track is required, with one supported sample entry and data-reference header. Replacement writes a 65-byte legacy description, including its Pascal font-name length at byte 59 and five-byte Arial name, and reserved fields at the checked positions. Text samples themselves are unchanged. The source cites Apple's [text sample description](https://developer.apple.com/documentation/quicktime-file-format/text_sample_description); the documented layout is the intended format contract. This review checked the field packing and bounds in code. Apple's Markdown endpoint could not be fetched through this reviewer's tools, so there is no claim of an independent complete specification download.

The implementation first measures movie metadata growth, then rebuilds containing atom lengths and relocates every parsed `stco` and `co64` table by the same signed delta. It checks table version/flags and exact entry count/width, requires original chunks inside the last media atom's payload, and rejects numeric overflow instead of truncating or silently changing table width. Unchanged atoms and the entire `mdat` are streamed verbatim. Because the accepted profile has one final media atom, no later media region or fragmented-relative offset needs separate relocation. Unsupported large-file layouts stop before publication; source files remain intact.

Future chaptered conversions validate the normalized artifact, and their output hash/size bind that artifact. Chapterless conversions skip normalization. The explicit correction changes its FFmpeg muxer selection to `mp4`, streams the existing AAC and cover, then normalizes privately before the existing full presentation check. That check compares codec/extradata, all compressed packet hashes/timing/side data, complete decoded PCM, cover bytes, retained metadata and chapter names/boundaries against the protected parent. A wrong relocation or audio change therefore cannot pass this correction's publication gate merely because duration looks plausible.

## Live write and recovery boundary

The next correction derives exactly ` - Chapters v2.m4b` from the original completed parent and never overwrites either previous M4B. The one-off runner retains the fixed parent job `9e04e700-ecf8-4807-8195-01a7a1d73bd6`, original output SHA256 `59f1527a05f1115f36e80473d0b94127612cd3ca6ad1b1e293f2aa0d68d61ff7`, and exact boundary-proof SHA256 `535fc85f08405a90c3305a5d9923831e8593c16344156232f9e7af7dc8e79db1`. It captures authoritative current catalog review/source order/cover evidence and repeats these checks under a short final SQLite writer exclusion, without editing catalog records. Read connections explicitly close. The accepted native protected-directory/hash/size/no-replace publication guards and durable intent journal are unchanged.

An early candidate changed recovery to accept only the new suffix, which would reject historical v0.4.2 owned journals. This was reported and closed in the frozen candidate: recovery accepts the two exact parent-derived historical/new suffixes, while retaining owned journal association, durable publication event, expected hashes/size, current review/source/cover checks. No arbitrary destination or filename-only adoption was added. The targeted fixture includes historical-suffix recovery and new-output collision rejection.

## Evidence and limits

Ender reports six targeted tests passing, including both chunk widths, malformed format rejection, complete media/presentation preservation and historical recovery; independent Futaba results are separate. Senua inspected exact pinned source, tests, call boundaries and hashes. No live media write, audio decode, native app/library action, user browser manipulation, server/catalog mutation or Git operation was performed by this reviewer.

The previous real artifact's 59-byte sample entry and muxer difference are structural clues. This review does not prove either is the sole reason iTunes 12.13.11.1 silently rejected import. A structurally valid file, FFmpeg decoding and safety clearance do not certify real iTunes acceptance or iPhone chapter navigation. The completed artifact still needs independent QA; actual native import remains unverified. No unique sources or unresolved evidence were deleted. This review generated only this durable report, so there is no owned disposable probe to prune.
