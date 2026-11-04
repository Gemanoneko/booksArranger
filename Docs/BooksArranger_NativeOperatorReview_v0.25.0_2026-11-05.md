# Books Arranger 0.25.0 — final native operator and plan review

Reviewer: Senua. Date: 2026-11-05.

**Operator review: CLEAR FOR ONE CANONICAL RUN.** Futaba and Jane were notified immediately after the successful read-only checks, before this report was written. This is construction/admission clearance for the exact prepared plan, not a native behavior result or publication verdict.

## Exact reviewed binding

```text
Source: 90f0368ba7631659a3caafc2fa6125e9075ccf2a
Build: 9b63e746-2a00-4cd8-a0ba-5b45e6405fc2
Product digest: 21a42959c039c1e80075a5be71e7a86b0b17b09301ff00481857f12047febb16
Artifact manifest SHA256: 2f58427054176b23f0110dda1a3b51920e8628ecbf571062942a951c292a41a4
Runtime manifest SHA256: f41e06413dee3dc1fdb2261c695baa38c8a846a02e408c690ee6d9ad08000b2e
Phase contract SHA256: 63fbc25237be6b9a548a6cb5d0d83ba53b473b86a8d00d6b265beb5fa3f00e3f
Operator SHA256: 6e4f1761b7edc0bb0b5906a1dc92364867a05fc5826236d425b1a8bc99816e78
Plan SHA256: 6793fedc82e0b5b27dc80b512ed3ef01bdb2b1950a8ccc9b1da02d8fa6b5137b
Authority SHA256: 1320031d13ba391bdcb9248c8e92cbb206edcabb70fda4a95e47712632ae139a
Full PASS receipt SHA256: afab5c83f884a5f6e283b96cdff60fba75b17abd44dec239183b64cc060a9de2
Full context SHA256: ef05253c057a0aff3a5ade8eb854f076725e4dd82ef512e641c407aa5cd9752c
```

The operator is `Docs/Evidence/converted-duplicate_2026-11-04/native-recipe-0250/native-once.mjs` (13,035 bytes). The actual plan is `C:/Antigravity Projects/n25/plan.json` (593,027 bytes), and authority is `C:/Antigravity Projects/n25/authority.json` (1,664 bytes). Their retained prepared copies match the actual files exactly. The private fixture is `C:/Antigravity Projects/n25/pa1-9b63e746-2a00-4cd8-a0ba-5b45e6405fc2`; source/context and ownership inputs come from the exact full-entry `q4` context.

## Independent pure checks

Senua verified the exact three actual-file hashes, the r3 binding, the full context hash and absence of every `PENDING` placeholder in the operator. Canonical `validatePlan()` succeeded with the actual authority. Canonical `readPin()` succeeded for authority, operator, full receipt and all 20 listed input pins, including their applicable native identity/link checks. The normalized operator path exactly equals the executing-operator path expected by `readPlan()`.

The original full receipt contains exactly one clean-source 0.25.0/`90f0368` entry-check receipt with `check pass` and the required clean ending. `full-pass-origin.json` links it to the original stdout, callback, invocation and retained full result; those file hashes were independently verified. In particular, the original callback is SHA256 `c5c5047c87163dc78674edc638b619028b152c42377f88a86970d53795055578`, and the linked check result reports normal exit 0, completed closure and native zero. No previous source/build PASS is substituted.

At the clearance check, both `launch-started.json` and the native fixture directory were absent. This was a pre-launch observation, not a claim about state after Futaba was cleared. Preparation had occurred once; no second preparation or alternate launch is included in this clearance.

The actual authority contains the exact current user quotations verified by Jane, the current 0.25.0 binding and its actual preparation timestamp `2026-11-04T23:03:28.110Z` (November 5 local time). Its effects retain the approved canonical private scope: one hidden copied app/fake-installer refusal, only the exact newly created own HKCU tray leaf cleanup, and one additional 8-byte numeric history reference while preserving preexisting UIOrderList bytes. No focus, installed app state, live library or Z: access is granted. This is a fresh authority object; an old approval artifact/timestamp is not reused.

## Construction checks

| Dimension | Status |
|---|---|
| Security | Pass: canonical pinned code, exact private paths/environment and unchanged bounded native effect scope. |
| Correctness | Pass: the actual operator/plan/authority/full-PASS/source/context/build bindings agree. |
| Crash/stability | Pass: unchanged original `execFile` callback, raw Buffer capture, 600,000 ms bound and owned evidence protocol. |
| Performance | Pass: no new work beyond the already reviewed one-run recipe. |
| State/data safety | Pass: fresh fixture and exclusive one-use marker; existing metadata is never adopted or overwritten by a repeat run. |
| Input handling | Pass: canonical plan validation and pinned-input reads succeed; normalized operator identity is exact. |
| Maintainability | Pass: critical pin/canonical/readPlan and run/callback bodies are byte-equal to audited operator `3de1a8b3...`. |
| Doc/code drift | Pass: exact authority quotations and README run/accept hashes agree with the actual frozen files. |
| Build/release hygiene | Pass for admission: r3 is already source/artifact-bound, and the required matching full PASS now exists. Native outcome remains independent. |

Static comparison with the earlier audited operator confirms no change to the pin/canonical/readPlan block or run/callback body. The reviewed version/path/binding/export literals and fresh authority are the relevant differences. The five named Windows DLL identity/link allowance and path normalization remain unchanged. The run path still verifies inputs before writing the exclusive one-use marker, invokes the unchanged canonical `--run` with hidden execution, records the original callback streams, and leaves final evidence acceptance to the unchanged evidence consumer. No native adapter or app was constructed by Senua.

The frozen README is SHA256 `d7fc34217fdfcb95179e37a2ac4f20735f834e52dc9d00f83e62ad98beabb121`. The handoff manifest is SHA256 `8bcdf173db77b112b3d4c72668e02247203d2bae003006ccf484cc7080ce7efe`; all 12 listed files match their hashes and sizes. Its run and later pure accept commands name the exact operator/self/plan pins above. The preserved blocked templates and old binding notes are provenance only, not launch inputs.

Open findings: Critical 0, Major 0, Minor 0. No safety-floor violation identified. Senua executed only pure metadata validation, pinned reads and file/hash inspection; no phase/native/app invocation, test suite or UI action. The single native run and its original callback/evidence verdict belong to Futaba. The release still requires that independent outcome.
