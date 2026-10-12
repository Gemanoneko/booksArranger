# Code Review — Books Arranger v0.13.1

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-10-12
Tool: Books Arranger
Release: v0.13.1
Commit range: b5c5937f458cad1c8f3b10ee8c71633381e79023 (v0.13.0)..fcf0b4991761770ddd7b407cf6786b5683f32c9a
  (previous certified code endpoint 7691025; 7691025..b5c5937 is the docs-only v0.13.0 review reconciliation)
Commits: 4cd7c9e (docs), b662709 (fix), fcf0b49 (test)
Files changed: 6 files, +183 / -2
Stand-down dimensions: none; Electron N/A (Python + local browser UI)
```

---

## Summary

v0.13.1 adds `.gitattributes` (`replacement_eye_plan.json text eol=lf`), bumps VERSION, adds a CHANGELOG entry and the handoff doc, and adds `tests/test_replacement_plan_bytes.py`. 4cd7c9e is a docs-only commit. No product code changed: `merge_service.py:392-394` still hashes the raw plan bytes against `db493dbb…35d20f`. The review also covered how the release gets applied, because the HTTP 400 came from the apply path and not from the commit.

Everything was checked in clones made with `--no-hardlinks` in the scratchpad. I ran no git command that writes to the live checkout and did not run the app. Results:

- **Fixtures.**
  - **Fresh materialisation of v0.13.1 gives LF `db493dbb` in every case tested:** clone with the machine default (`core.autocrlf=true`), `autocrlf=false`, `autocrlf=input`, `autocrlf=false` with `core.eol=crlf`, `git worktree add`, and `git archive`.
  - **Control:** v0.13.0 with the machine default gives CRLF `42da5fc0`, which matches the live install.
  - **Existing CRLF copies are not healed.** After upgrading to v0.13.1 by `git checkout`, `git reset --hard`, or Sully's delta (`restore --source --worktree`, then `--staged`, then `update-ref`), the plan stays CRLF `42da5fc0`. `git status` stays clean in all three cases. The plan's blob `d6187414` is the same in v0.13.0 and v0.13.1, so git never rewrites the file.
  - **`rm` then `git restore --worktree` gives LF `db493dbb`** with a clean status. This held after the Sully-style delta, and also when `.gitattributes` was only in the worktree.
  - **`rm` then `restore --source=<tree>` gives LF but a stale-stat ` M`.**
  - **`rm` with an index that lacks the plan leaves the file deleted:** the restore fails with "pathspec did not match".
  - **The live install (read-only check) is still CRLF `42da5fc0`.** The index entry is `d6187414`, HEAD is `4cd7c9e`, there is no `.gitattributes`, and `data/web-instance.json` is present, so the app is running.
- **Test mutations.** The suite fails in every case below:
  - **Real CRLF upgraded copy:** test 1 fails, and the message gives the raw sha256 and the CRLF count.
  - **Guard constant switched to the CRLF hash with a CRLF plan:** test 1 passes and test 2 fails.
  - **Guard deleted:** test 2 fails.
  - **Guard moved after `self.reviews`:** test 2 fails.
  - **`* -text` appended to `.gitattributes`:** test 3 fails.
  - **`.git/info/attributes` set to `eol=crlf`:** test 3 passes, but test 1 fails on the real bytes.
- **Test 1 runs the real guard.** It calls the real decorated `MergeService.replace_audiobook` and reads the hash from inside the guard; it does not copy the constant. The `__file__` patch takes effect: test 2 is rejected on the temp copy, so it reads that copy and not the real plan. The test can't give a false pass because test 2 is a sensitivity control: any change that stops the guard rejecting a CRLF copy fails the suite.
- **Not re-run by Senua:** the full 490-test suite. Ender's receipt is cited in the handoff doc, and behaviour is Futaba's area.

---

## Rubric

### 1. Security

- Status: Pass. The change adds no shell-out, network, path, IPC or secret surface. The test's `__file__` patch is in-process and is restored after each call.

### 2. Correctness & Logic

- Status: Concerns
- Findings:
  - The attribute is correct and enough for **every fresh materialisation**, under every `autocrlf`/`core.eol` combination tested. It does **not** fix copies that already exist; see F1.

### 3. Crash / Stability Safety

- Status: Pass. No runtime code changed. If the plan is wrong or missing, the admission still fails closed with a `ValueError` or `FileNotFoundError`.

### 4. Performance

- Status: Pass. The three new tests run in about 10 ms.

### 5. State & Data Safety

- Status: Concerns
- Findings:
  - **F6 [Minor]** `Docs/BooksArranger_LineEndingFix_v0.13.1_2026-10-12.md:28-36`, `tests/test_replacement_plan_bytes.py:58-60`: the procedure deletes the file before restoring it.
    - If the index has no `d6187414` entry for the plan, or `index.lock` is held, the restore fails and the plan is left absent. Fixture F10 shows this.
    - The test's failure message says "rm it, then git restore" but does not say to stop the app first or to check the index first.
    - The outcome fails closed, but the precondition must be explicit. See the required apply step below.

### 6. Input Handling

- Status: Pass. There is no new runtime input, and the plan is still gated by the unchanged raw-sha256 check.

### 7. Maintainability (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **F5 [Minor]** `tests/test_replacement_plan_bytes.py:37-51,68-71`: `test_gitattributes_pins_plan_to_lf` reads the text of the root `.gitattributes` only.
    - It ignores `.git/info/attributes`, `core.attributesFile`, case-insensitive matching (`core.ignorecase=true` in this repo) and `[attr]` macros.
    - Mutation M5 shows that an `eol=crlf` in `info/attributes` passes this test. The suite does not false-pass, because test 1 measures the bytes.
    - `git check-attr text eol -- replacement_eye_plan.json` would measure the effective attribute directly.
  - **F7 [Minor]** `.gitattributes:1`: the fix covers one file by name. If raw bytes of another tracked file are pinned in future, nothing makes that file get an `eol=lf` or `-text` rule.
    - Today the plan constant is the only 64-hex literal in tracked code and tests.
    - A generic test would close this: any tracked file whose sha256 appears as a literal must carry `eol=lf` or `-text`.

### 8. Doc/Code Drift (no Critical findings on its own)

- Status: Concerns
- Findings:
  - **F3 [Minor]** `Docs/BooksArranger_LineEndingFix_v0.13.1_2026-10-12.md` has stale lines:
    - `:3` says "The regression test below is uncommitted". It was committed in fcf0b49.
    - `:93` says "The branch is based on `b5c5937`". The parent of b662709 is `4cd7c9e`, so the branch already contains main.
    - `:20` cites the `.gitattributes` sha256 `b68aa072…`. That is the hand-written LF copy in the staging worktree. A copy materialised by git under `autocrlf=true` is CRLF `14c39f59…`, so this hash must not be used as an apply pin.
  - **F4 [Minor]** `CHANGELOG.md:7` says the release keeps the plan as exact LF on Windows Git checkouts. That is true only for freshly materialised copies. The entry does not mention that upgraded copies need the step that re-materialises the file.

### 9. Build & Release Hygiene

- Status: Concerns. VERSION is 0.13.1, the CHANGELOG entry is present, `v0.13.1` is not tagged yet, and `origin/codex/books-release-0.13.1` is at fcf0b49.
- Findings:
  - **F1 [Major]** `.gitattributes:1` with `merge_service.py:392-394`: the release does not apply itself.
    - Every existing v0.13.0 copy that was materialised under `autocrlf=true` keeps the CRLF plan after `git pull`, `git checkout`, `git reset --hard` or a delta restore. That includes the live install and any clone on Sergei's other machines.
    - `git status` reports it clean.
    - Only the manual step below heals the copy. The app shows the problem only when an admission POST returns HTTP 400.
    - Next cycle: consider a launcher-side or startup preflight that runs the same raw guard and makes the failure visible before any admission.
  - **F2 [Major]** (outside the commit range; logged because it is this release's apply path) `scratch/eye-of-god-2026-10-12/metadata/actual-admission/sully_apply_release.py:24-25,150,159-163`:
    - It verifies the applied files after CRLF→LF normalisation.
    - It skips paths that start with a dot, so `.gitattributes` is never verified.
    - Its `installed-source-manifest.json` pinned the CRLF bytes. Every later admission packet then pinned `42da5fc0` as the correct installed plan, for example `admission-v3-call-contract.json:210`; the other files are listed in the bug-class section.
    - At each step, the check confirmed the bytes that were on disk, not the bytes the guard requires.
    - For 0.13.1: the plan needs a raw comparison; the attribute is checked with `git check-attr`, not by the raw bytes of `.gitattributes`; and any new admission pins come from the guard constant, `db493dbb`, not from the disk.

---

## Required apply step (live install) — Sully must follow exactly

Work from the install root in Git Bash, and quote the path.

**Preconditions.** Check all of these and STOP if any fails.

- a. **The app is stopped.**
  - It was stopped by its normal shutdown, inside the same offline exclusion as the delta apply.
  - `data/web-instance.json` is absent.
  - Nothing is relaunched until step 3 passes.
  - No other git process is running (`.git/index.lock` is absent), and no editor has the file open.
- b. **The 0.13.1 delta is in place.** It is applied to both the worktree and the index, and HEAD/main is at the 0.13.1 commit. `git check-attr text eol -- replacement_eye_plan.json` prints `text: set` and `eol: lf`. Do not pin the raw hash of `.gitattributes`; a git-materialised copy is CRLF.
- c. **The index entry is correct.** `git ls-files -s -- replacement_eye_plan.json` prints `100644 d6187414663eb1393913fa3ad5993304cadd5a1b 0`. If it does not, do NOT run `rm`.

**Steps**

1. `rm -- replacement_eye_plan.json`
2. `git restore --worktree -- replacement_eye_plan.json`. This restores from the index. Do not add `--source`: that leaves a stale-stat ` M`.

**Gate**

3. Run `sha256sum replacement_eye_plan.json`. It must print `db493dbbfa691e1fe6b875a3edacb8ebd318d487c80c9fa4de66639afa35d20f`. Compare the raw bytes only, never normalised bytes.
   - If the file is missing or the hash is wrong: do not launch. Re-run step 2 once. If it still fails, STOP and report.

**Supporting checks.** These are not a gate on their own; `git status` was also clean while the file was CRLF.

4. `git ls-files --eol -- replacement_eye_plan.json` shows `i/lf w/lf attr/text eol=lf`, and `git status --porcelain -- replacement_eye_plan.json` prints nothing.
5. Optional: `python -B -m unittest tests.test_replacement_plan_bytes` passes in the install root. `-B` stops it writing `.pyc` files.

**Afterwards**

- The installed manifest records the plan's raw sha256.
- Old admission packets must not be reused. They pin `42da5fc0` and will refuse, which fails closed. New packets must pin `db493dbb`.

**Assessment.** The step is safe. It deletes only a tracked file that can be rebuilt from blob `d6187414`, and the stopped app cannot see the short window while the file is missing. It is enough: fixture F7 reproduced Sully's delta apply on a CRLF v0.13.0 copy, and this step brought it to `db493dbb` with a clean status and the test passing. Re-materialising the file while the app runs is not certified by this review.

---

## Same bug class elsewhere (listed only, not fixed)

1. **`merge_service.py:392-394`** is the only tracked code that pins a hash of the raw bytes of a checked-out file. It is the only 64-hex literal in tracked code and tests, and v0.13.1 now covers it.
2. **`public_research.py:213-217`** reads `public_source_leads.json` raw. On this machine the file is CRLF, 794 bytes. The code applies a 65536-byte bound and a strict JSON parse, so it tolerates CRLF today. It would hit this bug if a hash pin were ever added.
3. **`web_server.py:181,185`** serves `web/` files raw.
   - The CSP at `:132` uses `'self'` only, with no script hashes or nonces, and there are no SRI `integrity=` attributes, so it is not affected.
   - It would be affected if hash-based CSP or SRI were added.
4. **`storage_cleanup.py:309-311`** hashes a rebuilt `inputs.txt` that assumes CRLF, from historical Windows `write_text` output. It is the same line-ending-sensitive raw hash, but on app-produced files rather than the checkout.
5. **Outside the repo:** `sully_apply_release.py` (normalised comparison, skips dot-paths) and `installed-source-manifest.json`. The following also pin `42da5fc0` for the installed plan:
   - `Admission_Packet.json`, `Admission_v2_Packet.json`, `Admission_v3_Packet.json`
   - `admission-call-contract.json`, `admission-v2-call-contract.json`, `admission-v3-call-contract.json`
   - `admission-before-proof.json`
   - `application-continuation-contract.json`, `ApplicationContinuation_Packet.json`, `continuation-proof/after-proof.json`
   - `canonical-application-continuation-packet.json`
   - `partial-application-readonly-proof.json`

---

## Patterns

Three checks measured a proxy instead of what the guard measures:

1. **My v0.13.0 review** accepted "blobs equal the candidate after explicit CRLF-to-LF normalization" for a file whose only consumer hashes raw bytes.
2. **The apply script** compared normalised bytes.
3. **The admission preflight** pinned whatever was on disk.

For any file that is read by a byte-exact guard, the evidence must be the raw bytes at the location the guard reads. ProcessRules § Verification Discipline covers this. Future reviews will check this for every hash-pinned input.

---

## Verdict

- Total Critical: 0
- Total Major: 2
- Total Minor: 5

**Verdict:** RELEASE CLEAR

The safety floor is intact. The release clears on the condition that the required apply step above is carried out and its gate (step 3) passes before the app is relaunched. F1 and F2 are logged for Ender for the next cycle.
