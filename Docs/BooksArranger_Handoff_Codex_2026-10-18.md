# Books Arranger — Handoff to Codex (2026-10-18)

Parked by Jane (Claude) on Sergei's request. Branch `codex/books-electron-m1`, HEAD `14eea66` (clean, pushed).

## State
- **Installed live:** v0.16.11. Library conversion is running in the app. Leave it running.
- **Built, not released:** v0.16.12.
  - Installer: `dist/builds/4be1f71f-0f5c-4bb5-8bcd-b241101d64a6/Books-Arranger-Setup-0.16.12.exe`
  - SHA256 `b17d3276d4ae9c4c31a4e44a572932e5105b508fa36480055ffebe35bc3cf584`
  - Manifest `dist/release-artifacts.json` SHA256 `86f602de252e600b99afc80c7358c9e68abfc9bf158094be728ac211273613ac`, source_head `14eea665728116a6f89d0ebd3d365c1b627f9a17`
- **v0.16.12 contents** (`2e688aa`):
  - `series_backfill.py`: adds Goodreads/FantLab series to books that were already published. Writes a proven metadata-only copy next to the published file, renames it to `Author/Series - NN - Title - Author.m4b`, records it, then removes the old file.
  - The Retry button stays disabled and shows "Queued" once accepted; non-M4B retries report queued-next.
  - "Retry selected" added.

## Left to do (in order)
1. **Senua review** of `68a7cdc..14eea66`, red-team style. The review was stopped mid-run and no doc was written.
   - Focus: `series_backfill.py` rewrites published books on Z:, and those files are now the only copies. Every crash point must leave one complete, playable copy.
   - Output: `Docs/BooksArranger_CodeReview_v0.16.12_2026-10-18.md`, with one `**Verdict:**` line, `Release source commit:` and `Release artifact manifest SHA256:`.
2. **Futaba lean smoke**, on an isolated empty catalog only. Never use a copy of the real catalog: held cleanups use real Z: paths.
   - Check: the version, status, the strip, "Retry selected", that Quit works, and that the real catalog fingerprint is unchanged.
   - Output: `Docs/BooksArranger_QA_v0.16.12_2026-10-18.md`, GO/NO-GO.
3. **If either finds a Critical or a NO-GO:** fix, re-pack, then redo 1–2.
4. **Sully** commits the two gate docs and `Docs/BooksArranger_ReleaseAcceptance_v0.16.12.json` (schema `books-desktop-acceptance-v1`, same as v0.16.11).
5. **Live apply:**
   - Quit the app normally (`--quit`); it finishes the current book first.
   - Install silently with `/S /currentuser`.
   - Launch from the Start menu and press Start once.
   - If the window stays open after the engine exits, end only that verified window process.
   - Then watch the series backfill, which starts about 2 minutes after launch. Expected example: Призраки белых ночей → «Нормальное аномальное» #10. Also confirm Retry stays "Queued".
6. **Sully** tags `v0.16.12` (annotated, at HEAD, pushed by name), then runs `node scripts/release.mjs` once. That keeps the last 4 releases: v0.16.12, v0.16.11, v0.16.10, v0.16.8.

## Sergei's standing decisions
- Go lean. Don't ask, finish and push.
- Once a book is verified and its originals match by content, remove all of its backups.
- "Keep files" is permanent.
- Retry and Repair are queued to run right after the current book.
- Series: Goodreads order wins; FantLab is the fallback check.
- "Check again" / "Convert again" are deferred.
- Agents never clean the session scratch folder. Give Sergei its path to delete.

## Scratch for Sergei to delete
- `C:\Users\AnGeLZzZ\AppData\Local\Temp\claude\c--Antigravity-Projects-Studio-Illuminati\3c1cc2ef-43a9-4b2a-b1fa-8a242d8fded6\scratchpad`
- `C:\Antigravity Projects\Studio Illuminati\WIP\Books Arranger\scratch\design-2026-10-17` (if present)
