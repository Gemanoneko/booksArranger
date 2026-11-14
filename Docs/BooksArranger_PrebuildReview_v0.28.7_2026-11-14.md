# 0.28.7 scoped prebuild safety review

Reviewer: Senua. Date: 2026-11-14.

Verdict: accepted for build within the reviewed portable-storage migration scope. This is static source review, not packaged-release QA or a binary GO verdict. No tests or live operations were run by this reviewer. The user explicitly declined postbuild QA.

Reviewed boundaries: relative installation/profile configuration; installer staged completion and retry; source detach before source-independent binding; native catalog exclusion; no-replace same-volume move and verified cross-volume copy; immutable control/provenance preservation; current-generation native identity history; managed-cover read adapters and conservative protection aliases; final current-package publication.

Resolved findings include queued-manifest hash corruption, missing terminal-state validation, absolute settings output, writable SQLite self-sharing conflict, stale package ownership, v2 control/binding composition, and old managed-cover read paths. The current matcher accepts only exact authenticated location history with exact current native identity/facts, under supported receipt classes. It does not create producer closure or deletion authority.

Different physical drives use the normal installer and a freshly locked source. Arbitrary Explorer copies are not authorized rebinding. Source catalogs and incomplete private copies remain preserved. Retained jobs stay held; this review does not authorize processing or old-data retirement.

Limits: an active-retained migration without a verified independent archive refuses. An already-detached v1 installation lacking the old alias and a saved migration preview remains a safe-refusal edge. Portable-aware retirement is separate and is not cleared here. No final-schema execution claim is made from earlier developer fixture results.

Accepted code SHA-256:

```
portable_storage_copy.py d7d2b2465bfe2ff97e626a17a989910c76fd9195a63c5ef98667b959d0309820
portable_storage_migration.py 484fdeba17bb918d7fd671a493e627dec94a5b33f0597e6381a139836701c576
storage_portable_namespace.py 1a9e52c3aa4c2eb60b736ec39c4517dc502b2b670882bef15fa845e0339be78c
storage_relocation_native.py 09d32b772ca76500a21f134b6c2c2a8c009bfaa37511939a40aba15fdd4b72a6
storage_retained_runtime.py 6aab8f93b12c16eac106091690a499a04f1e856b5b8b3e677386d27353c68c1b
storage_lifecycle.py fa7c5743678be8c77d304e3174bb205556d66c71ecbb9604205c8df2ef3fd472
installation_storage.py 8a21c410de89cf8743a19c97adccf84ddc359e54dcfcf2f81296d3e275f604cf
portable_catalog_paths.py b922c8bf8e2feeebeee36e47c0a78b362c1236501eb8b7b35a50cfdd0f18a144
desktop/installation-paths.js 6a82488aaf12b39bbbdad93d52d9a35d0976afb2d1b850dc0b11fd93d6cb982b
desktop/installer.nsh 4fbab2ae8f43f11be52f51c9427322c31664eec0924d548cf8c85fd681382450
desktop/main.js bc43b4b9819754967f1adae2bea87549e62f2b61daab08e42c56b794a2ccab01
desktop_settings.py 2bd5362f6e0bb8eb8e0209f7ba91424ff4d3401c977161ab349d1ea18d025f70
audio_pipeline.py 1ee44d336af4fdd58adae577baaec38c98b27219b5a8fef14449264e82cfd320
inplace_m4b.py cce3cd5c4a271794a8954172a3ae0d2656e19cdb6a6647871eb499f57835171b
storage_cleanup.py cddc43878dfbfd2b2ed3867a64b09ec099978004d46f0736343281098ed3358b
cleanup_ownership.py cba9020070e247289bf5c18777635ebcbc11b74a690c9a3f17327dd71b1616d9
book_delete.py 5fad1d25cbbbd27d26a908cbb88b6cdf0892e4f0a1c7914e53d8b707be892884
merge_service.py 43b492bcf52979e4837baeb7df8e7de5249b23d70a08598025b20d338bfbc2ba
```

No cleanup performed; existing evidence and fixtures remain retained under the user's no-delete instruction.
