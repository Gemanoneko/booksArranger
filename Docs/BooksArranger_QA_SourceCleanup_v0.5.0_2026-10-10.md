# Books Arranger source cleanup QA — v0.5.0 — 2026-10-10

**Verdict: GO for the pinned cleanup implementation and reviewed finite caller.** No real book originals were removed by QA. The separately authorized real 21-source operation remains Ender's responsibility. Actual iTunes/device behavior is outside this change and was not tested.

Accepted manifest: `scratch/source-cleanup-2026-10-10/manifest-frozen-2.json`, 32 files, SHA256 `5666525f9421357fcd69c6f6440c3aba0c476059c0cd35c0cd146df4cb4d8eb9`. All pins independently verified; owned copy `scratch/source-cleanup-qa-2026-10-10/candidate2`. Baseline marker 0.4.4; intended release 0.5.0 belongs to Sully. Complete exact pins are preserved in `test-evidence-final2.json`. Key changed safety pins:

| File | SHA256 |
| --- | --- |
| native_io.py | 9939de63b3448e02f0c664d43242fe46e728a2f4f77ad21ed62f0bf98c7fad44 |
| source_cleanup.py | 926425439f04c52edcca91bc9f3c3bc29b240d9e80c55efb1b44a620ea8e1d49 |
| merge_service.py | 6b424a00db3294bc779b5948e43becd9a5d721dc90b51c7dc347bf8e3136d813 |
| web_server.py | e1fca868527af683c3c6b71f9e2bd3d260377540265ae73170464e57ff81f5e0 |
| support/pilot_cleanup.py | 26ec97571c360579b42bdcbf45e3ea0fa6f89e634bcf92518d5c214c71861b15 |
| support/mapped_disposition.py | da4fead3c390a07eee8a88fa9c4ad60147f318294cfb313416984e1e28676d01 |

## Tested behavior and methods

**52 distinct targeted Python cases accepted**, with method and carry-forward separated:

- Freeze2: 35/35 in 9.94 seconds: 13 Windows native cleanup/recovery fault cases, five actual tiny-media review/export/service cases, 12 HTTP contracts, five finite-admission cases. Review → encode → validate → verified recovery → exact original removal → restart/scan → Created/View recovery facts succeeded. Output/read/review changes, all-backups-before-delete and reused-backup flushing, hardlink aliases, collision, pause/resume, unknown disposition and restore-publication checkpoint recovery pass.
- Carry-forward: ten catalogue-retirement cases from identical scanner/group/test pins. Confirmed retirements remain history without false missing/error counts or review revision loss. A genuinely new same-name arrival is read even with identical size/ns; errors stay visible; restored files become ordinary active sources; recovery ownership is exact.
- Carry-forward: five independent negatives (`extra-evidence.json`): same-size/ns changed source content; corrupt backup; identical-byte replacement after interrupted restore with different file identity; duplicate/non-MP3/podcast source membership; constructor never starts waiting cleanup automatically. These guard behaviors remain in the revised native/admission regression scope; no legacy automatic enrollment is claimed.
- Freeze2 independent: two identity regressions (`identity-evidence.json`): fallback is permitted only for API errors 1/50/87; access denied error 5 fails closed. Persisted identity-method drift is rejected.

Historical cleanup admission now rejects scan/running work, unrelated queued audio and unrelated paused cleanup under the shared operation lock. It resumes only the exact newly enrolled cleanup ID with `follow_audio=False`; it never drains unrelated encoders. The actual real caller was pinned/read-reviewed, **not executed by QA**. HTTP tests reject pasted paths, unknown fields, invalid IDs, untrusted origin and absent token for cleanup/restore.

The first snapshot was held for Senua's finite-caller finding and mapped-drive unsupported FileIdInfo. The initial hardlink fixture also encountered sandbox denial before product execution; its single scoped retry passed. These are recorded rather than counted as release success before correction. Freeze2 is the accepted snapshot.

