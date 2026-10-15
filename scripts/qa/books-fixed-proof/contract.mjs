// One Books-only operation. No shared registration or payload execution on import.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
export const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
export const ROOT=path.win32.normalize('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/resume-2026-10-15/maintenance-worktree/scripts/qa/books-fixed-proof');
export const STUDIO=path.win32.normalize('C:/Antigravity Projects/Studio Illuminati');
export const PYTHON='C:\\Python314\\python.exe';
export const SNAPSHOT=path.win32.normalize('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/resume-2026-10-15/proof-inputs-13');
export const OUTPUT=path.win32.normalize('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/resume-2026-10-15/proof-run-13-01');
export const CONTROL=path.win32.normalize('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/scratch/resume-2026-10-15/proof-control-13');
const hex=v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
export function validatePolicy(p){
 const keys=['schema','entry','root','guard_cwd','cwd','control','output','executable','argv','environment','deadline_ms','pins','manifest','fallback','evaluator'].sort().join('|');
 const env={SystemRoot:'C:\\Windows',WINDIR:'C:\\Windows',ComSpec:'C:\\Windows\\System32\\cmd.exe',PATH:'C:\\Python314;C:\\Windows\\System32',PATHEXT:'.COM;.EXE;.BAT;.CMD',TEMP:path.win32.join(OUTPUT,'tmp'),TMP:path.win32.join(OUTPUT,'tmp')};
 if(!p||Object.keys(p).sort().join('|')!==keys||p.schema!==1||p.entry!=='books-maintenance-13-fixed'||p.root!==ROOT||p.guard_cwd!==STUDIO||p.cwd!==SNAPSHOT||p.control!==CONTROL||p.output!==OUTPUT||p.executable!==PYTHON||JSON.stringify(p.argv)!==JSON.stringify(['-I','-S','-B',path.win32.join(ROOT,'proof-entry.py')])||p.deadline_ms!==600000)throw Error('Unknown fixed Books operation');
 if(Object.keys(p.environment??{}).sort().join('|')!==Object.keys(env).sort().join('|')||Object.entries(env).some(([k,v])=>p.environment[k]!==v))throw Error('Fixed private environment changed');
 if(!Array.isArray(p.pins)||!p.pins.length)throw Error('Missing immutable inputs');
 const names=new Set();for(const r of p.pins){if(Object.keys(r).sort().join('|')!=='path|sha256'||!path.win32.isAbsolute(r.path)||!hex(r.sha256)||names.has(r.path.toLowerCase()))throw Error('Invalid input pin');names.add(r.path.toLowerCase());}
 for(const n of ['runner.py','windows-owner.py','proof-entry.py','contract.mjs','hook-adapter.mjs'])if(!names.has(path.win32.join(ROOT,n).toLowerCase()))throw Error('Mandatory fixed helper missing');
 if(p.manifest?.path!==path.win32.join(ROOT,'input-manifest.json')||!hex(p.manifest.sha256))throw Error('Complete input map missing');
 const fallback={path:'C:/Users/AnGeLZzZ/.codex/hooks/command-safety-route/runtime-repair-20261013/timeout-compatibility-hook.mjs',sha256:'1207c0bb0837d111e8b62642b1d13595a6e4d36333f07688fd3365685cb63184',candidateSha:'fb695a60c92b8933521fa810ef870e11e5e0dc4dbaf1f85e5ec54220da64e222'};
 if(JSON.stringify(p.fallback)!==JSON.stringify(fallback))throw Error('Unchanged fallback identity required');
 if(JSON.stringify(p.evaluator)!==JSON.stringify({path:'C:\\Antigravity Projects\\Studio Monday\\.claude\\hooks\\dispatch.mjs',sha256:'5246fe90e99948dc97eff6d7139c92eb35d596d9a314dbe576339e581eedbdaf'}))throw Error('Original P9 evaluator changed');
 return p;
}
export function classify(raw,exact,cwd){
 if(Buffer.byteLength(raw)>1048576)throw Error('Oversized hook input');
 const p=JSON.parse(raw);
 if(!(Array.isArray(exact)?exact:[exact]).includes(p?.tool_input?.command)){
  if(typeof p?.tool_input?.command==='string'&&p.tool_input.command.startsWith("& '"+PYTHON+"' -I -S -B -c '# Books fixed maintenance-13\\n".replace('\\n','\n')))throw Error('Altered Books invocation');
  return{owned:false};
 }
 if(cwd!==STUDIO||p.cwd!==cwd||p.hook_event_name!=='PreToolUse'||p.tool_name!=='Bash'||Object.keys(p.tool_input).join('|')!=='command')throw Error('Wrong exact Books envelope');
 return{owned:true,payload:p};
}
export function render(policy, runnerSha, policySha, verify = false) {
  validatePolicy(policy);
  if (!hex(runnerSha) || !hex(policySha)) throw Error('Missing loader pins');
  // Python source uses fixed ASCII JSON strings; caller input never becomes code.
  const runner = path.win32.join(ROOT, 'runner.py');
  const code = `# Books fixed maintenance-13\nimport ctypes as C,hashlib,os,pathlib,time,threading\nBOOTSTRAP_STARTED=time.monotonic()\ndef bootstrap_expired():os._exit(124)\nbootstrap_timer=threading.Timer(${verify ? '6' : '600'},bootstrap_expired)\nbootstrap_timer.daemon=True\nbootstrap_timer.start()\nK=C.WinDLL('kernel32',use_last_error=True)\nK.CreateFileW.argtypes=[C.c_wchar_p,C.c_ulong,C.c_ulong,C.c_void_p,C.c_ulong,C.c_ulong,C.c_void_p]\nK.CreateFileW.restype=C.c_void_p\nK.GetFinalPathNameByHandleW.argtypes=[C.c_void_p,C.c_wchar_p,C.c_ulong,C.c_ulong]\nK.GetFinalPathNameByHandleW.restype=C.c_ulong\nK.ReadFile.argtypes=[C.c_void_p,C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.c_void_p]\nK.GetFileSizeEx.argtypes=[C.c_void_p,C.POINTER(C.c_longlong)]\nK.GetFileSizeEx.restype=C.c_int\nK.CloseHandle.argtypes=[C.c_void_p]\nK.CloseHandle.restype=C.c_int\nhandles=[]\ntry:\n p=pathlib.Path(${JSON.stringify(runner)})\n for q in [*reversed(p.parents),p]:\n  if os.stat(q,follow_symlinks=False).st_file_attributes&0x400:raise RuntimeError('Reparse bootstrap refused')\n  h=K.CreateFileW(str(q),0x81 if q!=p else 0x80000000,1,None,3,0x00200000|(0x02000000 if q!=p else 0),None)\n  if h==C.c_void_p(-1).value:raise RuntimeError('Bootstrap unavailable')\n  handles.append(h)\n  b=C.create_unicode_buffer(32768);n=K.GetFinalPathNameByHandleW(h,b,len(b),0)\n  if not 0<n<len(b) or os.path.normcase(b.value[4:].rstrip(chr(92)))!=os.path.normcase(str(q).rstrip(chr(92))):raise RuntimeError('Bootstrap canonical identity refused')\n expected_size=C.c_longlong()\n if not K.GetFileSizeEx(handles[-1],C.byref(expected_size)) or not 0<expected_size.value<=65536:raise RuntimeError('Bootstrap fixed size bound')\n raw=b''\n while True:\n  b=C.create_string_buffer(65536);n=C.c_ulong()\n  if not K.ReadFile(handles[-1],b,len(b),C.byref(n),None):raise RuntimeError('Bootstrap read failed')\n  if not n.value:break\n  if len(raw)+n.value>expected_size.value:raise RuntimeError('Bootstrap input grew')\n  raw+=b.raw[:n.value]\n if len(raw)!=expected_size.value:raise RuntimeError('Bootstrap input shrank')\n if hashlib.sha256(raw).hexdigest()!=${JSON.stringify(runnerSha)}:raise RuntimeError('Bootstrap tamper')\n FIXED_POLICY=${JSON.stringify(path.win32.join(ROOT,'policy.json'))}\n FIXED_POLICY_SHA=${JSON.stringify(policySha)}\n VERIFY_ONLY=${verify ? 'True' : 'False'}\n exec(compile(raw,str(p),'exec'),globals())\nfinally:\n bootstrap_timer.cancel()\n failures=[]\n for h in reversed(handles):\n  if not K.CloseHandle(h):failures.append(C.get_last_error())\n if failures:raise RuntimeError("Bootstrap handle closure failed: "+repr(failures))\n`;
  return { code, command: `& '${PYTHON}' -I -S -B -c '${code.replaceAll("'", "''")}'` };
}
export function readFrozen(file, hash) {
  const raw=fs.readFileSync(file);
  if (!hex(hash) || sha(raw) !== hash) throw Error('Frozen identity mismatch');
  return JSON.parse(raw.toString('utf8'));
}
