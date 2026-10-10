"""Owned immutable-source M4B staging and strict validation; no source rewrites."""
import hashlib,json,math,os,shutil,subprocess,time,uuid,threading,contextlib
from pathlib import Path
from native_io import DirectoryBoundary,publish_no_replace,BoundaryError,ordinary,ProtectedFiles,OwnedProcessJob

from encoding_policy import PROFILE, LEGACY_PROFILE, freeze_policy, choose_encoding
from quicktime_chapters import normalize
MAX_IMAGE=8*1024*1024
INPUT_FORMATS={'.mp3':'mp3','.m4a':'mov','.m4b':'mov','.aac':'aac','.flac':'flac','.ogg':'ogg','.opus':'ogg','.wav':'wav','.wma':'asf','.png':'image2','.jpg':'image2','.jpeg':'image2'}

class Paused(InterruptedError):pass
class ValidationError(ValueError):pass

def digest(path,stop=None):
    value=hashlib.sha256()
    with open(path,'rb') as stream:
        while block:=stream.read(1024*1024):
            if stop is not None and stop.is_set():raise Paused('Operation paused; this book will restart')
            value.update(block)
    return value.hexdigest()

def fingerprint(path):
    with open(path,'rb') as stream:item=os.fstat(stream.fileno())
    return {'size':item.st_size,'modified':str(item.st_mtime_ns)}

def same_source(item,stop):
    current=fingerprint(item['path'])
    if current!={'size':item['size'],'modified':str(item['modified'])} or digest(item['path'],stop)!=item['sha256']:
        raise ValidationError('Source changed — review required: '+item['path'])

def copy_owned(source,destination,expected,stop):
    destination=Path(destination)
    value=hashlib.sha256()
    with open(source,'rb') as incoming,open(destination,'xb') as outgoing:
        while block:=incoming.read(1024*1024):
            if stop.is_set():raise Paused('Operation paused; this book will restart')
            outgoing.write(block);value.update(block)
        outgoing.flush();os.fsync(outgoing.fileno())
    if value.hexdigest()!=expected:raise ValidationError('Copied bytes do not match the approved source/output hash')

def run_owned(arguments,directory,stop,deadline=300,max_output=8*1024*1024):
    """Only the owned FFmpeg/FFprobe child is canceled; diagnostic output is bounded."""
    directory=Path(directory)
    token=uuid.uuid4().hex
    stdout=directory/(token+'.stdout');stderr=directory/(token+'.stderr')
    with open(stdout,'xb') as out,open(stderr,'xb') as err:
        process=subprocess.Popen(arguments,stdin=subprocess.DEVNULL,stdout=out,stderr=err,
            shell=False,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'BELOW_NORMAL_PRIORITY_CLASS',0)|4)
        process._books_suspended=True
        started=time.monotonic()
        try:
            with OwnedProcessJob(process):
                while process.poll() is None:
                    if stop.is_set():raise Paused('Audiobook operation paused; interrupted book restarts')
                    if time.monotonic()-started>deadline:raise TimeoutError('Owned media operation exceeded its deadline')
                    if stdout.stat().st_size>max_output or stderr.stat().st_size>1024*1024:
                        raise ValidationError('Media diagnostic output exceeded its limit')
                    time.sleep(.1)
        finally:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=3)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
    raw=stdout.read_bytes();error=stderr.read_bytes()
    if len(raw)>max_output or len(error)>1024*1024:raise ValidationError('Media diagnostic output exceeded its limit')
    if process.returncode:raise ValidationError(error.decode('utf-8','replace')[-2000:] or 'Media operation failed')
    return raw

def probe(path,stage,stop):
    executable=shutil.which('ffprobe')
    if not executable:raise ValidationError('Installed ffprobe is required for output checks')
    format=INPUT_FORMATS.get(Path(path).suffix.lower())
    if not format:raise ValidationError('Unsupported media input format')
    raw=run_owned([executable,'-v','error','-protocol_whitelist','file','-f',format,'-show_format','-show_streams','-show_chapters','-of','json',str(path)],stage,stop,30)
    return json.loads(raw)

def audio_info(raw):
    audio=[stream for stream in raw.get('streams',[]) if stream.get('codec_type')=='audio']
    if len(audio)!=1:raise ValidationError('Exactly one readable source audio stream is required')
    stream=audio[0]
    try:duration=float(raw.get('format',{}).get('duration'))
    except (ValueError,TypeError):raise ValidationError('Source duration is unknown')
    if not math.isfinite(duration) or duration<=0:raise ValidationError('Source duration is invalid')
    return duration,(stream.get('codec_name'),str(stream.get('sample_rate')),stream.get('channels'))

