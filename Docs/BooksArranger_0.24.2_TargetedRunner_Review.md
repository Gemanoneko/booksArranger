# Books Arranger 0.24.2 — targeted runner safety review

Reviewer: Senua. Date: 2026-11-01. Scope: the proposed private, source-pinned targeted Python check route only. Tool HEAD observed: 070ec34; development source is dirty and actively changing. This report certifies no application commit range, full-entry receipt, QA result or release.

**Current targeted-runner status:** Exact, one-shot package decisions are recorded below. There is no blanket runner, additional-batch, replay or release clearance.

**Initial proposal verdict (superseded for routing-1 only):** NOT ADMITTED — concrete execution contract incomplete.

No tests, builds, applications, endpoints, live-data reads, audio reads or process-control operations were run by this review. No launcher, guard, admission, ownership helper or product source was modified.

## Reviewed proposal and fixed evidence

Proposal: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/targeted-runner-proposal.md`. SHA-256: `121ca6a5669b9428159e7ad38c1793803c18925c2c7a6c8e8b78f55a21c865c8`. This pin covers a prose design, not an executable runner or a frozen source batch.

It proposes importing existing `runOwned` from the studio REPL, then launching the existing QA Python with `[-I, -B, <batch>/run-targeted.py]`, cwd `<batch>/source`, `timeoutMs: 600000`, the existing qa-ownership Koffi root and the default 16 MiB output cap. Initial module: `test_source_folders`. Ender separately requested `test_shared_routing` and `test_organization` as a second fixed batch. Each batch would have a private source copy, work directory, minimal environment and its own hash manifest. Those concrete batch artifacts were not supplied.

The following bytes were independently read and hashed (paths relative to the studio root):

| File | SHA-256 |
| --- | --- |
| `.claude/skills/qa-handoff/scripts/bounded-check.mjs` | `45510f11a011b617b4831994bd40aa87763d4195cd06c97ee6489af45f91bce6` |
| `.claude/skills/qa-handoff/scripts/bounded-child.mjs` | `240a6a96a32f08989439387d5d6ab75d17e1bcf243863d31d2ff7287f68d1e42` |
| `WIP/Books Arranger/scripts/qa-owned-guardian-v2.mjs` | `c417781be8a70cab280c8654ce9471f284b83ca40f754279a31a43c404323f4e` |
| `WIP/Books Arranger/build-cache/qa-ownership-manifest.json` | `122eca8f1ad057bd86867f8e302c60fcaa5b6dba5ff4e660cfd860cf40769617` |
| `WIP/Books Arranger/scripts/qa-runtime.json` | `2b4a13a73868ccbc88329747156682be62576f054683252b4b72ad9b3fa192a6` |
| `WIP/Books Arranger/scripts/qa-entry-context.mjs` | `ee295f2d834ce1a1cbb00c6895180e32425734fdf25d220b93ea36a7e99e045f` |

The helper pair is unchanged from the independently reviewed correction recorded in `Team/Docs/BooksArranger_CanonicalOwner_SamplingFix_2026-10-21.md` and studio commit `86250c73b577f072a2db6fd35bbcaaa4580e3b35`. The runtime pin file declares Python SHA-256 `434b361fe0c5960d404974feed493db47f2603a1ace2574312104fbed0182c6f` and the complete 47-file Python/FFmpeg tree digest `a3cb3b5e0903b98e3a9e4865321a199eb6f4f53f5739be509bd61d50bbacb031`. Hashing that declaration is not verification of its actual runtime tree. This review did not execute or independently rehash the complete runtime/addon trees.

## What the existing contract supplies

`bounded-check.mjs:192-196` retains and assigns its supervisor to the private kill-on-close Job before releasing the work plan. The helper bounds collected output and refuses timeout, force, overflow, ownership-query or handle-close failures. Its success path requires supervisor stream closure, complete native zero and retained handles signaled (`:147`), followed by checked owner close. No custom owner/spawn override is proposed. These are suitable existing primitives; they do not enforce source hashes, an executable allowlist or filesystem containment.

`qa-owned-guardian-v2.mjs:163-194` accepts only `inert-controls`, `assemble` and `entry`. It cannot admit arbitrary targeted unittest modules. Re-labelling a targeted run as one of those operations would not satisfy that contract. No guardian extension is cleared here.

## Findings requiring a concrete follow-up

1. **[Major] Actual Node identity is missing.** `bounded-check.mjs:153` starts the supervisor with `process.execPath`, not a literal installed Node path. A helper imported inside the studio REPL therefore uses that controller runtime. The plan names no exact controller/supervisor executable or Node runtime manifest; a pin for some other installed Node would not bind this invocation. Supply the exact already-admitted controller invocation and its actual executable/runtime pins.

2. **[Major] The fixed batch is still a proposal.** There is no `run-targeted.py` byte pin, explicit literal environment, complete source/import/fixture manifest, complete tested source identity, or batch-specific invocation digest. The tests and source are being edited concurrently. The helper accepts arbitrary argv and cannot supply the absent restrictions. Each executable script, module list, imported-source closure and output root must be concrete and stable before review can clear a run. The allowlist must exclude app lifecycle/endpoint routes and live data. Runtime preflight must compare the actual complete Python and ownership-addon trees, not only their manifest file hashes.

3. **[Major] Initial test graph omits a console child.** `tests/test_source_folders.py:78`, `test_reparse_source_ancestor_is_rejected_without_following`, invokes `cmd.exe /d /c mklink /J` through `subprocess.run` without an explicit no-window startup flag. The helper passes `windowsHide` to its immediate children; that is not a demonstrated no-focus guarantee for this later Python-created child. The fixture paths are derived from its own private test directory, but the descendant command/no-focus contract still needs an explicit disposition. No console launch was attempted to investigate it. The routing suites inspected calculate paths and metadata in memory; that observation does not replace a pinned import graph.

4. **[Major] Deadline claim must retain its exact boundary.** `runOwned` starts its deadline at its own invocation. Snapshot creation, runtime/source preflight and module import occur before that, and synchronous trusted Node/Koffi/OS startup cannot be preempted by its JavaScript timer. `timeoutMs: 600000` is not proof of a hard 600000 ms bound covering the whole preparation/invocation. Prior engineering records explicitly retain a trusted-bootstrap limitation; this proposal must bind to that reviewed boundary or provide an existing admitted enclosing contract. Do not create a new watchdog, alter a hook or treat a tool yield/poll timeout as termination authority.

These are execution-admission gaps, not newly found Critical product defects and not a release-blocking verdict on 0.24.2. The safety floor has not been demonstrated for the complete proposed invocation, so the run stays stopped.

## Handoff and limits

Ender owns the concrete invocation decision and missing artifacts. Send the actual fixed runner, complete batch manifest, literal environment, actual installed controller identity and runtime preflight record for a narrow delta review. No broad discovery, dynamic later module expansion or generic guardian operation is cleared. If the existing route cannot provide the required contract, report that exact missing capability rather than replacing safeguards.

Any eventual evidence must preserve the actual helper result, including `ok`, `closed`, `forced`, `timedOut`, `overflow`, `truncated`, `outputComplete`, `closureError`, `native.complete/zero/active/unsignaled`, output hashes and source/runtime pins. Failed or uncertain closure is no result, with no duplicate launch. A targeted engineering pass cannot substitute for the final clean-source canonical entry or independent QA/release review.

All permitted writes remain inside the named private batch arena, except this durable review document. No Z: or live-data access, user personal-folder writes, app control, tray/browser/window launches, installs, Git mutations, launcher/admission changes or source writes are admitted.

Hygiene: this reviewer created no disposable probes or scratch artifacts. Existing per-session scratch and other agents' work were preserved.

## Concrete routing-1 delta — 2026-11-01

**Bounded execution verdict:** ADMITTED FOR ONE EXACT `routing-1` INVOCATION.

This clears only the unchanged fixed invocation below as targeted engineering verification. It is not a product-code review, a passing test result, canonical entry/QA receipt or release clearance. `test_source_folders` and every other module remain outside this admission. The initial proposal above is preserved as the evidence/history of what was corrected.

### Exact artifacts

Directory: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/routing-1`.

| Artifact | Bytes | Independently verified SHA-256 |
| --- | ---: | --- |
| `driver.mjs` | 3614 | `8199ad9106d21df18b44f424ed301b6c7a19195c2a75d0130ac72b741ef6cd6d` |
| `plan.json` | 16643 | `880610c5bb2912cf919f1a236f63816aedc591d448556a360a76aa598dcc5a7f` |
| `invocation.json` | 1285 | `613d5dc9423bd4a3c478271ce0d5e7038e48794bc9d009b3dbf7459de122f94a` |
| `run-targeted.py` | 333 | `4f101b808fdf95de695a1b6dcab00f8e414543106c09e8e13049feaf61cd9685` |

Controller executable: `C:/Program Files/nodejs/node.exe`; verified SHA-256 `14319838b3f355e0398c13569a90270bce4fc68f25189f58c59b03dadae0e6d5`. Its only argument is the absolute `routing-1/driver.mjs` path. `cp.execFile` options must be exactly the `invocation.json` options: studio-root cwd, the literal seven-key environment, `windowsHide: true`, `timeout: 600000`, `killSignal: SIGKILL`, `maxBuffer: 2097152`; no shell, extra arguments, inherited environment or custom owner. The caller must verify the exact invocation/driver/plan hashes immediately before submitting this one call.

Child: the pinned `build-cache/qa-runtime/python/python.exe`, exact argv `[-I, -B, <routing-1>/run-targeted.py]`, cwd `<routing-1>/source`. The script explicitly loads only `test_shared_routing` and `test_organization`. Static inspection found 19 and 26 test methods respectively (45 total, counted by their `def test_` definitions); this is a discovery expectation, not an executed count. No unittest broad discovery is admitted.

The literal controller and child environment is the same:

- `SystemRoot` and `WINDIR`: `C:/Windows`.
- `PATH`: `C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/build-cache/qa-runtime/ffmpeg;C:/Windows/System32`.
- `TEMP` and `TMP`: the absolute `routing-1/work` directory.
- `PYTHONDONTWRITEBYTECODE`: `1`; `PYTHONIOENCODING`: `utf-8`.

No `NODE_OPTIONS`, user-profile/data variables, inherited `BOOKS_*`, external test variables or environment additions are cleared. Python receives `-I -B`; its pinned `python314._pth` contains only `python314.zip`, `.` and a commented-out site import.

### Independent read-only verification

Every actual tree member was read and hashed; ordinary non-link files with one link were required and unexpected/missing members compared. Digest method: SHA-256 of sorted `relative/path<TAB>file-sha256` lines joined by LF, matching the existing manifest helper.

| Tree | Actual files | Actual digest | Result |
| --- | ---: | --- | --- |
| `routing-1/source` | 92 | `ed7c5f328b0c52f3e7bddf7d3d5027066ac52cbaed699016ca510160f1218c78` | Exact plan manifest match |
| Existing `build-cache/qa-ownership` | 92 | `a1629fdbc1c73fac1fabd64db245bdd2a12dafe8b93891acce9647dc163f52ad` | Exact ownership manifest match |
| Existing `build-cache/qa-runtime` | 47 | `a3cb3b5e0903b98e3a9e4865321a199eb6f4f53f5739be509bd61d50bbacb031` | Exact declared runtime count/digest match |

