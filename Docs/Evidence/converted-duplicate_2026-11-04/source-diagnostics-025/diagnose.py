import base64,hashlib,json,os,pathlib,struct,sys,threading,time
root=pathlib.Path(__file__).resolve().parent
source=pathlib.Path('C:/Antigravity Projects/Worktrees/Books Arranger/converted-duplicate-20261104')
main=pathlib.Path('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger')
sys.path.insert(0,str(source));sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
from native_io import DirectoryBoundary,VerifiedFile,ordinary
from audio_pipeline import run_owned,ValidationError
start=time.monotonic();deadline=start+570;stop=threading.Event();output={'started_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'m4b':[],'koontz':[]};total_read=0
def save():
    (root/'diagnostic.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def check_time():
    if time.monotonic()>=deadline:raise TimeoutError('Approved diagnostic elapsed bound reached; no duplicate run')
def stable(file,expected,before=None):
    now=file.refresh()
    if now['size']!=expected['size'] or str(now['modified'])!=str(expected['modified']):raise RuntimeError('Source size/time differs from approved catalog snapshot')
    if before and any(now[key]!=before[key] for key in ('identity','identity_method','dev','ino','size','modified')):raise RuntimeError('Source native identity changed during diagnostic')
    return now
def boxes(data,start=0,end=None):
    end=len(data) if end is None else end;result=[];at=start
    while at<end:
        if end-at<8:raise ValueError('Incomplete box header')
        size,kind=struct.unpack_from('>I4s',data,at);header=8
        if size==1:
            if end-at<16:raise ValueError('Incomplete extended box')
            size=struct.unpack_from('>Q',data,at+8)[0];header=16
        elif size==0:size=end-at
        if size<header or at+size>end:raise ValueError('Nested box extent invalid')
        result.append((kind,at,header,size));at+=size
        if len(result)>10000:raise ValueError('Metadata box count cap')
    return result
def child(data,kind):
    values=[data[at+header:at+size] for actual,at,header,size in boxes(data) if actual==kind]
    return values[0] if len(values)==1 else None
def table_summary(data):
    result={}
    for kind,at,header,size in boxes(data):
        payload=data[at+header:at+size];name=kind.decode('latin1')
        if kind==b'stsd':result[name]={'bytes':len(payload),'base64':base64.b64encode(payload).decode()}
        elif kind==b'stsz' and len(payload)>=12:
            fixed,count=struct.unpack_from('>II',payload,4);sizes=[fixed]*min(count,32) if fixed else [struct.unpack_from('>I',payload,12+4*i)[0] for i in range(min(count,32))]
            result[name]={'fixed_sample_size':fixed,'sample_count':count,'first_sample_sizes':sizes,'bytes':len(payload)}
        elif kind in (b'stsc',b'stco',b'co64',b'stts') and len(payload)>=8:result[name]={'entry_count':struct.unpack_from('>I',payload,4)[0],'prefix_base64':base64.b64encode(payload[:128]).decode(),'bytes':len(payload)}
    return result
def moov_summary(data):
    tracks=[]
    for kind,at,header,size in boxes(data):
        if kind!=b'trak':continue
        trak=data[at+header:at+size];mdia=child(trak,b'mdia');hdlr=child(mdia,b'hdlr') if mdia else None
        minf=child(mdia,b'minf') if mdia else None;stbl=child(minf,b'stbl') if minf else None
        tracks.append({'handler':hdlr[8:12].decode('latin1') if hdlr and len(hdlr)>=12 else None,
            'tkhd_base64':base64.b64encode(child(trak,b'tkhd') or b'').decode(),
            'tref_base64':base64.b64encode(child(trak,b'tref') or b'').decode(),
            'tables':table_summary(stbl) if stbl else {}})
    return tracks
snapshot=json.loads((main/'Docs/Evidence/converted-duplicate_2026-11-04/m4b-unsupported-readonly/snapshot.json').read_text('utf8'))
first=json.loads((main/'Docs/Evidence/converted-duplicate_2026-11-04/m4b-unsupported-readonly/first-title.json').read_text('utf8'))
targets=[]
for item in first:
    manifest=json.loads(item['job']['manifest']);targets.append((manifest['metadata']['title'],manifest['sources'][0]))
names={'Splatterpunk stories 3','Последняя глава','Сборник рассказов японских авторов Сад Камней'}
for group in snapshot['groups']:
    review=json.loads(group['review'] or '{}')
    if group['superseded'] or review.get('title') not in names:continue
    members=json.loads(group['evidence'])['members']
    if len(members)!=1:raise RuntimeError('Approved M4B source count changed')
    record=next(file for file in snapshot['files'] if file['path']==members[0]['path']);targets.append((review['title'],record))
if len(targets)!=4:raise RuntimeError('Approved exact four-source set unavailable')
try:
    for index,(title,expected) in enumerate(targets):
        check_time();path=ordinary(expected['path']);item={'title':title,'path':str(path),'expected_size':expected['size'],'boxes':[]};output['m4b'].append(item)
        with DirectoryBoundary(path.anchor,path.parent),VerifiedFile(path) as file:
            before=stable(file,expected);item['native_before']=before;consumed=0;at=0
            def read(offset,count):
                global total_read
                check_time()
                if count<0 or offset<0 or offset+count>before['size']:raise RuntimeError('Read escaped exact source extent')
                if item.get('metadata_bytes_read',0)+count>8*1024*1024 or total_read+count>32*1024*1024:raise RuntimeError('Approved metadata byte cap reached')
                value=file.read_at(offset,count)
                if len(value)!=count:raise RuntimeError('Short source read')
                item['metadata_bytes_read']=item.get('metadata_bytes_read',0)+count;total_read+=count;return value
            while at<before['size']:
                if len(item['boxes'])>=4096:raise RuntimeError('Top-level box count cap')
                if before['size']-at<8:item['structure_error']='Trailing incomplete top-level box header';break
                raw=read(at,min(16,before['size']-at));size,kind=struct.unpack_from('>I4s',raw);header=8
                if size==1:
                    if len(raw)<16:item['structure_error']='Incomplete top-level extended header';break
                    size=struct.unpack_from('>Q',raw,8)[0];header=16
                elif size==0:size=before['size']-at
                box={'kind':kind.decode('latin1'),'offset':at,'declared_size':size,'header_base64':base64.b64encode(raw).decode()};item['boxes'].append(box)
                if size<header or at+size>before['size']:item['structure_error']='Top-level extent invalid';break
                if kind==b'moov':
                    moov=read(at+header,size-header);(root/('moov-'+str(index)+'.bin')).write_bytes(moov)
                    item['moov_sha256']=hashlib.sha256(moov).hexdigest();item['tracks']=moov_summary(moov)
                at+=size
            item['native_after']=stable(file,expected,before);save()
            if expected['size']==2097152:
                try:run_owned([str(main/'build-cache/qa-runtime/ffmpeg/ffmpeg.exe'),'-v','error','-xerror','-err_detect','explode','-nostdin','-threads','2','-i',str(path),'-map','0:a:0','-vn','-sn','-dn','-f','null','-'],root,stop,min(120,deadline-time.monotonic()),1024*1024)
                except ValidationError as error:item['strict_decode_error']={'class':type(error).__name__,'message':str(error)}
                else:item['strict_decode']='passed'
                item['native_after_decode']=stable(file,expected,before);save()
    koontz=json.loads((main/'Docs/Evidence/converted-duplicate_2026-11-04/koontz-stopped-readonly/snapshot.json').read_text('utf8'))
    matches=[row for row in koontz['jobs'] if row['job_id']=='75e98ca5-3cae-4e9b-a95e-b0b2a9c10715']
    if len(matches)!=1:raise RuntimeError('Approved Koontz job changed')
    sources=json.loads(matches[0]['manifest'])['sources']
    if len(sources)!=57 or sum(s['size'] for s in sources)!=501440217:raise RuntimeError('Approved Koontz source count/bytes changed')
    for index,expected in enumerate(sources):
        check_time();path=ordinary(expected['path']);item={'index':index+1,'path':str(path),'expected_size':expected['size']};output['koontz'].append(item)
        with DirectoryBoundary(path.anchor,path.parent),VerifiedFile(path) as file:
            before=stable(file,expected);item['native_before']=before
            try:run_owned([str(main/'build-cache/qa-runtime/ffmpeg/ffmpeg.exe'),'-v','error','-xerror','-err_detect','explode','-nostdin','-threads','2','-i',str(path),'-map','0:a:0','-vn','-sn','-dn','-f','null','-'],root,stop,min(120,deadline-time.monotonic()),1024*1024)
            except ValidationError as error:item['strict_decode_error']={'class':type(error).__name__,'message':str(error)}
            else:item['strict_decode']='passed'
            item['native_after']=stable(file,expected,before);save()
        if 'strict_decode_error' in item:break
    output['complete']=True
except BaseException as error:
    output['stopped']={'class':type(error).__name__,'message':str(error)};save();raise
finally:
    output['elapsed_seconds']=time.monotonic()-start;output['metadata_bytes_read']=total_read;save()
print(json.dumps({'complete':output.get('complete'),'elapsed_seconds':output['elapsed_seconds'],'metadata_bytes_read':total_read,'m4b':[{'title':item['title'],'structure_error':item.get('structure_error'),'strict_decode_error':item.get('strict_decode_error'),'tracks':[{'handler':t['handler'],'stsd':t['tables'].get('stsd'),'stsz':t['tables'].get('stsz')} for t in item.get('tracks',[])]} for item in output['m4b']],'koontz':output['koontz']},ensure_ascii=True))
