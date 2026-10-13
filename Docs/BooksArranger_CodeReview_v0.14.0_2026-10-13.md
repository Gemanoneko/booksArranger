# Code Review — Books Arranger v0.14.0

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-13
Tool: Books Arranger
Release: v0.14.0
Commit range: v0.13.1..67e3d43cc123a5f33d99a15e6f8778ce85509f72 (branch codex/books-fast-identity-0.14.0; includes docs commit e68597a)
Files changed: 19 files, +1451 / -34
Stand-down dimensions: none
```

---

## Summary

v0.14.0 adds local-agreement identity (Sergei decision "local evidence is enough when it agrees", 2026-10-12). Embedded tags plus file and folder names can now decide a book's title and author without the Internet. The Internet only fills gaps (FantLab, Wikidata, Open Library, Google Books, iTunes). The release also changes per-host pacing, the User-Agent, DuckDuckGo challenge handling, the cache bound (5,000 entries / 64 MB) and retry scheduling.

The review was red-team. Method, all read-only:
- Read the full diff, all of `local_identity.py`, and the touched admission, evidence, policy and source-gate code.
- Ran the pure matcher functions on adversarial inputs (no app, no network, no Z:/Y:).
- Queried Ender's catalog copy `scratch/fast-identity-2026-10-13/evidence/catalog-copy.sqlite3`, opened `mode=ro&immutable=1`, and his `measure-after.json`.

**Result:** the matcher approves books whose author is wrong. One case is live: 5 books in the 2026-10-12 copy would publish under the narrator's name. The split-part guard fails open in two layouts. The release is blocked.

Confirmed sound:
- Admission, media probing, publication, retirement and recovery code is untouched. The diff touches none of `source_cleanup.py`, `recovery_retention.py`, `replacement_retirement.py`, `audio_jobs.py` or `native_io.py`.
- `approve_automatic` re-derives the agreement inside the existing locks. The probe still re-compares embedded tags before encoding.
- The 1,309 same-folder split files are all held: 0 of 1,309 are approvable in `measure-after.json`.

---

## Rubric

### 1. Security

- Status: Pass
- Findings:
  - **SQL:** `folder_siblings` is parameterised and escapes LIKE (`!`, `%`, `_`).
  - **Catalog URLs:** search URLs are built with `urlencode`. Citation URLs are regex- or int-constrained (`/works/OL…W`, Google id `[A-Za-z0-9_-]{4,40}`, iTunes `collectionId` int, FantLab int, Wikidata `Q…`).
  - **Output paths:** names still go through `safe_name`. There are no new shell-outs.
  - **URL-less evidence:** it cannot be reached from HTTP. `web_server.py:356` whitelists save kwargs, so `automatic_facts` and `automatic_pending` cannot be posted.
  - **User-Agent:** the public repo URL only; no e-mail or secret. This meets the Wikimedia and Open Library identification ask.
  - **Homoglyphs:** probed. Mixed Latin/Cyrillic look-alikes (`Cтивeн Kинг`, `Stephen Kіng`) fail closed (no match). They cannot make different names agree.

### 2. Correctness & Logic

- Status: Fail
- Findings:
  - **[Critical] C1 — a narrator credit becomes the author.** Location: `local_identity.py:308-324` (`_embedded`) and `:353-368` (`_supports_author`).
    - In this library the artist tag is often "Сборник" (collection). `NOT_PEOPLE` drops it, and the next credit wins. Here that credit is `album_artist` = "читает Роман Волков" ("read by Roman Volkov"). The file name "01 читает Роман Волков - Недобрый глаз" repeats it, so the author "agrees".
    - Nothing recognises narrator markers (читает / чит. / read by …) in credits or path names.
    - **Live:** `measure-after.json` marks 5 books approvable with `canonical_author` "читает Роман Волков", "читает Наташа Белкина", "читает Дмитрий Шабров", "читает Анастасия Стряпко" and "читает Радион Нечаев". They are in `Сборники\АНТОЛОГИЯ РУССКОЙ МИСТИКИ\`. `source_gate` passes them (`author_matches` accepts the same string).
    - On the first post-upgrade pass these 5 would be converted and published under `<root>\читает …\`, and their originals retired.
  - **[Critical] C2 — `PATRONYMIC` deletes real surnames.** Location: `local_identity.py:52`, `:130-138`, and the dedupe at `:321`.
    - The regex `[а-я]+(?:ович|евич|ич|овна|евна|ична|инична)` (Latin `…ovich|evich…`) treats surnames such as Гжендович, Костюкевич, Хазанович, Ходасевич and Abramovich as patronymics and drops them. The name then matches on the given name alone.
    - Probe results: `compare_names("Дмитрий Костюкевич","Дмитрий Хазанович")` is a full `same` match. Both are real people in this catalog, an author and a narrator. "Ярослав Гжендович" matches "Ярослав Хорошков", and "Roman Abramovich" matches "Roman Polanski".
    - In `_embedded`, two different credits are therefore merged into one person, and `AUTHOR_TAGS` order makes `album_artist` win. Synthetic row: artist "Ярослав Гжендович", album_artist "Ярослав Хорошков", folder "Ярослав Гжендович". Result: **accepted, author "Ярослав Хорошков"**, the narrator.
    - No live instance was found in the copy, but the names are from this library. This also breaks the documented rule that "every word must pair one to one". The same defect feeds `_name_matches` and `_full_name` in the gap search, and marks "Ярослав Гжендович" as `partial`.
  - **[Critical] C3 — the split-part guard only sees part of the book's neighbourhood.** Location: `local_identity.py:386-408` (`folder_siblings`), with `agreement` `:438-455` and `_path_components` `:251-261`.
    - **(a) The guard is blind at the library root.** The query `path LIKE '<folder>\%' … LIMIT 2000` scans the whole subtree (`EXPLAIN`: `SCAN files`) and then filters to direct children.
      - For `Z:\Audiobooks` (9,519 audio descendants) it returned **1 of the 44** direct root files. 9 root-level candidates are approvable in the copy.
      - Probe: root-level "Пётр Сидоров - Длинная книга (Часть 1).m4b" (album "Длинная книга") is accepted, and `source_gate` gives no reasons. The guard only sees "(Часть 2)" when that sibling is visible.
      - `sorted(folders)[:20]` truncates silently in the same way.
    - **(b) Disc and part folders are checked one at a time.** `_path_components` treats `CD1` / `Part 1` / `Часть 1` folders as transparent and takes identity from the parent book folder. `folder_siblings` still looks only inside the one disc folder.
      - Probes: `…\Пётр Сидоров - Длинная книга\CD1\Длинная книга.m4b` and `…\Длинная книга (часть 1)\Длинная книга.m4b` are both accepted.
      - No live instance: the only grandparent with ≥2 numbered folders, each holding one M4B, is Harry Potter, and those are real separate books.
    - In both cases one part is published as the whole book and its originals are retired. That is the failure the guard exists to stop.
  - **[Major] M1 — a lone numbered part or chapter is accepted as the whole book.**
    - A single file whose name carries a trailing part number that the title lacks is accepted.
    - Live: `James S. A. Corey\5. Игры Немезиды\5. Игры Немезиды 1.m4b` (16.2 h, no catalogued sibling) is approvable. Its neighbour `4. Пожар Сиболы` is split 1/2. This one needs a human look before the first pass.
    - Chapter-like titles also pass: a lone "Глава 01" is accepted. Numeric-only chapter titles ("01" beside "02") bypass the sibling check, because `title_key(…, True)` only strips a number that follows a separator.
  - **[Major] M2 — the cross-script key ignores vowels.** Location: `local_identity.py:42-50`, `:141-150`.
    - Different names with the same consonants agree: Кинг ≈ "Kong", Семёнова ≈ "Simonova", "Анна Петрова" ≈ "Nina Petrova", Акунин ≈ "Brs Kn".
    - The "≥3-letter key" strength test does not help, because the skeleton holds only consonants.
  - **[Major] M5 — anthology components bypass collection handling.** The local work sets `work_type: ''` and `contained_story: False` (`public_research.py:742`).
    - Items in `Сборники\` and the WH40K anthology folder become standalone books, which skips `_collection_lookup`.
    - Example: "неSplatterpunk stories 2" and "ТЁМНЫЕ АЛЛЕИ 2.1" are credited to the narrators Князев and Булдаков.
    - These are locally consistent, so the rule accepts them. This needs a Sergei call, not a code guess.
  - **[Minor]** `local_identity.py:472-474`: a structured-name contradiction is dropped whenever another component supports the field. In the copy these were all benign series folders, but it contradicts the rule that contradictions hold.
  - **[Minor]** The album tag always wins over the title tag. Example: "Трофики [Пожилой Ксеноморф] 64" becomes the title "Трофики 64" (64 is likely a bitrate), while the title tag says "Трофики".

### 3. Crash / Stability Safety

- Status: Pass
- Findings:
  - **No tight loop.** Each gap deferral needs a full queue drain before the next pass. `ResearchWait.retry_at` is always more than `now`+5 s. Deferral is bounded at 3. Retry backoff still applies.
  - **[Minor]** `merge_service.py:474-475` converts only `sqlite3.Error` from `folder_siblings` into a hold. Any other exception escapes as a run failure (Needs attention) rather than a per-book hold.

### 4. Performance

- Status: Concerns
- Findings:
  - **[Major] M3 — cache cost on the shared catalog database.** Location: `public_research.py:339-342`.
    - The eviction runs `SUM(length(raw)) OVER …` on every fetched response, inside `BEGIN IMMEDIATE`. `length()` on a TEXT column reads every value.
    - Measured on a scratch table of 5,000 × 13 KB (68 MB): **0.47–0.63 s per insert** while holding the write lock.
    - The existing 7-day purge (`:282`, no index on `fetched`, which is stored after `raw`) now costs about 60 ms on every `read()`, cache hits included.
    - Suggested fix: store a byte-size column, index `fetched`, and evict in batches.

### 5. State & Data Safety

- Status: Fail
- Findings:
  - C1–C3 reach source retirement through the unchanged, correct pipeline. The defect is in the identity gate in front of it, not in retirement or recovery.
  - **Admission recheck is sound.**
    - `revalidate` runs inside the review and group locks, against the fingerprint-checked current row and freshly queried siblings.
    - A catalog read error becomes a hold.
    - Tags are re-probed before encoding.
  - It inherits C3: `revalidate` calls the same `folder_siblings`.

### 6. Input Handling

- Status: Concerns
- Findings:
  - Catalog JSON is type-checked, and `_full_name` and `_gap_fantlab` require a unique title and author match.
  - **[Minor]** No NFC normalisation. The catalog contains NFD text (U+0306 combining breve seen in paths). `words()` splits й into "и" plus a fragment, and `norm` turns й into и. This mostly fails closed (missed agreements).
  - **[Minor]** `_latin_keys` caps variants with `list(variants)[:16]`. Set order changes with hash randomisation, so names with more than 16 spelling variants match nondeterministically between processes. Use `sorted(…)[:16]`.
  - **[Minor]** `CHALLENGE_MARKERS` (`public_research.py:309`) now pauses any host for 1 h when a response body contains a marker string (previously 5 min). A catalog record that quotes one of the strings would pause that catalog.
  - **DuckDuckGo:** HTTP 202 and the challenge page are a 1-hour pause with no bypass. Correct.

### 7. Maintainability (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **[Major] M4 — tests do not cover the production default.**
    - The legacy research-path test classes now patch `local_agreement=False`. Their hold assertions therefore no longer describe the default behaviour.
    - No test covers narrator markers, -ич surnames, root-level siblings or disc-folder splits.
    - Run those classes with local agreement on and list which holds flip.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **[Minor]** The handoff (`Docs/BooksArranger_FastIdentity_v0.14.0_2026-10-13.md`) calls the candidate "uncommitted" and says the worktree lacks the standing-rule section. Both are stale: 67e3d43 is committed, and e68597a adds the section.
  - **[Minor]** The CHANGELOG says pacing "follows published vendor limits (… Google Books)". The code comment admits Google publishes no anonymous number. The 40/h value is a courtesy cap below the default, not a published limit.

### 9. Build & Release Hygiene

- Status: Pass
- Findings:
  - `VERSION` goes from 0.13.1 to 0.14.0.
  - The CHANGELOG has a v0.14.0 entry.
  - `RESEARCH_VERSION` is bumped so every waiting or held book gets one fresh pass.
  - Pacing is raised only for Open Library (published 1 req/s; 1.1 s spacing) and iTunes (published ~20/min; 3.5 s).
  - No lockfile applies (Python). No secrets are in the diff.

---

## Verdict

- Total Critical: 3
- Total Major: 5
- Total Minor: 8

**Verdict:** RELEASE BLOCKED

| # | Sev | Dim | file:line | Finding | Must fix before release |
|---|-----|-----|-----------|---------|--------------------------|
| C1 | Critical | 2 Correctness | `local_identity.py:308` (`_embedded`), `:359` (`_supports_author`) | Narrator credits ("читает X") become the author. 5 live approvable books in `АНТОЛОГИЯ РУССКОЙ МИСТИКИ`. | (1) Treat any credit or path author piece containing a narrator marker (читает, читают, чит., исполняет, исп., озвучил/а, read by, narrated by, narrator, reader) as a recording credit, never an author. (2) If an author or artist tag is a `NOT_PEOPLE` collection credit, do not fall through to another credit: no local acceptance (research path). Add the 5 live rows as test fixtures and confirm they are held. |
| C2 | Critical | 2 Correctness | `local_identity.py:52`, `:130-138`, `:321` | -ович/-евич/-ич surnames are dropped as patronymics, so different people match on the given name. A narrator can become the author. | (1) Drop a patronymic token only when the name has 3 or more words and at least 2 other non-initial words remain. (2) In `_embedded`, merge two credits only on a full, non-subset match with no dropped tokens. Add tests for Костюкевич/Хазанович and Гжендович/Хорошков (artist plus album_artist). |
| C3 | Critical | 2 Correctness / 5 Data | `local_identity.py:386-408` (`folder_siblings`), `:251-261` | The split guard fails open. (a) At the root, LIMIT 2000 over the subtree shows only 1 of 44 root files. (b) Disc and part folders are checked one at a time. | (1) Select direct children exactly, with no LIMIT. Or, if a cap is kept, return `unreadable` (fail closed) when it is hit or when more than 20 folders exist. (2) When the candidate's folder matches `DISC`, or its folder or file name carries a part marker the title lacks, include the sibling disc and part folders under the parent in the sibling set. Add tests for the root-level "(Часть 1)/(Часть 2)" pair and for `CD1/CD2`. |

---

## Round 2 — a7d9b42

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-13
Fix round: 67e3d43..a7d9b42 (17 files, +1591 / -301)
Full range re-confirmed: v0.13.1..a7d9b42 (22 files, +2748 / -41)
```

