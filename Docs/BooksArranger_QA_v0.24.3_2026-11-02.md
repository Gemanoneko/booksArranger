# Books Arranger 0.24.3 — QA

Futaba · 2026-11-02 · Original full entry timed out; explicitly approved replacement and packaged native passed. No QA reruns.

**Verdict:** GO

The changed startup and clipboard behaviors have focused positive evidence. The original full entry timed out. Sergei explicitly approved one replacement check on the unchanged sealed candidate; that replacement passed with its actual receipt and final postflight. The packaged native check also passed with its twelve original records, normal owned closure and exact own-leaf cleanup. QA accepts this named source/build within the practical limits below.

Release source commit: 641aa11e3f751633305f2c54225cee8d832d6da9
Release artifact manifest SHA256: 024ee973e47a5c5d1912f9fe6cf92ef117528448dab34ca3639403273b852ddd
Native QA evidence SHA256: 5b66645d4250806a23e0752986572d78cc57a454e68c27ea39af366eb82807a0

Candidate build: `5e9c20da-f00b-4a7f-af0b-f87d9c21f399`, version 0.24.3. The approved replacement final entry and packaged native acceptance passed.

## Explicitly approved replacement entry — PASS

Sergei approved “Allow one replacement check” (question call00e62106145f49558aee37d2b7b181ea). The unchanged source/build/context ran 10:41:46.378–10:50:58.052Z (551.7 seconds), actual callback error null/empty outer stderr. All 2,331 unique Python methods completed with zero failures/errors/skips; 241 Node cases, 39 frontend scripts and 11 syntax files passed. Normal owned closure: 10,873 retained, final active/assigned/listed/unsignaled zero, complete true, no force/timeout, output complete; 613 cumulative transient incomplete queries. Final entry postflight passed and the receipt reports personal folders clean. The first timeout remains a failure below, not relabelled.

QA independently consumed the original callback/summary and matched the actual stdout hash and receipt. [Portable replacement summary](Evidence/v0.24.3_2026-11-02/replacement-entry/summary.json) SHA256 `ed9df17c8784f254c3006d1e9b5a04c9ff49702fb31e6c0ff068e3f376610447`; nine original files are preserved byte-exact. No further full run was performed.

Actual receipt (not a separate QA rerun):

```text
Entry-check receipt v2: books-arranger v0.24.3 @ 641aa11e3f751633305f2c54225cee8d832d6da9 (dirty: N) [source:4f62a1a6c1c45ab6afe6f19bbe91f7da122a9aa0523fb1203021654bf4129ea7; harness:7852c9e3cb673b48f3aff491ea71bd245d9eb58bcecb67d5ba999557f8dda877; runtime:5d3562ed3a04005275ea9af81576a624a3b926445cc80236e9fedc95590a29e1; checker:6378352ea131eee3338019d36bafc100c54837e29aac271ea8de1687c639a07f] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a; personal-folders clean
```

## Original full entry — FAIL_TIMEOUT

Actual invocation ran 10:19:42.278–10:29:42.317Z. All 13 Python workers reached their 540-second deadline: 2,331 methods were discovered, 1,734 observed started in the measured worker-progress comparison, and zero workers produced completion reports. No Python pass count can be certified. The Node/frontend side chain completed, but the overall entry failed. The outer callback reports SIGTERM/killed at 600 seconds; no final entry receipt or final postflight exists.

The check's owned closure was forced/timedOut at 576.65 seconds, with final complete zero proven: 9,780 retained, active/assigned/listed/unsignaled zero, closureError null. Its 547 cumulative incomplete sampling diagnostics do not invalidate that final zero observation. They do not supply the absent entry postflight either. Own scratch/11 had an EPERM cleanup failure and remains assigned for cleanup, not silently certified clean.

[Original byte-exact portable evidence](Evidence/v0.24.3_2026-11-02/full-entry-timeout/files.json) preserves the actual summary, owned result, stdout/stderr and outer callback/output. Summary SHA256: `3055b680e660071c6a54e2a9995777a2ad86cabab05112ae898a95a79f8f6529`.

[Targeted diagnosis](Evidence/v0.24.3_2026-11-02/full-timeout-diagnosis.json) records the three original FAIL-marked methods rerun serially on unchanged source in fresh private copies: set-release ruling 56, approve-as-is missing author, and chapter-preserving M4B join. All three passed individually in 29.94, 20.21 and 31.20 seconds, with normal complete-zero closure. QA independently verified all eleven referenced raw record sizes/hashes. These supplemental passes do not erase the original failures or certify the unfinished 2,331-method run.

[Measured comparison](Evidence/v0.24.3_2026-11-02/full-timing-comparison.json) shows the same 13-worker/540-second scheduling, pinned runtime, and unchanged runner/three failing test modules after EOL normalization. The prior 0.24.2 workers finished in 395.3–463.9 seconds. Current workers stopped in different methods; only worker 8 contains the three new startup methods. This supports broad slower throughput as an observation, not a diagnosed CPU/disk/AV cause. The cause remains unknown; no product code fix is justified by these records alone.

## Packaged native — PASS

The single approved hidden packaged PA-1 completed with actual callback error null/empty stderr at 10:52:25.463Z. All eight required assertions passed: update offered, download SHA512 verified, invalid installer refused by Windows, shell stayed alive with installer-blocked cause, fake download seen, old engine health/version recovered, and normal Quit ended the shell. Payload and owned endpoints remained valid; 203 finite observations reported no visible own window or intrusion. This is a hidden packaged update/recovery check, not a physical clipboard/Retry GUI repeat or a live-catalog launch.

