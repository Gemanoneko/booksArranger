# Books Arranger v0.17.0 — release complete

Sully, 2026-10-18. Installed, real target verified, processing resumed, and published: https://github.com/Gemanoneko/booksArranger/releases/tag/v0.17.0 .

Product source `e028fc04c4b30ee26b6960f90948526205acb3ac`; annotated tag `v0.17.0` resolves to accepted live-verification commit `7c6bee8eeac1d18b3c817b3dd6f7f1913477cfac` (tag object `4ade30f649b529de26fe2ed0b3a679c3600837cf`). This later operational record does not move the tag or rebuild the artifact.

The accepted manifest is `3797c7d5117abdaf2f1cdd9b5879e7d8b51dfb370d6c9064b4c148f762716584`; current build `dist/builds/ca0f85ed-aee7-458f-9709-44e9da85ed95`. All 225 installed payload files independently match the manifest. Senua RELEASE CLEAR and Futaba GO are indexed by `BooksArranger_ReleaseAcceptance_v0.17.0.json`.

## Verified real result

The previous app finished its current book and quit normally, without a kill. The new app launched inactive with the existing saved profile and stayed genuinely Paused while the standard backfill scheduler worked. A provider limit recorded per-book deferred reasons and retry times while later books continued; one exhausted FantLab allowance no longer stopped the entire pass.

At 16:03:45 UTC / 19:03:45 Jerusalem, target job `0d7a3865-0a02-4f80-9f67-019982f2f141` reached done with Goodreads evidence for **«Нормальное аномальное» #10**. The actual file is:

`Z:\Audiobooks\Лена Обухова, Наталья Тимошенко\Нормальное аномальное - 10 - Призраки белых ночей - Лена Обухова, Наталья Тимошенко.m4b`

Independent read-back found 279602632 bytes, full SHA256 `1b09d309248f6c58aa6b4eca614eed5da466e44ec65846baba3263d58af1b7ed` matching the ledger, correct grouping/album/sort-album/track 10 tags, readable M4B/AAC 44100 Hz stereo, duration 34671.558333 seconds matching the retained original, and 15 chapters. Former and exact temporary paths are absent. The ledger retains Goodreads search/series receipts and exact disposal identity/ancestry facts.

Audio preservation was verified through the reviewed app's enforced old/new media, compressed-audio and decoder-configuration proof path before done and exact former disposal. The surviving full hash and structure were independently checked; original/new equality was not independently replayed after deletion, and no additional full decode or playback was performed. Detailed evidence and receipt hashes: [live acceptance](BooksArranger_LiveAcceptance_v0.17.0_2026-10-18.md).

Only after this result, Start was sent once and returned HTTP 202/Running. The app was left running, backend PID 93020, instance `fe8b54eeee67f896a3e9c693802c4f3c`. Final post-publication health reported 0.17.0 and closing false; recovery work was active. No extra Start/Retry/Quit controls or provider-budget changes were made.

## Publication verification

The maintained `node scripts/release.mjs` ran exactly once, exited 0, and verified all three published assets. Independent GitHub inspection confirmed uploaded stable-release assets with these exact sizes and SHA256 digests:

| Asset | Bytes | SHA256 |
|---|---:|---|
| Books-Arranger-Setup-0.17.0.exe | 173141509 | `1c6e17972f9410c818d4e4da82d0c506e8f2552cc15587ba4a33e3fae75272dd` |
| Books-Arranger-Setup-0.17.0.exe.blockmap | 180761 | `24a7b666007b7fdc17b26bb29943072ae16f71faf974e5928788bed740ff3cfb` |
| latest.yml | 360 | `8ea1c9e0c39f500d000ca568a33f3ad75518abb1b12cb60e5f5a5b294dbddcfd` |

Keep-four verified: v0.17.0, v0.16.12, v0.16.11 and v0.16.10. Fetch/prune removed the retired v0.16.8 tag locally; local/remote tag identities match and the v0.17.0 peeled target remains unchanged.

Research, including independent source/download options and the original-versus-retailer numbering distinction, is durable in the studio repository: [series source research](https://github.com/Gemanoneko/illuminati/blob/main/Team/Research/BooksArranger/SeriesSources_2026-10-18.md), commit `158d05f65f608cdb5805c0fb266eed20d8028269`. Wikipedia/Ozon/Open Library are research/discovery options, not newly enabled automatic numbering authorities.

## Retained scratch and local outputs

Session scratch remains for Sergei to delete manually: `C:/Users/AnGeLZzZ/AppData/Local/Temp/books-codex-20261018`. Current accepted build, sources and recorded historical review evidence remain preserved. The existing `scripts/clean-dist.js` intentionally preserves prior builds; no supported exact local deletion planner was found, so no new deletion framework or broad cleanup was introduced. In particular, prior `dist/builds/db404224-54fa-4c4a-8d50-602d5cded895`, superseded `dist/builds/d7fce1bd-d21b-40c0-ad11-136b30588ae2`, blocked `dist/builds/4be1f71f-0f5c-4bb5-8bcd-b241101d64a6` and archived manifests/pointers remain retained rather than assuming they are disposable.
