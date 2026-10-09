# Books Arranger

Repository: https://github.com/Gemanoneko/booksArranger

Books Arranger helps Sergei inventory and arrange his audiobook, podcast and text-book libraries. It will produce one Apple-compatible audiobook per verified book, preserve supplementary metadata, and arrange books under reviewed names. Milestone 1 is a runnable read-only incremental scanner with Start/Stop/Resume across restarts, evidence inspection, and sorting preview. It deliberately does not convert, move, rename, delete, rewrite tags, play audio or invent metadata matches.

## Confirmed rules

- Audiobooks: `Z:\Audiobooks`; `Unsorted` is the arrival area. `Podcasts` is a separate library type and excluded from audiobook grouping.
- Podcasts: `Z:\Audiobooks\Podcasts`. Preserve one episode/file, existing podcast classification, show tags, identifiers, descriptions, artwork and transcripts. Never merge them as audiobooks. Current classification may also reside in iTunes, not just embedded tags.
- Ebooks: `Y:\Books\Books`; preserve file formats and bytes. Arrange `Main Genre/Author/Series if any/Book Title/original file`.
- Ebook main genres: Science Fiction, Fantasy, Horror, Adventure, Mystery & Thriller, Nonfiction, Children's Tales.
- Nonfiction adds a topic between genre and author: `Nonfiction/Topic/Author/Series if any/Book Title`. Psychology, Philosophy, Sexuality, Project Management and Cinema are examples; do not invent a topic absent evidence.
- Original works written in Russian use Russian canonical titles/authors. All other original works use English canonical titles/authors, including Russian translations. Embedded edition language does not establish original language.
- Author folders are surname first. Multi-author series get their series folder at the applicable library root. The review records this explicitly.
- Future audiobook filenames: `Series - Number - Title - Author.m4b`, with series/number omitted for standalone books. Multi-author ebook series place files directly under their library-root series folder as `Series - Number - Title - Author.original-extension`; preserve their bytes and reject uncertain positions/colliding destinations for review.
- Future output stays within the corresponding source library root. Future authorized cleanup is not implemented in milestone 1.
- Final audiobook target is single-file M4B with appropriate audio, Unicode tags, one cover and optional trustworthy chapters. Actual iTunes/iOS 27 import, search, sync, seek and chapter behavior need a real device pilot before bulk conversion. No device compatibility is claimed by this scanner.
- Incremental delivery follows ComixManagementTool: usable small milestones, preserve completed verified work. Persistent scan continuation is additionally explicit here.

## Stack and commands

Python standard library: Tkinter desktop UI plus local HTTP/browser interface, SQLite catalog/checkpoint queue, pathlib/os traversal, bounded EPUB/FB2 metadata reads. Optional existing FFmpeg `ffprobe` reads embedded audio metadata. No dependencies need installing. GUI launch: `python app.py` or `launch.cmd`; browser launch: `python web_server.py` or `launch-web.cmd`, URL `http://127.0.0.1:5210/`; checks: `python -m unittest discover -s tests -v` and optionally `node tests/test_browser.js` for the frontend edit/source-refresh regression. Node is not a runtime dependency. No build/release installer exists for this prototype. Sully owns commits, versions and pushes.

## Decision log

| Decision | Reason | Revisit when |
| --- | --- | --- |
| Tkinter rather than Electron/web server | Existing Python includes Tk; minimum usable local scanner without installs or a dev port | Judy joins for Daily Use or packaging is needed |
| SQLite pending tasks plus catalog | Stop and restart resume without throwing away discovered/completed work | Library-scale measurements show bottlenecks |
| Size + nanosecond mtime reuse | Avoid rereading every large audiobook during inventory | Conversion requires cryptographic source/output integrity checks |
| Human-confirmed canonical preview | Original language, translations, author roles and series cannot safely be guessed from filenames or current tags | Reliable external source matching is added |
| No library writes in milestone 1 | First establish inventory, stop/resume and a reviewable arrangement | Verified pilot conversion/move milestone is authorized |
| Browser extension keeps the existing engine/Tk UI | User requested the same local in-app-browser experience as their separate Comics Organizer | UX polish or packaged startup is requested |
| Strict loopback port 5210 | Unique studio assignment; no silent fallback or public bind | An explicit port reassignment is approved |
| Per-process request token plus Host/Origin/Fetch-Site validation | Prevent unrelated pages from reading library inventory or invoking controls | Authentication requirements change |
| Exclusive catalog owner for either interface | Avoid one process resetting another's live scan queue | Multi-client/process coordination is deliberately designed |

## Validation and limitations

The frontend connection/inventory correction follows `Docs/BooksArranger_ConnectionInventory_UX_2026-10-09.md`, published at `40ef3fa` before implementation. Connection feedback is separate from action/review feedback, clears only after a complete current-library poll, and does not infer a scanner crash from a failed fetch. Counts explicitly measure files and pending directory/file tasks. This patch changes only frontend assets and documentation; the backend/API/catalog/scanner remain unchanged and can continue an active scan. HTML/JS tolerate either asset order; the new script adds its optional notice/helper elements when loading older HTML. An already-open older page may be reloaded when the user is ready, without restarting the server.

Targeted frontend recovery check: `node tests/test_connection.js`; retained unsaved-review fingerprint check: `node tests/test_browser.js`. Node remains optional for checks only.

Fixture tests cover restart continuation, changed/new/deleted records, no false missing files on an incomplete/offline scan, podcast exclusion, arrival detection, source bytes unchanged and confirmed routing. Browser checks additionally cover narrow HTTP routes, cross-site rejection, payload validation, exact nanosecond fingerprints, exclusive ownership and shutdown. Windows native GUI is not auto-launched during implementation. Audio metadata errors and unsupported formats require review; PDF/MOBI/AZW/DJVU metadata extraction is deferred. Existing tags are snapshots, not complete private-tag preservation promises for future processing. No hashes are used for reuse yet. Source libraries remain read-only. The browser is a local frontend in Codex's browser panel, not a remote ChatGPT app with independent access to Windows drives.
