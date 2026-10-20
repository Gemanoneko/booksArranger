# Concrete derived publication migration fixture — 2026-10-20

Developer evidence only. No live library/catalog/settings/queue, iTunes, UI, installer/compiler or release action. This fixture follows the original relocation protocol `10de6b5`, operation documentation reference `ffedfbf`, and primary Ender's two-Major correction checkpoint authorized by pinned review `bb339a9`.

`tests/test_derived_migration.py` creates an actual private retained-source conversion, then performs the existing real corrected AAC chapter restoration with Cyrillic source-track labels and its full presentation/cover checks. It asserts that this derived file has no `verified_outputs` entry. The test neither inserts a verification cache entry nor fabricates a resolver binding, output receipt, media validation, publication history or journal.

It closes the private service, acquires the real native `catalog_lock`, calls actual `migration_planning.prepare`, writes a new SHA-pinned reviewable plan outside the catalog and libraries, and runs the concrete `MigrationOperation` for the single selected publication. The test requires:

- Exactly one current publication, `Chaptersv2`, with the corrected file as source; the superseded base is excluded from the import tree.
- Fresh execution of the real authoritative chapter-journal verifier and its exact journal digest in the typed `books-authorized-chapter-output-v1` sealed-media proof.
- Actual complete source/destination hashes, no-replace publication, same retained write-capable parent flush, location binding, old-file disposition and a final `moved`/verified/complete outcome.
- The derived original path absent and the sole destination M4B present with the expected full hash.
- Base job row/immutable output journal, base bytes, original corrected-artifact journal bytes and all retained input hashes unchanged.

The actual first execution after primary declared the product correction ready passed **1 test in 12.588 seconds**. The unchanged reviewed native-owned bounded runner used `timeoutMs=600000` and returned `ok=true`, `closed=true`, `forced=false`, `timedOut=false`, native `active=0`, `unsignaled=0`, `zero=true` (retained58). No duplicate run, supervisor change or combined heavy command was used.

Read-only inspection of that test's retained plan also confirmed `scope_counts.uncached_variants_fully_hashed=1`, `enrolled=1`, `held=0`, `approved_candidates=1`, `current_candidates=1`, and `not_approved=0`. The fixture plan is `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/derived-migration/reviewed-plans/34bfe080-1990-458d-be86-353006b1437b.json`, SHA256 `f5356a522b14eb5d44dd7f7390264a87bc8521891a0caff6e2c7c03bf752c123`. Session evidence is retained for Sergei's manual cleanup.

## Execution source pins

| Source | SHA256 |
| --- | --- |
| tests/test_derived_migration.py | b6d8d19d94298078db3407102190a4545f901f28e7744a10e9642e5ddccf7fe8 |
| migration_planning.py | 381117ad7917f7a16755530b04fcd02cc31e7ccee0dbb9b7715a57813ceb0222 |
| migration_operation.py | 60d87fbe730f5bacbc340b7c828840ac189be297b2d6c1e26803e2523da06e33 |
| publication_binding.py | 6230cfd9413dc7cfaf88a936a24a6a80039c612b660bd3ab6bfd9eda172d299a |
| output_migration.py | 453e1500ba3cb75d5f50abc77b5e51029ee994351f3bda44d455d7e660d57c8c |
| native_io.py | e5e6aef41da64308215d10b636d6e583635b7e2476c7d90a7158d8ad4525dc14 |

This slice changed only the new fixture and this evidence document. Product corrections belong to primary Ender. Entry/source/destination/kind/candidate/size/root mismatch controls are his operator tests, not claimed as additional coverage here. Successful private local OS flush is not a NAS hardware persistence promise or live deletion clearance. Formal QA, the unresolved combined heavy gate/native-owner membership limitation, independent compiler NO RESULT and full release review remain separate; this fixture does not close those gates.

## Final-source primary verification

Jane explicitly authorized primary Ender to repeat the single unchanged actual derived test after the planner gained durable verification-cache progress. Final source: migration_planning.py1a76c4d8a8af5623ae1b57ffa1eda6d839dc07bd647e6469174144d707558efc; migration_operation.pya12172b3cf98f7759d449c071d30793130fea4626a60cfc7c2feb8332f052cfb. Test unchangedb6d8d19d94298078db3407102190a4545f901f28e7744a10e9642e5ddccf7fe8. Result1/1PASS11.959s (owner elapsed12.362s), closedtrue, forcedfalse, active0/unsignaled0,58 retained native identities. The real uncached corrected chapter was selected, native-hashed, planned, freshly journal-authorized and actually moved by the concrete operator; immutable parent output/job/journal and source hashes remained unchanged. No live app/media operation or formal QA receipt is implied.

Following Senua’s review, only the verification-deferred explanatory message changed; final planner SHA8ba34427605b0c2b93a279c1d1bf0276e9208f1ce3c93051946c77e59528cc2a. It explicitly avoids promising that replans finish an individually over-bound file. No algorithm, test or native contract changed, so the actual derived media test was not repeated for this text correction.

After the accepted explicit preflight-selection addition, primary reran the unchanged actual derived case once:1/1PASS11.421s, owner elapsed11.817s, closedtrue/forcedfalse/native active0/unsignaled0/58 retained. Final operatione8d247893dbe1b1a3657c7f5da6321971993272e09cc97f9b14b20fb77d018bc and planningaefd085b9c2cfdcf3a9aa483b0133ca780a0c8b2a7bcf24b3b8c221525708e3b. No live action/formal receipt.
