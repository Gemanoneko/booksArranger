# Books Arranger: merge safety design audit

Date: 2026-10-09. Senua; bounded design audit for the authorized source-preserving MP3-to-M4B milestone. This is not a release clearance or a review of implemented merge code. No encoder, provider request, live control, source write, or source deletion was run.

## Reviewed boundary

Reviewed committed metadata/merge UX at `ab5d120` and its assistant-review addendum at `8aa7e7e`, plus current `scanner.py`, `metadata.py`, and the local web request boundary in `web_server.py`. The reviewed design uses private `data/merge-staging/<job UUID>`, source-hash manifests, output validation, configured-root publication without overwrite, durable jobs, preserved originals, and recognition of previously created outputs. Ender's concrete merge implementation is not present in these reviewed files. Findings below concern contracts that the stated design must make explicit; they do not assert that unimplemented code already violates them.

Severity follows Team/Docs/ProcessRules.md, **Severity definitions**. Conditional Critical findings identify unsafe implementations that must be excluded before any live-file pilot. Actual merge code requires a subsequent bounded source review.

## Findings and essential contracts

### Critical C1: lexical containment does not establish a safe write destination

`scanner.inside()` compares normalized absolute strings. It does not resolve or reject a junction/reparse point in an ancestor. `_directory()` skips discovered symlinks/junctions, but that does not protect a later writer, its configured root, queued paths, or a directory replaced after scanning. Reusing either mechanism as sufficient permission to write risks writing outside the configured library.

**Required contract:** the server derives destination components from the accepted review and a configured audiobook root; clients never supply an arbitrary executable, staging directory, or output path. Reject traversal, special/device paths and alternate data streams; validate every existing ancestor including the configured root for unexpected reparse traversal. Validate newly created ancestors and recheck immediately before publication. Bind writes to the inspected directory identity using supported handle-based mechanisms where feasible; reject observed root/parent identity drift. Do not describe repeated path checks as eliminating every race. If the platform cannot establish the required directory boundary, stop that book with a concrete destination error. Apply the same boundary/ownership checks to staging cleanup; never recursively clean a path solely because its string starts with the staging prefix.

### Critical C2: cross-volume fallback and collision handling can overwrite files or expose partial outputs

Private staging on C: and final output on mapped Z: cannot be assumed to support one atomic cross-volume rename. `exists()` followed by an overwriting replace/copy is unsafe; another process or queued book can claim the path after the check. Copying directly to the final `.m4b` makes an incomplete file visible as the audiobook. An interrupted fallback must not delete an unrelated file that subsequently occupies that name.

**Required contract:** use a uniquely owned destination-side temporary created exclusively inside the validated output directory. Copy the checked private result there, flush/close it, verify its exact hash and required output checks, and publish by a supported same-volume **no-replace** operation. Never use `os.replace`, an overwriting move/copy, or overwrite-enabled encoder options on the final path. A collision at publication stays a collision even if the earlier preview was clear; no hidden suffix or silent adoption. Validate the actual Windows/mapped-volume behavior in fixtures before a live pilot; an unsupported no-replace path fails closed. Source paths are never cleanup or replacement targets. Owned temporary paths and final output paths must be distinct from every source, catalog/database file and app source path.

### Major M1: pre/post hashes alone do not establish which source bytes the encoder consumed

Size/mtime are inventory reuse fingerprints, not sufficient conversion identities. A source may change during encoding, including a transient edit restored before the final hash. A review revision also becomes stale when membership, order, recording evidence, canonical fields, accepted evidence or cover changes.

**Required contract:** a queued job freezes the exact ordered member list, approved content hashes, review/evidence revisions, cover hash and output contract. Encode owned source snapshots whose copied bytes are verified against those approved hashes, or use an equivalent demonstrated mechanism that prevents source replacement/modification during consumption. Before publication, revalidate that the live originals and accepted review still match the queued revision, as the UX requires. Keep all source tags/comments in the recovery record and apply approved tags only to the new output. Do not hold a database transaction for the duration of encoding; use short transactions and an explicit revision compare immediately at the publication boundary. Detected source/review drift invalidates the job rather than quietly blessing a new source.

### Major M2: a crash after publication but before the database update can produce duplicate work or false ownership

The filesystem and SQLite cannot be committed in a single transaction. A final file can exist while the job still says checking/publishing, or a job can say completed after an output is lost or replaced. An arbitrary pre-existing file at the expected path is not proof of a successful job.

