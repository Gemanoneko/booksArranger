# Code Review — Books Arranger v0.29.0 (release acceptance)

## Header

```
Reviewer: Senua (Code Reviewer)
Date: 2026-11-18
Tool: Books Arranger
Release: v0.29.0
Commit range: edf974f..0f21134 on main (2 commits: 7c51ee1 docs, 0f21134 release bump).
  Follows BooksArranger_CodeReview_v0.29.0_final_2026-11-18.md, which cleared d29f8ed..edf974f.
  Together the two reports cover the full 0.29.0 range, d29f8ed..0f21134.
Files changed: 8 files, +454 / -8
  build inputs: package.json, package-lock.json, scripts/build-inputs.json (+4 / -4)
  CHANGELOG.md (+17); Docs/ (4 files: QA r3 and my final review added, QA r1 and r2 edited)
Candidate: build e8a77a5b-8087-418d-bf82-3a755e69dbd4, packaged from 0f21134 (pinned in the Verdict section)
Stand-down dimensions: 4 Performance and 6 Input Handling are N/A, because no runtime code changed.
```

---

## Summary

What changed:
- `0f21134`: the version goes from 0.28.13 to 0.29.0 in `package.json` and in the two lockfile `version` fields. The lockfile pin `packageLockSha256` is updated, and a CHANGELOG entry is added.
- `7c51ee1`: docs only. It adds QA r3 (GO) and my final review. It also edits QA r1 and r2 so that they no longer name evidence folders that were removed.
- No code, test or `desktop/*` file changed. 7c51ee1 has the same product tree as edf974f: `d977ac98…`.

How it was checked (read-only; I did not write to `dist/` or `build-cache/`, did not run the installer and did not run `npm run release`):
- **Hashes.** I re-hashed the installer, the manifest and the entry log with `sha256sum`. All three equal the brief's values.
- **Manifest entries.**
  - All three artifacts (exe, blockmap, `latest.yml`) match by SHA-256 and size.
  - The SHA-512 in `latest.yml` equals the installer's.
  - The repo's own `artifactContract` and `packageContract` pass.
- **Product digest.**
  - I imported `scripts/release-contract.mjs` `productTree` and `scripts/release-flow.mjs` `gitEntries` and ran them on `git ls-tree -rz --full-tree 0f21134`.
  - The result is `a32a44cb…e1e3`, which equals the manifest's `product_digest`. `HEAD` gives the same result.
- **Shipped bytes, checked three ways:**
  - **Installer payload.** I carved the embedded `app-64.7z` out of the installer and extracted it with the repo's `7za` into scratch. All 405 files equal `payload.files` by hash and size, with no extra or missing file.
  - **`win-unpacked`.** All 405 files equal `payload.files`, with no extra or missing file.
  - **Source.**
    - The 144 shipped backend `.py`/`.json` files equal their git blobs at 0f21134: 39 byte for byte, 105 differing only in CRLF.
    - The 26 app files in `app.asar` equal their 0f21134 blobs: 9 exact, 16 CRLF only. The exception is `package.json`, which differs only by the builder's own edits: it removes `scripts`, `build`, `devDependencies` and `allowScripts`, and adds `booksInstallationBootstrapRequired`, as `scripts/build_phase.py:188` intends. Its version is 0.29.0.
    - The backend `VERSION` reads `0.29.0`.
- **Entry log.** Line 3 is the receipt: `books-arranger v0.29.0 @ 0f21134f… (dirty: N) … check pass … personal-folders clean`. The run exited 0 at 23:30:31Z.

What I found:
- **No Critical. The safety floor is intact.**
- **Ender's two pre-build fixes do not change any shipped byte. Details are in § 9.**
- **One Major (R-M1).** The release tag `v0.29.0` is already pushed. It is a lightweight tag on 0f21134. The tool's own release script requires the tag to point at the clean HEAD that holds the acceptance docs, so `npm run release` will refuse.
- **Four Minors (R-m1 to R-m4):** release hygiene and docs.

---

## Rubric

### 1. Security

- Status: Pass
- Findings: none. No code changed. A secret scan of the range diff (`ghp_`, `github_pat_`, `gho_`, token, password, secret, Authorization) finds only prose.

### 2. Correctness & Logic

