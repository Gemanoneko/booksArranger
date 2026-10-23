# Books Arranger — in-place single-M4B edit and the re-hash cut (0.21.0, 2026-10-22)

Branch `codex/books-inplace-m4b` off `v0.20.3`, uncommitted for Sully. Sergei's rulings, 2026-10-22:
- The layout is the developer's call, provided every tag is correct and the book plays in Apple Books.
- No decode on the fast path; keep every check that does not need one.
- Build approved.
- Fold in the re-hash cut for every book, accepting the residual risk described in section 7.

## 1. What the copy flow already does

For an AAC single M4B, v0.20.3 never remuxes. `m4b_preservation.plan()` does three things:
- It keeps every original byte at its offset.
- It changes the old `moov` type to `free`, a 4-byte patch.
- It appends a new `moov` that holds the approved tags and cover, plus the original `trak` and `mvhd` bytes, byte for byte.

The 0.21.0 fast path applies that same plan to the original file instead of to a staged copy. The published file is byte-identical to the copy flow's `checked.m4b`: the test compares the two sha256 values.

## 2. Eligibility

Eligibility reuses the copy flow's own decisions; nothing new is invented. Code: `inplace_m4b.offered()` and `_edit()`.

Every one of these must hold:
- the automatic profile;
- exactly one `.m4b` source;
- no `replacement_id`;
- no approved repair;
- the frozen cleanup policy retires the original after verification (`cleanup_policy.enabled`). A policy that keeps the sources, such as a manually approved M4B or a Retry child that keeps a retained checkpoint, keeps the copy flow and its original;
- `choose_automatic_encoding` returns `copy`/`aac`;
- `plan()` succeeds with no repairs, padding, appended media or header patches;
- the frozen chapters and the frozen encoding policy match;
- the reviewed sha256 matches.

An in-place edit adds these requirements:
- the file can be opened READ|WRITE while sharing read access only (so it is not read-only and nobody else is writing to it);
- one link, and attributes limited to ARCHIVE or NORMAL;
- no named streams other than the Windows download marker (Zone.Identifier), which the existing marker protocol removes before the move. Its exact bytes are journaled in the intent before the first write, and every undo puts them back (0.21.1, Futaba m-3). A marker that changes after the intent is never removed;
- the destination is absent and on the same volume as the source;
- the volume has free space for the appended `moov` plus 16 MiB.

Any refusal returns `None` before the first written byte, and the copy flow runs in the same attempt with all of its checks. It may reuse the cover copy that the in-place attempt already put in the stage, but it repeats the cover's probe, dimension check and decode on that copy. A cover the in-place attempt refused is therefore refused again. The fallback reason is recorded in the job history as `{'in_place': {'fallback': ...}}`.

## 3. Edit mechanism and Apple Books

The edit uses the studio's own planner, through one native handle. ffmpeg or mp4v2 would write a new file. AtomicParsley needs padding the library lacks. mutagen shifts `mdat` in place.

Order:
1. Commit an `inplace_edits` journal row. It holds the path, identity, size, ns mtime, attributes, the reviewed sha256, the type offset, the planned `moov` and output sha256 and size, and the download marker's bytes when the original has one (0.21.1).
2. Append the planned `moov` at the original end of file, then `FlushFileBuffers`.
3. Write `free` over the old `moov` type, then `FlushFileBuffers`.

At every instant the file is a valid MP4. Before step 3 the original `moov` is still the first one, and after it the only one.

**Apple Books.** The output layout (`ftyp`, the old `moov` now `free`, `mdat`, then the new `moov`) is exactly what the copy flow has published since v0.16.0 for every preserved book, 358 of them. The layout is unchanged in every respect:
- brands;
- `stik=2` (audiobook);
- the `covr` cover;
- QuickTime and Nero chapter structures;
- sample tables.

A `moov` after `mdat` is valid QuickTime/ISO-BMFF and matters only for progressive network streaming, not for a local import. So 0.21.0 is not a compatibility regression. The device field stays "Apple Books sync not checked", as today.

## 4. Verification (no decode)

**Before the write**, with the original untouched:
- the held-handle full hash equals the reviewed sha256, and the same pass gives the planned output sha256;
- the plan;
- the probe profile;
- the chapters equal the frozen chapters;
- the source-relative packet and presentation evidence;
- the planned `covr` payload equals the reviewed cover bytes.

**After the write**, with the writer still held so nobody else can write:
- the profile and duration;
- the chapters;
- every approved tag;
- the packet and presentation evidence equals the evidence taken before the write.

