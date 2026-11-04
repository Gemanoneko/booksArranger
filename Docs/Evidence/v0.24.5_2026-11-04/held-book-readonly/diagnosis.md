# Похититель детей: existing held cleanup, 4 November 2026

Ender performed app-local read-only diagnosis only. The live catalog was opened using SQLite URI `mode=ro`, `query_only=ON` and read transactions; only SELECT statements read persisted state. No installed app action, focus, live DML, file repair, Z: enumeration or media read occurred. Stored Z: paths below are receipt text. Service constructors and filesystem-dependent status methods were not invoked.

The user is correct that this exact book was the subject of the protected-output cleanup fix: `Docs/BooksArranger_0.24.4_TechnicalPlan.md` and its UX explicitly name its 29 October hold. That fix added **Retry cleanup** for the already enrolled book and new native diagnostics. It did not automatically retry historical source deletion. The 0.24.5 queue fix additionally lets independent books progress when a prior producer cannot be proved closed; it does not release this older safety hold.

## Exact persisted state

- Candidate `bda0de7c-2b26-4a10-b26a-b2ffcdb9b0ee`, current group/context revision 5, matches the enrolled review binding exactly.
- Completed job `c60f052d-aac1-4dc2-b9c1-2a8484928a44`, last changed `2026-10-29T01:15:43.999335+00:00`.
- Cleanup `bc5f1302-fdee-4621-9823-522a0a9ad2a1`, `needs_attention`, exact reason `Cannot refresh protected file identity`, last changed `2026-10-29T01:54:45.276736+00:00`. No retry has changed this record since then.
- Validated output receipt: `Z:\Audiobooks Sorted\Brom\Похититель детей - Brom.m4b`, 1,996,889,421 bytes, SHA256 `950e7fe489b2b0f71bede1f6b9f513b501a99de330bb1101e9436a655308acec`.
- 37 frozen originals, 2,102,929,304 bytes total. Historical member receipts: 36 `backup_verified`, one `removal_intended`; zero source retirement records. These receipts do not prove today's file presence or bytes.
- The unresolved removal intent is `Z:\Audiobooks\Unsorted\Бром - Похититель детей [Александр Аравушкин]\01.mp3`, 17,132,434 bytes. Its recorded recovery copy is `data/source-recovery/bc5f1302-fdee-4621-9823-522a0a9ad2a1/00000.mp3`.
- No cleanup hold-history diagnostic exists. The historical protected final-output `GetFileInformationByHandle` check discarded its Windows error, so the precise OS cause remains unknown. `identity_api_error:87` in a saved original's identity facts describes its supported extended-identity fallback; it is not evidence of the failed output refresh's OS error.

At the read snapshot, other jobs had reached 757 completed and 447 pending, compared with the screenshot's 749 converted/448 queued. Source scans were complete with zero scan errors. There were no `checking`/`removing` cleanup states and no isolated retained producer checkpoints. This book's old hold is not evidence that the new queue is globally stopped.

## Supported next action

Open **Output needs attention** (or the Needs attention shortcut), select **Похититель детей**, and press its row/details primary **Retry cleanup** once. The accessible label is `Retry cleanup: Похититель детей`. Queued/Cancel while another action finishes is expected. This is the distinct existing cleanup action, not conversion Retry, Start over, ordinary Resume or Delete recovery copies.

The current installed `source_cleanup.py`, `native_io.py`, `merge_service.py` and `web_server.py` match main after CRLF normalization. Calling only the current source's pure eligibility and review-binding methods against the read-only catalog returned `allowed:true`, exact manifest/output correspondence and exact review binding. The source trace confirms the UI's row/details action uses that capability and `/api/audiobook/cleanup/retry`, retaining the same completed job and cleanup. No app button was pressed in this investigation.

No new code fix or additional private preflight is required before this supported press. Existing `test_legacy_intent_retry_reopens_and_verifies_every_copy_before_first_delete` covers the same legacy reason plus first removal-intent shape; it is historical accepted test coverage, not a new test execution here.

The admitted worker reopens and hashes the complete output, protects and checks all original identities/bytes, verifies every recovery copy and its durability, and rechecks review/location guards before another source disposition. This requires actual filesystem access by the app and can take time for this roughly 2 GB output/2.1 GB source set. It does not reconvert or silently accept missing files. Ordinary Resume and retention do not select this generic identity hold, so waiting or restarting alone will not trigger it.

Completion is not guaranteed from database evidence. If `01.mp3` is absent after the unproved intent, the worker must hold with an unknown removal outcome; it does not adopt absence as successful deletion. If another protected output-identity call fails, the new failure records the actual Windows code/API/path. If the supported retry fails, preserve its new reason/diagnostic and receipts before deciding the next recovery step. Do not clear the row, force deletion or discard recovery copies to conceal the hold.

## Preserved evidence

`snapshot.json` contains exact job/manifest/output/enrolled intent/member/marker/retirement/cleanup error/review receipts from one read transaction. SHA256 `c71094350ddf7f8c05645cb84208efd5922abb478651a7a15bf5e38a1d59c962`, 703,828 bytes. `summary.json` extracts the selected book's state and first intent; `eligibility.json` records the pure capability/binding results and installed-source byte comparisons. No diagnostic scratch was created and no disposable output requires cleanup.
