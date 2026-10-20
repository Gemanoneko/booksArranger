# Console helper and read-only collector — source review

2026-10-20. Three-file SOURCE review under d71e0a82c8eaa9c248c233df4d13e3fc4c2d4ffa design. Implementation doc SHA256 `d073d7bae140e7bf3896b2fa72986b50942b73d3957548f4e0ffbaab79e254d5`. No System32/native/process/PID probe, tests, compiler, source/global/app/data change performed by reviewer. Not a release/formalQA verdict or collector/nativegroup admission.

## Findings

**Major — discovery capability can authorize an unreviewed OS-file baseline.** console-companion.mjs acquireConsoleCompanion permits expectedFacts omitted for collector discovery, but its returned acceptImage still accepts the exactpath after revalidation. This contradicts the reviewed policy that only separately reviewed immutable expectedfacts may activate the companion exception. The positive47pure fixture explicitly calls acceptImage on an acquisition without expectedFacts, so the gap is encoded as intended behavior rather than tested against. Future integration could omit expectedFacts and silently adopt the currentfile.

Finite correction: discovery acquisition may provide descriptive proof/revalidate/checkedclose ONLY. Its acceptImage must unconditionally refuse unless expectedFacts was actually supplied, own-data validated and matched to the acquired immutable facts. Alternatively separate discovery/acceptance capabilities without a generic policy framework. A missing/null/malformed/drifted reviewed proof must never gain policy authority. Keep the collector in discovery mode and preserve its stdout-only fact behavior. Add negative discovery→acceptImage refusal and a positive supplied-matching-reviewedfacts→acceptImage case; no root/supervisor/controller/worker substitution, changedfacts, leaseexpiry or closedcap may accept. Source held pending ruling/pin; no exception is activated today.

**Minor — own-data validation is less strict than advertised.** shape uses Object.keys/Object.getOwnPropertyDescriptors without proxy rejection, prototype validation or symbol-inclusive exactkey checks. Proxy traps may execute, symbols/nonplain prototypes can survive; volume64/creation strings and attrs/links also lack exact native uint64/uint32 bounds. Expectedfacts ordinarily comes from parsed pinnedJSON, so current typednativebackend path does not exploit this, but the exported proof validator should not claim the existing strict own-data contract. Use the existing bounded own-data approach: reject proxies/getters/nonplain/symbol/extra fields without invoking traps; bound native integer strings/masks/counts and array shapes, no coercion. Meaningful malformed/proxy/getter/overflow tests required if correcting this contract.

**Minor — successful revalidation lacks a final deadline/reserve check.** check runs before native operations, but an EOF/native final read can finish after reserve expiry and revalidate/acceptImage can still returntrue. CollectorMain has a final pre-stdout deadline check, so this is not currently a false successful collector exit; future policy consumers should not receive an expired acceptance. Check the original reserve again after the final validation/hash and before returning a policy acceptance/acquisition; no new deadline or native retry. Inject a fake clock crossing reserve on the final read/close, and keep actual external ownership as the blockingIO safeguard.

## Source/native surface reviewed

Paths are literal C:\Windows\System32/conhost with bounded nativeGetSystemDirectory equality, exactly3ancestors+file and16MiB/64KiB reads. Actual source escaping/prefix lengths were checked. Native opens are OPEN_EXISTING/read-only/shareREAD/nullsecurity/noninherit/OPEN_REPARSE_POINT; no write/delete/process primitive is exposed. File full128/volume/birth/size/link facts, held path comparisons, defaultstream enumeration and hash are compared; reverse checkedclose attempts every retainedhandle. Stream enumeration has a cap and checkedFindClose. Dedicated positiveOSlinkcount remains local; no general nlink1/runtime/deletion guard is changed. No actual native behavior/sharing proof exists;47controls are API/sharing fakes. A private real hardlink test must remain separate from actual System32.

## Missing exact invocation boundary — no command admission

The implementation doc gives only a command TEMPLATE with a future13digitdeadline. It explicitly leaves actual numericdeadline, original external owned-operation route, cwd/environment/runtimepins and stdout capture/checkedownerclosure to later review. No literal complete collector invocation/request or externalobserver source was supplied. Therefore this review cannot admit ONE collector command now even apart from the Major.

After correction provide the frozen3source/test pins, pure controls, exact fixed readonlycollector request/deadline/cwd/env/runtime/sourceadmission and original externalowner/observer invocation. All setup/startup trust and blockingIO boundaries must be honest; original owneddeadline must include teardown/logging margins without wrappers or extension. Actual success must jointly include bounded captured stdout facts, exact source/runtime/inputjoins, actual observedcollector exit0/EOF, checkedfile/directory/enumerator closure and original SAME-instance nativeowner closure—not exit0 or checked_closeJSON alone. No System32probe/nativegroup/preparation/compiler granted here.

## Exact reviewed pins and next scope

| Source | SHA256 |
| --- | --- |
| console-companion.mjs | `2c5ee66fb2202bb75f6ab43ea0079d5405b7e707c4a585f472986f991405fdeb` |
| console-companion-collector.mjs | `2935ce4511a642027b9853db0d3720a0610aa3662c87511a8bf8c8366d1843c3` |
| console-companion-checks.mjs | `18beb04419be4c186d57070d55f8f0b96176ff384010d0befb44e1f00d07fb6d` |

Fix only this finite new helper/collector/test scope after Sully pins the review; preserve other agents’ v3source/policy work. No consumerexception or fact baseline is admitted. e275 original outercheckedclosedtrue/groupFAIL remains; older UNKNOWNgroups/compiler NO RESULT unchanged.
