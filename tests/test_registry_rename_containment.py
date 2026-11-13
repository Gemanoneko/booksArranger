"""Static containment only: never invoke a host registry rename to test it."""
import ast
from pathlib import Path
import re
import unittest

FORBIDDEN={'regrenamekey','ntrenamekey','renamekey'}
FACTORIES={'getattr','__getattr__','getprocaddress','func','cfunc','wrap'}
EXECUTORS={'run','popen','spawn','spawnsync','exec','execsync','execfile','execfilesync','system','check_output','check_call','call'}


def _names(value):
    return bool(re.search(r'\b(?:RegRenameKey|NtRenameKey)\b',value,re.I))


def _registry_shell(source):
    problems=[];registry_location=False
    for line in re.split(r'[;\n]',source):
        line=re.sub(r'#.*$','',line)
        registry=bool(re.search(r'(?:Registry::|\bHK(?:CU|LM|CR|U|CC):|\bHKEY_(?:CURRENT_USER|LOCAL_MACHINE|CLASSES_ROOT|USERS|CURRENT_CONFIG))',line,re.I))
        if re.search(r'\b(?:Set-Location|cd|sl)\b',line,re.I):registry_location=registry
        rename=re.search(r'\b(?:Rename-Item|Move-Item|rni|ren|mi|mv)\b',line,re.I)
        filesystem=bool(re.search(r'[\x27\x22\s][A-Z]:[\\/]',line,re.I))
        if rename and (registry or registry_location and not filesystem):problems.append('registry-provider rename/move')
    return problems


def registry_rename_bindings(source,suffix):
    """Conservative maintained-route audit, not a general security parser."""
    found=[]
    if suffix=='.py':
        tree=ast.parse(source);assigned={}
        for node in ast.walk(tree):
            if isinstance(node,ast.Assign) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str):
                for target in node.targets:
                    if isinstance(target,ast.Name):assigned[target.id]=node.value.value
        for node in ast.walk(tree):
            if isinstance(node,ast.Attribute) and node.attr.casefold() in FORBIDDEN:found.append('native attribute binding')
            if isinstance(node,ast.ImportFrom) and node.module=='winreg' and any(a.name.casefold() in FORBIDDEN for a in node.names):found.append('registry import binding')
            if isinstance(node,ast.Subscript) and isinstance(node.slice,ast.Constant) and isinstance(node.slice.value,(str,bytes)):
                value=node.slice.value.decode('ascii','ignore') if isinstance(node.slice.value,bytes) else node.slice.value
                if _names(value):found.append('native indexed binding')
            if not isinstance(node,ast.Call):continue
            callee=getattr(node.func,'attr',getattr(node.func,'id','')).casefold()
            strings=[]
            for argument in node.args:
                for part in ast.walk(argument):
                    if isinstance(part,ast.Constant) and isinstance(part.value,(str,bytes)):
                        strings.append(part.value.decode('ascii','ignore') if isinstance(part.value,bytes) else part.value)
                    elif isinstance(part,ast.Name) and part.id in assigned:strings.append(assigned[part.id])
            if callee in FACTORIES and any(_names(s) for s in strings):found.append('dynamic native binding')
            if callee in EXECUTORS:
                for value in strings:found.extend(_registry_shell(value))
        return found
    if suffix in {'.ps1','.cmd','.bat'}:return _registry_shell(source)
    # Skip comments and distinguish quoted data from actual member bindings.
    tokens=re.findall(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\x27(?:\\.|[^\x27\\])*\x27|`(?:\\.|[^`\\])*`|[A-Za-z_$][\w$]*|\S',source)
    previous='';frames=[]
    for token in tokens:
        if token.startswith(('//','/*')):continue
        quoted=token[:1] in {'"',"'",'`'}
        if quoted:
            if frames and frames[-1] in FACTORIES and _names(token):found.append('FFI signature binding')
            if previous=='[' and _names(token):found.append('native indexed binding')
            found.extend(_registry_shell(token[1:-1]))
        elif token=='(':frames.append(previous.casefold())
        elif token==')' and frames:frames.pop()
        elif previous=='.' and token.casefold() in FORBIDDEN:found.append('native member binding')
        previous=token
    return found


class RegistryRenameContainmentTests(unittest.TestCase):
    def test_nonexecuted_unsafe_binding_controls_are_rejected(self):
        controls=[('.py','dll.RegRenameKey'),('.py',"getattr(dll,'NtRenameKey')"),
            ('.py',"GetProcAddress(handle,b'RegRenameKey')"),('.py','from winreg import RenameKey'),
            ('.mjs',"dll.func('LONG RegRenameKey(HKEY, wchar_t*)')"),
            ('.ps1',"Rename-Item -LiteralPath 'HKCU:\\Software\\Private' -NewName Other"),
            ('.ps1',"Set-Location HKCU:\\Software; Move-Item Private Other")]
        for suffix,text in controls:
            with self.subTest(suffix=suffix,source=text):self.assertTrue(registry_rename_bindings(text,suffix))

    def test_filesystem_rename_and_inert_names_remain_allowed(self):
        for suffix,text in [('.py','path.rename(other)'),('.py',"name='RegRenameKey'"),
                ('.mjs',"const name='NtRenameKey'; file.rename(next);"),
                ('.ps1',"Move-Item -LiteralPath 'I:\\Private\\source' -Destination 'I:\\Private\\target'")]:
            with self.subTest(source=text):self.assertEqual(registry_rename_bindings(text,suffix),[])

    def test_maintained_source_and_runner_routes_have_no_live_registry_rename(self):
        root=Path(__file__).resolve().parents[1]
        paths=list(root.glob('*.py'))
        for folder in ('tests','scripts','desktop'):
            paths.extend(p for p in (root/folder).rglob('*') if p.is_file() and
                         p.suffix in {'.py','.js','.mjs','.cjs','.ps1','.cmd','.bat'} and
                         not any(part in {'node_modules','__pycache__'} for part in p.parts))
        violations=[]
        for path in sorted(set(paths)):
            bindings=registry_rename_bindings(path.read_text('utf-8-sig'),path.suffix)
            if bindings:violations.append((str(path.relative_to(root)),bindings))
        self.assertEqual(violations,[])


if __name__=='__main__':unittest.main()
