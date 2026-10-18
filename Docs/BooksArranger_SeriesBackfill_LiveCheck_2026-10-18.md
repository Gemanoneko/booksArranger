# Books Arranger v0.16.12 — live series-backfill check

Checked 2026-10-18, approximately 15:23–15:26 UTC / 18:23–18:26 Asia/Jerusalem (UTC+03:00). Ender; read-only observation and diagnosis. Product source: `09714f2a0a607f670a14c120e32f12dad2d2158b`.

## Measured live facts

- Health reported version 0.16.12, PID 23604, instance `25440822267b795414f9e4c9b8d3dd23`, `closing: false`. Automatic processing was Running; the current conversion was *The Oppenheimer Alternative*, checking, with 111 queued jobs. The app was left running.
- `series_update` was null. A read-only SQLite connection found zero rows in `series_backfill`; no completed, deferred or failed backfill record was available.
- Latest completed target job: `0d7a3865-0a02-4f80-9f67-019982f2f141`, candidate `9966457b-69e7-4395-a35e-7597eb8f2145`. Its title is «Призраки белых ночей», canonical author `Лена Обухова, Наталья Тимошенко`, series and number both empty. Source cleanup, storage cleanup and source-folder cleanup were completed; recovery retention was deleted. There was no target backfill entry.
- Current original path: `Z:\Audiobooks\Лена Обухова, Наталья Тимошенко\Призраки белых ночей - Лена Обухова, Наталья Тимошенко.m4b`. It exists; measured size 279,602,502 bytes equals its recorded size. Recorded SHA256 is `122b54d2f07390aec1eff2ad289b5dee8ef8a5d62d324c101f6ddd096b7c0a30`; this check did **not** recompute the full file hash or decode audio. The existing validation record reports passed, profile `aac-normalized-or-m4b-copy-quicktime-v4`, duration 34,671.558333 seconds.
- Proposed series path, derived read-only with the existing naming function and the requested metadata, does not exist: `Z:\Audiobooks\Лена Обухова, Наталья Тимошенко\Нормальное аномальное - 10 - Призраки белых ночей - Лена Обухова, Наталья Тимошенко.m4b`.
- First eligible completed candidate in the current ordering is *MirrorMask*, job `0b6fedcc-2d95-46a9-a4a3-4192da37ff72`. Its Goodreads search response was fetched at approximately 15:15:42 UTC and remains cached. The cached bytes match their stored SHA256; pure parsing with the shipped series lookup returns no series. Its FantLab fallback URL, `https://api.fantlab.ru/search-works?q=MirrorMask&onlymatches=1`, is uncached.
- The shared `api.fantlab.ru` request history contained exactly 100 reservations in the preceding hour, matching the configured limit of 100/hour. Applying the existing read-only readiness calculation gave the next slot as `2026-10-18T15:27:31.373274+00:00` / 18:27:31 Asia/Jerusalem, approximately 124 seconds after that measurement. This was a snapshot, not a promised completion time; automatic research shares the allowance.

## Diagnosis from the measured state and shipped code

The evidence supports the following deferral chain: *MirrorMask* → cached Goodreads result without a series → uncached FantLab fallback → exhausted shared hourly allowance → `ResearchWait` → backfill `Later` → return from the entire pass. The background loop clears visible progress and waits 600 seconds; this deferral does not write a ledger reason. Consequently, the target is not reached by that pass. This is an explanation from the recorded cache/quota state and inspected control flow, not an injected exception trace from the live thread.

An independent requirement also applies: `_idle()` defers file changes while conversion, cleanup or scanning is active. Source lookup availability alone therefore does not guarantee an immediate rewrite while the observed conversion continues.

An initial DuckDuckGo human-check hypothesis was corrected during diagnosis: the series-specific Goodreads/FantLab methods do not use DuckDuckGo discovery. Its separate pause does not establish the cause of this series-backfill deferral.

## Outcome and proposed remedy

The requested series update was **not observed**. Blank catalog metadata, absent destination and empty ledger do not support a claim that the target was rewritten. No new-file integrity or playability proof is claimed.

Smallest proposed correction: persist a per-book deferred reason and next-retry time, and continue other eligible Goodreads lookups when one candidate must wait for FantLab. Preserve all provider allowances, Goodreads precedence, exact-file safety proofs and the independent idle-only write gate. This proposal has **not** been implemented; no product code was changed by this check.

Only loopback health/state reads, narrow read-only catalog queries, cached-response parsing and file existence/size checks were performed. No provider requests, Start/Retry/stop controls, catalog/library writes, metadata edits, process termination, audio playback or desktop activation were performed. Sully owns committing and pushing this note.
