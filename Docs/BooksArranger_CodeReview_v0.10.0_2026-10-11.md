# Books Arranger code review — v0.10.0

Date: 2026-10-11. Reviewer: Senua. Scope: automatic public-source retry and fallback extension.

## Certified range and endpoint

Reviewed release baseline `78f0c41fcd900ac42a0794052f3ac4589674b165` (v0.9.2) through committed UX HEAD `fa2ef0107b32bda7066cca63f4348688ab7efea3`, plus the exact frozen candidate-v2 payload at `scratch/source-retry-2026-10-11/candidate-v2`. This certifies the pinned payload, not a future moving checkout. Source VERSION is 0.9.2; Sully owns the target 0.10.0 version bump and release.

- Full 65-file normalized source digest: `f844942df51295f70aedb7769cbb6c4f2a14be6359a3551cb846fd5a3e268a46`.
- Raw manifest SHA256: `e0e8e960a86689692746be0e099ff0ff0f06ad7a60a642ff6b562eb0dc33f65a`.
- Six promotion paths: `automatic_processing.py`, `public_research.py`, `tests/test_automatic_processing.py`, `tests/test_automatic_frontend.js`, `web/app.js`, `Docs/BooksArranger_Brief.md`. The seventh changed path versus the release baseline is the committed AutomaticProcessing UX document.
- Every manifest file was independently checked for raw size/SHA256. All 65 text payloads were compared with the release baseline, allowing only CRLF/LF equivalence; no additional changed path appeared.
- Declared staged `web/app.js` SHA256: `c33d731696b400bcde97866ef9f93846e3a4b0ae86cf56d2a793a0afdda4244d`. The overlay is kept outside the live serving path; released canonical asset SHA256 is `c6ba90792dcee02ef1fd1130f016d6652108919439ead3b5d7f3d72bf2accc5c`. Deployment must promote the matched backend and staged frontend together.

## Findings and disposition

Open findings: Critical 0; Major 0; Minor 0. Safety floor intact in this range.

- **Major, closed in v2:** two already-admitted PublicClient instances could overwrite a longer real source pause with a later shorter failure. `public_research.py:290` now updates the shared host record under BEGIN IMMEDIATE, retains the maximum deadline and its cause, and returns that effective wait. The deterministic regression at `tests/test_automatic_processing.py:150` exercises a 429/7200-second pause followed by a 500/300-second failure.
- **Minor, closed in v2:** armed-wait copy lacked the required unavailable-time text and typed wait reasons lacked generic fallbacks when the source label was missing. `web/app.js:395` and `web/app.js:449` now implement the committed Judy strings, including invalid-time and three typed-cause fixtures.

## Nine review dimensions

| Dimension | Result and evidence |
| --- | --- |
| Security | No new command, host, proxy, redirect, credential or provider route. HTTPS allowlist/public-address/TLS pinning, owned DNS, response bounds and token/origin controls are unchanged. New cooldown reasons use fixed safe text. |
| Correctness and logic | App reservations are per host, 100 per rolling hour, atomically shared; eligibility uses the oldest necessary reservation expiry. Cache hits and other hosts remain usable. Valid Retry-After can extend actual source pauses; the v2 shared update cannot shorten them. The worker selects the earliest candidate retry opportunity. |
| Crash and stability | Waiting uses interruptible Event waits capped at 60-second chunks. Stop clears retry ownership and saves Paused work; construction after restart remains Paused. Unexpected errors retain the existing nonactive diagnostic path and never turn into approval. |
| Performance | Indexed host/time lookups, seven-day reservation retention, unchanged 100-entry/seven-day raw cache and serial research remain bounded. No repeated scan is introduced while the saved research loop retries. |
| State and data safety | Deferred candidates remain checkpoint-owned; done IDs are deduplicated. Eligible candidates and admitted jobs/required working cleanup continue before retry waiting. Exact revision/fingerprint checks protect migrated wait records. Manual drafts and job-bound identities retain their existing gates. |
| Input handling | Only the exact historical local daily-limit marker and typed local host bound are recalculated. Genuine external and per-candidate deferrals are preserved. Retry-After parsing tolerates invalid input; UI rejects invalid timestamps and renders typed reasons as text. |
| Maintainability | Named local-budget constants and typed wait kind/scope distinguish app limits from source responses. The four-file v1-to-v2 correction is narrow; no new helper framework or dependency is introduced. |
| Documentation/code drift | The explicit v0.10.0 Brief extension and committed 19-line Judy addendum describe armed Running/waiting, earliest check, local-budget attribution and Stop/restart semantics. Earlier version-scoped sections remain historical. |
| Build/release hygiene | The complete immutable graph, staged overlay and exact fixed QA route identify the reviewed release input. Source VERSION remains 0.9.2 pending Sully. Final actual producer/receiver evidence is recorded below. |

## Validation and limits

