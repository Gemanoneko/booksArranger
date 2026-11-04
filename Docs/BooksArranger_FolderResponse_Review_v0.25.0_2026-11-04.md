# Books Arranger 0.25.0 — folder-response source review

Reviewer: Senua. Date: 2026-11-04.

Reviewed commit range: `a4e43d05e8a456dc3999b309b4f767dc45fc31e3..7cca37ded8acbfde31ecbc01dc3cfa301d6d447a`. Source/test scope: six files, +130 / -11. This is a source-slice assessment, not a final release verdict. The source-decode consumers and further navigation/editor changes remain separate work.

## Finding

**F1 [Major], performance — `merge_service.py:5331`: output-folder navigation still synchronously refreshes the candidate.** The new catalog-only `_source_directories()` removes the grouping wait for an existing source folder. However, a missing source folder recurses into `open_folder(..., 'output')`, where `reviews._row()` still reaches `Inventory.candidate()` and can wait for an unrelated worker holding the grouping lock when the global revision is stale. A direct output-folder press uses the same path. The seven-case receipt covers the fallback's normal behavior, but its held-lock tests exercise the existing-source path. Sent to Ender as a concrete remaining latency case; this does not expand filesystem authority.

Open findings in this slice: Critical 0, Major 1, Minor 0. No safety-floor violation identified. F1 is advisory under ProcessRules; it is not an additional release gate.

## Checked boundaries

| Dimension | Status for this slice |
|---|---|
| Security | Pass: opaque record/selected-directory IDs remain required, configured roots and native ancestry remain checked, and Explorer dispatch keeps its argument-vector contract. |
| Correctness and logic | Pass for the changed source lookup: active catalog evidence supplies only the shown candidate's source folders; archived/superseded/out-of-root candidates refuse. |
| Crash and stability | Pass: known access refusals carry typed local HTTP outcomes; uncertain requests end with an unknown-outcome message and enabled retry. |
| Performance | Concerns: existing-source dispatch avoids unrelated grouping/review/operation work, but F1 remains on the output/fallback route. |
| State and data safety | Pass: catalog-only navigation grants no write/delete authority; native path protection is still required before dispatch. |
| Input handling | Pass: selected directory remains catalog-derived, and per-row generation/attempt state suppresses duplicate pending presses and stale completion effects. |
| Maintainability | Pass: navigation lookup and known dispatch refusal have bounded, distinct responsibilities. |
| Doc/code drift | Concerns only to the extent of F1: prompt source dispatch does not yet cover every fallback/output navigation path. |
| Build/release hygiene | Source scope passes: no dependency or runner-graph change; final accumulated source and package remain pending. |

The UI reports waiting after three seconds and ends an unanswered request after 30 seconds. It does not silently retry an uncertain Explorer dispatch or infer a disconnected drive from a generic error. Existing source identity, configured-root membership, opaque directory selection and no-reparse ancestry checks remain intact.

## Evidence audit

Verified summary SHA256 `68950c212abc60ba70597dbd99b64a9bff3dad0834f9087d2a133bdce685c3e7` and patch SHA256 `b778381f979c0b4ad07b5432f61be7967ecf69c53e47bbf4faada0faa5ac7b71` under `Docs/Evidence/converted-duplicate_2026-11-04/folder-response`. All six committed source/test LF-normalized hashes and all 14 listed evidence hashes match.

The preserved baseline test fails because dispatch occurs after the grouping worker releases its lock. The corrected receipt records dispatch at 0.012297 seconds before worker release at 0.012325 seconds, while the real HTTP token/admission route also succeeds with Explorer mocked and unrelated group/review/operation locks retained. The frozen seven-case cohort passes in 2.872 seconds with complete owned closure, native zero, no force and no timeout. Three frontend scripts pass, including pending/unknown/error/retry/late-reply/generation cases. The wrong-selector error and three unrelated long-private-path failures in broader runs remain preserved and are not represented as a full pass.

Senua ran no tests, apps or native probes, took no focus and accessed no live library. Final release clearance must await the remaining requested source, independent QA, accumulated range review and exact build binding.
