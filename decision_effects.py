"""Request-bound receipts for the existing book-review transactions."""
import copy
import json
from durable_decisions import DecisionChanged,packed
from scanner import connect


class Effect:
    def __init__(self,application,step,*,actions,final=False):
        self.application=application;self.step=step;self.actions=frozenset(actions);self.final=final
        self.inputs=None

    def bind(self,operation,values):
        if self.inputs is None:self.inputs={'request_id':self.application.request_id,'step':self.step,'operation':operation,'values':copy.deepcopy(values)}
        elif operation==self.inputs['operation']:
            if packed(values)!=packed(self.inputs['values']):raise DecisionChanged('Decision effect was reused with changed mutation values')
        elif not (operation=='context' or self.inputs['operation']=='metadata_choices' and operation=='review'):
            raise DecisionChanged('Decision effect was reused by a different consumer')

    def _payload(self,saved):
        if self.inputs is None:raise ValueError('Decision effect requires its exact semantic mutation values')
        payload=json.loads(saved['payload'])
        action=saved['action'];values=self.inputs['values']
        if action in ('review','tracks','metadata_choices'):
            # Endpoint payload is immutable; compare all caller-controlled fields,
            # including fields whose application fills an existing default.
            defaults={'review':{'approve':False,'manual_note':'','proposal_id':None,'cover_id':None,'names_row_only':False},
                      'tracks':{'evidence_note':''},'metadata_choices':{'manual_note':''}}[action]
            expected=dict(defaults,**payload)
            public={key:value for key,value in values.items() if not key.startswith('_')}
            if packed(expected)!=packed(public):raise DecisionChanged('Book-review values differ from the accepted decision payload')
            if action=='review' and (values.get('_actor')!='user' or values.get('_automatic_facts') is not None or values.get('_user_approval')):
                raise DecisionChanged('A saved user review cannot authorize private approval evidence')

    def before(self,db,row):
        saved,_=self.application.check_current(db,row)
        self._payload(saved)
        if saved['action'] not in self.actions or saved['book_id']!=row['id'] or saved['source_fingerprint']!=row['fingerprint']:
            raise DecisionChanged('Saved decision does not bind this book-review operation')
        current=db.execute('SELECT revision,fingerprint FROM book_groups WHERE id=? AND superseded=0',(row['id'],)).fetchone()
        if not current or current['revision']!=row['revision'] or current['fingerprint']!=row['fingerprint']:
            raise DecisionChanged('Book changed before its saved decision could commit')
        return self.application.prior_step(db,self.step,self.inputs)

    def replay(self,row,operation=None,values=None):
        if operation is not None:self.bind(operation,values)
        with connect(self.application.store.database) as db:
            db.execute('BEGIN')
            return self.before(db,row)

    def commit(self,db,row,revision,**result):
        return self.application.commit_step(db,self.step,self.inputs,
            dict(result,candidate_id=row['id'],candidate_revision=revision),
            final=self.final,applied_revision=revision if self.final else None)


def approval(press,step,*,final=False):
    application=(press or {}).get('decision')
    return Effect(application,step,actions=('approve',),final=final) if application is not None else None