### Method

The review was red-team and read-only. I made a scratch copy of the evidence catalog and reran Ender's `evidence/measure.py` against a7d9b42. The result matches Ender's `fix2/measure-after-v3.json` exactly: 445 approvable, 67 of them routed to `Сборники`, and 479 that agree locally. I ran pure-function probes on synthetic rows. I queried the copy with `mode=ro&immutable=1`. I did not run the app, read the live database, use the network or touch Z:/Y:.

### Round 1 findings, rechecked

**C1 — narrator taken as author: fixed.**
- No approvable author carries a reader marker, and none matches a catalog reader.
- The 5 `АНТОЛОГИЯ РУССКОЙ МИСТИКИ` books now route as collections, with the narrator recorded only as narrator.

**C2 — -ич surnames dropped: fixed.**
- These pairs no longer match: Гжендович/Хорошков, Костюкевич/Хазанович and Abramovich/Polanski.
- `_embedded` merges two credits only through `same_person`.

**C3 — split-part guard: fixed for both layouts.**
- `folder_siblings` uses the `(root,path)` primary-key range. The query plan is `SEARCH … COVERING INDEX`, with no LIMIT.
- For a root-level candidate it returns 43 of 43 siblings in 0.03–0.09 s.
- `catalog_index` takes 1.1 s once, then 0.002 s while cached. The cache is keyed to the trigger-maintained `book_catalog_revision`.
- With no root, more than 20 folders, or a read error, the guard fails closed. Both callers turn any exception into a hold (`merge_service.py:474-479`, `_siblings`).
- Disc and part sibling folders are now included.

