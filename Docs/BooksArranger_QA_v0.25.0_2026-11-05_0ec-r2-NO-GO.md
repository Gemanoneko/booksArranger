# Books Arranger 0.25.0 QA — corrected r2 build, 2026-11-05

**Verdict:** NO-GO. The single full schema 3 entry on build `140014b8-b350-4a3e-a99b-05d24349f139` failed. No same-build repeat or native/hidden release check was run.

Source commit: `0ec4971169a70d57a407ae1a9ef6bf96227724d4` (clean). Release artifact manifest SHA256: `8f055521103f91f9417331091b971c423f7da483980364ee7a020016c99a9ca9`. Runtime pointer SHA256: `fe2e42723bbf6c5f7bfec0ad7d77b84255907a363ecf4d2c612ce432e61ec130`. Schema 3 context SHA256: `fb3181e4c169835a8e083608b048c0e9d5b0cc2dc5ad7411bb34b58ae7b12179`.

All **13 Python batches passed**, reporting 2,405 test methods with no failures or errors. The remaining failure is `tests/test_precheck_frontend.js:126`: the UI returned “Can't convert — M4B feature unsupported”, while the test expected “Can't convert — M4B not supported”. Ender is assessing the intended copy. The owned check exited 1 after 488.7 s but closed normally with complete output and native zero; there was no force or timeout. The personal-folder audit was clean.

[Exact receipt, raw logs, context and failure index](Evidence/converted-duplicate_2026-11-05/full-entry-0ec-r2-failure/summary.json) are retained. Receipt SHA256: `27b38ef5288d82fe53df788a34b4ef2be0516d0d201471f2e9c311c9d2a1c1b5`. The private `q3` source/context/ownership trees remain intact for diagnosis.

Entry-check receipt v2: books-arranger v0.25.0 @ 0ec4971169a70d57a407ae1a9ef6bf96227724d4 (dirty: N) [source:5fc7ae7c33b093f3f74c6a885c1b719434fc2b96070f04b3c87a0ca9baf282f4; harness:0b39618db4f5c8d969d73424e5157e735d9a59dca2dee773fb7165707ed22080; runtime:9b1d6629000104e25b0214104326e146b863afc0d28ee2de8bc66c267600f6f6; checker:4bae2cde4e4cdd2f22fb3060571730ec32fec1dd5403ea070086973b18b695e4] — pre-qa n/a, post-build n/a, check-electron n/a, check fail (owned check), test:smoke n/a; personal-folders clean
