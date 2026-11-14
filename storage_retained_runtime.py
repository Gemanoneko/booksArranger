"""Exact retained members admitted for display and kept outside work/disposal."""
import ntpath
from pathlib import PureWindowsPath
import re
from contextlib import ExitStack, contextmanager
from pathlib import Path

from storage_relocation import RelocationRefused, _inside, _key, _relative

SCHEMA = 'books-storage-retention-runtime-v1'
STAGE = {'retained-legacy-stage','retained-unconfirmed-stage','retained-closed-stage-directory'}
REPAIR = {'retained-completed-chapter-evidence','retained-chapter-diagnostic'}
COVER = {'deterministic-cover-cache','retained-cover-diagnostic-pair'}


def reviewed_members(report, plan):
    if (report.get('schema') != 'books-retained-class-analysis-v1' or
        report.get('selection_sha256') != plan['preservation_selection']['sha256'] or
        report.get('unclassified') != [] or
        any(report.get(key) is not False for key in ('membership','resume_authority','disposal_authority'))):
        raise RelocationRefused('Reviewed retention evidence does not cover this verified selection')
    members = index_members(report.get('members'), plan['scopes'][0])
    if set(members) != set(plan['owned_state']['copy_only']):
        raise RelocationRefused('Reviewed retention member set differs from verified copied files')
    return members


def historical_members(plan):
    """Add earlier typed retained paths without changing their transfer classes."""
    result=[]
    scope=PureWindowsPath(plan['scopes'][0])
    dirs={_key(row['relative']):row['relative'] for row in plan['directories']}
    for row in plan['owned_state']['files']:
        if row['kind']!='historical-staging-retained':
            continue
        tail=PureWindowsPath(row['relative']).relative_to(scope).parts
        if len(tail) not in (4,5) or tail[:2]!=('merge-cache','audio-staging'):
            raise RelocationRefused('Historical staging evidence escaped its exact producer')
        job=tail[2]
        attempt=tail[3] if len(tail)==5 else None
        values={'job_id':job,'resume_authority':False,'disposal_authority':False}
        if attempt:
            values['attempt_id']=attempt
            parent=_key(ntpath.dirname(row['relative']))
            result.append(dict(values,relative=dirs[parent],category='retained-closed-stage-directory'))
        result.append(dict(values,relative=row['relative'],category=
                           'retained-legacy-stage' if attempt else 'retained-historical-stage-marker'))
    return list({_key(row['relative']):row for row in result}.values())


def index_members(rows, scope, *, allow_empty=False):
    if not isinstance(rows,list) or not int(not allow_empty) <= len(rows) <= 15000:
        raise RelocationRefused('Invalid retained runtime census')
    result={}
    for row in rows:
        path=_relative(row['relative'])
        key=_key(path)
        if (key in result or not _inside(path,scope) or
            any(row.get(item) is not False for item in ('resume_authority','disposal_authority'))):
            raise RelocationRefused('Invalid retained runtime scope or authority')
        tail=PureWindowsPath(ntpath.relpath(path,scope)).parts
        category=row['category']
        if category in STAGE:
            valid=(len(tail) in (4,5) and tail[:2]==('merge-cache','audio-staging') and
                   tail[2:4] == (row.get('job_id'),row.get('attempt_id')) and
                   all(re.fullmatch('[a-f0-9-]{36}',part) for part in tail[2:4]))
        elif category=='retained-historical-stage-marker':
            valid=(len(tail)==4 and tail[:2]==('merge-cache','audio-staging') and tail[2]==row.get('job_id') and
                   tail[3]=='ownership.json' and re.fullmatch('[a-f0-9-]{36}',tail[2]))
        elif category in REPAIR:
            valid=(len(tail) in (2,3) and tail[0]=='chapter-repairs' and tail[1]==row.get('repair_id'))
        elif category in COVER:
            valid=len(tail)==3 and tail[:2]==('merge-cache','covers')
        else:
            valid=category=='retained-series-backfill-root' and tail==('merge-cache','series-backfill')
        if not valid:
            raise RelocationRefused('Retained runtime evidence does not match its exact area')
        result[key]=row
    return result


@contextmanager
def retained_target_lease(target, records):
    """Hold every exact file/directory and shared ancestor against replacement."""
    from native_io import DirectoryBoundary
    from source_cleanup import single_stream
    from storage_relocation_operator import NativeItem,Security,_no_directory_streams,checkpoint
    target=Path(target).absolute()
    guards={}
    items={}
    security=Security()
    from storage_admission_progress import report
    report('retained',0,len(records))
    with ExitStack() as stack:
        for key,record in records.items():
            checkpoint()
            native=record['native']
            relative=_relative(native['relative'])
            if _key(relative)!=key:
                raise RelocationRefused('Retained native record escaped its registered path')
            path=target/relative
            if path.parent not in guards:
                guards[path.parent]=stack.enter_context(DirectoryBoundary(target.anchor,path.parent))
            directory='facts' not in native
            item=stack.enter_context(NativeItem(path,directory=directory))
            if directory:
                _no_directory_streams(path)
                valid=item.facts['identity']==native['identity']
            else:
                single_stream(path)
                valid=item.facts==native['facts'] and item.sha256()==native['sha256']
            if not valid or security.capture(item)['sha256']!=record['security_sha256']:
                raise RelocationRefused('Retained target identity, bytes or permissions changed: '+relative)
            items[key]=item
            report('retained',len(items),len(records))
        yield items
