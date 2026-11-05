import difflib,hashlib,json,pathlib,shutil,subprocess
root=pathlib.Path(__file__).parent
source=pathlib.Path('C:/Antigravity Projects/Worktrees/Books Arranger/durable-decisions-20261105')
target=pathlib.Path('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/Docs/Evidence/durable-decisions_2026-11-05/ledger-stage');target.mkdir(parents=True,exist_ok=False)
base='eb38a3502286f6ab70d578df2d02447a9f68d93c';paths=['durable_decisions.py','tests/test_action_queue.py'];files=[]
for name in paths:
 raw=(source/name).read_bytes();before=subprocess.run(['git','-C',str(source),'show',base+':'+name],capture_output=True)
 old=before.stdout if before.returncode==0 else b''
 files.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'lf_sha256':hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest(),'baseline_lf_sha256':hashlib.sha256(old.replace(b'\r\n',b'\n')).hexdigest() if old else None})
patch=subprocess.check_output(['git','-C',str(source),'diff',base,'--','tests/test_action_queue.py'])
patch+=('diff --git a/durable_decisions.py b/durable_decisions.py\nnew file mode 100644\n'+''.join(difflib.unified_diff([], (source/'durable_decisions.py').read_text(encoding='utf-8').splitlines(keepends=True),fromfile='/dev/null',tofile='b/durable_decisions.py'))).encode('utf-8')
(root/'ledger.patch').write_bytes(patch)
subprocess.run(['git','-C',str(source),'-c','core.whitespace=cr-at-eol','diff',base,'--check','--','tests/test_action_queue.py'],check=True)
evidence=[]
for name in ('owned.mjs','focused.py','ledger-first.json','ledger-first.log','ledger-acceptance.json','ledger-acceptance.log','ledger.patch','freeze-ledger.py'):
 file=root/name;raw=file.read_bytes();shutil.copyfile(file,target/name);evidence.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
summary={'baseline':base,'files':files,'patch_sha256':hashlib.sha256(patch).hexdigest(),'design':'eb38a35:Docs/BooksArranger_DurableDecisions_Design_2026-11-05.md',
 'milestone':'Foundation only: new SQLite ledger/receipt/fence API and existing-suite private tests. NOT connected to live HTTP, Merge application, startup worker or frontend; no claim user-visible durable Save/Approve complete.',
 'checks':'9/9 PASS1.533s (owned2.013s), closed/outputComplete/nativecompletezero/no force/timeout. Actual MergeService operation/review/group/AudioJobs locks held by another thread while acceptance commits under1s. RealSQLite writer contention boundedunder1s and cannot returndurableacceptance; sameclientrequestID retryafterrelease reconcilesexactlyonce. Reopen retainspayload; disjointeffects survive; incompatiblelateholddoesnotmovehead; oldgenerationfenced; substepconsumertransactionrollback atomic; payloadprunedonlyfulfilled withreceipt/hash tombstone.',
 'remaining':'Wire existing source-safe consumers and their same-transaction receipts, server acceptance/reconciliation, restart worker, all existing Save/Approve UI including overlays/lostreply; ordinary review and independent focused QA required. No full/build/release.',
 'scope':'Private fixtures only, no live DB/API/Z/focus. Current whole-feature scratch remains owned and active for following integration stage; no cleanup yet. Existing test_action_queue.py already in canonical check graph; newrootmodule automatically collected by packaging.',
 'evidence':evidence}
(target/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'path':str(target),'summary_sha256':hashlib.sha256((target/'summary.json').read_bytes()).hexdigest(),'patch_sha256':summary['patch_sha256']}))
