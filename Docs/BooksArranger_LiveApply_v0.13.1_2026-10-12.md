# Books Arranger v0.13.1 live apply — 2026-10-12

**Release:** tag `v0.13.1` (annotated) on `8d325bd9a3514ff21b8daa7a4df6bd57aec5146f` (candidate `fcf0b49` plus the Futaba GO and Senua RELEASE CLEAR docs). `main` pushed through `c31bbbd` (Jane's Brief decisions, committed after the stop). Named tag pushed alone; no `--tags`, no force.

**Ordering chosen:** the delta changes `VERSION`, `.gitattributes`, `CHANGELOG.md` and a test, so main's working tree (the live install) was only touched after the app was stopped. Verdict docs were committed in the staging worktree first.

## Safe stop
- Read-only first: loaded v0.13.0 Pythonw PID 100520, run `96cbe916-3b2b-4858-b386-89d493cb4f24` Running/research; jobs Completed, 0 queued, cleanup inactive, no scan. The instance record had a stale `recovery_active: true`; live `/api/health` and state both read false across 48 s before the Stop.
- One supported Stop, Paused confirmed, then one supported current-instance shutdown. Owner exited, instance record gone, port 5210 bind proven free. No force kill, relaunch or Start.
- Five completed records unchanged before/after (SHA256 `3c299753f7024677f30510c0659b584dd8dbb9fbad07916a2a8282c1fa4b4112`).

## Senua mandatory step
Preconditions held (no `data/web-instance.json`, no `.git/index.lock`, attrs `text: set`, `eol: lf`, blob `d6187414663eb1393913fa3ad5993304cadd5a1b`). `rm` then `git restore --worktree` done once. Raw `sha256sum replacement_eye_plan.json` = `db493dbbfa691e1fe6b875a3edacb8ebd318d487c80c9fa4de66639afa35d20f` (gate passed first try).

## Other tracked files
203 tracked files at the tag compared by raw bytes: 139 byte-identical, 64 differ only by CRLF checkout line endings (Windows autocrlf, as in earlier applies), 0 content mismatches. `Docs/BooksArranger_Brief.md` matches `main` rather than the tag (Brief commit is after the tag).

## Follow-up needed
Senua F2: `sully_apply_release.py` compares line-ending-normalised bytes and skips `.gitattributes`; it cannot catch a CRLF plan file. Needs fixing later; not changed now.

Proofs: `scratch/release-0.13.1-2026-10-12/` (`before-stop.json`, `paused-proof.json`, `shutdown-proof.json`, `applied-hashes.json`, `plan-raw-sha.txt`, `release_control.py`). Shell was Git Bash. App is stopped; Sergei launches it from the Start menu.