**Required contract:** durably record publication intent before final publication: job UUID, source/review revision, exact final path, destination temporary ownership, checked output hash/size and validation outcome. After publication verify the final artifact, then commit completion. On restart, reconcile publishing jobs by that recorded exact artifact identity; only the matching expected artifact can be recovered as this job's completion. An unmatched existing final path is a collision/needs-attention state. An unchanged verified completed artifact is skipped. A missing or modified completed output needs reviewed recovery, never automatic overwrite. Interrupted encoder work restarts at the book boundary; it is not resumed from a partial AAC/M4B. Pending state must be durable before acknowledging queue/pause/shutdown actions.

### Major M3: scoped cancellation and temporary ownership need mechanisms, not names

A UUID-looking folder is not automatically owned disposable data. Broad `taskkill` by executable name can stop the user's converter; recursive cleanup through a swapped junction can escape the job. A timeout is not safe if the owned encoder or descendants keep writing after the worker returns.

**Required contract:** launch the encoder with a validated executable and an argument array, without a shell. Use safe owned input aliases/manifests rather than interpolating arbitrary filenames into FFmpeg concat syntax. Limit file inputs/protocols to those needed by the job. Track the exact child/process group or Windows job ownership; pause/shutdown stops and waits only for that owned work before declaring paused and before deleting its temporary files. Use a reasonable media-based deadline/watchdog and bounded cancellation escalation, rather than a 600-second QA command limit for real audiobook conversion. Cleanup removes only recorded owned temporaries after path/identity checks; preserve uncertain artifacts for recovery. No process was launched during this audit.

### Major M4: free-space estimates and output checks must include the second volume and copied artifact

Source snapshots plus private encoded output and the destination-side copy can require several times the final audiobook's size. C: space does not prove Z: space. Network disconnects, quota limits, or disk-full events can occur after a successful estimate. A successful encoder exit or an FFprobe header alone does not establish a playable complete audiobook.

**Required contract:** estimate/check private and destination storage separately, including snapshots and destination copy, and handle mid-write failures without publishing a final file. Preserve originals and a retryable journal; delete only verified owned disposable partials. Validate one expected audio stream/container, full decode readability, duration against the reviewed source total with a stated tolerance, Unicode canonical metadata/author role, audiobook classification, exactly one accepted cover and the approved optional chapter plan. Validate the destination temporary's exact hash against the checked private output before publishing; record the final hash. Output checks passed is separate from actual iTunes/Apple Books/iPhone sync, as the addendum requires.

## Bounded implementation acceptance evidence

Before a live pilot, exercise isolated fixtures for: ancestor junction or root drift; traversal/device/stream-shaped names; a collision inserted between preview and publish; case-insensitive duplicate destinations; a destination copy interrupted/disconnected/disk-full; cancellation while encoding/copying; source/review mutation while queued and during work; unreadable/corrupt output or rejected tag/cover/duration; and crashes just before publication, just after publication and before completion commit. Confirm originals' hashes remain unchanged, no incomplete final audiobook exists, unrelated processes/files remain untouched, and restart neither duplicates nor adopts an unrelated output. A network filesystem without demonstrated publication semantics remains blocked for live writing.

## Ender's contract response

After the initial findings were sent, Ender confirmed the following planned implementation: an approved ordered-member/review/evidence/cover/profile manifest; SHA256 of every source at approval; exclusive source copies into UUID-owned private staging with snapshot hashes equal to the approved hashes; live-source stat/hash revalidation; encoding only the snapshots; full decode/duration/tag/single-cover/QuickTime-chapter validation; an exclusively created destination-side UUID temporary, flushed and hash-checked; and same-directory Windows `MoveFileExW` without `REPLACE_EXISTING` or `COPY_ALLOWED` (with `WRITE_THROUGH`). Cross-platform or network semantics that cannot be established fail closed. Publishing intent and expected final hash are durable before the rename; restart recognizes only the exact manifest/hash artifact. Cleanup is confined to owned UUID manifests and never deletes sources. No conversion code exists yet; grouping/filter QA comes first.

This response addresses the central snapshot, cross-volume, no-overwrite and recovery design gaps. Code review must still establish the actual path/identity boundary, concurrent revision gate, temporary ownership/cancellation, supported mapped-volume semantics and failure handling; stating a Windows API choice does not by itself verify these properties.

**Design outcome:** the revised staging/preservation contract is viable. Two conditional Critical hazards and four Major requirements recorded for implementation verification; these are not six demonstrated defects in existing merge code. No merge-code clearance issued. No disposable artifacts were created. The report itself is the retained review evidence.
