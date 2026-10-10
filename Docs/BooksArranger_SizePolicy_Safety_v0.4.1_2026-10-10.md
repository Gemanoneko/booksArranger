# Books Arranger v0.4.1: focused output-size safety audit

Date: 2026-10-10, Asia/Jerusalem. Senua. Narrow prototype safety-floor/correctness audit of future-output encoding. The earlier strict byte-budget design below is historical: the user's subsequent quality-priority direction supersedes that cap and compression retry. This is not a full nine-dimension release review. Existing accepted native, HTTP, UI, process, source-preservation and publication guards are outside the unchanged-code re-review scope.

**Current safety floor:** CLEAR for quality-first frozen-3. **Current open findings:** 0 Critical, 0 Major, 0 Minor. The frozen-1 Major finding and frozen-2 byte-budget closure remain historical; the final section binds the current source-matched policy and unchanged physical-write guards.

## Initial source binding

Read-only comparison from committed source `e589fd6853bbeb4095faeaf492ae3ed7009422f8` to immutable `scratch/size-policy-2026-10-10/frozen-1/`. Manifest SHA256 `47da12c9e8cf9db2aa290a3e813093ea9c2d351a773910237fc4da0642e51c6f`; independently recomputed37/37 matching file hashes. These are candidate source pins, not a clearance of an unspecified working tree or final release commit range.

| Changed runtime source | SHA256 |
|---|---|
| encoding_policy.py | baa21d71f2ecfdc360933eb607a17f7085c33f5eb7bd9d39bfff282091141bd0 |
| audio_pipeline.py | 8bbb1ac826d64ac33a2923d92154c22116ba3ecc51c4616a3920a586ff79ed66 |
| audio_jobs.py | 4f8cd83dae745e578d76c2e3bea0b898b324b780331e943e48586c03287cb351 |
| review_backend.py | 238297c97bad7ae0c02e69a88fe8aab982476d3868fa0d6b85f2701108c46166 |
| merge_service.py | 683d017c5f801425eb2ed62949289131cc64633684d3d6e6cf2bf96b7627ab9c |

Unchanged native guard pin is `dc6a2ee08eb2ffeaf444492dad7cebd2bbf8b5c23aea91f3bcb3316842e3f000`, covered by the earlier focused merge report and exact mapped-volume capability evidence. The reviewed copy spec is committed at `e589fd6`.

## Finding in frozen-1

**Major M1 — new server jobs still select the legacy encoder profile.** `review_backend.py:2` imports only `freeze_policy`, while line20 retains the local legacy PROFILE constant. `build_manifest` at line433 sets that legacy value despite attaching the new byte policy. The pipeline's LEGACY_PROFILE branch intentionally uses160 kb/s stereo and skips new budget/retry gates; consequently ordinary new jobs do not exercise the size-aware behavior at all. Direct pipeline fixtures supplied the new profile manually and missed this server-to-encoder mismatch.

Required correction for the requested behavior: derive new-job PROFILE from `encoding_policy.PROFILE`, keep legacy acceptance for historical completed artifacts, and verify an actual server-built manifest selects the new policy before passing it through the pipeline. This is a concrete construction correctness finding, not an out-of-scope write or source-destruction safety-floor violation. It was sent immediately to Ender and Jane. No runtime promotion of this incomplete behavior was recommended.

## Remaining changed mechanisms inspected

The frozen policy totals only included source-audio bytes, binds selected-cover bytes, preserves supported uniform channels/rate and rejects mixed/unsupported profiles or a quality floor breach. Selection/retry calculations cannot enlarge the accepted byte allowance. New outputs are measured exactly after encoding and during validation; publication refuses an over-budget validated size or private artifact before any destination creation.

The unchanged merge service acquires deny-write/delete protection on the validated private output before publication. Destination copy uses exclusive owned creation, and the accepted native publication helper compares actual destination-temporary size and SHA256 through its exact held handle before no-replace rename. Therefore, when the new profile is correctly selected, the exact byte check remains bound to the artifact that is published, rather than a rounded prediction or an unprotected later file name.

At most one lower target is selected: attempt2 cannot obtain another lower-rate retry. Both attempts retain the original staged source-input manifest and protected source/cover snapshots; the second writes a distinct `checked-retry.m4b` with overwrite-disabled FFmpeg and never transcodes the first AAC. No new cleanup/overwrite of intermediate/source files is added. If an attempt cannot fit, it remains private and the job requires attention.

The attempt2 encoding target is journalled before launching that retry and retained on pause/restart. Resume starts a new owned attempt directory at a book boundary, revalidates the frozen policy against current approved source snapshots and constrains a persisted retry bitrate to the supported floor/current target. Interrupted work may restart that same attempt; it cannot silently grant another reduction or loop a size-failed needs-attention job through Resume. Source/review guards still run at queue/build, worker start and publication. Legacy completed160k artifacts remain eligible for exact recorded hash/size validation without automatic rewriting.

Senua read the changed source, call boundaries and targeted fixtures and verified immutable hashes. No test writes, source/catalog/server action, provider request, encoder/native/UI run, git mutation or disposable probe occurred. QA's supplied14 targeted checks are separate behavioral evidence; they are not independently repeated here. No redundant mapped-volume or reparse experiment was run.

**Initial frozen-1 safety floor:** CLEAR

**Initial open counts:** 0 Critical, 1 Major, 0 Minor. This floor outcome does not mean the requested size policy works: M1 must be corrected to implement the authorized behavior. Await the bounded profile-binding correction and exact repin; unchanged native data guards retain their earlier scope and limits.

## Frozen-2 correction and current disposition

