# Books Arranger code review — v0.12.0 — 2026-10-12

**Verdict:** RELEASE CLEAR

Reviewer: Senua, Codex gpt-6.1-sol xhigh. Open findings: **0 Critical / 0 Major / 1 inherited Minor**. The always-blocking safety floor is intact in the reviewed scope. Severity and release criteria follow Studio ProcessRules; the inherited Minor is advisory and remains accepted.

## Certified range and endpoint

Accumulated review range: released v0.11.3 baseline **09af951719b19a0145301b047b1786a27998a149** through source HEAD **9a5f6e66937caebc0314fc0ef2f5c0ace26f0848**, plus the exact frozen working-tree and staged frontend delta in the final manifest. Source VERSION is 0.11.3, target is 0.12.0, dirty=true. This certificate identifies the pre-release bytes; Sully owns the later version/release commit.

The review covers the phased public-work/source identity, standing metadata and fan collection, recording classification, additive v4 media policy, guarded source refresh/controller retry, admission/readiness/cleanup, and staged Ready-list frontend changes. There are 37 declared promotion paths. All source phases and the final two-test-only continuation delta have been reviewed. Canonical frontend publication and live runtime acceptance are separate from this certificate.

Artifact base: scratch/source-fallback-2026-10-11/.

| Identity | Exact value |
| --- | --- |
| Final manifest, 85 logical / 87 physical sources | source-manifest-standing-v2.json — SHA256 5927156571175832e3b7604dc43eaacc1ec76816bc658251b1a8a9727e59eaed |
| Logical source digest | b851c1eb240bc70b638c53efd9f746f675e49ae8594da37a66c2741419b90727 |
| Physical source digest | ae0e55c52d517642cf35912a13be26f2a48fcdb2b29517ee5692b3cb931bf7a6 |
| Finite continuation contract | manual-contract-standing-v2.json — SHA256 e9d9ac1b52396449ae702419447065644774b390b6467c4e4c796e942cedfabe |
| Exact inline execution source | SHA256 5794e845a6fbe05f6c151720cdbeec0ffe2aa81f7cadfd26ca9bee01b7c69c4c |
| Independent QA GO | BooksArranger_QAReport_v0.12.0_2026-10-12.md — SHA256 71abeb1d27260a79a15519cdbd0d127742e6a5cfb3c4c699d2cde1bf13a3a5a2 |

Both staged transitive aliases (web/style.css and tests/test_metadata_frontend.js) are explicit physical inputs. The retained frontend proof binds eight staged files and one separately pinned Node runtime. The corrected validator checks all nine roles before and after; no alias or runtime row is ignored. I freshly rehashed all 87 physical source inputs after the final QA, found no mismatch, recomputed both declared digests, and verified the manifest, contract and inline hashes. QA's final receipt independently records all 94 source/runtime/native/proof after-pins matching.

## Nine-dimension review

| Dimension | Conclusion at the certified bytes |
| --- | --- |
| Security | Fixed argument-array subprocess routes, retained native ownership/ordinary-path guards, bounded public URL/DNS/redirect/response handling and no new credential route. Neutral-cover native handles close in finally blocks. No new safety-floor finding. |
| Correctness and logic | Work, edition, author role, translation and collection constituents are distinguished. Contradictory explicit identities hold. Ready is exactly the existing converted-membership predicate, computed once per page and used by inspection. |
| Crash and stability | Stop, restart/Paused, source waits and classified job retries preserve durable state; uncertainty uses interruptible bounded backoff. Unknown/published/source-changed failures do not replay publication or retirement journals. |
| Performance | Existing public cache, host admission/cooldown and per-candidate bounds remain; refresh is limited to observed members and readiness polling does not add quadratic media hashing. Media proofs stream rather than retain full PCM in memory. |
| State and data safety | Active manual-draft leases are checked in both refresh snapshots; final writes are atomic. Approval and queue enrollment remain coupled. Source/output native leases, collision refusal, exact cleanup receipts and 24-hour recovery are retained. |
| Input handling | Every constituent title clue, author, order and known series ordinal is bound independently. Unsupported fan rows, uncertain spans/layouts and unknown M4B presentation bounds hold. Verified full author credits are preserved without guessed surname order. |
| Maintainability | New pure identity/metadata/recording modules keep their explicit proof boundaries. v4 encoding behavior is additive; historical profiles remain supported. Targeted fixtures exercise the actual gates. |
| Documentation/code drift | The standing rules and brief describe the bounded implementation and Held limits. One inherited HTTP-availability notice discrepancy remains below. No claim of local-dump ingestion or live-library acceptance is made. |
| Build/release hygiene | Exact staged/backend physical dependency graph, five runtimes, trusted native containment and retained receipts are bound. Finite QA uses shared deadlines and descendant/output closure. VERSION bump, clean release commit and runtime replacement remain Sully/root actions. |

