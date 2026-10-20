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
