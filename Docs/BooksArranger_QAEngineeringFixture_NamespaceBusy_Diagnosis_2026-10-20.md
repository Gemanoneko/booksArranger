# Namespace rename refusal: bounded diagnosis

DOC ONLY. Actual00b8 remains FAIL. Root-supplied actual result SHA8a8f9323a5ecd4c6b64db9178c1a47c4f80609118097dc3f3068f76e5cf72780 records EBUSY for branch -> branch-original. Both completed inner cases and original outer closure remain their own actual evidence; flood/wait/final work/companion-close were not completed. No retry or source mutation here.

## First substantive finding

native-fixture-controller.mjs:48-49 performs two different rename assertions. While phase owns its directory handles it expects EPERM/EACCES/EBUSY. Its finally then calls phase.teardown(); only after that returns does the second, required-success rename run. build-worker.mjs:57 teardown iterates EVERY phase handle, checks every CloseHandle return, empties handles, then throws if any close failed. Thus reaching the second rename means this code's phase close loop reported success. There is no source-proven omitted phase teardown or marker mismatch to fix.

The long-lived io instance has a distinct handle set. At this point its source shows fixture root/evidence/tmp/lease ancestry and input leases; it never intentionally retains branch or leaf. Observer launches controller at STUDIO (native-fixture-observer.mjs:28), inner children at fixture_root (controller:34); neither shown cwd is branch. Observer rejoin is only after successful controller wire and cannot explain this earlier branch refusal. These source facts do NOT identify an actual outstanding Windows holder or establish that no other handle/object state exists. Do not diagnose antivirus, stale process, parent directory semantics or asynchronous closure from EBUSY alone.

Cross-close record case is downstream at controller:50-52 and was not reached. No result about its post-writer-close native facts is established.

## Smallest justified next correction

No behavioral rename waiver is justified. Propose a bounded diagnostic amendment ONLY in controller namespace case and its focused pure controls: record namespace stage, exact fixed source/destination, original phase full128/birth proof, bounded long-lived io parent PATH inventory (not handles), held-rename actual error, and phase_teardown_returned set only after actual checked teardown returns. On second rename failure capture its exact own-data code/errno/syscall/path/dest, then persist ONE fixed namespace-failure record through existing creation-owned evidence writer before rethrowing. Preserve capture failure as failure; no fallback, polling, sleep or second rename attempt. Records remain descriptive, not closure or holder authority. If this needs an observer/schema change, stop before that edit and review its exact format. No process/handle enumeration or PID cleanup is proposed.

Pure counterexamples: second rename cannot precede every phase close; any failed close prevents it; teardown error is not replaced by rename error; successful close followed by EBUSY persists failure and never marks native case success; unknown error/capture failure refuses; branch path is not borrowed from caller input; original held-denial assertion and full128 replacement-refusal remain required. Native next-run review must still require actual successful unheld rename, same-path replacement with different birth/native identity refusal, exact post-close record comparison, remaining overflow/timeout closures and final companion checked-close proof under the ORIGINAL bound. A new actual namespace/run requires independent admission; old00b8 cannot be replayed.

## Read scope/pins

Exactly three source files read, no additional probes:
- native-fixture-controller.mjs: b74419aa65ab174262de5c132c5f7f1598aeaa27af9991de173ae7faefad084b
- build-worker.mjs: cb0057924ef95f515a077434c817d97afc252ba6f307fe53337616856c1e7e29
- native-fixture-observer.mjs: c28eeabf265e96b8cb4806e763326dec7e8b9e6a1c5a17523a7330e47c36a4e3

Actual holder/cause remains unproved. Source-only proposal; no claim that added diagnostics repair the native behavior, no CPP work, tests, native/process/RNG/Git/global/live changes. All prior evidence and scratch preserved.