def decoded_duration(path,stage,stop,estimated):
    """Count decoded PCM frames; MP3 TLEN/bitrate estimates are not completeness facts."""
    stderr=Path(stage)/(uuid.uuid4().hex+'.decode-stderr')
    state={'bytes':0,'error':None}
    with open(stderr,'xb') as errors:
        args=[shutil.which('ffmpeg'),'-hide_banner','-v','error','-xerror','-nostdin','-threads','2','-filter_threads','1',
          '-protocol_whitelist','file','-f',INPUT_FORMATS[Path(path).suffix.lower()],'-i',str(path),'-map','0:a:0','-ar','44100','-ac','2','-c:a','pcm_s16le','-f','s16le','pipe:1']
        process=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=errors,shell=False,
          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'BELOW_NORMAL_PRIORITY_CLASS',0)|4)
        process._books_suspended=True
        def consume():
            try:
                while block:=process.stdout.read(64*1024):state['bytes']+=len(block)
            except Exception as error:state['error']=str(error)
        thread=threading.Thread(target=consume,daemon=True);thread.start()
        started=time.monotonic()
        try:
            with OwnedProcessJob(process):
                while process.poll() is None:
                    if stop.is_set():raise Paused('Decode verification paused; this book restarts')
                    if time.monotonic()-started>max(300,estimated*2):raise TimeoutError('Owned decode verification exceeded its deadline')
                    if stderr.stat().st_size>1024*1024:raise ValidationError('Decode diagnostics exceeded their limit')
                    time.sleep(.05)
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=3)
            thread.join(3)
            process.stdout.close()
        if thread.is_alive():raise ValidationError('Owned decoder output has not finished draining')
    if state['error'] or process.returncode or state['bytes']%4:
        raise ValidationError('Full audio decode failed: '+stderr.read_text(encoding='utf-8',errors='replace')[-1000:])
    if not state['bytes']:raise ValidationError('Audio decoder produced no samples')
    return state['bytes']/4/44100

def ffmetadata_escape(value):
    return str(value).replace('\\','\\\\').replace('=','\\=').replace(';','\\;').replace('#','\\#').replace('\r','').replace('\n','\\\n')

def snapshot_manifest(manifest,stage,stop):
    sources=manifest['sources']
    if not sources:raise ValidationError('No reviewed source files are included')
    root=ordinary(manifest['root'])
    copies=[];durations=[];profiles=[];compatibility=None
    total_bytes=sum(item['size'] for item in sources)
    if shutil.disk_usage(stage).free<total_bytes*2+32*1024*1024:
        raise ValidationError('Insufficient private staging space for snapshots and audiobook output')
    for index,item in enumerate(sources):
        source=ordinary(item['path'])
        try:source.relative_to(root)
        except ValueError:raise ValidationError('Source is outside the configured audiobook library')
        if source.suffix.lower() not in {'.mp3','.m4a','.aac','.flac','.ogg','.opus','.wav','.wma'}:
            raise ValidationError('This source format is not supported by the merge path')
        same_source(item,stop)
        alias=stage/(f'source{index:05}'+source.suffix.lower())
        copy_owned(source,alias,item['sha256'],stop)
        same_source(item,stop)
        # Read bitrate/profile and PCM duration from the same protected, hash-verified bytes.
        with ProtectedFiles([alias]):
            if digest(alias,stop)!=item['sha256']:raise ValidationError('Protected snapshot differs from reviewed source bytes')
            raw=probe(alias,stage,stop)
            duration,profile=audio_info(raw)
            if manifest.get('profile')==LEGACY_PROFILE and compatibility is not None and compatibility!=profile:
                raise ValidationError('Included files have incompatible recording/audio stream parameters')
            compatibility=profile
            stream=next(s for s in raw['streams'] if s.get('codec_type')=='audio')
            profiles.append((*profile,stream.get('bit_rate')))
            duration=decoded_duration(alias,stage,stop,duration)
        durations.append(duration);copies.append(alias.name)
    cover=manifest['cover']
    cover_source=ordinary(cover['path'])
    if cover_source.stat().st_size>MAX_IMAGE:raise ValidationError('Selected cover exceeds8 MiB')
    cover_bytes=cover_source.read_bytes()
    extension='.png' if cover_bytes.startswith(b'\x89PNG\r\n\x1a\n') else '.jpg' if cover_bytes.startswith(b'\xff\xd8\xff') else None
    if extension is None:raise ValidationError('Select one usable JPEG or PNG cover')
    cover_copy=stage/('cover'+extension)
    copy_owned(cover_source,cover_copy,cover['sha256'],stop)
    image=probe(cover_copy,stage,stop)
    image_streams=[s for s in image.get('streams',[]) if s.get('codec_type')=='video']
    if len(image_streams)!=1 or image_streams[0].get('width',0)*image_streams[0].get('height',0)>16000000:
        raise ValidationError('Selected cover dimensions are invalid or too large')
    return copies,durations,cover_copy,profiles

