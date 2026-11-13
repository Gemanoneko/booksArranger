# Code Review — Books Arranger v0.28.0

## Header

```text
Reviewer: Senua (Code Reviewer)
Date: 2026-11-13
Tool: Books Arranger (Electron desktop and Python backend)
Release: v0.28.0
Commit range: d11302ab70a2831e2096ec4a6a4629f33fc0f9c9..8dbebbf99b97241a5c607bf321567579e66bd040
Files changed: 147 files, +22989 / -2878 lines including retained documentation and prior-release evidence
Count method: git diff --shortstat over the exact range above
Stand-down dimensions: none
Status: Complete
```

Release source commit: 8dbebbf99b97241a5c607bf321567579e66bd040

Release artifact manifest SHA256: 31f4fc24d83ee3ff455bd7df2e7b5c89e5993055194fa886e459c1fbee9bb9e8

## Summary

This review covers configurable installation and temporary storage, the offline native-identity relocation bridge, durable file-disposition fencing, installer catalog discovery and reuse, retained profiles, finite uninstall cleanup, package publication and guarded build changes. The previous full review's certified end establishes the range start. I reviewed the accumulated source, the authority, ownership and build corrections, the installer and QA delta, and the directory rename buffer fix.

## Rubric

### 1. Security

- Pass. Configured roots and native handles remain separate from historical expected identities. Only the selected managed junction receives the exact target lease; general reparse rejection remains. Electron isolation and trusted IPC remain intact, subprocesses use literal argument vectors, and the build adapter admits only the exact pinned valueless directory-choice flag. No credential literal was found by the scoped secret-pattern audit.

### 2. Correctness & Logic

- Concerns. **M3 [Major] — `storage_relocation_operator.py:1045`: interrupted seal replay requires every target file to be a typed historical binding.** The descriptor is generated from `plan['receipt_classes']`, while the full source census also admits fixed `web-instance` records and SQLite WAL/SHM members without those bindings. Legitimate surviving fixed members can therefore make replay refuse before mutation. This is a source-based finding; no native reproduction is claimed. Validate the complete census against its independently pinned full source/target generation while retaining the separate typed-binding checks. Files remain protected; this finding does not permit bypassing the refusal.

### 3. Crash / Stability Safety

- Pass. Durable intent precedes ACL mutation. Native-success state is set before subsequent journal I/O, and recovery cannot reinterpret an intent-only missing file as successful disposal. Interrupted terminal cleanup blocks normal admission and exposes its recovery record. The build completion guard now refuses unresolved or unverified asynchronous completion, including explicit process exit.

### 4. Performance

- Concerns. **M2 [Major] — `runtime_file_disposition.py:291` and `runtime_file_disposition.py:292`: immutable disposition history is fully scanned at every owner admission and eventually prevents startup.** A successful disposal creates four phase files; 25,000 successes plus `context.json` produce 100,001 members, exceeding the 100,000-member admission bound. No bounded compaction mechanism exists in this range. Plan a separately reviewed history-retention solution next cycle; retain the current safe refusal until then. This count is derived from the four successful publication phases and the explicit bound, not a performance benchmark or a claim about the current live ledger size.

### 5. State & Data Safety

- Pass. Original C1 is closed in A2: seal validates current census, replay native bindings, logical catalog state and every allowed security transition before its first ACL restoration. Source recovery validates all held identities/security before restoring any member. Failed source finalization only restores the unchanged original bytes and operation-owned full or DELETE-relaxed fence. Foreign security remains held.
- The earlier core-review source/Git deletion finding is closed by exact catalog scope and independently rederived snapshot membership. Replacement recovery records receive the typed location bridge, while uncertain/prepared producer recovery stays held. Relocation preserves historical receipt text and origin/boot proofs; it creates no producer closure. Target verification precedes explicit normal enablement, and rollback refuses unreconciled new writes.
- M1 from this review is closed in A2: uninstall refresh now consumes the same frozen-snapshot membership/classifier as independent cleanup admission, including closed/retained runtime ledgers, exact replacement recoveries and typed OpenLibrary members. Unknown, orphan and outstanding state stays held. SQLite cleanup queries operate on a private consistent frozen DB/WAL/SHM tuple and standalone backup; original tuple facts and hashes remain strict.
- NAS originals remain retained under the explicit provider limitation. Safe new no-replace publication is separate. The accepted matching NSIS operational copy is a disclosed retained component with exact package/native/content evidence; it grants no deletion authority and carries no automatic or reboot-removal promise.

### 6. Input Handling

- Pass. Absolute paths, bounded strict ownership documents, duplicate rejection, exact native identities, hashes and explicit selections constrain state changes. Missing selected storage refuses without an alternate personal/system storage path. Existing installations keep legacy per-machine behavior until configured migration.
- **[Minor] — `tests/real-shell-update-support.mjs:89` and `scripts/qa-real-shell-phase.mjs:69`.** The packaged recovery test checks the plan’s environment paths for lexical containment. It launches the first owned Node child before checking each actual environment path for reparse ancestors. Fresh fixture creation and the app worker’s independently constructed and checked home paths limit the exposure. Extend the recovery check to the exact environment paths used by the first child.

### 7. Maintainability

- Pass. A2 removes the divergent lifecycle catalog graph in favor of the shared typed membership and historical classifier. Finite native deletion capabilities preserve caller authority and keep filesystem and registry journals distinct.

### 8. Doc/Code Drift

- Pass. Current contracts distinguish implementation maps and component receipts from release acceptance and live-migration approval. The copy protocol now explicitly requires preservation of the reviewed security transition; content-only cross-volume copying is refused unchanged. Previous native registry-rename receipts are historical, not current safe-host acceptance.

