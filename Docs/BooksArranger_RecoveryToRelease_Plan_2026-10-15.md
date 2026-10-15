# Books Arranger — recovery to Windows release plan, 2026-10-15

Owner: Ender. This is a planning/source-preparation checkpoint, not execution, deletion, tested repair or a release. Deliverables belong in this maintenance branch first, then the accepted repair is integrated into the Electron candidate. No live application action is authorized by this document alone.

## Goal and order

1. Release space from provably redundant **failed derived outputs**, before requiring the entire library to finish.
2. Repair M4B preservation and safely retry held books; prevent new attempts from piling up.
3. Integrate the accepted backend into the standalone Windows app, independently verify it, then have Sully publish the installer.

The large failed checked/compatible files are **not inherently required forever because their jobs are unfinished**. The earlier 61.13 GB classification established they were not disposable under the shipped publication-only cleanup path. It did not establish that all those failed outputs must be retained permanently.

## Saved baselines and present runtime

Maintenance checkpoint: branch codex/books-attention-fixes, supplied pushed HEAD 880e267, source-only and untested; 13 focused test methods and zero executed. Electron checkpoint: supplied 75e46c1, candidate 0.16.0; no newly verified installer. Sully rechecks exact full HEAD/tree/remote/concurrency state before changes or save.

The last reviewed runtime observation was installed v0.15.0 PID 54960 / generation 134365295749473510 / instance 721b890bb723a4b3d22fffb3edf35f1c. Its last format observation had a current 135-input M4B normalization job and seven pending jobs, three single M4Bs and four multi-input sets. This is historical evidence, not a current running/ownership claim. Reverify through a separately reviewed ordinary read-only observation before any live action. This planning turn performs no app action, retry, pause or deletion. The heartbeat remains paused.

## Phase A — exact Books proof route and smallest functional check

Ender prepares a **Books-owned fixed operation**, Senua reviews its contract and bounds, the shared safety maintainer coordinates the one sequential registration window, and Futaba independently repeats the identical operation. This work is not waiting for a QuickLaunch app release.

The host enforcement repair has sender/receiver PASS; the remaining gap is that its enrolled command contract is specifically QuickLaunch lock-only. Unmatched commands still reach P9. No generic compatible Books operation is currently registered. Preserve the existing QuickLaunch contract and fallback P9. Do not edit hook/trust configuration from this Books task by inference.

First functional operation: run only the 13 deterministic maintenance clock/SQLite regressions, with no real books, conversion, media child, UI, network, library path or live catalog. This proves the small source checkpoint and operation ownership, **not** the backlog container-preservation fix.

Prepared unexecuted local entry:
- canonical scratch/resume-2026-10-15/first-proof-maintenance-13.py;
- SHA-256 5986ac0b003180921c0d8c047d641ac934dcdebb75da205fcedc66510fdb4862;
- exact logical child argv: C:/Python314/python.exe -I -S -B <that exact entry path>;
- child cwd: the absolute maintenance-worktree path;
- entry explicitly inserts the pinned maintenance source root for discovery, requires exactly 13 cases, private temp and no skipped tests. This avoids incorrectly assuming Python -I plus bare unittest discovery automatically exposes the application modules.

Exclusive output root, to be created natively by the reviewed owner only: canonical scratch/resume-2026-10-15/first-proof-maintenance-13; private TEMP and TMP both point to its tmp child. Current code has not created that directory. Proposed child environment is a fully enumerated whitelist: SystemRoot/WINDIR=C:\Windows; ComSpec=C:\Windows\System32\cmd.exe; PATH=C:\Python314;C:\Windows\System32; PATHEXT=.COM;.EXE;.BAT;.CMD; TEMP/TMP=that exact private tmp path. Review resolves exact Windows string/case representation before freezing; nothing extra is inherited. Isolated/no-site/no-bytecode Python excludes user startup customizations. Any additional required variable is a contract revision, not a silent addition.

Reuse assessment: existing qa-owned-guardian.mjs SHA-256 4a521ec6a8844b8ffa625ade3bb9b0107ce59f62b33a45f7c5be4bb5d46824a2 already provides native input leases, private Job assignment, whole invocation 600000 ms deadline and closure evidence. It supports **only inert-controls, assemble and entry**, fixes bootstrap cwd/environment, and currently launches its child with studio cwd and STARTUP environment. It cannot directly run this maintenance entry/private temp. Do not pass arbitrary Python argv through it.

