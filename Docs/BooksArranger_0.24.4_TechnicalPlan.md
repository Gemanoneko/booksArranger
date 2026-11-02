# Books Arranger 0.24.4 — protected-output cleanup retry

The stored Похититель детей cleanup stopped on 2026-10-29 after its first removal intent, before any recorded source disposition. Windows refused a held final-output file-information read; the old message discarded the Windows error. Global Resume excludes this held reason. The catalog records 37 verified recovery copies; current NAS/recovery files were not inspected.

Reuse the existing enrolled cleanup, immutable manifest/binding/output-location policy, exact source membership and single cleanup worker. A separate per-book Retry cleanup action uses the existing action queue/admission and Cancel/Pause rules. It never calls conversion Retry, enrolls another job, starts automatic processing, or expands Retry all. Eligibility is the exact legacy protected-identity hold, or a newly recorded typed final-output identity-read failure; unrelated proof failures stay held.

Each admitted retry runs the existing cleanup from the beginning with fresh output/recovery/source handles. Full output bytes, recovery hashes/durability, reviewed source identities/hashes and catalog/location guards must pass before new deletion. Existing removal_intended/disposition_set reconciliation is unchanged: an absent original with unproved outcome remains held. Legacy records retain their existing provenance policy; no historical identity or current file presence is fabricated.

Capture Windows error immediately when the native call fails: numeric code, system message, API and affected path. Wrap only the final-output identity check as a typed cleanup failure; persist its diagnostic in existing cleanup hold history and expose it in status. Old holds explicitly have no recorded Windows code. No generic BoundaryError is automatically retried.

Expected files: native_io.py, source_cleanup.py, merge_service.py, web_server.py, web/app.js; focused existing cleanup/API/frontend tests and Brief/implementation evidence. No version/build/release/guard/toolchain changes. UI follows committed Docs/BooksArranger_0.24.4_UX.md.

Risk: source deletion remains safety-critical; no weakened identity/hash/provenance checks, automatic deletion policy change, NAS access, live catalog writes, app control or installer work. Focused private BEFORE proof uses the existing CleanupTest fixture and real invalid-owned-handle error; AFTER cases cover exact held intent, fresh reopen, changed/missing output/recovery/source, wrong/stale scope, single owner/queue/cancel/pause and actual diagnostics. One final full entry belongs to the final candidate later.
