"""User-requested M4B damage repair: detection, damage description and admission binding.

Never automatic. A repaired child job exists only after the user presses Repair and the
backend entry point admits it. Detection opens the source read-only and reads only box
headers and the movie box, within m4b_preservation's own read bound. Nothing here writes,
encodes or publishes; the silence-repair proof only decodes, through the caller's owned runner.

The child reuses the failed-M4B repair ledger (manifest key 'm4b_repair'). That gives one
child per failed parent, no automatic retry of a child and no repair of a repair. The
pipeline passes approved_repairs(manifest) to m4b_preservation.plan(repair=...) and calls
confirm(manifest, plan), so the applied repair must equal the one the user approved.
"""
import hashlib
import json
import os
import shutil
import threading
from pathlib import Path

import m4b_preservation as preservation
from failed_m4b_retry import unpublished_single_m4b

SCHEMA='m4b-damage-repair-v1'
CHECK_TITLE='Repair check'
_MODULE_SHA256=hashlib.sha256(Path(preservation.__file__).read_bytes()).hexdigest()
_CACHE={};_LOCK=threading.Lock();_CACHE_LIMIT=1024

def diagnose(source_size,read_at):
    """Classify one source: intact, damaged and repairable, or refused.

    Returns {'state','reason','damage','repairs'}. reason is the remaining refusal (or the
    strict one that the repair answers); damage holds one plain description per repair.
    """
    try:
        preservation.plan(source_size,read_at,{'title':CHECK_TITLE})
        return {'state':'intact','reason':'','damage':[],'repairs':[]}
    except preservation.Refused as error:strict=str(error)
    try:repaired=preservation.plan(source_size,read_at,{'title':CHECK_TITLE},None,preservation.REPAIRS)
    except preservation.Refused as error:
        return {'state':'refused','reason':str(error),'damage':[],'repairs':[]}
    repairs=[dict(item) for item in repaired.repairs]
    if not repairs:return {'state':'refused','reason':strict,'damage':[],'repairs':[]}
    return {'state':'repairable','reason':strict,'damage':[item['description'] for item in repairs],'repairs':repairs}

def diagnose_path(path,stop=None):
    """Read-only handle; header and movie-box reads only."""
    with open(Path(path),'rb') as reader:
        size=os.fstat(reader.fileno()).st_size
        def read_at(offset,count):
            if stop is not None and stop.is_set():raise InterruptedError('Repair check stopped')
            reader.seek(offset);return reader.read(count)
        return diagnose(size,read_at)

def eligible(row):
    """Static rule, no I/O: a failed, unpublished single-.m4b job that is not itself a child.

    Damage can surface under any failure reason (a legacy remux failure or a preservation
    refusal), so no reason filter applies here; diagnose() decides whether a repair exists.
    """
    try:return unpublished_single_m4b(row)
    except (KeyError,TypeError,ValueError):return False

def _key(row):return (row['job_id'],row['manifest_hash'],_MODULE_SHA256)

def classify(row):
    """The row's repair field without I/O: None (not applicable), {'state':'unchecked'}, or a
    cached check() result. Safe to call on every status read."""
    if not eligible(row):return None
    with _LOCK:found=_CACHE.get(_key(row))
    return dict(found) if found else {'state':'unchecked'}

def check(row,stop=None):
    """Diagnose the row's source now (read-only, may take seconds) and cache the answer."""
    if not eligible(row):return None
    source=json.loads(row['manifest'])['sources'][0]['path']
    try:result=diagnose_path(source,stop)
    except OSError as error:result={'state':'refused','reason':'Source unavailable: '+str(error),'damage':[],'repairs':[],'unavailable':True}
    with _LOCK:
        if len(_CACHE)>=_CACHE_LIMIT:_CACHE.clear()
        _CACHE[_key(row)]=result
    return dict(result)

