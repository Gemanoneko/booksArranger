# Books Arranger legacy-copy proof — 10 October 2026

Read-only eligibility proof: all four finite checked M4B copies have exact independently anchored bytes. No production catalog changes, conversion, or deletion was executed.

| Copy | Exact raw bytes | Independently anchored raw SHA256 |
|---|---:|---|
| eye | 1300066162 | 59f1527a05f1115f36e80473d0b94127612cd3ca6ad1b1e293f2aa0d68d61ff7 |
| mirror | 117288167 | cee37820d6592043052721327128aacd040d0f73009c73087fb104f3e154ccf7 |
| snapshot | 254315396 | d788417424a15a9d72843c12702275b17cb97f04f08d5364e8ba549485e55f30 |
| repair | 1300067893 | c88c390c02996e7e73a9e4ee0737f5f5a40b7b1f25260cf294e8ae851975d9cb |

Eye equals its immutable validated final. The other three raw hashes were independently reconstructed from the immutable final, replacing the canonical65-byte chapter description with the exact pinned producer59-byte entry and subtracting6 from each stco/co64 offset. Both forward full normalized hashes and inverse full raw hashes matched, including saved mdat hashes and exact final chapters (11,10,40). Full raw/final file and ancestry protection remained open through each proof. The large artifacts were hashed as exact virtual normalization byte streams to avoid creating redundant gigabyte copies; a tiny actual production normalize output proved the streamed calculation identical.

The independent FFmpeg8.1.1 tiny fixture pins the entire59-byte entry (SHA2568cf704704822228ad2d3ae24a04bd51efe482c18620dafad45ac5f92367c2de6) and overwritten43-byte body (SHA256ab38f726afcf355e35e93c151982ef4510e3759aedd6455832a48b8bb111cce5). Its explicit write_btrt=0 omits the optional20-byte bitrate atom; the first default fixture demonstrated that optional atom. FFmpeg binary SHA25609948d4cdd0650da6ff5a87577469f2a218dc2615ae379f8f734d24c49de0f73. All43 single-byte body corruptions produced identical normalized bytes but were rejected by the producer-entry equality guard; altered chunk offsets failed normalized equality. See FFmpeg primary implementation: https://raw.githubusercontent.com/FFmpeg/FFmpeg/n8.1.1/libavformat/movenc.c (subtitle sample description writer).

Compact source/evidence is pinned in scratch/retention-cleanup-2026-10-10/legacy-proof/evidence-index.json, including four proof JSONs, tiny fixture proof, transform snapshot and adversarial checks. The finite-caller-contract.json contains exact three authorization rows and the exact repair tuple, plus current corrected-final ancestry/hash/size/chapter requirements. finite_caller_plan.py verifies these pins and emits the plan; it has no mutation path. Parent must implement and obtain QA/Senua review on the executing caller before use. Production execution must stop the previous service, acquire exclusive catalog_lock, reject active/unfinished work, check current source/runtime/catalog/proof pins, and keep the corrected final/parent/journal native guards open THROUGH discard_repair_copy. All unproven tiny diagnostics remain preserved.

Measured four targets from the fixed completed-job and completed-repair records, four complete raw/full-final hash comparisons, exact chapter lists from bounded owned FFprobe children,43 overwritten-field mutations and two altered chunk tables. Largest individual proof29.292s; total deadline600000ms. All owned media processes closed through OwnedProcessJob; no UI/focus.
