# Books Arranger v0.20.0 — QA report, 2026-10-21

Futaba. Corrected source checks, actual packaged manual Save, inspected visuals, A's desktop Quit and the final native-Close B pass now clear the declared release scope. Earlier failed attempts remain recorded below. The native-Close pass preserves the original page/backend and proves natural closure after explicit private-backend cleanup.

## Current corrected candidate: independent source checks PASS

Current product source is `f0c39197bff78401af630c83fe963e76d687b57d`, Books Arranger 0.20.0, dirty N, in the same clean QA repository. The correction adds the renderer's universe field to the HTTP review validator; the original packaged rejection and all earlier evidence below are preserved rather than promoted into clearance.

Protocol-2 context: `shared/standard-entry-20261021-v8/context.json`, SHA-256 `8934c29c8b2e413132d392fb572c757405cc479f20ce40b0eebae98831f20070`. Receiver literal `run-receiver.ps1`, SHA-256 `8f353314e1b2d82ab677c1706edfadbf5692c27ee32025a983da464249766530`, differs from the sender only in its exclusive log path and human labels.

Actual independent receiver: original session `18528`, start `2026-10-21T09:10:03.6970276Z`, terminal chunk `5dbe73`, exit 0 at `2026-10-21T09:17:25.6299307Z`. Independent evidence parse `3dba8c` verified all of the following:

- 1,214 Python cases, both batches complete (678 + 536), zero failures/errors/skips; includes the new HTTP review payload regression.
- 57 Node cases, zero failures/cancellations/skips; all 16 frontend scripts and eight syntax files complete.
- Actual `BOOKS_INTEGRATED_CHECKS_PASS` with these exact counts.
- Owned elapsed 416940.0001 ms, `ok=true`, `closed=true`, complete output, no forced termination/timeout/overflow, active/assigned/listed 0 and all 2,647 retained processes signaled. Fifty-three transient incomplete samples reconciled to complete final zero.
- The actual sender and receiver receipt lines match exactly, case-sensitively. No source or runtime changes were made between runs.

Sender log SHA-256 `c8f83dbcda9fc723a2fdc57ea7ed1f6885ec2a6660b8178de84dee4c1b2631dc`; receiver log SHA-256 `2b697f2e68578de6c614cc910521bc71969142acbf31bc64bafca25102288d8f`, both under the v8 context directory. Sender separately exited 0 with complete output and owned closure, 1,214/57/16/8 actual counts, all 2,648 retained processes signaled.

```text
Entry-check receipt v2: books-arranger v0.20.0 @ f0c39197bff78401af630c83fe963e76d687b57d (dirty: N) [source:deaf7e0a6abf24943fff2b5d320423863a26e50b5f2336681ebbe52be8a236f9; harness:7c676b68ea9f327d1ac39f7ae94f0d8a6fe6224f5d59117e9f844e201fd26e49; runtime:506e1609b58ddf3ec4b7f17db83a51837ccbe4612fed0076eeb3bbf43f3d820b; checker:8af6c2583c60cdef7b610f2161010394aa7ad45fafe7584f69e98fc5c131ce6a] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a
```

The old c2f2e00 installer below remains rejected. Actual corrected-package Save and screenshot results are recorded later; Close/Quit coverage is still required before release GO.

Release source commit: f0c39197bff78401af630c83fe963e76d687b57d

Release artifact manifest SHA256: 28ca7285b659cab01790ee469d926203319f6cae7e4fe3319bdc06a9b3c18682

## Historical candidate c2f2e00: scope and evidence

