# Books Arranger — Eye of God real pilot QA

**Verdict: GO for this created artifact.** Device sync and external recording completeness remain unchecked.

Completed job `9e04e700-ecf8-4807-8195-01a7a1d73bd6`, v0.4.0. Artifact:

`Z:\Audiobooks\Rollins James\Sigma Force - 9 - The Eye of God - Rollins James.m4b`

- Size: **1,300,066,162 bytes**.
- Independently streamed output SHA256: **59f1527a05f1115f36e80473d0b94127612cd3ca6ad1b1e293f2aa0d68d61ff7**. Output handle identity, size and exact timestamp stayed stable during hashing.
- Independent ffprobe: one AAC audio stream, 44,100 Hz, stereo; container duration **64,133.171995 seconds**, approximately 17 h 48 min 53 s.
- Title **The Eye of God**; Artist/Album Artist **James Rollins**; album **Sigma Force - 9 - The Eye of God**, grouping **Sigma Force**, position **9**.
- Unicode comments retain **Леонов  Андрей**, add **Narrator: Андрей Леонов**, and preserve source album/date information alongside series fields. Exact Unicode assertions passed; shell console character rendering is not used to judge tag encoding.
- Exactly one attached picture. Extracted its existing encoded bytes through a read-only ffmpeg pipe and independently matched selected-cover SHA256 **6994191f25cab4a7c2f9d223783ed4bf5b285edd4bfa77aaccb5e276c3fc3a9b**. No playback or full audio decode was performed by QA.
- No chapter markers, matching the approved manifest; no invented chapters.

Read-only durable catalogue query confirms the completed job/output record matches the saved producer proof. All **40** selected sources match the initial ordered source list and approved manifest. Producer completion evidence rehashed all 40 originals unchanged; QA independently compared every recorded hash and checked current opened-handle size/exact timestamp for all 40. No redundant full source rehash. Output is separate from every original source path; publication used the previously verified exclusive/no-replace path. The owned partial no longer exists. This check does not claim a retrospective byte comparison of unrelated library files.

Worker full decode validation passed: output **64,133.18965986394 s**, selected-source PCM **64,133.172244897956 s**, difference approximately **0.0174 s**. Independent container duration agrees within 0.001 s. Original MP3 header-duration estimates were inaccurate, so they do not establish missing audio. Published recording completeness remains **unknown**; matching the selected 40 sources is not proof that they contain every part of a published edition.

Producer proof `scratch/metadata-2026-10-09/pilot-review-2026-10-10/completed-proof.json` SHA256 **856dc2f28b70aac9384dda68cec422ce457a9d346c9aa2727aab2758fabd30e4**. Independent evidence: `scratch/metadata-qa-2026-10-10/runtime/pilot-artifact-evidence.json`; test driver `pilot_artifact_check.py`. Owned session 60987 exited code 0; subprocesses completed and read handles/database closed. No browser lease, service control, scan, new job, source/output/catalogue write, Explorer window, audio playback or device test occurred. Actual iTunes search/sync and Apple Books playback on the user's iPhone still require device verification.
