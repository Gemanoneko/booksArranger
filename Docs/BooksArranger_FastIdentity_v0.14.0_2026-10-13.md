# Books Arranger v0.14.0 candidate — fast identity handoff (Futaba / Senua)

Ender, 2026-10-13. Uncommitted candidate in worktree `scratch/fast-identity-2026-10-13/worktree`, branch `codex/books-fast-identity-0.14.0`, based on main `90c82db`. Sully commits after Futaba GO and Senua CLEAR. Rule implemented: Sergei decision "local evidence is enough when it agrees" (2026-10-12). Its text is the last section of `Docs/BooksArranger_StandingRules_2026-10-11.md` **in the live checkout, still uncommitted there**; this worktree's copy of that file does not have it, so Sully should commit Jane's section together with this release.

## What changed

| Area | Change | Files |
| --- | --- | --- |
| Local identity | New pure module. Compares embedded tags (album / title for one file; author, album_artist, artist) with the file name and the two nearest folders, field by field: 🟢 same script, 🟡 other script or word order, 🔴 conflict, ⚪ missing. Accepts identity only when title and author are 🟢/🟡 and series/number are not 🔴. Records which local fields agreed and how. | `local_identity.py` (new) |
| Research entry | `PublicResearch.lookup` runs local agreement first. Accepted: builds the work, policy, evidence and source gate from local data; the Internet is asked only for missing fields. Not accepted: the existing research path runs unchanged. | `public_research.py` |
| Gap search | FantLab, then Wikidata, for original title / language / series; Open Library, Google Books (no key), iTunes Search for a missing full author name. A catalog answer is used only when its title and author match the local agreement. Optional gaps never hold a book; a missing full author name does (required). | `public_research.py` |
| Admission | `approve_automatic` accepts a `local_agreement` source instead of a fetched credit, only for `identity_basis == local_agreement`, and re-derives the agreement from the current row and folder before admission (`revalidate`). Everything after that (probe, encoding, cover, recording review, manifest, queue, publication, retirement, 24-hour recovery) is unchanged. | `merge_service.py` |
| Evidence | Local citations have no URL; `local_evidence` validates them and is accepted only when the standing facts carry `identity_basis: local_agreement`. `manual_evidence` behaviour is unchanged (validation split into a shared helper). | `metadata_sources.py`, `review_backend.py` |
| Policy | `build_policy(local=…)` stores `identity_basis`, the agreement summary and title basis `local_agreement` (cleaned local title, unknown original language). `validate_policy` checks them. | `standing_metadata.py` |
| Source gate | For local identity only, title comparisons accept the agreed title as a segment of a local name ("Series 03. Title", "Title - 01", bracketed narrator notes). Order, membership, disc/track totals and series checks are unchanged. | `source_identity.py` |
| Scheduling | `_wait` picks the time the candidate can progress: the latest earliest-reopening among fully blocked stages (catalog, discovery, credit pages), instead of the earliest closed source. A local book whose optional gap sources are cooling down waits only while the converter is busy, at most 3 queue drains. | `public_research.py`, `automatic_processing.py` |
| Hosts | Per-host pacing (vendor-published limits only), contact User-Agent (repo URL, no e-mail), DuckDuckGo HTTP 202 / challenge = 1-hour pause, research cache 5,000 entries / 64 MB. New hosts: `www.googleapis.com`, `itunes.apple.com`. `RESEARCH_VERSION` standing-18-v1 gives every waiting/held book one fresh pass. | `public_research.py` |
| Tests | 22 new focused tests + 3 end-to-end admission tests with private audio (real ffmpeg). Research-path test classes now switch local agreement off explicitly (`patch.object(PublicResearch,'local_agreement',False)` in `setUp`) because their fixtures agree locally. | `tests/test_local_identity.py`, `tests/test_local_admission.py`, `tests/test_automatic_processing.py`, `tests/test_public_work_identity.py` |

Not done tonight: cover gap search (embedded or neutral cover as before), conversion-throughput tuning (item 4 of the brief), Google human-verification button (needs Judy).

## Measurement (offline, copy of the live catalog)

Copy: sqlite backup API, source opened `mode=ro`, one attempt, 1.6 s, `quick_check` ok, 2026-10-12 21:19 UTC, after Jane confirmed the app idle. No network, no Z:/Y: reads, every public source replaced by an always-closed stub.

| | Before (`90c82db`, v0.13.1 rule) | After (this candidate) |
| --- | --- | --- |
| Waiting/held books checked | 2,426 (2,360 waiting, 66 held) | 2,426 |
| **Approvable without the Internet** | **0** (2,394 "Book identity uncertain", 32 mixed recordings) | **403** |
| Identity agrees locally | — | 461; 58 of them still held by existing gates (32 sources disagree, 21 playback order, 10 source membership, 1 full author name) |
| Local conflict (title or author 🔴) | — | 1,465, of which 1,309 are split-part files (a file beside other files with the same title) |
| Missing locally (⚪ only) | — | 500 |
| Optional gaps among the 461 | — | original title 413, series 461, full author name 11 (required) |