## Findings closed during the reviewed phases

- Public work evidence: fetched publisher English title/author credit is required even when an English label equals the original title. Original-title catalog evidence and published-English-title evidence cite their respective fetched sources. P50/P407 qualifiers and malformed property scopes hold; work/edition and ambiguous roles do not become approval.
- Fan collections: named heading, immediately associated non-negated fan provenance and contents table must agree. Navigation/footer/sidebar material cannot supply provenance. Every numbered/linked component must parse; no trailing constituent is silently dropped. Each meaningful filename and embedded title independently matches its mapped component; author aliases remain distinct from title aliases. Known public series/name/position contradictions now reach the source gate.
- Author folders: the verified full credit is used without token-count/script-based surname inference.
- Media: producer receipts and consumer no-write/delete leases bind normalized PCM against substitution through encoding/verification. Single AAC/ALAC M4B copy binds complete chapters, compressed payload, decoder/layout, relative packet timing and skip/discard fields, full native-rate/all-channel PCM SHA/count, and canonical movie/audio presentation bounds. The final output stays held through proofs and final hash. Unknown leading/edit bounds hold. Packet-only duplicate identity is refused; reuse requires complete ordered source bytes/chapters and a fresh valid completed output.
- State: source refresh preserves protected approvals/manual drafts/jobs and rechecks exact draft id/revision/expiry at both optimistic snapshots. Controller re-research uses the current source revision, retains compact historical proof, and only remaps complete observed path coverage after a proven split. Typed retry leaves unsafe publication states untouched. v4 normalized-WAV cleanup requires exact producer attempt/name/size/hash; unrecognized same-looking files survive.
- Frontend: inspector error/changed precedence, whole-library empty status, and generation-plus-context stale rejection were corrected. Backend facts drive readiness, provenance and recording review; intermediate presentation changes do not remove admission gates or start processing.

## Open advisory finding

**Minor — inherited generic HTTP availability-notice copy/doc drift.** Connection recovery still displays the generic connection-interruption notice for specific HTTP backend failures, contrary to the older exception-specific copy expectation. The specific error feedback, stale-state indication and mutation availability gate remain intact. This release does not fix or conceal that discrepancy. It is inherited, accepted, and nonblocking.

## Actual validation and retained failed evidence

**181 unique Python cases PASS across two stages, plus four unchanged Node fixtures reused. This was not one passing 181-case invocation, and there is no identical combined producer receipt.** Earlier focused producer evidence remains attributed to Ender.

The initial independent combined attempt reached 136 cases: 134 PASS and two controller assertion failures; 45 later cases were unrun. It completed owned teardown at 144.946s. The failures were confirmed fixture drift: author expectation Writer John instead of verified John Writer, and a fake wait callback that continued advancing after Stop was signalled. Only those two test lines changed. Reversing them reproduces the entire prior test-file hash 17de762567f9964ca14ce4b04e04eea7a6109c00ce9c4e7f70f2f9ea17b7c383; current test SHA is 908e424362e63dd5d174f523483473f1ac0ae630ca1aa89b6407ebb5127bcc7b. Exact wake/attempt counts, Paused state, no-approval and all other assertions remain. Production inputs stayed unchanged, so the 134 accepted passes remain applicable.

