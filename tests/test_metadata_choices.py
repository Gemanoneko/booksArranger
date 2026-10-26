"""Content-scoped conflict questions and append-only user decisions."""
import copy
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import manual_metadata
import metadata_choices as m


class MetadataChoicesTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.addCleanup(self.db.close);manual_metadata.initialize(self.db)
        self.row={'id':'candidate-1','fingerprint':'source-1','revision':3}
        self.a={'id':'a','provider':'Catalog A','public_url':'https://a.invalid/work/1','title':'Первая книга','authors':['Автор Один'],'original_language':'ru','series':'Цикл А','retrieved_utc':'2026-10-19','per_field_evidence':{'title':{'record':'A1','retrieved_utc':'2026-10-19'}}}
        self.b={'id':'b','provider':'Catalog B','public_url':'https://b.invalid/work/2','title':'Другая книга','authors':['Автор Два'],'original_language':'en','series':'Цикл Б','retrieved_utc':'2026-10-19'}

    def present(self,providers=None,manual=None,conflicts=None):return m.present(self.db,self.row,[self.a,self.b] if providers is None else providers,manual or [],conflicts or [])
    def answer(self,snapshot,mode='provider',option=0,values=None):
        choices=[{'question_id':q['id'],'mode':mode,**({'option_id':q['options'][option]['id']} if mode=='provider' else {'values':values} if mode=='corrected' else {})} for q in snapshot['questions']]
        return m.prepare(self.row,snapshot,snapshot['signature'],choices,note='Explicit user decision')

    def test_admission_requires_answer_and_exact_selected_values(self):
        snapshot=self.present()
        with self.assertRaisesRegex(ValueError,'Resolve metadata question'):m.admission(snapshot,{})
        prepared=self.answer(snapshot);m.append(self.db,prepared['record'])
        answered=self.present();review=prepared['patch']
        self.assertTrue(m.admission(answered,review))
        review=dict(review,title='Silently reset provider default')
        with self.assertRaisesRegex(ValueError,'Saved metadata choice differs'):m.admission(answered,review)

    def test_new_evidence_asks_again_at_approval(self):
        prepared=self.answer(self.present());m.append(self.db,prepared['record'])
        changed=self.present([self.a,dict(self.b,title='New relevant provider title')])
        with self.assertRaisesRegex(ValueError,'Resolve metadata question'):m.admission(changed,prepared['patch'])

    def test_two_provider_disagreement_is_one_coherent_work_question(self):
        question=self.present()['questions'][0]
        self.assertEqual(question['type'],'work_profile');self.assertEqual(len(question['options']),2)
        profiles={(o['values']['title'],o['values']['canonical_author'],o['values']['original_language']) for o in question['options']}
        self.assertEqual(profiles,{('Первая книга','Автор Один','ru'),('Другая книга','Автор Два','en')})
        result=self.answer(self.present());self.assertIn((result['patch']['title'],result['patch']['canonical_author'],result['patch']['original_language']),profiles)
        self.assertEqual(result['corrected_values'],{})

    def test_three_sources_with_two_equal_profiles_group_evidence_without_approval(self):
        c=dict(self.a,id='c',provider='Catalog C',public_url='https://c.invalid/1')
        snapshot=self.present([self.a,self.b,c]);self.assertEqual(len(snapshot['questions'][0]['options']),2)
        self.assertEqual(sorted(len(o['sources']) for o in snapshot['questions'][0]['options']),[1,2]);self.assertEqual(snapshot['unresolved_count'],1)

    def test_matching_title_is_not_same_work_proof(self):
        b=dict(self.a,id='b',provider='Catalog B',series='Other series')
        self.assertEqual(self.present([self.a,b])['questions'][0]['type'],'work_profile')

    def test_shared_authoritative_work_id_allows_field_questions_only(self):
        a=dict(self.a,work_id='work:1');b=dict(a,id='b',provider='Catalog B',series='Other series')
        snapshot=self.present([a,b]);self.assertEqual([(q['type'],q['field']) for q in snapshot['questions']],[('field','series')])
        self.assertEqual(set(self.answer(snapshot)['patch']),{'series'})

    def test_identity_disagreement_remains_whole_work_even_with_claimed_same_id(self):
        snapshot=self.present([dict(self.a,work_id='work:1'),dict(self.b,work_id='work:1')])
        self.assertEqual(snapshot['questions'][0]['type'],'work_profile')

    def test_missing_value_is_not_fabricated_conflict_or_empty_override(self):
        b=dict(self.a,id='b',provider='Catalog B',series='')
        self.assertEqual(self.present([self.a,b])['unresolved_count'],0)
        c=dict(self.a,id='c',provider='Catalog C',series='Other')
        sources=[dict(value,work_id='work:1') for value in (self.a,b,c)]
        question=self.present(sources)['questions'][0];self.assertEqual(len(question['options']),2);self.assertEqual(question['not_supplied'][0]['provider'],'Catalog B')

    def test_saved_decision_survives_restart_and_identical_timestamp_refresh(self):
        snapshot=self.present();prepared=self.answer(snapshot);m.append(self.db,prepared['record'],applied_revision=5)
        a=copy.deepcopy(self.a);a['retrieved_utc']='2026-10-20';a['per_field_evidence']['title']['retrieved_utc']='2026-10-20'
        fresh=self.present([self.b,a]);self.assertEqual(fresh['signature'],snapshot['signature']);self.assertEqual(fresh['unresolved_count'],0)
        self.assertEqual(fresh['questions'][0]['chosen_by'],'you');self.assertEqual(m.records(self.db,self.row)[0]['applied_revision'],5)
        self.row['revision']=100
        self.assertEqual(self.present([a,self.b])['unresolved_count'],0)

    def test_no_provider_evidence_never_fabricates_a_conflict_from_a_hold(self):
        self.assertEqual(self.present([])['questions'],[])

    def test_new_relevant_assertion_asks_again_and_keeps_prior_decision(self):
        snapshot=self.present();m.append(self.db,self.answer(snapshot)['record'])
        fresh=self.present([self.a,self.b,dict(self.a,id='new',provider='New provider',title='Третья книга')])
        self.assertEqual(fresh['unresolved_count'],1);self.assertTrue(fresh['questions'][0]['renewed']);self.assertIn('previous_decision',fresh['questions'][0])

    def test_same_work_unrelated_field_change_does_not_renew_series_choice(self):
        a=dict(self.a,work_id='work:1');b=dict(a,id='b',provider='Catalog B',series='Other series')
        snap=self.present([a,b]);m.append(self.db,self.answer(snap)['record'])
        self.assertEqual(self.present([a,dict(b,genre='new unrelated genre')])['questions'][0]['evidence_signature'],snap['questions'][0]['evidence_signature'])

    def test_keep_unresolved_never_dismisses_or_approves(self):
        snapshot=self.present();prepared=self.answer(snapshot,'unresolved');self.assertEqual(prepared['patch'],{})
        m.append(self.db,prepared['record']);fresh=self.present();self.assertEqual(fresh['unresolved_count'],1);self.assertFalse(fresh['questions'][0]['resolved'])

    def test_corrected_cyrillic_becomes_only_explicit_manual_evidence_without_self_conflict(self):
        source=manual_metadata.capture(self.row,{'title':'Старая книга','canonical_author':'Старый Автор'},'Earlier entry');manual_metadata.append(self.db,source)
        entered=manual_metadata.records(self.db,self.row);snapshot=self.present(manual=entered)
        values={'title':'Исправленная книга','canonical_author':'Правильный Автор','original_language':'Unknown'}
        prepared=self.answer(snapshot,'corrected',values=values);self.assertNotIn('original_language',prepared['corrected_values'])
        correction=manual_metadata.capture(self.row,prepared['corrected_values'],'Explicit user decision');manual_metadata.append(self.db,correction)
        saved=m.append(self.db,prepared['record'],applied_revision=4);self.assertEqual(saved['correction_source_ids'],[correction['source_id']])
        fresh=self.present(manual=manual_metadata.records(self.db,self.row));self.assertEqual(fresh['unresolved_count'],0)
        self.assertEqual(len(manual_metadata.records(self.db,self.row)),2);self.assertEqual(prepared['patch']['title'],'Исправленная книга')
        renewed=self.present([self.a,self.b,dict(self.a,id='new',title='New relevant assertion')],manual_metadata.records(self.db,self.row))
        self.assertEqual(renewed['unresolved_count'],1)
        self.assertTrue(any(o['values']['title']=='Исправленная книга' for o in renewed['questions'][0]['options']))

    def test_changed_source_and_stale_evidence_are_not_implicitly_accepted(self):
        snapshot=self.present();m.append(self.db,self.answer(snapshot)['record'])
        self.row['fingerprint']='different-recording';self.assertEqual(self.present()['unresolved_count'],1);self.assertEqual(m.records(self.db,self.row)[0]['status'],'stale')
        with self.assertRaises(m.ChoiceChanged):m.prepare(self.row,self.present(),snapshot['signature'],[])

    def test_bad_options_hybrid_corrections_and_append_mutation_refused(self):
        snapshot=self.present();question=snapshot['questions'][0]
        for choice in ({'question_id':question['id'],'option_id':'unknown'}, {'question_id':question['id'],'mode':'corrected','values':{'title':'Only half identity'}}, {'question_id':question['id'],'mode':'corrected','values':{'title':'x','canonical_author':'y','unrelated':'z'}}):
            with self.assertRaises(ValueError):m.prepare(self.row,snapshot,snapshot['signature'],[choice])
        m.append(self.db,self.answer(snapshot)['record'])
        for sql in ('DELETE FROM metadata_choices','UPDATE metadata_choices SET actor="provider"'):
            with self.assertRaises(sqlite3.IntegrityError):self.db.execute(sql)

    def test_context_checkpoint_can_roll_back_manual_evidence_and_choice_together(self):
        prepared=self.answer(self.present(),'corrected',values={'title':'Книга','canonical_author':'Автор'})
        try:
            with self.db:
                manual_metadata.append(self.db,manual_metadata.capture(self.row,prepared['corrected_values'],'Correction'))
                m.append(self.db,prepared['record'],applied_revision=4)
                raise RuntimeError('Synthetic context transaction failure')
        except RuntimeError:pass
        self.assertEqual(manual_metadata.records(self.db,self.row),[]);self.assertEqual(m.records(self.db,self.row),[])

    def test_automatic_compared_values_are_shown_without_copying_unknown_identity(self):
        source=manual_metadata.capture(self.row,{'title':'Manual book','canonical_author':'Manual author'},'Manual note');manual_metadata.append(self.db,source)
        conflicts=[{'field':'title','manual_value':'Manual book','other_value':'Actual research title','other_work_id':'catalog:42','other_sources':[{'provider':'Actual catalog','url':'https://example.invalid/42'}]}]
        snap=self.present(providers=[],manual=manual_metadata.records(self.db,self.row),conflicts=conflicts)
        matching=[o for o in snap['questions'][0]['options'] if o['values']['title']=='Actual research title'][0]
        self.assertEqual(matching['values']['canonical_author'],'');self.assertEqual(matching['sources'][0]['evidence'][0]['other_sources'][0]['provider'],'Actual catalog')