The helper pair, manifest helper, runtime pin file, ownership manifest, Python script and Node executable were independently rehashed and matched the plan. The private batch ancestry and relevant runtime/helper ancestors were checked as ordinary directories without symlinks; source/runtime member walks rejected links and special entries. `routing-1/work` was empty. `owned-result.json`, `stdout.log` and `stderr.log` did not exist. This is an ordinary-file/quiescence check, not retained native namespace leases or a claim of immutable files.

Read the full frozen two test modules and their invoked planner path. `shared_routing`, `organization`, metadata path/tag helpers, `destination_overrides.check_fact/inside` and anthology constants operate on in-memory values/path strings in this graph. Importing `native_io` binds Windows API declarations; the tested calls do not invoke its live filesystem/process operations. No application/service lifecycle, endpoint, registry mutation, media decode/read or later process launch is reached. The 90 other root Python files are pinned snapshot content; being present does not cause unittest to discover/import all of them.

### How the prior gaps close, and retained limits

1. The controller is explicitly the pinned installed Node, not the REPL runtime. The driver checks its actual `process.execPath`; existing `runOwned` therefore starts the supervisor under that same executable.
2. The actual fixed driver, runner, complete source manifest, runtime closure and literal invocation now exist and match the above pins. Driver preflight and postflight verify the full source, ownership and Python/FFmpeg trees and helper/runtime pins.
3. The source-folder suite and its `cmd.exe` junction fixture are excluded. Only the two inspected planner modules are admitted.
4. The external `cp.execFile` timeout bounds this controller invocation, including its startup/preflight. The inner owner receives `600000 - 10000 - elapsed` milliseconds; its existing cleanup reserve is contained within that remaining budget. The controller holds the private Job handle, so terminating it closes that handle and invokes the existing kill-on-close behavior. An outer timeout establishes no observed descendant-closure success and must be recorded as no result. Snapshot preparation completed before this invocation and is not represented as Job-owned work. Trusted installed Node/OS loading and the verified existing Koffi bootstrap remain the finite engineering trust boundary; no new guard/guardian/watchdog was introduced.

Lead Ender explicitly confirmed an operational freeze: no edits to the exact snapshot/plan/driver/runner, helper/runtime/Koffi inputs or their ancestors through closure; no other agent owns those paths. Parallel edits are confined to the live checkout outside this snapshot. Ender will recheck the three absent output leaves immediately before launch.

The driver uses default `fs.writeFile` for the three fixed output leaves. This admission therefore covers one fresh invocation in this verified, stable namespace only. It grants no replay, overwrite, namespace-substitution or reusable-runner authority. These writes are the only planned output files and remain in `routing-1`.

### Required result handling

Submit the exact `invocation.json` arguments/options once, await its real completion, and retain that outer result. Accept passing engineering evidence only when the outer controller exits 0 without timeout/overflow, the exact tests execute successfully, the driver postflight completes, and the actual helper result shows `ok=true`, `closed=true`, no force/timeout/overflow/truncation/closure error, complete native zero, `active=0`, `unsignaled=0`, and complete output. An inner `owned-result.json` that says success is insufficient if the controller subsequently fails postflight.

Record the three artifact hashes, complete test counts/output, the actual source/runtime pins above and native closure evidence. A mismatch, uncertain closure, output collision or timeout stops the batch; do not replay it. Any changed bytes, selected modules, environment, executable, deadline, paths or new batch require a narrow delta review. No test was run by Senua during this review.

## Concrete chapters-1 delta — 2026-11-01

**Bounded execution verdict:** ADMITTED FOR ONE EXACT `chapters-1` INVOCATION.

Scope: the frozen `test_terminal_chapters` module, exactly 20 cases (17 mocked and 3 native); no skip accepted. No test was run by Senua. The standalone source-folder, series and cleanup graphs are not included. This is permission for one bounded engineering check, not a claim that it passes or clears a release.

Directory: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/chapters-1`. Exact independently verified artifacts:

| File | SHA-256 |
| --- | --- |
| `driver.mjs` | `42d64b6c4e4cce7d265309c1930fa472d8d1bbe66a46a74fc3a3dfb19d4cd444` |
| `plan.json` | `54528b9d2549ad11e4fb5a98c3d8966aa4f8ddd057efe120f4866c39caddf25f` |
| `invocation.json` | `eb18ffe16887a088b4a34a74b7c60842519ecc2dca1500fd31c74e77ce6fbfc7` |
| `run-targeted.py` | `7bbf08d63673f6b470cf257b7630a9f84a92074bba92c1d80722de223b7197a1` |
| `native-graph.json` | `c87ad7843a9fc8b088483616d9e5dec2b568bd9afd25f1b0f4f4aede5fe232a2` |
| `review-request.md` | `b2b1e3c0c1d87e158192fb2ba576cc975b667c7133cac52c0e8a107daef8f4c9` |
| `read-only-preflight.json` | `f8d591aa5d290b0d038d1140364f08e74eb60fa12394743d2ec1fa32d7418e5b` |

The invocation retains the exact previously reviewed installed Node executable/hash, studio cwd, no-shell `cp.execFile`, hidden launch, outer timeout600000, SIGKILL and 2 MiB controller-output bound. Its only argument is the pinned `chapters-1/driver.mjs`. The driver retains unchanged `runOwned` with remaining `600000 - 10000 - elapsed` budget. The child is the same pinned Python, `-I -B`, this batch's fixed runner and source cwd. Environment is the routing-1 seven-key shape with batch-local TEMP/TMP, plus only `BOOKS_TERMINAL_FIXTURE_ROOT=<chapters-1>/work/fixtures`. No inheritance or extra variable is permitted.

Independent full-file walks and hashes verified:

- 91 source files, digest `98b9ade045de17d2ffe42d560fd0d7bc8580aa390d7041affd0076adbdc4de70`, exact plan match. The stable base is routing-1's root Python snapshot; only `audio_pipeline.py` was substituted, and the dedicated test replaces the routing tests. Pipeline pin `f0682219fd19ef11e8d6bce75a1fb66b580639846f1a2604b8b2095c4b26e2b2`; test pin `529d51638f420098e57987115a53a733205d5aae6204205a6845e660791b96e1`. This tests the isolated pipeline, not concurrent live service/renderer edits.
- 47 runtime files, digest `a3cb3b5e0903b98e3a9e4865321a199eb6f4f53f5739be509bd61d50bbacb031`; 92 ownership files, digest `a1629fdbc1c73fac1fabd64db245bdd2a12dafe8b93891acce9647dc163f52ad`. Both match the exact plan and original runtime manifests.
- Node, helper pair, manifest helper, runtime pin file, ownership manifest, runner and native graph hashes match. Ordinary source/runtime files have one link. Twenty-two distinct batch/runtime/helper ancestor paths were ordinary directories without symlinks. Work was empty and all three result leaves absent.

### Native graph assessment

The full test module, reached pipeline functions, existing media owner/primary-thread mechanism and import-time module statements were read. The 17 deterministic tests patch `probe`, `VerifiedFile`, container planning, packet evidence and PCM evidence: their synthetic `C:/private-fixture/part.m4b` value does not trigger filesystem access. The three native tests create a fresh UUID fixture under the exact work root, generate two seconds of AAC and a 32x32 PNG, alter only their newly generated chapter timing, and exercise full-source proof, private truncation refusal and a two-part private conversion. In-memory and generated-fixture changes are within scope.

The only native executable descendants are the pinned FFmpeg/FFprobe leaves. `audio_pipeline.py:194`, `:240` and `:311` launch them with `shell=False`, `CREATE_NO_WINDOW`, below-normal priority and `CREATE_SUSPENDED`; `closed_media_job` assigns each retained subprocess to its nested kill-on-close Job before the existing `resume_owned_primary` resumes it. The outer Job still contains Python and all descendants. The primary-thread enumeration is the established owned-child startup mechanism, not a diagnostic snapshot or control of the user's running application. No breakaway, shell, installer, browser, GUI, app endpoint or publication function is reached.

Names and argv derive only from the fixed generated fixtures/pinned code. FFmpeg reads generated lavfi input, local files or pipes and writes only private fixtures/staging; there is no playback, real media or network source. Joined encoding can overlap one encoder with one decoder. Imported `m4b_repair` hashes its own pinned `m4b_preservation.py` source at import; this is a read of snapshot code, not live data.

`native-graph.json` records a static expected 49 native leaves on its successful path. This is not an executed process count. The review verifies confinement and ownership of the reached launch paths, and does not convert the static estimate into evidence of actual execution. Failed assertions may stop a path early.

### Freeze and result requirements

Chapter Ender froze all candidate inputs; lead Ender confirmed shared helper/runtime/Koffi/executable and ancestor freeze through this invocation, with no concurrent run/writer to this batch. Other live-source edits do not mutate the snapshot. The executor must recheck the exact invocation/driver/plan hashes and fresh output leaves immediately before launching. No replay or overwrite authority is granted.

All routing-1 acceptance conditions remain: outer completion exit0 without timeout/overflow, exactly20 executed/no skips/success, all postflight pins, and the actual helper result with `ok/closed/outputComplete=true`, no forced/timeout/overflow/truncation/closureError and complete native zero with active0/unsignaled0. The controller's default output writes cover only its three verified-absent fixed leaves. Generated native fixtures/diagnostics remain under the exact work root as named by the graph. An outer kill or uncertain closure is NO RESULT, with no duplicate launch. Do not treat a success-looking inner result as sufficient after failed controller postflight.

The original trusted Node/OS/Koffi bootstrap and quiescent ordinary-path limits remain explicit. No new owner, guardian, hook, watchdog or product code was changed in this review. No live paths, app actions, installation, personal-folder writes or release operation are admitted.

## Concrete cleanup-1 delta — 2026-11-01

**Bounded execution verdict:** ADMITTED FOR ONE EXACT `cleanup-1` INVOCATION.

Directory: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/cleanup-1`. Scope is exactly `test_cleanup_242` (18 methods) plus `test_source_folders` (44 methods), 62 total with no skipped cases accepted. Static counts were independently checked; none was executed by this reviewer.

| Exact artifact | Independently verified SHA-256 |
| --- | --- |
| `driver.mjs` | `ef59d887ec64a1abb21aecf7a2762bc5b40c3a7013e37c57bfa5ba88a1e47e5f` |
| `plan.json` | `de46a697ffb84e435612c49f45b9ec097cfdd0f06aa8a799bfaa4e1c05415471` |
| `invocation.json` | `abd4227cc59d23f75b658402f191a00c6d2bf69a654bf0fede4d64f5d8a1165b` |
| `run-targeted.py` | `3781e6a25f959bc12ab22c295928d12d64c3b0f72a80909172bc5a850493978e` |
| `review-request.md` | `911b4ee3dcb541560a1f17a0017f1d98084ade625736f6113e2095bdb8dbf03f` |

The complete source tree is 95 ordinary single-link files, exact plan match, digest `5ce608e3784100e5b362c9ad26806f06213182683be098d990b14bdac904759a`. The independently rehashed 47 runtime files still match `a3cb3b5e0903b98e3a9e4865321a199eb6f4f53f5739be509bd61d50bbacb031`; 92 ownership files still match `a1629fdbc1c73fac1fabd64db245bdd2a12dafe8b93891acce9647dc163f52ad`. Node, helper pair, manifest helper, pin files and runner all match their exact plan pins.

