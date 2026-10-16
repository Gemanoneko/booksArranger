# Books Arranger — real-catalog-copy QA recipe (status pile-up fix)

Author: Ender, 2026-10-16. For: Futaba. Build under test: the next packaged build containing the status pile-up fix (expected 0.16.1; Sully decides the number).

Goal: run the **packaged** app, idle and Paused, against a **private copy of Sergei's real catalog** for 10 minutes and prove status polling stays bounded. This is the test the 0.16.0 smoke could not do (its catalog was empty), and the one that failed live on 2026-10-16 (engine threads 366 → 515 and memory 18.7 → 22.2 GB in under 3 minutes; window stuck on "Waiting for the engine checkpoint…").

## 1. Why this is safe (and the conditions that keep it safe)

The real catalog stores **absolute paths** into the real data folder (`…\WIP\Books Arranger\data\source-recovery\…`) and the NAS library (`Z:\Audiobooks\…`). A copy engine therefore sees real paths. What an idle, Paused engine does with them was checked three ways:

1. **Code reading** of everything that runs without a click: engine startup (stale-record retirement, catalog lock, `Inventory` init, `MergeService` init incl. cleanup enrollment, `AutomaticProcessing` init), the background retention loop (`working.reconcile`, recovery purge, published revisits) and every status poll.
2. **A guarded run** of exactly those steps against a throwaway catalog copy, with a process-wide guard that refuses (and counts) any open, write, rename, delete, directory listing, child process, network call or native call on `Z:`, `Y:` or the real data folder. Result, with the real root strings **and** with private roots: **zero refused operations**. Init, one reconcile tick, the recovery gate, `due()`, ten forced purges (gate deliberately bypassed) and a full status computation made no attempt to touch anything outside the copy. (Correction 2026-10-17, from code review: that run emulated the real backups as missing, which hid one read-only check on `Z:` — see the next paragraph.)
3. **Native boundary checks** on the only deleting path that could see real files (recovery purge):
   - Gate: `_recovery_idle()` refuses while any audio job is pending or running. The copy has 194 pending, so automatic purge never starts.
   - Location: purge only works inside `<its own data folder>\source-recovery\<cleanup id>`. In the copy that folder does not exist, and the native boundary refuses a missing location (verified: `BoundaryError: An inspected destination ancestor is unavailable`).
   - Correspondence: each backup must sit directly in that location (`path.parent == location`). Real backups live under the real data folder, so they are refused even if the first two layers were absent.
   - The working-file lifecycle builds delete targets from its own `merge-cache\audio-staging` plus job/attempt ids, never from stored absolute paths. The copy also has no working attempts.

What the copy engine **does** touch outside the copy, read-only, once per status computation (at most about one per second after the fix):
- about 2,100 metadata reads (stat/lstat/is-file) of the real `data\source-recovery` backup files;
- **directory checks on `Z:`**: for every completed source cleanup whose backups are all present, `CleanupJobs.status()` (`source_cleanup.py`, the `restore_available` line) checks that each original's parent folder still exists (`is_dir`). The paths come from the catalog, so private roots do **not** prevent this.

At idle nothing opens, lists, writes, renames or deletes anything on `Z:` or `Y:`. Everything else (scan, conversion, research, source cleanup, folder cleanup, update check) only starts on a click.

**Note for Futaba:** those `Z:` checks reach the NAS. If the NAS is asleep, the first computations wait for it to spin up, so early poll times (and a possible `503 Status is still updating` on `/api/state`) can reflect the NAS, not the engine. Record whether the NAS was asleep; judge latency on the samples after the first minute, and report any 503 with its time.

The safety therefore rests on four conditions. If any one fails, STOP:
- **C1** — the real app is not running while you copy (otherwise the copy can miss committed pages) and stays stopped throughout.
- **C2** — private library roots via `--roots-json`. This keeps scans off `Z:` and makes accidental library actions refuse, because every catalog path is outside the configured roots. It does not stop the read-only folder checks above.
- **C3** — **no mutating clicks** (list in §5).
- **C4** — the real data folder fingerprint is identical before and after (§4 and §7). That is the proof, not this argument.

## 2. Preconditions

