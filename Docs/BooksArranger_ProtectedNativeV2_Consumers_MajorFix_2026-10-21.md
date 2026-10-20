# Protected native V2 consumers — three-Major correction checkpoint

SOURCE ONLY; independent recheck pending. Implements only the three findings in committed review49cb6f00ee269bded79fa9867c0d15f07c789902, report SHA55a9d35bb120ef106f9be0ad7583df6c234fe2f5f161fabfb3ae80d76381158e. No test, source-module evaluation, compilation, native/candidate invocation, deployment, global/host mutation or live-product action occurred. The shared Node kernel remains quarantined after the separate RPC timeout; it was not called, reset, probed or reconciled here.

## Bounded changes

1. **Manifest aliases:** launch-books-qa.mjs now forms duplicate keys by replacing Windows backslashes with forward slashes and lowercasing. Both membership lookup and insertion use that same key. Existing absolute/relative/traversal/colon/empty-component, hash and size checks remain intact; member paths and admitted roots themselves are not rewritten. Aliases are refused even with identical bytes, and conflicting hash/size aliases receive no special acceptance.

   The existing PRE fixture builder accepts optional source-member data and recomputes every dependent manifest/context/guardian/policy/registry hash. New written controls therefore reach member validation instead of merely failing a stale hash. They cover both mixed-separator orders, same-separator and case duplicates, identical versus conflicting hash/size pairs, plus single canonical relative members using either separator.

2. **Required installation policy:** provision-protected.mjs now requires native-admission-policy.json in addition to the separate dispatch-policy.json and all previously mandatory files. This is the exact protected filename emitted in the registry's policy_path. Existing disabled-only plan rules, 110-member and8MiB ceilings remain unchanged. New written controls reject omission of either policy, accept synthetic exact110/exact8MiB boundaries and refuse one extra member/byte. These are unrun arithmetic/data controls, not measured fit of an actual protected inventory; actual artifact-fit/protected-copy proof remains a STOP gate. No quota was raised.

3. **Rejected-first POST:** exercisePostBoundary now calls consumeFixturePending with the actual opaque pending token before binding, original-result or capability validation can return or throw. Its existing WeakMap lookup deletes the genuine slot before validating expected fields. A malformed, nonzero, signaled, missing-EOF or late first attempt therefore burns that association. A copied token still cannot identify or consume the genuine slot; no JSON/disk authority was added. Existing result/frame/binding checks and observation cleanup remain unchanged.

   Written refused-first/then-valid controls cover null/empty result, nonzero exit, signal, nonterminal, false and missing stdout/stderr EOF, over-budget final duration, terminal time beyond actual duration, malformed frame and JSON-copied Buffer data. Every second use must fail with replay. A wrong first binding also consumes its original token before the later correct binding is tried. All previous copied/successful replay/false-origin controls remain present.

Focused controls now import the existing disabled provision validator to test its required inventory; no new runner/module/framework was added. The production PRE/POST/dispatch refusals, literal terminal/context/registry schemas, canonical helpers and non-Books host bytes are unchanged. C++ and primary-agent pending controls were not edited or inspected.

## Frozen source pins

Ordinary read-only default-PowerShell tool chunk629edb exited0, wall0.3117576s, after hashing the ten owned files and reading the two changed method lines. Exactly five source files changed relative to the reviewed baseline:

| Relative path | Bytes | SHA256 |
|---|---:|---|
| scripts/qa-native/launch-books-qa.mjs |21441|04c57f79cde833e90bf57d3459d2445cd1ac284eab43be7cad13fa0e7d59c723|
| scripts/qa-native/provision-protected.mjs |4666|ab4fe3a0a02aa08ab84d5f6787558a83219edf8f011cffe743e2431dc22e0789|
| scripts/qa-native/protected-admission-result.mjs |6690|abaf098879d55352c9152599c102c850b8f1208014e2ac8435710518d63a5bab|
| scripts/qa-native/protected-admission-checks.mjs |10102|79a0d410419202ed6aa981c4994864b390334222c9d9f24a7229cc73bbc12aa0|
| scripts/qa-native/protected-admission-result-checks.mjs |6484|ad735b43107a222c25011d3978d90d2444f68fd70cb8c4dec79ef2c026f0d7bc|

The five other owned files rehashed unchanged:

- operations.registry.template — 708899cb60c77e726c2b2f6af691584c3400a45c2355ee49aabcb9b031bbc272
- protected-admission.mjs — 8b350f4357b29773cc6e0e0a0edef31872cc14ec29e32b89756dbb4d876134bc
- qa-context-assembly-v2.py — 944f4d846743d0fcb9962146eddacb4a23c27b944404dc8f4e5c0b01e72db499
- dispatch-books.mjs — cbcd2de8550b99a534e3e21f2c630e95a8b8c21d0374f3bea204a102bc0312df
- deployed-host.candidate.mjs — b7e8604f01a7a791ccd9bb6995d4545b4be25208d4feae3019cd2d25e279d9fb

**All current-delta controls and JavaScript syntax checks are UNRUN.** The earlier eight constructor-only parse observations applied to the earlier hashes and are not reused as validation of these changed bytes. No permitted nonexecuting syntax tool outside the quarantined kernel was available; no Node process, replacement kernel or wrapper was started. Source inspection/hashing is not a test PASS or proof these review findings are resolved at runtime.

Production remains disabled/refusing pending independently reviewed current-source native artifacts, measured closure/installation fit, protected birth/copy/readback and actual private original-host full-stream/EOF/duration association. Existing Proxy/reflection limitations remain unchanged. Old failed/UNKNOWN/native/compiler evidence and all session scratch are preserved. This checkpoint grants no execution or release admission.
