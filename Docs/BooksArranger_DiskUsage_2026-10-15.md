# Books Arranger local disk attribution — 2026-10-15

Owner: Ender. Read-only inventory for Sergei's report that roughly 100 GB disappeared. No deletion, cleanup execution, source processing or catalog access was performed by this inventory.

## Finding

The main local consumer is conversion working storage, not the 24-hour original-track recovery folder: data/merge-cache contains **98,030,554,184 logical bytes (98.03 GB / 91.30 GiB)**. Source and replacement recovery together contain 6,016,058,303 bytes (6.02 GB / 5.60 GiB). These current totals plausibly account for the reported space, but are not a historical before/after growth measurement or proof of reclaimable capacity.

## Method and exact scope

Measured 2026-10-15T09:15:22.183Z through 2026-10-15T09:15:42.048Z (12:15 Asia/Jerusalem). Direct node:fs/promises lstat/readdir ordinary-file metadata reads, bounded at 30,000 entries per root; each listed root completed without reported errors or symbolic links. .git entries were excluded. Logical st_size bytes were summed; hard links were not deduplicated, allocation/compression/sparse-file size and alternate streams were not measured. No symbolic links or junctions identified by lstat were followed. This is not a full native reparse audit or an atomic snapshot; concurrent changes can alter later totals.

Paths in the following table are relative to C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/. No Z:/Y: or real source libraries were traversed. The catalog, journal, locks and app ownership JSON were not opened by this owner. No Books modules/checkers/plans were imported or executed, no blocked operation was retried through another route, and no hooks/trust/settings were changed.

| Relative root | Files | Logical bytes | Decimal GB |
| --- | ---: | ---: | ---: |
| data/merge-cache | 5235 | 98030554184 | 98.031 |
| data/source-recovery | 37 | 2115856369 | 2.116 |
| data/replacement-recovery | 3 | 3900201934 | 3.900 |
| data/chapter-repairs | 25 | 185823 | 0.000 |
| scratch/electron-2026-10-13/worktree/build-cache | 1806 | 774457979 | 0.774 |
| scratch/electron-2026-10-13/worktree/dist | 201 | 751803969 | 0.752 |

Total across these six non-overlapping roots: 105,573,060,258 bytes (105.57 GB / 98.32 GiB). Other scratch roots, candidate node_modules/source, the catalog, installed runtime and the remainder of C: were outside this bounded inventory. No claim that all Books-related space was measured.

C: statfs available blocks multiplied by block size reported 52,138,962,944 available bytes (52.14 GB / 48.56 GiB). This is a point observation, not a guarantee that the next conversion fits.

## Working-copy attribution

merge-cache contains audio-staging and covers. The observed working audio split is:

| Role inferred from producer code and exact filename | Files | Logical bytes |
| --- | ---: | ---: |
| sourceNNNNN source snapshots (.m4b/.mp3) | 432 | 36,472,415,109 |
| checked.m4b — encoded/checked candidate | 80 | 30,565,483,388 |
| compatible.m4b — chapter/sort compatibility remux | 80 | 30,565,483,947 |
| Other covers, markers and evidence | 4,643 | 427,171,740 |

The 376 M4B files comprise 216 source snapshots plus 80 checked and 80 compatible files; they do not mean 376 converted books. There were 216 MP3 snapshots and **zero WAV files** in this scoped current merge-cache. The historical 136-WAV/119,317,276,892-byte cleanup scope is not a current reclaim estimate and must not be re-applied to these files.

104 audio-staging job directories contain 106 attempt directories; only two jobs have more than one attempt directory. Each of the 104 bounded ordinary ownership.json staging manifests parsed and matched its parent job ID and embedded manifest job ID. This is a static naming/content check, not live native ownership or catalog membership proof. 100 manifests enable original-track cleanup and four do not declare that policy. Profiles: 99 automatic v4, four v3 and one v1.

Static audio_pipeline.py shows source snapshots are protected private copies, checked.m4b is generated, and compatible.m4b is a separate remux for chapters/sort-title compatibility. Up to three sizable copies can therefore exist for one input audiobook. The biggest observed job is 578056ef-a81c-4762-a88e-0fa2df6c6315 at 7,216,833,410 bytes, including one approximately 2.406 GB source and two approximately 2.405 GB generated copies. The next two largest jobs are 9a38e7e5-a4cf-4a54-9db4-11587236ac3a (4,081,833,430 bytes) and b3627cdd-01f9-465d-8c28-f29774b5820a (2,892,751,354 bytes).

File metadata alone does not establish which of these jobs are published, pending, held, historical, failed or currently useful. The reported six fully finished books / ten published outputs are a different lifecycle counter and cannot be matched against 104 staging jobs without a supported current app/catalog receipt. The two reported stream-held outputs may explain some retained files, but do not establish the reason for all 80 generated pairs. No bulk disposal conclusion follows.

