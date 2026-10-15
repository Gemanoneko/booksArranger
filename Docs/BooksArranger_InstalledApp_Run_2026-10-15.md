# Books Arranger installed-app run request — 2026-10-15

User authorization: “OK. Run the existing app for now. At least, it will continue conversion”. This permits normal installed v0.15.0 launch and one supported guarded continuation of saved work. It does not authorize candidate installation, manual orphan-record removal, source/hook/trust changes, force killing, migration or changing the paused heartbeat.

> Superseding operational result: the exact stale record was reversibly quarantined after independent review; the normal installed v0.15.0 app was launched. A single supported Start timed out awaiting its reply, but a separate authenticated observation at 09:23:51 UTC confirmed automatic processing Running on the same native owner. A later independently reviewed read-only catalog observation at 09:26:56 UTC found one running audio job with eight pending, and exact native process activity subsequently advanced. The saved audio queue is processing again; no claim is made that its current stage is encoding. Later evidence and cleanup limits are recorded below. Earlier blocked-status findings remain historical.

## Initial result: installed app ownership gate

Senua independently cleared exactly one finite read-only preflight invocation:

~~~powershell
& 'C:/Python314/python.exe' -I -B 'C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/resume-2026-10-15/live-preflight.py'
~~~

The default native PowerShell route actually executed that command once. It exited 1 after approximately 0.453 seconds. A post-invocation clock observation was 2026-10-15 09:09:25 UTC (12:09:25 Asia/Jerusalem); this is not claimed as the exact process-start timestamp.

Canonical app_launcher.verified_owner read the bounded existing ownership record, then Windows OpenProcess for its PID returned error 87. app_launcher.WindowsProcess converted that into ProcessLookupError: 46560. The supported launcher refused with:

> Books Arranger has an old ownership record. Its previous exit needs recovery before a new app can start.

Existing record fields observed statically: application Books Arranger; version 0.15.0; instance 671202f77eabc30ede7655cf9feca31a; PID 46560; port 5210; URL http://127.0.0.1:5210/; closing false; restart_context false; recovery_active true. These file fields are NOT current health/recovery state. Native failure establishes the recorded process was absent at that invocation; no retained live owner or creation FILETIME was obtained. It does not prove every possible owner absent or the port/catalog free.

No app launch, Restart, authenticated Start, Stop, shutdown or live write was performed. No conversion continuation or queue progress is claimed. The helper reached neither authenticated state nor protected completed/checkpoint baseline nor exclusive port/catalog checks because its native owner gate failed first. The URL is the configured address, not verified current service readiness. The record, originals, catalog, recovery sets and unresolved evidence were preserved. This was an application safety refusal, not a P9 command refusal or automatic-approval denial.

## Supported recovery investigation

After the result, Jane explicitly scoped a read-only investigation of an existing supported orphan recovery route. Canonical installed v0.15.0 sources and README were inspected:

- app_launcher.py normal Open and Restart both call verified_owner; a dead recorded PID raises the refusal above. Both launch-web.pyw and restart-web.pyw therefore stop at the same gate.
- web_server.py owned_instance_record uses native CREATE_NEW and refuses any preexisting ownership record. Normal orderly exit disposes only its own continuously held producer bytes after exact native identity/hash/stream checks. Calling its producer context to retire someone else's old record would not be a supported recovery action.
- No canonical recovery CLI/API or orphan-adoption operation was found across the 41 top-level pinned inputs. The historical latest-stable/live_control.py is hardcoded to 0.12.1 and writes prior evidence files; it is not a recovery route and was not executed.
- Historical latest-stable and live-update release-application-recovery folders contain source-application snapshots/proofs, not a live orphan-record repair helper. No safe operational recovery was found there.
- Electron candidate stale-owner handling is unreleased candidate code. It was not applied, installed, imported or adopted for the installed application.

Thus the shipped normal launcher cannot complete this run request while the stale record remains. Existing user launch authorization does not make a manual record deletion/rename or gate bypass valid. Further recovery requires a separately scoped exact native-safe recovery operation or reviewed installed-app correction, including recognized original ownership evidence, native ancestry/identity/bytes, confirmed absence, exclusive port/catalog and preserved protected baseline. No such operation is cleared or executed by this record.

## Source and evidence pins

Finite read-only helper retained at canonical scratch/resume-2026-10-15/live-preflight.py; SHA-256 082c53326712f9da2d916753256c449da9350f010e8159a9e8f6a19d885eda41, 8,096 bytes. It has a total 45,000 ms watchdog, blocks child launch and explicit mutation audit events, performs no POST or launch, and checks 41 canonical input byte pins. Senua reviewed its exact bytes and the pinned Python executable before the sole invocation. Native held source files plus owner verification were scoped only to that read-only operation; no later action inherits its handles or clearance.

