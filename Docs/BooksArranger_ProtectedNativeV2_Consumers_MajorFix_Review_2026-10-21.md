# V2 consumers — three-Major correction review

Senua, opus review tier,2026-10-21. **ALL THREE PRIOR CONSUMER MAJORS CLOSED BY SOURCE INSPECTION; BOUNDED FIVE-FILE DELTA ACCEPTED.** No new Critical/Major/Minor finding in this delta. No syntax/test/native/host/QA/release clearance. The native source findings15641ffc55decbd92006630603fcb78fdc8cfcc3329ae2b7e318aa2eaf8ed233 remain separately owned and unwaived.

Reviewed committeded27f8ccdb9baad14af617aa00608f2e9c2578b3 correction description5853B/084c3dbe640f37802d2222e2180994ce09432fbb5a56f9ffcd224c0487fcd1e6 against prior complete ten-file review55a9d35bb120ef106f9be0ad7583df6c234fe2f5f161fabfb3ae80d76381158e. Independently read the five changed sources/controls and rehashed all ten owned files. Changed/current pins match exactly:

| scripts/qa-native file | SHA256 |
| --- | --- |
| launch-books-qa.mjs |04c57f79cde833e90bf57d3459d2445cd1ac284eab43be7cad13fa0e7d59c723|
| provision-protected.mjs |ab4fe3a0a02aa08ab84d5f6787558a83219edf8f011cffe743e2431dc22e0789|
| protected-admission-result.mjs |abaf098879d55352c9152599c102c850b8f1208014e2ac8435710518d63a5bab|
| protected-admission-checks.mjs |79a0d410419202ed6aa981c4994864b390334222c9d9f24a7229cc73bbc12aa0|
| protected-admission-result-checks.mjs |ad735b43107a222c25011d3978d90d2444f68fd70cb8c4dec79ef2c026f0d7bc|

Other five owned files rehash to the prior accepted baseline: registry template708899cb..., PRE8b350f43..., assembly944f4d84..., dispatcher cbcd2de8..., deployed-host b7e8604f.... No change is attributed to a historical syntax observation; all current-delta syntax and controls are UNRUN.

## Closed findings and controls inspected

**Manifest alias Major closed.** Duplicate lookup and insertion now use the same backslash-to-forward-slash/lowercase key. Original member/root data are not rewritten and existing relative/absolute/traversal/colon/empty-component/hash/size checks remain. a/b versus a\\b in either order, case variants and identical or conflicting bytes are rejected as duplicate member names. Written fixture construction rehashes dependent source/context/guardian/policy/registry bytes, so these controls reach member validation rather than failing a stale digest. Single ordinary members using either separator are included as controls. No production/native alias proof is borrowed from this string normalization.

**Required policy inventory Major closed.** native-admission-policy.json is now mandatory alongside dispatch-policy.json and every prior required fixed file. It matches the emitted registry policy_path. Existing110-member/8MiB caps and disabled-only rules remain unchanged. Written controls cover each policy omission, exact count/byte boundaries and one-over refusals. These synthetic data controls do not measure actual artifact fit, ACLs, copied bytes or protected installation.

**Refused-first pending Major closed.** exercisePostBoundary's first expression consumes the supplied genuine opaque pending token, then validates binding/result/capabilities. Existing consumeFixturePending deletes that WeakMap entry before checking expected fields; wrong binding, malformed shape, nonzero/signal/nonterminal/EOF/time/frame/capability refusal cannot leave it usable for a substitute second result. A copied token cannot identify or consume the genuine private association. Observation acquisition/WeakSet replay tracking/checked close remains unchanged; no observation close is claimed when acquisition never occurred.

Thirteen written refused-first/then-valid sequences cover null/empty result, nonzero, signal, nonterminal, false/missing stdout and stderr EOF, over-budget original duration, terminal elapsed beyond original duration, malformed frame and JSON-copied Buffer data. Each second call must fail with replay. A separate wrong-first-binding then correct-binding case covers deletion before binding rejection. Existing success replay, copied token, wrong call and false origin controls remain. No sequence was evaluated and no fixture result supplies a real host association.

## Preserved authority and remaining gates

Twenty-field terminal order, nine raw-input digests, opaque payload/base64 rules, strict registry/policy/context schemas and acyclic sidecar construction are unchanged by these finite corrections. Production PRE/POST/dispatch refusal functions and non-Books host source bytes rehash unchanged. Canonical five checker helpers were not edited. Fixture functions continue to return authority/production/accepted false as applicable. Prior explicit Proxy/reflection/fixture trust limitation remains unchanged.

This source acceptance does not admit a command or enable production. Still required: current-source C++ corrections and independent source/consumer parity review; an accepted owned compiler route and native/fault evidence; measured bootstrap/install fit; genuine protected birth/copy/readback/ACL evidence; and actual private original-host call/full-stream/EOF/final-duration association. Current controls and syntax need a separately admitted execution route; the quarantined shared kernel is not a route. No copied frame/JSON receipt, prior73af engineering pass or complete-looking source report satisfies those gates.

Only this review was created. No shared-kernel call/reset/probe, candidate import/evaluation, test/native/process/compiler/RNG/media/Git/host/code/live action or cleanup occurred. Main Ender's independent C++ work, frozen M4B artifacts, older FAIL/UNKNOWN evidence and all scratch remain preserved.
