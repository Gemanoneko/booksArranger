# Books Arranger actual source cleanup QA — v0.5.0 — 2026-10-10

**Verdict: GO — exact two-book cleanup postconditions verified read-only.** Ender performed the authorized removal; QA neither enrolled nor resumed any job, deleted any source, nor altered library or recovery content.

| Book | Job ID | Cleanup ID | Confirmed originals removed / verified recovery copies | Recovery bytes |
| --- | --- | --- | ---: | ---: |
| MirrorMask | 0b6fedcc-2d95-46a9-a4a3-4192da37ff72 | eafb1b0b-82e4-445d-9273-0fb54911f21f | 11 / 11 | 114,906,562 |
| Snapshot | dc4874af-e132-47cd-93ab-85e5b0fbeea7 | 0b7cf961-85c6-43a0-879a-0e6c75b414a5 | 10 / 10 | 243,387,177 |

Total: **21 confirmed original names absent, 358,293,739 bytes retained in persistent C: recovery**. For every original, QA checked the authoritative `cleanup_members` removed state and matching `source_retirements` hash against its immutable original manifest. Absence alone was not counted as success. Every recovery file was independently streamed in full; SHA256, byte count and nanosecond modified timestamp match that original. Opened-file identity/size/timestamp stayed stable across each read. Recovery directories are `data/source-recovery/[cleanup ID]` under the tool. All recovery content remains intact; no purge was performed or promised.

Both completed outputs were independently streamed in full and remain unchanged:

| Actual output | Bytes | SHA256 |
| --- | ---: | --- |
| `Z:\Audiobooks\Gaiman Neil\MirrorMask - Gaiman Neil.m4b` | 117,288,173 | fee7f5119803919d9571905f640fad8fce50ca803f528ed5396e124b6dc988d5 |
| `Z:\Audiobooks\Sanderson Brandon\Snapshot - Sanderson Brandon.m4b` | 254,315,402 | 8fa450ff941c48833c3d4ea7705ec837741dc150b74d251ecc2de38e49d5ea70 |

Their selected cached covers still match the approved cover hashes. Snapshot's remaining source-folder JPEG (`Брендон Сандерс - Стоп-кадр.jpg`, 106,988 bytes) was independently hashed: `bca7ca57a9d477bd2b19c8813e0be2fb0b3fac0b3266115b9ad036148e109b67`, identical to the selected artwork. Source directories remain; the cleanup member set contains only the 21 approved MP3 paths, never JPEGs, source folders, outputs, companions, podcasts or ebooks. No unrelated cleanup enrollment appears in the read-only catalogue.

The original caller's title search could not locate source-clue names after enrollment. MirrorMask's worker completed despite that monitor failure. QA independently verified its settled cleanup before any further operation. The corrected scratch-only caller SHA256 `246031bdb5c2865c43a972fcf2244ecff653238af00b5f9b41fe52dd321e0176` was read-reviewed: the original pinned finite admission and guarded opaque-job API action remain; exact authoritative job/candidate/cleanup intent IDs replace title search. Completed MirrorMask is skipped only after exact manifest/output/member/count correspondence; an incomplete prior cleanup refuses reenrollment. Read-only helper evaluation established MirrorMask completed and Snapshot unenrolled before Ender's subsequent run. QA never executed the mutating caller.

Current GET-only runtime receipt: v0.5.0, PID 55876, instance `23a8d2f9c79c979558e614b4749eeb16`, port 5210, `closing=false`. Audio jobs: three completed, zero queued, zero failed; cleanup inactive. Scanner pending zero, retained generation 4 catalogue count 9,550 and one existing unresolved read error. No scan was triggered. The existing UI/device claims were not retested or inferred from these filesystem postconditions.

## Evidence and limitations

- Immutable pre-cleanup batch manifests: `scratch/next-batch-2026-10-10/completed-proof.json`, SHA256 `89d248ccb87c20f9ad01accca0b99e634d1ccc89b3d819ace2e91498b9f3eb5e`.
- Independent exact per-file hashes, timestamps and dispositions: `scratch/source-cleanup-qa-2026-10-10/postconditions-MirrorMask.json` and `postconditions-Snapshot.json`.
- Caller review: `corrected-caller-audit.json`; retained artwork: `retained-jpeg.json`; live GET state: `postcleanup-health.json`, in the same QA scratch folder. `postconditions.py` records the read-only method.
- MirrorMask settled API record: `scratch/source-cleanup-2026-10-10/mirrormask-api-settled.json`, SHA256 `92d72e87e62c01a1267d0f322eb528483a9c4773a36320478e694bba3e308c81`.

No Blocker/Major/Minor postcondition discrepancy. Pattern disposition: fix title-based operation monitoring through exact authoritative IDs, verify correction, preserve the initial failure record; never duplicate removal merely because a monitor fails. Recorded bytes are verified original data removed from Z: and retained in C: recovery, not a measured filesystem free-space increase. Earlier artifact QA established tags/chapters/covers; no redundant full audio decode was performed. Actual iTunes import/sorting/sync and iPhone playback for these two files remain untested; external publisher completeness remains unknown.

All owned commands exited, read-only SQLite connections/file handles closed. QA created only compact workspace evidence/report files; no temporary media or browser lease was needed for this postcondition pass. Persistent recovery, journals, original provenance and unique evidence were preserved. Existing frozen implementation QA report was not edited.
