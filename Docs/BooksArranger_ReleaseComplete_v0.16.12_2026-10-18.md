# Books Arranger v0.16.12 — release complete

Completed 2026-10-18 by Sully. This operational record supersedes the pending-release state in `BooksArranger_Handoff_Codex_2026-10-18.md`.

- Release: https://github.com/Gemanoneko/booksArranger/releases/tag/v0.16.12
- Annotated tag `v0.16.12` resolves to `c7380148895571482095021d1d028f031d4dc1af`; tag object `348ce94a4d37b2a3ecd94bc15a7e995b8d4f6481`. The later operational-doc commit does not move the tag.
- Product source: `09714f2a0a607f670a14c120e32f12dad2d2158b`. Version remains 0.16.12.
- Accepted manifest SHA256: `d10b4265941fc217265e2aa0f968eec1968afe45b2404eee711123d2ae6b4db6`.
- Build: `dist/builds/db404224-54fa-4c4a-8d50-602d5cded895`.
- Installer SHA256: `5e0670fab2b26b57f8ad24ab3a7322305296a842e08c7a9715d5202d4965da3e`, 173132445 bytes.

## Accepted corrections and gates

Two Critical series-backfill recovery/disposal findings were corrected in `4aff686`; missing, changed or unprovable copies are retained, and exact native-held proofs protect disposal. Retry flicker and stale accepted-state replacement were corrected in `09714f2`. Final artifact-bound Senua RELEASE CLEAR and Futaba GO are the reports named in `BooksArranger_ReleaseAcceptance_v0.16.12.json`.

Focused developer evidence includes 17 backfill tests plus a separate held-race check, three retry frontend suites and 21 backend retry tests. Final packaged QA matched 225/225 payload files and passed 19 retry assertions, 12 status requests, and normal Quit with zero retained descendants/forced termination. Accepted Queued behavior was exercised with synthetic renderer responses; no real retry action was submitted to the live catalog. The canonical handoff receipt was unavailable because its read was denied by the existing command guard; the reports disclose this and the lean scope.

## Live apply and verification

The previous installed 0.16.11 received one normal `--quit` request. It finished «Неандертальский параллакс. Люди» through checking/copying, then closed port 5210 and all Books Arranger processes without any kill. The final accepted installer ran hidden with `/S /currentuser`, exit 0. Independent verification found all 225 installed payload hashes/sizes equal the accepted manifest and installed backend VERSION 0.16.12.

The verified Start-menu target launched with `--show-inactive`, using the existing saved profile and real data folder. Health reported 0.16.12, backend PID 23604, instance `25440822267b795414f9e4c9b8d3dd23`. The existing authenticated Start action was sent once, returned HTTP 202 and Running. The app remains Running; no additional Start/Retry/Quit or process termination was performed.

During the requested approximately two-minute backfill watch, `series_update` remained null and the read-only `series_backfill` ledger was empty. The expected «Призраки белых ночей» series example was not observed in that window; this record does not claim it resolved or verify real rewritten-output playability. The historical 2026-10-15 SQLITE_BUSY failure remains historical state, while current automatic processing reported Running. Final post-publication health remained 0.16.12, closing false.

## Publication and retained evidence

The maintained `node scripts/release.mjs` ran exactly once under its native finite owner, exited 0, verified all three remote asset sizes/SHA256 digests, and verified keep-four cleanup. Independent GitHub inspection confirmed a stable public release and exactly v0.16.12, v0.16.11, v0.16.10 and v0.16.8 retained. Fetch/prune removed the deleted v0.16.7 tag locally; all local/remote tag identities match.

Session scratch remains for Sergei to delete manually: `C:/Users/AnGeLZzZ/AppData/Local/Temp/books-codex-20261018`. Older scratch paths in the original handoff remain governed by that handoff. The current accepted build and historical rejected-artifact evidence are preserved. Local `scripts/clean-dist.js` intentionally preserves previous builds; no dedicated supported removal planner was found, so superseded local build output is retained rather than removed through a new ad hoc deletion route. This session's superseded build is `C:/Antigravity Projects/Worktrees/Books Arranger/electron-m1/dist/builds/d7fce1bd-d21b-40c0-ad11-136b30588ae2`; its archived manifest is `dist/release-artifacts.json.previous-e233dccb-0a61-4b78-a727-f989c2ca5522`. The original blocked build `dist/builds/4be1f71f-0f5c-4bb5-8bcd-b241101d64a6` remains historical evidence.
