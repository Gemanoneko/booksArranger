# Books Arranger v0.5.0: source cleanup safety

2026-10-10. Senua. Focused prototype safety-floor audit of snapshot-backed removal, restoration, catalog retirement, service/API integration and the exact two-book pilot caller. This is not the formal nine-dimension release skill or a claim that live originals have already been removed.

**Verdict:** CLEAR

**ACTUALWRITE:** CLEAR for the two bound completed jobs below, after independent QA GO and deployment of matching accepted source. No other historical cleanup or permanent recovery purge is cleared.

**Open findings:** 0 Critical, 0 Major, 1 Minor (advisory discovery limitation M1). The always-blocking safety floor is intact for the reviewed source and caller.

## Exact source binding

Reviewed `scratch/source-cleanup-2026-10-10/manifest-frozen-2.json`, SHA256 `5666525f9421357fcd69c6f6440c3aba0c476059c0cd35c0cd146df4cb4d8eb9`. Independently recomputed all 32 listed candidate files with zero mismatches. The pins identify runtime, UI, tests, design/UX and both actual pilot/probe callers. This is exact-source certification rather than an unspecified later commit range. The snapshot's version marker is 0.4.4; Sully may change only the accepted release marker to 0.5.0 without altering the reviewed logic.

| Safety-relevant source/caller | SHA256 |
|---|---|
| native_io.py | 9939de63b3448e02f0c664d43242fe46e728a2f4f77ad21ed62f0bf98c7fad44 |
| source_cleanup.py | 926425439f04c52edcca91bc9f3c3bc29b240d9e80c55efb1b44a620ea8e1d49 |
| merge_service.py | 6b424a00db3294bc779b5948e43becd9a5d721dc90b51c7dc347bf8e3136d813 |
| scanner.py | d6152d575442bf6d09f18e590f67c18a9c785d19dfdc622c436bbe101af2f499 |
| groups.py | a124928da0fabd7beee49f26d9f6dc38f9f714f2ee1e13afd0578ba17d8f1b90 |
| review_backend.py | cd1df5b216cff450206697405a149d676aee26524c40a01dddf553aa2eba65e4 |
| audio_jobs.py | ac20d5e1a7941a8ecc633a05f10062254dd14368917280c72b1221f125cd904a |
| web_server.py | e1fca868527af683c3c6b71f9e2bd3d260377540265ae73170464e57ff81f5e0 |
| support/pilot_cleanup.py | 26ec97571c360579b42bdcbf45e3ea0fa6f89e634bcf92518d5c214c71861b15 |
| support/mapped_disposition.py | da4fead3c390a07eee8a88fa9c4ad60147f318294cfb313416984e1e28676d01 |
| support/reconcile_probe_remnants.py | 1bd774e550a406c157c3abc7edae89d6ab8bb89123276591aad04581ae3283d4 |

Design contract SHA256 `50044739a3013aadfae46718d690fe1e76d10c730fec8cb427fc3f38ed207fe7`; separate prior design safety report remains applicable. Source-matched encoding, title-sort and chapter implementation bytes are unchanged by this feature.

## Bound authorization and final guard chain

The initial historical route accepts only MirrorMask job `0b6fedcc-2d95-46a9-a4a3-4192da37ff72` and Snapshot job `dc4874af-e132-47cd-93ab-85e5b0fbeea7`. The actual pilot additionally fixes their candidate identities, eleven/ten selected sources, 114,906,562/243,387,177 source bytes and output SHA256 `fee7f5119803919d9571905f640fad8fce50ca803f528ed5396e124b6dc988d5` / `8fa450ff941c48833c3d4ea7705ec837741dc150b74d251ecc2de38e49d5ea70`. All mutations use the token/origin/shape-validated loopback API; the pilot's SQLite access is read-only. It binds expected live instance/version 0.5.0 and repeats exact finite-batch preflight before admission. Total authorized initial originals: 21 files, 358,293,739 bytes.

Future selected MP3 conversions freeze their cleanup policy into their authoritative manifest. Constructors only recover/enroll recorded intent and never start deletion. Podcasts, ebooks, unselected members, companion/cover files, directories and Eye of God are excluded from this initial route. Output success is durable before cleanup and remains a separate completed audio record after cleanup failures; no error recovery repeats encoding.

Enrollment requires the published complete validation record, matching canonical title/author/audiobook kind/profile, selected decoded source frames and output duration, saved chapter choice and current authoritative review/order/source/cover binding. Output ancestry and the exact current full output hash/size are protected and checked before source removal; the selected cover is separately held/hash-checked. Recovery ancestry is persisted and rebound on restart. A changed output/review/source/cover, unsupported storage operation or filesystem boundary stops cleanup.

All selected source ancestors and native READ/DELETE handles are held before first disposition. Ordinary/reparse, link count, supported attributes, exact native identity versus approved opened-file identity, size, timestamp and full handle-streamed hash are checked. Extra filesystem streams are rejected. No path-only unlink, shell or recursive delete exists. Every selected original has an exclusively created persistent registered recovery copy, metadata restoration and successful held-handle `FlushFileBuffers` plus full hash/size verification before the first native removal. Reused/pending backups are flushed again after metadata updates. Output and recovery handles remain protected across the removal loop. Recovery assets have no expiry/purge path.

Each member receives a durable committed removal intent; under the shared review boundary and a short SQLite writer exclusion the authoritative guard repeats, native disposition applies only to its already verified handle, disposition acknowledgment is committed, then the handle closes and expected-name absence is checked before retirement. No long media copy/hash is performed under that final transaction. Stop completes the current member checkpoint and leaves remaining originals untouched. Unsupported disposition or unexpected retained/replacement names never trigger a weaker delete fallback.

