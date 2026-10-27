# Books Arranger 0.22.1 / 0.22.2 backlog

**0.22.2 scope FROZEN (Sergei, 2026-10-26).** New feedback goes to the "0.22.3" section at the end of this file.

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

## 0.22.2 additions from Sergei (2026-10-26)

- **A deleted book's row stays on screen** (0.22.1, Sigma Force 9 "All files missing"). After Delete book it shows "Deleted. The book is gone from the app.", but the row is still listed with Scan again / View metadata / Source folders. Judy's spec says the row leaves on success and the list and counts drop within a poll. Find out whether the list cache (30 s) or the forced reload is skipped after Delete. The row must disappear at once.
- **«Ширли Джексон - Призрак дома на холме» says "Author missing"** (Sergei, 2026-10-26: "There was an author in the name.").
  - The tag credits the reader «Пухов Сергей», whom the rules map as a reader.
  - The row says "No author in the tags, file name or folder name." That's false: the title and file name start with "Ширли Джексон - ".
  - The Author field (prefilled "Jackson Shirley") is right, but the destination keeps "Ширли Джексон - " in the title: `Jackson Shirley\Ширли Джексон - Призрак дома на холме - Jackson Shirley.m4b`.
  - **Fix:**
    - when the only credited name is a reader, a leading "Person - " in the title/file name IS the author (Senua's W8 rule, with the reader case included);
    - strip it from the title;
    - don't ask.
  - The title should become "The Haunting of Hill House" (ruling 29: an English original).
- **«Пртоколы SCP. Сейф №1–3»** (Sergei, 2026-10-26): "This is a series 'SCP Protocols'. All 3 books are story collections. The Russian name is misspelled."
  - **Spelling:** the title should be «Протоколы SCP» (missing "о"). Record it as a lasting correction, like the author rules, so future scans of these files get the right spelling.
  - **Collections in a series:** these are three story collections forming the series «Протоколы SCP» (Сейф №1, 2, 3). A collection that belongs to a series files under Сборники with its series and position, using the existing series naming, e.g. `Сборники\Протоколы SCP\Протоколы SCP 1 - Сейф №1 - Разные авторы.m4b`. Ender confirms the exact pattern against the current naming rules.
  - **Editing on every row:** these rows ("Waiting for retry checks", repair) have no Title/Author fields, so Sergei can't fix the spelling himself. Every row should let him correct the title, author and series (Judy specs where).
- **The research run stops on SQLITE_BUSY** (2026-10-26, while researching «Свет Джедаев»). A cache-only `read()` writes (`_expire`) while the group rebuild holds the write lock for about 10.5 s, and nothing catches it. Fix plan and tests are in the builder brief. Separately, the "Pause audiobook jobs before starting automatic processing" rule waits on Sergei's answer.
- **«Джек из Тени» (Zelazny):** "Can't convert — M4B not supported", and the destination shows a Russian folder for an English author. Diagnosis is running.

- **Ruling 29:** translated books wait for their English title unless they were written in Russian. If no English title can be found, they convert under the Russian title.
- **Ruling 30:** "Вселенная …" folders become a Universe, laid out as Universe > Series > Book, like Warhammer. Detection is needed for new books; the 14 Дозоры and 5 Warhammer books already converted move in the rename pass.

## Universe routing miss (Sergei, 2026-10-25)

- `Z:\Audiobooks Sorted\де Клемешье Алекс\Сын Дога - де Клемешье Алекс.m4b`, converted 10-20, belongs to Lukyanenko's **Дозоры** universe. It was filed under its author alone, not routed into the Дозоры universe the way the 2026-10-20 Universe/Cycle routing decisions intend (Brief: "confirmed Universe/Cycle routing", 11 existing Дозоры/Warhammer routing decisions).
- To do:
  - find out why this book missed the routing;
  - fix detection for new books;
  - move this one (and any other misses) in the later rename pass (ruling 21).

## Later, by ruling 21

- The in-app "rename in Sorted" pass (`Docs/BooksArranger_SortedRenames_2026-10-24.md`).

## 0.22.2

**Sergei, 2026-10-26:** the updater items of the 0.22.1 QA and review move out of the 0.22.1 fix round (branch `ender/0221c`). None of them was started there. Sources: `Docs/BooksArranger_QA_v0.22.1_2026-10-26.md` (Futaba) and `Docs/BooksArranger_CodeReview_v0.22.1_2026-10-26.md` (Senua).

- **Futaba M-1 (Major): a failed install still closes the app.** In the real shell with a hidden window, an installer that can't start makes the shell exit with code 0 about 1.7 s after "Update now": no window, no relaunch, no message. Ruling 27 says a failed install reopens the old app with a clear line.
  - Futaba's reading of the cause: electron-updater 6.8.9's `quitAndInstall` queues `app.quit()` with `setImmediate`. The failed spawn is handled in the same turn, and `restartEngineAfterUpdate` sets `state.quit='none'` at once. The queued quit then reaches `requestQuit` while the old engine is still marked exited, which calls `finishExit(0)`. W7's hold stops the updater's fallback, not this quit.
  - Reproduce it in the real shell, not with mocks.
  - Found while reading the same path (not reproduced): the relaunch after a failed install reuses the launch's catalog mode. After a first-run "New catalog" in the same session that mode is `new`, and the engine refuses `new` on a folder that now holds the catalog. `restartEngine` already switches to `existing`; `restartEngineAfterUpdate` does not.
- **Futaba PA-1: a hidden-window real-shell update-failure test in the gate** (a fake feed, an installer that can't start), because the mocks pass while the real shell fails. Headless and focus-free. Notes for whoever builds it:
  - the gate has no Electron binary today (`node_modules/electron/dist` is not installed); the pinned `electron-v44.4.5-win32-x64.zip` is in the electron-builder cache;
  - the GitHub provider needs HTTPS: a self-signed certificate made by the test, `--host-resolver-rules` and `--ignore-certificate-errors`;
  - the tray icon leaves a `NotifyIconSettings` record per exe path, so the test's app copy needs a fixed path.
- **Restart to update with a conversion and an approval running took 99.1 s** (Futaba m-1; the conversion alone stops in 1.4 to 1.9 s). The conversion waited the whole 90 s safe-point window and was forced at 90.8 s. Find why the approval in flight holds it, and bound it.
- **Cancel update gives no feedback for up to 33.7 s** (Futaba m-2). Show immediate feedback with Judy's existing lines. Note: with a stalled worker the engine waits its 25 s resume bound before it answers, and it stays in `pausing` until then, so the page keeps its controls inert and Quit blocked meanwhile.
- **Senua W16:** an engine exit that lands during `restart()`'s lease close is never followed by a restart (`desktop/update-controller.js:183`, `:178`).
- **Futaba's updater Minors:**
  - m-3: an update soon after start on a large catalog waits on the engine's recovery pass (150 s at 8,000 books);
  - m-4: a download cut by `ERR_CONTENT_LENGTH_MISMATCH` reads the generic line, not "the connection dropped";
  - m-5: pressing the inert Restart to update while loading writes nothing to the message line;
  - m-11: the update dialog says a conversion "starts again from the beginning", but it comes back Paused and needs Resume audiobook jobs.

## 0.22.3 (new feedback after the 0.22.2 freeze)

- **Senua M5:** a wrong online match can create a bad learned author rule (strict match makes it rare). Add a page list of learned author rules with "Take back" (Judy specs it; the `retract_author_rule` route exists but nothing uses it).
- **Senua m7:** an author spelling from Approve is saved even when that Approve is refused.
- **Gate:** per-worker deadline and worker count (workers at 81–88%).
- **Futaba m-2:** with a cached FantLab record for a Cyrillic-only foreign author, the book gets its English title but a Cyrillic author folder (`Гроссман Лев\The Magicians`), and no author rule is learned. Ruling 39 says the folder should be English (Grossman Lev).
- **Quit can fail under load** (seen on 0.22.1, 2026-10-27): tray Quit showed "Books Arranger is still running. Quit could not be confirmed; ownership remains held. Request timed out". Quit must always work: stop the work safely, then exit, and never show a bare timeout. Check whether 0.22.2 already covers it.
