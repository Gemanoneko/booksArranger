"""Bounded 24-hour retention of registered original-track recovery sets."""
import contextlib
import hashlib
import json
import stat
from datetime import datetime, timezone, timedelta
from pathlib import Path
from scanner import connect
from source_cleanup import packed
from native_io import BoundaryError, DirectoryBoundary, ordinary

HOURS=24

def utc():return datetime.now(timezone.utc)
def moment(value):
    parsed=datetime.fromisoformat(value)
    if parsed.tzinfo is None:raise ValueError('Recovery completion time has no timezone')
    return parsed.astimezone(timezone.utc)

class RecoveryRetention:
    def __init__(self,storage,clock=utc,guard=None):
        self.storage=storage;self.database=storage.database;self.clock=clock;self.guard=guard or storage.guard
        with connect(self.database) as db:
            db.execute('CREATE TABLE IF NOT EXISTS recovery_retention(job_id TEXT PRIMARY KEY,cleanup_id TEXT UNIQUE,output_hash TEXT,completed_at TEXT,expires_at TEXT,state TEXT,reason TEXT,actor TEXT,deleted_at TEXT)')
        self.sync()

    def sync(self):
        # Called at construction or durable source completion, never by GET polling.
        with connect(self.database) as db:
            rows=[dict(r) for r in db.execute("SELECT * FROM source_cleanup WHERE state='completed'")]
            for row in rows:
                if db.execute('SELECT 1 FROM recovery_retention WHERE job_id=?',(row['job_id'],)).fetchone():continue
                members=[dict(r) for r in db.execute('SELECT * FROM cleanup_members WHERE cleanup_id=?',(row['id'],))]
                intent=json.loads(row['intent']);output=intent['output']
                prior=[dict(r) for r in db.execute("SELECT * FROM storage_cleanup_files WHERE job_id=? AND kind='recovery'",(row['job_id'],))]
                deleted=bool(members) and len(prior)==len(members) and all(r['state'] in ('removed','absent_after_intent') for r in prior) and not any(Path(r['backup']).exists() for r in members)
                event=db.execute('SELECT completed_at FROM recovery_completion WHERE cleanup_id=?',(row['id'],)).fetchone()
                completed=event[0] if event else ''
                reason='';expires=''
                try:
                    expires=(moment(completed)+timedelta(hours=HOURS)).isoformat()
                    if not members or any(r['state']!='removed' for r in members):raise ValueError('Original-track retirement is incomplete')
                    if not deleted and any(not r['backup_facts'] for r in members):raise ValueError('Legacy recovery native identity is unavailable; copies preserved')
                except (ValueError,KeyError,TypeError):reason='Recovery completion or native identity is unavailable; copies preserved'
                state='deleted' if deleted else 'needs_attention' if reason else 'retained'
                deleted_at=next((r['updated'] for r in prior),'') if deleted else ''
                db.execute('INSERT INTO recovery_retention VALUES(?,?,?,?,?,?,?,?,?)',(row['job_id'],row['id'],output['sha256'],completed,expires,state,reason,'legacy' if deleted else '',deleted_at))

    def _rows(self,sql,params=()):
        with connect(self.database) as db:return [dict(r) for r in db.execute(sql,params)]

    def status(self,job_id):
        rows=self._rows('SELECT * FROM recovery_retention WHERE job_id=?',(job_id,))
        if not rows:return {'state':'unavailable','eligible':False,'reason':'Successful source cleanup is required','count':None,'bytes':None,'location':'','token':'','total':None,'removed':None,'expires_at':''}
        row=rows[0];members=self._rows('SELECT * FROM cleanup_members WHERE cleanup_id=?',(row['cleanup_id'],))
        receipts={r['path']:r for r in self._rows("SELECT * FROM storage_cleanup_files WHERE job_id=? AND kind='recovery'",(job_id,))}
        count=0;size=0;removed=0;facts=[];uncertain=False
        for member in members:
            path=Path(member['backup']);receipt=receipts.get(str(path))
            try:
                value=path.lstat()
                if not stat.S_ISREG(value.st_mode) or getattr(value,'st_file_attributes',0) & 0x400:raise OSError('Reparse recovery entry')
                count+=1;size+=value.st_size;facts.append([str(path),value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns])
                if receipt and receipt['state'] in ('removed','absent_after_intent'):uncertain=True
            except FileNotFoundError:
                if receipt and receipt['state'] in ('removed','absent_after_intent','disposition_set'):removed+=1
                else:uncertain=True
            except OSError:uncertain=True
        state=row['state'];reason=row['reason']
        source=self._rows('SELECT state FROM source_cleanup WHERE id=?',(row['cleanup_id'],))
        if not source or source[0]['state']!='completed':uncertain=True;reason='Original-track recovery or cleanup requires attention'
        if uncertain:state='needs_attention';reason=reason or 'Recovery copies changed or are unavailable; preserved for attention'
        if state=='deleted' and count:state='needs_attention';reason='Replacement files at a discarded recovery location were preserved'
        eligible=state=='retained' and count==len(members) and bool(count)
        token=hashlib.sha256(packed([row,facts,count,size]).encode()).hexdigest()
        return row|{'state':state,'reason':reason,'eligible':eligible,'count':None if uncertain else count,'bytes':None if uncertain else size,'location':str(self.storage.recovery_root/row['cleanup_id']), 'token':token,'total':len(members),'removed':removed}

    def due(self):
        result=[]
        for row in self._rows("SELECT * FROM recovery_retention WHERE state IN ('retained','deleting')"):
            try:
                if row['state']=='deleting' or self.clock()>=moment(row['expires_at']):result.append(row['job_id'])
            except (ValueError,TypeError):pass
        return result

    def _set(self,job_id,state,reason='',actor=None):
        with connect(self.database) as db:
            db.execute('UPDATE recovery_retention SET state=?,reason=? WHERE job_id=?',(state,reason,job_id))
            if actor is not None:db.execute('UPDATE recovery_retention SET actor=? WHERE job_id=?',(actor,job_id))
            if state=='deleted':db.execute('UPDATE recovery_retention SET deleted_at=? WHERE job_id=?',(self.clock().isoformat(),job_id))

    def purge(self,job_id,actor='automatic',confirmation=None):
        status=self.status(job_id)
        if status['state']=='deleted':return status
        if confirmation is not None and any(status.get(k)!=confirmation.get(k) for k in ('token','count','bytes')):raise ValueError('Recovery copies changed. Review the updated details and try again.')
        persisted=self._rows('SELECT * FROM recovery_retention WHERE job_id=?',(job_id,))
        reconciling=bool(persisted and persisted[0]['state']=='deleting')
        if status['state'] not in ('retained','deleting') and not reconciling:raise BoundaryError(status.get('reason') or 'Recovery copies are not eligible')
        if actor=='automatic' and not reconciling and self.clock()<moment(status['expires_at']):return status
        row=self._rows('SELECT * FROM recovery_retention WHERE job_id=?',(job_id,))[0]
        try:
            with self.storage.protected_output(job_id,guard=self.guard) as (manifest,output),contextlib.ExitStack() as stack:
                if output['sha256']!=row['output_hash']:raise BoundaryError('Retention output identity changed')
                events=self._rows('SELECT completed_at FROM recovery_completion WHERE cleanup_id=?',(row['cleanup_id'],))
                if not events or events[0]['completed_at']!=row['completed_at'] or (moment(row['completed_at'])+timedelta(hours=HOURS)).isoformat()!=row['expires_at']:raise BoundaryError('Immutable recovery completion deadline changed')
                cleanup,members=self.storage._source_safety(stack,job_id,manifest,output)
                if not cleanup or cleanup['id']!=row['cleanup_id']:raise BoundaryError('Recovery cleanup identity changed')
                location=ordinary(self.storage.recovery_root/cleanup['id'])
                stack.enter_context(DirectoryBoundary(self.storage.recovery_root.anchor,location))
                names={Path(r['backup']).name for r in members}
                if any(p.name not in names for p in location.iterdir()):raise BoundaryError('Unknown recovery content preserved')
                prepared=[]
                for source in manifest['sources']:
                    member=next(r for r in members if r['path']==source['path']);path=ordinary(member['backup'])
                    if path.parent!=location or not member['backup_facts']:raise BoundaryError('Recovery native correspondence is unavailable')
                    item=self.storage._prepare(stack,job_id,'recovery',path,self.storage.recovery_root,(source['sha256'],source['size'],source['modified']))
                    if item:
                        if item[1].facts()!=json.loads(member['backup_facts']):raise BoundaryError('Recovery native identity changed; replacement preserved')
                        prepared.append(item)
                self._set(job_id,'deleting',actor=row['actor'] or actor)
                self.storage._dispose(prepared,guard=self.guard)
            self._set(job_id,'deleted')
        except InterruptedError:
            raise # Cooperative shutdown preserves deleting intent for restart reconciliation.
        except Exception as error:
            self._set(job_id,'needs_attention',str(error));raise
        return self.status(job_id)