def bind(parent,fresh,diagnosis,module_sha256):
    """Admission manifest: the identical reviewed manifest plus the user-approved repair."""
    if not eligible(parent):raise ValueError('This book is outside the M4B repair scope')
    prior=json.loads(parent['manifest'])
    remove=lambda value:{key:item for key,item in value.items() if key!='job_id'}
    if remove(prior)!=remove(fresh):raise ValueError('Frozen review/source/cover/policy changed; failed job preserved')
    if fresh['job_id']==parent['job_id']:raise ValueError('A repair needs a distinct job identity')
    if diagnosis.get('state')!='repairable' or not diagnosis.get('repairs'):raise ValueError('The source has no provable repair')
    if not isinstance(module_sha256,str) or len(module_sha256)!=64:raise ValueError('Repair module identity is missing')
    kinds=[item.get('kind') for item in diagnosis['repairs']]
    if len(set(kinds))!=len(kinds) or not set(kinds)<=preservation.REPAIRS:raise ValueError('Unknown repair')
    result=dict(fresh)
    result['m4b_repair']={'schema':SCHEMA,'parent_job_id':parent['job_id'],
        'parent_manifest_hash':parent['manifest_hash'],
        'parent_journal_sha256':hashlib.sha256(parent['journal'].encode()).hexdigest(),
        'module_sha256':module_sha256,'repairs':[dict(item) for item in diagnosis['repairs']],
        'note':' '.join(diagnosis['damage']),'user_requested':True,'one_child_per_failed_parent':True}
    return result

def approved_repairs(manifest):
    """Repair kinds the user approved for this job; empty for every ordinary job."""
    binding=manifest.get('m4b_repair')
    if not isinstance(binding,dict) or binding.get('schema')!=SCHEMA:return frozenset()
    kinds=frozenset(item.get('kind') for item in binding.get('repairs',[]))
    preservation.need(kinds and kinds<=preservation.REPAIRS,'Approved repair is invalid')
    return kinds

def confirm(manifest,plan):
    """Applied repairs must equal the approved ones exactly (kinds and facts).

    Returns the per-book note record {'note','repairs'} for the job's validation, or None.
    """
    binding=manifest.get('m4b_repair')
    approved=binding.get('repairs',[]) if isinstance(binding,dict) and binding.get('schema')==SCHEMA else []
    applied=[dict(item) for item in plan.repairs]
    preservation.need(applied==approved,'Applied repair differs from the approved repair')
    return {'note':binding['note'],'repairs':applied} if applied else None


def silence_approved(manifest):
    """True when the user approved the truncated-final-frames repair for this job. The cut source
    cannot pass a strict full decode, so the pipeline skips that duration decode and the repair
    proof decodes the intact frames instead."""
    return preservation.REPAIR_TRUNCATED_FRAMES in approved_repairs(manifest)

def silenced(plan):
    """The truncated-final-frames repair record of a plan, or None."""
    return next((item for item in plan.repairs if item['kind']==preservation.REPAIR_TRUNCATED_FRAMES),None)

class _Pcm:
    """Streaming f64 PCM proof: full hash, hash of the first `limit` bytes, and a count of
    samples at or after byte `zero_from` that are not exactly 0.0 (either sign)."""
    def __init__(self,frame_bytes,limit=None,zero_from=None):
        self.frame_bytes=frame_bytes;self.limit=limit;self.zero_from=zero_from;self.bytes=0;self.nonzero=0
        self.full=hashlib.sha256();self.prefix=hashlib.sha256();self.carry=b''
    def feed(self,raw):
        start=self.bytes;self.bytes+=len(raw);self.full.update(raw)
        if self.limit is not None and start<self.limit:self.prefix.update(raw[:self.limit-start])
        if self.zero_from is not None and self.bytes>self.zero_from:
            data=self.carry+raw[max(0,self.zero_from-start):];usable=len(data)-len(data)%8
            self.nonzero+=sum(1 for value in memoryview(data[:usable]).cast('d') if value!=0.0);self.carry=data[usable:]

class _Packets:
    """Streaming packet timing: hash of the first `count` packets (relative pts/dts, duration,
    trims), the total count, corrupt flags, and the durations of packets after `count`."""
    def __init__(self,count):
        self.count=count;self.seen=0;self.origin=None;self.prefix=hashlib.sha256();self.corrupt=[];self.after=[];self.pending=b''
    def feed(self,raw):
        lines=(self.pending+raw).split(b'\n');self.pending=lines.pop()
        preservation.need(len(self.pending)<=4096,'Packet timing line exceeds its bound')
        for line in lines:
            line=line.strip()
            if not line:continue
            values=dict(part.split(b'=',1) for part in line.split(b'|') if b'=' in part)
            try:pts=int(values[b'pts']);dts=int(values[b'dts']);duration=int(values[b'duration'])
            except (KeyError,ValueError):raise preservation.Refused('Packet timing cannot be verified')
            skip=values.get(b'skip_samples',b'0');discard=values.get(b'discard_padding',b'0')
            if self.origin is None:self.origin=pts
            if b'C' in values.get(b'flags',b''):self.corrupt.append(self.seen)
            if self.seen<self.count:self.prefix.update(b'%d,%d,%d,%s,%s\n'%(pts-self.origin,dts-self.origin,duration,skip,discard))
            else:self.after.append(duration)
            self.seen+=1

