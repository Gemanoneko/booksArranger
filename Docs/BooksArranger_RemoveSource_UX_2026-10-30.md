# Books Arranger 0.24.0: remove a source folder, and the up-front warning on Choose folder (Judy, 2026-10-30)

Basis: ruling 73d (`Team/Docs/BooksArranger_Rulings_2026-10-24.md`: "Sergei should be able to remove a source folder inside the app, for example a retired NAS share. Judy specs it first") and 73e (my offer of an up-front warning on Choose folder); Part B of `Docs/BooksArranger_0.23.1_UX_2026-10-29.md` (sections 14, 15, 19: the destination block, `chooseMode`, tooltips); `Docs/BooksArranger_Brief.md`; a read-only look at `desktop/main.js` (`readSettings`, `configuration`, `restartEngine`), `desktop_settings.py`, `source_config.py`, `scanner.py` (`Inventory`), `destination_admission.py`, `audio_jobs.py` L1108-1140, `merge_service.py` L359-440, `destination_overrides.py` (`_inside_by_identity`, `UNCHECKED_*`), `web/index.html` (`#root`), `web/app.js` (L700, `chooseMode`, `updateDestination`, `clockNote`) and `web/desktop-ui.js` (the update confirm), on main at 35bc4b6. Nothing launched, nothing measured, no rects taken: every "by the code" below is a reading Ender confirms, and geometry is target geometry for Futaba. Spec only: no code, not committed. Paths and counts in mockups are examples (the paths are the two in `Docs/BooksArranger_DeletePaths_Audit_2026-10-24.md`); the engine supplies the real values.

**Timing and the warning's go-ahead come by relay.** The coordinator relays that Sergei set this to ship in 0.24.0 and said yes to the up-front warning. The rulings file still reads 73d "when it ships is not yet decided" and 73e "Explain me". Jane records both before Sully commits this doc.

**Scope line.** This spec says where the control lives, what it says and what Sergei sees happen to his books. What the engine stops, sets aside, writes and restarts is Ender's. Every new line hides when the engine sends no data for it. Nothing new to learn: no new color, font, token or animation; existing buttons, `field-help`, `--warning`, the in-house confirm dialog.

**Invariant, first and non-negotiable.** Removing a source folder never deletes, moves, renames or writes a file inside it, in Audiobooks Sorted, or anywhere else on disk. Its only writes are the source settings file and the catalog's own records. No cleanup, retention, probe or delete routine runs for it (checks 4 and 5).

## 1. What the code says (shapes everything below)

| # | Finding | Consequence for the design |
|---|---|---|
| F1 | The list lives only in `audiobook-sources.json` (`%APPDATA%\Books Arranger`), read once at start by `desktop/main.js` and handed to the engine. Its only writer, `desktop_settings.py --configure-sources`, is CREATE_NEW and refuses an existing file ("Existing or unknown desktop settings were preserved"). The page shows it as plain text lines in `<p id="root">` (`app.js` L700: "Source 1: …", "Output: …"). | There is a list on screen already: the control goes there. A change needs a new replace-in-place write (engine need E4). |
| F2 | `source_config.normalize_sources`: 1 to 32 sources, and **Source 1 must equal the fixed main Audiobooks root** (`scanner.DEFAULT_ROOTS['Audiobooks']`, `Z:\Audiobooks`; the Podcasts folder nests inside it). | **Source 1 can never be removed**; Source 2 to 32 can. The last-source case cannot happen. If the retired share is Source 1, this feature does not help him (question 1). |
| F3 | The engine reads the list once, in `Inventory.__init__`. The shell's `restartEngine` answers only while loading (`state.loaded` returns false) and reuses the settings read at start. | Applying a removal means a new engine launch with the list read again. The nearest existing path is Restart to update (stop at safe points, a bound, resume afterwards). The confirm must say so (section 3). |
| F4 | Lists and counts read `root IN (configured sources)` (`merge_service.py` approved query, `groups.py`). The catalog rows of a folder that leaves the list stay, unread. | Removal can hide without deleting. The folder, added back by hand, brings its books back with their saved state. |
| F5 | A pending job whose root is no longer configured fails `destination_admission.observe` ("Queued source root is outside current configured sources"); `audio_jobs.py` L1131-1135 turns that into needs attention **and `_stop.set()`: the whole queue stops.** | Queued jobs of the removed folder must be set aside before the new list goes live, or one removal halts every conversion. This is a safety need, not a preference (E5). |
| F6 | `_inside_by_identity` refuses **every** Choose folder when a source or the data folder is away and not provably absent, or reports volume serial 0. Only "no file index" is limited to folders on that drive. A retired NAS share on a mapped letter is "away" ("Connect the drive and try again": wrong advice for a share that is gone for good); an identity-less drive is no-serial (its copy ends "Source folders can't be removed in the app.", which this release makes false). | Both sentences change (section 6.4). Only the every-folder causes can be warned about up front (section 6.1). |
| F7 | The destination block already has `chooseMode` (ready / nobridge / picking / moving / queued / offline), `aria-disabled` instead of `disabled`, `DEST_TIPS`, and `aria-describedby` on the state line. | The warning is one more mode, not a new component (section 6.2). |

