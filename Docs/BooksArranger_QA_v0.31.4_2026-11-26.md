# Books Arranger 0.31.4 QA report

Release source commit: c8a342ca3b96043f940dc00b9b618bd1a7dd3afb
Release artifact manifest SHA256: 870003866bf5660dcd2092cbd15f38d245ba1d943b8d904dbb60d8d55f86e6e1
**Verdict:** GO

Futaba tested Windows build d97dcc2d-31be-435d-b00b-ccc6a20cbcec on 2026-11-26. Eight late-write probes, the scanner regression, large-ledger startup admission, and the packaged window smoke passed.

## Package identity

- Installer SHA256 217f8b20406b0c40322825c1a335cc85a1afcc23f5b62df38b789620e16f1efd matched Ender’s handoff and the manifest’s installer entry.
- The manifest matched Ender’s handoff, named the release source commit and build above, and recorded payload verification, installer equivalence, and shell and backend version 0.31.4. Product digest 2dd522a0dd486afb66dd6e001086a9d0a7628e84085d772f575482f635772496.
- The unpacked executable, app.asar, and the sampled backend and renderer files matched their payload hashes. Thirteen product files, including runtime_file_disposition.py, runtime_disposition_owners.py, catalog_contention.py, scanner.py and the source configuration and cleanup modules, matched the pinned Git sources after CRLF normalization. All 147 shipped Python bytecode headers matched their source hashes.
- Ender ran the canonical entry check once. Futaba compared the receipt read from the entry log with the handoff.

Ender’s exact receipt, compared byte for byte with the handoff

> Entry-check receipt v2: books-arranger v0.31.4 @ c8a342ca3b96043f940dc00b9b618bd1a7dd3afb (dirty: N) [source:2f25a03596a477e7e711d341b66dac3be7a38287ae42ea1aaa1264ae5ec88d60; harness:7cc64d45d8055d60edde1965bf32594033711d5da7b9bd2b26d4c54d464c1a21; runtime:d325d745077c78ebfea935676f97e7e15ab59f3a3296475e3dc23f7297a9f71b; checker:39b828fff18ddc748a1a798fe5bcf359a256b72a53a37774cadcb3bbc2fbf73b] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a; personal-folders clean

The entry ran 3,325 Python and 285 Node checks with zero failures. Exit code 0, natural closure, 796.882 seconds. No timeout, truncation or forced stop. The personal-folder audit was clean across six folders and ten drive roots. Ender’s C: guard found no new files in ten inspected locations and 180 owned entries. C:/Windows/Temp was inaccessible (EPERM).

Entry log I:/AI Projects/Worktrees/Books Arranger/q0314/g/logs/ender-entry.log, SHA256 c920727f70dc1fad9ba1e5a60542a64c97debc400ef9cbcc933c8ee8e1d525ad.
Context I:/AI Projects/Worktrees/Books Arranger/q0314/g/context/context.json, SHA256 90b5954a48784a70f59ad2c8a88aef066ad5ed9cdb0edba0be4cf9e9bee80e3e.

The independent behavior probes ran on source 84c8c1be3f2eb554745d99008d1f936caa98d108, build 7ebc2e40-4936-4826-b1f0-e85f857f50db. The final Git diff changes only tests/test_rule_filing_names_031.py, forwarding the existing on_created callback through the test spy. I physically hashed every file in both 427-file unpacked payloads and checked both full manifest maps against disk. The 48-file runtime manifest, ASAR, Electron executable and all packaged source files match. Of the 427 payload files, 280 were byte-identical. The other 147 were Python bytecode with matching source hashes and recursively identical marshalled code after replacing only the compiler's build staging filename. These filenames carry a different build-cache UUID, which also changes the payload manifest hash. The rebuilt installer, its blockmap and latest.yml were independently checked against the final manifest. The packaged behavior results therefore apply to the final executable. I reran the native-window smoke on the final package.

## Packaged behavior

The probes used the candidate’s packaged Python, FFmpeg and backend modules. Three fixture helper files came from the pinned Git commit. Each fixture used locally generated audio, a private catalog, and controlled Windows error simulation where required. The clock advanced for minute-scale retries.

