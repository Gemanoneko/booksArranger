# Books Arranger 0.31.0: QA report, round 4 (Futaba, final delta pass on the release build)

Date: 2026-11-24, about 04:32 to 05:17. Build tested: packaged, `d96979d8acae368e6fc76245cb502dfa76a7772a`. Left uncommitted. Round 3 is `BooksArranger_QA_v0.31.0_r3_2026-11-24.md` (GO on `399caea`, with the note that `d96979d` needed its own pass).

**Verdict:** GO

This GO covers the build handed over for `d96979d` (installer SHA-256 `48565304…9fd8`), hash-checked below. No Blocker and no Major is open. B1 holds in a fully automatic lane. The Goodreads revert is in: a Goodreads human check is a try with a 300 second back-off, never a one-hour pause, and never recorded as "nothing found". Smoke passes. Findings are two Minors (one carried, one single-sample observation).

## 1. Hash check (compared only; the entry check was not re-run)

| Item | Handed over | Found | Match |
|---|---|---|---|
| Entry log `q031i/ender-entry.log` SHA-256 | `e6ff5b75…d5b8` | `e6ff5b7510d9af0d352a0518f654e4bb1d335238f71500f3368275bd4153d5b8` | yes |
| Installer `Books-Arranger-Setup-0.31.0.exe` SHA-256 | `48565304…9fd8` | `4856530492f7cc85af9124edee637a3e785726aa588be4cf2e3b081502bf9fd8` | yes |
| `dist/release-artifacts.json` SHA-256 | `fec4eabb…35ef` | `fec4eabb51f751e0fef639d8aa7252ed926a9b09e429c1eb8934fe56b2af35ef` | yes |
| Unpacked `Books Arranger.exe` SHA-256 | `c96a8d73…4801` | `c96a8d73c5f9843f871db89713518ba4d4791afb413d2d5d112b12b0a9fd4801` | yes (same shell exe as r3; the backend is what changed) |
| Manifest `source_head` | `d96979d` | `d96979d8acae368e6fc76245cb502dfa76a7772a` | yes |
| Worktree `ender-031` HEAD | `d96979d` | `d96979d` (read only: `git log`, `rev-parse`; `status --short` empty before and after) | yes |
| Receipt, line 3 of the log | `d96979d…, dirty: N, check pass, personal-folders clean` | read in full: `Entry-check receipt v2: books-arranger v0.31.0 @ d96979d8acae368e6fc76245cb502dfa76a7772a (dirty: N) … check pass … personal-folders clean` | yes |

- **The packaged backend is the commit, not just the label** (the version is 0.31.0 in both r3 and r4, so the filename cannot tell them apart). Method: for every top-level `.py` in `git ls-tree d96979d` that also exists in the unpacked `resources\backend`, SHA-256 of the packaged file against `git show d96979d:<file>`, line endings ignored (the packaged `web_server.py` differs only by CR). 146 files compared, 0 differ. The two files the revert touched differ from `399caea`: `public_research.py` packaged `8fb52306…` = `d96979d`, `399caea` is `7b18b915…`; `series_backfill.py` packaged `84ec3300…` = `d96979d`, `399caea` is `b5c735d0…`.
- **Test counts** (read from the log, nothing re-run): Python, the log prints `Ran N tests` once per batch; I summed them with `grep -o` and `awk`: 13 batches, 3,199 (equal to the hand-over). Node: `# tests 279`, `# pass 279`, `# fail 0`.

## 2. How it was run

