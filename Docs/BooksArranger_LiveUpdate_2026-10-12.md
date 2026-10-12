# Books Arranger live update handoff — 2026-10-12

Ender: supported old-owner shutdown completed; app is offline. Exact release application belongs to Sully and was authorized by root after shutdown proof. No replacement process was launched from the tool host.

Live recheck found v0.11.1 Pythonw PID50896, instance81ee5d1c8e1e90c20798f923a029ac6b. Automatic run96cbe916-3b2b-4858-b386-89d493cb4f24 had already stopped with a nondurable SQLITE_BUSY diagnostic; Start and Stop availability were false. No scan, conversion, job queue or source cleanup was active. Four completed books remained authoritative. No newly completed book was observed.

The bounded live diagnostic was preserved outside SQLite before shutdown, together with the durable run checkpoint, failure candidate, prior durable errors and full completed-job validation/metadata/candidate/context records: `scratch/live-update-2026-10-12/failure-preservation.json`. It is recovery evidence, not an application of unsaved state to the catalog. The failed candidate d306e2ba-569a-4141-9b95-0e2922060fee remains in the pending checkpoint. Counts:2316 pending,2431 historical done,77 deferred. Pending and historical done may overlap during revisits.

Loaded v0.11.1 source contracts were read from its tag. The public supported Stop changes durable Running to Stopping and pauses jobs; the already-ended failed automatic thread cannot save a new Paused state. Consequently no claim is made that this failure was durably recorded or that an explicit Paused checkpoint was saved. Normal startup changes Running/Stopping to Paused and Researching candidates to Pending, while retaining the checkpoint bytes. It does not start automatic processing.

Root authorized supported Stop and guarded shutdown. The current-instance token shutdown accepted the idle state, the exact held old process exited, the ownership record disappeared, and a native exclusive bind proved port5210 released. Shutdown proof is `scratch/live-update-2026-10-12/shutdown-proof.json`; pre-Stop and post-Stop identity proofs are retained alongside it. The historical name `paused-proof.json` means idle verification only; automatic status remained Needs attention before exit.

- Exact four completed records matched before and after shutdown: SHA256 `dba3bd841c2ae9f2d98cfeff4e694a936f38d8c930a25243595f20758b28c22e` over sorted Unicode JSON.
- Exact saved checkpoint bytes matched before and after: SHA256 `2cda9e9f0b6fc08073e0ffd7ffd62bc05b8611b2f392f96c9c373141d7b7135e`.
- The four completed outputs,24-hour recovery policy and native source-verification rules were unchanged. No originals, Open Library data or Comics/Comix state was touched.

Sully applied the reconciled release after shutdown. Canonical main advanced to released b569cc1e556726043671f9b329a2f3cb0cf49ea7; VERSION is 0.12.0 and the index/tree exactly match the release. Eight baseline paths were applied (VERSION, CHANGELOG, four interface tests and web/app.js plus web/index.html); all 84 remaining reviewed physical input pins were retained. Exact original path/index snapshots and before/after evidence are preserved under scratch/live-update-2026-10-12/release-application-recovery. The normal Start-menu Books Arranger and Restart Books Arranger links still target the canonical Pythonw scripts with -I -B. No replacement owner has yet been verified.

Next: Sergei uses Windows Start menu **Books Arranger** normally. Ender verifies exact new Pythonw owner, loaded v0.12.0, inactive Paused saved run, matching checkpoint and four completed records before one separately authorized supported automatic Start. SQLITE_BUSY root cause/recovery work remains a separate agent-owned fix; v0.12.0 does not promise uninterrupted processing.
