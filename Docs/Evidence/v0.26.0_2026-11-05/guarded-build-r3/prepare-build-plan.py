import hashlib,json,pathlib,subprocess
root=pathlib.Path(__file__).parent;release=pathlib.Path('C:/Antigravity Projects/Worktrees/Books Arranger/0260-release-20261105-r3');main=pathlib.Path('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger');studio=main.parents[1]
head='3932155e9f3ceac00632d2d82a4e91315f7c832f'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def pin(path):return {'path':str(path).replace('\\','/'),'bytes':path.stat().st_size,'sha256':digest(path)}
assert subprocess.check_output(['git','-C',str(release),'rev-parse','HEAD'],text=True).strip()==head
assert not subprocess.check_output(['git','-C',str(release),'status','--porcelain'])
pkg=json.loads((release/'package.json').read_text());assert pkg['version']=='0.26.0' and pkg['scripts']['pack']=='node scripts/build-step.mjs pack'
stage=json.loads((root/'stage-owned.json').read_text());assert stage['ok'] and stage['code']==0 and stage['closed'] and stage['outputComplete'] and stage['native']['zero'] and stage['native']['complete']
staged=json.loads(stage['out']);assert staged['verified'] and staged['seed']['files']==2301
names=subprocess.check_output(['git','-C',str(release),'ls-files','-z']).split(b'\0');source_files=[]
for raw in names:
 if raw:
  name=raw.decode('utf-8');source_files.append({'path':name,'sha256':digest(release/name)})
helper=studio/'.claude/skills/qa-handoff/scripts'
paths=[root/'build-operator.mjs',root/'stage-inputs.mjs',root/'stage-owned.json',release/'package.json',release/'package-lock.json',release/'scripts/build-inputs.json',release/'desktop/runtime-pins.json',
 pathlib.Path('C:/Program Files/nodejs/node.exe'),pathlib.Path('C:/Program Files/nodejs/node_modules/npm/bin/npm-cli.js'),pathlib.Path('C:/Program Files/Git/cmd/git.exe'),pathlib.Path('C:/Python314/python.exe'),pathlib.Path('C:/Windows/System32/cmd.exe')]
paths.extend(helper/name for name in ['run_entry_checks.mjs','entry-main.mjs','entry-identity.mjs','bounded-check.mjs','bounded-child.mjs'])
for name in ('empty-user-config.txt','empty-global-config.txt'):
 path=root/name;assert path.is_file() and not path.is_symlink() and path.stat().st_nlink==1 and path.read_bytes()==b'';paths.append(path)
ownership_root=main/'build-cache/qa-ownership/node_modules/koffi';ownership=[]
for path in sorted(ownership_root.rglob('*')):
 assert not path.is_symlink()
 if path.is_file():
  assert path.stat().st_nlink==1;paths.append(path);ownership.append({'path':path.relative_to(ownership_root).as_posix(),'size':path.stat().st_size,'sha256':digest(path)})
ownership.sort(key=lambda item:item['path'])
npm_root=pathlib.Path('C:/Program Files/nodejs/node_modules/npm');npm_tree=[]
for path in sorted(npm_root.rglob('*')):
 assert not path.is_symlink()
 if path.is_file():
  assert path.stat().st_nlink==1;paths.append(path);npm_tree.append({'path':path.relative_to(npm_root).as_posix(),'size':path.stat().st_size,'sha256':digest(path)})
npm_tree.sort(key=lambda item:item['path'])
pins=[pin(path) for path in paths]
plan={'schema':'books-0260-build-execution-v1','source_root':str(release).replace('\\','/'),'source_head':head,'source_dirty':'N','version':'0.26.0','deadline_ms':600000,
 'invocation':['C:/Program Files/nodejs/node.exe',str(root/'build-operator.mjs').replace('\\','/'),'pack','<EXACT_SHA256_OF_THIS_PLAN>'],
 'child_argv':['C:/Program Files/nodejs/node.exe','C:/Program Files/nodejs/node_modules/npm/bin/npm-cli.js','run','pack'],'cwd':str(release).replace('\\','/'),
 'canonical_route':'package pack→scripts/build-step.mjs pack→guarded-io.runNativeOwned(build600000)→pinned C:/Python314 native build lease→existing build_phase. Outer canonical runOwned600000 owns all descendants before release; normal zero/complete/EOF mandatory. No npm run build/release, app install, focus or live media.',
 'staging':{'source':'Existing main graph-identical node_modules and exact declared pack seed; immutable ordinary files copied withwx and complete before/after manifests, everyproductionFiles hash checked; no npm install/lifecycle/network. Source seed retained untouched.', 'dependencies_files':staged['dependencies']['files'],'dependencies_bytes':staged['dependencies']['bytes'],'seed_files':staged['seed']['files'],'seed_bytes':staged['seed']['bytes'],'runtime_archives':staged['archives'],'native_zero':True},
 'boundaries':'Only r1 ignoredbuild-cache/dist/node_modules and ownedtasktemp/profile. Existing guarded leases/protected tree/NSIS private generator/installer-equivalent payload verification remain. No sourcegraph or guard changes. Build may use only existing pinned runtime archive URLs if cache absent; staged archive list proves cached inputs present. Any deadline, ownership, identity or input failure stops without duplicate.',
 'ownership':{'root':str(ownership_root).replace('\\','/'),'files':ownership},'npm_tree':{'root':str(npm_root).replace('\\','/'),'files':npm_tree},'source_files':source_files,'pins':pins}
(root/'build-plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'plan':str(root/'build-plan.json'),'sha256':digest(root/'build-plan.json'),'source_files':len(source_files),'pins':len(pins),'staging':plan['staging'],'operator_sha256':digest(root/'build-operator.mjs')}))
