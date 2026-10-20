# Direct-parent sharing: bounded isolation proposal

DESIGN ONLY. No source/native/process/probe/test/run or sharing-mask change. Actual00b8 remains FAIL; actual EBUSY holder and internal failing Windows operation remain unproved. Supplements ParentCache_Trace SHA7a588f66d032622c7d1a22f60d17dd38167b1a46f07106b62cd992d6607a3bc3.

## Documented mechanism, not runtime diagnosis

Current Leases.retain directory access0x81 is FILE_LIST_DIRECTORY|FILE_READ_ATTRIBUTES; native creation access0x100081 adds SYNCHRONIZE. BOTH use share1 (FILE_SHARE_READ only). The long-lived io retains fixture_root, branch's direct parent, through the attempted rename. Phase closing its branch/leaf handles does not close that independent parent handle.

Microsoft CreateFile documents that existing share modes remain effective until close and incompatible requested write access fails. The MS-FSA FileRenameInformation algorithm describes a destination-directory open for a nonempty path portion: directory-source DesiredAccess is FILE_ADD_SUBDIRECTORY, with read/write/delete sharing; failure of that parent open fails rename. FILE_ADD_SUBDIRECTORY shares the directory bit with FILE_APPEND_DATA; the MS-FSA sharing algorithm includes FILE_APPEND_DATA in its existing-open compatibility rules. Thus a destination-parent reopen needing that write-class right can conflict with our still-held parent lacking FILE_SHARE_WRITE. The new open's generous sharing does NOT override an existing denial. The same algorithm also has a relative-name path that uses the existing parent without this extra open, so not every rename necessarily takes this route.

Node v26.12.0 bundled libuv fs__rename calls MoveFileExW with MOVEFILE_REPLACE_EXISTING; libuv does not expose which internal parent-open path failed. Therefore authoritative sources SUPPORT the proposed direct-parent conflict mechanism, but they do not prove MoveFileExW took it or identify00b8's actual holder. Do not label EBUSY itself proof of this hypothesis.

Sources: [CreateFile sharing](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilea); [MS-FSA rename](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fsa/87f86c9b-6c2a-4803-84b7-131a74a434fa); [MS-FSA sharing](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fsa/8c0e3f4f-0729-49f4-a14d-7f7add593819); [exact Node26.12 bundled libuv fs__rename:2171](https://github.com/nodejs/node/blob/v26.12.0/deps/uv/src/win/fs.c#L2171).

## Smallest fixture correction for review

Isolate ONLY the namespace test one level below a phase-owned container:

fixture_root/namespace-case/branch/leaf

Use phase's existing native creation operations for namespace-case, branch and leaf; capture the entire original full128/birth directory proof and require rename-while-held denial exactly as before. Then checked-close EVERY phase handle, INCLUDING namespace-case, before renaming branch -> branch-original and creating the replacement branch. Long-lived io continues to hold fixture_root/input/evidence/runtime leases; it MUST NOT acquire namespace-case or descendants before substitution. The direct destination parent is now the closed phase-owned container, while the work-security root remains held as an ancestor. Never rename namespace-case itself. Dedicated replacement Leases rejoins the original proof and MUST refuse the changed branch birth/native identity; unrelated errors cannot count as that positive assertion. Cross-close record case retains its original exact fact comparison and order afterward. All current directory/path bounds apply; no mask relaxation, lease release, delay, retry, expected-EBUSY waiver or new owner.

This layout removes the known fixture-owned DIRECT-parent sharing overlap without claiming it diagnoses the historical OS failure. If the isolated rename still fails, retain the bounded stage/error/close diagnostic and fail; do not add increasingly permissive fallbacks.

## Finite source/native controls

Source delta: native-fixture-controller.mjs namespace routine only; its focused launch/plan or NEW import-safe namespace checks as explicitly owned after review. No build-worker, companion, owner, dispatcher or C++ edit required. Pure fake controls must prove exact create/denied-rename/full-close/successful-rename/replacement order; container close failure prevents mutation; io cache excludes isolated parent; original proof covers container+branch+leaf; replacement rejection specifically comes from original birth/identity mismatch, not generic IO failure; namespace error remains failure; cross-close assertions unchanged; path overflow refuses. Require descriptive stage/error diagnostic if actual rename fails.

Future admitted native evidence must independently prove held denial, checked phase closes, isolated unheld rename SUCCESS, exact replacement identity refusal, cross-close native facts, remaining two owner cases and final companion teardown within original bound. No present native result proves this proposal. Independent review precedes source implementation and any new preparation/run. Previous source hashes and failure evidence remain preserved.
