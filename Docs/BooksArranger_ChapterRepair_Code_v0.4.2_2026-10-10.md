# Books Arranger v0.4.2: focused chapter preservation safety

Date: 2026-10-10, Asia/Jerusalem. Senua. Bounded prototype safety-floor audit of new source-track chapter defaults and the explicit marker-only repair helper. The design conditions are committed at `d0bdb41`; full formal release and unchanged native/platform review are excluded.

**Current safety floor:** CLEAR for frozen-3, including its actual one-off pilot caller. **Current open findings:** 0 Critical, 0 Major, 0 Minor. Initial frozen-1 source findings and the former caller-inspection condition are preserved below; the final sections close them for exact44-file pins.

## Exact source binding

Immutable source `scratch/chapter-preservation-2026-10-10/frozen-1/`,43-file manifest SHA256 `c987b83a347ede29280d34ec203bfe7ed815559aba97262b0499d2ef697483b8`. Independently recomputed43/43 matching hashes. This binds candidate bytes, not an unspecified subsequent working tree or release commit range.

| Changed safety-relevant source | SHA256 |
|---|---|
| chapter_plan.py | a164d4e79d3ff78660fdea65d28bb0268d8632948baca4395cd1908695b1ba24 |
| chapter_repair.py | baf3eb7d2625e7b87b5e15b557b198d31c7240fcad5b3e997e03a4875134f7bb |
| audio_pipeline.py | f5fbf35bef7d320f3d1a09f2e30341ba794c181873388e1fdff7dd605de6bb65 |
| review_backend.py | 3ed43a7560bd7e8f4bdc55ee0e888d9c734da5159db5f236d2908358fbfbfdc4 |
| web/app.js | 43535f1604aeb8cf34796afff73cd9e783cd21d8b0fdb153387d0277ffc50fdf |
| web/index.html | 14ca696c8c5255f5d5cdb5d69f5fd95d03a2cf856b6e73ce96900aac92353898 |

Native no-replace/directory/file/process guards, the accepted queue and source-matched encoding policy are unchanged. No reparse/Z:/native experiment was repeated.

## Core repair boundary inspected

The helper requires a completed parent, binds the existing M4B to its recorded expected hash/size and derives exactly one distinct `- Chapters.m4b` destination. It checks ordered source paths/hashes against the boundary proof, positive integer44.1k PCM counts, bounded marker labels and total duration against the validated parent. Source content fingerprints/hashes and the caller's review guard are checked before staging and repeated by accepted publication. The old artifact is held under directory and deny-write/delete file protection through repair/publication, copied exclusively into an owned UUID stage and verified again. No in-place parent/source edit or audio re-encode is used.

Presentation validation fingerprints the protected parent's AAC stream/extradata, every packet's payload hash/boundary/timestamps/flags/side data, and the whole decoded PCM byte hash/frame count. The repaired output must match that complete receipt, including start/timebase/duration/delay evidence; duration alone cannot pass. Stream copy uses file-only MOV input, argument arrays, owned suspended/job-assigned process execution and overwrite-disabled output. Selected cover bytes and original canonical/additional global tags are compared, except explicit container implementation tags. QuickTime marker names/count/start/end are checked against the escaped millisecond plan with1ms tolerance. Exact source frames/proof identity are preserved; TrackNN fallbacks do not assert literary chapter names.

Private validation includes the final output's hash/size. Accepted publication copies to an exclusive owned destination temporary and uses the existing held-file hash/size check plus same-parent no-replace rename. A collision, source/cover/review drift, unsupported boundary or presentation mismatch stops safely. Parent hashes/files remain untouched.

The distinct fsynced append-only JSONL journal records intent, parent job/artifact/manifest hash, chapter proof hash, sources/cover/revision, expected destination and validation. Publication intent is durable before rename; the completed receipt remains associated with its original parent without rewriting that parent job. Recovery accepts only an owned journal's matching job association, derived corrected destination, durable publication event, current source/review guard and exact parent/corrected/cover hashes. It returns a receipt, does not overwrite/retry or adopt a file merely because its name exists. An unreadable/truncated/oversize journal fails closed.

