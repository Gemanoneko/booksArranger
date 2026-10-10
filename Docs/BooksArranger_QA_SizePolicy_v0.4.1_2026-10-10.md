# Books Arranger v0.4.1 size policy QA

**Verdict: GO for quality-first frozen-3.** Its final acceptance and exact current pins appear below. Frozen-1/frozen-2 strict byte-budget plans remain superseded and held, with their historical test evidence preserved. Future encoding matches verified MP3 stream bitrate and retains channels/sample rate; it permits container/artwork growth without a lower-bitrate retry. This does not establish bit-identical audio or subjective listening quality. Existing outputs and device sync were not changed or tested.

Historical, superseded snapshot: `scratch/size-policy-2026-10-10/frozen-2`, **37/37 pins verified**, full manifest SHA256 **d55e38ea77f75c266f3da8cba429e5ce9d8105542b5c6e1ae9fb40dfa505b208**. Preserved complete pins in `scratch/size-policy-qa-2026-10-10/accepted-final2-manifest.json`; marker is baseline 0.4.0, with Sully owning the 0.4.1 bump. The following original table/checks describe frozen-2, not final accepted runtime pins.

## Historical strict-budget plan — HOLD

| File | SHA256 |
| --- | --- |
| encoding_policy.py | baa21d71f2ecfdc360933eb607a17f7085c33f5eb7bd9d39bfff282091141bd0 |
| audio_pipeline.py | 8bbb1ac826d64ac33a2923d92154c22116ba3ecc51c4616a3920a586ff79ed66 |
| audio_jobs.py | 4f8cd83dae745e578d76c2e3bea0b898b324b780331e943e48586c03287cb351 |
| merge_service.py | 683d017c5f801425eb2ed62949289131cc64633684d3d6e6cf2bf96b7627ab9c |
| review_backend.py | a511055f2482f8a3083f26acebd0d9ed51204e244df80873446cf10449d886fd |
| tests/test_encoding_policy.py | 6025170637ac8fe6f55aa77ce1cb2cd5a57169cddc7293c2d981ca117beffce3 |
| tests/test_merge_service.py | bf038e57e8fcd8176b76d1abf1bbd7ae3d9942a2c6e93259adbeb7a6e9b92a9f |

The committed size-policy UX document hash is 4182a1487e6295cc52d2cc1fccd60f49a0bc187456e9228c0af45f590817da7c. Other frontend/native pins are unchanged; their prior acceptance is retained, without repeating UI/native/full-suite testing.

## Checks and measured results

**Nine unchanged policy/recovery/actual-media tests passed on frozen-1 before the integration blocker was reported.** They cover mono/sample-rate retention, stereo without downmixing, unsupported/mixed layouts, insufficient budget/artwork reserve/quality floors, one lower retry only, publication oversize rejection before reaching its write boundary, durable retry state across pause/restart with no endless Resume, actual mono/stereo outputs fitting their source budgets with decoded duration and tags/source hashes preserved, and validation of an existing legacy 160 kbps completed record. Those exact policy/pipeline/job pins are identical in frozen-2, so these results remain binding. The frozen-1 pass was deliberately stopped: no whole-suite GO claimed.

**Nine affected/independent tests passed on frozen-2 in 16.668 s:** five complete media/service tests and four independent boundary cases. Full service review/approval → new manifest → actual M4B → restart reuse validates the new profile, source budget and retained mono layout; stale review jobs fail, unreviewed jobs cannot enqueue, source/selected/created metadata-cover inspection stays distinct, and opaque folder dispatch is mocked.

The independent HTTP route test executes the actual Handler with the real reviewed fixture service, without sockets: `/api/audiobook/create` → durable job → actual encoded/validated/published M4B. The durable manifest carries `aac-source-budget-quicktime-v2` and **529,356 source bytes**; output **103,191 bytes**, mono 44,100 Hz, source PCM **6.000 s**, decoded output **6.013968 s**. Source hashes remain unchanged. This tests the integration boundary rather than calling the encoder directly.

Independent real encoder boundary case intentionally pads the first private checked artifact beyond the budget, then runs the actual second encode from the same original snapshot input list. It chooses a lower target once: successful retry **95,000 bps**, **482,412 source bytes**, **365,904 output bytes**, mono 44,100 Hz, attempt 2. Narrator Unicode/comments, Artist and one attached picture are checked. Another case forces both private encodes over budget: exactly two encode invocations, no published destination. Restart with the saved attempt-2 target invokes only one encode and refuses another oversize; it cannot reset the retry allowance. An invalid persisted bitrate below the supported floor is rejected before encoding. Oversize fixtures are simulated by padding private files, not by altering original audio or production artifacts.

The nine retained checks plus nine final checks provide **18 targeted passing checks**, explicitly across the two pinned snapshots. No claim of a fresh full-suite pass. Exclusive no-replace native publication remains on its previously accepted unchanged pin; the new policy's independent publication size gate prevents an oversized artifact from entering that boundary.

## Findings and limitations

Frozen-1 **Major: policy bypass at the review-to-job boundary**, found by Senua: `review_backend` still generated legacy manifests despite the new pipeline. QA stopped promptly. **Fixed and independently regression verified** on frozen-2: corrected service manifest assertions and the actual HTTP create/durable job/output case establish the new policy is used for future exports. Only review_backend and the corresponding service tests differ between those snapshots. Legacy completed records remain valid; the real Eye of God pilot was neither rewritten nor re-encoded.