- Product: Books Arranger 0.20.0, source commit `c2f2e00e50e7b3d32384f424e79f88f8749128e2`, dirty N.
- Source repository: `C:/Antigravity Projects/Worktrees/Books Arranger/qa-0.20.0`.
- Reviewed protocol-2 context: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/standard-entry-20261021-v7/context.json`, SHA-256 `db8d761a44e1904cceb424b76c657665a425faab425bf34a3a92a91f045bc6e6`.
- Runtime includes eight complete manifests, including the exact private MP3 fixture; the real library was not used by QA. The fixed 600000 ms total deadline and private Windows Job ownership remained active.
- Receiver invocation preserves the sender's exact canonical executable, argv, fixture validation and environment binding. Only its exclusive log path and human labels differ. Receiver literal SHA-256: `f7f77264c255b039bf798e26e7c9f037a851fe8e20d440bd493853262cd57870`.

The complete source and runtime identities were checked before and after the canonical run. Its private run copy and fixture writes were separate from Sergei's catalog and source folders. No focus-taking GUI, account session, audio playback, live controls, migration, iTunes operation, shared Node-kernel call or quarantined-file access occurred.

## Independent receiver result: PASS

Original execution session `42067`, start `2026-10-21T08:07:04.8098905Z`; terminal tool chunk `34d958`, exit 0, terminal `2026-10-21T08:15:05.0509034Z`. The original session was polled to completion; it was not relaunched.

| Declared work | Actual result |
| --- | --- |
| Python | 1,213 cases: 677 + 536 complete; zero failures, errors or skips |
| Node | 57 cases; zero failures, cancellations or skips |
| Frontend | All 16 declared scripts completed |
| Syntax | All eight declared files checked |
| Integrated completion | Actual `BOOKS_INTEGRATED_CHECKS_PASS` present with the same counts |
| Owned closure | `ok=true`, `closed=true`, complete output, active/listed/assigned 0; all 2,649 retained processes signaled |
| Deadline and failure flags | Owned elapsed 454412.4996 ms; no forced termination, timeout, overflow or closure error |

Forty-nine transient incomplete native-membership observations were reconciled; the final observation was complete and zero. This is closure evidence, not a performance benchmark.

The Python discovery count was read from actual output and both completed unittest summaries. Node totals and zero-failure/skip/cancellation fields were read from actual TAP output. The integrated marker independently confirms the frontend list and syntax count. A bare zero exit or receipt without those outputs was not accepted.

Sender log SHA-256: `c71ecbff42bb4162212a7f179a2c515e96ed7b1e2711a5030a2eabbd374adb90`.

Receiver log SHA-256: `abc962bf7984ec2cd396fcc59fcf2cd94c9114eddb94b9792ec1b6a3d11aa6ca`.

Both logs remain under `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/standard-entry-20261021-v7/`. Their actual receipt lines compare exactly, case-sensitively:

```text
Entry-check receipt v2: books-arranger v0.20.0 @ c2f2e00e50e7b3d32384f424e79f88f8749128e2 (dirty: N) [source:76aedbce216307f361f2390d84e2109eae74a2ae4a391d35312787487000fdb7; harness:7c676b68ea9f327d1ac39f7ae94f0d8a6fe6224f5d59117e9f844e201fd26e49; runtime:506e1609b58ddf3ec4b7f17db83a51837ccbe4612fed0076eeb3bbf43f3d820b; checker:8af6c2583c60cdef7b610f2161010394aa7ad45fafe7584f69e98fc5c131ce6a] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a
```

## Regression coverage and limits

The declared graph includes Retry All submission-versus-admission feedback and pause/start fences; catalog contention and revision-preserving SQL replay; hierarchy and author-folder versus Artist-tag separation; additive sources; retained manual metadata and explicit conflicts; publication/relocation bindings and recovery; reacquire retirement guards; the exact private zero-audio-loss MP3 repair; desktop quit/update contracts; and the integrated frontend modules. These results certify the synthetic/private automated cases, not the current live library or external providers.

Earlier false-green, ownership, timeout, fixture-layout, teardown and obsolete-frontend failures remain failed historical runs. They are not counted as passing QA or independent receiver evidence for this commit.

No general positive serious-audio-damage classifier, live producer closure for Сказка, live output migration, additional-source activation or new Open Library editions activation is certified by this pass. Unknown damage must not be labelled repairable or in need of reacquisition without its required evidence.

## Packaged acceptance: PENDING

Required before release GO: bind the actual accepted installer, blockmap, update metadata, extracted payload/runtime and source manifest; run the reviewed isolated hidden-app driver; check actual UI/backend version, discovery, routing/manual-metadata flow, tooltips and screenshots; exercise Close-to-tray on that same hidden instance; request normal Quit and prove natural exit and closed ports/process tree. No second-launch control, native input, focus or audio is permitted. Screenshots need visual inspection; automated logic alone does not clear pixels.

### First packaged attempt: FAIL, diagnostic phase incomplete

The accepted manifest was independently verified as SHA-256 `a4c1c5f20ef41e292900ca4b2835bc93b4eb748a641498d9150f9e8f40af6b9c`, source `c2f2e00e50e7b3d32384f424e79f88f8749128e2`, product digest `780887b59232c359d916f7ab69b47667296c30d1f3c4b0c22a9f86972292d3de`, build `b90eb16c-ec6a-4872-903e-51bc07449b99`. Its 265-file payload is marked installer-equivalent; 48 runtime entries are recorded. I independently hashed all three release artifacts before the run: installer 173600324 bytes / `64dcf2c0b55e694c8ead9a3160be101e14cf67a95a106aa14527b9711f159bfb`; blockmap 181113 bytes / `381c9e404a7aa0a053cd319487a470fa0606ff421c48f44dc57de7eae2730b9e`; latest.yml 360 bytes / `c0e8ac094a933814fbfa8ce6b04657fc7e1b65ded0049c7dc88c5b88e28fd1b6`. All match the manifest.

One reviewed hidden packaged run was executed through the exact six-argument literal, SHA-256 `5a5f7839428ee5b812d92a1cb61fdf53d9bb68ab16db9f5a8e64e28344e966b4`, using the prepared driver SHA-256 `1ff0baf68084c74e9415f03d621885fb5413fda7b3476cdb21dd9e9e0f1ff298`. Original tool session `85648`, start `2026-10-21T08:27:25.2756200Z`, terminal chunk `032356`, exit 1 at `2026-10-21T08:27:37.8020311Z`.

The driver stopped on an eight-second `Runtime.evaluate` CDP timeout. The original diagnostic identifies the method but not which expression/stage; no product cause is established. No screenshot, final action record or packaged result was produced. Do not claim actual Close/Quit or natural app exit from this attempt.

Failure cleanup completed: owner `closed=true`, complete output, native active/assigned/listed 0, all 11 retained processes signaled; owner elapsed 10179.4772 ms, no outer timeout or overflow. This is failure-cleanup proof, not natural-Quit evidence. Full payload inventory and manifest/driver/controller hashes still matched afterward. Evidence remains at `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/packaged-v020-final/`. No rerun was made; Ender owns a separately reviewed trace-only diagnostic correction before a fresh attempt.

### Trace-only second attempt: FAIL, failing expression isolated

After independent source/literal review, one fresh diagnostic run used driver `5a0deca6673d505be27f504a84f083fba8c4c1fad683c51d08377210d3492956` and literal `3f41df7032628bf58fbe1a55be98416f5993984ec981774788069064c0975fe9`, with unchanged product, actions and deadlines. Original session `72897` started `2026-10-21T08:33:34.6261407Z`, ended exit 1 in chunk `b07167` at `2026-10-21T08:33:47.1824992Z`. Evidence is in `shared/packaged-v020-final-2/`.

Actual bounded trace: startup CDP requests 1–4 responded in 2–4 ms; the `window.close()` request 5 responded in 3 ms. Request 6, stage `window-close-fresh-backend`, then exceeded its unchanged eight-second command bound. This expression combined an awaited renderer fetch of the private `/api/state` with `window.closed`; it does not distinguish backend responsiveness from renderer promise scheduling. The Close command itself was acknowledged. No product cause, screenshot acceptance, natural Quit or release GO follows. The owner again closed completely, all 11 retained processes signaled, with unchanged post-run payload/manifest/controller/driver hashes; elapsed 10229.406 ms. Further diagnosis must separate the synchronous window facts from an independently bounded authenticated private-backend request.

### Third packaged attempt: FAIL, manual save did not persist

The independently reviewed QA correction preserved the actual Close and Quit checks, moved Close after the ordinary UI workflow, and separated its fresh backend read from renderer promise scheduling. Same accepted product/manifest; driver `6326d30709c970ac4b6722f4bf2db8b3dd6169ea685868ac9703d2ae5ddc5646`, literal `7c80549a70fe4948c92946cfd2c8f34ebe71771940beee30fc38fa9f06acaad7`, fresh evidence `shared/packaged-v020-final-3/`.

Original session `23440` started `2026-10-21T08:40:18.3815642Z`, terminated exit 1 in chunk `9439a3` at `2026-10-21T08:40:40.6610014Z`. Startup, discovery, hierarchy previews and tooltip assertions reached completion; the `manual-save` condition then stayed false for its unchanged 15-second bound. CDP continued responding within milliseconds. No screenshot or final Close/Quit acceptance followed.

A subsequent short, read-only coherent observation of this closed private fixture catalog found two candidates at revision 1 with empty reviews, zero `candidate_context` records and zero `manual_metadata_sources` records. Method: standard-library SQLite URI `mode=ro`, query-only BEGIN, one-second busy bound and three-second progress interrupt, explicit rollback/close; original read chunk `1479d6`, exit 0. Therefore no manual draft or source was persisted; this is not merely a mismatched post-save predicate. The cause remains unproved until the actual rendered message, save readiness and lease state are captured. Ender owns that diagnosis; no blind rerun or app change is cleared by this report.

Failure cleanup again completed: active/assigned/listed 0, all 15 retained processes signaled, complete output, unchanged full post-payload inventory, owner elapsed 19965.7753 ms. This does not prove natural app exit. The verdict remains NO-GO.

### Fourth packaged attempt: FAIL, actual Save rejection captured

A separately reviewed observation-only delta recorded bounded form state and screenshots before submission and on failure. Same accepted package; driver `7c07ab76dfed68da60da72923e5837efab6168b59fc3fb6cbc70e508a55d1f78`, literal `04f61d84d4696b5b2d10d4f29e859791b7d509f0d302fabea10e77dddd1f0a60`, fresh `shared/packaged-v020-final-4/` evidence. Original session `66723`, start `2026-10-21T08:49:17.6436599Z`, exit 1 in chunk `18a24b` at `2026-10-21T08:49:45.7595223Z`.

`before-manual-save.json` shows a valid form, enabled submit button, dirty=true, busy=false, ended=false and a confirmed active manual editing lease without failure. All visible input-validity checks passed. After submission, `failure-manual-save.json` and the inspected `failure-manual-save.png` show the actual message **Review fields are incomplete or unknown**; the draft remains dirty, selected revision 1, review null. This is not an early click, disabled control or absent editing lease. The failure screenshot was visually inspected: v0.20.0 and the entered title, separate author-folder/Artist credits, universe and cycle are visible. No natural Quit or final packaged acceptance follows.

Owner cleanup completed, all 15 retained processes signaled, complete output and unchanged post-payload inventory; elapsed 25779.7209 ms. Ender received the actual state, screenshot and private-catalog observations for diagnosis. The exact validation cause remains his investigation; QA has not guessed which input or boundary caused it.

## Corrected PACK3: manual Save and visual regression PASS; Close/Quit coverage pending

The actual defect was the HTTP review validator omitting the universe field that the renderer always submits. Corrected source f0c39197 and its new HTTP case passed the independent 1,214-case source run above. The rebuilt package has manifest SHA-256 `28ca7285b659cab01790ee469d926203319f6cae7e4fe3319bdc06a9b3c18682`, build `48c60713-bcb9-4d75-987f-ffa9fa13330b`, product digest `c6e2e7e968b4dc2a50379f22ed46d7d8e3c356d7a72338d4054722ac261055ce`, 265 payload files and 48 runtime files.

I independently hashed the actual rebuilt artifacts before QA: installer 173600302 bytes / `d28c9a587be2e728474361391fd018d9a7d340f5f4e7a888a0e4388db934a666`; blockmap 181205 bytes / `5d5f56d415d2249f5017a3c3a4238022ed92d36398f6ff884a80791552651615`; latest.yml 360 bytes / `3addd10313d2f5c9788b2974ad3cd997757230ff57edbadcf389045b4abc1eb1`. All match the new manifest. The old package was not reused or accepted.

One reviewed run used fresh `shared/packaged-v020-final-5/`, original session `91454`, start `2026-10-21T09:21:37.6358479Z`, exit 1 in chunk `068118` at `2026-10-21T09:22:02.7945078Z`. Literal SHA-256 `76b5577435d7ed2c78cce76d8c6b6ce4e2e8bbe9d9c92ef1d50be7318540b556`; driver 7c07ab76 unchanged from the diagnostic workflow.

Actual UI discovery, all seven routing variants, tooltips and manual Save assertions passed. A separate closed-private-catalog read (chunk `220fac`, read-only/query-only BEGIN, one-second busy bound, three-second progress interrupt, rollback/close) confirms the review at revision 3 with title, universe/cycle and distinct folder/Artist authors; exactly one candidate_context and one durable Entered by you source were saved. That source records actor=user and the exact entered values. Approval remains 0; saving evidence did not approve or queue the book. QA-1 is CLOSED by actual packaged UI plus persisted data, not merely the developer's unit test.

I visually inspected `metadata-1280.png` and `metadata-720.png` from that run. Both display v0.20.0, the successful saved-source message, the reviewed destination, distinct author credits and the new metadata controls without a blocking visual defect. The form stacks at 720. Readback of geometry JSON finds 51 visible interactive-control rectangles at each width, zero pairwise intersections exceeding one pixel in both dimensions, and document scroll widths 1265/705 versus inner widths 1280/720. The included-source table keeps its existing local scroller at 720; there is no page-wide horizontal overflow.

Screenshot SHA-256: 1280 `6ed4522c51c0afe023a1679f790f4b0fb28c114b847df611aaa6f91b4f5d0962`; 720 `804d3a06cc64e4b44f9d0305a9cf4f16ea4ee1c0a35e91123a67bfa1392698ac`. These are actual captured pixels, not a headless-only visual claim.

The run then acknowledged the actual window.close request (CDP id 64) but its next synchronous window.closed CDP evaluation (id 65, window-close-sync-facts) did not respond within eight seconds. The independent fresh backend probe was after that evaluation and was not reached. This does not establish a dead app/backend or a product Close defect. No normal Quit result was produced. Owner cleanup closed all 15 retained processes, complete output and unchanged full post-payload inventory, elapsed 22844.5925 ms. Overall release remains NO-GO until the independently reviewed split Close/normal-Quit acceptance is actually executed; no duplicate or unreviewed rerun is allowed.

## Paired packaged lifecycle acceptance, 09:35–09:36 UTC

Both runs bind the unique release source and manifest fields above: source `f0c39197bff78401af630c83fe963e76d687b57d`, manifest `28ca7285b659cab01790ee469d926203319f6cae7e4fe3319bdc06a9b3c18682`, PACK3 build `48c60713-bcb9-4d75-987f-ffa9fa13330b`. The reviewed controller was `18f03e45d512d150528ad8006d218062932cc74a40b2791eb74242c9c6c4317f`. Each owner retained the original 600000 ms total budget, exclusive new private root, hidden/muted launch and complete pre/post payload verification. A completed before B started; neither was duplicated.

### A: actual desktop Quit PASS

Evidence: `shared/packaged-v020-final-6-ui-quit/`. Driver `9889035e90ca56c391524bcab4fa6162b51aa07bdfdaffc0b32812a4407cdebc`; literal `e875b1f0dfd9c2fdb4929b758fd9290b3ebb6b59c0567e5bfe2ae5a21166d875`. Original exec session `20691`, start `2026-10-21T09:35:46.8603937Z`, terminal chunk `5aff23`, exit 0 at `2026-10-21T09:36:04.3257257Z`.

Actual package UI/backend versions were 0.20.0. Discovery found two candidates; seven routing variants, tooltips and actual manual Save passed again. Save retained the entered review, kept approval false and displayed the saved-source message. Both originals remained unchanged. The 1280/720 screenshots were visually inspected; the form wraps/stacks within the page, with recorded document widths 1265/705 against viewport widths 1280/720 and no blocking visual defect observed.

Actual desktop Quit was requested at `09:36:02.141Z`; packaged process exited naturally with code 0 at `09:36:03.148Z`. Both ports were refused afterward. Owner `ok=true`, `closed=true`, `forced=false`, `timedOut=false`, complete output; native active/assigned/listed 0, all 15 retained processes signaled, complete final zero. Owner elapsed 15148.4371 ms; full post-payload and input hash verification passed. Focus events were 0. This independently closes the natural-Quit coverage gap; native tray input was not exercised.

### B: STOP, Close-to-tray target assertion FAIL

Evidence: `shared/packaged-v020-final-7-close-tray/`. Driver `4a0263e0285642818a3e0b9266e4250421c60536d4c8ccc313ed97ff7175bbe4`; literal `d1bfa0b449d37592deec650c8212610ea3305e7cdb3a2018bd81c4357b2c0b50`. Original exec completed once, exit 1 in chunk `f2859e`, start `2026-10-21T09:36:25.6601168Z`, terminal `2026-10-21T09:36:30.7628451Z`.

The trace records the actual Close request at `09:36:28.718Z`, its CDP acknowledgement at `.723Z`, then an independent authenticated backend HTTP 200 at `09:36:29.245Z`. The version 0.20.0, same initial backend instance/PID, port 5214 and `closing=false` assertions passed before the next assertion failed. At driver line 72, stage `window-close-target`, the `/json` response contained zero page targets matching the backend origin, where one was expected. Raw `/json` was not persisted, so other target types and the cause are unproved. No post-hide renderer Runtime evaluation or focus observation was made. The intended instance-bound backend-shutdown stage was not reached, and no `packaged-result.json` or final action report was produced.

Owner failure cleanup completed: `closed=true`, `forced=false`, `timedOut=false`, complete output, active/assigned/listed 0, all 11 retained processes signaled, complete final zero; elapsed 2738.2915 ms. Full post-payload/input hash verification passed. These are failure-cleanup facts, not a normal-Quit claim for B. QA stopped and reported to Jane/Ender without edits, retries or product-cause assumptions. Close-to-tray acceptance remains incomplete pending a separately reviewed disposition.

### B metadata diagnostic: STOP, original page absent from both metadata lists

After a prelaunch pin mismatch was caught without launching anything, the revised exact pins received independent clearance and were frozen through completion. One diagnostic ran with driver `9e1950a9ba7547276b405e9e5ae29cbcb2f8fc2d12e0ccc7b286b4adeda9b5ee`, literal `99fcb9d7876dcb359e94c820591f9dd789449f7859295f71b0bf026f3b1cb8cf`, owner `0a57dbfd736ed7a04deaf5e3633e07330d009e847d08c2194bc74c43e9c68dab` and the unchanged controller/artifact. A was not rerun. Evidence: `shared/packaged-v020-final-8-close-metadata/`. Original execution completed exit 1 in chunk `d1c9b3`, start `2026-10-21T09:42:35.9252132Z`, terminal `2026-10-21T09:42:40.9457690Z`.

The persisted `after-close-metadata.json` identifies the original page as `94A74286B396F3B281DEF9211602BDCB`, type page, origin `http://127.0.0.1:5214`, path `/`. After Close, fresh authenticated backend facts were version `0.20.0`, instance `ec37b9ce68f596534d098571e51bc480`, PID 57596, port 5214 and `closing=false`. Both sanitized HTTP target metadata and independent browser `Target.getTargets` metadata were empty arrays; `browserMetadataError=null`. The strict exact-original-page assertion therefore failed at driver line 88. `appExitObserved=null` records only the app-exit promise observation at that point; it is not a native-process liveness measurement. No post-hide renderer evaluation or focus probe was used. Cause remains unproved; a surviving backend is not complete Close-to-tray acceptance.

