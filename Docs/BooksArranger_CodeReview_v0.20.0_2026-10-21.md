# Code Review — Books Arranger v0.20.0

## Header

```
Reviewer: Senua (Code Reviewer), opus-equivalent review tier
Date: 2026-10-21
Tool: Books Arranger (Electron / Python)
Release: v0.20.0
Commit range: c2abd97861d6c4ba7df40f3298f784a9c0a6b986..f0c39197bff78401af630c83fe963e76d687b57d
Release source commit: f0c39197bff78401af630c83fe963e76d687b57d
Baseline: endpoint certified in BooksArranger_CodeReview_v0.19.0_2026-10-19.md
Reviewed source: C:/Antigravity Projects/Worktrees/Books Arranger/qa-0.20.0
Branch: codex/books-qa-0.20.0
Files changed: 373 files, +23730 / -823 (includes retained engineering reports, experimental QA sources and reviewed closing corrections)
Stand-down dimensions: none
```

The report is deliberately written in the original desktop checkout's Docs directory. The frozen QA worktree was not edited. This report certifies the endpoint above; later product edits require a recorded closing delta review.

## Summary

Reviewed the accumulated product changes and their admission/disposition dependencies: durable bulk retry requests and Pause/start fencing; SQLite-only scan replay and coherent progress snapshots; hierarchy, multiple sources and manual evidence/choices; output relocation and effective-location consumers; producer isolation/retention; finite MP3 tag preservation and narrow M4B admission. Read the changed production paths, focused test contracts, Electron configuration and staging boundary. Incorporated the already completed finite source reviews for the experimental native QA components, without treating their unimplemented or unproved runtime contracts as release requirements.

No open Critical or Major finding remains. Two Major findings at the initial 675d0f3 candidate were corrected and independently re-reviewed in the six-file closing delta committed as bf9152e. The findings below remain as review history, with their closing dispositions recorded separately.

## Rubric

### 1. Security

- Status: Pass. New HTTP actions retain the existing trusted/token control gate, validate candidate/job identities and bounded request shapes, and derive filesystem targets server-side. UI evidence uses text nodes and checked source links. Electron retains context isolation, sandboxing and disabled renderer Node integration. No new shell interpolation or credential exposure was found.

### 2. Correctness & Logic

- Status: Pass. Historical M1 below is closed in the recorded closing delta.
- **[Major] M1 — `organization.py:18`: author folder selection ignores the reviewed folder name.** `canonical_author` takes precedence over `author`, and the resulting variable drives both the directory and filename. The UI still presents `author` as “Author folder name” and `canonical_author` as the Artist-tag author. For a standalone or single-author cycle, entering a verified folder name distinct from the Artist credit has no effect. Migration uses the same planner and therefore proposes the same unexpected folder. Separate folder-author selection from canonical tag/stem credit, preserving the canonical author metadata. Add a fixture with different folder/tag spellings and check normal, single-cycle and migration routing; do not alter accepted multi-author/universe placement.

Retry submission now distinguishes requests from admitted jobs, retains waiting/refusal reasons, and binds delayed queue/cleanup starts to a generation invalidated by Pause/closing. Queued route changes become explicit holds or distinct retry intents rather than mutation of frozen work. Provider/manual conflicts require evidence-scoped answers; choosing a result saves a draft and does not independently approve recording or media.

### 3. Crash / Stability Safety

- Status: Pass. Recovery and migration refuse uncertain identities or unknown artifacts; new SQL contention replay contains captured SQL changes rather than repeated metadata/media operations. Source failures and catalog failures follow separate paths. Migration journals exclusive creation and final publication before subsequent phases, and interrupted removal remains conservative when owner closure is unavailable.

### 4. Performance

- Status: Pass. Historical M2 below is closed in the recorded closing delta.
- **[Major] M2 — `catalog_contention.py:33-44`: each file conflict token enumerates and JSON-parses every group under its root.** The membership filter in line 42 runs in Python after selecting the entire `book_groups` root. Scanner observations and transaction-time CAS checks call this repeatedly, including for unchanged readable files. The resulting work scales as files times groups and repeats on SQL retries; this is avoidable CPU/allocation and writer-transaction time in the large library where progress already stalled. Introduce an exact bounded membership lookup/index or equivalent captured membership representation while preserving detection of overlapping/newly added membership and all context/retirement/reacquisition guards. A scaling regression should verify unrelated groups are not fully materialized for every file. This is a source complexity finding, not a measured current-runtime stall diagnosis.

