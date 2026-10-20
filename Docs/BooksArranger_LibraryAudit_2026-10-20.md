# Books Arranger — current library audit and implementation plan

Observed 2026-10-20T07:13:04.520Z (UTC), 2026-10-20 Asia/Jerusalem. Read-only HTTP GETs against existing v0.19.0 PID 97132 instance 0155977371a645caabadef9333ecd7fa, port5210. Health agrees with existing data/web-instance.json. No app launched, queue control used, media moved, settings changed, iTunes touched or source deleted.

## Access and scope
Desktop branch codex/books-electron-m1, original clean HEAD0469966; Judy spec subsequently committed as2ead477. Direct Git Bash via Node execFile succeeds; exec shell parameter maps Bash to missing WSL runtime. No tooling repair. Existing desktop-settings.json points to Studio Illuminati/WIP/Books Arranger/data. Root source Z:/Audiobooks; Podcasts/Ebooks remain separate. Local API succeeds; old restricted session failures do not apply to these reads.

## Measured counts
Authenticated GET /api/state?library=Audiobooks:480 approved,383 converted/Ready,23 queued, raw384 completed jobs and146 failed jobs. Raw job counts contain history; unique current-book progress differs. GET /api/inventory?library=Audiobooks&view=candidates&status=all:1763 current catalog book candidates, not literary works or physical books on unscanned sources.1283 candidates outside progress-approved;97 approved not Ready. Converted IDs are explicitly accumulated only within approved IDs, so that subtraction is valid. These calls are separate observations of an active catalog, not one atomic database snapshot; values must be rechecked before live migration. Catalog file count9607 is file rows, not books.

Approval: merge_service.progress_books + conversion_progress.approved_scope require matching current context/group revision, no automatic_pending/changed/conflicts, valid review/destination, metadata/source-coverage/order confirmations, exact member/order/inclusion sets, current saved SHA256/size/mtime, usable saved cover/file. Single M4B requires metadata_facts. Converted adds matching completed representative job/manifest/revision/metadata/cover/scope, validation passed, current output stat identity and required completed source/storage cleanup. Ready383 is not a claim that every M4B in Audiobooks is owned or migration eligible.

## Current output attention (73)
Authenticated GET /api/inventory?library=Audiobooks&view=candidates&status=output_attention returned73, all rows in one page. API can take over10s; bounded45s read succeeded. Typed group25 retry,46 other,2 unsupported. All73 report originals_untouched true (saved API evidence, not independent original-byte verification).

| Count | Exact current reason/category | Action/barrier |
|---:|---|---|
|7|Unsupported structural box, precheck passed|Retry admitted; historical reason does not mean current refusal|
|8|Leading gaps/edit presentation, precheck passed|Retry admitted|
|6|Remux decoder/timing mismatch, precheck passed|Retry admitted|
|2|Preservation changed decoder/packets/presentation, precheck passed|Retry admitted|
|2|Unsupported/ambiguous brand, precheck passed|Retry admitted|
|44|Remux changed decoder configuration or relative audio packet timing; Other|CURRENT readmission refusal is Additional filesystem streams require review; original retained (44/44). Saved remux error is historical. Diagnose named stream list; do not strip unknown streams. Metadata does not repair audio|
|1|Full MP3 audio decode Header missing|Damaged-source diagnosis/repair or replacement; retain original|
|1|Prior producer not durably closed|Safety hold; retain owned files, no PID kills or unsafe clear|
|2|Sample size table unsupported|Подземелье and Червь, Curran Tim; preservation parser diagnosis, no blanket allowance|

## Held candidates, separate from output attention
GET inventory status=held returned65:32 mixed recordings;15 playback order uncertain;3 source membership uncertain;2 both order/membership;8 sources disagree title/author;3 book identity uncertain;1 cover unverified;1 exact file missing WinError2. Thus65 is not a metadata-held count.11 title/author/identity holds, plus1 cover. Automatic state Paused, research waiting1218/held65; audiobook runner Running.

Current manual procedure: Books→Held→select→Manual review→save preview metadata, record author-role/metadata evidence and usable cover→Approve candidate metadata; separately choose included files/order and confirm coverage/order/evidence, then Create. Conflicts and single-M4B automatic metadata_facts gate can prevent creation; this is a barrier to extend, not advice that all1283 can be approved by a button. Resume automatic processing only after jobs safely stop; public evidence may still be absent/conflicting.

