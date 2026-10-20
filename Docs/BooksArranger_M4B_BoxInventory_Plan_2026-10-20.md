# Five held M4Bs: read-only box inventory proposal

**Status: plan only; existing diagnostic is inadequate unchanged. No media reads or execution authorized by this document.** Current query-only SQL confirmed five active newest, non-set-aside jobs with exact reason `M4B preservation requires review: Unsupported structural box`, plus two with `M4B preservation requires review: Sample size table`. All seven are candidate revision 5 and contain exactly one frozen source member (index 0). These reasons establish app preservation barriers, not original audio damage.

## First substantive route finding / STOP

The previously successful real-input route is `iron-inferno-diagnostic/run.mjs` → existing `bounded-check.mjs::runOwned` → `C:/Python314/python.exe -I -B diagnose.py`. That Python helper explicitly requires one source, writes `source.mp3`, forces the MP3 demuxer and invokes FFprobe/FFmpeg. Reusing it unchanged would rerun Iron Inferno and cannot inspect these M4Bs. It must not be relabelled or repurposed without review. This finding stops further investigation/execution in this task.

Minimal proposed extension: a **new, independently reviewed read-only box-inventory Python helper**, with a fixed five-record request, using the existing native source guards and unchanged existing owner. A small literal Node invocation file would name only this reviewed helper and request, use the existing owner and create a fresh evidence receipt; it is not an accepted route merely because it imports that owner. Both files, request and dependency closure must receive source review and explicit route approval before any execution. No unit tests, canonical QA commands or app startup may be embedded. No implementation is included here.

## Exact mandatory source set

