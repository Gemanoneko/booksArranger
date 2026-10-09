# Books Arranger QA: grouping and filters v0.3.0 candidate

Date: 2026-10-09. **Verdict: GO** for the frozen grouping/filter prototype. Candidate marker remains 0.2.2; publication version and any later provider/merge feature need their own handoff. No Blocker or Major found. This acceptance covers the persisted metadata candidate and inventory workflow; it does not authorize conversion or claim recording completeness.

Copied Ender's frozen `scratch/grouping-2026-10-09/candidate`, extending accepted anthology roles, dark theme and recovery guards. Committed UX references: grouping 6bc52f2 and filtering 643d92e. All 18 files matched after testing. Preserved full accepted manifest: `scratch/grouping-qa-2026-10-09/accepted-manifest.json`, SHA256 **5f1489846dba00404212db728035953925d1a5e00a332d678d923efb13f98fc2**.

| Changed runtime file | SHA256 |
|---|---|
| groups.py | fcee796e0f974e6f70e68b31e3cc7c30332735a56a789cb50ae0d50736a0ebfb |
| scanner.py | 48e1d005ffa95140d0702615dae8c680dd70a1ca0ab5191e98bbd00f0692f655 |
| web_server.py | 4251c3f9435bdd0007e55c45d06cb254016b1a10fbcb9450d2d50d7f935064b7 |
| web/index.html | 5fe36c8ab1279dd88541e46d07f0684db07f1b2477897fa2f8b6acd820d614cf |
| web/app.js | 68be1aa68b5a0b49f12775fe1c18feed64a80aaf345efbc55f6fcbece0f4e772 |
| web/style.css | 718b5a47b6d052d42afab34778b79c9f4db07d5560460cb65fc2adf8e2d5b288 |

## Independent engine/data checks

**19/19 passed.** Real scratch scans verified a failed read counts as one checked file, one run failure and one unresolved file. A fresh discovery pass reuses healthy unchanged metadata and reads only prior errors; new/changed files are read while unchanged files are reused. An intentionally changing scratch source during read invalidates its saved review, retains concrete before/after size and integer nanosecond evidence, and resolves on a successful fresh retry. Stopping and reopening preserves pending progress; partial scans do not establish missing files, an accessible completed resume does, and offline roots preserve records. A deliberately failed directory yields a separately inspectable scan issue without a fake file or unresolved-file count.

Catalogue fixtures then verified whole-library filtering before pagination: 125 error files produce 100 then 25 results; query AND status can produce zero results despite healthy query matches. Track zero and 1/2/10 remain ordered and included; exact modified value 1700000000000000101 survives as a string. Draft review is distinct from explicit approval. Persistent UUID remains stable when a member is added, evidence revision increases, saved approval is invalidated, and a stale revision is refused. Matching disc folders group and order disc 1 before 2. Mixed work/reader clues prevent approval. Order-only numeric conflict/ties remain visible separately even when canonical metadata is approved.

## Actual browser/API checks

**8/8 groups passed** through the studio guarded isolated browser. Error shortcut clears query and reaches both error pages; status applies the current query and resets pagination. Error details show concrete retry advice and an older snapshot label, without asserting corruption/deletion. Details remain visible when their row is filtered out. Clear returns all files and first page. Candidate draft and explicit approval work end to end, while membership, completeness and track order remain Needs review. Approved filter works; mixed recording approval remains disabled with its reason. Files/candidates retain separate filter choices, and the error shortcut remains reachable.

Twenty control rectangles were measured: ten at 1,440 CSS px and ten at 700 CSS px, all at least 24 px tall and pairwise nonoverlapping. No page-wide overflow; tables retain their existing horizontal scroll. Evidence: `scratch/grouping-qa-2026-10-09/rectangles.json` and actual screenshots `screenshots/candidate-1440.png`, `candidate-700.png`, `error-wide.png`, `error-narrow.png`. Jane viewed all four and accepted the captured fields as readable, dark styling/layout stable, and no apparent overlap. These captures do not imply a global pixel guarantee.