def create_private(manifest,stage_root,stop,progress=lambda *_:None):
    identity=manifest['job_id']
    if str(uuid.UUID(identity))!=identity:raise ValidationError('Invalid owned job identity')
    attempt=manifest.get('attempt_id') or str(uuid.uuid4())
    if str(uuid.UUID(attempt))!=attempt:raise ValidationError('Invalid owned attempt identity')
    stage_root=ordinary(stage_root)
    job=stage_root/identity;stage=job/attempt
    frozen={key:value for key,value in manifest.items() if key!='attempt_id'}
    with DirectoryBoundary(stage_root.parent,stage_root,create=True):
        with DirectoryBoundary(stage_root,job,create=True):
            marker=job/'ownership.json'
            if marker.exists():
                if json.loads(marker.read_text(encoding='utf-8'))!={'job_id':identity,'manifest':frozen}:
                    raise BoundaryError('Existing private job directory has different ownership')
            else:
                with open(marker,'x',encoding='utf-8') as stream:
                    json.dump({'job_id':identity,'manifest':frozen},stream,ensure_ascii=False)
                    stream.flush();os.fsync(stream.fileno())
            if stage.exists():raise BoundaryError('Existing attempt directory is not reused or overwritten')
            with DirectoryBoundary(job,stage,create=True):
                progress('Checking sources',{})
                copies,durations,cover,profiles=snapshot_manifest(manifest,stage,stop)
                with ProtectedFiles([stage/name for name in copies]+[cover]):
                    for name,item in zip(copies,manifest['sources']):
                        if digest(stage/name,stop)!=item['sha256']:raise ValidationError('Protected snapshot differs from reviewed source bytes')
                    if digest(cover,stop)!=manifest['cover']['sha256']:raise ValidationError('Protected cover differs from reviewed artwork')
                    if manifest.get('profile')==PROFILE:
                        if manifest.get('encoding_policy')!=freeze_policy(manifest['sources']):raise ValidationError('Frozen encoding policy changed')
                        encoding=choose_encoding(profiles)
                    elif manifest.get('profile')==LEGACY_PROFILE:
                        encoding={'bitrate':160000,'channels':2,'sample_rate':44100,'selection':'legacy fixed profile'}
                    else:raise ValidationError('Unsupported frozen encoding profile')
                    return _encode_private(manifest,stage,copies,durations,cover,stop,progress,encoding)

