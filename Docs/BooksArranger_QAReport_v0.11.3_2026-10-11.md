# Books Arranger QA — v0.11.3 — 2026-10-11

**Verdict:** GO for the pinned initial-view change under the Lean path. **New findings:** 0 Blocker / 0 Major / 0 Minor. The initial view is Book candidates instead of Files; manual Files selection and non-Audiobooks behavior remain available through the existing logic.

Baseline HEAD independently matched c94c496ae2f5fce6edc9bc7bbe6267cfef9fac74. Local web/app.js is 80494 bytes, SHA-256 2301cd45639d1c4025490ad903b67ae725a15ebce12588f6bbf948ba554a5fac. Independent GET http://127.0.0.1:5210/app.js returned HTTP 200 with exactly matching bytes, size and hash.

Actual Git diff changes only web/app.js:6: let view='files' → let view='candidates'. Complete baseline/current comparison confirms this is the sole literal change after line-ending normalization. Source inspection confirms viewControls still offers the existing view selector for Audiobooks and forces Files for other libraries (lines 30–34). The manual selector's change handler still takes its chosen value and refreshes inventory (line 258); refresh/poll retains the selected view and does not reset it (lines 213–251). Existing controls, filtering, manual review, processing actions and status logic are unchanged. This establishes source compatibility, not an executed UI flow or processing pass. The new default applies at page initialization; existing library-switch behavior is unchanged.

Judy's approved scope is the audiobook default, preserved manual Files access and Files for noncandidate libraries. Ender's syntax PASS was supplied as producer evidence; QA did not rerun it. No UI evaluation, new tests, framework/helper, snapshot, cache, restart, runtime/library mutation or Comics action occurred. No rendered-browser claim is made.

An already-open browser page needs a refresh to initialize the new default. No new pattern alert; inherited release limitations remain unchanged. No disposable output was created beyond this retained compact report, and prior reports/evidence remain untouched.
