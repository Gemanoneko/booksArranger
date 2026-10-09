# Books Arranger: review provenance and batch readiness addendum

Date: 2026-10-09. Bounded clarification to `BooksArranger_MetadataMerge_UX_2026-10-09.md`, frozen SHA256 `5F0E7B5A77438799E642CB9B329089A3A3EC1626E18738903E7C686363DDFF0A`, committed at `ab5d120`. The original spec remains unchanged. This addendum supersedes its human-only approval wording and its device-pilot sequencing where they conflict with the following rules.

## Review may be performed on the user's behalf

Sergei authorized the assistant to check metadata, group chapters and create audiobooks. The flow therefore supports evidence-based assistant review as well as user review; it must not require Sergei to personally approve every book merely to repeat work the assistant can establish from reliable evidence. Existing review controls remain available for manual correction. No new review-mode selector or settings panel is needed.

Every accepted metadata, membership, order, recording and completeness review records the actual reviewer actor, date, accepted revision and supporting evidence. Display **User review** or **Assistant review**, beside the corresponding fact, according to the recorded actor. Replace unconditional **Completeness confirmed by you** and **Playback order confirmed by you** with **Completeness: user reviewed**, **Completeness: assistant reviewed**, **Playback order: user reviewed**, or **Playback order: assistant reviewed** as applicable. Show the supporting evidence in the existing evidence disclosure. Never render a checked user assertion or claim **Confirmed by you** when an assistant supplied that review.

Assistant review requires concrete evidence for each accepted fact, not a confidence score, filename guess, source Artist assumption, folder scan completion or uninterrupted chapter numbering alone. Metadata evidence must establish the canonical work identity and author role; track evidence must establish the selected recording, exact membership, completeness and playback order. A print/work catalog match alone cannot prove which audio recording or complete chapter set is present. A reviewed field need not wait for an unrelated optional field, but unresolved identity, recording, completeness, membership or order that is required for creation keeps the affected book blocked. Show the specific missing evidence and retain the candidate for later review. User authorization to process books does not fabricate those facts or bypass detected conflicts.

Review provenance is attached to the same exact candidate/source/evidence revision as the existing approval. Changes invalidate affected approvals regardless of reviewer actor. Queueing includes only books whose required review facts and technical checks are established; assistant-reviewed ready books can be queued under the existing task authorization. Original preservation, no overwrites, source-change checks and output validation remain mandatory.

## Technical pilot and actual device verification are separate

One-book technical pilot validation precedes activating batch creation. Batch capability can be implemented and tested after that pilot; it is not blocked solely because an actual iPhone/iTunes/Apple Books sync check requires Sergei's later participation. Keep the two outcomes visibly separate: **Output checks passed** and **Apple Books sync not checked**. Do not claim actual device compatibility from a container/tag/decode check. Actual device findings can require fixes before broader use, but absence of that check alone must not stop building the authorized batch functionality or discard completed technical validation.

The parent coordinates any necessary real-device check around a concrete validated output. Do not add a mandatory device-confirmation checkbox, approval modal or automatic compatibility claim. The existing incremental queue, pause/resume and source-preserving output flow applies unchanged.

Judy wrote only this addendum. No code, git, live controls or library files changed, and no disposable probes were created. Freeze and commit/push this exact doc through Sully before Ender's review/merge brief cites it.