## 2. Decisions in brief

1. **The control is a "Remove…" button on each removable line of the Source folders list at the top of the page** (section 3). Not on book rows, not in a menu, not a settings page.
2. **Source 1 shows no button**, only "Main library folder. It can't be removed."
3. **One confirm dialog** (the in-house modal pattern: Cancel focused, Esc cancels) with counts, the safety sentence first, what stops, what is set aside, and "You can't add it back in the app." (section 4).
4. **Removing hides, never deletes.** Books, approvals, names and folder choices stay in the catalog; the books leave every list and count (section 5).
5. **Applying restarts the engine**, reusing the update's running-work wording; the result is a line in the list that survives the reload (section 4.3).
6. **Up-front warning (ruling 73e, yes):** when a source or the data folder blocks every folder, "Choose folder…" is `aria-disabled` with the reason as a visible line and in its tooltip, plus a "Show source folders" button that goes to the Remove control (section 6).
7. **Copy has one home, the engine**, for the blocked sentences; the post-pick refusal and the up-front line say the same thing (section 6.4).

## 3. Where it lives: the Source folders list

### 3.1 Placement

The list replaces the plain `<p id="root">` text in the "Library scan controls" panel, **for the Audiobooks library only**. Podcasts and Ebooks keep their one "Source:" line (they are not in the list and cannot be removed). It stays always visible, not folded into a `details`: the warning's button needs a target Sergei can find again.

Why here: the list is where Sergei already reads his sources (recognition over recall, Jakob). A per-book or per-row control would act on a library-wide property from a place that acts on one book, which Part B section 14 already ruled against for Choose folder.

### 3.2 Anatomy (target geometry)

```
Source folders
Source 1  Z:\Audiobooks
          Main library folder. It can't be removed.
Source 2  Z:\OLD_Audiobooks                                   [ Remove… ]
          Its drive can't confirm which folder is which, so no folder can be chosen for any book while it is listed.
Output    Z:\Audiobooks Sorted
```

- A list (`aria-label="Source folders"`): per source a label ("Source 1"), the path (`.path`, wraps anywhere, full path in `title`), then the button. Output stays a plain line below, as today; it has no control.
- `Remove…`: face with an ellipsis, as "Choose folder…" (more input follows). `quiet row-retry`, at least 96 x 32, 8 px gap. At a width under about 600 px the button wraps under its path and stays 96 x 32.
- Support lines are `.field-help` (13 px, `--muted`), shown only when the engine sends the fact: "Main library folder. It can't be removed." (Source 1); the blocked line of 6.5; "Not reachable now." (engine `reachable: no`, words not color).
- With more than six sources the list scrolls inside its own box (max height about 232 px, `tabindex="0"`, `role="group"`), the rule of Part A 3.3.
- **Numbers shift.** Removing Source 2 renumbers Source 3. Every sentence names the path, never the number.
- A list with only Source 1 (nothing removable) shows no button and no extra line: it reads as today.

### 3.3 Remove… states

