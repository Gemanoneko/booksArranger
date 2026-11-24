# Books Arranger 0.31.2: QA report (Futaba, release candidate confirmation)

Date: 2026-11-24, about 21:20 to 21:55 local. Build tested: the unpacked packaged build of the 0.31.2 release candidate, built from main `71cbc84fad08ab4f70ac640bf1dbf695112ea59e`. Left uncommitted. This follows my GO at `534d0c9` (round 3 of 0.31.1: `BooksArranger_QAReport_v0.31.1_r3_2026-11-24.md`); 0.31.1 was tagged but never published, and Sergei chose to release the same code as 0.31.2.

Release source commit: 71cbc84fad08ab4f70ac640bf1dbf695112ea59e
Release artifact manifest SHA256: 80594fad8fae5c6994fc45494a884eb7057f00e5c5e8f89dd621460951ec6125
**Verdict:** GO

This GO covers Books Arranger 0.31.2 at the commit and manifest above. The product code is the code I cleared at `534d0c9`: the only product change is the version number. The isolated launch reports 0.31.2 everywhere it can be read, the stuck-load state behaves, and a hand-moved book is still found. No Blocker, no Major, no Minor. It is a behavior verdict only; Senua's RELEASE CLEAR is separate.

## 1. Hash check (compared only; the entry check was not re-run)

| Item | Handed over | Found | Match |
|---|---|---|---|
| Entry log `q0312a\logs\ender-entry.log` SHA-256 | `f672deb7…8aba` | `f672deb74fe6ff404a6e07eb2c8d3fad8af2ca42d9cd65b541a9b82efe2c8aba` | yes |
| Context `q0312a\context\context.json` SHA-256 | `f9f9e6c6…7a95f` | `f9f9e6c610879ddc261bd5137e99aed5c147ff902ba12d3f8c8c2e5c1727a95f` | yes |
| Installer `…\6f83ddba-…\Books-Arranger-Setup-0.31.2.exe` SHA-256 | `e1e6af2c…0b76` | `e1e6af2cd304bb4b8c9656f7cd021172b3330ebef6786c17cc96f1e3d07f0b76` | yes |
| `dist\release-artifacts.json` SHA-256 | `80594fad…6125` | `80594fad8fae5c6994fc45494a884eb7057f00e5c5e8f89dd621460951ec6125` | yes |
| Unpacked `Books Arranger.exe` SHA-256 | `76b80f77…4f2d` (changed with the embedded version) | `76b80f77776bdaf17576bf2733ea032f72049a363189e69460b38831a51d4f2d` | yes |
| Source HEAD of `WIP\Books Arranger` (branch `main`) | `71cbc84…` | `71cbc84fad08ab4f70ac640bf1dbf695112ea59e`; `git status --short` empty | yes |
| Receipt, line 4 of the log | `v0.31.2 @ 71cbc84, check pass` | read: `Entry-check receipt v2: books-arranger v0.31.2 @ 71cbc84fad08ab4f70ac640bf1dbf695112ea59e (dirty: N) … check pass` | yes |

## 2. What changed since my GO

`git diff --stat 534d0c9 71cbc84`: 11 files, 1,064 insertions, 4 deletions: `CHANGELOG.md`, six Docs files (the three code reviews, the three QA reports, the UX spec), and three version files. I checked the rest by name: **0 files** changed that are not a doc, the changelog, `package.json`, `package-lock.json` or `scripts/build-inputs.json`. The product lines changed are the version fields (`0.31.0` to `0.31.2`, twice in the lockfile) and the lockfile hash recorded in `build-inputs.json`. No `.py`, `.js` or web file changed.

## 3. The isolated launch

Run folder `futaba-0312` under `I:\AI Projects\Worktrees\Books Arranger\`, my own installation config (my own profile, data and temp folders), my own ports, the unpacked exe of this build. Sergei's copy (shell 125832, host 114640, engine 83536, port 5210) was never touched; the same six PIDs and the listener were there at the start and at the end. No mouse, no keyboard, no clipboard; a read-only foreground logger beside every launch.

### It reports 0.31.2
- The shell's own user agent: `BooksArranger/0.31.2 … Electron/44.4.5`.
- `window.booksDesktop.status()` in the real page: `engineVersion: 0.31.2`; the page's text shows `0.31.2` (twice at Ready).
- The engine banner `Books Arranger 0.31.2 — http://127.0.0.1:5362/` and `/api/state` `version: 0.31.2` on the engine lane (the packaged python and packaged backend of this build).

### The stuck-load state (real shell, real engine, real page)
The page's `/api/state` answer replaced by the engine's own 503 body once the engine reported loaded, at the network layer.
- 0.7 s: `Working · Loading finished. Preparing the library status.`
- 10.4 s: `Waiting · Loading finished. The library status is taking longer than usual (10 s). The engine is still answering.`
- 60.1 s: `Stuck · Loading finished, but the library status has not arrived after 1 min 0 s…`, action row Restart Books Arranger and Copy details only, warning style on, no moving stripe.
- After the 503 was released: `Ready`.

### A hand-moved book is still found
Four real finished books on the engine lane (real scan, real conversion, real cleanup). Book 03 moved by hand into `Elsewhere` while the engine ran; Resume audiobook jobs pressed 3 s later: `relinked` went from 0 to 1 two seconds after the press, totals stayed `4 converted out of 4`, engine log `finished book found again after a move outside the app`.

## 4. Findings

Blocker: none. Major: none. Minor: none.

One observation, not counted. In the shell launch the foreground logger (150 ms polling) recorded my shell window (PID 15744) as the foreground window for 4.1 s, 52 s after loaded, between two periods of the same Godot game window, which then had focus again. Sergei was clearly working at the machine (File Explorer windows open on the Temp folder, game, ChatGPT and Chrome windows changing). A control launch of the same build with nothing attached (no debug port, no page script, no network interception) for 95 s showed no Books Arranger foreground event among 27 other window changes. This is the third short blip of this kind in about fifteen shell launches over the 0.31.1 and 0.31.2 passes; each time the previous window (or another) was in front again within seconds, and I cannot attribute it: the shell calls its focus-taking `showWindow` only from the tray and from a second instance, neither ran, and the product code has not changed since the first of them. It could be someone clicking the new taskbar entry, or my debugging attachment, or something else. Listed so it is not a surprise; Jane's call whether to chase it.

## 5. Not tested (said plainly)
Nothing beyond what the brief asked: the rest of the product behavior stands on rounds 1 to 3 of 0.31.1 (same code). Still BLOCKED from round 1, unchanged: Restart Books Arranger with a book converting (the native question needs a click) and pressing Copy details (clipboard).

## 6. Pattern alerts
Pattern alerts: none.

## 7. Personal-folder listing (list only; nothing deleted or moved)
`node scripts/qa/personal-folders.mjs check --since <snapshot taken at the start>`: `personal folders: clean (7 folders, 10 drive roots watched)`. `I:\Books Arranger\` (Profile, Data), `Z:\`, port 5210 and Sergei's installed copy were not written to. The tool repo was read only.

## 8. Disposal
- Stopped: the engine lane by its own shutdown route, both shells by their own `--quit`; the lane and debug ports are not listening (checked); no process of mine remains; Sergei's six are as at the start.
- The run folder `futaba-0312` (38.73 MB) was swept: the dry run planned exactly that one item, `--apply` removed it (`removed 1 item(s), 38.73 MB, stuck 0`). It is gone from `Worktrees\Books Arranger\`.
- Left, not mine: `q0312a` (Jane sweeps it after the release).