All paths below are relative to the existing immutable source root `Z:\Audiobooks\`. Each row specifies job ID / candidate ID / current title / exact member path / frozen member SHA / immutable manifest SHA.

1. `02d4ae1c-3625-497a-ac40-7557fd01b62a` / `2aec490f-dead-4b4b-a4ee-4d5c52a11866` — **ИСТОРИЯ ОДНОЙ ЛЮБВИ**
   - `Niel Gaiman\Neil Gaiman  - ИСТОРИЯ ОДНОЙ ЛЮБВИ.m4b` (two spaces before the hyphen).
   - Source `576c62154e7ce0319128a84dd50626f1423450ad16e335e08abf76522ce27430`.
   - Manifest `aef744cc2034943950a9d20365c2ea5757dce2b1517e7112e39fe272e66639bc`.
2. `0907b64a-9daf-4758-85b7-2bb826e0b804` / `8b9b97d4-acfc-4392-9c35-6b935b7fb610` — **Унылый незнакомец**
   - `Philip K. Dick\Унылый незнакомец.m4b`.
   - Source `ed410225dc088745ba554b79abc9b642e816f7a3842f9c73344f3ec481374246`.
   - Manifest `de8a1496fd2adfeabb1d4a7289c90dd35ae717510f89f74f29e93970d0e265ea`.
3. `1c6c878b-0cdc-4050-9f99-f5f5eea9b659` / `93c06963-9483-464c-a233-a2d2741f4f84` — **Звонок-3: Петля**
   - `Судзуки Кодзи\3 Судзуки Кодзи - Звонок-3 Петля.m4b`.
   - Source `2c13c7b7b9065cebe3a3d6288420c7565f6b262476021494453da330f00dbabd`.
   - Manifest `5f8e96720658195ef8dbe8c43c648f1a171de5965c3b43d1b21c0f129047b1ec`.
4. `d6a34295-80b2-4b23-bdba-12d9c5ba1b0e` / `990784b0-f8a9-48b1-82bd-b45e07a8fc24` — **Звонок-0: Рождение**
   - `Судзуки Кодзи\4 Судзуки Кодзи - Звонок-0 Рождение.m4b`.
   - Source `6780d2d9d775ed3fd737716d0738a238b96d5af294c5d9b9187ccc1f0b5b09db`.
   - Manifest `960932d2482f45ac829e359744773731ef2a43a87da115862c8fb3cb55b3ad71`.
5. `f82d81f8-240e-4777-97ae-58486384ba55` / `76e0dc33-8538-4ea9-b285-5a7297a8a2f6` — **Бегущий по лезвию бритвы**
   - `Philip K. Dick\Дик Филип Киндред - Бегущий по лезвию бритвы.m4b`.
   - Source `f32a28c5c2e48c02b8804cd3e75513c62ee79d63fe3bce4d1963d3a119e1e09c`.
   - Manifest `4b1eca350b1eeb4c1f369a8fec8645bd8ff1fc57a9a116b96aacae8571fe45ba`.

The two Curran files are **excluded by default**. Include them only in a separately frozen request if needed to validate the existing zero-count/fixed-16 text profile: job `592cbac0-18d2-4988-ac55-f124d46ca620`, candidate `a7b3873b-d03f-4b33-872e-0b4ad66ba45f`, `Tim Curran\Подземелье & Червь\Подземелье.m4b`, SHA `e1e2145e60e9bbf94768e8d58bea9ccf45c6f7c6624088c1b2f1278dfd6add96`; job `7adcefa5-7176-47be-9849-75abbb6da496`, candidate `1705d060-d016-42af-8ece-76040b5ce89a`, `Tim Curran\Подземелье & Червь\Червь.m4b`, SHA `a7026a82477765562a8fa64dc668fd2f8ec92b89464aa8ad630aa56ed1666f96`.

## Proposed bounded observation

Before execution, freeze an exact query-only projection of the five job/candidate revisions, manifest hashes, source paths, sizes, modified values and source SHAs. Refuse if any identity changed; do not silently add jobs. For each source sequentially, hold the existing `DirectoryBoundary` and `VerifiedFile` through all observations and final verification. Apply the existing read-admission/link/stream rules unchanged; unknown capabilities or an admission refusal stop that case. Never delete a marker or change alternate streams.

While held, record native file/parent identities, ancestry and size/modified facts; stream the **entire** source SHA and require the frozen SHA. Read only bounded metadata regions for the inventory: top-level box headers, one bounded `moov`, and child boxes in already defined container types. Seek over `mdat` except for the full-file hash pass. A second full SHA and native facts/ancestry recheck finish each case before handles close. A Python read stream, if needed for bounded seeks, must be opened while the native deny-write/delete guard is held and proven to name the same retained object; an unavailable same-object proof is a STOP, not a path-only fallback.

Proposed caps for review: one cumulative 540-second cooperative work budget inside the existing owner's 600,000-ms bound; metadata allocation at most 32 MiB per file; nesting at most 16; at most 10,000 box records per file; final evidence at most 2 MiB, terminal summary at most 8 KiB. Oversize, malformed extents, inconsistent lengths, duplicate mandatory structures, deadline/cancellation or missing roots produce an incomplete/refusal result. No automatic second run or higher limits. No full media copy, PCM decode, remux, mutation or payload salvage is necessary.

Output: per source, frozen job/member binding and before/after full SHA/native facts; each observed box's absolute offset, size, four-character type, parent path and bounded payload digest; explicit opaque/unvisited boxes; and the exact production whitelist mismatch **only where the already defined caller/container schema makes that comparison unambiguous**. Do not decode unknown boxes as containers by guesswork, dump embedded tags/private metadata, or call an unknown box safe. No catalog/job update follows the inventory. Findings then return to Ender/Senua for a separately scoped preservation design.

## Pinned existing components and execution prerequisites

| Existing component | SHA256 |
| --- | --- |
| Session `iron-inferno-diagnostic/run.mjs` | `395928b330408786282b7ae860f9e9fe2707d210cccd9b72b90375c49b9243cf` |
| Session `iron-inferno-diagnostic/diagnose.py` | `b3eb762fadd2ce7554c22fa57a25ea41dc4dd42742d9de1f6884a1c78c66e06b` |
| Desktop `m4b_preservation.py` | `a3ca16290c260d9691c555e7186e09a79cf255f19f3b3244a055cb82ab5d1d01` |
| Desktop `native_io.py` | `e5e6aef41da64308215d10b636d6e583635b7e2476c7d90a7158d8ad4525dc14` |
| Studio `.claude/skills/qa-handoff/scripts/bounded-check.mjs` | `3f7e6bc022fe9a34aad63340059bd0f975fad8948e1b770c0f7a3bd6e3c1038c` |

Consumer boundary: this observation informs `m4b_preservation.profile`'s existing explicit whitelist refusal. It does not edit that whitelist, repair/chapter code, source files or preservation semantics. The two Curran cases concern `profile_zero_chapter_count`; unchanged native track bytes and existing chapter presentation remain mandatory. No assertion that these seven barriers are already fixed follows from this plan.

Future scratch location, not created by this task: `C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/m4b-box-inventory/`. Preserve all session evidence. The prospective normal tool route would use default PowerShell, login=false, Studio workdir, explicit Node path and literal reviewed helper path; no shell override, guard changes, test wrappers or formal-QA authority. The final command cannot be frozen until the missing helper, input request, runtime/dependency pins and permitted ownership/closure route are independently reviewed. Required receipt: actual original terminal result plus existing owner closure status; timeout, forced close, uncertain native ownership or absent closure makes the run incomplete and stops follow-up. No tool admission is inferred merely from prior media success.

No source files, helpers, requests, globals, media, databases or app state were changed. This document is the only deliverable of the planning task.
