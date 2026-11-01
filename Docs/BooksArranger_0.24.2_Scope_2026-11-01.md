# Books Arranger 0.24.2 — approved scope

Sergei approved on 2026-11-01: “The scope is everything that is in backlog + the bugs”, followed by “Go”. Earlier draft recommendations to defer backlog items are superseded. This extends the existing tool; preserve unrelated behavior and safety protections.

## Included work

- Installed 0.24.1 paused/stalled Start and Resume: unrelated old cleanup checks, misleading activity, duplicate starts, pause attribution and safe interruption. The app recovered without agent intervention; no thread snapshot was taken.
- Ruling 78: Start over returns the book to automatic processing while preserving actual user choices; the changed-source offer appears promptly.
- Every open Senua 0.24.1 finding: M1, M3; m1–m8, m10–m12. m9 is already resolved and must remain resolved. Fixed M2/M4/M5 remain safeguards.
- Every Futaba 0.24.1 minor m1–m5, O1 recovery-cleanup retry, P1 delayed disk-change/fault recovery, and the carried 0.24.0 finished-output-held-open issue. Close the documented exact folder-fault, engine-load and S8 validation gaps as applicable to the changed work. Existing safe root/direct-child protection remains; a retained folder is explained accurately rather than deletion scope broadened.
- Choose folder delay: diagnose and address the application-controlled cause; measure external dialog/NAS limits honestly without taking focus or controlling Sergei’s app.
- McCammon: recognize the confirmed Matthew Corbett series and positions, and correctly handle The Queen of Bedlam’s internal sections without generic unsafe merging.
- Tolkien: preserve successful research in grouping preview and approval despite HTTP-cache eviction; retain original titles, exact cycle spelling “Властелин колец” and positions 2/3, plus the confirmed Middle-earth universe relationship through existing naming rules. Internal Books 3–6 are not trilogy positions.
- Tolkien chapter refusal: correct the proven terminal-end metadata case only with full-audio proof and preserve audio, chapter names, start times and order; give actionable file/chapter/timing explanations. No blanket weakening of chapter validation or dropping chapters.

## Source records and completion tracking

Detailed findings and all backlog item descriptions are in:

- `BooksArranger_PausedCleanup_Diagnosis_2026-11-01.md`, including its complete backlog disposition table. All open items now need an outcome in this release, not the draft deferrals.
- `BooksArranger_SeriesPreview_Diagnosis_2026-11-01.md` and `BooksArranger_DiagnosisEvidence_2026-11-01.json`.
- `BooksArranger_CodeReview_v0.24.1_2026-10-31.md` and `BooksArranger_QA_v0.24.1_2026-10-31.md`.
- `Team/Docs/BooksArranger_Rulings_2026-10-24.md`, rulings 74e–78 and relevant existing naming/safety rulings.

Ender records each included item’s implementation and verification in a completion matrix. Judy owns visible behavior and copy. Futaba checks the changed behavior only; Senua reviews the accumulated release diff. One full entry check per build, with receipt/hash comparison instead of duplicate full runs.

## Standing limits

No writes to Z: or live `data/`. No QA installs on Sergei’s profile. No mouse/focus interference or app control. No running-thread snapshot without a fresh request and permission. The four-file Tolkien read-only timing inspection was already completed; it authorized no source repair. Use private fixtures and isolated profiles. No Claude attribution. Preserve other sessions’ edits and recovery data. Clean verified owned temporary output.

Tray-history exceptions require Sergei’s separate OK for this release; prior versions’ exceptions do not apply. Firefly stays a per-book Choose folder decision; no multi-author-series feature was ordered.
