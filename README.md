# Books Arranger — inventory prototype

Double-click `launch.cmd`, or run `python app.py` in this folder. Requires Python 3.10+ with Tkinter. Optional `ffprobe` on PATH reads audio tags; it is already available on the development machine. No package installation is required.

Select Audiobooks, Podcasts or Ebooks and click **Start scanning**. **Stop scanning** saves completed inventory and pending work. **Resume scanning** continues the saved queue, even after reopening the app. The first scan is not automatic. Subsequent completed scans discover arrivals and reuse metadata when size and modification time match. Files changed by the same size while retaining the exact modification timestamp require a future stronger integrity pass; this prototype does not hash entire audio libraries.

The sources are `Z:\Audiobooks`, `Z:\Audiobooks\Podcasts`, and `Y:\Books\Books`. Audiobook scans exclude the podcast subtree. `Z:\Audiobooks\Unsorted` is included and marked as arrivals; ebook files are eligible arrivals. Podcast episodes remain separate files. Companion images/transcripts and unsupported formats are inventoried without rewriting them.

Select a row to view existing metadata, its confidence and the proposed destination. Missing original-language/canonical-author evidence produces **Needs review**, never a fabricated translated title. **Review canonical metadata…** stores your verified choices in the local catalog and produces a path preview. This does not change source tags or files. Changed files invalidate prior review choices. Audiobook grouping/order and device compatibility remain future milestones.

All application state is in `data/inventory.sqlite3` inside the project; that folder is gitignored. Library files are opened only for reading. There is no conversion, moving, renaming, deleting, metadata rewriting, external metadata lookup, podcast feed download or audio playback in milestone 1.

If a root is unavailable, saved results remain visible and Resume retries after reconnection. Missing files are marked only after a complete error-free traversal. Symlinks and Windows junctions are skipped. Stop takes effect between entries/reads; a slow network directory read may still need to return first. Audio probes have a 15-second timeout. Unexpected exit leaves running tasks available for retry.

Run meaningful checks with `python -m unittest discover -s tests -v`. Test sources are created in temporary directories. Importing `app.py` does not open a window.

For fixture roots or a second catalog: `python app.py --roots-json scratch/roots.json --database scratch/pilot.sqlite3`. A roots JSON must contain exactly `Audiobooks`, `Podcasts`, `Ebooks`; never point the catalog database at a library source folder.
