# Fixed console companion — separate source implementation

2026-10-20. Ender SOURCE checkpoint under design/review pin d71e0a82c8eaa9c248c233df4d13e3fc4c2d4ffa. No actual OS/native/process probe, fixture, compiler, global/app/data change or policy activation. Existing25-source graph is unchanged.

## Scope and evidence

New sources only:

| Path | SHA256 |
|---|---|
| scripts/qa-native/console-companion.mjs | 2c5ee66fb2202bb75f6ab43ea0079d5405b7e707c4a585f472986f991405fdeb |
| scripts/qa-native/console-companion-collector.mjs | 2935ce4511a642027b9853db0d3720a0610aa3662c87511a8bf8c8366d1843c3 |
| scripts/qa-native/console-companion-checks.mjs | 18beb04419be4c186d57070d55f8f0b96176ff384010d0befb44e1f00d07fb6d |

Fresh in-process import after pure-kernel reset: consoleCompanionChecks returned passed47/nativefalse. Includes exact path/systemdir/root-role policy, positive dedicated nlink4, invalid native identity/hash/size/link/birth/schema/defaultstream, changed ancestry/content/ADS, initial failure cleanup, expired capability, checked-close failures, fixed collector argument rejection and MOCKED hardlink alias sharing refusal. Initial import found unavailable process global in pure host; direct-main guard corrected before fresh47pass. No Koffi/native factory was invoked. Actual private hardlink write/delete/rename proof remains unexecuted; general nlink1 runtime/source/deletion rules remain unchanged.

## Finite API contract

acquireConsoleCompanion(api,{deadline,expectedFacts?}) opens only fixed C:\Windows\, C:\Windows\System32 plus C:\ and computed literal conhost.exe. Native GetSystemDirectoryW must equal exactly C:\Windows\System32; alternate canonical spellings/roots refuse. Fixed read limits:1025 UTF16 path units, exactly3 ancestors +1 file, exactly one default stream, file0<size<=16MiB,64KiB read blocks. Closure reserve2s under caller absolute deadline, acquisition rejects beyond600000ms. Blocking native calls still require the separately reviewed external owner; this is not a hard standalone timeout guarantee.

The private capability offers proof() (defensive descriptive clone), revalidate() (same held handles/path/full128/birth/size/link/ancestry/defaultstream/fullhash), acceptImage(image,'member') (exact literal admission path plus revalidation), and close() (resource checked-close of all4 handles, reverse order, reports every failure). close() alone is NOT fresh-content or Job closure clearance. Consumer must revalidate through descendant/Job/EOF completion BEFORE closing, and treat any validation or close error as failure. No JSON object is a capability. Calls after close refuse. Reacquisition for a later fixture MUST supply the immutable reviewed expectedFacts, compare all facts, and retain new private leases before any child release. Merely parsing a prior receipt never permits an image.

Facts schema books-fixed-console-companion-v1 contains exact own-data fields: schema,system_directory,path,access,os_trust,file,streams,sha256,ancestry. file and each ancestry facts contain volume64,full128 file_id128,creation_ticks,attrs,size,links. The helper deliberately permits positive linkcount ONLY in this dedicated readonly OS lease. Native backend has OPEN_EXISTING/read-only access/shareREAD/null security attributes(noninherit)/OPEN_REPARSE_POINT. It has no write/delete/rename/process/RNG/signature/ACL primitive. Full native finalpath must exactly equal the fixed expected DOS path after stripping only the required native \\?\ prefix. Wrong alias never normalizes into eligibility.

This is installed-Windows trust, not executable authenticity/signature/loadedcode integrity or process parentage. All native owner member counts, PIDcreation, Jobmembership, waits, v3 admission-image object proof, EOF, deadlines and checkedclose remain external and unchanged. Node-only positive graphs remain valid. Root/supervisor/controller/worker MUST remain pinnedNode. Unknown images and missing companion proof refuse. Consumers have NOT been edited yet, so actual companion exception remains inactive.

## Collector source and proposed later invocation

Collector lazy native factory loads the existing exact Koffi engineering dependency only on explicit call. Importing source has no FFI side effect. collectConsoleFacts(api,deadline) acquires/revalidates, captures descriptive facts, checked-closes all native handles then returns books-console-companion-collection-v1 {facts,checked_close:true,limitations}. Checkedclosetrue describes ONLY these readonly file/directory/enumerator handles, never a process/Job closure claim. No OS/source/output file is created. stdout is one bounded JSON record (<16384bytes); stderr failure <=1024 message characters; external observer must bind actual exit/EOF/owner result to captured bytes. The collection is not plan admission.

Prospective literal command template FOR REVIEW ONLY:

    C:/Program Files/nodejs/node.exe
    C:/Antigravity Projects/Worktrees/Books Arranger/electron-m1/scripts/qa-native/console-companion-collector.mjs
    --deadline-unix-ms <one exact reviewed absolute13digitdeadline>

CLI accepts precisely those2 arguments; deadline >now+2000 and <=now+60000. Actual numeric deadline, outer fixed owned-operation invocation, cwd/environment/source3hashes +existing Node/Koffi/OS trusted engineering runtime pins must be separately frozen/reviewed before execution. No command/probe has been invoked. The owner must reserve logging/teardown inside its existing absolute budget; no new route or global allowlist is supplied here. No durable receipt backend or scratch adoption is introduced; existing observer may capture stdout after its actual checkedclose.

Next bounded step: independent source review of these3 files and exact later read-only collector request; then actual facts can be reviewed, and only then Sources may integrate immutable expected facts/private retained leases into observer+inner controllers. Pure/mock sharing controls do not prove Windows native sharing. Subsequent private native hardlink controls require their own admitted request and must never target System32. Current e275 remains groupFAILED with its own outerclosedtrue; earlier UNKNOWN groups/compiler NORESULT remain unresolved.
