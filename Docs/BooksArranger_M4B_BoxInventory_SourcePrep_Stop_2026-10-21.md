# Metadata inventory source preparation: stopped on changed current binding

**STOP / UNRUN / NOT ADMITTED.** This records the permitted source-preparation task under Senua review SHA `43acfd7003ab1fc295606479e931dce0025cc64e13168aec39f22a214f59ecad`, committed `ab56bf354c24a3d5d8920a0f30e516bf3c8c86fb`, following plan SHA `ed9a5612f21ab3a1e6106e11cccadc01c1e0f7bfe9d7079a23f07569661c40cd`.

The exact five-record current-held request can no longer be frozen. The separately authorized targeted query established a newer **running** job for Ring-3. No source inspection, file admission, media/native execution, process, tests, repair or live controls followed this observation. Existing v0.19 work is allowed to continue undisturbed.

## Exact changed-case observation

Read-only/query-only SQLite snapshot, explicit `BEGIN`, `ROLLBACK` and connection close in `finally`, confined to job `1c6c878b-0cdc-4050-9f99-f5f5eea9b659` and candidate `93c06963-9483-464c-a233-a2d2741f4f84`:

- Candidate remains revision 5, active (`superseded=0`).
- Historical job `1c6c878b-0cdc-4050-9f99-f5f5eea9b659` remains `needs attention`, stage `checking sources`, exact reason `M4B preservation requires review: Unsupported structural box`. It is not set aside and has neither an output receipt nor publication intent. Created `2026-10-15T18:44:04.762492+00:00`; updated `2026-10-17T23:58:54.804344+00:00`. Frozen manifest SHA `5f8e96720658195ef8dbe8c43c648f1a171de5965c3b43d1b21c0f129047b1ec`.
- Newest non-set-aside job `c49a8bd9-4830-4f20-8106-c4ef61fd4354` is `running`, stage `copying`, with an empty reason, frozen revision 5 and no output receipt or publication intent. Created `2026-10-20T20:44:43.909442+00:00`; updated `2026-10-20T21:00:25.863932+00:00`. Manifest SHA `af8fae72688188275f5bc2b61a5f6029b0a4d1ddd0418e73f093fd3756dd193e`.
- The candidate has exactly those two recorded jobs in the targeted result. No completed publication is recorded there. This is a catalog observation, not physical output verification or a prediction of the running job's eventual result.

The original five-ID current-held query returned four matching records. This does **not** establish the global count of current structural holds, nor that Ring-3 is fixed. It explains why the old Ring-3 job is no longer the newest held job for that active candidate.

## Four records still matching the original predicate

All four remained current revision 5 / frozen revision 5 / member 0 at that query. Source paths, source SHAs and manifest SHAs remain listed in the original plan; no source bytes were read.

| Job | Frozen size | Frozen modified value |
| --- | ---: | --- |
| `02d4ae1c-3625-497a-ac40-7557fd01b62a` | 47332348 | `1526936522339880400` |
| `0907b64a-9daf-4758-85b7-2bb826e0b804` | 67873077 | `1547248112000000000` |
| `d6a34295-80b2-4b23-bdba-12d9c5ba1b0e` | 213066284 | `1474314090421431500` |
| `f82d81f8-240e-4777-97ae-58486384ba55` | 255538614 | `1540835927795394900` |

These four are not silently substituted for the reviewed five-record scope. A four-record request would require an explicit reviewed amendment. The active Ring-3 job must not be substituted or inspected. Prefer reconsidering actual inventory only after a separately authorized safe pause/drain during activation, rather than racing the old app. No pause, drain or control action was performed here.

## Preserved partial artifact and unmet gates

One draft file was created before the binding mismatch was found:

`C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/m4b-box-inventory-source-v1/inventory.py`

Its literal scope remains the original five IDs; it requires an exact five-record current query match before any native source open. It is **UNRUN, incomplete, unreviewed and not executable admission**. It sketches helper-local checked-close adapters, fresh same-handle full128/basic facts, bounded same-handle seek/hash, default-data-stream-only admission and copied production whitelist comparisons. These are source intentions, not measured native facts or accepted resolution of the eight review conditions. In particular, the evidence-parent before/after comparison around an intended CREATE_NEW write needs source review for expected directory metadata changes; a conservative false refusal is possible. No field in the draft is a completed observation.

No `request.json`, `closure.json` or Node invocation was created. The runtime/dependency closure, exact final argv and all eight condition resolutions are therefore **not frozen or reviewed**. No command is proposed for execution. Do not fill missing bindings from old data, loosen current-state predicates or increase limits to obtain a run.

The existing owner, production native_io/parser, previous Iron diagnostic and all old evidence remain unchanged. The earlier unadmitted unit wrapper remains excluded and was not rerun or deleted. Session scratch is preserved. Only this new helper draft and this document belong to this stopped preparation task; all other concurrent work is preserved.

Preserved UNRUN draft SHA256: `70957cd7d90dc19c46a3ef473768f077d578e2939ec6b8f169138e1e963f9fd6` (22810 UTF-8 bytes). This pin identifies the partial artifact only; it grants no execution authority.
