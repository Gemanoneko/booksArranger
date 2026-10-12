# Books Arranger v0.13.1 — line-ending fix: handoff for Futaba and Senua (2026-10-12)

Author: Ender. Status: uncommitted in worktree `scratch/eye-of-god-2026-10-12/metadata/release-staging-0.13.1` (branch `codex/books-release-0.13.1`, HEAD `b5c5937`). Sully commits.

## Cause: confirmed
The real Eye of God admission returned HTTP 400 because the plan-hash guard in `merge_service.py:394` rejected the installed `replacement_eye_plan.json`.
1. **Live install bytes.** `WIP/Books Arranger/replacement_eye_plan.json` is CRLF, sha256 `42da5fc0…a3a811`, 16730 bytes. Git shows `i/lf w/crlf attr/`. The guard requires `db493dbb…35d20f`, the LF blob.
2. **The bytes were the same at POST time.** The file mtime is 17:04:37, when the v0.13.0 application step wrote it. The server process started at 17:28:03 and the POST went out at 17:43:54 (`replacement-issued.json`). The admission script also hash-checked this file against `42da5fc0` just before the POST (`admission-v3-call-contract.json`, `installed_files`).
3. **Same code.** The live `merge_service.py` normalises to the v0.13.0 blob and contains the guard constant (receipt `live_install_readonly`).
4. **The guard is the first check that can fail.** The exact recorded admission body and headers were replayed offline through the real `web_server.Handler.do_POST` and the real `MergeService.replace_audiobook`, using a stub server and a stub after the guard:
   - live CRLF bytes → `HTTP 400 {"error":"Approved replacement media plan changed"}`
   - approved LF bytes → every check before the guard passes, the guard passes, and the request reaches the first statement after the guard
   - Nothing after the guard could have run. Auth failures return 403, not 400.
5. **Why pure validation missed it.** It read `media/MediaSourcePlan_Frozen.json` (LF, `db493dbb`) and never read the installed plan or ran the guard. It could not reproduce the failure.

## How the live install got CRLF
`sully_apply_release.py` ran `git restore --source=<v0.13.0> --worktree -- <19 paths>`, and the plan was one of those paths. The system gitconfig has `core.autocrlf=true`, so the file was written as CRLF. The script's post-check compared `normalized()` (CRLF→LF) bytes, which hid the difference. `installed-source-manifest.json` even records `"line_endings": "CRLF"` for this file.

## What v0.13.1 changes (`git diff` + untracked)
- `.gitattributes` (new): `replacement_eye_plan.json text eol=lf` (sha256 `b68aa072…`)
- `VERSION`: 0.13.1
- `CHANGELOG.md`: v0.13.1 entry
- this doc

The worktree's own copy of the plan was rewritten to LF (`db493dbb`, `w/lf attr/text eol=lf`). This step does not show in `git diff`.

## Required step when 0.13.1 is applied to the live install
`.gitattributes` alone does **not** rewrite a file that is already checked out (fixture C5). After the delta, including `.gitattributes`, is in both the index and the worktree, run these steps from the install root with the app stopped:
1. `rm -- replacement_eye_plan.json`
2. `git restore --worktree -- replacement_eye_plan.json`
3. Check the **raw** bytes: `sha256sum replacement_eye_plan.json` = `db493dbbfa691e1fe6b875a3edacb8ebd318d487c80c9fa4de66639afa35d20f`. Also `git ls-files --eol replacement_eye_plan.json` shows `w/lf attr/text eol=lf`, and `git status --porcelain` has no line for the file.

Do not compare CRLF-normalised bytes for this file. They match even when the guard will reject the file.

These commands were tested and do **not** rewrite it (the file stays CRLF `42da5fc0`): `git restore --worktree`, `git checkout --`, `git checkout-index -f`, `git restore --source=<tree> --worktree`. Each of them skips a file whose stat data has not changed. `rm` followed by `git checkout-index -f` does produce LF, but it leaves a stale-stat ` M` in `git status`. Use `git restore` instead.

The running server reads the plan on every admission. Re-materialising the file would therefore take effect without a restart. Whether to do that is Jane's or Sergei's decision; this doc does not recommend it.

## Fixture evidence (`scratch/eye-of-god-2026-10-12/line-ending-fix/v4/`)
- Script: `run_v4_fixture.py` (sha256 `4442463d…`)
- Passing receipt: `v4-fixture-receipt-20261012T212600.json`, 16/16 checks, `"passed": true`
- Fixture git trees are private clones of this branch. The 0.13.1 tree is built with `write-tree` and no commit is made anywhere.

| Fixture | Result |
|---|---|
| C1 **positive control:** fresh clone, machine default, no attribute | CRLF `42da5fc0`, byte-identical to the live install; guard REJECTS |
| C2 control: `core.autocrlf=false` | LF `db493dbb`; guard passes. This shows `autocrlf` is the mechanism. |
| C3 fix: fresh checkout of the 0.13.1 tree, machine default | LF `db493dbb`, `attr/text eol=lf`; guard passes. `merge_service.py` stays CRLF, so the attribute only affects the plan. |
| C4 edited plan in the fixed checkout (tolerance 1→2) | git ` M`; guard REJECTS. A genuinely edited CRLF or LF plan is also rejected (receipt `guard`). |
| C5 in-place upgrade (Sully-style delta apply) | plan stays CRLF; only delete-then-re-checkout gives LF |

Fixture bugs caught on the way (receipts kept):
- run1: the stub raised its sentinel too early, so the HTTP positive control failed.
- run2: a status-line check expected `HTTP/1.1`, but the server sends `HTTP/1.0`.

The earlier v1 fixture failed because `checkout-index -f` does not rewrite a stat-clean file. Its baseline was never CRLF. This is the same behaviour as C5.

## Test suite
`python -m unittest discover -s tests -p "test_*.py"` in this worktree: 487 tests, 10 errors (`v4/unittest-0.13.1-worktree.txt`).

Control: a fresh clone of v0.13.0 at the **same path length** (`v4/base-v0.13.0`) gave the same 10 errors plus 2 timing failures (`v4/failure-set-*.txt`). Those 2 tests (`test_waiting_*`) passed on rerun in both trees (`v4/unittest-waiting-rerun.txt`).

The 10 errors already happen on v0.13.0 and are not caused by 0.13.1:
- missing untracked fixtures `scratch/source-fallback-2026-10-11` and `../baseline_native_io.py`
- Windows path length under the deep scratch path
- one test-side defect: `test_merge_http` builds a `BrowserServer` that has no `loaded_version`

## For Futaba
Check the raw plan hash and `git ls-files --eol` in the committed 0.13.1 build. After application, check the same on the live install. A fresh clone should give `db493dbb` with no extra steps.

## For Senua
The code diff is attribute-only. Please red-team the application-step requirement above and the fixture's replay stubs (`StubMerge`, `StubServer`).

## Note for Sully
The branch is based on `b5c5937`. Main is at `4cd7c9e`, a later docs-only commit.