| State | Face | Why / tooltip |
|---|---|---|
| Ready | Remove… | Stop using {path} as a source folder. No files are deleted. You confirm first. |
| Loading (ruling 28) | Remove… (`aria-disabled`) | Removing a source folder is available when loading finishes. |
| No desktop shell (browser launch, dev roots) | Remove… (`aria-disabled`) | Removing a source folder works in the desktop app. |
| Closing or an update installing | Remove… (`aria-disabled`) | Books Arranger is closing. / An update is installing. (the existing sentences) |
| Dialog open | Remove… | unchanged; focus is in the dialog |
| Applying | Removing… (`aria-disabled`) | Removing the folder. Running work is stopping safely. |

Nothing else is refused for being busy (ruling 35): a running conversion is named in the dialog and stops safely, it does not block the press. `aria-disabled`, never `disabled`, so the button keeps focus and its tooltip.

## 4. The confirm dialog and what follows

### 4.1 The dialog

The in-house modal confirm (the update confirm in `web/desktop-ui.js` L168-180 and the Delete book dialog): a `<dialog>`, `aria-modal`, labelled by its title, **Cancel focused**, Esc is Cancel, Enter acts only on the focused button. It opens at once; the counts arrive from a read (E1) and "Checking what is in this folder…" stands in their place, with the confirm button `aria-disabled`, until they do. Max height about 80% of the window; the body scrolls inside, the two buttons stay visible. In flow inside the dialog; nothing is positioned over anything.

```
Remove Z:\OLD_Audiobooks from your source folders?

Books Arranger stops looking for books there. Removing it deletes no files and keeps your saved approvals, names and folder choices.

 - 24 books from this folder leave the lists: 9 waiting, 3 queued, 12 finished. The finished audiobooks stay in Audiobooks Sorted.
 - 3 queued conversions are set aside. They won't run.
 - Books Arranger restarts its engine and reloads your books. That can take about a minute. Running work stops safely first: the conversion of {title}.
 - You can't add it back in the app.

[ Cancel ]  [ Remove from sources ]
```

**Why these faces.** "Remove from sources", not "Remove folder": the second reads as deleting the folder on disk, which is the one thing this never does. The title names the list it leaves, and the lead's first fact after the effect is "deletes no files".

