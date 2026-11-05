# Books Arranger — requests for the next version after 0.25.0

## Universe dropdown options

Requested by Sergei on 2026-11-05. Status: queued for the next version; not implemented in 0.25.0.

Add these selectable values to the existing Universe dropdown in Edit names, using the requested spelling:

- Warhammer 40K
- SCP
- Eve Online
- World of Warcraft

Preserve the existing Series and Universe dropdown interaction. This request adds choices; it does not request automatic reassignment of existing books or changes to live library data.

Implementation owner: Ender. Focused verification owner: Futaba.

## Queue pause and misleading status — prepared for next release

Reported by Sergei on 2026-11-05 while using 0.25.0. Implemented and pushed through source commit `885264ef7568fb94b1797a861ba9866a4a85d4af`; not packaged or released.

- A protected prior working attempt for «Возрожденный Дракон» caused a book-specific restaging refusal to pause the entire queue. The fix holds that book while unrelated jobs continue, preserving the retained files and ownership safeguards. Unknown boundary/systemic errors still stop work safely.
- The audiobook card now distinguishes conversion queue state from concurrent metadata research. Pre-conversion claimed work is described as checking pending work rather than implying encoder progress. An unattributed interruption is not assigned the unrelated «Похититель детей» cleanup hold as its cause.
- Queued Edit names text distinguishes in-memory pending edits from a successful durable save, including cancel and uncertain-response states. This copy change does not make pending actions durable across restart.

Futaba independently passed 31 focused lifecycle tests on `433885d` and 26 progress/status Python tests plus three DOM scripts on `885264e`, using private fixtures. These are focused source checks, not packaged-build or release clearance. Live files and app controls were not changed. See the dated ResumeHold focused QA reports and evidence for exact identities and limitations.

## Tolkien approval error — prepared for next release

Sergei reported `Approve cancelled: 'retrieved_utc'` for The Return of the King and The Two Towers and explicitly requested its repair. Source commit `11b1e0227812326da2ea4905a8ebedfe961d13a7` repairs the curated-decision producer/consumer contract without weakening generic manual/public evidence rules. The Fellowship of the Ring and legacy Middle-earth path are covered too.

Senua's bounded source review is clear. Futaba independently passed 74 focused checks on the committed source after correcting one omitted committed evidence fixture in her private test copy. This is not packaged-build or release clearance. Own Tolkien implementation scratch cleanup was refused before command launch; retained paths are recorded in `Docs/Evidence/approve-retrieved_2026-11-05/cleanup-status.json` and must not be removed through an alternate route.

## Persistent Save/Approve and automatic Resume label — prepared for next release

Sergei explicitly superseded the queued Save UX: Save and Approve must promptly retain decisions on disk rather than cancel because another book is busy, survive restarts, and clean temporary payloads after application. Committed design and UX contracts are `BooksArranger_DurableDecisions_Design_2026-11-05.md` and `BooksArranger_DurableDecisions_UX_2026-11-05.md`. The prior queued-save wording above is an intermediate fix, not the final requested behavior.

The complete implementation is committed through `c567adbaa8e7b57109ac9a5c979aee228fd7c3b1`: ledger foundation `c92b724`, Names backend `9bcc58b`, consumer transactions `229a5c2`, six-action backend wiring `03fe85f`, and frontend `c567adb`. Save/Approve acceptance commits durable decisions promptly without waiting for unrelated worker locks. Atomic per-step/application receipts, immutable payload and revision/source binding, restart recovery, and request-ID reconciliation prevent lost or duplicated decisions. Later validation holds retain the decision with a specific reason. Completed payloads are pruned while compact idempotency receipts remain.

The frontend preserves newer text/nontext edits, restores accepted choices with current-source binding, retains uncertain requests through lost replies and authentication/status failures, and permits a fresh explicit retry after a terminal needs-review hold. All six Save/Approve sites use the durable transport. Paused automatic processing now shows Resume automatic processing with matching help and tooltip text; its existing whole-workflow behavior is unchanged.

Senua's bounded backend/frontend reviews and Judy's final source/spec audit are clear for the recorded source identities. Futaba independently passed 54 backend Python tests, 32 affected DOM scripts, and all six actual production JS-to-Handler routes on archived commit `c567adb`, with normal ownership closure and zero native residue. This is focused source QA, not a full check, installer/native UI test, or release clearance. No version bump, package, release, live-source mutation, focus change, or installed-app update was performed. Universe dropdown additions above remain queued as requested.
