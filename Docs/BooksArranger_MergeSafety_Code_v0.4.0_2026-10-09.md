# Books Arranger v0.4.0: focused merge safety source audit

Date: 2026-10-09. Senua. Prototype safety-floor review; not the full release-code-review workflow and not a tagged-release clearance. Scope: source-preserving writes, source/review revision binding, path boundaries, exclusive publication, durable recovery, owned cancellation and the HTTP/provider boundary. Unknown publisher completeness is not a blanket processing blocker: the reviewed output covers the exact accepted source set; recording completeness remains labelled unknown.

## Immutable source binding

Initial audited snapshot: `scratch/metadata-2026-10-09/safety-core-1/`. Manifest SHA256: `63005a6443d283a7fd6fa7ceb3a3883891182dea51fd693d35521ecbde97bc01`. Independently recomputed all 11 source hashes; 11/11 matched. These are uncommitted candidate pins, not a commit-range certificate. The referenced design contract is committed at `dbbe758`.

| File | SHA256 |
|---|---|
| native_io.py | d6bf5922e6c6a8d2ab2409b6aa26cc0a0487f039fda8c93d572879640a3ac8cc |
| audio_pipeline.py | b6423e2de54732daa65b1a22df4dc5615223d0d29c19be1886cd6938e176394d |
| audio_jobs.py | 4d4eb716fc732471687073b06ad301b73f6edb3bfd5f5c5f9d1f492b0ad27177 |
| merge_service.py | b8c8a4bfdafa4ca9dd08c2d5227b8740ed1b8d791f82b051a6c2b9dc3e44d134 |
| review_backend.py | 9d5da2c7e6064160abb1e66572a47e09d8cdffa96a4dcbba675debab31624382 |
| web_server.py | e11bda4a19cc92060054baeca02bc1e472272852ef22dcb92bd9caf9c19f658f |
| metadata_sources.py | e77b72cebdf06211d13ad9353629dd93cfbdb7fd464007628485c7f63bc0d010 |
| scanner.py | 5a6dc92683804ffbd21c4366d36781165095c3b49b571d438d1cf5a6a70fb7ec |
| groups.py | b4196880e82f662b16a0aa4d64d36734274361d85686371b801855a518e80cdd |
| metadata.py | 23a9f01764e6506d1450bea18ae379c7263aa1adf375cbf29668817e6ca8cc00 |
| app.py | 192ee63bc475219d02940e56dc785c830e84949a4e601689b3469184b9a095f1 |

## Findings in safety-core-1

### Critical C1: new cover-cache writes do not enforce the owned directory boundary

`review_backend.py:64` resolves the requested cache path, then creates it. `review_backend.py:259` constructs a predictable UUID artwork path and uses `write_bytes` when `exists()` is false. Unlike the audio staging writer, it neither rejects a redirected ancestor before resolving it nor holds a protected directory chain and exclusively creates the file. A cache junction redirects creation outside the intended app cache; a dangling cover symlink satisfies the false existence check and redirects the write to its target. Resolution normalizes this redirection instead of rejecting it. This is an actual out-of-scope-write mechanism in the new implementation, on the always-blocking safety floor.

**Required fix:** retain the configured ordinary cache boundary, protect/reject reparse ancestry before directory creation and throughout writes, create new artwork exclusively without following a pre-existing entry, and validate/reuse an existing cache artifact without replacing it. Audit the containing merge-cache creation as the same boundary. Include an isolated cache-junction/dangling-entry fixture; the app must refuse without creating or modifying the redirect target.

### Major M1: destination temporary is not verified and bound across final publication

`audio_pipeline.py:279` copies to a destination-side temporary. `copy_owned()` hashes incoming bytes, then closes the destination. The temporary is not subsequently re-hashed from disk or protected against file replacement/content modification before `publish_no_replace` at line 287. The hash at line 288 checks only after the file is visible at its final path. A changed temporary can therefore be published as an unvalidated final audiobook before the error is detected. Ancestor handles do not protect the child file's contents or identity.