## Recovery and age

source-recovery: 37 files / 2,115,856,369 bytes, inside 20 child directories. Their mtime range is 2017-02-02 through 2024-09-13 because recovery preserves original-track timestamps; these dates do not mean the copies have been kept since those years. Exactly 24 elapsed hours starts at durable successful original-removal completion, not mtime or directory age. No eligibility calculation was performed against the live catalog.

replacement-recovery: three M4B files / 3,900,201,934 bytes in one child directory. These are a separate former-output recovery category; the source-recovery 24-hour rule does not by itself authorize their removal. They remain protected until exact replacement-retirement receipts and applicable policy are checked.

chapter-repairs is only 185,823 bytes of retained evidence, not a large audio consumer. Candidate build-cache and dist together are 1,526,261,948 bytes (1.53 GB), unchanged from the earlier inventory. Retain the older build until a replacement is built and verified as instructed by Sergei.

## Safe cleanup path and limits

Current merge_service.py calls _prune_working after durable publication. storage_cleanup.working_files selects only exact published-attempt non-snapshot producer receipts, protects/revalidates the final output, and requires matching job/manifest, hashes/sizes, native identity, single stream and hard-link restrictions. In principle, the 61.13 GB of checked/compatible names deserves receipt-based examination first; **61.13 GB is not a certified reclaimable amount**. Unknown attempts, missing producer receipts and changed/unsupported native facts stay preserved. Snapshot names are deliberately excluded from that publication-only path.

Full staging cleanup separately requires exact completed original-retirement correspondence, or unchanged retained originals when retirement is disabled. A held original cleanup can legitimately retain snapshots. The source-recovery retention worker checks at startup/periodically only while the app runs and admission is idle: scanning, active or queued audio jobs, ongoing source cleanup/restoration, closing, changed output/recovery identity or incomplete evidence defer/preserve. A resumed busy queue can therefore defer expiry even when 24 hours have elapsed.

Next safe investigation is supported app/status or a separately reviewed bounded catalog snapshot to correlate the 104 job IDs with publication and exact cleanup failure receipts. Then plan and independently review a literal receipt-based cleanup operation for eligible generated copies. Do not turn this inventory into recursive folder deletion, reset jobs, weaken stream checks, remove snapshots/recovery by age, or conflate expired eligibility with verified disposition. The approved Zone.Identifier-only exception is still unimplemented and is not bypassed here.

## Handoff

Actual files removed: **0**. Actual reclaimed bytes: **0**. Cleanup is incomplete. No probes/exports/caches were created by this inventory; only this intentional Docs record was written. Originals, recovery sets, evidence, old builds and other chats' work remain preserved. This report is for Senua's bounded static review and Sully's explicit-file save/push; no code, version bump, release or native operation is authorized by the report.

## User-authorized cleanup continuation — 2026-10-15

Sergei subsequently explicitly authorized checking which working files are redundant and safely deleting only those, preserving unfinished conversion and recovery data, and getting the app converting again. This authorization does not make the earlier inventory a deletion plan.

Static route review found no isolated working-only HTTP endpoint. /api/audiobook/cleanup starts historical source cleanup; merge.resume includes broader postprocessing. External live-catalog disposal is not admitted while the installed app owns the catalog. Senua confirmed no concurrent external cleanup clearance. No new endpoint, product code, shutdown, deletion helper or external database operation was introduced. Normal app-owned automatic Start is handled separately by Ender app-resume owner; its built-in _prune_working may process eligible completed jobs under app ownership.

Post-Start metadata remeasurement at 2026-10-15T09:24:01.743Z–09:24:02.770Z found merge-cache unchanged: 5,235 ordinary files / 98,030,554,184 bytes, including unchanged 432 snapshots and 80 each checked/compatible M4Bs. No links or metadata errors observed. C: available was 51,720,081,408 bytes (51.72 GB); the change from the earlier free-space point is not attributed to Books by this inventory. These metadata observations are not proof of publication, eligibility or a cleanup receipt. Current app-owned status/cleanup diagnostics remain pending. No files removed by this owner; no reclaimed capacity claimed.

### Completed-job receipt correlation and actual outcome

Senua cleared exactly one bounded native read-only snapshot helper, scratch/resume-2026-10-15/cleanup-receipts-readonly.py SHA-256 eee7b6f8552ad14d03e7c8fe04185ecde9c23c72008336012f05582e2a5c580d. The approved command ran once with C:/Python314/python.exe -I -B and returned exit 0. It retained 41 canonical source pins/native read handles, exact live owner checks, a 45-second hard process deadline, SQLite mode=ro/query_only, one-second busy timeout, query progress deadline and row/output limits. No application constructor, media validation/hash, external mutation or child process ran.

