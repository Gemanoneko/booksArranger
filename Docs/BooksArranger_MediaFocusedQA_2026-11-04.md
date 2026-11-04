# Books Arranger 0.25.0 media-source focused QA — 2026-11-04

**Verdict for these two slices: GO.** This is a committed-source check, not packaged-build or release clearance.

I tested a private `git archive` of pushed `a4e43d05e8a456dc3999b309b4f767dc45fc31e3`. All four changed source/test files matched the frozen PNG and source-decode evidence by raw SHA256 before and after the run.

The complete `test_m4b_preservation` and `test_mp3_tag_repair` modules returned **119 passed, 1 skipped, 0 failed** in 7.54 seconds under the 600-second native owner. The skipped case requires an explicitly opted-in private MP3 fixture; the independent generated bad-source case ran. The owner returned exit 0, `closed=true`, `outputComplete=true`, no force or timeout, and native `complete=true`/`zero=true` with no active or unsignaled process.

The real AAC plus PNG/text-chapter case passed the production preservation pipeline with byte-exact audio packets, chapters, container and source. PNG signature, extent, CRC, header, critical chunk order, short read and image-byte limits refused malformed inputs; JPEG remained supported and unknown image entries remained refused. The native bad MP3 case identified original source 12 of 57 through its staging alias, retained the original path and diagnostic through JSON, left source/staging bytes intact, and did not create repair audio. Unrelated native failures and timeouts remained unclassified.

[Raw receipt, log, runner and exact source hashes](Evidence/converted-duplicate_2026-11-04/futaba-media-a4e/summary.json) are retained. No live Z: media was read. The primary job journal/UI consumers, folder latency, saved old-job readmission, packaged build and release gates remain separate work. No new pattern alert arose.

Owned scratch cleanup remains pending: the studio disk-hygiene planner refused the private Git archive because it contains the protected copied path `src/.claude`. It created no cleanup manifest, and no removal was attempted by another route. The exact refusal is retained with the QA evidence.
