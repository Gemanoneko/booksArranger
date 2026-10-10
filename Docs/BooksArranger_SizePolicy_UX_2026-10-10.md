# Books Arranger: quality and output size policy copy

Date: 2026-10-10. Judy; intended tier sonnet, supported model inherited. EXTEND the existing audiobook creation and job status flow. The current user instruction is: **“Make sure size is not inflated uselessly, but don't make quality worse.”** This replaces the earlier strict source-byte ceiling and automatic lower-bitrate retry plan. Preserve the existing layout, controls, theme, metadata review, source protections and unrelated errors. No encoder settings interface is added.

## Contract and scope

Ender owns codec selection, source-based bitrate selection and technical validation. New jobs preserve supported uniform mono or stereo channel layouts and supported uniform sample rates. They choose an encoding target from the original audio characteristics rather than applying a fixed 160 kb/s stereo profile to every recording. Output size is a consequence of that source-matched profile and necessary cover/container metadata; size alone must not trigger a lower-bitrate encode or reject a technically valid file. Do not silently reduce channels, sample rate or the chosen encoding target to force a byte limit.

For this bounded MP3 joining path, Ender verifies each protected source snapshot's audio-stream bitrate and uses the highest verified included track bitrate as the AAC target. There is no 160 kb/s cap, exact output-size ceiling or automatic size-driven retry. Mixed source bitrates can therefore produce a larger output because the higher-quality track determines the whole-book target; do not promise that every result is smaller. The pilot's sources establish a 128 kb/s mono target. Unknown or invalid audio-stream bitrate blocks an encoding decision instead of selecting a guessed value. Raw PCM bitrate is not a compressed-audio quality target; this patch does not extend the MP3-specific policy into a new format conversion path.

Mixed sample rates, mixed mono/stereo layouts and more than two channels require encoding review rather than automatic resampling, channel normalization or downmixing. Unknown or unsupported source characteristics must remain a concrete review issue when a reliable encoding profile cannot be chosen. This addendum does not authorize a new normalization path.

AAC conversion is re-encoding. Never describe it as lossless, as recovering detail lost in MP3 compression, or as proving identical perceived sound. Preserving source characteristics and using a source-matched bitrate avoids needless profile inflation; it is not a mathematical guarantee of identical audio quality. Full audio duration, canonical metadata, selected cover and all existing source/output safety checks still apply. The completed pilot remains unchanged; this change does not force a smaller replacement.

## Copy in existing states

Reuse **Creating audio**, **Checking output**, **Audiobook created** and **Output needs attention**. No new filter, badge, settings panel, checkbox or action is needed. Remove any size-only failure, fixed source-byte-limit claim or **Adjusting audio size** detail from this policy. Do not announce a completed audiobook until the existing output checks pass.

Use the following concrete messages only for the actual corresponding conditions, in the existing job failure detail:

| Actual condition | Failure message |
| --- | --- |
| Included sources mix mono and stereo layouts, which the current joining path cannot safely combine | **These audio files mix mono and stereo recordings. This book needs an encoding review before it can be joined.** |
| Included sources mix sample rates, which this path cannot safely combine | **These audio files use different sample rates. This book needs an encoding review before it can be joined.** |
| An included file has more than two audio channels | **This audio recording has more than two channels. This book needs an encoding review before conversion.** |
| Reliable source information is insufficient to choose the supported encoding profile | **The app cannot determine suitable audio settings from these source files. This book needs an encoding review before conversion.** |

Do not replace read failures, changed or missing sources, unsafe paths, collisions, decoder errors or other validation failures with generic encoding copy. Preserve their concrete existing messages. An unsupported sample rate should be identified in the existing failure detail rather than being silently resampled.

The retained source notice **Your source files stay in place** remains accurate. **No audiobook was published** may appear as a status detail only after the backend establishes that no final file was published. Never describe a temporary file as completed or imply a pre-existing output was removed. Unresolved encoding decisions go to Jane/Sergei; do not direct the user to a settings button the app does not have. Other safely reviewed jobs may continue under the existing queue contract.

## User explanation and verification

Explain measured pilot growth plainly: its conversion used 160 kb/s AAC stereo while the inputs were approximately 128 kb/s mono. The higher target increased the file size without restoring detail absent from the originals. Future exports preserve mono and use source-matched audio settings. A small size increase from the single cover, metadata and container overhead is acceptable; the app does not shrink a book solely to hit its original byte count.

Exact encoding numbers belong in the explanation or existing technical details, not a new persistent settings matrix. Avoid product copy promising **No quality loss**, **Same sound guaranteed** or **Output never larger**. Report confirmed preservation of channel count, sample rate and full duration as individual measured facts.

QA verifies uniform mono and stereo preservation, supported sample-rate preservation, the implemented source-based target calculation, absence of fixed-profile inflation, and no size-driven downward retry. A technically valid result slightly above source size must not be rejected for size alone. Exercise mixed channel layouts, mixed/unsupported sample rates and insufficient source information where those conditions are supported by the backend. Verify original byte/hash preservation, full duration, metadata, cover and existing completed-job preservation. No new hit areas or layout elements are introduced, so no additional rectangle or tooltip work is created.

Design basis: NN/g truthful status and concrete recovery language; user control through no hidden size-driven compression; Hick's Law through reuse of existing status surfaces. Encoding values and selection mechanisms remain Ender's responsibility. No code, Git, live service, library or browser changes are included. No disposable files or probes were created. Sully commits and pushes this document before the implementation brief cites it.
