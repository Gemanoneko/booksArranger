# Books Arranger — retention copy addendum

Date: 2026-10-10. Scope: existing cleanup/recovery text only. This supersedes persistent-retention and restore promises in BooksArranger_SourceCleanup_UX_2026-10-10.md for jobs covered by the new retention policy. No controls, layout, features or implementation changes are specified.

## Exact replacement copy

| Existing element or state | Exact text |
| --- | --- |
| Cleanup-enabled output-policy notice | Creates one audiobook, verifies it, then removes the included originals. Temporary recovery and working files are automatically removed after cleanup succeeds. Errors preserve remaining files for recovery. |
| Cleanup-enabled Create audiobook tooltip | Create and verify this audiobook, then remove its included originals and temporary files after successful cleanup. |
| Source cleanup plan fact | Source cleanup: remove originals after audiobook verification; automatically remove temporary files after successful cleanup |
| Temporary-copy preparation status | Checking temporary recovery copies |
| Originals removed, temporary purge still pending | Originals removed; temporary file cleanup pending |
| Originals removed, temporary purge running | Originals removed; removing temporary files |
| Successful original removal and verified temporary purge | Originals removed; temporary recovery and working files removed |
| Cleanup needs attention | Source cleanup needs attention: [specific reason]. Remaining originals and temporary files are preserved for recovery. |
| Existing recovery path fact while files actually remain | Temporary recovery storage: [actual location] |
| Existing recovery byte fact while files actually remain | Temporary recovery storage on C: [verified current bytes] bytes |
| Existing recovery fact after verified purge | Temporary recovery files: removed |
| Existing recovery location fact after verified purge, if rendered | Recovery location: none — temporary files removed |
| Existing recovery/restore explanatory text after verified purge, if rendered | Temporary recovery files were removed after successful cleanup. Original tracks cannot be restored from them. |

Retained-source historical jobs retain their existing notice and tooltip. Waiting, removal-count, pausing and paused text retains its existing accurate wording. Use backend-confirmed current retention/purge facts: original-removal completion alone must never select the final temporary-files-removed text. A failed purge keeps output verification and original-removal success visible, shows the actual remaining temporary files and the failure reason, and does not offer or promise restore from purged copies. Never claim all originals remain after partial removal. Do not show a removed recovery location as available storage or keep a pre-purge byte total labelled as current storage.

## Documentation corrections

BooksArranger_Brief.md currently promises persistent recovery copies and never permanently purging recovery assets. Replace that current-policy description with: **The current workflow verifies the audiobook before removing its exact included originals. Temporary recovery and working files remain until successful cleanup, then are automatically removed. Errors preserve remaining files for recovery.** Historical release records remain historical.

## Verification

Check copy for eligible pre-create, retained-source historical, partial original removal, originals removed with purge pending, successful purge, and purge failure. Existing output success remains independent of cleanup attention. Existing text areas wrap in normal flow; no target or layout changes. No probes or app interaction were performed. Design basis: NN/g visibility of system status and plain-language error recovery.
