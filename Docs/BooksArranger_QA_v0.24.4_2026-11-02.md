# Books Arranger 0.24.4 — QA

Futaba · 2026-11-02 · Focused evidence adjudication only; final build acceptance pending. No QA tests rerun.

**Verdict:** GO

Focused cleanup retry evidence passes its stated scope. The first two candidate full entries remain failures. The final candidate passed under the separately reviewed and deployed schema-3 budget profile, with an actual final receipt and postflight. The relevant packaged browser-hosted Retry integration and canonical Electron check both passed with normal closure and exact own-leaf cleanup. QA accepts this named source/build within the limits below.

Release source commit: 9ccbbecef48d12498583a0a97ab595ce2a88ccb1
Release artifact manifest SHA256: 49ed6d8389e2fa224133cd0092e7c6cffe0776d4a3cd1a2bd07a4b43ee9c9fb1
Native QA evidence SHA256: 82cf373c3d5e9cb0ecb34f646bb41665bebb6390a408e63030f780f908f44247

## Final schema-3 candidate — full PASS

Source `9ccbbecef48d12498583a0a97ab595ce2a88ccb1`, build `2adf6f0f-3b2c-4ea6-8ee2-207c096fca9e`, context `7cf1faacee0def1838a0c23bc6bf536f42aec3a273097a99d93d306075e097e4`. Actual invocation 15:56:42.762–16:06:44.920Z, 602.158 seconds, original callback exit 0/error null. All 2,340 unique Python methods across 13 batches passed without failure/error/skip; 242 Node cases, 39 frontend scripts and 11 syntax files passed. Final postflight and personal-folder checks passed. Owned check closed normally with 10,873 retained, final complete zero, 375 cumulative transient incomplete sampling diagnostics, no force/timeout, output complete.

This was a legitimate schema-3/900-second entry profile, not a claim that 602 seconds passed the old schema-2/600-second deadline. The reviewed deployed shared runner is ROOT79b6e3f/TOOL9ccbbec: exact legacy profile remains 600 seconds; new finite profile uses 660-second workers, 810-second gate, explicit cleanup reserves and a 930-second EOF-only transport drain. The expected 1,200ms nested-timeout probe remains a separate intentionally forced timeout. The failed copy-cache performance experiment and both old full failures remain failed.

QA independently matched original receipt.txt to summary and actual stdout, consumed the final outcome, and preserved eleven files byte-exact in [portable schema-3 evidence](Evidence/v0.24.4_2026-11-02/full-entry-schema3-pass/files.json). Summary SHA256 `7278a2f8a5ae455683915867f8a5f7a5962b0bab7f6850638ac908a7b0aa278e`; files index SHA256 `638d46cc69fbd08a9d8f890a8c0278ed8a34325e5bc1115bed6ba065ad2757c5`. Independent final source/artifact review SHA256 `5a3a34d2e7c5165d78480421b9689169e157b4cedeafe59ea92e8c2c5c14b079` is RELEASE CLEAR. No receiver full rerun was performed.

Actual receipt:

```text
Entry-check receipt v2: books-arranger v0.24.4 @ 9ccbbecef48d12498583a0a97ab595ce2a88ccb1 (dirty: N) [source:4b327c3a82b697262fbbeaac68c712e8eec78efc5431c2fdec236ebabbb337ca; harness:2e93ff8b0a46c1c2d694051fbbfc043ab5c90640efc1e5dd2b00bcc0a8887f12; runtime:5d3562ed3a04005275ea9af81576a624a3b926445cc80236e9fedc95590a29e1; checker:4bae2cde4e4cdd2f22fb3060571730ec32fec1dd5403ea070086973b18b695e4] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a; personal-folders clean
```

## Canonical packaged Electron check — PASS

[NativeQA](BooksArranger_NativeQA_v0.24.4.json), SHA256 `82cf373c3d5e9cb0ecb34f646bb41665bebb6390a408e63030f780f908f44247`, binds the same final source/build/product/artifact as full and feature proof. QA independently matched all twelve raw role sizes/hashes and consumed original callback, functional, inner/controller ownership, postflight and cleanup. Actual callback 16:58:41.608Z error null, empty stderr. All eight required assertions passed: update available, download SHA512 verified, invalid installer refused by Windows, shell stayed alive, installer-blocked cause, fake download seen, old engine health/version recovered and normal Quit ended shell.

