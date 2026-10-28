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

- **Done in 0.22.3 (2b8949e, 001b62d; Judy section 4):** **Senua M5:** a wrong online match can create a bad learned author rule (strict match makes it rare). Add a page list of learned author rules with "Take back" (Judy specs it; the `retract_author_rule` route exists but nothing uses it).
- **Done in 0.22.3 (2ad474a):** **Senua m7:** an author spelling from Approve is saved even when that Approve is refused.
- **Done in 0.22.3 (4fb1a54):** **Same author? answer on a refused Approve** (Sergei, 2026-10-27, the m7 pattern): the answer is taken back (a retraction by the app, never read as his Take back) and his other books are requeued only once the Approve is accepted.
- **Done in 0.22.3 (f795a98):** **Gate:** per-worker deadline and worker count (workers at 81–88%).
- **Done in 0.22.3 (f66d591):** **Futaba m-2:** with a cached FantLab record for a Cyrillic-only foreign author, the book gets its English title but a Cyrillic author folder (`Гроссман Лев\The Magicians`), and no author rule is learned. Ruling 39 says the folder should be English (Grossman Lev).
- **Done in 0.22.3 (d89cda8; 0.22.2 did not cover it):** **Quit can fail under load** (seen on 0.22.1, 2026-10-27): tray Quit showed "Books Arranger is still running. Quit could not be confirmed; ownership remains held. Request timed out". Quit must always work: stop the work safely, then exit, and never show a bare timeout. Check whether 0.22.2 already covers it.
- **Done in 0.22.3 (f55602a; the cause: the details panel's own chapter default for a multi-MP3 book counted as an unsaved panel edit):** **Edit names Save and Approve locked by an unseen edit** (Sergei, 2026-10-27, on «Джеймс Герберт - Крысы 1. Крысы»). Sergei typed Title The Rats, Author James Herbert, Series The Rats, Number 1 in the row's Edit names box. Save and Approve both stayed grey, and the only explanation was a tooltip: "Save or discard the edits in the details panel first." (`askPanelEdits` in `web/app.js`: `dirty`, or `trackDirty`, on the same book). Sergei did not knowingly edit the details panel. Find what marked it dirty. Possibly the two editors share state, so typing in the row box dirties the details panel and locks itself. Fix it so the row box's Save always works. If another edit really is pending, show the reason on screen next to the button, with a way to clear it, not only in a tooltip (rulings 28 and 35). Also, clicking the row did not open the details panel, so Sergei had no way to reach the "pending" edit and discard it. **It comes back after an app restart** with freshly typed values, so the row box most likely locks itself. Sergei has no workaround: this blocks the book. Workaround found: View metadata → Save there worked. **Seen again on a "Same author?" ask** (Sergei, 2026-10-27, «Крампус. Повелитель Йоля», Бром vs Бром Джеральд): with only a radio choice made, Approve was grey with the same tooltip. So the lock is not tied to typing names, and it is likely to hit any ask. High priority for 0.22.3.
- **Done in 0.22.3 (f66d591):** **Brom author mapping** (2026-10-27): «Крампус. Повелитель Йоля» goes to `Brom\…`, which is correct. Sergei: "Brom" (the author publishes under the single name). Remaining item: «Бром Джеральд» should also map to `Brom` and not get its own folder. The title also stays Russian; that is fine under ruling 29/38 (the English title comes with the rename pass).
- **Done in 0.22.3 (2b8949e, 001b62d; Judy section 1):** **Two editors for the same names** (Sergei, 2026-10-27): "Why do we have 2 menus that do the same thing? The first menu was good enough (except it didn't work)." The row's Edit names box and the View metadata panel both edit the same names. Ruled (40): one editor, the row box. View metadata stops being an editor. Judy specs it.
- **Done in 0.22.3 (2b8949e, 001b62d; Judy sections 2 and 3):** **Save in View metadata gives no feedback** (Sergei, 2026-10-27): after Save it showed "Saving" and then nothing for a while. Sergei could not tell whether it was frozen or working, and the book just disappeared from the list. It needs visible progress and a clear "Saved — filed to …" result (ruling 28).
- **Done in 0.22.3 (bde0ed6; the colon stays the path's "_", metadata.safe_name):** **"Series N. Title" names are flagged instead of parsed** (Sergei, 2026-10-27): "All the information was in the folders and files names. Why did this book need me in the first place?" Examples: «Джеймс Герберт - Крысы 1. Крысы»; «Профессия: инквизитор 1. Леди не движется» and «Профессия: инквизитор 4. Настоящие индейцы» (author Дивов Олег, already detected). The app sees the pattern ("Title unclear: the title starts with what looks like a series name and number") but asks Sergei instead of splitting it into Series / Number / Title itself. The proposed path also turns the colon into an underscore (`Профессия_ инквизитор 1. Леди не движется`) and keeps the series inside the title. Ruled (41): split automatically and file without asking. **Then (rulings 45, 46):** sibling folders decide the series («Мертвый ноль 7. Мертвый ноль» is book 7 of «Сновидения Ехо»), and «Сновидения Эхо» / «Сновидения Ехо» are one series spelled «Сновидения Ехо» (65b2381).

## 0.22.4 (Senua's 0.22.3 review: the minors left for later)

Source: `Docs/BooksArranger_CodeReview_v0.22.3_2026-10-27.md`. Fixed in 0.22.3 itself: M1 (1f80255), M2 and m4 (2be2d0b), M3 (7012da8), m1 (f93455c); from pass 2: M4 (9e8c0c1), m12 (565d912), m13 (6817bb3), m14 (a59914d) and m11; ruling 49 (6d7ec12); from pass 3: M5 and m16 with ruling 50 (3ecfd23), m15 (117044f) and the last m11 comments; from pass 4: M6 with ruling 51 and the `merge_service.py` m11 comment; from pass 5: ruling 52 (it narrowed M8 to sets: two siblings with the same name pattern still confirmed each other), M7, m18, m19 and the `local_identity.py` m11 comment; from pass 6: M8's sets with ruling 53, M9, m20 narrowed with ruling 54 (not closed: uncredited siblings and two album spellings of one book still voted), ruling 55's test, and m21's first half; from pass 7 and Futaba's 51caef1 QA: M10, M-1 (the rest of a set released after the run has ended), the set taking the series he corrected, m22, m20's remainder, and the m11 lines. From Futaba's 0.22.3 QA (`Docs/BooksArranger_QA_v0.22.3_2026-10-27.md`): M-1 (cd8973d), m-1 (2044249), m-2 (e6d9787).

- **m2:** the "Same author?" undo is not atomic. A crash between the answer's commit and the job (power loss, or Quit's 30 s kill during the file check) leaves the rule in force with no Approve, and his books answered by it wait for the next run's scan.
- **m3:** after a silent or refused Quit the shell closes the pipe and kills the host after 30 s, without waiting for `critical_sections`; `finish_shutdown` alone can take longer, so under load the kill is the likely end, and each forced stop leaves a `web-instance.stale-*.json` in the data folder. Consider a longer bound, or one that waits while critical sections are open.
- **m5:** while a Take back is pending, `pressTick` rebuilds the rules list every second, so a mouse press on a rebuilt button can be lost; `controls()` now re-renders from 2 s instead of 3 s.
- **m6:** `noteLeavers` takes any list answer requested after the press as "the reload": paging, filtering or searching right after a Save or Approve shows "It left this list" and Show it for a book that only left the view.
- **m7:** `loadAuthorRules` runs while the engine is still loading; the first read gets 409 and the list reads "unavailable" for up to 30 s after every start.
- **m8:** the chain resolution for every known author costs about 32 ms per `Rules()` at 8,000 job authors (2.6 ms before), repeated while converting because the cache key includes `audio_jobs` `max(updated)`.
- **m9:** the gate stops itself 580 s after its start but still checks the worker inventories and digests the runtime tree afterwards; a gate passing close to 580 s can end in the entry check's outer kill (592 s) instead of its own message.
- **m10:** `SERIES_SPELLINGS` is a code constant; every future ruling-46 pair needs a release. Sergei's other lasting answers live in the catalog.
- **Done in 0.22.3 (with the pass-2 fixes):** **m11:** comments that no longer matched the code: `desktop/main.js:362` (e6d9787), `scripts/python-check-batches.mjs:64-65` (copies up to 40 s; past that the gate total binds), `local_identity.py`'s "the odd-name check still asks" (rewritten with m12), `merge_service.py`'s "nothing takes the answer back once queued" and the Brief's rulings 45/46 row (rewritten with M4); pass 3: `author_rules.py`'s module and `Rules` docstrings (an app retraction is no 'none' row), its m13 comment (the book is marked, and m15 puts it back on the run) and `public_research.py`'s ruling-49 lookup (asked with the identity's author after the rules, as automatic filing asks).
- **Futaba 0.22.3 M-1, the open part (a product question):** a book of the same credit researched before the author rule exists (nothing cached, «Лев» reads as a Russian first name) is still filed in Cyrillic (`Гроссман Лев\Волшебная страна`). Should it wait for the rule, or move with the rename pass?
  - **Ruled (48, Sergei 2026-10-27: "B"):** don't hold it; it files now and the rename pass moves it to the English folder later.