The one authorized continuation ran exactly the two corrected cases and the previously unrun 15 media-policy, 10 encoding and 20 recording-classification cases: **47/47 PASS**, exits [0,0,0,0,0], 74.178s outer / 74.010s manual, empty outer stderr, no warning/truncation. Owned jobs and drains completed. I independently reconciled actual passing case IDs: 134 prior plus 47 continuation, no overlap, 181 unique.

The four automatic/connection/progress/cleanup Node fixtures are reused from the unchanged independent bounded execFile pass; they were not rerun and their earlier route is not described as an owned-Job execution. Current eight physical stage inputs plus Node are checked against that receipt. No actual browser rendering was performed for this release. Six inherited mock HTTPError cleanup ResourceWarnings occurred in the first Python attempt; the production transport explicitly closes response/connection, and no real socket/file/process leak was demonstrated. The continuation emitted none.

| Retained proof | SHA256 |
| --- | --- |
| receiver-manual-standing-v2.json, actual 47 PASS | 0b2b2d7a37d6ebe2d5be1713e4cd025c8be1dc7ce991fe47ea245c56770696df |
| receiver-owned-standing-v2.json, closure and 94 after-pins | 4023243b64716b532db0106fb4f823656f34b7dca64ee96514d6292ce28aa8c8 |
| receiver-manual-standing-v1b.json, first 134 PASS / 2 FAIL | c081c8401765687c7160284afac060b7a7a3d55b8d778dfc30676e826e7c10ab |
| receiver-owned-standing-v1b.json, initial closure | 9c2558cfff7296e934ecaaf533010bee100d80cef1f4f85c1bf862d740ea5fc0 |
| QAReport-standing-v1b-nogo.md, preserved failed report | d28d3243c83a3d357d88bc3cffb8b1a3c02b62495bf0542af9c1121fe93a8ff2 |
| scratch/ready-list-ui/frontend-qa-standing-rules-v1.json, reused Node4 | cf2e5e03130a5b6a8749e57ffa16138452a2109a58b3cf8aefa70d4a7dbb7f46 |

Actual final receiver receipt line:

```text
BOOKS_MANUAL_QA|tool=Books Arranger|target=0.12.0|source=0.11.3|HEAD=9a5f6e66937caebc0314fc0ef2f5c0ace26f0848|dirty=true|source_digest=b851c1eb240bc70b638c53efd9f746f675e49ae8594da37a66c2741419b90727|manifest_sha256=5927156571175832e3b7604dc43eaacc1ec76816bc658251b1a8a9727e59eaed|python=pass|node=pass(reused4)|package=n/a(manual nonpackage contract)
```

## Practical limits and disposition

This clearance covers the pinned source and private fixture evidence. Expanded policy was not tested through actual public-provider/live-library admission, normal user runtime replacement, browser rendering or real-library conversion/deletion. Recognized fan tables and one complete source per constituent are supported; unsupported schemas and continuous recordings without proven component spans stay Held. Unknown M4B presentation bounds/layouts stay Held. Custom/neutral artwork does not claim catalog-pixel equality.

Refresh examines only observed members (500 members / 4GiB / 120s); it is not new-file discovery or a whole-catalog scheduler. Possible duplicates preserve originals; encoding differences alone do not prove distinct recordings. Published/unclassified/source-changed failures do not reset publication/retirement journals. Verified-output source retirement and the existing 24-hour recovery window remain required, with unknown staging content preserved.

No Y:/Open Library or local-dump import/index/archive mutation is included. The healthy old runtime was not replaced by review or QA. The staged backend-dependent frontend must be paired with the matching released backend through the normal authorized user restart; this certificate does not assert live readiness. No Comics, library, service, Start-menu, network, Git or product-code operation was performed by this reviewer. No reviewer disposable output was created; unique failed and passing proofs remain retained.
