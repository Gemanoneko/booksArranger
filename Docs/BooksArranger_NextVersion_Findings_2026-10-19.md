# Books Arranger — findings carried past v0.19.0

Sergei, 2026-10-19: ship v0.19.0 now; carry these into the next version. All are Minor. None blocks a release.

| # | Finding | Source | Owner | Status |
|---|---|---|---|---|
| 1 | **Start over right after a safety stop still queues a start.** One more book gets tried after a disk-full or working-file hold. | Senua delta d1, `BooksArranger_CodeReview_v0.19.0_2026-10-19.md` | Ender | Open |
| 2 | **Pause audiobook jobs doesn't end a pending auto-start.** The pause is undone within about 3 s. | Senua delta d2 | Sergei to decide (should Pause cancel the pending start?), then Ender | Open — **decision pending** |
| 3 | **Counter is briefly wrong.** After a Start over press the label reads "Showing 1–4 of 3 candidates" until the list reloads. | Futaba, `BooksArranger_QA_v0.19.0_2026-10-19.md` | Judy, then Ender | Open |
| 4 | **Stale details-panel note.** After a safety stop or Quit, "…will start by itself…" stays until another book is selected (same as after Cancel today). The spec is silent. | Ender, fix-round report | Judy | Open |
| 5 | **Two pending-start kinds not tested.** The disk-full and working-file safety stops, and the "conversion"/"stopping" pending kinds, couldn't be reproduced in QA. | Futaba v0.19.0 | Futaba | Untested |
| 6 | **No end-to-end conversion in QA.** The public sources declined the fixtures, so no full conversion ran. | Futaba `c2abd97` / v0.19.0 | Futaba | Untested |
| 7 | **No qa-handoff receipt.** It requires a Senua-reviewed context plan, which doesn't exist (`BooksArranger_QA_Readiness_2026-10-15.md`). | Ender, Futaba | Ender + Senua | Open (older) |

## Next work already approved
- **Open Library editions integration.** The source is validated READY (`Y:/Open Library/ol_dump_editions_2026-09-30.txt.gz`, checksums match the manifest). Ender's integration plan lists six must-fix importer risks before activation. Sergei handed usage to the team ("as you see fit, if at all"). Branch off the released electron-m1 tip, in `C:/Antigravity Projects/Worktrees/Books Arranger/ol-editions/`.

## Declined
- **Second-launch focus path:** a second app launch shows and focuses the window. Sergei said no on 2026-10-19.
- **Plain Start over beside the combined button:** Sergei said no on 2026-10-19.
