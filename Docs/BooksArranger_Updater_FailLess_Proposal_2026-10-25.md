# Books Arranger: why 0.21.1 could not update, and a fail-less updater for 0.22.1 (ruling 27)

Ender, 2026-10-25. This is a read-only diagnosis and a proposal. No code was changed and nothing is committed. All times are local (Israel, +02:00).

## 1. Cause

**The update request times out because the shell's timeout is shorter than the engine's idle check.**

- **The shell gives up after 5 s.** "Restart to update" calls `parkOwnedEngine` (`desktop/engine-update.js`). It sends `POST /api/desktop/update` through `request()` in `desktop/main.js` with the default 5 s socket timeout. If the reply takes longer, the shell throws "Request timed out", and that bare text is what Sergei saw.
- **The engine's check has no time limit.** On the engine side, `DesktopControl.prepare_update()` (`desktop_backend.py`) holds `control_condition` and runs `verify_idle(self.server.state('Audiobooks'))`. That is a fresh, uncached state computation, with no time limit: `merge.state()`, then `inventory.status()`, then automatic status. The Brief records that this read touches about 100 MB of the real catalog. The desktop status poll has a 4 s cap (`STATUS_ANSWER`) and a shared cache, but this fence has neither, because "restart/update fences stay fresh". On the 706 MB catalog that computation can outlast 5 s. Before the status-snapshot fix, the Brief recorded a 10 s poll on the real catalog.
- **The engine finishes the fence after the shell has stopped listening.** The handler keeps running after the shell disconnects. If idle is confirmed, it sets `closing=True` and phase `updating`. That is the only way the page can show "Parking the idle engine for update…", so the screenshot proves the engine accepted the fence. It then starts `_shutdown()`.
- **Nothing undoes the fence.** No code path resets `closing` or the phase, so 0.21.1's engine never "resumes". It ends one of two ways:
  - **(a) Clean exit with code 0.** The shell is no longer in update mode (`state.quit` was never set, because the POST threw first). `child.on('exit')` treats code 0 as a normal stop and calls `finishExit(0)`. The whole app closes and the installer never runs.
  - **(b) `finish_shutdown` fails.** The phase becomes `blocked`, controls stay refused, and the buttons are inert.
- **Why it "returned to normal after a minute".** Shutdown waits for workers, with a join of up to 20 s, and the exit watchdog adds up to 20 s more. Then the app closes. A relaunch shows only the tray icon for about 1.5 minutes before the window appears (section 4). That fits "it came back on 0.21.1 after about a minute". The engine cannot resume after this fence.

**Evidence on disk** (read-only: file times, the catalog opened with `mode=ro&immutable=1`, process lists; no HTTP call to the app, no stack sample):

- **Session 1.** The window opened at 20:27:44 (Electron `Session Storage/LOG.old`). The 0.22.0 installer finished downloading at 20:28:07 (`books-arranger-updater/pending`). The session ended before 20:57.
- **Session 2.**
  - The shell started at 20:57:33 (new `blob_storage` folder) and the window opened at 20:59:12.
  - The engine made 4 public-research requests (goodreads, fantlab) at 21:01:13–21:01:22.
  - The last catalog write was at 21:02:34.7.
  - At 21:02:46.58 the WAL was checkpointed to 0 bytes and `web-instance.json` was removed. That is the clean-shutdown signature: a crash leaves the record, which the next start sets aside as `web-instance.stale-*`, and no new stale record exists.
  - The shell profile was flushed at 21:02:54.97, a clean shell exit.
  - No installer had run at that point. 0.21.1 has no engine request log (`log_message` is silenced), so which control triggered this shutdown cannot be proven. The update fence that finishes after the shell has given up is the one path that closes the app with nothing visible on screen.
- **After session 2.** The installer copied itself into the updater cache at 21:05:36. The install folder changed to 0.22.0 at 21:06:01. 0.22.0 was running from 21:06:19 and seeded `author_rules` at 21:06:22. Sergei confirms he installed it manually and it works.

**"Check for updates → Request timed out".** The check never touches the engine. It runs only in the Electron shell (`electron-updater` asking GitHub). electron-updater's own socket timeout (60 s, `builder-util-runtime/httpExecutor.js`) produces exactly the same text, "Request timed out". The update panel also has a single message line (`u.error`), shared by check, download and install. So the text he saw was either a slow GitHub or network request, or the leftover message from the failed install. The screenshots cannot tell which, and the fix covers both (section 5).

## 2. Was the engine busy?

**Not with conversion, automatic processing or scanning.** From the catalog:

- `audio_jobs`: 506 completed, 148 needs attention, none running, queued or pending. The last conversion finished on 2026-10-24 at 05:54 UTC.
- `automatic_runs`: the latest run has been `Paused` since 2026-10-24 06:01 UTC.
- Both scans are completed.

**What it was doing:**

- boot work;
- page and status computations;
- some public research at 21:01.

The Restart button is only enabled when status reports idle. So the failure needs no busy engine: on this catalog, the fence's own fresh state computation is the slow part.

