import hashlib,json,pathlib,shutil,subprocess
root=pathlib.Path(__file__).parent
source=pathlib.Path('C:/Antigravity Projects/Worktrees/Books Arranger/resume-hold-20261105')
destination=pathlib.Path('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger/Docs/Evidence/resume-hold_2026-11-05/core')
destination.mkdir(parents=True,exist_ok=False)
baseline='73926663a2045780509ca7ab1cdc6a2d31f6f449';paths=['working_lifecycle.py','tests/test_attempt_working_lifecycle.py']
files=[]
for name in paths:
 raw=(source/name).read_bytes();old=subprocess.check_output(['git','-C',str(source),'show',baseline+':'+name])
 files.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'lf_sha256':hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest(),'baseline_lf_sha256':hashlib.sha256(old.replace(b'\r\n',b'\n')).hexdigest()})
subprocess.run(['git','-C',str(source),'-c','core.whitespace=cr-at-eol','diff',baseline,'--check','--',*paths],check=True)
patch=subprocess.check_output(['git','-C',str(source),'diff',baseline,'--',*paths]);(root/'core.patch').write_bytes(patch)
evidence=[]
for file in sorted(root.iterdir()):
 if file.is_file():
  raw=file.read_bytes();shutil.copyfile(file,destination/file.name);evidence.append({'path':file.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
summary={'baseline':baseline,'files':files,'patch_sha256':hashlib.sha256(patch).hexdigest(),
 'cause':'Live catalog read-only: Jordan job204b6574 became needs attention07:50:40Z after closed prior attemptc0c01a82 retained uncaptured producer files. WorkingLifecycle.admit final nonretired check raised generic BoundaryError; AudioJobs preattempt generic handler globally stopped and invoked automatic.stop(force=True). Pauses recorded same instant. Prior Brom identity hold is unrelated and remains protected.',
 'fix':'RestagingHeld inherits existing JobWorkingHold and BoundaryError only after retire returns normally and same attempt is durably producerclosed and attention/sources_retained. No new attempt admitted; retained bytes untouched. Unknown thrown ownership/native/IO/catalog errors retain global stop.',
 'results':'NormalResume baseline private uncapturedclosedattempt reproduces3independentjobspending/globalstop. Corrected samefixture completes3independentbooks, preserves heldmanifest/attempt/journal/output/uncapturedbytes andoriginal. Unknownownershipboundary remainsglobalstop.5focusedPASS +31/31WorkingLifecycleTests PASS11.198s (owned11.805s); normalclosed/outputComplete/nativezero, noforce/timeout.',
 'scope':'No live API/app/actions/focus/Zsource access. Live SQLite URI mode=ro+query_only, boundedqueries only; no mediafilesopened. Local failure records preserved; protected incomplete source snapshots not cleared. Injected validated output for independent continuation, no claim of codec regression beyond existing module.',
 'ui':'Separate committed Judy11c4043 truthfulness work pending; this twofile source is frozen for independent integration now.',
 'evidence':evidence}
(destination/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'path':str(destination),'summary_sha256':hashlib.sha256((destination/'summary.json').read_bytes()).hexdigest(),'patch_sha256':summary['patch_sha256'],'evidence_files':len(evidence)+1}))
