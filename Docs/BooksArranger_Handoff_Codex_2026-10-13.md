# Books Arranger — handoff to Codex, 2026-10-13

From Jane's Claude Code session (2026-10-12 → 13). Sergei is parking here and continuing in Codex. Repository: https://github.com/Gemanoneko/booksArranger (public). The studio session recap is `Team/Docs/Session_2026-10-12_Recap.md`, Part 2.

## 1. Live app state (as of handoff)

- The live install is this checkout, `WIP/Books Arranger`, on main. It runs released **v0.14.0** (Pythonw PID 8424; it may have changed if Sergei restarted it).
- **Automatic processing is PAUSED.** The app paused itself at 12:42 UTC when C: ran out of space, with 90 jobs queued. **Do not resume until the disk issue below is fixed.**
- Drive C: has about 1–2 GB free. `data/merge-cache/audio-staging` holds **119 GB of leftover working WAVs** from 8 completed, published jobs: 846deacf, a8ab6b6b, 4db85341, a8d51f2c, 3b299c69, b324a55e, 71c8534e, b55f0216.
  - **Why they are left behind.**
    - Each job's source retirement failed with "Additional filesystem streams require review; original retained" (`source_cleanup.py:51`).
    - Working-file cleanup only runs after retirement succeeds (`merge_service.py:323` returns early, and `storage_cleanup._source_safety` also refuses).
    - The WAVs are 64-bit float (`audio_pipeline.py:277`), about 4× larger than needed.
  - The 8 audiobooks are published and verified on Z:. Their originals are still in place, so duplicates exist until retirement.
  - Reclaimable: 120 `normalized#####.wav` files, 119,317,276,892 bytes, each matched to its job's own staging receipt.
  - **Do not delete them without Sergei's yes** (question A below).
- Eye of God replacement: done (job 79a59bdb). Its recovery copies in `data/replacement-recovery` expire about 2026-10-13 20:45Z.

## 2. Branches and releases

| Item | Where | State |
|---|---|---|
| v0.13.1, v0.14.0 | tags on main | Released; v0.14.0 applied live |
| **v0.15.0 candidate** (split-book grouping + spelling fixes) | branch `codex/books-split-books-0.15.0` @ d3c5526; worktree `scratch/split-books-2026-10-13/worktree` | **Futaba GO and Senua RELEASE CLEAR at d3c5526.** Not released yet. It needs the working-file fix (§3) first, as a reviewed delta. |
| Electron milestone 1 | branch `codex/books-electron-m1`; worktree `scratch/electron-2026-10-13/worktree` | Built and tested on a data copy. Handoff: `Docs/BooksArranger_Electron_M1_2026-10-13.md`. Not reviewed or released. |
| Google human-verification UX | `Docs/BooksArranger_GoogleVerification_UX_2026-10-13.md` on main | Spec done with Sergei's answers. Implement after v0.15.0. |

The history was rewritten on 2026-10-13: Gemanoneko no-reply identity, Windows username and source-site filename scrubbed. Repo-local git identity is `Gemanoneko <219725471+Gemanoneko@users.noreply.github.com>`; keep it. Do not use real names or emails in commits. No Claude/AI attribution trailers in commits.

## 3. Next work, in order

1. **Working-file cleanup fix** (urgent; this becomes v0.15.0 round 4, on d3c5526 in the split-books worktree). Not started: the previous attempt died at a usage limit before changing anything.
   1. Once a job's audiobook is verified and published, remove its verified working files (normalized WAVs and other disposable staging), whatever happens to source retirement. Keep snapshots and recovery data only where retirement or recovery still needs them.
   2. Re-evaluate the 64-bit float WAV format. Pick the smallest format that keeps the exact PCM/sample-count proofs.
   3. Make free-space checks robust: estimate the working size per job and hold the job cleanly when space is short.
   4. Add a supported, receipt-matched cleanup for already-leftover working files of completed, published jobs. Never touch snapshots, recovery data or unverified files.
   5. Tests, then a Futaba-style QA delta and a Senua-style review delta, then release v0.15.0 and apply it (stop/apply pattern in `Docs/BooksArranger_LiveApply_v0.14.0_2026-10-13.md`). After that Sergei launches the app normally, and research is resumed with one guarded Start.
2. Google human-verification button, per Judy's spec.
3. Electron milestone 1 review, then milestone 2 (GitHub release, keep-last-4, idle-gated update check) and milestone 3 (live switch). The UX items for Judy are in the M1 handoff §7.
4. Follow-ups:
   - Senua R3-M1 "1-1/1-2/2-1" piecemeal-set residual;
   - middle-initial word order;
   - `sully_apply_release.py` normalises line endings and skips `.gitattributes`;
   - stale `recovery_active: true` in `data/web-instance.json`;
   - Zahn and Pratchett spellings, which need verified catalog evidence.

## 4. Open questions for Sergei

**Urgent:**
- **A.** Delete the 119 GB of leftover working WAVs now (120 receipt-matched files; audiobooks published, originals and recovery untouched)? yes / no
- **B.** May the hidden NTFS streams on the originals be listed read-only? If they are only Windows' "downloaded from internet" mark (Zone.Identifier), may those originals be retired normally? yes / no

**Earlier, still open:**
1. A folder of books numbered only "1, 2, 3…" with no titles: separate books / parts of one book / hold? (Senua M3)
2. A single author's collection in a folder named after that author: under the author / Сборники as "Разные авторы"? (Senua M4)
3. Should Quit also offer "Quit now" while it waits for the current book? yes / no
4. Installed-app data in `%LOCALAPPDATA%\Books Arranger\data`? OK / other
5. Existing data: move it there later, or keep its current location?
6. Parts with no own title ("Торадора! Том 1"): name them "Торадора! - 1 - Торадора!"? yes / hold
7. Read-only chapter probe (ffprobe) over about 1,000 split files on Z: to measure how many are held because of chapters? yes / no

## 5. Standing rules that still apply

- Sergei's decisions: `Docs/BooksArranger_StandingRules_2026-10-11.md` (all sections, including the 2026-10-12/13 local-agreement rulings) and `Docs/BooksArranger_Brief.md` decision logs.
- Never weaken source verification, publication checks, the 24-hour recovery or retirement safety.
- A false identity or grouping that could retire the wrong originals is always blocking.
- Never act on the live app (Stop, Start or POST), on `data/`, or on Z:/Y: without an explicit, stated reason and approval. Read-only database work goes through a sqlite backup-API copy, taken once.
- Sergei is not QA. Every build gets independent QA and review before he sees it, and he only launches the app from the Start menu.
- The PowerShell tool is blocked by Bitdefender for encoded commands; use Bash.
- Disposable scratch to clean when space allows (QA exports holding `.claude` folders, which the cleanup planner refuses):
  - `%TEMP%\fq\*`
  - the session scratchpad `futaba-0131`, `futaba-0140`, `senua-0131`, `v4-work-*`, `split-books\before-code`, `split-books\catalog-copy.sqlite3` (keep it until v0.15.0 is released)
  - `scratch/fast-identity-2026-10-13/evidence/catalog-copy.sqlite3`
  - the Electron `scratch/electron-2026-10-13` build downloads and `pristine/`
