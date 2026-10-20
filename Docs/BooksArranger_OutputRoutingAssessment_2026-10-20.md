# Books Arranger — provisional existing-output routing assessment

Measured 2026-10-20, read-only. Ready API pages were read 08:03:20–08:07:04 UTC; every page reported total 385. The completed audio-job records were read in one SQLite query-only transaction. Native ordinary file sizes and target-directory listing were read at 08:11–08:12 UTC. This is an active-catalog provisional assessment, not a migration eligibility receipt; drain all mutators and revalidate every publication, native identity, hash, receipt, and routing acceptance before applying. No files or settings were moved or changed.

- 385 unique Ready current publications: 384 original and one replacement; 385 distinct existing paths. All matched a completed job receipt path and size.
- Existing media: 192,283,136,938 bytes (179.08 GiB); largest 2,094,929,300 bytes. Destination Z:/Audiobooks Sorted was empty. Free bytes at the later statfs observation: 401,643,614,208. Space exceeds a full second copy by 209,360,477,270 bytes before reserves/other running work; no space reservation or copy was attempted.
- Pure books-hierarchy-v2 preview accepts all 385 current accepted reviews, produces zero case-insensitive target collisions and maximum target length 188 characters. This does not establish that their old grouping metadata is semantically complete.
- Stored accepted fields yield 300 Author standalones, 75 Author/Cycle books and ten ungrouped collections retaining Сборники per Sergei’s explicit decision. No current accepted review has Universe or multi_author_cycle set.

Actual metadata cases requiring a focused routing decision or corroborated evidence:

- Seven The Horus Heresy books span five accepted authors but all have multi_author=false and no Universe. Their literal previews incorrectly retain separate author folders for the requested shared-cycle behavior. The books are Horus Rising, False Gods, Galaxy in Flames, The Flight of the Eisenstein, Fulgrim, Descent of Angels, Legion. The Talon of Horus has cycle Чёрный Легион and no Universe. Confirm an explicit shared universe and its exact folder name before applying those eight routes; filenames alone are not evidence.
- Three books under Дозоры Сергея Лукьяненко span three accepted author credits and all have multi_author=false. Review whether this is one shared cycle and any applicable universe before applying their old author-scoped paths.
- История будущего occurs under Stephenson Neal and Heinlein Robert A. Shared cycle labels alone cannot establish a common universe or multi-author cycle: these may be homonyms. No automatic merge is proposed.
- Accepted spelling variants Шерлок Холмс/Sherlock Holmes and Robert Langdon/Robert Langdon series remain distinct. No undocumented alias normalization is applied.

Do not introduce a universal “prove no universe” hold. Ordinary accepted standalones remain author-routed. Confirm the concrete shared-world cases above; preserve separate evidence and explicit user answers.

Reproduction evidence retained once in the session scratch shared/migration-assessment/: input.json (385 read-only API rows and coherent completed-job rows), assessment.json (exact IDs, current receipt identity, sizes, proposed paths and route fields), page-0/100/200/300.json and assess.py (pure organization.plan call). These are evidence, not production migration instructions.

| Candidate | Current accepted title | Author | Cycle | Literal proposed relative path |
|---|---|---|---|---|
| 5b457dca-1a09-4a2b-8103-948a85694283 | Лавина | Stephenson Neal | История будущего | Stephenson Neal\История будущего\История будущего - 1 - Лавина - Stephenson Neal.m4b |
| 91406f8a-2c9f-4887-9176-5214eff8c405 | The Talon of Horus | Dembski-Bowden Aaron | Чёрный Легион | Dembski-Bowden Aaron\Чёрный Легион\Чёрный Легион - 1 - The Talon of Horus - Dembski-Bowden Aaron.m4b |
| 31668414-237c-456d-8fab-e79a2b0cbece | Horus Rising | Abnett Dan | The Horus Heresy | Abnett Dan\The Horus Heresy\The Horus Heresy - 1 - Horus Rising - Abnett Dan.m4b |
| 236c7bee-8c4d-440c-9b68-a31002176769 | False Gods | McNeill Graham | The Horus Heresy | McNeill Graham\The Horus Heresy\The Horus Heresy - 2 - False Gods - McNeill Graham.m4b |
| 3b1601a0-4cf1-46e8-ae02-fee58728218d | Galaxy in Flames | Counter Ben | The Horus Heresy | Counter Ben\The Horus Heresy\The Horus Heresy - 3 - Galaxy in Flames - Counter Ben.m4b |
| 1418d2e0-eb30-4874-8575-21e2bb58358c | The Flight of the Eisenstein | Swallow James | The Horus Heresy | Swallow James\The Horus Heresy\The Horus Heresy - 4 - The Flight of the Eisenstein - Swallow James.m4b |
| fb04364a-249f-489c-981c-8454ea7903a5 | Fulgrim | McNeill Graham | The Horus Heresy | McNeill Graham\The Horus Heresy\The Horus Heresy - 5 - Fulgrim - McNeill Graham.m4b |
| ec6be5c6-5aa3-4a94-a3b0-5f061de95a56 | Descent of Angels | Scanlon Mitchel | The Horus Heresy | Scanlon Mitchel\The Horus Heresy\The Horus Heresy - 6 - Descent of Angels - Scanlon Mitchel.m4b |
| c154603e-ba62-4d02-9d5c-48d9df80533a | Legion | Abnett Dan | The Horus Heresy | Abnett Dan\The Horus Heresy\The Horus Heresy - 7 - Legion - Abnett Dan.m4b |
| b25c56a4-3753-421e-97dc-de88f3215a80 | Orphans of the Sky | Heinlein Robert A. | История будущего | Heinlein Robert A\История будущего\История будущего - 2 - Orphans of the Sky - Heinlein Robert A.m4b |
| 11934811-6c30-42ad-bd38-d94aafeb7f65 | Дикий артефакт | Угаров Виктор | Дозоры Сергея Лукьяненко | Угаров Виктор\Дозоры Сергея Лукьяненко\Дозоры Сергея Лукьяненко - 8 - Дикий артефакт - Угаров Виктор.m4b |
| f354f26a-7d9d-4a54-90bf-1d1c6aa98d51 | Иной Среди Иных | Каплан Виталий | Дозоры Сергея Лукьяненко | Каплан Виталий\Дозоры Сергея Лукьяненко\Дозоры Сергея Лукьяненко - 1 - Иной Среди Иных - Каплан Виталий.m4b |
| a5602c97-4c79-41f1-87f2-9ee9590bc1d4 | Невский Дозор | Никита Аверин, Игорь Вардунас | Дозоры Сергея Лукьяненко | Никита Аверин, Игорь Вардунас\Дозоры Сергея Лукьяненко\Дозоры Сергея Лукьяненко - 3 - Невский Дозор - Никита Аверин, Игорь Вардунас.m4b |