### 5. State & Data Safety

- Status: Pass. Relocation keeps original job/publication receipts immutable and stores an independently validated effective-location envelope. Copy and final proofs hash held complete contents; no-replace publication and destination durability checks precede original removal. Unsupported destination-directory flush retains the original. Source, staging, derived-output and replacement cleanup paths recheck location generations within their destructive writer transactions and retain exact native file protection through disposition. Producer recovery grants retention/isolation, not ownership or deletion of old files. Reacquisition reconciliation requires a complete accessible scan, exact source-incarnation observations and protected dependency checks before setting historical rows aside.

### 6. Input Handling

- Status: Pass. Additional sources preserve the first durable source key and reject overlapping/aliased roots. Output discovery exclusions and source/output roots remain distinct. Planner sanitization and native boundaries handle path containment; migration input files are bounded and hash-pinned. Metadata choices bind their displayed evidence signatures and source fingerprints, and refuse stale answers. The MP3 repair accepts only its finite terminal ID3v1 profile, verifies packet extents plus complete native PCM/frame equality, and encodes a protected working copy while retaining frozen original-source identities.

### 7. Maintainability

- Status: Pass. New routing, publication bindings, contention handling and evidence decisions have separate modules with explicit callers. The duplicated root/manifest compatibility logic has a narrow documented legacy default rather than broad normalization. M1 and M2 are tracked in their functional dimensions and are not counted twice.

### 8. Doc/Code Drift

- Status: Pass. Changelog and source explicitly disclose inactive general serious-audio-damage classification and retained recovery limitations. M1's contradictory field behavior is recorded as a correctness finding. The extensive experimental QA reports describe scoped source/engineering results rather than product QA success; those reports do not substitute for the current candidate's checks.

### 9. Build & Release Hygiene

- Status: Pass. Candidate package and lockfile both name 0.20.0. Electron packaging includes desktop files and the staged backend/runtime; backend staging copies root Python/web product files, while experimental `scripts/qa-native` and its uncompiled watchdog are outside that packaged application route. No experimental POST/guardian/native launcher is required for the normal canonical entry check. Release artifact acceptance, packaged QA, installation and conversion resumption still need their separate actual evidence.

## Verification and limits

### Closing source delta — bf9152edc769507e73493fd5e41d6e4441fb4791

Read-only Git inspection confirmed that the delta from 675d0f3 contains exactly `organization.py`, `groups.py`, `scanner.py`, `catalog_contention.py`, and their two focused test modules. M1 is closed: path/stem selection now prefers the separately reviewed `author`, falls back to `canonical_author` only when blank, and leaves Artist-tag credit unchanged. Three new fixtures cover distinct folder/tag spelling, standalone routing and the fallback.

M2 is closed: an exact root/path/group membership index replaces per-file whole-group materialization. Existing Inventory startup backfills it within its writer transaction; group INSERT/UPDATE/DELETE triggers maintain membership atomically, including INSERT OR REPLACE. The indexed lookup still captures complete matching group and context rows, overlaps and newly added membership; no connection-local data-version shortcut was introduced. Seven new written controls cover backfill, changed review/context/membership, overlap/root boundaries, rollback, replacement, malformed membership and indexed query/no-JSON-scan behavior. These controls were read, not executed by Senua. Correctness/Logic and Performance are **Pass** at the final endpoint; the finding paragraphs describe the initial candidate only.

Reviewed raw six-file SHA256 pins at closing inspection:

| File | SHA256 |
|---|---|
| organization.py | 6245f3c934b73048514be795f4cbcf9b48df33f64ec4894a7d752afb8649554f |
| groups.py | 23bad0097f5e1e91e71a98c086fba839f0f8c3b45a776ff800dfdd3aa6c3ad72 |
| scanner.py | 18f4e78f2fd9a067b2ea37ec3d4242dd54fc9eecb8b11c574ee9f8ef7a967dac |
| catalog_contention.py | beea6a57c3598b232149d7ae9310d242fc618118cdf7a4cc120c73c73268b1e2 |
| tests/test_organization.py | a85bfa758d67e4fb84a44c39f413d257b04cabd319d7e1528e6629e299e22fff |
| tests/test_catalog_contention.py | a899a5350c685ddb30b236f09415f4392525db27cab9f327165b8ed510f156a5 |

Release artifact manifest SHA256: 28ca7285b659cab01790ee469d926203319f6cae7e4fe3319bdc06a9b3c18682

