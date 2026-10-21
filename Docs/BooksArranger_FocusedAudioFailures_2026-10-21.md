# Focused audio/status fixture diagnosis and corrections

Developer check only; not the canonical full QA gate, packaged QA, release clearance or production data evidence. Candidate base HEAD99669aa3f91c887b10dd306e2eddb7fa9c4f63a2 plus the explicit changes pinned below.

## Actual results and ownership

Twelve exact existing methods from seven assigned test modules were reproduced. First owned run:12 cases,11ERROR/1FAIL,4.973s unittest/5588.5604ms owner; exit1. Intermediate after fixture/current product fixes:11PASS/1FAIL,5.431s unittest/6049.1814ms owner; exit1. Final:12/12PASS, no failures/errors/skips,6131.6357ms owner; original tool chunkd8c7ca exit0, total wall6.4205209s. Final output gives closed=true,forced=false,timedOut=false,outputComplete=true,closureError=null; nativeactive/assigned/listed/unsignaled0,complete=true,zero=true,22 retained. No membership incomplete queries.

Exact selected IDs are in request-v4.json. Only these methods ran; no fullsuite repeated. Every attempt used unchanged corrected canonical bounded-check.runOwned from standard-entry-20261021-v3/harness-owner-fixed (SHA45510f11a011b617b4831994bd40aa87763d4195cd06c97ee6489af45f91bce6), fixed C:/Python314/python.exe, timeoutMs600000 and existing Koffi index.cjs. Actual command was default PowerShell/login:false at Studio: `& 'C:/Program Files/nodejs/node.exe' 'C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/diag-audio-20261021/run-focused-v4.mjs'`. This is explicitly unittest execution, not disguised as a media diagnostic.

All711 source-manifest files were verified/copied from immutable original canonical run entry-run-wduzna before diagnosis. The first attempted copy from current QA correctly stopped when the separately authorized Sources test_attention_repair edit differed; no tests launched then, partial copy retained. Original-source-v2, intermediate-v3 and final-v4 private copies/evidence remain separate. Final copies overlay only seven authorized fixture files plus primary Ender's audio_jobs.py correction. No live catalog/source/library, UI, kernel or Git action occurred.

## Root causes and exact corrections

- test_desktop_quit Drain2: Start while draining now raises typed StartRefused(start_state=closing). Assert that current contract; retain uninterrupted first book, second pending, no extra runner and no changed states. No guard changed.
- test_automatic_media queue insertion: FailInsert proxy hid SQLite in_transaction, so failure happened before intended INSERT. Delegate unknown connection attributes to the real private connection, retaining injected INSERT OperationalError and approval rollback/original preservation assertions.
- test_failed_m4b_retry legacy debt: __new__ service lacked inventory.database now required by real reacquire admission. Supply its existing private AudioJobs DB; working-debt refusal and unchanged snapshot checks remain real.
- test_status_snapshot replacement snapshot: __new__ state fixture lacked jobs needed by durable bulk-receipt read. Add actual private AudioJobs/DB and checked cleanup; retain snapshot enter/exit assertion.
- test_replacement_jobs raw completion: status double lacked _db required by bulk receipt. Delegate _db to existing real private queue, retaining all raw-parent/completed/converted/current-job assertions.
- test_blocked_retry Service4 plus status_under_load FastPress: inventory doubles lacked database/roots, and blocked fixture lacked draining initialization. Supply actual fixture DB/library root and draining=False; all reacquire checks remain real, not stubbed. Final remaining bulk failure was a lambda accepting only retry; current per-target call also supplies job_ids. Forward both to actual AudioJobs.attention_summary; preserve queue/refusal counts and later per-poll/ledger assertions. Include receipt in failure message for useful future diagnostics.
- StatusCost1 was a real production regression: audio_jobs.attention_summary opened a second DB just for reacquire projection. **Primary Ender owned and changed this file**, moving the projection into the first existing DB context; marker admission remains intact. Audio retained expected exactly1 connection and no source guard/media reads. Audio made no product edits.

These fixes add legitimate dependencies or current typed expectations; they do not waive marker holds, replace eligibility functions with unconditional True, remove assertions or alter source/retirement guards.

## Tested current pins

- `audio_jobs.py`: `9477ab6d672cf30e77acaeeff32b653b159ea1ed8695a6951e8be52a8d7ce774`.
- `tests/test_desktop_quit.py`: `41794bdf664525adf1601f03f8c2904c03da2ad0cdaa4efdb276226cc5c40824`.
- `tests/test_automatic_media.py`: `9af2df8ef89ba9f677a5910185515936889b6b5f80be9034e99177a28158ca43`.
- `tests/test_failed_m4b_retry.py`: `627690fa2e4a5c64a917817ef8ca56a25e34787d51d3c678c431998bc2f11272`.
- `tests/test_status_snapshot.py`: `3b698a6778c559575cffbe3b578b8b92677570398ebb37f3fda03b607b63215e`.
- `tests/test_replacement_jobs.py`: `30d2b5b8c5edfb9203440792d30af5bfb5535f6bf352d3e304d1cfcfc808cfb3`.
- `tests/test_blocked_retry.py`: `7034379a66e1b79a1910f44afa92d40758bcfa26120e944317a95b03e7372d3e`.
- `tests/test_status_under_load.py`: `6a4a209b70706919093ccad73534c2f331a17b05ed50b77825103550a0a7b6b7`.

The first is primary Ender's production correction. Remaining seven files are EnderAudio's only QA source changes. Current QA paths were rehashed equal to the final private tested bytes when this report was written. Exact edits are limited to imports/typed assertions and small fixture constructors/delegation described above; no existing production module was edited by EnderAudio.

## Evidence pins

Base evidence directory: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/diag-audio-20261021/`.

- `run-focused-v4.mjs`: `e6dd14dc36d9b0c9c18d4d768effa70f6970f93707738f6f4db169f33c1bbe6d`.
- `request-v4.json`: `eff25768f64ea6ee797e3ac3a44388b49fa11d1a51f57197a77d7fa0f7ba18b4`.
- `focused-v4-result.json`: `5cc67465474cc45d3c144729596af1a440234a49b8b3478e4c04a9ee027ac0a6`.
- `focused-v4.stderr.txt`: `db7dab2ee64c3b82a3a45965ff4f77ee427a7445aed4547e756d962e458ba102`.
- `focused-result.json`: `30c3bb683920bfe145aa1707f22c85053a7ecaf31284a90b5154625a5942c2fd`.
- `focused.stderr.txt`: `6fd711a2fa29a8a9bfc83b8ed44fd69f28fe84679e4d15e74f154f135caa0a59`.
- `focused-v3-result.json`: `8261d43837502db68b8c9acb791f146b7dfc4040f39d7bc912756805712b4e62`.

Fixture environment explicitly sets BOOKS_QA_RUN_ROOT to each private source copy and BOOKS_QA_FIXTURE_ROOT to version-specific private fixtures; PATH begins existing bundled runtime/ffmpeg. Existing private MP3 path is explicitly supplied via BOOKS_MP3_REAL_FIXTURE, though these selected methods do not execute that optional class. AutomaticMedia's selected setup creates its own tiny private sine MP3s; originals/live books are never used. All session scratch is preserved. Full canonical1193-case batch and independent Senua/Futaba gates remain unresolved by this focused receipt.