Choose the smallest compatible integration after reviewing the actual protocol: use unchanged protocol-2 entry only if its real canonical checker can bind this exact maintenance source/version/13-test graph and private cwd/temp; otherwise add one narrowly fixed maintenance operation reusing the existing Job/deadline/closure implementation. No generic interpreter launcher or new safety framework. In either case, prepare the literal full command, exact classifier/verifier/authenticated adapter and outer-loader binding against fresh shared preimages; Senua approves before coordinated registration/trust/load of the changed definition. Books-specific harmless positive and altered-command/blocked-negative proofs must pass under that actual loaded definition before the functional operation.

Capsule completeness remains a required deliverable, not a claim made here. Existing SourceInputs lists 40 application/test files, but lacks complete interpreter stdlib/native runtime, actual import closure, guardian/checker/Koffi/native optional-addon maps and final adapter/loader bytes. Ordinary static pins of the five current checker files and local entry are recorded in the draft capsule. Before execution, freeze and independently verify complete actual source/import/runtime/helper trees, copied inert inputs, final argv/cwd/env, output native identity and loaded contract preimages. The prior refused plan digest must not be computed through an alternate route. A complete new approved literal plan digest belongs to its supported entry.

Enforce **600000 ms total**, assign the suspended child to the private Windows Job before release, retain exact handles, and prove all descendants exited before closure. Require success exit, all 13 cases/no skips, result.closed true, forced/overflow/truncated false, native zero true and unsignaled zero. Preserve exact IDs/counts, stdout/stderr hashes, timing, loaded source/runtime/operation pins and output inventory. Deadline or incomplete closure is failure even if assertions passed. Guard/AV/P9 refusal means stop; no alternate encoding or transport. Analysis, media proof, full regression and packaging need separate fixed operations.

## Phase B — release failed-derived space without sacrificing unfinished work

Ender designs a dedicated **app-owned failed-attempt retirement** operation; Senua reviews its safety contract and Futaba tests private failure/crash fixtures. The shipped working_files method cannot do this because it requires completed publication, so it must not be repurposed by lying about job state.

Admission must freeze the exact failed job, manifest hash, attempt ID, failure/journal and every reference/ownership relationship. Refuse active/running/queued attempts, live child or handle use, publication/output intent, output/replacement/source-cleanup references, changed snapshots, unknown content and changed identity. Use the app's owner/admission locks, not an external live-database deleter.

For each candidate:
- prove complete source snapshots still match their frozen manifest bytes/native identities and remain protected; originals and original/replacement recovery are untouched;
- separately prove the proposed files are redundant failed **derived** artifacts, rather than input snapshots or unique recovery. Current hashes alone are not retroactive producer receipts;
- collect exact native current identities, hashes/sizes, metadata/error evidence and the selected byte ranges/roles; preserve necessary unique diagnostic examples and compact durable evidence;
- where old producer records are incomplete, use a separately reviewed explicit **legacy enrollment** proof bound to the historical marker/attempt/journal plus complete source/payload/provenance correspondence. If that cannot be proved, leave that file;
- commit exact authorization/removal intent through compare-and-swap while native file/ancestor handles remain held, dispose only those handles, reconcile durable crash receipts and confirm final absence. No directory sweep, name/age-only rule, original/stream exception or invented producer proof.

This can potentially reclaim a substantial part of the historical 61.13 GB before the M4B writer is repaired, **but no exact reclaimable amount is certified**. Source snapshots and the ten completed original-stream cleanup sets remain outside this scope. Reclamation is measured from actual disposition receipts and fresh free-space observations, not a folder total.

First proof should be a tiny private failed attempt with two derived artifacts and a protected source, plus negative changed-source/intent/reference/unknown-file/active-job cases and crashes at each durable transition. Then a reviewed read-only plan for real explicit files, followed by independent exact-operation clearance and bounded app-owned application. No bulk actual deletion is part of this planning checkpoint.

## Phase C — stop new accumulation and preserve M4B timing

Implement early durable producer receipts for every future created artifact/attempt, including failure/crash cases, so cleanup does not depend on reaching successful output validation. Keep immutable source snapshots separate from rebuildable derived output. Preserve required recovery/diagnostic bytes; do not retain every failed full duplicate merely for a log.

