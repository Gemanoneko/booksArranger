# Books Arranger v0.4.0: focused merge safety re-review

Date: 2026-10-10, Asia/Jerusalem. Senua. Prototype safety-floor audit of the actual merge implementation and new metadata/cover/directory-inspection routes. This is not a formal nine-dimension release review or a tagged-release clearance.

**Current safety floor:** CLEAR for immutable final-4 only. Final-2 clearance was withdrawn and final-3 was blocked; the final-4 section below records the corrected mechanism and exact mapped-volume proof. This is source-safety clearance to proceed to the authorized source-preserving technical pilot, not a claim that a real book or device sync has passed.

**Historical final-2 outcome, now withdrawn:** CLEAR, with 0 then-identified findings. Subsequent actual native probes disproved the directory-protection assumption. **Current final-4 open count:** 0 Critical, 0 Major, 0 Minor.

## Exact source binding

Reviewed immutable candidate `scratch/metadata-2026-10-09/frozen-final-2/`, manifest SHA256 `20b13676aa22e2474768b1e06daba6745cb35361a41fd59f4d9426cfedd27a4b`. Independently recomputed all 33 files listed by the manifest: 33/33 matched, no mismatches. Binding is to these candidate bytes, not an unspecified working tree or future commit. Compare any later promoted code to these pins before applying this clearance.

| Safety-relevant source | SHA256 |
|---|---|
| native_io.py | 0809d01d375110e1894f5d04a0b91b04897228ab3edbc768bcd10adec4812ef6 |
| audio_pipeline.py | 918487d2e9c9d3f3fcc9066dfa5cc75e0e970fa6d333d9f88ddcef89d5b610dc |
| audio_jobs.py | 4d4eb716fc732471687073b06ad301b73f6edb3bfd5f5c5f9d1f492b0ad27177 |
| merge_service.py | 83fac8920d59e8eaadb9f475c6845b57e89d1a1c4e2734e6db817cffc912ece4 |
| review_backend.py | a2808056c0473cc74bfee00108e1d803656f18e0274059c49b43c87fa985aadf |
| web_server.py | 3dbf2bf4443c82457b40d5e0a8efaa330f3c088ab23e4645614942ead17691cf |
| metadata_sources.py | e77b72cebdf06211d13ad9353629dd93cfbdb7fd464007628485c7f63bc0d010 |
| scanner.py | 9bde3dab61b5b2e38f74758295b84f8d872b11fc5af4828409f8ac6b6f64245c |
| groups.py | b4196880e82f662b16a0aa4d64d36734274361d85686371b801855a518e80cdd |
| metadata.py | 23a9f01764e6506d1450bea18ae379c7263aa1adf375cbf29668817e6ca8cc00 |
| app.py | 192ee63bc475219d02940e56dc785c830e84949a4e601689b3469184b9a095f1 |
| web/app.js | dd4aa087b4066ed3b5dd892f03b77cd3f976a011bb263945d1d474b8db346d62 |

The complete 33-file manifest also binds HTML/CSS, docs/launchers and tests; retain it with the immutable snapshot as review evidence. Source comparisons were read-only `git diff --no-index`; no repository git state was modified.

## Closure of initial findings

Historical blocked report: `BooksArranger_MergeSafety_Code_v0.4.0_2026-10-09.md`, SHA256 `10400EAC45F557689E1E8F9E18CAFACBB7C68439E01FB13C7C835F4ACA232947`, bound to `safety-core-1`. Its initial findings remain historical; this report supersedes their open disposition only for final-2.

**C1, cover-cache out-of-scope writes — resolved.** `CandidateReviewService` retains an ordinary configured path instead of resolving a redirected cache into acceptance. Creation and artwork writes hold `DirectoryBoundary` across existing ancestry, reject reparse entries and compare stored cache directory identities. New cached files use exclusive `xb` creation; existing artifacts are checked rather than replaced. Protected file reads reject reparse/non-file entries and deny concurrent writes/deletes. The containing merge-cache creation also uses the guarded boundary. The initial junction and dangling-entry write mechanism is closed in these pins.