QA independently read [NativeQA](BooksArranger_NativeQA_v0.24.3.json), matched all twelve raw file hashes/sizes and exact source/build/product/manifest binding, then consumed callback, functional, inner/controller ownership, postflight and cleanup. Inner execution: 23.067 seconds, 21 retained; controller: 37.183 seconds, 25 retained. Both exited zero normally, complete final zero, zero incomplete queries, no force/timeout/truncation, output complete. Postflight unchanged. Exact new own leaf was deleted via the same handle, closed and absent; preexisting leaves unchanged, UIOrderList not written, one approved 8-byte history reference retained. Together with the source probe this used exactly the two approved references. The proper current phase-contract validator passed; no old compatibility exception was used.

## Changed behavior

- **Cold startup — focused PASS.** [Core evidence](Evidence/v0.24.3_2026-11-02/startup-clipboard-results.json), SHA256 `9c1e3605ffb4f6b1a615c41cdf41227fbca387a9fe69cf4eb8b1eec1bec9cb40`, records three actual authenticated HTTP/serve_owned cases in 25.473 seconds: a synthetic 669-row catalog stays loading with one pending SharedSnapshot page worker and publishes Ready after completion; a real underlying page error remains fatal; Quit interrupts the pending loader. Owned closure was normal, complete and zero. QA independently matched all eleven recorded source/test byte pins to the current candidate. The 50ms fixture reader wait and event-gated original page read exercise the production pending path; this is not a timing measurement of Sergei's NAS/catalog.
- **Copy details — actual source Electron GUI PASS.** Pinned source `822bd67b8e58a5a1ebd300c9c22c75eeb7ab0d9d`, exact Electron 44.4.5, private profile/catalog. A deliberately invalid private SQLite header produced the genuine Stopped pane with `sqlite3.DatabaseError: file is not a database`. Clicking the real Copy details button put the correct 674-character diagnostic on the OS clipboard; SHA256 `686ba523f226e21e728d50b64fa98381ed40ea14ecbac0c18c4c8621524c8c8a`. A harmless QA sentinel replaced the clipboard before any readback; the original clipboard was never read. This exercised the actual main/preload clipboard bridge.
- **Selection and Ctrl+C — actual source Electron GUI PASS.** Selected technical text `Last engine output:` survived 14.835 seconds of periodic updates. Real Ctrl+C produced exactly `Last engine output:\r\n` (21 characters including Windows newline) on the OS clipboard. Selection remained unchanged after copying.
- **Try again — USER-observed positive.** After the failed private engine/host exited, Ender quarantined the entire own fault data directory and restored the sealed valid three-book fixture at the same path. Sergei voluntarily clicked Try again after the approved QA focus period. His screenshot showed the private source 0.24.3 app Ready, Loaded 0s, Files catalogued 3, with the QA Audiobooks root. This was Sergei's click and screenshot, not an automated Futaba click or an installed-app regression result.

[Portable source GUI proof](Evidence/v0.24.3_2026-11-02/source-gui-results.json), SHA256 `6a134dd0f910ae4b3f2dc454927783fa619fafb0741e01946632a4ba9ae3c24f`, references eight filtered own records. Foreign registry baselines are excluded.

## Probe boundaries and closure

Actual GUI focus began 09:39:48.885Z; the 120-second approval ended 09:41:48.885Z. Last QA input was Ctrl+C at 09:41:15.992Z. A guarded later Retry attempt refused before observation/click; no QA UI input occurred after the deadline. No install, playback, conversion, user-app control, live catalog, or Z: access occurred.

Sully's single supported hidden CLI Quit completed normally. Primary source ownership: 14 retained, 26,454 queries, zero incomplete, final complete zero, no force/timeout; secondary Quit: 3 retained, 15 queries, normal complete zero. Exact own source tray leaf was subsequently deleted with absence verified; foreign leaves/root schema/order were unchanged and UIOrderList was not written. One approved 8-byte history reference remains. Filtered cleanup SHA256 `204f8b3bb5e0550becbc17a1d4dfc788af6858883235c3e92ee5f7667c5513b9`; source owned SHA256 `7373cc6a2c07a27d22eea536c382e8f3d3d7f66c145b4be64138ad7b46a9f79b`; Quit owned SHA256 `9123693dc496b240f4ff19cda489db09cf59b651227e8ca29e325162e0791f5b`.

## Coverage gap and remaining acceptance

0.24.2's earlier component/API and empty-catalog native passes remain historical passes within their stated scope. They missed the joint cold existing-catalog/desktop-ready path and actual OS clipboard behavior. This regression pass addresses those specific gaps rather than repeating unrelated dogfooding.

All required current acceptance records are now present: focused changed-behavior evidence, explicitly approved replacement full receipt, packaged native proof and normal closure/own-leaf cleanup. The version-specific acceptance index points to this QA report and the independent code review. Publication and temporary-directory cleanup remain Sully/Ender operations; no additional QA run is requested.

The earlier recommendation against an automatic full retry was followed: Sergei explicitly authorized exactly one replacement. Its actual PASS is recorded above; no further repeat or gate waiver is inferred. Resource observations after the first run showed no present pressure and cannot establish its historical cause.

Practical limits: the 669-row integration fixture is synthetic and uses private local roots; GUI recovery used a three-file private source fixture. No final installer was installed on Sergei's profile, and no live/NAS startup was performed. Source GUI clipboard evidence does not itself prove the packaged GUI. The final hidden check passed its separate scope as stated above.
