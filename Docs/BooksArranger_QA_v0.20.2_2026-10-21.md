# Books Arranger v0.20.2 — QA report, 2026-10-21

Futaba. Both canonical checks, the independent supplemental 25 native-move cases and actual new packaged A/B acceptance passed. No open product blocker remains in the declared release scope.

**Verdict:** GO

Release source commit: 2309d8f2d71a8570e329c1010afc6dfa6ce633ba

Release artifact manifest SHA256: 522a9de2888b4d37628eaa20ba2e7cd12609b3126dca77f068031aa732157cc4

## Pinned source and independent handoff

Books Arranger 0.20.2, dirty N, repository `C:/Antigravity Projects/Worktrees/Books Arranger/qa-0.20.0`. Checks used the reviewed immutable 724-file snapshot, full pinned harness/runtime inventories, original 600000 ms ownership deadline and canonical protocol-2 checker. No live shared-tree test, real-library operation, installed-app control, focus-taking launch, audio or iTunes action occurred.

Context: `shared/standard-entry-20261021-v0202/context.json`, SHA256 `ad82dcc851a3fad8a91abcb5a301fe246fca32b4907bfa0f9fe73df5f3970fcb`. Receiver literal: `run-receiver.ps1`, SHA256 `55c4e653066bdd6de513b742ef2b497bc88119b0eb345a2cca9e2647c40aed3a`. Sender and receiver used identical canonical executable/argv/context/fixture/run parent sequentially; only exclusive logs and human labels differ.

Sender original session 63946 started `2026-10-21T17:22:21.7135663Z` and exited 0 at `2026-10-21T17:31:09.8592879Z`. Sender log SHA256 `e721166751207ea1abf0a2ddc15e83ab6301f3f18c7601cf46523c9b9138829c`. Futaba independently verified its actual complete native closure before starting the receiver.

Independent receiver original session 65543 started `2026-10-21T17:34:12.4630424Z`, terminal exit 0 in chunk `d185d2` at `2026-10-21T17:42:47.6350170Z`. Only that original session was followed. Receiver log SHA256 `b55ff7a7d764ef89ef735900399d1fb5ba4d8ee71e0eb279749f52471673d75b`.

Independent parse `0c7d75` verified:

| Check | Actual result |
| --- | --- |
| Canonical Python | 1,227 cases: completed batches 680 + 547; zero failures, errors or skips |
| Node | 57 tests, 57 passed; zero failures, cancellations or skips |
| Frontend and syntax | All 16 declared frontend scripts and eight syntax files complete |
| Completion | Actual `BOOKS_INTEGRATED_CHECKS_PASS` with the same totals |
| Owned closure | `ok=true`, `closed=true`, complete output; native active/assigned/listed 0, all 2,731 retained processes signaled |
| Deadline/failure flags | 488681.0102 ms owned elapsed; no force, timeout, overflow, truncation or closure error |

Forty-six transient incomplete native samples reconciled to a complete final zero. Sender separately passed the same actual counts, complete output and native closed zero with all 2,731 retained processes signaled. Bare exits were not substituted for actual test completion or ownership evidence.

Both actual receipts match exactly, case-sensitively:

```text
Entry-check receipt v2: books-arranger v0.20.2 @ 2309d8f2d71a8570e329c1010afc6dfa6ce633ba (dirty: N) [source:6c7d0f8a101d260c7be49fb766abb58c0b524d4f21f938810dae684013f0e935; harness:7c676b68ea9f327d1ac39f7ae94f0d8a6fe6224f5d59117e9f844e201fd26e49; runtime:bb1f57c3e8062a50ccd01e9b6ae192a46050cf04fb6df32c1bf1fdfd5c085ec9; checker:8af6c2583c60cdef7b610f2161010394aa7ad45fafe7584f69e98fc5c131ce6a] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a
```

## Independent supplemental native-move checks: 25 PASS

The unchanged canonical whitelist does not include the 15 new native-rename cases, eight real/private move-worker cases or two startup-fence cases. Those 25 are not claimed inside the 1,227 canonical count. Jane explicitly retained the committed declared graph and required an independent exact supplemental run, rather than changing product/checker code during QA. Developer's earlier 104 focused cases remain separate evidence.

