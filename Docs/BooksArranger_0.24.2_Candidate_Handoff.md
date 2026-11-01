# Books Arranger 0.24.2 candidate handoff

Product implementation and the QA-phase corrections are ready for Sully’s atomic candidate source/version commit: PURE-2 passed all 69 targeted cases with original normal closure and full postflight. This is not a packaged-build or release-clear verdict. Source is frozen; no Ender git mutation, version edit, full entry, package, app launch or user-library operation has occurred.

Proposed commit: fix: keep foreground processing responsive and retain verified book decisions

Root causes: unrelated completed-book verification held up foreground Start/Resume; one-time cleanup flags stranded interrupted/transient work; stale approval/research provenance confused genuine choices and automatic decisions; conservative series/person and internal-volume clues dropped established identity; three existing terminal chapter ends exceeded complete source audio; picker and row feedback hid pending/request origin.

Suggested changelog content for Sully:

- Start/Resume admits requested work promptly while idle finished-book checks yield safely. Show actual checks, pause origin and cancellation, and retry transient output/recovery/folder faults.
- Start over returns eligible stopped work to automatic handling while retaining explicit names, cover, order and destination choices; source replacement can refresh without restarting the app. Saving queued names preserves the new title and waits for explicit approval.
- Retain current verified title/series/world facts and recognize the confirmed McCammon/Queen/Tolkien cases. Identity-bound multi-author series/worlds omit the author folder, retain credits and preserve explicit Choose folder destinations.
- Correct only a proven final chapter-end overrun in newly joined outputs, preserving source bytes and all starts/titles/order; expose exact refusal diagnostics. Keep existing whole-M4B and historical frozen-routing guarantees.
- Coalesce identical inventory reads, open only one folder picker, and keep folder retention/ownership/removal receipts accurate.

Targeted evidence: routing 45, series 19, terminal chapters 20 including 3 private native cases, 154 backend contracts positive across retained backend-3 plus corrected 14-case backend-4, and nine UI entry points accepted across UI1/UI2 (picker 8 assertions). Failed earlier attempts remain explicit in the matrix and compact JSON; no guard was waived. Backend-4 outer exit 0, both ASCII markers, exact source/runtime/helper postflight and normal native complete-zero closure; all 95 product Python files byte-identical to backend-3. Diff whitespace check passed.

Geometry now has158 retained accepted frames plus2 corrected private-fixture checks, with normal wrapper/outer closure, full postflight and unchanged product UI. Judy accepted the saved renderer snapshot in BooksArranger_0.24.2_UX_Verification.md. Outstanding before release: measured engine-load/S8 QA, canonical immutable non-app entry once on the committed candidate, package payload/hash proof, separately mandatory PA-1 with real release-specific user consent, and independent final Senua/Futaba findings. All requirements remain tracked; none is silently deferred. Root headless helper repair is a separate parent-owned studio change and is not a Books backend pinned input.

Sully owns package.json, package-lock.json and CHANGELOG.md updates for 0.24.2 in addition to the exact tool-relative paths below. The scope/UX/diagnosis pins were committed earlier and need no duplicate staging. Confirm no concurrent documentation writer before staging; use explicit paths, no broad add.

```text
Docs/BooksArranger_0.24.2_BackendTests.md
Docs/BooksArranger_0.24.2_Candidate_Handoff.md
Docs/BooksArranger_0.24.2_EntryPhases_Implementation.md
Docs/BooksArranger_0.24.2_Implementation.md
Docs/BooksArranger_0.24.2_ReleasePhaseTests.md
Docs/BooksArranger_0.24.2_RestartTests.md
Docs/BooksArranger_0.24.2_SeriesIdentity_Implementation.md
Docs/BooksArranger_0.24.2_SharedRouting_Implementation.md
Docs/BooksArranger_0.24.2_TargetedEvidence.json
Docs/BooksArranger_0.24.2_TargetedRunner_Review.md
Docs/BooksArranger_0.24.2_TerminalChapters_Implementation.md
Docs/BooksArranger_0.24.2_UI_Implementation.md
Docs/BooksArranger_0.24.2_UX_Verification.md
Docs/BooksArranger_Brief.md
Docs/BooksArranger_QAPlan_v0.24.2_2026-11-01.md
README.md
admission_diagnostics.py
audio_jobs.py
audio_pipeline.py
automatic_processing.py
book_restart.py
cleanup_ownership.py
cleanup_retry.py
desktop/folder-picker.js
desktop_backend.py
groups.py
local_identity.py
merge_service.py
migration_operation.py
migration_planning.py
organization.py
part_sets.py
pause_state.py
public_research.py
review_backend.py
reviewed_routing.py
scanner.py
scripts/check-desktop.mjs
scripts/qa-entry-context.mjs
scripts/qa-phase-contract.mjs
scripts/qa-real-shell-phase.mjs
scripts/release-contract.mjs
scripts/release-flow.mjs
shared_routing.py
storage_cleanup.py
tests/desktop-folder-picker.test.mjs
tests/qa-entry-context.test.mjs
tests/real-shell-update-contract.test.mjs
tests/real-shell-update-support.mjs
tests/real-shell-update.test.mjs
tests/release-contract.test.mjs
tests/release-flow.test.mjs
tests/test_0231_destination_frontend.js
tests/test_0231_rows_frontend.js
tests/test_0242_frontend.js
tests/test_automatic_frontend.js
tests/test_backend_242.py
tests/test_cleanup_242.py
tests/test_desktop_host.py
tests/test_desktop_quit.py
tests/test_integration_242.py
tests/test_metadata_choices.py
tests/test_organization.py
tests/test_output_migration.py
tests/test_restart_242.py
tests/test_ruling37_frontend.js
tests/test_safety_boundaries.py
tests/test_series_backfill.py
tests/test_series_identity_242.py
tests/test_shared_routing.py
tests/test_source_folders.py
tests/test_start_over.py
tests/test_terminal_chapters.py
tests/test_todo_holds_frontend.js
web/app.js
web_server.py
```

Temporary evidence is still needed for review/handoff under C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/. Compact receipts and source hashes are retained in Docs/BooksArranger_0.24.2_TargetedEvidence.json. Follow the current per-session scratch exception when disposing of this folder; no unrelated or recovery material is included in this handoff’s deletion authority.

QA-phase correction: all 18 prior Node entries remain exactly once (17 canonical + 1 mandatory native); one additive pure contract entry gives 18 canonical + 1 native. No case is skipped or N/A. Release 0.24.2+ requires twelve distinct raw native-evidence roles before credentials/publication. PURE-1 was not admitted and never ran; PURE-2 passed 69/69, plan 0d1182f83dc2df537e7a177c4ecf15e5df3b2b62d7d3be3bae6c4aa4639a73fe, source14 tree 013a3c6eedc31c22962d3a56dbb4c84333db8adcafa7584fc0d233b74bba545d, summary c2a9defd61db741b2786da5d2e495bed1839eb474b1b4ce319b91f7b4dccb542. All raw output bindings, source/runtime/helper postflight and zero guarded native attempts passed. The actual native PA-1 controller/app graph remains unexecuted and default blocked without actual authority. The exact list contains 76 tool-relative files (the prior 75 plus Judy’s report), before Sully’s version/lock/changelog edits.

The supported next-stage preparation and its remaining admission requirements are recorded in BooksArranger_0.24.2_EntryPhases_Implementation.md. No full context or candidate HEAD is fabricated before the atomic commit.
