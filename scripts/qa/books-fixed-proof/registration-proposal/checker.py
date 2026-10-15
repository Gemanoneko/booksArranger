import ctypes as C,hashlib,json,os,pathlib,subprocess,sys
K=C.WinDLL('kernel32',use_last_error=True)
K.CreateFileW.argtypes=[C.c_wchar_p,C.c_ulong,C.c_ulong,C.c_void_p,C.c_ulong,C.c_ulong,C.c_void_p];K.CreateFileW.restype=C.c_void_p
K.GetFinalPathNameByHandleW.argtypes=[C.c_void_p,C.c_wchar_p,C.c_ulong,C.c_ulong];K.GetFinalPathNameByHandleW.restype=C.c_ulong
K.ReadFile.argtypes=[C.c_void_p,C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.c_void_p];K.CloseHandle.argtypes=[C.c_void_p]
K.GetFileInformationByHandle.argtypes=[C.c_void_p,C.c_void_p];K.GetFileInformationByHandle.restype=C.c_int
handles=[]
raw=sys.stdin.buffer.read(1048577)
if len(raw)>1048576:raise RuntimeError('Oversized hook input')
try:command=json.loads(raw).get('tool_input',{}).get('command')
except (ValueError,TypeError,AttributeError):command=None
books=isinstance(command,str) and command.startswith("& 'C:\\Python314\\python.exe' -I -S -B -c '# Books fixed maintenance-13\n")
old_records=[["C:\\Antigravity Projects\\Studio Illuminati\\scripts\\qa\\quicklaunch-dependency-route\\python-bootstrap-pins.json","2413c208eb7d0e8085025e6bce250c26d8878f38389ca1196158445a8863155d"],["C:\\Program Files\\nodejs\\node.exe","a619e2e09eb0d50ef4c733d678b4d22689d2afef138cd67fd3fa107b535f8819"],["C:\\Users\\AnGeLZzZ\\.codex\\hooks\\command-safety-route\\runtime-repair-20261013\\hook.mjs","34edde5437cabc1d2600d1f415d5ec126f77dbe7d234a4fdb0e942877d02cb03"],["C:\\Antigravity Projects\\Studio Illuminati\\scripts\\qa\\quicklaunch-dependency-route\\contract.mjs","ed77c944edcedfc2ae5663178c4e23019fd11fcb8bad0f60b78c6b4b6353b5b1"],["C:\\Antigravity Projects\\Studio Illuminati\\scripts\\qa\\quicklaunch-dependency-route\\hook.mjs","5836fbcde7ec01fc31d174d659dc2acfb80337e874a5e3a1be4ae31731debf81"],["C:\\Users\\AnGeLZzZ\\.codex\\hooks\\command-safety-route\\runtime-repair-20261013\\timeout-compatibility-hook.mjs","1207c0bb0837d111e8b62642b1d13595a6e4d36333f07688fd3365685cb63184"],["C:\\Users\\AnGeLZzZ\\.codex\\hooks\\command-safety-route\\runtime-repair-20261013\\observation-policy.capture-v1.json","a612ab9002c463376a01550fd407f0f94344d40be41b6e6292a9be0a890a6f92"],["C:\\Users\\AnGeLZzZ\\.codex\\hooks\\command-safety-route\\timeout-v1\\timeout-compatibility-hook.mjs","eeddc99ee66975f2a287da371ab39b063b6af6f3236d47ce01b9e33ebd2c0f76"],["C:\\Users\\AnGeLZzZ\\.codex\\hooks\\command-safety-route\\observer.mjs","4eab19e937a28166f8af4e019b325f1118be7e3d644c1914d72351b541b2a171"],["C:\\Users\\AnGeLZzZ\\.codex\\hooks\\command-safety-route\\observation-policy.capture-v1.json","4b0101b90e67b741bc9011044520b87a8cd143780f9d35b52cac8d74855a0ec3"],["C:\\Antigravity Projects\\Studio Illuminati\\scripts\\qa\\quicklaunch-dependency-route\\policy.json","2867c5dbfeb53b81213c74fc497be5280d0cf96af00772f761e401c890e2ed48"],["C:\\Antigravity Projects\\Studio Illuminati\\scripts\\qa\\quicklaunch-dependency-route\\frozen.json","0598caa4452dd6af828da5ca38b70fa6c152d61a4f8dff750df688e8b2500d47"],["C:\\Users\\AnGeLZzZ\\.codex\\hooks\\command-safety-route\\timeout-v1\\fixed-bootstrap-candidate.json","fb695a60c92b8933521fa810ef870e11e5e0dc4dbaf1f85e5ec54220da64e222"]]
books_records=[["C:\\Antigravity Projects\\Studio Illuminati\\scripts\\qa\\quicklaunch-dependency-route\\python-bootstrap-pins.json","2413c208eb7d0e8085025e6bce250c26d8878f38389ca1196158445a8863155d"],["C:\\Program Files\\nodejs\\node.exe","a619e2e09eb0d50ef4c733d678b4d22689d2afef138cd67fd3fa107b535f8819"],["C:\\Antigravity Projects\\Studio Illuminati\\WIP\\Books Arranger\\scratch\\resume-2026-10-15\\maintenance-worktree\\scripts\\qa\\books-fixed-proof\\runner.py","a62a9ed2ee5a5098c82af36dfcc62e352a55427b8b37fc201b8c48f892070d5c"],["C:\\Antigravity Projects\\Studio Illuminati\\WIP\\Books Arranger\\scratch\\resume-2026-10-15\\maintenance-worktree\\scripts\\qa\\books-fixed-proof\\windows-owner.py","525c9df2b22c732065cf1cd79cca7def1388885e99d58c4b0770cc5c09236bdd"],["C:\\Antigravity Projects\\Studio Illuminati\\WIP\\Books Arranger\\scratch\\resume-2026-10-15\\maintenance-worktree\\scripts\\qa\\books-fixed-proof\\proof-entry.py","53fc9ef90d274d2c7f14eb4ff61be89bbe50b189ec59a72a66c2a1fde2597ce8"],["C:\\Antigravity Projects\\Studio Illuminati\\WIP\\Books Arranger\\scratch\\resume-2026-10-15\\maintenance-worktree\\scripts\\qa\\books-fixed-proof\\contract.mjs","af7fa9c8d17bca1e4caaf7fb9b05d510a7a41082af1da523d1e24c82d297c1a0"],["C:\\Antigravity Projects\\Studio Illuminati\\WIP\\Books Arranger\\scratch\\resume-2026-10-15\\maintenance-worktree\\scripts\\qa\\books-fixed-proof\\hook-adapter.mjs","1b6918ba86a2ea83285af55d91e39fb237ecc375450250c8ebbdf71ff94d0f4f"],["C:\\Antigravity Projects\\Studio Illuminati\\WIP\\Books Arranger\\scratch\\resume-2026-10-15\\maintenance-worktree\\scripts\\qa\\books-fixed-proof\\policy.json","d7c1b8d4fd0e222b7769df357372529174675b5f1d57a435233339f18346f792"],["C:\\Antigravity Projects\\Studio Illuminati\\WIP\\Books Arranger\\scratch\\resume-2026-10-15\\maintenance-worktree\\scripts\\qa\\books-fixed-proof\\frozen.json","a25faaa2929aaeaf987135cac6721064f7b8711a4e83f515c7532bc4a94b3b86"],["C:\\Antigravity Projects\\Studio Illuminati\\WIP\\Books Arranger\\scratch\\resume-2026-10-15\\maintenance-worktree\\scripts\\qa\\books-fixed-proof\\input-manifest.json","0d8039294b5e3fd07fba733f3eab6188b8b175eb315e55d5b38381132a5fafba"]]
records=(books_records if books else old_records)+[["C:\\Antigravity Projects\\Studio Illuminati\\WIP\\Books Arranger\\scratch\\resume-2026-10-15\\maintenance-worktree\\scripts\\qa\\books-fixed-proof\\registration-proposal\\route.mjs","ca10d28df11947cf3560adcb57623ec2570feed10dd259fb1e3b606e0b4e697b"]]
try:
 for filename,expected in records:
  p=pathlib.Path(filename)
  for q in [*reversed(p.parents),p]:
   if os.stat(q,follow_symlinks=False).st_file_attributes&0x400:raise RuntimeError('Reparse checker refused')
   h=K.CreateFileW(str(q),(0x81 if books else 0) if q!=p else 0x80000000,1,None,3,(0x00200000 if books else 0)|(0x02000000 if q!=p else 0),None)
   if h==C.c_void_p(-1).value:raise RuntimeError('Checker unavailable')
   handles.append(h);b=C.create_unicode_buffer(32768);n=K.GetFinalPathNameByHandleW(h,b,len(b),0)
   if not 0<n<len(b) or os.path.normcase(b.value[4:].rstrip(chr(92)))!=os.path.normcase(str(q).rstrip(chr(92))):raise RuntimeError('Checker canonical identity refused')
   if books:
    info=(C.c_ulong*13)()
    if not K.GetFileInformationByHandle(h,C.byref(info)) or info[0]&0x400 or bool(info[0]&0x10)!=(q!=p) or (q==p and info[10]!=1):raise RuntimeError('Books native kind/link fact refused')
  digest=hashlib.sha256();parts=[]
  while True:
   b=C.create_string_buffer(65536);n=C.c_ulong()
   if not K.ReadFile(handles[-1],b,len(b),C.byref(n),None):raise RuntimeError('Checker read failed')
   if not n.value:break
   digest.update(b.raw[:n.value])
   if filename=="C:\\Antigravity Projects\\Studio Illuminati\\scripts\\qa\\quicklaunch-dependency-route\\python-bootstrap-pins.json":parts.append(b.raw[:n.value])
  if digest.hexdigest()!=expected:raise RuntimeError('Checker byte tamper')
  if filename=="C:\\Antigravity Projects\\Studio Illuminati\\scripts\\qa\\quicklaunch-dependency-route\\python-bootstrap-pins.json":records.extend((x['path'],x['sha256']) for x in json.loads(b''.join(parts)))
 sys.exit(subprocess.run(["C:\\Program Files\\nodejs\\node.exe","C:\\Antigravity Projects\\Studio Illuminati\\WIP\\Books Arranger\\scratch\\resume-2026-10-15\\maintenance-worktree\\scripts\\qa\\books-fixed-proof\\registration-proposal\\route.mjs"],input=raw,cwd="C:\\Antigravity Projects\\Studio Illuminati").returncode)
finally:
 for h in reversed(handles):K.CloseHandle(h)