- **Engines.** The packaged python and the packaged `resources\backend` of the tested build, started by my own launcher (`web_server.main()`, `--roots-json`, `--audiobook-output-root`, one data folder per lane). Ports 5290 to 5295 (never 5210 or 5212). TEMP inside my run folder. Everything under `I:\AI Projects\Worktrees\Books Arranger\futaba-031e\` (now deleted).
- **Goodreads injection.** In my launcher only: `public_research.transport` replaced by a wrapper that, for `www.goodreads.com` only, raises `HTTPError` 202 with the header `x-amzn-waf-action: challenge` (the real shape; every injection logged to a file). Everything else real. A mode file switches `online`, `offline` (every non-loopback lookup and connection refused) and `gr202` at each call.
- **The page** was read and driven through headless Edge (the studio helper `scripts/qa/headless-browser.mjs`, my own lease), by script over the debug protocol: title, text, and the page's own `Start automatic processing`, `Stop` and `Resume` buttons. No window, no focus, no mouse, no keyboard. I never pressed Choose folder… this round.
- **Fixtures.** Cuts (two parts of 25 s) of my own copy of `ba-mp3-fixture/fixture.mp3` (SHA-256 prefix equal to the original, original untouched), tags set with the packaged ffmpeg.
- **Shell smoke.** The unpacked exe with my own `--installation-config` (schema v1, `catalog_mode: new`, every folder in my run folder), `--roots-json`, `--port=5294`, `--show-inactive`. The close and quit commands were second instances carrying my own `--installation-config`, so they could only reach my copy.
- **Counts and how they were read.** "N converted out of N approved" is the page's own line, cross-read with `audiobook_jobs.converted_total / approved_total` from the engine. "Listed under Audiobook Ready" is the page's default Ready list in a freshly opened tab, plus the list route with `status=converted`. File facts: size, SHA-256, decoded-audio md5 and audio-packet md5 (packaged ffmpeg `-f md5`), tags and chapters (packaged ffprobe). Back-off and ledger values were read read-only (`mode=ro`) from my own lane databases.
- **Lanes.** A (shell smoke), C3 (B1, offline conversion then online), G1 (Goodreads injected from the first look-up, online), G2 (stopped before it did anything; replaced), G3 (see section 3, item 2; not evidence).

## 3. What was checked, by the brief's items

### Item 1. B1, a book the rules rewrote and moved reads as converted: PASS

Lane C3, **fully automatic**: Liu Cixin, title `Тёмный лес`, two parts. I pressed `Start automatic processing` once at the start (04:35:54). After the engine was restarted online (05:01:03) **nothing was pressed or typed**.

| Time | What happened |
|---|---|
| 04:56:09 | Converted offline under the Russian title; engine shut down by the app's own route 2 s later, before any look-up try was spent (the 04:56:05 pass found the cleanup unfinished and deferred 10 minutes, with no source tried). |
| 05:01:03 | Relaunched online, after every stored host back-off had ended (05:00:59). |
| 05:06:06 | Ledger: `held`, `Series found. Moving it into its series folder waits for your approval.` (Remembrance of Earth's Past, No. 2, from Wikidata; the rules approve this step). Page: `all done`, with the move still owed (Minor 1). |
| 05:13 | Rules wrote the file and filed it into `sorted\Liu Cixin\Remembrance of Earth's Past\`. |

State after the rewrite, from a freshly opened tab at 05:13:25:

| Check | Result |
|---|---|
| Row status | `Audiobook Ready` |
| Where it is | `Now in sorted\Liu Cixin\Remembrance of Earth's Past\Remembrance of Earth's Past - 2 - The Dark Forest - Liu Cixin.m4b` |
| Choose folder… | present on the row (with `Use computed folder`, `Cancel move`, `Move book`, `Keep it here`, `Cancel`) |
| Note | `Moved. The audiobook is now in …\sorted\Liu Cixin\Remembrance of Earth's Past.` and `Renamed or moved by the app · 1` |
| Counter | `All done · 0 need attention · 1 converted out of 1 approved books` (engine: `converted_total 1 / approved_total 1`) |
| Listed under Audiobook Ready | yes: the page's Ready list shows the row; the list route with `status=converted` returned 1 row (total 1), and `status=all` 1 row |
| Title | `Books Arranger: all done` |

- My poller (counter, Ready rows, All rows, `pending.moves`, `writes`, every 3 to 4 s from 05:01:41) never saw the counter below 1/1 or the Ready list empty. It logged the move owed from 05:06:08 and cleared at 05:13:16. It did not catch the write itself (no `writes=1` sample), so I cannot say how long the write window lasted. In r2 the same step turned `1 converted` into `0`.
- **File integrity.** Before and after the rewrite: decoded-audio md5 `4423a983…f360` and audio-packet md5 `74310443…7cd` identical; chapters identical (2, ending 25.013 s and 50.027 s); streams identical (aac, data, png cover). Size 2,164,614 to 2,164,796 (tags only). Tags after: title `The Dark Forest`, album and sort_album `Remembrance of Earth's Past - 2 - The Dark Forest`, grouping `Remembrance of Earth's Past`, track 2, artist and album_artist `Liu Cixin`.
- Not pressed this round: Choose folder… (only its presence is checked, as the brief asked; r3 exercised the press after a rules move).

### Item 2. The revert: a Goodreads human check is a try with a short back-off: PASS

Live Goodreads is still challenging: my curl at 04:44 got `HTTP/1.1 202 Accepted`, `x-amzn-waf-action: challenge`.

**G1** (online, standalone English book `Andy Weir / The Martian`, Goodreads injected from the first look-up, FantLab, Wikidata and the search engine real):

