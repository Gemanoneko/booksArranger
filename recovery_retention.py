"""Original-track recovery sets: deleted as soon as the book's output is verified (v0.16.8).

Sergei, 2026-10-18: once the converted audiobook is verified and each original's content matched what was
checked, the app removes all backups of that book. The 24-hour window is gone: a new set's deadline is its
completion time, and sets recorded with the former 24-hour deadline are purged too. Purge verifies the
output in full first; a missing or unverified output keeps the copies, flagged with the reason.

"Keep files" is permanent (Sergei, 2026-10-18): a book recorded in kept_files is left out of every automatic
purge until Sergei acts on it again; the manual "Delete recovery copies" is such an action.
"""
import contextlib
import hashlib
import json
import stat
from datetime import datetime, timezone, timedelta
from pathlib import Path
from scanner import connect
from source_cleanup import packed
from native_io import BoundaryError, DirectoryBoundary, ordinary

HOURS=0         # deadline for new sets: purged as soon as the output is verified
LEGACY_HOURS=24 # deadline recorded by 0.16.7 and earlier; still a valid immutable deadline

def utc():return datetime.now(timezone.utc)
def moment(value):
    parsed=datetime.fromisoformat(value)
    if parsed.tzinfo is None:raise ValueError('Recovery completion time has no timezone')
    return parsed.astimezone(timezone.utc)

AUDIOBOOK_MISSING='Audiobook missing: '
AUDIOBOOK_UNVERIFIED='Audiobook not verified: '

def kept_reason(error):
    """The reason a purge kept a set. A missing or unverified audiobook is the 0.16.8 keep-case (B), told
    apart by a fixed prefix so the attention groups never parse English messages."""
    text=str(error) or type(error).__name__
    if isinstance(error,FileNotFoundError) or 'cannot find' in text.lower() or 'Completed output destination changed' in text:return AUDIOBOOK_MISSING+text
    if 'Completed output' in text or 'Retention output identity changed' in text:return AUDIOBOOK_UNVERIFIED+text
    return text

def moved(member):
    """A 0.21.0 in-place original: retired by its journaled rename into the output, never copied to recovery."""
    try:return json.loads(member['facts'] or '{}').get('disposition')=='renamed_into_output' and member['state']=='removed'
    except (ValueError,TypeError,AttributeError):return False

KEPT_FILES_TABLE='CREATE TABLE IF NOT EXISTS kept_files(job_id TEXT PRIMARY KEY,kept_at TEXT NOT NULL)'