The outer invocation preserves the installed Node14319838… pin and routing-1 controller shape: exact hidden no-shell `cp.execFile`,600000ms timeout, SIGKILL,2MiB output bound, studio cwd and only one absolute driver argument. Environment is the original seven-key literal shape with cleanup-1/work TEMP/TMP. Python remains the pinned runtime with `-I -B`, this runner and source cwd; unchanged `runOwned` receives the remaining budget minus10000ms. No inherited environment, modules or executable overrides.

### File/deletion and process graph

The 18 new regressions use in-memory SQLite and a `MergeService.__new__` object with mocked workers, no service constructor or app startup. Their only concurrency case starts a bounded Python thread around the mocked maintenance lock/guard, with bounded waits/join. Synthetic `C:/library/...` values are database/text keys, not filesystem reads or writes.

The 44 source-folder cases create a fresh `TemporaryDirectory` under `source/scratch/progress-folders-2026-10-10/empty-folder-fixtures`. Database, synthetic MP3/M4B bytes, recovery tree, stage tree, covers, alternate streams, hardlinks and junction target all derive from that fresh private directory. Queue construction initializes only the passed private database; no audio worker is started. CleanupJobs and StorageCleanup receive only those private roots. The fixture output-policy seam explicitly declares this private library as sorted. Tests exercise real deletion/retirement only on their generated bytes and remove their own temporary tree at teardown. Native safety assertions preserve fixture roots/output/unknown files. No media decoder, app endpoint, live database, configured Z: root or real source is reached. Source code files remain pinned; the permitted `source/scratch` subtree holds disposable fixtures only.

The sole extra executable is `C:/Windows/System32/cmd.exe`, independently hash-matched to `ccd79a7568ea9240ccd6fe124807b9d3e4dbc3a4cf92954299ac3029f4a91d02`, also checked by the driver before/after. `test_source_folders.py:78` now uses exact `/d /c mklink /J` plus two private fixture paths, `capture_output=True`, `timeout=10` and `CREATE_NO_WINDOW`. It inherits the outer Job. `/d` disables AutoRun. The command and both arguments contain no user input or command metacharacters; list argv quoting handles the fixed space in `Old Book`. Both the junction and its target are inside the same generated test directory. There is no delete shell command, other shell fragment or interactive console. This resolves the original proposal's omitted/unhidden child for this exact snapshot only.

Twenty-four distinct batch/runtime/helper/command ancestor paths checked as ordinary directories without symlinks; work was empty and `owned-result.json`, `stdout.log`, `stderr.log` absent. Native fixtures intentionally create links/streams only after starting inside their private subtree; they are not imported executable inputs.

Lead confirmed cleanup-1 inputs, shared helpers/runtime/Koffi, cmd and their ancestors frozen through closure, no concurrent run, and chapter-1 already closed. Executor must immediately recheck exact invocation/driver/plan hashes and absent result leaves before this one launch. Default-w result writes grant no reuse/overwrite authority.

Required acceptance: actual outer exit0 without timeout/overflow; exactly62 tests executed successfully with no skips; complete unchanged source/runtime/helper postflight; actual helper `ok/closed/outputComplete=true`, no force/timeout/overflow/truncation/closureError and complete native zero/active0/unsignaled0. Temporary fixture leftovers that alter the source manifest cause postflight refusal, never a passing claim. Failure or uncertain closure is retained and stopped, with no replay. No release verdict or admission of another batch is implied.

## Concrete series-1 delta — 2026-11-01

**Bounded execution verdict:** ADMITTED FOR ONE EXACT `series-1` INVOCATION.

Directory: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/series-1`. Fixed module `test_series_identity_242`,19 methods, no skips. No reviewer execution and no broader/release clearance.

| Exact artifact | Independently verified SHA-256 |
| --- | --- |
| `driver.mjs` | `63e543f3fb39940c4bfb1ec8be89f7a91f08994f1a0d96a433176db75a24fc29` |
| `plan.json` | `6d2d8ced8bed5b5ca8d240c569943b223abab19a5eb08885b2e1d150d99a9f89` |
| `invocation.json` | `d3cbce86b3639570c2136d611eaddbfb621cc12eebdc68f2a145d0c9e8537da1` |
| `run-targeted.py` | `89969b5f6a3d7d36c5cd7f89f9abf2d952229feaeb015894fdd26234fb872b57` |
| `graph.md` | `c101c8a27deb4a4a8b5a9c939961580a0c977bf0428aaf13d0b1aaee5a916660` |

Independent walks/hashes:92 source files exactly match the plan, tree digest `9b2bd07ed78ed910a228a9626823688285a0a1ca0b4e97f3d3cc272058060324`;47 runtime files digest `a3cb3b5e0903b98e3a9e4865321a199eb6f4f53f5739be509bd61d50bbacb031`;92 ownership files digest `a1629fdbc1c73fac1fabd64db245bdd2a12dafe8b93891acce9647dc163f52ad`. All Node/helper/manifest/runner pins independently match. Source/runtime files are ordinary single-link members. Twenty-two batch/runtime/helper ancestors are ordinary non-symlink directories; work is empty and all three result leaves absent.

The exact controller/child/timeout/remaining-budget/closure structure is unchanged from routing-1. Only batch root, schema, fixed module list and pins change. Outer invocation is the pinned installed Node14319838… with one absolute driver argument, studio cwd, literal seven-key environment with series-1/work TEMP/TMP, hidden no-shell `cp.execFile`,600000ms timeout, SIGKILL and2MiB bound. Python remains pinned with `-I -B`. The fixed runner rejects import errors, any count other than19 and skipped/failing cases.

### Reached graph

Read the full frozen test and actual `PublicResearch.approved`, `_local_lookup`, `_english_original`, `_part_set`, retained-evidence and routing functions plus the relevant path helpers/import-time statements. `CacheOnlyResearch` replaces identity, saved-name, rules and gap lookup seams; it does not initialize a public client. The real approval chain stays on its zero-request budget. Author-rule writes are not reached for these approved fixtures. An unexpected client use has no configured client/database to operate on.

The sole fixture-data read is snapshot `Docs/BooksArranger_DiagnosisEvidence_2026-11-01.json`, SHA-256 `eb175a5e294b66832cb99ecaa7bed73d4f5bf5cab3d63b7d2b68c653474d0732`. It is included in the complete source manifest. Recorded source path strings are replaced with synthetic paths before tested product calls; no Z: or live path is opened. Those synthetic files are not created or read. Corbett folder and shared-routing tests use strings and in-memory metadata only.

The Queen `_part_set` case returns from the exact confirmed-edition branch; `part_sets.read_chapters` is replaced with an assertion-raising mock. Native destination validation is not called; `native_io` only binds API declarations on import. Scanner/groups/imported modules do not instantiate an inventory/service or run database/network work. No subprocess follows the owned Python child, and no app/GUI/media/network/installation or deletion path is admitted.

Lead confirmed this batch and shared helper/runtime/ancestor freeze, with prior cleanup-1 fully closed and no concurrent run. Immediately before the one invocation, executor must recheck driver/plan/invocation hashes and absent outputs. Preserve outer exit/result and the unchanged postflight alongside the helper evidence. Passing evidence requires exactly19 successful/no-skip cases, outer0 without timeout/overflow, postflight success, `ok/closed/outputComplete=true`, no force/timeout/overflow/truncation/closureError and complete native zero/active0/unsignaled0. Default result-file writes are authorized only for these fresh leaves; no replay, overwrite or modified graph. All earlier trusted-bootstrap/quiescence limits remain.

## Concrete cleanup-2 assertion delta — 2026-11-01

**Bounded execution verdict:** ADMITTED FOR ONE EXACT `cleanup-2` INVOCATION.

Fresh directory: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/cleanup-2`. This is a new reviewed package, not a replay of cleanup-1. Lead reports cleanup-1 closed with postflight intact but four assertion failures; its evidence remains. Series-1 subsequently completed nineteen passing cases with outer0, postflight and native zero, so no prior run overlaps. Those outcomes are executor reports, not tests run by this reviewer.

| Exact artifact | Independently verified SHA-256 |
| --- | --- |
| `driver.mjs` | `d42d2a8e9227ed2be29a076dad9cc6bb93b94a8ee5db6174d04eddcbe9daff1d` |
| `plan.json` | `970372077d285ace0887129c7c773cf5245ea57d9ebf717f6f1f5a904bfcf315` |
| `invocation.json` | `bc8cb115177b191fce68eea4205301821fbf3a8fe3345dbb653ef0589404d23a` |
| `run-targeted.py` | `3781e6a25f959bc12ab22c295928d12d64c3b0f72a80909172bc5a850493978e` |
| `source/tests/test_source_folders.py` | `71988bc3e107153ee5e05891545a9d5b5030343e66678392130e6ece8eaaa00f` |

Independent complete walk:95 source files exactly match plan, tree digest `07fc7c8c2fa55859f631cb9c4e83cd1b46c266b2af68a51d91c9b1995054aaea`. The only source change from cleanup-1 is the named test file; all production modules and the18 cleanup tests are byte-identical. Runtime47 files and ownership92 files independently rehash to the earlier `a3cb3b5e0903b98e3a9e4865321a199eb6f4f53f5739be509bd61d50bbacb031` and `a1629fdbc1c73fac1fabd64db245bdd2a12dafe8b93891acce9647dc163f52ad` digests. All eight explicit pins, including cmd.exe, match. Source/runtime/ownership members are ordinary single-link files; 25 distinct ancestors checked as ordinary non-symlink directories. Work is empty and all three result leaves are absent.

Read the exact four test edits. Both held-open scenarios now require retryable `BoundaryError`, then remove the mock fault and prove completion, folder removal and preserved output. The long-receipt case additionally requires the previous forty receipt rows to remain exact. The protected-root and unknown-actor expectations match the existing conservative wording; unknown-actor absence remains explicitly distinct from a recorded removal. No new fixture path, executable, source operation or external read is added. The source-folder module remains44 cases and the runner still requires all62 cases successful with no skips.

The driver is byte-identical to cleanup-1 after substituting batch name and fixed plan hash. The exact outer installed-Node invocation, literal seven-key environment, pinned Python `-I -B`,600000ms controller deadline, elapsed-time subtraction and10000ms closure reserve, owned supervisor/job handling, before/after pins and manifest checks remain unchanged. The only extra executable remains the reviewed hidden10s `cmd.exe /d /c mklink /J` operation on private fixture paths. All cleanup-1 graph restrictions and private source/scratch/write boundaries carry over.

Lead explicitly confirmed cleanup-2 plus shared helper/runtime/Koffi/cmd inputs and ancestors frozen through closure, outputs fresh and no concurrent execution. Executor must recheck driver/plan/invocation hashes and output absence immediately before this one unchanged launch. Acceptance requires outer0, unchanged postflight, exactly62 successful/no-skip tests, helper `ok/closed/outputComplete=true`, no force/timeout/overflow/truncation/closureError and complete native zero/active0/unsignaled0. Timeout or missing closure is no result; retain evidence and stop without replay. No release, additional package or reusable-runner clearance is given.

## Concrete chapters-2 fixture delta — 2026-11-01

**Bounded execution verdict:** ADMITTED FOR ONE EXACT `chapters-2` INVOCATION.

