# Books Arranger v0.14.0 live apply — 2026-10-13

**Release:** tag `v0.14.0` (annotated) on `6662f8fdc6c32c8f4633ad72e4c772cf30f5a165` (candidate `abd70ef` plus the Futaba GO and Senua RELEASE CLEAR docs). `main` fast-forwarded from `e68597a` and pushed; named tag pushed alone; no `--tags`, no force. Repo-local identity verified as the Gemanoneko no-reply, unchanged.

**Gate:** `check_release_preconditions.mjs` is not version-aware for this Python tool (clean-tree only), so the equivalent was done by hand: `VERSION` 0.14.0, tag absent locally and remotely, each verdict doc has exactly one machine-readable line (`GO` naming abd70ef; `RELEASE CLEAR — abd70ef`); the release commit differs from abd70ef only by those two docs.

## Safe stop
- Read-only first: v0.13.1 PID 38788, run `96cbe916-3b2b-4858-b386-89d493cb4f24` Paused/research, jobs Completed, 0 queued, cleanup inactive, no scan, `can_stop` false. Instance record carried the same stale `recovery_active: true` as in v0.13.1; live state read false.
- No Stop needed (already Paused). One supported current-instance shutdown; owner exited, instance record gone, port 5210 bind proven free, completed records and checkpoint unchanged. No force kill, relaunch or Start.

## Apply / verify
- 212 tracked files compared by raw bytes against the tag: 135 byte-identical, 77 differ only by CRLF checkout line endings, 0 content mismatches.
- `replacement_eye_plan.json` raw sha256 `db493dbbfa691e1fe6b875a3edacb8ebd318d487c80c9fa4de66639afa35d20f` (unchanged by the fast-forward; no re-restore needed).
- `data/web-instance.json` absent, no `.git/index.lock`, working tree clean.

Proofs: `scratch/release-0.14.0-2026-10-13/`. Shell was Git Bash. App is stopped; Sergei launches it himself, then Ender verifies and Starts.
