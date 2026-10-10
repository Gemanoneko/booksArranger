# Books Arranger v0.7.0 — empty-source-folder safety decision

2026-10-10. Senua. Focused read-only native-deletion review; combined progress/counter/Converted-filter release review is still pending.

**Folder-disposition safety:** BLOCKED for the pinned implementation below.

Open findings: 1 Critical, 0 Major, 0 Minor. This blocker is confined to directory disposition; it does not reject the independent progress/counter/filter capability.

## Exact reviewed source and evidence

| Input | SHA256 |
|---|---|
| native_io.py | 85d3c00beacad98ad03ce106ce992d00fa201656abcc14288cb962b278958cf0 |
| storage_cleanup.py | 112ae1854a90dc19e540d30cec79591e6784853bc8881ebed5294e6b445668da |
| tests/test_source_folders.py | aa429297a026e02002c93c048774d67f105a8aedd7fe0425090bdb568ffb2a12 |
| scratch/progress-folders-2026-10-10/empty-folder-fixtures/late-ads-proof.json | 76185bf3615953d3f734c248f0054670ed14a3d969eddb698c5bb1ba786c78d8 |

Independently read/rehashed all four inputs with matching pins. This certifies a focused source/evidence observation, not an uncommitted release HEAD or a clearance of later changes.

## Critical F1 — late directory data stream is erased

`native_io.py:268-276` checks os.scandir and directory streams, then applies FileDispositionInfo to the held target directory. `storage_cleanup.py:410-420` treats that disposition as an empty-folder removal. Directory handles hold the exact ordinary identity and deny ordinary replacement; ordinary child creation is atomically rejected when it makes the directory nonempty. Those facts do not make named-stream absence atomic.

The fixture at `tests/test_source_folders.py:105-133` inserts a new27-byte named stream after the last successful empty/stream check. It opens the stream with GENERIC_WRITE and READ|WRITE|DELETE sharing while the base directory is already protected with LIST_DIRECTORY|READ_ATTRIBUTES|DELETE and READ sharing. Native disposition still succeeds; closing the target handle removes both the directory and the unique stream. The saved proof reports native_disposition_blocked=false, directory_present_after_target_handle_close=false and late_stream_data_after_close=null. This is demonstrated data loss, not a hypothetical pathname race. The preexisting-stream and ordinary-late-child tests do not cover it.

Windows defines directory named streams separately from directory entries; a directory can carry named alternate streams without a default data stream. [Microsoft filesystem protocol specification](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fscc/e2b19412-a925-4360-b009-86e3b8a020c8).

## Minimal safe boundary

Place the capability refusal inside `VerifiedDirectory.dispose_empty`, before any destructive native call, so a future caller cannot bypass a UI/service-only gate. Preserve targets whose exact held filesystem supports named streams, and preserve unknown, unsupported or ambiguous capability/provider results. A second stream scan, more hashing, a directory read-sharing restriction or native ordinary-nonempty rejection does not close the demonstrated gap.

Only a positively established streamless supported provider may be considered for a future deletion allowance, retaining existing exact held identity/ancestry, approved source-only candidate scope, durable intent, protected output, late ordinary-child atomic refusal and no path/recursive fallback. An absent/zero feature value from an unsupported query is not positive proof; unknown providers remain preserved. That allowance needs a bounded accepted capability/native fixture before clearance. No ACL mutation, global lock, transaction or broader oplock framework is needed to make the current release safe: the unsupported disposition route can simply remain unreachable.

Windows exposes named-stream support as FILE_NAMED_STREAMS (0x00040000) for the filesystem associated with a handle; a suitable query must preserve that association and fail closed on failure. GetVolumeInformationByHandleW is documented as unsupported for SMB3, so it must not silently degrade to a configured drive-path assumption on mapped storage. [Microsoft handle-based volume query](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getvolumeinformationbyhandlew). Native volume attribute querying also documents zero for unsupported fields; a broad zero-result interpretation cannot certify streamlessness. [Microsoft native volume query](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntqueryvolumeinformationfile).

Parent reports an exact protected-handle read-only query for Z:/Audiobooks: filesystem NTFS, flags327791, FILE_NAMED_STREAMS=true. Therefore the current Z: library is outside the safe directory-removal capability. Keep its folders and expose the retained capability reason/count; do not report them removed, confuse this with ordinary nonempty preservation, or claim automatic empty-folder removal works there. This parent-supplied capability observation was not rerun by Senua.

The progress/counter/Converted-filter changes can proceed after this unsafe native path is removed or reliably gated. Final release clearance must inspect the corrected combined immutable candidate; it must not inherit a folder-deletion clearance from ordinary-entry tests or from v0.6's verified file-copy deletion review.

## Scope and limits

Senua read sources/evidence and primary documentation only. No real directory/library deletion, stream creation, fixture/test, capability probe, app/desktop interaction, implementation edit or Git operation occurred. Unique late-ADS proof and all source evidence are preserved. No disposable output was created.


## Frozen native-gate closure — same day

The original blocked source and negative27-byte proof above remain historical evidence. The demonstrated Critical F1 is closed for these exact replacement pins:

| Input | SHA256 |
|---|---|
| native_io.py | 5bc7bfaf137e6eea29a5c4e829f6ae1fd604b2152fe8fdd61f139ab84215855e |
| storage_cleanup.py | d20a8a5a14e92951032510edc57cbcd1d5eb3a24259ece4e8ffa2d30bd54d882 |
| tests/test_source_folders.py | ae3876624a986a6514f7a2df5c41081137c2322bc5ab9c598dae5a3ab94cafd2 |
| scratch/progress-folders-2026-10-10/empty-folder-fixtures/check-receipt.json | 56076684eaab6e77866b5a8e1807b69438de6e8345631052b12a192d732e86f0 |

Independently rehashed all three source files and the producer receipt with matching pins. `VerifiedDirectory.dispose_empty` now calls `require_empty_disposition` internally at native_io.py:299, before any native deletion call. Capability is obtained from the same protected target handle, with nonzero matching volume serial, nonempty filesystem name and component limit. Named-stream capability refuses immediately. Query/API failure and ambiguous volume facts refuse; a strict nonzero local Volume GUID from the same handle is additionally required, with no mapped/UNC/path-volume fallback. The source-stream scan no longer pretends to authorize a named-stream filesystem.

StorageCleanup checks capability before recording removal intent, repeats the native gate through dispose_empty, and records retained_unsupported plus a distinct job-level unsupported reason. Completed source retirement and verified payload-copy purge are unchanged and remain completed when only folder housekeeping is unsupported. The actual Z: library remains outside supported removal capability; no new live-folder removal is certified.

Producer receipt reports23 native fixtures passing in8.075 seconds. Source review confirms the new late-stream test creates the exact27-byte stream, deliberately mocks stale empty=true, then asserts the native capability refusal and exact surviving stream bytes. The negative late-ads-proof.json is preserved separately. Eight ordinary-entry/receipt tests explicitly simulate a streamless capability to exercise their older atomic-child and crash/state paths; those results do not certify an actually mounted streamless filesystem provider. No tests/probes/deletion were performed by Senua.

**Native gate closure:** CLEAR for the demonstrated named-stream data-loss defect at these three source pins; 0 open Critical in this focused closure. This is not the final combined v0.7.0 release verdict or positive live filesystem support. The full progress/counter/Converted-filter source range and immutable combined manifest remain to be reviewed.