def _encode_private(manifest,stage,copies,durations,cover,stop,progress,encoding):
    executable=shutil.which('ffmpeg')
    if not executable:raise ValidationError('Installed ffmpeg is required for audiobook creation')
    (stage/'inputs.txt').write_text(''.join(f"file '{name}'\n" for name in copies),encoding='utf-8')
    review=manifest['metadata'];comments=manifest.get('comments','')
    if review.get('series'):
        comments+=('\n' if comments else '')+f"Series: {review['series']}\nSeries number: {review.get('number','')}"
    if review.get('narrator') and ('Narrator: '+review['narrator']) not in comments.splitlines():
        comments+=('\n' if comments else '')+'Narrator: '+review['narrator']
    # Keep edition clues distinct from canonical original-work identity. Unknown
    # private source tags remain losslessly recorded in the durable job manifest.
    edition=[]
    for item in manifest['sources']:
        source_metadata=item.get('metadata',{})
        for key,value in source_metadata.get('tags',{}).items():
            if key.casefold() in {'album','date','year','composer','publisher','copyright','language'} and value:
                line='Source '+key+': '+str(value)
                if line not in edition:edition.append(line)
        if source_metadata.get('edition_language'):
            line='Recording language: '+str(source_metadata['edition_language'])
            if line not in edition:edition.append(line)
    if edition:comments+=('\n' if comments else '')+'\n'.join(edition)
    tags={'title':review['title'],'album':review['title'],'artist':review['canonical_author'],
      'album_artist':review['canonical_author'],'genre':'Audiobook','media_type':'2','comment':comments}
    if review.get('series'):
        tags['album']=' - '.join([review['series'],review.get('number',''),review['title']])
        tags['grouping']=review['series']
        tags['sort_album']=tags['album']
        if str(review.get('number','')).isdigit() and 0<int(review['number'])<65536:
            tags['track']=str(int(review['number']))
    output=stage/'checked.m4b'
    args=[executable,'-hide_banner','-v','error','-xerror','-nostdin','-n','-threads','2','-filter_threads','1','-protocol_whitelist','file',
      '-format_whitelist','concat,mp3,mov,aac,flac,ogg,wav,asf','-f','concat','-safe','1','-i',str(stage/'inputs.txt'),'-f','image2','-i',str(cover)]
    chapters=[]
    if manifest.get('chapters'):
        if len(manifest['chapters'])!=len(copies):raise ValidationError('Chapter plan must match the reviewed source boundaries')
        chapter_file=stage/'chapters.txt';text=';FFMETADATA1\n';position=0
        for name,duration in zip(manifest['chapters'],durations):
            start=round(position*1000);position+=duration;end=round(position*1000)
            chapters.append({'start':start,'end':end,'title':str(name)})
            text+=f'[CHAPTER]\nTIMEBASE=1/1000\nSTART={start}\nEND={end}\ntitle={ffmetadata_escape(name)}\n'
        chapter_file.write_text(text,encoding='utf-8',newline='\n')
        args+=['-f','ffmetadata','-i',str(chapter_file),'-map_chapters','2']
    else:args+=['-map_chapters','-1']
    args+=['-map','0:a:0','-map','1:v:0','-map_metadata:g','-1','-af','asetpts=N/SR/TB','-c:a','aac','-b:a',str(encoding['bitrate']),'-ar',str(encoding['sample_rate']),'-ac',str(encoding['channels']),'-threads:a','2','-c:v','copy','-disposition:v:0','attached_pic','-movflags','+faststart+disable_chpl']
    for name,value in tags.items():args+=['-metadata',name+'='+value]
    args+=['-f','mp4',str(output)]
    progress('Creating audio',{'duration':sum(durations),'source_durations':durations,'source_pcm_frames':[round(d*44100) for d in durations],'source_pcm_rate':44100,'encoding':encoding})
    run_owned(args,stage,stop,max(300,sum(durations)*2))
    chapter_format=None
    if chapters:
        compatible=stage/'compatible.m4b'
        chapter_format=normalize(output,compatible,stop)
        output=compatible
    progress('Checking output',{})
    validation=validate(output,manifest,durations,chapters,stage,stop,encoding)
    if chapter_format:validation['chapter_format']=chapter_format
    for item in manifest['sources']:same_source(item,stop)
    if digest(manifest['cover']['path'],stop)!=manifest['cover']['sha256']:raise ValidationError('Selected cover changed — review required')
    return output,validation