def prove_silenced_tail(source,output,plan,stage,stop,expected,encoding,*,evidence,run):
    """Decode-level proof for the truncated-final-frames repair (replaces whole-file equality).

    1. Decoder configuration and presentation equal (copied_audio_evidence, source-relative).
    2. Packets: the first N (intact) packets have identical relative timing; the source has N
       packets, or N+1 with the last flagged corrupt; the output has N+k, none corrupt, and the k
       replaced packets keep exactly the source's sample durations.
    3. PCM: the output decodes completely under -xerror; its PCM starts with exactly the PCM of
       the source's intact frames (lenient decode, which drops the cut frame); every sample from
       the second replaced frame's slot onward is exactly 0.0. The first replaced slot carries
       the last intact frame's MDCT overlap tail, i.e. that frame's own completion.
    Returns (output_evidence, output_pcm, proof) for the job's validation.
    """
    record=silenced(plan);preservation.need(record is not None,'No silence repair in this plan')
    intact=record['first_frame'];frames=record['frames'];channels=encoding['channels']
    preservation.need(channels==record['channels'],'Silence repair channel layout differs')
    source_evidence=evidence(source,stage,stop,expected,source_relative=True)
    output_evidence=evidence(output,stage,stop,expected,source_relative=True)
    for key in ('decoder_configuration','presentation'):
        preservation.need(source_evidence[key]==output_evidence[key],'Silence repair changed decoder or presentation')
    ffprobe=shutil.which('ffprobe');ffmpeg=shutil.which('ffmpeg')
    preservation.need(ffprobe and ffmpeg,'Installed ffmpeg is required for the silence repair proof')
    def packets(path):
        telemetry=_Packets(intact)
        run([ffprobe,'-v','error','-protocol_whitelist','file','-f','mov','-select_streams','a:0','-show_packets','-show_entries',
             'packet=pts,dts,duration,flags:packet_side_data=side_data_type,skip_samples,discard_padding','-of','compact=p=0:nk=0',str(path)],
            stage,stop,max(300,expected*2),telemetry=telemetry)
        if telemetry.pending.strip():telemetry.feed(b'\n')
        return telemetry
    before=packets(source);after=packets(output)
    preservation.need(before.prefix.hexdigest()==after.prefix.hexdigest(),'Silence repair changed intact packet timing')
    preservation.need(before.seen==intact and not before.corrupt or before.seen==intact+1 and before.corrupt==[intact],'Source damage differs from the approved repair')
    preservation.need(after.seen==intact+frames and not after.corrupt,'Repaired packets are incomplete')
    preservation.need(len(after.after)==frames and sum(after.after)==record['replaced_ticks'],'Replaced frames changed duration')
    def decode(path,strict,telemetry):
        run([ffmpeg,'-hide_banner','-v','error',*(['-xerror'] if strict else []),'-nostdin','-threads','2','-filter_threads','1','-protocol_whitelist','file',
             '-f','mov','-i',str(path),'-map','0:a:0','-c:a','pcm_f64le','-f','f64le','pipe:1'],stage,stop,max(300,expected*2),telemetry=telemetry)
    frame=channels*8;reference=_Pcm(frame);decode(source,False,reference)
    preservation.need(reference.bytes and reference.bytes%frame==0,'Source intact audio did not decode')
    check=_Pcm(frame,limit=reference.bytes,zero_from=reference.bytes+preservation.AAC_FRAME*frame);decode(output,True,check)
    preservation.need(check.bytes%frame==0 and reference.bytes<check.bytes<=reference.bytes+frames*preservation.AAC_FRAME*frame,'Repaired audio length is not the intact audio plus the replaced frames')
    preservation.need(check.prefix.hexdigest()==reference.full.hexdigest(),'Silence repair changed intact decoded audio')
    preservation.need(check.nonzero==0,'Replaced frames do not decode to silence')
    output_pcm={'sha256':check.full.hexdigest(),'sample_count':check.bytes//frame,'bytes':check.bytes,'sample_format':'pcm_f64le',
                'sample_rate':encoding['sample_rate'],'channels':channels,'channel_layout':encoding.get('channel_layout')}
    proof={'intact_pcm_sha256':reference.full.hexdigest(),'intact_samples':reference.bytes//frame,
           'replaced_samples':(check.bytes-reference.bytes)//frame,'intact_packets':intact,'replaced_packets':frames}
    return output_evidence,output_pcm,proof
