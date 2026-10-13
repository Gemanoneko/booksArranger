# Books Arranger v0.15.0 urgent working-cleanup subset QA

Futaba, 2026-10-13. Exact acceptance pin: `6bd10c97e355021f4458defd8c390727f573414a`, branch `codex/books-split-books-0.15.0`. Delta from reviewed R3 implementation `d3c55261cf64e8b8040ecc4cb86d551f51bdddfa`: committed working-only helper and historical caller at 8874f53, then caller resume correction at 6bd10c9; intervening docs are context. This is a GO for the urgent receipt-only cleanup subset, not acceptance of the unfinished full cleanup/precision/space delta or permission to resume live processing. Dirty shared audio_pipeline.py was never executed.

**Verdict:** GO

## Scope and results

All execution used committed git-archive sources or fresh private copies of the sender immutable archive. No live database, data deletion, Z:/Y:, HTTP Start/Stop/POST, source retirement on the library, real app launch, desktop input, or Git mutation. Fixtures contain tiny invented files on private C: paths. The approved historical set is 8 jobs, 136 receipt-matched WAVs, 119317276892 bytes; those real files were not tested or deleted by QA.

- Shared manual receiver: 15 of 15 native working-cleanup tests PASS, 2.125 seconds; owned envelope 3.071 seconds. Matches actual sender 15 of 15 PASS, 3.980 seconds / 4.876 seconds envelope.
- Independent private run: the same 15 tests plus 11 independently authored probes PASS; total envelope 4.251 seconds. Each child starts suspended, is assigned a private kill-on-close Windows OwnedProcessJob before release, and uses the remaining bounded 600000 ms envelope. Complete source/runtime/harness hashes checked before and after.
- Independent probes: exact source bytes, source snapshots, unknown working files and recovery sentinel unchanged; dry-run makes zero database-row changes; frozen-plan byte-identical new-native-file replacement refused; replacement after committed intent refused; bad second WAV blocks every disposition; changed manifest refuses; original custom ADS preserved without retirement; output Zone.Identifier preserved; frozen caller resumes after partial disposition, rejects native-fact tampering and rejects a newly receipt-listed unplanned WAV before deletion.
- Committed cases additionally cover changed output, receipt byte mismatch, actual working-WAV hardlink and ADS refusal, unknown attempt, ownership mismatch, missing without intent, terminal path recreated with identical bytes, traversal name, and crash reconciliation. Working-only success creates no full storage-cleanup completion. Source safety in the full route remains mandatory.

Initial 8874f53: 13 producer cases passed; 7 of 8 independent probes passed. The remaining probe assumed published-output Zone.Identifier should refuse cleanup; the unchanged protected-output boundary validates default bytes/ancestry and preserves the output ADS. Ender/Senua confirmed this existing preserved-output behavior; revised probe verifies output and ADS unchanged without retirement/full completion. It is not a weakened working-WAV stream guard. First attempt also lacked the archive scratch directory; all tests failed during fixture setup before operations. QA created the required private directory and reran. Both earlier logs/receipts remain as evidence.

## Actual manual handoff

Applied qa-handoff's separately reviewed nonpackage/manual contract. No package checker receipt is fabricated. Sender and receiver independently executed identical argv through Git Bash, with tool timeout 600000:

```bash
exec 'C:/Python314/python.exe' -I -B 'C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/split-books-2026-10-13/worktree/scratch/cleanup-delta-2026-10-13/manual_owned.py'
```

The actual independently compared identity/result line (locations and elapsed differ) is:

```text
MANUAL BooksArranger target=0.15.0 source_VERSION=0.15.0 HEAD=6bd10c97e355021f4458defd8c390727f573414a snapshot_dirty=false source_digest=67570c0e427110030cd47aff814153c2cbdc33b7a5f9e012922037fb8edc7d49 test_working_cleanup.py=PASS15 package_checker=n/a(nonpackage)
```

Context and records under worktree scratch/cleanup-delta-2026-10-13:

