# Protected native terminal frame — finite proposal

DESIGN ONLY. No existing source changed; no execution authority. Follows Senua review `623c14a0…181baa` / `c5f50a30`. Current `books-qa-watchdog.cpp` captures both child channels privately in `start`/`drainAvailable`, then `run` writes raw child bytes plus a counts-only line. That stream has no trustworthy invocation join. Retained Job counts/waits are its own contract, not engineering-v3 image/birth proof.

## Producer and literal format

Keep ONE child capture pipe and exact inherited handle list (inert stdin, capture writer only). Never forward raw child bytes onto parent stdout. Protected watchdog alone serializes ASCII stdout:

```text
BOOKS_NATIVE_RESULT_V1\n
payload_bytes=<canonical decimal>\n
payload_base64_bytes=<canonical decimal>\n
<one RFC4648 base64 payload line>\n
terminal_bytes=<canonical decimal>\n
<one canonical UTF-8 JSON terminal line>\n
<actual stdout EOF>
```

Parse exact lengths, order, canonical encoding and EOF; no searching for magic or last matching line. Child stdout/stderr remain one opaque payload, including any imitation frame. Parent stderr must be empty for acceptance. Bound outer stdout to 16 MiB, terminal to 8 KiB and raw child capture to 12 MiB minus 8 KiB (new reviewed bound, not current MAX_OUTPUT). Duplicate/trailing/partial records refuse. No failure text is a pass frame; exceptions, termination, overbound, lost pipe or missing closure produce nonzero exit and/or incomplete stream, always refusal.

Proposed terminal exact fields: `schema=books-native-terminal-v1`, `invocation_id`, `registry_sha256`, `context_sha256`, `policy_sha256`, `source_sha256`, `runtime_sha256`, `bootstrap_sha256`, `watchdog_sha256`, `payload_sha256`, `payload_bytes`, `child_exit_code=0`, `active=0`, `unsignaled=0`, `retained_closed`, `pipe_eof=true`, `work_handles_closed=true`, `elapsed_ms`. Hashes mean exact held bytes: registry; context; immutable admission policy; context-defined versioned source closure; runtime/bootstrap manifests; actual watchdog image; raw captured payload. Digest equality is not native authority. No unknown fields, booleans as substitutes, fabricated image/birth claims or reconstructed source aggregate.

## One execution and separate original-result acceptance

PRE admits only the exact protected watchdog literal. Runtime independently reopens/freezes the registered context, policy, complete source/runtime/bootstrap closure and validates joins BEFORE one fixed child. No PRE handles are lent forward. Registry/context identify the same invocation; a trusted original-tool producer privately associates it with ONE actual tool call. Pending state is consumed once and never reconstructed from disk receipts; restart loses pending authority. No public POST accepts supplied JSON as the original tool result.

Emit terminal only after exact Job zero, retained handles signaled/checked closed, actual capture EOF and input/child/pipe/Job closure. Keep deadline monitor alive through potentially blocking outer writes; then checked-close monitor/control handles and exit zero. Frame cannot honestly claim those later control closes already happened. POST requires the actual original tool terminal observation: matching pending call/invocation, success/no signal, complete bounded stdout, empty stderr and measured terminal duration within the reviewed whole-operation limit. Frame alone cannot prove final teardown or future exit. Emergency timeout cannot promise a complete failure frame.

## Missing truth gates and ownership

Sources owns future edits: `books-qa-watchdog.cpp` serialization/closure, fixed `launch-books-qa.mjs` input join, `dispatch-books.mjs::verifyBooksGuard`, deployed host original-result producer and strict route consumer. New `protected-admission*.mjs` ends would later consume this version after independent review; their current proposed schemas differ and production still refuses. Literal-format consumers are only that serializer, bounded host parser and pure negative fixtures; logs/UI must never treat payload text as control.

BLOCKED pending real host tool-call identity/default-shell binding and native-origin observation API, protected image/ACL/held input proofs, exact versioned policy/source/runtime digest definitions and selected C++ behavior/build evidence. Exact inherited handles prevent child-pipe frame confusion; they do not prove resistance to arbitrary same-user process injection/handle duplication. That stronger origin threat boundary needs Senua's explicit decision/evidence before acceptance, not an invented boolean. Negatives: forged child payload frame, copied/replayed invocation, wrong pins/call/source, altered payload, duplicates/trailing/encoding errors, nonzero/timeout, unsignaled member, absent EOF, failed close and exit after bound. No probe, implementation, current-native acceptance or deployment is claimed.
