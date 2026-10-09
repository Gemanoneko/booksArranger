# Books Arranger — first prototype QA — 2026-10-09

**Verdict:** GO

Scope of GO: revised pinned candidate scanner logic and source-only prototype publication. Initial candidate: 19/20 checks passed; a Major stale-preview defect was found, fixed by Ender, and independently verified. Revised candidate supplied suite: 10/10 passed; affected independent regressions: 3/3 passed. Native visual/interaction/actual process-exit checks are separately pending a permitted away window; this GO does not clear a user-facing GUI handoff or packaged release.

## Candidate and method

Version: unset; initial version assignment belongs to Sully. This is a pre-commit pinned snapshot, not a release clearance. Ender explicitly froze eight files; Futaba copied them into gitignored `scratch/qa-2026-10-09/candidate` and independently matched all SHA-256 hashes before testing. No live shared-tree tests, installs, source-library writes, playback, conversion, moves, deletion, or visible windows. Prototype qa-handoff scripted gate is not applicable.

| Candidate file | SHA-256 |
| --- | --- |
| app.py | 0dcf5a40d0655274d7b2462fa9ab5a79b5cafbbfa4f7d3e03cefeeb49e664522 |
| scanner.py | 0c6a70b380c7c8e69d06a344bec53daa99383475b149782f085acc9968721916 |
| metadata.py | 9ae8504127c65fd45ffbc3ac0b4843cb4417ce19e10c311ddf1429d4011a0a02 |
| launch.cmd | f275784f1bfb121020639bdbcd9dd815c028e8e249eaf19c5664e73f3557f165 |
| README.md | c6de1e2b8f73c4db04400e89fd72508c92e7d49ba670ef40886982dd3eb8e126 |
| Docs/BooksArranger_Brief.md | 8b04865c40eaef747f685774074f43facd01f79baed799c54b1f0634c379da56 |
| tests/test_inventory.py | 894fb84106c829733da270d4b3110610d646766737114e2b979def5661d58501 |
| .gitignore | 3142ff0f50c6ff66585a30bae8be55f7cbeeb7894ea9a43bf97675e21b8485b4 |
| .claude/settings.json | 047afec5274c7b8d97a74fd28e3c3eba659e0b9448befaaf31fb969021684cbf |

Bootstrap-only addition after runtime regression: .claude/settings.json independently matches the existing ComixManagementTool baseline byte-for-byte; .gitignore adds only the mandated per-machine settings/cache ignores. The initial ignore pin was `a48bbf0bafc1f291614bc47a529f0f583e9a1cf115c2dd69eacd7b26781d697a`. No runtime modules changed, so this bootstrap delta requires no rerun of scanner behavior. Final seven runtime/document/test files matched their revised frozen hashes on read-back; the notified bootstrap delta accounts for the remaining publication files.

Initial supplied suite: `python -m unittest discover -s tests -v`, run from the pinned candidate, **9/9 passed**. Initial independent scratch suite: `python scratch/qa-2026-10-09/independent.py`, **10/11 passed** (the final added growth-during-read case failed). Revised snapshot is preserved separately as `scratch/qa-2026-10-09/candidate-r2`; only scanner.py and its supplied test file changed. Supplied revised suite **10/10 passed**. Independent affected regression selection with `QA_CANDIDATE=candidate-r2`: growth-during-read, error recovery, and incremental change/review/missing checks **3/3 passed**. The growth test was additionally strengthened to require cleared review, blank destination, visible per-file error, and stable fresh-scan recovery; **1/1 passed**. These repeated regression runs are not counted as distinct test cases. Both suites use temporary fixtures, explicit finite waits, and clean up only their own fixture directories. One initial fake-close harness error omitted the app's status variable; the harness was corrected to reflect the frozen app, then passed. That was a harness error, not an app fix.

## Independently verified behavior

- Start, Stop, and Resume controller methods invoke the scanner correctly; stopping during a read preserves a completed record and resumes pending work after constructing a new inventory instance.
- Incremental scans reuse metadata for unchanged files, discover additions, reread changed files, invalidate reviewed metadata on a successfully reread change, and mark missing files after a complete traversal.
- Offline roots preserve visible records without marking them missing; reconnection and Resume complete the same generation.
- Audiobook traversal excludes the podcast subtree; independent podcast scans preserve episode paths and companion transcripts.
- Canonical previews require identity/original-language review; a Russian edition title cannot silently become a verified English title. Science Fiction uses the approved full folder name. Nonfiction requires a topic. Multi-author ebook cycles live at the root and use Series - Number - Title - Author with the original extension.
- Literal `%` and `_` path searches and pagination return correct rows. Catalog ownership rejects a second lock and releases on completion.
- CP1251 Russian FB2 metadata reads correctly; source bytes remain identical.
- A fake-window close callback requests Stop then destroys an idle window. This validates controller calls only, not native app/process shutdown.
- Supplied positive/negative checks cover destination collisions, crash-recovery queues, source-database placement rejection, read-error display, and stale review rejection after a successful rescan.