Fresh directory: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/chapters-2`. The chapters-1 failure evidence is retained. Its executor reported17 passing deterministic cases and three failed native cases, with unchanged postflight and complete native closure. This package corrects the synthetic fixture rather than modifying the production proof. Reviewer ran no tests or native media commands.

| Exact artifact | Independently verified SHA-256 |
| --- | --- |
| `driver.mjs` | `386643f1e958c880e51b380f2f05418ad96b9ee4955989aabb7f79b42f920ba5` |
| `plan.json` | `818295ac0b6fdc1e77e80d7a00adedf0e31c3068b48858932bc965a741288f7d` |
| `invocation.json` | `5d2e2e9110e204876ea72f93628e2fc5db52b4760a737d3a1ed215c9515139dd` |
| `run-targeted.py` | `7bbf08d63673f6b470cf257b7630a9f84a92074bba92c1d80722de223b7197a1` |
| `native-graph.json` | `a4ff39606c4b5dc3c031d435535add1e8969aee3a56c3cd2b419d17f6ee985f9` |
| `source/tests/test_terminal_chapters.py` | `7543b26744f714f40ff1d521374ca6590d1b462af22cf2329952269334107350` |

Independent complete walk:91 source files exactly match plan, tree digest `92e36c3492388a8d87bde42f5a8d17494f890ca2c12e098ca963263faf674b13`. Only the named test file differs from chapters-1. Production audio_pipeline remains `f0682219fd19ef11e8d6bce75a1fb66b580639846f1a2604b8b2095c4b26e2b2`; all dependencies remain byte-identical. Runtime47 files and ownership92 files independently match the established `a3cb3b5e0903b98e3a9e4865321a199eb6f4f53f5739be509bd61d50bbacb031` and `a1629fdbc1c73fac1fabd64db245bdd2a12dafe8b93891acce9647dc163f52ad` digests. All eight explicit pins match. Source/runtime/ownership files are ordinary single-link members;23 batch/shared-input ancestors checked as ordinary non-symlink directories. Work is empty and the three result leaves are absent.

Read the full fixture delta and retained native test body. The added edits change only the generated text track tkhd duration and single zero-origin elst duration, using an exact text/movie timescale conversion. They do not alter audio clocks, packets, byte offsets or chapter starts/titles/order. The initial real probe must now show a last endpoint beyond audio duration plus0.25s; otherwise setup fails instead of reporting correction coverage. Production tolerances, strict decode, container proof, digest/mtime checks and output-validation assertions are unchanged. The truncated-container case still requires refusal without changing its bytes. Source identities and corrected joined output remain asserted.

The controller is byte-identical to chapters-1 after substituting batch identity and plan hash. Exact fixed installed-Node `cp.execFile`, eight-key literal environment including `BOOKS_TERMINAL_FIXTURE_ROOT=<batch>/work/fixtures`, pinned Python `-I -B`, outer600000ms deadline and elapsed-time subtraction plus10000ms closure reserve are unchanged. All source/native-graph/runtime/ownership/helper/runner pins are checked before and after. The runner requires exactly20 executed cases with no failures or skips.

The owned graph remains17 deterministic cases plus3 native cases, generated2s AAC/PNG/private stage only. FFmpeg/FFprobe continue through existing no-shell `CREATE_NO_WINDOW | BELOW_NORMAL_PRIORITY_CLASS | CREATE_SUSPENDED` launch, nested Job assignment before existing owned-primary-thread resume, and outer Job inheritance. No new executable, native thread-inspection operation, live media source, app endpoint, network, install, source deletion or shell graph is added. The49 predicted leaves remain a static successful-path estimate, not an observed process count. Huge synthetic text duration does not authorize live source data or a longer controller budget.

Before this decision, lead reported cleanup-2 completed all62 cases with no skips, outer0, matched postflight, complete native zero/active0/unsignaled0, no force/timeout and no concurrent run. Lead then confirmed chapters-2 and shared input/helper/runtime/Koffi/executable ancestors remain frozen through closure and result leaves remain uncreated. Executor must immediately recheck driver/plan/invocation hashes and output absence, then run this exact invocation once. Default output writes grant no reuse authority.

Passing evidence requires outer0 without timeout/overflow, unchanged postflight, all20 successful/no-skip cases, helper `ok/closed/outputComplete=true`, no force/timeout/overflow/truncation/closureError and complete native zero/active0/unsignaled0. Timeout, failure or uncertain closure means retain evidence and stop; no replay or unreviewed package. All trusted-bootstrap and quiescence limits from routing-1 remain. This is neither final release review nor canonical full-entry clearance.

## Concrete chapters-3 planner and output contract delta — 2026-11-01

**Bounded execution verdict:** ADMITTED FOR ONE EXACT `chapters-3` INVOCATION.

Fresh directory: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/chapters-3`. This is a narrow safety review of the frozen product/runner delta; it does not establish product test success, final release clearance or a reusable encoding/runner route. No reviewer test, probe, build or native media execution occurred.

The prior chapters-2 receipt was independently read: `ok=false`, `closed=true`, `forced=true`, `timedOut=false`, `code=null`, `outputComplete=false`, reason `Final supervisor output differs from streamed bytes`. Native accounting is complete/zero with active/assigned/listed/unsignaled0, retained18 and142 queries with none incomplete. Its log says20 ran with two errors; that is not an accepted passing result. Retained diagnostics show replacement characters around the quoted title. A non-UTF-8 Windows text encoding is a plausible cause; original raw bytes/code page were not retained, so this review does not claim those bytes or the exact code page were measured. The prior evidence remains unchanged and is not replayed.

| Exact artifact | Independently verified SHA-256 |
| --- | --- |
| `driver.mjs` | `ca3f05703f147db4abca34a822e85d3074080ea3376596267c343e0718093d7a` |
| `plan.json` | `14dd645acc6a0f32cae55e32279cdd91d8548e3b77b9bc6f8bbb824f1cfce612` |
| `invocation.json` | `101cf9c0e6bc4a80000b909af8e69adf3fa898f59eb743f1f05a0c1bf6fcbd59` |
| `run-targeted.py` | `a733008645b6c68c05c9518487298767ceacacf2c0fe9225c9b1ad20e73e9858` |
| `native-graph.json` | `3bdf01698e1f82192736ca1e3c414f33f0d9b0a6fcf8a28897673c874735d847` |
| `review-request.md` | `c9e9e166cb2612be12a228b594d982f33218fad2eb770d26790a73f8672cf7f5` |
| `source/audio_pipeline.py` | `2650ea70ef839aad200bca5f4bd2f2d507a8046d7722d73f55cbbcbe4057985d` |
| `source/tests/test_terminal_chapters.py` | `8266b5b3681199a9c477418a0ac4fb876fab51c34b917b7e35563df3bc51d039` |

Independent full walk:91 source files match the plan exactly, digest `d65b77594e0d82970e305bd30aa5a9a2403fb8bf8836f5c4e0ba63ee5f9dbcc8`. Only audio_pipeline and its dedicated test differ from chapters-2. Runtime47 files independently match `a3cb3b5e0903b98e3a9e4865321a199eb6f4f53f5739be509bd61d50bbacb031`; ownership92 files match `a1629fdbc1c73fac1fabd64db245bdd2a12dafe8b93891acce9647dc163f52ad`. All eight explicit Node/helper/manifest/runner/graph pins match. The three trees contain ordinary single-link files;23 relevant ancestors are ordinary non-symlink directories. Work is empty and owned-result/stdout/stderr leaves are absent.

### Product delta

Read the complete verified_source_chapters body, preservation.plan, approved_items and existing m4b_repair.diagnose pattern. Passing an in-memory title satisfies the existing metadata input contract. The planner reads via the held read callback, validates the intact container and creates an in-memory candidate. This caller consumes only track facts; it neither streams that candidate nor passes it to a writer. Its default repair set remains empty and no damage allowance, packet count, duration tolerance, source digest/facts refresh or strict decode check changes. The dedicated fake now invokes real approved_items, which refuses empty tags. Native full-proof/join/truncation assertions remain unchanged. This removes the planner input-contract error without authorizing source modification or repair.

### Explicit diagnostic contract

The fixed Python runner calls stdout/stderr.reconfigure with ASCII and backslashreplace before test imports, then emits the same known curly-quote/Cyrillic marker on both streams. The plan marker was checked as literal single-backslash Unicode escape sequences. Non-ASCII Python text is represented with its escape value rather than discarded or replaced with question marks; this is explicit diagnostic rendering, not reconstruction of the previous run bytes. The environment mirrors this setting, but the runner does not rely on PYTHONIOENCODING under isolated Python.

The unchanged supervisor sends raw base64 stream chunks and independently UTF-8-decodes the final accumulated bytes. ASCII output is valid UTF-8, so its exact byte comparison remains meaningful. No captured output is filtered or rewritten after collection. The driver additionally requires only ASCII and the expected marker on each stream, after existing closure and postflight checks; a missing marker or unexpected byte fails the outer driver. A count other than20, any skipped/failing test or import error still yields nonzero Python status. Existing helper failure/force/timeout remains nonzero; marker checks cannot turn failed tests or a rejected supervisor receipt into success. Native FFmpeg/FFprobe diagnostics remain private bounded files, not inherited raw text on these Python pipes. Binary writes or a future output path are not admitted by this package.

The native graph matches chapters-2 after private path substitution; only explanatory fixture/output fields differ. It remains17 deterministic plus3 native cases and49 predicted successful native leaves, not an execution count. Existing hidden no-shell suspended native launch, nested Job assignment before owned-primary-thread resume and outer Job inheritance remain unchanged. Only generated private AAC/PNG/stage fixtures are reachable. No source deletion, live/Z: data, real app endpoint, network, installation, desktop control or new shell graph is added.

The exact installed-Node invocation still uses one absolute driver argument, literal eight-key environment, hidden cp.execFile without shell,600000ms outer deadline and2MiB controller output cap. Unchanged runOwned receives the remaining deadline after preflight minus10000ms closure reserve,16MiB child-output bound and pinned Koffi root. All source/runtime/ownership/helper/runner/graph inputs are checked before and after; trusted Node/OS bootstrap and operational quiescence remain explicit limits.

Lead confirmed no concurrent run and chapters-3 plus all shared helper/runtime/Koffi/executable inputs and ancestors frozen through closure. Executor must immediately recheck exact driver/plan/invocation hashes and absent result leaves before one unchanged invocation. Passing evidence requires all20 successful/no-skip tests, both escaped markers and ASCII streams, outer0, unchanged postflight, helper ok/closed/outputComplete true, no force/timeout/overflow/truncation/closureError and complete native zero/active0/unsignaled0. Any failure, outer timeout or uncertain closure is retained and stopped with no replay. No additional batch or release is cleared.

## Concrete UI-1 sequential JavaScript batch — 2026-11-01

**Bounded execution verdict:** ADMITTED FOR ONE EXACT `ui/ui-1` INVOCATION.