**M1, destination temporary identity — resolved.** `publish_no_replace` opens the exact destination-side temporary with read/delete access and read-only sharing, rejects reparse/non-file attributes, verifies size and SHA256 through the held handle, then renames that same protected handle with `SetFileInformationByHandle(FileRenameInfo)` and `ReplaceIfExists=False`. Ancestry remains protected and is revalidated. The writer neither copies directly to the final name nor uses an overwrite/cross-volume fallback. Tampering cannot pass the expected hash and substitution cannot change the held file object.

**M2, process assignment after execution starts — resolved.** Both media execution paths launch suspended, mark ownership and assign the process to the kill-on-close Windows job before resuming the sole owned primary thread. Resume validates the thread's owner and expected suspend count. Assignment/resume failure tears down the owned work. Cancellation checks job accounting and waits exact acquired owned process handles rather than trusting a reusable PID or an accounting count alone. No broad process-name kill exists.

**M3, embedded artwork input protocols — resolved.** Artwork extraction uses the owned bounded media runner, restricts file protocols and forces the expected input demuxer. Source probing/decoding likewise forces known formats, and the outer concat path restricts its format set and uses safe staged aliases. Local artwork diagnostics/output are bounded; arbitrary citation URLs are not media inputs. Snapshot hashes are checked again after acquiring deny-write/delete protection before encoding.

## Added inspection and folder boundary

The new `/api/inspect` and `/api/open-folder` POST routes retain local token/host/origin/fetch-site gates and strict body shapes. File records use opaque SHA256 IDs, candidates canonical UUIDs, and folder alternatives server-derived UUIDs. The service resolves these to existing catalog records or validated completed jobs; no client-supplied path or executable is accepted. Output-folder access requires a matching verified completed artifact. Source/output folders are validated directories beneath the configured library and their ancestor boundary remains held during dispatch. Dispatch calls the Windows-directory Explorer executable through an argument list with `shell=False`. It cannot execute a requested source file or proposed output filename. No actual Explorer invocation was performed by this reviewer.

Source-cover inspection is bounded and read-only. EPUB members are read within the ZIP without filesystem extraction; external cover references are refused. FB2 inspection retains bounded XML/entity rejection and bounded image decoding data. Cached cover response reads occur under directory/file protection. UI inspection uses text nodes/textContent for tag values and paths; cached artwork URLs must be same-origin, and source links restrict protocols. No new arbitrary network fetch, shell interpolation or credential logging boundary was found.

## Retained physical data contracts

Queue manifests freeze ordered source membership/content hashes, accepted metadata/evidence/cover and candidate revision. Sources are opened read-only, copied exclusively to private owned snapshots, hash-checked and protected for encoding. Live source/review checks are repeated at publication; review/group locks bind the revision gate. Source originals are never retagged, moved, replaced or deleted by this pipeline.

The destination-side temporary is copied and flushed before protected-handle verification/rename. Durable publication intent precedes rename; completion/restart accepts only the expected hash/size/validation contract and recorded directory identity. An unrelated collision remains untouched; missing/changed artifacts require attention. Pending work is durable, paused interrupted books restart at a book boundary, and startup does not auto-run the queue. Owned partials remain recovery evidence, not completed books.

Output checks cover full audio decoding and PCM-duration comparison, canonical author/title/media-kind tags, one selected attached cover's exact bytes and optional reviewed chapter count/titles/boundaries. Unknown publisher completeness is correctly a labelled limitation of the selected-source output, rather than a invented completeness claim or automatic rejection. Apple Books sync is separate from technical output checks.

## Evidence and practical limits

Senua independently inspected the frozen code, diffs, relevant boundary-test source and frontend injection boundary, and verified 33 file hashes. No tests that write fixture files, encoder run, source/library write, provider request, live server/catalog action, real browser/native action or process launch was performed by this reviewer. Ender reports 76/76 integrated Python tests, frontend VM checks and four ordinary-host native boundary fixtures, including an actual workspace junction, temporary tampering/collision and early descendant cancellation. These are producer results, not independently repeated Senua execution; Futaba's behavioral/rendered verification is separate.

**Actual mapped Z: semantics remain unverified.** Before the first real-book write, perform the previously agreed tiny exclusively owned destination fixture to establish handle-bound no-replace rename/collision and ancestry protection on the actual mapped filesystem. Unsupported semantics must stop with an error; never relax the guard or use an overwrite/copy-to-final fallback. This source clearance permits proceeding to that scoped fixture, not claiming it already passed. Actual iTunes/Apple Books/iPhone import/search/sync is also not certified here. Full formal release review remains deferred under the prototype phase policy.

