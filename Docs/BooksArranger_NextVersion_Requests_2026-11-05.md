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
