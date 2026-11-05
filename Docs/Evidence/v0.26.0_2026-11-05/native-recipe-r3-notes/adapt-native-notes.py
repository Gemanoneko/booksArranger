from pathlib import Path
import json,hashlib,difflib,shutil
main=Path('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger')
old=main/'Docs/Evidence/v0.26.0_2026-11-05/native-recipe-r3';new=main/'Docs/Evidence/v0.26.0_2026-11-05/native-recipe-r3-notes'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not new.exists() and not Path('C:/Antigravity Projects/n26').exists()
operator=old/'native-once.mjs';assert sha(operator)=='07577db9f9c22c25a40f7500fa89ed6fd6898267520a18bd34f8e056f1c09336'
before=operator.read_text(encoding='utf-8');needle="line.endsWith('; personal-folders clean')";assert before.count(needle)==1
after=before.replace(needle,r'/; personal-folders clean(?: \((?:1 subfolder note|(?:[2-9]|[1-9]\d+) subfolder notes)\))?$/.test(line)')
new.mkdir();(new/'native-once.mjs').write_text(after,encoding='utf-8',newline='\n')
patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='pin-only-r3/native-once.mjs',tofile='clean-notes-r3/native-once.mjs'))
(new/'operator-diff.patch').write_text(patch,encoding='utf-8',newline='\n')
boundaries={}
for name,next_marker in [('canonical','async function readPlan'),('readPlan','function fullPass'),('prepare','async function run'),('run','async function accept'),('accept','const [mode,expectedSelf')]:
 def body(text):
  start=text.index(('async function '+name+'('));return text[start:text.index(next_marker,start)]
 a=body(before);b=body(after);assert a==b
 boundaries[name]={'before_sha256':hashlib.sha256(a.encode()).hexdigest(),'after_sha256':hashlib.sha256(b.encode()).hexdigest(),'byte_equal':True}
recipe=json.loads((old/'recipe.json').read_text());prior=recipe['operator'];recipe['prior_pin_only_operator']=prior
recipe['operator']={'path':str(new/'native-once.mjs').replace('\\','/'),'sha256':sha(new/'native-once.mjs')}
recipe['status']='OPERATOR PREPARED ONLY; canonical clean-with-notes receipt compatibility is a separately reviewed code change; no real authority/plan/launch'
recipe.pop('literal_adaptation_patch_sha256',None);recipe['receipt_compatibility_patch_sha256']=sha(new/'operator-diff.patch')
recipe['compatibility_reason']='Canonical entry-identity personalFolderVerdict emits clean (N subfolder note[s]) with clean=true; the original custom receipt suffix rejected that legitimate form. Accept only exact clean or canonical positive-note grammar; reject listed/not checked and every other altered result/source/receipt.'
recipe['unchanged_boundaries']=boundaries
for args in recipe['invocation_templates'].values():args[1]=recipe['operator']['path'];args[3]=recipe['operator']['sha256']
(new/'recipe.json').write_text(json.dumps(recipe,indent=2)+'\n',encoding='utf-8')
shutil.copyfile(old/'publisher-readiness.json',new/'publisher-readiness.json');shutil.copyfile(__file__,new/'adapt-native-notes.py')
print(json.dumps({'operator':recipe['operator'],'recipe_sha256':sha(new/'recipe.json'),'patch_sha256':sha(new/'operator-diff.patch'),'unchanged_boundaries':boundaries}))
