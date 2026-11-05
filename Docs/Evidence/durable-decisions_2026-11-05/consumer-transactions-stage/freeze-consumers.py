import difflib,hashlib,json,pathlib,shutil,subprocess
root=pathlib.Path(__file__).parent
source=pathlib.Path('C:/Antigravity Projects/Worktrees/Books Arranger/durable-decisions-20261105')
target=pathlib.Path('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/Docs/Evidence/durable-decisions_2026-11-05/consumer-transactions-stage');target.mkdir(parents=True,exist_ok=False)
base='9bcc58b5876e0ad2e6de8e4de39597f2bb9b7ac5'
paths=['durable_decisions.py','audio_jobs.py','decision_effects.py','review_backend.py','tests/test_action_queue.py','tests/test_review_backend.py'];files=[];patch=b''
for name in paths:
 raw=(source/name).read_bytes();before=subprocess.run(['git','-C',str(source),'show',base+':'+name],capture_output=True);old=before.stdout if before.returncode==0 else b''
 files.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'lf_sha256':hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest(),'baseline_lf_sha256':hashlib.sha256(old.replace(b'\r\n',b'\n')).hexdigest() if old else None})
 if old:patch+=subprocess.check_output(['git','-C',str(source),'diff',base,'--',name])
 else:patch+=('diff --git a/'+name+' b/'+name+'\nnew file mode 100644\n'+''.join(difflib.unified_diff([],raw.decode('utf-8').splitlines(keepends=True),fromfile='/dev/null',tofile='b/'+name))).encode('utf-8')
(root/'consumer-transactions.patch').write_bytes(patch)
names=['owned.mjs','focused.py','freeze-consumers.py','consumer-transactions.patch']
for run in ('approve-boundary-red','approve-boundary-green','review-atomic-first','review-atomic-corrected','approve-review-consumers'):names.extend([run+'.json',run+'.log'])
evidence=[]
for name in names:
 raw=(root/name).read_bytes();shutil.copyfile(root/name,target/name);evidence.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
summary={'baseline':base,'files':files,'patch_sha256':hashlib.sha256(patch).hexdigest(),'stage':'Unexposed transaction consumers only; Approve/review/choices/tracks durable HTTP still refused. Merge propagation and frontend are not included.',
 'atomicity':'Canonical group review + context/manual/choice evidence + request step now commit together; track hashes/confirmations + step commit together. Reopening a partial review skips its committed mutation without a new revision. Private AudioJobs enqueue binds request/current book/source/head and commits final context + pending job + optional explicit English-name rule + final decision receipt in one transaction. Injected receipt failure rolls back all effects. Disjoint approval dependencies remain; fully overlapping superseded owners no longer strand approval.',
 'results':'32 affected ledger/enqueue/review tests pass with owned native zero. Faults exercise review/context rollback, track/hash rollback, queued job/approval/rule rollback and restart partial-review replay. Existing public evidence actor/HTTPS/time validators unchanged; curated Tolkien dispatch preserved.',
 'scope':'Private fixtures only, no live/source Z/API/focus, no full/build/release. Six paths frozen for bounded review while Merge propagation continues in separate files.', 'evidence':evidence}
(target/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'path':str(target),'summary_sha256':hashlib.sha256((target/'summary.json').read_bytes()).hexdigest(),'patch_sha256':summary['patch_sha256']}))
