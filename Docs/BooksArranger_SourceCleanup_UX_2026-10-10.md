# Books Arranger — verified source cleanup

Date: 2026-10-10. EXTEND the existing audiobook review, jobs and View metadata surfaces. This addendum supersedes source-retention copy only for jobs explicitly covered by the current cleanup policy. Preserve metadata, chapter, naming, encoding, review, scan, layout and output-publication behavior.

## Scope and actual problem

Sergei wants conversion followed by removal of originals without another approval for each book. A completed M4B and a cleaned source set are separate facts. The app must show whether originals remain, are being removed, have been removed with recovery copies retained, or require attention. It must not present a conversion as failed merely because cleanup was blocked.

Ender's confirmed design retains fully verified recovery copies on C: under protected data/source-recovery/<cleanup UUID> before removing each exact included original on Z:. Removal is journaled per file. This releases the original audio bytes on Z: while retaining recovery storage on C:. No recovery purge is included. Only the approved source audio membership is eligible: no source folders, excluded tracks, cover files, companions, siblings, existing M4Bs, podcasts or ebooks are removed. Existing completed jobs are not silently enrolled. The selected MirrorMask and Snapshot cleanup is a bounded enrollment; Eye of God is outside it.

No new controls or layout region are required. Reuse Audiobook output, Audiobook jobs, View metadata and the existing audiobook-job pause/resume controls. No repeated confirmation modal, checkbox per book, bulk-delete control, settings matrix, recovery-purge control or scan-control change.

## Output plan and queue copy

For an eligible new job, replace the source-retention notice in Audiobook output with **Creates one audiobook, checks it, then removes the included originals. Recovery copies are kept.** The summary adds **Source cleanup: remove after output checks** and **Recovery storage: [actual location]**. These facts must match the saved job plan; do not infer them for a historical retained-source job.

Create audiobook tooltip for cleanup-enabled jobs: **Create and check this audiobook, keep recovery copies, then remove its included originals.** Retained-source jobs keep the existing preservation tooltip and notice. Approval of metadata still means approval of metadata, not source deletion; its tooltip may accurately say sources stay unchanged during that approval. Saving track review also remains non-destructive. The cleanup policy is visible before the actual creation action, without creating another approval step.

When a source-retaining historical job is being inspected, show **Source cleanup: originals retained**. A missing or unsupported cleanup policy must not render a removal promise. Existing collision and source-review constraints still apply.

## Stages and persistent facts

Use separate labels **Audiobook output** and **Source cleanup** in the existing output summary and created-file View facts. Maintain **Output checks passed** and the validated final path after successful publication, even when cleanup needs attention.

Exact cleanup copy, according to the backend's confirmed state:

- Not enrolled: **Originals retained**.
- Eligible output still being created or checked: **Waiting for output checks**.
- Backup preparation/verification: **Checking recovery copies**.
- Removal in progress: **Removing originals: [removed] of [included]**.
- Pausing: **Pausing source cleanup**.
- Paused: **Source cleanup paused: [removed] of [included] removed**.
- Successful cleanup: **Originals removed; recovery copies retained**.
- Interrupted or blocked cleanup: **Source cleanup needs attention: [specific reason]**.

A counter measures confirmed journaled original removals, not planned files, missing paths or copy progress. If some files were removed before an interruption, continue to show **[removed] of [included] removed** with the concrete blocking reason. Never show **Originals retained** for that partial set. Deleted originals are not read errors when their authoritative job says they were removed; unchanged completed jobs are not recreated because expected original paths are absent.

Example errors: **Source changed: [filename]. Review this file before cleanup.**; **Recovery copy could not be verified: [filename]. Originals have not been removed.**; **Output changed. Cleanup stopped; remaining originals are retained.** The statement about untouched originals must be based on actual per-file progress. A successful output stays visible and can still be inspected when cleanup is blocked.

Show **Removed from Z: [verified bytes]** only for confirmed deletion of originals from Z:. Show **Recovery storage on C: [verified bytes]** separately. Same-volume relocation must never be described as freed space. Do not promise a retention deadline or automatic purge. Recovery files remain until a separate purge is authorized.

## Existing pause and resume behavior

Keep button labels **Pause audiobook jobs** and **Resume audiobook jobs**. For cleanup-enabled work, Pause tooltip: **Pause audiobook work. Source cleanup finishes the current file before stopping.** Resume tooltip: **Continue pending audiobook work. Paused cleanup resumes without recreating the audiobook.**

Associated jobs help: **Pausing source cleanup finishes the current file. Resume continues its saved progress. Scanning has separate stop and resume controls.** Preserve existing audio-creation interruption help where that is the current stage: **An interrupted conversion restarts; completed outputs stay in place.** Display both short stage-specific facts if the queue can contain both kinds of work. Do not claim that audio creation resumes mid-file.

During a pending safe pause, show Pausing until the backend acknowledges it; do not visually report Paused while a file operation is in flight. Resume is enabled only for the existing resumable state. Resuming or restarting the service rechecks output, recovery and remaining sources, uses confirmed cleanup journal progress and never starts another encoder for an already-created output. Scanning controls are unchanged.

## Recovery information in View

In the created-file metadata facts show **Source cleanup**, **Originals removed**, **Originals remaining**, **Recovery copies**, and **Recovery location**, with actual confirmed values. Keep the existing output path, metadata and cover. Paths wrap in normal flow and remain selectable. A failed recovery check is shown as an error fact, not **Recovery available**.

When the bounded restore route exists and all its guard checks apply, the help may state **Recovery copies can restore the original tracks. Existing files are never overwritten.** Do not claim a Restore button exists: this milestone introduces none. Recovery content is not an unsorted book candidate or a user source-folder target. Existing Open output folder remains the created audiobook action; do not repurpose Open source folder to an absent original or to the private recovery store.

## Accessibility and verification

Use current dark-theme roles, text sizing and spacing. Stage/status text appears in normal flow through the existing polite live status region, without moving focus on poll updates. Errors contain a readable word and concrete reason, never color alone. Wrap long paths and filenames without covering controls. Existing buttons retain visible keyboard focus and at least 24 by 24 CSS-pixel hit areas; no new accelerator or interactive target.

Futaba verifies at 1440 and 700 CSS pixels: pre-queue removal notice; historical retained-source copy; recovery verification; count progression; successful removal; partial failure/drift; pause requested during a file operation; paused progress across restart; resume without new encoding; truthful output success beside cleanup attention; View recovery facts; absent-original folder action; no podcast/ebook/companion enrollment. Measure status/help/button rectangles for overlap in each available running, pausing, paused, completed and failure state. Backend/native safety tests belong to Ender and Senua; UI states must reflect their authoritative receipts.

Design basis: NN/g visibility of system status through separate output and cleanup facts; error prevention through visible policy and exact source membership; user control through existing pause/resume and recovery; Jakob's Law and Hick's Law through reuse of established surfaces. No source cleanup, native operation, implementation, Git operation, probe or disposable output was performed for this doc-only handoff. Commit this spec through Sully before implementation cites it.
