# Books Arranger sort-title QA — v0.4.4 — 2026-10-10

**Verdict: GO for future-export sort-title metadata.** Actual iTunes sorting and iPhone sync are not verified by this pass. The user confirmed the prior Chapters v2 file imports; that confirmation does not establish this new sort behavior.

Pinned snapshot: `scratch/sort-title-2026-10-10/frozen-1/manifest.json`, 20 files, SHA256 `c5f7dde3ab77203f2ea40ba5c149e592f4753dbcb7a2a820990e5fd5d02d7dc7`. All pins verified before and after testing. Runtime changes:

| File | SHA256 |
| --- | --- |
| metadata.py | 4994a44ae0482738f33eb97a024d21a63f60ffcdf75650d2b8dfa696d961f679 |
| quicktime_chapters.py | 9e68214164866a85764599b499fd60a830e66159424cf3a74320bc36bf99e358 |
| audio_pipeline.py | d42325b4e9141bde9b1c5813fcf6d5537f669e81000dda45a34da30987800342 |
| tests/test_sort_title.py | cc1944de738fed4dba8b825bc67e124a725200181bd4042fd3cb1e9f5976ada7 |
| Docs/BooksArranger_Brief.md | e377add301e3958031159eb2f1340c27750c36cf3e7ec8bf798f235cb7acb558 |

Nine targeted checks passed in 12.54 seconds: three supplied sort-title cases, four supplied QuickTime structural cases, and two independent regressions. Actual backend canonical review → queue → tiny MP3 export ran with chapters on and off. Both produced full title `The Eye of God`, ffprobe `sort_name=Eye of God`, one UTF-8 Apple `sonm/data` atom, verified author, audiobook media kind 2, retained cover, expected chapter count and unchanged source hashes. Existing pipeline validation completed, including source/decoded-duration/tag/cover checks. These are owned generated fixtures, not real-library export trials.

Whole-word case-insensitive leading `The` is removed only for canonical non-Russian (`Other`) language; `Theatre`, `The-Eye`, bare `The`, `A`, `An`, Russian and missing language keep their title. Display title remains intact. Both 32-bit and 64-bit chunk relocation cases pass, with malformed layouts rejected and destination collisions protected.

Independent repeat normalization used actual exported files, not a synthetic metadata-only assertion. Chapter-on output was 10,999 bytes; chapter-off output was 10,408 bytes. Two successive normalizations had zero metadata growth and **identical whole-file bytes** to their original export, proving unchanged media, offsets, title, cover and chapter atoms. A separate synthetic atom check replaced duplicate old `sonm` siblings with exactly one UTF-8 `Éye — 神`, preserved title and cover siblings, and remained byte-idempotent.

Evidence and all 20 exact pins: `scratch/sort-title-qa-2026-10-10/evidence.json`; harness: `check.py`. Direct owned session 16709 exited 0. Services/media subprocesses and handles closed; generated fixture directories contain no remaining files. Unique pinned evidence and harness are retained. No live catalogue, service, original audio, pilot artifact, browser/native application or library was changed.

No Blocker, Major or Minor finding. Pattern alert: metadata readback is not proof of Apple application behavior; disposition **accept scoped structural clearance, retain actual iTunes sort/sync as unverified**. Existing pilot files are unchanged; this rule applies to future exports.