**Final audio-untouched proof.** This runs under a READ|DELETE handle, held deny-writers through the rename. With the 4 type bytes reverted, `[0, original size)` must hash to the reviewed sha256. The tail must equal the planned `moov`, and the whole file must equal the planned output sha256. Last, as in the copy flow, the selected cover file is read again and must still hash to the reviewed cover ("Selected cover changed — review required"; Sergei, 2026-10-23: the fast path runs every check the copy flow runs). A refusal here undoes the edit, and the copy flow then refuses the same way.

**Integrity trade-off of no decode.** The copy flow decodes the source in full (`-xerror`, refusing "Full audio decode failed") and compares the source and output PCM. The fast path does neither, so a source with bitstream corruption inside its AAC frames is published instead of being flagged. The PCM comparison itself carries no information here: identical `trak`, `mvhd` and `mdat` bytes give identical decoder input. That check never fired in 358 preserved books.

What remains is:
- the container and sample-table proof (every chunk inside `mdat`, with no overlap);
- a complete packet listing;
- the byte proof.

The output is the original's own audio bytes, so no book gets worse; only an undecodable source goes unreported.

The cleanup contract (`source_cleanup._validation_contract`) accepts `publication_mode='in_place'` instead of decoded frames, but only with the in-place byte proof bound to the reviewed sha256.

## 5. Move, records and cleanup

**The move.** `merge_service._publish_in_place` records the same publication intent fields as `publish()`, then renames with `native_io.rename_no_replace`, the 0.20.2 handle-bound no-copy primitive. The publication goes through the same `checkpoint('publishing')` revision guard and the same guard under the review lock. The order differs from `publish()`: the in-place path commits the publication intent before it takes the review lock, while `publish()` commits it inside the lock, after the guard. `output_rename.RenameWorker` cannot be used, because it moves an existing publication generation.

**The guards.** After the edit, the size and mtime differ. The held DELETE handle shares READ only, so it excludes every opener that does not share DELETE, which in practice is most programs. So `build_manifest` and `enrich` take a `held` map for this job's source:
- the review data is compared as usual;
- the source sha256 must still be the reviewed one;
- the chapters come from the post-edit probe.

**The handle.** The rename's named-file proof shares READ and DELETE only, so the held DELETE handle cannot also hold WRITE. An undo before the move releases it and reacquires a writer.

**Records after the move.** `_check_output`, `verified_outputs`, completion and history are unchanged. Source cleanup gains `_retire_moved`:
- it needs the job's `published` journal row and its rename receipt. When a crash or a rename postcondition error after the rename left no receipt, it proves the move itself (`inplace_m4b.confirm_move`): the old path is absent and the job's current output hashes in full to the planned output. It then journals that receipt. Otherwise it refuses and retires nothing;
- the old path must be absent;
- it writes `cleanup_members` as `removed`, with `disposition: renamed_into_output` and no recovery copy, plus the `source_retirements` row;
- recovery retention records the set as `deleted` by actor `in_place`;
- the working-attempt discharge skips the snapshot proof (there is no snapshot).

**Counting.** The mode can be counted from `validation.encoding.selection = existing_m4b_in_place_metadata_edit` and the `inplace_edits` table. That table is additive; there is no schema migration. No UI shows the encoding mode, so the UI is unchanged.

## 6. Crash, NAS drop and check failure after the write starts

**In process.** Any failure after step 1, including a pause, undoes the edit:
- before any write, prove the file is the edited original: the same native file ID (a writer reopened by path is checked too), and one full read in which `[0, original size)` with the type reverted hashes to the reviewed sha256. That proof alone shows the undo restores the exact original, so the bytes past the original size are cut off without being judged, whether whole, torn, or zero-filled at full length by a power loss (0.21.0 F12). A file that fails either proof is left exactly as found, and the row becomes `unresolved`;
- truncate to the original size;
- write `moov` back;
- put back the download marker the edit removed, from its journaled bytes, as a new stream (0.21.1 m-3). A marker still present is left as it is. This comes before the write time, because writing a named stream moves the file's own write time;
- restore the ns write time and the attributes;
- re-read, and require the reviewed sha256.

Every value the undo uses is checked before its first write: any field the edit writes missing or of another type, a write time `restore_metadata` cannot set exactly, or attributes other than ARCHIVE or NORMAL make the row damaged, and nothing is written (0.21.1 F15, m-4).

After the undo, the copy flow runs (a pause stops instead). An undo that cannot reproduce the reviewed sha256 raises `Unresolved` and leaves the row `unresolved`.

