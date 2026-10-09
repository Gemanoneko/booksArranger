# Books Arranger QA: anthology and author review

Date: 2026-10-09. **Verdict: GO** for the pinned prototype role/routing feature. Candidate marker is 0.2.2; the intended next minor publication and any grouping additions remain Sully/Ender's separate handoff. No Blocker or Major found. No production deployment or live user catalogue interaction occurred.

Tested a copied, frozen candidate from `scratch/anthology-2026-10-09/candidate`, rebased on accepted default-dark baseline 4e3079a, against committed role UX 0e9cb61. All sixteen manifest files still matched after testing. The full accepted manifest is preserved in `scratch/anthology-qa-2026-10-09/accepted-manifest.json`, SHA256 ca825b061d3ef5492ad6a425b9316d7391bb185b8669653e8c3d93685b1ddfa8.

| Runtime file | SHA256 |
|---|---|
| app.py | 192ee63bc475219d02940e56dc785c830e84949a4e601689b3469184b9a095f1 |
| metadata.py | 23a9f01764e6506d1450bea18ae379c7263aa1adf375cbf29668817e6ca8cc00 |
| scanner.py | 687327205e48b0aa7826f126ae2e06b8f88681d2c9940b94803bf59ad04db682 |
| web_server.py | 91119904dc8691c6ad86e0fa7e626387016babd822ee7ab90da7b926fc5e7ae6 |
| web/index.html | 6c4a6c1c3a6bf5b74c78c95ead11c670bf31a1f0cbe04a2cf59045db1d014e48 |
| web/app.js | 79043214afd3f6cb72c16c1ec09cc6dcbfdb89c4d782af24f2d3bedd6306f461 |
| web/style.css | 3850d675db4df8101805b9d290788f3cf5cdf14bff13ac1891ff09a7bf9133da |

## Checks and evidence

Independent scratch engine/data checks: **12/12 passed**. Standalone collections use Сборники without an author directory; Unicode collection series stay under Сборники/Пять Вечеров and preserve the confirmed number. Missing author credit and inconsistent translation-language review retain Needs review. Ebooks and podcasts retain their prior routing. Regular multi-author novels retain root series routing. Source Artist/reader evidence supplies no automatic author identity. Explicit Artist and narrator roles preserve all three distinct existing comment entries; repeated previews are stable and pure. Legacy review JSON and new role fields both reload durably from a scratch catalogue.

Actual guarded browser/API checks: **10/10 groups passed**. Saved collection controls load with unused author folder and multi-author controls disabled; turning anthology off/on restores both saved values. Polling preserves unsaved title and the original review fingerprint regression remains passing. Blank Artist credit uses the explicitly saved author-folder fallback with visible explanation; source reader remains labelled unverified. Real Save preview metadata updates only the scratch catalogue, routes a Unicode collection, distinguishes comment field sources, and appends exactly one labelled narrator entry. Legacy eight-field API review payload succeeds. Ebook UI hides audio-only fields and backend independently refuses active audio-role values. Podcast UI and API review remain unavailable. Transport failure and successful recovery clear the connection notice while retaining unsaved anthology form values.

Actual captures: `scratch/anthology-qa-2026-10-09/screenshots/collection-1440.png` and `collection-700.png`. Both checkbox label hit areas measure 24 CSS px high; vertical separation prevents overlap at both widths. No page-wide overflow; the inventory's existing horizontal scroll is expected. Dark canvas is #121820 and focus remains visible. Jane independently viewed both screenshots and accepted the captured layout as readable and consistent with dark styling, with no apparent overlap. No global pixel or native OS-popup guarantee is implied.

Targeted supplied regressions also passed: six anthology Python tests, two Tk controller tests using fake widgets (no native window), and three actual-script Node receipts for unsaved fingerprint, anthology toggling/comment sources/audio boundaries, and connection failure/recovery/stale-request behavior. The Tk controller was exercised without a desktop launch; its native rendered layout/close flow was not retested. Broad unchanged engine suites and formal prototype handoff gate were not rerun.

## Safety, migration and cleanup

Review additions are optional JSON fields. Legacy reviews are accepted without schema migration or invented author/reader identities; this is preview-only, not source-tag rewriting, conversion or book grouping. Any later combined grouping/filter milestone needs its own frozen acceptance.

Fixture service was isolated on port 5211: PID 39148, instance 583a86d72da73d12fdb4795dd4cd2cf9, session 51906. Protected shutdown succeeded, actual process exited code 0, and exclusive bind confirmed the port released. Browser driver exited code 0; guarded lease e2a445eac2b1 cleanup reported remaining 0. Four scratch source files matched original hashes after all catalogue reviews and were then removed by exact verified scratch paths. Frozen source snapshot, catalogue, manifest, measurements and screenshot evidence remain preserved. No real Z:/Y: library sources, production port 5210, PID 3100, user's browser tab or native PC input were touched.

## Findings and pattern disposition

No new defect identified in this pass. Existing general prototype tooltip polish remains **defer** to Daily Use; these new role fields provide adjacent, programmatically associated accessible help and title text. Grouping/counters and the live source-read errors reported elsewhere remain separate Ender work; this GO makes no claim about that investigation or future conversion.