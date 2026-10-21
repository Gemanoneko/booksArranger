# Books Arranger v0.20.1 — QA report, 2026-10-21

Futaba. Both canonical runs and the actual new packaged A/B acceptance passed on the committed patch. No open product blocker remains in the declared release scope.

**Verdict:** GO

Release source commit: 968d4cebba39b49ec8c228f6a03cb7f6b5d0bcc9

Release artifact manifest SHA256: 21c988593b6ecd43719751ec8e0d0055d0e5c52505778e7034b716ef78294f0d

## Pinned source and independent handoff

Books Arranger 0.20.1, dirty N, source repository `C:/Antigravity Projects/Worktrees/Books Arranger/qa-0.20.0`. QA used the reviewed immutable source snapshot, complete harness/runtime inventories and canonical protocol-2 checker. No live shared-tree test, real-library operation, installed-app control, focus-taking launch, audio or iTunes action occurred.

Context: `shared/standard-entry-20261021-v0201-runtime2/context.json`, SHA256 `3a0d3d16f1b9ef4a3fd487ff0c18f7ca8cb122646984b77590c5ad5c6d7a7c25`. Receiver literal: `run-receiver.ps1`, SHA256 `6f655e2cf69988128ab6cdb3e377547a405bf780e544186fe72c71ff2bac5425`. The canonical executable, argv, context, fixture and run parent were identical between the sequential sender and receiver; only exclusive logs and human labels differ. The original 600000 ms deadline and private Windows Job ownership remained active.

Sender original session 19076: start `2026-10-21T11:29:17.1491183Z`, terminal exit 0 at `2026-10-21T11:37:19.2561140Z`. Sender log SHA256 `11e10c9eebf250b16e4e8934b8e5a72cc69affba5d6dfe66b2912d4649b50be0`.

Independent receiver original session 11886: start `2026-10-21T11:38:02.0914881Z`, terminal exit 0 in chunk `fe1ded` at `2026-10-21T11:45:50.3407138Z`. Only that original session was followed. Receiver log SHA256 `72913def97ceda931a12587b611ed208dc2324c592186ed9cde5824ea977e83c`.

Independent parse `bf4740` verified the actual receiver output:

| Check | Actual result |
| --- | --- |
| Python | 1,220 cases: both completed batches 680 + 540; zero failures, errors or skips |
| Node | 57 tests, 57 passed, zero failures, cancellations or skips |
| Frontend and syntax | All 16 declared frontend scripts and eight syntax files complete |
| Completion | Actual `BOOKS_INTEGRATED_CHECKS_PASS` with the same totals |
| Owned closure | `ok=true`, `closed=true`, complete output, native active/assigned/listed 0, all 2,732 retained processes signaled |
| Limits and failure flags | 442477.0463 ms owned elapsed; no force, timeout, overflow, truncation or closure error |

Sixty-seven transient incomplete native samples reconciled to a complete final zero. Sender separately passed the same actual counts and closure with 455833.3661 ms owned elapsed and all 2,732 retained processes signaled. Bare exit codes were not substituted for test completion or ownership evidence.

The sender and receiver actual receipt lines compare exactly, case-sensitively:

```text
Entry-check receipt v2: books-arranger v0.20.1 @ 968d4cebba39b49ec8c228f6a03cb7f6b5d0bcc9 (dirty: N) [source:e8c1cc76a9b41e57b00e52883f97116d573d91c2af8a5428fc9c3af76080910c; harness:7c676b68ea9f327d1ac39f7ae94f0d8a6fe6224f5d59117e9f844e201fd26e49; runtime:817590a0c6274b2bea30548d9480bfb5fac9058286a6f6787713f1f80d41c726; checker:8af6c2583c60cdef7b610f2161010394aa7ad45fafe7584f69e98fc5c131ce6a] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a
```

## Regression coverage and limits

The declared graph includes publication-location and migration-planning tests covering completed historical series-backfill lineage, legitimate legacy proof absence, refusal of altered or unsupported evidence, whole-record pinning after enrollment, held-book accounting, and real private retag → enroll → relocate → recovery re-entry. It also retains the existing Retry All, catalog contention, source configuration, organization, manual metadata, publication/recovery, MP3 repair and frontend checks. These are private/synthetic checks, not certification of the live catalog or NAS files.

The first 0.20.1 sender preflight refused the changed hidden dependency lockfile before checks, ownership runner, run lock or run root. The authorized version bump had changed only its top-level version; a narrow reviewed audit reconstructed the old hash by reversing that one field and verified the other 7,588 dependency files unchanged. That refusal and its context/log remain preserved, not counted as a successful test or invented native-closure proof. The fresh runtime2 pair above used the reviewed updated inventory.

## Actual packaged acceptance: PASS

The independently verified manifest above binds build `4630f60c-9fa4-4bde-ac70-dab9aaec43f3`, product digest `76cd92e96e18f3fb0fbf5ece3b4ca03442adeb2b8e12f9d592cb96d69f60ca28`, source 968d4ce and shell/backend version 0.20.1. Its 265-file payload is marked verified and installer-equivalent. Futaba independently hashed all three actual release artifacts: installer 173605368 bytes / `dcd013faec3086d5cf437c8770e91f4aad8f83c56a2dce3f64f2525a007befb8`; blockmap 181091 bytes / `a0de9fd6b59c77da9ca5a3486b0bf462ff5375a58e68dcf3807d77b7c9de6cd1`; latest.yml 360 bytes / `fae99b33a15e7ca6372331e0aea1a993ab8c115bd062df1cc4bf00614aa379c4`. All match the manifest.