**After a crash.** `AudioJobs._recover` calls `inplace_m4b.recover_all` at startup, when the queue is constructed, before the first scan. `_work_attempt` calls `clear` before any attempt on that source. A startup recovery that cannot settle an edit, or cannot read or write the journal at all, is not ignored. The interrupted book is marked needs attention with the reason, through the queue's existing attention path. The pre-attempt `clear` still refuses that source until the edit is undone.

| What recovery finds | Action |
|---|---|
| The original is still at its path | Undo, always proving the content first (one full read, as above). A share may report a new file ID after reconnecting, so recovery does not require the same ID; the content proof decides → `rolled_back` |
| The source path is absent and the destination hashes in full, under a deny-writers handle, to the planned output | `published`, with a recovered rename receipt that source cleanup accepts. A matching size alone proves nothing |
| The journaled library root itself cannot be seen, as when the library share is not reconnected yet (0.21.0 F13; 0.21.1 F17) | Nothing is recorded and the row stays open. The interrupted book restarts as usual, and the next start or attempt that can see the library settles it. That attempt is not refused: it cannot read the source either, and nothing writes to a source that differs from its review |
| Anything else: the library root is visible but neither the original nor the planned output is there, a book folder renamed or deleted included (0.21.1 F17); or the journal row is damaged (0.21.0 M1, 0.21.1 F15 and m-4) | `unresolved`: the job needs attention, other books continue, and recovery is retried at the next start or attempt |
| A row whose `job_id` or `attempt_id` is not text, which SQLite allows in this primary key (0.21.1 F16) | Damaged. Nothing is written or recorded, since the journal cannot address the row. Its own book needs attention (found by job, or by its source path before an attempt), and no other book is affected. Source cleanup proves no move from it |

A row written by 0.21.0 has no marker field. Its marker bytes then come from the marker removal receipt in its detail, when that is readable; otherwise no marker is put back, as in 0.21.0.

**Backup.** None is needed. Only the 4 known bytes are overwritten, and everything else lies past the original end of file. The journal row is the complete undo, so no full copy is ever made.

## 7. Re-hash cut (every book)

**Scope.** `source_proofs.attempt()` binds fingerprints to one job attempt on one thread. The first full hash in an attempt records the file's size, ns mtime, volume serial and file ID. A later revision check in the same attempt skips the re-read only on an exact match. These checks use it:
- the `build_manifest` revision guards at the publishing checkpoint and in `publish()`;
- the five `same_source` calls;
- the working-space admission hash.

**Strictness.** Any difference runs the old code path unchanged, with the same refusals. A change to the file ID alone forces a full hash, which then accepts identical bytes or refuses changed ones. Outside an attempt nothing is skipped.

**Kept in full**, because a deletion, a retirement or a copy depends on it:
- queue/admission `build_manifest`;
- the first check of each attempt;
- `copy_owned`'s hash of the snapshot it copies;
- source cleanup `_match` and the recovery-copy proof before disposition;
- the marker-removal validation;
- storage cleanup's check of retained originals;
- the in-place pre-write hash and byte proof;
- chapter repair, which runs outside attempts.

Replacement media jobs do run inside an attempt (`_work_attempt`), so their revision guards take the cut. That is harmless, because replacement sources are kept.

The existing guard semantics settle why a cheap identity is not enough for those. `review_backend.py` says size and mtime only *screen* a reviewed source and its content hash *decides*, and that Windows file IDs are not stable on the library's SMB share. A cheap identity therefore cannot be proven sufficient for a deletion.

**Residual risk** (accepted by Sergei): a change inside one attempt that keeps size, ns mtime and file ID identical is not seen by the skipped checks. It is still seen by the deletion proof, and the tests demonstrate both sides.

**Measured** (`test_source_proofs.WholeBookReadTests`, one real copy-flow conversion): full source hashes per source per book fell from 12 to 3.

| | Revision guards | Pipeline | Held handle | Total |
|---|---|---|---|---|
| Before | 5 | 5 | 2 | 12 |
| After | 2 | 0 | 1 | 3 |

## 8. Measurement and expected time (read-only, 2026-10-22)

**Pool.** The pool holds 853 unconverted single-M4B books, 338 GB in total.
- **Historical outcomes:** 87% of the 410 candidates that ever had a job completed through no-repair preservation; 1% needed a repair; 10% are legacy remux refusals now being retried on 0.20.3.
- **Header sample:** 28 of 30 files are clean on brand and tail. All 30 are on the output volume, and none is read-only or hard-linked.
- **Expected eligibility:** about 90% of the pool, about 770 books.
- **Overwrite inside the old `moov` padding** (the alternative layout, rejected): it would fit only about 5 to 17% of books. New metadata is larger in 97% of them, and 27 of 30 files have the `moov` at the front with little or no padding.

