# Books Arranger v0.18.0 — release complete

Sully, 2026-10-18. Installed, local index verified, prior target preserved, processing resumed, and published: https://github.com/Gemanoneko/booksArranger/releases/tag/v0.18.0 .

Final product source is `adef2118ecac4d7c3202e364bbd7c5423fd7baf7`. Annotated tag `v0.18.0` resolves to live-accepted commit `292b7ec0b762e81333a8b7f45bd589dde0d705b2` (tag object `d2cd8d3aad5d366620196b7e831d54fdb6de8089`). This later completion record does not move that tag or rebuild the accepted artifact.

## Final accepted build and live state

Manifest SHA256 `8f3e4b2e39e2a3dddb33b47415af2e444e0009c6bc621fd38890810233a5714b`; build `dist/builds/bc7ac95d-e228-45ca-b87a-61363b8b1494`. Final Senua RELEASE CLEAR and Futaba GO are indexed by `BooksArranger_ReleaseAcceptance_v0.18.0.json`. QA independently matched 229/229 payload files and measured normal Quit in 370 ms with zero active/unsignaled native descendants and no force/timeout; real data fingerprints were unchanged.

The earlier prepublication candidate was superseded after its CLI summary failed on a Unicode title under console cp1251 despite correct index activation. The two-file correction escapes only result transport; receipt/index serialization and active generation identity are unchanged. Eighteen local-index tests passed, including the actual cp1251 roundtrip. No multi-gigabyte replay was needed.

The old running 0.17 finished its book and quit normally. The earlier paused 0.18 also quit normally before final replacement. No process was killed. Final silent installation exited 0; **229/229 installed file sizes/SHA256 hashes** matched the accepted manifest. Normal inactive saved-profile launch at 17:40:31 UTC / 20:40:31 Jerusalem reported backend 0.18.0, PID 36708, instance `b252b1012c8da7be4667200bf85ef7ac`. Its genuine paused/idle state was verified after the normal identity pass completed. Start was then restored once, returning HTTP 202/Running; final post-publication health remained 0.18.0, closing false. The app was left running.

The actual target remains correct:

`Z:\Audiobooks\Лена Обухова, Наталья Тимошенко\Нормальное аномальное - 10 - Призраки белых ночей - Лена Обухова, Наталья Тимошенко.m4b`

Ledger done, empty reason; series #10. Independently recomputed SHA256 `1b09d309248f6c58aa6b4eca614eed5da466e44ec65846baba3263d58af1b7ed`, 279602632 bytes, matching the ledger. Installed ffprobe read correct series/album/track tags and duration 34671.558333 seconds; former path absent. This verifies preservation of the earlier proven rewrite, not a new comparison to a deleted original. Full details: [live acceptance](BooksArranger_LiveAcceptance_v0.18.0_2026-10-18.md).

## Actual local data and source limits

The authenticated full authors/works traversal, gzip EOF/CRC, official hashes, references and SQLite integrity were verified before atomic activation. Ready SHA256 `239ea63175ff732f59d60e6324ec0de67787eaf819843b6d886617921775c3bb` matches registry, immutable completion and retained native identity/size. Coverage is **241 requested / 218 eligible / 23 identity-held**, with **451 works / 427 authors / 0 editions**. Installed-module read-only lookup verified a covered *Our Lady of Darkness* result with explicit candidate IDs, an honest `identity_incomplete` *The Subtle Knife* stub, and `outside_coverage` for an outsider. It did not invent unique authors or series ordinals.

Editions remained a `.crdownload`, last observed 6838370214 bytes at 20:34:14 Jerusalem, and was excluded. No Editions readiness or automatic future import is claimed. Its eventual complete file still requires authentication, EOF/CRC, reference validation and reviewed atomic activation. Existing human-check/source holds remain respected; no provider quota reset or bypass occurred.

Wikidata requires explicit referenced narrative-series/order statements; Wikipedia provides bounded revision/reference discovery, and the initial decisive publisher adapter supports the reviewed Penguin Random House schema. Unsupported layouts and ambiguous identity/order stay held. This release does not claim every provider yielded a live answer or generic Eksmo/Ozon scraping. Studio research: [fallback contracts](https://github.com/Gemanoneko/illuminati/blob/main/Team/Research/BooksArranger/SeriesFallbackContracts_2026-10-18.md), committed `1cba558202e79486ca6da9c8b23dffb36f208a08`.

## Publication verification

The maintained release script ran once against the final prebuilt candidate, exited 0, and verified three assets. Independent stable-release inspection confirmed:

| Asset | Bytes | SHA256 |
|---|---:|---|
| Books-Arranger-Setup-0.18.0.exe | 173192373 | `20784d8607b4c58d3496a9c29cb5ea62230ebc59883789c8a9bf9c4b18cd211f` |
| Books-Arranger-Setup-0.18.0.exe.blockmap | 180731 | `4b5e9b0509a6108a301497123cd487bada5bb4a7343d9226378a13a40c8ab27c` |
| latest.yml | 360 | `8b9ae79ff713bde2ac57d5c0f8f51e36ac160fb3348386824df2c8f0828884fa` |

Keep-four verified: **v0.18.0, v0.17.0, v0.16.12, v0.16.11**. Fetch/prune removed retired v0.16.10 locally; all local/remote tag identities match, with final v0.18.0 peeled target unchanged.

## Retained evidence

Session scratch remains for Sergei to delete manually: `C:/Users/AnGeLZzZ/AppData/Local/Temp/books-codex-20261018`. Actual import/installed-lookup proofs remain under `shared/research/` there. Current accepted output and historical rejected/superseded evidence are preserved. Existing `scripts/clean-dist.js` deliberately preserves previous builds; no supported exact local deletion planner was found. In particular, superseded v0.18 build `dist/builds/817dc432-53b9-4834-b280-cb266a742482`, prior release build `dist/builds/ca0f85ed-aee7-458f-9709-44e9da85ed95`, and their archived manifests/pointers remain retained rather than assuming they are disposable. No new deletion framework, shared safety configuration changes, broad cleanup or extra import was introduced.
