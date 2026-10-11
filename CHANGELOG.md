# Changelog

## [v0.11.3] - 2026-10-11

### Changed

- Open the browser in Book candidates by default instead of Files. Switching views and their filters remain unchanged.

## [v0.11.2] - 2026-10-11

### Changed

- Rename the candidate filter label to “Converted by this app” to clarify its scope. The internal filter value and completion predicate are unchanged.

## [v0.11.1] - 2026-10-11

### Fixed

- Remove the blanket Windows Job-membership rejection that blocked normal Start-menu launch and restart. Exact-owner, idle, exclusive port/catalog, completed-record and readiness guards remain intact. No Job manipulation or tool-host launch bypass is introduced.
- Correct the startup admission documentation. Targeted producer and independent receiver launcher checks pass; actual normal-user launch/restart acceptance remains pending.

## [v0.11.0] - 2026-10-11

### Added

- Windowless Pythonw launch and guarded idle restart entrypoints, plus a bounded installer for the current user’s Books Arranger and Restart Books Arranger Start-menu entries. Installation does not launch the app.
- Verified-owner reuse and cause-specific native startup feedback. Restart refuses active work or unverified ownership; ordinary launch/restart leaves saved automatic work paused until Start.

### Fixed

- Health reports the loaded server version, and the server supports absent Pythonw standard streams. Existing metadata, retry, conversion and recovery safeguards remain unchanged.

## [v0.10.0] - 2026-10-11

### Added

- Active automatic runs retry eligible saved metadata research after interruptible waits, with the earliest retry check and distinct wait reasons shown in the browser. Explicit Stop and server restart keep work paused until Start.

### Changed

- Replace the app-imposed 100-request daily limit with 100 uncached requests per rolling hour per allowlisted host. Genuine source pauses and Retry-After remain respected; blocked hosts and cache hits do not spend the candidate request budget.
- Preserve confidence/admission gates, bounded public transport and evidence storage, existing conversions and 24-hour recovery retention. No new provider or paid connector is added.

## [v0.9.2] - 2026-10-11

### Fixed

- Closed, reset or aborted browser connections during response headers or body now end only that request, without a second response through the disconnected socket. Connected backend failures and unrelated I/O errors retain their existing behavior.
- This handles the observed disconnect symptom; WinError 10053 alone does not establish why the connection closed. Automatic-processing, conversion and recovery safeguards remain unchanged.

## [v0.9.1] - 2026-10-11

### Fixed

- Unexpected metadata-research failures now retain bounded sanitized diagnostics and atomically mark the run and affected candidate inactive. Previously stranded research states report missing historical details without inventing an exception cause.
- Explicit Start retries an eligible saved research checkpoint while preserving pending, completed and deferred work. Failure to save the checkpoint blocks retry rather than claiming it was saved.
- The original overnight exception remains unknown; this patch repairs lost diagnostics and misleading state, without changing approval gates, existing jobs or 24-hour recovery retention.

## [v0.9.0] - 2026-10-10

### Added

- Automatic audiobook discovery, bounded public metadata research, conservative approval and queueing through the existing converter. Explicit Start resumes saved work; Stop and server restart preserve pending work without an unattended retry scheduler.
- Evidence and held reasons in the browser, with protected manual drafts and safer separation of unrelated recordings sharing a folder.

### Changed

- Public-source requests and cached responses have bounded budgets, deadlines and retention. Missing or contradictory identity, source order, translation, name ordering or verified cover evidence keeps a book held; public search leads alone never approve it. The evidence-only Kabir/Shimada pilot did not enroll either recording.
- Existing approved/completed identities, validated conversion, Converted counts, source cleanup and 24-hour recovery retention remain unchanged. Empty-folder removal remains safely unavailable on the actual Z: drive. No paid connector, audio upload or dump importer is added.