At 2026-10-15T09:26:56.211148Z, the exact installed v0.15.0 owner remained PID 54960 / instance 721b890bb723a4b3d22fffb3edf35f1c. Current durable audio states were **22 completed, 81 needs attention, eight pending and one running**. This establishes resumed conversion, superseding the earlier paused observation. UI projections/aggregate failure counts use different definitions and need not equal these raw job states.

The query returned twelve completed storage-cleanup job rows, no recent storage_cleanup_errors rows, and only removed states among all grouped storage_cleanup_files receipts. The newest returned disposition timestamps were historical October 14; they do not prove any bytes reclaimed in this session. Completed publication summaries bound each job to manifest hash, output hash/size, validation status and published-attempt generated-file producer receipts where present. Three legacy completed rows lacked attempt receipts and were not treated as disposable.

At 2026-10-15T09:27:19.061Z, a separate bounded ordinary-file metadata traversal matched every remaining checked.m4b/compatible.m4b parent job ID against those 22 exact completed IDs. **All 160 generated files (61,130,967,335 bytes across 80 jobs) were outside the completed-ID set; zero completed-job generated files remained.** These are non-atomic read-only observations and do not certify native disposal identity. They do establish that the large generated-file set cannot be called redundant completed-book leftovers: it belongs to unfinished/attention jobs and must be preserved under Sergei's instruction.

Derived correlation evidence is scratch/resume-2026-10-15/completed-generated-intersection-20261015.json; the full native query JSON remains in the tool transcript. Preserve the helper and this correlation as unresolved evidence. No deletion operation was proposed or cleared, since this scoped check found no completed generated-audio leftovers to apply it to. Source snapshots, failed/pending/running attempts, original/replacement recovery and originals remain untouched. This does not certify every small leftover or every scratch subtree disposable. Actual files deleted/reclaimed by this continuation: **0 / 0 bytes**. The app remains running; no stop/restart loop or heartbeat change was performed.

### Final source-snapshot classification and preservation reason

Parent authorized one final narrow read-only query to distinguish source cleanup holds from potential redundant snapshots. Senua cleared source-cleanup-reasons-readonly.py SHA-256 f30df28b6cce37d2aa6214dedeb5320c88385144453e0f4a96fb67fbb2cb3a1d under the same exact-owner/native-source-pin/deadline/query-only constraints. The literal pinned Python command ran once, exit 0, observed 2026-10-15T09:29:13.126719Z. Its raw output is preserved as scratch/resume-2026-10-15/source-cleanup-reasons-20261015.json. No source-library paths or media were opened.

The prior metadata snapshot at 09:28:13.488Z contained 433 source snapshots / 37,086,692,825 bytes. It grew by one 614,277,716-byte source file compared with 09:15; resumed processing makes the earlier 98.03 GB total a historical point observation. Joining those exact parent job IDs with the 09:29 state query gives:

| Saved job state | Source snapshot files | Logical bytes | Retain reason |
| --- | ---: | ---: | --- |
| Needs attention | 80 | 30,495,450,870 | Unfinished jobs; preserve retry/recovery inputs. |
| Pending | 135 | 1,042,273,318 | Queued conversion input copies. |
| Running | 2 | 1,228,555,432 | Active job a0030d08-ff99-42c2-9aca-e58be379f179. |
| Completed | 216 | 4,320,413,205 | All ten jobs have incomplete original retirement with the explicit stream hold below. |
| Unknown | 0 | 0 | No unmatched snapshot parent IDs in this join. |

For **all ten** completed jobs with remaining MP3 snapshots, the current durable source_cleanup state is needs_attention with reason **“Additional filesystem streams require review; original retained”**. These ten lack completed full-storage-cleanup receipts and have no removed original-retirement rows in this query. Publication-only working_files explicitly excludes snapshots; full staging cleanup requires completed exact retirement correspondence for these enrolled jobs. Therefore the 4.32 GB is protected under the current cleanup contract, not established safely redundant. No ADS contents were read, no Zone.Identifier exception implemented and no original retirement attempted.

The same later job-state query classifies **all 160 generated M4B files / 61,130,967,335 bytes / 80 jobs as needs attention**, with no completed or unknown generated-file jobs. This sharpens the earlier completed-ID intersection without changing preservation. The derived evidence file now includes exact snapshot and generated-file mappings and query timestamps. Queries and filesystem metadata were observed at separate moments while the app worked; no atomic snapshot or native eligibility claim is made.

Final bounded outcome: the large retained files are accounted for by unfinished conversion attempts and ten stream-held source-retirement sets. **No currently safe disposal candidate was certified in this scope; zero files deleted and zero bytes reclaimed.** The user-authorized cleanup check is complete within this scope; cleanup itself is not claimed complete. The existing app is running with a durable running job; failed/attention jobs remain preserved for their separate repair rather than being silently reset or discarded. No further external cleanup/app changes are planned by this owner.