### Current corrected-source checks and actual artifact binding

The actual current manifest hash above was independently read and binds reviewed source `f0c39197bff78401af630c83fe963e76d687b57d`, product digest `c6e2e7e968b4dc2a50379f22ed46d7d8e3c356d7a72338d4054722ac261055ce` and build `48c60713-bcb9-4d75-987f-ffa9fa13330b`. Its actual schema is `books-desktop-artifacts-v1`, version 0.20.0, with verified shell/backend 0.20.0 and installer equivalence. All three actual artifact hashes independently match: installer `d28c9a587be2e728474361391fd018d9a7d340f5f4e7a888a0e4388db934a666`, blockmap `5d5f56d415d2249f5017a3c3a4238022ed92d36398f6ff884a80791552651615`, and update metadata `3addd10313d2f5c9788b2974ad3cd997757230ff57edbadcf389045b4abc1eb1`.

Current v8 sender and independent receiver both passed all 1,214 Python cases, 57 Node tests, 16 frontend scripts and eight syntax checks, with matching exact canonical receipts. Independently read/hash-verified logs: sender `c8f83dbcda9fc723a2fdc57ea7ed1f6885ec2a6660b8178de84dee4c1b2631dc`, receiver `2b697f2e68578de6c614cc910521bc71969142acbf31bc64bafca25102288d8f`. Both original checks exited zero, complete output, no force/timeout/overflow; native active zero, all 2,648 sender and 2,647 receiver retained handles signaled. The receiver's incomplete intermediate membership samples are explicitly retained in evidence; final complete zero/signals and closure were proved.

The corrected artifact's exact one-run packaged invocation was reviewed: literal `76b5577435d7ed2c78cce76d8c6b6ce4e2e8bbe9d9c92ef1d50be7318540b556`, fresh-root-only owner `597ea109cb085ade4e786da41051c4c7f94a05cb02a8b17dc8bbb67278124ace`, unchanged controller `18f03e45d512d150528ad8006d218062932cc74a40b2791eb74242c9c6c4317f`, and save-diagnostic driver `7c07ab76dfed68da60da72923e5837efab6168b59fc3fb6cbc70e508a55d1f78`. The six arguments bind this actual manifest and its matching unpacked build. Same original 600000 ms budget, immutable before/after payload verification, private roots/profile/catalog/ports and hidden muted startup remain. The driver preserves real UI Save, routing checks, source equality, screenshots, Close-to-tray/same-instance fresh backend, no focus and normal Quit; bounded diagnostic captures contain metadata and request status rather than tokens/headers/bodies. Actual packaged behavior and visual acceptance remain Futaba's separate verdict; construction acceptance does not assert installation, live backup, migration or conversion resumption.

### Historical rejected artifact and previous-endpoint canonical checks

The previous artifact manifest `a4c1c5f20ef41e292900ca4b2835bc93b4eb748a641498d9150f9e8f40af6b9c` bound source `c2f2e00e50e7b3d32384f424e79f88f8749128e2` and product digest `780887b59232c359d916f7ab69b47667296c30d1f3c4b0c22a9f86972292d3de`. It is now rejected following packaged Save failure and the corrective product change below. The historical manifest identifies schema `books-desktop-artifacts-v1`, version 0.20.0, build `b90eb16c-ec6a-4872-903e-51bc07449b99`, 265 payload members and 48 runtime members, verified shell/backend version 0.20.0 and installer equivalence. Actual manifest hash and all three release artifact hashes were independently read: installer `64dcf2c0b55e694c8ead9a3160be101e14cf67a95a106aa14527b9711f159bfb`, blockmap `381c9e404a7aa0a053cd319487a470fa0606ff421c48f44dc57de7eae2730b9e`, and update metadata `c0e8ac094a933814fbfa8ce6b04657fc7e1b65ded0049c7dc88c5b88e28fd1b6`.

The previous endpoint's actual complete sender and independent receiver passed: 1,213 Python cases, 57 Node tests, 16 frontend scripts and eight syntax checks each, with exact matching canonical receipts. No failures, errors or skips; both owners closed with complete output, native zero and all retained handles signaled. Sender log SHA256 `c71ecbff42bb4162212a7f179a2c515e96ed7b1e2711a5030a2eabbd374adb90`; receiver log SHA256 `abc962bf7984ec2cd396fcc59fcf2cd94c9114eddb94b9792ec1b6a3d11aa6ca`. These do not clear the new endpoint. Earlier failed runs described below remain historical failures.

