# M4B source preservation — 2026-10-15

Source preparation only. No product application, user-media transformation, retry, or publication has been performed.

## Preserved source observations

Root executed the independently reviewed header-only observer once at 2026-10-15 13:22:02.502599 UTC (16:22:02 Jerusalem), native exit 0. Helper SHA-256: 6100e464dfea0f99dc3cc2dce70f92a0d6bf126600642ea6268a18dc396bb32a. Python pin was freshly checked. Installed owner generation remained unchanged. The full JSON is retained in the root operation transcript; this document records compact observed facts, not an independent media/decode certificate.

The three original source movie-header hashes matched the earlier preserved metadata receipt (mp4-metadata-20261015.json, SHA-256 15aa3f0666228f9d8d31be3e906910a6cc414db3cb2ad5680b3d67b2d3ca0800). Header bytes read were respectively 7,112,333; 4,362,172; and 2,515,583. No mdat payload was read; no app controls were sent.

- Job 07d89b9c-ff57-445d-88f9-3a44c844470a: audio track 1 mp4a, media clock 44,100, 1,657,352 samples × 1,024; no edit list. Its chap reference targets text track 2, clock 1,000.
- Job 139b3941-bfa4-4199-ab4e-8380a97dbd70: audio track 1 mp4a, clock 44,100, 1,045,240 × 1,024, edit-list media_time 2,112. Audio chap references target tracks 3 and 2. Track 2 has vide handler and mjpg sample entry, ONE sample with duration 1,070,323,631 in clock 44,100 and edit-list media_time 0. Track 3 is text, also clock 44,100, eight chapters. Movie clock 600. The video is explicitly part of the source chapter reference graph; dropping it or relabeling it as an ordinary attached cover is unsafe.
- Job f96f5926-74d0-4f77-8a20-7a427a4fa404: audio mp4a, media clock 22,050, 535,065 × 1,024. Decoder description SHA-256 16c2e05d5c15e51ab99fd063345059e1b138d347ea998095a29c5343be8b9187. chap targets text track 2, clock 600, 43 chapters. A stored clock of 22,050 alone does not establish an invalid HE-AAC decoder clock.

## Bounded implementation contract

The single-source metadata path must preserve all original tracks, chapter references, movie/media/edit clocks, decoder descriptions, sample tables, compressed payload and unapproved metadata byte for byte. Approved metadata/known-role artwork updates must be explicit. Existing generic remux validation remains strict; the preservation branch needs independent source-relative validation rather than tolerance widening or relabeling source tracks.

The proposed streaming construction leaves original data and offsets in place, retypes the old moov to a same-extent free box, and appends the approved new moov. It loses fast-start layout, a performance tradeoff to document. Reject unsupported offset/reference structures, fragmented/compressed movies, ambiguous/multiple moov, size-zero-to-EOF boxes, external data references and unknown layouts. Every referenced chunk span must lie in a retained mdat extent. Private owned output, space budget, crash intent and atomic no-replace publication remain required.

The existing 12-method pure prototype is insufficient for real-file support; its separately executed baseline is recorded below. It rejects actual chapter/video layouts and uses opaque synthetic packet/decoder bytes. A separately reviewed meaningful native codec fixture and independent structural/payload/decode comparisons are required. These observations do not certify all 80 held jobs or authorize any live transformation.

## Actual original prototype baseline

At 2026-10-15 13:32:32.379444 UTC, mp4-prototype-qa-01 completed with outer exit 0 and all owned descendants closed. Twelve distinct methods were discovered and run; zero failures, errors or skips; zero children or network/media operations. Native root 96820 exited 0, active descendants 0, owned-finally true; graph elapsed 26,504 ms and tests approximately 0.0055 seconds. Receipt SHA-256 1d6dffd9d906586f8d50b93cec4e101ad06ca2993f0196596c80cd52499c7c98. Entry 17bea0332523b1dadb5c4c0bed7182bb2de0190a30fcf057b64b2d9243145779; manifest 63e842f3207699ad8ebf9234d9d4fd7156a645927323101aa1c519edc74f15de. Lease CLOSED.