### 9. Build & Release Hygiene

- Pass. Version, lockfile and corrected build-input lock hash agree. The exact plugin-directive adapter preserves pinned vendor files and strict compiler flags. Branch-specific NSIS variables retain their live consumers. Diagnostic records are bounded and credential-redacted. The packaged installer, blockmap and update metadata match the accepted manifest.

## Verification

- Reviewer actions were read-only source/diff inspection and examination of retained developer receipts. No full suite, native application, installer, uninstaller, registry rename, live catalog or library operation was executed by the reviewer.
- Independently read the corrected builder receipts: nine ACL cases, three finalization cases, three copy/integration cases and five used-catalog cleanup cases. They report success, normal closure and zero active native job members. Earlier failed receipts remain retained and are not counted as passes. These are engineering proofs, not final packaged acceptance.
- Read `compiler-positive-a5f/result.json`, the exact input-transform record and native supervisor receipt. The reconstructed initial-uninstaller compile succeeded with unchanged `-WX`, no warnings, empty stderr and native-zero closure. Its generated executable was never executed. This establishes the scoped compiler repair, not a complete package.
- A6 removes the eager duplicate `StrContains` helper and preserves its inline substring scan and register balance. The private `installUtil` copy requires its exact pinned vendor source SHA, removes only the dead old-uninstaller dependency set, preserves the live result handler and replacement macro, and redirects exactly one compiler include. The original vendor file remains unchanged. Read both reconstructed A6 branch result/supervisor records under `repair-A6/private-util-installer` and `repair-A6/private-util-uninstaller`: compiler exit zero, empty stderr, no warnings and closed/native-zero eight. Result SHA-256 values are `0c11a3bf4b7b80e5d1de2e5905e92c5e01ec4e65c9a2c3903894bb5dd85a7b3d` and `898ba877ff38802d205579b8154cf3581e9798bc148b07e05106d0ee770835f2`. Generated executables were not executed. These reconstructed branch proofs do not substitute for the final full package.
- A7 locates one raw 7z archive by walking the installer’s bounded NSIS block framing through the retained installer handle. The verifier checks installer CRC, archive extent and both 7z header CRCs, then extracts the standalone archive into fresh owned work. The existing complete path, size and SHA-256 payload comparison remains mandatory. Ender reported all 379 comparisons passing on the retained A6 installer and passing malformed framing controls.
- The final installer delta requires the selected descriptor and active native catalog lease through profile copy and bootstrap publication. Profile affinity uses the exact historical catalog path and retained source or target identity. Process inspection accepts a failed image query only with exit evidence on the same handle. Reviewed output migration requires the admitted disposition owner. Retagging can complete while an unsupported empty work directory is retained. The QA harness checks local fixed volumes and isolates worker scratch and snapshot work.
- The 21 frozen file hashes and all seven retained evidence hashes matched. Four focused runs passed with confirmed process closure and no active native job members. The failed run also confirmed closure and remains recorded as a failure.
- The final checker correction isolates build-guard fixtures from the worker’s general disposition scope. Its mismatch tests require the original native boundary refusal, verify the retained recovery marker’s hash and check that the protected file survives. This delta changes the checker and its fixture only.
- The Windows directory rename fix copies exact UTF-16 code units into a zero-initialized buffer with an extra WCHAR. The filename length counts bytes before the terminator, and the native call receives the full structure size. This preserves the existing no-replace flags, same-parent lease and native identity checks. The new test inspects the request with supplementary Unicode before delegating to the native API. The developer reported three focused passes.
- The final PA-1 marker parser accepts a canonical drive letter and still requires the exact planned fixture and executable strings. The established TAP escaping rule, native fixed-volume and reparse checks, process ownership, cleanup identity and raw evidence hashes retain their existing checks. The developer reported 96 focused passes. The previous package passed the inner real-shell functional test, but the outer controller rejected its I: fixture marker. That run remains a failed outer gate. A fresh real-shell result for the current package was pending at review completion.
- I independently verified the clean I: source checkout at `8dbebbf99b97241a5c607bf321567579e66bd040`, the manifest hash above, and the SHA-256 and size of all three release artifacts. I also enumerated and checked the 379 unpacked payload files against the manifest with zero drift. The manifest records verified installer equivalence and build ID `092f09e7-07bd-4cfa-9886-bfe0cc50b4b9`. Canonical entry and packaged behavior have separate acceptance receipts.
- Packaged QA verified restart at a job boundary. The existing v0.27 Quit defect can interrupt a conversion in progress, retain its work and leave the job needing attention. For the live migration, let active work finish and confirm the batch is closed before taking the source offline.
- The current registry replacement test uses distinct fake key objects with every exercised registry operation mocked. The static containment preflight runs before aggregate workers. This proves caller selection/reporting under the model; it does not establish Windows kernel behavior during native registry-key replacement. No unsafe archived rename probe was replayed.
- Directory-change traces are bounded observations of declared fixture roots; they are not system-wide proof of zero C: writes. Final packaged behavior, associated profile/outbox, conversion/restart and exact artifact evidence remain the independent QA/build obligations.
- Earlier v0.27.0 manual-conversion performance/alias and minor UI/documentation advisories remain recorded in that report; unchanged source is not represented as newly fixed here.

## Verdict

- Open Critical: 0
- Open Major: 2 (M2, M3)
- Open Minor: 1 (packaged recovery environment path coverage)
- Closed in this cycle: C1 and M1

**Verdict:** RELEASE CLEAR