| Input/evidence | SHA-256 |
|---|---|
| manual-context.json, 224 immutable source files | cbed742afe64ca917cc66446c87a6285f4fb2b7e316f20431fb4282e8fec2a86 |
| manual_owned.py | 3494696e5a33aa11426fcbd4b4fbfc3a62c90dcfcc465874cd0420c0698a3a31 |
| manual_inner.py | e3ed777d11d79479113e3cdcfad50bb05aded338457b58ae5efefb821f5d861a |
| Sender receipt, manual-run-3a3ba26f-f44f-475e-ae77-694fd95ba931 | de3c577f861c3dc95c6c8e59be870330a8e658304ae76b46bf05fcb6434a41eb |
| Receiver receipt, manual-run-2ed92399-31cf-4dee-96bf-1668d458babd | 47095cfecb73839a76bc09655d0f24edd95ece3f9226192f4fa7a3816287505a |
| Receiver log | 4ec0e7f49250130106c430011b4ba4dfa95896539a8539fdc68a4c403b90c38e |

Python runtime C:/Python314/python.exe SHA 434b361fe0c5960d404974feed493db47f2603a1ace2574312104fbed0182c6f. Native ownership module SHA 46affe8d8ba8304944c5a2f0e4ad7ca2db79566c40016ab694b366b3dbf5becd. Bash/FFmpeg/ffprobe are independently checked by the shared context; no FFmpeg process is needed for this subset.

## Independent evidence

Own scratch: WIP/Books Arranger/scratch/futaba-cleanup-2026-10-13. Invocation:

```bash
/c/Python314/python.exe -I -B 'WIP/Books Arranger/scratch/futaba-cleanup-2026-10-13/run_private_subset.py'
```

The finite harness runs `python -B -m unittest discover -s tests -p test_working_cleanup.py -v`, then `python -B independent_subset.py` against immutable pin-6bd10c9. Independent manifest digest 927b28ee215cb0dea053d2f70fe4147fa3f36bd9b7661133eae5d8403606eed6 uses its own normalized path/hash dictionary, so differs from the sender path/hash/size dictionary digest. Individual source bytes agree.

| Evidence | SHA-256 |
|---|---|
| run_private_subset.py | 17cd70fa1b4f9efe7d3586efc32fb305ab4797ac00cc67d78fae0c5f60f3a37c |
| independent_subset.py | ab2becd3456846aca978b8c47f22e59c9658206c5b466cd34169da45f4ff9742 |
| final-private-private-receipt.json | cbfc5e65133b3eab5134183af491ba83567b9312a5d5c9991b84dbaa14287d17 |
| final-private-0.log, 15 cases | 6329b59a4f7b0fe6dcc32b3db7650522e04ef91973cfdad8551dd96e6ddc6550 |
| final-private-1.log, 11 probes | b9d09ea7044f014f9255cfe429c9522e67611a6aa4e99edf22d584caf6949675 |
| storage_cleanup.py | 21a1e4ce087ed8f02627897918757602f47f5ee075f4e586f97a2bc5f3f8edbf |
| cleanup_published_working.py | 426eaa4c3593b36eadbb31395a6391c1902ba4ddd4dd25d7eb274cd7df834446 |
| tests/test_working_cleanup.py | a0a02ab9c1750c229474a505e7a9274f60e703262ea705efb6031f98521e56af |

## Limits and handoff

No new reparse fixture, actual eight-job historical CLI apply, actual library publication validation, full Ready UI flow, media precision/size policy, disk-short clean holds or full v0.15.0 regression is certified by this subset. Reparse/native boundary code and 24-hour recovery policy are unchanged; independent sentinels prove this working route leaves recovery bytes intact, not retention timer behavior. Caller helper resume is exercised with a tiny privately patched approval scope; real CLI must use the exact fixed approval scope, frozen plan hash, supported shutdown/catalog_lock, and original source/runtime pins. QA performed no shutdown.

Fixture teardown removed all generated private media/database directories. Small logs, receipts, harnesses and immutable archives remain evidence for the pending full release review; other agents' files were untouched.

Pattern alerts: none.
