# Books Arranger — private runtime COPY candidate, 2026-10-20

Status: BLOCKED after pinned review; revision2 below is authoritative. Producer CLI refuses before setup. COPY NOT RUN. No private Git directory or proof was created. No Git/cmd child was executed. No canonical checker, global hook, installed runtime, app catalog, media or iTunes was changed.

## Concrete review inputs

- Project candidate: scripts/provision-qa-runtime.mjs, 22586 bytes, SHA256 bdb0fdc3b0f591cf6ba0f3d8b68233cef28ee5a6abcbf7ed4b7fb0370aa002bb.
- Focused tests: tests/qa-runtime-provision.test.mjs, 6140 bytes, SHA256 58ad2c3cbe91cb0dd393200d8f6e3506ac545b8a77934b52db38f46dd7bf02e8.
- Actual complete plan: C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/qa-context-prep-20261020/runtime-copy-plan-v1.json, 6827 bytes, SHA256 f94b85154a5e274d5103bb69198503f48bf4d5047ff59b3b1d4f86176773c972.
- Prior static PE observation remains immutable: C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/qa-context-prep-20261020/git-static-closure-review.json, SHA256 14c2e640d7e59901554bb239e5e16085714c2d24af00fbd9293196142abb587b. That observation is NOT execution clearance.

The plan freezes six actual installed files, all measured with readonly native held handles and complete FindFirst/NextFileNameW alias enumeration. Its source hashes, volume serial, file index, modification time, size and exact alias lists are literal. Total copy is 7,026,668 bytes; quota is 7,340,032 bytes (7 MiB), not a whole Git installation. Core plus four directly imported non-OS DLLs total 6,686,700 bytes. The sixth file is the shell needed by the separate later npm/checker route.

| File | Bytes | Links | Volume | File index | Modified ns |
|---|---:|---:|---:|---:|---:|
| git.exe | 4413272 | 4 | 2803554832 | 35465847065620174 | 1791227498000000000 |
| libiconv-2.dll | 1141951 | 2 | 2803554832 | 63894819713396577 | 1791215398000000000 |
| libintl-8.dll | 298164 | 2 | 2803554832 | 67553994410635110 | 1791215398000000000 |
| libpcre2-8-0.dll | 706022 | 2 | 2803554832 | 50665495807995775 | 1791215398000000000 |
| zlib1.dll | 127291 | 2 | 2803554832 | 168884986026471627 | 1791215398000000000 |
| cmd.exe | 339968 | 2 | 2803554832 | 1407374889573946 | 1790135453992031700 |

Exact source aliases (these are readonly source observations, never deletion targets):

- git.exe: “C:\Program Files\Git\ucrt64\bin\git-receive-pack.exe”; “C:\Program Files\Git\ucrt64\bin\git-upload-archive.exe”; “C:\Program Files\Git\ucrt64\bin\git-upload-pack.exe”; “C:\Program Files\Git\ucrt64\bin\git.exe”.
- libiconv-2.dll: “C:\Program Files\Git\ucrt64\bin\libiconv-2.dll”; “C:\Program Files\Git\ucrt64\libexec\git-core\libiconv-2.dll”.
- libintl-8.dll: “C:\Program Files\Git\ucrt64\bin\libintl-8.dll”; “C:\Program Files\Git\ucrt64\libexec\git-core\libintl-8.dll”.
- libpcre2-8-0.dll: “C:\Program Files\Git\ucrt64\bin\libpcre2-8-0.dll”; “C:\Program Files\Git\ucrt64\libexec\git-core\libpcre2-8-0.dll”.
- zlib1.dll: “C:\Program Files\Git\ucrt64\bin\zlib1.dll”; “C:\Program Files\Git\ucrt64\libexec\git-core\zlib1.dll”.
- cmd.exe: “C:\Windows\System32\cmd.exe”; “C:\Windows\WinSxS\amd64_microsoft-windows-commandprompt_31bf3856ad364e35_10.0.26100.9549_none_26c71961ca689840\cmd.exe”.

## COPY contract and refusal behavior

The outer Node entry accepts only --plan <absolute path> --plan-sha <SHA256>, fixed Windows x64 installed Node, project cwd, a bounded <128 KiB ordinary plan and exact fixed output C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/git-ro-v1 plus its adjacent proof. It rejects any existing target/proof before its first output operation. Six exact installed source names/paths are mandatory. No arbitrary command, argv, output root, file list, shell launch or executable entry is exposed.