Directory: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/ui/ui-1`. Review covers this frozen test graph and sequential controller adaptation, not the accumulated product release diff or real browser geometry. Reviewer executed no tests, app, dialog or browser. Lead reports chapters-3 accepted20/no-skip tests, both encoding markers, outer0/postflight and normal native complete/zero closure; no run remains concurrent.

| Exact artifact | Independently verified SHA-256 |
| --- | --- |
| `driver.mjs` | `73a7b0f495720fd6a91b2b042b4605c7bafa46cd76d464e77060983ffc2c9719` |
| `plan.json` | `4f22a8eac80e73f5474731e6ce80a4d18a2b524eaf1ab7bba0c66ae45ea2aeeb` |
| `invocation.json` | `4e8cc01f1976460901ef41dcb58094a597dd4b61dfe33126f1c8f5e5dfd2e1a4` |
| `native-graph.json` | `4806d3af912a6f520611d928c3084a4d5c9a9aa6370e245f2cc5b6dd18987990` |
| `review-request.md` | `2641d6a8789b3fe0c461a9d8de95baf632586e13ca3a217c0b55c526d590df17` |

Independent complete tree walk:15 ordinary single-link source files exactly match plan, digest `d5bba774ce13d2852c84aaaff008ec7871d5da855c580dc0e2082b895011c499`. Runtime47 files match `a3cb3b5e0903b98e3a9e4865321a199eb6f4f53f5739be509bd61d50bbacb031`; ownership92 files match `a1629fdbc1c73fac1fabd64db245bdd2a12dafe8b93891acce9647dc163f52ad`. All seven explicit installed-Node/helper/manifest/graph pins independently match. Twenty-four relevant ancestors are ordinary non-symlink directories. Work is empty. All28 result paths are absent: owned-result/stdout/stderr01 through09 and summary.json.

### Fixed execution graph

The exact order is test_0242_frontend, test_0231_destination_frontend, desktop-folder-picker.test.mjs, test_automatic_frontend, test_ruling37_frontend, test_0231_rows_frontend, test_todo_holds_frontend, test_progress_frontend, test_odd_names_frontend, all under source/tests with the extensions pinned in plan. Nine separate Node test children are launched sequentially by the existing owned supervisor. The test process receives only its absolute fixed entry path, with no npm, --test isolation, extra argument or shell. Direct node:test usage registers the eight picker cases in that process. No further test-created process is present in the reached source graph.

Inspected all entry setups, dependency/file-read and execution sites, completion sites, shared retry harness, actual picker implementation and fake picker suite. Renderer scripts read only the frozen harness/app/markup/styles. Six entries slice the shared harness before its original test IIFE, then compile their own fixed assertion body; its original PASS cannot satisfy their completion marker. Automatic/progress entries construct their own DOM/transport contexts. Fetch and open-folder routes terminate in in-memory functions; the loopback origin and Z:/other drive fixture strings are data, not opened resources. Timers are doubles except short host scheduling waits. app.js executes in the explicit VM context without a real browser or real desktop bridge. These are reviewed source doubles, not a claimed general-purpose VM security sandbox.

The actual folder picker imports only node:path and receives the supplied fake dialog/window/IPC. Its showOpenDialog calls resolve or reject in-memory promises; no Electron module or real dialog is imported. The destination renderer test similarly provides a fake booksDesktop.chooseFolder. Fake element focus mutates a document property only. No real desktop focus, app endpoint, clipboard, window, tray, library/media access, network or installation path is admitted. There are no test filesystem writes; only frozen source reads. desktop-ui/HTML/CSS are snapshot references, not real browser/geometry evidence.

Each of eight frontend entries has exactly one final PASS output site after its assertions; asynchronous catches retain nonzero exit status. The picker has exactly eight fixed node:test declarations. The driver requires each helper result.ok and its PASS marker, or picker TAP tests8/pass8/fail0/skipped0, together with normal native closure. A prematurely settled async script without its marker cannot pass. An assertion failure may continue only after normal complete/zero closure; its failed summary entry persists and prevents overall success. Forced/timed-out/uncertain closure throws before another test entry. The unchanged helper sets closed=false on handle-close failure and result.ok=false on output/exit/closure rejection; no failure is normalized away.

### One controller deadline and evidence

Outer invocation remains fixed installed Node14319838… with one absolute driver argument, studio cwd and literal five-key environment: SystemRoot/WINDIR=C:/Windows, PATH=C:/Program Files/nodejs;C:/Windows/System32, TEMP/TMP=<batch>/work. No inherited NODE_OPTIONS/NODE_PATH or lifecycle launch is supplied. Hidden no-shell cp.execFile has600000ms timeout, SIGKILL and2MiB output bound. Before each runOwned call, remaining time is recomputed as600000 minus elapsed controller time minus10000ms reserve; this is one shared deadline, not nine fresh ten-minute budgets. Every child remains under the unchanged ownership-before-work handshake/private kill-on-close Job,16MiB output bound and strict supervisor byte comparison. Node text output uses UTF-8; no Python encoding workaround is involved. The pinned Python/media runtime is integrity-checked but never executed.

Each entry writes its own fresh result/log trio. summary.json is intentionally updated within this single invocation, initially complete:false, and reaches complete:true only after all nine entries and full source/runtime/ownership/helper postflight. Those internal summary updates do not authorize replay or overwriting pre-existing evidence. Outer exit0, complete:true/ok:true, all nine accepted entry receipts/markers and unchanged postflight are required. An intermediate summary or inner result cannot substitute for successful outer/postflight completion. Outer timeout is no observed closure result, even if OS Job-handle close terminates children.

Lead confirmed no concurrent run and full snapshot/shared Node/helper/runtime/Koffi/ancestor freeze through closure. UI owner separately confirmed source/artifact/ancestor freeze; any geometry preparation remains outside ui-1 and cannot mutate shared pinned inputs or execute tests/browser work. Executor must immediately recheck exact driver/plan/invocation hashes, empty work and absence of all28 result leaves, then run this exact invocation once. Accept only normal closure for every entry, with ok/closed/outputComplete true, no force/timeout/overflow/truncation/closureError and complete native zero/active0/unsignaled0, plus all completion markers and postflight. Retain any failure and stop without replay. No geometry, backend batch, broader runner or release clearance is given.

## Concrete UI-2 reporter/assertion delta — 2026-11-01

**Bounded execution verdict:** REVIEW COMPLETE; NOT YET ADMITTED pending executor confirmation of shared-input freeze and no concurrent run. This section grants no execution authority until that condition is explicitly recorded.

Fresh directory: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/ui/ui-2`. Only the two nonaccepted UI-1 entries are selected. Independently read prior summary: complete:true, ok:false; seven entries accepted, picker exited0 with marker:false, automatic exited1 with marker:false; all nine closed:true. Prior evidence remains unchanged and seven accepted entries are not replayed.

| Exact artifact | Independently verified SHA-256 |
| --- | --- |
| `driver.mjs` | `d6eba00b31a94036a908901474fbeaaaa75babbef13e9ea8456eeb0c58d1479d` |
| `plan.json` | `6eb0015b5f080475793d963efdabe6c1ebeb440bc71893722e306d6e7a1f52d0` |
| `invocation.json` | `9872966edafab15da81cb358d9e474d0525388a68c945ccb645787cd41cdfbeb` |
| `native-graph.json` | `c8977b8e41650d8035ced555fe3ad2327ed85d99691f8a2e1c5aa73101259f3b` |
| `review-request.md` | `6d9eaacef7691b2f1812a241d2e2b90510f4be248a7051ddd15cceab942e9a7c` |
| `source/tests/test_automatic_frontend.js` | `a251f956da950de92a2b519e53322df97e0ee894cebd8f047db7251fdf2bdc59` |

Independent full source walk:15 ordinary single-link files, digest `669918707102a28162517b359c3cb10d122d5b94a4dd48c2be8a73c6a4db5a41`, exactly matching plan. The sole source change is one assertion in test_automatic_frontend: exact approved pending acknowledgement replaces the stale Starting substring. Subsequent failure-state and stale-reply assertions remain intact. All production app/picker/markup/style and other tests are byte-identical to UI-1. Runtime47 files and ownership92 files independently match the established `a3cb3b5e0903b98e3a9e4865321a199eb6f4f53f5739be509bd61d50bbacb031` and `a1629fdbc1c73fac1fabd64db245bdd2a12dafe8b93891acce9647dc163f52ad` trees. All seven explicit pins match;24 ancestors are ordinary non-symlink directories. Work is empty and all28 formerly named result paths are absent; this driver can create only seven.

The driver now compares the entire two-entry declaration, including exact argv/completion values, against a literal constant. Entry1 is installed Node with --test-reporter=tap followed by the absolute frozen desktop-folder-picker.test.mjs path; entry2 is the same Node with only the absolute test_automatic_frontend.js path. TAP is the built-in formatter, not a custom reporter module, npm invocation or --test isolation request. No reporter destination or extra file output is supplied. Node/supervisor/test graph and actual fake-dialog/DOM/fetch source are unchanged. No actual app/browser/dialog/network/media or filesystem mutation path is added.

No marker comparison is waived. Picker still requires tests8/pass8/fail0/skipped0 plus result.ok and normal closure. Automatic still requires its final PASS and successful exit after all assertions. Two entries replace nine consistently in the exact list and final summary length; no stale nine-entry executable loop remains. Any normal assertion failure persists in the summary and prevents success; uncertain, forced or timed-out closure stops before the next entry. Strict supervisor byte comparison, all existing helper/Job closure rules and postflight remain unchanged.

**Minor documentation finding:** native-graph.outputs retains the old text01..09. It does not drive execution. Actual pinned driver, plan.tests and entryCount permit only01/02 result/log trios plus summary.json. Any eventual admission is limited to these seven leaves; the stale prose grants no03..09 output or extra-entry authority. No frozen package edit is required for this safety decision; preserve its hashes and record the discrepancy.

Outer invocation retains one600000ms deadline, hidden no-shell installed Node, literal five-key environment with ui-2/work temporary paths,2MiB controller output cap and SIGKILL. Each existing runOwned call receives only the remaining whole budget minus10000ms reserve, with16MiB output bound and unchanged pinned Koffi. Summary is intentionally updated within this one prospective invocation, and final complete:true/ok:true follows both entries and full postflight. Required acceptance remains outer0, both markers/exit0, complete unchanged source/runtime/ownership/helper postflight, and each receipt ok/closed/outputComplete true with no force/timeout/overflow/truncation/closureError plus native complete/zero and active0/unsignaled0. No replay, extra tests, geometry or release clearance.

Owner has confirmed source/artifact freeze through eventual closure. Lead was asked for explicit new UI-2/shared Node/helper/runtime/Koffi/executable/ancestor freeze and no-concurrent-run confirmation; that response is outstanding at this record. Once recorded, executor must immediately recheck the three artifact hashes, empty work and seven absent output leaves before one exact invocation. Until then, hold this package. Reviewer ran no tests or app.

### UI-2 freeze condition satisfied — 2026-11-01

**Bounded execution verdict:** ADMITTED FOR ONE EXACT `ui/ui-2` INVOCATION. This supersedes only the pending-freeze hold above; every recorded pin, limit and Minor documentation finding remains.