## Implementation slices and consistency design
1. Durable manual metadata evidence table independent of canonical candidate context, bound to candidate ID and source fingerprint, with versions/time/fields/note and stale status. Saving human metadata appends evidence. Automatic release/start-over clears draft only, never evidence. Re-evaluation compares manual and provider proposals; disagreement stays explicit, no unconditional override.
2. Extend routing metadata with universe and explicit cycle author scope/collection. Common authoritative path planner covers ordinary single-author cycles, root multi-author cycles, universe/cycle and universe standalone, collections named with applicable cycle/universe and Short Stories. Preserve unspecified standalone behavior. Never infer universe from filenames alone. Version existing routing policy; previews changing must not invalidate old converted outputs before migration bindings exist.
3. Multi-source is architectural: existing Inventory.roots[Audiobooks] scalar is consumed by scanner, groups, reviews, jobs, cleanup and automatic pass. Add durable source identities and source-specific grouping, preserving candidate IDs for existing source; prevent cross-source deletion and exclude output. No raw roots JSON edit. Existing source remains and Z:/OLD_Audiobooks appended only through supported configuration.
4. Managed output migration journal: wait for/drain all conversion, scan, research and cleanup mutators; snapshot exact job/candidate/receipt identities. Preflight ownership, safe ancestry, verified output/size/hash, routing evidence, destination collisions and free space. Create no-replace destination copy; verify full content SHA256 and media validation; durable staged journal binds old/new bytes and identities. Atomically publish catalog/job/output-binding updates; keep original manifest/publication history immutable and add relocation binding understood by completion/current-audiobook/recovery/cleanup consumers. Recovery checks follow current verified output binding, never source roots. Delete old owned output only after committed destination verification and restart-safe state; source-removal failure reports copied+verified/original retained. Restart reconciliation handles every stage without guessing or erasing either copy. No plain filesystem move.
5. App barriers: type real current output causes/remedies; diagnose44 remux and2 sample-table failures against representative actual files read-only; prior producer safety state requires exact native ownership proof. Keep unsupported shapes held unless validated preservation handling can be proven.
6. UI follows committed Judy spec2ead477; same-snapshot candidate counts and exact metadata cause codes; existing editor only.

Z:/Audiobooks Sorted and Z:/OLD_Audiobooks both exist as directories. Z: statfs available blocks392773208 ×1024 =402199764992 bytes. Destination entries/collisions, total eligible output bytes, ownership and media verification remain to assess. No live migration while runner active.

## Consumer inventory and release plan
Path/root/review consumers include scanner.py, groups.py, metadata.py, review_backend.py, merge_service.py, automatic_processing.py, audio_jobs.py, audio_pipeline.py, conversion_progress.py, current_audiobook.py, source_cleanup.py, recovery_retention.py, storage_cleanup.py, working_lifecycle.py, replacement_* modules, desktop/main.js, desktop_backend.py, web_server.py, web/app.js, web/index.html, app.py and fixtures. Exact literals must be re-grepped as each contract changes. QA uses fresh synthetic catalog/media beneath named session scratch/shared; never startup-copy real catalog containing cleanup-capable Z: paths. qa-handoff reviewed context plan pending. No focus-taking app launch.

Open Library editions is approved separate backlog: fix authorless fallback, >100 editions/work invalidation, global100k cap, bounded long series, strict ISBN checks, line-size headroom before activation; no activation in current library without separate validated import. NextVersion Pause semantics remain undecided; do not infer.

## Exact current 73 candidate/job identities