def validate(output,manifest,durations,chapters,stage,stop,encoding=None):
    raw=probe(output,stage,stop)
    duration,profile=audio_info(raw)
    encoding=encoding or {'bitrate':160000,'channels':2,'sample_rate':44100,'selection':'legacy fixed profile'}
    if profile!=('aac',str(encoding['sample_rate']),encoding['channels']):raise ValidationError('Output audio profile is incorrect')
    expected=sum(durations);tolerance=max(.25,len(durations)*.1)
    if abs(duration-expected)>tolerance:raise ValidationError(f'Output duration differs from reviewed sources: expected{expected:.3f}s, actual{duration:.3f}s, tolerance{tolerance:.3f}s')
    pictures=[s for s in raw.get('streams',[]) if s.get('codec_type')=='video' and s.get('disposition',{}).get('attached_pic')==1]
    if len(pictures)!=1:raise ValidationError('Output must contain exactly one attached cover')
    if any(s.get('codec_type')=='video' and s not in pictures for s in raw.get('streams',[])):raise ValidationError('Unexpected video stream in audiobook output')
    tags={k.lower():str(v) for k,v in raw.get('format',{}).get('tags',{}).items()}
    review=manifest['metadata']
    expected_tags=[('title',review['title']),('artist',review['canonical_author']),('album_artist',review['canonical_author']),('media_type','2')]
    if review.get('series'):
        expected_tags += [('grouping',review['series']),('album',' - '.join([review['series'],review.get('number',''),review['title']]))]
        if str(review.get('number','')).isdigit() and 0<int(review['number'])<65536:expected_tags.append(('track',str(int(review['number']))))
    for key,value in expected_tags:
        if tags.get(key)!=value:raise ValidationError('Output metadata check failed: '+key)
    picture=Path(stage)/(uuid.uuid4().hex+('.png' if pictures[0].get('codec_name')=='png' else '.jpg'))
    run_owned([shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-protocol_whitelist','file','-i',str(output),'-map','0:v:0','-c:v','copy','-frames:v','1',str(picture)],stage,stop,30)
    if digest(picture,stop)!=manifest['cover']['sha256']:raise ValidationError('Attached cover bytes differ from the reviewed artwork')
    actual=raw.get('chapters',[])
    if len(actual)!=len(chapters):raise ValidationError('Output chapter count does not match the reviewed optional plan')
    for item,wanted in zip(actual,chapters):
        if item.get('tags',{}).get('title')!=wanted['title'] or abs(float(item['start_time'])-wanted['start']/1000)>.05 or abs(float(item['end_time'])-wanted['end']/1000)>.05:
            raise ValidationError('QuickTime chapter titles/boundaries differ from the reviewed plan')
    actual_samples_duration=decoded_duration(output,stage,stop,expected)
    if abs(actual_samples_duration-expected)>tolerance:
        raise ValidationError('Decoded output samples do not match the reviewed source audio')
    return {'profile':manifest.get('profile',LEGACY_PROFILE),'encoding':encoding,'duration':duration,'expected_duration':expected,'duration_tolerance':tolerance,
      'sha256':digest(output,stop),'size':output.stat().st_size,'chapters':chapters,
      'source_durations':durations,'source_pcm_frames':[round(d*44100) for d in durations],'source_pcm_rate':44100,'decoded_duration':actual_samples_duration,'checks':'Output checks passed','device':'Apple Books sync not checked','tags':tags}

def publish(output,manifest,validation,stop,journal,revision_guard,review_lock=None):
    destination=ordinary(manifest['destination']);root=ordinary(manifest['root'])
    if destination.suffix.lower()!='.m4b':raise ValidationError('Only a reviewed M4B destination can be published')
    if any(os.path.normcase(str(destination))==os.path.normcase(item['path']) for item in manifest['sources']):raise ValidationError('Output must be distinct from every source')
    for item in manifest['sources']:same_source(item,stop)
    if not revision_guard():raise ValidationError('Candidate review changed — review required')
    with DirectoryBoundary(root,destination.parent,create=True) as boundary:
        if destination.exists():raise FileExistsError('An audiobook already exists at this path; nothing was overwritten')
        if shutil.disk_usage(destination.parent).free<validation['size']+16*1024*1024:raise ValidationError('Insufficient destination space')
        temporary=destination.parent/('.books-arranger-'+manifest['job_id']+'-'+manifest.get('attempt_id',str(uuid.uuid4()))+'.partial')
        journal('copying',{'temporary':str(temporary),'destination':str(destination),'validation':validation,'parent_identity':boundary.identities})
        copy_owned(output,temporary,validation['sha256'],stop)
        if stop.is_set():raise Paused('Publication paused; owned temporary retained for recovery')
        for item in manifest['sources']:same_source(item,stop)
        if digest(manifest['cover']['path'],stop)!=manifest['cover']['sha256']:raise ValidationError('Cover changed — review required')
        with review_lock if review_lock is not None else contextlib.nullcontext():
            if not revision_guard():raise ValidationError('Candidate review changed — review required')
            boundary.revalidate()
            journal('publishing',{'temporary':str(temporary),'destination':str(destination),'validation':validation,'parent_identity':boundary.identities})
            publish_no_replace(temporary,destination,boundary,validation['sha256'],validation['size'])
        if digest(destination)!=validation['sha256']:raise ValidationError('Published output hash did not match the checked artifact')
        journal('completed',{'destination':str(destination),'validation':validation})
    return str(destination)
