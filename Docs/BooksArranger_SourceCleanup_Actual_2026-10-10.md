# Books Arranger — actual source cleanup, 2026-10-10

Version 0.5.0, published source e7001bbd41e8b7d853a84339d47ef20c9cf91dc4. Assistant execution under Sergei's authorized convert-then-remove workflow. Exactly two independently validated completed books were enrolled; no new conversion, scan, or other historical cleanup ran.

## Results

| Book | Cleanup ID | Removed originals | Recovery bytes |
| --- | --- | ---: | ---: |
| MirrorMask | eafb1b0b-82e4-445d-9273-0fb54911f21f | 11 | 114,906,562 |
| Snapshot | 0b7cf961-85c6-43a0-879a-0e6c75b414a5 | 10 | 243,387,177 |
| Total | | 21 | 358,293,739 |

Every included original MP3 name is absent from Z:, and every recovery file matches the approved original full SHA256, size, and nanosecond timestamp. These are sums of file sizes removed, not a measurement of physical NAS free space. Recovery copies remain on C:; no permanent purge was performed.

Recovery directories:

- `C:\Antigravity Projects\Studio Illuminati\WIP\Books Arranger\data\source-recovery\eafb1b0b-82e4-445d-9273-0fb54911f21f`
- `C:\Antigravity Projects\Studio Illuminati\WIP\Books Arranger\data\source-recovery\0b7cf961-85c6-43a0-879a-0e6c75b414a5`

## Outputs and collateral

Both completed output files retained their exact bytes, metadata, artwork, quality profile, and chapter markers. Cleanup did not encode or modify either output.

- `Z:\Audiobooks\Gaiman Neil\MirrorMask - Gaiman Neil.m4b`: 117,288,173 bytes; SHA256 `fee7f5119803919d9571905f640fad8fce50ca803f528ed5396e124b6dc988d5`; 11 chapters.
- `Z:\Audiobooks\Sanderson Brandon\Snapshot - Sanderson Brandon.m4b`: 254,315,402 bytes; SHA256 `8fa450ff941c48833c3d4ea7705ec837741dc150b74d251ecc2de38e49d5ea70`; 10 chapters.

Both original source directories remain. MirrorMask's source directory is empty. Snapshot's original `Брендон Сандерсон - Стоп-кадр.jpg` remains: 106,988 bytes, SHA256 `bca7ca57a9d477bd2b19c8813e0be2fb0b3fac0b3266115b9ad036148e109b67`. Eye of God, podcasts, ebooks, and unrelated sources were excluded. Actual Apple import/sync for these two books remains untested.

## Execution and evidence

The first caller enrolled MirrorMask successfully but failed its title-based monitoring lookup after the source was retired. This was a caller-monitoring failure; the cleanup worker completed all 11 removals. A separately pinned, independently reviewed caller correction monitored exact authoritative job and cleanup IDs, verified the completed MirrorMask receipt without reenrollment, and enrolled Snapshot only. Its SHA256 is `246031bdb5c2865c43a972fcf2244ecff653238af00b5f9b41fe52dd321e0176`.

Evidence is retained under `scratch/source-cleanup-2026-10-10/`:

- `final-source-removal-proof.json`: SHA256 `fd214a12351de0121445f39c0752df406694f3548a920ac9545ff110a2f8e3c7`.
- `actual-cleanup-corrected.json`: SHA256 `d5aac40f5de2015fe60035adcbf040a9cc2afea92d552215fd816c976929e568`.
- `manifest-frozen-2.json`: SHA256 `5666525f9421357fcd69c6f6440c3aba0c476059c0cd35c0cd146df4cb4d8eb9`.

Independent read-only postcondition QA: `Docs/BooksArranger_QA_ActualSourceCleanup_v0.5.0_2026-10-10.md`, SHA256 `436c4082c4b038d440def32d8f4cfd621bc678cfb7a32fa60cb68fb1a0398013`.

The retained service is healthy: PID 55876, instance `23a8d2f9c79c979558e614b4749eeb16`, version 0.5.0. Catalog remains 9,550 files, generation 4, one existing read error, pending zero; three audio jobs remain completed, no queued or failed audio jobs, and no active cleanup. Exactly two cleanup records and 21 source-retirement rows were recorded. Recovery files, journals, immutable manifests, rollback material, and unique evidence are retained. No further processing is scheduled by this operation.
