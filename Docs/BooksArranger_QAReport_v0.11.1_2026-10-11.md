# Books Arranger QA — v0.11.1 — 2026-10-11

**Verdict:** GO for the narrow pinned startup correction under the Lean path. **New findings:** 0 Blocker / 0 Major / 0 Minor. The independent launcher suite passed 18/18 once; real normal-user Open/Restart acceptance remains pending. The inherited v0.11.0 generic HTTP-error notice-copy Minor remains accepted and unchanged.

## Pinned patch and actual checks

Released baseline: 8ec01381d8ce43fb4d1ea2d6e3837e92afa0a3d2. Source version 0.11.0; target 0.11.1. The canonical patch was pinned before the regression and rehashed unchanged afterward; no mutable unpinned build was certified.

| File | Bytes | SHA-256 before and after |
|---|---:|---|
| app_launcher.py | 15069 | 9aeceddcfc51435bb3b7b431c8521ec1333f498b5d561097535a2edaaad00af7 |
| tests/test_app_launcher.py | 14467 | 3d7c5545e092153e46aa62ca5558796f91e0871834b3c61800847a0fee92ecaf |
| README.md | 13786 | c2f838bf635236cbbf609c80693cf0911a3af6dfa603a2999beec7bb38928a59 |
| Docs/BooksArranger_Brief.md | 46537 | 5944e7fdcf1d1f1edfc532689ec6d6bb6201794ebc3893f433db079b28572dfd |

The user reported that both installed entrypoints universally refused their normal process Job membership. This patch removes that launcher admission condition and corrects the accompanying process-lifetime claims. It retains exact-owner, idle, port/catalog lease, protected completed-record and readiness checks. It does not prove independence from an external Job lifetime or authorize a persistent tool-host launch.

| Run | Result | Case / owned duration |
|---|---|---|
| Ender producer | 18/18 PASS, exit 0, owned closed | 0.206 / 0.764 s |
| Futaba receiver | 18/18 PASS, exit 0, owned closed | 0.204 / 0.773 s |

Both ran only the existing test_app_launcher.py discovery route. The identical existing in-memory supervisor hash f9988554c0cd66cb6436e151f051c2fc5c8d6eb5f7219e6342f2517dac011e43 was independently matched before execution. Outer Python uses -I -B; child uses -B for standard canonical cwd imports; PYTHONPYCACHEPREFIX is explicitly removed. Hidden finite execution uses the reviewed native suspended-child OwnedProcessJob, exact child exit and pipe closure, a 590-second communication budget and enclosing 600000 ms timeout. No timeout, warning or closure failure occurred.

Python executable hash 434b361fe0c5960d404974feed493db47f2603a1ace2574312104fbed0182c6f and native helper hash 9939de63b3448e02f0c664d43242fe46e728a2f4f77ad21ed62f0bf98c7fad44 matched before and after. Full baseline HEAD matched. Lean scope requires no package/manual full-graph receipt; no such gate was fabricated and no source copy or new helper was created.

Actual compact evidence:

- Producer: scratch/app-launch-2026-10-11/job-membership-fix-targeted-proof.json, SHA-256 8e2cc958c5a462384782682c7974fc8d114f50953fc733776713794e52a005cf; independently hashed and retained in QA scratch.
- Receiver: scratch/app-launch-qa-2026-10-11/job-membership-fix-receiver-proof.json, SHA-256 acee11e5b84399e896617c0c59ca5e7741a6c6e7ed56cdea23d95649a71d323b, 4932 bytes. This contains actual output and four-file before/after identities.

## Coverage and limits

The revised cases verify that Job membership no longer blocks guarded startup and a failed Job query no longer blocks verified healthy-owner reuse. Other passing cases cover healthy reuse without restart/Start, busy-research rejection without shutdown, checkpoint/exact exit before replacement bind/readiness, mismatched-owner preservation, shutdown timeout without replacement, failed startup without a success page and completed-record identity protection. Native private COM shortcut save/reopen and unrelated-entry preservation, mutex contention/reacquisition, protected record readers/retirement, dangling/hardlinked record refusal and pyw fixed import paths also pass.

These are private native fixtures and mocked lifecycle actions, not execution of the installed shortcuts or live app. No HTTP/browser/media regression, provider request, user Start-menu mutation, app startup, library action, runtime change, Comics action or Git mutation occurred. Normal user-click launch/restart must be verified after the patch; the previous v0.11.0 fixture GO did not certify it. The historical automatic-pass unexpected failure cause remains unknown.

**Pattern alert disposition:** the normal-launch gap is addressed by the small user-reported admission correction and targeted regression; real acceptance remains pending. Previous fixture-drift maintenance remains deferred outside this patch. No broader framework or tests were added by QA.

## Hygiene

The owned launcher process and descendants/drains closed. Private test temporary folders cleaned themselves; scratch/app-launch-tests is empty. No task bytecode prefix was recreated and no disposable files remain from this narrow receiver run. Preserve the unique actual proofs, earlier failed endpoint evidence and accepted reports. The v0.11.0 cleanup receipt remains separate; no prior report was edited.