**Time per book now:** median 6.7 min, mean 8.4 min, over 352 books in continuous runs, measured start to next start.

**Fast path (estimate).** For a median book (445 MB, 9.7 h) the estimate is about 3.2 min, with a range of 2.5 to 3.5 min. Saved time is about 18.4 s per audio hour plus 0.077 s/MB. That figure counts:
- 1 f64 and 2 s16 decodes no longer needed (7.4, 1.8 and 1.8 s per audio hour, timed on a local fixture at idle priority);
- 1 further f64 decode, since this path does none;
- about 10 network passes;
- the local staging passes.

Two costs remain:
- about 2 to 2.5 min of fixed per-book overhead (catalog guards, post-completion bookkeeping, a 47 s queue gap);
- two packet listings (about 1.2 s per audio hour each).

Across the about 770 eligible books (about 6,200 audio hours) this saves about 38 h of about 108 h.

**Re-hash cut.** It removes 9 network passes per source per copy-flow book. A pass costs 0.0048 s/MB (the slope of the measured 'copying' stage) to 0.009 s/MB (uncached gigabit). That is about 19 to 36 s for a 445 MB book, and about 4 h over the about 730 books still on the copy flow.

**Also avoided:** about 1.2 TB of full-copy writes (Z: publication copies, local staging, C: recovery copies) for the in-place books.

**To measure once deployed:**
- the count of `selection = existing_m4b_in_place_metadata_edit` against `in_place.fallback` and `in_place.rolled_back` history entries;
- `inplace_edits` states, where any `unresolved` row is investigated;
- per-book start-to-next-start time against the baseline above.

## 9. Tests

`tests/test_inplace_m4b.py` (40 tests, in the check gate):
- damaged rows, generated (0.21.1, `DamagedRowTests`): from a row the edit really wrote, each key of its intent and of its detail (nested receipts included) is deleted and given a value of another type, and each key column is set NULL. Both world states (the edited original at its path; moved into its output) go through every reader: startup recovery, `clear()` before an attempt, and source cleanup's `published_move` and `confirm_move`. A damaged intent refuses only its own book with the damaged-record reason and writes nothing; a damaged detail never decides what the intent proves; the other book is unaffected. A field the edit starts writing is covered with no change to the test;
- every undo puts back the download marker it removed: in process, after a crash, and for a row 0.21.0 wrote; a marker that changed after the intent is not removed;
- a write time or attributes the undo cannot set writes nothing;
- an unreachable library root leaves the edit open, while a renamed book folder or a file moved by hand is a missing original;
- source cleanup retires an in-place book through the rename's own receipt, without proving the move again (0.21.1 F20);
- the eligible end-to-end path, byte-identical to the copy flow, whose byte proof satisfies the cleanup contract while a missing, unverified or foreign proof is refused;
- tags, cover and chapters on the published file;
- the download marker;
- a publication failure undone;
- every ineligibility with its fallback: ALAC, a repair, a replacement, a policy that keeps the sources, an existing destination, another volume, a foreign stream, read-only, a planner refusal, a changed hash, changed chapters, a post-write check failure;
- an oversized cover that makes the in-place attempt fall back is refused again by the copy flow;
- a crash at each of 6 write steps, recovered;
- a torn type patch;
- a real process kill after the rename, before its receipt: recovery proves the move and journals the receipt source cleanup requires;
- a destination of the right size but the wrong bytes is never recorded as the move;
- recovery and an in-process undo write nothing into a file rewritten in place (same file ID, foreign bytes);
- source cleanup retires nothing without a receipt or a provable move;
- an unprovable original that stays journaled and blocks;
- the queue itself reaches recovery: at startup it undoes an interrupted edit, and it marks an edit it cannot undo, or a journal it cannot read, as needs attention on the interrupted book; before an attempt it undoes the edit, or refuses the book, before the runner sees the source;
- the byte proof rejecting one changed audio byte;
- the full `MergeService` run (automatic approval, in-place move, cleanup, retention, Converted count, restart);
- the full `MergeService` run with a rename postcondition error after the OS rename: the book completes and its source cleanup completes.

`tests/test_source_proofs.py` (6 tests):
- an unchanged file skips the re-hash;
- a size, mtime or file-ID change forces the re-hash with unchanged strictness;
- a change keeping size, mtime and file ID is the accepted risk, and the deletion proof still blocks it;
- the whole-book count.
