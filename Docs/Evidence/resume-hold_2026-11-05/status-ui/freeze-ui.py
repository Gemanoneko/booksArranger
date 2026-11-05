import hashlib,json,pathlib,shutil,subprocess
root=pathlib.Path(__file__).parent
source=pathlib.Path('C:/Antigravity Projects/Worktrees/Books Arranger/resume-hold-20261105')
destination=pathlib.Path('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/Docs/Evidence/resume-hold_2026-11-05/status-ui')
destination.mkdir(parents=True,exist_ok=False)
baseline='433885d0b658e8f4096a10e85c12da51e0d4b54e'
paths=['audio_jobs.py','merge_service.py','web/app.js','tests/test_progress_rows.py','tests/test_progress_frontend.js','tests/test_0242_frontend.js','tests/test_ruling35_frontend.js']
files=[]
for name in paths:
 raw=(source/name).read_bytes();old=subprocess.check_output(['git','-C',str(source),'show',baseline+':'+name])
 files.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'lf_sha256':hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest(),'baseline_lf_sha256':hashlib.sha256(old.replace(b'\r\n',b'\n')).hexdigest()})
for name in ('working_lifecycle.py','tests/test_attempt_working_lifecycle.py'):
 assert (source/name).read_bytes().replace(b'\r\n',b'\n')==subprocess.check_output(['git','-C',str(source),'show',baseline+':'+name]).replace(b'\r\n',b'\n'),name
subprocess.run(['git','-C',str(source),'-c','core.whitespace=cr-at-eol','diff',baseline,'--check','--',*paths],check=True)
patch=subprocess.check_output(['git','-C',str(source),'diff',baseline,'--',*paths]);(root/'ui.patch').write_bytes(patch)
names=['owned.mjs','owned-node.mjs','focused.py','freeze-ui.py','ui.patch']
for run in ('queue-phase','queue-phase-corrected','progress-ui','pause-ui','queued-save-ui','queued-save-final','progress-affected'):
 names.extend([run+'.json',run+'.log'])
evidence=[]
for name in names:
 file=root/name;raw=file.read_bytes();shutil.copyfile(file,destination/name);evidence.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
summary={'baseline':baseline,'spec':'11c4043686f5f64f6141153729c29c7828e3fde3:Docs/BooksArranger_QueueStatus_UX_2026-11-05.md','files':files,'patch_sha256':hashlib.sha256(patch).hexdigest(),
 'changes':['Existing jobs status starts with queue state and queue/attention counts; converted/approved retained. Series activity explicitly labelled Metadata. User/update/closing attribution kept; interrupted/unbound pause says exact stopping book is unidentified, never guesses old Brom/Jordan attention row.',
 'Read-only books-audio-queue-work-v1 marker only while a real alive worker has a claimed job but no durable running job. Existing state/control semantics unchanged. Merge excludes marker during actual cleanup/postprocessing. UI says Checking pending audiobook work with no invented conversion progress.',
 'Queued names Save says values wait in session memory, not durably saved. Generic pending-action copy likewise removes false saved claim. Existing queued Cancel positively confirmed preserves editor draft and says not saved. Lost Save reply says not confirmed; durable success alone closes draft with saved receipt.'],
 'results':'26/26 progress_rows+quiet_status Python tests PASS9.938s (owned10.589s normalnativezero), including actual private AudioJobs worker held at preattemptadmission; phase marker true, no current job/phase, disappears after completion. Three existing Node/DOM scripts progress_frontend,0242_frontend,ruling35_frontend PASS normalnativezero. Fixtures cover paused418/65+series0/292+unrelatedBromhold, actualrunningconversion, queuedSaveRAM/ahead/cancel/draftretained/refusal/lostreply/success. Initial newphase fixture had no sources and correctly failed enqueue; fixed fixture supplies required ordered source, no guard changed.',
 'limitations':'Focused source/DOM verification only; no fullcheck/build/release/native/real-window/rect measurement. No live mutation/API/Z/media access. No actual new global pause is attributed to Jordan: core keeps that expected hold local, and old generic pause record has no typed book binding. SourcebadJordanuncapturedfiles and Bromidentityhold remain protected; this change does not repair either book.',
 'unmodified_core':'Two core433885d paths normalized-equal verified; excluded from UI delta. No new framework/options/universe changes.',
 'graph':'Existing test modules/scripts only. Prepared canonical Node phase helper was not executed because parent limited followup to affected source/DOM checks; no release gate claim.',
 'evidence':evidence}
(destination/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'path':str(destination),'summary_sha256':hashlib.sha256((destination/'summary.json').read_bytes()).hexdigest(),'patch_sha256':summary['patch_sha256'],'evidence_files':len(evidence)+1}))