## 3. Does 0.22.0 have the same weakness? Can it update itself to 0.22.1?

**Same weakness: yes.** `git diff v0.21.1 v0.22.0` shows the updater code is unchanged: `desktop/*`, `web/desktop-ui.js`, `desktop_backend.py`, `desktop_host.py`, `desktop_update_lease.py` and `app_launcher.py` are all identical, and only the version in `package.json` moved. The same weaknesses remain:

- the 5 s POST against an uncapped state computation held under the control lock;
- no undo for the fence;
- the shell exits on code 0 when it is not in update mode;
- the Restart button is disabled whenever anything is busy.

**0.22.0 → 0.22.1 in-app update: not reliably.**

- **Busy engine** (a conversion, research or a scan): the button stays disabled until everything is idle.
- **Idle engine:** the fence can still take longer than 5 s on the real catalog, which repeats the failure.

**So the 0.22.0 → 0.22.1 step also needs the manual route:**

1. Right-click the tray icon and choose **Quit Books Arranger**. If a book is converting, choose "Quit after this book".
2. Wait until the tray icon is gone and Task Manager shows no "Books Arranger" entry.
3. Download and run `https://github.com/Gemanoneko/booksArranger/releases/download/v0.22.1/Books-Arranger-Setup-0.22.1.exe`. This is the same asset pattern as 0.22.0's `.../v0.22.0/Books-Arranger-Setup-0.22.0.exe`.
4. Open Books Arranger from the Start menu. The tray icon appears first, and the window follows after about 1.5–2 minutes.

**Settings, catalog and data survive a manual install:**

- The installer is per-user NSIS (`perMachine: false`, `deleteAppDataOnUninstall: false`).
- `desktop-settings.json` and `audiobook-sources.json` live in `%APPDATA%\Books Arranger`.
- The catalog folder is outside the install folder, and the shell refuses a data folder inside it.
- Sergei's 0.21.1 → 0.22.0 manual install has just confirmed this in practice.

## 4. Slow start, and why it starts in the tray

This is expected in 0.21.1 and 0.22.0, not a malfunction. Startup runs in this order (`startConfigured` in `desktop/main.js`):

1. The shell creates the tray icon.
2. It waits up to 3 minutes for the engine's `/api/health` to answer with the matching ownership proof.
3. Only then does it create the window.

So the tray icon is all Sergei sees while the engine boots: catalog lock, startup guard, stale-record check, and building the inventory and merge service on the 706 MB catalog. `--start-hidden` is not involved; the 0.22.0 shell's command line has no arguments.

Measured times:

- **Session 2 (0.21.1):** about 1 min 39 s from shell start to window.
- **0.22.0's first start:** 106 s of engine CPU in its first 2 minutes, including its one-time author-rules seeding.

Two things worth flagging. Changing either is Sergei's call:

- There is no "Starting…" window or tray tooltip during boot.
- The shell's 3-minute startup limit is getting close as the catalog grows. A boot longer than 180 s reports "The engine did not become ready within 3 minutes".

## 5. Proposal for 0.22.1: a fail-less updater (ruling 27)

### A. Check for updates: shell only, bounded, with its own message

- **Keep it engine-free.** The check stays entirely in the shell, as today: it never calls the engine and never waits on engine status.
- **Bound each attempt.** Wrap `checkForUpdates()` in a shell deadline of 30 s per attempt. Retry automatically twice, after 5 s and after 15 s.
- **Report a timeout plainly.** If every attempt times out, say so in plain words (table D). Nothing else changes.
- **Give each operation its own message.** Check, download and install each get their own message and a time stamp ("checked 21:04"). A new check clears only the check's message, so a failed install can no longer show up as a check result.

### B. Restart to update: always available, and the engine stops in bounded steps

1. **The button is enabled whenever an update is downloaded and verified.** There is no idle gate any more. If work is running, a confirm names it, for example: "Converting *Title*. It will stop and restart from the beginning after the update. Your source files are not touched." The wording is for Judy.
2. **The engine answers the request at once.** `POST /api/desktop/update` does no state computation in the request. Under the control lock it:
   - sets `closing=True`, so new work is refused;
   - records the request;
   - calls `merge.drain()`, `automatic.stop()` and `inventory.stop()`;
   - starts the park thread;
   - replies 202 in milliseconds.

   A repeated POST returns the current park phase, so the request is idempotent.
3. **Bounded wait for a safe point (`pausing`, proposed T_safe = 90 s).**
   - The book in progress stops at its next checkpoint.
   - Research stops at its checkpoint, and the scan stops.
   - Controls already admitted (an Approve, a Delete) finish. They are short.

   Status reports what it is still waiting for, by name.
4. **Then a safe forced stop (`forcing`), using the existing `stop_now` path** (the one used for Windows sign-out). The book in progress is abandoned and restarts from its saved state next time. FFmpeg children end with the engine's native Job. Sources are untouched, because conversion only reads them.

   **One exception: never interrupt a critical section.** These are:
   - the in-place M4B tag edit (`inplace_edits` journal; it writes inside an original, ruling 2b);
   - a source-cleanup disposal;
   - the Delete-book file loop;
   - a publication rename.

   The engine reports `critical: <name>` in status, and the forced stop waits for that step to end. Each one takes seconds.
