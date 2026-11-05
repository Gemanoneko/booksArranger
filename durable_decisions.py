"""Durable book-local decisions, separate from conversion/disposal authority.

Acceptance stores bounded immutable intent without taking worker locks. Application
uses the existing consumers and records each effect in that consumer's transaction.
No method in this module opens a source/output file or starts an audiobook worker.
"""
import copy
import datetime
import hashlib
import json
import uuid

from scanner import connect

SCHEMA='books-durable-decision-v1'
ACTIONS=frozenset(('names','approve','review','metadata_choices','tracks','file_review'))
MAX_PAYLOAD=64*1024
MAX_EFFECTS=128
MAX_PENDING=1000


class DecisionChanged(ValueError):
    code='decision_changed'


def packed(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def digest(value):return hashlib.sha256(packed(value).encode('utf-8')).hexdigest()


def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()


def setup(db):
    db.execute('''CREATE TABLE IF NOT EXISTS book_decisions(
      request_id TEXT PRIMARY KEY,book_id TEXT NOT NULL,action TEXT NOT NULL,seq INTEGER NOT NULL,
      predecessor TEXT,observed_revision INTEGER NOT NULL,source_fingerprint TEXT NOT NULL,
      payload TEXT,payload_hash TEXT NOT NULL,effects TEXT NOT NULL,dependencies TEXT NOT NULL,
      accepted_utc TEXT NOT NULL,state TEXT NOT NULL,reason TEXT NOT NULL DEFAULT '',
      result TEXT,applied_revision INTEGER,superseded_by TEXT,UNIQUE(book_id,seq))''')
    db.execute('''CREATE TABLE IF NOT EXISTS book_decision_heads(
      book_id TEXT PRIMARY KEY,generation INTEGER NOT NULL,request_id TEXT NOT NULL,
      source_fingerprint TEXT NOT NULL,effects TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS book_decision_steps(
      request_id TEXT NOT NULL,step TEXT NOT NULL,input_hash TEXT NOT NULL,
      result TEXT NOT NULL,committed_utc TEXT NOT NULL,PRIMARY KEY(request_id,step))''')
    db.execute('CREATE INDEX IF NOT EXISTS book_decisions_current ON book_decisions(book_id,state,seq)')


def _identity(value):
    if not isinstance(value,str) or str(uuid.UUID(value))!=value:raise ValueError('A canonical decision request ID is required')
    return value


def _object(value,label,limit=MAX_PAYLOAD):
    if not isinstance(value,dict):raise ValueError(label+' must be an object')
    raw=packed(value)
    if len(raw.encode('utf-8'))>limit:raise ValueError(label+' exceeds its allowed bound')
    return raw


def _effects(value):
    if not isinstance(value,list) or not value or len(value)>MAX_EFFECTS or len(set(value))!=len(value):raise ValueError('Decision effects are missing or repeated')
    if any(not isinstance(key,str) or not key or len(key)>128 or any(ord(c)<33 for c in key) for key in value):raise ValueError('Invalid decision effect')
    return sorted(value)


def receipt(row):
    return {'schema':SCHEMA,'request_id':row['request_id'],'book_id':row['book_id'],
            'action':row['action'],'sequence':row['seq'],'accepted_utc':row['accepted_utc'],
            'state':row['state'],'reason':row['reason'],'payload_sha256':row['payload_hash'],
            'result':json.loads(row['result']) if row['result'] else None,
            'applied_revision':row['applied_revision']}


class Decisions:
    def __init__(self,database):
        self.database=database
        with connect(database) as db:setup(db)

    def accept(self,*,request_id,book_id,action,revision,fingerprint,payload,effects,
               predecessor=None,current_revision=None,current_fingerprint=None):
        """Commit intent only. Caller supplies server-derived effects/current facts.

        Shape/actor/source-scope checks belong to the existing route validator.
        Fresh media/review application remains separate and may retain a hold.
        """
        _identity(request_id)
        if action not in ACTIONS:raise ValueError('Unsupported durable decision action')
        if not isinstance(book_id,str) or not book_id or len(book_id)>200:raise ValueError('Decision book identity is invalid')
        if type(revision)is not int or revision<0:raise ValueError('Decision revision is invalid')
        if not isinstance(fingerprint,str) or len(fingerprint)!=64 or any(c not in '0123456789abcdef' for c in fingerprint):raise ValueError('Decision source fingerprint is invalid')
        if predecessor is not None:_identity(predecessor)
        encoded=_object(payload,'Decision payload');effect_keys=_effects(effects)
        immutable={'book_id':book_id,'action':action,'revision':revision,'fingerprint':fingerprint,
                   'payload':payload,'effects':effect_keys,'predecessor':predecessor}
        payload_hash=digest(immutable)
        # This is deliberately bounded acceptance, not the 30 s application retry.
        with connect(self.database,timeout=.25) as db:
            db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT * FROM book_decisions WHERE request_id=?',(request_id,)).fetchone()
            if old:
                if old['payload_hash']!=payload_hash:raise DecisionChanged('This request ID already records different choices')
                return receipt(old)
            if db.execute("SELECT count(*) FROM book_decisions WHERE payload IS NOT NULL AND state NOT IN ('applied','superseded')").fetchone()[0]>=MAX_PENDING:
                raise ValueError('Too many unfinished saved decisions; resolve their reported holds first')
            head=db.execute('SELECT * FROM book_decision_heads WHERE book_id=?',(book_id,)).fetchone()
            seq=db.execute('SELECT COALESCE(MAX(seq),0)+1 FROM book_decisions WHERE book_id=?',(book_id,)).fetchone()[0]
            reason=''
            if current_fingerprint is not None and current_fingerprint!=fingerprint:reason='This book’s source list changed; review the saved decision against the current book'
            elif current_revision is not None and current_revision!=revision:reason='This book’s revision changed; review the saved decision against the current book'
            elif predecessor!=(head['request_id'] if head else None):reason='A newer decision was accepted first; review these saved choices before applying them'
            compatible=not reason
            inherited=json.loads(head['effects']) if head else {}
            dependencies={key:owner for key,owner in inherited.items() if key!='approval'} if action=='approve' else {}
            db.execute('INSERT INTO book_decisions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (request_id,book_id,action,seq,predecessor,revision,fingerprint,encoded,payload_hash,
                        packed(effect_keys),packed(dependencies),utc(),'accepted' if compatible else 'needs_review',reason,None,None,None))
            if compatible:
                # Disjoint earlier effects remain in the cumulative head. Only
                # explicitly submitted overlapping keys acquire the new owner.
                merged=dict(inherited)
                for key in effect_keys:merged[key]=request_id
                db.execute('INSERT OR REPLACE INTO book_decision_heads VALUES(?,?,?,?,?)',
                           (book_id,(head['generation'] if head else 0)+1,request_id,fingerprint,packed(merged)))
                for prior in set(inherited.values())-set(merged.values()):
                    db.execute("UPDATE book_decisions SET state='superseded',superseded_by=? WHERE request_id=? AND state IN ('accepted','applying','needs_review')",(request_id,prior))
                prior_approval=inherited.get('approval')
                if action!='approve' and prior_approval and prior_approval in merged.values():
                    db.execute("UPDATE book_decisions SET state='needs_review',reason=? WHERE request_id=? AND state IN ('accepted','applying')",
                               ('New choices were saved after this approval; review the saved approval with those choices',prior_approval))
            return receipt(db.execute('SELECT * FROM book_decisions WHERE request_id=?',(request_id,)).fetchone())

    def get(self,request_id,*,include_payload=False):
        _identity(request_id)
        with connect(self.database) as db:row=db.execute('SELECT * FROM book_decisions WHERE request_id=?',(request_id,)).fetchone()
        if row is None:return None
        value=receipt(row)
        if include_payload:value['payload']=json.loads(row['payload']) if row['payload'] else None
        return value

    def head(self,book_id):
        with connect(self.database) as db:
            row=db.execute('SELECT * FROM book_decision_heads WHERE book_id=?',(book_id,)).fetchone()
            if not row:return None
            result=dict(row);result['effects']=json.loads(result['effects'])
            return result

    def pending(self):
        """Current compatible cumulative effects, in original acceptance order."""
        with connect(self.database) as db:
            heads=[dict(row) for row in db.execute('SELECT * FROM book_decision_heads ORDER BY book_id')]
            result=[]
            for head in heads:
                owners=set(json.loads(head['effects']).values())
                for row in db.execute("SELECT * FROM book_decisions WHERE book_id=? AND state IN ('accepted','applying') ORDER BY seq",(head['book_id'],)):
                    if row['request_id'] not in owners:continue
                    dependencies=json.loads(row['dependencies'])
                    if row['action']=='approve':
                        dependency_ids=set(dependencies.values())-{row['request_id']}
                        if any((db.execute('SELECT state FROM book_decisions WHERE request_id=?',(key,)).fetchone() or ['missing'])[0]!='applied' for key in dependency_ids):continue
                    item=dict(row);item['payload']=json.loads(item['payload']);item['generation']=head['generation']
                    item['active_effects']=[key for key,owner in json.loads(head['effects']).items() if owner==row['request_id']]
                    result.append(item)
        return result

    def application(self,request_id,generation):return Application(self,request_id,generation)

    def hold(self,request_id,generation,reason):
        if not isinstance(reason,str) or not reason.strip():raise ValueError('A held decision needs its actual reason')
        with connect(self.database) as db:
            db.execute('BEGIN IMMEDIATE');scope=self.application(request_id,generation);scope.check(db)
            db.execute("UPDATE book_decisions SET state='needs_review',reason=? WHERE request_id=?",(reason[:2000],request_id))

    def purge_fulfilled(self,limit=16):
        """Remove fulfilled payload only; request/hash/result tombstones remain."""
        if type(limit)is not int or not 1<=limit<=100:raise ValueError('Bounded decision cleanup is required')
        removed=0
        with connect(self.database) as db:
            db.execute('BEGIN IMMEDIATE')
            for row in db.execute("SELECT * FROM book_decisions WHERE payload IS NOT NULL AND state IN ('applied','superseded') ORDER BY accepted_utc LIMIT ?",(limit,)).fetchall():
                if row['state']=='superseded':
                    successor=db.execute('SELECT state FROM book_decisions WHERE request_id=?',(row['superseded_by'],)).fetchone()
                    if not successor or successor[0]!='applied':continue
                head=db.execute('SELECT effects FROM book_decision_heads WHERE book_id=?',(row['book_id'],)).fetchone()
                if head and row['request_id'] in json.loads(head[0]).values():continue
                if row['state']=='applied' and not row['result']:raise DecisionChanged('Applied decision has no durable result receipt')
                db.execute('UPDATE book_decisions SET payload=NULL,effects=? WHERE request_id=?',('[]',row['request_id']))
                db.execute('DELETE FROM book_decision_steps WHERE request_id=?',(row['request_id'],))
                removed+=1
        return removed


