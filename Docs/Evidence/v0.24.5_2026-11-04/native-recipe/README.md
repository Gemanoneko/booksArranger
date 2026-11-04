# 0.24.5: one canonical hidden packaged check

Prepared by Ender after Futaba's r3 full PASS. No native launch has been performed by this preparation. Canonical product/test/build files are unchanged. Senua must review `native-once.mjs` before Futaba invokes `run`.

## Exact binding

- Source: `bf4425de09c355d2a0743771ca4209b24c8f0de1`
- Build: `c2d002ed-118f-47c1-8364-39a8f6d91352`
- Product digest: `509fcca6bf4c909827bd815cd6c6b3bcce4aa111e085f9eec0186e4bb6c7b156`
- Artifact manifest: `0c01cb73b9ed7b4adc7e6eeccdbb30b1c933a99ccf554af5fbf0aca4b0a09133`
- Runtime manifest: `f41e06413dee3dc1fdb2261c695baa38c8a846a02e408c690ee6d9ad08000b2e`
- Runtime pointer: `0f66ee569f9d6c5e4deca41098f11ed8aa2495e7a93b38da41f6678daf81b997`
- Full context: `f157295d631201cc7a334176299a0fc0b552b3e47a3bfe1afe0117675d788378`
- Actual full PASS receipt: `863a9308de6de34f32fea6ac1a14b3abca46243d9146ab303f5c2df549fcedb5` (500 bytes, preserved in adjacent `new-build-r3-full-entry-pass/receipt.txt`).
- Operator: `3de1a8b3f15f6390cf6ed64e461478be542219af38b51a31bd209658201bd3c3`
- Actual fresh plan: `C:/Antigravity Projects/qa-native-0245-bf4425d-20261104-r2/plan.json`, SHA256 `28c75f6affd1c3ef4b2cad87001e3238e1b8bc9ebbff426a717aa8167b92370e`, 512730 bytes.

The plan is already prepared; do not run `prepare` again. The pure preparer initially refused a Windows DLL's multiple hard links before creating any private output. It now captures native identity and link count for only the five explicitly named system DLLs, matching canonical `readPin` support. Its second metadata-only invocation succeeded in 3.25 s. Neither preparer invocation constructed native adapters or launched the app.

Senua then found the original plan stored the operator path with backslashes while the admission comparison expected forward slashes. The pin writer now normalizes every stored path to forward slashes. Old plan/authority copies are preserved byte-exact in `preflight-path-mismatch/`; the old private root contains only those two metadata files. The reviewed cleanup planner refused that old root, so it remains intact and no alternate deletion was attempted. The corrected plan uses the distinct `-r2` private arena above; pure preparation passed in 3.55 s. An independent pure probe passed the actual normalized-path predicate, operator SHA, canonical `validatePlan` and `readPin` for the operator/authority/full receipt. No native adapter or application was constructed. The new launch marker and app fixture remain absent.

## Execute once, after review

Futaba owns execution and its private fixture after this handoff. From PowerShell, use the exact installed Node and absolute operator path:

```powershell
& 'C:/Program Files/nodejs/node.exe' 'C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/Docs/Evidence/v0.24.5_2026-11-04/native-recipe/native-once.mjs' run 3de1a8b3f15f6390cf6ed64e461478be542219af38b51a31bd209658201bd3c3 28c75f6affd1c3ef4b2cad87001e3238e1b8bc9ebbff426a717aa8167b92370e
```

The operator preflights every canonical input, then creates `launch-started.json` with exclusive creation. Any existing marker refuses a second launch. It calls unchanged `q/context/source/scripts/qa-real-shell-phase.mjs --run <plan> <planSHA>` with `windowsHide:true`, raw Buffer output, an actual `execFile` callback, 600000 ms timeout and 32 MiB output cap. Canonical controller and test use the unchanged reviewed `runOwned`, one original remaining 600000 ms deadline, private Windows Jobs and exact final closure. A timeout, force, incomplete output, missing callback, foreign state drift, ownership uncertainty or assertion failure remains FAIL. Stop and report; no second invocation or recovery is authorized by this recipe.

## Private scope and effects

Input source/ownership are retained `C:/Antigravity Projects/q/context/source` and `q/ownership`. Built input is the clean r3 release worktree's manifest-pinned `dist/builds/c2d002ed-118f-47c1-8364-39a8f6d91352/win-unpacked`. Fixture is freshly created at `C:/Antigravity Projects/qa-native-0245-bf4425d-20261104-r2/pa1-c2d002ed-118f-47c1-8364-39a8f6d91352`. Every library, data directory, profile, cache, update download and temporary path belongs to this private fixture. Existing paths are never adopted or cleared. The fake GitHub binds private loopback and host rules refuse other hosts. Endpoint ownership and no visible own window are continuously checked. No installed process, live catalog, Z:, clipboard or focus operation occurs.

Windows creates one HKCU `Control Panel/NotifyIconSettings` numeric leaf for the private copied EXE. After normal closed-owned proof, canonical cleanup deletes only that exact new leaf through the same retained handle, verifies absence and preserves all preexisting leaf bytes/types. It never writes UIOrderList; ONE added 8-byte numeric ID history reference remains, with the prior history bytes intact. Authority quotes the current actual user instructions and records this exact effect. No unavailable old approval record or old timestamp is invented.

PA-1 reaches real packaged updater/download verification, Windows refusal of a deliberately invalid fake installer, recovered old engine/version, the documented Close command while hidden, continued private health, then normal Quit ending the shell. It does not claim a physical Close click or visible geometry test.

## Accept and preserve

Only after the single command completes normally, run the pure evidence consumer:

```powershell
& 'C:/Program Files/nodejs/node.exe' 'C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/Docs/Evidence/v0.24.5_2026-11-04/native-recipe/native-once.mjs' accept 3de1a8b3f15f6390cf6ed64e461478be542219af38b51a31bd209658201bd3c3 28c75f6affd1c3ef4b2cad87001e3238e1b8bc9ebbff426a717aa8167b92370e
```

This uses unchanged `evidenceSummary` and `validateNativeEvidence`: exact twelve roles, actual callback binding/streams, one PA-1 case with eight ordered assertions, normal inner/controller native zero, exact payload/input postflight and completed same-handle own-leaf cleanup. It compares actual outer callback bytes to original controller streams before exporting. No synthetic PASS or rewritten output is accepted.

Success exports `accepted/BooksArranger_NativeQA_v0.24.5.json` and its twelve evidence records. Futaba verifies and copies these to the corresponding tool Docs paths, records summary SHA256 in the QA report's exact `Native QA evidence SHA256:` line, and sends Sully the accepted source/build binding. `scripts/release-flow.mjs` consumes those same canonical references through `validateNativeEvidence` before publication.

Preserve original failures, callback/output/progress and unique diagnostic evidence. `baseline.private.json` contains foreign registry values: keep it private and exclude it from portable Docs. After evidence is safely copied and normal complete native zero plus own-leaf absence are proved, Futaba removes only this exact private fixture/evidence root and other explicitly owned disposables through the reviewed scoped cleanup route. Preserve unresolved evidence and stop on ambiguous identity, denial or active ownership. Do not remove shared q inputs or the retained r3 build without their owners' coordination.