- Status: Pass
- Findings: none. The version is 0.29.0 in every place it appears: `package.json`, both lockfile fields, the asar `package.json`, backend `VERSION`, `latest.yml`, the manifest's `version`/`shell_version`/`backend_version`, and the entry receipt. The lockfile diff touches only the two `version` fields.

### 3. Crash / Stability Safety

- Status: Pass
- Findings: none. No runtime code changed.

### 4. Performance

- Status: N/A. No runtime code changed.

### 5. State & Data Safety

- Status: Pass
- Findings: none in range.
  - The stale-pointer recovery archived the file instead of deleting it. The archived file is `build-cache/runtime-pointer.json.previous-22a176a6-…`. Its SHA-256 is `a26773fd…`, which equals the evidence copy, and it has the same file identity as the original.
  - The protected data files equal the source. `replacement_eye_plan.json` equals its git blob, and `public_source_leads.json` equals the bytes in the working tree.

### 6. Input Handling

- Status: N/A. No runtime code changed.

### 7. Maintainability

- Status: Pass
- Findings: none in range.

### 8. Doc/Code Drift

- Status: Concerns
- Findings:
  - **R-m4 [Minor]** `Docs/BooksArranger_QA_v0.29.0_r2_2026-11-17.md:109`.
    - 7c51ee1 rewrote historic QA reports in place, replacing evidence paths with "(superseded evidence folder, removed)". The SHA-256 values stay, so each report is still bound to its evidence.
    - The r2 sentence now reads "`(superseded evidence folder, removed)` is the entry log this report cites; keep it until the verdict is acted on". It tells the reader to keep a folder it calls removed.
    - Next time, add a dated note below the original text. Do not edit the evidence rows.
  - The CHANGELOG entry matches the 0.29.0 range I reviewed: the check pass, Light Novels, leftover-only source folders, resume after restart, status and Stop, Waiting for you, and the three fixes.

### 9. Build & Release Hygiene

- Status: Concerns

**Ender's two pre-build fixes (brief question): neither changes shipped bytes.**

- **The stale `runtime-pointer.json` rename:**
  - Pack attempt 2 refused with "Incomplete prior candidate preserved", from `scripts/build_fs_guard.py:367`: 0.28.13's `dist/` had been removed after its release, and the pointer was left behind.
  - Ender archived the pointer at 23:18:53Z. Attempt 3 then started at 23:18:59Z with `prior_archived: {}`, a fresh build.
  - The new pointer names build `e8a77a5b`.
  - Its 48 runtime entries match three things: the manifest's `runtime.files`, the payload's `resources/python` and `resources/ffmpeg`, and the 48 entries of the stale 0.28.13 pointer. So the runtime bytes are unchanged from 0.28.13.
  - `runtime.pins_sha256` equals the SHA-256 of `desktop/runtime-pins.json`.
  - The pointer is not in the installer.
- **The package-lock.json LF restore:**
  - The working-tree file now equals the git blob at 0f21134 (`fc77b676…`). That is also the value of the pin.
  - `package-lock.json` is not in `app.asar` and not in the payload.
  - The product digest uses git object IDs, so it ignores line endings.
  - Pack attempt 1 refused on the CRLF copy before any build work, which is fail-closed.

**Findings:**

- **R-M1 [Major]** `scripts/release-flow.mjs:24` with `:32`, `:16` and `:36`. The tag `v0.29.0` already exists, locally and on origin. It is a lightweight tag on 0f21134. The tool's release script needs four things to hold together:
  1. a clean checkout (`:16`);
  2. the tag resolving to HEAD (`:24`);
  3. the pushed tag at HEAD (`:32`);
  4. `Docs/BooksArranger_ReleaseAcceptance_v0.29.0.json` plus both pinned reports, read from that same tree (`:36`, `:38-45`).

  The acceptance docs do not exist at 0f21134. Committing them moves HEAD past the tag, and leaving them uncommitted fails the clean check. So `npm run release` refuses at `:24` before it builds or uploads anything. It fails closed, and nothing shipped is affected.

  The 0.28.13 tag was put on the QA-report doc commit after acceptance (`Docs/BooksArranger_ReleaseReceipt_v0.28.13_2026-11-16.json` `tag_target_note`). This time the order was reversed.

  Do not delete, move or force-push the pushed `v0.29.0` tag without Sergei's explicit call; moving a pushed ref falls under the safety floor's source-of-truth item. The two routes I can see are:
  - route B, a manual publish of the three verified assets as at 0.28.12 and 0.28.13, which needs Sergei's authorisation;
  - a tag move that Sergei approves.

  For next cycle: the studio pipeline's "tag the bump commit" step and this tool's acceptance flow need one agreed order.