### Closing HTTP Save admission correction — f0c39197bff78401af630c83fe963e76d687b57d

Packaged QA proved that the renderer always sends `universe`, while the HTTP review allowlist omitted it; both candidate and file Save requests were rejected before persistence. The three-line product correction adds this existing backend text field as optional, defaults legacy omission to blank, and applies the unchanged 1,000-character string bound. Required fields, unknown-key refusal, booleans, language/genre validation, source fingerprints and candidate revision checks remain intact. Read the renderer, both HTTP consumers and backend TEXT_FIELDS/save boundary. No open construction finding remains for this correction.

Reviewed pins: `web_server.py` `73cfb3b0b395fbb73d360ba6abf399769d62d753d6dfd01eff9ac70ce0ac296f`; `tests/test_web.py` `f4dad967b465e9de5a451c564d4ab034487a39c5dc8f8f4700a2fdbdfb558e92`. Tests exercise actual candidate HTTP Save and v2 universe preview, file Save roundtrip/Artist credit with preserved legacy file routing, legacy omitted field, malformed/oversized/unknown/missing-required refusals, unchanged saved review after refusal and unchanged source bytes. Whole HTTP receipt `37610985842efb1aae15618b2348a8f444e62941821282980ca56b2051d17d38` was independently read and hashed: 21 discovered/completed, no errors/failures/skips, original exit zero, complete output and owner closed/native zero with all four retained handles signaled. The initial overreaching file-preview test assertion's failed result remains preserved; the corrected test places hierarchy assertions on the candidate contract.

The new endpoint requires fresh matching canonical sender/receiver results, a rebuilt artifact manifest and actual packaged behavior acceptance. Prior source/artifact approvals do not substitute for these.

The exact hidden packaged-QA invocation was reviewed separately: literal SHA256 `5a5f7839428ee5b812d92a1cb61fdf53d9bb68ab16db9f5a8e64e28344e966b4`, owner `886ccfc8476b8f60683ccc762dc9ce667c83bda179d106a453f5e0a94a0bc522`, controller `18f03e45d512d150528ad8006d218062932cc74a40b2791eb74242c9c6c4317f`, driver `1ff0baf68084c74e9415f03d621885fb5413fda7b3476cdb21dd9e9e0f1ff298`. Its six artifact/driver arguments bind the actual manifest and unpacked payload above. The adapter verifies complete payload membership/bytes before and after, uses private fresh catalog/profile/roots/ports with hidden muted startup, and requires natural Quit exit zero, refused QA ports and enclosing native closure. This is construction acceptance for that one run; actual packaged behavior and visual acceptance remain Futaba's separate verdict. No publication, installation, live backup, migration or conversion resumption is asserted by this report.

The first packaged run did not obtain behavior acceptance. A diagnostic-only scratch delta was subsequently reviewed: driver `5a0deca6673d505be27f504a84f083fba8c4c1fad683c51d08377210d3492956` adds bounded trace records (at most 1,024 records / 262,144 bytes) containing method, id, stage and expression SHA, without evaluated values or tokens. Actions and the eight-second CDP / original 600000 ms total deadlines are unchanged. Diagnostic owner `becda9489367ef4eefd82e47a486264dbff250aa9876122fd2359ee9ffcebb0d` changes only the fresh private evidence root to `packaged-v020-final-2`; controller remains unchanged. Literal `3f41df7032628bf58fbe1a55be98416f5993984ec981774788069064c0975fe9` binds those exact inputs and the same actual artifact manifest. This clears one diagnostic invocation, not a diagnosis, behavior result or product change. Previous evidence remains preserved.

### Closing fixture-only delta — 99669aa3f91c887b10dd306e2eddb7fa9c4f63a2

The exact one-line change in `tests/test_mp3_tag_repair.py` (10297 bytes, SHA256 `47bdbd1738882681166daff082ff239b48a4299d08031dfa7cabbb09eb5411b5`) places generated `app-staging-*` output under the existing `BOOKS_QA_FIXTURE_ROOT` when supplied, preserving the original source-parent fallback. The immutable input SHA, output SHA, packet/frame/PCM assertions and original-source equality checks are unchanged. This allows a separately manifested immutable private input directory while generated outputs stay in the owned run scratch. No production code or canonical checker guard changed. Source inspection accepts this delta with no additional finding; actual execution remains Ender/Futaba's evidence.

### Closing integrated-check corrections — 00d9aaa689e220c6cff4582fd9fb699797ff3cc5