Lead explicitly confirmed no owned test run active, UI-2 source/artifacts and shared Node/helper/runtime/Koffi inputs and ancestors frozen through this one closure, and no build/provisioning/other run during it. Owner freeze was already recorded. Reviewer then independently rehashed driver `d6eba00b31a94036a908901474fbeaaaa75babbef13e9ea8456eeb0c58d1479d`, plan `6eb0015b5f080475793d963efdabe6c1ebeb440bc71893722e306d6e7a1f52d0`, invocation `9872966edafab15da81cb358d9e474d0525388a68c945ccb645787cd41cdfbeb`, all seven explicit shared/graph pins, complete15-source/47-runtime/92-ownership trees and24 ordinary ancestors. All still match the preceding record. Work remains empty; all seven actual output leaves and the unused03..09 names remain absent.

Executor must repeat the immediate three-hash/fresh-output check, then run this exact two-entry invocation once. Only01/02 result/log trios and summary.json are authorized outputs. All prior strict markers/exit/closure/postflight acceptance conditions remain. No replay, integrated backend package, browser/geometry or release admission is implied.

## Concrete backend-1 integrated engineering package — 2026-11-01

**Bounded execution verdict:** ADMITTED FOR ONE EXACT `backend-1` INVOCATION.

Directory: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/backend-1`. This certifies the exact frozen execution graph below for one targeted engineering run. It is not the canonical clean-HEAD full entry, accumulated release review or product test-pass verdict. Reviewer executed no tests, app, media or fixture commands. UI-2 accepted closure was reported by lead before this package, with no concurrent owned run.

| Exact artifact | Independently verified SHA-256 |
| --- | --- |
| `driver.mjs` | `f9b5f4df64c694d58bb2ab30e83e920a48e73ae6b33bac488aab3b37dcf1ad1a` |
| `plan.json` | `d204237f3c24db3ae856cf045987a8d6dc2d0178d2b9c3c46b807d55744b2430` |
| `invocation.json` | `20823c0b3b7ecd1667a813319e7c89d8924371d3f047481056d0e695ca5b964c` |
| `run-targeted.py` | `025178a3ce72d4cbedbea8b18b6947cf6556a7218cdde19a44e00b59d63d4c23` |
| `review-request.md` | `971d06e39d30faa50aa18828b7350d7150b91f1396f47b4a01af5c027b65c671` |

Independent full walk:102 ordinary single-link source files exactly match plan, digest `63f51166ebd8a211e39219d4aa8b78aa7fad342535ba6520c97f1b8407cbfc91`. This includes95 root Python modules, six exact test modules and sorted_fixture. Complete runtime47 and ownership92 trees match `a3cb3b5e0903b98e3a9e4865321a199eb6f4f53f5739be509bd61d50bbacb031` and `a1629fdbc1c73fac1fabd64db245bdd2a12dafe8b93891acce9647dc163f52ad`. All eight explicit Node/helper/manifest/runner/cmd pins match. Twenty-five relevant ancestors are ordinary non-symlink directories. Work is empty and owned-result.json/stdout.log/stderr.log are absent.

### Fixed cases, import order and output contract

Independent source method counts match: test_start_over32, test_restart_24217, test_backend_24227, test_integration_2429, test_cleanup_24218, test_source_folders44, total147. The fixed runner loads and completes the standalone Start over32 before loading any other test module. Its production imports are expected; no other test module is preloaded. The waiting-worker monkeypatches are registered with unittest cleanup, and the captured REAL_WORK points to production code before those patches. Remaining modules then load as one fixed115-case suite. Both suite counts are checked before running and actual counts/success/no skips are required at final exit. An import failure, skip, unexpected count or either suite failure remains nonzero.

The runner explicitly sets both Python text streams to ASCII/backslashreplace before test imports and emits the same reviewed escaped Unicode marker on both. The environment retains PYTHONIOENCODING=utf-8, which isolated -I Python ignores; safety and exact bytes rely on the explicit reconfigure calls. Driver requires both ASCII markers and exact standalone=32/integrated=115/total=147 completion line, while unchanged supervisor raw-chunk/final-byte comparison and result.ok still decide successful output/exit. No diagnostic filtering or failed-status waiver is added.

### Actual reached graph and private boundaries

Reviewed the new restart/backend/integration tests, standalone Start over setup, worker/quit and route paths, import-time effect sites, newly added helper modules, and affected production consumers. All real catalogs and tiny synthetic files are rooted below snapshot source/scratch in unique TemporaryDirectory cases; cleanup tests retain their previously reviewed private fixture layout. No injected path denotes a real library. Root95 modules are present for consistent imports; their mere presence does not authorize unrelated entry points. The only import-time file-content read identified in this graph is the preservation-module hash over the frozen source file itself.

Start over constructs AudioJobs without a conversion runner; its constructor creates/recover-checks only the private ledger and does not start pending work. MergeService is built with __new__, private inventory and review doubles; repair checks are patched. AutomaticProcessing receives an explicit research stub and its normal work loop is replaced with a bounded waiting worker. The one intentionally exercised REAL_WORK branch starts at a private saved research checkpoint: no candidate listing, queued conversion or discovery is available, and the sole requeued book lookup raises the expected missing-row ValueError before research or media work. Pending workers use private events with bounded waits/joins.

The DesktopControl quit case controls only the supplied in-memory server double and those private coordinator threads. finish_shutdown is a Mock, inventory.stop is a stub, and exit_bound is None, so neither real server shutdown nor os._exit is armed. This is not live desktop/app control. HTTP route tests instantiate Handler/BrowserServer with __new__, io.BytesIO request data and a response callback; no socket constructor, bind/listen or serve loop runs.

Restart refresh creates only its synthetic two-member source set, passes an explicit mock metadata reader to Inventory and exercises native DirectoryBoundary/VerifiedFile on those exact private members. No scanner worker or codec is launched; database currentness/refresh commits remain private. Source edits are test-authored changes to tiny generated bytes, not snapshot Python or original media.

Backend approval/grouping/shared-peer/diagnostic tests use private SQLite or in-memory data; research identity/approval and packet/chapter verification seams are mocks. Shared routing consumers do not instantiate a provider. Published-verifier cases deliberately start private in-process verifier threads, but output_current is replaced with deterministic functions; fictitious output paths are never opened. Page-cache concurrency uses bounded events and caller threads only.

Integration cases call queued-admission handling through a SimpleNamespace with mocked approve_book, pure typed-failure copying, currentness checks and routing planners. The audio-stage mapping case patches create_private and forces the destination check false, so no in-place session is created; its mock raises before any publication path. Joined chapter fingerprints operate on dictionaries/hashes, with recording-suffix seams patched, not on media. New admission_diagnostics/pause_state operate solely on supplied database handles; reviewed_routing uses pure proof checks/deep copies. The storage_cleanup delta since cleanup-2 only adds a bounded retained-details SELECT.

The unchanged18 cleanup/44 source-folder test bodies retain their prior private deletion, hardlink, junction and alternate-stream fixtures. Sole extra executable remains pinned cmd.exe `ccd79a7568ea9240ccd6fe124807b9d3e4dbc3a4cf92954299ac3029f4a91d02`, exact /d /c mklink /J with two generated private paths, CREATE_NO_WINDOW and10s timeout, inherited outer Job. Fixed arguments have no shell metacharacters or user inputs; /d disables AutoRun. No other subprocess follows Python. Python/FFmpeg paths in PATH do not authorize media execution; all reached media/provider calls are stubbed. There is no actual app, browser, window, tray, audio playback, live/Z: data access, installation or network graph.

### Ownership, deadline and one-shot acceptance

Controller/owned-supervisor structure remains cleanup-2 plus the reviewed chapters-3 explicit diagnostic contract. Fixed hidden no-shell cp.execFile launches pinned installed Node with one absolute driver argument, studio cwd and literal seven-key environment. Outer600000ms covers startup/preflight/work/postflight/closure; unchanged runOwned receives only remaining time after preflight minus10000ms reserve, pinned Python -I -B and16MiB output cap. Ownership is established before supervisor work release and inherited by Python/cmd. Trusted Node/OS/Koffi bootstrap and operational namespace freeze remain explicit limitations.

Source scratch fixtures are permitted only as generated per-case data; teardown must remove their files or the complete source postflight fails. Default writes to the three evidence leaves are authorized only for this fresh invocation. Lead explicitly confirmed all snapshot/shared helper/runtime/Koffi/Node/cmd inputs and ancestors frozen through closure, no concurrent owned run/build/provision, and no execution before admission. Executor must immediately recheck the three exact artifact hashes and absent output leaves, then launch once.

Acceptance requires all147 successful/no-skip cases in32+115 order, both escaped diagnostic markers and exact count line, outer0, unchanged full postflight, helper ok/closed/outputComplete true, no force/timeout/overflow/truncation/closureError and native complete/zero with active/assigned/listed/unsignaled0. Any failure or uncertain closure is retained and stopped; no replay or broad graph fallback. This admission does not cover the separate browser/geometry proposal or any future package/release.

## Concrete geometry-1 headless package — 2026-11-01

**Bounded execution verdict:** NOT ADMITTED. STOP this exact package. No browser/holder/relay/native monitor/test was executed by reviewer, and no launch was authorized. This is a process-contract decision, not a release verdict.

Directory: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/ui/geometry-1`. Independently verified package hashes: plan `f38aa70f34ebf616fc6e86649680205c8310bd60e19ab84dfa75dd5f2c6384e9`; driver `acaa3cb472c3702672abfac1a88f7c68f0de465d61d5e90c78c86b99c07fbdbe`; invocation `c1b4c298b3f2f4a7197d453333f31ac9bb6e6ebfdb68d635a3d3643956883486`; graph `6d21b574dee5d3608587e95ba86e929698495ea3feec96dcf28a0d110ae3c8f1`; request `b9d1edd90731179fc58333e124d8611844999ba7141288ce23916c832619541f`. Read the actual runner/input checks/window monitor and relevant complete ownership, launch, policy/read-back and close paths. Core helper/holder/runner bytes matched their supplied pins.

### Blocking contract gaps

1. **Declared outer-Job escape does not match code.** native-graph.processEdges says the PowerShell relay uses a parent-process handle to escape the outer Node Job. Pinned headless-holder.ps1 lines90–122 sets only PROC_THREAD_ATTRIBUTE_HANDLE_LIST for three stdio handles. Its CreateProcessW uses EXTENDED_STARTUPINFO_PRESENT | CREATE_NO_WINDOW, with neither a parent-process attribute nor CREATE_BREAKAWAY_FROM_JOB. The comments rely on Node/libuv SILENT_BREAKAWAY behavior, while the exact enclosing bounded-check.mjs createPrivateJob lines59–61 sets only0x2000 KILL_ON_JOB_CLOSE and explicitly grants no breakaway permission. No actual exact nested-job membership evidence was supplied. The reviewer cannot certify the requested independent-holder graph from that mismatched contract, nor silently substitute a different ownership topology.

2. **Unknown process verification can become reported zero.** In unchanged headless-browser.mjs killRounds lines329–353, remaining starts empty and verified=false. Failed snapshot calls are caught and the loop continues. If all queries fail, it returns remaining:[] with verified:false/last:null. stopLease lines1046–1058 discards verified/last and reports remaining:0. geometry-runner accepts closure.reason===stop-requested and remaining===0 without a separately successful final process verification. Additionally, headless-holder.ps1 lines254–284 catches a straggler query error and can subsequently emit stragglers=0. Thus the declared independent/breakaway graph lacks a fail-closed final external-tree closure proof. Outer runOwned native zero cannot be used as proof of processes claimed to be outside that Job. Unknown closure must remain failure; no comparison/guard waiver is authorized.

