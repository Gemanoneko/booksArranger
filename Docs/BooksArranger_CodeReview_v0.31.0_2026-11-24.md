# Code Review — Books Arranger v0.31.0 (release acceptance)

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-11-24
Tool: Books Arranger
Release: v0.31.0
Commit range: v0.30.1 (50c4d4b)..d96979d (merged to main in cf7c905)
Type: release acceptance; no new code read
```

## What this report is

This is the release-acceptance code review for 0.31.0. It certifies `v0.30.1..d96979d`. It reads no new code. It rests on the five committed reviews below. Each one found no open Critical finding and the safety floor intact. Together they cover the range with no gap.

| Report | Range it certifies |
|---|---|
| [Full review](BooksArranger_CodeReview_v0.31.0_2026-11-23.md) | `50c4d4b` (v0.30.1)`..a8b6804` |
| [Delta 1](BooksArranger_CodeReview_v0.31.0_delta_2026-11-23.md) | `a8b6804..8cc8c5a` |
| [Delta 2](BooksArranger_CodeReview_v0.31.0_delta2_2026-11-23.md) | `8cc8c5a..7023cc9` |
| [Delta 3](BooksArranger_CodeReview_v0.31.0_delta3_2026-11-24.md) | `7023cc9..399caea` |
| [Delta 4](BooksArranger_CodeReview_v0.31.0_delta4_2026-11-24.md) | `399caea..d96979d` |

## Checks

I ran these read-only in the main checkout on 2026-11-24, on `main` at `b64af88`.

1. **Manifest: pass.** `sha256sum dist/release-artifacts.json` matches the pinned SHA-256 below. The manifest's `source_head` is the full hash of `d96979d`, and its `version` is `0.31.0`.
2. **Ancestry: pass.** `git merge-base --is-ancestor d96979d HEAD` exits 0. HEAD is `b64af88`, a docs commit. Its parent, `cf7c905`, merges `ender/0.31.0` at `d96979d`.
3. **No code after the reviewed commit: pass.** `git diff --stat d96979d HEAD -- . ':!Docs' ':!CHANGELOG.md'` prints nothing.

## Deferred findings

No Critical finding is open. Majors M1 to M8 are all closed: M1 to M3 in delta 1, M4 and M5 in delta 2, M6 in delta 3, and M7 and M8 in delta 4.

These Minors stay open and are deferred to the next version:

- **m16** (delta 3): under a saved Pause, a write that has begun finishes even when nothing of his waits for it. For a write he approved himself, its follow-up queues a move that the queue does not park, so the move runs under the Pause.
- **m17** (delta 3): the writer thread and the queue thread can run one write's follow-up at the same moment. The later write-back erases the recorded follow-up.
- Earlier Minors that are still open:
  - **m1:** stalled moves don't count against the two-book limit.
  - **m2:** a write that becomes blocked after dispatch holds its slot indefinitely.
  - **m3:** a doubtful source does not make the book doubtful.
  - **m4:** the 0.30.0 approval route bypasses the write of names.
  - **m5** (partly fixed): a held write of names still reports series wording.
  - **m6:** a write of names in flight at a rollback to 0.30.1 is never finished there.
  - **m7:** `NameWrite` inherits `SeriesBackfill` wholesale.
  - **m8:** the two writers keep out of each other's way by check-then-act reads, with no lock.
  - **m10** (delta 1): a Quit or restart between a write and its follow-up drops his choice.

## Verdict

No Critical finding is open, and the safety floor is intact.

Release source commit: d96979d8acae368e6fc76245cb502dfa76a7772a
Release artifact manifest SHA256: fec4eabb51f751e0fef639d8aa7252ed926a9b09e429c1eb8934fe56b2af35ef
**Verdict:** RELEASE CLEAR