Before each phase, reserve a conservative computed working-space requirement based on actual source duration/channels/rate/selected exact PCM representation and existing retained attempts. One active owned conversion plus its reservation must not silently consume capacity promised to a retry. Refuse/defer when peak space cannot be covered; a failed estimate/ENOSPC ends at a safe checkpoint. Reuse existing policy where present. Any discretionary OS free-space reserve or user storage ceiling is a product decision for Sergei; this plan invents no GB/percentage threshold or new recovery duration.

A new attempt starts only after the previous redundant derived set has been safely retired or adequate capacity for both has been proved. No repeated unsupported conversions just because the queue is running. Unknown/needed evidence stays and blocks that retry if necessary.

For the 81 observed media holds, use a source-container metadata writer that retains exact original audio/chapter sample descriptions, timing, movie/audio clocks, edits/ctts/trim, and media payload, changing only approved tags/cover and exact validated chunk offsets. Reuse bounded quicktime_chapters atom infrastructure, but explicitly support/refuse source layouts, cover/chapter/video track relationships, versions and stco/co64. No blind dropped video track, float tolerance increase, lost initial gap or source quality reduction.

Smallest first preservation proof after Phase A is executable: one tiny synthetic unfragmented M4B fixture with a nonzero edit/offset and non-1000 movie clock. Change a tag with a measured metadata-size delta, then demonstrate identical exact rational timeline, compressed packets/order, decoder/trim, all-channel native PCM and chapter mapping, and unchanged source bytes. Include a deliberately altered edit that must fail. No real library input is needed. Only then implement/support more profiles and test privately against copies of the three retained representative cases under a separate bounded media capsule.

App-owned recovery admission must bind the old frozen manifest/attempt/failure to the newly proven policy and fresh protected source evidence, archive the exact old journal, and create a new attempt under normal queue rules. Old retryable:false is never silently flipped. The one historical SQLite lock failure lacks native code proof and needs that explicit admission or remains held. No raw database reset, failed-output adoption or blind new Start.

## Phase D — complete backlog and ship the standalone installer

After Ender sender/Futaba receiver acceptance on the exact saved repair and Senua code review, Sully integrates only accepted repair/lifecycle changes into the Electron candidate. Reconcile backend, browser/desktop contract and packaged runtime together; verify current Brief, standing rules, desktop UX and build-guard records. Judy specifies any changed controls/presentation. Candidate 0.16.0 is not automatically today's final version; Sully owns the confirmed milestone version/lockfile/changelog.

Clear separate exact full regression and guarded pack operations. Declared historical 137 Python / 29 Node checks are not results; discover and execute the actual frozen graph. Build NSIS/standalone Windows artifact, verify ASAR/backend/runtime versions and exact artifact hashes, then Futaba packaged launch/core-flow/close-process smoke with private data. Desktop input checks follow the studio away-window rule. No real processing or installation occurs as installer QA.

Senua binds final review to the exact source/artifact; Sully commits/pushes explicit files, tags/pushes only the named version, publishes the GitHub installer and checks retention policy. Normal user-authorized application happens at a verified safe processing boundary, preserving completed records, checkpoints and recovery. Verify the new actual owner/loaded version before one admitted resume. Keep older local builds until the new replacement is built and verified. Automatic continuation remains paused unless Sergei changes that request.

## Owners, next concrete deliverables and present result

Ender: first fixed Books proof capsule/entry, failed-derived retirement design/private fixtures, preservation proof and working-space lifecycle. Senua: exact-operation and source/artifact review. Futaba: identical independent acceptance and regression/packaged behavior. Sully: every git operation, integration/version/release and immediate push. Shared safety maintainer: fresh preimage/registration window for the Books-specific handler addition, not a QuickLaunch product dependency.

Next deliverable is the completed fixed 13-case Books operation capsule and narrow integration proposal for review; concurrently prepare the private failed-derived retirement contract so space recovery can precede bulk conversion repair. No new product implementation begins from this document until its committed plan and executable proof route are ready.

Actual planning-turn deletion/retry/app changes: **0**. No reclaim or conversion completion is claimed. The scratch proof entry is unexecuted source preparation and not a registered runtime. Preserve it, existing evidence and active work. This plan and draft capsule are intentional deliverables; no verified disposable media output was created.
