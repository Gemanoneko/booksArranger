# Isolated MP4 preservation bytes prototype

Source preparation only, 2026-10-15. No import, syntax check, test, media command or application operation has executed for this prototype. It is not imported by the frozen 13-case graph, not a deployed repair, and does not clear any of the 81 held jobs. All fixtures are constructed in memory; the module has no filesystem, subprocess, network or live-data API.

`retag(source_bytes, approved_tag)` returns new bytes and a structural receipt. The sole approved change is replacing the existing single Apple `sonm/data` UTF-8 tag, updating enclosing sizes and relocating all `stco` or `co64` entries by the exact tag-byte delta. `prove` independently parses both operands and requires byte-for-byte equality with that complete authorized transformation; changing even an otherwise valid edit is rejected. Source bytes are immutable. Payload and decoder descriptions are compared exactly; presentation, decode duration, composition offsets and edit mapping use `Fraction`, without tolerances or millisecond conversion.

## Deliberately narrow supported profile

- Maximum 8 MiB input/output, 4096 atoms/table rows/samples, 8000 UTF-8 tag bytes; ordinary 32-bit atom headers only.
- Exact top-level `ftyp/moov/mdat`, M4A major brand and only listed compatible brands; no free/wide/fragmented atoms.
- Exactly one audio track, version-0 movie/track/media headers and required version-0 rate-1 edit list, allowing leading empty edits and nonzero media start. Track duration equals the edit sum/movie duration. Edits must stay within media decode duration.
- Exact declared child layouts and a single self-contained URL data reference. One version-0 `mp4a` description with an opaque `esds` descriptor, retained byte-for-byte. The prototype does not interpret that descriptor or certify its codec validity.
- `stts`, optional version-0/1 `ctts`, one `stsc` run (one sample per chunk/description 1), fixed or variable `stsz`, and exactly one `stco` or `co64`. Chunks cover the entire single mdat payload contiguously in sample order; overlaps, gaps, unclaimed bytes and offset overflow refuse.
- Exactly one `udta/meta` with mdir handler and one existing `ilst/sonm/data`, UTF-8 type and zero locale. No tag creation, artwork or chapter rewriting.

Unknown/duplicate boxes, additional tracks, chapter references/text/video, alternate tracks, fragmented/external media, unsupported versions, large/zero atom sizes and all layouts outside this profile refuse. Rejecting chapter/video input is intentional: no relationship is dropped or claimed preserved by acceptance. The prototype cannot yet accept the no-edit representative, the real chapter layouts, HE-AAC clock/sample-table changes or most production M4Bs. It establishes only the first tiny structural tag/timing proof, not a general-purpose MP4 validator or production metadata writer.

## Prepared verification and remaining proof

There are **12 unittest method definitions**, counted statically; zero discovered or executed cases. They cover non-1000 movie clock/nonzero edit/leading gap and tag growth, co64 shrink, ctts preservation, altered edit/payload detection, unknown/fragmented/external/video refusal, chunk overlap, truncation/extended sizes, and invalid/unapproved tags. The synthetic esds/payload are deliberately opaque structural bytes, not valid decodable AAC, so **no PCM, decoder trim or native playback proof is supplied**. The receipt reports those obligations false.

Next: Senua reviews exact source/test/runtime and an isolated operation capsule, then separately authorized execution discovers/runs these tests. A later independently reviewed real encoded synthetic fixture/media capsule must prove full all-channel native PCM, decoder trim/skip/discard semantics and chapters before application integration or retry. Additional profiles require explicit source changes/review and new negative tests. No execution permission or hook/trust change is implied by this directory.

The bounded atom header pattern was studied in canonical `quicktime_chapters.py`; it was reimplemented without importing that module, whose filesystem/native dependencies and broader chapter transform are outside this proof. No disposable files were generated.