Two sequential, independently reviewed private runs used hidden/muted launches, fresh profiles, the original 600000 ms ownership deadline and full payload/input verification before and after. A fully closed before B. No renderer `window.close()` substitution or real user-instance control occurred.

### A: UI, metadata, screenshots and actual desktop Quit

Literal `shared/packaged-v0201-adapter/run-ui-quit-payload.ps1`, SHA256 `c34dc3fa81a821be98cf128253de519f8060f8be96c48324e8acd7b7d7df0b10`; owner `d27fdf08b3c55469a74c7e90a241426f81ad6fa96710c49038090ba78b061539`; driver `aeb475f5e2a90d1420f7f517ddbb04c5606b0d3e64f426806d3dc460545a04f0`; unchanged controller `18f03e45d512d150528ad8006d218062932cc74a40b2791eb74242c9c6c4317f`. Evidence: `shared/packaged-v0201-A-ui-quit/`.

Original session 22816 started `2026-10-21T11:51:12.5694648Z`, terminal exit 0 in chunk `0a6ab2` at `2026-10-21T11:51:28.9371460Z`. Actual UI/backend version 0.20.1; discovery completed with two private candidates; all seven hierarchy/short-story/fallback routing variants, tooltips and actual Manual review Save passed. Saved title, universe/cycle and separate folder/Artist authors remained in the review; approval stayed false. The saved-source message and enabled Check metadata action appeared. Both private originals remained unchanged.

The 1280/720 screenshots were visually inspected at original resolution. The form wraps/stacks within the page, the saved-source message and reviewed paths are readable, and no blocking visual defect was observed. Geometry readback found 51 visible interactive controls and zero intersections exceeding one pixel in both dimensions at each width. Document widths were 1265/705 against viewport widths 1280/720. The source table retains its local horizontal scroller at 720; there is no page-wide overflow. Screenshot SHA256: 1280 `16a976dc6aae191f009f356f8cc5c318a978c12f3f0a301fe164e7929ad8ef77`; 720 `47d892b79bde6a347da4a82e66657f981200ea3fb3ddcfbe8ecf9531033cca12`.

Actual desktop Quit was requested at `11:51:27.396Z`; the packaged process exited naturally with code 0 at `11:51:27.764Z`, and both ports were refused. Focus events: 0. Owner elapsed 14050.2338 ms, `ok=true`, `closed=true`, complete output; no force, timeout, overflow or truncation. Native active/assigned/listed 0, all 15 retained processes signaled, complete final zero. Full post-payload/input verification passed. Packaged-result SHA256 `543491a8def57c94343f2ce6a43eb4fef79e015b4d689318d7fc7379cdead221`; owner-result `af8000d6f4b406a159f3204c496ad3eb9f89df6ffd8586c9dfd4f8e4d68f5c15`.

### B: native Close preserves the original page/backend

Literal `shared/packaged-v0201-adapter/run-native-close-payload.ps1`, SHA256 `f19b28a76bc5e053cff93e0c9490ff99797fd7f15df6e5e57383e7cd8b929a9e`; owner `0ae2ee738089c182b884405eaf59df50744cc10a505589be4c6aeaaf1ecab0c4`; driver `c4c98316dd94c8dd085481b3f4bf66a0b6a46812338021428a6da30cff57a898`; unchanged native controller `190abc9d24273a4822166ecbd2a8d4e862e82b16c4eecd12197d15cc74304fd2`. Evidence: `shared/packaged-v0201-B-native-close/`.

One execution started `2026-10-21T11:51:47.4020502Z`, terminal exit 0 in chunk `6a6437` at `2026-10-21T11:51:54.4961412Z`. Native Close was requested at `11:51:50.439Z` through the fixed same-payload/profile/environment owned `--close-window` secondary invocation. The secondary exited naturally with code 0 at `11:51:52.322Z`. Both fresh HTTP target metadata and independent browser `Target.getTargets` retained exact original page `432400A96AD6EB60E3AC5FD0629FB80D`; fresh authenticated backend state was version 0.20.1, same instance `0f13c88b2906dcd79cec2cf0959d15a9`, PID 50408, port 5214, `closing=false`. No post-hide renderer Runtime or focus probe was used.

Explicit instance-bound backend shutdown at `11:51:52.867Z` was private cleanup, not a second desktop-Quit claim. The primary exited naturally with code 0 at `11:51:53.308Z`; both ports were refused. Owner elapsed 4761.1431 ms, complete output, `ok=true`, `closed=true`; no force, timeout, overflow or truncation. Native active/assigned/listed 0, all 12 retained processes signaled, complete final zero. Full post-payload/input verification passed. Packaged-result SHA256 `e729e2fd943d9497614cee680f43cfad1a63e77077f80390975e638dd41c4b8b`; owner-result `f35eb613caf2bbf12100b18fded6ff490068aaae835f423873d5573eaf849218`.

Limits: this pass does not certify native input/tray interaction, post-hide renderer/focus events, live provider conflicts, full conversion in the packaged smoke, installation/updater execution, source activation or live migration. It certifies the declared source checks and actual installer-equivalent package, not Sergei's live installation or NAS migration.

## Findings and pattern alerts

No product failure found in the completed declared source checks or packaged A/B acceptance. No open QA blocker remains in the declared release scope.

Pattern alerts: none.

## Preservation

All session evidence and shared heavy fixtures remain under `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20` for the user's manual cleanup. This report is outside the clean QA checkout until final release acceptance. No source, settings, catalog or media files were edited by Futaba.