At the initial final-2 review no additional Critical mechanism had been identified. Subsequent evidence below supersedes that initial outcome. No disposable artifacts were created by Senua; historical and final snapshots/reports are retained review evidence.

## Narrow final-3 follow-up: directory sharing remains unsafe

Snapshot `scratch/metadata-2026-10-09/frozen-final-3/`, full 33-file manifest SHA256 `843b2f0bc04f28d79d38aa3ec86985e96a65eada5fa3beb44ec9f468df4e697e`: independently verified 33/33 hashes. Native source SHA256 `1B628E7039A3DD207C8F0ABD204757FD5688DFF9CD37447BD86AF5C9E5492D91`. Narrow diffs also cover inspector labels, raw Title/Album facts, stored review evidence exposure and the ancestor-rename regression test; no new path/executable HTTP input was introduced.

The actual mapped-volume probe exposed that final-2's directory `READ_ATTRIBUTES`-only handles did not engage deny-delete sharing, on both C: and Z:. Final-3 added `LIST_DIRECTORY|READ_ATTRIBUTES` access and used READ|WRITE sharing without DELETE. The revised held directory resisted rename, while legitimate child-file publication remained possible.

Producer mapped probe `mapped_capability.py` SHA256 `6043FD39CAEF03B1D8A81DF45906849FF957ADD4F0257BFF5F94CFF587F7B2BC` and `mapped-capability-evidence.json` SHA256 `D8A6C8B89CB091BEF112317A81C4438846591DDE7CFE16D6ED4E1B5B53A2944E` show a 68-byte exclusively owned Z: artifact, matching publication hash, collision preservation and ancestor rename rejection with error32. Both tiny fixtures were cleaned with verified ownership; old-fixture cleanup record SHA256 `36FABC56718E647DF79CC745EE4AE3CB1FDE05C886DA6A9552838ACB59D08552`. The probe imported the working native module; its hash independently matched the frozen final-3 native pin. These results establish those tested actions, not immunity to other directory mutations.

### Critical C2: WRITE sharing permits a held directory to become a junction

`native_io.py`, final-3 `DirectoryBoundary.__enter__`, opens ancestors with desired access `0x81` and sharing `3` (READ|WRITE). Directory identity handles prevent rename but still permit another writer to alter an empty directory's reparse data. Cache/staging writers then use path-based child creation under that held boundary; a newly attached junction can redirect writes outside the configured owned location before a subsequent revalidation. Rechecking the held file's identity does not eliminate this path-redirection mechanism.

Senua asked for this exact boundary implication after reading the share-WRITE change. Ender reproduced it in an isolated owned workspace fixture: an external GENERIC_WRITE handle opened successfully, and `FSCTL_SET_REPARSE_POINT` succeeded while the final-3 directory boundary was held. The fixture removed its own reparse data and directories; no source/library data was touched. Retained reproducer `probe_reparse.py` SHA256 `A92CE47A89BFF42D947517E9F2F3D740230BCE83C453972C703240D9D0CC0D6F` explicitly imports the immutable final-3 module. This is a demonstrated safety-floor mechanism, not a theoretical concern or a mapped-volume incompatibility.

**Required fix:** hold directory boundaries with WRITE and DELETE sharing denied, while retaining only the owned access needed for legitimate child creation/publication. Bind publication to the protected parent handle rather than relax write sharing to make a path-based rename succeed. Ender's bounded proposed correction uses an owned parent with ADD_FILE access and a handle-relative no-replace rename; the actual supported local and mapped-volume behavior must be established before clearing the corrected pins. A fixture must reject the external writer/reparse mutation while allowing the owned output rename and preserving an existing collision. Unsupported semantics fail closed. No broad framework or unrelated code review is required.

**Final-3 safety floor:** BLOCKED

**Historical final-3 open counts:** 1 Critical, 0 Major, 0 Minor. Historical final-2 CLEAR did not apply to final-3 or a live pilot. This intermediate blocked state is superseded only by the exact final-4 correction below.

## Final-4 correction and current clearance

