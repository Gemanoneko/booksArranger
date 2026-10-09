# Books Arranger — browser prototype QA — 2026-10-09

**Verdict:** GO

Scope: browser interface extending the previously tested read-only engine; source-only v0.2.0 prototype publication and user try-it. **37/37 meaningful checks passed:** supplied Python 17/17, independent HTTP 8/8, actual-script VM regression 1/1, rendered browser workflow 11/11. All **505/505 fixture source files** remained byte-identical. This is not Apple compatibility, conversion/arranging, or packaged-release clearance.

## Exact candidate

Tests ran against the frozen copy in gitignored `scratch/web-qa-2026-10-09/candidate`, not live implementation files. Initial backend snapshot was frozen by Ender; his subsequent explicit frontend-only revision preserved unsaved review fingerprints. Revised hashes were independently matched before browser testing. Final read-back matched all 13 runtime/document/test files below to the live publication candidate. Runtime core is unchanged from v0.1.0 commit `54054e9ed68bc1f8535ea12ad750e3e677a6b730`.

Version while tested: VERSION contained **0.1.0**, SHA-256 `3d097c315a1c543040f548da4c7051265e94c77211a2411ced1d4621344270de`. Sully owns the intended **0.2.0** marker-only bump; the web health/version display reads VERSION on each request. No runtime-source changes are authorized by this GO.

| File | SHA-256 |
| --- | --- |
| app.py | 0dcf5a40d0655274d7b2462fa9ab5a79b5cafbbfa4f7d3e03cefeeb49e664522 |
| scanner.py | 0c6a70b380c7c8e69d06a344bec53daa99383475b149782f085acc9968721916 |
| metadata.py | 9ae8504127c65fd45ffbc3ac0b4843cb4417ce19e10c311ddf1429d4011a0a02 |
| web_server.py | 69d7ece4d7ad996d28b00397dbacc4341e4f77df61a20ef252d00bc9c1990cb0 |
| launch-web.cmd | 7175ae1b825a4e287b5f13a958fcb7f2c1d7e364323c898a302edc1580c77ef0 |
| web/index.html | 151e3df9ef981ef22a90878c1b261943b998231743d589b14930ed6d7a57b9c2 |
| web/app.js | 3b44264a6eaa4f828eea52c0b9831b0cb1621e6e7e3595a0d0c68d3b3aca192a |
| web/style.css | ccdf471983b3659d9c9dfb7ecae5533851d39c1530f3c794be9cc7efe0cea9fb |
| tests/test_inventory.py | 894fb84106c829733da270d4b3110610d646766737114e2b979def5661d58501 |
| tests/test_web.py | ab054416896de25d06b620acbf970285ab647f4a83368552b22f57ae6a37206e |
| tests/test_browser.js | 19b8f19e9d21860a053ce0fc2302de0f170b51f71c951ab2f953aa1394c9b3c4 |
| README.md | 088554d10469e0ef3f9487b916b758cdeaa49070c84483762bd4af81efc73e26 |
| Docs/BooksArranger_Brief.md | 1d174037449788b4573203ef6c7ddc00846566e3f690e20bb08a9973a7818cd6 |

## Checks and evidence

### Python supplied suite — 17/17

`python -m unittest discover -s tests -v` from the pinned candidate. Covers engine persistence, crash recovery, Stop/Resume, incremental changes/missing records, source-change review invalidation, errors, podcast isolation, ebook destination collisions, metadata language, catalog ownership, strict loopback/port, token/origin protection, route allowlist, bounded malformed requests, precise review fingerprints and shutdown.

The initial sandbox run could not connect to localhost (WinError 10013), producing six environment errors. The identical fixture-only suite then passed 17/17 with scoped loopback escalation. Environment failure is recorded and not counted as an app failure or a passing test.

### Independent HTTP checks — 8/8

`python scratch/web-qa-2026-10-09/independent_http.py`, disposable fixture roots and ephemeral loopback ports. These tests were not copied from Ender's assertions.

1. Concurrent scan-start requests produce exactly one owner: responses 200 and 400, no overlapping worker launch.
2. Audiobook scan excludes podcast subtree; podcast episode destinations are preserved, companion transcripts remain present, podcast/companion rows reject canonical-book review writes; full before/after hashes match.
3. Invalid JSON/UTF-8/primitive bodies and negative, decimal, overly long offsets/search are rejected; subsequent valid state request still works.
4. Raw/encoded traversal, Windows drive routes, and unconfigured library paths do not expose source files or arbitrary files.
5. Forged local hosts, null/foreign/wrong-port origins, same-site fetch headers, and bad tokens are blocked; same-origin positive control succeeds.
6. 206 fixture ebooks paginate without overlap; literal percent/underscore search finds the intended filename; timestamps round-trip as exact strings rather than rounded JS numbers.
7. Nonfiction topic preview uses Nonfiction/Philosophy/Author; Unknown original language yields no proposed destination; boolean source-size fingerprint is rejected.
8. Health identifies exact app/instance/port; cross-origin shutdown is rejected while server remains alive; authorized shutdown succeeds.

### Unsaved-review fingerprint regression — 1/1

`node tests/test_browser.js` executes the actual revised frontend in a VM: edit canonical fields, refresh catalog to a changed source size/timestamp, then Save. Posted fingerprint remains the originally inspected one and stale-save rejection is surfaced. Ender identified and corrected this browser-specific issue before rendered testing; initial JS pin was `d5364c7f32b649db9fb607a786a573cddb6c2463186692a95982f66655034f66`. QA verified revised pin `3b44264a...`; this was not a QA code fix.

### Actual rendered browser — 11/11

