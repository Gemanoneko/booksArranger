"""Prepare one immutable Books protocol-2 input set; never run its checks.

CANDIDATE v2: requires independent review, approved execution route and final
source/runtime pins. This module does not deploy a hook or grant QA admission.

Reviewed operation: python -I -B <this file> --plan-sha <SHA256> --plan-json
<exact reviewed books-entry-assembly-plan-v2 JSON>. The plan supplies
source_head, bootstrap hashes (this file/native_io.py/build_fs_guard.py), five
checker hashes, executable {path,sha256} refs and complete runtime-tree digests.
No path is inferred from TEMP/PATH and no dependency is installed. Existing
output bases refuse. Failure preserves partial new evidence; there is no cleanup.

The installed Python and initially imported stdlib are trusted bootstrap inputs,
as in build_native.py. Local guard modules execute only verified source bytes, then
retained under native read leases. Independent entry validation later rechecks
the committed Git identity, full manifests, runtime and checker; assembly is
not a check receipt or release acceptance. The reviewed outer guardian must own
this entire invocation before launch; the inner Git Job is an additional owner,
not protection for the interval between child creation and inner assignment.
"""
import argparse
import ast
import contextlib
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import threading
import time
import types

ROOT = Path(__file__).absolute().parents[1]
STUDIO = Path('C:/Antigravity Projects/Studio Illuminati')
CONTEXT_BASE = Path('C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/qa-entry-context')
RUN_BASE = Path('C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/q')
GIT_RUNTIME = Path('C:/Users/AnGeLZzZ/AppData/Local/Temp/codex-books-2026-10-20/shared/git-ro-v1')
CHECKER = STUDIO / '.claude/skills/qa-handoff/scripts'
CORE = ['run_entry_checks.mjs', 'entry-main.mjs', 'entry-identity.mjs', 'bounded-check.mjs', 'bounded-child.mjs']
BOOTSTRAP = ['scripts/qa-context-assembly-v2.py', 'scripts/build_fs_guard.py', 'native_io.py']
CHECK_NAMES = ('pre-qa', 'post-build', 'check-electron', 'check', 'test:smoke')
RUNTIME_NAMES = {'dependencies', 'ownership-js', 'ownership-native', 'node-installation', 'system-python', 'bundled-media', 'git-installation'}

