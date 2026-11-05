import difflib,hashlib,json,pathlib,shutil,subprocess
root=pathlib.Path(__file__).parent
source=pathlib.Path('C:/Antigravity Projects/Worktrees/Books Arranger/durable-decisions-20261105')
target=pathlib.Path('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/Docs/Evidence/durable-decisions_2026-11-05/names-backend-stage-r2');target.mkdir(parents=True,exist_ok=False)
base='c92b724e2969aa2d277f1fcac4216ec1fc122293'
paths=['durable_decisions.py','decision_runtime.py','merge_service.py','web_server.py','tests/test_integration_242.py','tests/test_lock_timing.py','tests/test_action_queue.py'];files=[];patch=b''
for name in paths:
 raw=(source/name).read_bytes();before=subprocess.run(['git','-C',str(source),'show',base+':'+name],capture_output=True);old=before.stdout if before.returncode==0 else b''
 files.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'lf_sha256':hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest(),'baseline_lf_sha256':hashlib.sha256(old.replace(b'\r\n',b'\n')).hexdigest() if old else None})
 if old:patch+=subprocess.check_output(['git','-C',str(source),'diff',base,'--',name])
 else:patch+=('diff --git a/'+name+' b/'+name+'\nnew file mode 100644\n'+''.join(difflib.unified_diff([],raw.decode('utf-8').splitlines(keepends=True),fromfile='/dev/null',tofile='b/'+name))).encode('utf-8')
subprocess.run(['git','-C',str(source),'-c','core.whitespace=cr-at-eol','diff',base,'--check','--',*[name for name in paths if name!='decision_runtime.py']],check=True)
for name in ['curated_decisions.py','tolkien_trilogy.py','public_research.py','review_backend.py','tests/test_shared_routing.py']:
 expected=subprocess.check_output(['git','-C',str(source),'show','11b1e0227812326da2ea4905a8ebedfe961d13a7:'+name])
 assert (source/name).read_bytes().replace(b'\r\n',b'\n')==expected.replace(b'\r\n',b'\n'),name
(root/'names-backend.patch').write_bytes(patch)
names=['owned.mjs','focused.py','freeze-names-r2.py','names-backend.patch']
for run in ('names-atomic-first','names-atomic-corrected','names-binding','names-http-first','names-backend-cohort','names-http-final','runtime-liveness','runtime-liveness-corrected','names-backend-liveness-cohort'):names.extend([run+'.json',run+'.log'])
evidence=[]
for name in names:
 raw=(root/name).read_bytes();shutil.copyfile(root/name,target/name);evidence.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
summary={'baseline':base,'files':files,'patch_sha256':hashlib.sha256(patch).hexdigest(),
 'stage':'Names backend only; frontend and other Save/Approve consumers not switched. New authenticated /api/book-decisions accepts ONLY names, all other actions refuse before durable acceptance. /status reconciles same request ID fromSQLite.',
 'atomicity':'Existing names transaction now verifies application/book/source/value/head binding and commits names entries+pending approval hold+terminal decision receipt together. No-op commits guarded terminalreceipt. Crashbeforecommit rollsbacknames/context/receipt; restartreadsappliedstate beforeanyrepeat. ApplicationpreparesoutsideSQLitewriter; acceptedintentstoredwithoutworkerlocks. No source fingerprint/revision drift auto-rebase.',
 'runtime':'DecisionRuntime recovers accepted names at service start; consumer busy leaves accepted intent for later retry, independentbooks canproceed. Catalog scan/hold-write failures cannot kill the owner; transient and permanent failures expose typed runtime status, keep stored intent, and retry fresh durable state after bounded waits. Unknown consumer errors are held, never blindly replayed. Application startup failure after acceptance cannot turn a committed receipt into a refused Save. Close signals and joins its catalogreader before teardown. No audiobook worker/start/conversion is invoked by names application. Fulfilled payload pruned onlyafterconsumerreceiptcommits; names evidence/tombstones remain.',
 'results':'39/39 ledger+integration242+actualSourceFolderDispatchTests PASS8.822s(owned9.576s), plus explicit transient/permanent runtime scan-failure visibility and automatic recovery without a new click. LastnormalHTTPcase additionallycheckedtokenandunwiredapprove denialPASS1.551s. ActualMerge4workerlocks held during HTTPaccept<1s; requeststatusreconciles, runtimeclosed/reopenedbeforeapply, savednamesapplyonceafterrelease, sameIDreplayreturnsapplied, jobsremainempty/sourcebytesunchanged. Threeatomicnamescasesincludingrollback/noop passed separately. Initialtest-onlymissinguuidimport corrected with rawfailure preserved.',
 'preserved_Tolkien':'Allfive imported11b1e0 source/test files normalized-equal verified, excluded; no evidence-dispatch overwrite.',
 'remaining':'Senua code-boundaryreview before commit; then Approve/review/choices/tracks transaction consumers and frontend durable receipt/reconciliation. No full/build/release/productionfeaturecompletionclaim.',
 'scope':'Private fixtures only; no liveDB/API/Z/focus. Scratch remainsownedactiveforfollowingstages. Existing test modules already canonical; newrootmodule collects automatically.',
 'evidence':evidence}
(target/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'path':str(target),'summary_sha256':hashlib.sha256((target/'summary.json').read_bytes()).hexdigest(),'patch_sha256':summary['patch_sha256'],'evidence_files':len(evidence)+1}))