**M2, M3 and M4 are fixed:**
- **M2:** vowels now count in cross-script matching. Kong, Simonova, "Brs Kn" and Хокинг/King no longer match.
- **M3:** eviction now goes through the small side-index table, and expiry is an indexed delete.
- **M4:** the legacy tests run under the default rule. The final suite failure set equals the baseline (543 run, the same 9 environment errors).

**M1 — lone numbered part: still open on the live file. [Major]**
- `James S. A. Corey\5. Игры Немезиды\5. Игры Немезиды 1.m4b` is approvable in both my run and Ender's v3 run.
- `PART_TITLE` (`local_identity.py:879`) checks only the title tag. Here the tag says "Игры Немезиды", and only the file name carries the trailing " 1".
- `test_m_lone_numbered_part_or_chapter_is_held` uses `album='Игры Немезиды 1'`, which is not the live tag. The handoff's claim that this file is held is wrong.
- Fix: apply the part check to the file stem when the stem minus a trailing number equals the title.

**M5 — anthologies: addressed through ruling 1.** That route is reviewed below.

### New findings

#### R2-1 [Critical] — the ruling-1 route files real single-author books as "Разные авторы"

Location: `local_identity.py:957-976`, `public_research.py:742`.

The route needs two signals, and the "collection credit" and "credited person is the reader" signals count even when a real person credit is still present. The person is then dropped, and the book is published as `Сборники\<title>` under "Разные авторы". Synthetic probes on `agreement()`:

