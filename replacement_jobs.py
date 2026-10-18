"""Exact approved successor relationships. Media/history are never rewritten."""
import contextlib
import copy
import hashlib
import json
import threading
from datetime import datetime, timezone
from scanner import connect
from sqlite_retry import transaction

STATES={'queued','published','retiring','completed'}

def packed(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)

def digest(value):
    return hashlib.sha256(packed(value).encode('utf-8')).hexdigest()

def now():return datetime.now(timezone.utc).isoformat()

class Replacements:
    def __init__(self,database):
        self.database=database
        with connect(database) as db:
            db.execute('CREATE TABLE IF NOT EXISTS audiobook_replacements(id TEXT PRIMARY KEY,parent_job_id TEXT UNIQUE NOT NULL,replacement_job_id TEXT UNIQUE NOT NULL,candidate_id TEXT UNIQUE NOT NULL,candidate_revision INTEGER NOT NULL,parent_record_sha256 TEXT NOT NULL,previous_publication_json TEXT NOT NULL,approval_json TEXT NOT NULL,state TEXT NOT NULL,current_output_json TEXT NOT NULL DEFAULT \'\',failure_json TEXT NOT NULL DEFAULT \'\',created TEXT NOT NULL,updated TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS audiobook_replacement_retirements(replacement_id TEXT NOT NULL,original_path TEXT NOT NULL,provenance_json TEXT NOT NULL,recovery_json TEXT NOT NULL DEFAULT \'\',state TEXT NOT NULL,reason TEXT NOT NULL DEFAULT \'\',updated TEXT NOT NULL,PRIMARY KEY(replacement_id,original_path))')

    def _status_local(self):
        return self.__dict__.setdefault('_status_rows',threading.local())

    def rows(self):
        cached=getattr(self._status_local(),'rows',None)
        if cached is not None:return [dict(row) for row in cached]
        with connect(self.database) as db:return [dict(row) for row in db.execute('SELECT * FROM audiobook_replacements ORDER BY created,id')]

    @contextlib.contextmanager
    def snapshot(self):
        """Read-only status computation: one consistent relation read on this thread instead of one per lookup."""
        local=self._status_local()
        if getattr(local,'rows',None) is not None:
            yield;return
        local.rows=self.rows()
        try:yield
        finally:local.rows=None

    def get(self,*,candidate=None,new_job=None,parent=None):
        matches=[r for r in self.rows() if (candidate is None or r['candidate_id']==candidate) and (new_job is None or r['replacement_job_id']==new_job) and (parent is None or r['parent_job_id']==parent)]
        if len(matches)>1:raise ValueError('Ambiguous replacement relation')
        return matches[0] if matches else None

    def files(self,id):
        with connect(self.database) as db:return [dict(r) for r in db.execute('SELECT * FROM audiobook_replacement_retirements WHERE replacement_id=? ORDER BY original_path',(id,))]

    @staticmethod
    def raw_job(db,id):
        row=db.execute('SELECT * FROM audio_jobs WHERE job_id=?',(id,)).fetchone()
        if not row:raise ValueError('Replacement history job unavailable')
        return dict(row)

    def admission(self,db,manifest,binding):
        """Called in the SAME transaction immediately before new AudioJobs insert."""
        expected=binding['parent_row'];approval=binding['approval'];previous=binding['previous_publication']
        parent=self.raw_job(db,expected['job_id'])
        if parent!=expected or parent['state']!='completed':raise ValueError('Original completed record changed')
        if manifest['job_id']==parent['job_id']:raise ValueError('A replacement needs its own job identity')
        old=json.loads(parent['manifest'])
        if (manifest.get('replacement_parent_job_id')!=parent['job_id'] or manifest.get('replacement_id')!=binding['id'] or
                manifest['candidate_id']!=old['candidate_id'] or manifest['candidate_revision']!=old['candidate_revision'] or
                manifest['metadata']!=old['metadata'] or manifest['sources']!=old['sources'] or manifest['cover']!=old['cover']):
            raise ValueError('Replacement source/review lineage changed')
        if manifest.get('cleanup_policy',{}).get('enabled'):raise ValueError('Original replacement sources must remain')
        if manifest['destination']!=approval['destination'] or manifest['profile']!=approval['profile']:raise ValueError('Replacement plan changed')
        if manifest!=approval.get('replacement_manifest'):raise ValueError('Complete replacement manifest is not frozen by admission')
        group=db.execute('SELECT * FROM book_groups WHERE id=?',(manifest['candidate_id'],)).fetchone()
        context=db.execute('SELECT * FROM candidate_context WHERE id=?',(manifest['candidate_id'],)).fetchone()
        if not group or not context or dict(group)!=approval['group_row'] or dict(context)!=approval['context_row']:
            raise ValueError('Replacement approval context changed')
        existing=db.execute('SELECT * FROM audiobook_replacements WHERE candidate_id=?',(manifest['candidate_id'],)).fetchone()
        if existing:raise ValueError('Candidate already has an explicit replacement')
        timestamp=binding['timestamp']
        db.execute('INSERT INTO audiobook_replacements VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (binding['id'],parent['job_id'],manifest['job_id'],manifest['candidate_id'],manifest['candidate_revision'],digest(parent),packed(previous),packed(approval),'queued','','',timestamp,timestamp))
        old_files=approval['old_outputs']
        if len(old_files)!=3 or len({f['path'] for f in old_files})!=3:raise ValueError('Exact three old outputs required')
        for file in old_files:
            db.execute('INSERT INTO audiobook_replacement_retirements VALUES(?,?,?,?,?,?,?)',(binding['id'],file['path'],packed(file),'','waiting','',timestamp))

    @staticmethod
    def cas(db,table,expected,changes,keys):
        columns=list(expected)
        where=' AND '.join(f'{key} IS ?' for key in columns)
        update=','.join(f'{key}=?' for key in changes)
        # Table/column names are constant caller-owned schema, never user text.
        count=db.execute(f'UPDATE {table} SET {update} WHERE {where}',(*changes.values(),*expected.values())).rowcount
        if count!=1:raise ValueError('Replacement receipt changed during guarded transition')

    def publish(self,expected,new_row,output,storage_row,verify):
        """Caller freshly verified media/native/journal; callbacks never do filesystem work here."""
        if expected['state']!='queued':
            if expected['state'] in {'published','retiring','completed'} and json.loads(expected['current_output_json'])==output:return expected
            raise ValueError('Replacement publication state changed')
        approval=json.loads(expected['approval_json'])
        if new_row['job_id']!=expected['replacement_job_id'] or new_row['state']!='completed':raise ValueError('Replacement job incomplete')
        manifest=json.loads(new_row['manifest']);journal=json.loads(new_row['journal'])
        if manifest.get('replacement_id')!=expected['id'] or manifest.get('replacement_parent_job_id')!=expected['parent_job_id']:raise ValueError('Replacement job lineage changed')
        if output!=json.loads(new_row['output']) or not self.validated_output(manifest,output):raise ValueError('Replacement validation changed')
        if journal.get('publication_intent')!=output or not any(item.get('stage')=='publishing' and item.get('details')==output for item in journal.get('history',[])):
            raise ValueError('Replacement publication intent unavailable')
        if storage_row.get('job_id')!=new_row['job_id'] or storage_row.get('state')!='completed':raise ValueError('Replacement staging cleanup incomplete')
        if output['final_path']!=approval['destination'] or manifest.get('cleanup_policy',{}).get('enabled'):raise ValueError('Replacement destination/source preservation changed')
        if verify is not True:raise ValueError('Fresh replacement native proof required')
        with connect(self.database) as db:
            db.execute('BEGIN IMMEDIATE')
            if self.raw_job(db,new_row['job_id'])!=new_row:raise ValueError('Completed replacement changed')
            parent=self.raw_job(db,expected['parent_job_id'])
            if digest(parent)!=expected['parent_record_sha256']:raise ValueError('Historical parent changed')
            self._bound_manifest(expected,parent,new_row)
            for table,key,row in [('book_groups','id',approval['group_row']),('candidate_context','id',approval['context_row']),('storage_cleanup_jobs','job_id',storage_row)]:
                current=db.execute(f'SELECT * FROM {table} WHERE {key}=?',(row[key],)).fetchone()
                if not current or dict(current)!=row:raise ValueError('Publication approval or cleanup changed')
            owned=db.execute('SELECT * FROM owned_artifacts WHERE path=?',(output['final_path'],)).fetchone()
            values=(output['final_path'],new_row['job_id'],'output',output['sha256'],output['size'])
            if owned and tuple(owned)!=values:raise ValueError('Replacement output ownership conflict')
            if not owned:db.execute('INSERT INTO owned_artifacts VALUES(?,?,?,?,?)',values)
            self.cas(db,'audiobook_replacements',expected,{'state':'published','current_output_json':packed(output),'updated':now()},('id',))
        return self.get(new_job=new_row['job_id'])

    @staticmethod
    def _bound_manifest(relation,parent,new):
        old=json.loads(parent['manifest']);manifest=json.loads(new['manifest']);approval=json.loads(relation['approval_json'])
        if (digest(parent)!=relation['parent_record_sha256'] or digest(manifest)!=new['manifest_hash'] or
                parent['job_id']!=relation['parent_job_id'] or new['job_id']!=relation['replacement_job_id'] or parent['job_id']==new['job_id'] or
                manifest!=approval.get('replacement_manifest') or manifest.get('replacement_id')!=relation['id'] or
                manifest.get('replacement_parent_job_id')!=parent['job_id'] or manifest.get('job_id')!=new['job_id'] or
                manifest.get('candidate_id')!=relation['candidate_id'] or manifest.get('candidate_revision')!=relation['candidate_revision'] or
                manifest.get('candidate_id')!=old.get('candidate_id') or manifest.get('candidate_revision')!=old.get('candidate_revision') or
                any(manifest.get(key)!=old.get(key) for key in ('metadata','sources','cover','root')) or
                manifest.get('sources')!=approval.get('sources') or manifest.get('destination')!=approval.get('destination') or
                manifest.get('profile')!=approval.get('profile') or manifest.get('cleanup_policy')):
            raise ValueError('Replacement manifest lineage or frozen content changed')
        return manifest

    @staticmethod
    def validated_output(manifest,output):
        validation=output.get('validation',{});tags=validation.get('tags',{});media=validation.get('replacement_media',{})
        if (validation.get('passed') is not True or validation.get('checks')!='Output checks passed' or
                validation.get('profile')!=manifest.get('profile') or validation.get('sha256')!=output.get('sha256') or validation.get('size')!=output.get('size') or
                tags.get('title')!=manifest['metadata'].get('title') or tags.get('artist')!=manifest['metadata'].get('canonical_author') or str(tags.get('media_type'))!='2' or
                media.get('actual_tags')!=tags or media.get('actual_audio',{}).get('codec_name')!='aac' or
                str(media.get('actual_audio',{}).get('channels'))!='1' or str(media.get('actual_audio',{}).get('sample_rate'))!='44100'):
            return False
        if [item.get('title') for item in validation.get('chapters',[])]!=manifest.get('chapters',[]):return False
        return True

    def structural_guard(self,relation,historical=False,queued=False):
        """One non-recursive verdict for metadata, Ready, retirement and startup history."""
        try:
            with connect(self.database) as db:
                current=db.execute('SELECT * FROM audiobook_replacements WHERE id=?',(relation['id'],)).fetchone()
                if not current or dict(current)!=relation:return False
                parent=self.raw_job(db,relation['parent_job_id']);new=self.raw_job(db,relation['replacement_job_id'])
                manifest=self._bound_manifest(relation,parent,new);approval=json.loads(relation['approval_json'])
                if not historical:
                    for table,row in [('book_groups',approval['group_row']),('candidate_context',approval['context_row'])]:
                        value=db.execute(f'SELECT * FROM {table} WHERE id=?',(row['id'],)).fetchone()
                        if not value or dict(value)!=row:return False
                if relation['state']=='queued':return bool(queued)
                if relation['state'] not in {'published','retiring','completed'} or new['state']!='completed':return False
                output=json.loads(new['output'] or '{}');journal=json.loads(new['journal'])
                if (output!=json.loads(relation['current_output_json']) or output.get('job_id')!=new['job_id'] or
                        output.get('final_path')!=manifest['destination'] or not self.validated_output(manifest,output) or
                        journal.get('publication_intent')!=output or not any(item.get('stage')=='publishing' and item.get('details')==output for item in journal.get('history',[]))):return False
                storage=db.execute('SELECT * FROM storage_cleanup_jobs WHERE job_id=?',(new['job_id'],)).fetchone()
                if not storage or storage['state']!='completed' or storage['output_hash']!=output['sha256']:return False
                owned=db.execute('SELECT * FROM owned_artifacts WHERE path=?',(output['final_path'],)).fetchone()
                if not owned or tuple(owned)!=(output['final_path'],new['job_id'],'output',output['sha256'],output['size']):return False
                return True
        except (ValueError,OSError,KeyError,TypeError):return False

    def transition(self,expected,state):
        allowed={'published':{'retiring'},'retiring':{'completed'}}
        if state not in allowed.get(expected['state'],set()):raise ValueError('Non-monotonic replacement transition')
        if state=='completed' and (len(self.files(expected['id']))!=3 or any(r['state']!='removed' for r in self.files(expected['id']))):raise ValueError('Old output retirement is incomplete')
        changes={'state':state,'updated':now()}
        transaction(self.database,lambda db:self.cas(db,'audiobook_replacements',expected,changes,('id',)))
        return self.get(new_job=expected['replacement_job_id'])

    def file_transition(self,expected,state,recovery=None):
        allowed={'waiting':{'copied'},'copied':{'retirement_intended'},'retirement_intended':{'removed'}}
        if state not in allowed.get(expected['state'],set()):raise ValueError('Non-monotonic old-output retirement')
        changes={'state':state,'updated':now()}
        if recovery is not None:changes['recovery_json']=packed(recovery)
        transaction(self.database,lambda db:self.cas(db,'audiobook_replacement_retirements',expected,changes,('replacement_id','original_path')))
        return next(r for r in self.files(expected['replacement_id']) if r['original_path']==expected['original_path'])

    def file_purged(self,expected,recovery):
        """A removed former output's recovery copy was deleted (or found gone) after the replacement was
        verified: the record keeps state 'removed' and gains purged_at; history no longer needs the copy."""
        if expected['state']!='removed':raise ValueError('Only a retired former output has a recovery copy to purge')
        changes={'recovery_json':packed(recovery),'updated':now()}
        transaction(self.database,lambda db:self.cas(db,'audiobook_replacement_retirements',expected,changes,('replacement_id','original_path')))
        return next(r for r in self.files(expected['replacement_id']) if r['original_path']==expected['original_path'])

    def copy_intent(self,expected,recovery):
        if expected['state']!='waiting' or expected['recovery_json']:raise ValueError('Recovery copy intent already exists')
        changes={'recovery_json':packed(recovery),'updated':now()}
        transaction(self.database,lambda db:self.cas(db,'audiobook_replacement_retirements',expected,changes,('replacement_id','original_path')))
        return next(r for r in self.files(expected['replacement_id']) if r['original_path']==expected['original_path'])

    def failure(self,expected,error,phase):
        failure={'type':type(error).__name__,'message':str(error),'phase':phase,'at':now()}
        changes={'failure_json':packed(failure),'updated':now()}
        transaction(self.database,lambda db:self.cas(db,'audiobook_replacements',expected,changes,('id',)))

    def representative(self,jobs,candidate):
        relation=self.get(candidate=candidate)
        if relation and relation['state'] in {'published','retiring','completed'}:
            return next((j for j in jobs if j['job_id']==relation['replacement_job_id']),None),relation
        matches=[j for j in jobs if j['manifest']['candidate_id']==candidate and not j['manifest'].get('replacement_id')]
        return (matches[-1] if matches else None),relation

    def projected(self,jobs,current_id=None):
        """Visible progress selects active replacement; durable completion counts candidates once."""
        completed={j['manifest']['candidate_id'] for j in jobs if j['state']=='completed'}
        result=[]
        for candidate in dict.fromkeys(j['manifest']['candidate_id'] for j in jobs):
            active=next((j for j in jobs if j['manifest']['candidate_id']==candidate and j['job_id']==current_id),None)
            representative,_=self.representative(jobs,candidate)
            pending=next((j for j in reversed(jobs) if j['manifest']['candidate_id']==candidate and j['state'] in {'pending','needs attention'}),None)
            selected=active or pending or representative
            if selected:result.append(copy.deepcopy(selected))
        return result,len(completed)