"Approvable" = identity, source scope, playback order and metadata policy pass with every public source closed. Audio probe, encoding, cover and publication run at admission as before and are not simulated. 30-book chip sample: `Docs/BooksArranger_IdentitySample_2026-10-13.md`.

Calibration on the real copy found and fixed, before this number: titles losing a leading number ("81 миля"), bracketed narrator notes breaking the source gate, a narrator taken as author (James S. A. Corey files name the narrator), "Сборник" taken as a person, and split chapter files each "agreeing" on the book title. The last one alone was about 550 false approvals in an earlier run; it is now a hold.

Biggest remaining lever: the 1,309 split-part files. Today every M4B is its own candidate, so a book split into chapter or part files cannot be one book. Grouping them is a grouping/media change and was not attempted.

## Risks — where to look hardest (Senua)

1. **False local identity.** Tags and folder names created by the same tagger agree by construction; Sergei accepted that. Guards: two different people in author/artist tags are a conflict (resolved only when an author folder names exactly one and no file/folder name mentions the other); a credit listing several people never matches one of them; titles never match across languages; files beside other files with the same title are refused (split books). Look at `local_identity._embedded`, `agreement`, `compare_names`.
2. **Cross-script matcher false positives.** Consonant skeleton + ending check + at least one long word. Short names (2-letter skeletons) can collide; every word must still pair one to one.
3. **Admission integration.** `merge_service.approve_automatic`: the `local` branch replaces only the fetched-credit requirement; `revalidate` re-reads the folder listing from the catalog read-only (`folder_siblings`) inside the existing locks; a catalog read error becomes a held candidate, not a run failure.
4. **Evidence without URL.** `review_backend.save` accepts `source_url == ''` only for `identity_basis == local_agreement` facts that `validate_policy` has already checked.
5. **Source gate relaxation.** `source_identity.source_gate` segment matching applies only when `work['identity_basis'] == 'local_agreement'`.
6. **Pacing.** `HOST_POLICY` numbers and their sources are in the comment above it; actual 403/429/Retry-After handling is unchanged.

## How to test (Futaba)

1. Full suite: `python -m unittest discover -s tests -p "test_*.py"` (timeout 600000). Compare with the baseline below.
2. Focused: `python -m unittest discover -s tests -p "test_local_*.py"` — 25 tests, real ffmpeg for the 3 admission tests.
3. Offline measurement: copy the live catalog only with Jane's go-ahead (backup API, read-only source), then run `scratch/fast-identity-2026-10-13/evidence/measure.py <code dir> <copy> <out.json>` for both `90c82db` (`git archive`) and this candidate. Expect 0 → about 400 approvable.
4. Spot-check `Docs/BooksArranger_IdentitySample_2026-10-13.md` rows against the copy with `evidence/probe_row.py <code dir> <copy> "<title text>"`.
5. After release and Sergei's normal Restart: the first automatic pass revisits every waiting/held book once (research version change). Watch that admitted local books show `identity_basis: local_agreement` in the accepted evidence and that split chapter files stay held.

## Suite result (Ender, this worktree, path length 99 characters)

| Run | Tests | Errors | Failure set vs baseline |
| --- | --- | --- | --- |
| Baseline, pristine `90c82db` in this worktree | 490 | 9 | — |
| Candidate run 1 (before the last two matcher refinements) | 514 | 9 | identical |
| Candidate run 2 (final code) | 515 | 10 | baseline 9 + `test_web…test_restart_guard_rejects_wrong_instance_busy_admission_and_active_research`: tearDown `PermissionError [WinError 32]` (temp SQLite file still open during cleanup), no assertion failed; passed 3 of 3 isolated reruns |
| Candidate run 3 (final code) | 515 | 9 | **identical** |

The 9 pre-existing errors are the known environment/fixture set from `Docs/BooksArranger_QAReport_v0.13.1_2026-10-12.md` (missing untracked `scratch/source-fallback-2026-10-11` fixtures, `baseline_native_io.py`, `BrowserServer.loaded_version`, path length). Known flakes seen: `test_waiting_uses_earliest_candidate…` (pre-existing F4, 1 of 3 file runs) and the test_web tearDown lock above.

Evidence kept for QA (not in Git): `scratch/fast-identity-2026-10-13/evidence/` — the catalog copy (377 MB; delete after QA), `measure-before.json`, `measure-after.json`, `copy-receipt.json`, the scripts and the suite outputs.