- Canonical VERSION reads 0.15.0; VERSION SHA-256 0ebe650ae75c55c17ee49c6d05286fef45fe11783a56d7463f5e28e15b676e1e.
- app_launcher.py SHA-256 9aeceddcfc51435bb3b7b431c8521ec1333f498b5d561097535a2edaaad00af7.
- native_io.py SHA-256 46affe8d8ba8304944c5a2f0e4ad7ca2db79566c40016ab694b366b3dbf5becd.
- web_server.py SHA-256 7950ef9227b0a09f4555d596a0f60b4a83ba7c1a7120b1a78245541af75e08d1.
- C:/Python314/python.exe SHA-256 434b361fe0c5960d404974feed493db47f2603a1ace2574312104fbed0182c6f.

The failed helper is unresolved operational evidence and remains retained. No disposable logs/caches or app output were created; removed files 0, reclaimed bytes 0. The heartbeat remains paused. Installer checks/build/publication blockers remain separate and unchanged.

Ender-owned persistent handoff: this new Docs file only, plus retained ignored scratch helper source. Sully saves the explicit Docs path and pushes immediately after independent static validation. At this initial checkpoint no app had yet been established; the later reviewed recovery and launch below supersede that result.

## Reviewed reversible recovery — completed

Jane subsequently authorized design and execution of an exact reversible orphan-record quarantine after Senua's independent operation-specific review. This superseded the earlier prohibition only for this fixed preserved record; no blanket record deletion/adoption was authorized.

Exact helper scratch/resume-2026-10-15/record-quarantine.py SHA-256 38861984355fb5eb7af398f32b7b2ccbd3623d6a1acbba05aa31eb20e645c398 ran once, exit 0, about 3.749 seconds. Final stdout explicitly reported ok true, phase complete-after-native-release, locks_held false. Its on-disk result receipt deliberately remains ok false / quarantined-pending-release and must be read with that actual final process result; a pre-release receipt alone is not completion evidence.

The shipped startup mutex, exclusive port 5210, exact existing catalog-lock byte range and ordinary native ancestry were retained. The native held stale record was rechecked against fixed recognized bytes, size 232, SHA-256 a6cdbba12ea7893c083c8135868c700c54b90cfa6109c113c53afe5824a0b05d, and fresh recorded-PID absence immediately before a same-handle no-replace same-parent rename. Its exact content, file identity and all filesystem streams were preserved at data/web-instance.orphan-671202f77eabc30ede7655cf9feca31a-20261015.json. No stream contents were inspected, stripped or specially allowed. No bytes were deleted.

Catalog protections verified exact identity/hash preservation through the repair: inventory.sqlite3 451,502,080 bytes, SHA-256 c14b2872fe05167e75677b3d32fe75d38c98241173936385ed313a8cf32ec18b; its journal was an unchanged zero-byte file. No WAL/SHM existed in the protected auxiliary entry set. Catalog-lock bytes remained unchanged. No SQL, catalog, queue, media or recovery mutation occurred in this repair. The operation created only its private evidence files:

- scratch/resume-2026-10-15/record-quarantine-intent-671202f77eabc30ede7655cf9feca31a-20261015.json; SHA-256 d6b493c55d072ea3e8bf3796d600c19fd3bf2e96c02463649ad0f2b81a5e0b2a.
- scratch/resume-2026-10-15/record-quarantine-result-671202f77eabc30ede7655cf9feca31a-20261015.json; SHA-256 5c687404073c6e62549afbb46859b4008433e5aab60851762802de5db44dc2aa.

The quarantine is a 232-byte preserved ownership record. It did not create or consume a 100 GB conversion/recovery set.

## Normal installed launch and readiness — completed

The first separately reviewed Windows Shell.Application COM shortcut action failed with process exit -1073740791, emitting a GoogleDrive shell-extension unavailable-pipe diagnostic. Its success marker was absent. A separate read-only preflight at 09:17:20 UTC established no owner plus positively exclusive free port/catalog. No duplicate launch or success was inferred from the failed COM route.

Jane then authorized the corrected ordinary native Windows shell route; Senua cleared exact normal-launch-native.py SHA-256 68eb819c79f1ced73725067f62dba4ab37d0d4f95b62dc91da820cd8479d947b. It pinned the existing Start-menu shortcut, Pythonw and installed launcher, freshly checked no owner/exclusive port/existing catalog lock, released those gates, then requested exactly one ShellExecuteExW open of the ordinary installed shortcut. No direct detached Pythonw spawn, Explorer fallback, guard bypass or candidate installation was used. Native action exited 0 and returned observation handle PID 54960; shell success was treated only as activation.

Immediate readiness caught startup before publication of its ownership record, with port already bound (WinError 10048). No new launch followed. A separately reviewed bounded observer at 09:21:07 UTC established the real owner and authenticated state:

