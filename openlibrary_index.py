"""Explicit sparse Open Library import; lookups never decompress a dump.

Pending builds are not discoverable by readers. Every invocation authenticates the
entire compressed source under native read holds BEFORE trusting resumable rows.
gzip.seek replays prior decompression: this saves index work, not decompression time.
Source dumps remain untouched. Editions/edition series strings are not order proof.
"""
import argparse
import contextlib
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import datetime as dt
import uuid
import base64

SCHEMA=1
NORMALIZATION='local-title-key-v1'
ADAPTER='openlibrary-sparse-identity-v2'
MAX_LINE=8*1024*1024
MAX_TARGETS=10000

def _json(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def _digest(value):return hashlib.sha256(_json(value).encode()).hexdigest()
def _hash(path):
    result=hashlib.sha256()
    with open(path,'rb') as stream:
        while block:=stream.read(1024*1024):result.update(block)
    return result.hexdigest()
def _check(deadline):
    if time.monotonic()>=deadline:raise TimeoutError('Open Library import time slice ended; checkpoint retained')

def official_manifest(raw,receipt,date,directory):
    """Only the small dated metadata response; embedded download URLs are ignored."""
    from public_research import strict_json,allowed_url
    dt.date.fromisoformat(date)
    url='https://archive.org/metadata/ol_dump_'+date
    allowed_url(url)
    if not isinstance(raw,bytes) or len(raw)>2*1024*1024 or receipt.get('url')!=url or receipt.get('sha256')!=hashlib.sha256(raw).hexdigest():raise ValueError('Official metadata receipt mismatch')
    data=strict_json(raw)
    if not isinstance(data,dict) or data.get('metadata',{}).get('identifier')!='ol_dump_'+date or not isinstance(data.get('files'),list):raise ValueError('Wrong official dump snapshot')
    sources={}
    for kind in ('authors','works','editions'):
        filename='ol_dump_'+kind+'_'+date+'.txt.gz'
        records=[entry for entry in data['files'] if isinstance(entry,dict) and entry.get('name')==filename]
        if len(records)!=1:raise ValueError('Missing or duplicate official dump entry')
        record=records[0];size=str(record.get('size',''))
        if not re.fullmatch(r'[1-9]\d{0,13}',size) or not re.fullmatch('[a-f0-9]{40}',str(record.get('sha1',''))) or not re.fullmatch('[a-f0-9]{32}',str(record.get('md5',''))):raise ValueError('Invalid official dump integrity fields')
        sources[kind]={'path':str(Path(directory).absolute()/filename),'size':int(size),'sha1':record['sha1'],'md5':record['md5']}
    return {'schema':SCHEMA,'date':date,'source_url':url,'metadata_receipt':receipt,'metadata_raw_base64':base64.b64encode(raw).decode('ascii'),
            'sources':{kind:sources[kind] for kind in ('works','authors')},'pending_editions':sources['editions']}

def validate_manifest(manifest):
    if not isinstance(manifest,dict) or manifest.get('schema')!=SCHEMA:raise ValueError('Unsupported dump manifest')
    date=manifest.get('date','')
    if not re.fullmatch(r'20\d{2}-\d{2}-\d{2}',date) or manifest.get('source_url')!='https://archive.org/metadata/ol_dump_'+date:raise ValueError('Official dated dump manifest required')
    dt.date.fromisoformat(date)
    receipt=manifest.get('metadata_receipt',{})
    if receipt.get('url')!=manifest['source_url'] or not re.fullmatch('[a-f0-9]{64}',str(receipt.get('sha256',''))) or not isinstance(receipt.get('retrieved_utc'),str):raise ValueError('Official raw metadata receipt required')
    sources=manifest.get('sources')
    if not isinstance(sources,dict) or set(sources) not in ({'works','authors'},{'works','authors','editions'}):raise ValueError('Complete works and authors sources required')
    for kind,source in sources.items():
        if not isinstance(source,dict):raise ValueError('Malformed dump source')
        path=Path(source.get('path',''))
        if not path.is_absolute() or path.name!='ol_dump_'+kind+'_'+date+'.txt.gz':raise ValueError('Partial or mismatched dump filename')
        if type(source.get('size')) is not int or source['size']<=0 or not re.fullmatch('[a-f0-9]{40}',str(source.get('sha1',''))) or not re.fullmatch('[a-f0-9]{32}',str(source.get('md5',''))):raise ValueError('Official compressed size, SHA1 and MD5 required')
    raw=base64.b64decode(manifest.get('metadata_raw_base64',''),validate=True)
    bound=official_manifest(raw,receipt,date,Path(sources['works']['path']).parent)
    for kind,source in sources.items():
        expected=bound['pending_editions'] if kind=='editions' else bound['sources'][kind]
        if source!=expected:raise ValueError('Dump expectations differ from receipt-bound official metadata')
    return sources

@contextlib.contextmanager
def _source(path):
    from native_io import DirectoryBoundary,VerifiedFile
    path=Path(path)
    with contextlib.ExitStack() as stack:
        stack.enter_context(DirectoryBoundary(path.parent,path.parent));held=stack.enter_context(VerifiedFile(path))
        if held.facts()['links']!=1:raise ValueError('Dump source is linked')
        held.dump_streams=local_dump_streams(path,held.facts()['size'])
        yield held

def local_dump_streams(path,default_size):
    """Read-only downloaded-dump policy, separate from destructive recovery rules.

    Only the authenticated default bytes are decompressed. The optional browser
    marker is not read, interpreted, executed, copied, indexed, removed or changed.
    """
    import ctypes
    from ctypes import wintypes
    from native_io import kernel
    class Stream(ctypes.Structure):_fields_=[('size',ctypes.c_longlong),('name',wintypes.WCHAR*296)]
    kernel.FindFirstStreamW.argtypes=[wintypes.LPCWSTR,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD];kernel.FindFirstStreamW.restype=wintypes.HANDLE
    kernel.FindNextStreamW.argtypes=[wintypes.HANDLE,ctypes.c_void_p];kernel.FindNextStreamW.restype=wintypes.BOOL
    kernel.FindClose.argtypes=[wintypes.HANDLE]
    info=Stream();handle=kernel.FindFirstStreamW(str(path),0,ctypes.byref(info),0)
    if handle==ctypes.c_void_p(-1).value:raise ValueError('Cannot enumerate downloaded dump streams')
    result=[];seen=set()
    try:
        while True:
            name=info.name;size=info.size
            if name in seen or name not in ('::$DATA',':Zone.Identifier:$DATA') or size<0 or name==':Zone.Identifier:$DATA' and size>65536:raise ValueError('Unsupported downloaded dump stream; source unchanged')
            seen.add(name);result.append({'name':name,'size':size})
            if not kernel.FindNextStreamW(handle,ctypes.byref(info)):
                if ctypes.get_last_error()!=38:raise ValueError('Incomplete downloaded dump stream enumeration')
                break
    finally:kernel.FindClose(handle)
    if [entry['size'] for entry in result if entry['name']=='::$DATA']!=[default_size]:raise ValueError('Downloaded default stream size differs from held source')
    return sorted(result,key=lambda entry:entry['name'])

def _authenticate(held,expected,deadline):
    if held.facts()['size']!=expected['size']:raise ValueError('Dump is incomplete or size differs from official manifest')
    digest=hashlib.sha1();md5=hashlib.md5();local=hashlib.sha256()
    for block in held.chunks():_check(deadline);digest.update(block);md5.update(block);local.update(block)
    if digest.hexdigest()!=expected['sha1'] or md5.hexdigest()!=expected['md5']:raise ValueError('Dump differs from official compressed checksum')
    return local.hexdigest()

def _publish_json(path,value,boundary):
    from native_io import VerifiedFile,publish_no_replace
    raw=_json(value).encode('utf-8');temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    with open(temporary,'xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    with VerifiedFile(temporary) as held:
        if held.facts()['links']!=1:raise ValueError('Index receipt temporary is linked')
        identity=held.facts()['identity']
    def checked(facts):
        if facts['identity']!=identity:raise ValueError('Index receipt temporary changed')
    publish_no_replace(temporary,path,boundary,hashlib.sha256(raw).hexdigest(),len(raw),checked)

@contextlib.contextmanager
def _owned_sqlite(path,binding,boundary):
    """SQLite namespace ownership, not exclusion of arbitrary external writers.

    Cooperative builders share the importer lock. Native retained ordinary unique
    DB/journal handles deny rename/delete while SQLite uses compatible R/W sharing.
    PERSIST uses the precreated journal; no WAL, SHM, disk temporary or ATTACH runs.
    """
    import ctypes
    from native_io import kernel,VerifiedFile,FileInfo
    from source_cleanup import single_stream
    owner=path.with_name(path.name+'.owner.json');journal=path.with_name(path.name+'-journal')
    if any(os.path.lexists(p) for p in (path.with_name(path.name+'-wal'),path.with_name(path.name+'-shm'))) or any(path.parent.glob(path.name+'-mj*')):raise ValueError('Unexpected SQLite sidecar; index retained')
    with contextlib.ExitStack() as stack:
        previous=None
        if os.path.lexists(owner):
            protected=stack.enter_context(VerifiedFile(owner))
            if protected.facts()['links']!=1 or protected.facts()['size']>65536:raise ValueError('Invalid SQLite ownership receipt')
            single_stream(owner);previous=json.loads(b''.join(protected.chunks()))
            if previous.get('binding')!=binding:raise ValueError('SQLite ownership binding differs')
        elif os.path.lexists(path) or os.path.lexists(journal):raise ValueError('Unknown SQLite leaves without producer receipt')
        held_files=[]
        for leaf in (path,journal):
            handle=kernel.CreateFileW(str(leaf),0x80000080,3,None,3 if previous else 1,0x00200000,None)
            if handle==ctypes.c_void_p(-1).value:raise ValueError('Cannot retain ordinary SQLite leaf')
            held=VerifiedFile(leaf);held.handle=handle;held.info=FileInfo();stack.callback(held.__exit__,None,None,None)
            if not kernel.GetFileInformationByHandle(handle,ctypes.byref(held.info)) or held.info.attributes&(0x400|0x10) or held.facts()['links']!=1:raise ValueError('SQLite leaf is reparse, directory or linked')
            single_stream(leaf);held_files.append(held)
        identities=[held.facts()['identity'] for held in held_files]
        if previous:
            if previous.get('identities')!=identities:raise ValueError('SQLite retained identities differ from producer receipt')
        else:
            _publish_json(owner,{'binding':binding,'identities':identities},boundary)
            protected=stack.enter_context(VerifiedFile(owner))
            if protected.facts()['links']!=1:raise ValueError('SQLite producer receipt is linked')
        with contextlib.closing(sqlite3.connect(path,timeout=.2)) as db,db:
            db.execute('PRAGMA temp_store=MEMORY')
            if db.execute('PRAGMA journal_mode=PERSIST').fetchone()[0].lower()!='persist':raise ValueError('SQLite persistent journal unavailable')
            db.execute('PRAGMA synchronous=FULL')
            yield db
        for held,identity in zip(held_files,identities):
            if not kernel.GetFileInformationByHandle(held.handle,ctypes.byref(held.info)) or held.facts()['identity']!=identity or held.facts()['links']!=1:raise ValueError('SQLite leaf identity changed')
        if any(os.path.lexists(p) for p in (path.with_name(path.name+'-wal'),path.with_name(path.name+'-shm'))) or any(path.parent.glob(path.name+'-mj*')):raise ValueError('Unexpected SQLite sidecar after close')

@contextlib.contextmanager
def _read_sqlite(path):
    from native_io import VerifiedFile,DirectoryBoundary
    from source_cleanup import single_stream
    with contextlib.ExitStack() as stack:
        stack.enter_context(DirectoryBoundary(path.parent,path.parent));held=stack.enter_context(VerifiedFile(path))
        if held.facts()['links']!=1:raise ValueError('Read-only index is linked')
        single_stream(path)
        owner_name=path.name.replace('index-','pending-',1) if path.name.startswith('index-') else path.name
        with VerifiedFile(path.with_name(owner_name+'.owner.json')) as owner:
            if owner.facts()['links']!=1 or owner.facts()['size']>65536:raise ValueError('Read-only index ownership receipt invalid')
            single_stream(owner.path);receipt=json.loads(b''.join(owner.chunks()))
            if receipt.get('identities',[None])[0]!=held.facts()['identity']:raise ValueError('Read-only index identity differs from producer receipt')
        immutable=path.name.startswith('index-')
        if not immutable:
            journal=stack.enter_context(VerifiedFile(path.with_name(path.name+'-journal')))
            if journal.facts()['links']!=1 or journal.facts()['identity']!=receipt['identities'][1]:raise ValueError('Read-only registry journal differs from producer receipt')
            single_stream(journal.path)
        with contextlib.closing(sqlite3.connect('file:'+path.as_posix()+'?mode=ro'+('&immutable=1' if immutable else ''),uri=True,timeout=.1)) as db:
            yield db,held

def _hold_title(db,key,reason,record_id='',people=None,record_type=None):
    detail={'record_id':str(record_id)[:100],'record_type':str(record_type)[:100],
            'authors_shape':type(people).__name__,'authors_count':len(people) if isinstance(people,list) else None}
    db.execute('INSERT OR IGNORE INTO identity_holds VALUES(?,?,?)',(key,reason,_json(detail)))

def _hold_edition(db,linked,reason,record_id,people):
    for work in linked:
        row=db.execute('SELECT title_key FROM works WHERE id=?',(work,)).fetchone()
        if row:_hold_title(db,row[0],reason,record_id,people,'edition')

def import_slice(manifest,targets,directory,*,seconds=540,max_records=1000000000):
    """One finite resumable slice; ready activation occurs only after both EOF/CRC.

    The trusted manifest is obtained from the dated official metadata endpoint,
    separately from this offline importer. No network, live catalog or worker runs.
    """
    from local_identity import title_key
    sources=validate_manifest(manifest)
    if not isinstance(targets,list) or not 0<len(targets)<=MAX_TARGETS or not all(isinstance(t,str) and 0<len(t)<=500 for t in targets):raise ValueError('Bounded explicit target title list required')
    coverage=sorted({title_key(t) for t in targets});coverage_set=set(coverage)
    if not all(coverage):raise ValueError('Empty normalized target')
    if not 0<seconds<=540 or type(max_records) is not int or not 0<max_records<=1000000000:raise ValueError('Invalid import slice bound')
    directory=Path(directory).absolute()
    if any(directory.is_relative_to(Path(source['path']).parent) for source in sources.values()):raise ValueError('Index output must be outside dump source directory')
    from native_io import DirectoryBoundary
    identity={'schema':SCHEMA,'adapter':ADAPTER,'normalization':NORMALIZATION,'targets':coverage,'manifest':manifest}
    token=_digest(identity);pending=directory/('pending-'+token+'.sqlite3');ready=directory/('index-'+token+'.sqlite3')
    deadline=time.monotonic()+seconds;processed=0
    # Existing OS advisory catalog lock has no database/worker side effects.
    from catalog_owner import catalog_lock
    with DirectoryBoundary(directory.anchor,directory,create=True) as boundary,catalog_lock(directory/'import-lock.sqlite3',{}):
        if ready.exists():
            # A previous crash may have occurred between immutable close and pointer activation.
            with _read_sqlite(ready) as (db,held):
                if db.execute('SELECT value FROM state WHERE key=?',('complete',)).fetchone()!=('true',):raise ValueError('Incomplete ready index')
                if db.execute('SELECT value FROM state WHERE key=?',('identity',)).fetchone()!=(_json(identity),):raise ValueError('Ready index provenance differs')
            return _activate(directory,ready,identity,token)
        with _owned_sqlite(pending,token,boundary) as db:
            db.executescript('CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY,value TEXT NOT NULL);CREATE TABLE IF NOT EXISTS works(id TEXT PRIMARY KEY,title TEXT NOT NULL,title_key TEXT NOT NULL,authors TEXT NOT NULL,links TEXT NOT NULL);CREATE INDEX IF NOT EXISTS works_title ON works(title_key);CREATE TABLE IF NOT EXISTS authors(id TEXT PRIMARY KEY,names TEXT NOT NULL);CREATE TABLE IF NOT EXISTS editions(id TEXT PRIMARY KEY,title TEXT NOT NULL,works TEXT NOT NULL,authors TEXT NOT NULL,isbn TEXT NOT NULL,series TEXT NOT NULL);CREATE TABLE IF NOT EXISTS edition_works(work TEXT NOT NULL,edition TEXT NOT NULL,PRIMARY KEY(work,edition));')
            db.execute('CREATE TABLE IF NOT EXISTS identity_holds(title_key TEXT PRIMARY KEY,reason TEXT NOT NULL,detail TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS unusable_authors(id TEXT PRIMARY KEY)')
            bound=db.execute('SELECT value FROM state WHERE key="identity"').fetchone()
            if bound and bound[0]!=_json(identity):raise ValueError('Pending index provenance changed')
            db.execute('INSERT OR IGNORE INTO state VALUES("identity",?)',(_json(identity),));db.commit()
            for kind in [v for v in ('works','editions','authors') if v in sources]:
                if db.execute('SELECT value FROM state WHERE key=?',(kind+'-complete',)).fetchone():continue
                expected=sources[kind];path=Path(expected['path'])
                with _source(path) as held:
                    local_sha256=_authenticate(held,expected,deadline)
                    db.execute('INSERT OR REPLACE INTO state VALUES(?,?)',(kind+'-compressed-sha256',local_sha256));db.commit()
                    db.execute('INSERT OR REPLACE INTO state VALUES(?,?)',(kind+'-source-streams',_json(held.dump_streams)));db.commit()
                    offset=db.execute('SELECT value FROM state WHERE key=?',(kind+'-offset',)).fetchone()
                    offset=int(offset[0]) if offset else 0
                    needed={person for (people,) in db.execute('SELECT authors FROM works UNION ALL SELECT authors FROM editions') for person in json.loads(people)} if kind=='authors' else None
                    work_ids={key for (key,) in db.execute('SELECT id FROM works')} if kind=='editions' else None
                    with gzip.open(path,'rb') as stream:
                        # The whole compressed stream was authenticated while held, so retained
                        # checkpoint rows cannot be mixed with a same-size changed source prefix.
                        stream.seek(offset);_check(deadline)
                        eof=False
                        while processed<max_records:
                            _check(deadline);line=stream.readline(MAX_LINE+1)
                            if not line:eof=True;break  # gzip verifies all member CRC/trailers here.
                            if len(line)>MAX_LINE or not line.endswith(b'\n'):raise ValueError('Malformed/truncated or oversized dump row')
                            parts=line.split(b'\t',4)
                            if len(parts)!=5:raise ValueError('Malformed dump columns')
                            record=json.loads(parts[4]);key=parts[1].decode('utf-8')
                            if not isinstance(record,dict) or record.get('key')!=key:raise ValueError('Dump record identity differs from row key')
                            if record.get('type',{}).get('key')=='/type/delete':continue
                            if kind=='works':
                                title=record.get('title')
                                if isinstance(title,str) and title_key(title) in coverage_set:
                                    people=record.get('authors',[])
                                    reason=''
                                    if not re.fullmatch(r'/works/OL[1-9]\d{0,11}W',key) or not isinstance(people,list) or not 0<len(people)<=8:reason='Matched work lacks complete credited author identity'
                                    authors=[]
                                    if not reason:
                                        for person in people:
                                            if not isinstance(person,dict) or person.get('role','author') not in ('author',None):reason='Qualified author relationship needs independent evidence';break
                                            author=person.get('author',{}).get('key') if isinstance(person.get('author'),dict) else None
                                            if not isinstance(author,str) or not re.fullmatch(r'/authors/OL[1-9]\d{0,11}A',author):reason='Matched author relationship lacks a supported immutable ID';break
                                            authors.append(author)
                                    if reason:
                                        _hold_title(db,title_key(title),reason,key,people,record.get('type'));processed+=1
                                        continue
                                    links=[link['url'] for link in record.get('links',[])[:20] if isinstance(link,dict) and isinstance(link.get('url'),str) and len(link['url'])<=2048] if isinstance(record.get('links',[]),list) else []
                                    value=(title,title_key(title),_json(sorted(set(authors))),_json(links))
                                    previous=db.execute('SELECT title,title_key,authors,links FROM works WHERE id=?',(key,)).fetchone()
                                    if previous and previous!=value:raise ValueError('Conflicting duplicate work')
                                    if previous or db.execute('SELECT count(*) FROM works WHERE title_key=?',(title_key(title),)).fetchone()[0]<21:
                                        db.execute('INSERT OR IGNORE INTO works VALUES(?,?,?,?,?)',(key,*value))
                            elif kind=='editions':
                                linked=record.get('works',[])
                                linked=[entry.get('key') for entry in linked if isinstance(entry,dict)] if isinstance(linked,list) else []
                                if work_ids.intersection(linked):
                                    title=record.get('title');people=record.get('authors',[])
                                    if not re.fullmatch(r'/books/OL[1-9]\d{0,11}M',key) or not isinstance(title,str) or not 0<len(title)<=500 or not isinstance(people,list) or not 0<len(people)<=8:
                                        _hold_edition(db,linked,'Matched edition lacks complete identity',key,people);processed+=1;continue
                                    converted=[entry.get('key') for entry in people if isinstance(entry,dict)]
                                    if len(converted)!=len(people) or not all(isinstance(person,str) and re.fullmatch(r'/authors/OL[1-9]\d{0,11}A',person) for person in converted):
                                        _hold_edition(db,linked,'Matched edition author IDs are unsupported',key,people);processed+=1;continue
                                    people=converted
                                    isbn=[]
                                    for prop,pattern in (('isbn_10',r'[0-9]{9}[0-9X]'),('isbn_13',r'[0-9]{13}')):
                                        entries=record.get(prop,[])
                                        if not isinstance(entries,list):raise ValueError('Malformed edition ISBNs')
                                        isbn.extend(value for value in entries[:20] if isinstance(value,str) and re.fullmatch(pattern,value))
                                    series=record.get('series',[])
                                    if not isinstance(series,list) or not all(isinstance(value,str) and len(value)<=500 for value in series) or len(series)>20:raise ValueError('Malformed edition series discovery')
                                    value=(title,_json(sorted(set(linked))),_json(sorted(set(people))),_json(sorted(set(isbn))),_json(series))
                                    previous=db.execute('SELECT title,works,authors,isbn,series FROM editions WHERE id=?',(key,)).fetchone()
                                    if previous and previous!=value:raise ValueError('Conflicting duplicate edition')
                                    # Bound sparse edition volume; unsupported excess stays explicitly incomplete.
                                    if not previous and db.execute('SELECT count(*) FROM editions').fetchone()[0]>=100000:raise ValueError('Sparse edition index bound reached; narrow targets')
                                    db.execute('INSERT OR IGNORE INTO editions VALUES(?,?,?,?,?,?)',(key,*value))
                                    db.executemany('INSERT OR IGNORE INTO edition_works VALUES(?,?)',[(work,key) for work in sorted(work_ids.intersection(linked))])
                            elif key in needed:
                                name=record.get('name');aliases=record.get('alternate_names',[])
                                if not isinstance(name,str) or not 0<len(name)<=500 or not isinstance(aliases,list) or len(aliases)>99 or not all(isinstance(value,str) and 0<len(value)<=500 for value in aliases):
                                    db.execute('INSERT OR IGNORE INTO unusable_authors VALUES(?)',(key,));processed+=1;continue
                                values=[name]+aliases
                                value=_json(values);previous=db.execute('SELECT names FROM authors WHERE id=?',(key,)).fetchone()
                                if previous and previous[0]!=value:raise ValueError('Conflicting duplicate author')
                                db.execute('INSERT OR IGNORE INTO authors VALUES(?,?)',(key,value))
                            processed+=1
                            if processed%1000==0:
                                db.execute('INSERT OR REPLACE INTO state VALUES(?,?)',(kind+'-offset',str(stream.tell())));db.commit()
                        db.execute('INSERT OR REPLACE INTO state VALUES(?,?)',(kind+'-offset',str(stream.tell())))
                        if eof:
                            if local_dump_streams(path,held.facts()['size'])!=held.dump_streams:raise ValueError('Downloaded stream inventory changed during import')
                            db.execute('INSERT OR REPLACE INTO state VALUES(?,"true")',(kind+'-complete',))
                        db.commit()
                    if not eof:return {'status':'pending','processed':processed,'source':kind,'token':token}
            needed={person for (people,) in db.execute('SELECT authors FROM works UNION ALL SELECT authors FROM editions') for person in json.loads(people)}
            missing=(needed-{key for (key,) in db.execute('SELECT id FROM authors')})|{key for (key,) in db.execute('SELECT id FROM unusable_authors')}
            if missing:
                for work,title,people in db.execute('SELECT id,title_key,authors FROM works'):
                    if missing.intersection(json.loads(people)):_hold_title(db,title,'Referenced author ID is unresolved in the authenticated author dump',work)
                for edition,linked,people in db.execute('SELECT id,works,authors FROM editions'):
                    if missing.intersection(json.loads(people)):
                        for work in json.loads(linked):
                            row=db.execute('SELECT title_key FROM works WHERE id=?',(work,)).fetchone()
                            if row:_hold_title(db,row[0],'Edition author ID is unresolved in the authenticated author dump',edition)
            if db.execute('PRAGMA quick_check').fetchall()!=[('ok',)]:raise ValueError('Index integrity check failed')
            db.execute('INSERT OR REPLACE INTO state VALUES("complete","true")');db.commit()
        from native_io import publish_no_replace
        from native_io import VerifiedFile
        with VerifiedFile(pending) as held:
            digest=held.sha256();facts=held.facts()
            if facts['links']!=1:raise ValueError('Completed index became linked')
        def same(fresh):
            if fresh['identity']!=facts['identity']:raise ValueError('Completed index identity changed before publication')
        publish_no_replace(pending,ready,boundary,expected_sha256=digest,expected_size=facts['size'],before_rename=same)
        _publish_json(ready.with_name(ready.name+'.complete.json'),{'token':token,'sha256':digest,'size':facts['size'],'identity':facts['identity']},boundary)
        return _activate(directory,ready,identity,token)

def _activate(directory,ready,identity,token):
    with _read_sqlite(ready) as (db,held):
        from native_io import VerifiedFile
        with VerifiedFile(ready.with_name(ready.name+'.complete.json')) as completed:
            if completed.facts()['links']!=1 or completed.facts()['size']>65536:raise ValueError('Index completion receipt is invalid')
            from source_cleanup import single_stream
            single_stream(completed.path);proof=json.loads(b''.join(completed.chunks()))
            digest=held.sha256();facts=held.facts()
            if proof!={'token':token,'sha256':digest,'size':facts['size'],'identity':facts['identity']}:raise ValueError('Completed index differs from immutable completion receipt')
        compressed={kind:db.execute('SELECT value FROM state WHERE key=?',(kind+'-compressed-sha256',)).fetchone()[0] for kind in identity['manifest']['sources']}
        streams={kind:json.loads(db.execute('SELECT value FROM state WHERE key=?',(kind+'-source-streams',)).fetchone()[0]) for kind in identity['manifest']['sources']}
        held_titles=[key for (key,) in db.execute('SELECT title_key FROM identity_holds ORDER BY title_key')]
    receipt={'schema':SCHEMA,'adapter':ADAPTER,'normalization':NORMALIZATION,'targets':identity['targets'],'coverage_sha256':_digest(identity['targets']),
             'held_titles':held_titles,'eligible_coverage_sha256':_digest([key for key in identity['targets'] if key not in set(held_titles)]),
             'source_manifest':identity['manifest'],'compressed_sha256':compressed,'source_streams':streams,'file':ready.name,'sha256':digest,'token':token}
    # One SQLite transaction switches the small registry. No replacement of an
    # open index or pathname rename against native ancestor guards is needed.
    from native_io import DirectoryBoundary
    with DirectoryBoundary(directory,directory) as boundary,_owned_sqlite(directory/'active.sqlite3','openlibrary-active-v1',boundary) as db:
        db.execute('CREATE TABLE IF NOT EXISTS active(id INTEGER PRIMARY KEY CHECK(id=1),receipt TEXT NOT NULL)')
        db.execute('INSERT OR REPLACE INTO active VALUES(1,?)',(_json(receipt),))
    return {'status':'ready','receipt':receipt}

def lookup(directory,title):
    """Return explicit coverage and provenance; never interpret outside coverage as no book."""
    from local_identity import title_key
    directory=Path(directory);pointer=directory/'active.sqlite3'
    if not pointer.is_file():return {'status':'unavailable','works':[]}
    try:
        with _read_sqlite(pointer) as (registry,registry_held):
            row=registry.execute('SELECT receipt FROM active WHERE id=1').fetchone()
            if not row:raise ValueError('Index activation pending')
            receipt=json.loads(row[0])
        if receipt.get('schema')!=SCHEMA or receipt.get('adapter')!=ADAPTER or receipt.get('normalization')!=NORMALIZATION or _digest(receipt['targets'])!=receipt['coverage_sha256']:raise ValueError('Index coverage changed')
        key=title_key(title)
        if key not in receipt['targets']:return {'status':'outside_coverage','works':[]}
        filename=receipt['file']
        if not re.fullmatch(r'index-[a-f0-9]{64}\.sqlite3',filename):raise ValueError('Invalid index generation')
        path=directory/filename
        from native_io import DirectoryBoundary,VerifiedFile
        with DirectoryBoundary(directory,directory),VerifiedFile(path) as held:
            if held.sha256()!=receipt['sha256']:raise ValueError('Activated index bytes changed')
            with contextlib.closing(sqlite3.connect('file:'+path.as_posix()+'?mode=ro&immutable=1',uri=True)) as db:
                hold=db.execute('SELECT reason,detail FROM identity_holds WHERE title_key=?',(key,)).fetchone()
                if hold:return {'status':'identity_incomplete','works':[],'reason':hold[0],'detail':json.loads(hold[1]),'receipt':receipt}
                works=[]
                for id,shown,people,links in db.execute('SELECT id,title,authors,links FROM works WHERE title_key=? LIMIT 21',(key,)):
                    authors=[]
                    for person in json.loads(people):
                        found=db.execute('SELECT names FROM authors WHERE id=?',(person,)).fetchone()
                        if not found:raise ValueError('Activated index author missing')
                        authors.append({'id':person,'names':json.loads(found[0])})
                    editions=[]
                    for edition,edition_title,isbn,series in db.execute('SELECT e.id,e.title,e.isbn,e.series FROM edition_works w JOIN editions e ON e.id=w.edition WHERE w.work=? LIMIT 101',(id,)):
                        editions.append({'id':edition,'title':edition_title,'isbn':json.loads(isbn),'series_discovery':json.loads(series),'narrative_order_verified':False})
                    if len(editions)>100:raise ValueError('Edition lookup bound reached')
                    works.append({'id':id,'title':shown,'authors':authors,'links':json.loads(links),'editions':editions})
                if len(works)>20:return {'status':'ambiguous','works':[]}
        return {'status':'covered','works':works,'receipt':receipt}
    except (ValueError,KeyError,TypeError,OSError,sqlite3.Error):return {'status':'invalid','works':[]}

def generation(directory):
    """Cheap negative-result binding; absence/busy never proves a new generation."""
    pointer=Path(directory)/'active.sqlite3'
    if not pointer.is_file():return None
    try:
        with _read_sqlite(pointer) as (registry,held):
            row=registry.execute('SELECT receipt FROM active WHERE id=1').fetchone()
            receipt=json.loads(row[0]) if row else {}
            token=receipt.get('token')
            return token if receipt.get('adapter')==ADAPTER and isinstance(token,str) and re.fullmatch('[a-f0-9]{64}',token) else None
    except (ValueError,KeyError,TypeError,OSError,sqlite3.Error):return None

if __name__=='__main__':
    # The bundled isolated Python deliberately omits the script directory.
    # The owned invocation pins this script and its sibling implementation files.
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',required=True);parser.add_argument('--targets',required=True);parser.add_argument('--directory',required=True);parser.add_argument('--seconds',type=float,default=540);parser.add_argument('--include-editions',action='store_true')
    args=parser.parse_args()
    manifest=json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    if args.include_editions:manifest['sources']['editions']=manifest['pending_editions']
    # Console code pages may not encode every retained title. Escape only the
    # reporting transport; index/receipt serialization and Unicode stay intact.
    print(json.dumps(import_slice(manifest,json.loads(Path(args.targets).read_text(encoding='utf-8')),args.directory,seconds=args.seconds),ensure_ascii=True,sort_keys=True,separators=(',',':')))
