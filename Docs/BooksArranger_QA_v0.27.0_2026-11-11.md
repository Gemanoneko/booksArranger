# Books Arranger 0.27.0 QA

**Verdict:** GO

Release source commit: d11302ab70a2831e2096ec4a6a4629f33fc0f9c9
Release artifact manifest SHA256: 8825b291e3d55abc45bc0ba488d98c2d5a32d32c29d17a64dd5de4c7639a66b7
Native QA evidence SHA256: 0fb88e58649711e0beac803b56cb13f842927a0ac9e046c61ae6e2675e7962c0

The guarded build is `0245e25b-e185-4357-b48c-8f1cb4b242c0`. Its installer SHA256 is `3c55a291e7609c967a7a9eea6d1e8b83269ae02dbff8a72a6b7f4c899d2f9f82`. The extracted installer payload matched all 334 guarded package files. The one full entry check passed 2,447 Python methods, 245 Node cases, and 42 frontend scripts. The full check exited normally with complete output and zero remaining owned processes. Actual entry stdout SHA256 is `b0f187eef49f7879b0b71e398e81e474ec38a5767ed49355c87b74618c59bedc`.

Independent Manual Conversion checks rejected replaced source files even when the replacement matched the original size and modification time. The saved reservation survived reorder and subset refusals. An unchanged draft survived restart and produced the chosen M4B in the selected order. Cleanup removed only the selected originals after verification, and the book appeared in Converted. Those checks and the packaged backend smoke used `ed8d9bc`. The final commit changes only the TCP witness and its contract tests. The three targeted witness tests passed independently on the final commit.

The one approved hidden Electron run on this exact build passed PA-1. Windows refused the deliberately invalid installer, and the private 0.27.0 engine recovered. The close command reached the real window-close callback, and the hidden shell and engine remained healthy until the subsequent normal Quit. The listener witness made 73 queries and observed raw states 0 and 6 in the listener-only table. Both owned process scopes closed normally with complete output and zero remaining native processes. The actual callback matched the original controller streams. The strict validator passed all [12 accepted raw evidence roles](BooksArranger_NativeQA_v0.27.0_Evidence/) bound to the [native summary](BooksArranger_NativeQA_v0.27.0.json).

The cleanup removed only the exact private tray entry. It preserved all baseline tray leaves and ordering bytes, including the first test’s history reference. Windows retained one additional 8-byte history reference. The hidden run used a private catalog and kept foreground focus, the installed app, and the live library untouched.

Pattern alerts: none on the corrected build. The earlier listener-witness refusal remains a separate NO-GO record for the superseded build.

Entry-check receipt v2: books-arranger v0.27.0 @ d11302ab70a2831e2096ec4a6a4629f33fc0f9c9 (dirty: N) [source:8b74e02d62594d96ed805e89efe56b7adba4adbe92b8729470db82ab2284b968; harness:aad093d5e1ce44954efbbfb188563082134f33d102dc31a4d7b32148de2dbd1e; runtime:282bd00619313196035b233699464de9a0f44f9e67a632807e0da25364adc035; checker:4bae2cde4e4cdd2f22fb3060571730ec32fec1dd5403ea070086973b18b695e4] — pre-qa n/a, post-build n/a, check-electron n/a, check pass, test:smoke n/a; personal-folders clean (5 subfolder notes)
