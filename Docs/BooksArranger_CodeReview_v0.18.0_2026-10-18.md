# Code Review — Books Arranger v0.18.0

## Header

Reviewer: Senua (Code Reviewer)
Date: 2026-10-18
Release: v0.18.0
Commit range: e028fc04c4b30ee26b6960f90948526205acb3ac..902d3128943544ec07772fa489e94b9559ca126d
Files changed: 19 files, +1348 / -18 (git diff --stat, including prior release documentation)
Release source commit: 902d3128943544ec07772fa489e94b9559ca126d
Release artifact manifest SHA256: b52be300dd46351d5ca9bb72913df6185298e5ddc32483e714696770654b9940
Release installer: dist/builds/817dc432-53b9-4834-b280-cb266a742482/Books-Arranger-Setup-0.18.0.exe
Release installer SHA256: 60a92a45905a5aa35b8d28272648b892139a434ab83236ed6157afeea195e98d
Product digest: d501ac3e506e20750435c5f45d2308c2d59694e92a368d54b7e96f1816c7bbba
Stand-down dimensions: none.

## Summary

Red-team review of independent series evidence, shared provider limits, sparse offline Open Library import/lookup, negative-cache revisions, and the fixed owned importer entry. The new strict series adapter separates work/author identity from unrelated original-language requirements. Local editions remain discovery evidence, never narrative order. No product edits, provider requests, imports, live app actions or commits were performed by Senua.

## Rubric

### 1. Security

Pass. Archive access is restricted to exact dated metadata-only HTTPS routes, with bounded responses and existing transport/holds. Mutable SQLite DB/journal leaves now have native ordinary unique identity ownership, protected producer receipts and deny-delete holds; native ancestor admission precedes writes. Unknown/reparse/linked leaves and sidecars refuse safely.

### 2. Correctness & Logic

Pass. Wikidata requires exact work/all-author identity, referenced same-statement P179/P1545, narrative series type and revisions. PRH requires exact current canonical product/title/authors plus explicit Book N and book-scoped narrative continuation. Wikipedia/search/local links are discovery only. Per-title incomplete work/author identities hold the entire title even if another same-title candidate looks valid.

### 3. Crash / Stability Safety

Pass. Checkpoint data and offsets commit together; immutable completion receipts prevent altered ready files being blessed on resume. Registry activation is transactional and preserves the previous generation on failure. Existing audiobook replacement/hash/native-disposal protections are unchanged.

### 4. Performance

Pass. Sparse indexed lookup avoids dump scans; source processing is streamed in finite slices. Existing owned execution bounds the child at the remaining 600-second budget, including gzip replay. A long replay may remain pending; no completion claim is made from yield intervals or partial coverage.

### 5. State & Data Safety

Pass. Each incomplete source is fully authenticated against official compressed size/SHA1/MD5 before checkpoint reuse, then gzip EOF/CRC is required before activation. Inputs remain held read-only. Default-stream bytes alone are used; a bounded Zone.Identifier is preserved and ignored. Destructive cleanup stream guards remain strict.

### 6. Input Handling

Pass. Partial download names are excluded. Official raw metadata is embedded and SHA-bound to exact snapshot expectations. Requested versus eligible coverage, identity holds, outside coverage and unavailable/invalid indexes remain explicit. Known Goodreads ordering conflicts hold; no ordinal comes from list position, publisher collection or edition series text.

### 7. Maintainability

Pass. Index-specific ownership and import logic reuse existing native/process primitives. No maintenance CLI, fake idle mode, generic execution framework or shared safety-policy change was introduced.

### 8. Doc/Code Drift

Pass. Brief and changelog describe implemented strict sources and truthful index coverage. Legacy negative lookups retry once after policy/new active-generation changes; unavailable/busy generation does not cause hot loops. Done/held/skipped and active file recovery states remain protected.

### 9. Build & Release Hygiene

Pass. Version/lockfile agree. Actual manifest/installer hashes independently match the header; the manifest binds the reviewed source commit. All five changed production inputs independently match their unpacked payload bytes, including the new modules.

## Verification and closed findings

Developer evidence: 59 focused cases passed in 7.010 seconds (17 index, 9 scheduler, 33 provider/source cases). Test source was reviewed; these runs are not claimed as independent Senua reruns. Unchanged audiobook media tests were not redundantly repeated.

Closed before release: the Critical mutable SQLite leaf/root write-redirection gap; the Major ready-file rehash/reblessing gap; per-title sparse work/author failure handling; legacy negative-cache invalidation; Wikidata search maxlag omission. The importer execution also closes the stale bytecode admission gap using isolated Python with a held ordinary manifest FILE as pycache_prefix. A real stale-cache negative control read STALE! without this option and SOURCE with it, with inputs unchanged and native ownership closed. No old cache was deleted or shared setting changed.

Independently checked actual module/payload equivalence:

- openlibrary_index.py: 9e3d9e57c44e77f16f51b9e795522bb121a2f1247cedf5dd63a3d56a8344ec07
- series_evidence.py: c8709ab2f09aa9ac348f14fc899b0519ac6eadd950954231175cc85d6b818c5d
- series_backfill.py: 9a45580075ed56d856d95bd66438d35bc35bcd81c049f365b3ca92c5486ee2e1
- public_research.py: a9f4750c437ae1e98c61b07843f9a72c65bf452932a1beb81472b6b126c722c0
- public_source_leads.json: 4401541e57b313f9b91f95bc36ee0a512b34c5a4968774b77da2dad7b964d57d

## Limits and execution evidence

The metadata research request and completed-name works/authors are distinct from the still-downloading editions file. Small owned fixture runs independently survived integrity/identity/coverage/hash checks; R2 fixture owner reported normal closure, no force/timeout and zero descendants. Initial real attempts refused unsupported streams and sparse identity safely; later slices retained checkpoints normally. At report writing the real index build/resume is pending; this report does not assert activation or complete local lookup coverage. Later activation evidence may be appended without changing the artifact binding.

No canonical handoff receipt is asserted: the previously denied receipt-read route was not rerouted. This construction verdict does not replace Futaba's packaged behavior verdict or claim independent replay of live audiobook originals.

## Exact packaged smoke source/pins review

Newly reconstructed fixed qa-v0180 helper, not claimed to restore older bytes. Owner SHA256 a10ee03c8569600ba1288d9691582eca817225469e6ab0a480009cc8eb46c9b0; helper SHA256 d905f2f7befbbe3ddc5a7c1505bde76e0a6c7f5ee675ef43574c379ac9520a89; exact pins SHA256 aac65fa630e33f88516a1629df3642058c12912385d9c10231edc8c847449170. Senua independently checked all 327 pins with zero mismatches and authorized one exact smoke under ordinary guard evaluation.

Scope is fresh private empty catalog/profile/environment folders and three explicit private roots, version/status/renderer/normal bound Quit only; hidden/inactive launch and no bare-PID/name kill. Existing canonical runOwned ownership and held pre/post input hashes are used; successful acceptance requires closed ownership, zero descendants, no force/timeout/overflow/truncation. Canonical ownership-before-release semantics are inherited from the unchanged reviewed route; the JavaScript bootstrap timer cannot preempt synchronous input reads, so total deadline also depends on host/canonical behavior. Source/pins clearance is not a smoke execution result or global route enrollment. All session scratch/evidence remains retained under the standing exception.

## Verdict

- Open Critical: 0
- Open Major: 0
- Open Minor: 0

**Verdict:** RELEASE CLEAR