## Crash, restoration and finite worker scope

An early candidate lacked recovery for a crash after successful disposition but before its DB acknowledgment. Fixed: an absent `removal_intended` member is explicitly uncertain and cannot be falsely counted removed; the guarded restore helper includes it. Known `disposition_set` can reconcile with exact backup/output and absent-name evidence. A replacement remains untouched. Every recovery member is verified before destructive work; unknown/corrupt partial backups stop safely.

The early restoration checkpoint gap is also closed: the existing native no-replace publication now exposes a callback after temporary handle/hash/size verification but before rename. Restoration durably records this exact temporary identity/expected destination, then publishes without replacement. A restart accepts an existing restored name only if its native identity, full source hash and timestamp match that owned publication intent. A same-name unrelated file is preserved. Recovery copies survive restoration; restoration never overwrites the completed M4B.

Frozen-1's historical cleanup endpoint could resume unrelated paused audio/cleanup work. Fixed in frozen-2: shared operation admission rejects unrelated pending/running jobs and cleanup, starts only the enrolled cleanup UUID, and disables automatic audio continuation. The cleanup worker enforces that selected-ID set. Resuming historical cleanup likewise avoids unrelated encoding. Pilot preflight independently rejects preexisting queued/running audio work and unrelated pending cleanup; the server gate is authoritative, so a mere client-side check is not the protection.

## Mapped-Z capability evidence

Probe scope was reviewed before execution: fresh random UUID directory under Z:\Audiobooks, exclusively created owner/source/restore fixture names, exact hash/identity checks, handle disposition, no-replace restoration/collision, and only exact hash-bound fixture cleanup plus empty-directory removal. The separate failed-probe reconciler binds precisely two previously created UUIDs, preserves both owner/source facts and hashes in an exclusive fsynced receipt, then rebinds identity/hash before removal. No book file is a probe fixture.

The first native identity attempt failed closed before disposition because mapped Z: did not provide `FileIdInfo128`. The accepted native code permits the standard held-handle 64-bit representation only for explicit unsupported errors 1/50/87, rejects zero/unavailable identity and any arbitrary API failure, tags the representation/error and refuses stored representation/dev/inode drift. This is not a pathname deletion fallback.

Producer `scratch/source-cleanup-2026-10-10/mapped-disposition-receipt.json`, independently measured SHA256 `6b43e5672146383255fd5c66d19cbe957542b4c86d56aeb529f5a174a3b4f5f3`, binds native SHA256 above and fixture UUID `62ef1306-1c1d-41d4-afbd-b091b7ee73a9`. It reports writer denial, exact native removal, byte/timestamp restoration, collision preservation and owned fixture removal all true. Opened Python fstat and protected native facts agree: volume 760290819, inode 11845331232653488920, 4,900 bytes, modified ns 1791638612160628700; representation `BY_HANDLE_FILE_INFORMATION64`, unsupported error 87. Producer provenance additionally binds exact probe script/payload hashes and removal of the three owned probe directories. Senua read these receipts, did not execute the probe; independent QA is separate.

## Catalog, tests and advisory finding

Retirement preserves ordered historical source evidence and completed candidate revision while identifying retired members separately from active input. Saved scan queues distinguish exact retired absence from read failures. Existing/reappearing names always take the normal read path even with identical size/timestamp; successful reads supersede retirement, while failed arrivals remain visible active errors. Ordinary new arrivals are not skipped by generic filename patterns. Restored retirement cannot suppress a genuinely missing file. Recovery/temporary assets use exact registry exclusions; output inspection/status remains separate from removed source provenance. Filters apply before pagination.

Producer frozen-2 reports 13 native/recovery cases, five actual media/service cases, twelve HTTP cases, ten retirement/discovery cases, five finite-admission cases and frontend checks passing. Relevant code/tests include real native disposition/restoration, source writer denial, uncertain deletion restoration, post-rename checkpoint reconciliation, both first/reused flush failures preserving originals, hard-link rejection, changed output/review rejection, exact source hash restoration and retirement/new-arrival regressions. This review inspected tests and mechanisms; Futaba's independent results and live post-deletion evidence remain distinct.

**Minor M1 — exact-path asset exclusion can hide an unrelated replacement.** Scanner recovery/temporary exclusion uses the persistent registry path and kind, without checking current file identity/hash. An unrelated file replacing a formerly registered temporary at that exact UUID-shaped name is still excluded from discovery. There is no destructive operation against that replacement in this cleanup, and source retirement itself does reprocess reappearing names. Log for a later bounded ownership/discovery improvement; it does not block the safety floor or this finite pilot. Persistent recovery hashes are independently verified by the cleanup/restore mechanisms before use.

## Actions, limits and hygiene

Actual write clearance requires independent QA GO, matching deployed runtime/caller pins and freshly checked source/output/recovery/review evidence. It does not assert that 21 live originals have already been removed, that iPhone navigation passed, or that power loss outside the successful supported Windows storage flush contract cannot damage hardware/storage. C: recovery storage and Z: freed bytes must be reported separately.

Senua performed read-only source/receipt/hash inspection and wrote this durable report. No live media/catalog writes, native applications, test or deletion/restore execution, Git mutation, server restart or disposable probes were performed by this reviewer. Existing unique evidence and recovery assets were preserved; there is no owned disposable probe to prune.
