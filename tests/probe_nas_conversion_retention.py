"""Explicit real-media NAS/I two-job assessment, exclusively fresh owned roots.

Run again against the final bundled I: runtime/backend; engineering runs do
not constitute final packaged verification. No existing library is selected.
"""
import argparse,contextlib,hashlib,json,os,shutil,subprocess,sys,threading,time,uuid
from pathlib import Path
from unittest.mock import patch


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend',required=True);parser.add_argument('--ffmpeg',required=True)
    parser.add_argument('--local-parent',required=True);parser.add_argument('--nas-parent',required=True)
    args=parser.parse_args();backend=Path(args.backend).absolute();local_parent=Path(args.local_parent).absolute()
    nas_parent=Path(args.nas_parent).absolute();codec=Path(args.ffmpeg).absolute()
    if backend.drive.casefold()!='i:' or local_parent.drive.casefold()!='i:' or nas_parent!=Path('Z:/Books Arranger/Engineering'):
        raise ValueError('Explicit approved engineering backend/work/NAS roots required')
    if Path(sys.executable).drive.casefold()!='i:' or codec.drive.casefold()!='i:':raise ValueError('Actual I: Python and FFmpeg required')
    tag='nas-conversion-'+uuid.uuid4().hex;local=local_parent/tag;nas=nas_parent/tag
    local.mkdir();nas.mkdir();temporary=local/'Temp';temporary.mkdir()
    os.environ.update(BOOKS_WORK_TEMP=str(temporary),TEMP=str(temporary),TMP=str(temporary))
    os.environ['PATH']=str(codec)+os.pathsep+str(Path(os.environ['SystemRoot'])/'System32')
    sys.path[:0]=[str(backend),str(Path(__file__).resolve().parent)]
    from storage_relocation_native import configure_work_temp
    configure_work_temp()
    import test_automatic_media as fixtures
    from test_automatic_processing import fixture_payload
    from scanner import Inventory
    from scan_wait import finish_scan
    from merge_service import MergeService
    from catalog_owner import catalog_lock
    from public_research import PublicClient,PublicResearch
    from native_write_trace import NativeWriteTrace
    import research_switch
    for name in ('scanner','merge_service','audio_jobs','native_io','runtime_file_disposition'):
        __import__(name)
        if not Path(sys.modules[name].__file__).is_relative_to(backend):raise AssertionError('Production module escaped target backend: '+name)
    f=fixtures.AutomaticMediaTests('test_confident_no_manual_form_to_verified_chapters_retained_recovery')
    with patch.object(fixtures,'AREA',local):f.setUp()
    f.temp._finalizer.detach() # explicit review evidence; never point cleanup at NAS
    f.service.close()
    library=nas/'Library';library.mkdir();sorted_root=nas/'New output';sorted_root.mkdir()
    first=library/'Book one';second=library/'Book two';first.mkdir();second.mkdir()
    sources=[]
    for path in f.sources:
        copy=first/path.name;shutil.copyfile(path,copy);sources.append(copy)
        produced=local/('second-'+path.name)
        subprocess.run([str(codec/'ffmpeg.exe'),'-v','error','-nostdin','-n','-i',str(path),'-map','0','-c','copy',
                        '-metadata','album=A Book Two',str(produced)],check=True,timeout=30,creationflags=0x08000000)
        copy=second/path.name;shutil.copyfile(produced,copy);sources.append(copy)
    before={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    roots={'Audiobooks':str(library),'Podcasts':str(nas/'Podcasts'),'Ebooks':str(local/'Ebooks')}
    Path(roots['Podcasts']).mkdir();Path(roots['Ebooks']).mkdir()
    data=local/'Data';data.mkdir();database=data/'inventory.sqlite3'
    guard_roots={**roots,'Output':str(sorted_root)}
    def fetch(url,*unused):
        from urllib.parse import unquote_plus
        two='book two' in unquote_plus(url).lower() or '/43/' in url or 'book-two' in url
        title='A Book Two' if two else 'A Book';identifier=43 if two else 42
        if '/search-works?' in url:return json.dumps([dict(work_id=identifier,name=title,rusname='Книга Два' if two else 'Книга',all_autor_name='John Writer',all_autor_rusname='Джон Писатель')]).encode()
        if '/work/' in url and '/extended' in url:
            value=fixture_payload();value.update(work_id=identifier,work_name='Книга Два' if two else 'Книга',work_name_orig=title);return json.dumps(value).encode()
        if 'duckduckgo.com' in url:return ('<a class="result__a" href="https://ast.ru/book/'+('book-two' if two else 'book-one')+'/">'+title+'</a>').encode()
        if 'ast.ru' in url:return ('<p>John Writer. '+title+'</p>').encode()
        if 'fantlab.ru/images/cover.jpg' in url:return f.cover
        raise AssertionError('Unexpected fixture URL')
    started=time.monotonic();job_ids=[];outputs=[];cleanup=[]
    try:
        with NativeWriteTrace(local) as local_trace,NativeWriteTrace(nas) as nas_trace:
            (local/'trace-control').write_bytes(b'local positive control');(nas/'trace-control').write_bytes(b'NAS positive control')
            with catalog_lock(database,guard_roots):
                f.inv=Inventory(database,roots,output_root=str(sorted_root));f.audio=library;f.sources=sources
                f.inv.launch('Audiobooks');finish_scan(f.inv)
                f.service=MergeService(f.inv,data/'merge-cache');f.client=PublicClient(database,fetch=fetch)
                rows=f.service.reviews.page()['rows'];f.assertEqual(len(rows),2,rows)
                with patch.object(f.service.jobs,'resume',return_value=None):
                    for row in rows:
                        result=PublicResearch(f.client).lookup(row,str(library));f.assertEqual(result['reasons'],[],result)
                        _,job=f.service.approve_automatic(row,result,threading.Event(),f.client);job_ids.append(job)
                f.service.jobs.resume();f.wait()
                jobs={j['job_id']:j for j in f.service.jobs.status()['jobs']}
                for job in job_ids:
                    f.assertEqual(jobs[job]['state'],'completed',jobs[job]);output=jobs[job]['output']
                    path=Path(output['final_path']);f.assertTrue(path.is_relative_to(sorted_root))
                    f.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),output['sha256']);outputs.append(dict(path=str(path),sha256=output['sha256']))
                    row=f.service.cleanup.status(job);f.assertEqual(row['state'],'needs_attention',row)
                    f.assertEqual(row['removed'],0,row);cleanup.append(dict(state=row['state'],remaining=row['remaining'],reason=row.get('reason','')))
                f.assertEqual({str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},before)
                f.service.close()
            with catalog_lock(database,guard_roots):
                f.inv=Inventory(database,roots,output_root=str(sorted_root));f.service=MergeService(f.inv,data/'merge-cache')
                jobs={j['job_id']:j for j in f.service.jobs.status()['jobs']}
                f.assertTrue(all(jobs[j]['state']=='completed' for j in job_ids));f.service.close()
            f.assertEqual({str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},before)
        f.assertTrue(any('/audio-staging/' in e['path'].replace('\\','/') for e in local_trace.events))
        f.assertTrue(any(Path(e['path']).is_relative_to(sorted_root) for e in nas_trace.events))
        report=dict(schema='books-nas-conversion-retention-assessment-v1',local=str(local),nas=str(nas),
            python=sys.executable,backend=str(backend),ffmpeg=str(codec),jobs=len(job_ids),completed=len(outputs),
            all_originals_retained=True,restart_completed=True,cleanup=cleanup,outputs=outputs,
            local_event_count=len(local_trace.events),nas_event_count=len(nas_trace.events),elapsed_seconds=round(time.monotonic()-started,3))
        trace=local/'filesystem-trace.json';trace.write_text(json.dumps(dict(local=local_trace.events,nas=nas_trace.events)),encoding='utf8')
        report['trace_sha256']=hashlib.sha256(trace.read_bytes()).hexdigest()
        (local/'evidence.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
    finally:
        f.service.close();research_switch.restore_pin(f)


if __name__=='__main__':main()
