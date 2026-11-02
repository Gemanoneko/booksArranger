# Books Arranger 0.24.4 — QA

Futaba · 2026-11-02 · Focused evidence adjudication only; final build acceptance pending. No QA tests rerun.

**Verdict:** NO-GO

Focused cleanup retry evidence passes its stated scope. The first candidate full entry failed; the corrected candidate's full entry also timed out without a final receipt or postflight. Neither approved hidden packaged check launched. No 0.24.4 tray reference was consumed. Release remains blocked.

Release source commit: 3c45da40c82043379351fa60aac4e000a02ca172
Release artifact manifest SHA256: 0c85b34b48ff0c81fbae5b0b40254b94e15252051e692f41494c46e84f97f78b

## Corrected candidate full entry — FAIL_TIMEOUT

Corrected source above, build `3c395d29-d3fc-4ddd-ac3d-e708bfbb9063`, context `c4b46ec3336c571bd0e00d94c1863e9a74721b81fabf8ec97a1641b4e51e736a`, ran 12:41:41.973–12:51:42.006Z. The outer callback reports SIGTERM/killed at 600 seconds. The check was forced/timedOut after 566.17 seconds, output incomplete, closureError null; final owned complete zero was proved, with 10,523 retained and 340 cumulative transient incomplete sampling diagnostics. That final zero does not supply the missing entry receipt/postflight.

Only 117 child-output bytes were printed, including source copies finishing at 29.6 seconds. There are zero printed worker completion reports. Discovery/completion/error/pass counts, Node cases and frontend results are **unknown** for this corrected run because output was buffered. No specific assertion or product failure is inferred from absent output, and the first candidate's counts are not carried across.

[Byte-exact corrected timeout records](Evidence/v0.24.4_2026-11-02/full-entry-corrected-timeout/files.json) preserve nine originals. Summary SHA256 `c5aeec70108591502158a28d2e2037bd5da7f444ba1094286260426dd513808f`; files index SHA256 `5ab920ccea7fe4ec526b70877251e42d8ea0f9a6e5de6376a480276e1bdfb717`. Assigned worker scratch is retained for postmortem. The corrected review remains source construction clearance (report SHA256 `63e2137fad2f6ec36cff71ab857fa2f4681d6736ea2a1e75e70630d4f17492b1`), not behavior acceptance.

The observed post-copy outer budget conflict with the 540-second worker allowance is a runner constraint requiring separate resolution, not proof that the product passed. A subsequent three-file copy-cache experiment reported 23 correctness checks passing but took 75.521 seconds against a 15-second target; that experiment failed its performance target and is not accepted for shipping. Its edits are assigned to Sully for restoration to the committed corrected source. No third full run or app check is authorized by this report.

## First candidate full entry — FAIL, preserved

Source `1ab490b1fb5852edfd88ca689c0d340842a5ee1d`, build `46a8983e-8529-4efd-a91d-01b46d46fe3a`, did not pass. Of 2,338 discovered Python methods, only ten batch completion reports were produced: those reports contain 23 errors, with an additional start_over ERROR marker in an incomplete worker. Workers 5, 8 and 12 reached 540 seconds. The independent Node chain passed 241 cases; it does not certify overall acceptance. No final entry receipt or postflight exists.

The owned check exited 1 and closed normally, final complete zero/10,859 retained; 364 cumulative incomplete sampling diagnostics, no force or timeout on that owned result. The outer invocation nevertheless reached its 600-second deadline and reported SIGTERM. These are distinct observations. [Byte-exact portable originals](Evidence/v0.24.4_2026-11-02/full-entry-first-failure/files.json) include summary SHA256 `c4494e8b46afc5f88533423ec097abf685b8bc2a2e0529bad418d28023a2ff6c`, index SHA256 `b053d4aedfaeaed55565b0afa23df171bbe449d79c0335b7ed0d795cff7008a7`, raw outputs, owned result, callback and invocation. The first failure remains a failure.

