# Books Arranger 0.26.0 QA — corrected r2 build, 2026-11-05

**Verdict:** NO-GO. The single full schema 3 entry on build `696fda91-c49f-4294-8cea-054f9ee4c912` failed. No same-build repeat or native/hidden packaged check was run.

Release source commit: `a7e20113fabcb5c7a4c7896e8b64304aa918eafc` (clean). Release artifact manifest SHA256: `9f538ebe75163c31ead29d5794b277cf026443ab0192d970f91efdb14bea61ef`. Runtime pointer SHA256: `7abf4088f166b8f09d56bf5c39fb1ba93f04316d4628025d3d16d8eae32672ee`. Context SHA256: `77154febfda44ea5d6efd397e9a0eedbaf7c40b4cbe3f4fcebaa2145f06371d0`.

All 13 Python batches passed: 2,447 methods executed, zero failures, errors or skips. The Node test runner then passed 242 tests. The focused frontend side phase passed several scripts before `tests/test_browser.js` exited 1: its isolated DOM raised `TypeError: approval.removeAttribute is not a function` in `controls` at `evalmachine.<anonymous>:602:76`. Ender is diagnosing the browser test setup against the committed app code. The remaining frontend scripts and native phase were not reached.

The owned check exited 1 after 534.6 s; the outer callback finished after 572.5 s. It closed normally with complete output and native zero, without force, timeout or output overflow. The personal-folder audit was clean.

[Exact receipt, raw callback, failure index, batch summary, context manifests and file hashes](Evidence/v0.26.0_2026-11-05/full-entry-a7e-r2-failure/summary.json) are retained. Receipt SHA256: `1eb3fd4c061eb780a9a7e5684d66c8b793ecf87df9809c151b46ecb7722808c2`. The q27 private source/context/ownership root remains intact for read-only diagnosis. This release gate failure is not evidence of a recurring user-facing pattern; disposition is to diagnose and correct the exact issue, then verify on a newly pinned build.

Entry-check receipt v2: books-arranger v0.26.0 @ a7e20113fabcb5c7a4c7896e8b64304aa918eafc (dirty: N) [source:efbf0b752a8784512c9a4683bf7a1af92eeedbee5701dcf93275191cc87e7532; harness:b3cb287fc0ecb6485289bc10deed63509a129191d7d6e2989ba21914ced808fe; runtime:7156e0d940c5e5df988b2406f509620647af07b755a405bc4d73508a5f2d4eca; checker:4bae2cde4e4cdd2f22fb3060571730ec32fec1dd5403ea070086973b18b695e4] — pre-qa n/a, post-build n/a, check-electron n/a, check fail (owned check), test:smoke n/a; personal-folders clean