## Bugs

### BA-QA-01 — Major — fixed, independently verified on revised source pin

**Trigger:** a previously reviewed audiobook changes while being read, as can happen when copying an arrival.

**Repro:** inventory `Unsorted/Arriving.mp3`; save canonical review; change the fixture before the next scan; the fixture metadata reader writes a larger file while reading. The scanner's before/after stat check detects the change and finishes with errors.

**Actual:** the queue task becomes an error, but the old `files` row and review remain. `rows()` still presents **Reviewed preview** and the stale canonical destination, with no per-file read-error state. The completed job clears its current message, leaving only an aggregate error count.

**Expected:** preserve source bytes but invalidate the stale review or mark that row unavailable/read-error until a successful stable reread. An error must not leave a valid-looking stale preview.

**Evidence:** deterministic failure in `test_changed_during_read_cannot_keep_stale_reviewed_preview` in the independent scratch suite. Sent immediately to Jane and Ender. No QA source-code fix performed.

**Regression:** Ender's revised scanner pin `0c6a70b...` passes the exact original failed case, plus adjacent error-recovery/incremental checks. The row now clears its review, has a blank destination and Read error, and requires fresh review after a successful stable scan. Initial failed scanner pin retained: `baae9124223391db1d5af9411aae5f5739ddc0867edfdb863b7b3dfee466a8de`. Initial supplied tests pin retained: `0150f1ddba4f4136ff440417fb2677b3125d77bdaa3725dee1b37e87436553a1`. Commit mapping is pending Sully's source publication; no fix commit is invented for an uncommitted pin.

### BA-QA-02 — Minor — deferred to Daily Use polish

New controls have no tooltip implementation in this candidate. Source inspection finds buttons/comboboxes/inputs without tooltip handlers. Core actions have direct labels, so this does not block the prototype's scanner flow. The new-control tooltip rule should be addressed when the UI is polished; no pixel/layout verdict is inferred from source.

## Read-only real-source checks

Futaba independently read two bounded samples with full SHA-256 before and after metadata reading:

| Sample | Bytes | Hash before = after |
| --- | ---: | --- |
| `Y:/Books/Books/Hofstadter Douglas. I Am a Strange Loop.epub` | 1,986,314 | 4676aece40ac65dcdd9374924e3ac34bee9b094543f422aadbbc3b80a769d2ce |
| `Z:/Audiobooks/Podcasts/Fink J., Cranor J. - Welcome to Night Vale/01 - Pilot.mp3` | 20,000,283 | 3524cbacebd156ae2f34dd7f33a696a84367459fc1c138fc5032b7d0c6e49b68 |

EPUB title read as `I Am a Strange Loop`; podcast embedded tags included comment, artist, title, genre, album, date. These checks certify only the two source files remained byte-identical and metadata was readable. They do not establish iTunes/iPhone compatibility or improved podcast tagging.

Ender's separate bounded real-root pilot (reported evidence, not Futaba's independent full-library scan) stopped/restarted/resumed podcasts from 1 to 2 records and ebooks from 65 to 106 records. Its two explicit Read error rows were illustrated FB2 files above the 8MB parser cap: `Абарат. Первая книга часов (с иллюстрациями).fb2` (16,314,610 bytes) and `Книги крови IV–VI. Запретное.fb2` (8,617,214 bytes). This is a known first-milestone metadata-coverage limitation; no claim that all 106 files parsed successfully.

## Pending checks and limits

- Native visible main screen and canonical-review dialog: rendered screenshot/layout, physical click behavior, and closing from each screen followed by actual process exit. No permitted away window was supplied. Standard Tk creation loads a native root before a later withdraw; no existing supported guaranteed offscreen rendering route was found. No native window was opened to gamble on invisibility.
- Large illustrated FB2 metadata; full-library grouping, book/chapter order, authoritative metadata lookup, conversion, cleanup, library arranging, Apple sync/search behavior, and stronger integrity checking are later milestones.
- Stop is cooperative; network enumeration/stat reads may have to return before it takes effect. No performance or worst-case shutdown-duration claim is made.
- Initial version and publication are Sully's work; this report names exact source hashes until a commit exists.

Pattern alerts: none.
