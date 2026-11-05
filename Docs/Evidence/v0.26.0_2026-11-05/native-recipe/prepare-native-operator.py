import hashlib, json, pathlib, re, difflib
main=pathlib.Path('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger')
release=pathlib.Path('C:/Antigravity Projects/Worktrees/Books Arranger/0260-release-20261105-r1')
context=pathlib.Path('C:/Antigravity Projects/q26/context')
target=main/'Docs/Evidence/v0.26.0_2026-11-05/native-recipe'
canonical=main/'Docs/Evidence/converted-duplicate_2026-11-04/native-recipe-0250/native-once.mjs'
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
assert not pathlib.Path('C:/Antigravity Projects/n26').exists(), 'Fresh native arena must remain absent before full PASS'
assert not target.exists(), 'Fresh recipe evidence required'
m=read(release/'dist/release-artifacts.json'); c=read(context/'context.json')
assert m['version']=='0.26.0' and c['source']['head']==m['source_head'] and c['source']['dirty']=='N'
binding={'version':m['version'],'source_head':m['source_head'],'product_digest':m['product_digest'],'build_id':m['build_id'],'artifact_manifest_sha256':digest(release/'dist/release-artifacts.json'),'runtime_manifest_sha256':hashlib.sha256(json.dumps(m['runtime'],separators=(',',':'),ensure_ascii=False).encode()).hexdigest(),'phase_contract_sha256':digest(context/'source/scripts/qa-phase-contract.mjs')}
original=canonical.read_text(encoding='utf-8'); text=original
def replace(old,new):
 global text
 assert old in text, old
 text=text.replace(old,new)
