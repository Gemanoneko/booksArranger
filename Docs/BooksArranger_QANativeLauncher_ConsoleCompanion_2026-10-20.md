# Saved console-companion mismatch — policy proposal only

Read-only scope: saved owner-result5dba11e40ecd2f81fbc175e300e2deb971b2dd7b478afa6cb8ba833f0738946d, native-fixture-child.mjs74ecf4f54857e59da287c8044d77fc654928113f23deb86eb0cd998470481bb1, bounded-check.mjs3f7e6bc022fe9a34aad63340059bd0f975fad8948e1b770c0f7a3bd6e3c1038c. Three local files; no process/probe/source change. Current e275groupFAIL; original outer checkedclosedtrue/active0/retained14/unsignaled0/zero. Previous groups remain UNKNOWN.

## Exact saved evidence

Four of14 observed members have admission image C:\Windows\System32\conhost.exe. Each is signaled, same held-object terminal proof admission-image-retained-terminal, PIDcreationconfirmed=true and sample_list_absent=true:

| PID | Creation FILETIME |
| --- | --- |
| 46048 | 134369759198459224 |
| 93604 | 134369759197515284 |
| 94428 | 134369759201964066 |
| 100560 | 134369759202797797 |

Saved proof gives process admission path, not executable file ID/hash, signature, parentage, OS ACL/ownership or current-image proof. None is inferred. This is a latent policy mismatch; actual first refusal was a different member image-query error5, not this Node-only assertion.

## Purpose and actual launch options

Existing observer loops all observed images after validateOwnedResult/matchController; controller applies its equivalent Node-only assertion after returned inner native closure. These assert the expected fixture process graph, not a pre-execution sandbox/launch admission. Native assignment still separately requires the initial supervisor to be fixed installedNode; member Job/heldhandle/PID/creation/close authority is independent. Therefore permitting one explicit trusted OS console companion would amend fixture expectations and unexpected-image detection, not authorize arbitrary command execution. That scope must be reviewed explicitly.

Fixed child spawn already sets windowsHide:true,stdio:[ignore,inherit,inherit]; reviewed owner supervisor spawn sets windowsHide:true,detached:false onWindows,stdio:[pipe,pipe,pipe]. No parent attribution or uninspected supervisor-inner creation flags are claimed. [Node26.12 documentation](https://nodejs.org/api/child_process.html#child_processspawncommand-args-options) describes window hiding; it does not promise no console-host Job member. [Microsoft CREATE_NO_WINDOW](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags) explicitly concerns console creation and is ignored with DETACHED_PROCESS/CREATE_NEW_CONSOLE. No supported currentNode-option guarantee of eliminating conhost was established; changing flags or detached mode is not proposed as a guessed fix.

## Smallest proposed explicit policy

Under the existing TRUSTED INSTALLED WINDOWS OS assumption, retain fixedNode supervisor admission and all current native ownership/closure checks. Amend only per-member fixture expectation to fixedNode OR one specifically admitted OS console companion, never any executable/basename. The exact path must come from native GetSystemDirectoryW plus literal conhost.exe, resolve to the expected protected Windows system directory/defaultstream/ordinary file, and be bound to one held full native file identity+SHA/size before child release. Preserve that file+ancestry read/no-write/delete leases through group closure, and compare recorded admission paths exactly under native path normalization. Any changed/unavailable proof refuses. The current saved path alone is insufficient; these file facts were not collected.

No general signer/ACL framework is necessary if Senua accepts that explicit OS trust boundary, already used for Windows native APIs/loader. Native canonical system-directory fact is needed to avoid attacker-controlled environment/path; exact file identity/hash+held read fence binds the particular expected OS file and blocks substitution; current Job/process handles remain the authority for membership and closure. A signature/ACL inspection is an alternative additional trust requirement ONLY if the existing OS assumption is rejected, not silently mandatory here. No System32 read/probe was performed.

Legitimate OS hardlinks must not be treated as arbitrary source/runtime allowance: proposed dedicated READONLY OS-companion proof records positive linkcount and same fullfileID/hash and holds deny-write/delete on the fileobject across aliases. Whether this exception is acceptable is an explicit policy decision; general nlink1/runtime/deletion guards remain unchanged. If that boundary is not accepted, STOP rather than enumerate aliases/relax globalguard or copy System32. Later bounded fact collection needs separately reviewed exact GetSystemDirectoryW +held ancestry/file defaultstream full128ID/volume/size/hash/linkcount only; no executable launch, repair or broad system inventory.

## Finite policy controls before any native group

Positive: ordinary fixedNode-only graph; exact trusted/admitted companion with unchanged Job/retainedproof; legitimatehardlink dedicatedOS proof if explicitly approved. Negative: userdirectory conhost.exe, wrongsystemdirectory, reparse/ADS/pathalias, wronghash/nativefileID, missinglease/proof, changed OS file, unknown image, companion substituted for supervisor, process outsideJob, reused processidentity, unclosed/partial tree, and unsanctioned general hardlink waiver. Existing EOF/timeout/overflow budgets remain unchanged. Any future implementation/source or native invocation requires new independent review and instruction; e275 is not retried.
