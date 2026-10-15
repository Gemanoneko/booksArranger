# Working lifecycle component: native private QA

Status: component PASS; source checkpoint only, not installed or release approved. Maintenance base b67dd0a962ab359a93501bb8897e54a4bf33fc32 plus the six explicit files below.

At 2026-10-15 13:16:40 UTC, lifecycle-qa-02 actually ran 27 tests: 27 passed, zero errors/failures/skips. Five fixed Python fixture producers were admitted. The private Windows Job root PID95692 exited 0; active_after=0, owned_job_returned_after_native_finally=true. Native elapsed 41,548 ms; test elapsed 22.722 s; parent observed actual supervisor exit 0 and final all_owned_descendants_closed=true. Native result SHA256 690253994b039c9ee35e7f4ff8a2bc8176181b8d232bea488971d24004b00eda at scratch/resume-2026-10-15/lifecycle-qa-02/output/lifecycle-27-unittest/native-result.json.

The earlier lifecycle-qa-01 ran 27 tests with 26 passing and one teardown error. Its contention test used sqlite3.Connection as a transaction context without explicitly closing it, leaving inventory.sqlite3 open on Windows. QA02 wraps that fixture connection in contextlib.closing; product code did not change for this error. QA01 evidence and lease are preserved; it was not replayed.

## Verified component behavior

Durable per-attempt producer intents and captured native identities cover failure/cancel/timeout; exact redundant generated files are retired after producer closure. Source snapshots retire only when frozen originals can be restaged; unavailable or changed inputs and unresolved identities remain protected. Another attempt cannot create another snapshot while prior cleanup debt remains. Compact bounded diagnostic bytes and semantic probe facts are saved before scratch disposal; unknown references, aliases, streams, junctions, newer attempts and publication intents refuse disposal. Interrupted disposition reconciles exact captured identities without adopting replacements.

Actual private fixtures exercised three failed/retried producers without cumulative generated audio, cancellation, nonempty timeout output, hardlink/ADS/junction refusal, crash receipts, cross-job references, failed capture, and published generated-role cleanup despite an original stream hold. A concurrent BEGIN IMMEDIATE during native hashing proved no SQLite write transaction spans that IO; actual resume preempted an unrelated background hash without a global lock wait. Reconciliation handles one relevant attempt per idle tick, not a full-library hash sweep. Fixtures use synthetic bytes; this is not codec/publication correctness QA.

## Immutable operation

Exact command: Python314/python.exe -I -S -B scratch/resume-2026-10-15/lifecycle-qa-02/focused-unittest-entry.py, from the Studio root (full literal in the capsule EXECUTION-PLAN.md). Entry 1b35f8edce9e423c79a761bfc9f3716719b0ca150f0ad27ea41feb1b78bf4723; manifest b8fdbef2a80c956751d0d40b6c59bbee69f0eb6c65e4f8c8d8e970ce9d72a25e; review-manifest 75298c80cdc22003b1b8c9fe04ee3e0cd6a64767685230e7def3dce773d02e0d. Complete runtime/input holds and source/import/private-write fences reused the accepted ceec native owner with a cumulative 600000 ms deadline, bounded drains, retained descendant closure and postflight. All mutations were private fixtures; no installed app, real catalog/original library, codec, browser, hook or packaging operation ran.

## Exact source checkpoint

| File | SHA256 |
|---|---|
| working_lifecycle.py | af602d2c2fa76ee126b864f6165f5d15ccb0c4a74abbb35cfab64785d3529103 |
| audio_pipeline.py | 8d7e1aa39fc321a87ce79cdacee97ad5b6a76c3de1cc2df3223299ea44c2fa60 |
| audio_jobs.py | 3dc5aba909fc110316cc166d4f4273817b7f2cae749762f6a1f6ac8794201fb8 |
| merge_service.py | c125ee0f4cbce0b01a7d47542cbbdfe4ca9631618cc2da9644300076904e2d75 |
| storage_cleanup.py | bb651781c4b95338dff86c8bc8e47b402c752feecdac2afe54130bbb0b5f7a2c |
| tests/test_attempt_working_lifecycle.py | 29e762c31096a44a9aeb01399d1e98b1f3c18e44369ef9fb649997ca5ff2251f |

## Remaining required work

Published input snapshots still depend on existing original-retirement/full-staging gates. Independent safe discharge must support both exact surviving original/recovery input and accepted intentional source-retirement plus terminal recovery outcomes; unexplained missing inputs stay protected. The approved Zone.Identifier-only original-cleanup exception, legacy 29.586 GB snapshot assessment, M4B timeline preservation, combined regression/real conversion and standalone Windows installer remain unfinished. Existing 24-hour recovery policy is unchanged. No new deployment, app controls or user-data disposal is implied by this component PASS.