Failure cleanup completed: owner `closed=true`, `forced=false`, `timedOut=false`, complete output, native active/assigned/listed 0, all 11 retained processes signaled, complete final zero; elapsed 2697.3492 ms. Full post-payload verification passed within the original budget. QA stopped and reported the actual evidence without a retry or fix. The verdict remains NO-GO pending reviewed resolution of Close-to-tray coverage.

### Final native-Close B: PASS

The preceding JavaScript `window.close()` runs used a different test primitive from the desktop main-process `win.close()` route. They remain failed historical attempts; their missing targets are not promoted into product-Close acceptance. Ender's separately reviewed correction invoked the packaged app's fixed `--close-window` route through the same payload, private profile, environment and working directory, hidden and muted. This exercises native `win.close()` without native input or the real user instance. A's previously accepted desktop-Quit/UI/Save/visual evidence was reused, not rerun.

One native-Close B ran in `shared/packaged-v020-final-9-native-close/`, start `2026-10-21T09:47:52.8532284Z`, terminal `2026-10-21T09:47:59.6902595Z`, exit 0 in chunk `a643a1`. Exact frozen driver `571f82e56fbe74af3e449557814329f2fd84323f9340a9ed8f2b086f54b29037`; controller `190abc9d24273a4822166ecbd2a8d4e862e82b16c4eecd12197d15cc74304fd2`; owner `36b3c25ed327f50627bcdacb01c772fddd3cf2b661f158f1fdb07f640830c568`; literal `6c8631ffe77ead7df229917d6de4ea560b749d69202f63645aa7df3e82e7341f`. Product source, manifest and build remain the unique release identities above.

