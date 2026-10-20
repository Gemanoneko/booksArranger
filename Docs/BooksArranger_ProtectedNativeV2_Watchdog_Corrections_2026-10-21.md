# Native V2 watchdog — four-finding source correction

SOURCE ONLY, frozen for independent closing review. Corrected sole code file `scripts/qa-native/books-qa-watchdog.cpp`:62,868 bytes, SHA256 `ed73ab95a16ddff4c6b84a508082848aa77d6c16510b4d4240ec1d382ee9d11d`, observed by ordinary read-only PowerShell chunk853314 exit0. No C++ syntax/compiler/control/native execution occurred. All counterexamples below are WRITTEN UNRUN. No source-control module was created, inspected, replaced or adopted; the older RPC-timed-out controls file and shared kernel stay UNKNOWN/quarantined.

Authority: source review15641ffc55decbd92006630603fcb78fdc8cfcc3329ae2b7e318aa2eaf8ed233 at ed27f8ccdb9baad14af617aa00608f2e9c2578b3; explicit monitor/shell amendment969a105c8c600fe0bc6aa65edab7951e546431252f7f7b3aa2c57f0696d2b8a3 and AmendmentReview0d613d7e17718aff4b69549ef412a26df0eef97bc6c7bda7818ffec18ccaa1d3 committed d069acdc3af909b6ff0e88b95125a91f58afd0fc. Original d7093f checkpoint and intermediate5b754a17 tree/UUID-only checkpoint remain documented; no historical outcome is upgraded.

## Exact correction map

| Finding | Source correction | Authority preserved |
|---|---|---|
| Major1 monitor waits behind worker lock/close | Owner::timeout performs ONE TryAcquireSRWLockShared. False reads no Job field; true inspects/terminates only original lock-protected Job then releases. BOTH reach TerminateProcess(GetCurrentProcess(),124) with no intervening throwing check/IO/wait/close/retry. Unexpected return reaches MSVC __fastfail(FAST_FAIL_FATAL_APP_EXIT), never normal work. | Private noninherited KILL_ON_JOB_CLOSE; no extra Job handle/reference, stale-handle read, foreign PID termination, post-deadline grace or successful emergency closure claim. Normal checked work/monitor closes and original deadline unchanged. |
| Major2 tree canonical ordering | Inputs::tree converts every relative path separator to '/' BEFORE case-sensitive UTF16 ordering and record construction. | Original guardian canonical serializer, Unicode escaping, record keys/digests and native case/alias refusal unchanged. |
| Major3 declared cmd role outside seven roots | Only validated context.runtime.shell{name,path,sha256}, after raw context/runtime-sidecar equality, calls verifyDeclaredShell; ordinary exact SYSTEM_SHELL=C:/Windows/System32/cmd.exe only. Fresh held fullSHA/volume64/full128/birth/default stream/size/time/attributes/trusted OS ACL/primary ancestry are required. Dedicated sampled-image path deliberately calls the same held capability/hash, not generic file lookup. | Seven complete runtime root inventories unchanged. Only that role is exempt from root containment; no eighth tree, arbitrary OS image, WinSxS alias, conhost inheritance, copied shell path or write/delete authority. No public JSON/wire change. |
| Minor UUID grammar | uuid() retains lowercase hex/dash checks and requires version4 at14 plus variant8/9/a/b at19. | Same invocation grammar as accepted JS consumers; native registry/terminal cannot accept another version/variant. |

### Explicit shell-floor implementation

InputRole is private C++ state: Generic or DeclaredSystemShell. The fixed shell role accepts born links1 or exactly2; general file input remains links1. Input stores its role, full born facts/link count and exact observed native path. Every fresh hash/revalidation requires unchanged links, full native identity/birth, size/time/attributes, native path, default stream and effective trusted owner/ACL. Held primary file and ordinary ancestors remain shareREAD and survive through checked original work Job close. Protected OS checks use actual security descriptors, never pathname or a historical hash as authority.

On cached lookup the REQUESTED role is checked against born link count before returning: Generic cannot borrow a two-link cached shell. Repeated genuine shell refs reuse the same held object; a general manifest/member/ref naming that path with links2 still refuses. A generic guardian-plan file ref containing this OS shell is therefore not silently reinterpreted as the shell role; a future plan must respect the explicit role versus generic-ref distinction. Case-variant refs retain the existing same-native-object redundant-handle proof/checked close, but the shell role additionally uses strict fixed primary/native path equality; no casefold adoption of another object.