## Actual mapped volume capability

After explicit Senua containment clearance and Ender's completed producer run, QA executed the exact pinned probe once with a distinct UUID `4d8c7944-f5a4-41d0-ba43-36753f72ce14`, under `Z:\Audiobooks\.books-cleanup-capability-[UUID]`. It touched only its three exclusively created tiny fixture names, never book paths.

**Five checks passed:** writer denied while protected; exact handle disposition removed the verified name; original bytes and ns restored; existing destination collision preserved; verified own files and empty directory removed. Source payload was 4,900 bytes. Z returned unsupported FileIdInfo error 87; tagged `BY_HANDLE_FILE_INFORMATION64` volume/index exactly matched fresh **opened** fstat on the same protected file. Restored file has a new identity, as expected, with identical bytes/ns. Scope is this mapped filesystem capability, not a claim that every arbitrary storage device supports safe cleanup.

Independent receipt: `scratch/source-cleanup-qa-2026-10-10/mapped-disposition-receipt.json`. Producer receipt SHA256 `6b43e5672146383255fd5c66d19cbe957542b4c86d56aeb529f5a174a3b4f5f3`, provenance SHA256 `ee604a6c25b7b680e3b20045291c7f7ddc6e9a1cc3475ebf5f197e0be7bfd388`. Producer separately reconciled both failed earlier UUID-only probes; no QA duplicate reconciliation was performed.

## Browser/UI evidence

Actual-script frontend VM passed planned policy/historical retention, authoritative counters, partial pause/failure/completion, output success, dirty-form preservation, stage-specific controls and inherited inspector assertions. Frozen inherited harness is included in the accepted32 manifest.

Guarded isolated browser at verified fixture port 5211 exercised **real owned tiny-media prequeue, completed cleanup and created View facts**, with 1440/700 CSS-pixel captures. Saved recovery facts remain available after original fixture audio is removed. Three additional states (running, paused, attention) were **synthetic authoritative response overlays for rendering**, not claims of physically interrupted browser-driven removal; their actual native checkpoint behavior is separately covered by Python fault tests. Counts and successful output remain readable beside cleanup attention. No real Explorer action occurred.

Screenshots under `scratch/source-cleanup-qa-2026-10-10/`: `prequeue-{1440,700}.png`, `completed-{1440,700}.png`, `running-{1440,700}.png`, `paused-{1440,700}.png`, `attention-{1440,700}.png`, `created-view-700.png`. `browser-evidence.json` retains state text and control rectangles; existing job buttons meet 24px hit-area height. These captures do not establish a global pixel-layout guarantee. The source fixture volume was C:; rendered Z:/C: labels are the product's fixed real-workflow copy, not proof of Z-space savings from that C-fixture browser run. Actual Z disposition capability is separately measured above.

Initial browser attempts stopped on sandbox loopback timeout and a wrong QA route-overlay matcher; both were fixture/harness issues. Final browser used corrected `/api/inventory` overlay and exited 0. Lease `1566101662da` reports remaining processes 0. Fixture session 93118 exited 0 and removed its tiny generated media. Earlier failed leases also report remaining 0; owned interrupted fixture leftovers were containment-checked and removed before the final pass.

## Limits and disposition

No unresolved Blocker or Major. Senua's advisory Minor is retained: exact registered private temporary-path scan exclusion does not rehash a replacement at that same private path. It never deletes such a replacement, and actual original-source same-name arrival regressions pass. Disposition: **accept the advisory limit for this scoped milestone; retain ownership evidence and do not broaden exclusion/deletion semantics**.

Recovery copies consume C: storage and have no automatic purge. Constructors do not perform historical cleanup. Output success and cleanup attention are separate. Source-set accounting does not prove external publisher completeness. No device test, subjective playback, real source deletion or current-library conversion was performed in this QA pass. All owned command sessions/probes exited, media handles and browser leases closed; fixture leftovers are empty, and unique snapshots/proofs/captures are preserved.
