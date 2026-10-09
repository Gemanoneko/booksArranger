# Books Arranger: source coverage and recording completeness

Date: 2026-10-09. Bounded scope clarification to the frozen metadata/merge UX and review-provenance addendum. Those documents remain unchanged. This addendum supersedes their requirement to prove a complete publisher recording before merging reviewed existing chapter files.

## The requested operation

Sergei asked to group existing MP3 chapters, verify book metadata and merge each book into one audiobook file. The app must establish which existing source files it will combine and preserve their audio and originals. It does not need to reconstruct or certify a publisher's complete release when no reliable external completeness evidence exists.

Creation requires reviewed same-book/recording membership and playback order, current readable source identities, and coverage of the exact reviewed source set. Replace the complete-book assertion with **These included files belong to one recording and contain the source tracks intended for this output**. Tooltip: **Review the exact source set for this output. This does not certify the publisher's complete recording.** Preserve accurate User review / Assistant review provenance; an assistant review does not appear as a user assertion. Existing playback-order review remains separate. No new selector, preference or extra approval dialog is required.

Show **Source files reviewed** when those facts are established. Separately show **Recording completeness unknown** when no reliable external evidence establishes the full released recording. That unknown fact alone does not disable creation or imply corruption, a missing chapter or an incomplete book. Do not label the output **Complete recording** or conceal this distinction behind an overall Approved badge. The exact included file list, total measured duration and output path remain visible before queueing and in the saved output record.

Known unreadable/missing members, unresolved mixed identities/recordings, uncertain playback order, changed source fingerprints, incomplete coverage of the known intended source set, or credible contradictory completeness evidence remain blocking. A trustworthy published track list with a known missing required track is concrete evidence; a numbering gap or a small unexplained duration difference alone is a review clue. Show the clue and its source without converting it into an invented missing chapter. Excluded known tracks remain visible and require an explicit reviewed inclusion decision; never omit introductions, short tracks or duplicates silently to reach readiness. Reviewers must report an unresolved substantive contradiction rather than approve around it.

For example, a publisher duration of 17:47:43 versus 17:46:26 across 40 local files shows **Published duration differs by 1m 17s; cause unverified** when that evidence is recorded. It does not independently prove that a particular chapter is absent. The source-set and output checks still must prove that the selected local audio was included without unintended trimming, loss or omission. Original MP3 bytes remain preserved in source files; re-encoded output is not described as byte-identical to MP3 inputs.

## Safety and validation remain required

The worker still rechecks the exact source set/revision, decodes/reads every included track, includes its full intended audio, preserves the original files, validates output duration against those inputs with the documented technical tolerance, validates metadata/cover/container/chapters, and publishes only a validated output without overwriting existing files. Technical output validation proves faithful creation from the reviewed source set; it does not prove publisher completeness or actual Apple Books sync. Keep **Output checks passed**, **Recording completeness unknown** when applicable, and **Apple Books sync not checked** as distinct facts.

Reliable later completeness evidence can update the recording review. Source/evidence changes invalidate affected review/readiness under the existing revision rules. Batch creation may include source-set-reviewed books with external completeness unknown, while known conflicts remain out of the queue with their specific reason.

Judy wrote only this new addendum. No source code, git, catalog, live controls or library files changed; no disposable probes were created. Sully freezes and commits/pushes this exact document before Ender's merge-scope brief cites it.