class Application:
    def __init__(self,store,request_id,generation):
        self.store=store;self.request_id=_identity(request_id)
        if type(generation)is not int or generation<1:raise ValueError('Invalid decision generation')
        self.generation=generation

    def check(self,db):
        if not db.in_transaction:raise ValueError('Decision application requires the consumer transaction')
        row=db.execute('SELECT * FROM book_decisions WHERE request_id=?',(self.request_id,)).fetchone()
        if not row or row['state'] not in ('accepted','applying'):raise DecisionChanged('Saved decision is not currently applicable')
        head=db.execute('SELECT * FROM book_decision_heads WHERE book_id=?',(row['book_id'],)).fetchone()
        if not head or head['generation']!=self.generation or self.request_id not in json.loads(head['effects']).values():
            raise DecisionChanged('A newer saved decision changed this application generation')
        return row,head

    def prior_step(self,db,name,inputs):
        self.check(db)
        if not isinstance(name,str) or not name or len(name)>128:raise ValueError('Invalid decision step')
        row=db.execute('SELECT * FROM book_decision_steps WHERE request_id=? AND step=?',(self.request_id,name)).fetchone()
        if not row:return None
        if row['input_hash']!=digest(inputs):raise DecisionChanged('Saved decision step inputs changed')
        return json.loads(row['result'])

    def bind_names(self,db,book_id,fingerprint,values):
        row,head=self.check(db)
        if row['book_id']!=book_id or row['action']!='names' or row['source_fingerprint']!=fingerprint:
            raise DecisionChanged('Saved names do not bind this exact book/source generation')
        payload=json.loads(row['payload']) if row['payload'] else {}
        original=payload.get('names')
        if not isinstance(original,dict):raise DecisionChanged('Saved names payload is unavailable')
        owned={key.split('.',1)[1] for key,owner in json.loads(head['effects']).items() if owner==self.request_id and key.startswith('names.')}
        if values!={key:value for key,value in original.items() if key in owned}:
            raise DecisionChanged('Applied names differ from this accepted decision')

    def commit_step(self,db,name,inputs,result,*,final=False,applied_revision=None):
        row,head=self.check(db);encoded=_object(result,'Decision application receipt',16*1024)
        prior=self.prior_step(db,name,inputs)
        if prior is not None:
            if packed(prior)!=encoded:raise DecisionChanged('Saved decision step result changed')
            return prior
        db.execute('INSERT INTO book_decision_steps VALUES(?,?,?,?,?)',(self.request_id,name,digest(inputs),encoded,utc()))
        if final:
            # Consumer mutations and this receipt share one commit. Non-enqueue
            # Save/no-op/answer-only outcomes use exactly the same boundary.
            remaining={key:owner for key,owner in json.loads(head['effects']).items() if owner!=self.request_id}
            db.execute('UPDATE book_decision_heads SET effects=? WHERE book_id=? AND generation=?',
                       (packed(remaining),row['book_id'],self.generation))
            db.execute("UPDATE book_decisions SET state='applied',reason='',result=?,applied_revision=? WHERE request_id=?",(encoded,applied_revision,self.request_id))
        else:db.execute("UPDATE book_decisions SET state='applying' WHERE request_id=?",(self.request_id,))
        return copy.deepcopy(result)