The concrete regression was attention_summary calling CleanupJobs private _rows on legacy status collaborators. [Correction evidence](Evidence/v0.24.4_2026-11-02/public-capability-correction/results.json), SHA256 `886c5e88f7833e6767dbe0a82c2db8737e7ff1abebd97992d8b552e73c1afbab`, records a narrow public identity_attention capability: missing capability offers no action, while real implementation exceptions propagate. It reports 120 affected-module cases plus the exact start_over case passing, normal complete-zero closure, in 66.87 and 0.945 seconds owned elapsed. This supplements focused coverage; it does not turn the original full run into a pass. No exact resource cause for the three slow workers is established.

## Actual focused evidence

[Focused proof](Evidence/v0.24.4_2026-11-02/focused-results.json), SHA256 `025ab8efefe7d589dab84874410ae671d3be44e016988858ff4c97e1d618b1cb`. Before the correction, QA independently matched all eight source/test byte pins and all twelve raw record sizes/hashes, then consumed original outputs and ownership results. Four corrected file pins are separately recorded in the correction proof above; the original eight-pin result is historical evidence, not a claim those eight bytes remain unchanged. Earlier API/DOM fixture failures remain failures, with their records retained.

The BEFORE run used two synthetic source files and a deliberately closed **owned Windows output handle**. It actually observed Windows error 6, while the old display exposed only “Cannot refresh protected file identity”; saved member states were removal_intended/backup_verified, zero removed, and normal Resume made zero attempts. This reproduces the mechanism in a private fixture; it does not establish the historical live book's exact Windows code or current files.

Six changed safety cases passed: fresh output/source/recovery hashes precede every new disposal; the existing cleanup/job is reused; changed/missing output or recovery and changed source refuse further deletion; an absent original after unproved removal intent remains unknown; actual Windows 6/API/path is retained while another refusal loses eligibility; duplicate retry has one owner and Pause preserves the checkpoint. The happy fixture reconciles a retained intent and finishes with the two included originals recorded removed. Broader already-removed/recreated-state regression coverage remains part of the final entry, not newly claimed from this six-case run.

The service/API case passed exact revision/completed-job/enrollment/eligible-hold admission, stale/wrong-state/scanning refusals, strict queued payload and existing queued dispatch. It asserted no conversion Resume or new cleanup enrollment and follow_audio=false. DOM execution of actual app.js passed the distinct Retry cleanup route, legacy “Windows error not recorded”, observed Win6 detail/path, Checking inert state, queued Cancel visibility, accessible hint linkage and no conversion-state mutation. This checks route/control behavior with existing doubles; it is not a physical click, layout measurement or actual cancel-to-worker end-to-end test.

Actual normal owned closure: BEFORE 4 retained/0.705s; safety 4/2.831s; service+DOM 8/0.848s; final DOM 4/0.267s. All ended complete zero with no force/timeout or incomplete queries.

## Checklist coverage and limits

The reported trigger, safe reopen/full revalidation, changed/missing proofs, interrupted intent, exact native error, admission, duplicates/Pause and unaffected protective holds have focused evidence. Existing queue cancellation and mixed completed-member behavior are reused; their complete regression results remain pending. No generic proof refusal is granted retry by this patch. No Retry all/bulk or conversion expansion is certified.

No evidence yet shows the changed controls in a packaged visible window. DOM evidence establishes copy/state semantics, not geometry. A hidden packaged smoke can establish its actual stated native scope, not retrospectively prove visible UI or the live book's recovery. No install, live catalog/NAS/Z: access, user-app control, focus, clipboard or tray action was performed by QA. The historical 37-source/backup/intent diagnosis is not a statement about current live data.

## Remaining acceptance

Resolve the incomplete full-entry gate under an explicitly agreed next step before either approved hidden packaged check proceeds. Both app checks remain unrun; zero 0.24.4 tray-history references have been consumed. The 121 targeted correction passes remain supplementary and cannot replace a final acceptance receipt. Do not repeat the receiver full entry or automatically rerun the candidate. No acceptance index or release GO is created. No additional tests, app replay, focus or tray action was performed by QA.
