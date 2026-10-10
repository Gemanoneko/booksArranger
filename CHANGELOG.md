# Changelog

## [v0.9.0] - 2026-10-10

### Added

- Automatic audiobook discovery, bounded public metadata research, conservative approval and queueing through the existing converter. Explicit Start resumes saved work; Stop and server restart preserve pending work without an unattended retry scheduler.
- Evidence and held reasons in the browser, with protected manual drafts and safer separation of unrelated recordings sharing a folder.

### Changed

- Public-source requests and cached responses have bounded budgets, deadlines and retention. Missing or contradictory identity, source order, translation, name ordering or verified cover evidence keeps a book held; public search leads alone never approve it. The evidence-only Kabir/Shimada pilot did not enroll either recording.
- Existing approved/completed identities, validated conversion, Converted counts, source cleanup and 24-hour recovery retention remain unchanged. Empty-folder removal remains safely unavailable on the actual Z: drive. No paid connector, audio upload or dump importer is added.
