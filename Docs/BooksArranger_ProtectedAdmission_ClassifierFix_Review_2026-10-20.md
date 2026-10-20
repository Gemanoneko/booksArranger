# PRE classifier fixes — narrow source recheck

Senua, 2026-10-20. **DIRECT-CHECKER MAJOR RESOLVED; TRANSPORT MAJOR PARTIALLY RESOLVED, ONE DATA-FALSE-POSITIVE REMAINS.** Source preparation only; production must continue unconditional `native_contract_missing` refusal. No execution, host integration, QA, deployment or release clearance.

Verified fix doc SHA `04090dbbfaf1e04ab18a49a48b53de72832763e0c4fa52ee9b1e269cd6059fac`, documentation commit `4bea7ccebf3017678d1edeffdd37442d71900f25`; PRE SHA `d9a7c09c56809a7c0fe26c5a5fc4d1b0bfc46eec8421277550d87ed31ea2148c`; checks SHA `411fc8e9998a2d34aba8d9a7f067baf6b0c38de74d4148b408e47226a5128f06`. Read only these two files/doc. No tests or moving engineering files inspected/executed.

The new `target()` includes the canonical checker in executable position and arguments. Absolute/relative/quoted/Windows-separator paths deny without relying on context arguments. Supported read/echo/search uses remain opaque data. Original-owned routing remains first. This resolves the second Major in review `34f1ded592446b998adf55e4cda947f444069291ef468322a68cb01151b3a54d`.

Separating identification from strict `payload()` fixes the first Major's reproduced normal cmd/workdir cases: omitted observation fields and unrelated top-level host metadata no longer cause unrelated commands to deny. `validatePreRequest` still demands the exact five-field Books envelope; a candidate classification grants no admission, alias support or shell binding.

**Remaining part of transport Major:** when `identification()` fails, `unproved(raw,booksText(raw))` treats a raw substring as Books execution evidence. Counterexample, inferred directly from this source, not executed:

```json
{"tool_input":{"command":"echo 'run_entry_checks.mjs'","cwd":"C:/other"}}
```

This is an unproved alias envelope containing a quoted data mention. It currently returns deny because `booksText(raw)` matches the checker name. Unknown transport must remain integration STOP, but its mere data substring does not establish executable-position ownership. That retains the non-Books preservation failure for unknown/malformed envelopes. The added tests cover unknown aliases without Books text and executable aliases with it, but omit this data-only counterexample.

Minimal correction: unknown/unproved transports may unconditionally preserve exact original bytes with `integration_stop:true`; this is no Books allow. No additional alias parser or alias-pair support is required. Raw substring/quoted data alone cannot establish executable ownership. Add unknown-alias echo/search/file-read mentions as opaque+STOP controls; known cmd/workdir direct/wrapped checker calls still deny. Preserve the strict watchdog envelope and original-owned priority. A later trusted host capsule must bind the actually measured known cmd/workdir transport or refuse integration; do not deploy while that binding or any integration STOP is unresolved.

Reported four RED reproductions then71 pure PASS support the implemented cases only; no independent rerun or native result is claimed here. Proxy limitation and all POST/native framing/registry/host gaps from the preceding review remain outside this recheck. Current unimported source is safely nonauthoritative because production still always refuses. No other edit, probe, source change, scratch or git action performed.