| Time | Fact |
|---|---|
| 04:36:05 | Injected challenge #1. Goodreads host back-off stored `next 04:41:05`, exactly +300 s, reason `Public source unavailable; no bypass attempted` (not the human-check reason, not 3,600 s). Page: `Waiting for an online answer: The Martian · Next try 04:46. After 3 tries a book converts with the names from its files.` |
| 04:46:05 | Injected challenge #2. Stored `next 04:51:05` (+300 s), same reason. |
| 04:56:05 | Injected challenge #3. Stored `next 05:01:05` (+300 s), same reason. The book then converted with the names from its files (page 04:56:15: `1 converted out of 1`, row `Audiobook Ready`, `Now in sorted\Weir Andy\The Martian - Weir Andy.m4b`). |
| 04:56:16 | Series ledger row for the book: state `deferred`, reason `www.goodreads.com: Public source unavailable; no bypass attempted`. Goodreads: `{"tries": 1, "reason": "Public source unavailable; no bypass attempted", "next": +6 h}`. **It is a try, not `none`.** `deferrals: 1`. The wait recorded is the host back-off (`retry_at` +300 s, kind `source_unavailable`). |

- **The search engine's human check is unchanged.** In the same ledger row the publisher and Litres sources (both through DuckDuckGo, which gave its own live human check) are `{"answer": "none", "reason": "Public source presented a human check; no bypass attempted"}`: nothing found, at once (ruling R32 still holds for its host).
- **Old against new, same shape of challenge.** r3 on `399caea`: the same injected challenge stored a one-hour pause (`Next try 04:06` from a 03:06 start), a book held at the identity stage for an hour or more, and a Goodreads ledger answer of `none` with the human-check reason. Today: +300 s each time, a try every 10 minutes, the book converted after 3 tries (20 minutes from the start). **r3's M2 is gone.**
- **Live, un-injected, same result.** G3 (no injection at its first try): its first Goodreads request at 04:43:04 stored the same generic 300 s back-off (`next 04:48:04`, `Public source unavailable; no bypass attempted`); the second at 04:53:04 was answered. C3 (online from 05:01): Goodreads request at 05:06:05, stored `retry_at 05:11:05`, recorded in the series record as `deferred_sources` (a try); Wikidata gave the series, so the rewrite was not held back (item 1). I cannot see the HTTP answer inside the engine for G3 and C3, only the stored result; it matches what my curl got.
- **G3 is not evidence for the ledger stage.** I meant to switch Goodreads to the injected challenge between its conversion and its first look-up; its first look-up ran at 04:53:54, eight seconds before I switched (04:54:02), so it recorded Goodreads' real answer. No injection happened in G3. G1 covers the ledger stage.
- **Known issue, not counted:** G1's page after the third try reads `Checking what is left · … Next try 10:56` (six hours): a Goodreads challenge holding back "All done", as the brief said.

