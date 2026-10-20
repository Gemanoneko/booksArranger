# Legacy output-root manifest comparison — 2026-10-20

This narrow compatibility change adds one semantic default to the preservation-retry and damage-repair bind comparisons. It does not authorize a new Sorted root, hierarchy, destination, source, policy or queue admission. No live catalog/media/settings were accessed or changed.

Read-only baseline inspection of `0469966:failed_m4b_retry.py` and `0469966:m4b_repair.py` confirmed that both bind functions parsed the frozen manifest, removed only `job_id` and compared dictionaries directly. Therefore an old manifest lacking `output_root` differed from an otherwise identical current child explicitly containing `output_root == that old manifest.root`. The new private regression reproduces that exact old comparison refusing the otherwise equivalent pair, then checks both updated bind functions accept it without rewriting the parent's serialized manifest/hash/journal.

`manifest_compatibility.normalized_output_root(value)` copies the dictionary. Only an absent `output_root` receives that dictionary's actual nonempty string `root`; missing/malformed root is not synthesized as None. An explicit output-root value is retained verbatim, including invalid values for existing validation/equality to reject. No string/path normalization, case folding, root substitution or fallback to a configured output root occurs.

`equivalent_manifest(left, right, ignore_fields=('job_id',))` preserves already exact dictionary equality without needing a synthesized field. This preserves old minimal equal fixtures that lack both root fields. Otherwise it compares copies after that one absent-field default, removing only explicitly specified exclusions (the bind callers use the default `job_id` only). The helper does not replace full manifest validation, native/media proof or admission CAS. Already equal malformed manifests do not become validated merely because a comparison returns true.

Literal consumer map:

- `failed_m4b_retry.py`: imports `equivalent_manifest`; its `bind(parent, fresh, proof)` uses it for the existing frozen-review comparison. Eligibility, distinct child, preservation-profile proof and parent manifest/journal digests remain unchanged.
- `m4b_repair.py`: imports the same helper; `bind(parent, fresh, diagnosis, module_sha256)` uses it at the same comparison boundary. Repair diagnosis, allowlisted repair kinds, module identity and user-requested child binding remain unchanged.
- Primary Ender owns any separate `MergeService._guard` adoption of `normalized_output_root` and any explicit routing-authorized child design. Those regions were not edited in this slice.

Developer checks: **31 tests passed** through the unchanged reviewed native-owned bounded route (`timeoutMs=600000`), sequentially: six new pure compatibility cases in0.003s,21 existing `test_failed_m4b_retry.py` cases in0.986s, and four existing `RepairAdmissionContractTests` cases in0.034s. Each runner returned `ok=true`, `closed=true`, `forced=false`, `timedOut=false`, native `active=0`, `unsignaled=0`, `zero=true`.

The new tests cover serialized legacy absence/current explicit same root for both binders; parent/input immutability; changed explicit root, Sorted root, destination and spelling refusal; source membership/hash and chapter order, metadata, cover, profile, revision, options and cleanup-policy refusal; explicit null/empty/nonstring output roots remaining unequal; missing/malformed root normalization refusal; unknown new keys; and the still-required distinct child identity. They are pure contract tests, not a claim that any actual historical book passed current native/media/source checks or queued successfully. Existing SQL/CAS/repair tests retain their prior safeguards. No formal QA, release or routing clearance follows.

| Source | SHA256 |
| --- | --- |
| manifest_compatibility.py | 9d70158c6f8a247fffc6993ded82d66b308537bbb6addb919b359dbadc9efb58 |
| failed_m4b_retry.py | 24f45434afcbcd94d3bce691190c69949ce3b6863f680a8dd006527f36c02e3d |
| m4b_repair.py | ee7b9f06a279f74327948ce41c359ef7aee5bff7b383afe92fa19e689507a9fd |
| tests/test_manifest_compatibility.py | fd1c46597b6a3404280abd2036a275211927cf3799d0ae01d0249b3085962091 |

No native QA infrastructure, compiler/binary, UI, process, OS restart, queue or source lifecycle code was modified. No new scratch inputs were necessary for the pure cases; existing session evidence remains retained.