After canonical closure, Futaba ran exactly one independently reviewed `shared/native-move-supplemental-qa-owned-1.mjs`, SHA256 `a0402348c1406bcd1eb6894f90a75232fbb15b23ce4acc8bf6a0fc8d16c1d7d4`, with original 600000 ms budget, fresh private root and immutable source 2309d8f. It verifies the complete 724-file snapshot and reviewed eleven-file freeze, media runtime and private source bytes before/after. Actual tests: `test_native_rename` 15, `test_output_rename` 8, `test_merge_service.NativeMoveStartupFenceTests` 2.

Original session 89005 started `2026-10-21T17:43:27.4813791Z`, terminal exit 0 in chunk `70f5e8` at `2026-10-21T17:43:47.6367098Z`. Actual discovery was 15 + 8 + 2; all 25 completed, zero failures/errors/skips, with `BOOKS_NATIVE_MOVE_SUPPLEMENTAL_RESULT 25 0 0 0 True`. The real local Windows rename preserves the held native file and bytes; collision, cross-device and changed-identity refusals preserve files; durable crash/native gaps re-enter correctly; duplicate cleanup protects the committed Sorted copy; startup fences precede recovery writes. Simulated NAS64 identity is a private local test, not proof of actual NAS capability or server power-loss durability.

Owned elapsed 15687.0685 ms, complete output, `ok=true`, `closed=true`, code 0; no force, timeout, overflow, truncation or closure error. Native active/assigned/listed 0, all 79 retained processes signaled, complete final zero. Receipt: `shared/native-move-supplemental-qa-1/owner-result.json`, SHA256 `4cb693eeaca22a9b290c20d908fcdc3b4cb93dffd6049bf2ca5d04846a23e648`. This is the actual post-run private receipt; it is not claimed pre-reserved or fsynced. Original tool terminal and complete native closure are independently recorded above. It is not a canonical receipt.

## Actual new packaged acceptance: PASS

The unique manifest above binds build `4f050b08-65c2-432a-a39b-c3ca3dab4f60`, product digest `be5b57a02994efff13c96c40580c5b89902607a739ccf1087c144544204dcda8`, source 2309d8f, shell/backend 0.20.2, 267 payload files and 48 runtime entries. Payload is marked verified and installer-equivalent. Senua separately admitted the native CRLF-only representation against Git source; no unreviewed product change or old artifact was substituted.

Futaba independently verified actual manifest bytes and all three release artifacts before launching: installer 173638373 bytes / `1fc1a45869835bc3d52f302ef13273ddb285edc535ddc8aa7ea6871575ff502f`; blockmap 181133 bytes / `9e8889c2d3a5ae579c6cf5898aa3e09ed178bdf0f15a1febde9aedad7f46af80`; latest.yml 360 bytes / `bff281a8919ea027cff86f5e073cb13c60c6d1d2a7b03d33b360702c4d0d5f08`. All match the manifest.

Two sequential private runs used fresh profiles, hidden/muted launches, original 600000 ms ownership deadlines and complete pre/post payload/input verification. A fully closed before B. No renderer `window.close()` substitution, native input or real-instance control occurred.

### A: UI/manual metadata, screenshots and real desktop Quit

Reviewed literal `shared/packaged-v0202-adapter/run-ui-quit-payload.ps1`, SHA256 `34e48261784890d89d614ebaab84f8b5d5609c1fc8c7848a182327c4f10f4340`; owner `0966d58097265370c8682f073eb6dc01c70133d4ff3839cfefe198cde4bb4207`; driver `91599ecf5a5e1665ff10ea946885da3a36704c9a924857caee365234c738d0ff`; unchanged controller `18f03e45d512d150528ad8006d218062932cc74a40b2791eb74242c9c6c4317f`. Evidence: `shared/packaged-v0202-A-ui-quit/`.

Original session 57884 started `2026-10-21T17:49:19.0487535Z`, terminal exit 0 in chunk `ddbd00` at `2026-10-21T17:49:35.9910613Z`. Actual UI/backend version 0.20.2; discovery completed with two private candidates. All seven hierarchy/short-story/fallback routing variants, tooltips and actual Manual review Save passed. Saved title, universe/cycle and separate folder/Artist authors remained in the review, approval stayed false, and the saved-source message and enabled Check metadata appeared. Both originals remained unchanged.

