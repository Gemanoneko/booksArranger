# Books Arranger 0.30.0 release QA

**Verdict:** GO

Release source commit: 2c7129f84b394e0f086f94222935e812ce3d6412
Release artifact manifest SHA256: 1deac1f34ab8cfca0f3f46baa1a6fde2356ff6c025233ccab0177ec6e3430055

2026-11-20 · Futaba (Codex) · Delta acceptance from the [round 2 report](BooksArranger_QA_v0.30.0_r2_2026-11-20.md). The final candidate incorporates the local update gate from `981be38597639aa945e5edb05d740cf5793610d9` and the audio and Approve fixes from `5741228`.

## Final build identity

- The isolated candidate was clean at the full commit above. Manifest build ID `a4d64d9a-217e-4348-9d27-6280e75fd2fd`, product digest `c2e2a1691fd969cc3e1905da678523b1f7af91944a6e3362f156b481f7fab44d`. Installer SHA-256 `d280da9ad5ed7e8f753a641d50203de45609151bdbea6a0e6ac92aa746c0bd18` matched the manifest. Independently matched the SHA-256 and size of all three upload assets and the installer's SHA-512 in `latest.yml`.
- Verified the packaged ASAR hash, its version and all 13 desktop JavaScript files against the final source. Also matched the packaged backend version and measured byte equality for the changed audio pipeline and the five renderer assets used by the visual probe. Sully's [pack verification receipt](<I:/AI Projects/Worktrees/Books Arranger/sully-030-output/pack-2c7129f/verification.json>) records 415 equivalent payload files. The pack log and native receipt hashes matched that receipt.
- Ender's [entry log](<I:/AI Projects/Worktrees/Books Arranger/q30h/ender-entry.log>) SHA-256 `20b8c70ebd84fa53ed44bba2b35123d92ad582007038ccef2377cc4b24b5b256`, exit 0. Ender's entry test evidence recorded 2,894/2,894 Python cases and 279/279 Node TAP tests, plus separate DOM scripts. QA read the one entry receipt.

```text
Entry-check receipt v2: books-arranger v0.30.0 @ 2c7129f84b394e0f086f94222935e812ce3d6412 (dirty: N) [source:f2d317f79f9814fdecf4eb641e183a9371ac9fdf9ebdba785de22a726efef15d; harness:dff1ab53146b87d56bf59a460f143f6631a93d85ffac88be2a2088d1a00505a8; runtime:83fcec557613a8c6cf180a95dbcc6613ee7da0b637737abf1444d71c6ee6bca9; checker:4bae2cde4e4cdd2f22fb3060571730ec32fec1dd5403ea070086973b18b695e4] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a; personal-folders clean
```

## Final candidate regression checks

| Behavior | Result and method |
| --- | --- |
| Playable damaged ALAC | **1/1.** A 20-second stereo ALAC fixture failed strict input decode and refused conversion on `882a1d3`. On the final source with the packaged Python 3.14.8 and FFmpeg, the staged output kept 44.1 kHz stereo 24-bit ALAC. Strict output decode exited 0 and yielded 877,904 frames, byte-for-byte equal to the ordinary input decode. PCM SHA-256 `a474b3e19c05d3f6e7e1e90529f744114ff1da6db4523379092e4c71a79e95c9`. The input SHA-256 stayed `b29d218dab2793f02729d3e084b2b27c72f3c348c67e7e5a2ac481209c88743b`. The validation note recorded 0.093 seconds skipped at 4.087 seconds, with zero digital silence. Ender separately recorded 7/7 in the changed damage module. |
| Approve's final file count | **3/3.** The packaged renderer from the exact manifest displayed **6 of 6 files** beside **The Orchard Ledger** at **Step 4 of 4 - Checking each file again**. The progress bar remained determinate and its accessibility text included the count. The preceding frame displayed **5 of 6 files**. The conversion control stayed indeterminate and said **Finalizing conversion**. Actual packaged JavaScript ran with DOM fixtures. On `882a1d3`, a real six-file Approve already returned the final count over HTTP, and that renderer hid it. |
| Project-local update failure and recovery | **1/1.** Ran the exact required case independently from the pinned snapshot with private loopback services and a fake Electron host, engine and installer. The real shell JavaScript kept the app open after installer start failed, restarted the previous engine and showed recovery on the Install line. Matched the 13 shipped shell JavaScript files to this source. Sully reruns the same gate against the accepted package during publication. |

## Prior independent product evidence

The unaffected delta results below come from the exact earlier candidate `882a1d3a7ce1d49b35ff2a69adac585fc349035f`, compared with `03041ee73c8c34e222885abe2db884fc23a34c9b`. The [baseline evidence](<I:/AI Projects/Worktrees/Books Arranger/qa-030-codex/baseline-evidence.md>) records its distinct installer and receipt. Final entry passed on the new source. QA limited the fresh product checks to the two fixes above.

| Behavior | Result and method |
| --- | --- |
| Saved Pause, held cleanup and restored queue | **6/6.** Private relaunch cases held file work and finished-book checks until admitted Resume. Restored catalog-only actions could run under Pause. The no-press controls kept the originals and held records in place. Older download-marker holds also waited. |
| Darwin's Blade and queue copy | **5/5.** Real automatic conversion produced one book with both album-numbered parts and four chapters in order. The same-album control converted. A part gap held, different artists and incompatible profiles split, and Metro 2033 stayed separate from 2034. The immediately runnable action reported a null blocker. The queue strip omitted the cause for that action and named the conversion queue when it actually blocked work. |
| AAC damage and damage UI | **6/6** media checks, plus the renderer case. Copy and in-place paths accepted a short glitch, a Join retained ordered chapters with strictly decodable output, and worse damage stopped. The manual UI hid Retry and Reopen for unrepairable parts and kept Reopen for a different failure. The renderer offered repair for a cut-final-frame M4B and displayed the minor note for the accepted case. The final audio retest above specifically covered the later ALAC change. |
| Research, freshness and refused series moves | **4/4.** The first and final research frames named the book. Finished-book checker progress alone did not produce a freshness warning. A genuinely older snapshot did. A stranger file appeared as a refusal with its reason, and removing the collision restored the move-only plan. |
| Quit and no-focus smoke | **2/2** shell logic tests with doubles. On a real held Approve, one safe-stop request reached `blocked`, named the approval, and moved to `exiting` after release. The custom post-close port probe was inconclusive. A separate **1/1** process smoke loaded the page, scanned and listed one synthetic file, accepted shutdown and exited 0. |

## Limits and disposition

- Optional native Windows tray QA was unrun per Sergei. The installed app, packaged Electron app and installer were not launched. All independent release QA used private synthetic data, ports and offscreen tooling.
- Focus-free visual confirmation used the actual packaged HTML, CSS and renderer in a studio-owned Chrome lease with a synthetic status row. The screenshot shows **6 of 6 files** and **Step 4 of 4 - Checking each file again**. The lease closure verified zero remaining processes and a clean personal-folder audit. A preceding Edge lease timed out before exposing a DevTools port and closed. [Jobs panel screenshot](<I:/AI Projects/Worktrees/Books Arranger/qa-030-codex/approve-6-of-6.png>)
- **Pattern alert PA-1, deferred.** The older studio sweep ACL hold at `qa-9d05455.sweep-62492-1794936066900` remains assigned to its cleanup owner. Earlier sweep EBUSY reports are recorded in the baseline evidence. Neither affected the behavior checks.
