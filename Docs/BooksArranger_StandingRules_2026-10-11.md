# Books Arranger — standing automatic-processing rules

User decisions received 2026-10-11 through Jane. Scope: Books Arranger Audiobooks, old-to-new library transformation without per-book questions. These rules supersede the earlier narrow automatic admission policy; they are authorized requirements, not a claim that all are already implemented. Existing completed work and the earlier 0.12 core/test evidence remain preserved. Unofficial translations are intended; original fanfiction was not requested.

| Case | User-approved standing rule |
| --- | --- |
|1 Work identity uncertain/conflicting | Process other books first, then repeatedly revisit uncertain work using different Internet sources. Avoid tight loops and known failures. Do not pick the first conflicting result. |
|2 Unofficial Russian translation alias | Accept explicit unofficial translation/recording credits as alias evidence connecting the recording to the verified original. Search the Russian book name with English/original-title leads. No official Russian edition is required. |
|3 Original language unknown | Allow it, record the original-work language as Unknown, and use recording-language placement. Do not turn recording language into an invented original-work language. |
|4 No published English title | Use the Russian source title, explicitly source-derived. Do not invent an English title or claim official publication. |
|5 Author/narrator/translator/editor role unclear | Verify the author role using other sites; keep researching rather than silently assigning a recording role as author. |
|6 Surname order ambiguous | Use the verified full author name for the folder. Do not guess the surname. |
|7 Series/position | Use verified series and position. Omit genuinely unknown values; never invent them. |
|8 Fan-assembled collection | Positively establish collection provenance, verify constituent identities and source/order mapping, retain a source-derived collection label marked as fan assembly. Search unofficial collection sites too; Созвездие Льва is a motivating example. Do not force a fictitious single published-work identity. |
|9 Mixed source group | Split proven independent works. Preserve/hold ambiguous membership; a folder alone is not proof. |
|10 Playback order | Allow coherent filename order where source membership/numbering is proven; otherwise hold. |
|11 Covers | Usable embedded custom/fan covers are allowed; exact public-catalog pixel equality is not required. An absent cover may use a neutral cover; image generation is optional, not a required interactive step. |
|12 Audio format | Verify and arrange existing M4B without re-encoding. Define safe automatic encoding for other formats; preserve media integrity and source protection. |
|13 Recordings/duplicates | Keep demonstrably distinct recordings/editions separate and reuse proven completed work. Mark possible duplicates for user review. Unresolved same-recording duplicates preserve originals; verified distinct recordings can carry a nonblocking related-recording marker. |
|14 Destination collision | Never overwrite blindly. Distinguish outputs using verified metadata, or skip/reuse a proven identical output. Preserve unrelated colliding bytes. |
|15 Manual draft | Preserve manual drafts. No explicit authority to overwrite them was given. |
|16 Changed/unreadable input | Rescan/retry current inputs. Never delete unverified sources. |
|17 Output/cleanup failure | Preserve source/recovery evidence, diagnose and retry recoverable failures. No verification or native cleanup bypass. |

## Evidence and data boundaries

Identity evidence remains field-specific and associated with the actual work/person/recording. Search snippets and whole-page name co-occurrence are leads. Translator/editor/narrator qualifiers do not establish the author. Contradictions remain visible and block uncertain membership/retirement; weaker missing optional facts may be omitted or labelled Unknown under the rules above. Original work, recording translation/edition, fan assembly and output file are distinct identities.

Every final output must pass the appropriate protected-source/media verification and destination publication checks before exact included originals can be retired. Existing 24-hour recovery policy remains unchanged. No Comics state/config/ledger or Y:/Open Library archive is modified. No arbitrary new overwrite, blind delete, weakened path/reparse/stream guards or host/OS launch bypass is authorized. Host pacing, actual vendor 403/429/Retry-After, bounded requests and safe transport remain enforced.

## Planned implementation ownership

Ender lead: public research/evidence integration; recording-alias and unknown-language/source-title/full-author routing policy; verified/omitted series; component-aware fan collection manifests and source mapping; durable other-books-first research retries; integration with existing approval/queue/counters. Source/proof v1/v2 of the earlier 0.12 core stays immutable and must not be released as satisfying these expanded rules.

Separate media Ender: a focused media-policy module, encoding_policy.py/audio_pipeline.py and private media fixtures for existing M4B remux/copy verification, supported format normalization, usable source/neutral cover preparation. Integration in merge_service.py/review_backend.py belongs to the lead.

Separate duplicate Ender: a pure duplicate/collision classification module and fixtures; no library actions or integration-file edits. Lead applies its verified decision in admission and queue. Frontend code/layout/copy belongs to the separately assigned Ender after Judy's committed spec; Sully owns all Git/version/release operations.

## Verification and live application

Test each modified boundary with private fixtures, including adversarial alias/author-role/collection-component conflicts; Unknown versus known language; Russian title fallback; full-name routing; verified versus omitted series; coherent filename order; custom/no-cover preparation; unchanged decoded audio for existing M4B; compatible encoding; distinct/possible/identical recording cases; collision preservation; retries that leave manual Stop/restart Paused; source changes and failed verification that never retire originals. Combine only after worker contracts are pinned and reviewed; use existing finite owned test execution, no extra framework or stale 86-case receiver run.

Actual application waits for QA/review/release. Read-only proof of no active conversion/research/cleanup, supported automatic Stop with saved checkpoint where necessary, normal user Restart entry, new loaded-version/owner/protected-record verification, then one guarded resume under the user's existing authorization. No persistent service is launched from the tool host and no active conversion is interrupted.
