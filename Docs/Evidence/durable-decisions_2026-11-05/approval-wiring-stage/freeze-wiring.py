import difflib,hashlib,json,pathlib,shutil,subprocess
root=pathlib.Path(__file__).parent
source=pathlib.Path('C:/Antigravity Projects/Worktrees/Books Arranger/durable-decisions-20261105')
target=pathlib.Path('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/Docs/Evidence/durable-decisions_2026-11-05/approval-wiring-stage');target.mkdir(parents=True,exist_ok=False)
base='229a5c2a291d780f7e0daa62f3028e07f52b2892'
paths=['decision_contract.py','decision_runtime.py','merge_service.py','web_server.py','tests/test_lock_timing.py','tests/test_shared_routing.py'];files=[];patch=''
for name in paths:
 raw=(source/name).read_bytes();before=subprocess.run(['git','-C',str(source),'show',base+':'+name],capture_output=True);old=before.stdout if before.returncode==0 else b''
 lf=raw.replace(b'\r\n',b'\n');oldlf=old.replace(b'\r\n',b'\n')
 assert lf!=oldlf,name
 files.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'lf_sha256':hashlib.sha256(lf).hexdigest(),'baseline_lf_sha256':hashlib.sha256(oldlf).hexdigest() if old else None})
 patch+='diff --git a/'+name+' b/'+name+'\n'
 if not old:patch+='new file mode 100644\n'
 patch+=''.join(difflib.unified_diff(oldlf.decode('utf-8').splitlines(keepends=True),lf.decode('utf-8').splitlines(keepends=True),fromfile='a/'+name if old else '/dev/null',tofile='b/'+name))
for name in ['durable_decisions.py','audio_jobs.py','decision_effects.py','review_backend.py','tests/test_action_queue.py','tests/test_review_backend.py']:
 expected=subprocess.check_output(['git','-C',str(source),'show',base+':'+name])
 assert (source/name).read_bytes().replace(b'\r\n',b'\n')==expected.replace(b'\r\n',b'\n'),name
(root/'approval-wiring.patch').write_text(patch,encoding='utf-8',newline='\n')
names=['owned.mjs','focused.py','freeze-wiring.py','approval-wiring.patch']
for run in ('durable-approve-first','durable-approve-green','durable-mid-approve-first','durable-post-track-red','durable-restart-green','durable-six-http-first','durable-wiring-cohort'):names.extend([run+'.json',run+'.log'])
evidence=[]
for name in names:
 raw=(root/name).read_bytes();shutil.copyfile(root/name,target/name);evidence.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
summary={'baseline':base,'files':files,'patch_sha256':hashlib.sha256((target/'approval-wiring.patch').read_bytes()).hexdigest(),
 'patch_method':'Direct committed baseline blob to actual source bytes, LF-normalized; never relies on this old-base checkout index. Previously integrated six consumer files match229a5c2 exactly after LF normalization and are excluded.',
 'contract':'All six authenticated durable actions accept before worker/global admission. Exact original payload, server-derived effect keys and request ID/hash are retained; status404 enables same-ID reconciliation; book returns only effective unresolved head owners for reopen overlay. File review has deterministic library/path identity and exact catalog size/modified generation. No media/source file access at acceptance.',
 'application':'Existing source/identity/metadata/cover/chapter/overwrite guards remain. Approve binds every legacy argument to captured payload before effects; set-aside/names/same-author/review/context/tracks/checkpoints have request receipts; English-name rules and final approval+job+applied receipt share enqueue transaction. Answer-only terminal outcome has atomic names/rules/reset+receipt. Original track choice plan freezes before self-writes so restart does not reinterpret internal track evidence as a different user choice. Runtime recovers compatible exact receipted revisions, projects only disjoint names from superseded approval, retains validation holds, never starts an audio producer for Save/Approve.',
 'results':'54/54 affected methods PASS36.389s (owned37.159s, closed/outputComplete/native complete+zero, no timeout/force). HTTP six-action method explicitly checks every action acceptance under four real worker locks <1s, status/request/hash/reopen, close/restart and same-ID replay. Five Save types apply; controlled approval validation hold retains payload. Two actual native Tolkien approval cases queue one pending job without conversion/source mutation. Injected interruptions after metadata and after tracks recover the same request into exactly one pending job after reopening MergeService, no second press. Post-track initial RED exposed self-write interpretation and is preserved; corrected two-point proof PASS6.071s. Runtime SQLite failure/recovery and constructor abort ownership cases remain in affected cohort.',
 'boundaries':'Backend wiring only. Frontend independently owned by Ender_m4b; no UI source edits here. No liveAPI/liveDB/Z/focus/full check/build/release. No whole-feature QA or release claim until integrated backend+frontend focused verification.',
 'evidence':evidence}
(target/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'path':str(target),'summary_sha256':hashlib.sha256((target/'summary.json').read_bytes()).hexdigest(),'patch_sha256':summary['patch_sha256'],'files':files}))