Actual screenshots were visually inspected at original resolution. At 1280/720 the form wraps/stacks within the page, saved-source feedback and reviewed paths remain readable, and no blocking visual defect was observed. Geometry readback found 51 interactive controls and zero pairwise intersections exceeding one pixel in both dimensions at each width. Document widths were 1265/705 against viewport widths 1280/720. The narrow source table has its existing local scroller; there is no page-wide overflow. Screenshot SHA256: 1280 `27a3e592ed3aba8d96a7c4d056b4607670874be6b31ea34c3007e8048eae78de`; 720 `1a617c75b39e956084e348db4685d180fb074332f28e411d8837faca02f3c052`.

Real desktop Quit was requested at `17:49:34.446Z`; process exit was natural code 0 at `17:49:34.794Z`, with both ports refused and focus events 0. Owner elapsed 14583.2447 ms, `ok=true`, `closed=true`, complete output; no force, timeout, overflow or truncation. Native active/assigned/listed 0, all 15 retained processes signaled, complete final zero. Full post-payload/input hashes passed. Packaged-result SHA256 `6852651a2629e318a16ad7ae5bf9e98646e17b95f8323fe4736d6f4b0facfc31`; owner-result `2ab6d2c03fbdafaecc69fea8709989c470341c12ad7717c1799ebfa326cb5536`.

### B: native Close keeps the original page and responsive backend

Reviewed literal `shared/packaged-v0202-adapter/run-native-close-payload.ps1`, SHA256 `61887e6c2e758249a3853d8a760dfaa7fa5e516fa828de05fa91e47a7493dbca`; owner `2308b0b4a8c74cd459cbe0302c7b0d8132b260ef030d810dee85d9d078b2e5f3`; driver `eb1b7aa98ed5ccd7827ba5a8fbc15a896e7be9919cc4313dc65fd7115e1aebcc`; unchanged native controller `190abc9d24273a4822166ecbd2a8d4e862e82b16c4eecd12197d15cc74304fd2`. Evidence: `shared/packaged-v0202-B-native-close/`.

One execution started `2026-10-21T17:49:47.2053333Z`, terminal exit 0 in chunk `d1dbd8` at `2026-10-21T17:49:54.2903556Z`. Native Close at `17:49:50.239Z` used the fixed owned same-payload/profile/environment `--close-window` secondary route. The secondary exited naturally with code 0 at `17:49:52.142Z`. Both fresh HTTP and independent browser target metadata retained exact original page `4DE2D1C545618A5AC5F824C50A7819C0`. Fresh authenticated backend was 0.20.2, same instance `3ae705119b849797db5914cbad71bebd`, PID 16060, port 5214, `closing=false`. No post-hide renderer Runtime or focus probe was used.

Explicit instance-bound backend shutdown at `17:49:52.699Z` was private cleanup, not a second desktop-Quit claim. Primary exit was natural code 0 at `17:49:53.097Z`; both ports were refused. Owner elapsed 4745.0338 ms, complete output, `ok=true`, `closed=true`; no force, timeout, overflow or truncation. Native active/assigned/listed 0, all 12 retained processes signaled, complete final zero. Full post-payload/input hashes passed. Packaged-result SHA256 `d36a21d3217697d8d4cde694c9d69d1d7db6db98f2968b71b8216da741ea16df`; owner-result `65f45c169a4e7dbe35768655ecfd0e03564e709095d708b46200067480e0e63d`.

## Findings, limits and preservation

No product failure found in the completed canonical, independent supplemental or actual packaged A/B checks. No open QA blocker remains in this release scope. Actual NAS capability, live deployment/migration, real-provider conflicts, native tray/input, post-hide renderer/focus observations, full conversion in this packaged smoke, installation/updater and server power-loss durability are not certified here.

Pattern alerts: none.

All session evidence and shared heavy fixtures remain under `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20` for the user's manual cleanup. This report remains outside the clean QA checkout until final acceptance. Futaba edited no product source, settings, catalog or media files.
