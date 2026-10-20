# Completed-candidate migration receipt — 2026-10-20

SOURCE ONLY, pending independent review and executable verification. No actual catalog/native/media IO, planning, migration or application action was run.

The planner independently counts latest non-set-aside completed jobs for current candidate IDs before review/native eligibility. It no longer loses a completed candidate behind the aggregate not_approved counter: that candidate receives an explicit current-review-unapproved hold. Missing/revision-mismatched context continues to receive an explicit hold. No metadata approval or publication authority is inferred from completed state.

Additive completed_candidate_completeness has schema books-completed-candidate-accounting-v1, immutable census candidate/completed-job/manifest-hash bindings and exactly one reasoned enrolled/already_at_destination/held/verification_deferred disposition per census ID. Duplicate census/outcomes, unknown outcomes, missing outcomes and unsupported/empty reasons refuse. It never labels enrollment as moved. The actual drained census is measured, with no hardcoded407 or Ready384 cutoff.

Only migration_planning.py and existing tests/test_migration_planning.py changed. The unchanged operator accepts additive top-level fields, reads the exact SHA-pinned whole plan and retains existing publication/root/native identity checks. The accounting receipt does not add move authority. Exact producer/consumer literal audit is in the source packet; existing check-desktop already discovers the planning test module.

Nine new pure Python cases cover three independent completed candidates (approved, unapproved, context missing), noncompleted exclusion, latest/set-aside ordering, duplicate census/outcomes, unknown/missing outcomes, typed reasons, and explicit deferred/already outcomes. **UNRUN**: the available in-process kernel is Node, with no established in-process Python interpreter. The brief forbids launching a process. No JS mirror was substituted for production Python tests. A finite separately admitted pure Python execution route is required; native integration regressions are also not rerun under this source-only brief.

migration_planning.py SHA256 ae4f85adbc1e1017a6873a0416d07c0390db712e379339a2b2b341c0e1c70ce4
tests/test_migration_planning.py SHA256 5c9a1f862d4aad8549be948c306c21fc37520189a18eb5bbfdd75fafa143d354

Source packet C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/migration-completeness-source-packet-v1.json SHA256 f736a77d64b3db0d3ae76ea2b60b7da80a2baed2122f27ef75a88f5ba07eb7a6