Compact evidence `scratch/size-policy-qa-2026-10-10/evidence.json`, SHA256 **90d3e51f08272bcee8832ab9713f6838ce82ac4c3b7e756169029e47cc04bcbf**. Initial stop receipt `frozen1-stopped.txt` preserves the partial-pass history. Owned initial session 48154 exited after interruption; its exact temporary fixture was removed after absolute-path containment verification. Final session 96961 exited code 0; all test temporary directories self-cleaned, the owned fixtures directory is empty, media children finished and job services closed. Pinned snapshots/harness/compact evidence remain preserved. No live catalogue/server controls, existing library/pilot writes, browser, Explorer, playback, install, git or device actions occurred. Published recording completeness and physical iTunes/Apple Books sync remain outside this test; separate Senua construction clearance is required.

## Final quality-first frozen-3 — GO

Accepted complete 37-file manifest **ae07dd09adcdb2eb7037a4442f999081a0e8dcf94a79087145026d51498f9eff**, snapshot `scratch/size-policy-2026-10-10/frozen-3`; **37/37 hashes verified**. Preserved current full pins in `scratch/size-policy-qa-2026-10-10/accepted-quality-manifest.json`.

| Current file | SHA256 |
| --- | --- |
| encoding_policy.py | 0acbcbfedd2cf9c6fd04248de33c889dbc9a7e37fa32dbc0150669aa7dbc5de2 |
| audio_pipeline.py | b78a5a6791df2b502e051e43374c0b19bdc9e18c9815ca1a138ef01b9bd3be09 |
| review_backend.py | 8b1de1611325678fbb6facbba8ce9912608705fecafe8dc57afe5d747c0a0063 |
| merge_service.py | 31e9b7164ff9ef6cb70276490865775f36e2cea311f0c24bba4b9a1d83c2b82f |
| audio_jobs.py — unchanged published engine | 4d4eb716fc732471687073b06ad301b73f6edb3bfd5f5c5f9d1f492b0ad27177 |
| tests/test_encoding_policy.py | 81f8bbadf9f25a8f8f99cae04511080b2ce09f5bd67ec0f7e09f36d5a2f62512 |
| tests/test_merge_service.py | af1b9bfde4f053371110308aa829bf94c775c76e80d7efbb3e897b7d4fc41248 |

**18/18 final targeted checks passed in 30.660 s:** 10 supplied quality policy/actual-media checks, 5 complete service checks and 3 independent cases. These are new quality-first checks, separate from the historical strict-budget results. No whole-suite/native/UI retest was needed on unchanged accepted pins.

| Actual media case | Source bytes | Output bytes | Target / layout |
| --- | ---: | ---: | --- |
| Uniform MP3 mono | 34,360 | 32,639 | 128,000 bps, mono, 44,100 Hz |
| Uniform high-bitrate MP3 stereo | 67,674 | 62,286 | 256,000 bps, stereo, 48,000 Hz |
| Tiny mono with added artwork | 5,102 | 7,860 | 128,000 bps, mono, 44,100 Hz |
| Mixed 128/256 kbps tracks, same stereo recording profile | 50,778 | 62,545 | highest verified 256,000 bps, stereo, 48,000 Hz |
| Actual HTTP review/create → durable job → publication | 11,790 | 10,959 | 128,000 bps, mono, 44,100 Hz |

Each direct media output validates source PCM duration and retained tags, with one attached picture and no checked-retry artifact. Uniform mono decoded 2.020136 s versus source 2.000 s; stereo decoded 2.005351 s versus source 2.000 s, within the supported AAC padding tolerance. Original source hashes remain unchanged. The tiny-artwork case grows by 2,758 bytes without a forced bitrate reduction; mixed source bitrates select the highest verified target rather than a blind 160 kbps cap. An independent wrapped real encoder case confirms exactly one `_encode_private` call, with input list referencing protected MP3 snapshots and no AAC/M4B intermediate.

Independent actual HTTP Handler dispatch uses the real reviewed fixture service and persists `aac-source-matched-quicktime-v3`; its policy has neither max_bytes nor max_retries. The job encodes/validates/publishes correctly, preserves original comments and reader credit, and keeps source hashes unchanged. Another independent test removes only stream bitrate evidence from actual source probes: although container bitrate still exists, conversion refuses before encoding instead of guessing or silently falling back. Mixed channel layouts/sample rates, unsupported PCM/multichannel profiles and targets beyond AAC frame capacity also require review. Existing completed legacy 160 kbps outputs remain valid. Stale reviewed jobs and unreviewed creation remain blocked, with inspection and mocked opaque folder dispatch unchanged.

Evidence `scratch/size-policy-qa-2026-10-10/quality-evidence.json`, SHA256 **2f891e6a357b48aedfb2aa5ad17d8294dfa3211fc4cb1f58fb525831bde0f360**. Driver `quality_check.py` and frozen pins remain preserved. Owned session **42542 exited code 0**; generated source/output/stage fixture trees self-cleaned, quality-fixtures directory empty, owned media children completed and service jobs/database handles closed. No live catalogue, server controls, existing library/pilot changes, browser, Explorer, playback or device checks occurred.

Disposition: forced byte-cap/lower-bitrate retry policy **superseded**, integration bypass **fixed and verified on the current profile**. QA confirms settings selection, structural audio validity and source preservation. AAC transcoding is lossy; equal nominal bitrate and a successful full decode do not prove bit-identical audio or subjective quality. No listening comparison was performed. Physical Apple Books/iTunes compatibility remains device-unchecked; separate Senua construction clearance remains independent.