**Line rules** (each line only when it applies; counts are the engine's):

| Line | Shown when | Rule |
|---|---|---|
| Books leave the lists | always | `0`: "No books are listed from this folder." One category only: "{n} finished books from this folder leave the lists." (waiting / queued the same way). Two or more: "{n} books from this folder leave the lists: {w} waiting, {q} queued, {f} finished." with the nonzero parts only. One book: "1 book from this folder leaves the lists." "waiting" is every book not finished and not queued (needs an answer, approved, held, stopped). |
| Finished stay | finished > 0 | Appended to the first line: "The finished audiobooks stay in {outputName}." (`outputName()`, as the app words it today.) |
| Queued set aside | queued > 0 (question 2's default) | "{q} queued conversions are set aside. They won't run." One: "1 queued conversion is set aside. It won't run." |
| Cleanups waiting | the engine counts any | "{k} cleanups of original files are waiting. They won't run, and the originals stay where they are." |
| Restart and running work | always | "Books Arranger restarts its engine and reloads your books. That can take about a minute." (the brief measured about 43 s to load on a copy of the live catalog, 2026-10-26.) When work runs, append "Running work stops safely first: {names}." from the update confirm's own name builder (`desktop-ui.js` L6-9, 95-110: the conversion of a title, the library scan, research, an approval, a cleanup), with its approvals sentence, "An approval in progress stops, and the book is not approved. Press Approve again afterwards." |
| Add back | always | "You can't add it back in the app." |

### 4.2 Faces and tooltips

| Control | Tooltip |
|---|---|
| Cancel | Keep this folder. Nothing changes. |
| Remove from sources | Remove {path} from your source folders. No files are deleted. |
| Remove… | section 3.3 |

Accessible names start with the visible face: "Remove {path} from source folders", "Cancel", "Remove from sources".

### 4.3 After the press

1. Cancel or Esc: nothing is sent; focus returns to Remove….
2. Confirm: the dialog closes, the button reads **Removing…** and, under that source, a line (role `status`): "Removing {path}… 0:07", through the existing `clockNote` ladder (clock from 2 s, "The app is busy with background work, so this takes longer." from 3 s, "Still waiting (n min)" from 60 s). Nothing else on the page is disabled; no timers, no toasts.
3. The engine restarts. The window shows the existing load strip (Working, Step 1 of 4). The old page is gone, so **the result cannot be a page-held line.** After the reload the list shows, under the Source folders heading, "Removed {path}. Books Arranger reloaded its books." (role `status`, from engine state, E7) for as long as that engine runs. The removed line is no longer in the list. Nothing steals focus.
4. **"Removed" appears only when the new engine runs with the new list.** A removal that did not happen never says it did.

### 4.4 Failures

Typed causes; the page maps each to its sentence (`--warning`, role `alert`, under the source line, "Remove…" available again). In every one, the list is as it was.

| Cause | Sentence |
|---|---|
| `write_failed` (the settings file could not be replaced) | Couldn't save the change. {path} is still a source folder. Nothing was changed. |
| `changed` (the list is not the one the page saw) | The source folders changed. Check the list and try again. |
| `main` (the engine refuses Source 1; the page never offers it) | {path} is the main library folder. It can't be removed. |
| `work_bound` (running work did not stop in time) | Removal cancelled: {what} did not stop in time. {path} is still a source folder. Press Remove… to try again. |
| `closing` / `update` | Books Arranger is closing. Nothing was changed. / An update is installing. Nothing was changed. |
| `engine_exit` (saved, the engine did not come back) | The load strip's existing Stopped state with Try again. The list is already saved; Try again loads it. |
| no answer from a busy engine | This hasn't been confirmed yet. The app is busy with background work, so it may still go through. Check the list in a moment. (existing) |

## 5. What happens to books, jobs and approvals

The default is the safe one: **hide, set aside, never delete.** Sergei's two judgment calls on it are questions 2 and 3.

| Thing under the removed folder | What happens | Where Sergei reads it |
|---|---|---|
| Files on disk: originals, converted audiobooks, working and recovery files | Untouched. No delete, cleanup, move, rename or probe runs. | Dialog lead: "deletes no files" |
| Catalog records: books, files, scan state | Kept, unread. They come back if the folder is added back (by hand today). | Dialog: "keeps your saved…"; "can't add it back" |
| Books waiting for him (asks, holds, stopped, approved and not queued) | Leave every list and count. Their names, answers, approvals and chosen folders stay saved. | Dialog line 1 and lead |
| Approvals | Stay recorded. The book is not listed, so nothing converts. | Dialog lead |
| Queued conversions | Set aside before the new list goes live; kept, not run (question 2). | Dialog line 2 |
| A conversion running | Stops at a safe point as in an update, then is set aside, not restarted. | Dialog restart line names it |
| An approval in progress | Stops; the book is not approved (the update's own sentence). | Dialog restart line |
| Finished books | Leave the lists with the rest (question 3); their audiobooks stay in the output folder. | Dialog line 1 |
| Source cleanup waiting (originals still to be removed) | Parked; never runs; the originals stay. | Dialog line, when any |
| Author rules and names learned from these books | Unchanged: they belong to authors, not to a folder. | none |

## 6. Up-front warning on Choose folder (ruling 73e: yes)

### 6.1 When it shows

When the engine reports that a source folder, or the app's data folder, blocks **every** folder choice.

| Cause | Blocks | In this section |
|---|---|---|
| No volume serial (`UNCHECKED_NO_SERIAL`) | every folder | Yes, the case Sergei named |
| Away: the place cannot be opened and is not provably absent (`UNCHECKED_AWAY`) | every folder | **Question 6, recommend yes.** The retired NAS share hits this first. Same layout, own copy (6.4) |
| No file index (`UNCHECKED_INDEX`) | only folders on that drive | **No.** Whether it applies depends on the folder he picks, which the page cannot know before the picker opens. It stays a refusal after the pick, with its engine sentence |

Whether the engine can tell before a pick is Ender's to confirm (E2). The page needs one state, not one per row.

### 6.2 Disabled or enabled: `aria-disabled`, with the reason in view

Decision: **the control stays on the row, face "Choose folder…", `aria-disabled="true"`**, with a visible line above it and the reason in its tooltip. Not enabled-and-warn: the picker would open, Sergei would choose, and the engine would refuse every choice he could make: work spent on an answer known in advance. Not hidden: Part B check 15 says every row with a destination has the control, and a missing control explains nothing. `aria-disabled`, not `disabled`: it keeps focus and its tooltip, as the nobridge and queued modes already do.

A press on the disabled control does nothing (the existing `aria-disabled` early return); the line and the tooltip are its answer, so a keyboard user reads them through `aria-describedby` without pressing.

| State of the engine's report | Choose folder… |
|---|---|
| `ok`, or not known yet | Enabled, no line. Not known is the normal first seconds after a start; the refusal after the pick (6.6) is the backstop. |
| `blocked` | `aria-disabled`, line, tooltip, link button |
| `blocked`, a move queued or moving, picker open | The existing queued, moving and picking tooltips win; the line still shows |
| No desktop bridge | The nobridge tooltip wins ("Choosing a folder works in the desktop app."); no line, since nothing could be picked anyway |

`chooseMode` precedence: offline, picking, moving, queued, nobridge, **blocked**, ready.

"Use computed folder" is not affected: on a book not yet finished it only clears a saved choice, with no picker and no check. On a finished book it moves the file back; if Ender's move path runs the same identity check (E9), that one press gets the same `aria-disabled` and reason.

### 6.3 Anatomy

In the destination block of every row that has the control, directly above the control group so the reason comes before the disabled button:

```
Goes to  Audiobooks Sorted\Без автора\Rak_Ed_Farrer_Met_Den_Osvobogdeniy.m4b
No folder can be chosen while Z:\OLD_Audiobooks is one of your source folders: its drive can't confirm which folder is which.
[ Choose folder… ]  [ Show source folders ]
```

- The line is `.field-help` (muted, 13 px; contrast already measured for the list: `--muted` on `--row-selected` 4.97). **Not `--warning`, and no `role`**: it repeats on every row, so it must neither shout nor create hundreds of live regions. `--warning` stays for the post-pick refusal and the Remove failures, which happen once.
- The group wraps; each button at least 96 x 32, 8 px gap; with a saved choice the group holds up to three buttons (Choose folder…, Use computed folder, Show source folders) and wraps without overlap. In flow only.
- `aria-describedby` on Choose folder… lists the line's id and the existing state line's id.

### 6.4 Copy (the engine's, one home; the post-pick refusal uses the same words)

Each blocker carries `why` (the row line, and the first sentence of the refusal) and `fix` (the second sentence, in the tooltip and the refusal). `{place}` is the full path.

| Blocker | why | fix |
|---|---|---|
| A removable source, no serial | No folder can be chosen while {place} is one of your source folders: its drive can't confirm which folder is which. | If it's gone for good, remove it under Source folders. |
| Source 1 (main folder), no serial | (same) | It is your main library folder, so it can't be removed in the app. |
| The data folder, no serial | The app's data folder is on a drive that can't confirm which folder is which, so no folder can be chosen. (the existing sentence) | none |
| Two or more | No folder can be chosen while {n} of your folders sit on drives that can't confirm which folder is which. | See Source folders for which ones. |
| A removable source, away (if question 6 is yes) | No folder can be chosen while {place}, one of your source folders, isn't available: the app can't tell whether a folder is inside it. | Connect the drive. If it's gone for good, remove it under Source folders. |
| The data folder or Source 1, away (if yes) | the same with their own place | Connect the drive and try again. |

The old `UNCHECKED_NO_SERIAL` ends "Source folders can't be removed in the app." That is false from 0.24.0 for every source but Source 1 and must go; the tests that assert it change with it. The old away copy, "Connect the drive and try again.", stays for the data folder and Source 1 only.

Tooltip of the disabled control = `why` + " " + `fix`. The row line = `why`.

### 6.5 The link to Remove

**"Show source folders"** appears in the group only when at least one blocker is removable (a source other than Source 1). Not for the main folder or the data folder: nothing could be done there. Press: the page scrolls the Source folders list into view and moves focus to the blocking source's Remove… button (the first one, when there are several); focus is visible. If the scroll target is already on screen, only the focus moves.

On the list's side, the same blocker has its own line under its path (section 3.2): "Its drive can't confirm which folder is which, so no folder can be chosen for any book while it is listed." Away: "Not reachable now. No folder can be chosen for any book while it is listed." Sergei reads the consequence next to the control that fixes it, whichever way he arrived.

Cancel or Esc in the dialog returns focus to Remove…. The page does not take him back to the row; the Remove… press is the end of that task, and a successful removal reloads the page anyway. After the removal the blocker is gone from the new engine's report, so the lines and the link button disappear and Choose folder… is enabled, with no press of his.

### 6.6 Truth and timing

- The report comes from a background check with a bound; **opening the page, a poll or a list never waits on a drive that is away.** Ender chooses the cache and when it runs (at the engine's start, after a source change, and again on a quiet interval).
- A refusal after the pick (cause `unchecked`) updates the report in the same moment, so every row flips to blocked without waiting for the next check.
- Blocked to ok, or back, while a row's control has focus: the attributes and the line change in place; the row is not rebuilt and focus stays (the standing rule).
- The post-pick refusal stays as the backstop for what the up-front check missed (a drive that dropped after it, an index-only refusal), shown as the engine sent it in the existing state line, now with the new `fix` sentence.

### 6.7 Tooltips

| Control | Tooltip |
|---|---|
| Choose folder… (blocked) | `why` + `fix` of 6.4 |
| Show source folders | Go to the list of source folders. You can remove one there. |

## 7. Copy sheet (single source; straight apostrophes)

| Where | String |
|---|---|
| Heading | Source folders |
| Source 1 line | Main library folder. It can't be removed. |
| Blocked source line (list) | Its drive can't confirm which folder is which, so no folder can be chosen for any book while it is listed. |
| Away source line (list) | Not reachable now. No folder can be chosen for any book while it is listed. (the second sentence only when it blocks) |
| Faces | Remove… / Removing… / Cancel / Remove from sources / Show source folders |
| Dialog | Section 4.1 (title, lead, line rules) |
| Applying | Removing {path}… {m:ss} + the ladder |
| Done | Removed {path}. Books Arranger reloaded its books. |
| Failures | Section 4.4 |
| Row warning | Section 6.4, `why` |
| Tooltips | Sections 3.3, 4.2, 6.7 |

## 8. What the UI needs from the engine (names assumed; Ender confirms)

- **E1. Preview read (the dialog's counts):** a read for one source path answering `{total, waiting, queued, finished, cleanups_waiting, running: [{kind, title}]}`. No writes; never waits on the drive.
- **E2. State:** `source_folders: [{path, number, main, removable, reachable: yes|no|unknown, identity: ok|no_serial|away|no_index|unknown}]` and `folder_choice: {state: ok|blocked|unknown, blockers: [{kind: source|data, path, cause, removable, why, fix}]}`. Cheap fields only; computed in the background with a bound (6.6).
- **E3. Remove request:** the source path and the list as the page saw it (a revision, for `changed`); answers accepted (with progress) or a typed cause of 4.4. The engine refuses Source 1 and any path not in the list.
- **E4. The write:** replace `audiobook-sources.json` in place and atomically (`desktop_settings._create` refuses an existing file today). Keeps the order of the others, keeps `audiobook_output_root` and no other key, passes `normalize_sources`. A failed write leaves the file as it was.
- **E4b. Apply:** the shell launches the engine again with the list **read again** (`restartEngine` answers only while loading and reuses the start's config). Stop running work at safe points as the update does, with its bounds; a stop that does not finish cancels the removal (`work_bound`) and leaves the file as it was.
- **E5. Set aside, before the new list is live:** the removed folder's pending and queued jobs and its waiting cleanups. Nothing may be left that hits `Queued source root is outside current configured sources` (F5). Kept in the catalog, not deleted.
- **E6. Lists and counts:** confirm that Audiobook Ready, Needs your answer, the approved count and every status line read only configured roots after the change.
- **E7. The notice:** `source_change: {removed, at}` in state, kept while the engine runs, so the line survives the reload.
- **E8. Copy constants** of 6.4 in `destination_overrides.py` (`UNCHECKED_NO_SERIAL`, `UNCHECKED_NO_SERIAL_APP`, `UNCHECKED_AWAY`), including the Source 1 variant; the tests that pin the old sentences change.
- **E9. For Ender to say:** does the move-back path of "Use computed folder" on a finished book run the identity check (6.2)?
- **E10. For Ender to say:** does the recovery-copy retention worker, which removes the app's own copies after 24 hours, neither run early nor stop for books of a removed folder? The dialog claims only that the removal itself deletes no files.

## 9. Implementation checklist for Ender (slices)

**Slice F: engine and shell (E1, E3 to E7).** The write, the apply, the set-aside, the preview, the state. Ships with G.

**Slice G: page, the list and the dialog.**
1. Replace `<p id="root">` for Audiobooks with the Source folders list of 3.2, from `source_folders` (E2); Podcasts and Ebooks keep the one line. Source 1 and the removable rows as 3.2; support lines hide with no data.
2. Remove… with the states and tooltips of 3.3 (`aria-disabled`, never `disabled`; inert while loading).
3. The dialog of 4.1 on the in-house confirm pattern, with the line rules, the name builder of the update confirm reused (no new strings for running work), counts from E1.
4. Applying and result lines of 4.3, the failure sentences of 4.4, the Done line from E7.
5. Only strings from section 7.

**Slice H: the warning (E2, E8).**
6. `chooseMode` gets `blocked` (6.2 precedence); the line, the tooltip and the `aria-describedby` of 6.3; no `role` on the line.
7. "Show source folders" (6.5): scroll and focus; present only with a removable blocker. **If H ships without F and G, the `fix` sentences and the button are left out**, since there is nothing to point to.
8. The copy of 6.4 from the engine's `why` and `fix`, used by the row, the tooltip and the post-pick refusal.
9. Tests: the live state shape; one fixture per blocker kind; the flip with focus on the control.

## 10. Checks for Futaba (committed build, seeded fixture, the live state shape, nothing on a real drive or NAS)

1. **List.** Audiobooks shows each configured source with its path; Source 1 has no button and the line "Main library folder. It can't be removed."; Source 2 and later have "Remove…"; Podcasts and Ebooks show their one line and no button; a list of one shows no button.
2. **Dialog.** Press Remove…: focus on Cancel; the counts equal a seeded catalog (waiting, queued, finished under the removed folder only; Source 1's books uncounted); every line rule of 4.1 appears for its fixture and hides for the others, with no "undefined" or "0".
3. **Cancel.** Cancel and Esc send nothing (stub dispatcher: zero requests) and return focus to Remove….
4. **No file touched (the invariant).** Fixture source folders hashed before and after a removal: identical, including no probe or temp file; a call-recording seam shows no cleanup, retention, delete, move or probe routine ran. The settings file after: the removed path gone, the others in order, `audiobook_output_root` unchanged, no new key. Control: the same recorder does catch a cleanup when a fixture book is cleaned up.
5. **Catalog kept.** Row counts of the catalog tables are equal before and after; the approved flags are unchanged.
6. **Lists.** After the removal no list, filter, count or Audiobook Ready entry shows a book of the removed folder; Source 1's books are all still there.
7. **Queue.** Seed a pending job of the removed folder ahead of a pending job of Source 1: after the removal the Source 1 job runs to completion and the text "outside current configured sources" appears nowhere. Control: the same fixture with the set-aside step disabled stops the queue, so the check can fail.
8. **Running work.** With a conversion and an approval running, the dialog names both; Confirm stops them safely (the update's bounds); a stub that never stops gives `work_bound`, "Remove…" is back and the file is unchanged.
9. **Failures.** One stubbed failure per cause of 4.4: its sentence, `--warning`, role alert, the list unchanged. "Removed" never shows when the engine did not restart with the new list.
10. **Survives.** After the reload the Done line shows; a second restart still has the folder gone; Source 1 refused by the engine if the page sends it (`main`).
11. **Warning, shown.** Fixture state with a no-serial source: every row with a destination block shows the exact line of 6.4 above an `aria-disabled` Choose folder… whose tooltip is `why` + `fix`; "Show source folders" is present; pressing the disabled control calls the picker stub zero times; the line has no `role` and is not `--warning`.
12. **Warning, kinds.** Source 1: no button, the "can't be removed" fix. Data folder: its own sentence, no button. Two blockers: the "{n} of your folders" line and the button. Away (only if question 6 is yes): its own copy.
13. **Warning, absent.** `ok` and not-known states: no line, enabled. No bridge: the nobridge tooltip, no line.
14. **Link.** "Show source folders" scrolls to the list and focuses the blocking source's Remove… (the first of several); Cancel returns focus to Remove…. After a fixture removal of that source the lines and the button are gone and Choose folder… is enabled with no press.
15. **Flip and backstop.** The state flipping with focus on the control changes attributes in place: no rebuild, focus kept. A refusal after a pick with `ok` shown updates every row to blocked at once and shows the new sentence.
16. **Rects** at 1440, 1024, 700 and 200% zoom: the list with 1, 3 and 32 sources and a 200-character path; the dialog with a long title and every line present; the destination block with the warning, a saved choice and three buttons: no two elements intersect, buttons at least 96 x 32, no horizontal scroll, focus ring not clipped, the dialog's buttons always visible.
17. **Tooltips and names** on every control of sections 3.3, 4.2 and 6.7 in the packaged window; the dialog labelled and described for a screen reader.

## 11. Questions for Sergei (one word each; the spec assumes the default)

1. **Which source is the retired one: Source 1 (`Z:\Audiobooks`) or a later one?** Source 1 is the main library folder and the code requires it (the Podcasts folder sits inside it), so it cannot be removed by this feature. Default: **later**. If the answer is "Source 1", this feature does not solve it and a different, larger change is needed. Answer "later" or "first".
2. **Queued conversions from the removed folder:** set them aside (kept, not run, nothing deleted), or refuse the removal until none is queued? Default and recommendation: **set aside**. Refusing would send you to dequeue each book by hand, for a folder that is gone. Answer "set aside" or "refuse".
3. **Finished books from the removed folder:** leave the lists with the rest (their audiobooks stay in Audiobooks Sorted, untouched), or stay listed in Audiobook Ready? Default and recommendation for 0.24.0: **leave**. Keeping them listed puts finished rows outside the checks that read the source list (Edit names, Choose folder, Delete) and is a larger change; nothing is lost, and the dialog states the count. If you miss them afterwards, "stay" is the first follow-up (offer 2). Answer "leave" or "stay".
4. **When does a removal take effect?** Now (the engine restarts at once, running work stops safely, about a minute to reload) or at the next start? Default and recommendation: **now**. With "next start" the list, the queue and the warning would disagree with the saved file until then. Answer "now" or "next start".
5. **Folders removed here: add back in the app, later?** Today the only way back is editing `audiobook-sources.json` by hand, and the dialog says "You can't add it back in the app." Default: **no, not in this release.** Answer "no" or "yes, spec it".
6. **Should the up-front warning also cover a source that is away (offline, unplugged, a share that no longer exists), not only one whose drive cannot confirm folder identity?** The away case blocks every folder in the same way and is the one a retired NAS share produces first; it currently says "Connect the drive and try again." Default and recommendation: **yes**. Answer "yes" or "no serial only".

## 12. Offers (not in this release)

1. **Add source folder…** in the same list, through the Windows folder picker, with the same checks as the file (overlap, 32 at most). It makes removal reversible.
2. **Finished books of a removed folder stay listed** read-only (Open book folder, View metadata) if question 3's "leave" proves too blunt.
3. **Remove from the row's warning:** a "Remove {place}…" button on the row that opens the same dialog without leaving the book. Not recommended while the list is one scroll away: a source-wide action on every book row invites mis-presses.