The catalogue-heavy screenshots intentionally follow an injected directory failure: this scan's checked counter is zero and one directory failure is shown alongside manually seeded library records. Those synthetic counts do not indicate a scanner counting defect. No synthetic catalogue record asserts a real source exists.

Targeted supplied regression checks passed: ten Python grouping/filter tests and three actual-script Node receipts covering fingerprint/polling, anthology/comment boundaries, and connection/filter recovery behavior. No unchanged broad engine rerun or formal prototype gate. Two early browser-driver attempts were corrected for the table's source title-clue column and awaited asynchronous filter result state; app source was unchanged and the complete final pass succeeded.

## Live errors: read-only reachability

Production had not acquired these new filters. An authorized GET-only enumeration of its existing inventory pages reached all **9,550** distinct saved paths and **22** distinct paths with read errors. Original PID 3100 and instance 1171e36d693625c4667d9a276e28826c remained unchanged. No live scan, review, shutdown or restart control was used. This proves the records are reachable; it does not resolve those errors or establish damaged books. Ender's separate diagnostic found 21 prior transient size/mtime mismatch reads subsequently stable and readable, plus one empty audio file; physical cause of the transient changes remains unproven.

## Safety and cleanup

Own fixture port 5211: PID 10448, instance af236d2531850d83ee3912209ce56b0e, session 21965. Protected shutdown succeeded and actual process exited code 0; exclusive bind confirmed the port released. Final browser driver exited code 0; lease 7afe32b2e0ad reported remaining 0. Earlier diagnostic leases 11d2bc1fe4f6 and c5c34f1adc04 also cleaned to remaining 0. The engine tests intentionally changed/deleted only designated scratch sources to exercise arrivals/missing/read races. The two remaining sources matched their post-engine hashes throughout browser/API reviews, then were removed by exact verified scratch paths. Frozen snapshot, catalogue, hash/rectangle evidence and screenshots remain preserved. No real library bytes, user browser tabs or native PC input changed.

## Findings, limitations and pattern disposition

No app defect identified. General prototype tooltip polish remains **defer** to Daily Use; new view/filter/approval controls have their specified help. Membership/order resolution editors and merge are explicitly outside this candidate. Cached catalogue evidence updates on discovery; metadata approval stays distinct from recording/order approval and offers no merge readiness. Later provider, grouping resolution or source-preserving merge changes require a fresh frozen QA pass. Existing source-read diagnostic uncertainty is recorded rather than labelled corruption or silently declared fixed.
## Final published v0.3.0 correspondence

Fresh guarded browser GET-only proof displayed `v0.3.0 · local prototype`, `Source: Z:\Audiobooks`, dark canvas #121820 and explicit run/catalog counters. Served JavaScript 68be1aa68b5a0b49f12775fe1c18feed64a80aaf345efbc55f6fcbece0f4e772 and CSS 718b5a47b6d052d42afab34778b79c9f4db07d5560460cb65fc2adf8e2d5b288 match the accepted frontend. Retained post-promotion PID 45344, instance c52db568c6c4f05a17f3e1c62c9d0036, generation 2 and 9,550 catalog records were healthy and idle with pending 0. The new library-scoped error filter returned all 22 distinct unresolved error paths; offset 100 returned zero further error rows. Candidate GET count was 553. No POST, scan/review/shutdown control, force reload of the user's tab or broader retest. Historical run checked 9,529/reused 9,528 counts were preserved from the pre-patch job, not rewritten retroactively. Screenshot and JSON: scratch/grouping-qa-2026-10-09/screenshots/published-v0.3.0.png and published-proof.json. Own driver session 59156 exited code 0; lease 8f5954c68ee8 cleanup reported remaining 0. The Files helper's old statement that grouping is later remains the known minor copy limitation scheduled with subsequent merge work; candidate workflow itself is available.