Native Close was requested at `09:47:55.849Z`; the secondary command exited naturally with code 0 at `09:47:57.681Z`, within its eight-second limit and the original 600000 ms total budget. Sanitized HTTP and browser target lists both retained exact original page `58A6B3367AF018362499E2C5D19F1CB8`, type page, origin `http://127.0.0.1:5214`, path `/`. Fresh authenticated backend state was version `0.20.0`, same instance `7a0a320db4d96d0189255545064a38a5`, PID 89864, port 5214, `closing=false`. Thus the native Close route preserved the original page and responsive backend. No post-hide renderer Runtime evaluation or focus probe was made.

Instance-bound backend shutdown was explicitly requested at `09:47:58.220Z` for cleanup; the primary process then exited naturally with code 0 at `09:47:58.521Z`. Both ports were refused. This cleanup is not described as a second desktop-Quit test; A supplies that coverage. Owner `ok=true`, `closed=true`, complete output and actual `BOOKS_PACKAGED_QA_PASS`; no forced termination, timeout, overflow or closure error; native active/assigned/listed 0, all 12 retained processes signaled, complete final zero. Elapsed 4513.9235 ms. Full post-payload/input hash verification passed within budget.

Limits remain: no native tray/input interaction, post-hide renderer/focus observation, provider network/conflict interaction, full conversion in this packaged smoke, installation/updater execution, additional-source activation or live migration. The accepted package's installer-equivalent payload and versions are certified, not an installation into Sergei's live setup. No real library, iTunes operation, source-code write or user-app control occurred.

