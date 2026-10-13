"""Assemble one immutable Books protocol-2 input set; never run its checks.

Reviewed operation: python -I -B <this file> --plan-sha <SHA256> --plan-json
<exact reviewed books-entry-assembly-plan-v1 JSON>. The plan supplies
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
CONTEXT_BASE = Path('C:/Users/AnGeLZzZ/AppData/Local/Temp/ba016-20261013')
RUN_BASE = Path('C:/b16')
CHECKER = STUDIO / '.claude/skills/qa-handoff/scripts'
CORE = ['run_entry_checks.mjs', 'entry-main.mjs', 'entry-identity.mjs', 'bounded-check.mjs', 'bounded-child.mjs']
BOOTSTRAP = ['scripts/qa-context-assembly.py', 'scripts/build_fs_guard.py', 'native_io.py']
PYTHON_TESTS = ['test_desktop_quit.py', 'test_desktop_catalog.py', 'test_desktop_host.py', 'test_build_guard.py',
                'test_working_cleanup.py', 'test_working_precision.py', 'test_working_lifecycle.py',
                'test_storage_cleanup.py', 'test_automatic_media_policy.py', 'test_automatic_media.py', 'test_standing_admission.py']
NODE_TESTS = ['release-contract.test.mjs', 'release-flow.test.mjs', 'update-controller.test.mjs',
              'engine-update.test.mjs', 'launch-options.test.mjs', 'release-leased-executables.test.mjs']

def packed(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()

def sha(value):
    return hashlib.sha256(value).hexdigest()

def ref_ok(value):
    return isinstance(value, dict) and isinstance(value.get('path'), str) and bool(re.fullmatch('[a-f0-9]{64}', value.get('sha256', '')))

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
        if plan.get('schema') != 'books-entry-assembly-plan-v1' or not re.fullmatch('[a-f0-9]{40}', plan.get('source_head', '')):
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
            if {item.get('name') for item in roots} != {'dependencies', 'ownership', 'node-installation', 'system-python', 'bundled-media'} or len(roots) != 5:
                raise ValueError('Incomplete runtime tree map')
            runtimes = []
            for item in roots:
                root = Path(item['root'])
                lease = stack.enter_context(BuildTree(root))
                files = full_map(lease, root)
                if sha(packed(files)) != item['sha256'] or len(files) != item['count']:
                    raise ValueError('Reviewed complete runtime map changed: ' + item['name'])
                if item['name'] == 'bundled-media' and (root != ROOT / 'build-cache/runtime' or len(files) != 48):
                    raise ValueError('Expected exact existing 48-file bundled media map')
                runtimes.append((item, files))
            python_ids = []
            for name in PYTHON_TESTS:
                tree = ast.parse(held_read(source, ROOT / 'tests' / name).decode('utf-8-sig'))
                python_ids.extend(name[:-3] + '.' + cls.name + '.' + method.name for cls in tree.body if isinstance(cls, ast.ClassDef)
                                  for method in cls.body if isinstance(method, ast.FunctionDef) and method.name.startswith('test'))
            node_ids = []
            for name in NODE_TESTS:
                node_ids.extend(name + ':' + title for title in re.findall(r"(?m)^test\('([^']+)'", held_read(source, ROOT / 'tests' / name).decode('utf8')))
            if len(python_ids) != 137 or len(node_ids) != 29:
                raise ValueError('Declared static graph changed; actual discovery is still pending')
            uuid = '00000000-0000-0000-0000-000000000000'
            future = RUN_BASE / 'entry-run-XXXXXX'
            examples = [future / 'scratch/automatic-processing-2026-10-10/test-fixtures/tmpXXXXXXXX/cache/audio-staging' / uuid / uuid / ('0' * 32 + '.decode-stderr'),
                        RUN_BASE / 'build-guard-probes' / uuid / 'build-cache/builds' / uuid / 'metadata-rotation-complete.json']
            if max(len(str(path)) for path in examples) > 259:
                raise ValueError('Declared deepest fixture path exceeds ordinary Windows path bound')
            graph = {'schema': 'books-entry-graph-v1', 'kind': 'static-declarations-not-executed', 'python_ids': sorted(python_ids), 'node_ids': sorted(node_ids),
                     'fixture_parent': 'scratch/source-fallback-2026-10-11', 'private_temp': 'scratch/entry-temp', 'sibling_output': 'build-guard-probes',
                     'required_free_ports': [5212], 'path_examples': [{'path': str(path), 'chars': len(str(path))} for path in examples],
                     'preserved_wait': 'single state snapshot plus both workers inactive', 'runtime_packaged_equivalence': 'pending guarded pack'}
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
                                     'runParentNativeReceipt': run_receipt, 'auditedNodes': [{'path': route['path'], 'sha256': route['sha256'], 'kind': 'pure-node', 'command': 'node scripts/check-desktop.mjs'}]}}
            identity()
            context_ref = emit('context.json', context)
            owner_ref = emit('assembly-owner.json', {'schema': 'books-entry-assembly-owner-v1', 'plan_sha256': args.plan_sha, 'source_head': plan['source_head'],
                                                    'context_base': directory_receipt(output, CONTEXT_BASE), 'context_root': directory_receipt(output, owned),
                                                    'run_parent': run_receipt, 'context_file': _native_receipt(output, Path(context_ref['path']))})
            remaining()
            print(json.dumps({'assembled': True, 'checks_executed': False, 'context': context_ref, 'owner': owner_ref, 'runRootParent': str(RUN_BASE), 'max_declared_fixture_path': max(len(str(path)) for path in examples)}))
    finally:
        timer.cancel()

if __name__ == '__main__':
    main()