## Caller integration boundary before the real invocation

`restore` and `recover` deliberately accept explicit `review_guard` callbacks, with `restore` also accepting `review_lock`; they have no public HTTP repair route. The supplied synthetic fixture uses `lambda: True`, which tests the helper but is not the actual pilot's catalog authorization. The existing creation guard cannot substitute unchanged: it rejects the now-occupied canonical destination and compares the current encoder profile to a historical completed parent.

Ender's actual caller plan reads the authoritative completed-parent/current review/source rows and uses a bounded SQLite BEGIN IMMEDIATE boundary for the final catalog revision/evidence check plus native publication. That actual caller must be frozen/read before the real repair invocation; it must bind the parent record, current candidate/context source order/cover/review and original boundary-evidence hash, and must register the returned corrected artifact as owned so scanning does not treat it as a new source book. This missing invocation-end inspection is a concrete contract handoff, not a new user approval, general architecture rewrite or native-platform re-test. Helper source publication can proceed after QA; the real write still needs the actual guard/caller receipt.

## Future source-track defaults

The new plan derives names from genuine per-track title tags, excluding repeated whole-book album labels, and uses source numbers only when unambiguous; otherwise fallback labels follow the reviewed included order. Introductions, including source track0, are retained. Defaulting on applies to multi-MP3 candidates with readable known durations. A persisted explicit false remains false and does not become an implicit approval. Frontend defaults mark track review dirty, and server `tracks` persists the exact boolean/order/membership choice with source hashes. `build_manifest` emits names only for the accepted saved choice, and existing revision/source guards still bind creation. Actual decoded source durations and PCM frame counts are now durable in job/output validation evidence.

## Findings, evidence and disposition

**Minor M1:** unrelated error/helper labels in `audio_pipeline.py` and `review_backend.py` acquired mojibake `вЂ”` in place of the em dash while this candidate was prepared. This is readability/doc-copy drift; canonical source tag strings and FFmetadata writing remain UTF-8. Sent to Ender for a bounded correction; it does not block the safety floor.

Senua read source/diffs/call boundaries and verified43 hashes and the existing40-source boundary proof arithmetic. Parent reports five plan tests, two API/actual AAC-repair fixtures and JS VM checks passing; those are producer results, with independent QA separate. The synthetic repair preserves different beginning/end tones, exact compressed/decode presentation, original parent/source hashes, escaped Cyrillic chapter titles, collision behavior and owned-intent recovery. Senua did not run these file-writing tests. No encoder/provider/probe/native/browser run, library/catalog/server action, git mutation or disposable artifact occurred in this review.

**Helper/source safety floor:** CLEAR for the exact43-file pins.

**Open findings:** 0 Critical, 0 Major, 1 Minor. **Actual pilot invocation guard/caller inspection:** pending. This is not a full release clearance or a claim of corrected iPhone navigation. Previous blocked/native design evidence is preserved separately; no original book was changed by this reviewer.

## Frozen-2: actual caller and copy correction

Immutable source `scratch/chapter-preservation-2026-10-10/frozen-2/`,44-file manifest SHA256 `eb152400dd88e43fd3ec9e41b303da9a05112c494642ad046710df21e9dc4705`. Independently recomputed44/44 matching hashes. The helper, chapter plan, frontend, encoding policy, queue and native guards carry forward unchanged. Differences from frozen-1:

| Corrected/added source | SHA256 |
|---|---|
| audio_pipeline.py | a5741b384b5fbafdc3983f738391fd63a8c8e584c7eaf658740caf4b19d840f5 |
| review_backend.py | 778736cad2276a4b9f7845e26799b62763d046d31ac9dd11fd0e601028c044d0 |
| support/repair_runner.py | 5baf4c56fa2ab6a181bbfabc68a253a0f9ec5b8dc2dc5caaaf6a656785b6fc0c |

Minor M1 is closed: the two Python files restore the proper UTF-8 dash and the affected Russian-language alias `русский`; the source/hash/review/publication logic is unchanged. No new incidental metadata encoding transformation was introduced.