| Check | Observed |
|---|---|
| Repeated file errors on a reachable library | WinErrors 67 and 59 produced two 60-second deferrals. The third error (121) held the book with “Couldn’t reach the book’s folder. Both files were kept.” Both file hashes stayed identical. Cleanup recorded one kept, zero removed and zero bytes freed. One keep line contained WinError 121. |
| Transient error | WinError 53 deferred the job. The next eligible pass completed it, removed the old 18,622-byte copy and preserved the replacement hash. |
| Root answers while the library tree is away | Three passes left the ledger and retry mark unchanged, with zero kept, removed or bytes freed. When the tree returned, the previously verified old copy was removed. |
| Availability witness beyond the first page | Twelve missing verified paths preceded a responding peer. The next witness page established that the tree answered. The missing book’s folder received the ordinary folder-change hold and both copies in the moved folder were preserved. |
| Moved temporary folder with a recreated original pathname | Both moved files and an unrelated file at the old pathname kept their hashes. The ownership row and last known temporary path stayed on file. One keep line explained the missing or changed parent. The fresh names retry stayed unused. |
| Foreign file appears before exclusive creation | The unrelated file and original audiobook kept their hashes. The candidate took no ownership of the unrelated file and held the attempt once, with the retained-path diagnostic. |
| Fresh names try and filing API | The test moved the book folder after the valid temporary copy was removed. The published audio hash stayed identical. A second pass left the held record unchanged. The old-file removal count remained zero. Authenticated POST /api/filing/could-not returned one matching entry with the exact reason shown below. The backend log recorded the failure once with the proposed title, job ID and exact reason. |
| Shared log rotation and encoding | Repeated source-cleanup refusal emitted one line. The source and late-write diagnostics both escaped lone surrogates. With a reduced private-test rotation threshold, the three lines appeared across books-backend.log and books-backend-1.log. |

Exact filing copy

> Couldn’t update the names. The audiobook is unchanged. The book’s folder changed since the app checked it.

## Startup recovery and scanner

Packaged Python exercised the normal existing-catalog startup path through the native owner admission check. The QA fixture used a newly initialized catalog and its own native lock. One real disposition of an owned synthetic file provided the four receipt forms for 25,000 synthetic groups. The packaged startup callback stopped the positive run before the server started. The native Electron smoke below used a separate empty catalog.

| Journal fixture | Packaged admission result | Observed elapsed |
|---|---|---:|
| 100,001 members with valid closed receipts | Admitted, zero held | 94.514 s |
| 100,007 members with three invalid groups | Startup refused and retained all three. The reasons were malformed fenced JSON, pending native success requiring settlement, and a changed closed proof. | 89.643 s |
| 100,008 members, including a late orphan | Startup refused during membership preflight with one orphan reason before reading an intent. | 15.514 s |

All three runs preserved the context receipt and left the private temporary directory empty. Elapsed times were observed while the separate entry run was active.

The scanner skipped the exact unclaimed path recorded by an active names write. It cataloged an unrelated file with the same basename in another folder and preserved its bytes. After the write record changed to held, the original path was eligible for discovery.

The measured startup cases and scanner outcomes are in scratch/0314-release/qa/l-1e352/ledger-results.jsonl, SHA256 fd16065477d4536c8dc67674c4e260435fc22a76531991f34a95fa346c7e3aaf. Two initial startup probes stopped at a harness assertion about the normalized root map. I corrected the harness and reused the original private catalog, native owner, and unchanged journal context for the completed measurements.

## Native window and exit

The exact packaged app opened with --show-inactive and an empty, newly initialized private profile and catalog. The renderer badge read v0.31.4, the shell reported 0.31.4 and the owned loopback engine returned 0.31.4 from health. The visual demonstration supplied the independently verified filing API result to the packaged renderer. The revised message was legible in the native window at **1920 × 1290** physical pixels. The renderer remained unfocused, the candidate never became the foreground window, and the foreground handle matched before and after each capture and close operation. Jane inspected both captures and confirmed the visual gate.

The native Close system command sent to the candidate window hid it and left the shell and engine serving. The private-profile --quit command then exercised the tray’s Quit handler. The shell exited with code 0 in 1.157 seconds. The exact-path check found zero candidate processes and the engine stopped listening.

The first final-package smoke also closed normally. An unrelated foreground-window switch during Quit tripped the harness’s unchanged-foreground assertion. The completed repeat above had no foreground change.

Evidence held for the release handoff

- Runtime equivalence in scratch/0314-release/qa/identity-repack.json, SHA256 b398f942ac6dd85556e5f034b19b455baa193c3d845e84e67365e5f7014dea68

- scratch/0314-release/qa/v-c89aa/fresh-names-failure.png, SHA256 b4081910b76c5eb06fa1dd770d8d88ead0d7a9821564e252f75203af56c589f2
- scratch/0314-release/qa/v-c89aa/version-0.31.4.png, SHA256 b9d80361f47d0d9c0ef254551d395dca230ddb003165b994f8a0b777b114b2a9
- scratch/0314-release/qa/v-c89aa/focus-and-geometry.jsonl, SHA256 704ccddb12ed9f7ac295e39d2bc91aff1fc28ca699b581c722a0c01238c1a1c0
- Eight packaged backend probes and the authenticated filing response in scratch/0314-release/qa/e-69f33/results.jsonl.

All QA listeners and candidate processes exited. Fixture catalogs, profiles, caches, captures and logs stayed within the private task folder on I:. No known QA disposable files remain on C:. The NAS behavior was simulated. The installed app and real catalog were outside the scope of this run. Jane owns the project sweep.