def packed(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()

def sha(value):
    return hashlib.sha256(value).hexdigest()

def ref_ok(value):
    return isinstance(value, dict) and isinstance(value.get('path'), str) and bool(re.fullmatch('[a-f0-9]{64}', value.get('sha256', '')))

def declared_graph(source, source_files, root, run_base, held_read):
    """Derive declarations from pinned source bytes; never import/run product code."""
    import fnmatch
    records={item['path']:item for item in source_files}
    def read(relative):
        if relative not in records:raise ValueError('Graph member missing from complete source snapshot: '+relative)
        return held_read(source,root/relative,records[relative]['sha256']).decode('utf-8-sig')
    package=json.loads(read('package.json'))
    scripts=package.get('scripts',{})
    if not isinstance(scripts,dict):raise ValueError('Malformed package scripts')
    if package.get('workspaces') is not None:raise ValueError('Unreviewed workspaces')
    routes={}; lifecycle=[]
    def route(name,stack=()):
        if name in stack:raise ValueError('Declared script cycle')
        command=scripts.get(name)
        if not isinstance(command,str) or not command.strip():raise ValueError('Malformed declared script')
        for prefix in ('pre','post'):
            child=prefix+name
            if child in scripts:
                lifecycle.append({'from':name,'to':child,'kind':prefix})
                route(child,(*stack,name))
        for segment in command.split('&&'):
            segment=segment.strip()
            alias=re.fullmatch(r'npm run ([a-zA-Z0-9:_-]+)',segment)
            if alias:
                lifecycle.append({'from':name,'to':alias[1],'kind':'alias'});route(alias[1],(*stack,name));continue
            match=re.fullmatch(r'node ([a-zA-Z0-9_./-]+)(?: ((?:--[a-zA-Z0-9=._-]+(?: |$))*))?',segment)
            if not match:raise ValueError('Unreviewed package route: '+segment)
            relative=match[1]
            # This preparer only supports the reviewed pure-node Books desktop graph.
            if relative!='scripts/check-desktop.mjs':raise ValueError('New node route requires separate review: '+relative)
            read(relative)
            prior=routes.get(relative)
            value={'path':relative,'sha256':records[relative]['sha256'],'kind':'pure-node','command':segment}
            if prior and prior!=value:raise ValueError('Ambiguous audited node command')
            routes[relative]=value
    declared={}
    for name in CHECK_NAMES:
        if name in scripts:route(name);declared[name]=scripts[name]
    if not routes:raise ValueError('No declared automated route')
    code=read('scripts/check-desktop.mjs')
    def literals(expression):
        value=ast.literal_eval(expression)
        if not isinstance(value,list) or not value or any(not isinstance(item,str) or not item for item in value):
            raise ValueError('Unsafe graph array')
        return value
    initial=re.search(r'const patterns\s*=\s*(\[[^;]+\]);',code)
    if not initial:raise ValueError('Python discovery declaration missing')
    patterns=literals(initial[1])
    for match in re.finditer(r'patterns\.push\(([^;]+)\);',code):patterns.extend(literals('['+match[1]+']'))
    if len(set(patterns))!=len(patterns):raise ValueError('Duplicate Python discovery pattern')
    syntax=re.search(r"for\(const name of (\[[^;]+?\])\)run\(process\.execPath,\['--check',name\]\)",code)
    node=re.search(r'const nodeOutput=run\(process\.execPath,(\[[^;]+?\])\);',code)
    if not syntax or not node:raise ValueError('Unrecognized syntax/node route declaration')
    syntax_files=literals(syntax[1]);node_args=literals(node[1])
    if node_args[:2]!=['--test','--test-reporter=tap']:raise ValueError('Unreviewed Node test mode')
    node_files=node_args[2:]
    if not node_files or any(not name.startswith('tests/') or not name.endswith('.test.mjs') for name in node_files):
        raise ValueError('Unsafe Node test route')
    frontend=sorted(name for name in records if re.fullmatch(r'tests/test_.*\.js',name))
    # The source hash binds the literal no-GUI frontend enumeration implementation.
    if "/^test_.*\\.js$/" not in code or "run(process.execPath,[path.join('tests',name)])" not in code:
        raise ValueError('Unrecognized frontend route declaration')
    python_files=[]
    for pattern in patterns:
        found=sorted(name for name in records if name.startswith('tests/') and '/' not in name[6:] and fnmatch.fnmatchcase(name[6:],pattern))
        if not found:raise ValueError('Declared Python pattern has no source: '+pattern)
        python_files.extend(found)
    if len(set(python_files))!=len(python_files):raise ValueError('Overlapping Python discovery')
    python_ids=[]
    for relative in python_files:
        tree=ast.parse(read(relative),filename=relative)
        python_ids.extend(relative[6:-3]+'.'+cls.name+'.'+method.name for cls in tree.body if isinstance(cls,ast.ClassDef)
                          for method in cls.body if isinstance(method,(ast.FunctionDef,ast.AsyncFunctionDef)) and method.name.startswith('test'))
    sources=[]
    for relative in sorted(set(syntax_files+node_files+frontend+python_files)):
        read(relative);sources.append({'path':relative,'sha256':records[relative]['sha256']})
    fixture_match=re.search(r'const fixtureRootMap\s*=\s*(\{[^;]+\});',code)
    if not fixture_match:raise ValueError('Compact fixture-root contract is absent')
    fixture_map=json.loads(fixture_match[1])
    expected={name+'.AREA':'scratch/a' for name in ('test_automatic_processing','test_local_identity','test_local_identity_fixes','test_split_books')}
    if fixture_map!=expected:raise ValueError('Compact fixture-root map differs from the reviewed four-module contract')
    if 'BOOKS_QA_FIXTURE_ROOT' not in code:raise ValueError('Private additional-fixture environment contract absent')
    # Record transitive local imports and native/subprocess sites statically. They
    # remain independently reviewed source, not a claim every branch executes.
    python_records={name[:-3].replace('/','.') if name.startswith('tests/') else name[:-3]:name
                    for name in records if name.endswith('.py')}
    modules={name[6:-3]:name for name in records if name.startswith('tests/') and name.endswith('.py')}
    modules.update({name[:-3]:name for name in records if '/' not in name and name.endswith('.py')})
    pending=list(python_files);visited=set();imports=[];spawns=[]
    while pending:
        relative=pending.pop()
        if relative in visited:continue
        visited.add(relative);text=read(relative);tree=ast.parse(text,filename=relative)
        for item in ast.walk(tree):
            names=[alias.name.split('.')[0] for alias in item.names] if isinstance(item,ast.Import) else [item.module.split('.')[0]] if isinstance(item,ast.ImportFrom) and item.module else []
            for name in names:
                if name in modules:
                    imports.append({'from':relative,'to':modules[name],'line':item.lineno});pending.append(modules[name])
            if isinstance(item,ast.Call):
                called=ast.unparse(item.func)
                if any(token in called for token in ('Popen','subprocess.run','subprocess.call','check_output','check_call','OwnedProcessJob','OwnedProducer','CreateProcess','start_backend')):
                    spawns.append({'source':relative,'line':item.lineno,'call':ast.get_source_segment(text,item),'classification':'review-required-native-fixture-site'})
    identifier='00000000-0000-0000-0000-000000000000';future=run_base/'entry-run-XXXXXX'
    examples=[future/'scratch/a/tmpXXXXXXXX/cache/audio-staging'/identifier/identifier/('0'*32+'.decode-stderr'),
              run_base/'build-guard-probes'/identifier/'build-cache/builds'/identifier/'metadata-rotation-complete.json']
    if max(map(lambda value:len(str(value)),examples))>259:raise ValueError('Compact ordinary fixture path still too long')
    graph={'schema':'books-entry-graph-v2','kind':'source-declarations-not-executed','declared_scripts':declared,
           'lifecycle_and_alias_edges':lifecycle,'audited_nodes':list(routes.values()),'python_patterns':patterns,
           'python_files':python_files,'python_declared_ids':sorted(python_ids),'python_import_edges':imports,
           'native_fixture_sites':spawns,'node_test_argv':node_args,'syntax_files':syntax_files,'frontend_scripts':frontend,
           'child_source_pins':sources,'fixture_root_map':fixture_map,'fixture_environment':'BOOKS_QA_FIXTURE_ROOT',
           'private_temp':'scratch/entry-temp','sibling_output':'build-guard-probes','required_free_ports':[5212],
           'path_examples':[{'path':str(value),'chars':len(str(value))} for value in examples],
           'limits':'Static source audit only. Actual discovery, native branches and packaged equivalence require independent review and execution.'}
    return graph,list(routes.values())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan-sha', required=True)
    parser.add_argument('--plan-json', required=True)
    args = parser.parse_args()
    if os.name != 'nt' or not re.fullmatch('[a-f0-9]{64}', args.plan_sha):
        raise ValueError('Windows and an exact reviewed plan digest are required')
    deadline = time.monotonic() + 600
    def expired():
        os.write(2, b'Assembly refused: total600000ms elapsed\n')
        os._exit(2)  # Native Job handles close; no new grace period or duplicate run.
    timer = threading.Timer(600, expired)
    timer.daemon = True
    timer.start()
    def remaining():
        value = deadline - time.monotonic()
        if value <= 0:
            raise TimeoutError('Assembly total deadline exceeded')
        return value
    try:
        raw = args.plan_json.encode('utf-8')
        if len(raw) > 2 * 1024 * 1024 or sha(raw) != args.plan_sha:
            raise ValueError('Reviewed assembly plan differs')
        plan = json.loads(raw)
        if plan.get('schema') != 'books-entry-assembly-plan-v2' or not re.fullmatch('[a-f0-9]{40}', plan.get('source_head', '')):
            raise ValueError('Unsupported assembly plan')
        if set(plan.get('bootstrap', {})) != set(BOOTSTRAP) or set(plan.get('checker', {})) != set(CORE):
            raise ValueError('Incomplete local checker/bootstrap pins')
        bootstrap_bytes = {}
        for relative in BOOTSTRAP:
            bootstrap_bytes[relative] = (ROOT / relative).read_bytes()
            if sha(bootstrap_bytes[relative]) != plan['bootstrap'][relative]:
                raise ValueError('Bootstrap source changed: ' + relative)
        # Source-only module construction bypasses both __pycache__ and extension
        # shadowing. The native guard imports only this exact registered native_io.
        for name, relative in [('native_io', 'native_io.py'), ('build_fs_guard', 'scripts/build_fs_guard.py')]:
            module = types.ModuleType(name)
            module.__file__ = str(ROOT / relative)
            sys.modules[name] = module
            exec(compile(bootstrap_bytes[relative], module.__file__, 'exec'), module.__dict__)
        from build_fs_guard import BuildTree, no_named_streams, _native_receipt
        from native_io import FileInfo, OwnedProcessJob, kernel
        def held_read(tree, path, expected=None):
            remaining()
            facts = tree.protect(path)
            no_named_streams(path)
            if expected is not None and facts['sha256'] != expected:
                raise ValueError('Reviewed input changed: ' + str(path))
            return b''.join(tree.files[str(tree.child(path)).casefold()].chunks())
        def full_map(tree, root):
            # Complete native inventory, no symlink/reparse/hardlink traversal.
            result = []
            def visit(folder):
                tree.directory(folder)
                for item in sorted(os.scandir(folder), key=lambda entry: entry.name):
                    remaining()
                    info = item.stat(follow_symlinks=False)
                    if info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                        raise ValueError('Runtime reparse entry refused: ' + item.path)
                    file = Path(item.path)
                    if item.is_dir(follow_symlinks=False):
                        visit(file)
                    elif item.is_file(follow_symlinks=False):
                        data = held_read(tree, file)
                        result.append({'path': file.relative_to(root).as_posix(), 'sha256': sha(data), 'size': len(data)})
                    else:
                        raise ValueError('Special runtime entry refused')
            visit(root)
            return sorted(result, key=lambda item: item['path'])
        def directory_receipt(tree, path):
            directory = tree.directory(path)
            info = FileInfo()
            handle = tree.directories[str(directory).casefold()].handles[-1]
            if not kernel.GetFileInformationByHandle(handle, ctypes.byref(info)):
                raise ValueError('Owned directory identity unavailable')
            return {'path': str(directory), 'identity': [info.volume, info.index_high, info.index_low], 'attributes': info.attributes}
        with contextlib.ExitStack() as stack:
            source = stack.enter_context(BuildTree(ROOT))
            for relative in BOOTSTRAP:
                held_read(source, ROOT / relative, plan['bootstrap'][relative])
            executables = plan.get('executables', {})
            if set(executables) != {'node', 'npmCli', 'shell', 'npmShim', 'git', 'systemPython'} or not all(ref_ok(item) for item in executables.values()):
                raise ValueError('Incomplete executable pins')
            for item in executables.values():
                file = Path(item['path'])
                lease = stack.enter_context(BuildTree(file.parent))
                held_read(lease, file, item['sha256'])
            if Path(executables['git']['path']) != GIT_RUNTIME / 'git.exe':
                raise ValueError('Only the separately reviewed private ordinary Git copy may be used')
            if Path(executables['systemPython']['path']) != Path(sys.executable):
                raise ValueError('Wrong active bootstrap Python')
            def git(*args):
                # Fixed read-only Git identity commands, suspended before release
                # into an existing native kill-on-close owner. No user hooks/PATH.
                env = {key: value for key, value in os.environ.items() if not key.upper().startswith('GIT_')}
                env.update(GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')
                argv = [executables['git']['path'], '--no-pager', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=NUL', '-c', 'protocol.allow=never', '-C', str(ROOT), *args]
                process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, creationflags=0x08000004)
                process._books_suspended = True
                try:
                    with OwnedProcessJob(process) as owner:
                        out, err = process.communicate(timeout=min(10, remaining()))
                        info = ctypes.create_string_buffer(48)
                        kernel.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]
                        kernel.QueryInformationJobObject.restype = wintypes.BOOL
                        if not kernel.QueryInformationJobObject(owner.handle, 1, info, 48, None) or int.from_bytes(info.raw[40:44], 'little'):
                            raise ValueError('Read-only Git descendants did not complete naturally')
                        if process.returncode != 0 or len(out) + len(err) > 4 * 1024 * 1024:
                            raise ValueError('Read-only Git identity lookup failed or overflowed')
                finally:
                    # Ownership setup can fail while the exact child is still
                    # suspended. Dispose only its retained Popen HANDLE; no PID lookup.
                    if process.poll() is None:
                        kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
                        kernel.TerminateProcess.restype = wintypes.BOOL
                        if not kernel.TerminateProcess(wintypes.HANDLE(int(process._handle)), 1):
                            raise ValueError('Exact suspended Git child could not be closed')
                        process.wait(timeout=remaining())
                remaining()
                return out.decode('utf-8', 'strict')
            def identity():
                if Path(git('rev-parse', '--show-toplevel').strip()) != ROOT or git('rev-parse', 'HEAD').strip() != plan['source_head']:
                    raise ValueError('Wrong source repository or HEAD')
                if git('status', '--porcelain').strip():
                    raise ValueError('Source must be committed and clean before assembly')
            identity()
            source_files = []
            for record in git('ls-files', '--stage', '-z').split('\0'):
                if not record:
                    continue
                metadata, relative = record.split('\t', 1)
                mode, _, stage = metadata.split()
                if mode not in ('100644', '100755') or stage != '0':
                    raise ValueError('Unsupported source Git entry')
                data = held_read(source, ROOT / relative)
                source_files.append({'path': relative, 'sha256': sha(data), 'size': len(data)})
            source_files.sort(key=lambda item: item['path'])
            if len({item['path'] for item in source_files}) != len(source_files):
                raise ValueError('Duplicate source entry')
            checker = stack.enter_context(BuildTree(CHECKER))
            tooling = [{'path': name, 'sha256': sha(held_read(checker, CHECKER / name, plan['checker'][name]))} for name in CORE]
            roots = plan.get('runtimeTrees', [])
            if {item.get('name') for item in roots} != RUNTIME_NAMES or len(roots) != len(RUNTIME_NAMES):
                raise ValueError('Incomplete runtime tree map')
            runtimes = []
            for item in roots:
                root = Path(item['root'])
                lease = stack.enter_context(BuildTree(root))
                files = full_map(lease, root)
                if sha(packed(files)) != item['sha256'] or len(files) != item['count']:
                    raise ValueError('Reviewed complete runtime map changed: ' + item['name'])
                if item['name'] == 'git-installation' and root != GIT_RUNTIME:
                    raise ValueError('Unreviewed Git runtime root')
                if item['name'] == 'bundled-media' and root != ROOT / 'build-cache/runtime':
                    raise ValueError('Bundled media root changed')
                runtimes.append((item, files))
            graph, audited_nodes = declared_graph(source, source_files, ROOT, RUN_BASE, held_read)
            # All input validation precedes output. Both exact bases must be absent;
            # native FILE_CREATE refuses a concurrent preexisting path as well.
            if os.path.lexists(CONTEXT_BASE) or os.path.lexists(RUN_BASE):
                raise ValueError('Assembly output base already exists; never adopt or remove it')
            output = stack.enter_context(BuildTree(CONTEXT_BASE.parent))
            run_owner = stack.enter_context(BuildTree(RUN_BASE.parent))
            output._create_directory(CONTEXT_BASE)
            owned = output.fresh(CONTEXT_BASE)
            run_owner._create_directory(RUN_BASE)
            run_receipt = directory_receipt(run_owner, RUN_BASE)
            snapshot = output.directory(owned / 'source', create=True)
            for item in source_files:
                original = source.files[str(source.child(ROOT / item['path'])).casefold()]
                facts = output.write(snapshot / item['path'], original.chunks())
                if facts != {key: item[key] for key in ('sha256', 'size')}:
                    raise ValueError('Native snapshot copy differs')
            def emit(relative, value):
                file = owned / relative
                facts = output.write(file, [packed(value)])
                return {'path': str(file), 'sha256': facts['sha256']}
            source_manifest = emit('source-manifest.json', {'files': source_files})
            harness = output.directory(owned / 'harness', create=True)
            harness_ref = emit('harness/graph.json', graph)
            harness_manifest = emit('harness-manifest.json', {'files': [{'path': 'graph.json', 'sha256': harness_ref['sha256']}]})
            runtime_manifests = []
            for item, files in runtimes:
                runtime_manifests.append({'name': item['name'], 'root': item['root'], 'manifest': emit('runtime-' + item['name'] + '.json', {'files': files})})
            runtime = {key: {'name': key, **executables[key]} for key in ('node', 'npmCli', 'shell', 'npmShim')}
            runtime.update(manifests=runtime_manifests, koffiRoot=plan['koffiRoot'])
            route = next(item for item in source_files if item['path'] == 'scripts/check-desktop.mjs')
            context = {'schema': 2, 'deadlineMs': 600000, 'ownership': 'private-job-or-process-group',
                       'source': {'repo': str(ROOT), 'root': str(snapshot), 'head': plan['source_head'], 'dirty': 'N', 'manifest': source_manifest},
                       'harness': {'root': str(harness), 'manifest': harness_manifest}, 'runtime': runtime, 'tooling': {'files': tooling},
                       'execution': {'runRootParent': str(RUN_BASE), 'requiredFreePorts': [5212], 'ownedSiblingDirectories': ['build-guard-probes'],
                                     'runParentNativeReceipt': run_receipt, 'auditedNodes': audited_nodes}}
            identity()
            context_ref = emit('context.json', context)
            # V2 raw-byte sidecar; context schema/runtime data remain unchanged.
            runtime_index_ref = emit('runtime-index.json', {'schema': 'books-protocol2-runtime-index-v2', 'runtime': runtime})
            owner_ref = emit('assembly-owner.json', {'schema': 'books-entry-assembly-owner-v2', 'plan_sha256': args.plan_sha, 'source_head': plan['source_head'],
                                                    'context_base': directory_receipt(output, CONTEXT_BASE), 'context_root': directory_receipt(output, owned),
                                                    'run_parent': run_receipt, 'context_file': _native_receipt(output, Path(context_ref['path']))})
            remaining()
            print(json.dumps({'assembled': True, 'checks_executed': False, 'context': context_ref, 'runtimeIndex': runtime_index_ref, 'owner': owner_ref, 'runRootParent': str(RUN_BASE), 'max_declared_fixture_path': max(item['chars'] for item in graph['path_examples'])}))
    finally:
        timer.cancel()

if __name__ == '__main__':
    main()
