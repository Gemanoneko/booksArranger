# Books Arranger: output size policy copy

Date: 2026-10-10. Judy; intended tier sonnet, supported model inherited. EXTEND the existing audiobook creation and job status flow. This bounded addendum specifies copy for the confirmed requirement that newly created audiobooks must not exceed the combined size of their included source audio files. Preserve the existing layout, controls, theme, metadata review, source protections and other error messages. No encoder settings interface is added.

## Contract and scope

Ender owns codec selection, quality floors, size calculations and enforcement. The accepted technical direction freezes each new job's selected original file byte total, exact decoded duration and channel/sample-rate profile; preserves mono rather than expanding it to stereo; reserves space for artwork and container overhead; and checks the complete temporary output against the frozen byte total before publication. At most one fresh encode retry may use a lower target, starting from the original sources rather than the first encoded result. Every attempt remains subject to the agreed quality floor and all existing output checks.

Ender's confirmed engineering thresholds are 64 kb/s for mono, 96 kb/s for stereo, and a 160 kb/s cap; these are conservative app limits rather than universal guarantees of perceived quality. The allowance calculation reserves artwork bytes, 64 KiB metadata, 12 bytes per AAC frame and a 5% margin. Uniform supported sample rates are preserved (16, 22.05, 24, 32, 44.1 and 48 kHz). Mixed sample rates and more than two channels require review rather than automatic resampling/downmixing; reviewed mixed mono/stereo sources use stereo. These numbers are implementation context and are not new primary UI text.

The size limit concerns the sum of **included source audio file bytes**, including their embedded metadata. Excluded tracks and companion artwork/files do not increase that allowance. A displayed rounded value is explanatory; the backend gate uses exact bytes. AAC conversion is re-encoding and must never be described as lossless, as improving quality, or as preserving identical sound merely because its bitrate is higher. The existing completed pilot is not automatically rewritten by this change.

## Copy in existing states

Reuse **Creating audio**, **Checking output**, **Audiobook created** and **Output needs attention**. Do not add a new filter, badge, settings panel, approval checkbox or action. A permitted retry remains part of the current job; do not briefly report failure or success between attempts. If a stage detail is already shown, the retry detail may say **Adjusting audio size**. Do not announce a new audiobook until both the size check and all other checks pass.

Use these messages in the existing job failure detail, choosing the actual condition:

| Actual condition | Failure message |
| --- | --- |
| The source byte allowance cannot cover the container/artwork overhead and the minimum supported audio profile | **This audiobook cannot fit within the source files' size at the supported audio quality. An encoding decision is needed before retrying.** |
| The first encoded result exceeds the allowance and lowering the target would breach the quality floor | **Keeping this audiobook within the source files' size would require more compression than the app supports. An encoding decision is needed before retrying.** |
| The one permitted retry still exceeds the allowance | **The encoded audiobook is larger than its source files, so it was not saved to the output folder. This book needs an encoding review before retrying.** |

Do not substitute a size-specific message for a read failure, changed source, missing source, unsafe path, collision, decoder error or unrelated validation failure. Existing concrete error copy continues to identify those conditions.

The retained source notice **Your source files stay in place** remains accurate. **No audiobook was published** may appear as an existing status detail only after the backend establishes that no final file was published. Temporary files and persisted retry/recovery evidence must not be described as a completed output. Never promise that a colliding pre-existing output has been removed.

For size-only failures, repeated Resume must not create an endless automatic retry loop, lower quality beyond the floor or silently enlarge the file. Other safely reviewed books may continue under the existing queue contract. A size-only failure does not invalidate verified title, author, cover or track order; it is an output issue rather than a source read error. An unresolved encoding decision is reported to Jane/Sergei; this spec does not invent a settings action in the app.

## User explanation and verification

When explaining the pilot's growth, state the measured cause plainly: the existing conversion used 160 kb/s AAC and stereo output, while the inputs were approximately 128 kb/s mono. Re-encoding at a higher bitrate made the file larger without recovering detail already absent from the MP3s. Future outputs preserve mono and choose a size-aware bitrate; final size is checked before saving. Exact encoding numbers belong in the explanation or technical details, not a new persistent product settings matrix.

QA verifies three size-specific failure paths above, absence of a published file, source byte/hash preservation, existing error filter placement, no fictitious settings action, and no repeated retry loop. A passing file must be no larger than the exact combined included source byte count and retain full audio duration, canonical metadata and the selected cover. Mono remains mono. Existing completed jobs remain unchanged. There are no new hit areas or layout elements, so this addendum creates no additional rectangle or tooltip work.

Design basis: NN/g visibility of status and specific recovery language; user control without hidden quality reduction; error prevention through an enforced publication gate; Hick's Law through reuse of existing status surfaces. Numerical quality floors and implementation mechanisms are Ender's technical responsibility. No code, Git, live service, library or browser changes are included. No disposable files or probes were created. Sully commits and pushes this document before the implementation brief cites it.