The diagnosis receipt `scratch/source-retry-2026-10-11/diagnosis-2026-10-11.json` (SHA256 `9494f600b2d68641dcf506feef872e366e38b8ede311dc30bddf7f73122f4584`) records 100 reservations under the old global daily guard and 2,393 waits carrying its exact local-limit reason. This identifies the local request-bound defect; it does not establish a provider quota or explain unrelated historical exceptions/service exits.

The reviewed v2 fixed route uses the same hidden suspended owned-process containment and shared 600000 ms total deadline. Manifest bytes are read once and hashed before parsing; all 65 sources, trusted native helper and four executable runtime pins stay held through the five fixed commands and final rehash. Pipes retain at most 2 MiB per stream, and exact child/descendant exit and drain closure are required. No real provider request or production service/library operation is part of this QA route.

Route pins: manual-contract-v2.json `829278755650a0ca997f39484766ed5b4b385eb589203c03f8a5cbf36169db1e`; qa_checks_v2.py `d34e015ce1fb03bdb5ccd3fbf5747401f0990e02498595100ad0e767d92ad669`; run_qa_v2_owned.py `ec25edaa70b466514162415a0a626488bdcff606f534ab1cab18a4ee5f72aecd`.

Actual producer v2: **PASS**, 48 processing/public-source fixtures + 8 real private-media cases + all three existing pure-Node automatic/progress/recovery routes; five commands exit 0. Owned elapsed 67.739 seconds, no truncated output. Manual receipt `producer-manual-v2-pass.json` SHA256 `c4792a71d81400d40613946f0024f6c0577eb9bf7d51b607c3f9734dbd348ddf`; owned receipt `producer-owned-v2-pass.json` SHA256 `14d6759f2a610340f64cf72886b704e5c483e295568330a08ffdbd802b98b027`.

Actual independent receiver v2: **PASS**, the identical 56 Python cases and three Node routes, five commands exit 0; owned elapsed 68.380 seconds. Tool/target/source VERSION/HEAD/dirty flag/source digest/manifest/commands/results match the producer. Raw receipts at `scratch/source-retry-qa-2026-10-11/receiver-manual-v2-pass.json` SHA256 `d0e7260dde7073fdfb00db1a4f03837e6e107cffc532064ccae6ceddf6e17b08` and `receiver-owned-v2-pass.json` SHA256 `d5eb9b5f5cfd52f0b7040f1c850872af7d334d28b4a853f302ff923f7fc3c81a` were independently hash-verified. Final reviewer rehash still matches all 65 source pins and the raw manifest.

Identical actual producer/receiver handoff line:

```text
BOOKS_MANUAL_QA|tool=Books Arranger|target=0.10.0|source=0.9.2|HEAD=fa2ef0107b32bda7066cca63f4348688ab7efea3|dirty=true|source_digest=f844942df51295f70aedb7769cbb6c4f2a14be6359a3551cb846fd5a3e268a46|manifest_sha256=e0e8e960a86689692746be0e099ff0ff0f06ad7a60a642ff6b562eb0dc33f65a|python=pass|node=pass|package=n/a(manual nonpackage contract)
```

Five ResourceWarning messages are retained in the receiver output. Their mocked HTTPError(fp=None) objects use CPython3.14's in-memory io.BytesIO fallback (urllib/error.py:45-47), wrapped by urllib.response.addbase with delete=False. Its finalizer closes that memory stream and warns about implicit closure; this construction creates no disk tempfile. Production transport constructs the same error wrapper, so the warning is not claimed impossible there. The actual HTTP response and HTTPS connection are explicitly closed in `public_research.py:130`. These receipts do not demonstrate a socket/file/process leak; no expanded test or blocking finding follows.

Earlier v1 evidence remains retained: 55 Python cases passed, the first Node route failed because snapshot(Paused) replaced the fixture's candidate with backend state, and the two remaining Node routes did not run. V2 retains/restores the same waiting candidate without clearing the result key or weakening assertions. Failed manual/owned SHA256 values are `61bfb0b599e705715bb9d67e286d530d49f5d3386db56f650cad176f50278ff6` / `616d4d40dcd4ef5c381cfe7650911c02f29aa0abf92aa469dcf4ff413cc8b35c`. An earlier unexecuted harness was corrected for Windows Path separator comparison before execution; containment and commands were unchanged.

Coverage is scoped to the affected controller/request logic, existing private automatic-media safeguards and pure-Node UI contracts. No public-provider smoke, actual browser rendering, live queue/library action or persistent runtime/deployment certificate is claimed. Confidence, independent fetched evidence, original-versus-edition language, source membership/order, cover, collision, frozen conversion verification, native cleanup and 24-hour recovery implementations are unchanged. Comics and its budgets are excluded. No Senua disposable output was created; immutable candidates and unique/failed proof remain preserved.

**Verdict:** RELEASE CLEAR
