# Books Arranger — attention audio source-slice review

2026-10-20, Senua. **Scope: source slice only, not release clearance.** Static red-team review of the working audio delta against v0.19.0 `0469966`, while other agents edit disjoint product areas. This does not certify the whole working tree, packaged behavior, migration, a commit range for release, or a formal QA receipt. No independent test execution, live catalog/source read, media mutation or app launch was performed by Senua.

## Findings

**Major — new native/audio controls absent from integrated graph; resolved in source during review.** Initially `scripts/check-desktop.mjs` omitted `test_attention_audio_admission.py`, so its ten controls would not execute in the canonical sender/receiver check. Ender added the explicit pattern. Senua independently read it at line28; script SHA256 is `eaa5e36a70cbe1d770b8ffc95e6f2b0fb4efb44d6a6008f559cf335328c9ea70`. Integrated execution/discovery outcomes remain pending. The original finding concerned coverage, not an unsafe product proof.

**Minor — obsolete repair wording in test docstring.** `tests/test_attention_audio_admission.py` describes a text-table repair, although accepted implementation preserves the invalid zero count. Change the descriptive wording to the byte-preserving profile to avoid future accidental count correction. No functional defect follows from the current wording.

No Critical finding or always-blocking safety-floor violation identified in this pinned audio delta. This statement is limited source-review advice, not RELEASE CLEAR. The integrated-graph source correction was observed; independent execution remains pending.

## Construction reviewed

- `zone_identifier.readable_source_streams` requires the same unique read-only protected base file, accepts plain data or a sole bounded recognized Zone.Identifier, and limits its NUL exception to the exact observed 27-byte marker. It holds an exact read-only native marker handle with deny-write/delete sharing; checks stream set, size, volume, attributes, identity and bytes; and exposes a recheck used immediately before enqueue in both M4B admission methods. Unknown/additional/oversized/unrecognized streams refuse. Existing recognized marker metadata without NUL remains accepted through `_known_marker`; this is not a general strip-NUL rule. The helper performs no deletion or marker rewrite.
- `source_cleanup.single_stream` and existing marker-removal implementation remain unchanged. Read admission does not grant original/recovery deletion authority. Existing cleanup preserves arbitrary bounded marker bytes in durable receipts under the October 18 rule, separate from this stricter read-admission parser.
- `profile_zero_chapter_count` requires text handler, the exact 67-byte observed sample description, fixed size16/count0, one32-bit offset table bounded1..99, exact single stsc mapping1/1/1, and exact serial16-byte text payloads. Virtual count is independently derived from chunks and then passed through the unchanged strict validator, including timing clock, self-contained dataref, mapping and retained mdat extents. Whole-plan reference and global-overlap checks remain. Nonzero wrong counts, different audio tables, bad payloads and timing mismatch still refuse.
- The virtual box is not published: `expected` retains every original native track byte, original track SHA is recorded, and profile notes explicitly disclose the preserved invalid count and independent mapped count. Receipts carry that note. There is no new repair kind or synthetic chapter list. Existing repair diagnosis treats a preservation-supported file as requiring no repair; it does not correct this malformed field.
- The production pipeline independently verifies every retained byte and approved appended movie; hashes source against frozen manifest; compares complete packet/decoder/presentation evidence and full native decoded PCM; and requires source/output/frozen chapter lists to match. These checks were not relaxed. A four-byte count correction that exposes new chapters would still fail the chapter guard.
- Retry eligibility adds the historical sample-table reason only as a route to fresh planner proof, not blanket admission. Existing parent hash/review/source equality, one-child ledger and working-file refusal remain. The two changed MergeService admission methods retain native source/module handles, frozen candidate/context checks and pre-enqueue stream recheck. Other MergeService edits belong to separate review.

## Execution evidence read, not rerun

Read Ender's `Docs/BooksArranger_AttentionFixes_2026-10-20.md` and the saved JSON at `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/observed-text-count/byte-preserved-profile-proof.json`. It records the two exact jobs, matching frozen hashes, complete retained-byte verification, source/output recognition of the same writer note, equal full packet/decoder/presentation and PCM evidence, and empty frozen/source/output chapter lists. Mapped text samples are19/35. These are developer-owned actual execution records; Senua independently read their contents but did not reproduce media checks or native ownership closure. The diagnostic candidates remain scratch evidence, not approved converted publications or iTunes inputs.

Ender reports145 earlier focused cases and a final10-case suite, with native active/unsignaled0 at closure. Source review confirms the ten test methods and their native ADS/alias/negative-profile intent; reported PASS and native closure are not independently re-executed here. The formal integrated handoff remains pending, including corrected graph, immutable protocol-2 context, actual independent sender/receiver runs and matching receipts.

Сказка's unproved producer closure and the damaged MP3 remain held. No PID-age inference, unsafe file retirement, corrupt-audio skip or blind retry was added. Source replacement/reconciliation remains separately scoped work.

## Pinned input identity

The first six hashes below were read before and after the review and were unchanged. MergeService is pinned as the observed complete file hash, but review covers only `_retry_preserved_m4b` and `_repair_damaged_m4b`; concurrent unrelated edits invalidate any broader interpretation.

| File | SHA256 |
|---|---|
| failed_m4b_retry.py | `274e8dab8183e60dcc1b4e3c427767d7638856fe19e1484cebcc9af9614042ae` |
| m4b_preservation.py | `a3ca16290c260d9691c555e7186e09a79cf255f19f3b3244a055cb82ab5d1d01` |
| m4b_repair.py (unchanged consumer) | `8ba5cb6435e8a99e479cf231811e056f8a18c3e251921a0fa9414df2e6a4d895` |
| zone_identifier.py | `62876ee26d142b536c0e508c7063cb0e5bd589670c578b51a46334cf229944b3` |
| source_cleanup.py (unchanged safety consumer) | `72453a6faf19b0ccbc9f9bddd4e428c5586a8ffa186ffea869d0cb8e96151ba5` |
| tests/test_attention_audio_admission.py | `8b61dd31d1b0a5cbe4ea3d160603c4450d47bc63bbc22ae1fc368ef600efbf57` |
| merge_service.py (observed whole file; two methods reviewed) | `c863c4ebb1cc0c60432b8d1186a7b2870e6d71d5b9d08209a0139f828355ed2f` |

Created only this review document; no scratch/disposable output was created or removed. Preserve session scratch and unresolved evidence per the user's session exception. Whole-product diff review and release acceptance remain separate.
