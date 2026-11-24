# Books Arranger 0.31.0: QA report, release acceptance (Futaba)

Date: 2026-11-24. This is the release-acceptance report for Books Arranger 0.31.0. It carries the pins the release script reads and rests on the round-4 test of the release build. No new testing was run for it: it is hash checks and a tree comparison, all read-only.

Release source commit: d96979d8acae368e6fc76245cb502dfa76a7772a

Release artifact manifest SHA256: fec4eabb51f751e0fef639d8aa7252ed926a9b09e429c1eb8934fe56b2af35ef

**Verdict:** GO

## 1. What this rests on

The GO is round 4's, on the release build. Rounds 1 to 3 are the history that led to it.

| Round | Report | Build | Result |
|---|---|---|---|
| r1 | [BooksArranger_QA_v0.31.0_2026-11-23.md](BooksArranger_QA_v0.31.0_2026-11-23.md) | `a8b6804` | GO (delta pass) |
| r2 | [BooksArranger_QA_v0.31.0_r2_2026-11-23.md](BooksArranger_QA_v0.31.0_r2_2026-11-23.md) | `7023cc9` | NO-GO (B1, M1) |
| r3 | [BooksArranger_QA_v0.31.0_r3_2026-11-24.md](BooksArranger_QA_v0.31.0_r3_2026-11-24.md) | `399caea` | GO, with one new Major (M2, a live Goodreads check holding a book at the identity stage for an hour) |
| r4 | [BooksArranger_QA_v0.31.0_r4_2026-11-24.md](BooksArranger_QA_v0.31.0_r4_2026-11-24.md) | `d96979d` | GO: B1 holds, the Goodreads revert removes M2, smoke passes, no Blocker and no Major open |

r4 is a committed report. It was written against the packaged build for `d96979d`, the same build checked below.

## 2. Hash and tree checks (read-only, 2026-11-24, main checkout)

1. Release manifest `dist/release-artifacts.json`: SHA-256 equals the manifest pin line above (`fec4eabb…35ef`). It is the same manifest r4 checked in its worktree. The manifest records version 0.31.0, source head `d96979d` and build id `bf4a0ade-a9fd-428a-9176-be5f96dcb37a`.
2. Installer `dist/builds/bf4a0ade-a9fd-428a-9176-be5f96dcb37a/Books-Arranger-Setup-0.31.0.exe`: SHA-256 `4856530492f7cc85af9124edee637a3e785726aa588be4cf2e3b081502bf9fd8`. It matches r4's recorded installer hash (`48565304…9fd8`), and the manifest lists the same hash.
3. Product tree: `git diff --stat d96979d HEAD -- . ':!Docs' ':!CHANGELOG.md'` is empty. HEAD is the merge on `main`, `b64af88`, and `d96979d` is an ancestor of it. Nothing outside `Docs/` and `CHANGELOG.md` changed after the tested build.

## 3. Known issues accepted

Under Sergei's rulings (as relayed in r4, Jane's ruling of 2026-11-24), none counted against the GO:
- A Goodreads challenge in the series ledger is a try six hours later, so "All done" can wait on it (r4 G1 showed `Next try` six hours out).
- While Goodreads is challenged, a standalone book spends its three identity tries, ten minutes apart, before it converts with the names from its files (about 20 minutes in r4 G1).

Minors open in r4 (details and repro in r4 section 4):
- "All done" shows while a rename or move is still owed (about 7 minutes in r4 C3; quitting in that window leaves the move for the next launch). Carried from r2 and r3, not new.
- One 503 "Your books are still loading" on a list route in a quiet app, a single sample, not reproduced. The page treated it as still updating and no wrong row was seen.
- Carried over and not retested, because `d96979d` does not touch them: r3 Minors 1, 3, 4 and 5, and r2's "approving by hand leaves the queue Paused q 1".

No Blocker and no Major is open.

## 4. Personal-folder listing

No new run for this report: nothing was launched, and nothing was written outside this file. The listing is r4 section 7 (`personal folders: clean`, 7 folders and 10 drive roots watched). Nothing was deleted or moved.

## 5. Pattern alerts

Pattern alerts: see r4 section 6 (P1 to P4, each with its disposition or proposed disposition). P1 ("All done" and the status lines are honest only at the edges the build tests) is still waiting for Jane's fix, accept or defer. Nothing new was seen in this pass.
