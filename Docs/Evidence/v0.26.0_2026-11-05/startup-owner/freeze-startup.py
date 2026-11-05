import ast,difflib,hashlib,json,pathlib,shutil,subprocess
root=pathlib.Path(__file__).parent;source=pathlib.Path('C:/Antigravity Projects/Worktrees/Books Arranger/0260-release-20261105-r1');main=pathlib.Path('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger')
target=main/'Docs/Evidence/v0.26.0_2026-11-05/startup-owner';target.mkdir(parents=True,exist_ok=False)
base=subprocess.check_output(['git','-C',str(main),'rev-parse','4941b06'],text=True).strip();paths=['web_server.py','tests/test_startup_loading.py'];files=[];patch=''
for name in paths:
 raw=(source/name).read_bytes();old=subprocess.check_output(['git','-C',str(main),'show',base+':'+name]);lf=raw.replace(b'\r\n',b'\n');before=old.replace(b'\r\n',b'\n')
 files.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'lf_sha256':hashlib.sha256(lf).hexdigest(),'baseline_lf_sha256':hashlib.sha256(before).hexdigest()})
 patch+='diff --git a/'+name+' b/'+name+'\n'+''.join(difflib.unified_diff(before.decode().splitlines(keepends=True),lf.decode().splitlines(keepends=True),fromfile='a/'+name,tofile='b/'+name))
dispositions={
 'test_approve_as_is.py':'ApproveFixture.start registers each actual service.close with addCleanup.',
 'test_automatic_media.py':'tearDown closes current service; PNG fixture replacement first closes previous service.',
 'test_catalog_busy.py':'addCleanup(self.close), close calls current self.merge.close.',
 'test_cleanup_resume.py':'local constructor is enclosed in try/finally service.close.',
 'test_desktop_update.py':'fixture addCleanup(self.close) closes current merge; local instance uses finally merge.close.',
 'test_destination_admission.py':'inherits RetryIntent.tearDown closing current service; replacement closes old before construct.',
 'test_inplace_m4b.py':'tearDown closes current service; reopening explicitly closes prior.',
 'test_local_admission.py':'tearDown closes current service before temporary directory cleanup.',
 'test_merge_service.py':'normal/reopened instances use current-service tearDown. NativeMoveStartupFence constructor lambda must fail before setup/runtime startup; positive source fence checks catalog unchanged.',
 'test_output_rename.py':'addCleanup(f.tearDown) resolves current f.service; replacement closes previous service first.',
 'test_retry_intent.py':'tearDown closes current service; activate closes old before replacement.',
 'test_shared_routing.py':'each initial/reopened service has addCleanup(service.close); deterministic restart patch keeps runtime inert until actual run_once.',
 'test_sorted_wiring.py':'addCleanup(current service.close) for the one constructed instance.',
 'test_split_books.py':'each constructor registers service.close with addCleanup, ahead of temporary-directory cleanup.',
 'test_startup_loading.py':'local construction tests close in finally; cold-serve factory owner is serve_owned, whose finally server_close closes current Merge. New failure case explicitly closes constructor service; RED fixture capture cleanup is honest.',
 'test_start_while_converting.py':'addCleanup(self.close); close calls current merge.close.',
 'test_status_read_contention.py':'tearDown calls BrowserServer.server_close, which calls merge.close (not only automatic/jobs close).',
 'test_working_lifecycle.py':'tearDown delegates current AutomaticMediaTests.tearDown; replacement closes previous service first.'}
inventory=[]
for file in [*source.glob('*.py'),*(source/'tests').glob('*.py')]:
 tree=ast.parse(file.read_text(encoding='utf-8-sig'));parents={child:node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
 for node in ast.walk(tree):
  if not isinstance(node,ast.Call) or not (isinstance(node.func,ast.Name) and node.func.id=='MergeService' or isinstance(node.func,ast.Attribute) and node.func.attr=='MergeService'):continue
  name=file.relative_to(source).as_posix();owner=[];parent=node
  while parent in parents:
   parent=parents[parent]
   if isinstance(parent,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):owner.append(parent.name)
  assert file.name in dispositions,(name,node.lineno)
  inventory.append({'path':name,'line':node.lineno,'owner':'.'.join(reversed(owner)),'disposition':dispositions[file.name]})
audit={'method':'Python AST Call nodes named MergeService across every top-level production Python and tests/*.py; rg of MergeService aliases/module calls/factory assignment checked separately. __new__ stubs are inert and not constructors. Docs/Evidence are historical non-executable source, excluded. Every discovered successful instance has explicit current-instance or server ownership closure.',
 'constructor_calls':len(inventory),'files':len({item['path'] for item in inventory}),'calls':inventory,
 'production_factory':'BrowserServer._open_merge uses default factory=MergeService. Synchronous __init__ now closes assigned merge on background-start failure. Deferred _load owns self.merge after return; preassignment abort closes local merge, later abort/error/quit/update is closed through server_close/finish_shutdown and serve_owned finally. Merge constructor DecisionRuntime.start remains final operation after aborting progress/enrollment work. Merge.close signals approval stops before joining decisions and closes remaining catalog readers/workers.',
 'open_dispositions':[]}
(target/'constructor-inventory.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
(target/'source.patch').write_text(patch,encoding='utf-8',newline='\n')
evidence=[]
for name in ['owned.mjs','focused.py','freeze-startup.py',*[run+ext for run in ('startup-owner-red','startup-owner-green','startup-owner-cohort') for ext in ('.json','.log')]]:
 data=(root/name).read_bytes();shutil.copyfile(root/name,target/name);evidence.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
summary={'baseline':base,'files':files,'patch_sha256':hashlib.sha256(patch.encode()).hexdigest(),'cause':'BrowserServer synchronous constructor had assigned a real MergeService, then background startup failure closed only HTTP socket. Its new non-daemon durable-decision owner had no returned server owner and remained alive.',
 'fix':'Close assigned merge before socket on constructor exception, clear reference only after successful closure, always close socket in finally. Do not force-exit/daemonize/skip closure. Exception cleanup preserves normal close failure semantics.',
 'proof':'Actual constructor regression RED(owner alive), then3/3construction GREEN1.150s and17/17complete startup/loading+real SQLite writer-contention PASS23.154s; owned23.798s/normalzero/closed/outputComplete. Abort/quit/update/unload/cold-page included. RED fixture explicitly closes its captured private service in finally, not runner force exit.',
 'inventory':{'calls':len(inventory),'files':audit['files'],'sha256':hashlib.sha256((target/'constructor-inventory.json').read_bytes()).hexdigest(),'open_dispositions':[]},'scope':'Private fixtures only; no live/source/Z/focus/full/build/native run. Other dirty four files already represented by committed4941 baseline; no stale overwrite.', 'evidence':evidence}
(target/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'path':str(target),'summary_sha256':hashlib.sha256((target/'summary.json').read_bytes()).hexdigest(),'patch_sha256':summary['patch_sha256'],'inventory':summary['inventory'],'files':files}))