The package also relies on holder TTL/owner death for independent lifetime control, while subsequent CIM/PowerShell cleanup is not shown bounded by the outer Job under its claimed topology. The two concrete gaps above must be resolved before claiming that600000ms covers the entire declared lifecycle. This review does not design or authorize a new launcher, breakaway path, process sweep or helper modification. Owner was asked for existing exact reviewed evidence; absent such evidence, the package stays stopped. Any correction must be a fresh concrete review.

Lead and owner confirmed input/shared-runtime freeze and no active owned run, but freeze does not resolve these process-accounting gaps. The supplied927-file installed Edge content/identity manifest and160-frame geometry intent remain proposed, not an executed or admitted browser route. Review stopped at the blocking contract findings before completing independent927-file browser-tree verification; no full browser-input clearance is claimed. Headless frame/network isolation and read-only window metadata observation were inspected but are not separately cleared for execution. Existing read-only top-level personal-folder/drive-root metadata inventory authorization does not authorize live content reads or writes. All prior private-output, no actual app/tray/input/focus/installation and no replay constraints remain.

Core relevant pins: headless-browser.mjs `ef3ce1bb44c2e142d37e3695eb2e2915ef0d1cdaa62f025f577c753ad17797c5`; headless-holder.ps1 `14e5122340974402fa32b581f21b3f87c770fd68353eb061cea70f383813aa9d`; headless-procs.ps1 `e3607650242d9ae34d6bb8f522efe748e9e3e88ab002300f4f5f62d14a2f8ef4`; copied holder DLL `405de5709fbde4206f5d5b5f2ae9d1c1834b01b45685fe5f55e46f22635a37b7`; geometry-runner `4d6542f948a1b8f2dfb62f991835c7c1a990ab8671aba690a13220811551866f`. Prior engineering package admissions do not extend to this different process graph.


## Concrete backend-3 corrected integration package — 2026-11-01

**Bounded execution verdict:** ADMITTED for one fresh unchanged backend-3 invocation only, subject to the immediate pins/output-absence checks and continuing operational freeze below. No test or package process was executed by reviewer. This is not a release verdict or a successful-test claim.

### Prior evidence and exact identity

Lead reported backend-1 NOT ACCEPTED: all147 cases ran, with failures/errors in both32 and115 phases. Native closure was complete/zero without force or timeout, but postflight correctly rejected a leftover private catalog from the failed Quit fixture. Preserve its whole evidence; no replay or postflight waiver. Backend-2 was withdrawn unexecuted after its new names-save fixture omitted the real enqueue prerequisite source.fingerprint. Review covers backend-3 only; its correction preserves that production guard. Geometry-1 remains NOT ADMITTED and unlaunched, so no geometry closure is outstanding before this separate backend invocation. The geometry owner independently confirmed both recorded source findings; no revised browser route is cleared here.

Directory: C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/backend-3. Independently read/hashed actual files:

| Artifact | SHA-256 |
|---|---|
| driver.mjs | 77a6ef1a3a5fd8e35178b74dbc1c3b0744bbb8ec0fb6c4fbbb761267759f5419 |
| plan.json | a6f2a847d2462e215c5ea5b08678ab3e9edf4d840f73590bf1c429838a832539 |
| invocation.json | cffcd7aab40e0fc90128c0ae857e454650b3c9da7069cda55a1f59e5ae825db9 |
| run-targeted.py | 5c236f75e4b9723fe5ffe78ca8985625da19dde3c002e4158c35f08207b76a4d |
| review-request.md | 01f5d9ebe33aaa19646347a4998f49c1e6472e63c7f200cc9ad20e3972550df6 |
| read-only-preflight.json | ed0884a08f1ea72faa61009bbfb0d188735514b4b96cd846e511276fb9f0329b |

Reviewer independently walked all102 source files and matched their complete path/hash manifest: tree20d3d6402641c3cab369ab026ec916aa6894b9f9ac66839d6758813b2a9b1d2a. All47 runtime files rehashed to a3cb3b5e0903b98e3a9e4865321a199eb6f4f53f5739be509bd61d50bbacb031; all92 ownership files rehashed to a1629fdbc1c73fac1fabd64db245bdd2a12dafe8b93891acce9647dc163f52ad. Walked entries were ordinary, source/runtime/ownership files single-link;26 relevant ancestors were ordinary directories without symbolic links. All eight explicit Node/checker/child/manifest-helper/runtime-manifest/ownership-manifest/runner/cmd pins matched. Work was empty and owned-result.json/stdout.log/stderr.log were absent at review.

Unchanged installed Node pin14319838b3f355e0398c13569a90270bce4fc68f25189f58c59b03dadae0e6d5; bounded-check45510f11a011b617b4831994bd40aa87763d4195cd06c97ee6489af45f91bce6; bounded-child240a6a96a32f08989439387d5d6ab75d17e1bcf243863d31d2ff7287f68d1e42; qa-entry-context ee295f2d834ce1a1cbb00c6895180e32425734fdf25d220b93ea36a7e99e045f; runtime manifest2b4a13a73868ccbc88329747156682be62576f054683252b4b72ad9b3fa192a6; ownership manifest122eca8f1ad057bd86867f8e302c60fcaa5b6dba5ff4e660cfd860cf40769617; cmd.exe ccd79a7568ea9240ccd6fe124807b9d3e4dbc3a4cf92954299ac3029f4a91d02.

### Reviewed delta and reached graph

Exactly eight source files differ from backend-1: automatic_processing.py, merge_service.py, organization.py and tests/test_backend_242.py, test_cleanup_242.py, test_integration_242.py, test_restart_242.py, test_start_over.py. All were read as concrete diffs. Remaining source bytes match the prior reviewed graph. No additional executable, app endpoint, media probe, socket, browser or network client is reached.

Runner first imports/runs only32 standalone Start over tests to completion, then imports17 restart,28 backend,14 integration,19 cleanup and44 source-folder cases (122); static method counts match154. It requires exact counts, both successful results and zero skips. Driver changes from backend-1 are only exact root/schema/plan pin and154/count-line substitutions. Explicit ASCII/backslashreplace reconfiguration and known escaped Unicode marker on both streams precede test imports; unchanged supervisor strict byte comparison and failure status remain required.

Quit fixture now awaits its real private asynchronous stop event, asserts final exiting state and joins the private control thread before database/temp cleanup even after assertion failure. Server finish_shutdown remains a Mock; no actual desktop/app or server is operated. Combined-start assertions verify the exact new restart authority and loss of old choices, rather than deleting the assertion. Restart/Queen fixtures supply actual audio-profile prerequisites to real grouping; the added negative case proves identity does not waive a missing profile. No grouping or native proof guard was relaxed. Maintenance tests create/close only their private SQLite title record under source/scratch and check actual scheduled-owner/pause retry semantics.

New integration policy cases operate on dictionaries/hashes and pure destination planning. The producer test patches source digest, supplies a stub chapter-plan callback and empty job list, so its fictitious C:/private paths are not opened. Legacy absent-policy and explicit joined-chapters-v1 behavior are distinguished; unknown policy and downgrade are rejected. The names Save case creates a fresh private SQLite catalog and UUID manifests, including the required source fingerprint. Real AudioJobs constructor/enqueue only initialize/recover the empty private ledger and enqueue rows; neither starts a worker. Real names_save/_names_replan and entered_names/book_restart transactions stay in that catalog; research/requeue/request_start/press callbacks are supplied doubles. Assertions cover the newly entered title, exact approval hold, selected job set-aside and unchanged unrelated job. No audio file is opened or produced.

All prior cleanup/source-folder private native fixtures and sole cmd.exe /d /c mklink /J descendant remain unchanged: fixed generated paths, CREATE_NO_WINDOW,10s timeout and inherited owned Job. No original media/live catalog/Z content access, live writes, app/tray/picker/focus/input control or installation is included.

The separately authorized scripts/qa/headless-browser.mjs edit and new pure closure test are absent from backend-3 source/runtime/ownership manifests and all explicit pins; driver/checker/child/manifest-helper contain no reference to that wrapper. Their separate source edit is not an execution clearance and must not alter this batch's shared frozen Node/helper/runtime/Koffi inputs.

### One-shot limits and acceptance

Lead explicitly confirmed batch/shared inputs and relevant ancestors frozen through closure with no active owned run. Freeze is operational, not a claim of native immutability. Executor must immediately recheck the exact driver/plan/invocation hashes and all three absent evidence leaves, then use invocation.json unchanged once. No reuse/overwrite/replay authority is granted.

Pinned installed Node is the trusted hidden fixed bootstrap, no shell, one absolute driver argument, studio cwd and literal seven-key environment. Outer600000ms covers startup, preflight, work, postflight and closure; unchanged runOwned owns the inert supervisor before work release, then Python -I -B and its inherited cmd descendant. Inner budget is only remaining time after preflight minus10000ms reserve, at most590000ms, with16MiB output cap. No helper/guard/admission/launcher changes are part of this contract.

Acceptance requires all154 successful/no-skip cases in32+122 order, exact backend-3 count line and both escaped ASCII markers, outer0, full unchanged source/runtime/ownership/helper postflight, helper ok/closed/outputComplete true, no forced/timedOut/overflow/truncation/closureError, and native complete/zero with active/assigned/listed/unsignaled0. Scratch fixture files left behind must still fail full source postflight. Any failed check, timeout or uncertain closure stops this invocation and preserves evidence. No waiver, automatic replay, broader batch or release clearance follows.


## Concrete backend-4 narrow fixture correction — 2026-11-01

**Bounded execution verdict:** ADMITTED for one fresh unchanged14-case integration invocation only. Reviewer executed no tests. No release clearance or test-success claim.

Lead reported backend-3 NOT ACCEPTED overall: standalone32 passed; remaining122 produced one error at the new fixture's incorrect book_values()['title']['value'] assertion. All other cases passed. Full source/runtime/helper postflight passed, with normal native complete-zero closure, retained6,2054 complete queries, no force/timeout and32.715s elapsed. Its failure evidence stays preserved; no broad154-case replay is authorized.

Backend-4 directory: C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/backend-4. Independently verified actual pins:

| Artifact | SHA-256 |
|---|---|
| driver.mjs | 4ba572e72859180c863b4e2c709038a69cc2b2bfa959fc15d42abbbd2384d2e8 |
| plan.json | 0922623859c4cd25d41567a4fdd233d558f7eaf2f58e2ec5497ed4441cdd408f |
| invocation.json | e8de05957faf8cc51d19d75be294d4b013eface2aef079f52d30ba0d4f98d949 |
| run-targeted.py | 2d3ec07ed58b31a79b030721e57a0eb3eb6ca643cca12dc12ec2f2c27c1aaa56 |
| review-request.md | da5d77fdb536e11f8446dc085b33fe6752b99cae7072f63fef381d565e1a98a1 |

All96 source files were independently walked/hashed against the exact manifest, tree20d14388648780ca0d1132bb5af32170db775148fb9e0b5d9602593b536666cf. All95 root Python files are byte-identical to backend-3; sole changed source is tests/test_integration_242.py. Full47-runtime and92-ownership trees rehashed unchanged to a3cb3b5e0903b98e3a9e4865321a199eb6f4f53f5739be509bd61d50bbacb031 and a1629fdbc1c73fac1fabd64db245bdd2a12dafe8b93891acce9647dc163f52ad. All seven explicit pins matched, using the already recorded unchanged Node/checker/child/manifest-helper/runtime-manifest/ownership-manifest pins and this exact runner. Files were ordinary/single-link and24 relevant ancestors ordinary without symbolic links. Work empty; owned-result.json, stdout.log, stderr.log absent at review.