Only verifyDeclaredShell, called by runtimePath for the validated name shell, enrolls the capability pointer AFTER held SHA matches. Node/npm/other roles call the normal verifier. Sampled shell image must equal its exact native path, then full held hash/identity/link/ACL checks run again. Other images take the unchanged pinned-runtime path; they receive no shell exception. Normal input close checked-closes all retained handles and clears the capability pointer only afterward. No alias enumeration/uniqueness-of-name or physical cleanup authority is claimed.

Historical cmd links2/WinSxS observations remain dated context (QAContext9/156, QARuntimeProvision21/30), not new measured facts or an expected digest hardcoded here. No fresh shell/ACL/native query was performed in this task.

## Finite correction matrix — ALL UNRUN

This new independent document is the correction-control matrix. It neither imports nor replaces the UNKNOWN source-controls file and is not a test result or new execution mode.

| Boundary | Required counterexamples / expected result |
|---|---|
| Monitor false try | Worker owns exclusive lock while suspended/inside stalled close: ONE try returns false, no Job valid/handle read, no wait/IO/callback, self-only fatal path. Exact failure scope remains UNKNOWN, no success frame. |
| Monitor true try | Concurrent worker close cannot enter until shared lock released; only actual original Job is read/terminated; invalid/already closed/reused numeric handle is never used without lock. |
| Monitor native failures | TerminateJobObject false still reaches self termination; unexpected TerminateProcess return reaches fail-fast; failed flag cannot be reset into normal completion. No member enumeration/close/hash under lock. |
| Monitor completion | Existing original600000/2000reserve and frame-before-checked-monitor/control-teardown remain; late/nonzero/final-close failure cannot be accepted by POST. |
| Tree separators | Inputs ['a\\z','a0'] emit/order ['a/z','a0']; interleaved nested paths normalized before ordering. Native SHA must equal actual guardian canonical records. |
| Tree case/Unicode | Preserve case-sensitive UTF16 order; BMP and surrogate-pair paths versus U+E000 follow JS UTF16 comparison, not UTF8/codepoint order. Existing lowercase Unicode-unit escaping unchanged; case-colliding filesystem members still refuse. |
| UUID | Accept lowercase canonical v4 variants8/9/a/b; reject wrong version, wrong variant, uppercase, missing/misplaced dash, invalid length/nonhex. |
| Shell role | Exact name/path/context-sidecar/hash joins only; wrong field name, supplied generic ref/boolean, other OS/WinSxS/copied path, conhost and another runtime role cannot obtain the exception. |
| Shell links/cache | Role accepts1/2 only;0/3 refuse. General fresh or cached lookup at2 refuses; count drift1->2/2->1/2->3 refuses; genuine repeated shell capability reuses exact object. |
| Shell native identity | Same bytes/different full128 or creation, case-distinct object, reparse, extra stream, size/time/attribute/hash drift, unknown/unsafe owner or effective ACL refuse before release/admission. |
| Shell lifetime/close | Exact primary ancestry/file held through actual work closure; sampled native image revalidates same capability. File/ancestor/redundant close failure refuses; no alias gets deletion/write/move authority. |
| Scope | All seven complete inventories, original quotas, lifetime process-obligation count, retained-object two-pass logic, opaque child payload, terminal fields and actual-tool pending association remain required. |

## Ownership, verification and remaining STOP gates

Only the C++ file and this new document changed in this correction. Sources confirmed frozen consumers preserve the exact existing named shell ref in raw context/runtime equality and introduce no generic Windows/conhost trust. No JS/Python/template/canonical helper/product/source/media/catalog code was edited. No hidden test path or temporary protected-root override was added. __fastfail is a native MSVC intrinsic; actual selected-compiler/header correctness remains UNRUN, not a source-text proof.

Ordinary PS was used only for allowed source reading/hashes; it is not owned native or QA evidence. There is no compiler/syntax/pass result, no control invocation, no new fixture/namespace, no shared-kernel call/reset/provider, no host/trust/config/provisioning/Git/release action, and no scratch cleanup. Source is frozen for independent closing review, not self-declared Major closure.

Root additionally reports an external host blocker from official CLI0.162.1 research: PostToolUse.tool_response supplies a truncated output string, without strict original exit/time/session/result metadata. That does NOT implement the accepted original-call/EOF/duration/private one-use POST contract; Desktop remains unmeasured. This task did not independently reproduce that research or invent a new bridge. Production remains disabled/refusing. Compiler existence does not admit the hard-disabled current build operator. Genuine protected birth/copy/readback, current-source native build/fault evidence, measured closure fit, unknown conhost handling and actual supported host association remain separate gates; trust alone cannot manufacture them.
