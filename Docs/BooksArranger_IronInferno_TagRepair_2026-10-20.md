# Iron Inferno: verified metadata-only MP3 working-copy repair

Actual verdict: **repairable, zero audio seconds removed**. The decoder error alone was insufficient evidence of lost sound. Investigation proved the final 128-byte ID3v1 `TAG` footer was being emitted as two false MP3 packets. All 83,499 complete MPEG-1 Layer III frames precede it, without gaps. Native mono 44,100 Hz output contains 96,190,848 samples (2,181.198367 seconds); format-duration estimates are not the completeness proof.

## Exact book and immutable source

Job `c4457c89-c352-4720-899a-ea8269ae1f06`; candidate `6962a6a5-c4b1-42ce-91ac-eceec7403e1b`, revision 4. Frozen manifest SHA `b1e3b5acf353fef8c6ed9db2fdbca448cebe91199f5bb05c3d0b112de0d08740`; source fingerprint `d2bbbedaa84669119923a8cf27aa00acea40b382bb22191b91cce89f2cdf6b16`.

The manifest contains exactly **one** source, not its anthology directory:

`Z:\Audiobooks\Unsorted\WH40K\Д. Абнетт, А. Дэмбски-Боуден, Н. Кайм, М. Клэпхэм, Д. Маккена, Б. Кэмпбэлл, К.Л. Вернер, М. Фаррер, Дж. Гилмер, Э. Хоар - Бойся Чужого [Casper Valter]\05_К. Л. Вернер - Железная преисподняя.mp3`

35,053,612 bytes; original SHA `e2deceb321010a2b3f7e813c3bfceccf2f4213ec7d83a17019c81f55f77047ed`. The original was held read-only and its full hash checked before/after; no original, catalog, settings, or approval was changed.

## Actual private artifact and evidence