Actual two-line fixture delta reviewed against production APIs: entered_names.book_values returns field-to-stored-value, so the exact saved title is asserted as a string. The _names_state double now maps those stored values to its effective-name field-to-{value} shape. It does not change real Save/SQLite/job-setaside/hold transaction calls or weaken exact title equality, revision/fingerprint hold context, held reason, selected-job state or unrelated-job unchanged assertions. The complete module's standalone import/reached paths were checked; no reliance on another test module's setup is introduced.

Runner imports only test_integration_242, requires14 cases before running, requires14 successful/no-skip results afterwards and prints exact backend-4 counts: integrated=14 total=14. Static method count is14. Driver delta only narrows module/count and substitutes root/schema/pins. Explicit pre-import ASCII/backslashreplace and both escaped Unicode markers remain, with strict unchanged supervisor byte comparison. All other accepted backend-3 modules are excluded from this invocation.

Graph is narrower than backend-3: fixed trusted installed Node bootstrap -> owned inert supervisor -> isolated Python; no executable descendant after Python. No cmd/mklink cases remain. New names fixture uses only the private generated SQLite catalog under source/scratch, no worker start; callbacks remain doubles. Other14-module paths are the prior reviewed pure planning/mock-admission cases. No media file access, actual app/browser/socket/network, live catalog/Z writes, installation, input/focus/tray or native picker operations are authorized.

Lead explicitly confirmed batch/shared inputs and ancestors frozen through closure, no active run. Executor must immediately recheck these exact driver/plan/invocation hashes and three absent output leaves, then execute invocation.json unchanged once. Fixed hidden no-shell installed Node, literal environment, outer600000ms and remaining inner budget minus10000ms reserve (maximum590000), Python -I -B,16MiB helper output and unchanged ownership-before-work contract remain. Full source/runtime/ownership/helper postflight is mandatory; leftover generated fixture files still fail it.

Acceptance requires exact14 all-pass/no-skip count line, both ASCII markers, outer0, unchanged full postflight, ok/closed/outputComplete true, no forced/timedOut/overflow/truncation/closureError, and native complete/zero with active/assigned/listed/unsignaled0. Any failure stops and preserves evidence; no replay or overwrite. Geometry-1 remains NOT ADMITTED. This fixture-only admission does not admit the separate headless helper tests, a browser route, any future batch or release.


### Backend-4 execution receipt reported by lead

Lead reported the exact admitted backend-4 invocation accepted:14 cases/no skips in0.137s; exact count line and both ASCII markers; outer0 and complete source/runtime/helper postflight. Normal native complete/zero with active/assigned/listed/unsignaled0, retained4,49 queries with none incomplete, no force/timeout; enclosing1.305s. No active run remained. Product95-file bytes stayed identical to backend-3. This narrow successful correction supplements retained backend-3 evidence; backend-3 itself remains an unsuccessful aggregate receipt. Reviewer did not execute either package.

## Root headless closure correction and closure-1 pure package — 2026-11-01

**Bounded patch review:** no open blocking finding in this exact root change. **Bounded execution verdict:** ADMITTED for one fresh unchanged closure-1 pure17-case invocation only. This does not admit a browser launch or certify the Books Arranger release. Actual test results are still required before the parent treats this patch as validated.

### Exact reviewed patch and consumer behavior

Reviewed actual root wrapper diff from blob SHA-256 ef3ce1bb44c2e142d37e3695eb2e2915ef0d1cdaa62f025f577c753ad17797c5 to ea1ba51c67545b315456da0b70376fbaf6b4a28029e0da2d251469c3c98bb1c1. Root git HEAD wrapper bytes independently matched the former pin; actual diff content matched supplied wrapper.patch2f3331b19ab977533dd5e16a4e3e207220449b3c61fdd8c57fe8bcce5fd3ec37. New deterministic test file SHA-256 ac83224cadcbc9abeceb3039fff97e685c1b7aebb98be460517551e7b21bd460; consumer report Team/Docs/BooksArranger_0242_HeadlessClosure_2026-11-01.md SHA-25658d64d72e9167aad388eb9dd37b063237393f76dcbd44549865d861ce223544b. These are the parent's three authorized root files; reviewer changed none of them.

Latest snapshot failure now invalidates killRounds.verified and last, retaining any previous remaining array only as last-known diagnostic data. No new kill occurs on that failed-query branch. Successful final empty listing retains verified zero; known surviving targets retain a nonzero result. A thrown planner/initial-query error propagates as failure rather than a manufactured success.

stopLease preserves verify:false or query failure as verified:false/remaining:null and gates lease deletion on verified empty. close propagates validity. Launch failure paths retain the comparison snapshot and avoid the ended claim when closure is unconfirmed. CLI run/stop and both --kill sweep forms require verified empty for success; uncertain closure cannot be hidden by an independent allow-personal refusal. Text reports unknown/closure-not-confirmed and JSON exposes validity. Snapshot deletion after stop requires verified empty; personal-folder comparison remains list-only and does not determine exit status.

sweepLeases returns before cleanup after a failed final query; the unqueried onlyIfDead fast path no longer purges recovery folders/snapshots. With a verified listing it retains prior per-lease cleanup decisions. sweepProfileRoot retains its array/verified shape and propagates invalidity. Reviewed unchanged .claude/hooks/headless-reaper.mjs: it consumes remaining/killed/removed arrays for informational logging and performs no additional cleanup based on their length; its always-zero hook exit is not a closure proof. Array compatibility is preserved. Existing mixed native headless-browser.test.mjs remains outside this test admission. The CLI run/launch failure/close propagation paths were reviewed statically; the17 pure cases do not exercise a real launch.

No process selection, target scope, kill order, Job flag, timeout, holder PS/DLL, global guard or admission check was changed. Added snapshot/killFn seams are optional imported-function parameters, defaulting to the existing native behavior, with no CLI bypass option. A future geometry consumer must explicitly require verified zero and outer native complete/zero under a truthful nested-ownership contract; the previously rejected geometry-1 stays unlaunched/not admitted.

**Minor — test-boundary wording:** the package says all child_process launch exports are intercepted. The actual test intercepts spawn, spawnSync, exec, execSync, execFile, execFileSync and process.kill; fork is not intercepted. Current exact source has no fork call/import path, and the wrapper/entry-identity reachable process imports are covered, so this does not block the frozen graph. This review does not certify the guard as a general process sandbox or cover future added launch paths. Owner was notified; no source change or package churn is required for this exact admission.

### Concrete pure graph and integrity

Directory: C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-20261101-242/shared/headless-closure/closure-1.

| Artifact | Independently verified SHA-256 |
|---|---|
| plan.json | 663324841bf19880b33a87b10bd9b24517c8d36d1c293fa1097cb46611d25b13 |
| driver.mjs | 793fdc8c761d510ff9c87ff54b93385d33d5314c920f367e760f267e3c9fc28a |
| invocation.json | ab7347136dc9707270f9346b5bc44f44e65d38f1dd3b7285c4178365981a578c |
| native-graph.json | 8e4d4c8845ce175e74d233a6eaed71bab381544fe456c08a81f75ae4d1be33e5 |
| review-request.md | 0d0ad8eb956e214d8e26b40d40c23bdac90f6dda997a1effc121f6ab279334f3 |

All three source files independently rehashed to tree3eedffbee61efdb5c3d75a93c2753eab4727b959bd91e742e3f030745a5b54cf and matched corresponding root bytes: changed wrapper, new test and unchanged entry-identity.mjs b36b7b52f7c95868c79c494fbc629d5790886426669a8dbdda236248ba7e9856. Full47-runtime/92-ownership trees rehashed to unchanged a3cb3b5e0903b98e3a9e4865321a199eb6f4f53f5739be509bd61d50bbacb031 / a1629fdbc1c73fac1fabd64db245bdd2a12dafe8b93891acce9647dc163f52ad. Seven explicit Node/checker/child/manifest-helper/runtime-manifest/ownership-manifest/graph pins matched. All walked files ordinary/single-link;25 relevant ancestors ordinary without symbolic links. Work empty; owned-result-01.json, stdout-01.log, stderr-01.log and summary.json absent.

Single fixed installed Node test entry scripts/qa/headless-browser-closure.test.mjs, direct execution without test-runner process isolation. Before dynamic wrapper import, child-scoped reachable launch functions and process.kill become throwing, attempt-recording doubles; built-in ESM exports are synchronized. Tests call exported killRounds/stop/sweep/CLI using synthetic snapshots and kill callbacks. The known personal snapshot is explicitly notChecked and returns without real personal-folder inventory. Import-time CLI guards remain inactive. No actual PowerShell, CIM, browser, network, OS termination, window query, app, media or native picker is reached.

All generated lease/recovery/JSON stand-ins are under the explicit absolute HB_CLOSURE_FIXTURES=<batch>/work/fixtures, checked beneath literal private TEMP and required absent before creation. Root validation/deletion touches only these generated private leaves. Assertions preserve unrelated sibling files and uncertain recovery evidence.17 fixed cases cover failed/latest/recovered process observations, known survivors, explicit no-verification, cleanup refusal, successful private cleanup, CLI JSON/text/refusal status and sweep compatibility. Static17-call count matched. Each failed case is retained as a failure, not skipped; unexpected attempts cause failure. Restoration of built-ins is child-local and happens after awaited cases; no background task or launch is scheduled.

### One-shot execution limits

Owner and lead explicitly confirmed snapshot/artifacts/shared Node/checker/child/runtime/Koffi inputs and relevant ancestors frozen through closure, no active run/build/provision/concurrent execution. Executor immediately rechecks driver/plan/invocation hashes and all four absent evidence leaves, then uses invocation.json unchanged once. Source/output freeze is operational, not native immutability. No replay or overwrite.

Graph: trusted fixed hidden installed Node driver -> inert owned Node supervisor -> direct Node test; no further executable descendants. Existing runOwned establishes ownership before work release. Fixed no-shell argv/cwd and literal seven-key env include private TEMP/TMP/HB_CLOSURE_FIXTURES; installed Node pin remains14319838b3f355e0398c13569a90270bce4fc68f25189f58c59b03dadae0e6d5. Outer600000ms covers startup/preflight/test/native closure/postflight; inner remaining time subtracts elapsed preflight and10000ms reserve, at most590000ms; helper output cap16MiB. No new launcher/guardian operation or helper mutation.

Acceptance:17 PASS lines plus exact completion JSON with closure_tests_complete:true, passed:17, failed:0, nativeAttempts:0; outer0 and final summary complete/ok true; unchanged full source/runtime/ownership/helper/graph postflight; helper ok/closed/outputComplete true, no forced/timedOut/overflow/truncation/closureError and native complete/zero with active/assigned/listed/unsignaled0. Private fixture results/logs remain evidence. Any failure or uncertain closure stops and preserves the package; no automatic retry. Reviewer ran no tests/native processes. Root commit authority remains with Sully after actual positive evidence; no Books Arranger release verdict is supplied.
