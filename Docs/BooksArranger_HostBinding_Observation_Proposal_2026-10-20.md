# One host-binding observation — decision proposal

DESIGN ONLY: no observation, process, hook change or approval request. Existing chain: global hooks SHA `c4b5…26aa3` pins host `cf2f…45f3`; observer metadata at `C:/Users/AnGeLZzZ/.codex/hooks/command-safety-route/observer-metadata.jsonl` records event/tool/input-key/cwd shape, without command fingerprint or call ID. Trusted Windows/tool host is an explicit base assumption, not a native capability proved by JSON.

## Prospective ordinary request

Exactly ONE `tools.exec_command` call, outside QA and without a wrapper, with this proposed payload:

```json
{
  "cmd": "$booksHostProbeToken='books-host-binding-20261020-01'; [ordered]@{version=$PSVersionTable.PSVersion.ToString();edition=$PSVersionTable.PSEdition;image=[System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName}|ConvertTo-Json -Compress",
  "shell": "C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
  "workdir": "C:/Antigravity Projects/Studio Illuminati",
  "login": false,
  "yield_time_ms": 10000,
  "max_output_tokens": 1000
}
```

The token is a fixed correlation label, not a secret, nonce or authority; do not reuse after an attempted call. Output contains only PowerShell version, edition and current process image path. No environment/account enumeration, file write, guard replay, npm, QA, elevation or default-shell reliance. Observation fields are UI/output settings, not a claimed native execution deadline. Failure, unexpected output or incomplete original terminal result means STOP; no automatic retry or shell substitution.

## Existing-log attempt and exact limits

Before considering execution, quiesce the agent tree and other known writers. In-process filesystem reads record current hook/host/observer/policy hashes, log identity/size cursor and SHA-256 of its entire byte prefix. After the ONE actual original tool terminal result, read again: same identity, unchanged full prefix, only complete bounded JSONL append(s), no truncation/replacement, and no known concurrent writer. External writers cannot be excluded merely by pausing agents; ambiguity means STOP. Preserve original tool request/result and before/after byte evidence together. Reject zero/multiple/partial appends rather than select a convenient record.

One append under those conditions supports a bounded causal association with that observation. It does not cryptographically authenticate the writer or prove exact transformed command bytes, shell field retention, an immutable host session or all future calls. The structured request proves the submitted explicit shell value; successful expected stdout supports actual PowerShell selection under the trusted-host assumption. Metadata proves only the observed `tool_name`, input keys and cwd shape. Existing records cannot establish the submitted cmd-to-hook-command equality or original P9 call provenance. This may therefore remain insufficient for Senua's V2 binding requirement.

## Smallest fallback candidate, if required

Separately review a metadata-only amendment to the existing observer: for ONE exact, reviewed probe token/command shape, append bounded schema-versioned metadata with event/tool name, sorted input keys, token, UTF-8 SHA-256 and byte length of raw hook input, and per-present-field type plus SHA-256/length for string `command`, `cmd`, `shell`, `workdir`; record literal boolean/integer values only for login/yield/output fields. Never record command bodies, arbitrary field values, secrets or full stdout. Reject ambiguous token occurrences; no generic alias decoder. Field hashes expose whether exact submitted strings survived; a transformed command requires its concrete recorded mapping to be reviewed, not guessed from the token.

Keep forwarding original raw bytes unchanged, original decisions/status untouched and no allow/exception path. Fingerprints remain descriptive evidence, not capabilities or signatures. This candidate is NOT implemented and NOT installed. Any global change requires concrete source/config diff, exact prior/candidate hashes, bounded capture and human-controlled installation/rollback review before a later approval request. No global instrumentation is authorized by this document.

Senua decision: is the existing-log association plus explicit-shell output sufficient for the finite host binding, or is the one-probe fingerprint candidate necessary? Even the latter leaves trusted original-tool association/terminal observation, protected input/native lifetime and future native POST framing as separate missing proofs. No V2 integration may infer authority while these gates remain unresolved.
