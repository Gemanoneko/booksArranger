# Progress rows: what each activity can measure (Ender, notes for Judy's spec)

Date: 2026-10-17. Input for `BooksArranger_ProgressRows_Spec.md`. These notes cover data only; layout, labels and styling are Judy's.

## Why the bar never moved
- The bar is determinate only while encoding (seconds) and while removing originals (N of M). Every other phase shows an indeterminate `<progress>`.
- With `appearance:none` and no animation, an indeterminate bar draws as an empty track.
- Everything before encoding is reported as one phase, "Checking source files". That covers copying sources, re-hashing them, the PCM proofs and per-track normalization. This is why it can sit there for 20+ minutes.

## API shape (new)
`/api/state` gains `activities`, one entry per running activity, in a stable order:

```
{id, kind, title, step, label, state, completed?, total?, unit?}
```

- `kind`: `conversion`, `cleanup`, `temporary`, `published_check`, `scan`, `research` or `recovery`.
- `title`: the book, or the scope (for example "Library").
- `step`: a machine key. `label`: plain words for the step.
- `state`: `running`, `pausing`, `paused` or `attention`.
- `unit`: `bytes`, `seconds`, `files` or `books`. `completed` and `total` are present only when measured. When they are absent, the step is genuinely unknown and should show indeterminate.

## Per activity

| Activity (kind) | Step and label | Data today | v0.16.6 adds | Unit |
|---|---|---|---|---|
| Conversion | Copying source files | none | bytes copied of all sources | bytes |
| Conversion | Checking source copies | none | bytes re-hashed (sources and cover) | bytes |
| Conversion | Reading source audio | none | tracks probed of total | files |
| Conversion | Checking source audio (PCM proof, automatic books) | none | tracks done of total | files |
| Conversion | Normalizing audio | none | audio seconds done of the book total, from FFmpeg | seconds |
| Conversion | Checking joined audio | none | none; one decode pass with no counter | indeterminate |
| Conversion | Converting audiobook | seconds (exists) | none | seconds |
| Conversion | Finalizing conversion | none | none | indeterminate |
| Conversion | Verifying audiobook | none | none; decode check with no counter | indeterminate |
| Conversion | Copying to library | none | bytes copied of output size | bytes |
| Cleanup | Checking recovery copies | none | originals checked of total | files |
| Cleanup | Removing originals | N of M (exists) | none | files |
| Temporary | Removing temporary files / empty folders / former outputs | phase name only | none (short) | indeterminate |
| Published check | Checking finished audiobooks (background after launch, and at Start) | none | books checked of total | books |
| Scan | Scanning library | checked and pending (exists) | as a row: checked of checked + pending | files |
| Research | Researching metadata | counts, plus current book, source and stage (exists) | as a row: books done of this pass | books |
| Recovery | Deleting recovery copies | removed of total (exists) | as a row | files |

## What can run at the same time
- Conversion or cleanup (one at a time, same worker), plus research, plus the published check (after launch or Start), plus recovery deletion when idle.
- Scan never runs alongside conversion.
- Expect 1–3 rows; 4 is possible but rare.

## States
- `paused` or `attention`: the last measured values are kept; the bar is static.
- `pausing`: the work is still running until its checkpoint.
