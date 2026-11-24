# Books Arranger 0.31.x: UX spec, "loaded, status not here yet" and a refused Restart engine (Judy, 2026-11-24)

Spec only. No code written. Sections 8 (moved and missing finished books) and 9 (Keep files wording), both 0.31.1, were added later the same day. Builds on 0.22.1 section 3 (the load strip) and section 4 (busy engine); section numbers below ("3.4", "3.6") point there. Numbers in mockups are examples.

## In brief

1. **New state: Loaded, preparing the library status.** The strip never shows a step line after the shell says loading finished. It says so, with the one clock that matters (how long the status has been missing).
2. **No spinner, no stripe.** Nothing here can prove movement. The clocks carry the signal.
3. **Warning at 60 s** (Waiting at 10 s). Actions at the warning: **Restart Books Arranger** (new, Sergei's call: a full app relaunch, section 6), Copy details and Technical details. Restart engine is not offered: it cannot work after loading.
4. **A refused Restart engine answers beside the button**, in a one-line note inside the strip, with the real reason. It stays until the strip's state changes. It is never silent.
5. **Tooltips:** one sentence for the controls that stay inert in this state, and one for the new Restart Books Arranger button.

## What went wrong, in UX terms

Two lies on one screen. The strip said "Stuck, no progress for 1 h 7 min" about a step that had finished, and it offered a button that could never work and said nothing when pressed. Both come from one gap: the page had no way to know loading was done.

## 1. Loaded, preparing the library status

### 1.1 Decisions

1. **"Leaves the loading view" means the step view, not the loading mode.** After the shell's loaded signal the page keeps its placeholders and inert controls until the first status answer paints (3.6, 3.7: no control goes live before its data). Settling to "Ready" on the shell's signal alone would be the same lie reversed: Ready over a blank, inert page. **Ready appears only after the first status answer and the first list paint, as today.**
2. **Once the shell says loaded, the strip never again shows "Step n of N"** in this launch. The last loading answer is discarded at that moment, so "1,149 of 1,149 books" and "No progress for…" cannot come back.
3. **Time alone moves the state here.** 3.4 says a load that keeps moving can take ten minutes. This wait is different: it has no progress signal and a known short normal length, so the clock since "loaded" is the signal. The engine's answer-silence rule (3 s / 10 s) still applies on top; the worse of the two wins.
4. **The way out is Restart Books Arranger**, a one-press full relaunch (specified in section 6). It replaces Restart engine in this state because it works after loading. Quit Books Arranger still exists beside it.

### 1.2 The strip

Same `section#load-strip`, same place, same height behaviour (the strip keeps its settled min-height rule). Bar: **all segments done** (`--accent`), no stripe, no alert segment, because loading did finish; the state line carries the warning.

Working (under 10 s since loaded):

```
| Working · Loading finished. Preparing the library status.                     |
| [#######][#######][#######][#######][#######]                                 |
| loaded in 4 min 40 s · preparing status 0:07 · engine answered 1 s ago        |
```

Waiting (10 s to 60 s; no buttons, as in 3.3):

```
| Waiting · Loading finished. The library status is taking longer than usual    |
| (23 s). The engine is still answering.                                        |
| [#######][#######][#######][#######][#######]                                 |
| loaded in 4 min 40 s · preparing status 0:23 · engine answered 0 s ago        |
```

Stuck (60 s and more; `--warning` line, action row appears, the one height change):

```
| Stuck · Loading finished, but the library status has not arrived after 1 min  |
| 12 s. The engine is answering but still says the status is not ready. Your    |
| files are not touched. You can restart Books Arranger to try again.           |
| [#######][#######][#######][#######][#######]                                 |
| loaded in 4 min 40 s · preparing status 1:12 · engine answered 0 s ago        |
| [ Restart Books Arranger ] [ Copy details ]   > Technical details             |
```

### 1.3 Strings and timing

The clock starts at the shell's `loadedAt` (not at page receipt), so a reloaded window resumes the same count. The 5 s sleep guard of 3.4 applies to it. Thresholds live in `THRESHOLDS` beside the others: `statusWaiting: 10000`, `statusStuck: 60000`. Why 60 s, not the 30 s of load progress: the first status on a large catalog can legitimately take a while, and a false warning costs trust; the 2 min notice of section 4 is the ceiling.

| Sub-state | When | Word | State line ({x} = time since loaded) |
| --- | --- | --- | --- |
| Preparing | under 10 s | Working | Loading finished. Preparing the library status. |
| Slow | 10 s to 60 s | Waiting | Loading finished. The library status is taking longer than usual ({x}). The engine is still answering. |
| Not arriving | 60 s and more | Stuck | Loading finished, but the library status has not arrived after {x}. The engine is answering but still says the status is not ready. Your files are not touched. You can restart Books Arranger to try again. |
| Engine silent (answer clock) | 3 s / 10 s | Waiting / Stuck | Loading finished. The engine hasn't answered for {x}. / Loading finished. The engine hasn't answered for {x}. It may have stopped responding. Your files are not touched. You can restart Books Arranger to try again. |
| Status here, list on its way | first status answer to first list paint (normally under 1 s) | Working | Loading finished. Showing your books. |

- **Detail line** (14 px, tabular-nums, parts wrap between, never inside): `loaded in {m} min {s} s` (omitted if unknown) · `preparing status {m:ss}` · `engine answered {s} s ago`. The launch-based "running 1:12:09" and "last load took" are dropped here: the first made an hour look like work, the second repeats the first part.
- **Bar:** `aria-valuenow` = `aria-valuemax`; `aria-valuetext` "Loading finished. Preparing the library status." (Stuck: "Loading finished. The library status has not arrived.").
- **Duration format:** existing `duration()`.

### 1.4 The rest of the page while this holds

The strip owns the message line: section 4's "busy" notice stays suppressed (it needs a "Last update" that does not exist yet). Placeholders swap their word so nothing says "loading" after loading finished:

| Place | Working, Waiting | Stuck |
| --- | --- | --- |
| `#root`, `#status`, `#automatic-status`, `#research-status`, jobs lines | "{Name}: preparing…" | "{Name}: not ready yet." |
| `#empty`, `#page` | Preparing your books… | Your books are not ready yet. (skeleton bars removed, as in Stopped) |
| `#filter` single option | Preparing… | Not ready |
| `#automatic-start-reason` | Automatic processing can start when the library status is ready. | same |

Still no number for a missing part (3.5). Every control that 3.6 makes inert stays inert, with the one sentence of section 3 below.

### 1.5 Announcer, tray, details

- **Announcer** (existing polite region; counts and clocks never announced): shell says loaded, from any state: "Loading finished. Preparing the library status." Waiting: not announced. Stuck: "The library status has not arrived after {x}. Restart Books Arranger is available." (Restart engine is never mentioned.) Restart Books Arranger pressed: "Restarting Books Arranger." First status answer: "Books Arranger is ready." only; no "moving again" before it.
- **Tray:** unchanged ("Books Arranger"). A tray warning for this state is not specced.
- **Technical details** (State 1; raw engine text lives only here):

```
Loading finished: {ISO time} (took {m} min {s} s)
Library status: not received for {s} s
Last status reply: {raw text, e.g. Status is still updating; retrying}
Engine answered: {s} s ago
State: {working|waiting|stuck}
```

- **Focus:** if focus is on Restart engine when the state changes and the button leaves, it goes to the Status filter (the standing fallback of 3.7). No state change takes focus, plays a sound or raises a hidden window.

## 2. A refused Restart engine

### 2.1 Should it be offered?

- **Not in State 1, never after loaded.** The shell refuses it by design; a button that can only fail is worse than none. Restart engine shows only while the shell reports loading unfinished (and the 3.4 conditions hold). Try again (Stopped) is unchanged.
- **It stays visible but inert** only in the existing unsafe case (`restart_safe` false), as 3.4 already says.
- **Its replacement in State 1 is Restart Books Arranger** (section 6): a full relaunch does work after loading. "Check again" would be a placebo: the page already asks every 800 ms.

### 2.2 When a press is still refused

After the fix this is a rare race, but it must never be silent. The shell returns a reason with the refusal; the page shows one line.

- **Where:** a new `p#load-note` inside `#load-strip`, directly under the action row (so it follows the buttons whether or not the row is showing). `role="status"`, polite; the page does not also announce it. 14 px, `--text` (13.87:1), not `--warning`: nothing is wrong, nothing happened. No icon. Wraps; nothing overlaps.
- **Not in `#message`.** That line sits in the Library panel, below the scan controls (index.html:69), nowhere near the button. This corrects 3.6 for the strip's own buttons: the answer goes beside them. It applies to the inert press too (the NOT_SAFE sentence), which today also goes to `#message`.
- **How long:** until the strip's state word changes, Ready settles, or any strip button is pressed again. No timer: a note that vanishes while it is being read fails a slow reader. Focus does not move.
- **Order of events:** the page announces "Restarting the engine." only after the shell accepts, not before (today a screen-reader user hears it and then nothing).
- **After a refusal the page re-reads the shell's record** at once, so the strip shows the true state with the note beneath.

| Reason from the shell | Note |
| --- | --- |
| loaded (finished in the same moment) | Loading had already finished, so nothing was restarted. |
| restarting (double press) | The engine is already restarting. |
| quitting | Books Arranger is closing, so the engine was not restarted. |
| admission check running (inert press) | Wait for the data folder check to stop before restarting. (existing sentence, moved here) |
| unsafe (inert press) | Not safe right now: the engine is changing the catalog. Wait for it to finish. (existing sentence, moved here) |
| no reason given, or the call failed | Nothing was restarted. Your files are not touched. (the raw error goes to Technical details) |

## 3. Tooltips

One new control (Restart Books Arranger, section 6) and one new sentence for the inert controls.

| Control | State | Tooltip |
| --- | --- | --- |
| Every control that 3.6 makes inert (the three "Not yet" sentences) | State 1, any sub-state | Not yet: Books Arranger is preparing the library status. This works as soon as it is ready. |
| Restart Books Arranger | State 1 Stuck | Close Books Arranger and open it again. Loading starts over. Your files are not touched. |
| Restart Books Arranger, busy (`aria-disabled`) | after the press | Restarting Books Arranger… |
| Restart engine | while loading is unfinished | unchanged: Stop the engine and start it again. Loading starts over. Your files are not touched. |
| Copy details, Technical details | State 1 Stuck | unchanged |
| Quit Books Arranger | State 1 | unchanged; see check 8 |

The new sentence joins `notYetSentences`, so a press on an inert control writes it to `#message` (as 3.6) and it clears at Ready.

## 4. What Ender needs to provide

1. A `loaded` flag and `loadedAt` (ms, same clock as `startedAt`) in the shell's startup record; `lastLoadMs` already exists. Push on change and answer `startup()` with it, so a reloaded window resumes.
2. `restartEngine` resolves `{started:true}` or `{started:false, reason}` with the reasons of 2.2.
3. The page's "first status answer" means the first successful `/api/state` carrying a status; a 503 counts as "heard" only.
4. The two new thresholds in `THRESHOLDS`; the state line and detail line in `load-state.js` (pure, tested), the swaps of 1.4 in the placeholder `word`.
5. A preload call and shell handler for the relaunch of section 6 (name for Ender to confirm; the page asks, the shell does it), returning `{started:true}` or `{started:false, reason}`. It reuses the Quit path and the app's existing relaunch for updates; it adds no new way to end the engine.

## 5. Checks for Futaba (stub engine that answers `/api/state` with 503 "Status is still updating; retrying" after loading finishes)

1. 0 to 10 s: Working line and detail line as 1.2; no `Step n of N`; no spinner or moving stripe; no buttons.
2. 10 s: Waiting line, no buttons. 60 s: Stuck line, action row with Restart Books Arranger then Copy details (no Restart engine, no Try again), `--warning` line, bar still all done.
3. Placeholders read "preparing…", then "not ready yet." at 60 s; every inert control's tooltip is the new sentence; a press writes it to `#message`.
4. Release the 503: "Loading finished. Showing your books." then Ready; no step line in between.
5. Reload the window mid-wait: it returns to State 1 with the same clock, not Step 1.
6. Race a Restart press against the loaded signal: the note of 2.2 shows under the strip, focus lands on the Status filter, no "Restarting the engine." announced.
7. Narrow width and 200% zoom: lines wrap, no overlap, no horizontal scroll; light and dark unchanged (no new tokens).
8. Quit Books Arranger in State 1 (Stuck): closes without a long wait. The relaunch of section 6 rides the same path, so it must not wait either.
9. Section 6: press Restart Books Arranger in State 1 Stuck with no book converting: no question, the window closes, a new window opens at Step 1 without taking focus, the running clock restarts, "last load took" is still shown. Press it twice fast: the second press is answered by the note. Press it with a book converting (stub): the native question appears; Cancel changes nothing.

## 6. Restart Books Arranger (Sergei's call, 2026-11-24)

Sergei answered the two questions of the first draft: **yes** to a one-press relaunch in the Stuck state; **no** to browser mode (`launch-web`), which he does not use, so this spec leaves it out entirely.

| Part | Spec |
| --- | --- |
| Label | Restart Books Arranger |
| Element | `button#load-relaunch`, native, `type="button"`, the primary look of Restart engine (`--accent` on `--on-accent`), at least 96 x 32 px, wraps, `aria-disabled` when busy (never `disabled`) |
| Shown | State 1, Stuck only (both Stuck rows of 1.3). Hidden in Working, Waiting, the loading views and Ready. Never beside Restart engine: they exist in different states |
| Placement | In the strip's action row, **first, directly left of Copy details**: `[ Restart Books Arranger ] [ Copy details ]   > Technical details`. It takes the slot Restart engine has in 0.22.1 3.3. Tab order: this button, Copy details, Technical details. No accelerator |
| Tooltip | Close Books Arranger and open it again. Loading starts over. Your files are not touched. |
| Face and tooltip once pressed | Restarting… and "Restarting Books Arranger…", `aria-disabled="true"`, focus stays; a second press is answered by the note below |
| Announcer | "Restarting Books Arranger." once the shell accepts the press (as in 2.2, never before) |

**Confirm: none from the page.** It follows Quit's own rule and Restart to update (0.22.1 2.4): a question only when a book is converting. In State 1 the page has no status, so it cannot know; the shell asks, as Quit does.

1. **No book converting, or the shell's own status does not answer** (the usual State 1 case): no question. The press starts the relaunch at once. This is Sergei's standing rule that Quit must always work (0.22.3).
2. **A book is converting:** the existing native question, reworded for a restart. Title "Restart Books Arranger". Message "Restart after the current book?" Detail "{Title} finishes converting first, then Books Arranger closes and opens again. Queued books stay queued." Buttons "Restart after this book" and "Cancel"; Cancel is the default and Escape. No page overlay, so no hit-area change. Cancel returns the button to its ready face; it is not a refusal and shows no note.

**What happens on press** (Ender confirms the mechanism; the sequence is the UX contract):

1. The button takes its busy face at the press; the page announces it once the shell accepts.
2. The shell stops the engine the way Quit does (engine told to stop, bounded, then ended through its pipe; the book in progress stops safely and converts again next time), then **closes the app and starts a new copy of it**. This is a full relaunch of the process, not the engine-only restart of Restart engine.
3. The new copy opens its window at once, visible but **without taking focus** (the show-inactive behaviour of 0.22.1 3.2), on the load strip at Step 1, with the running clock restarted and "last load took" kept. The old window is gone; nothing else moves.
4. No sound, no toast, no raised hidden window. The tray tooltip follows the new launch.
5. If the new copy cannot start, the update restart's own failure handling applies (0.22.1 2.6); Ender confirms it covers this and reports back if not. A relaunch that vanishes with no window and no message is the one outcome this spec forbids.

**A refused press** shows the note of 2.2 (same `#load-note`, same lifetime). One reason applies to this button: Books Arranger is already closing, a Quit or relaunch is under way: "Books Arranger is already closing." Any other failure: "Nothing was restarted. Your files are not touched."

## 7. Noticed, not specced

- `index.html` has 4 bar segments and `aria-valuemax="4"`, while `load-state.js` says 5 steps (0.29.0). At "Step 5 of 5" no segment is current.
- `engineStopped` in the shell ignores an exit after loading, so this strip shows nothing for it; section 4's rule (the shell closes the app with its own message) is assumed. Ender to confirm Try again can never show after loaded.

## 8. Moved and missing finished books in the status line (0.31.1, approved by Sergei)

A finished book in Audiobooks Sorted is done to him. Two things can now happen to it without him touching the app, and the status line says each, so he sees it is happening:

1. He moved it by hand: **at the next launch or Start** the app finds it again (same name, file ID, size and hash) and records the new location. Not mid-session; Sergei accepted that (2026-11-24), so the page shows nothing between the move and that pass.
2. It cannot be found (no match): the app removes it from its records. Catalog only; no file is touched. (Ruling 2026-11-24; it replaces "no flag, debug line only".)

**Which "status bar".** The Audiobook jobs status line, `#jobs-status`: a badge, then parts joined by " · " (0.31.0 1.3). Confirmed by Sergei. Not `#status` ("Library status", the scan's counts).

### 8.1 The two parts

| Question | Moved book found | Missing book removed |
| --- | --- | --- |
| Copy, one | **1 moved book found, new location saved** | **1 missing book removed from the list, library files untouched** |
| Copy, several | **5 moved books found, new locations saved** | **4 missing books removed from the list, library files untouched** |
| Count format | `toLocaleString()`: `1,200 moved books found, new locations saved` | the same |
| How long | **10 minutes** after the latest find | **1 hour** after the latest removal |
| Names the book or folder | No | No |
| Look | Plain text like its neighbours: same size, colour and weight. No icon, not `--warning`, no notice box, no toast, no sound, no tray text, no window-title change | the same |

- **Where.** The last parts of the status line, after "background look-ups left": found first, removed second, so the stable parts keep their places.
- **Both in one pass.** Two parts, each with its own count and its own clock, separated by " · " like every other part. They are never merged into one sentence: the first says where the books went, the second says what was forgotten, and each keeps its own reassurance. Example:

```
[All done] · 0 need attention · 1,506 converted out of 1,506 approved books · 2 moved books found, new locations saved · 1 missing book removed from the list, library files untouched
```

- **A burst.** A later find (or removal) inside the time adds to that part's count and restarts its time. After the quiet time the part goes and its count starts again at 0. Neither part is dismissible, neither is carried into a later session (a find the launch pass itself makes does show), and neither shows while the line reads "Last confirmed —" (a count that old cannot be trusted). The clock starts when the pass that found the books finishes.
- **Why removal stays longer.** A found book costs him nothing; a removed record he cannot see happen. It is the one change he may need to notice after coming back to the window. An hour is a cue, not a record (8.2).
- **Words.** "moved" and "found" are plain; "missing" is the word of the existing "All files missing" row status; "removed from the list" is the existing "Remove from list" meaning (the catalog entry, not the files).
- **"Library files untouched", not "no files touched" (Senua M3, amended).** The first version was not true: the removed book's own recovery copies and working files are deleted by a later background sweep (Sergei's ruling: a removed book leaves nothing behind). What is never touched, by the removal or the sweep, is his library and source files, so that is the claim. "Library" is the app's word for the whole collection, source folders included ("Library status", "library drive"). The source-removed line's "No files were touched." stays true for its own pass and is not changed here. The sweep has no copy on the page: it is the app tidying its own leftovers, and the engine log keeps its lines.
- **Announcer and tooltip.** The line's own polite region, as for any part that changes; no extra announcement. No tooltip: they are not controls.

### 8.2 Copy details and Technical details

- **Moved book found.** The startup strip's Copy details and Technical details carry nothing: the strip is gone by the time a relink shows. The book's own Technical details (`#technical-details`, `technicalText(row)`) carry one line, the last relink, kept across restarts until it is relinked again:

```
Technical detail: Found again after a move outside the app (22 Nov, 14:05). Was in {old path}. Now in {new path}. Matched by name, file ID, size and hash.
```

  Its Copy details copies it with the rest. Nothing new on the row. If the details panel does not show Technical details for a finished book, Ender reports back; no new panel is invented.
- **Missing book removed.** Nothing: the book has no row left to carry a Technical details line, and the strip's are not involved. The trace is the engine's own log, one normal-level line per removed book (title, recorded path, time), not debug. Question 1 offers a visible record. Two strings the engine writes say the same corrected thing (Senua M3), both short and true:

| Where | Today (not true) | New |
| --- | --- | --- |
| Job reason, a record text (`finished_removal.py`) | Finished book not found; removed from the list. No files were touched. | Finished book not found; removed from the list. Library and source files were not touched. The app's own recovery copies and working files for it are deleted later. |
| Engine log line (`_removal_log`) | Finished book removed from the list (not found; no files touched): {title} (was {path}) | Finished book removed from the list (not found; library and source files untouched): {title} (was {path}) |

  The job reason names the later sweep because it is a record read by someone looking for what the app did; the log line does not, because the sweep writes its own lines. Ender confirms the job reason reaches no list or panel on the page; if it does, it reads as written.

### 8.3 When the app refuses to remove

The app does not remove when too many books are missing at once, or when the library folder cannot be reached: a missing NAS looks exactly like a thousand missing books. Then nothing is removed, and one calm line says so.

**The line:** **Missing books were not removed. Check that the library drive is connected.**

- **Where.** A new `p#jobs-removal-note` directly under the status line, above the book candidate counts, in the Audiobook jobs panel. It is a sentence with an action, so it is not a part of the " · " list, where it would be missed.
- **Look.** 15 px, `--text` (13.87:1), normal weight. Calm: no `--warning`, no icon, no "stuck", "error" or "failed". `role="status"`, polite, rewritten only when its text changes. No button, no tooltip.
- **One line for both causes.** He does the same thing either way, so the words are the same and the line does not say which. The cause, if the engine knows it, goes to the engine log.
- **How long.** It is a state, not an event: it shows while the engine's last removal pass was refused and goes at the first pass that completes normally. No timer, not dismissible. It is not shown at launch before a pass has run, and not while the status line reads "Last confirmed —".
- **A second line for the same cause is accepted.** The Library panel already has one line per source folder that does not answer ("... isn't available. Its books stay on the list. Check that the drive is connected." with Check again). The two answer different questions and clear on their own; if both show for one cause, both stay.
- **"Drive", not "NAS".** The app says "the library drive" (and "the drive") in every existing line about this. Sergei's word was NAS; it is the same thing on screen, and one word per thing is the copy rule. Question 2.
- **Announcer:** the line itself, once, when it appears. Not when it goes.

### 8.4 What Ender needs to provide

1. In the state the page reads: `relinked: {count, last_age_ms}` and `removed: {count, last_age_ms}`. `count` is the finds (removals) since that burst began, back to 0 after its quiet time; an age, not a timestamp (as `progress_age_ms`). The page hides a part at count 0 or when the age reaches its time (found 600000 ms, removed 3600000 ms; two named constants).
2. `removal_refused: true|false`, true from a refused pass until the next normal pass. Ender tells Judy how often a pass runs: if the line can outlive the drive's return by more than about a minute, add the existing Check again button (as in the Library panel) and report back.
3. Per book: its last relink as `{at, was, now}`.
4. The two parts in `statusParts`, last, with the existing `plural` helper. The removal itself and its "too many" threshold are Ender's; this spec does not set them.
5. Ender confirms that a missing finished book is removed in the same launch or Start pass that finds a moved one (8.1 and checks 3 and 4 assume it); if not, say which pass, and the checks follow.
6. The corrected strings: the page part (`statusParts`, the removed part), the job reason and the log line (8.2). Nothing else on the page says "no files touched" for a removal.

### 8.5 Checks for Futaba (seeded fixture library, nothing real, no real NAS)

1. Move one finished book by hand and do nothing else: mid-session the page does not change (no part, no flag, no message, no count). Press Start (or relaunch): when the pass finishes the line ends with "1 moved book found, new location saved"; nothing else changes.
2. Move two, press Start: "2 moved books found, new locations saved". Move a third and press Start again within 10 minutes: "3 moved books found, new locations saved", and the 10 minutes restart; 10 minutes after the last pass the part is gone. Relaunch: a part from the earlier session is not shown; a book moved while the app was closed shows once the launch pass finds it. Stub 1,200: "1,200 moved books found, new locations saved".
3. Delete one finished book's files: "1 missing book removed from the list, library files untouched"; the book leaves the list; no library or source file is touched (names and sizes before and after). Four: "4 missing books removed from the list, library files untouched". The part stays for an hour, then goes. After the background sweep the book's own recovery copies and working files are gone; that is expected, and the page says nothing about it. The job reason and the engine log line read as in 8.2.
4. One move and one missing in the same pass: both parts, found first, in the order and wording of 8.1.
5. Stub the library drive unreachable (and, separately, too many missing): nothing is removed, no removal part shows, the line of 8.3 shows under the status line, calm look; it goes at the next normal pass.
6. Make the engine silent: the status line reads "Last confirmed —" and no part and no refusal line shows.
7. Open a relinked book: its Technical details line shows both paths and the date; Copy details copies it.
8. Narrow width and 200% zoom: both parts and the line wrap, nothing overlaps; light and dark unchanged (no new tokens).

### 8.6 Questions for Sergei

1. **Should a removal leave a name list?** The Library panel already has one line for books removed because their source files are gone: "Removed N books whose files are gone. No files were touched.", with Details (titles and paths) and Dismiss. Routing finished-book removals into it (the engine adds them to `source_check.removed_list`) gives him names and a durable line at no new design; the status part stays as the short cue. My recommendation: yes. Default in this spec: no, the status part and the engine log only.
2. **"Check that the library drive is connected", or "NAS"?** Default: "library drive", the app's existing word.

## 9. Keep files after the no-recovery-copies ruling (0.31.1, Sergei 2026-11-24)

The ruling: published books keep no recovery copies, and it overrides "Keep files is permanent" (2026-10-18). The engine already does it (commit `c4e8a50`): a kept book's recovery copies go through the same verified purge once its audiobook verifies, and stay while it does not; for "Original changed since checked" they go by the background cleanup after the first status, a few books per pass (9.3). Keep files still keeps the book's originals and its folder (no cleanup of originals; no rename, move, series or name writes). Pressing it still deletes nothing and starts no job.

### 9.1 What the code says today

| Where | Today | Verdict |
| --- | --- | --- |
| Label (`rowActions.keep`) | Keep files | **Still accurate.** "Files" now means the originals and the folder; the app calls the backups "recovery copies" everywhere else (Delete recovery copies…), so the two nouns do not clash. A rename would cost habit, tests and the queued-press wording for no gain |
| Tooltip (`ready`) | Keep this book's files and stop flagging it. Nothing is deleted. | **False.** Recovery copies are still deleted |
| Pending face and note | Keeping… / Keeping these files… | Accurate |
| Refused | Keep files was not accepted. Check the status above. | Accurate |
| Kept row hint (`KEPT_HINT`) | Files kept at your choice. | Too wide: reads as if the copies are kept too |
| Details panel line | You chose to keep these files. | Too wide, same reason |
| Group hints (`attentionCopy`: changed, missing, unverified) | Recovery copies are kept until you decide. | **False.** He no longer decides |
| Confirmation line | none | Stays none (9.2) |
| Code comment at the `keep` action | "the kept recovery copies stop being flagged" | Stale; Ender updates it |

### 9.2 New wording

| String | New |
| --- | --- |
| Tooltip (amended: true for every group) | Keep this book's originals and folder as they are, and stop flagging it. It does not keep recovery copies. |
| Kept row hint | Kept at your choice: originals and folder stay as they are. |
| Details panel line (amended) | You chose to keep this book's originals and folder as they are. This does not keep recovery copies. |
| Group hint, "Original changed since checked" (amended, 9.3) | The app left this original in place. Recovery copies are not kept. |
| Group hints, "Audiobook missing" and "Audiobook not verified" | Recovery copies are kept until the audiobook is verified. (unchanged: here the copies are the only source until it verifies) |

- **The row hint is short on purpose.** It shows on a kept row in any filter, long after the copies are gone, so it must stay true. The tooltip and details line now say only what the button does and does not do ("It does not keep recovery copies"), not when the copies go: that differs by group (9.3), and a schedule in a tooltip would be wrong for one of them.
- **The group hints sit beside the button**, so they must not suggest the button decides the copies. Each says what is true for its own group.
- **No confirmation, still.** The press deletes nothing and queues nothing; what it no longer prevents would happen anyway, and the tooltip says so before the press. A dialog would make a safe press look dangerous.
- **Unchanged:** label, pending face, refused line, order and sizes in the row (0.16.8 spec section 3). Tooltips and hints only; no layout change.

### 9.3 "Original changed since checked" once its copies are gone (Sergei's ruling, Ender's finding)

My first sentence ("kept until the audiobook is verified") was wrong for this group. Its copies are deleted too, under the no-copies rule, by the background cleanup after the first status, a few books per pass. So for a while after launch the copies may still exist, then they are gone; the row must read true in both moments.

- **What the group is, now.** It was flagged because an original no longer matches what was checked, so the app held that book's source cleanup. The copies were the stake in the decision. With them gone, nothing is left to recover; what remains is one original the app will not remove, still in the library folder. The group is no longer "decide about the backups". It is **"an original the app left in place."**
- **Title:** unchanged, "Original changed since checked". It is still the reason.
- **Hint** (before and after the copies go): **The app left this original in place. Recovery copies are not kept.** No schedule, so it is true during the minutes before the cleanup reaches the book and after.
- **When the copies are gone:** the details panel's existing Recovery copies panel says it ("Recovery copies deleted automatically."); no new string. The row, its two buttons (Keep files, and Open folder) and their order do not change.
- **What the one choice is.** Keep files stops the flag and protects the original and the folder from the held-cleanup sweep and the rules writers. He can also open the folder and deal with the file himself. Neither touches recovery copies.
- **Does the row stay in Needs attention?** As built, yes, until he presses Keep files. Question 1 asks whether it should.

### 9.4 Question for Sergei

1. **Once its copies are gone, should "Original changed since checked" leave Needs attention by itself?** The copies were the reason it asked for a decision; what is left is an original the app already leaves alone, so the flag now only costs him a press of Keep files per book. It matches "a finished book is done". My recommendation: yes, it leaves by itself (the original stays untouched, as if kept). Default in this spec: no, it stays until he presses Keep files, as built.

### 9.5 Noticed, not specced

- The Recovery copies panel and "Delete recovery copies…" with its dialog stay accurate ("permanently deletes these backups"); they will simply show less often.
- The automatic policy notice ("Once a book is verified, its backup copies are deleted right away.") already agrees with the ruling.
- The 0.16.8 attention spec's Keep files rows ("Nothing is deleted", "Files covers both") are superseded by 9.2.

### 9.6 Checks for Futaba

1. Hover Keep files on a changed, a missing and an unverified row: the new tooltip, exact.
2. The group hints: "Original changed since checked" reads "The app left this original in place. Recovery copies are not kept."; the two audiobook groups read "Recovery copies are kept until the audiobook is verified."; none says "until you decide".
3. Press Keep files: no dialog; the pending face; the row leaves the groups; the kept row hint and the details line read the new text.
4. Seed a kept book whose audiobook then verifies: its recovery copies go, and the hint and details line are still true.
5. Seed an "Original changed since checked" book with recovery copies: its hint reads the same before and after the background cleanup removes them; afterwards its Recovery copies panel says they were deleted automatically; the row still shows Keep files and Open folder, and stays in Needs attention until Keep files is pressed (unless Sergei answers question 1 with yes).
