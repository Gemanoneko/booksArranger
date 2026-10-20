# Retained-object v3 implementation and consumers — scoped source review

2026-10-20. Static SOURCE-only scope: packet `54c1d5e68a8bc2812df2b7d8d285314df82460086170c8145b5df9fec91f42f1`,25-file snapshot/11declared deltas under retained-object ruling0270340dc5e781fae391de2d96fe10d23f009602. No tests/imports/process/native/probe/preparation/compiler/global/app/data action performed by reviewer. Console collector/facts/policy integration is outside this snapshot. No invocation permission or release/formalQA verdict.

## Findings

No new Critical, Major or safety-floor finding in the bounded v3 delta. One Minor diagnostic-contract limitation:

**Minor — diagnostic capture is typed descriptive serialization, not native-v3 semantic validation.** diagnostic-capture.mjs objectProof.schema/image_basis remain bounded generic strings; clone permits absent known fields and encodeDiagnostic does not call validateNativeSnapshot. Thus a missing/unknown/legacy proofbasis can be preserved with capture_ok=true if the rest is serializable. Legacy observed.image alias, unknown extra fields/getters/proxies are rejected as tested. Actual owner/normal/negative/final acceptance paths use strict validateNativeSnapshot and refuse bad native-v3 semantics, so this is not a closure bypass. Keep reports/UI/docs explicit that capture_ok proves capture only, not native-v3 validity. If exact diagnostic proof semantics are intended, add a separate explicit bounded enum/required-field check and meaningful missing/wrongbasis tests without normalizing bad input or inventing authority; do not assert existing serializer already provides that check. Sent Sources; no fix performed here.

## Contract verified

- FULL fresh native image/PID/positiveuint64creation/originalJob admission remains for supervisor/new members; only admitted immutable identities beside original lexical handles enter retained path. SupervisorfixedNode/no-kill rejectedhandle rules stay.
- Listed retained members: actual waitfirst, signaledlisted refuses/noPIDreopen, samehandle freshPID/creation and current exactJob check. Final retained members use actualwait then samehandle freshPID/creation for both live/terminal; absentlive remains unsignaled/nonzero. No retained image API/errorfallback/retry, no pathfreshness claim.
- Native owner-v3 observed members use exact image_path_at_admission/objectproof-v2 uniform admission-image-continuously-retained-object basis. Structural validator checks own-data/type/count/signal/listabsence/supervisor correspondence, rejects oldschema/image aliases, and never exports kernel continuity. CompleteJobzero/retainedsignals/EOF/SAME-instance snapshots/checkedclose/bounds remain independent acceptance requirements.
- Controller/observer/fixturemap actual joins use admissionpath and validateNativeSnapshot for normal and overflow/timeout paths. Supervisor/wire worker initialimage remains separate. Node-only per-member expectations stay exact; conhost is NOTallowed/filtered.
- Dormant build-observer/build-worker use admissionpath in their existing exactNode/toolchain image predicates; their admission stays disabled and the set is not widened. No compiler execution/policy approval follows.

## Test replacement versus lost coverage

Fresh developer receipt `74cf2628d16a931d7960745f1b589cefbbf4617533196c82ff39f97318f547f9` reports252 pure cases:50owner/51object/62diagnostic/75IDs/14plan.52→50 owner removes exactly the obsolete retained-list and retained-final fresh-image-failure cases. These are intentionally superseded by the explicit accepted live-object contract, not silently waived: new opaque-object controls cover imageAPIunavailable5/31 after admission with zero retainedimagecalls, fresh retainedPID/time failures in BOTHstates, membership/wait/query/handle lifetime failures, initial/new image failures, missingadmissionimage, sampled live→terminal and pathmutation labelled admission-only. Initial/new/close-newmember imagefailure diagnostics and first-versus-close error/no-kill controls remain in50owner. Source inspection found no dropped independent admission/closure safety check in those two replacements. Purefakes remain nonnative; unchanged broader suites/runtimepreflight were not rerun or re-certified.

## Source pins

All25 hashes stable before/after; final sizes/dev/ino/mtime match. Both implementation doc hashes and accepted design review match. The packet is exact full boundary, not an accumulated release commit-range certification. Eleven deltas:

| Source | SHA256 |
| --- | --- |
| build-observer.mjs | `35011efe50053641ac53f288604f4e2b649466edf5eb6e476d24e4ce10e558bb` |
| build-worker.mjs | `cb0057924ef95f515a077434c817d97afc252ba6f307fe53337616856c1e7e29` |
| diagnostic-capture-checks.mjs | `35e83184481308ca1b6a2789ca9d98f3c5b40eced89304bd744851ebb0fe5594` |
| diagnostic-capture.mjs | `4422e8a106b49041ed65b5b113bba2f5be1599dea7ae308f192cd12a8a9d64bf` |
| engineering-owner-checks.mjs | `3c40a9c0f7667e11eaa35657304d56007cb97b6ceee127037f210cc286ede96e` |
| engineering-owner.mjs | `f90898597497c0db5a9b5ac2d7f085ae2d63350406a93ec1fb2867592a67fab0` |
| engineering-terminal-checks.mjs | `5be3ab7d5d1e47b12ac93af8b890a29745bd694a2ab5527dcd2611092915bcec` |
| fixture-owner-ids-checks.mjs | `f63452e138f889bffd2d2d1a8148ec4193c971063f2f24f791f753cd524b9715` |
| fixture-owner-ids.mjs | `ea586614b177f0dfcadf985538aee92fd4183f7e3d376cacd3d97d55db67724f` |
| native-fixture-controller.mjs | `69995859b35193cde7139ed15c1747e4c28a5a6f8838f9c159cbd676980cae42` |
| native-fixture-observer.mjs | `659e06f43d38f140d107799197dbbf4e65afefd67de8cf328426d5f40a693fd5` |

## Planning limits and next source stage

Namespace planning provenance175101a8b2a290cc82a78f3733626cc596482b56a45a7783077c7bea887c0413 records one separately authorized existingREPL builtincrypto.randomUUID call yieldingc4435676-2c5c-4fe4-af84-6ca4b9e25474. It explicitly does not identify targetinstalledNode/version or claim native ownership; it supplies one public namespace, not fourinnerlabels or executable admission. No process/RNG call was made by reviewer. Pending9f73 disabled draft has noinnerlabels, execute_reviewedfalse/admissionzeros and is explicitly awaiting consoleintegration; its illustrative argv is NOTadmitted.

Scoped SOURCE acceptance only. Preserve thisv3 snapshot until owner findings handled/coordinated. ConsoleOSfacts+dedicatedreadonlyhardlinkproof/exactpolicy/sourceintegration and completefinalgraph/request review remain required. No preparation/nativegroup/compiler/probe/globalhook/app/data approval. e275 originalouter checkedclosedtrue/groupFAIL is not changed; olderUNKNOWNgroups/compiler NO RESULT remain.
