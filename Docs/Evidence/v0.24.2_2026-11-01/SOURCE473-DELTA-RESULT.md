# SOURCE473 changed-behavior QA result

**Source checks: PASS.** Backend load/admission and S8 startup behavior passed. **Release: NO-GO pending the canonical full entry, final artifact binding and native PA1/package smoke.** This is not a final-build or installer verdict.

Source:47374c5923abb48e650e35d7ce84e3e689b8239f; exact102 reached inputs (95 Python +7 support/UI), tree0298e43e95c359c841a5dcb0aaddcd9df5b231b3be0ac95f41142f186db5e4a1. Runtime47/owner92 and source/helper postflight pins passed. Later packaging-only commits can reuse this evidence after exact reached-byte comparison, without relabelling this run.

Backend-2: real private service,1,572 candidates/500pending/189protective-refusal records, zero valid native outputs. Twelve HTTP responses recorded. First/repeated state176/140ms and list1310/516ms; while real page computation was held, Resume4.08ms and Start176.40ms answered; repeated Start14.36ms retained one worker. Same-key callers shared one actual computation. **Both deliberately held unprimed list callers returned503** (1919.82/1916.94ms), as the diagnostic contract allowed; the wrapped computation then completed successfully after release. No timeout, duplicate page work or compute error.

S8-1:7/7 observations passed,319 clock steps at<=1000ms. Actual answer age remained6000ms/Waiting and306001ms/Stuck before the new state reply. Startup kept stale/busy warnings suppressed through one actual abort/re-ask and settled only after list paint. Post-startup stale positive control appeared and cleared. Native/unexpected-fetch attempt counters0, runtime errors0. No geometry was repeated.

Closure: both normal complete/zero; backend392 and S8464 native queries,0 incomplete; active/assigned/listed/unsignaled all0; no force/timeout/overflow. Backend remaining Python threads[]; S8 lease verified remaining0 with stop-requested, postflighttrue. Twenty-nine100ms owned-window samples had0hits/errors; this is finite sampling. Wrapper personal-folder observation clean with lines[].

Limits:6.25MB synthetic catalog; native conversion/research workers were gated. No real media/output hashing, CPU-saturation, NAS/92GB throughput, p95/SLA, native dialog/tray or packaged acceptance claim. S8 used fake transport/clock and an empty first page. No source/audio/live-data/user-app operation or product/Git/guard change.

Prior backend-1 failed because synthetic evidence lacked title_clue; source inspection also identified required scope. Parent authorized only those two fixture fields in fresh backend-2. Original failed evidence and its pre-exit books-status snapshot remain preserved; corrected backend-2 had no remaining threads. No application defect inferred.

Pattern alerts: none in these product contracts. All raw private callbacks/results retained until end cleanup; only filtered metrics/closure proof are suitable for a committed QA report. Full input manifest and exact evidence hashes: SOURCE473-DELTA-PROOF.json.
