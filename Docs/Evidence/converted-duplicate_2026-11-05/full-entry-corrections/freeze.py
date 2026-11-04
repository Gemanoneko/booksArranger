import hashlib,json,pathlib,shutil,subprocess
root=pathlib.Path(__file__).parent
source=pathlib.Path('C:/Antigravity Projects/Worktrees/Books Arranger/converted-duplicate-20261104')
main=pathlib.Path('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger')
destination=main/'Docs/Evidence/converted-duplicate_2026-11-05/full-entry-corrections'
destination.mkdir(parents=True,exist_ok=False)
baseline=json.loads((root/'baseline-files.json').read_text(encoding='utf-8'))
paths=[value['path'] for value in baseline['files']]
patch=subprocess.check_output(['git','-C',str(source),'diff',baseline['baseline'],'--',*paths])
check=subprocess.run(['git','-C',str(source),'-c','core.whitespace=cr-at-eol','diff',baseline['baseline'],'--check','--',*paths],capture_output=True,check=True)
(root/'source.patch').write_bytes(patch)
records=[]
for value in baseline['files']:
    raw=(source/value['path']).read_bytes()
    records.append({'path':value['path'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'lf_sha256':hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest(),'baseline_lf_sha256':value['lf_sha256']})
artifacts=[]
for file in sorted(root.iterdir()):
    if file.is_file() and file.suffix in ('.json','.log','.py','.mjs','.patch'):
        shutil.copyfile(file,destination/file.name)
        raw=file.read_bytes();artifacts.append({'path':file.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
summary={'baseline':baseline['baseline'],'files':records,'patch_sha256':hashlib.sha256(patch).hexdigest(),
 'production_change':'Only web/app.js legacy untyped single-MP3 replace_source status/hint restored. Typed books-media-failure-v1 exact filename/check labels keep precedence and remain unchanged. No SQL/cleanup/ownership/admission guard modified.',
 'classification':[
  {'group':'replacement inspector missing root','cause':'Fixture hand-created book_groups(id,revision,review). Actual groups.setup creates root/evidence/superseded; Inventory._candidate_row queries root. Fixture now uses real groups.setup and explicit complete candidate row.'},
  {'group':'destination navigation/current view','cause':'Explicit Double omitted new _source_directories method; now includes real method and persisted groups.setup row. Current publication input omitted manifest; now supplies actual frozen manifest. Moved/native-bound and renamed-waiting target assertions unchanged.'},
  {'group':'cleanup sweep interruption','cause':'Test injected the old protected_output wrapper, which now delegates to typed protected_cleanup and is not called by run_folders. Inject actual production self.guard; interruption propagates, library bytes unchanged, prior selection retained, no marker recorded, later safe retry completes. Navigation _source_directories is only consumed by inspect/open_folder.'},
  {'group':'shared peers and names save','cause':'Minimal __new__ fixtures omitted ReviewBackend.page_local and three admission RLocks. Fixtures now reproduce exact constructor state, no optional/getattr/noop product fallback. All stale/CAS/rollback assertions remain.'},
  {'group':'legacy frontend','cause':'Untyped existing proven single-MP3 replacement remedy accidentally adopted generic new status. Restore established status and full-check replacement hint; typed multi-track/newM4B labels unaffected.'},
  {'group':'five Tolkien old expectations','cause':'Assigned independently to media Ender by Jane. Not edited or included in this delta.'}],
 'results':{'baseline':'e691 full failure exact indexed evidence retained separately; owned focused baseline reproduced all own Python categories:10 methods,2failures+10errors including subcases,normal nativezero2.747s.',
 'corrected':'Same10methods PASS nativezero3.005s; all affected modules + actual Inventory concurrency suite172/172 PASS46.636s (owned47.546s).',
 'frontend':'Iron/Skazka,attention,refused_retry,retry scripts all PASS in separately owned bounded calls.',
 'guards':'No sourceZ/app/live writes/focus/Explorer. Real dispatch is mocked; actual catalog and native private files used. timeout600000 unchanged. No full/hidden gate repeated.'},
 'lock_proof':{'MergeService.operation_lock':'threading.RLock at merge_service.py214','CandidateReviewService.lock':'threading.RLock at review_backend.py111','Inventory.group_lock':'threading.RLock at scanner.py139','trilogy':'_trilogy_stale called by _plan_stale, does not call names_save. Existing full integration names-save pending replan/CAS/rollback and real HTTP busy/retry tests passed.'},
 'commands':[
 'node owned.mjs full-failures-baseline test_replacement_jobs.ReplacementTests.test_verified_current_inspector_tags_cover_and_folder_target_agree test_destination_override.ChooseTests.test_a_renamed_book_waiting_for_a_restart_stays_finished_and_opens_its_new_folder_D1r3 test_destination_override.ChooseTests.test_moved_book_resolves_for_delete_book_and_the_current_audiobook_view test_source_folders.SourceFolderTests.test_interrupted_sweep_retains_its_selection_and_retries test_backend_242.SharedPeerConsumerTests test_integration_242.IntegrationTests.test_name_save_replans_exact_pending_job_with_truthful_hold_and_new_names',
 'node owned.mjs full-failures-corrected [same explicit selectors]',
 'node owned.mjs full-affected-modules test_replacement_jobs test_destination_override test_source_folders test_backend_242 test_integration_242 test_lock_timing.SourceFolderDispatchTests',
 'node owned-node.mjs <unique-result-name> tests/test_<iron_skazka|attention|refused_retry|retry>_frontend.js'],
 'graph':'Existing test modules/scripts only; no new discovery helper, selector, weight, build input or workflow change.',
 'evidence':artifacts}
(destination/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'evidence':str(destination),'files':paths,'summary_sha256':hashlib.sha256((destination/'summary.json').read_bytes()).hexdigest(),'patch_sha256':summary['patch_sha256'],'evidence_files':len(artifacts)+1}))
