# Books Arranger actual batch QA — v0.4.4 — 2026-10-10

**Verdict: GO for the two completed artifacts, within structural and source-preservation scope.** Actual iTunes import, sorting, iPhone sync and playback were not tested. The intended source sets are accounted for; external publisher recording completeness remains unknown.

| Book / actual output | Sources / chapters | Source bytes | Output bytes | SHA256 |
| --- | ---: | ---: | ---: | --- |
| `Z:\Audiobooks\Gaiman Neil\MirrorMask - Gaiman Neil.m4b` | 11 / 11 | 114,906,562 | 117,288,173 | fee7f5119803919d9571905f640fad8fce50ca803f528ed5396e124b6dc988d5 |
| `Z:\Audiobooks\Sanderson Brandon\Snapshot - Sanderson Brandon.m4b` | 10 / 10 | 243,387,177 | 254,315,402 | 8fa450ff941c48833c3d4ea7705ec837741dc150b74d251ecc2de38e49d5ea70 |

Each actual output was independently streamed for SHA256 and size, with opened-file size/mtime/identity stable across the read. Bounded ffprobe and compressed-cover extraction confirmed one AAC stream, one exact selected cover, correct title/author/album/audiobook kind 2, and all chapter titles/boundaries against the approved manifest. Actual MP4 atoms were read directly: faststart `ftyp/moov/free/mdat`, one conforming 65-byte legacy text description with Pascal `Arial`. No metadata rewrite or output modification occurred.

MirrorMask: source-derived target 191,719 b/s, stereo 44,100 Hz; source stream rates range 191,698–191,719 b/s. Exact included-source PCM duration 4,779.440 seconds; producer full output decode 4,779.456145 seconds, inside its 1.1-second tolerance. Actual 11 `Chapter 1`–`Chapter 11` markers match the saved PCM-derived boundaries. Author is Neil Gaiman. Reader remains unverified and blank. Source album/date clues remain in Comments. Selected cached PNG cover SHA256 `2e56990ec185048fba35334a4b9d583dec34e68dd440f20c1a7da084f9a27da1` matches the actual attached image; producer separately records its correspondence to source JPEG artwork.

Snapshot: source-derived target 192,000 b/s, stereo 44,100 Hz; all ten input streams report 192,000 b/s. Exact source and fully decoded output duration are both 10,095.38612244898 seconds. All ten original Russian chapter names and PCM-derived boundaries match. Author is Brandon Sanderson; Comments retain the original Russian reader credit/link plus reviewed narrator Олег Булдаков and source album/date/publisher clues. Actual attached JPEG SHA256 `bca7ca57a9d477bd2b19c8813e0be2fb0b3fac0b3266115b9ad036148e109b67` matches the selected cover. Output sizes exceed source sizes modestly; the accepted quality-first policy does not force compression to a byte ceiling.

Evidence pins:

- Producer `scratch/next-batch-2026-10-10/MirrorMask-completed-proof.json`: `7b38ddf78e445a1d9238fcae869ff1c425ee69657baaf8778af1f03b801bd8e2`.
- Final combined producer `scratch/next-batch-2026-10-10/completed-proof.json`: `89d248ccb87c20f9ad01accca0b99e634d1ccc89b3d819ace2e91498b9f3eb5e`; both jobs completed, all 21 originals streamed by producer and SHA/size/ns unchanged. QA compared preservation records with the manifests and reused the full-decode receipt rather than repeating audio decode or source hashing.
- Independent compact actual-file checks: `scratch/next-batch-qa-2026-10-10/MirrorMask-evidence.json` and `Snapshot-evidence.json`; reusable read-only driver `check.py`. MirrorMask job `0b6fedcc-2d95-46a9-a4a3-4192da37ff72`; Snapshot job `dc4874af-e132-47cd-93ab-85e5b0fbeea7`.

Both owned bounded command sessions exited 0; handles and media probe children closed. No temporary media, browser leases or fixture services were created by this pass. Unique proof files are retained. No live controls, catalogue writes, library changes, native applications, listening tests or Git actions occurred. No Blocker/Major/Minor finding. Pattern disposition: accept structural validation and preserve explicit Apple-device and external-completeness limits; no broader library-conversion claim.
