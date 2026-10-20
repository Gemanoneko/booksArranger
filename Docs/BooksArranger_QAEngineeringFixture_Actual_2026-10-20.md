# Engineering fixture actual result — 2026-10-20

Invocation `00b8fb63-d4ac-4d74-a1e4-ef6c22730dc1` ran exactly once after the conditional and final-delta reviews. Result: **GROUP FAIL; original outer native closure proven**. This is engineering evidence, not formal product QA or release admission.

The original exec_command result was chunk `d0163a`, exit 1, wall 1.8090521 seconds, no session. Its API output is combined; it reported the diagnostic location and `Native fixture observer REFUSED: Owned operation failed or uncertain`. The saved controller reason is `EBUSY` renaming the fixture `branch` directory to `branch-original`. These facts do not establish the holder or underlying cause. No retry, cleanup or source change occurred.

| Layer/case | Actual result | Native closure facts |
|---|---|---|
| Outer owner `5a7f5aa3-bb40-4df7-b436-dddaa6d4df3a` | controller code 2; ok false; 1300.6338 ms | closed true; active 0; retained 21; unsignaled 0; zero true |
| nested-final | code 0; ok true; 324.057 ms; eight short-leaf markers plus final stdout/stderr | closed true; active 0; retained 12; unsignaled 0 |
| linger-root | code 0; ok true; 478.8857 ms; `linger-root-final` and late `linger-lease-denied-final` captured | closed true; active 0; retained 5; unsignaled 0 |
| flood / wait | Not started in saved phase inventory | No claim |

Each saved result native snapshot equals its same-owner terminal evidence; all retained observed members are signaled, and failure/close-error fields are empty. The outer supervisor is PID 93640, creation FILETIME 134370023241808137. No force, timeout, overflow, truncation or image-query failure is reported. Listed/signaled comparison is **UNEXERCISED in this run**; the prior accepted component remains separate. The namespace birth/substitution check failed, and no final separate companion-close record exists. No full seven-check/four-case PASS is claimed.

Fresh preflight at 20:38:38.318Z verified all 152 pin occurrences, source31/runtime95 declared identities and both absent run roots. Postflight at 20:39:23.700Z verified the same pins and final-review/plan hashes unchanged. Preparation, admission, inputs, runtime and source bytes remain frozen. Startup/imports and ordinary OS IO retain their reviewed trust limitations; tool exit is not substituted for native closure. Older failed/unknown groups are unchanged.

Evidence (all immutable session scratch):

- Original tool record: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/qa-native-fixture-plan-v1-VzIVqp/engineering-fixture-actual-tool-00b8fb63-d4ac-4d74-a1e4-ef6c22730dc1.json` — 1363 bytes; SHA256 `46e1c65479ae694f6d28183f69bd2619e77408c8035f741a40a239f7fbcb74a4`.
- Full receipt/pins/joins: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/qa-native-fixture-plan-v1-VzIVqp/engineering-fixture-actual-result-00b8fb63-d4ac-4d74-a1e4-ef6c22730dc1.json` — 44501 bytes; SHA256 `8a8f9323a5ecd4c6b64db9178c1a47c4f80609118097dc3f3068f76e5cf72780`.
- Owner result: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/native-fixture-diag-00b8fb63-d4ac-4d74-a1e4-ef6c22730dc1/owner-result.json` — 16114 bytes; SHA256 `87eb22c8d3f49dd15c4166a9e805bf8bae17ae480bd9e3a214fd0a618b4aa4bf`.
- nested-final: SHA256 `0e961f7ca01febcb4033a9648700135daa52c75adcacc21b1853f6ce134b11df`.
- linger-root: SHA256 `a81705b7ad47e626fc431eb3c18e7bd35d2418b48c29c3dd61e2752bccc61a13`.
- Controller error: SHA256 `487f8b6d0dae1d536c7b410b53b27b9b409b290d0d6e23de970f8aa1284ce1bf`.

STOP after saved-evidence collection. No compiler, product tests, global changes, installation, media/live catalog actions or automatic next stage.