These tests exercised the ORIGINAL opaque in-memory prototype only. The new production preservation core is a separate unexecuted draft; this baseline proves neither its correctness nor real AAC decoding, source chapter/video layout support, or Apple Books behavior. No repeat of the same twelve is required absent changed input or a new finding.

### Additional fields from the same retained observer output

No observer rerun was used. All three audio sample entries are version-zero mp4a with a self-contained data reference and esds: payload lengths 79, 79 and 82 bytes for 07d, 139 and f96. Their complete stsd SHA-256 values are d92b36d3a9d82178f43a66e8f0fdb658cc343d6cfd729b676ed57641eb960a87; 3dd7e4209d7f5608239817db391789d4210d43713b86f360fd216492b77d99f0; and 16c2e05d5c15e51ab99fd063345059e1b138d347ea998095a29c5343be8b9187. The f96 sample-entry clock field is 22,050; its opaque descriptor remains byte exact. All chapter text entries are text with 51-byte payloads. The 139 mjpg entry has 88-byte payload, including a ten-byte fiel box with payload 01 00; SHA-256 2e25bd98b5afb58793b6437b5e03d7654ce960cf875b828286f58086cccbefa6. Its dref is the self-contained url flag-1 record, SHA-256 4202aff9896704e3f61b936a535726e169d4dad3dbd1e4489be9f95d6ae31848. These facts bound a structural profile; opaque esds bytes alone do not independently certify decoder semantics.

## Restart checkpoint — unexecuted implementation draft

The dedicated branch starts at lifecycle checkpoint 15a7ab599595c1d86775fcd7917f3532b40eecbf. New m4b_preservation.py is a pure bounded metadata-plan/stream-copy core; tests/test_m4b_preservation.py declares twenty structural methods, all UNEXECUTED. No pipeline integration, live source transform, retry, publication or deployment has occurred. The original twelve-test baseline above does not validate this new core. The core and twenty-method fixture builders require independent review and exact private execution before any correctness claim.

Draft profile: version-zero mp4a/esds, observed 51-byte legacy chapter text, chapter-linked mjpg/jpeg with only the exact optional fiel payload 01 00, internal url data reference, supported sample tables, retained-mdat chunk containment and non-overlap. Every original trak byte is retained. Unsupported auxiliary/relative offsets, fragments, external references, unknown structural/entry extensions or ambiguous metadata are refused. This is a conservative draft profile, not proof that all three observed sources or all eighty held jobs are supported. Native fixture work has not run.

The next integration must assess existing copied_audio_evidence/_copy_presentation eligibility explicitly: that old remux guard rejects some leading-gap/edit/movie-clock relationships. A new exact source-preservation proof must not silently weaken that guard or invent audio tolerances. Full-track/payload identity and meaningful native decoding evidence are required before replacing any validation behavior.

Space assessment: the existing automatic single-M4B copy mode already avoids normalized WAVs. The proposed metadata path can produce ONE candidate directly, avoiding checked-remux plus compatible-rewrite pairs, while retaining streaming decode/hash/config/presentation validation. Current immutable source snapshot and destination publication temporary remain. Honest peak across volumes is approximately original + snapshot + candidate + publication temporary, about four compressed copies plus bounded metadata/artwork; stage alone is ordinarily snapshot + candidate. Retained recovery obligations can add more. Two-times compressed-size peak is not promised. Multi-source normalization/encoding remains outside scope.

Codec binaries were resolved read-only through the ordinary native route, then hashed without executing them. Fixed directory: C:/Users/AnGeLZzZ/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.1-full_build/bin (members ffmpeg.exe, ffplay.exe, ffprobe.exe). ffmpeg.exe: 227,398,656 bytes, SHA-256 09948d4cdd0650da6ff5a87577469f2a218dc2615ae379f8f734d24c49de0f73. ffprobe.exe: 227,193,344 bytes, SHA-256 a6618e99bb58869ded3c6f37b53aa1a8d701c3591dbb7b5b317d47369c112be2. A future independently reviewed private graph must pin inputs/runtime/argv/environment/output and own every codec descendant; these recorded hashes alone authorize no execution.

No native operation owned by this Ender is active at checkpoint. Installed Books Arranger remains running under the prior user authorization; no Quit, Stop or Pause was sent. Earlier failure receipts/leases and all unique source/recovery evidence remain retained. No Windows installer has been produced.