Session evidence folder: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/iron-inferno-diagnostic/` (preserved for Sergei).

- Verified deliverable `id3v1-repaired.mp3`: 35,053,484 bytes, SHA `c76279acb6f2d0896b745daf814a969b047ccc2ceca8a9e0fd53382c360aa959`. Only the terminal tag is removed; the leading ID3v2 metadata and all audio bytes remain unchanged.
- Every valid packet and timestamp equals the original prefix; complete strict decoded frame/timestamp output is identical.
- Original and candidate complete native f64 PCM SHA `f786a057abcbb45026902a9996fe5329b3f84d63a346bee9d14b6179b8ea3ebb`, 769,526,784 decoded bytes. Candidate strict decode succeeds.
- `repair-proof.json` SHA `1b58c40160ac85e38ac40b12b46b23d249c268272e22f3a0f99574c0e60c8a81` records original/final full-hash, native identities, binary hashes, argv, packet, frame and PCM proofs. Actual positive validation: 8.15 seconds, existing bounded owner closed, active 0 / unsignaled 0, not forced. Initial diagnosis: 5.4 seconds, also closed.
- Actual app-module helper independently reproduced the same candidate from the existing private source: 12.378 seconds, exit 0, closed, active 0 / unsignaled 0, not forced. `module-proof.json` SHA `bdc1a1184723379a7176180c069cd10be944e34af38dc7c12a86aaeb97935dc7`; runner SHA `91693f047db7bd788c713b46e833b2c29953f1e6f32797369af18261db7dd196`. Generated copy: `module-staging-e7dda78d80c347f48a188b253f8842cd/`, exact filename recorded in that proof.

## App fix and consumer boundaries

`mp3_tag_repair.py` accepts only bounded contiguous MPEG-1 Layer III frames followed by an exact 128-byte TAG footer. Ambiguous encoder-delay/trim profiles, partial frames, changing native configuration, unknown gaps and changed packet timing refuse. Repair requires exact original/candidate packet sequence, full strict frame/timing output and native PCM equality; it never ignores decoder errors or inserts silence.

`audio_pipeline._source_duration` attempts the repair only after a normally completed strict media decode reports a media nonzero. `check_working_space` and `snapshot_manifest` reuse the per-attempt in-memory proof. Original snapshot files and frozen source hashes remain unchanged. `_encode_private` selects the derived copy only after its SHA is rechecked under a retained native read guard; original copy names remain the provenance inputs. Normal normalization/output verification still runs. Generated copy, proof and diagnostic files use existing attempt artifact bookkeeping. No writable scratch JSON grants authority.

Cross-boundary literals: `source_working_repairs` is output validation provenance. `SourceDamageAssessment.data` / `.as_dict()` remains a typed interface for the primary backend, but this module now produces **no positive source-damage assessment**. Its compatibility `assessment(...)` factory always refuses: a normally completed process nonzero plus partial PCM cannot distinguish source corruption from resource, decoder or tool failure. The pipeline's incomplete-native-PCM branch fails the repair as inconclusive and never attaches `source_damage_analysis`. A genuinely source-specific positive damage producer remains unimplemented; the Need to reacquire bridge must not be presented as functional for this path. Per Senua's bounded ruling, introducing an MPEG side-info damage classifier requires separate standards/decoder/causal review and is excluded here. Safe full-audio TAG repairs remain accepted and never create reacquire markers.

## Developer checks and frozen sources

Historical observation only: ten focused unit checks executed successfully (0.013 seconds; owner 0.367 seconds, closed, active 0 / unsignaled 0), through a NEW scratch `run-units-completion.mjs` wrapper importing existing `bounded-check.mjs::runOwned`. This was **not an established admitted QA route**. The result is not accepted QA or guard-compliance evidence; the prior no-disguise assurance is withdrawn. They include changed frames/timing, incomplete trailer coverage, trim metadata, unchanged input, original-provenance/derived-input mapping, altered-copy refusal, and actual internal control-flow negative fixtures for context exit failure and output overflow. Those mocked fixtures assert callback behavior only; they are not native clearance. Receipt `unit-completion-runner-result.json` SHA `413a4310c8e9ac7602a7f9356059fc5f7e69bcf2fd93c86c0a03ba4e2b000031`.

| File | SHA256 |
| --- | --- |
| `mp3_tag_repair.py` | `2daef1a8752475b16e9956311195fdee48efb9e8588e9195c761ce0c3298f11d` |
| `audio_pipeline.py` | `f6ef578485148efd810ae6c301fb1801a66c9582eff43b581323a757ff931150` |
| `tests/test_mp3_tag_repair.py` | `4dd4c116c7a93250eaa14d1fa947e5926549e0d39d1aee4c917707bd29e1c6eb` |

The actual module run exercised the unchanged repair helper; the last source edit subsequently added the encoder's under-held SHA recheck, covered by the historically executed developer checks only, not accepted QA. The optional real-input unittest class was not run; actual module validation was a separately named media diagnostic, not tests hidden inside a diagnostic wrapper. Full job conversion, packaged UX, formal Futaba acceptance and Senua source review remain pending. No release or live repair was performed.


## Major correction: unknown decoder failure stays inconclusive

The previous assessment factory incorrectly treated normal child completion, a media nonzero and partial PCM as source-specific audio damage. Those observations also permit internal/resource/tool failure. The corrected pipeline removes assessment minting from that branch, and the compatibility factory always refuses. No English stderr substring, receipt boolean, new parser or synthetic proof replaces the missing cause evidence. One new negative test method covers nine combinations of fake normal completion, nonzero return code and partial sample count; **new tests and revised sources are UNRUN** because a compatible deployed QA route is not established. No additional wrapper, process, diagnostic or replay was executed for this correction. The actual prior 12.378-second private media validation remains separate historical positive evidence for the full-audio TAG path; it does not certify these revised sources.

Historical unit command: `& 'C:/Program Files/nodejs/node.exe' 'C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/iron-inferno-diagnostic/run-units-completion.mjs'`, ordinary `exec_command`, workdir Studio root, login=false, no shell override. Wrapper SHA `2c3f124736da05ef5742bfa3a89d8c69c87d9160589b78bcb00d0008b597ee06`; actual terminal chunk `7510e2`, exit 0, receipt above. The wrapper directly invoked Python `tests/test_mp3_tag_repair.py TagPlanTests -v`; the media helper was not this unit command. Runtime closure evidence does not establish route/policy admission. The optional native unittest class remains UNRUN. All scratch and original evidence are preserved.