Before importing Koffi or the existing native Job owner, it checks the complete existing Node/Python/Koffi/addon manifests and five bootstrap pins. It repeats full verification while retaining native readonly no-write/no-delete leases for those ordinary inputs and ancestors. These four runtime manifests reuse the earlier six complete measured runtime pins; no runtime tree is duplicated. The bootstrap pins include this producer, Node/Python and the unchanged bounded-check/bounded-child helpers. Windows kernel/loader is an explicit machine trust boundary, not falsely represented as a complete hash-pinned OS tree.

The child is isolated Python -I -S -B under existing reviewed runOwned/private Job with remaining time from the same total 600000ms deadline. The worker does not import or execute Git/cmd. The only hardlink exception is its fixed source reader: it holds each exact installed source and every declared alias readonly with FILE_SHARE_READ, pins ordinary ancestors, rejects reparse points/additional streams, verifies native identity + exact full alias set + hash, and repeats checks before writing and before receipt. This does not change general checker/deletion/audio nlink==1 floors.

It creates a new ordinary target directory and every file with CREATE_NEW, checks exact bytes/quota during the copy, flushes, closes each writer, re-enrolls a readonly native handle and checks file identity across that gap, nlink==1, ordinary shape, default stream only and full readback hash. It rejects unknown output entries or changed source topology. The adjacent proof is CREATE_NEW, bounded, flushed and read back, binding plan SHA + all six source/output facts. Unknown/partial outputs are preserved on failure and have no valid receipt; the entry never deletes installed sources, aliases, destinations or scratch evidence. All handles must close and the private Job must report zero active/unsignaled children before the outer success receipt. Receipt explicitly says execution_permitted:false.

## Measured tests and limits

Isolated native-owned test invocation used installed Node to run --test tests/qa-runtime-provision.test.mjs under runOwned timeoutMs=600000. Result: 17/17 Node tests passed; actual Python worker AST compiled; 14 in-memory transition cases exercised the actual extracted check_plan/copy_runtime functions. Negative controls cover execution admission, target escape, quota, missing/extra/source/hash/alias/identity changes, incomplete/wrong runtime, bootstrap pins, deadline, and injected freeze/absence/create/deadline/write/flush/readback/source-recheck/output-enumeration/proof faults, changed source bytes and source growth. Native result: ok=true, closed=true, forced=false, active=0, retained=7, unsignaled=0, zero=true; elapsed 437.8825ms. No installed source was opened by those tests and NativeCopy was never instantiated.

These tests validate the contract/transition flow, not the native Win32 implementation or real alias freezing. Native same-name replacement, actual short writes/flush failure, stream races and cancellation cleanup still need reviewer-approved synthetic native fixtures before copy clearance. No copy-only clearance is inferred from pure tests.

## Separate unresolved execution boundary

Direct PE imports of the five Git files were recursively resolved and no delay imports observed. Git imports LoadLibraryExA/GetProcAddress; DLL literal scans cannot prove all reachable dynamic loads for the five builtin commands. libintl GetModuleHandle/GetProcAddress and possible optional iconv loading also require a reviewed reachable-path argument or constrained loader execution evidence. System32/API-set trust, cwd/PATH search rejection and local Git config/include/filter/helper closure remain unresolved. This producer intentionally permits COPY ONLY, even after a successful copy receipt. Neither this plan nor an ordinary private directory admits Git execution.

Git/checker invocation changes are proposed in BooksArranger_QAContext_2026-10-20.md. They are not implemented or approved. No global dispatch route has been deployed. Persistent Books dispatch must survive deletion of the session scratch and fail closed for missing Books context, while preserving the pre-existing non-Books fallback byte-for-byte; or an explicit temporary deployment must CAS-restore its exact original bytes before cleanup. No dispatch may remain dependent on deletable scratch after Jane gives Sergei the session scratch path to remove.

Final application/check graph and source snapshot are not frozen. Primary Ender reports a continuing 60-pattern graph; every source/harness/runtime/checker pin must refresh after the final reviewed graph. The two earlier qa-context-assembly-v2.py and qa-owned-guardian-v2.mjs candidates were preserved unchanged in this task.


## Revision 2 — pinned review response and finite launcher STOP

This section supersedes the earlier executable-candidate description. Review pinned/pushed at commit125c9b77dad18c6e9afc70a1cf35d07a36a8b9f4: BooksArranger_QARuntime_Review_2026-10-20.md. Current producer CLI unconditionally throws ADMISSION_BLOCKER before timer setup, runtime reads, Koffi import, native initialization or any target operation. It has no supported execution route. It cannot be enabled by an argv/environment flag. The deferred implementation below that refusal is review material only.

