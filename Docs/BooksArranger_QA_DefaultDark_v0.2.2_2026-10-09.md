# Books Arranger QA: default dark v0.2.2

Date: 2026-10-09. **Verdict: GO** for the scoped CSS prototype milestone. No Blocker or Major finding. Formal prototype handoff gate and broad engine reruns are deferred under the prototype rules.

Tested a pinned copy of Ender's frozen `scratch/dark-2026-10-09/candidate`, against Judy's committed specification `15ae429`. Snapshot VERSION is 0.2.1; Sully owns the forthcoming 0.2.2 marker. All 18 files matched `candidate-manifest.json` again after testing. The sole runtime delta is the stylesheet. Accepted pins:

| File | SHA256 |
|---|---|
| web/style.css | 0d3cf9c99a8dc511d104ace17fb6e2edcd59951254ec11ebd12e99f31505e18f |
| web/index.html | 3881fcba98282e08d787a6a030fac77571ffae7b2359721cb8c4e0ff6d0931de |
| web/app.js | ae27649da135fe58fd522fff984739194ab5935a9e507f59d5bae8fca653fd8c |
| web_server.py | 69d7ece4d7ad996d28b00397dbacc4341e4f77df61a20ef252d00bc9c1990cb0 |
| scanner.py | 0c6a70b380c7c8e69d06a344bec53daa99383475b149782f085acc9968721916 |
| metadata.py | 9ae8504127c65fd45ffbc3ac0b4843cb4417ce19e10c311ddf1429d4011a0a02 |

## Targeted browser evidence

Eight of eight independent check groups passed using the studio's guarded, isolated headless browser. The fixture ran on port 5211 with a scratch catalogue. Browser presentation states were controlled through page-local interception: these checks establish dark rendering of scan/stop/resume states, not a fresh engine lifecycle test. Backend, HTML and JavaScript remain byte-identical to accepted v0.2.1.

1. All 21 computed palette tokens and native `color-scheme: dark` match the specification.
2. Startup, empty inventory, normal and disabled controls remain readable; disabled opacity is 1.
3. Primary hover and pressed colors match the spec; scanning, stopping and resumable controls retain their presentation semantics.
4. Hovered rows and selected rows use their specified colors; selection overrides hover and retains its inset accent; keyboard outline is 3 px.
5. Expanded tag snapshot, review inputs and language select use the dark palette; summary/input keyboard focus remains visible.
6. Seventeen actual control/content rectangles match the light baseline at each of 1,440 and 700 px: 34 rectangle comparisons, all x/y/width/height differences at most 0.1 px. Checked controls retain at least 24 px hit height; no page-wide overflow. The table's own horizontal scrolling remains expected.
7. Action validation and interrupted-connection warnings remain legible alongside Read errors 1 and retained unsaved canonical text.
8. Twenty-three independently computed/composited contrast samples pass: text at least 6.07:1 against the 4.5:1 threshold; sampled border/focus indicators at least 4.05:1 against 3:1. These are scoped sampled states, not a guarantee about every possible pixel or OS popup.

The first geometry comparison reported a 15 px right-edge difference. Both pages had the same expanded details, four rows and 1,690 px content height; native scrollbar gutter left client widths of 1,440 versus 1,425 px. Matched-client comparisons temporarily hid vertical overflow in both test pages only, and then passed. Raw unmodified wide/narrow screenshots were captured before that normalization. No app source change was made for this discrepancy.

Evidence is preserved in `scratch/dark-qa-2026-10-09/`: `computed-results.json`, `geometry-debug-1440.json`, `geometry-debug-700.json`, the driver and frozen candidate. Actual screenshots under `screenshots/` include `startup-wide.png`, `scanning-wide.png`, `stopping-wide.png`, `resumable-wide.png`, `selected-1440.png`, `selected-700.png`, `select-open-wide.png`, and `warning-narrow.png`. The native select's color scheme and computed style were checked; no broad claim about an OS dropdown outside the captured browser surface.

## Safety and cleanup

Owned fixture PID 57872, instance d0e84f0bc9638aa8759aff3835141163, session 26700, received protected shutdown and exited code 0. Exclusive bind confirmed port 5211 released. Browser driver session 70971 exited code 0; lease bb1562caf6a6 cleanup reported remaining 0. Earlier diagnostic leases also reported remaining 0. All four disposable source files retained their original SHA256 hashes; removed only these exact verified scratch files afterward. Candidate, screenshots, catalog and evidence retained. No real library source reads/writes or user port 5210 actions were needed; the user's retained service was not stopped, restarted or controlled.

## Findings and pattern disposition

No app bug identified in this pass. The scrollbar discrepancy was a comparison normalization issue, resolved in the task driver. Prototype tooltip absence remains **defer** to Daily Use polish as previously accepted. Native PC input, global layout guarantees, full engine retesting and future live v0.2.2 badge correspondence are outside this CSS pass; the latter can be checked read-only after promotion.
Jane independently viewed selected-1440.png and warning-narrow.png: accepted the captured dark tables, fields, focus, disabled controls, source text and warnings as readable, with no apparent overlap in those states and the scrollbar-gutter qualification above.
