# Books Arranger Electron M2 source review — early pin

Reviewer: Senua. Date: 2026-10-13. Frozen range: 57ab44b4583f5b2f55ca3bbb074fe9d8cc6edcf7..7098fbe7297073ef32a3861f348b5a83779252f4. Scope: all committed Electron/setup/update/native host/build/release changes; 56 changed paths, +6801/-47 text lines, binary icon excluded from line counts. Immutable Git blobs only; concurrent CAS/desktop corrections excluded.

## Open findings

### S1 — Critical: actual backend startup never runs its safety callbacks

web_server.py:541 accepts before_start, startup_guard and create_data but lines554–577 use none. Inventory is always constructed immediately after catalog_lock, which creates the data folder. desktop_backend.py passes exact stale-record and catalog-mode guards but they are dead callbacks. A previously configured Existing folder that disappears can silently receive a fresh catalog; a changed/unsupported database bypasses the promised final startup inspection before schema/queue mutation. Unknown stale ownership can refuse only after Inventory construction. Must invoke the explicit mode/data/native/source checks before any creation/schema reset, invoke exact stale-record retirement only under retained catalog ownership, and add real web_server.main entry tests for Existing-missing/unsupported/new/replaced/stale cases. Isolated helper tests do not prove this integration. Ender acknowledged this pin remains blocked and is correcting the missing body.

### S2 — Major: blocked update leaves all retry controls disabled

desktop/main.js:458–469 sets state.quit to updating after the accepted idle fence, then throws on a blocked worker or deadline. UpdateController restores ready notification but shell state remains updating. Tray Quit is disabled, requestQuit returns and another restart refuses. Backend ownership remains safely held; user loses the supported retry route. Restore a truthful retryable shell state after failure without releasing backend ownership or weakening its closing fence.

Independent bounded processless Node VM reproduction uses the frozen shell's actual configureUpdater/parkEngine callback and real frozen UpdateController. Startup omitted; Electron/provider/HTTP/timers injected, no process, filesystem write, network or GUI action. Accepted POST followed by GET phase blocked produces error fixture checkpoint, shell quit updating, controller ready, backendExited false. Source SHA256: main edd1acc71b91d67879da610b04850493f1d5125b1004cddb5329dd3f78f932c7; controller 62ab3dfd5d3207ecdcfe45c42196a4a32c1668f763148c6ab61da5497a5da9c9. This reproduces shell integration, not a claimed installer test.

## Earlier findings and closure boundaries

- M1 C1 PID-only force tree termination removed. Detached native host retains the exact newly suspended engine HANDLE/generation/image and Job before engine execution; failed HTTP no longer kills it. Host waits for actual child exit; shell pipe loss requests checkpoint stop.
- M1 C2 unconditional shutdown after close timeout removed. _shutdown returns blocked without stopping serving on failed finish_shutdown; worker-safe completion alone changes phase to exiting. Scanner timeout now also retains ownership.
- M1 C3 unsafe pathname stale retirement replaced in the helper by source exclusion, ACTIVE_CATALOG capability, retained ordinary ancestry, one-link/single-stream/schema/dead-process checks and exact identity/hash no-replace rename. End-to-end closure remains blocked by S1, which never calls this helper.
- M1 C4 old recursive build deletions removed and native ancestry/fresh-write guard construction reviewed in earlier preflight. Previous-pointer retirement/CAS remains in-progress outside7098; no actual new-pin guarded-build/junction proof or final installer closure claimed.
- Early E1 Git/GH external lease bypass fixed: release uses leasedExecutable and no independent resolver/PATH fallback. E2 genuine ownedRoot refusal fixed through the exact retained proof's build child path. E3 desktop_host dependency now tracked. These are source-level closures; actual immutable owned protocol evidence still required.
- Version regression fixed: package/lock/root package version0.16.0. Prior reports remain history; this early report does not overwrite their evidence or certify a final installer.

## Review evidence and limits

Read complete pinned shell/preload/setup/controller/backend/catalog/settings/update-lease/host/catalog-owner changes, worker/server drain/lifetime consumers, all pinned build/release scripts and relevant tests/docs. Checked argument lists, renderer sandbox/context isolation/no Node, bounded trusted IPC/control tokens, exact installer SHA512 native lease and full-idle admission fence, exact native engine exit before install, disabled auto-install on normal Quit, and protected raw JSON/NSIS/ASAR/runtime manifest bindings. Source/publication/retirement/24-hour safeguards remain inherited unchanged; no retirement bypass was accepted.

The reported eight moderate npm advisories are not characterized from a count alone. Exact advisory JSON was unavailable at this review; parent permits deferring actual dependency reachability to the final candidate report. No audit/autofix/network request or dependency upgrade performed. Developer25 Python desktop/23 Node checks are sender claims, not this reviewer's independent receipt or packaged acceptance. Final protocol-2 sender/receiver graph, owned build, actual artifact-manifest hash, packaged native-input/selector/tray/update/layout evidence and final CAS review remain required.

## Nine dimensions

1. Security — **Pass**: production PID-force path removed; restricted renderer/IPC/token and native exact tool/installer leases inspected, final artifact/runtime proof pending.
2. Correctness & Logic — **Fail**: S1 startup callbacks never execute; S2 update retry state is stuck.
3. Crash / Stability Safety — **Pass**: failed worker/scanner close retains serving/catalog ownership; no HTTP-based kill deadline.
4. Performance — **Pass**: streamed media/build/hash routes and bounded logs inspected; no full-library/build throughput claim.
5. State & Data Safety — **Fail**: S1 ignores Existing/New authorization and final catalog validation before mutation.
6. Input Handling — **Fail**: isolated schema/native/path guards exist but are not wired into actual backend startup.
7. Maintainability — **Pass**: explicit native host/control/setup/update roles and shared release contracts inspected.
8. Doc/Code Drift — **Concerns**: candidate docs describe guarded startup that S1 does not actually perform.
9. Build & Release Hygiene — **Concerns**: frozen version/tool dependency fixes inspected; final CAS/source/installer/QA manifest evidence and advisory reachability outstanding.

Severity/safety floor follow Team/Docs/ProcessRules.md § Severity definitions. Open scoped findings: Critical1, Major1, Minor0.

**Verdict:** RELEASE BLOCKED

Fix S1 before release and recertify a new immutable final pin. S2 is advisory under the standard severity rules. This is early source review, not full v0.16 installer clearance or authority for live install/data/source/Start/update/publication.
