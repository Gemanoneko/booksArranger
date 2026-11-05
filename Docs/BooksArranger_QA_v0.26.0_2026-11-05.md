# Books Arranger 0.26.0 QA — 2026-11-05

**Verdict:** GO

Release source commit: 3932155e9f3ceac00632d2d82a4e91315f7c832f
Release artifact manifest SHA256: 8d170ee68ad1e5cccca5be024cf23aaa0893c4b12b4c8ebdfb1dbd9a4086574f
Native QA evidence SHA256: ce4989c46fb193272f98cf0f0797d59a1a4e6ea8dd8dbb4c3a552670e67f8fff

The clean, guarded r3 build is `82b4dac4-0aad-453a-a013-d3486cc431eb` (product digest `6e9a3f3a785eb5fe243f032d6ccc30b9352518ef1efba1739aba57501a17b5c3`). Its installer, blockmap, release manifest and runtime pointer matched the frozen pack and q28 context pins. The [single full schema 3 entry](Evidence/v0.26.0_2026-11-05/full-entry-393-r3-pass/summary.json) passed: 13 Python batches executed 2,447 methods with no skips, failures or errors; the Node TAP phase passed 242 cases; all 41 declared frontend scripts completed. The owner exited 0 with complete output, normal closure, no force or timeout, and zero native residue. Exact full-entry receipt SHA256: `c6e4e84bcff6947e439c8867733566a870080c489187ee9206be3a5605365fee`.

The single reviewed, private packaged PA-1 run passed. It verified the real shell remained running when a deliberately invalid installer could not start, recovered the prior engine, and then exited through normal Quit. The [accepted native summary](BooksArranger_NativeQA_v0.26.0.json) binds this same source and build. The unchanged strict release validator passed on all [12 raw evidence roles](BooksArranger_NativeQA_v0.26.0_Evidence/), including the original callback, functional assertions, normal owned closure, payload postflight and exact private tray-leaf cleanup. No visible own window, live library, Z: source, installed app state or foreground focus was used. The cleanup preserved preexisting registry bytes; its one owned 8-byte history reference is recorded in the evidence.

The committed source and this build include the queue hold, durable decision, Tolkien approval and four Universe-option changes. Focused handoffs for those changes are retained in `Docs/Evidence/` and were followed by this fresh whole-graph check. Historical candidate q26 and q27 failures remain in separate dated NO-GO reports and are excluded from this verdict. No new recurring user-facing friction pattern was observed in the private checks; the earlier fixture failures were corrected and verified on the pinned r3 build. This verdict covers the guarded artifact and bounded private checks, with the user's live collection untouched.

Entry-check receipt v2: books-arranger v0.26.0 @ 3932155e9f3ceac00632d2d82a4e91315f7c832f (dirty: N) [source:a8c0b46ea1408a56f23aae0c0b2e957280fdc6d3d335097a2180ac8264357d4a; harness:5218f39bd78b546b4516fb6459a98fca53771ec1986f7e3eadf5e160535a4ae4; runtime:7156e0d940c5e5df988b2406f509620647af07b755a405bc4d73508a5f2d4eca; checker:4bae2cde4e4cdd2f22fb3060571730ec32fec1dd5403ea070086973b18b695e4] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a; personal-folders clean