- **Futaba 0.22.3 final pass:** the "Apollo 13: …" hold is labelled "Held — Title or author missing", but the question is really title vs. series. Judy to fix the label.
- **Judy, the series question's row (rulings 52 and 53):** the ask row shows only Title and Author; the Series and Number it files show only inside the Goes to path. Its reason line still reads "The title starts with what looks like a series name and number." although the Title field already shows the title without them. And the "Held — Title or author missing" label is wrong for every series question, not only "Apollo 13". Judy specs the row (the ask carries `split`: series, number, title). Since M10 (0.22.3), an Approve that answers an author question on a book whose series is still unconfirmed keeps the answer and files nothing; the row shows it as a refusal line ("Your answer is saved. The book is checked again with it, and its series is asked next…"), then the series question. Judy may want its own outcome there.
- **m21, the second half (Senua's pass 6):** an entered title that differs from the title the split left keeps the split's series beside it («Отряд Сигма - 1 - Отряд Сигма_01. Песчанный дьявол»). The first half is done in 0.22.3: a title or author he entered alone no longer skips the series question, so the row asks and the Goes to line shows the series. Fix: drop the split's series and number when the entered title differs from the split title (or split the entered title).
- **m17 (Ender's noted gap; Senua's pass 3 confirmed it, Minor):** if the list-row read fails right after an Approve's job is queued, the Approve stands but the queue doesn't start until the next Start, and the state reads "Paused" meanwhile. Rare; nothing is lost.
- **Ruling 49 note (Senua's pass 3, no finding):** Edit names can't keep a Russian title for a foreign book. Its editor reads the files' title, so a Save of «Волшебники» is "unchanged", and the next Approve files "The Magicians". Typing the title on the row at Approve does keep it.


### 0.22.3 final batch (2026-10-28; rulings 56–59)

Implemented for the next candidate, pending its entry check and delta QA/review: M11 saves an unchanged author/no-author answer before asking series; M12 removes set-wide release and corrected-series aliases (including an Approve series fix reaching other books); M13 leaves automatic runs stopped; M14 uses surname-first Cyrillic only in the correct language and preserves canonical English routing. Foreign Cyrillic keep is researched/asked for English again; unchanged Cyrillic approval cannot save another keep.

Deferred to 0.22.4: Senua m23 (no-author split name loses series/number), m9 (gate worker at 84% deadline), Judy series-question copy/layout notes, and optional set-wide answers (ruling57).


### Ruling 60 — bounded gate redistribution (2026-10-28)

Completed: five whole test modules redistributed across the existing nine workers; every case, serial-server grouping and the 540 s worker / 580 s gate / 600 s owned-entry limits remain unchanged. Candidate 3545d17 passed the canonical entry check: 1,916 Python cases and 143 Node cases, zero failures/errors/skips; slowest worker 516.8 s. Broader m9 weight/performance retuning stays deferred to 0.22.4. The preceding 30 s media-test timing failure and its 5/5 isolated checks are retained in the candidate handoff evidence.


### 0.22.3 corrective delta after packaged QA/review (2026-10-28)

M11: after an author answer, reset only the clicked book’s cached automatic hold to Pending; its unchanged file revision no longer makes Start skip the saved answer. Real automatic Held (until_change) regressions cover no author, ruling-33 spelling and two credits, including an unchanged sibling question. M13/ruling 56: human Approve saves/queues only and never resumes the audiobook conversion/cleanup queue; an unrelated paused job stays pending until explicit Start. Automatic processing inside an authorized Start still admits and converts books. Conversion fixtures now press Start explicitly; passive waits stay passive.

M15/ruling 59: a title, series, number or Cyrillic-author entry does not settle a foreign author’s English spelling requirement. Author lookup preserves a title Sergei actually entered; an author-only entry still permits a researched English original title. Ruling-57 comments now describe completed-Sorted confirmation and individual approvals, with no queued-job/global-alias/set-release claims. No deadlines or case coverage are reduced.

### 0.23.0 — inline series, Litres and confirmed anthology volumes (2026-10-28)

Rulings 62–64 extend the released 0.22.3 code. Author-decision rows expose the existing Author, Title, Series and Number draft directly, using one planner preview and one Approve. Untouched blank pairs and unchanged proposed Title/Author are omitted; explicit edits/clears retain their existing authority. Full Edit names shares those controls and keeps the inline answer valid while its broader data loads. Series-only edits retain a cached English original title (ruling 49); the English-author requirement remains (ruling 59). Approval still queues until Start and series answers remain book-local.

Litres is an optional final series-source fallback after the existing providers. Existing indexed discovery leads to query-free canonical Book/Audiobook pages; its robots-disallowed search and private APIs are not used. A matching main record supplies exact title and all authors, excluding readBy/related products; only the book-specific explicit series ordinal is accepted. Sources retain normal cache, pacing, body bound, pauses and citations. No research-version bump or blanket held-book reset activates it. Ordinary machine HTTPS returned 200 during research, but the actual DNS-pinned PublicClient check requested a source pause; successful production fetch is NOT yet claimed. The private cooldown is preserved.

The confirmed Калейдоскоп family groups story files by their exact numbered-volume folder and agreeing album. Different story authors are retained in original member metadata and existing credited-chapter style; the volume uses Разные авторы and the existing numbered-collection route. Playback order remains an existing order-review hold unless source numbering proves it or Sergei explicitly approves the shown/saved order. Generic mixed-author protection remains. Any reviewed/job-owned/frozen story reserves the whole known volume: no unprotected partial anthology or automatic ownership migration. Regrouping creates fresh evidence/identity and does not inherit per-story approval or manual evidence. Whole M4B chapter safeguards remain.

Focused evidence before the full entry check: 9 Litres parser/provider cases; 12 anthology/generic-protection cases; 2 R49/R59 controls; combined Author+Title+Series and Number real conversion and anthology reverse-order real conversion passed under the canonical owned supervisor. The real private catalog projection maps all 11 Калейдоскоп 4 sources and all 11 credits to one volume 4 with exactly Playback order uncertain and no protected-member conflict. Real-renderer headless screenshots cover light/dark appearance emulation and 1920/600/360 px viewports; controls are 37.5 px high, pair stacks below 408 px available width, and no horizontal overflow was observed. No actual new packaged app/tray launch is authorized by the old 0.22.3 OS-history exception.

Final affected-contract delta: 18 existing series-provider, backfill, source-credit and cache cases passed under the unchanged owned supervisor. The completed-job ownership regression also covers a protected story already absent from the active file catalog; its remaining stories do not form a partial volume. Unrelated 0.22.4 backlog work remains deferred.