```bash
WT="C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/electron-2026-10-13/worktree"
REAL="C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/data"
QA="<your scratchpad>/copyqa"            # Futaba's own scratch; nothing inside the worktree
INSTALLER="<path to the new Books-Arranger-Setup-<version>.exe>"
PY="$WT/build-cache/runtime/python/python.exe"
SEVEN="$WT/node_modules/7zip-bin/win/x64/7za.exe"
```

1. `sha256sum "$INSTALLER"` equals the artifact SHA in `"$WT/dist/release-artifacts.json"` for the new build, and that manifest's `source_head` is the commit under test.
2. Nothing of Books Arranger is running: `tasklist //FI "IMAGENAME eq Books Arranger.exe"` shows none, and nothing listens on 5210 or 5212 (`netstat -ano -p TCP | grep -E ":521[02]\b"`). Do not kill anything you find; report it.
3. `ls -la "$REAL"`: `inventory.sqlite3-wal` is absent or **0 bytes**. If it is larger, STOP: the copy would miss committed data.
4. C: has at least 3 GB free.

## 3. Build the private area (copy is read-only on the source)

```bash
mkdir -p "$QA/data/merge-cache/covers" "$QA/roots/Audiobooks" "$QA/roots/Podcasts" "$QA/roots/Ebooks" \
         "$QA/profile" "$QA/appdata" "$QA/localappdata" "$QA/temp" "$QA/payload" "$QA/evidence"
cp --preserve=timestamps "$REAL/inventory.sqlite3" "$QA/data/"
find "$REAL/merge-cache/covers" -maxdepth 1 -type f \( -name '*.png' -o -name '*.jpg' \) -exec cp --preserve=timestamps {} "$QA/data/merge-cache/covers/" \;
sha256sum "$REAL/inventory.sqlite3" "$QA/data/inventory.sqlite3"     # must match
"$PY" -I -B -c "import json,os,sys;r=sys.argv[1];json.dump({k:os.path.join(r,'roots',k) for k in ('Audiobooks','Podcasts','Ebooks')},open(sys.argv[2],'w'))" "$(cygpath -w "$QA")" "$QA/roots.json"
cat "$QA/roots.json"     # three absolute Windows paths under $QA\roots
```

Copy **only** these. Never copy `web-instance*.json`, `inventory.sqlite3.lock`, `source-recovery`, `merge-cache/audio-staging`, `replacement-recovery` or `chapter-repairs`.

Extract the app payload; do not install:

```bash
"$SEVEN" x "$INSTALLER" -o"$QA/payload" -y
"$PY" -I -B -c "
import json,hashlib,os,sys
m=json.load(open(sys.argv[1],encoding='utf-8'));root=sys.argv[2];bad=[]
for rel,e in m['payload']['files'].items():
    p=os.path.join(root,rel)
    h=hashlib.sha256(open(p,'rb').read()).hexdigest() if os.path.isfile(p) else None
    if h!=e['sha256']:bad.append(rel)
print('payload files',len(m['payload']['files']),'mismatch',bad[:5])" "$WT/dist/release-artifacts.json" "$QA/payload"
```

`mismatch []` is required.

## 4. Real-data fingerprint BEFORE (read-only)

```bash
cat > "$QA/fingerprint.py" <<'EOF'
import os, sys, json, hashlib
real = sys.argv[1]; out = {}
for d, dirs, files in os.walk(real):
    for f in files:
        p = os.path.join(d, f); s = os.lstat(p)
        out[os.path.relpath(p, real)] = [s.st_size, s.st_mtime_ns]
h = hashlib.sha256()
with open(os.path.join(real, 'inventory.sqlite3'), 'rb') as c:
    for b in iter(lambda: c.read(1 << 20), b''): h.update(b)
json.dump({'catalog_sha256': h.hexdigest(), 'files': out}, open(sys.argv[2], 'w'))
print('files', len(out), 'catalog', h.hexdigest())
EOF
"$PY" -I -B "$QA/fingerprint.py" "$REAL" "$QA/evidence/real-before.json"
```

## 5. Launch (private everything) and the no-click list

