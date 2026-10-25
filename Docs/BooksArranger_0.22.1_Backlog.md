# Books Arranger 0.22.1 / 0.22.2 backlog

**UPDATE (Sergei, 2026-10-25 night): 0.22.2 is folded back into 0.22.1.** Everything below ships in 0.22.1.

**Earlier release split (superseded):**
- **0.22.1** is ONLY the lock/speed fixes and approving on local identity at once (items 7 and 8 and their diagnosis below). Release it first.
- **0.22.2** is everything else: the updater, startup (ruling 28), queued Retry and Delete, busy-page copy, Delete on all-missing rows, and the Minors.

These are Sergei's 0.22.0 feedback and the carried items. Collected by Jane; work starts when Sergei says so. Rulings are in `Team/Docs/BooksArranger_Rulings_2026-10-24.md`.

## Sergei's feedback on 0.22.0

1. **Updater must not fail** (ruling 27). On 0.21.1, "Restart to update" timed out after 5 s, the engine shut down cleanly, and the shell exited without installing. Proposal: `Docs/BooksArranger_Updater_FailLess_Proposal_2026-10-25.md` (Ender).
2. **"Queue Retry"** (Sergei, minor bug, 2026-10-25). While another operation runs, Retry is disabled with the tooltip "Another operation is in progress.", e.g. on the Макс Фрай rows "Stopped — ready to retry". Sergei wants to press it anyway and have the retry queued, so that it runs when the current operation finishes.

3. **Queue "Delete book" too** (Sergei, 2026-10-25: "Do same for Delete Book"). When Delete is blocked (a scan is running, another operation is in progress, "being processed"), Sergei can still confirm it, and the delete runs once the blocker finishes.
   - **Safety:** every check runs again at execution time: own files only, inside a source root, not in Sorted, files still match what the dialog listed.
   - **If the book changed in the meantime,** the queued delete is cancelled and the row says so. Nothing is deleted from a stale list.
   - Judy specs the "queued" state and copy for both Retry and Delete.

4. **Slow start (Ender, 2026-10-25).** The tray icon appears first. The window appears only after the engine boots: about 1 min 39 s on 0.21.1 with a 706 MB catalog. The shell gives up if startup passes 3 minutes, and the catalog keeps growing, so this needs a faster start or a progress window before it hits the limit.
5. **The 0.22.0 → 0.22.1 update itself must be done manually** (0.22.0's updater is the same as 0.21.1's): tray Quit, wait until no process remains, then run the installer. Give Sergei these steps with the release.

6. **Delete book fails on "All files missing" rows** (Sergei, 2026-10-25, Засор and Sigma Force 9). The rows showed "Connection interrupted", and the next press showed "Local server unavailable". Diagnosis is in progress. Sergei just wants such rows gone.
7. **Clicks must never time out behind background work.** On the first 0.22.0 run, three passes ran at once (re-checking 506 finished books, updating series on 375, researching 2,065). The status poll, the list and Delete timed out.
8. **Approval should not wait for optional online lookups** (if the diagnosis confirms it does). Under the rulings, title + author from local data is enough; series position etc. get filled in later.

**Diagnosis of 6–8 (Ender, 2026-10-25):**
- The engine was alive but overloaded. `progress_books` holds `inventory.group_lock` while it does about 500 `PublicationBindings.lookup` calls, and that reruns on every research or series step. The list, Scan again, Remove from list, Delete and approvals all queue behind it (the list took 54–100 s).
- Approval DOES wait for the optional `_gap_fill` lookups (5–7 s per site plus 10 s downloads, and requeues up to 3×).
- Research runs at about 0.5 books/min, so the 1,554 remaining books would take 45–60 h.
- The blocking 506-book re-check runs on the approval path (`approve_automatic` → `resume()`, 4–5 min, under `operation_lock`).
- Series backfill shares the per-site request limits with research.

**Fixes:**
- release `group_lock` before the publication lookups (a separate read connection, cached);
- Scan again, Remove from list and the delete check read without the write transaction or regroup;
- approve on local identity at once and fill optional fields later, in the background;
- move the 506-book re-check off the approval path;
- on the page, a timed-out press while health answers reads "busy", not offline (Judy spec §4);
- add timing tests.

9. **"Order unclear" on a perfect book, with a WRONG proposed order** (Sergei, 2026-10-25). The book is `Z:\Audiobooks\James Rollins\Sigma Force\2. Map of Bones\`: 240 files named `Роллинс Джеймс - Кости волхвов - 001..240 - Kosti_001..240.m4a`, in perfect sequence.
   - The row says "Some track tags aren't plain numbers". Its proposed playback order starts 07, 09, 18, 21, 27, which are the files with a different modified date (3/7/2020) and odd track tags. Approving that order would build a scrambled book.
   - **Fix:** when the file names form one clean continuous 1..N sequence, they decide the order, whatever a few odd tags say. Never propose an order that contradicts a clean file-name sequence.
   - **Identity:** use the folder structure `Author\Series\N. Title`, so this book is James Rollins, Sigma Force #2, "Map of Bones" (English original, ruling 16). Today's "Goes to" says `Rollins James\Кости волхвов - Rollins James.m4b`.

10. **"1986" goes to Без автора** (Sergei, 2026-10-25; in 0.22.1 with item 9). The file is `Z:\Audiobooks\JESPER ERSGARD\JESPER ERSGARD - 1986.m4b`; its tag credits the reader «Илья Сланевский». Sergei's author rule already maps Сланевский to Ersgard Jesper.
   - The row says "Part of a bigger book: This file is named as one chapter.", the Author field is empty, and the destination is `Без автора\1986.m4b`.
   - **Fix (a):** the author comes from the file name and folder ("JESPER ERSGARD - …" in folder "JESPER ERSGARD"), and the seeded author rules apply (reader → real author). Без автора is only the last resort, when no local source names an author.
   - **Fix (b):** a single file whose title is a number ("1986", "1408") is a whole book, not a chapter, unless real sibling parts exist.
   - **Fix (c):** the Author field shows the author the app resolved, not an empty field.

## Carried from QA and review (Minor)

- **Futaba m-10:** focus after Delete on Stopped rows (about 1 in 3).
- **Futaba m-14:** the strip vanishes when the last row of a chip is deleted.
- **Futaba m-15:** "Remove this copy" stays hidden after a refusal while Sorted was away, until the next scan.
- **Senua N18:** Delete's "folder holds no other book" check misses a book in a subfolder, or an unknown audio format.
- **Senua N19:** "Remove this copy" reads the book twice over the NAS under locks, with a 120 s page wait.
- **Senua E1–E5:** entry-context script hardening.
- **Senua m6:** retracting an author rule.
- **Futaba observations:**
  - a conversion that loses the Sorted drive mid-run stops with no Retry;
  - the first scan after a dropped root ends "failed".

## Universe routing miss (Sergei, 2026-10-25)

- `Z:\Audiobooks Sorted\де Клемешье Алекс\Сын Дога - де Клемешье Алекс.m4b`, converted 10-20, belongs to Lukyanenko's **Дозоры** universe. It was filed under its author alone, not routed into the Дозоры universe the way the 2026-10-20 Universe/Cycle routing decisions intend (Brief: "confirmed Universe/Cycle routing", 11 existing Дозоры/Warhammer routing decisions).
- To do:
  - find out why this book missed the routing;
  - fix detection for new books;
  - move this one (and any other misses) in the later rename pass (ruling 21).

## Later, by ruling 21

- The in-app "rename in Sorted" pass (`Docs/BooksArranger_SortedRenames_2026-10-24.md`).