class MetadataChoiceServiceTests(unittest.TestCase):
    def service(self):
        from review_backend import CandidateReviewService
        service=CandidateReviewService.__new__(CandidateReviewService);service.lock=threading.RLock();service.matching={};service.jobs=None
        row={'id':'candidate','revision':7,'fingerprint':'recording','review':{'title':'Old','canonical_author':'Old author','narrator':'Keep narrator','genre':'Keep genre'}}
        a={'id':'a','provider':'A','title':'First','authors':'First author','original_language':'ru'}
        b={'id':'b','provider':'B','title':'Second','authors':'Second author','original_language':'en'}
        snapshot=m.questions(row,[a,b],[],[]);service._row=lambda library,id,revision=None:copy.deepcopy(row) if revision in (None,7) else (_ for _ in ()).throw(ValueError('stale'))
        service._context=lambda row:{'manual_note':'Keep note','cover_id':'cover'};service.metadata_questions=lambda row,ctx:copy.deepcopy(snapshot)
        captured={}
        def save(*args,**kwargs):captured.update(kwargs);captured['review']=args[3];return dict(row,metadata_questions=dict(snapshot,unresolved_count=0))
        service.save=save
        return service,row,snapshot,captured

    def test_provider_selection_never_creates_manual_source_approves_or_overwrites_unrelated_fields(self):
        service,row,snap,captured=self.service();q=snap['questions'][0]
        result=service.choose_metadata('Audiobooks',row['id'],7,snap['signature'],[{'question_id':q['id'],'option_id':q['options'][0]['id']}])
        self.assertFalse(captured['approve']);self.assertFalse(captured['capture_manual']);self.assertEqual(captured['manual_source_values'],{})
        self.assertEqual(captured['review']['narrator'],'Keep narrator');self.assertEqual(captured['review']['genre'],'Keep genre');self.assertEqual(result['unresolved_count'],0)

    def test_correction_capture_is_only_entered_fields_and_choice_checkpoint(self):
        service,row,snap,captured=self.service();q=snap['questions'][0]
        service.choose_metadata('Audiobooks',row['id'],7,snap['signature'],[{'question_id':q['id'],'mode':'corrected','values':{'title':'Новая книга','canonical_author':'Автор'}}],manual_note='My correction')
        self.assertTrue(captured['capture_manual']);self.assertEqual(captured['manual_source_values'],{'title':'Новая книга','canonical_author':'Автор'})
        self.assertEqual(captured['decision_record']['actor'],'user');self.assertFalse(captured['approve'])

    def test_candidate_revision_mismatch_is_typed_stale_before_save(self):
        service,row,snap,captured=self.service()
        with self.assertRaises(m.ChoiceChanged):service.choose_metadata('Audiobooks',row['id'],6,snap['signature'],[])
        self.assertEqual(captured,{})

    def test_all_unresolved_only_checkpoints_hold_and_retains_existing_evidence(self):
        service,row,snap,captured=self.service();q=snap['questions'][0]
        context={'metadata_approved':True,'metadata_facts':{'work_ids':['actual:1']},'duplicate_review':{'kept':'evidence'},'source_hashes':{'track':'hash'}}
        service._context=lambda row:copy.deepcopy(context)
        def checkpoint(row,ctx,**kwargs):captured.update(context=ctx,checkpoint=kwargs);return dict(row,metadata_questions=snap)
        service._write=checkpoint
        service.choose_metadata('Audiobooks',row['id'],7,snap['signature'],[{'question_id':q['id'],'mode':'unresolved'}])
        self.assertFalse(captured['context']['metadata_approved']);self.assertEqual(captured['context']['metadata_facts'],context['metadata_facts'])
        self.assertEqual(captured['context']['source_hashes'],context['source_hashes']);self.assertNotIn('review',captured)