Inner 21/controller 25 retained both exited zero normally, complete final zero, zero incomplete queries, no force/timeout, output complete. Postflight unchanged. Exact new own leaf was deleted through the same handle, closed and absent; preexisting leaves unchanged, UIOrderList not written, one approved 8-byte history reference remains. Alongside the failed feature Electron attempt, exactly two approved references were consumed; browser integration added none. Finite 257 observations reported no visible own window/intrusion. This is hidden native scope, not a physical Close click, visible geometry or live catalog proof. The proper current validator accepted the original twelve records without compatibility or bypass.

## Changed Retry cleanup integration — actual PASS

[Portable feature proof](Evidence/v0.24.4_2026-11-02/packaged-browser-retry-pass/summary.json), SHA256 `dda92818bf36ae3bd130081c9a3d9b1b1597a6bee15b04d376a7287d0f019a61`, binds the exact final source/build/product/artifact above. It uses packaged desktop_backend and web assets through an existing owned headless Chrome browser, with a supported explicit private C: output root. QA consumed the original functional/callback/progress records and independently matched the pinned original owned result hash. Six directly reached product files match current source byte pins; web/index.html is the generated packaged file, SHA256 `4d539540abcd57bc54d7548dc0391c96f9339ed9779705f3b4363d23e7395c19`, size 36,189, bound by the actual payload manifest SHA256 `2e9f6ddcc50be61fcc0dc72df3d811ad0b5db8b3001c84aa713cbd0bbbddab26`; it is not mislabelled a seventh unchanged source file.

The real Needs attention shortcut exposed Retry cleanup; actual DOM click at 16:57:24.306Z produced the authenticated POST at 16:57:24.518Z, HTTP 202 accepted for the same completed job and cleanup. At 16:57:24.613Z the two exact originals were absent and their cleanup members recorded removed. Job, attempt and cleanup IDs stayed the same, no new conversion/job was queued, output SHA256 and sibling bytes stayed unchanged. Callback at 16:57:27.728Z had error null/empty stderr; original owned exit 0, normal complete zero/36 retained, zero incomplete queries, no force/timeout, output complete. Browser closure was verified with zero remaining; backend Quit exited zero. This route created no tray reference and took no focus or clipboard.

This is browser-hosted packaged feature integration, **not a successful Electron Retry click, visible geometry, preload or desktop-startup claim**. The earlier Electron feature attempt really failed: its fixture output root was dropped by supported roots-json launch, so startup correctly refused the seeded cleanup. Its normal 13-process closure and exact own-leaf cleanup are retained; one approved 8-byte history reference remains. Subsequent headless operator/Edge DevTools/filter-selection failures remain failures, not product regressions or successful clicks. The successful route uses the same packaged DOM fetch/server/queue/cleanup action without an Electron-specific bridge. No live book or historical 37-source job was retried.

## Historical corrected candidate full entry — FAIL_TIMEOUT

Historical source `3c45da40c82043379351fa60aac4e000a02ca172`, build `3c395d29-d3fc-4ddd-ac3d-e708bfbb9063`, context `c4b46ec3336c571bd0e00d94c1863e9a74721b81fabf8ec97a1641b4e51e736a`, ran 12:41:41.973–12:51:42.006Z. The outer callback reports SIGTERM/killed at 600 seconds. The check was forced/timedOut after 566.17 seconds, output incomplete, closureError null; final owned complete zero was proved, with 10,523 retained and 340 cumulative transient incomplete sampling diagnostics. That final zero does not supply the missing entry receipt/postflight.

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

The reported trigger, safe reopen/full revalidation, changed/missing proofs, interrupted intent, exact native error, admission, duplicates/Pause and unaffected protective holds have focused evidence. Existing queue cancellation and mixed completed-member behavior are reused and their regression modules completed in the final full entry; the focused feature run itself does not claim every cancellation/crash boundary. No generic proof refusal is granted retry by this patch. No Retry all/bulk or conversion expansion is certified.

The real browser-hosted packaged DOM action passed. No evidence shows these changed controls in a packaged visible Electron window; geometry and Electron Retry remain unverified. A hidden packaged smoke establishes only its stated native scope, not visible UI or the live book's recovery. No install, live catalog/NAS/Z: access, user-app control, focus, clipboard or tray action was performed by QA. The historical 37-source/backup/intent diagnosis is not a statement about current live data.

## Remaining acceptance

The reviewed schema-3 full entry, relevant packaged browser-hosted feature integration and canonical Electron native proof now pass with exact binding and normal closure/own-leaf cleanup. The 121 targeted correction passes remain supplementary; original failures are not relabelled. The existing-format version-specific acceptance index names this report and independent review. Publication and removal of owned temporary files/folders remain assigned release/cleanup work. No tests, app control, focus or tray action was performed by QA during adjudication.