replace('0.25.0','0.26.0')
replace("const BASE='C:/Antigravity Projects/n25';","const BASE='C:/Antigravity Projects/n26';")
replace('C:/Antigravity Projects/q4/','C:/Antigravity Projects/q26/')
replace('C:/Antigravity Projects/Worktrees/Books Arranger/0250-release-20261105-r3',str(release).replace('\\','/'))
text,n=re.subn(r'const BINDING=\{[^\n]+\};', 'const BINDING='+json.dumps(binding,separators=(',',':'))+';',text);assert n==1
code_names=['scripts/qa-phase-contract.mjs','scripts/qa-real-shell-phase.mjs','tests/real-shell-update-support.mjs','tests/real-shell-update.test.mjs']
code={name:digest(context/'source'/name) for name in code_names}
text,n=re.subn(r'const CODE=\{[\s\S]+?\n\};','const CODE='+json.dumps(code,indent=1)+';',text,count=1);assert n==1
text,n=re.subn(r"const EXPECTED_CONTEXT='[a-f0-9]{64}';","const EXPECTED_CONTEXT='"+digest(context/'context.json')+"';",text);assert n==1
replace('da4cfa5c4684ed71706c48536962ba3419c07fac3b8c4281831d59fd4e2fab10',digest(release/'build-cache/runtime-pointer.json'))
helper=pathlib.Path('C:/Antigravity Projects/Studio Illuminati/.claude/skills/qa-handoff/scripts')
for old,p in [('89ecbd30698cae696ba52d677f31bfaa505c87227c22f85e0bb6a2103475fcbc',helper/'bounded-check.mjs'),('240a6a96a32f08989439387d5d6ab75d17e1bcf243863d31d2ff7287f68d1e42',helper/'bounded-child.mjs'),('14319838b3f355e0398c13569a90270bce4fc68f25189f58c59b03dadae0e6d5',pathlib.Path('C:/Program Files/nodejs/node.exe'))]:replace(old,digest(p))
manifests={p['name']:p for p in c['runtime']['manifests']}
replace('9baa25ddc8f3d43d5f7ac8f765f52e6525b12904706f3c94cf7e7bf2b09395ca',manifests['node-installation']['manifest']['sha256'])
replace('122eca8f1ad057bd86867f8e302c60fcaa5b6dba5ff4e660cfd860cf40769617',manifests['ownership']['manifest']['sha256'])
authority={'schema':'books-native-qa-authority-v1','binding':None,'approved_by':'Sergei','decision_ref':'Current user message in this release chat, client date 2026-11-05; exact message sent time unavailable','decision_text':'Current user message, quoted verbatim: "Add the four Universe options too, then have Sully release the next version with all these fixes. Don\'t stop until it\'s released unless there\'s a serious stopper." Jane and Senua interpret the existing canonical private PA-1 as necessary release workflow within that request: one hidden private copied app, invalid fake installer refusal, deletion of the exact newly created own HKCU tray numeric leaf, and ONE added 8-byte numeric history reference while preserving every preexisting UIOrderList byte. These enumerated registry effects are producer/reviewer scope interpretation, not words attributed to Sergei. No focus, installed app changes, live library or Z: access. No old 0.25 authority or proof is reused. approved_at records actual new preparation UTC, not the unavailable user-message sent time.','approved_at':None,'effects':{'hidden_private_app':True,'invalid_installer_attempt':True,'own_new_leaf_delete':True,'leave_numeric_history_reference':True,'ui_order_list_write':False}}
authority_line=' const authority='+json.dumps(authority,separators=(',',':')).replace('"binding":null','"binding":BINDING').replace('"approved_at":null','"approved_at":new Date().toISOString()')+';'
text,n=re.subn(r'^ const authority=\{[^\n]+;$',lambda _:authority_line,text,flags=re.M);assert n==1
target.mkdir()
operator=target/'native-once.mjs'; operator.write_text(text,encoding='utf-8',newline='\n')
patch=''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='canonical-0.25-native-once.mjs',tofile='fresh-0.26-native-once.mjs'))
(target/'pin-only.patch').write_text(patch,encoding='utf-8',newline='\n')
recipe={'schema':'books-0260-native-recipe-v1','status':'OPERATOR PREPARED ONLY; no native arena, authority, plan, launch or PASS receipt created','binding':binding,'canonical':{'path':str(canonical).replace('\\','/'),'sha256':digest(canonical)},'operator':{'path':str(operator).replace('\\','/'),'sha256':digest(operator)},'literal_adaptation_patch_sha256':digest(target/'pin-only.patch'),'context':{'path':str(context/'context.json').replace('\\','/'),'sha256':digest(context/'context.json')},'runtime_pointer_sha256':digest(release/'build-cache/runtime-pointer.json'),'code':code,'native_arena':'C:/Antigravity Projects/n26','ownership_root':'C:/Antigravity Projects/q26/ownership','release_root':str(release).replace('\\','/'),'deadline_ms':600000,'authority_template':authority,'preconditions':['One original exact current full PASS receipt; no Ender full repeat','Senua reviews actual operator and fresh pure-prepared authority/plan before single launch','n26 must be absent and is created exclusively by prepare; no adoption or recovery bypass'],'invocation_templates':{'prepare':['C:/Program Files/nodejs/node.exe',str(operator).replace('\\','/'),'prepare',digest(operator),'<EXACT_ORIGINAL_FULL_RECEIPT_PATH>','<EXACT_ORIGINAL_FULL_RECEIPT_SHA256>'],'run':['C:/Program Files/nodejs/node.exe',str(operator).replace('\\','/'),'run',digest(operator),'<EXACT_REVIEWED_PLAN_SHA256>'],'accept':['C:/Program Files/nodejs/node.exe',str(operator).replace('\\','/'),'accept',digest(operator),'<EXACT_REVIEWED_PLAN_SHA256>']}}
(target/'recipe.json').write_text(json.dumps(recipe,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'operator':recipe['operator'],'recipe_sha256':digest(target/'recipe.json'),'patch_sha256':recipe['literal_adaptation_patch_sha256'],'binding':binding}))
