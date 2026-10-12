"""v0.13.1 regression: the checked-out replacement plan must be the exact bytes the admission guard accepts.

MergeService.replace_audiobook hashes the raw bytes of replacement_eye_plan.json. A Windows checkout
with core.autocrlf=true writes that file as CRLF unless .gitattributes pins it to LF, and the guard
then rejects the real admission (HTTP 400). These tests run the real guard, not a copy of its constant.
"""
import fnmatch,hashlib,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
import merge_service

ROOT=Path(merge_service.__file__).resolve().parent
PLAN=ROOT/'replacement_eye_plan.json'
GITATTRIBUTES=ROOT/'.gitattributes'
APPROVED_PARENT='9e04e700-ecf8-4807-8195-01a7a1d73bd6'
REJECTED='Approved replacement media plan changed'

class PassedGuard(Exception):pass

class GuardOnly:
    """Stands in for MergeService: the first attribute read after the plan guard stops the call."""
    operation_lock=threading.RLock()
    @property
    def reviews(self):raise PassedGuard

def admission_guard(plan):
    """Run the real replace_audiobook plan guard against `plan`; it reads the file named next to merge_service."""
    assert plan.name=='replacement_eye_plan.json',plan
    with patch.object(merge_service,'__file__',str(plan.with_name('merge_service.py'))):
        try:merge_service.MergeService.replace_audiobook(GuardOnly(),'Audiobooks','guard-probe',0,APPROVED_PARENT)
        except PassedGuard:return 'accepted'
        except ValueError as error:
            if str(error)==REJECTED:return 'rejected'
            raise
    raise AssertionError('replace_audiobook returned without reaching the post-guard stop')

def attributes(path_name,text):
    """Git attributes for a root-level file: later matching lines override earlier ones."""
    state={}
    for line in text.splitlines():
        fields=line.split()
        if not fields or fields[0].startswith('#'):continue
        pattern=fields[0].lstrip('/')
        if pattern.startswith('**/'):pattern=pattern[3:]
        if not fnmatch.fnmatchcase(path_name,pattern):continue
        for attr in fields[1:]:
            if attr=='binary':state.update(text=False,diff=False,merge=False)
            elif attr.startswith('-'):state[attr[1:]]=False
            elif attr.startswith('!'):state.pop(attr[1:],None)
            elif '=' in attr:name,value=attr.split('=',1);state[name]=value
            else:state[attr]=True
    return state

class ReplacementPlanBytesTests(unittest.TestCase):
    def test_checked_out_plan_passes_real_admission_guard(self):
        data=PLAN.read_bytes();crlf=data.count(b'\r\n')
        self.assertEqual(admission_guard(PLAN),'accepted',
            f'{PLAN} (sha256 {hashlib.sha256(data).hexdigest()}, {crlf} CRLF) is rejected by the admission guard. '
            'If CRLF: rm it, then git restore --worktree -- replacement_eye_plan.json '
            '(Docs/BooksArranger_LineEndingFix_v0.13.1_2026-10-12.md).')

    def test_guard_rejects_crlf_copy_of_plan(self):
        """Sensitivity control: the check above must be able to fail on a CRLF checkout."""
        lf=PLAN.read_bytes().replace(b'\r\n',b'\n');self.assertIn(b'\n',lf)
        with tempfile.TemporaryDirectory() as temp:
            copy=Path(temp)/PLAN.name;copy.write_bytes(lf.replace(b'\n',b'\r\n'))
            self.assertEqual(admission_guard(copy),'rejected')

    def test_gitattributes_pins_plan_to_lf(self):
        state=attributes(PLAN.name,GITATTRIBUTES.read_text(encoding='utf-8'))
        self.assertEqual(state.get('eol'),'lf',f'{GITATTRIBUTES} must keep "replacement_eye_plan.json text eol=lf"; effective {state}')
        self.assertIsNot(state.get('text'),False,f'{GITATTRIBUTES} unsets text for the plan; effective {state}')

if __name__=='__main__':unittest.main()
