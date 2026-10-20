# Unknown transport correction — source only

Responds to review `78c450d1f13baef366133ba542898d462b133588b8309eb29216ad7e935eba87`, pin `683811bd54bc0a6e3a94d0dfe1750d1397a70842`. Only `protected-admission.mjs`, its pure checks and this new evidence file changed. No alias decoder or admission authority was added.

Removed the raw-substring Books test from all unknown/unproved transport paths. They now preserve the exact original input as opaque fallback with `integration_stop:true` and `authority:false`. Integration must stop; fallback is no Books allow. Known cmd/workdir executable classification, direct canonical checker denial, original-owned priority, strict watchdog validation and unconditional production refusal remain.

Two meaningful before/after counterexamples: unknown command/cwd envelope containing `echo 'run_entry_checks.mjs'`, and malformed JSON containing that filename. Both previously denied; both now return unchanged opaque bytes plus integration STOP. Additional controls cover alternate-envelope search/file-read data, unknown executable-looking text, invalid command type, unmatched quote and newline. Removed the prior contradictory test expecting unknown executable-alias denial; known direct/wrapped checker controls remain.

Existing in-process Node kernel without reset: **78/78 pure checks PASS**, `native_executed:false`, `admission_authority:false`. No process/native/OS/RNG/compiler/global/QA operation. No POST or existing31/active-owner source changes. Production still refuses `native_contract_missing`; measured trusted host transport/default-shell binding remains a future gate.

| Source under scripts/qa-native/ | SHA-256 |
| --- | --- |
| protected-admission.mjs | cd58b9ef23b66e7e8280b37659dbd0a4f67d5e9ea48843ac4fdb2e999d3089ac |
| protected-admission-checks.mjs | ad6e714cd0da17398692e84db9e2adfe1e53165d94cf300d73e4ca1f65abfa3e |

Consumer scope remains the supplied pure `runAdmissionChecks` API and internal PRE validation/fixture exercise. No production integration import was added; this receipt grants no execution, deployment or formal QA clearance.