| Candidate ID | Job ID | Title | Group | Saved reason |
|---|---|---|---|---|
| 2aec490f-dead-4b4b-a4ee-4d5c52a11866 | 02d4ae1c-3625-497a-ac40-7557fd01b62a | ИСТОРИЯ ОДНОЙ ЛЮБВИ | retry | M4B preservation requires review: Unsupported structural box |
| 76e0dc33-8538-4ea9-b285-5a7297a8a2f6 | f82d81f8-240e-4777-97ae-58486384ba55 | Бегущий по лезвию бритвы | retry | M4B preservation requires review: Unsupported structural box |
| 8b9b97d4-acfc-4392-9c35-6b935b7fb610 | 0907b64a-9daf-4758-85b7-2bb826e0b804 | Унылый незнакомец | retry | M4B preservation requires review: Unsupported structural box |
| 4249152d-4d1a-4350-a102-59141478f9ea | 9a38e7e5-a4cf-4a54-9db4-11587236ac3a | Месяц научной фантастики. Сборник рассказов | retry | M4B leading gaps or edit presentation require a verified preservation plan |
| 577d6577-808c-415d-bfcd-d6722baaa0ae | 63b08ecc-4991-4ddd-93f2-e53ce3179453 | О призраках безобидных… и не очень | retry | Remux changed the decoder configuration or relative audio packet timing |
| 984fe472-fd79-4ef0-b86c-55896e6d21ce | 2d7163d5-a5d9-4d3a-af04-f38a70450b59 | Пока все дома. Новогодняя серия | retry | M4B leading gaps or edit presentation require a verified preservation plan |
| d856a4d2-b64b-45cc-80d9-938175674c77 | 578056ef-a81c-4762-a88e-0fa2df6c6315 | Пока все дома | retry | M4B leading gaps or edit presentation require a verified preservation plan |
| ebbdaa90-d942-4403-91c9-6bcd93d52ff1 | c493cc43-8e85-4088-9b02-c1970f2df67f | Фантастика 2021 | retry | M4B leading gaps or edit presentation require a verified preservation plan |
| 0fe9dd3b-4bc5-4c4b-b972-b6334dc235e6 | 71ebbc8d-e235-46b9-8a1f-84307ffafa34 | Пять вечеров: В снегах | retry | Remux changed the decoder configuration or relative audio packet timing |
| 3dda40a2-06ce-42c0-ba29-07b36543920b | 59fa0cf6-9b65-4391-9eaa-ca4fa0260c76 | Пять вечеров: Кир Булычёв | retry | Remux changed the decoder configuration or relative audio packet timing |
| 1e8eacea-159b-474a-8e29-a78b72f258d3 | 71573ec9-a5ed-479a-b007-924887c78a3b | Пять вечеров: Магия | retry | Remux changed the decoder configuration or relative audio packet timing |
| 88c5ea85-62ff-4178-92a2-712820976c0c | 4a1e9cfa-6ba2-4353-90e3-fe1481ccfab0 | Пять вечеров: Одержимость | retry | Remux changed the decoder configuration or relative audio packet timing |
| 26f410b8-d180-4f52-8c4b-1ddce875c3dd | f314634c-2af2-46fc-ba76-910e7eec5477 | Пять вечеров: Призраки | retry | Remux changed the decoder configuration or relative audio packet timing |
| bb210052-b4b5-4e2d-8aea-ef375e5ab00a | 838dfd3a-0f27-48f3-8fbc-dc87c9c6324c | Сборник фантастики. Рассказы | retry | M4B leading gaps or edit presentation require a verified preservation plan |
| 037988f5-027e-4772-88a6-06ba1e91b100 | 7bd9447a-1f37-4a08-aa46-b989c92ca45c | Тайная история человечества. Сборник | retry | M4B leading gaps or edit presentation require a verified preservation plan |
| 7fd4e232-e970-4e6c-9cb0-81284a917684 | a8508379-58c9-435c-8110-f836a8238db9 | ТЁМНЫЕ АЛЛЕИ 2.1: Жестокость | retry | M4B leading gaps or edit presentation require a verified preservation plan |
| e10d5261-b80f-4de8-bd0d-52207b29c413 | 72aee65f-dc4c-4e08-a332-76016f53df8e | Тёмные Аллеи в Кино | retry | M4B leading gaps or edit presentation require a verified preservation plan |
| 882632ed-5a7e-4a08-8b31-6d582e6d2f27 | 45225b48-b5b8-4195-be27-2ac482c42313 | Сын Дога | retry | Preservation changed decoder, packets or presentation |
| c2a6db32-98bb-4474-ad4e-5df4846c5f39 | 093dbec3-e713-4e51-a792-30d97758945c | Калеки | retry | Preservation changed decoder, packets or presentation |
| dfb47c62-241e-41bf-a1f6-97e7c83a09eb | 217904d2-3cda-4d96-93f1-b6bf2451cefc | Маги без времени | retry | M4B preservation requires review: Unsupported/ambiguous brand |
| e4edb190-7b2d-4f52-9a83-99e154504bd7 | e3d1549b-c849-4edd-a307-f943c7d6f5b9 | Порог | retry | M4B preservation requires review: Unsupported/ambiguous brand |
| 276fd7d4-98c4-44ac-9ae7-ee7653bb302e | 6f0a713f-9f9c-4568-8606-bb6de042591c | Звонок | retry | M4B preservation requires review: Unsupported structural box |
| e11bc1fb-956b-4d14-8abd-79a33495eb35 | 3287d0b8-ad0e-45bc-a293-86c5180dde62 | Звонок-2: Спираль | retry | M4B preservation requires review: Unsupported structural box |
| 93c06963-9483-464c-a233-a2d2741f4f84 | 1c6c878b-0cdc-4050-9f99-f5f5eea9b659 | Звонок-3: Петля | retry | M4B preservation requires review: Unsupported structural box |
| 990784b0-f8a9-48b1-82bd-b45e07a8fc24 | d6a34295-80b2-4b23-bdba-12d9c5ba1b0e | Звонок-0: Рождение | retry | M4B preservation requires review: Unsupported structural box |
| df1ff311-fb71-44ae-963f-ed6c8cdea04e | 8a8a23d1-6b56-47ab-89f7-bf5e27125abb | Сказка | other | Working cleanup requires attention: A prior producer is not durably closed; another attempt is not admitted |
| 6962a6a5-c4b1-42ce-91ac-eceec7403e1b | c4457c89-c352-4720-899a-ea8269ae1f06 | Железная преисподняя | other | Full audio decode failed: [mp3float @ 000001b08f656380] Header missing  [aist#0:0/mp3 @ 000001b08cd6aa80] [dec:mp3float @ 000001b08f638700] Error submitting packet to decoder: Invalid data found when processing input  [aist#0:0/mp3 @ 000001b08cd6aa80] [dec:mp3float @ 000001b08f638700] Error processing packet in decoder: Invalid data found when processing input  [aist#0:0/mp3 @ 000001b08cd6aa80] [dec:mp3float @ 000001b08f638700] Task finished with error code: -1094995529 (Invalid data found when processing input)  [aist#0:0/mp3 @ 000001b08cd6aa80] [dec:mp3float @ 000001b08f638700] Terminating thread with return code -1094995529 (Invalid data found when processing input)   |
| bc18fb5e-16b1-4fdd-a45b-ab2e6cadd793 | 15fe3c8d-fc10-48a8-9645-2682f1f88220 | Алкоголь | other | Remux changed the decoder configuration or relative audio packet timing |
| 386d54a6-60ab-4163-a1bc-6858ac348244 | db39c60a-684a-4efa-980e-071d81538d2d | Альтернативная история | other | Remux changed the decoder configuration or relative audio packet timing |
| ed8a07f5-3d22-486b-b411-0561575cbd73 | 7eb681ae-54e8-42c2-973d-369d18466db2 | Альфред Хичкок представляет | other | Remux changed the decoder configuration or relative audio packet timing |
| a77e850b-2f71-41db-9d56-7fa6a821631d | fea8acd7-d159-4dee-8f2b-438f6db16564 | Антиутопия | other | Remux changed the decoder configuration or relative audio packet timing |
| d24f5b93-4ab8-4e8c-afe7-230537661569 | 139b3941-bfa4-4199-ab4e-8380a97dbd70 | Болезни и лечение | other | Remux changed the decoder configuration or relative audio packet timing |
| 3540ed2f-8f5f-4e36-aea1-9f4207e55676 | ce4bce5d-9556-4301-8994-20d8f612a37e | Вестерн | other | Remux changed the decoder configuration or relative audio packet timing |
| 8e6015e7-2df1-43e1-a410-aec4c1a367fc | 39f893c2-6377-4e3c-9170-45851a38d28e | Война | other | Remux changed the decoder configuration or relative audio packet timing |
| b7c365b4-8f68-4f4f-844c-131b4e3ebeee | 4ff4964f-3d11-48e9-a9f4-91138ab2b1b1 | День смеха | other | Remux changed the decoder configuration or relative audio packet timing |
| e035524d-a649-4e44-8a42-79f4af8f3b79 | d5d92c4b-d27f-4977-a11e-fe61ddc6c8fa | Деньги | other | Remux changed the decoder configuration or relative audio packet timing |
| b580c71a-6fa5-4553-92ed-ce252a7933d3 | 1bc90bdc-4eab-4b83-9c05-95f9d2a9ee07 | Детектив | other | Remux changed the decoder configuration or relative audio packet timing |
| 41c11ac2-50ac-4abc-b562-4a432803aa54 | 3a7450d0-fc6c-43ab-9be0-95c20d0342ae | Дети | other | Remux changed the decoder configuration or relative audio packet timing |
| 01041b78-568d-471e-af3c-e05667420931 | 6b4f1976-beed-4704-92cb-165626313fb8 | Другие планеты | other | Remux changed the decoder configuration or relative audio packet timing |
| 2232e88e-c8e2-45fb-a68f-eb7df497b5e4 | 78cebd9c-073d-49cb-8b25-c158583b0b3c | Дьявол | other | Remux changed the decoder configuration or relative audio packet timing |
| d9fb74fa-21ee-4772-836f-bd591624628e | 34bab43f-5566-4121-933e-053f1a5accb7 | Животные | other | Remux changed the decoder configuration or relative audio packet timing |
| 37605f71-9995-45e7-959b-d151ba9878a2 | d4360b41-802c-4a87-acfd-363dfbd99e9b | Жизнь после смерти | other | Remux changed the decoder configuration or relative audio packet timing |
| 8c40d242-5115-4d19-89f1-58364834a9be | 5610af47-8201-44c4-9b03-e6c0603b182c | Книги | other | Remux changed the decoder configuration or relative audio packet timing |
| a0683467-7108-43c6-8389-9cf8e1b07f37 | 7c50b6f4-86f6-430f-8e8b-115155679def | Контакт с инопланетянами | other | Remux changed the decoder configuration or relative audio packet timing |
| fec701ea-5238-47ba-b5ed-bef7781593bd | 94e42f3f-b78a-4872-a7e7-9bc5e6b52468 | Космос из прошлого | other | Remux changed the decoder configuration or relative audio packet timing |
| bdc884a5-8053-4972-803a-cbaed50faf14 | b6dadd9e-edd6-4ad7-ac28-465fa599e8d2 | Кошки | other | Remux changed the decoder configuration or relative audio packet timing |
| d29fd74d-7c6b-4acf-9b20-f0fe0ff47d27 | 6e29aa36-c399-453b-8d2b-c4afed1dae95 | Ксенофантастика | other | Remux changed the decoder configuration or relative audio packet timing |
| e4b5ca39-8d3e-4a3d-aae2-266cd7346b5d | adfeaaeb-031c-44df-8130-43b8b3437ad3 | Мифы Ктулху | other | Remux changed the decoder configuration or relative audio packet timing |
| ababbbdd-d675-4fb1-adbf-b098b775eb86 | b242df6d-c4e2-4b64-99e8-2c68f49cb504 | Мифы, легенды, сказки | other | Remux changed the decoder configuration or relative audio packet timing |
| 11cada2f-7924-4561-ab0b-385fb2bb11fe | c78ccdc9-9523-4932-8b3c-80e2994e6b61 | Море | other | Remux changed the decoder configuration or relative audio packet timing |
| 69a84979-747e-4142-ade3-8a02d610aebf | 37c7e2e8-1da4-4443-a5f6-f6c13a5cdce0 | Открытия | other | Remux changed the decoder configuration or relative audio packet timing |
| 5c817971-9363-4ce8-92b1-da40b45525ba | f58a0e9b-4300-4a6a-b59b-2dae4ae43616 | Параллельные миры | other | Remux changed the decoder configuration or relative audio packet timing |
| b9cb0f19-187a-4684-a611-6eba500f3616 | c9e5387e-d376-42be-bf3d-8413fe821aa5 | Первоапрельское погружение | other | Remux changed the decoder configuration or relative audio packet timing |
| 5218fe3e-121d-4598-af74-cef7745f1853 | 3cc937a4-cc83-48db-9823-17c3813225b3 | Постапокалипсис | other | Remux changed the decoder configuration or relative audio packet timing |
| 7e5aa4b4-42be-48d7-8ce4-0508cbf14f1e | c2997b37-95eb-49ec-be9b-dce8fd09182b | Путешествия во времени | other | Remux changed the decoder configuration or relative audio packet timing |
| 0bfee9a9-5d9b-4a29-a560-a7dc75a18bf3 | 466cbc5a-86d8-4510-850a-47c2fb5be5ab | Религия | other | Remux changed the decoder configuration or relative audio packet timing |
| 47adb46e-65b4-4c99-88fa-aed00460e1e0 | 66ade8ef-d683-4664-af25-14c6b3abca3a | Роботы | other | Remux changed the decoder configuration or relative audio packet timing |
| 3f64dca3-4abc-4d9e-b1ca-2794ead4b228 | dd06e8b2-51a9-4d3a-9f4a-c59d046c746e | Русская готика | other | Remux changed the decoder configuration or relative audio packet timing |
| 12beef01-c453-44fb-bf0d-4aa4c3b1da47 | b6cff65e-d5e5-4098-9e43-8cd9b7ebec08 | Сверхспособности | other | Remux changed the decoder configuration or relative audio packet timing |
| 3f2c053f-b2ef-4b4e-a298-19beb29cc628 | 55c8e961-601e-4b39-a305-179b83f18834 | Секс | other | Remux changed the decoder configuration or relative audio packet timing |
| 2a58e733-9fd6-4ceb-b02e-2b41384a9018 | 8a79d07a-92ae-4ed1-b9bb-731d1f61caad | Собаки | other | Remux changed the decoder configuration or relative audio packet timing |
| cc346c62-f0e4-4342-a0ea-9d4f8eae090d | ff072112-20ff-4284-95d2-fb402bb84797 | Советская фантастика | other | Remux changed the decoder configuration or relative audio packet timing |
| 21dcd2da-a348-4edb-b28b-a2421a630b29 | 3940cade-3b30-4f3a-9625-28147e10534c | Спецслужбы | other | Remux changed the decoder configuration or relative audio packet timing |
| 6ab49641-4886-452a-b1dc-8311c3ab097c | 31ff77bd-1b54-4821-be18-e9b4b4fb5d47 | Спорт | other | Remux changed the decoder configuration or relative audio packet timing |
| 5d3eb527-b71e-41f1-830b-bbc8f8e90d83 | bbddb82e-65d7-4cf6-9577-072ccea02b32 | Сто лет назад. Рассказы 1923 года | other | Remux changed the decoder configuration or relative audio packet timing |
| 031e4844-7742-45ce-914f-200f45cdf792 | 75e75ceb-644f-47d2-8020-8aa1751710a5 | Страх | other | Remux changed the decoder configuration or relative audio packet timing |
| 9273af14-ff60-4242-8cad-e19f4b5f9a81 | 358c1203-562e-4621-95e4-cb97a3aea091 | Фантастика | other | Remux changed the decoder configuration or relative audio packet timing |
| f84c9b76-3776-49d4-9b41-a996b6c656c2 | c228790c-9883-47f8-9ff5-5ed9ef0e3f1b | Фэнтези | other | Remux changed the decoder configuration or relative audio packet timing |
| 9a0496e7-28ca-4678-af16-4b5b901bf331 | c00ae153-d97c-4a27-b25a-a4f0b2ba876d | Хэллоуин | other | Remux changed the decoder configuration or relative audio packet timing |
| 4883b444-0825-459d-8855-91349e3f165c | 9a80ddbf-accc-47bb-a3f9-52403498ffc2 | Хоррор | other | Remux changed the decoder configuration or relative audio packet timing |
| 092631f9-6f49-4175-9556-979615bde236 | b6df0048-99bc-4cac-8b02-73e6332472d5 | Юмористическая фантастика | other | Remux changed the decoder configuration or relative audio packet timing |
| a7b3873b-d03f-4b33-872e-0b4ad66ba45f | 592cbac0-18d2-4988-ac55-f124d46ca620 | Подземелье | unsupported | M4B preservation requires review: Sample size table |
| 1705d060-d016-42af-8ece-76040b5ce89a | 7adcefa5-7176-47be-9849-75abbb6da496 | Червь | unsupported | M4B preservation requires review: Sample size table |

## Refusal clarification after frozen-manifest inspection
All44 Other/remux rows carry a current v0.19.0 file_problem/user readmission refusal: `Failed M4B retained: Additional filesystem streams require review; original retained`. They are single-M4B unpublished non-repair manifests, with source chapter records. No44 are currently refused because the remux path itself ran again. Need inspect exact stream names read-only and extend supported admission for recognized marker metadata without discarding unknown streams. Existing zone_identifier removal is cleanup-only; retry admission currently invokes single_stream first.
