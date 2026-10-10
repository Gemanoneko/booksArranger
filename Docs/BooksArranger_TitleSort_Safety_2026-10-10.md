# Books Arranger: focused title-sort safety review

2026-10-10. Senua. Bounded prototype safety-floor review of the leading-word title-sort rule and private MP4 metadata normalization. This extends the accepted chapter normalizer; it does not retag existing books or certify iTunes sorting.

**Verdict:** CLEAR

**Open findings:** 0 Critical, 0 Major, 0 Minor. Deploy after independent QA GO for matching pinned source.

## Exact source identity

Immutable `scratch/sort-title-2026-10-10/frozen-1/`, manifest SHA256 `c5f7dde3ab77203f2ea40ba5c149e592f4753dbcb7a2a820990e5fd5d02d7dc7`. Independently recomputed 20/20 listed file hashes; zero mismatches. This review certifies those source bytes rather than an unspecified later working tree.

| Changed source | SHA256 |
|---|---|
| metadata.py | 4994a44ae0482738f33eb97a024d21a63f60ffcdf75650d2b8dfa696d961f679 |
| quicktime_chapters.py | 9e68214164866a85764599b499fd60a830e66159424cf3a74320bc36bf99e358 |
| audio_pipeline.py | d42325b4e9141bde9b1c5813fcf6d5537f669e81000dda45a34da30987800342 |
| tests/test_sort_title.py | cc1944de738fed4dba8b825bc67e124a725200181bd4042fd3cb1e9f5976ada7 |
| Docs/BooksArranger_Brief.md | e377add301e3958031159eb2f1340c27750c36cf3e7ec8bf798f235cb7acb558 |

## Rule and metadata boundary

`audiobook_sort_title` derives a separate value without modifying the review's displayed title. It removes only a case-insensitive leading `The` followed by whitespace and another nonempty word, and only for the existing `Other` original-language category. `Theatre`, `The-Eye`, standalone `The`, `A`, `An`, Russian originals and unknown original language preserve their title. The preview receives this derived value; artist/narrator, folder names, recording language and canonical displayed title are unchanged.

The writer uses the private normalizer because the installed FFmpeg metadata route reportedly drops the sort tag. It inserts a `sonm/data` item carrying UTF-8 type 1, zero locale and the derived UTF-8 bytes. It preserves other metadata-list entries byte-for-byte, including display title, artist and cover, and removes existing `sonm` siblings before appending exactly one replacement. Repeated insertion of the same value therefore keeps one atom and measures zero further growth; changing a longer existing value can shrink metadata, with signed relocation applied to chunk offsets. The value is bounded to 8,000 UTF-8 bytes and unsupported empty/non-string values fail before output creation.

Only one Apple metadata list is accepted. Unsupported metadata full-box flags, malformed atom bounds or extra lists fail closed while still private. The normalizer continues to accept only its generated unfragmented faststart layout; large/extended atoms and unknown layouts are rejected. Its two-pass rebuild measures the entire movie metadata delta, rebuilds ancestor lengths, and updates all supported `stco`/`co64` entries with checked table width/count/range and numeric overflow rejection. A negative delta follows the same arithmetic. The final media atom and all its samples remain copied verbatim; the sort atom changes no AAC sample or chapter text sample.

Sort-only normalization disables chapter rewriting. Chaptered exports can apply chapter normalization and the sort atom in the same rebuild, avoiding separate competing offset adjustments. Exports whose sort value equals the display title add no sort atom solely for this rule. Existing chapter correction caller behavior is unchanged and receives no new sort request. No general retag route or live media migration was introduced.

## Validation and write safety

The pipeline validates the normalized output rather than the pre-normalization file. For an affected title it requires both the unchanged `title` and the decoded `sort_name`; existing author, audiobook media kind, artwork, chapter boundary and decoded-duration checks remain. The final normalized file's hash/size are used by the existing protected exclusive staging and native no-replace publication guard. Failure cannot silently publish the unnormalized file or overwrite a previous output. Source/review/cover validation and original source preservation are unchanged.

The tiny actual review/export fixture covers chapters on and off and reads back the real MP4 metadata via the pipeline plus direct atom traversal. It requires the full title, separate sort name, author, audiobook kind, selected chapter count, UTF-8 atom payload and unchanged input hashes. A synthetic existing-sort replacement test covers accented Unicode and both chunk widths; the earlier layout tests retain malformed atom/header and collision coverage. These are actual artifact assertions rather than FFmpeg command-string assertions. Ender reports seven targeted cases passing; Futaba's independent execution and repeated-normalization artifact check are separate evidence.

## Review limits and hygiene

This is source/format/publication safety clearance only. It does not certify how iTunes displays or sorts a real library, and does not certify iPhone chapter navigation. The user's successful import of the previous chapter correction does not imply this new sort atom has been device-tested.

Senua inspected pinned source, diffs, tests and all changed call boundaries; no live media writes, test execution, native application/library action, server/catalog mutation or Git operation were performed. No disposable probes were created, and all existing unique evidence remains untouched. The only reviewer-created artifact is this durable report.