Launch from your harness so the shell is your owned child (as in the 0.16.0 smoke), with this environment and these arguments:

```bash
TEMP="$(cygpath -w "$QA/temp")" TMP="$(cygpath -w "$QA/temp")" \
APPDATA="$(cygpath -w "$QA/appdata")" LOCALAPPDATA="$(cygpath -w "$QA/localappdata")" \
"$QA/payload/Books Arranger.exe" \
  --data-dir="$(cygpath -w "$QA/data")" --port=5212 \
  --roots-json="$(cygpath -w "$QA/roots.json")" \
  --shell-profile="$(cygpath -w "$QA/profile")" --show-inactive --quiet-errors
```

- `--data-dir` skips first-run Setup and opens the copy. `--shell-profile` keeps away from the real profile; its `desktop-settings.json` points at the real data folder, so never omit this flag. Port 5212 keeps 5210 free. `TEMP` keeps SQLite temp files inside `$QA/temp`, where they are counted.
- Expected in the window: version label for the build under test, "Automatic processing: Paused" (saved run after restart), audiobook jobs Paused with 194 queued, and **0 approved books**. Zero approved is expected: the private roots hide the catalog's `Z:` groups.

**Do NOT click:** Start/Stop automatic processing, Pause/Resume audiobook jobs, scan Start/Resume/Stop, Delete recovery copies, any Restore/cleanup control, Open folder/View folder, Check for updates/Download update/Restart to update, any candidate approve/queue/review/save control, or the Browse/Setup screen (it must not appear; if it does, Quit and STOP).

Allowed: watching, reading UI text, the title-bar Close (hides to tray) and showing the window again, and the in-window **Quit Books Arranger** at the end.

## 6. Observe for 10 minutes (5 shown, 5 hidden to tray)

Sample every 10 s, read-only. The engine is the owner of the 5212 listener.

```bash
cat > "$QA/sample.py" <<'EOF'
import ctypes as C, json, re, socket, struct, sys, time, glob, urllib.request
from ctypes import wintypes as W
K = C.WinDLL('kernel32'); P = C.WinDLL('psapi'); I = C.WinDLL('iphlpapi')
K.OpenProcess.restype = W.HANDLE; K.CreateToolhelp32Snapshot.restype = W.HANDLE
qa, seconds = sys.argv[1], int(sys.argv[2])
def owner(port):
    n = W.DWORD(); I.GetExtendedTcpTable(None, C.byref(n), False, 2, 3, 0); b = C.create_string_buffer(n.value)
    I.GetExtendedTcpTable(b, C.byref(n), False, 2, 3, 0); raw = b.raw
    for i in range(int.from_bytes(raw[:4], 'little')):
        st, la, lp, ra, rp, pid = struct.unpack_from('<IIIIII', raw, 4 + 24 * i)
        if socket.ntohs(lp & 0xFFFF) == port: return pid
class TE(C.Structure): _fields_ = [('size', W.DWORD), ('u', W.DWORD), ('tid', W.DWORD), ('owner', W.DWORD), ('b', W.LONG), ('d', W.LONG), ('f', W.DWORD)]
class PM(C.Structure): _fields_ = [('cb', W.DWORD), ('pf', W.DWORD)] + [(n, C.c_size_t) for n in ('pw', 'w', 'a', 'b', 'c', 'd', 'e', 'g', 'private')]
def threads(pid):
    s = K.CreateToolhelp32Snapshot(4, 0); e = TE(); e.size = C.sizeof(e); n = 0; ok = K.Thread32First(s, C.byref(e))
    while ok: n += e.owner == pid; ok = K.Thread32Next(s, C.byref(e))
    K.CloseHandle(s); return n
def private(pid):
    h = K.OpenProcess(0x1000, False, pid); m = PM(); m.cb = C.sizeof(m); P.GetProcessMemoryInfo(h, C.byref(m), m.cb); K.CloseHandle(h); return m.private // 2**20
token = re.search(r'name="books-token" content="([^"]+)"', urllib.request.urlopen('http://127.0.0.1:5212/', timeout=30).read().decode()).group(1)
end = time.time() + seconds
while time.time() < end:
    pid = owner(5212); t = time.perf_counter()
    try:
        urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:5212/api/state?library=Audiobooks', headers={'X-Books-Token': token}), timeout=30).read(); lat = round(time.perf_counter() - t, 3)
    except Exception as error: lat = 'error: ' + repr(error)[:80]
    print(json.dumps({'t': time.strftime('%H:%M:%S'), 'engine': pid, 'threads': threads(pid) if pid else None, 'private_MB': private(pid) if pid else None,
                      'etilqs': len(glob.glob(qa + '/temp/etilqs_*')), 'state_latency_s': lat}), flush=True)
    time.sleep(10)
EOF
"$PY" -I -B "$QA/sample.py" "$QA" 600 | tee "$QA/evidence/samples.jsonl"
```