class MetadataChoiceBrowserContractTests(unittest.TestCase):
    def test_native_radio_preparation_dirty_correction_stale_text_and_caret_in_isolated_dom(self):
        # Pure VM DOM contract: no Electron/browser launch and no geometry or
        # packaged-QA claim. Full rendering/contrast/zoom remains independent QA.
        code=r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('web/app.js','utf8'),start=source.indexOf('let metadataChoiceState=null;'),end=source.indexOf('function renderMergeCandidate(',start);
assert(start>=0 && end>start);
let context;
class Element {
 constructor(tag='div'){this.tagName=tag;this.children=[];this.listeners={};this.attributes={};this.value='';this.checked=false;this.hidden=false;this.textContent='';}
 append(...items){for(const item of items){if(item.parentElement)item.parentElement.children=item.parentElement.children.filter(child=>child!==item);item.parentElement=this;this.children.push(item);}}
 replaceChildren(...items){this.children=[];this.append(...items);}
 setAttribute(key,value){this.attributes[key]=value;}
 addEventListener(type,handler){(this.listeners[type]??=[]).push(handler);}
 querySelector(selector){if(selector!=='input[type=radio]')return null;const walk=element=>{if(element.tagName==='input' && element.type==='radio')return element;for(const child of element.children){const found=walk(child);if(found)return found;}return null;};return walk(this);}
 focus(){if(this===get('metadata-questions-heading')){assert.equal(get('manual-review').open,true,'editor opens before question heading focus');assert.equal(get('metadata-questions').hidden,false,'question is visible before heading focus');}context.document.activeElement=this;} scrollIntoView(){}
 async emit(type){const event={stopped:false,stopPropagation(){this.stopped=true;}};for(const handler of this.listeners[type] || [])await handler(event);if(!event.stopped && this.parentElement)await this.parentElement.emit(type);}
}
const nodes=new Map(),get=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
const form=get('form'),names=['original_language','title','author','canonical_author','narrator','universe','series','number','genre','topic'],inputs={};
for(const name of [...names,'multi_author','anthology']){inputs[name]=new Element('input');inputs[name].value=name==='original_language'?'Unknown':name==='title'?'Old title':name==='canonical_author'?'Old author':'';form.append(inputs[name]);}
form.elements={namedItem:name=>inputs[name]};form.append(get('metadata-questions'));get('metadata-questions').append(get('metadata-question-fields'),get('save-metadata-choices'));
get('manual-review').tagName='details';get('manual-review').open=false;get('manual-review').append(form);
get('metadata-questions-heading').tagName='h2';get('metadata-questions-heading').setAttribute('tabindex','-1');get('metadata-questions').append(get('metadata-questions-heading'));
assert.match(fs.readFileSync('web/index.html','utf8'),/<h2 id="metadata-questions-heading" tabindex="-1">/,'existing question heading is programmatically focusable');
const q={id:'q',type:'work_profile',label:'Which book is this recording of?',evidence_signature:'ev1',resolved:false,decision:null,options:[
 {id:'a',values:{title:'First',canonical_author:'Author A',original_language:'ru'},sources:[{id:'A1',provider:'Catalog A',public_url:'https://a.invalid/1'}]},
 {id:'b',values:{title:'Second',canonical_author:'Author B',original_language:'en'},sources:[{id:'B1',provider:'Catalog B',public_url:'https://b.invalid/2'}]}]};