Immutable snapshot: `scratch/metadata-2026-10-09/frozen-final-4/`. Full 33-file manifest SHA256 `1fa347ddfe4e1a20c3bc9c5c73176cecb02241a2f349c7ba5b8ab3a3f8bc3a69`. Independently recomputed 33/33 matching hashes. Only `native_io.py` and `tests/test_safety_boundaries.py` differ from final-3; all previously reviewed cache/source/job/revision/HTTP/inspection code is unchanged. Corrected native source SHA256 `dc6a2ee08eb2ffeaf444492dad7cebd2bbf8b5c23aea91f3bcb3316842e3f000`.

**C2 — resolved for these pins.** Directory handles now request LIST_DIRECTORY|READ_ATTRIBUTES (`0x81`) and permit only READ sharing (`1`); WRITE and DELETE sharing are both denied. This refuses the external write handle used by the demonstrated reparse mutation while retaining effective ancestor rename protection. The former READ_ATTRIBUTES-only and share-WRITE mechanisms are not accepted fallbacks.

The output's exact held deny-write/delete file handle is still hashed and size-checked. Publication now uses `NtSetInformationFile(FileRenameInformation=10)`, `ReplaceIfExists=False`, NULL RootDirectory and only the validated destination leaf name. Temporary and destination parents must equal the held boundary's parent, and ordinary-path checks reject traversal/device/stream names. The supplied name cannot direct the rename outside that file's protected existing parent. UTF-16 storage is sized by encoded code units. This avoids relaxing directory WRITE sharing merely to perform an absolute-path rename. Microsoft documents a simple file name with NULL RootDirectory as a rename within the same directory, and false ReplaceIfExists as collision failure: [FILE_RENAME_INFORMATION](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_rename_information). Unsupported native/filesystem semantics raise a boundary error; there is no unsafe alternate publication route.

The native positive control against final-3 successfully opened the external directory writer and set a junction; the corrected control refuses that writer. Corrected evidence `reparse-corrected-evidence.json` SHA256 `1DF8D2E2CABCDCA7FE1066BCEAFA5C84D1E3AA90D1303DDF6C31B523F3631234` records `external_write_opened=false`; the added native fixture also requires Windows sharing error32. An additional producer control, `reparse-read-attribute-evidence.json`, confirms an externally allowed READ_ATTRIBUTES-only handle cannot set the same reparse payload: the handle opens but the FSCTL returns access-denied error5. No runtime source changed for that check. This is a mechanism correction supported by the same attack condition, not merely a changed assertion.

**Exact final-4 mapped-volume evidence:** producer script `mapped_capability.py` SHA256 `DA2E58BB656908CE6C26A846FAACC08CC87B3409BBBF2E9D7FE603C267F37B17`; evidence `mapped-capability-evidence.json` SHA256 `91F305E7FEFF350BF54B74028FDC9A571F22C00008589F6320B0C0C5EF15770A`. The evidence explicitly records native pin `dc6a2ee0...`, root `Z:\Audiobooks`, volume serial760290819 and owned fixture UUID `2fdf2d3a-12d4-4897-8bc2-9d4e4d154842`. Results: 68-byte handle-bound publication hash `fa13006ef0148b0b53afd7a15ef1b0943ccba5167561a9fad6e0ab1e1b533b48`; replacement disabled; existing collision and attempted source preserved; ancestor rename refused with error32; directory reparse-write handle refused with error32; exact owned fixture cleanup complete. Ender reports six native boundary fixtures and five complete merge/inspection-service checks passing. Senua read the evidence and source and checked hashes, without repeating writes.

The actual destination's required tiny publication/collision/ancestor/reparse capability checks are therefore evidenced for this pin and current mapped root. That does not certify every remote outage, future mount/server change, or physical-device outcome. Runtime guards and durable recovery remain active; a capability failure or observed path/root drift must stop safely, not weaken checks. No original book has been merged as part of this source review.

**Final-4 safety floor:** CLEAR

**Current open counts:** 0 Critical, 0 Major, 0 Minor. C1 and C2 are closed for the exact final-4 pins; initial Major findings remain closed by unchanged reviewed mechanisms. This clearance supports proceeding to the authorized source-preserving real-book technical pilot with separate output and device validation. It is not a full release certificate. Retain historical blocked reports and positive-control evidence; no unrelated source, library file or user process was modified by Senua.