Hide the window to the tray (title-bar Close) at the 5-minute mark, and confirm the tray icon is present.

**Pass criteria (all required):**

| Check | Required |
|---|---|
| Engine threads | Last sample minus first ≤ 5, and never above first + 10 |
| Engine private memory | Growth ≤ 150 MB from the 1-minute sample to the last sample |
| SQLite temp files (`etilqs_*` in `$QA/temp`) | ≤ 4 in every sample |
| `/api/state` latency | p95 < 2.0 s, max < 5.0 s, no errors (after the first minute if the NAS was asleep — see §1) |
| Window, while shown | Never shows "Waiting for the engine checkpoint…"; "Start automatic processing" is **enabled** (do not click it); "Automatic processing: Paused" |
| After showing the window again from the tray | Same as above within 5 s |

For reference, Ender's profile on a copy (real paths emulated as missing, so the real machine is slower):
- one status computation: 4.9–5.0 s before → 0.85–1.0 s after
- one desktop status poll: 0.94 s cold, 0.06 s within 1 s of the last (before: 10–10.5 s)
- 40 simultaneous polls: 1 computation, 1.9 s total
- 60 s at 3 requests/s: 30 computations, at most 3 live request threads, p95 0.95 s

After the review fixes (2026-10-17, same copy, same emulation): one computation 0.76–0.81 s; one desktop poll 0.77–0.79 s cold, 0.02 s right after; 40 simultaneous polls: 1 computation, 1.2 s. Idle polling as the app does it (page every 0.8 s after each answer, shell once a second) for 30 s: 21 computations, page p95 0.82 s, shell p95 0.84 s. Answers now age from the start of their computation, so at this speed most polls compute fresh: expect about one computation per 1.5 s at idle (it was one per 2 s).

Expect roughly 1–2 s per computation on the real machine.

## 7. Quit, then prove nothing real changed

1. Click the in-window **Quit Books Arranger**. Required: the shell exits with code 0 within 30 s; engine and host are gone; port 5212 is free; `$QA/temp` has 0 `etilqs_*` files.
2. Run the AFTER fingerprint and compare:

```bash
"$PY" -I -B "$QA/fingerprint.py" "$REAL" "$QA/evidence/real-after.json"
"$PY" -I -B -c "import json,sys;a=json.load(open(sys.argv[1]));b=json.load(open(sys.argv[2]));d=sorted(k for k in set(a['files'])|set(b['files']) if a['files'].get(k)!=b['files'].get(k));print('catalog same:',a['catalog_sha256']==b['catalog_sha256'],'changed paths:',d[:10],len(d))" "$QA/evidence/real-before.json" "$QA/evidence/real-after.json"
```

Required: `catalog same: True`, `changed paths: [] 0`. Any difference means STOP and report it; do not touch the real folder.

Copy-only effects that are **expected**, inside `$QA/data` only:
- `web-instance.json`, the lock file, `-wal` and `-shm`;
- the saved run stays Paused;
- possibly attention rows from startup enrollment.

## 8. Cleanup and verdict

- Keep `$QA/evidence/*` (samples, both fingerprints, harness log) for the report. Remove the rest of `$QA`, the 470 MB catalog copy included, with the `studio-disk-hygiene` skill.
- The QA report must state the build SHA, the source commit, the copy's catalog SHA (equal to the real one at copy time), every §6 criterion with its measured value, the §7 result, and that no §5 control was clicked.
