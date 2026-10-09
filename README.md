# Books Arranger — inventory prototype

Double-click `launch.cmd`, or run `python app.py` in this folder. Requires Python 3.10+ with Tkinter. Optional `ffprobe` on PATH reads audio tags; it is already available on the development machine. No package installation is required.

For the browser interface, double-click `launch-web.cmd` or run `python web_server.py`, then open **http://127.0.0.1:5210/** in the app's browser panel. The server runs locally on Windows and uses the same catalog and scanner as Tkinter. It only binds loopback and fails if assigned port 5210 is occupied; it never switches to another port. Run one interface at a time because they share an exclusive catalog lock. The visible version comes from `VERSION`.

The browser has Start/Stop/Resume, inventory search and pages, evidence details, canonical metadata review, and sorting previews. Library paths cannot be changed through HTTP. Source files and catalog databases are never served as downloads. Requests use a process-specific token plus host/origin checks. No cloud service or external dependency is involved.

Inventory counts and pages refer to source files, including individual chapter tracks and companions; they are not a distinct-book count. Book grouping, online metadata matching and merging are later steps. A transient browser transport failure shows a separate retrying notice and last-received status. A complete successful current-library poll clears only that notice, preserving review/action feedback and actual read-error counts/details. The notice does not imply that the scanner stopped.

Closing the browser tab leaves the server running. **Stop server** stops scanning safely and shuts down the owned service; Ctrl+C in its terminal also stops it. Scan checkpoints remain available on the next launch. `data/web-instance.json` records the live application's PID, instance ID and URL for identity checks; it contains no request token. Its identity endpoint is `/api/health`.

Select Audiobooks, Podcasts or Ebooks and click **Start scanning**. **Stop scanning** saves completed inventory and pending work. **Resume scanning** continues the saved queue, even after reopening the app. The first scan is not automatic. Subsequent completed scans discover arrivals and reuse metadata when size and modification time match. Files changed by the same size while retaining the exact modification timestamp require a future stronger integrity pass; this prototype does not hash entire audio libraries.

The sources are `Z:\Audiobooks`, `Z:\Audiobooks\Podcasts`, and `Y:\Books\Books`. Audiobook scans exclude the podcast subtree. `Z:\Audiobooks\Unsorted` is included and marked as arrivals; ebook files are eligible arrivals. Podcast episodes remain separate files. Companion images/transcripts and unsupported formats are inventoried without rewriting them.

Select a row to view existing metadata, its confidence and the proposed destination. Missing original-language/canonical-author evidence produces **Needs review**, never a fabricated translated title. **Review canonical metadata…** stores your verified choices in the local catalog and produces a path preview. This does not change source tags or files. Changed files invalidate prior review choices. Audiobook grouping/order and device compatibility remain future milestones.

All application state is in `data/inventory.sqlite3` inside the project; that folder is gitignored. Library files are opened only for reading. There is no conversion, moving, renaming, deleting, metadata rewriting, external metadata lookup, podcast feed download or audio playback in milestone 1.

If a root is unavailable, saved results remain visible and Resume retries after reconnection. Missing files are marked only after a complete error-free traversal. Symlinks and Windows junctions are skipped. Stop takes effect between entries/reads; a slow network directory read may still need to return first. Audio probes have a 15-second timeout. Unexpected exit leaves running tasks available for retry.

Run meaningful checks with `python -m unittest discover -s tests -v`. Test sources are created in temporary directories. Importing `app.py` does not open a window.

For fixture roots or a second catalog: `python app.py --roots-json scratch/roots.json --database scratch/pilot.sqlite3`. A roots JSON must contain exactly `Audiobooks`, `Podcasts`, `Ebooks`; never point the catalog database at a library source folder.

The web equivalent uses `python web_server.py --roots-json scratch/roots.json --database scratch/pilot.sqlite3` and the same strict port. HTTP safety, exclusive ownership and control-flow fixture checks are included in the unittest command above.

With Node.js available, `node tests/test_browser.js` exercises the actual frontend's unsaved-edit/source-refresh/stale-save flow without opening a window. Node is only used for that check; the application itself requires Python.

`node tests/test_connection.js` exercises the actual polling script through transport failure/recovery, stale-library and incomplete refresh responses, preserving review/read-error feedback and old-HTML compatibility. It also verifies explicit file/task units and intentional shutdown behavior.