5. **Last resort (proposed T_force = 60 s after `forcing`, and only when no critical section is open).** The native host ends the engine's Job, which it already holds. Committed catalog work survives in SQLite WAL, and jobs restart from their saved state. **Senua must confirm that every write path is crash-safe before this step ships.** If she cannot, the last resort becomes: cancel, name the worker that would not stop, and keep the app running.
6. **Cancel undoes the fence.** A new `POST /api/desktop/update-cancel` (or a park that ends `blocked`) sets `closing=False` and phase `running`, so the app really does resume. Today nothing resets either one.

### C. Shell side: the state machine owns the update, not an HTTP timeout

- **Enter update mode before sending the POST.** Any later engine exit with code 0 then means "go and install". This removes the "app closes without installing" path that hit Sergei.
- **A POST timeout is not a failure.** Send it with a 15 s timeout and retry it (it is idempotent). The engine may have accepted it already.
- **The engine's exit is the signal that counts.** "Done" is the native host reporting that the engine process has exited. Status polls only feed the progress line.
- **One overall bound: T_safe + T_force + 30 s (3 minutes).** When it runs out, send the cancel and show why (table D). The old app keeps running.
- **Install, then reopen.** Call `quitAndInstall(isSilent=true, isForceRunAfter=true)`, so the installer needs no clicks and reopens the new version on the same data folder. Today it is `isSilent=false`. Whether Sergei wants to see the installer is his call.
- **If the engine has exited but the installer does not start:**
  - this includes `quitAndInstallCalled` being false, a non-zero exit, or an antivirus block;
  - the shell restarts the old engine (`startBackend`) and says what happened;
  - today the shell is left with no engine in this case, because `child.on('exit')` returns early in update mode.

### D. Wording (draft for Judy; it replaces every bare "Request timed out")

| Situation | Message |
| --- | --- |
| Check: GitHub did not answer | "Couldn't reach GitHub to check for updates (no answer in 30 s). Your connection or GitHub may be down. Nothing changed. Try again later." |
| Check: up to date | "Books Arranger 0.22.1 is up to date (checked 21:04)." |
| Restart pressed while work runs | "Update now? *Title* is converting. It stops and restarts after the update. Your source files are not touched." [Update now] [Cancel] |
| Waiting for a safe point | "Stopping safely for the update: waiting for *Title* to reach a safe point (12 s of 90 s)…" |
| Forced stop | "*Title* didn't reach a safe point in 90 s. Stopping it now; it restarts after the update." |
| Installing | "Installing 0.22.1… Books Arranger reopens by itself." |
| Cancelled after the bound | "Update cancelled: *what* did not stop within 3 minutes. Books Arranger is running as before. Try again, or Quit and run the installer." |
| Installer blocked | "The installer could not start (Windows or antivirus blocked it). Books Arranger has reopened on 0.22.0. You can run the installer yourself: *path*." |

### E. Busy-engine test (Futaba)

**Setup:**

- Use the packaged 0.22.1 candidate in a QA profile with a private copy of the real catalog (`Docs/BooksArranger_RealCatalogCopy_QA_Recipe.md`) and fixture libraries.
- Serve the update from a local feed: a generic provider on localhost serving a "0.22.1-test+1" build. GitHub is never involved.
- Record SHA-256 of every fixture source file before each run.

**Scenarios.** Each must end on the new version, reopened, within its bound:

1. Idle.
2. Conversion mid-encode (FFmpeg running): it either reaches a safe point, or is forced and restarts next start.
3. An Approve in flight while automatic research runs. Make public sources slow with a 503/slow stub, so the approval lasts more than 5 s.
4. A scan running.
5. A slow fence. Use the real-catalog copy under load, so a fresh state takes more than 5 s. This proves no HTTP timeout ends the update.
6. An in-place M4B edit in progress. The forced stop must wait for it to finish, and the undo journal must be clean.
7. The installer blocked (rename it after verification, or deny execute): the old version reopens with the "Installer blocked" message.
8. Cancel while waiting for a safe point: the engine is back to `running`, and controls work.
9. GitHub black-holed during "Check for updates": the plain message appears within 30 s × 3 plus the back-off.

**Checks after every run:**

- the source SHA-256 values are unchanged;
- `PRAGMA integrity_check` on the catalog copy;
- no orphan `python.exe` or `ffmpeg.exe` processes;
- the data folder and `%APPDATA%` settings are unchanged;
- the interrupted job is pending or restarted, not lost;
- the elapsed time for each phase is recorded.

## 6. Open points

- **For Sergei:**
  - Is T_safe = 90 s right?
  - Should the update install silently?
  - Should the confirm offer "update after this book" as well as "update now"?
- **For Senua:** whether the last-resort Job termination (B5) is safe on every write path.
- **For Judy:** final wording for table D and the confirm dialog.
- **For Sergei's call (offer only):** a "Starting…" window during engine boot, and raising or removing the 3-minute startup limit.
