from pathlib import Path
import hashlib,json,os,subprocess
root=Path(__file__).parent;release=Path('C:/Antigravity Projects/Worktrees/Books Arranger/0260-release-20261105-r3')
main=Path('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger');studio=main.parents[1]
head='1b2f81a8f6d86995e937332e0c225837d05cbc20';git='C:/Program Files/Git/cmd/git.exe'
def sh(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def pin(path):
 s=path.lstat();assert path.is_file() and not path.is_symlink() and not path.is_junction();return {'path':str(path).replace('\\','/'),'size':s.st_size,'sha256':sh(path)}
def tree(path):
 assert path.is_dir() and not path.is_symlink() and not path.is_junction();rows=[]
 for f in path.rglob('*'):
  assert not f.is_symlink() and not f.is_junction()
  if f.is_file():rows.append({'path':f.relative_to(path).as_posix(),'size':f.stat().st_size,'sha256':sh(f)})
 return {'root':str(path).replace('\\','/'),'files':sorted(rows,key=lambda x:x['path'])}
def gitread(*args):return subprocess.check_output([git,'-c','core.fsmonitor=false','-C',str(release),*args],timeout=30)
assert not (root/'plan.json').exists() and not (root/'launch-started.json').exists()
assert gitread('rev-parse','HEAD').decode().strip()==head and not gitread('status','--porcelain','--untracked-files=normal')
pkg=json.loads((release/'package.json').read_text());lock=json.loads((release/'package-lock.json').read_text())
assert pkg['version']==lock['version']=='0.26.0' and pkg['scripts']['release']=='node scripts/release.mjs'
assert 'prerelease' not in pkg['scripts'] and 'postrelease' not in pkg['scripts'] and not pkg.get('workspaces') and not (release/'.npmrc').exists()
assert sh(release/'package-lock.json')=='4793ceb09472d3381afc1acec949e4f9506cb31b311cbab4babdcceabafadd18'
code=(release/'scripts/release.mjs').read_text();assert "runNativeOwned({mode:'release',root,script:'scripts/release.mjs'})" in code and "throw new Error('No accepted candidate." in code
manifest=release/'dist/release-artifacts.json';m=json.loads(manifest.read_text())
assert sh(manifest)=='8d170ee68ad1e5cccca5be024cf23aaa0893c4b12b4c8ebdfb1dbd9a4086574f' and m['version']=='0.26.0' and m['product_digest']=='6e9a3f3a785eb5fe243f032d6ccc30b9352518ef1efba1739aba57501a17b5c3' and m['payload']['verified'] and m['payload']['installer_equivalent']
gitread('merge-base','--is-ancestor',m['source_head'],head)
for leaf in ['temp','npm-cache']:(root/leaf).mkdir(exist_ok=False)
for name in ['empty-user-config.txt','empty-global-config.txt']:(root/name).write_bytes(b'')
paths=[root/'publish-owned.mjs',root/'prepare-plan.py',root/'empty-user-config.txt',root/'empty-global-config.txt',manifest,release/'build-cache/runtime-pointer.json',Path('C:/Windows/System32/cmd.exe'),Path('C:/Python314/python.exe')]
for name in ['kernel32.dll','advapi32.dll','ntdll.dll','user32.dll','iphlpapi.dll']:paths.append(Path('C:/Windows/System32')/name)
helper=studio/'.claude/skills/qa-handoff/scripts'
for name in ['run_entry_checks.mjs','entry-main.mjs','entry-identity.mjs','bounded-check.mjs','bounded-child.mjs']:paths.append(helper/name)
accepted_names=['Docs/BooksArranger_ReleaseAcceptance_v0.26.0.json','Docs/BooksArranger_QA_v0.26.0_2026-11-05.md','Docs/BooksArranger_CodeReview_v0.26.0_2026-11-05.md','Docs/BooksArranger_NativeQA_v0.26.0.json']
for name in accepted_names:paths.append(release/name)
native=json.loads((release/accepted_names[-1]).read_text());assert sh(release/accepted_names[-1])=='ce4989c46fb193272f98cf0f0797d59a1a4e6ea8dd8dbb4c3a552670e67f8fff'
for ref in native['records'].values():
 f=release/ref['path'];assert f.stat().st_size==ref['size'] and sh(f)==ref['sha256'];paths.append(f)
artifacts=[]
for ref in m['artifacts']:
 f=release/'dist'/ref['path'];assert f.stat().st_size==ref['size'] and sh(f)==ref['sha256'];paths.append(f);artifacts.append(pin(f))
payload=release/'dist'/m['unpacked']
for name,ref in m['payload']['files'].items():
 f=payload/name;assert f.stat().st_size==ref['size'] and sh(f)==ref['sha256'];paths.append(f)
roots=[release/'node_modules',release/'build-cache/pack-inputs',Path('C:/Program Files/nodejs'),Path('C:/Program Files/Git'),Path('C:/Program Files/GitHub CLI'),main/'build-cache/qa-ownership']
runtime_trees=[tree(p) for p in roots]
source_files=[{'path':n.decode(),'sha256':sh(release/n.decode())} for n in gitread('ls-files','-z').split(b'\0') if n]
r=str(root).replace('\\','/')
env={'SystemRoot':'C:/Windows','WINDIR':'C:/Windows','ComSpec':'C:/Windows/System32/cmd.exe','PATH':'C:/Program Files/nodejs;C:/Program Files/Git/cmd;C:/Program Files/GitHub CLI;C:/Windows/System32','TEMP':r+'/temp','TMP':r+'/temp','USERPROFILE':os.environ['USERPROFILE'],'HOME':os.environ.get('HOME') or os.environ['USERPROFILE'],'APPDATA':os.environ['APPDATA'],'LOCALAPPDATA':os.environ['LOCALAPPDATA'],'NODE_OPTIONS':'','NODE_PATH':'','PYTHONHOME':'','PYTHONPATH':'','GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'0','GH_PROMPT_DISABLED':'1','npm_config_userconfig':r+'/empty-user-config.txt','npm_config_globalconfig':r+'/empty-global-config.txt','npm_config_cache':r+'/npm-cache','npm_config_audit':'false','npm_config_fund':'false','npm_config_update_notifier':'false'}
plan={'schema':'books-0260-publisher-plan-v1','source_head':head,'source_root':str(release).replace('\\','/'),'source_dirty':'N','version':'0.26.0','deadlineMs':600000,'tag':'v0.26.0','binding':native['binding'],'manifest_sha256':sh(manifest),'runtime_pointer_sha256':sh(release/'build-cache/runtime-pointer.json'),'artifacts':artifacts,'accepted_inputs':[pin(release/n) for n in accepted_names],'native_roles':12,'helper':str(helper/'bounded-check.mjs').replace('\\','/'),'koffi_root':str(main/'build-cache/qa-ownership/node_modules/koffi').replace('\\','/'),'environment':env,'credential_policy':'No credential values/files copied, inspected or pinned. Preserve real user config root paths solely so unchanged canonical native release gh auth token --hostname github.com reads existing CLI credentials inside its lease. Token environment overrides absent. No prompts/focus: GIT_TERMINAL_PROMPT=0/GCM_INTERACTIVE=0/GH_PROMPT_DISABLED=1.','credential_policy_sources':['Installed gh help environment','https://raw.githubusercontent.com/git-ecosystem/git-credential-manager/main/docs/environment.md#GCM_INTERACTIVE'],'sealed_call_graph':{'npm_command':['C:/Program Files/nodejs/node.exe','C:/Program Files/nodejs/node_modules/npm/bin/npm-cli.js','run','release'],'release_script':pkg['scripts']['release'],'prerelease_absent':True,'postrelease_absent':True,'workspaces_absent':True,'root_npmrc_absent':True,'path':'npm run release -> scripts/release.mjs -> runNativeOwned mode release600000 -> releaseFlow -> accepted artifact-only electron-builder publish -> remote digest/tag verification -> keep4. No pack/build/full check/native PA1 rerun. io.prepare always throws if accepted candidate missing.'},'runtime_trees':runtime_trees,'source_files':source_files,'pins':[pin(p) for p in dict.fromkeys(paths)],'execution_owner':'Sully only; after Senua exact plan/operator clearance and named local/remote tag pinned to this HEAD. Ender prepares only.','stop_policy':'One-use marker before actual publisher; no automatic retry after failure, timeout, drift or uncertain remote state. Preserve owner result/log even if postflight rejects. Do not cleanup inputs until all3remote digests and keep4 verify.'}
assert gitread('rev-parse','HEAD').decode().strip()==head and not gitread('status','--porcelain','--untracked-files=normal')
(root/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'plan':r+'/plan.json','plan_sha256':sh(root/'plan.json'),'operator':r+'/publish-owned.mjs','operator_sha256':sh(root/'publish-owned.mjs'),'source_files':len(source_files),'pins':len(plan['pins']),'trees':[{'root':t['root'],'files':len(t['files'])} for t in runtime_trees],'actual_argv':['C:/Program Files/nodejs/node.exe',r+'/publish-owned.mjs',sh(root/'plan.json')]}))
