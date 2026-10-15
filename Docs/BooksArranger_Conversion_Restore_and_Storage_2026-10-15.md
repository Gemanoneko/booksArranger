# Conversion restoration, storage and performance — 2026-10-15

This record separates measured results from work still awaiting execution. It does not authorize deletion, assert a new installer exists, or replace the operation receipts.

## Shutdown and performance findings

The installed v0.15.0 process was safely shut down on October 14 at 05:05:10 UTC. Its exact process exited and port/catalog ownership were released. At that checkpoint there were 95 queued jobs, six fully finished books and ten published outputs waiting for original-file cleanup. Protected records and checkpoints were preserved.

Three further outputs had been created, but only one increased the finished counter: two remained held because additional filesystem streams prevented original cleanup. The approved exception for the specific Zone.Identifier marker is now implemented and has passed eleven private native fixtures. Unknown streams continue to be preserved.

One 23-hour audiobook required about 49 minutes: 33 minutes checking/normalizing, 14 encoding and one final verification. Pre-encoding work accounted for approximately 61–69% across three measured books. The October 14 run had already been paused since 01:22 Jerusalem time; the cause of that pause was not established.

## October 15 process restoration

The formerly recorded process PID71064, native creation134365396553924233, was subsequently observed exited with exit code0 and no port5210 listener. Querying that ended process's image failed with Windows error31. Its actual exit cause was not established. This observation must not be presented as proof of a specific shutdown command or crash.

After native ownership, startup-mutex, exclusive-port and catalog-lock checks, one normal Start-menu launch restored the installed app. The old ownership record was retained by a no-replace rename to `data/web-instance.ended-b4581aa9a183687a6a818e2d0317599d.json`. No library or catalog data was removed during restoration.

The restored v0.15.0 process is PID86660, native creation134365553652631105, instance7570a78766426d76420541275cecf134. Its normal Start request was sent once. Although the HTTP reply timed out, subsequent read-only database observations proved automatic and audiobook processing were Running. No duplicate Start was sent.

The latest recorded observation at 17:01:51 UTC showed automatic research Running and audio job19c56029-fe5f-4197-861e-ef35ae4c355a checking sources, after the preceding job advanced. There were eight pending jobs, 26 completed and 89 needing attention. Free space on C was97,467,768,832 bytes. These are checkpoint measurements, not promises about the current state. The old app continued creating additional unsupported-M4B holds, which is why applying the verified replacement remains necessary.

## Storage actually released and storage still retained

Five verified native cleanup batches removed 154 disposable generated files totaling59,306,533,081 bytes. This result applies only to those generated files.

All77 selected legacy compressed source snapshots, totaling29,585,897,364 bytes, passed fresh original-survival and reference checks. The first28 were subsequently removed under a separate fresh native disposal operation, releasing10,688,638,960 bytes; receipt `legacy-snapshot-disposal-01-batch01.json` SHA256 `6e88a387ce088d8e4912cd8b0657846b87cd07a3387af25568d84286325a67a6`. The remaining49 total18,897,258,404 bytes and have not yet been deleted at this checkpoint.

Total confirmed old working-file reclamation is69,995,172,041 bytes. Separately, verified disposable private QA output cleanup released923,016,616 bytes; this must not be added to the old library working-file figure.

Three diagnostic jobs retain six generated checked/compatible outputs totaling1,824,434,254 bytes and three compressed source snapshots totaling909,553,506 bytes: nine files and2,733,987,760 bytes altogether. The new preservation route passed the corresponding three bundled-runtime real-book proofs. Retirement of these old diagnostic files still requires a fresh source-survival/reference assessment and accepted compact evidence; the77-job disposal approvals do not include them. Existing source originals, genuine unfinished-work recovery and published-output cleanup records remain protected.

The read-only survival inventory completed in three bounded batches of28,28 and21. Before calling a snapshot redundant, it established the exact failed parent row, absence of another durable reference or active/unfinished use, unchanged approved original identity and a complete original hash matching the cached snapshot. Inventory results alone do not authorize later deletion after the native handles close: disposal must repeat the live checks while retaining the exact original and snapshot handles.

## Candidate behavior preventing renewed accumulation

The integrated working lifecycle records owned generated files before creation and retires disposable output at terminal boundaries while retaining required source/recovery evidence. Published-snapshot retirement is separate from original-file replacement and requires its own checked publication proof.

The AAC M4B metadata-preservation path writes one candidate in the existing `checked.m4b` role. It preserves original audio/video/chapter track bytes and refuses unsupported structures. All three representative books passed complete bundled-FFmpeg8.1.3 audio, chapter and retained-byte checks without changing the original sources. This does not establish eligibility for every old failed book.

Narrow repair admission creates one new child attempt for an eligible unchanged failed parent and keeps the old history. It refuses to clone an original while the parent's legacy compressed-input debt remains. Thus old cache must first be safely retired or independently proven reusable; repair admission must not accumulate another copy behind retained legacy snapshots.

There is no universal two-times space guarantee. Staging can require an immutable source snapshot plus a candidate; cross-volume publication may add another compressed temporary copy while the original remains. Existing copy-space estimation remains conservative. No full-library pre-copy or indefinite terminal generated-output retention is intended.

The Z Audiobooks source and C recovery folder were observed on distinct NTFS volumes. Recovery therefore cannot be described as an atomic same-volume rename. The known-marker exception removes only the exact bounded, recognized Zone.Identifier stream after durable marker-byte evidence and current original/review proof. Unknown streams refuse cleanup; normal source identity/hash/recovery checks and a late stream check remain. It does not establish atomic exclusion of every possible newly arriving stream during the pre-existing cross-volume cleanup window.

## Release and application state

Version0.16.0 source is being saved through Sully. Full integrated graph04 passed366 Python cases,29 Node cases, seven frontend scripts and six syntax checks. Native root102796 exited0 with active descendants0; the outer operation exited0 and all descendants closed at17:43:25 UTC. Python execution took455.668 seconds, and the native operation474.373 seconds. Graph04 entry SHA256 `7368930e611db2475613afc4ff53f80a6f6bd847b0d3b157899da389fdab4546`; manifest SHA256 `bbec5710831705d9c50f86c978b735d2d24e88ef1162cb44abf8304aeb2884f9`.

Zone graph02 separately passed all eleven native cases with no skips; focused regression separately passed six corrected cases, seven frontend scripts and six syntax checks. The three real-book bundled8.1.3 proofs remain valid because their core/pipeline/runtime bytes are unchanged. Failed earlier preparation/runner/fixture attempts remain documented honestly. No Windows installer or installation is claimed by these source-test results.

Once the replacement is built and independently verified, application should use a normal checkpoint pause if necessary, preserve the existing catalog and queues, verify old process/port/catalog release, and start the verified replacement against that same catalog. No live source hotpatch or unverified install is authorized by a successful source test alone. The automatic continuation heartbeat remains paused.
