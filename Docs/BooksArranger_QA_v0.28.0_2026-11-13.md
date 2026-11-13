# Books Arranger 0.28.0 QA

Release source commit: 8dbebbf99b97241a5c607bf321567579e66bd040

Release artifact manifest SHA256: 31f4fc24d83ee3ff455bd7df2e7b5c89e5993055194fa886e459c1fbee9bb9e8

Native QA evidence SHA256: b3acaeb1b7ef7ec5a739ba18f5c5800841f5abf18e2cbb1862bad55dfb72e429

**Verdict:** GO

Installer SHA256: cce4643bc8f958d2f64903a5d543a8f818393872e38823a3459a27653b7c44c4. The measured installer size is 207,328,396 bytes. The version, source commit, and installer digest agree with the manifest for build `092f09e7-07bd-4cfa-9886-bfe0cc50b4b9`.

The builder's entry log SHA256 is `dfb09fceb55d98f90e990c2bb41145d2f8caf5b10640e33ad0c564e4e3922916`. The last receipt read from that log is:

> Entry-check receipt v2: books-arranger v0.28.0 @ 8dbebbf99b97241a5c607bf321567579e66bd040 (dirty: N) [source:3c7510fee14013ade20e7290eb4a7854734b0e1502847b0941319f4e1169d1ba; harness:011c1bb7985440dfefe4defb399c895c3782ca6c30a978ddf2f6f6d0a623d463; runtime:eb766327a168e2a78c868934cc5602bf900c9bc042f910988f91c8648aab0aa3; checker:4bae2cde4e4cdd2f22fb3060571730ec32fec1dd5403ea070086973b18b695e4] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a; personal-folders clean (1 subfolder note)

The builder's check ran 2,638 Python tests (sum of the 13 batch totals in the owned output) and passed 248/248 JavaScript tests (TAP totals). It closed normally with native zero. The observed personal-folder note was `SUBFOLDER C:\tmp | changed below the depth checked`. The builder also recorded one retained gate scratch directory under its private I: QA root after an EPERM. The held path is `I:\Books Arranger\QA\a11\entry-run-mMBT3e\scratch\12`.

Since the A8 behavior checks, the only changed production payload module is `directory_retention.py`. The last source change updates the native QA parser and its contract test. The builder's exact-source tests covered the real same-volume no-replace rename, UTF-16 termination and byte length for a path containing supplementary Unicode, and retained file identity. The prior A8 combined and NAS probes do not call that application directory retention function. The runtime, desktop shell and other non-bytecode product members match across the compared payloads. The A8 results below therefore carry forward as evidence of those scoped behaviors. A10 also passed the fresh private NSIS page fixture with static containment preflight, busy refusal, Keep default, protected selection refusal, confirmation gating, result and normal Close. Its native page evidence SHA256 is `92f8540e89a30de03ac7b9dc88781a7178246bc9a6f568d3c8a056ffbf3dd1d2`.

- A8 combined private I: relocation and packaged helper admission accepted the verified target and profile, preserved settings hashes, saved history and a pending job, refused when the target was unavailable, and recovered after restoration. This is a same-volume private fixture. The cross-volume controls are in the builder's suite. Actual Chromium outbox replay remains unverified.
- A8 packaged Python/backend/FFmpeg converted two private NAS books across a service restart at the completed-book boundary. Both outputs verified, all four original file hashes matched, and zero originals were removed. The private trace recorded 21,957 database/WAL/SHM events on I:, 16 I: staging M4B events, four Z: final M4B events and zero under the private original subtree. The selected Temp had zero events during capture. The trace covered the fixture I: and Z: roots only. Trace SHA256 `cee0b633c2806088460ab455ee1c947d00075d6705bff9d15836445fc3f556cb`.
- A8 in-flight drain during actual conversion left the current job needing attention before publication and the next job pending. The persisted failure came from the production working guard during closing. This behavior carries forward. The cutover procedure must wait for natural batch completion and independently verify closure. Major, deferred for this release with that operating constraint.

The approved foreground preview used two pinned wizard executables and a fresh private seed. The installer discovered the available private database and exposed the Existing and New choices, Browse, and Check again. Next opened the review, which showed the exact existing database and profile paths. Cancel closed the wizard before Install. The uninstaller's first page exposed Keep and Remove and a four-column review with protected and application rows. The pointer target for Next could not be established, so Escape closed the wizard before Uninstall. Both owned launcher jobs closed normally with zero active native processes. The installer and uninstaller supervisors recorded 15 and 9 retained process handles, respectively, and all five frozen fixture file hashes matched afterward.

The foreground observations came from the accessibility tree. The installer screenshot showed unrelated background, so this preview provides no screenshot-based layout verdict. The headless native fixture separately verified the confirmation and result pages. The generic uninstaller cannot demonstrate the package-owned maintenance copy. Existing engineering review and result records show the verified 13,440,804-byte copy separately.

The release-bound PA-1 run passed once on the current package. The real shell stayed up when the downloaded installer could not start, the old engine recovered, packaged health reported version 0.28.0, and normal Quit closed the shell and backend. The outer and inner owned supervisors returned exit 0 with native zero. Postflight verified the payload was unchanged. Cleanup deleted only the newly created private tray leaf by its held handle, verified absence, and preserved preexisting entries. The controller did not write the tray order list. QA independently checked the summary binding and all 12 original record lengths and SHA256 values against the submitted summary. The canonical native validator passed the same records.

The private wizard and exact-source suite cover lifecycle guards and selection. The engineering maintenance-copy records are earlier fixture evidence. A full successful install and terminal cleanup with the exact shipped setup executable, browser outbox replay, and a screenshot-based layout verdict remain unverified. This GO covers the tested build and does not authorize the live cutover.

Pattern alerts: none observed.
