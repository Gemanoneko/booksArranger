# Code Review — Books Arranger v0.15.0

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-13
Tool: Books Arranger
Release: v0.15.0
Commit range: v0.14.0 (f00b940)..3346da12ccb512acd44bd120afea5af28b603da7
              branch codex/books-split-books-0.15.0; includes docs-only main commits 8894fb6, 2072cf1, 904da7f
Files changed: 18 files, +1576 / -30 (code: 9 files, +655 / -29; tests: 1 new file)
Stand-down dimensions: none
```

---

## Summary

v0.15.0 adds split books. The new module `split_books.py` groups single-file candidates (chapter M4Bs, "Title 1/2" part sets, CD folders) into one candidate that becomes one M4B. The v4 normalizer now joins M4B parts. The release also adds a library-wide confirmed-spelling list (Pratchett), the middle-initial rule (Dick), the Булдаков ruling-1 exception, and the year-number sibling rule. The automatic run now adds new candidates while it runs.

The review was red-team and read-only.
- I read the full diff and the touched admission, gate, grouping, pipeline and run code.
- The worktree gained uncommitted edits in 8 files while I worked (Sergei's chaptered-parts decision, tests). This review does not cover them. I re-ran every probe on a `git archive` export of 3346da1.
- I probed the pure functions with adversarial inputs and ran `split_books.plan` on a scratch copy of Ender's catalog copy, opened `mode=ro&immutable=1`.
- I read Ender's `m-after-final.json`.
- `test_split_books.py` on the export: 38 run, 37 pass. The 1 error is the known path-length environment error: my export path is 144 characters, the baseline path is 100.
- No app, port 5210, live database, Z:/Y: or network.

**Result.** The grouping check ignores evidence that it documents as a hold. Title tags are read only when every part has one. Three separate novels tagged the way this library already tags a real trilogy are joined into one M4B, and their originals are retired. Release blocked.

Confirmed sound:
- **Media.** Copy mode is reachable only for exactly one M4B (`choose_automatic_encoding(single_m4b=len(copies)==1)`). Several M4Bs always go through the normalizer. That path checks:
  - the decoded duration of each part (more than 0.1 s difference is refused);
  - every output check, as before;
  - parts with more than one chapter, on the protected snapshot (`audio_pipeline.py:205`) and at admission (`merge_service.py:505`);
  - audio profiles, which must match at grouping time and again at admission (`:509`).
- **Untouched modules.** Publication, retirement, recovery, `native_io` and web code are not in the diff. Retirement is still limited to the frozen manifest's sha256-verified sources.
- **Membership between research and admission.** At admission, `_row` → `inventory.candidate()` re-syncs grouping inside the locks. If the parts changed, the group gets a new revision ("Candidate changed") or is superseded ("no longer current").
- **Live grouping.** All 173 live groups look correct by inspection. The 17 named "part" labels are all real "Часть N. Name" parts (Оно, Мерзость, Красные цепи, Wolves of the Calla).

---

## Rubric

### 1. Security

- Status: Pass. No new shell-outs. The `confirmed_spellings` SQL is constant, from a fixed table map, read-only (`mode=ro`, `query_only`). No secrets.

### 2. Correctness & Logic

- Status: Fail
- Findings:
  - **[Critical] C1 — title tags are checked only when every part has one.** Location: `split_books.py:253`, `if all(titles) and …`.
    - One part without a title switches off the "own title / volume number" hold for the whole set.
    - **Live anchor:** `Suzanne Collins\Suzanne Collins\` holds the three Hunger Games novels:
      - album "The Hungar games" on all three;
      - track 1/3, 2/3, 3/3;
      - a title tag on one file only: "Book 2 Cathing Fire".
    - Today only the "Book N" in the file names holds it, plus a sample-rate difference on book 3.
    - **Probe** with these real tags, names "The Hunger Games 1..3.m4b" and equal rates:
      - grouped, locally accepted as "The Hungar games" / Suzanne Collins, gate `[]`;
      - three novels become one M4B and their originals are retired.
    - Tim Miller "Тёмный экзорцист 1/2" (titles "…Том I" / "…Том II") is held only by its title tags. Remove one and it is grouped and accepted.
    - Cost of the fix: 0 of the 173 live groups have partial titles (checked).
  - **[Major] M1 — albums are compared without their bracketed text, and volume words in albums are never checked.**
    - Locations: `book_key` → `title_key` → `clean_title` strips `(…)` and `[…]` (`split_books.py:101`); `SAME_TAGS` has no album (`:54`); the volume check reads only names and titles.
    - Probe: albums "The Hunger Games (Book 1/2/3)" with names "The Hunger Games 1..3" are grouped, accepted, gate `[]`.
    - Albums "Пикник на обочине (Кузнецов)" / "(Козий)", two recordings, are also grouped.
    - The gate waives album disagreement when the folder names the book (`source_identity.py:132`).
    - The group does record "Different book album/title clues may indicate mixed works", but the automatic path never reads group conflicts.
    - Live: 1 bracketed-number album in the whole catalog; 0 live clusters with differing raw albums.
  - **[Major] M2 — a marker word plus a number turns any following name into a chapter.** Location: `split_books.py:174`.
    - "Эпизод 1. Скрытая угроза" / "Эпизод 2. Атака клонов", "CD1 Хоббит" / "CD2 Властелин колец" and "Track 1 - <novel>" all label as `part`.
    - Suggested fix: allow a name after часть/глава/chapter/part only; hold episode/track/cd/disc/section followed by a name.
    - Live: all 17 named parts are "Часть N. …", so the fix costs 0.
  - **[Major] M3 — bare numbers are treated as parts (a design residual; Sergei call).**
    - "Series 1..N.m4b" files with album = series, track n/N and no title tags are one book: "Ведьмак 1..3" is grouped and accepted.
    - Locally this cannot be told apart from "Террор 1..4".
    - This library does tag whole series as one album: Hunger Games, Elric, Sword Art Online, Toradora. Today all of them are held by names or titles only.
    - The same residual covers two questions in the brief:
      - **A missing last part.** Without track totals it is invisible. "Лавка дурных снов 1..3" has no totals. This is the same as MP3 folders.
      - **Abridged plus unabridged named as parts.** Such a pair is held only when tags or the audio profile differ.
  - **[Major] M4 — the Булдаков exception widens the ruling-1 route to single-author collections whose folder names the author.** Location: `local_identity.py:1056-1065`, `:1189-1197`.
    - Under any collection-folder ancestor, a plain "Олег Булдаков" credit is now dropped, and the book routes to `Сборники` as "Разные авторы".
    - The author named in the folder or parent folder is not consulted.
    - Probes that route and drop the author:
      - `Ходжсон Уильям Хоуп - Карнакки … (сборник) [Олег Булдаков]\` (the bracketed reader does not trigger R3-1);
      - `Ярослав Гжендович — Книга осенних демонов (сборник)\`;
      - `Stephen King\Сборники\Ночная смена.m4b`.
    - v0.14.0 held the same input ("folder credits a different person").
    - Live:
      - 0 wrong routes today;
      - 162 files in 15 folders carry a plain Булдаков author-tag credit, mostly single-author books ("Кларк Саймон – Чужак [Олег Булдаков]");
      - the library already uses "Author — Title (сборник)" folders (Гжендович, Маклин).
    - Rulings 1 and 5, read literally, allow this. R2-1's principle ("a real author is never dropped") does not. That makes it a product question, not a Critical.
    - Suggested fix: hold for research when a folder or file name names a person who is not a library reader. Of the 69 live routes, the only person names in the paths are the readers Головин and Булдаков.
    - Related, pre-existing since v0.14.0 and not counted: `Сборники\Пять Вечеров\Пять вечеров. Кир Булычёв.m4b` (title "Пять вечеров: Кир Булычёв") is approvable as "Разные авторы".
  - **[Major] M5 — the confirmed-spelling list trusts research that failed verification.** Location: `local_identity.py:841-889`, used at `:966`.
    - Most of the 12 confirmed spellings come from "Waiting for source" results whose reasons include "Author and work not independently verified":
      - all 3 Pratchett confirmations;
      - "Anatole France" (from a search for "Словарь");
      - "М. С. Парфёнов", the anthology compiler.
    - `slip_same` then adopts such a spelling library-wide.
    - Today it is precise: all 8 slip pairs in the live spellings are genuine typos (Pratchet, Gayman, Аякудзи, Глуховской, Стейплз, Расселл).
    - The remaining risk is two real people with the same first name and a one-letter surname difference (Lawrence/Laurence, Connolly/Connelly).
    - Suggested fix: confirm only from verified records (queued or completed jobs, saved reviews). For a slip, also require that the confirming record's own local author was that slip spelling.
  - **[Major] M6 — the year rule also exempts zero-padded part numbers.** Location: `local_identity.py:1116`.
    - A single file "Дорога 0001" (album "Дорога 0001") beside "Дорога 0002" is accepted as the whole book. v0.14.0 held it.
    - The albums carry the number, so the two files never form a split book either.
    - Suggested fix: limit the rule to `1[5-9]\d\d|20\d\d`.
    - Live: 0 (the "0001…" files in the catalog are bare numbers, which `PART_TITLE` holds).
  - **[Minor]** `middle_initial_same` ignores word positions.
    - "Mary K. Smith" = "Kate Mary Smith" and "M. Mary Smith" = "Margaret Mary Smith" are both true. In those pairs the initial stands for the other side's first name.
    - The R2-2 shapes are unaffected: А./Б. Стругацкий, Толстой А.Н./Л.Н., J./K. Sawyer and Иванов А. still stay apart. The only live merge is Dick.
  - **[Minor]** Protected split books are re-proven without `others`, both in `groups.py:210` and in the gate (`source_identity.py:93`).
    - A same-title file that arrives after a book was reviewed or approved is not seen there.
    - For local-agreement books, the sibling check at admission still covers it.

### 3. Crash / Stability Safety

- Status: Concerns
- Findings:
  - **[Major] M7 — sync crashes with a KeyError when scopes collide.** Location: `groups.py:108` (`split[row['path']]`).
    - Trigger: a protected split book's members are retagged, so their book key changes, and new files with the old title appear in the same folder.
    - The new plan reuses the protected scope string, and the bucket then mixes both sets.
    - Reproduced with the "Террор" probe.
    - `groups.sync` raises, so every candidate listing and admission fails until the catalog changes.
    - The trigger is contrived, but the failure is total.

### 4. Performance

- Status: Pass. Measured:
  - `confirmed_spellings`: 0.08 s uncached, 0.03 s cached;
  - full regroup: 3.0–3.3 s, against 2.7 s before (Ender's figures).

### 5. State & Data Safety

- Status: Fail
- Findings:
  - C1 reaches publication and retirement through the unchanged pipeline. The originals of separate books are retired into one joined M4B, with 24-hour recovery only. M1–M3 are the same class at lower likelihood. M4–M6 are the wrong-author and part-as-whole classes.
  - Retirement scope, hashing, recovery and the admission re-sync are sound (see Summary).

### 6. Input Handling

- Status: Concerns
- Findings:
  - **[Minor]** `_legacy_build` falls back to the literal title "split" when a group's album tags differ (`groups.py:157`, scope `'split'`). That title clue then reaches research (M1 probes).
  - **[Minor]** The stored catalog probe has no chapter data: 0 of the 3,817 M4B/M4A rows carry any. The chapter hold therefore exists only at admission, which is correct but invisible offline.

### 7. Maintainability (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **[Minor]** No test covers:
    - partial title tags;
    - bracket-only album differences or volume words inside albums;
    - episode/track/CD markers followed by a name;
    - a Булдаков credit with a folder-named author;
    - a zero-padded part number;
    - the scope collision.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **[Minor]** The handoff has three stale or loose claims:
    - it says "All changes are uncommitted", but 3346da1 is committed;
    - it says "935 grouped … 228 files in 92 books", while `m-after-final.json` gives 940 and 233;
    - "Open Library confirms Terry Pratchett" rests on unverified results (M5).
  - **[Minor]** The CHANGELOG says "An initial still never stands for a first name". The `middle_initial_same` Minor shows two pairs where it does. "81 approvable" split books counts books before the admission-time chapter hold, so the number that actually converts is unknown offline.

### 9. Build & Release Hygiene

- Status: Pass
  - `VERSION` is 0.15.0 and the CHANGELOG has a v0.15.0 entry.
  - `RESEARCH_VERSION` is standing-19-v1. `AGREEMENT_VERSION` is v4, and v3 records still validate.
  - `GROUP_VERSION` forces one resync.
  - No lockfile applies (Python). No secrets.

---

## Patterns

This is the same pattern as v0.14.0's C3 and R2-1: a guard that sees only part of the evidence it already holds. Here, the title tags of some parts, and the album text inside brackets. The other recurring pattern is a narrow exception (Булдаков) that bypasses a rule written for tag credits, while the path still names the real author.

---

## Verdict

- Total Critical: 1
- Total Major: 7
- Total Minor: 7

| # | Sev | Dim | file:line | Finding | Must fix before release |
|---|-----|-----|-----------|---------|--------------------------|
| C1 | Critical | 2 Correctness / 5 Data | `split_books.py:251-264` | Title tags are ignored unless every part has one. Separate novels of a series (live Hunger Games tagging; Tim Miller "Том I/II") can be joined into one M4B and their originals retired. | Label every title tag that exists against the album/book name; a distinct title or volume word on any part holds. Add tests: the Hunger Games tags (one title "Book 2 Cathing Fire") with names "The Hunger Games 1..3" must hold; Tim Miller with one title missing must hold. Costs 0 of 173 live groups. Recommended in the same pass (Major): M1 (exact album equality plus a volume check on albums) and M2. |

**Verdict:** RELEASE BLOCKED — 3346da1
