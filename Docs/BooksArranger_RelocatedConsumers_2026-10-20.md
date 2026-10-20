# Books Arranger relocated replacement and chapter consumers — 2026-10-20

Developer implementation evidence only; no formal QA, release clearance or live migration. Protocol reference: `BooksArranger_OutputRelocation_Protocol_2026-10-20.md` pinned at `10de6b5`; resolver correction review reference `125c9b7`. The current corrected adapter source must be reviewed with this consumer diff.

## Immutable and effective records

Original job manifests, output receipts, publication intents, chapter journals, replacement approval's three original paths and previous-publication records retain their original values. Effective locations are separate records with their own relocation envelopes and generations. `base`, `Chapters`, `Chaptersv2` and `replacement` resolve independently. No string replacement or blanket root allowance is used.

Primary Ender's `PublicationBindings` API supplies `current(original, kind, job, repair_journal_sha256=...)` snapshots and `guard(db, original, envelope, kind=..., repair_journal_sha256=..., require_transaction=True)` checks in the caller's retained SQLite write transaction. The binding adapter requires a bound chapter's frozen accepted `repair_journal_sha256` to equal the freshly authorized journal digest. The caller still supplies native-held journal authorization; a base publication proof alone cannot authorize a derived output.

## Consumer map

| Consumer | Effective-location behavior | Preserved authority |
| --- | --- | --- |
| `replacement_media.prepare_replacement` | Optional exact original/effective envelope selects the new final sibling and explicit output root. | Original manifest destination must still equal original output; immutable source root, tracks, sources and parent remain unchanged. Effective dictionary must exactly equal original receipt plus envelope location. |
| `MergeService.replace_audiobook` | Captures each of the three former publications independently, holding its native final and authoritative chapter journal while enqueueing. | Approval retains original paths; separate `former_locations` stores original/effective receipts, kind, generation and journal digest. All are rechecked in the actual replacement admission transaction. |
| `Replacements.admission` | Guards the exact three snapshots on the same connection immediately before relation/retirement rows are inserted. | Stale source/context/manifest/parent checks remain. Replacement manifest is frozen in full. |
| `CurrentAudiobooks.protect_former` | Yields original-path keyed authoritative mappings for base and both chapter variants; holds native repair journal handles throughout retirement. | Both exact completed chapter journals are required, with their fresh facts/ancestry/full hashes and immutable publication IDs. |
| `ReplacementRetirement.run` | Operates each effective former path and current successor, with full held hash, native identity and ancestry. | Original retirement-row keys and provenance remain unchanged. Every former and successor generation is checked in the same `BEGIN IMMEDIATE` transaction as exact old-handle disposition, handle closure, absence check and removed-receipt CAS. |
| Replacement recovery purge/history | Uses effective successor and former locations. Purge checks current generation through native recovery deletion/closure/receipt transaction. | Immutable original ownership remains required; bound successor additionally requires effective ownership. Migrated interrupted removal with absence and no exact native-owner closure is held, never inferred from absence. |
| `MergeService._finish_replacement` | Protects effective successor path but publishes its original immutable receipt. | Exact current envelope is rechecked inside the replacement publication transaction. |
| `chapter_repair.restore` | Reads the bound effective base and creates the derived sibling under that effective output root. | Parent original output/path/manifest remain frozen; journal separately records the effective parent and exact generation. Full audio presentation, chapter and cover safeguards remain. |
| `chapter_repair.recover` | Optional authoritative callback plus independently protected derived binding allows recovery at a relocated chapter path. | Parent provenance is separately required. Without fresh authoritative callback, a bound derived output is refused. Journal content is never rewritten. |
| `StorageCleanup.discard_repair_copy` | Freshly authorizes the exact held journal, protects the derived effective final, then checks its independent generation during copy disposition. | Parent protected output remains independent; held derived identity/ancestry/full hash and journal digest are required. The owned checked-copy root is kept separate from the effective final root. |

`Replacements.file_transition` and `file_purged` accept an optional retained SQLite connection. It must already be inside a transaction; they do not commit or open another writer. Legacy callers retain their original API. No adapter protection reservation is held while attempting a separate connection write.

