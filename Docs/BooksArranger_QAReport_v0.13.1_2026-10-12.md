# Books Arranger v0.13.1 QA — 2026-10-12

Author: Futaba. Candidate: branch `codex/books-release-0.13.1`, exact commit `fcf0b4991761770ddd7b407cf6786b5683f32c9a` (pushed; `git ls-remote origin` agrees). Base: tag `v0.13.0` = `b5c5937f458cad1c8f3b10ee8c71633381e79023`.

All evidence below was produced by Futaba from her own fresh clones of `https://github.com/Gemanoneko/booksArranger.git`. No Ender receipt, fixture or result was used as proof (Ender's failure-set list was read afterwards only to compare names). Not touched: the running app / port 5210, the live install checkout, Z:/Y:, admission requests. No commit, push, tag or stash.

Environment: Windows 11, Git for Windows 2.56.0, `core.autocrlf=true` from the **system** gitconfig only (`C:/Program Files/Git/etc/gitconfig`; no global or local override), Python 3.14.8. Clone paths were 148 characters long (matters for item 3).

Summary: GO for v0.13.1 at fcf0b49, conditional on the application step in F1; no defect found in the build itself. The machine-readable verdict line is the last line of this file.

## Result per check

| # | Check | Result |
|---|---|---|
| 1 | Fresh clone of the pushed branch, default git settings | PASS. HEAD `fcf0b49…`, `VERSION` = `0.13.1`. Plan raw sha256 `db493dbbfa691e1fe6b875a3edacb8ebd318d487c80c9fa4de66639afa35d20f`, 16251 bytes, 0 CRLF / 479 LF. `git ls-files --eol`: `i/lf w/lf attr/text eol=lf`. `git status --porcelain`: clean. |
| 2 | Positive control on v0.13.0 | PASS. Fresh clone of `v0.13.0`, same settings: plan CRLF, sha256 `42da5fc0057b3a6a292d050360dc0f2c9ed439b680aca59a1ea17b9cb4a3a811`, 16730 bytes, 479 CRLF (`i/lf w/crlf attr/`). New test file copied in (byte-identical, sha256 `946eb824…`): `test_checked_out_plan_passes_real_admission_guard` **FAILED** (`'rejected' != 'accepted'`, message names the CRLF sha and count), `test_gitattributes_pins_plan_to_lf` **ERRORED** (no `.gitattributes`), `test_guard_rejects_crlf_copy_of_plan` passed (it is the sensitivity control and should pass). In the fcf0b49 clone: 3 of 3 **PASS**. |
| 3 | Full suite on fcf0b49 | PASS, no new failures (details below). |
| 4 | Edited plan still rejected | PASS (details below). |
| 5 | No other product file differs | PASS (details below). |

### 3. Full suite — `python -m unittest discover -s tests -p "test_*.py"`
- fcf0b49 run 1: 490 tests, 3 failures + 17 errors = 20. Run 2: 490 tests, 2 failures + 17 errors = **19**.
- **Same-condition control:** v0.13.0 clone at the same path length (without the new test): 487 tests, **19**. The failure set of fcf0b49 run 2 is **byte-identical** to the v0.13.0 set (`diff` empty). The 3 new tests are among the 490 and none of them is in the failure list.
- The one difference in run 1 was `test_waiting_uses_earliest_candidate_and_does_not_revisit_later_source_early` (`[100005.0, 100020.0, None] != [100005, 100020]`). It is intermittent and **not caused by 0.13.1**: it passed 5 of 5 isolated reruns on fcf0b49, passed in run 2, and **failed 1 of 5 isolated reruns on the v0.13.0 clone**.
- The stated baseline is 10 pre-existing errors; I measure 19 on **both** trees. All 10 stated names are in my 19. The 9 extras are explained by my longer clone path (148 characters), by error text, not re-measured at a shorter path:
  - 6 raise `ValueError: Verified metadata exceeds the supported Windows output path length`: `test_confident_no_manual_form…`, `test_custom_source_cover…`, `test_independent_catalog…`, `test_queue_insert_failure…`, `test_existing_m4b…`, `test_unknown_staging_audio…`
  - 3 see an empty proposal path from the same guard: `test_destination_collision…` (`PermissionError: '.'`), `test_confirmed_standalone_and_series_collections` and `test_single_author_and_multi_author_novels…` (`'' != '<path>.m4b'`)
- The baseline 10 reproduce for the stated reasons: missing untracked `scratch/source-fallback-2026-10-11` and `baseline_native_io.py` (FileNotFoundError), path length, and `test_protected_cover…`: `'BrowserServer' object has no attribute 'loaded_version'`.

### 4. Edited plan rejected (own probe, outside the repo)
`guard_probe.py` calls the clone's real `MergeService.replace_audiobook` with a stub that raises on the first touch of service state, i.e. strictly after the guard.
- v0.13.0 CRLF plan (`42da5fc0`): **REJECTED** `Approved replacement media plan changed` (probe sensitivity control).
- fcf0b49 pristine (`db493dbb`): **ACCEPTED** (stub reached `reviews`, the first post-guard statement).
- fcf0b49 with one value changed in place, `chapter_readback_tolerance_ms` 1 to 2, LF kept, same size (sha256 `929299a9…`): **REJECTED**. `git status` shows ` M replacement_eye_plan.json`.
- Restored with `rm` + `git restore --worktree --`: back to `db493dbb`, status clean, **ACCEPTED**.

### 5. `git diff --stat v0.13.0 fcf0b49`
Six files, +183/−2: `.gitattributes` (new, `replacement_eye_plan.json text eol=lf`, blob sha256 `b68aa072…`), `CHANGELOG.md`, `VERSION`, `tests/test_replacement_plan_bytes.py` (new), `Docs/BooksArranger_LineEndingFix_v0.13.1_2026-10-12.md` (new), `Docs/BooksArranger_StorageCleanup_ActualReview_2026-10-12.md` (+7/−1). **No product source file differs**; `merge_service.py` and every other `.py`/`.js`/`.html`/`.json` are identical to v0.13.0. No stale `0.13.0` string outside `Docs/` and `CHANGELOG.md`.

## Extra check outside the five: in-place upgrade (what the live install will experience)
In the v0.13.0 clone I moved to fcf0b49 with `git checkout` (the plan blob is unchanged, so git leaves the file alone):
- plan stays **CRLF `42da5fc0`**, `git ls-files --eol` shows `w/crlf attr/text eol=lf`, **`git status --porcelain` prints nothing**, and the guard **REJECTS** it.
- the new test fails there (1 failure of 3), as designed.
- the doc's recipe (`rm -- replacement_eye_plan.json`, then `git restore --worktree -- replacement_eye_plan.json`) produced `db493dbb`, `w/lf`, clean status, guard **ACCEPTS**, new test 3 of 3 pass.

## Findings

| ID | Severity | Status | Finding |
|---|---|---|---|
| F1 | Major (application risk; not a defect in fcf0b49) | Open, owner Sully/Jane | Applying 0.13.1 to an already-checked-out install does **not** fix the plan: it stays CRLF and `git status` is silent, so the original HTTP 400 would recur. The `rm` + `git restore --worktree` step in the handoff doc works (measured above). It must be in Sully's apply checklist, followed by a **raw** `sha256sum` = `db493dbb…35d20f` (not a CRLF-normalised compare). `tests/test_replacement_plan_bytes.py` run in the install root is the confirmation. I did not touch the live install, so its current state is unverified by me. |
| F2 | Minor (doc drift) | Open, owner Ender | The handoff doc says the branch "is based on `b5c5937`", main is "a later" commit, and the test is "uncommitted". In fact: fcf0b49 = `b662709` (fix) + test commit, and the branch also contains docs-only `4cd7c9e` between v0.13.0 and the fix. `origin/main` is `4cd7c9e`, so the branch is a plain fast-forward of main. |
| F3 | Minor (pre-existing) | Accept / defer | Suite baseline depends on clone path length (10 on Ender's path, 19 on mine, identical on v0.13.0) and on untracked fixtures. Future QA should record the path length with the failure count. |
| F4 | Minor (pre-existing flake) | Defer | `test_waiting_uses_earliest_candidate…` is timing-sensitive, fails intermittently on v0.13.0 too. |

Info: with `core.autocrlf=true` the worktree copy of `.gitattributes` itself is CRLF (worktree sha `14c39f59…`, blob `b68aa072…`). Git and the new test both read it correctly (`git check-attr`: `text: set`, `eol: lf`), so it is harmless.

Pattern alerts: none.

## Not run / limits
- NOT RUN: `qa-handoff` entry-check script. It is not in the brief and needs a reviewed per-tool context; this report's receipt is fcf0b49 plus the clone evidence above.
- NOT RUN: the app, HTTP-level admission replay (Ender's replay through `web_server.Handler` was not re-verified; my check 4 exercises the real guard function directly), a real admission, and any machine with `core.autocrlf` other than `true`.
- Verified only on this one Windows/Git 2.56 machine with the default system config.

## Cleanup
NOT DONE: the clones were **not** removed. The studio cleanup planner (`studio-disk-hygiene`, plan mode) refused the task root: `Protected path: …/scratchpad/futaba-0131/fx/.git`. The skill forbids renaming paths or weakening checks, and the studio deny list blocks recursive `rm`, so nothing was deleted and no manifest was written. Remaining, all mine, in `C:\Users\<user>\AppData\Local\Temp\claude\c--Antigravity-Projects-Studio-Illuminati\2b7de6b0-ce4b-4a27-9134-6e4452d270f4\scratchpad\futaba-0131`:
- `fx/` (fcf0b49 clone, 6.2 MB, clean) and `base/` (v0.13.0 clone moved to fcf0b49 for the upgrade check, 6.2 MB, clean).
- Evidence kept: `suite-fx-run1.txt`, `suite-fx-run2.txt`, `suite-base-run1.txt`, `failset-*.txt` and `guard_probe.py`.

Jane: pick a removal method for the two clones (the `.git` folders are what the planner refuses). Other folders in the same scratchpad (`senua-0131`, `v4-work-*`, `hygiene-*.json`) are not mine and were not touched.

**Verdict:** GO — Books Arranger v0.13.1 / commit fcf0b49
