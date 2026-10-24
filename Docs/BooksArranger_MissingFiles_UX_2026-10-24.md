# Books Arranger: files gone from disk are not read errors

2026-10-24, Judy. EXTEND the Files and Book-candidates Status filters, the **Read errors · N** shortcut and the status line (FiltersIncremental UX, 2026-10-09). Ruling: Sergei, 2026-10-24. Ender implements; Sully commits this file before Ender is briefed. Basis: read-only look at `web/app.js`, `web/index.html`, `scanner.py`, `groups.py` and Attention Diagnosis item C. Nothing launched; no rects measured.

## Decision

1. **A gone file leaves the read-error count and list silently.** No toast, banner or new count. A read error is "current unresolved" (2026-10-09); a gone file cannot be re-read.
2. **It stays findable under the existing Status filter "No longer found".** That is the quiet home. No new control or badge: files vanishing is routine here, and a standing "Missing · N" button would turn housekeeping into a chore.
3. **Safe.** `scanner.py` marks a file gone only when a scan finishes with zero errors, so an offline NAS or stopped scan cannot hide a real read error.

## One rule

**Read error = error is non-empty AND the file is not marked gone.** One predicate for the status-line count, the shortcut, the Files "Read errors" filter, the candidates "Source read errors" filter (a member counts only if present) and every row or details display. Count and list always agree. Gone wins over error wherever shown; the old error text stays in the catalog, not on screen.

## What Sergei sees (a gone file that still holds an old error)

| Place | Now | After |
|---|---|---|
| Status line | Files with read errors 1 | Files with read errors 0 |
| Shortcut | Read errors · 1 | Hidden, space reclaimed (existing rule) |
| Files, Read errors | Listed | Not listed |
| Files, No longer found | Listed | Listed |
| Row Status cell | Read error · moov atom not found | **No longer found** |
| Details, reason line | moov atom not found | **Not found in the last complete scan.** |
| Details, Read error section and Notes | Shown, "Start scanning to retry unreadable files." | Hidden; old error not added to Notes |
| Candidates, Source read errors | Book listed | Not listed (its "Source files unavailable or unreadable" note stays) |

**Copy: two strings, both reusing the filter's wording.** "No longer found" also replaces the bare "Unavailable" on gone rows, so row and filter agree. "Not found in the last complete scan." replaces "Missing in last complete scan". Normal text colour, not warning: this is not an error. All other copy is unchanged.

## When the file comes back

No new behaviour. The next scan re-reads it (`scanner.py` reuses only paths with no stored error), and success clears the old error and the gone flag. The row looks normal, with no notice. If the re-read fails (say 0 bytes again), the file is present and unreadable, so it counts as a read error again and leaves "No longer found".

## Controls and hit areas

No new controls or elements, so no tooltip is owed and nothing can cover anything. The shortcut hides at 0 exactly as today.

## Checks for Futaba (committed build, seeded fixture, no real library)

1. One present unreadable file, one gone file with an old error, one gone file with none: status-line count, shortcut number and Read errors list total all read 1 and name the present file.
2. No longer found lists both gone files; the one with an old error shows the two strings above and no old error text anywhere.
3. Remove the present unreadable file: count 0, shortcut hidden, no gap in the toolbar.
4. Return a gone file intact, then scan: normal row. Return it unreadable: it counts 1 again.
5. Candidates, Source read errors: a book whose only flagged member is gone is not listed.

## Not decided here

The collection that held this file still reads "Source files unavailable or unreadable", and `automatic_processing.py` treats a gone member like an error. Whether such a book may still convert is Sergei's call. Offer only.
