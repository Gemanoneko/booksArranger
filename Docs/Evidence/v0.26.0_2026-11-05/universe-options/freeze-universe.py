import difflib,hashlib,json,pathlib,shutil,subprocess
root=pathlib.Path(__file__).parent;source=pathlib.Path('C:/Antigravity Projects/Worktrees/Books Arranger/0260-release-20261105-r1')
target=pathlib.Path('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/Docs/Evidence/v0.26.0_2026-11-05/universe-options');target.mkdir(parents=True,exist_ok=False)
base='2fa8f21374e1f1c4858db013799bac4b1c020fd3';paths=['merge_service.py','tests/test_entered_names.py','tests/test_inline_series_frontend.js'];files=[];patch=''
for name in paths:
 raw=(source/name).read_bytes();old=subprocess.check_output(['git','-C',str(source),'show',base+':'+name]);lf=raw.replace(b'\r\n',b'\n');before=old.replace(b'\r\n',b'\n')
 files.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'lf_sha256':hashlib.sha256(lf).hexdigest(),'baseline_lf_sha256':hashlib.sha256(before).hexdigest()})
 patch+='diff --git a/'+name+' b/'+name+'\n'+''.join(difflib.unified_diff(before.decode('utf-8').splitlines(keepends=True),lf.decode('utf-8').splitlines(keepends=True),fromfile='a/'+name,tofile='b/'+name))
(root/'source.patch').write_text(patch,encoding='utf-8',newline='\n')
names=['owned.mjs','focused.py','freeze-universe.py','source.patch']
for run in ('universe-provider','universe-store-cohort','universe-dom','universe-dom-corrected'):names.extend([run+'.json',run+'.log'])
evidence=[]
for name in names:
 data=(root/name).read_bytes();shutil.copyfile(root/name,target/name);evidence.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
summary={'baseline':base,'files':files,'patch_sha256':hashlib.sha256(patch.encode()).hexdigest(),'behavior':'Existing editable Universe datalist always offers exact Warhammer40K spelling as requested: Warhammer 40K, SCP, Eve Online, World of Warcraft. Union occurs after existing2000 learned-value bound so no previously offered learned/custom value is displaced and all four stay available in large catalogs. No selected value, book assignment, source/output, job or name entry is changed by offering suggestions.',
 'tests':'8/8 existing StoreTests PASS0.442s; one provider case covers2001 learned values plus saved custom and unchanged SQL rows. Existing complete inline-series DOM script PASS, proves four choices, existing learned value, free custom typing and choosing SCP. Initial DOM test looked for Universe in inline ask controls instead of full namesRows.inputs; test-only lookup corrected, raw failure preserved. All owned results normal closure/nativezero.',
 'runtime_scope':'No frontend product change, new control, layout, liveAPI/DB/Z/focus, build/full/native/release execution. Three code/test paths frozen for Sully integration; version0.26.0 remains Sully-owned.', 'evidence':evidence}
(target/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'path':str(target),'summary_sha256':hashlib.sha256((target/'summary.json').read_bytes()).hexdigest(),'patch_sha256':summary['patch_sha256'],'files':files}))