- Loaded version 0.15.0; C:/Python314/pythonw.exe; PID 54960; native creation FILETIME 134365295749473510; instance 721b890bb723a4b3d22fffb3edf35f1c; configured URL http://127.0.0.1:5210/.
- Actual health/state recovery_active false, no active scan and not stopping. The birth-time ownership record's recovery_active true is not current recovery state.
- Audio Paused with 9 queued, 21 projected completed and 11 fully converted. The summary reported 91 aggregate failure/attention entries; this counter combines audio, source-cleanup and storage attention records, so it is NOT proof that 91 distinct conversions failed.
- Automatic Needs attention with can_start true, preserved historical SQLITE_BUSY failure dated 2026-10-14 08:42:31 UTC, and the supported retry instruction Start automatic processing to retry this book and continue saved work.
- All 22 protected completed database projections matched the prelaunch digest 7773f1d1366bf7fd79843ba856e1c8dfdb07ce65e58e06b49560c2bcb4211989; 112 job manifests and 4 historical automatic error records remained. Saved run 96cbe916-3b2b-4858-b386-89d493cb4f24 checkpoint SHA-256 7b1726492b67f72aacc365c1df38de37702d8948160d41fc60c80435649ad8aa was unchanged.

These are current observations after other chats continued work; the earlier historical 95 queued / 6 finished / 10 published-hold figures remain historical, not a current-state baseline.

## One authorized Start — actual effect established, conversion progress pending

Senua cleared exact start-existing-once.py SHA-256 cf9591b6dc3df8cf3cba37b1ebd75cd02c3b8801c1c5748aa8e0db1d51febeaa. It retained the same owner native handle/generation, checked loaded version/root/library/idle state, protected projection digest and saved checkpoint, then created a durable exclusive per-instance no-repeat intent marker before exactly one authenticated POST /api/automatic/start with empty object.

The POST was sent, but the client timed out after 5 seconds waiting for its reply; helper exited 1 after approximately 8.834 seconds. The marker is intent/reservation, not acceptance evidence. It was never cleared or used to retry the POST. A separately cleared read-only observation at 09:23:51 UTC confirmed the SAME exact native owner and automatic state Running, can_start false / can_stop true, establishing that the requested Start took effect despite the missing HTTP acknowledgement. All 22 protected projection records and the saved 112 manifests / 4 historical errors remained at that observation. Audio was still Paused with 9 queued; no new encoding or converted book is claimed from automatic Running alone.

The source worker resumes saved jobs through normal MergeService.resume, which first checks/prunes completed working/staging under the app's existing rules. That source order is a possible reason for delayed queue activity, not proof of the current blocking phase or actual deletion. A later exact read-only progress observer reached a final authenticated state query timeout and emitted no counter evidence; no progress was fabricated from its unsaved earlier samples. No repeated Start, Stop or restart followed.

The live app is deliberately preserved as the user-authorized running deliverable. Extra working-file cleanup is a separate user-authorized operation owned by the disk-cleanup Ender with Senua review; no broad merge.resume call is labelled isolated working cleanup. Installer/build gates and the paused heartbeat remain unchanged.

## Latest verified continuation and native activity

The disk-cleanup Ender independently ran a Senua-cleared query-only receipt/status snapshot at 2026-10-15 09:26:56 UTC (12:26:56 Asia/Jerusalem), while verifying this same owner. Its audio_jobs state aggregate was 22 completed, 81 needs attention, 8 pending and 1 running (112 total). This supplies evidence that the saved audiobook queue progressed from the earlier Paused summary into an actual running job. It does not identify the book or certify that the current stage is encoding; the broader UI attention count is distinct from raw job state.

One separate native-only observer, scratch/resume-2026-10-15/native-activity-readonly.py SHA-256 9b507cc82a8b7154cda326cee256b06367e39bc5115e97ced8e3cb1e812b6991, ran exactly once with independent clearance, exit 0 in about 3.291 seconds. The retained process handle verified PID 54960, Pythonw image and creation FILETIME 134365295749473510. Across 3.00056 seconds, native process read counters grew by 290,938,706 bytes, writes by 7,770,638 bytes and kernel-plus-user CPU by 1.546875 seconds. These counters establish ongoing process activity, not disk allocation, conversion completion or deleted bytes. They were flushed as separate samples, so no heavy state endpoint could discard the evidence.

Combined result: the installed v0.15.0 app is left running, the single authorized automatic Start took effect, and a saved audio job is running with ongoing native activity. No additional Start, restart, stop, candidate application, source change or heartbeat resume occurred. No new fully completed book is claimed by this short observation.

Working-file eligibility/deletion and its reclaimed-byte/free-space result belong to the separate disk-cleanup record. This app-operation record certifies no independent working/recovery deletion. The old orphan JSON remains preserved at its quarantine path, and all task-created control sources and failure/intent evidence remain retained while their evidence obligations are open. No disposable probes or caches have been silently swept.

Final Ender-owned commit path: Docs/BooksArranger_InstalledApp_Run_2026-10-15.md. The source/runtime and Books canonical main checkout were not edited. Request independent static validation, then Sully's explicit-file commit and immediate push. Keep this running app as the user deliverable.