## Findings and pattern alerts

The completed declared automated check passed, but the actual packaged workflow has this open finding:

| ID | Severity | Reproduction and actual result | Status |
| --- | --- | --- | --- |
| QA-1 | Blocker | Scan the two private WAV books; choose All candidates; open Manual review; enter the UI fields for title, author folder, Artist author, universe and cycle; press the enabled Save preview metadata. The valid form and confirmed lease are refused with **Review fields are incomplete or unknown**, and no review/manual evidence is persisted. | CLOSED in f0c39197 / PACK3: actual UI Save succeeded; private catalog contains the exact durable manual source and review while approval stays 0. |

Screenshot/layout acceptance and A's actual desktop Quit/natural exit passed. The final native-Close B preserved the exact original target and fresh same-instance backend, then completed explicit private cleanup and natural exit. The earlier JavaScript-close target failures remain historical evidence of the incorrect QA primitive; no open product blocker remains in the declared release scope.

Pattern alert PA-1: the accumulated QA fixtures and launch contracts had drifted from the app (runtime containment, ancestor npm configuration, shell spelling, short-path layout, worker lifetime and retry copy). Disposition: fixed through separately reviewed changes before this candidate; retained failed evidence prevents a nominal green being promoted. The current sender/receiver both execute all declared work and match. Do not remove assertions or broaden deadlines to hide recurrence.

## Verdict

**Verdict:** GO

Reason: corrected source checks, actual packaged manual Save/persistence, inspected visuals, A's desktop Quit/natural exit and final B's native-Close target/backend preservation all passed for the unique release source and artifact manifest above. Both accepted runs proved refused ports, complete owned-process zero and unchanged post-run payloads. Session scratch and failed-run evidence are preserved for Sergei; agents must not clean it.