Immutable candidate `scratch/size-policy-2026-10-10/frozen-2/`, 37-file manifest SHA256 `d55e38ea77f75c266f3da8cba429e5ce9d8105542b5c6e1ae9fb40dfa505b208`. Independently recomputed37/37 matching hashes. Only two files differ from frozen-1:

| Corrected source/fixture | SHA256 |
|---|---|
| review_backend.py | a511055f2482f8a3083f26acebd0d9ed51204e244df80873446cf10449d886fd |
| tests/test_merge_service.py | bf038e57e8fcd8176b76d1abf1bbd7ae3d9942a2c6e93259adbeb7a6e9b92a9f |

**M1 resolved.** `review_backend` now imports the authoritative PROFILE alongside `freeze_policy` from `encoding_policy`, and removes its local legacy constant. Ordinary server-built manifests therefore select `aac-source-budget-quicktime-v2`, retain the exact frozen byte allowance and execute the reviewed size-aware encoder/validation/publication gates. Legacy recognition remains restricted to the separately retained historical profile behavior and accepted recorded outputs; this binding correction does not rewrite them.

The full-service fixture now obtains the actual review service's manifest, asserts new PROFILE and its exact included-source byte allowance, queues it through the real service, then asserts validated PROFILE, retained mono and final bytes at or below that allowance. It also retains exact source hashes and restart-reuse assertions. This closes the boundary missed by manually constructed pipeline fixtures. Ender reports five affected full-service tests passing; QA verification is independent. Senua inspected this narrow correction and hashes without rerunning file-writing tests or unchanged native guards.

**Frozen-2 safety floor:** CLEAR

**Current open findings:** 0 Critical, 0 Major, 0 Minor. This binds the precise corrected37-file candidate. Earlier safety guarantees/limits carry through unchanged; this focused audit does not certify perceived audio quality, real-device sync or a full release range. No code, git state, live service, source file or existing output was modified by Senua; no disposable probes were created.

## Quality-priority frozen-3: superseding direction and exact current pins

The user's latest instruction prioritizes suitable audio encoding over an artificial source-size cap. The strict byte limit, fixed160k ceiling and lower-rate retry described in the earlier sections are therefore intentionally removed from this candidate. Their removal is not a safety defect or a request to rewrite the existing pilot. Source preservation, exact artifact validation and no-overwrite publication remain required.

Immutable candidate `scratch/size-policy-2026-10-10/frozen-3/`, 37-file manifest SHA256 `ae07dd09adcdb2eb7037a4442f999081a0e8dcf94a79087145026d51498f9eff`. Independently recomputed37/37 matching hashes. Current changed runtime scope:

| Runtime source | SHA256 |
|---|---|
| encoding_policy.py | 0acbcbfedd2cf9c6fd04248de33c889dbc9a7e37fa32dbc0150669aa7dbc5de2 |
| audio_pipeline.py | b78a5a6791df2b502e051e43374c0b19bdc9e18c9815ca1a138ef01b9bd3be09 |
| review_backend.py | 8b1de1611325678fbb6facbba8ce9912608705fecafe8dc57afe5d747c0a0063 |
| merge_service.py | 31e9b7164ff9ef6cb70276490865775f36e2cea311f0c24bba4b9a1d83c2b82f |

`audio_jobs.py` is restored to the accepted production queue, rather than retaining the unshipped byte-retry journal extension. Independently compared its bytes, `native_io.py` and `web_server.py` to production: all match. Other differences from frozen-2 are the policy/service fixtures and explanatory docs. No native/process/HTTP/UI guard is changed.

The server imports the authoritative new PROFILE `aac-source-matched-quicktime-v3`, avoiding the historical M1 mismatch. Its frozen policy records selected source bytes for provenance, not a publication cap. After each source copy is hash-verified, the pipeline holds deny-write/delete snapshot protection, rechecks its approved hash, then probes that same protected audio stream for codec, rate, channels and bitrate and measures decoded PCM duration. The selection uses only this verified snapshot evidence. It preserves a uniform supported sample rate and mono/stereo layout, requires MP3 sources, and refuses missing/invalid bitrate, mixed/unsupported layouts or a target exceeding the supported AAC frame capacity. It selects the highest verified included MP3 stream bitrate without an artificial160k cap; no filename/tag estimate substitutes for the media evidence.

Encoding runs once from the original protected snapshot concat inputs. No size-lowering retry, intermediate AAC input, overwrite or cleanup path remains. Interruption still follows the accepted queue's book-boundary restart and repeats source/review/policy checks. The absence of a byte cap does not bypass actual disk-space failures, source mutation, recording conflicts, canonical metadata/cover/chapter validation or the final publication guard.

Full source and output decode/PCM-duration checks remain, as do selected rate/channel checks, canonical author/title/audiobook-kind tags, exact attached-cover bytes, optional chapter checks and current source/review revision/hash guards. The validated private output is protected during destination copying, and the unchanged native helper binds actual copied bytes/size to its protected file handle before same-parent no-replace publication. Legacy completed160k records remain valid only through their exact recorded artifact contract and are not automatically rewritten. Source-matched AAC remains re-encoding; this audit does not certify identical or subjectively superior sound.

Read-only comparison and call-boundary review found no new Critical or safety-floor mechanism. Parent reports10 policy/media and5 service/API fixture checks passing; QA's independent verification is separate. No encoder/probe run, native/platform experiment, source/catalog/server action, git mutation, test write or disposable artifact was created by Senua for this delta. Existing mapped-root/native proof is unchanged and was not repeated.

**Quality-first frozen-3 safety floor:** CLEAR

**Current open findings:** 0 Critical, 0 Major, 0 Minor. This current clearance binds the exact37-file manifest above and supersedes frozen-2's strict byte-budget scope. Earlier finding/closure evidence is preserved. It remains a focused prototype source-safety audit, not a formal release certificate or real-device/perceptual-quality guarantee.
