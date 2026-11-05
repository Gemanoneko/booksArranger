# Final restoration identity handoff

This is the current frozen handoff: app f2f2c279 / index ac82a817. It supersedes the parent 9ccb and `source-guards-final` a6aa snapshots. `summary.json` lists all 18 exact raw source/test pins; `implementation.patch` is the complete delta from base 9bcc.

Senua UI-M1 is covered at both write acknowledgment and read restoration: ID/path/revision/fingerprint/size/modified must still match before old responses clear drafts, replace rows or restore effective owner fields. The final residual uses the same helper in owner-read success/error callbacks and includes file size/modified in poll invalidation. This prevents a delayed file-owner reply from restoring accepted old-generation metadata onto the current file form.

Senua UI-M2 is covered by reusing only accepted/applying effective intents. An explicit fresh retry of terminal needs_review records a new current-revision decision even when values are unchanged. Accepted pending repeat presses still reuse the exact current receipt; ever-uncertain historical requests keep their original request ID/body/hash through auth failure or 404→422 until reconciled.

`restoration-a6aa-red` proves the exact a6aa source displays an accepted old-file reader over the current size/mtime generation. The corrected focused fixtures pass, and `restoration-final-affected` proves all 32 affected/shared-harness DOM scripts PASS (5.869s, code0, closed/outputComplete, native complete/zero; no timeout/force). Earlier exact9ccb REDs and their corrected source-generation/terminal-retry fixtures are retained in `source-guards-final`. Syntax passed.

`restoration-identity.patch` is the final three-line residual delta from a6aa. `all-review-corrections.patch` is the total semantic review correction from9ccb. These are semantic changes; the earlier f81 actual six-action Handler bridge remains historical. Futaba must bind the final committed combined source with its real Handler QA. No full entry, build, installed/native UI, focus or live-library action was performed in this lane.

The task-owned scratch is removed after evidence preservation. `runner/` archives the exact owned launcher, test runner and a6aa baseline loader used. Product/source remains in the named worktree for Sully integration after the separate bounded reviews.