1. **A "Сборник" tag overrides an author the tags and folder agree on.**
   - Setup: artist "Стивен Кинг", album_artist "Сборник", folder `Сборники\Стивен Кинг - Ночная смена\`.
   - Result: the route fires, although tags and folder agree on King.
   - The variant with author="Сборник" and a collection title also routes.
2. **An author who reads their own books becomes a narrator.**
   - Setup: artist "Дмитрий Глуховский" (catalog-wide a reader of his own books), album "Рассказы о Родине".
   - Result: routed. Глуховский is recorded only as narrator, and the credit becomes "Разные авторы".
   - Here the catalog-reader hold at `:875-876` is meant to send the book to research, but `reader_credit` at `:958` turns it into a route signal instead.
3. **An author not named in the path is dropped.**
   - Setup: under `Сборники\`, artist "Стивен Кинг", album_artist "читает Игорь Князев", author not named in the path.
   - Result: routed, narrator Князев, King discarded.

Scope:
- **Live: 0.** All 67 routed books in the copy carry only collection or reader credits; I checked each one.
- **Why it still blocks:** this is a wrong-author path to publication and retirement, by the same bar as round-1 C2 and C3. It also contradicts the intent stated for the fix ("collections *with no author credit*") and ruling 1, which concerns narrator-compiled collections, not single-author books.

#### R2-2 [Critical] — conflicting initials agree, and the canonical-spelling merge unifies different people

Location: `local_identity.py:309-319` and `:335-337` (`compare_names`), `:744-746` (`canonical_author.same`).

Initials on one side are compared only against the extra full words on the other side. Initials present on both sides are never compared with each other, so "А. Стругацкий" = "Б. Стругацкий" (a non-subset match).

1. **Agreement.**
   - Tag "Стругацкий А." with folder and file name "Стругацкий Б." is **accepted**: green, author "Стругацкий А.". "Robert J. Sawyer" against "Robert K. Sawyer" is also accepted.
   - That is a local contradiction treated as agreement.
2. **Ruling-3 canonical spelling.**
   - `same()` accepts any non-subset match, so the most common spelling wins across different people:
     - "Толстой А.Н." becomes "Толстой Л.Н." (Leo Tolstoy) when the library has Л.Н. 12× vs А.Н. 2×;
     - "А. Стругацкий" becomes "Стругацкий Б.";
     - "Robert J. Sawyer" becomes "Sawyer Robert K.";
     - "Иванов А." becomes whichever of Иванов Андрей / Алексей is more common.
   - The canonical name becomes the author folder of the published book.

Scope:
- **Live: 0** conflicting-initial groups among the 837 catalog spellings, and 0 among the 378 author approvals.
- Two Tolstoys written with initials is ordinary in a Russian library.

### Other findings

- **[Major] Silent fail-open when the root string does not match.** `folder_siblings` returns an empty list, not "unreadable", when no row matches the root string. With a trailing `\` or a lowercase root it returned 0 siblings.
  - Production passes the same `inventory.roots` string the scanner stores, so nothing triggers this today.
  - Fix: fail closed when the candidate's own paths are not found by the range query.
- **[Minor]** With the original language unknown, ruling 3 picks the English spelling whenever a Latin folder exists (`local_identity.py:769-770`). For a Russian original that would contradict "Russian name for Russian originals". No live case: every Latin result in the copy is a foreign author.
- **[Minor]** Ruling 3 faithfully adopts misspelled folder names as canonical: "Pratchet Terry", "Zahn Thimoty". This is Sergei's rule working as written, so I list it as information only.
- **[Minor] Doc drift:** the handoff's M1 row says the live "Игры Немезиды 1" is held. It is not (see M1).

**Unchanged and confirmed across v0.13.1..a7d9b42:**
- Retirement, recovery, media, publication and web modules are untouched (`source_cleanup`, `recovery_retention`, `replacement_retirement`, `audio_jobs`, `native_io`, `audio_pipeline`, `web_server`).
- `VERSION` is 0.14.0.
- The evidence and SQL handling from round 1 still pass.

### Round 2 verdict

- Open Critical: 2 (R2-1, R2-2). Round-1 C1–C3 are closed.
- Open Major: 2 (M1 live file, fail-open on root mismatch).
- Open Minor: 3.

| # | Sev | file:line | Must fix before release |
|---|-----|-----------|--------------------------|
| R2-1 | Critical | `local_identity.py:957-976` | Route to `Сборники` only when no person credit remains after reader and collection credits are removed (`embedded['people']` empty, and no uncorroborated author tag). Never count the catalog-wide "reads other books" conflict (`:875-876`) as a route signal; that stays a research hold. Add tests for the three probes above (King plus a "Сборник" tag; Глуховский self-reader; King plus "читает Князев" under `Сборники`). |
| R2-2 | Critical | `local_identity.py:309-337`, `:744-746` | Initials present on both sides must pair one-to-one with matching letters, otherwise no match. In `canonical_author`, count only spellings that are `same_person` with the agreed name, and never expand an initial to a full given name when the library holds more than one distinct given name for that surname and initial. Add tests: А./Б. Стругацкий, Толстой А.Н./Л.Н., J./K. Sawyer, Иванов А. with two Ивановs. |

**Verdict:** RELEASE BLOCKED — a7d9b42