- **R-m1 [Minor]** `scripts/build-inputs.json:6`. The lockfile pin changed line-ending convention between releases.
  - At edf974f the pin `c5cb9244…` was the CRLF hash of that lockfile.
  - At 0f21134 the pin `fc77b676…` is the LF hash. This checkout uses `core.autocrlf=true`, so every fresh checkout here writes CRLF and the pack refuses until LF is restored by hand. That is exactly what happened in pack attempt 1.
  - The same dependence on this checkout's line endings binds `desktop/runtime-pins.json` and `public_source_leads.json`. The manifest hashes their CRLF working-tree bytes, not the blobs, and `scripts/release.mjs:111-114` compares against the working tree. So the publish step must run from this checkout, unchanged.
  - Fix next cycle: add `.gitattributes` rules (`-text` or `eol=lf`) for each hashed file, as `replacement_eye_plan.json` already has. That change alters the product tree, so it is not for 0.29.0.
- **R-m2 [Minor]** `.claude/skills/release-pipeline/scripts/check_release_preconditions.mjs:384-394` (studio tooling, outside this repo's range). The two naming rules disagree.
  - The studio gate ranks `_final_2026-11-18` above this report's plain `_2026-11-18`, so Sully's precondition script will read my earlier final review, which certifies d29f8ed..edf974f, not this candidate. It reads Futaba's `_r3_` the same way.
  - The tool's `acceptanceIndex` (`scripts/release-contract.mjs:66-74`) accepts only the unmarked name.
  - Both of my reports say RELEASE CLEAR, so nothing is masked today. If a later unmarked report said BLOCKED, the studio gate would still pass on the older `_final_` report; only the tool's own flow would catch it.
- **R-m3 [Minor]** Outside the range; this is a process gap. The 0.28.13 local build cleanup (commit 125d7cd) removed `dist/` but left `build-cache/runtime-pointer.json`. Every pack after a published-build cleanup will hit the same refusal and need the same hand recovery. The cleanup step should archive or retire the pointer together with `dist/`.

**Release preconditions** (for Sully; not findings against the code). These hold only if the release-flow route is used:
- The acceptance index must name a QA report called `Docs/BooksArranger_QA_v0.29.0_<date>.md`, with no round marker. That report carries its own verdict, source pin and manifest-hash lines.
- `requiresNativeQa('0.29.0')` is true, so the flow also needs `Docs/BooksArranger_NativeQA_v0.29.0.json`, its records, and a `Native QA evidence SHA256:` line in that QA report.

**Still open from earlier reviews (unchanged, since no code moved):** D-m3, F-m1, F-m2, all Minor.

---

## Patterns

Release mechanics now cause more friction than the code does. Three of this cycle's four findings come from mismatches between the studio pipeline and the tool's own release contract: tag order, report naming, and which line endings each hash assumes. The pointer gap comes from post-release cleanup. Every one fails closed, but each costs a hand recovery or a reroute at release time.

---

## Verdict

- Total Critical: 0
- Total Major: 1 (R-M1)
- Total Minor: 4 (R-m1, R-m2, R-m3, R-m4), plus 3 carried over (D-m3, F-m1, F-m2)

**Verdict:** RELEASE CLEAR

Release source commit: 0f21134f3b8723d402b13813e0c3bd606a26da8b

Release artifact manifest SHA256: 66b1eb18f476ff07b41d8ec38758f474377ce6f3702b822e9b1ed3e921c91538

Verified values for this candidate:
- installer `dist/builds/e8a77a5b-8087-418d-bf82-3a755e69dbd4/Books-Arranger-Setup-0.29.0.exe`: SHA-256 `264ff5c8b02060695f0954c2afd78dc2800b9fdcbbb4a0c416cd207057bf7c4b`, 209,247,068 bytes;
- product digest `a32a44cbce1b8c7562bed2b0f44e91477c163b518f436abde4c97a1cbbe1e1e3`, equal to `productTree(0f21134)`;
- entry log `I:\AI Projects\Worktrees\Books Arranger\qa-0f21134\ender-entry.log`: SHA-256 `2a02c859e74f33ff5a04731362752870fa0d5a23e0fa3d0b0d128be06f5d641b`.