const makeRow=()=>({id:'candidate',revision:7,kind:'candidate',title_clue:'Actual book',review_context:{},review:{title:'Saved title',canonical_author:'Saved author'},metadata_questions:{signature:'snapshot1',questions:[structuredClone(q)],unresolved_count:1}});
let requests=[],response,errorNext=null;
context={console,later:(key,kind,handler)=>handler,keptNote:row=>row?.review_context?.manual_note || '',document:{activeElement:inputs.narrator},$:get,form,fields:names,dirty:false,coverId:null,busy:false,ended:false,recoveryDisconnected:false,trackDraft:null,manualMetadataTouched:false,selectedLibrary:'Audiobooks',selectedRow:makeRow(),
 node:(tag,text='',className='')=>Object.assign(new Element(tag),{textContent:text,className}),sourceLink:(url,text)=>Object.assign(new Element('a'),{href:url,textContent:text}),controls(){},syncManualDraft(){},
 async request(route,data){requests.push({route,data});if(errorNext)throw errorNext;return response;},select(row){context.selectedRow=row;context.renderMetadataQuestions(row,false);}};
vm.createContext(context);vm.runInContext(source.slice(start,end),context);
const directStart=source.indexOf("$('edit-held-metadata').addEventListener('click'");assert(directStart>=0);vm.runInContext(source.slice(directStart,source.indexOf('\n',directStart)),context);
form.addEventListener('input',()=>{context.dirty=true;context.updateMetadataChoiceControls();});
function radios(){const result=[];function walk(element){if(element.tagName==='input' && element.type==='radio')result.push(element);for(const child of element.children)walk(child);}walk(get('metadata-question-fields'));return result;}
(async()=>{
 context.renderMetadataQuestions(context.selectedRow,false);assert.equal(radios().filter(r=>r.checked).length,1);assert.equal(radios().find(r=>r.checked).value,'unresolved');
 // Both Resolve entries open the enclosing editor before focusing its question
 // heading. They must not select a provider or save data.
 inputs.narrator.value='Мой незавершённый ввод';inputs.narrator.selectionStart=2;inputs.narrator.selectionEnd=6;
 const entryRow=context.selectedRow,entrySignature=entryRow.metadata_questions.signature;
 await get('edit-held-metadata').emit('click');assert.equal(get('manual-review').open,true,'direct Resolve metadata opens Manual review');
 assert.equal(get('metadata-questions').hidden,false);assert.ok(context.document.activeElement===get('metadata-questions-heading'),'direct Resolve focuses the question heading');
 assert.equal(radios().find(r=>r.checked).value,'unresolved');assert.equal(requests.length,0);assert.equal(context.selectedRow,entryRow);assert.equal(context.selectedRow.metadata_questions.signature,entrySignature);
 assert.equal(inputs.narrator.value,'Мой незавершённый ввод');assert.equal(inputs.narrator.selectionStart,2);assert.equal(inputs.narrator.selectionEnd,6);
 get('manual-review').open=false;context.document.activeElement=inputs.narrator;await get('resolve-metadata-question').emit('click');
 assert.equal(get('manual-review').open,true);assert.ok(context.document.activeElement===get('metadata-questions-heading'),'inner Resolve focuses the same question heading');
 assert.equal(radios().find(r=>r.checked).value,'unresolved');assert.equal(requests.length,0);assert.equal(context.selectedRow,entryRow);assert.equal(context.selectedRow.metadata_questions.signature,entrySignature);
 assert.equal(inputs.narrator.value,'Мой незавершённый ввод');assert.equal(inputs.narrator.selectionStart,2);assert.equal(inputs.narrator.selectionEnd,6);
 const before=inputs.title.value,provider=radios().find(r=>r.value==='a');provider.checked=true;await provider.emit('input');await provider.emit('change');assert.equal(context.dirty,false);assert.equal(inputs.title.value,before);
 response={row:makeRow(),unresolved_count:0};await get('save-metadata-choices').emit('click');assert.equal(requests[0].route,'/api/candidate/metadata-choice');assert.equal(requests[0].data.choices[0].option_id,'a');assert(!('approve' in requests[0].data));
 // Background evidence arrival cannot touch a focused existing text input.
 inputs.title.value='Незавершённый текст';inputs.title.selectionStart=2;inputs.title.selectionEnd=5;context.document.activeElement=inputs.title;context.dirty=true;
 const renewed=makeRow();renewed.metadata_questions.signature='renewed';renewed.metadata_questions.questions[0].evidence_signature='ev2';context.renderMetadataQuestions(renewed,false);
 assert.equal(inputs.title.value,'Незавершённый текст');assert.equal(context.document.activeElement,inputs.title);assert.equal(inputs.title.selectionStart,2);assert.equal(inputs.title.selectionEnd,5);assert.equal(get('save-metadata-choices').disabled,true);
 // A clean draft can explicitly enter a correction using the existing fields.
 context.dirty=false;const correctedRow=makeRow();correctedRow.id='other';context.selectedRow=correctedRow;context.renderMetadataQuestions(correctedRow,false);
 const corrected=radios().find(r=>r.value==='corrected');corrected.checked=true;await corrected.emit('input');await corrected.emit('change');
 inputs.title.value='Исправленная книга';inputs.canonical_author.value='Верный Автор';await inputs.title.emit('input');assert.equal(get('save-metadata-choices').disabled,false);
 inputs.genre.value='Unrelated unsaved draft';await inputs.genre.emit('input');assert.equal(get('save-metadata-choices').disabled,true);inputs.genre.value='';await inputs.genre.emit('input');assert.equal(get('save-metadata-choices').disabled,false);
 const stale=new Error('Sources changed. Compare the updated results before saving.');stale.httpStatus=409;stale.body={row:{...correctedRow,revision:8,metadata_questions:{...correctedRow.metadata_questions,signature:'newer'}}};errorNext=stale;
 inputs.title.selectionStart=3;inputs.title.selectionEnd=6;await get('save-metadata-choices').emit('click');assert.equal(inputs.title.value,'Исправленная книга');assert.equal(inputs.title.selectionStart,3);assert.equal(inputs.title.selectionEnd,6);assert.equal(requests.at(-1).data.choices[0].mode,'corrected');assert.equal(requests.at(-1).data.choices[0].values.title,'Исправленная книга');
 assert.match(get('metadata-question-status').textContent,/Sources changed/);console.log('METADATA_CHOICE_DOM_CONTRACT_PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
        result=subprocess.run([shutil.which('node'),'-e',code],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,encoding='utf-8',timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertIn('METADATA_CHOICE_DOM_CONTRACT_PASS',result.stdout)


if __name__=='__main__':unittest.main()
