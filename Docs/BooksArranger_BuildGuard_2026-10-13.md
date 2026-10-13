# Books Arranger guarded installer build

Developer delta, 2026-10-13; construction evidence, not installer acceptance.

API: scripts/guarded-io.mjs exports runNativeOwned({mode,root,script,timeoutMs:600000}) and validateChildLease({mode,root}). Fixed workers: scripts/build-step.mjs (build), scripts/release.mjs (release), tests/guarded-owner-probe.mjs (private probe). Bare --owned flags do not authorize: random stdin nonce, retained lease, exact live supervisor PID/creation/image and fixed command line are mandatory. Worker starts suspended, is assigned the native kill-on-close Job, then resumed. No PID lookup/tree kill is used.

Returned lease root is checkout; ownedRoot is root/build-cache/builds/UUID; deadline is Unix milliseconds; manifestPath is stable dist/release-artifacts.json; executables maps fixed retained Git/GH paths for release. Source, node_modules, release Docs/dist/artifacts and executable ancestries/files remain held through the operation. Publisher strips ambient credentials.

BuildTree retains ordinary native ancestors, rejects reparse entries/hardlinks, atomically creates directories with parent-handle NtCreateFile(FILE_CREATE), writes native CREATE_NEW handles. ZIP members are all preflighted for traversal/device names/duplicates/links/size before any write. Trusted runtime archive SHA pins and LGPL/license probes remain required. No recursive delete or adoption of existing folders occurs. Exact-manifest file disposition validates the entire set first, preserves unknown files/all directories, and never falls back to pathname unlink.

Private UUID staging/runtime/cache paths and dist/builds/UUID replace stable mutable output. Actual NSIS embedded app64 extraction is compared with the entire unpacked payload; ASAR version/source, backend version/full map, all runtime files, raw protected JSON, and three artifact hashes are checked before verified manifest emission. Dirty product source refuses emission. Stable manifest and runtime pointer use CREATE_NEW; previous candidates/pointers refuse before downloads. Accepted old-cache retirement/pointer CAS still needs integration, never sweep unknown output.

Runtime pointer: schema books-runtime-pointer-v1, build_id, root (new runtime tree), files (relative SHA256/size), manifest_sha256 (SHA256 of json.dumps(files,sort_keys=True,separators=(',',':')).encode()). Installed production uses bundled pinned Python.

Package owner must route pack to node scripts/build-step.mjs. Ender has locked 7zip-bin@5.2.0. Fetch/stage aliases route the same full guarded transaction; clean-dist preserves existing output.

Explicit trust limits: installed Node and pinned C:/Python314/python.exe are developer trusted bootstrap prerequisites. Node ancestry/hash check immediately precedes spawn; helper retains native ancestry/image before imports/mutations. No native addon closes the executable check-to-open swap window, so this is a documented trusted-launcher assumption. Dynamic builder writes use fresh UUID trees; root leases alone do not claim protection from arbitrary same-account malicious insertion into future descendant paths. The targeted preexisting intermediate-junction C4 case is refused before mutation.

Developer evidence: six native tests PASS (fresh atomic/collision, intermediate junction outside marker unchanged, hardlink refusal, cleanup unknown/mismatch preservation, ZIP traversal zero writes, retained parent rename denial); actual native supervisor probe PASS (generation/program, nonce, lease retention, forged-nonce refusal). Python/Node syntax PASS. Small fixtures/lease records retained as unresolved review evidence; no heavy download/pack/release executed. No app/data/library/Z:/Y: mutations.
