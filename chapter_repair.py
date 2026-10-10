"""Owned, explicit one-off chapter restoration. No arbitrary destination or in-place edit."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import uuid
from audio_pipeline import (ValidationError, Paused, copy_owned, digest, probe,
    run_owned, ffmetadata_escape, publish, same_source)
from native_io import DirectoryBoundary, ProtectedFiles, OwnedProcessJob, ordinary
from quicktime_chapters import normalize

def streaming_receipt(arguments,stage,stop,lines=False):
    """Aggregate owned stdout without retaining unbounded packet or PCM output."""
    errors=stage/(uuid.uuid4().hex+'.stderr')
    result={'bytes':0,'sha256':None,'first':None,'last':None,'lines':0}
    failure=[]
    with errors.open('xb') as err:
        process=subprocess.Popen(arguments,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=err,
            shell=False,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'BELOW_NORMAL_PRIORITY_CLASS',0)|4)
        process._books_suspended=True
        def consume():
            try:
                h=hashlib.sha256()
                if lines:
                    while line:=process.stdout.readline(65537):
                        if len(line)>65536:raise ValidationError('Packet diagnostic line exceeded its bound')
                        h.update(line);result['bytes']+=len(line);result['lines']+=1
                        text=line.decode('utf-8','strict').strip()
                        if result['first'] is None:result['first']=text
                        result['last']=text
                else:
                    while block:=process.stdout.read(65536):h.update(block);result['bytes']+=len(block)
                result['sha256']=h.hexdigest()
            except BaseException as error:failure.append(error)
        reader=threading.Thread(target=consume,daemon=True);reader.start();started=time.monotonic()
        try:
            with OwnedProcessJob(process):
                while process.poll() is None:
                    if failure:raise failure[0]
                    if stop.is_set():raise Paused('Chapter restoration stopped; originals remain unchanged')
                    if time.monotonic()-started>600:raise TimeoutError('Chapter verification exceeded its 600-second deadline')
                    if errors.stat().st_size>1024*1024:raise ValidationError('Media diagnostics exceeded their bound')
                    time.sleep(.05)
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=3)
            reader.join(3);process.stdout.close()
        if reader.is_alive() or failure or process.returncode:raise ValidationError('Owned media verification failed: '+errors.read_text(errors='replace')[-1000:])
    return result

def presentation(path,stage,stop):
    stream=json.loads(run_owned([shutil.which('ffprobe'),'-v','error','-protocol_whitelist','file','-f','mov',
        '-show_streams','-select_streams','a:0','-show_data_hash','sha256','-show_entries',
        'stream=codec_name,sample_rate,channels,channel_layout,time_base,start_pts,start_time,duration_ts,duration,extradata_hash',
        '-of','json',str(path)],stage,stop,30))['streams'][0]
    packets=streaming_receipt([shutil.which('ffprobe'),'-v','error','-protocol_whitelist','file','-f','mov',
        '-select_streams','a:0','-show_packets','-show_data_hash','sha256','-show_entries',
        'packet=pts,dts,duration,size,flags,data_hash:packet_side_data','-of','compact=p=0:nk=0',str(path)],stage,stop,True)
    pcm=streaming_receipt([shutil.which('ffmpeg'),'-v','error','-xerror','-nostdin','-threads','2','-filter_threads','1',
        '-protocol_whitelist','file','-f','mov','-i',str(path),'-map','0:a:0','-c:a','pcm_s16le','-f','s16le','pipe:1'],stage,stop)
    channels=int(stream['channels']);rate=int(stream['sample_rate'])
    if not pcm['bytes'] or pcm['bytes']%(2*channels):raise ValidationError('Invalid decoded presentation samples')
    pcm.update(frames=pcm['bytes']//(2*channels),sample_rate=rate,channels=channels)
    return {'stream':stream,'packets':packets,'pcm':pcm}

def restore(parent,boundaries,owned_root,stop,review_guard,review_lock=None):
    """Parent is a read-only completed job manifest plus recorded validation/output.

    Caller must verify the durable current catalog revision/evidence in review_guard.
    The helper derives output paths, never updates the original completed job.
    """
    manifest=parent['manifest'];record=parent['output']['validation'];source=ordinary(parent['output']['final_path'])
    if parent.get('state')!='completed' or source!=ordinary(manifest['destination']):raise ValidationError('A verified completed parent audiobook is required')
    if source.suffix.lower()!='.m4b':raise ValidationError('Chapter repair requires the validated M4B parent')
    destination=source.with_name(source.stem+' - Chapters v2.m4b')
    sources=manifest['sources'];rows=boundaries['tracks']
    if len(rows)!=len(sources) or not sources:raise ValidationError('Exact boundary proof must cover all reviewed sources')
    durations=[];position=0;chapters=[]
    for item,row in zip(sources,rows):
        if row['sha256']!=item['sha256'] or row['source_path']!=item['path']:raise ValidationError('Boundary proof differs from the reviewed source order')
        frames=row['pcm_frames'];rate=row['pcm_rate']
        if type(frames)is not int or frames<=0 or rate!=44100:raise ValidationError('Invalid exact source PCM boundary')
        duration=frames/rate;durations.append(duration)
        title=str(row['title'])
        if not title or len(title)>1024 or '\x00' in title:raise ValidationError('Source-track marker name needs review')
        start=round(position*1000);position+=duration
        chapters.append({'start':start,'end':round(position*1000),'title':title})
    if abs(position-record['expected_duration'])>.000001:raise ValidationError('Boundary proof does not match the validated parent source duration')
    if not review_guard():raise ValidationError('Parent source/review evidence changed — review required')
    for item in sources:same_source(item,stop)
    with DirectoryBoundary(manifest['root'],destination.parent):
        if destination.exists():raise FileExistsError('A corrected audiobook already exists; nothing was overwritten')
    job_id=str(uuid.uuid4());root=ordinary(owned_root);stage=root/job_id
    with DirectoryBoundary(root,stage,create=True) as cache:
        journal_path=stage/'corrected-artifact.jsonl'
        with journal_path.open('x',encoding='utf-8') as journal_file:
            def journal(state,data):
                journal_file.write(json.dumps({'job_id':job_id,'parent_job_id':manifest['job_id'],'state':state,'data':data},ensure_ascii=False)+'\n')
                journal_file.flush();os.fsync(journal_file.fileno())
            intent={'parent_output':str(source),'parent_sha256':record['sha256'],'parent_size':record['size'],
                'destination':str(destination),'parent_manifest_sha256':hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest(),
                'boundary_evidence_sha256':hashlib.sha256(json.dumps(boundaries,sort_keys=True).encode()).hexdigest(),
                'candidate_id':manifest['candidate_id'],'candidate_revision':manifest['candidate_revision'],'sources':sources,'chapters':chapters,
                'root':manifest['root'],'cover':manifest['cover'],
                'mode':'copy existing validated AAC; source-track navigation','profile':manifest['profile']}
            journal('intent',intent)
            with DirectoryBoundary(manifest['root'],source.parent),ProtectedFiles([source]):
                if source.stat().st_size!=record['size'] or digest(source,stop)!=record['sha256']:raise ValidationError('The original audiobook changed since validation; nothing was overwritten')
                alias=stage/'parent.m4b';copy_owned(source,alias,record['sha256'],stop)
                with ProtectedFiles([alias]):
                    if digest(alias,stop)!=record['sha256']:raise ValidationError('Parent snapshot changed')
                    before=probe(alias,stage,stop);before_presentation=presentation(alias,stage,stop)
                    text=';FFMETADATA1\n'
                    for chapter in chapters:text+=f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={chapter['start']}\nEND={chapter['end']}\ntitle={ffmetadata_escape(chapter['title'])}\n"
                    chapter_file=stage/'chapters.txt';chapter_file.write_text(text,encoding='utf-8',newline='\n')
                    output=stage/'checked.m4b'
                    run_owned([shutil.which('ffmpeg'),'-v','error','-xerror','-nostdin','-n','-threads','2',
                        '-protocol_whitelist','file','-f','mov','-i',str(alias),'-f','ffmetadata','-i',str(chapter_file),
                        '-map','0:a:0','-map','0:v:0','-map_metadata','0','-map_chapters','1','-c','copy',
                        '-disposition:v:0','attached_pic','-movflags','+faststart+disable_chpl','-f','mp4',str(output)],stage,stop,600)
                compatible=stage/'compatible.m4b'
                chapter_format=normalize(output,compatible,stop)
                output=compatible
                with ProtectedFiles([output]):
                    after=probe(output,stage,stop);after_presentation=presentation(output,stage,stop)
                    if before_presentation!=after_presentation:raise ValidationError('Audio payload, delay, timestamps or decoded presentation changed during chapter restoration')
                    for key in before['format'].get('tags',{}):
                        if key in ('major_brand','minor_version','compatible_brands','encoder'):continue
                        if before['format'].get('tags',{}).get(key)!=after['format'].get('tags',{}).get(key):raise ValidationError('Parent metadata changed during chapter restoration: '+key)
                    actual=after.get('chapters',[])
                    if len(actual)!=len(chapters):raise ValidationError('Restored chapter count differs')
                    for got,wanted in zip(actual,chapters):
                        if got.get('tags',{}).get('title')!=wanted['title'] or abs(float(got['start_time'])*1000-wanted['start'])>1 or abs(float(got['end_time'])*1000-wanted['end'])>1:raise ValidationError('Restored source-track names or boundaries differ: '+repr((got,wanted)))
                    cover_receipts=[]
                    for path in (alias,output):
                        cover_receipts.append(streaming_receipt([shutil.which('ffmpeg'),'-v','error','-nostdin','-protocol_whitelist','file','-f','mov','-i',str(path),'-map','0:v:0','-c','copy','-f','image2pipe','pipe:1'],stage,stop))
                    if cover_receipts[0]['sha256']!=cover_receipts[1]['sha256'] or cover_receipts[1]['sha256']!=manifest['cover']['sha256']:raise ValidationError('Parent cover bytes changed')
                    validation={'sha256':digest(output,stop),'size':output.stat().st_size,'chapters':chapters,'source_durations':durations,
                        'presentation':after_presentation,'chapter_format':chapter_format,'cover_sha256':cover_receipts[1]['sha256'],'profile':manifest['profile'],
                        'checks':'Audio copied without re-encoding; presentation and chapter checks passed','device':'Corrected chapter navigation not checked on iPhone'}
                    journal('validated',validation)
                repaired=dict(manifest,job_id=job_id,destination=str(destination),chapters=[c['title'] for c in chapters])
                cache.revalidate()
                final=publish(output,repaired,validation,stop,journal,review_guard,review_lock)
                return {'job_id':job_id,'parent_job_id':manifest['job_id'],'output':final,'journal':str(journal_path),'validation':validation}

def recover(journal_path,owned_root,stop,review_guard):
    """Recognize only this owned intent's exact already-published bytes after a crash.

    Returns a receipt without writing, adopting unrelated files or retrying conversion.
    """
    path=ordinary(journal_path);root=ordinary(owned_root)
    if path.name!='corrected-artifact.jsonl' or not path.parent.is_relative_to(root):raise ValidationError('Recovery journal is outside owned chapter repairs')
    with DirectoryBoundary(root,path.parent),ProtectedFiles([path]):
        if path.stat().st_size>2*1024*1024:raise ValidationError('Recovery journal exceeded its bound')
        events=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
        intent=events[0]
        if intent['state']!='intent' or intent['job_id']!=path.parent.name:raise ValidationError('Recovery journal ownership differs')
        if any(e['job_id']!=intent['job_id'] or e['parent_job_id']!=intent['parent_job_id'] for e in events):raise ValidationError('Recovery journal association differs')
        publishing=[e for e in events if e['state'] in ('publishing','completed')]
        if not publishing:raise ValidationError('No durable publication intent exists; no output was adopted')
        data=intent['data'];destination=ordinary(data['destination']);source=ordinary(data['parent_output'])
        allowed={source.with_name(source.stem+suffix) for suffix in (' - Chapters.m4b',' - Chapters v2.m4b')}
        if destination not in allowed:raise ValidationError('Recovery destination differs from the parent-derived path')
        validation=publishing[-1]['data']['validation']
        if publishing[-1]['data']['destination']!=str(destination):raise ValidationError('Publication intent differs from the corrected destination')
        if not review_guard():raise ValidationError('Recovery source/review evidence changed')
        with DirectoryBoundary(data['root'],destination.parent),ProtectedFiles([source,destination]):
            if digest(source,stop)!=data['parent_sha256'] or digest(destination,stop)!=validation['sha256'] or destination.stat().st_size!=validation['size']:raise ValidationError('Recovery cannot adopt unmatched parent/output bytes')
            for item in data['sources']:same_source(item,stop)
            if digest(data['cover']['path'],stop)!=data['cover']['sha256']:raise ValidationError('Recovery cover evidence changed')
            return {'job_id':intent['job_id'],'parent_job_id':intent['parent_job_id'],'output':str(destination),'validation':validation,'recovered_from_owned_intent':True}