The committed correction set contains 17 source/test files and two diagnostic Docs, pinned in retained `shared/diag-main-20261021/consolidated-correction-pins.json` (SHA256 `a3de8ebac96e5124abd1b8498c1afe1643db2e629eb8fe93f97276bab0b82cc9`). All 19 current file sizes/hashes were independently compared with that manifest after commit. No open construction finding was introduced.

The only production change moves the unchanged reacquisition status projection into `audio_jobs.attention_summary`'s existing database read (file SHA256 `9477ab6d672cf30e77acaeeff32b653b159ea1ed8695a6951e8be52a8d7ce774`). It restores the existing one-read status contract without changing marker admission, media or retirement guards. Test corrections restore legitimate private DB/scan/task dependencies, current typed closing/refusal and guarded handoff contracts, move the misplaced main guard after its HTTP test methods, and align folder assertions with the accepted M1 correction. Existing safety assertions remain; focused tests do not replace the full gate.

The integrated checker now schedules exactly two isolated Python source copies while keeping the original declared pattern set and shared 540000ms checker / 600000ms outer-owner budgets. HTTP/server conflict modules share one serial batch; source/cwd/TEMP and mapped fixture paths are private per worker. Input copies are hashed before and after, both workers are awaited, combined output remains capped at 16 MiB, and each must report positive discovered/completed counts, exact assigned patterns, zero failures/errors/skips and successful exit. Repeated case IDs remain required occurrences. Added pure schedule controls refuse omitted or malformed completion. Reviewed pins: checker `2675fb32e9f96ded742dddc7e5026b129f06f89d41662c8707518373b60379df`, schedule module `abf092812063596022734bfbea012173827d3ba7bf09b09d1349d1f181f26d09`, controls `592d1f93ca2d45c473b3c1dd8e58594ae33498b1c011b1d4d574de399a4ecc60`.

Independently inspected actual scoped receipts: Sources three cases (`c3d34d17ddcbf4afd60bcd05d7be60d4a8158c11635abfa83e93b9395bfac2d7`), main eight cases (`24fbc683d6574c92ae73c7a77b80ad09a539972cd82ca71a10d7d766d11d41d2`), Audio twelve cases (`5cc67465474cc45d3c144729596af1a440234a49b8b3478e4c04a9ee027ac0a6`), and scheduler twelve controls (`72b45e7d5323fb2e4a02d4e4a7f5f0fce4a6187118c3a770bd06ec9718a08f7e`). They passed with complete output and proved owner closure; reviewer did not execute them. Earlier serial full-suite failure/timeout, header-only nominal zero and interrupted-owner results remain failures, not QA clearance. Current full-suite discovery totals must come from the new actual run; the historical 1193 count is not asserted for this endpoint.

### Closing short-layout and attention-fixture delta — cfae104e906c08053ff0cb80845f63ab3b465050

The next complete run exposed fixture failures rather than a new product-guard defect. This reviewed five-file correction shortens Python worker copies to `scratch/0` and `scratch/1`, maps only the series-backfill fixture AREA to `scratch/s`, and restores the original `scratch/source-fallback-2026-10-11` prerequisite in each worker before discovery. The approved concrete run parent is the ordinary Books worktrees sibling `q20`; each canonical entry child remains fresh, with no junction alias. Source hashes, process ownership, discovery/completion accounting, output bounds and the original 540000/600000ms budgets are unchanged. The product's 240-character output guard remains intact; pure controls exercise concrete representative 224/213-character fixture destinations. Pins: checker `9df169a136f622a3e22a866ea08d217dbc3b0c1f965f2424cfa58c9e75b78f5a`, helper `118f408a541d820025522e1808a723fe4c326bd0b3c0dff8e1f1ea24105f7961`, controls `848b601fd93584d1c280f3d25d9d62826ab8632d110e957c3e1a3373ccaf6fd2`.

The attention module fixture now supplies its real private ProducerRecovery collaborator and source root, includes the implemented reacquisition ordering, and checks repeated Repair's typed refusal plus absence of a second child (`aa3124726f4449456faecbd09cf39d01f392b6b290f9bf2a55a835033f76e56e`). No production code or guard was changed. All 21 module tests passed in the inspected receipt `8b850808874561fad5a1b39a50d27c9c50e95fc5f2f5f49260d542324c2cb7d8`, with complete output and zero/signaled owner closure.

