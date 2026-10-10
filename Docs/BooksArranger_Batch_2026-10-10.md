# Books Arranger next two-book batch — 2026-10-10

Existing published v0.4.4 processed exactly two explicitly authorized ordinary books sequentially. No code/version changes, rescan, source cleanup, overwrite or iTunes/device actions occurred. The existing app reviewed identity and exact intended source membership/order with assistant provenance, froze source hashes and cover, created protected snapshots, measured full decoded PCM boundaries, used source-matched AAC and validated all output/source/publication gates.

## Completed artifacts

### MirrorMask

- Output: `Z:\Audiobooks\Gaiman Neil\MirrorMask - Gaiman Neil.m4b`
- Job: `0b6fedcc-2d95-46a9-a4a3-4192da37ff72`; candidate `d3d04342-0034-4161-b35c-62d116462ea1`, frozen revision 4.
- Bytes: 117,288,173; SHA256 `fee7f5119803919d9571905f640fad8fce50ca803f528ed5396e124b6dc988d5`.
- Source set: 11 MP3s, 114,906,562 bytes. Final full streamed source hashes and exact size/ns match the approved manifest.
- Chapters: 11, original track titles retained. QuickTime legacy text description 65 bytes; no invented literary names.
- Exact selected-source PCM duration: 4779.440000000s; decoded output duration 4779.456145125s, within recorded AAC padding tolerance 1.1s.
- AAC target: 191,719bit/s, 2 channels, 44,100Hz; highest verified protected MP3 stream bitrate. No lower-bitrate retry or forced downmix.
- Artist/album artist: Neil Gaiman; display title: MirrorMask; audiobook classification type2.
- Cover SHA256: `2e56990ec185048fba35334a4b9d583dec34e68dd440f20c1a7da084f9a27da1`. Existing attached JPEG extracted under protected source handle, visually checked against title/author; preserved exact image without external replacement. MirrorMask cover credits McKean as creator alongside Gaiman; reader identity not claimed. Existing app cached PNG representation independently re-derived from protected same attachment, byte-identical to cached selection and visually verified; raw JPEG and PNG hashes both recorded in MirrorMask-cover-proof.json.
- Identity evidence: https://www.neilgaiman.com/works/books/mirrormask/in/189/
- Reader: Unverified; no reader inferred from Artist.

### Snapshot

- Output: `Z:\Audiobooks\Sanderson Brandon\Snapshot - Sanderson Brandon.m4b`
- Job: `dc4874af-e132-47cd-93ab-85e5b0fbeea7`; candidate `c444877b-28bc-4cb7-ab42-cea829fc4bdb`, frozen revision 4.
- Bytes: 254,315,402; SHA256 `8fa450ff941c48833c3d4ea7705ec837741dc150b74d251ecc2de38e49d5ea70`.
- Source set: 10 MP3s, 243,387,177 bytes. Final full streamed source hashes and exact size/ns match the approved manifest.
- Chapters: 10, original track titles retained. QuickTime legacy text description 65 bytes; no invented literary names.
- Exact selected-source PCM duration: 10095.386122449s; decoded output duration 10095.386122449s, within recorded AAC padding tolerance 1.0s.
- AAC target: 192,000bit/s, 2 channels, 44,100Hz; highest verified protected MP3 stream bitrate. No lower-bitrate retry or forced downmix.
- Artist/album artist: Brandon Sanderson; display title: Snapshot; audiobook classification type2.
- Cover SHA256: `bca7ca57a9d477bd2b19c8813e0be2fb0b3fac0b3266115b9ad036148e109b67`. Existing attached JPEG extracted under protected source handle, visually checked against title/author; preserved exact image without external replacement. MirrorMask cover credits McKean as creator alongside Gaiman; reader identity not claimed.
- Identity evidence: https://www.brandonsanderson.com/blogs/blog/snapshot-is-out
- Reader: Олег Булдаков.

## Limits and preservation

All 21 original MP3s remain unchanged according to final full streamed SHA256, size and nanosecond timestamp checks under protected read handles. Output records retain supplemental source metadata/comments and assistant evidence. External publisher recording completeness is not certified; all intended selected source audio passed the existing decoded-output checks. AAC reencoding is lossy and matching bitrate is not an identical-sound guarantee. Modest cover/container/codec size growth is allowed by the user’s quality-first rule.

MirrorMask uses the existing app’s PNG cache representation of its same-source attached JPEG; independent protected transformation and visual checks matched, with raw JPEG/cached PNG hashes retained. Snapshot uses its exact existing companion JPEG. No existing Eye of God artifact was read, changed or depended upon by these two jobs.

iTunes import, device synchronization and chapter navigation for these two new artifacts have not been tested. Independent artifact QA is a separate bounded read-only report.

## Durable producer evidence

- `scratch/next-batch-2026-10-10/completed-proof.json`, SHA256 `89d248ccb87c20f9ad01accca0b99e634d1ccc89b3d819ace2e91498b9f3eb5e`: both full job manifests/journals/output validation and final streamed output/original preservation receipts.
- `two-book-plan-approved-cover.json`: approved identity/order/naming/cover plan.
- `MirrorMask-cover-proof.json`: exact same-source cached artwork proof.
- `MirrorMask-completed-proof.json`: first artifact standalone preservation receipt.

No source or output files may be deleted based solely on this report.
