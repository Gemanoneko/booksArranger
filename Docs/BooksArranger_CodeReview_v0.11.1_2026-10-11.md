# Books Arranger code review — v0.11.1

Date: 2026-10-11. Reviewer: Senua. Lean path: small user-reported normal startup correction.

## Certified range

Released baseline `8ec01381d8ce43fb4d1ea2d6e3837e92afa0a3d2` (v0.11.0), through the exact four-file canonical patch below. Source VERSION is 0.11.0; Sully owns the target 0.11.1 bump/release. No new immutable snapshot, helper framework or broader test graph was required.

| Path | Bytes | SHA256 |
| --- | --- | --- |
| app_launcher.py | 15069 | `9aeceddcfc51435bb3b7b431c8521ec1333f498b5d561097535a2edaaad00af7` |
| tests/test_app_launcher.py | 14467 | `3d7c5545e092153e46aa62ca5558796f91e0871834b3c61800847a0fee92ecaf` |
| README.md | 13786 | `c2f838bf635236cbbf609c80693cf0911a3af6dfa603a2999beec7bb38928a59` |
| Docs/BooksArranger_Brief.md | 46537 | `5944e7fdcf1d1f1edfc532689ec6d6bb6201794ebc3893f433db079b28572dfd` |

Reviewer independently checked all four size/hash pins and the exact diff against the release baseline. Git showed only these four changed paths during that review. The producer and independent receiver tested these same identities; the receiver verified them before and after.

## Findings

Open findings: Critical 0; Major 0; Minor 1, inherited. No new finding or safety-floor violation in this patch.

The startup correction removes nine production lines: the IsProcessInJob declaration, outside_job() method and universal current-process eligibility call. Ordinary Windows apps may belong to a Job; membership alone does not establish unsafe lifetime or justify refusing normal startup/reuse. The Pythonw entrypoint, native startup mutex/topology, exact owner/runtime/instance verification, authenticated idle shutdown, captured old-process exit wait, exclusive port/catalog proof, protected completed records and readiness checks are unchanged. There is no Job manipulation, breakaway, broker, scheduler or alternate launch route. Tool-host persistent app launch remains operationally prohibited.

This correction supersedes the universal Job-admission condition described in the v0.11.0 review. The earlier suspended no-op diagnostic remains factual; its member=true result is not generalized into ordinary-user launch lifetime or the cause of an earlier service exit.

**Minor, inherited and accepted:** the released generic connection notice also appears for specific HTTP backend errors, conflicting with the older ConnectionInventory UX exception. The specific error, stale facts and submission block remain intact. This is documented in `Docs/BooksArranger_CodeReview_v0.11.0_2026-10-11.md` (SHA256 `732cd3a013a23f337187972f1b0aadb6004d4a6c89cc770dcd58389e25b198e3`). HTTP/browser code is unchanged and excluded from this targeted review; the advisory does not block release.

## Nine review dimensions

| Dimension | Assessment |
| --- | --- |
| Security | Removal of the universal Job query introduces no command, child process, escape, privilege, credential or external route. Exact owned-process and native file/directory guards remain unchanged. |
| Correctness and logic | Normal startup and verified healthy reuse no longer reject irrelevant Job membership/query conditions. Owner/idle/port/catalog/completed-record/readiness admission remains intact. Ordinary Open/Restart never invokes automatic Start. |
| Crash and stability | Query-based false refusal is removed. Existing post-construction teardown, owned instance-record lifecycle and safe failed-replacement handling remain unchanged. |
| Performance | One unnecessary process/query cycle is removed; no new work, wait, polling or thread is added. |
| State and data safety | Exact-owner token shutdown, idle recheck, held process wait, protected-record comparisons and ordinary Paused restart contract are unchanged. No library, queue, cleanup or recovery mutation path is added. |
| Input handling | Fixed isolated Pythonw entrypoints, runtime/argument checks and bounded safe error surfaces are preserved. |
| Maintainability | Obsolete outside_job API/refusal fixtures are removed. Two replacement cases exercise guarded startup and healthy reuse without consulting irrelevant Job evidence; remaining refusal/order/native cases stay intact. |
| Documentation/code drift | README/Brief correct the lifetime/admission claim and explicitly retain the operational no-tool-host route rule. No success or old-exit-cause inference is made. The inherited HTTP-copy advisory remains recorded. |
| Build/release hygiene | Four exact canonical pins plus actual targeted producer/receiver evidence identify this Lean patch. No unrelated HTTP/browser/media graph or new QA framework is claimed. Release/version operations remain Sully's. |

## Actual validation and limits

Both producer and independent receiver ran this same fixed command once:

```text
C:/Python314/python.exe -B -m unittest discover -s tests -p test_app_launcher.py -v
```

- Producer: **18/18 PASS**, cases 0.206 seconds, owned elapsed 0.764 seconds, exit 0, owned_closed=true. Proof `scratch/app-launch-2026-10-11/job-membership-fix-targeted-proof.json`, SHA256 `8e2cc958c5a462384782682c7974fc8d114f50953fc733776713794e52a005cf` (4790 bytes).
- Independent receiver: **18/18 PASS**, cases 0.204 seconds, owned elapsed 0.773 seconds, exit 0, owned_closed=true, no warnings or outer stderr. Proof `scratch/app-launch-qa-2026-10-11/job-membership-fix-receiver-proof.json`, SHA256 `acee11e5b84399e896617c0c59ca5e7741a6c6e7ed56cdea23d95649a71d323b` (4932 bytes).

Reviewer read/hash-verified both proof files and matched baseline/target, all four source identities, command, all 18 case names/results and native/runtime/supervisor identities. The tests cover guarded fresh startup, healthy reuse, wrong/busy owner refusal, exact old exit before readiness, timeout, completed-record preservation, failure without success page, private COM shortcuts and native mutex/record refusal/retirement. They do not execute a service or shortcut.

Existing in-memory supervisor SHA256: `f9988554c0cd66cb6436e151f051c2fc5c8d6eb5f7219e6342f2517dac011e43`; reviewed native helper `9939de63b3448e02f0c664d43242fe46e728a2f4f77ad21ed62f0bf98c7fad44`; Python `434b361fe0c5960d404974feed493db47f2603a1ace2574312104fbed0182c6f`. The existing finite hidden suspended OwnedProcessJob route is reused; no helper file was created. Outer -I -B, child -B and removed task cache prefix avoid task bytecode. Closure is recorded in both actual receipts.

Actual normal Windows Start-menu launch acceptance remains pending after the patched release. There was no host persistent launch, live service/Start/library/provider operation, unrelated Start-menu write, Comics mutation or reviewer test execution. Unchanged HTTP/browser/media/conversion/cleanup/recovery paths are outside this narrow review. No Senua disposable output was created; unique proof is preserved.

**Verdict:** RELEASE CLEAR