### Item 3. Smoke: PASS
- **Launch:** unpacked exe, my own installation config, port 5294, `--show-inactive`: engine answered within 12 s; window title `Books Arranger: checking what is left` (read with `tasklist /V`: PID 107284, which is mine; Sergei's shell, PID 40204, reads `Books Arranger`). I did not look at the screen.
- **Close to tray:** second instance with my config and `--close-window` (the close button's action): my window's title became empty/hidden; the shell, the host python and the engine stayed up and the engine kept answering (the recorded tray exception). Sergei's window title unchanged.
- **Quit:** second instance with my config and `--quit` (the tray's Quit): every process whose command line named my lane gone within 1 s (`CommandLine` listing, 0 left), port 5294 closed.
- Sergei's copy (shell 40204 and its helpers 40720, 40728, 39940; host 40560; engine 41472; port 5210) was running before the first step and after the last; none touched.

## 4. Findings

### Blocker
None.

### Major
None.

### Minor

1. **`All done` shows while a rename or move is still owed** (r2 Minor 1 and r3 Minor 2, still there, not new). C3: `work: all_done`, `pending.moves 1`, page title `all done` and line `All done · 0 need attention · 1 converted out of 1`, from 05:06:08 to 05:13:16 (about 7 minutes), until the rules wrote and filed the book. Quit in that window and the move waits for the next launch.
2. **One list-route answer of 503 `Your books are still loading` in a quiet app (not reproduced).** C3, 05:04:24, one 3 s sample of my poller (Ready and All lists), the next sample at 05:04:27 was fine; the counters and `work` state were unchanged, and nothing in the engine's output. The page treats a loading answer as "still updating", and I never saw a wrong row. One sample, so logged, not claimed. The cause is not known to me; it fell about two minutes after the look-up pass began.

### Carried over, not retested
- r3 Minor 1 (the Ready list lags the counter for an incomplete identity, heals by itself), r3 Minor 3 (the blocked-move wording names a drive), r3 Minors 4 and 5 and r2's "approving by hand leaves the queue `Paused q 1`": nothing in `d96979d` touches them.

### Known and accepted (Jane's ruling 2026-11-24), listed so nobody is surprised, not counted
- A Goodreads challenge in the series ledger is a try six hours later, so `All done` can wait on it (G1: `Next try 10:56`).
- While Goodreads is challenged, a standalone book spends its identity tries (3, ten minutes apart) before it converts with the names from its files: 20 minutes in G1. Live Goodreads challenged my curl and, from what the lanes stored, 2 of the 3 live (un-injected) Goodreads requests the app made in this pass (G3 first try and C3 at 05:06 stored as a try; G3 second try was answered).

## 5. Not verified (said plainly)
- The Choose folder… press after a rules move (r3 did it on `399caea`; `d96979d` does not touch it).
- DuckDuckGo's human check by injection: observed live in G1's ledger (`none`, human-check reason), not injected.
- What the Goodreads challenge does after its six-hour retry, and the end of the 6 h wait.
- The write window of the rewrite (my poller did not sample it), cover and data-stream content of the rewritten file (streams are listed identical, contents not compared), the shell's window title while automatic processing runs, keyboard use, layouts other than headless Edge's default.
- Counts of live Goodreads challenges are my reading of stored results in three live requests (plus one curl), not a measurement.

## 6. Pattern alerts
Pattern alerts:

- **P1 (open since round 1, disposition: fix or accept).** `All done` and the status lines are honest only at the edges the build tests. This round again: `All done` with a move owed for 7 minutes (Minor 1) and, in G1, `Checking what is left` for six hours behind a Goodreads try (known, accepted). One rule for "what is left", read from one place, would close the family. Jane to disposition: fix, accept or defer.
- **P2 (from round 2, B1 family).** The B1 shape (the page's picture of a finished book left behind by a rewrite) is fixed and held in this build. Disposition: accept as closed.
- **P3 (from r3: a change to a shared client moves every stage that uses it).** The revert put the shared client back; r3's M2 is gone. Disposition: accept with the rule that a change to `PublicClient` names every stage that calls it in its test list.
- **P4 (new, small).** Live Goodreads challenges are frequent today (curl 202 + challenge; the app's own live requests mostly stored as "try again"), so the accepted behavior (book converts after 3 tries over 20 minutes; series ledger six hours) is what Sergei will see most days for standalone books. Disposition proposed: accept, per the ruling; revisit only if Sergei finds it slow in daily use.

## 7. Personal-folder listing (list only; nothing deleted or moved)
`node scripts/qa/personal-folders.mjs check --since <snapshot taken at the start>`: `personal folders: clean (7 folders, 10 drive roots watched)`. The headless lease stop reported `personal folders clean`. `%LOCALAPPDATA%\Books Arranger`, `Z:\`, port 5210, Sergei's installed copy and Data folder, the worktree (`status --short` empty, HEAD `d96979d`), `q031*` and the main checkout's code: not written to.

## 8. Disposal
- Stopped: lane engines by the app's own shutdown route (G2 and G1 and G3 earlier, C3 last), the shell by its own `--quit`, my poller (PID 118048, ended with `taskkill`, my own PID; it had no folder name in its command line), my conversion watcher (ended itself), one background wait loop (stopped with TaskStop), headless Edge (`headless-browser.mjs stop 31a036d1d078`: 0 left).
- Checked by command line (CIM listing of `Books Arranger.exe`, `python.exe`, `msedge.exe`): **0** processes name `futaba-031e`, **0** run my launcher, poller or watcher. Ports 5290 to 5296 not listening. Only Sergei's six processes remain.
- `futaba-031e/` (63.81 MB) removed with the studio sweep (`node scripts/studio-sweep.mjs --project "Books Arranger" --path "I:/AI Projects/Worktrees/Books Arranger/futaba-031e" --apply`: removed 1, kept 56 not mine, **stuck 0**).
- Left, not mine: the sweep's kept items, `q031*`, `senua-031*-scratch` and `ender-031`, none touched. The headless helper's own cached `IlluminatiHbHolder-*.dll` sits in the session's shared temp folder (`scratch\tmp-ba1c5095\illuminati-headless\bin`), with other tools' files; I left it.
- Two harness notes: a stray `mkdir /tmp` and a stray stdin-fed `python -` line of mine were each stopped by the studio's guards before anything ran; nothing was written to C:.