Built-in browser route was attempted exactly as directed: `cua.createBrowserTab('iab', verifiedURL, {visible:false})`; result **Browser is not available: iab**. Fallback used only the existing studio `scripts/qa/headless-browser.mjs` guarded launcher, a fresh disposable profile, muted headless browser, and existing bundled Playwright connected to that leased browser. No user's tabs, browser profiles/accounts, desktop input, native app focus, installs, or system settings were touched. Task-specific scratch driver has a 600000ms total deadline; browser lease TTL is 600 seconds.

Successful final driver: `node scratch/web-qa-2026-10-09/browser_check.mjs` with scoped fixture-only execution.

1. Reopening the browser after a graceful service restart restores stopped state/catalog without an automatic scan.
2. Stopped checkpoint visibly retains **6 checked / 394 pending / zero errors** and enabled Resume.
3. Actual Resume increases checked count **6 → 10**, then Stop settles at **10 checked / 390 pending / zero errors**. Advancement is asserted numerically, not inferred from a transient Scanning label.
4. Ebook traversal and later rescan display **105 records**, with **105 reused** after completion; first page shows 100 rows.
5. Embedded `<script>window.qaXss=true</script>` metadata is rendered literally; no inserted script node or executed sentinel appears.
6. Next shows rows 101–105; Previous returns rows 1–100.
7. Path search for Book 000 returns one row; selecting it reveals source evidence and canonical review fields.
8. Changing language/title/author/genre and Save displays local success and the approved Horror/King Stephen/The Stand destination.
9. Actual 700px viewport renders the review form and saved path without page-wide horizontal overflow; the inventory table intentionally scrolls within its own container.
10. No frontend page errors or external network requests occur in this workflow.
11. Stop server disables scan controls and displays the saved-progress/browser-close message; service execution then exits naturally.

First rendered attempt completed seven preliminary observations then timed out on an overly exact test locator for the nested language select. The task-only driver was corrected to inspected form-name selectors. Its first Resume assertion was also strengthened to require a numeric increase; the early same-count observation is **not** cited as proof of advancement. No application changes were made for either harness correction. The first attempt is excluded from the 11/11 final count.

## Visual evidence

Screenshots are in gitignored `scratch/web-qa-2026-10-09/screenshots/`: `empty.png`, `stopped.png`, `inventory.png`, `review.png`, `saved-preview.png`, `review-narrow.png`, `server-stopped.png`. These are actual rendered pixels at 1440px and 700px viewports, not reconstructed mockups.

Futaba viewed wide and narrow review captures. Jane independently viewed inventory/stopped/saved-preview/narrow-review and accepted readability and absence of apparent overlaps in those captures. Narrow-table internal scrolling was expected and accepted. No guarantee is inferred for every display, zoom, theme or row length.

## Integrity and owned runtime cleanup

- Sources were **400 valid short WAV fixtures + 105 EPUB fixtures**, under named gitignored scratch roots. Full SHA-256 manifest before/after: **505/505 unchanged**. No actual Z:/Y: library was scanned, written, moved, renamed, converted, or cleaned during this web pass.
- Initial sandbox fixture service PID 48312/session 33199 could not be reached from an external loopback client; it was ended with Ctrl+C and verified absent. That environment cleanup provides no graceful-shutdown acceptance evidence.
- Reachable owned fixture service PID **52468**, instance `7d1dddf5bd61875a2b69026139aecae4`, session **7926**: health identity verified; protected `/api/shutdown` returned 200; process execution exited **code 0** before the persistent-catalog restart.
- Restarted fixture service PID **48956**, session **3442**: final browser Stop server ended execution **code 0**. Its owned instance file was removed.
- Browser lease **811595c4ec76** (PID 62056) and final lease **f169fefaae4e** (PID 78372) both ended through the guarded launcher's normal cleanup; each reported **remaining: 0**.
- After cleanup, an exclusive IPv4 bind to **127.0.0.1:5210** succeeded then immediately closed: fixture port is released for a separately owned user-service launch. QA retains no app/browser process.

## Findings, pattern alert and limits

No unresolved Blocker or Major core-flow defect was found in the accepted candidate. Existing large illustrated FB2 8MB metadata cap and size/mtime-only reuse limitations remain as documented in the previous prototype report.

**Pattern alert PA-BOOKS-01:** new controls have no tooltip implementation in both the Tk milestone and browser milestone. **Disposition: log-and-defer to Daily Use polish**, explicitly confirmed by Jane under Prototype-phase deferrals; no added UI/code stage during this prototype. Main control labels and footer instructions were readable in tested captures. This is separate from individual core-flow bugs.

User-facing library mutation, authoritative identity lookup, track-to-book grouping, audio conversion, cleanup, and Apple device testing remain later milestones. This report does not claim them complete. Native browser/account/desktop checks are neither needed nor authorized for this web workflow.

## Published version correspondence — v0.2.0

After Sully published source commit `a3bc50b` and tag v0.2.0, a single bounded read-only rendered visit verified the retained user service on `http://127.0.0.1:5210/`: visible badge **v0.2.0 · local prototype**, source **Z:\Audiobooks**, health **version 0.2.0 / PID 3100 / instance 1171e36d693625c4667d9a276e28826c**. Audiobooks, Podcasts and Ebooks all returned **not scanned / count 0 / active_library null**, with the confirmed default roots.

Actual screenshot: `scratch/web-qa-2026-10-09/screenshots/published-v0.2.0.png`. Jane independently viewed it and accepted visible version, idle source and readable controls. The visit issued GET requests only; no scan, review, shutdown or other control was clicked. Only the temporary guarded browser lease `bcc8d07c7934` was closed, with **remaining 0**. The retained user service was left alive and idle. This correspondence check adds no runtime source change or broad retesting.