## Fail-closed boundaries

An effective path does not waive full-content, native identity, ancestry, stream or ownership checks. Original input sources remain untouched. A changed current successor, derived journal digest, generation, receipt or metadata context prevents disposal. If an interrupted migrated former-file removal has no completed receipt and no exact native-owner closure capability, the app preserves recovery and reports a hold rather than adopting missing-name evidence.

The current protocol allows one frozen migration target per immutable publication ID. It does not authorize a second target or later generation rewriting of a saved chapter-parent location. Primary Ender confirmed that the real migration runs under the drained app owner, so chapter creation cannot occur midway between base location commit and completion. An unsupported later parent-generation change remains held; no historical generation waiver was added.

## Focused evidence and corrected regressions

The new replacement consumer fixtures use actual private native files and full hashes with structurally synthetic relocation history. They test consumer binding and closure, not production media migration admission or filesystem durability. Base, Chapters and Chaptersv2 have distinct ledger IDs and different effective folders; the successor has its own fourth location. The tests prove native retirement removes only effective former outputs, retains immutable original names and all input sources, and records handle closure without changing approval/history JSON. A stale independent chapter generation prevents the first disposal, and a wrong chapter journal digest cannot be replaced by base authority.

The new actual media fixture creates a real chapterless AAC audiobook, binds an effective base, restores Cyrillic chapter labels there with existing full presentation/cover checks, then independently binds the repaired publication. It checks authorized recovery and checked-copy cleanup at the effective derived final, with a negative derived-generation guard preserving the checked copy and all original inputs.

Two actual integration bugs were caught and corrected by these fixtures: the adapter's context-exit lookup dropped the fresh repair journal digest (fixed by primary Ender); cleanup reused its owned-copy `root` variable for the effective final root (fixed by keeping them separate). The tests retain both positive paths and their negative controls.

First legacy replacement run: 39/41 passed; two errors were old mock callback signatures lacking the new retained `db`/root arguments. Only those signatures/forwarding were updated, with their original native-protection assertions preserved. Final combined results are recorded at closeout below.

All new fixture paths honor `BOOKS_QA_FIXTURE_ROOT` or use the retained per-session shared scratch. No live app, catalog, media, settings, UI, iTunes or process state was changed. Session scratch remains for Sergei's manual cleanup.

## Closeout developer checks

The attempted combined replacement/jobs/new-consumer/full-media command has **no test result**. The reviewed native owner stopped it after 92.940 seconds with `Native job membership list is incomplete`; it returned `forced=true`, `closed=true`, `active=0`, `unsignaled=0`, `zero=true`, and no buffered test output. No duplicate command or supervisor change followed. Jane authorized smaller coherent checks through the identical existing native owner only after verified closure. The combined/full gate remains unresolved pending supported-runner evaluation; passing focused checks below do not claim that gate passed.

The separately closed, sequential focused runs passed **60 tests**:

- Existing `test_replacement_jobs.py`: 41 passed in 12.249 seconds, including unchanged native recovery protection across old-handle close/absence/receipt CAS and interrupted disposition behavior.
- New `test_relocated_replacement.py`: 4 passed in 2.674 seconds, covering three independently routed former publications, fourth successor location, fresh chapter-journal rejection, stale derived generation before first disposition, and exact-bound replacement planning preserving the original source manifest.
- New `test_relocated_chapter_repair.py`: 1 passed in 11.869 seconds, exercising actual AAC repair, independent authorized relocated recovery, derived-generation negative control and checked-copy disposal.
- Existing `test_replacement_media.ReplacementProofTests`: 14 passed in 0.038 seconds. The heavy forty-source media class was not retried after the combined ownership uncertainty.

Every focused run used the unchanged reviewed native-owned bounded route with `timeoutMs=600000`, returned `ok=true`, `closed=true`, `forced=false`, `timedOut=false`, and native `active=0`, `unsignaled=0`, `zero=true`. These are developer checks, not formal QA or a release verdict. No live migration or filesystem durability capability was assessed.