Current files:

- scripts/provision-qa-runtime.mjs:25338bytes, SHA2565e260049446b9daf5d7e693d6660a3fc71f60f9635285d74fe6c8eb1fc866c8e.
- tests/qa-runtime-provision.test.mjs:6417bytes, SHA25614bd4c40cfd5cfe26f40ec3d310f11cf603b43e8803f6e5e96ecea16045181eb.
- Current isolated result:18/18 tests pass, including fail-closed main with empty and plan-shaped argv, plus the14 actual extracted Python copy-flow cases. Python worker syntax compiles. No NativeCopy method was invoked against Windows and no installed source was opened by these tests. Native owner result closed=true, active0, retained7, unsignaled0, zero=true, elapsed470.7908ms. Evidence shared/qa-context-prep-20261020/provision-revision2-pure-tests.json.
- Earlier f94b8515 runtime-copy-plan-v1.json remains preserved immutable evidence; its producer hash references revision1 and is STALE for revision2. No replacement executable plan is issued while admission is blocked.

### Independent directory ownership correction

Removed CreateDirectoryW followed by ownership-establishing name reopen. Deferred worker now invokes NtCreateFile on the already-held fixed parent handle with one fixed git-ro-v1 basename: FILE_CREATE(2), FILE_DIRECTORY_FILE|FILE_SYNCHRONOUS_IO_NONALERT|FILE_OPEN_REPARSE_POINT(0x00200021), read/attributes/synchronize access, FILE_SHARE_READ only. It requires success and IO_STATUS_BLOCK.Information==FILE_CREATED(2), immediately retains the creation-returned directory handle, records native volume/file-index identity and keeps that no-delete/no-write lease through output/readback/proof. A subsequent name lookup can reject an identity change but cannot establish/adopt ownership. verify_root compares the birth handle and current name to that identity before file creation, readback, final enumeration and proof.

Microsoft's [NtCreateFile contract](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntcreatefile) supplies creation-returned handles and RootDirectory-relative names; the flags/returned FILE_CREATED are explicit. This fixes the design's creation/reopen gap, but the native implementation remains unexecuted and requires Senua review plus authorized synthetic native fixtures. No claim of native clearance follows from pure tests.

### Actual ACL/trust measurement

Exact read-only evidence:
C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/qa-context-prep-20261020/launcher-acl-observation-v1.json
SHA25672b2b8fe550f8b5c1b9ba8554279c71cf19bec2c53904733bbd4fffb4f8ed7ca.

The observation uses native GetNamedSecurityInfoW/GetAce/GetSecurityDescriptorControl and SID strings without account/network lookup, plus ordinary stat identities.18fixed paths were inspected. It ran as a read-only bounded observation under existing native runOwned; active0/retained4/unsignaled0/closed=true. That observer route is engineering evidence, not admission of the producer or proof of an immutable bootstrap.

Observed Node install directory/executable owner Administrators(S-1-5-32-544), ordinary nlink1; Users and Authenticated Users allow0x1200a9(read/execute), Administrators/System full access. The bounded-check/bounded-child source files, their studio ancestors, Koffi package/index.js and actual @koromix/koffi-win32-x64/win32_x64/koffi.node grant Authenticated Users(S-1-5-11)0x1301bf(Modify, including write/delete). Their observed DACLs contain no denying ACE. Their owner is the local user SID recorded in the evidence. This is sufficient to reject the claim of immutable installed ownership runtime; it is not presented as a complete effective-access proof for every possible restricted token. kernel32.dll is TrustedInstaller-owned, nlink2, explicitly within the trusted Windows OS loader boundary rather than the ordinary runtime floor.

STOP: installed Node alone does not protect workspace-writable ownership JS/native addon or their ancestors. Hash-then-import still has a mutation gap. createPrivateJob in existing bounded-check.mjs itself executes createRequire(Koffi) and loads kernel32 before creating the private Job. It cannot provide pre-import native freeze. Its Job controls released children, not its own earlier setup. A JS timer cannot preempt blocked synchronous setup reads. No inspected existing trusted launcher provides all promised guarantees. No ACL, installed file, global hook or other studio was changed.

### Concrete bounded alternative proposal — NOT BUILT, NOT DEPLOYABLE