The frozen caller is an explicit one-off Eye of God correction, not a general public repair API. Its constants bind original job `9e04e700-ecf8-4807-8195-01a7a1d73bd6`, exact boundary-file SHA256 `535fc85f08405a90c3305a5d9923831e8593c16344156232f9e7af7dc8e79db1` and validated original output SHA256 `59f1527a05f1115f36e80473d0b94127612cd3ca6ad1b1e293f2aa0d68d61ff7`. The database and proof/output paths are fixed owned task paths, with corrected audiobook destination derived by the helper from that recorded parent. No command-line arbitrary path/job/executable is accepted; execution requires the literal `--execute` option.

Preparation reads the authoritative completed job and captures its manifest/hash/state/output plus current candidate revision/fingerprint/evidence/review and context revision/data. It requires current revision equal to the completed manifest, unchanged group, approved metadata/source coverage/order, exact canonical metadata, selected source order, accepted source hashes/size/mtime and selected cover ID. The helper separately verifies current physical parent/source/cover hashes and exact boundary order/duration. Thus the actual guard is not the fixture's always-true callback and does not rely on the incompatible ordinary creation guard.

The guard rechecks the fixed boundary-file hash and all captured catalog rows. At the final publication boundary the actual context manager opens a short SQLite `BEGIN IMMEDIATE`, rechecks those rows, holds the writer exclusion while the helper repeats its guard and performs native publication, then rolls back/closes without catalog edits. The separate read-only guard connection can read the expected rows while the database writer exclusion prevents a concurrent review change. Source/parent/native handles and hash guards are those already reviewed. No transaction is held over audio copying, presentation decoding or earlier validation.

The caller records the returned receipt through exclusive creation at the fixed owned evidence path. The helper's fsynced append-only journal remains the authoritative corrected-artifact association to the original parent, including pre-publication intent and exact expected bytes; original job/output/catalog records are not rewritten. This one-off caller deliberately does not integrate the correction into `owned_artifacts` or app UI selection. That is a disclosed catalog/scan-association limitation, not an unsafe write or a reason to invent a schema feature for the authorized marker-only file repair. Keep the journal/receipt for subsequent registration or inspection; do not claim that the app has selected the corrected file automatically.

Read-only caller inspection and exact diffs found no unsafe publication bypass, arbitrary destination, re-encode or original overwrite. Parent reports read-only live preparation passed; QA's targeted actual caller check is separate. Senua did not execute preparation/repair, touch the live database/server, or run any new native/platform/codec experiment.

**Frozen-2 helper and actual caller safety floor:** CLEAR

**Current open findings:** 0 Critical, 0 Major, 0 Minor. This supports the already-authorized distinct-output technical repair after accepted source deployment and QA GO, using the exact frozen caller and matching deployed helper dependencies. It does not assert that the real corrected file or iPhone chapter navigation has passed. No original files, repository git state, user process or disposable probe were changed by Senua.

## Final caller connection-lifetime repin

Immutable `scratch/chapter-preservation-2026-10-10/frozen-3/`,44-file manifest SHA256 `cd17f89a0dbc5b6c0b04d59c2f95c666e5013f654292d560baa4fd178aa4f828`: independently verified44/44 matching hashes. Only `support/repair_runner.py` differs from frozen-2, now SHA256 `cd6cb6156bdaf19e29633379f705a763b1370ad2f17a63c7e6504e548816f0fa`. Its two read-only preparation/guard connections now use `contextlib.closing` so the underlying SQLite handles are explicitly closed after each read. The final BEGIN IMMEDIATE/rollback boundary already closed its connection and is unchanged. All helper, source/review/proof bindings, destination derivation, native publication, frontend and presentation checks are unchanged. No further test, native experiment or live operation was performed during this read-only diff check.

**Final frozen-3 safety floor:** CLEAR

**Current open findings:** 0 Critical, 0 Major, 0 Minor. The accepted invocation is the final frozen caller above with matching deployed helper pins, after QA GO. The distinct correction remains associated through the append-only journal/receipt; automatic app/scan registration is not claimed. This is the current exact source binding for the authorized technical repair.
