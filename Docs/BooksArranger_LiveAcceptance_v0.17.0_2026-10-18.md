# Books Arranger v0.17.0 — live target acceptance

Sully, 2026-10-18. The accepted v0.17.0 installer was applied and the requested real target verified before processing was resumed or the release tagged.

## Accepted source and installation

- Product source: `e028fc04c4b30ee26b6960f90948526205acb3ac`.
- Manifest SHA256: `3797c7d5117abdaf2f1cdd9b5879e7d8b51dfb370d6c9064b4c148f762716584`.
- Installer: `dist/builds/ca0f85ed-aee7-458f-9709-44e9da85ed95/Books-Arranger-Setup-0.17.0.exe`; SHA256 `1c6e17972f9410c818d4e4da82d0c506e8f2552cc15587ba4a33e3fae75272dd`, 173141509 bytes.
- Artifact-bound Senua RELEASE CLEAR and Futaba GO are indexed by `BooksArranger_ReleaseAcceptance_v0.17.0.json`; release preconditions passed four checks.

The previous 0.16.12 received one normal `--quit` at 15:53:22 UTC. It finished «Они жаждут» through publishing; port 5210 closed and no Books Arranger image remained. No process was killed. Silent `/S /currentuser` installation exited 0. Independent installed-file verification matched all 225 manifest payload files by size and SHA256; backend VERSION is 0.17.0.

The normal Start-menu target launched with `--show-inactive` and its existing saved profile at 16:00:22 UTC / 19:00:22 Jerusalem. Backend PID 93020, instance `fe8b54eeee67f896a3e9c693802c4f3c`, health 0.17.0, closing false. One initial state read returned 503 during startup; the next succeeded. Automatic processing was genuinely Paused, activities empty, no current conversion, cleanup or postprocessing. No Start was sent until the target below was complete and verified. The standard scheduler performed the work; no fake idle, quota reset, direct apply or maintenance CLI was used.

## Real scheduler and target result

At 16:02:49 UTC the ledger had four deferred books, demonstrating that a FantLab wait no longer aborted the pass. Example `96f89af4-c6ce-46ad-a795-bd792445c6c1` recorded `api.fantlab.ru: Books public research hourly host request bound reached`, app-limit/host scope, next attempt `1792340260.0182405` (16:17:40 UTC). Later observation showed 232 deferred and one done; the normal provider allowance remained intact.

Target job `0d7a3865-0a02-4f80-9f67-019982f2f141`, candidate `9966457b-69e7-4395-a35e-7597eb8f2145`, reached **done**, empty reason, at **16:03:45 UTC / 19:03:45 Jerusalem**. Its series is **Нормальное аномальное**, number **10**, provider Goodreads, source `https://www.goodreads.com/series/249925`.

The ledger retains the independently joined exact-title/all-author Goodreads search receipt (retrieved 15:40:38.466083 UTC, SHA256 `65bd117943f63997b855046bd568adb4e72973f1251fb40e3f349cbbff8cee06`) and explicit series-entry receipt (retrieved 15:37:39.361835 UTC, SHA256 `d93f48f7949a5ce96d0a9aba69f6a5664615907c7840c403fc4e4ed60761ad8f`). These cached receipts were used without new target provider requests.

Verified final file:

`Z:\Audiobooks\Лена Обухова, Наталья Тимошенко\Нормальное аномальное - 10 - Призраки белых ночей - Лена Обухова, Наталья Тимошенко.m4b`

- File exists, size **279602632 bytes**, matching the done ledger.
- Independently recomputed whole-file SHA256 **`1b09d309248f6c58aa6b4eca614eed5da466e44ec65846baba3263d58af1b7ed`**, matching the done ledger.
- Installed pinned ffprobe exited 0: readable QuickTime/M4B container, **34671.558333 seconds**, matching the retained original duration; AAC audio, 44100 Hz, stereo, 15 chapters and attached pictures.
- Actual tags read back: grouping `Нормальное аномальное`, track `10`, album and sort-album `Нормальное аномальное - 10 - Призраки белых ночей`; title and both authors remain present.
- Former `Призраки белых ночей - Лена Обухова, Наталья Тимошенко.m4b` is absent. The exact temporary `.books-arranger-series-0d7a3865-0a02-4f80-9f67-019982f2f141.m4b` is absent. The done record includes `removal_intended: true`, original identity/ancestry and original hash `122b54d2f07390aec1eff2ad289b5dee8ef8a5d62d324c101f6ddd096b7c0a30`.

Audio preservation was verified by the reviewed installed app path, which requires old/new media-byte, compressed-audio and decoder-configuration proofs before recording done and disposing of the exact former file. The surviving file's full hash, container, tags and duration were independently checked afterward. The original/new comparison was **not independently replayed after deletion**, and no new full decode or audio playback was performed. Senua accepted this calibrated evidence with no blocking gap.

## Resume and release handoff

After target acceptance, the existing authenticated Start action was sent **once**, returning HTTP 202 and Running. The user app remains running. No real Retry actions or additional Start/Quit controls were submitted. Sully may now annotate and push `v0.17.0` at the accepted documentation HEAD and run the maintained release script once; publication results belong in the final completion record.

Session scratch remains for Sergei: `C:/Users/AnGeLZzZ/AppData/Local/Temp/books-codex-20261018`. No shared safety configuration or provider budget was changed.