Technical choice required: retain STOP, or commission a separate finite protected-launcher component. Do not treat this outline as a ready human approval artifact. The exact proposed persistent location is C:/ProgramData/StudioIlluminati/BooksQA/v2/ (not session scratch or the broadly writable studio tree). Required files are a small native watchdog executable plus its reviewed source/build recipe; one fixed Books launch entry; an immutable copy of the exact reviewed bounded-check.mjs and bounded-child.mjs; the exact87-file ownership-js and5-file ownership-native manifests and ordinary copies; a fixed operation registry; pinned source/runtime/helper manifest; install/ACL verification record; and original global-entry bytes/hash plus CAS deployment/rollback journal. Installed Node remains C:/Program Files/nodejs/node.exe and its complete previously measured manifest. No Git executable, app runtime, whole dependency tree or media is copied by this bootstrap provisioning proposal. The previously measured bootstrap source pins are inputs for review, not permission to import them while writable.

Protected creation procedure, to implement/review separately: a trusted elevated installer checks all persistent ancestors against Administrators/System ownership and no untrusted add/delete/rename/WRITE_DAC/WRITE_OWNER rights; refuses unknown existing v2 roots; atomically creates an ordinary v2 root and CREATE_NEW bounded files; freezes exact reviewed input bytes/aliases before ordinary copy; verifies hashes/native identities/default streams and full exact enumeration. It disables inherited writable ACEs and gives Administrators/System full control, ordinary users read/execute only, with no Authenticated Users/User Modify/Write/Delete/owner-control grants. It then verifies DACL/owner/ancestor identity on the exact final objects and records the result. No ACL repair of the current studio/QuickLaunch directories is proposed. Installer/new-protected-root code, complete runtime-loader/ACL proof and packaging are UNBUILT; no admin action is requested or authorized now.

Outer watchdog requirement: a reviewed fixed native executable using the Windows OS trust boundary, no Koffi/JS import before ownership, creates a kill-on-close no-breakaway Job, creates the exact pinned Node child suspended with the fixed launch entry/operation/plan/hash, assigns and retains it, then releases work. It enforces one600000ms absolute admission deadline covering all released runtime/source hashing, imports, copy work and descendant closure, reserves drain time and requires native zero-active plus retained-handle signaling before success. Hash/manifest/ACL validation performed by the protected launch entry is therefore inside the already-owned child. No arbitrary executable/argv/cwd/env/shell operation is exposed. The native watcher's own Windows loader/startup is an explicitly trusted base; if the requirement includes enforcement against a stalled trusted watcher startup itself, an independently trusted pre-existing external watchdog is required. None was found, so no claim of an end-to-end externally enforced bound is made. Native watchdog source/toolchain/build/negative tests and exact binary pin are UNBUILT and require separate infrastructure scope; a second Node wrapper does not fill this gap.

Global Books dispatch, also UNBUILT: a protected persistent entry classifies the exact tool envelope/Books operation before reading any scratch context; non-Books input forwards unchanged raw stdin/stdout/stderr/exit to the preserved original global fallback. Missing Books scratch/context/runtime refuses Books only. Register separate exact QA/copy/pack/release operation contracts only after each code/owner contract exists and is reviewed; no generic allowlist and no migration route before its entry exists. No new dependency on another studio is introduced. Existing global C:/Users/AnGeLZzZ/.codex/hooks.json and current runtime-repair-20261018 hook/fallback remain byte-for-byte unchanged now.

Required deployment approval, only after concrete source/binary/manifest/installer/registry/global diff and Senua review exist: permission to create this exact protected persistent root/ACLs, install the exact fixed launcher closure and CAS-change the single reviewed global Books dispatch entry. No permission for current studio ACL changes, arbitrary shell execution, Git execution, media migration or iTunes would be implied. Because the installer/watchdog/dispatch artifacts are presently unbuilt, there is no executable deployment proposal to approve today.

Rollback/lifetime: keep complete original global entry bytes/hash and install journal in the protected persistent root, not scratch. CAS-restore only if the installed entry still matches its approved hash; otherwise stop without overwriting later edits. Revalidate original fallback before removing the accepted Books entry. Disable new Books operations before any protected-runtime removal; remove only exact manifest-owned files/empty root through a separately reviewed ownership-safe uninstaller. The persistent dispatcher may instead remain to fail closed when session scratch is deleted; unrelated fallback must still work. Session scratch remains C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20 for Sergei to delete after Jane's final handoff. Nothing deployed may depend on that deletable path after cleanup except a Books context whose absence is explicitly handled as a denial.

All runtime-copy/loader/config isolation work remains blocked. Existing canonical helpers, earlier two QA candidates, app code, Git, settings, catalog and media were untouched in this revision.