def kept_by_choice(db,job_ids=None):
    """Job ids whose files Sergei chose to keep. Read-only: the table exists once Keep files was pressed."""
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='kept_files'").fetchone():return set()
    if job_ids is None:return {row[0] for row in db.execute('SELECT job_id FROM kept_files')}
    return {row[0] for row in db.execute('SELECT job_id FROM kept_files WHERE job_id IN (SELECT value FROM json_each(?))',(json.dumps(list(job_ids)),))}

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
                if members and all(moved(r) for r in members):
                    # 0.21.0 in-place edit: the original became the output; no recovery copy ever existed.
                    db.execute('INSERT INTO recovery_retention VALUES(?,?,?,?,?,?,?,?,?)',(row['job_id'],row['id'],output['sha256'],completed,completed,'deleted','','in_place',completed))
                    continue
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
            if moved(member):removed+=1;continue  # nothing was ever copied for an in-place original
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
        """Every set not yet deleted: retained, partly deleted, or held. Purge decides; there is no waiting.
        A book whose files Sergei chose to keep is never due."""
        # A set without a recorded completion cannot prove its deadline: it stays, flagged.
        with connect(self.database) as db:
            kept=kept_by_choice(db)
            rows=db.execute("SELECT job_id FROM recovery_retention WHERE state IN ('retained','deleting','needs_attention') AND completed_at<>'' ORDER BY completed_at,job_id").fetchall()
        return [row['job_id'] for row in rows if row['job_id'] not in kept]

    def kept(self,job_id):
        """True once Sergei pressed Keep files for this book: no automatic purge touches it."""
        with connect(self.database) as db:return job_id in kept_by_choice(db,[job_id])

    def _set(self,job_id,state,reason='',actor=None):
        with connect(self.database) as db:
            db.execute('UPDATE recovery_retention SET state=?,reason=? WHERE job_id=?',(state,reason,job_id))
            if actor is not None:db.execute('UPDATE recovery_retention SET actor=? WHERE job_id=?',(actor,job_id))
            if state=='deleted':db.execute('UPDATE recovery_retention SET deleted_at=? WHERE job_id=?',(self.clock().isoformat(),job_id))

    def purge(self,job_id,actor='automatic',confirmation=None):
        persisted=self._rows('SELECT * FROM recovery_retention WHERE job_id=?',(job_id,))
        if persisted and persisted[0]['state']=='deleted':return self.status(job_id)  # idempotent: never twice
        if actor=='automatic' and self.kept(job_id):return self.status(job_id)  # Keep files: kept until Sergei acts again
        status=self.status(job_id)
        if confirmation is not None and any(status.get(k)!=confirmation.get(k) for k in ('token','count','bytes')):raise ValueError('Recovery copies changed. Review the updated details and try again.')
        if not persisted:raise BoundaryError(status.get('reason') or 'Recovery copies are not eligible')
        # No deadline and no idle wait: the full output verification below is the gate. A set held only
        # because a copy is already gone is purged too; a missing copy is recorded, never an error.
        row=persisted[0]
        try:
            with self.storage.protected_output(job_id,guard=self.guard) as (manifest,output),contextlib.ExitStack() as stack:
                if output['sha256']!=row['output_hash']:raise BoundaryError('Retention output identity changed')
                events=self._rows('SELECT completed_at FROM recovery_completion WHERE cleanup_id=?',(row['cleanup_id'],))
                deadlines={(moment(row['completed_at'])+timedelta(hours=hours)).isoformat() for hours in (HOURS,LEGACY_HOURS)} if events else set()
                if not events or events[0]['completed_at']!=row['completed_at'] or row['expires_at'] not in deadlines:raise BoundaryError('Immutable recovery completion deadline changed')
                cleanup,members=self.storage._source_safety(stack,job_id,manifest,output)
                if not cleanup or cleanup['id']!=row['cleanup_id']:raise BoundaryError('Recovery cleanup identity changed')
                location=ordinary(self.storage.recovery_root/cleanup['id'])
                present=True
                try:location.lstat()
                except FileNotFoundError:present=False  # every copy is already gone: recorded below
                if present:
                    stack.enter_context(DirectoryBoundary(self.storage.recovery_root.anchor,location))
                    names={Path(r['backup']).name for r in members}
                    if any(p.name not in names for p in location.iterdir()):raise BoundaryError('Unknown recovery content preserved')
                prepared=[]
                for source in manifest['sources']:
                    member=next(r for r in members if r['path']==source['path']);path=ordinary(member['backup'])
                    if path.parent!=location:raise BoundaryError('Recovery native correspondence is unavailable')
                    expected=(source['sha256'],source['size'],source['modified'])
                    try:path.lstat()
                    except FileNotFoundError:
                        self.storage.record_absent(job_id,'recovery',path,expected);continue  # already gone
                    # Content proof in _prepare (full hash against the reviewed original) is what allows the
                    # removal; the recorded native identity, when there is one, must still match.
                    item=self.storage._prepare(stack,job_id,'recovery',path,self.storage.recovery_root,expected)
                    if item:
                        if member['backup_facts'] and item[1].facts()!=json.loads(member['backup_facts']):raise BoundaryError('Recovery native identity changed; replacement preserved')
                        prepared.append(item)
                self._set(job_id,'deleting',actor=row['actor'] or actor)
                self.storage._dispose(prepared,guard=self.guard)
            self._set(job_id,'deleted',actor=row['actor'] or actor)
            try:location.rmdir()  # the emptied set folder; anything left in it stays
            except OSError:pass
        except InterruptedError:
            raise # Cooperative shutdown preserves deleting intent for restart reconciliation.
        except Exception as error:
            self._set(job_id,'needs_attention',kept_reason(error));raise
        return self.status(job_id)
