# Books Arranger: connection recovery and inventory units

Date: 2026-10-09. Scope: a minimal web-interface copy/state correction during the read-only inventory milestone. Preserve layout, theme, scanner, saved queue and catalog. No new screen, setting, book grouping or conversion UI.

## Connection notice

A failed browser request does not establish that the local scanner stopped or that the server is unavailable. For a polling transport failure use:

**Browser connection interrupted. The scan may still be running; retrying…**

Keep existing inventory/status visible while reconnecting; the notice explains that those values are the last received information. Do not add the raw `Failed to fetch` suffix to this notice. Do not display this notice for an individual source-file read error or a backend response that reports a specific validation/authentication/server error; retain that error's meaningful message instead.

The connection notice is independent of action/review feedback. Place it as a separate status paragraph immediately after the current action-message paragraph, in the same scan-control panel. Hide the connection paragraph when empty; use polite live-status semantics and the existing message styling. On the first complete successful poll for the currently selected library, automatically remove only the connection notice. A stale response from another library, an ignored response, or a state response followed by a failed required inventory request does not count as recovery. Do not erase review success/failure messages, unsaved-review indicators, actual backend scan errors, the Errors counter or selected-file read-error details. Ender chooses the smallest state implementation that keeps these message classes separate.

Repeated failed polls keep one notice; do not append duplicates or repeatedly announce unchanged text. A successful poll clears it without a persistent 'reconnected' toast. A later failure shows it again. Intentional Stop server retains its existing shutdown text and must not subsequently show the reconnect notice.

## Inventory, not distinct books

Change **Catalog N** to **Files cataloged N**. Change the inventory section's visible label, where present, to **File inventory**. Page numbering becomes **Files A–B · 100 per page**. Counts are files, including separate chapter tracks, rather than grouped books.

Add one concise helper sentence next to the existing inventory introduction:

**Each row is a source file, including chapter tracks and companion files. Book grouping, online metadata matching and merging are later steps.**

Keep this adjacent to the table rather than adding a modal, dismissal control or setup flow. Do not label a source MP3 row as a verified book, a conversion result or a completed arrangement. Existing destination paths remain proposals under the current read-only notice.

Use the confirmed units for the other status labels: **Files checked N**, **Files reused N**, **Pending tasks N**, **Read errors N**. Checked and Reused refer to files handled during this scan; Pending includes directory and file queue tasks. Read errors can concern files, metadata or directories and are not a unique count of broken books. Files cataloged includes audio and companion records; do not imply that it counts only playable audio. This addendum changes labels only, not counters or scan behavior.

## Verification and handoff

Use an isolated candidate and mocked requests; leave the active scan, live server and user browser untouched. Check: failure then success; repeated failure; state success plus inventory failure; stale-library success; action/review message plus connection failure/recovery; actual source read error plus a successful poll; and intentional shutdown. Confirm separate chapter files count as files, with no inferred distinct-book total.

Design basis: NN/g visibility of system status and plain-language error recovery. The scoped notice distinguishes uncertain connection state from scanner failure, and explicit units prevent misleading interpretation without introducing additional decisions.

Sully commits and pushes this spec before the implementation brief cites it. Ender owns the front-end patch and chooses whether publication is bundled with the anthology changes; this spec authorizes no service restart or live-page refresh. No UI launch, code edit, catalog/library write, or disposable probe output was created for the spec.