**Recommended fix:** verify the destination-side artifact itself and bind its identity/bytes through the owned rename, using supported Windows sharing/handle semantics that permit this rename while denying content writes and checking reparse/identity drift. Preserve no-replace collision semantics. Add a fixture that alters/replaces the temporary immediately before publication; no unvalidated final output may appear.

### Major M2: process-tree ownership is assigned after execution starts

`audio_pipeline.py:45` and `:88` start a running subprocess; `OwnedProcessJob` assigns that process to the owned Windows job afterward. A descendant spawned in that interval can escape the job. FFmpeg ordinarily does not spawn a process tree, but the implementation's general claim that cancellation contains all owned descendants is stronger than its mechanism.

**Recommended fix:** establish job ownership before execution can spawn descendants, for example a supported suspended launch/assignment/resume route, or explicitly constrain and verify the process behavior rather than claim universal tree containment. Preserve fail-closed assignment failure and termination/drain checks. An isolated early-spawn fixture should leave no descendant alive after cancellation.

### Major M3: embedded artwork extraction lacks the local-protocol restriction

The new `review_backend.py:285` embedded artwork command invokes FFmpeg on an untrusted source without `-protocol_whitelist file`, unlike the new pipeline's media commands. Container/playlist detection can use nested protocols; an audiobook extension is not an input-format security boundary. This can introduce unintended network or nested-protocol access during a local cover operation.

**Recommended fix:** use the same restricted local-protocol input contract for artwork extraction, retain bounded output/deadline behavior, and test a disguised playlist/network reference is refused. No arbitrary manual source URL is fetched by the metadata provider code; this finding concerns the media subprocess path.

## Mechanisms inspected without further findings in this slice

The HTTP merge APIs derive candidates from canonical UUID/revision inputs, reject unknown fields, and do not accept an arbitrary destination/executable. Host/origin/fetch-site checks and a local token gate mutations; request bodies are bounded and reject duplicate fields/non-finite constants. Provider requests use fixed HTTPS endpoints, no redirects/proxies, bounds and sanitized errors; credentials are not exposed through proposal/error records.

Ordered source hashes and accepted review/evidence/cover data enter the durable manifest. Sources are copied with exclusive creation and hash comparison to owned private staging, then encoded under protected snapshot handles. Source hash/review guards are repeated before publication; metadata/context and grouping revisions share held locks at publication. The encoder uses argument arrays and safe aliases, no shell, no source overwrite. Ancestor directory handles reject reparse entries; final `MoveFileExW` uses WRITE_THROUGH only, without replace or cross-volume copy flags. No source cleanup/delete operation exists in the reviewed slice.

Publication intent with expected output hash/size and directory identity is committed before rename. Restart accepts only the matching expected artifact, marks mismatches for attention, and does not blindly overwrite or recreate completed outputs. Pause/shutdown signals only the owned worker, waits its completion, and leaves pending books durable. Full output validation checks decoded duration, selected cover bytes, canonical tags/author, audiobook media kind and optional chapter boundaries. Device sync is accurately separate. These source mechanisms do not substitute for unresolved mapped-volume/crash/cancellation runtime evidence.

## Validation limits and disposition

Senua independently read source and verified immutable hashes; no library write, provider request, encoder execution, live server action or native/browser action was performed. Ender reports 69/69 integrated Python fixture tests passing under scoped fixture-loopback permission, three full private-service fixtures and five native publication fixtures. Those results are producer evidence, not an independent Senua execution. Actual mapped Z: publication semantics, crash-injection/cancellation stress and device sync remain explicitly unverified. No actual mapped-volume live pilot is cleared by this report.

**Counts for initial pins:** 1 Critical, 3 Major, 0 Minor.

**Safety floor:** BLOCKED

The live-file pilot must wait for C1's bounded fix and re-pinned review. Major recommendations were sent to Ender with precise mechanisms; they are advisory under the canonical severity policy. This report clears no later source changes automatically, including the forthcoming View/Open Folder integration. No disposable output was created; this document and frozen source slice are retained unresolved review evidence.
