# Books Arranger latest stable application — 2026-10-12

Sergei requested always running the latest stable Books Arranger, with his help for normal Windows launch when needed. Target is released v0.12.1, commit `a36d3fe9e61d5b6663dddba9322031ef9d9b194c`; remote main/release branch/tag agreement is retained in `scratch/sqlite-busy-2026-10-12/release-publication-proof.json`. Final Senua review clears release and Futaba independently passed 78 unique Python cases. This is the released SQLite BUSY patch; the isolated Google/Yandex prototype is excluded.

## Safe pause and shutdown

Ender's fresh observation at 2026-10-12T07:25:29.489496Z verified loaded v0.12.0 Pythonw PID53708, instance71d58343cdb17863c2232eb1f5eaebf6 and saved automatic run96cbe916-3b2b-4858-b386-89d493cb4f24 Running/research. Only the unchanged historical durable SQLITE_BUSY error was present. No new completed book, queued conversion, cleanup, scan or active recovery was observed. Four full completed validation/metadata/candidate/context records matched the prior protected digest.

After Sully's exact application plan was ready and Jane authorized shutdown, one supported Stop saved Paused/research and drained the research worker. No force kill, replacement launch or Start was issued. The current-instance-token supported shutdown accepted idle state; the held exact process exited, ownership record disappeared and native exclusive bind proved port5210 available.

The four full completed records matched before/after Stop and shutdown: SHA256 `dba3bd841c2ae9f2d98cfeff4e694a936f38d8c930a25243595f20758b28c22e` over sorted Unicode JSON. The final saved checkpoint matched exactly across shutdown: SHA256 `0c90f0dcb56ad896f0b707da6716acd3f2ab886f7a7cfd416bab0c54545871d8`. Research normally advanced between the active observation and Stop; the active checkpoint is not falsely claimed unchanged.

Evidence is retained under `scratch/latest-stable-2026-10-12`: `before-stop.json`, `paused-proof.json`, `shutdown-proof.json` and the scoped extended `live_control.py`. The previous update helper and evidence remain unchanged. Shell fallback used plain native PowerShell because both default Bash and explicit Git Bash shell mapping invoked unavailable WSL `/bin/bash`; no encoded command or persistent process was used.

Sully applied released v0.12.1 to canonical HEAD `a36d3fe9e61d5b6663dddba9322031ef9d9b194c`, with exact release index/tree and application recovery proofs under `scratch/latest-stable-2026-10-12/release-application-recovery`. UI physical bytes are unchanged from v0.12.0. Approved documentation changes and the isolated search prototype were preserved.

## Normal launch and guarded resume

Sergei confirmed normal Windows launch. Verified new loaded owner is v0.12.1 Pythonw PID90872, instance8374a6e1082799f0db255f30de9e41ae; old PID53708 is absent. All 83 non-document/non-dot tracked source/interface/test/runtime files match the release after CRLF normalization; physical hashes are in `new-owner-proof.json`. Saved run96cbe916-3b2b-4858-b386-89d493cb4f24 was inactive Paused/research, can_start=true; full completed records and exact checkpoint matched the shutdown proof.

The initial scratch helper refused the old update's unconditional restart_paused=true guard. Read-only released startup-contract inspection established `automatic_processing.py:82` changes the flag only for prior Running/Stopping. This update deliberately shut down an already durable Paused run, so restart_paused=false is the expected preserved value. After Jane's explicit GO, the scratch helper guard requires exact Paused/run/restart-flag equality with shutdown proof. No application source was changed and no failure was hidden.

One supported Start was issued and accepted for the same saved run. `start-issued.json` prevents replay; `start-reply.json` records Running/research. Two bounded observations at 2026-10-12T07:32:38.063562Z and 07:33:28.754821Z (10:32:38 and 10:33:28 Israel time, 50.691259 seconds apart) verified the same owner and Running/research. Pending changed2307→1970 and deferred86→423 while historical done2431 remained. These are saved research visits, not converted books. All four completed records remained exactly unchanged; no new conversion was observed.

The displayed durable error ece3d07c-9653-4d53-a583-5f2e84ed1c16 remains the historical 2026-10-11T21:11:48.760915Z SQLITE_BUSY event. No new controller failure appeared in this bounded observation. The patch's transient safe-write recovery does not promise uninterrupted processing; review/QA limits still apply. Observations are retained as `observation-073238.json` and `observation-073328.json`. Existing native source verification, 24-hour recovery and verification before original deletion remain unchanged; no Comics/Comix, Open Library dump or originals were modified by this update. No disposable scratch output was created; unique proofs/recovery/helper files remain retained.
