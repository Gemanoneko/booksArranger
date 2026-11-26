# Code Review — Books Arranger v0.31.4

## Header

```
Reviewer: Senua
Date: 2026-11-26
Release: Books Arranger v0.31.4
Commit range: 2fd59930b394719f344bea0736de1c8ddb82ff90..c8a342ca3b96043f940dc00b9b618bd1a7dd3afb
Files changed: 24 files, +1258 / -240 (git diff --shortstat)
Tagged v0.31.3 to candidate: 744fbbaeb39ebaedb0efd71b8559a64b2354e7c2..c8a342ca3b96043f940dc00b9b618bd1a7dd3afb
Stand-down dimensions: none
```

Release source commit: c8a342ca3b96043f940dc00b9b618bd1a7dd3afb
Release artifact manifest SHA256: 870003866bf5660dcd2092cbd15f38d245ba1d943b8d904dbb60d8d55f86e6e1

## Summary

Startup now admits valid disposition journals larger than 100,000 directory members. The previous reader counted each phase receipt separately, so a catalog with 25,000 closed operations and its context marker could stop the engine before it served its first health response. The release also changes how the series and names workers handle late writes when an audiobook folder moves or a network share partly remounts. It adds bounded folder retries, preserves the last known temporary path, and records failed fresh names writes in the backend log and the existing filing list. Source cleanup and recovery share the rotating UTF-8 log. Relative to the v0.31.3 tag, the product and release delta covers 21 files, +957 / -231.

Review of candidate `481b9bc` found a data-loss path. A writer could claim an occupied temporary name and dispose of its occupant without proof that the app created it. Commit `fc38721` uses exclusive creation, records the creating handle’s native identity together with catalog ownership, and compares that identity through the disposal handle. It holds unproven old records and same-folder replacements. The same correction paginates the remount witnesses, preserves the Windows error from a failed ancestor check and records an exhausted fresh names try before catalog commit.

Commit `84c8c1b` inventories exact operation IDs and phase membership under the catalog-owner lease before applying any recovery. Each inventory entry occupies 17 bytes. A count and SHA-256 protect both the initial inventory and the bytes consumed. Above 61,680 operations, recovery uses the configured, pinned application work directory. A standalone caller without an approved work directory refuses at that threshold. Catalog admission reports the total held count and up to eight examples. Explicit support recovery retains its detailed results. Relocation and uninstall continue to consume the original flat, immutable receipts.

## Rubric

| Dimension | Status | Result |
| --- | --- | --- |
| 1. Security | Pass | File operations use typed native handles. Diagnostic text enters the renderer through `textContent`. The delta introduces no new shell command, Electron privilege or credential. |
| 2. Correctness & Logic | Concerns | m1 below concerns the display of an unconfirmed removal. |
| 3. Crash / Stability Safety | Pass | Restart paths verify ownership before disposal. Recovery checks exact inventory membership, rejects orphan phases, and preserves pending operations. The shared log writer escapes unencodable text. |
| 4. Performance | Pass | A remount check probes up to eight catalogued paths per call and advances past stale results. Folder retries use a one-minute deferral. Startup reads ledger groups in batches of 128 and keeps at most 1 MiB of group records in RAM before spilling. |
| 5. State & Data Safety | Pass | The ownership row and file identity commit together. Conflicting owners, foreign occupants, changed parents and path-only legacy receipts preserve the file. Completed-book disposal still checks both files under held handles. Recovery retains the original owner, ACL, content and closed-handle proof rules. |
| 6. Input Handling | Pass | The worker checks ancestry and the expected temporary basename. The shared log handles Unicode and multiline diagnostics. |
| 7. Maintainability | Pass | Both late writers use the same ownership, disposal and bounded-retry implementation. |
| 8. Doc/Code Drift | Pass | The seven existing changelog items correspond to tested behavior. The late startup and ownership corrections were communicated to the release manager for the release notes. |
| 9. Build & Release Hygiene | Pass | Package and lockfile both specify 0.31.4. The lockfile matches the pinned build input. Independent hashes matched all three manifest artifacts and all eleven changed packaged runtime files. |

### m1 [Minor] — An unconfirmed removal appears as kept

After a verified disposal followed by repeated failed presence checks, the ledger and audit can say “Couldn’t verify whether the old file was removed.” The summary counts every terminal hold as kept, and the could-not list maps every held cleanup retry to “The old file was not removed.” For the same synthetic unconfirmed row the counts were one kept, zero removed and zero bytes freed. The UI also classified that job as kept. Carry the unconfirmed outcome into these two display paths next cycle. See `series_backfill.py:573`, `rule_filing.py:368` and `web/app.js:1697`.

## Verification

- Independent SQLite-in-memory checks exercised ownership conflicts and transaction rollback, a reachable ninth remount witness, a nested WinError 59 through the two-retry limit, and fresh-name causes before and after catalog commit.
- The renderer’s targeted cleanup test passed. Ender’s correction log recorded 64 focused Python cases passing in 143.521 seconds, including both writers, occupied names, same-parent replacements, path-only legacy rows, known-owned cleanup and abrupt restarts.
- Build `d97dcc2d-31be-435d-b00b-ccc6a20cbcec` declares the source commit pinned above. The installer SHA-256 is `217f8b20406b0c40322825c1a335cc85a1afcc23f5b62df38b789620e16f1efd`. The installer, blockmap and updater metadata matched the release manifest. Ten changed Python modules and `web/app.js` matched the clean checkout byte for byte.
- Ender’s final startup pass completed 34/34 focused checks, including a new scan during exclusive file creation. Both writers exclude their precise active temporary file from discovery before its ownership row is committed. A same-named file in a different folder remains discoverable. Scanning grants no removal authority.
- In a private native fixture, 25,000 closed operations yielded 100,001 directory members and zero holds in 49.391 seconds. Separate controls held a malformed intent, an unsettled pending operation, a changed closed proof, and an orphan receipt. An independent memory-backed inventory test traversed 100,001 distinct operation IDs and checked each replayed ID and phase mask. The 49.391-second measurement covers journal recovery in the synthetic fixture.
- The final source commit updates the rule-filing test spy to forward the named temporary-creation callback to the real retag operation. Both single-rewrite assertions and the file, tag and catalog assertions remain. Ender reported 15/15 tests passing in that module. Git shows that this test is the sole difference from the source used for the native startup fixture and scanner controls.
- The reviewer used memory fixtures and read-only package inspection. This review created no disposable files on C:.

## Verdict

- Critical findings open — 0
- Major findings open — 0
- Minor findings open — 1

**Verdict:** RELEASE CLEAR