Whole destination-admission, series-backfill and standing-admission modules were actually checked under the final short layout: 55 discovered/completed, no skips, all passed, source copy unchanged; retained receipt `112acd3623d904cd5a68b0aead7d81187fd0ae9825197acaa856b02ba2beebac`, owner closed with complete zero and all 810 retained handles signaled. Fourteen layout/accounting controls passed in `fe9e454d7d921f10c989f74002115b3d9d72d761a7dd18482d875086d3063a05`. These are scoped developer results independently inspected by Senua, not execution by this reviewer or full canonical QA. The previous completed 1213-case run's failures remain failures; a fresh matching sender/receiver run is still required.

### Closing fixture worker-join delta — 05894628c19d45c3a004b2873752385b598dae71

`tests/test_attention_repair.py` now captures the actual bulk worker, joins it with a ten-second bound, and asserts both thread termination and terminal run state before temporary catalog teardown (SHA256 `8b9f9fdb9af513a23231b81bf84aba3665807609e66fe8c7efe1fda3bccb71a3`). Terminal submission state alone precedes the worker's last SQLite receipt write; the previous fixture could race teardown against that write. No cleanup-ignore, production change or guard waiver was introduced. The whole module plus forty alternating RetryAll repeats passed: 61/61, no skips, complete output, owner closed with all four retained handles signaled; inspected receipt `ae37c01b14836f2b06654a0e005c4c6f5bf9d4e6da1d3aa7ce55107a5695b70a`. This resolves the fixture race, not a claim that drained status alone proves production closure. The prior full run's single teardown error remains failed QA evidence until the fresh full sender/receiver gate completes.

### Closing frontend-fixture delta — c2f2e00e50e7b3d32384f424e79f88f8749128e2

Six test-only files align stale assertions with the already implemented/requested distinction between saved retry requests and admitted conversion jobs: waiting-for-checks wording, new retry availability, output-issue totals, reacquisition strip ordering and request confirmation. Assertions for genuinely admitted jobs' Queued state remain. The automatic-search fixture now targets its real search-timer handle, verifies coalescing/cancellation and preserves the unrelated routing-preview timer instead of clearing all scheduled callbacks. No product UI, behavior or safety assertion was relaxed. Exact reviewed file pins are retained in `shared/diag-main-20261021/frontend-correction-pins.json`, SHA256 `0ce2e849470e8274da483c196b074523119d5bb74967ee11ac7eb203f47fa401`.

All sixteen frontend modules actually passed together, each with status zero, complete output and closed native ownership with all 36 retained handles signaled: inspected receipt `a6cda78efba08a693b96ae2e88baca77129705f2d5f244f24b6b0cce753d009c`, elapsed 2348.8486ms. This remains a focused frontend result. The preceding backend-only success (57 Node / 1213 Python) plus a frontend failure is not a full canonical pass; the new exact source endpoint still requires fresh matching full sender/receiver receipts.

- Source review only: no tests, compiler, native fixture, product process, installer, Git mutation or library operation was executed by this reviewer. Read-only Git inspection was explicitly authorized by Jane. The quarantined unknown controls file was not opened or adopted.
- The existing canonical entry route was separately read: one 600000ms wall budget covers identity validation and all declared checks, with per-check private Job ownership, native zero/retained-signals and checked closure. Original tool completion followed through the same returned session is observable without experimental PostToolUse serialization. Ender/Futaba must independently obtain matching actual receipts for their current context/candidate.
- Serious audio damage is **not** generally classified by this candidate: `mp3_tag_repair.py:86-93` deliberately refuses an assessment without independent positive damage proof. A failed or partial diagnostic therefore stays attention rather than automatically becoming Need to reacquire. Existing reacquire holds/reconciliation are not evidence that this missing classifier has run. This disclosed functional limitation does not justify weakening preservation checks.
- Source acceptance of migration does not prove NAS directory durability or complete the live migration. Each actual publication still needs its reviewed plan and successful concrete capability/content checks; originals remain when removal proof is insufficient.
- Earlier experimental native failures/UNKNOWN results and uncompiled native parity remain unchanged. They are not promoted to production QA clearance or imposed as new product release gates.

## Verdict

- Total Critical: 0
- Total Major: 0 open (2 closed in bf9152e)
- Total Minor: 0
- Always-blocking safety floor: intact in the reviewed range.

**Verdict:** RELEASE CLEAR

M1 and M2 were advisory findings under the studio's canonical severity rules and are now closed. This construction verdict does not replace Futaba's independent behavior verdict or Sully's exact-version artifact checks.
