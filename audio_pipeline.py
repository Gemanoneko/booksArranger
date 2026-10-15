"""Owned immutable-source M4B staging and strict validation; no source rewrites."""
import hashlib,json,math,os,shutil,subprocess,time,uuid,threading,contextlib,struct,errno,sys
from pathlib import Path
from fractions import Fraction
from native_io import DirectoryBoundary,publish_no_replace,BoundaryError,ordinary,ProtectedFiles,OwnedProcessJob,VerifiedFile

from encoding_policy import PROFILE, LEGACY_PROFILE, freeze_policy, choose_encoding, AUTOMATIC_PROFILE, freeze_automatic_policy, choose_automatic_encoding
from quicktime_chapters import normalize
from metadata import audiobook_sort_title
import m4b_preservation
MAX_IMAGE=8*1024*1024
PRESERVATION_CANDIDATE_NAME='checked.m4b'
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
    plan_generated(destination)
    value=hashlib.sha256()
    with open(source,'rb') as incoming,open(destination,'xb') as outgoing:
        while block:=incoming.read(1024*1024):
            if stop.is_set():raise Paused('Operation paused; this book will restart')
            outgoing.write(block);value.update(block)
        outgoing.flush();os.fsync(outgoing.fileno())
    if value.hexdigest()!=expected:raise ValidationError('Copied bytes do not match the approved source/output hash')


_ARTIFACTS=threading.local()
@contextlib.contextmanager
def generated_artifacts(stage, observer=None, attempt_context=None):
    if attempt_context is not None:attempt_context['entered']=True
    previous=getattr(_ARTIFACTS,'current',None)
    receipts={};closure={'safe':True}
    _ARTIFACTS.current=(Path(stage),receipts,observer,closure)
    try:yield receipts
    finally:
        error=sys.exc_info()[1]
        _ARTIFACTS.current=previous
        if observer is not None:
            try:
                captured=observer.closed(Path(stage),producer_closed=closure['safe'])
                if captured:receipts.update(captured)
            except Exception:
                if error is None:raise  # Never replace the original conversion failure.


def plan_generated(path):
    current=getattr(_ARTIFACTS,'current',None)
    if current and current[2] is not None and Path(path).parent==current[0]:
        current[2].planned(current[0],Path(path))


def uncertain_producer():
    current=getattr(_ARTIFACTS,'current',None)
    if current:current[3]['safe']=False


@contextlib.contextmanager
def closed_media_job(process):
    owner=OwnedProcessJob(process)
    try:owner.__enter__()
    except BaseException:
        uncertain_producer();raise
    try:yield owner
    finally:
        try:owner.__exit__(*sys.exc_info())
        except BaseException:
            uncertain_producer();raise


def remember_generated(path,sha256,size):
    current=getattr(_ARTIFACTS,'current',None)
    if current and Path(path).parent==current[0]:
        current[1][Path(path).name]={'sha256':sha256,'size':size}

def producer_bytes(stream,path):
    # Read the generator's CREATE_NEW descriptor, never reopen a possibly replaced name.
    stream.flush();os.fsync(stream.fileno());before=os.fstat(stream.fileno());stream.seek(0);raw=stream.read()
    after=os.fstat(stream.fileno());named=Path(path).stat()
    key=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)
    if key(before)!=key(after) or key(after)!=key(named):raise ValidationError('Generated artifact identity changed')
    remember_generated(path,hashlib.sha256(raw).hexdigest(),len(raw))
    return raw

def write_generated(path,text):
    plan_generated(path)
    raw=text.encode('utf-8')
    with open(path,'xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
        remember_generated(path,hashlib.sha256(raw).hexdigest(),len(raw))

class EncodingProgress:
    """Bounded FFmpeg machine telemetry; measurements describe encoding only."""
    def __init__(self,total,callback):
        self.total=total if isinstance(total,(int,float)) and math.isfinite(total) and total>0 else None
        self.callback=callback;self.pending=b'';self.last=0.0
    def feed(self,raw):
        self.pending=(self.pending+raw)[-65536:]
        lines=self.pending.split(b'\n');self.pending=lines.pop()
        for line in lines:
            if not line.startswith(b'out_time_us=') or self.total is None:continue
            try:seconds=int(line.split(b'=',1)[1])/1000000
            except (ValueError,OverflowError):continue
            if seconds<0:continue
            seconds=min(self.total,max(self.last,seconds));self.last=seconds
            self.callback({'phase':'encoding','completed':seconds,'total':self.total})

def run_owned(arguments,directory,stop,deadline=300,max_output=8*1024*1024,telemetry=None):
    """Owned child cancellation; bounded diagnostics and transient encoding pipe."""
    directory=Path(directory);token=uuid.uuid4().hex
    stdout=directory/(token+'.stdout');stderr=directory/(token+'.stderr')
    plan_generated(stdout);plan_generated(stderr)
    with open(stdout,'x+b') as out,open(stderr,'x+b') as err:
        process=subprocess.Popen(arguments,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE if telemetry else out,stderr=err,
            shell=False,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'BELOW_NORMAL_PRIORITY_CLASS',0)|4)
        process._books_suspended=True
        started=time.monotonic();drain=None;failure=[]
        def consume():
            try:
                while block:=process.stdout.read1(65536):telemetry.feed(block)
            except Exception as error:failure.append(error)
        try:
            with closed_media_job(process):
                if telemetry:
                    drain=threading.Thread(target=consume,name='BooksArrangerEncodingProgress',daemon=True);drain.start()
                while process.poll() is None:
                    if stop.is_set():raise Paused('Audiobook operation paused; interrupted book restarts')
                    if time.monotonic()-started>deadline:raise TimeoutError('Owned media operation exceeded its deadline')
                    if stdout.stat().st_size>max_output or stderr.stat().st_size>1024*1024:raise ValidationError('Media diagnostic output exceeded its limit')
                    if failure:raise ValidationError('Encoding progress stream failed') from failure[0]
                    time.sleep(.1)
        finally:
            try:
                if process.poll() is None:
                    process.terminate()
                    try:process.wait(timeout=3)
                    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
                if drain:
                    drain.join(3)
                    process.stdout.close()
                    if drain.is_alive():raise ValidationError('Owned encoding progress has not finished draining')
            except BaseException:
                uncertain_producer();raise
        if failure:raise ValidationError('Encoding progress stream failed') from failure[0]
        raw=producer_bytes(out,stdout);error=producer_bytes(err,stderr)
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
    plan_generated(stderr)
    with open(stderr,'x+b') as errors:
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
            with closed_media_job(process):
                while process.poll() is None:
                    if stop.is_set():raise Paused('Decode verification paused; this book restarts')
                    if time.monotonic()-started>max(300,estimated*2):raise TimeoutError('Owned decode verification exceeded its deadline')
                    if stderr.stat().st_size>1024*1024:raise ValidationError('Decode diagnostics exceeded their limit')
                    time.sleep(.05)
        finally:
            try:
                if process.poll() is None:process.kill();process.wait(timeout=3)
                thread.join(3)
                process.stdout.close()
                if thread.is_alive():uncertain_producer()
            except BaseException:
                uncertain_producer();raise
        if thread.is_alive():
            uncertain_producer()
            raise ValidationError('Owned decoder output has not finished draining')
        error_raw=producer_bytes(errors,stderr)
    if state['error'] or process.returncode or state['bytes']%4:
        raise ValidationError('Full audio decode failed: '+error_raw.decode('utf-8','replace')[-1000:])
    if not state['bytes']:raise ValidationError('Audio decoder produced no samples')
    return state['bytes']/4/44100

def ffmetadata_escape(value):
    return str(value).replace('\\','\\\\').replace('=','\\=').replace(';','\\;').replace('#','\\#').replace('\r','').replace('\n','\\\n')

def output_space_required(source_bytes, durations, encoding, count):
    if type(source_bytes) is not int or source_bytes<0 or not durations or any(not math.isfinite(d) or d<=0 for d in durations):
        raise ValidationError('Working-space estimate requires complete source durations')
    duration=sum(durations);rate=encoding['sample_rate']
    if not math.isfinite(duration) or type(count) is not int or count!=len(durations) or type(rate) is not int or not 8000<=rate<=192000:
        raise ValidationError('Working-space estimate has invalid complete-source bounds')
    payload=source_bytes if encoding.get('mode')=='copy' else math.ceil(duration*(encoding['bitrate']/8+rate/1024*128))
    return max(source_bytes,payload)+count*4096+16*1024*1024


def working_space_required(source_bytes, durations, encoding, count):
    output=output_space_required(source_bytes,durations,encoding,count)
    pcm=math.ceil(sum(durations)*encoding['sample_rate']*encoding['channels']*8)+count*4096 if encoding.get('mode')=='normalize' else 0
    # Reserve snapshots + worst-case double WAV + both chapter-rewrite outputs +
    # publication copy even when destination/stage share a filesystem.
    return source_bytes+pcm+3*output+64*1024*1024


def check_working_space(manifest, stage, stop):
    if shutil.disk_usage(stage).free<sum(item['size'] for item in manifest['sources'])+64*1024*1024:
        raise OSError(errno.ENOSPC,'Insufficient staging space before source admission; originals retained')
    durations=[];profiles=[]
    for item in manifest['sources']:
        path=ordinary(item['path'])
        if not path.is_relative_to(ordinary(manifest['root'])) or path.suffix.lower() not in INPUT_FORMATS:
            raise ValidationError('Source is outside the supported audiobook boundary')
        with DirectoryBoundary(manifest['root'],path.parent),VerifiedFile(path) as held:
            if held.facts()['size']!=item['size'] or str(held.facts()['modified'])!=str(item['modified']) or held.sha256()!=item['sha256']:
                raise ValidationError('Source changed before working-space admission')
            raw=probe(path,stage,stop);duration,profile=audio_info(raw)
            stream=next(s for s in raw['streams'] if s.get('codec_type')=='audio')
            profiles.append((*profile,stream.get('bit_rate'),stream.get('channel_layout')))
            durations.append(decoded_duration(path,stage,stop,duration))
    if manifest.get('profile')==AUTOMATIC_PROFILE:
        encoding=choose_automatic_encoding(profiles,single_m4b=len(profiles)==1 and Path(manifest['sources'][0]['path']).suffix.lower()=='.m4b')
    elif manifest.get('profile')==PROFILE:encoding=choose_encoding(profiles)
    elif manifest.get('profile')==LEGACY_PROFILE:encoding={'bitrate':160000,'channels':2,'sample_rate':44100}
    else:raise ValidationError('Unsupported frozen encoding profile')
    source_bytes=sum(item['size'] for item in manifest['sources'])
    required=working_space_required(source_bytes,durations,encoding,len(durations))
    if shutil.disk_usage(stage).free<required:
        raise OSError(errno.ENOSPC,f'Insufficient working space; need {required} bytes before snapshotting; originals retained')
    root=ordinary(manifest['root']);destination=ordinary(manifest['destination'])
    if not destination.is_relative_to(root):raise ValidationError('Destination is outside the audiobook library')
    parent=destination.parent
    while not parent.exists():
        if parent==root:raise ValidationError('Audiobook destination root is unavailable')
        parent=parent.parent
    with DirectoryBoundary(root,parent):
        if shutil.disk_usage(parent).free<output_space_required(source_bytes,durations,encoding,len(durations)):
            raise OSError(errno.ENOSPC,'Insufficient destination space before conversion; originals retained')
    return required


def snapshot_manifest(manifest,stage,stop):
    sources=manifest['sources']
    if not sources:raise ValidationError('No reviewed source files are included')
    # Split books (v0.15.0): M4B parts are joined by the v4 normalizer (decoded and re-encoded once,
    # one chapter per part). A part that carries its own chapter plan is refused below, on its
    # protected snapshot, so no existing chapter plan is ever dropped.
    joined_m4b=manifest.get('profile')==AUTOMATIC_PROFILE and len(sources)!=1 and any(Path(item['path']).suffix.lower() in ('.m4b','.m4a') for item in sources)
    root=ordinary(manifest['root'])
    copies=[];durations=[];profiles=[];compatibility=None
    check_working_space(manifest,stage,stop)
    for index,item in enumerate(sources):
        source=ordinary(item['path'])
        try:source.relative_to(root)
        except ValueError:raise ValidationError('Source is outside the configured audiobook library')
        if source.suffix.lower() not in {'.mp3','.m4a','.m4b','.aac','.flac','.ogg','.opus','.wav','.wma'}:
            raise ValidationError('This source format is not supported by the merge path')
        same_source(item,stop)
        alias=stage/(f'source{index:05}'+source.suffix.lower())
        copy_owned(source,alias,item['sha256'],stop)
        same_source(item,stop)
        # Read bitrate/profile and PCM duration from the same protected, hash-verified bytes.
        with ProtectedFiles([alias]):
            if digest(alias,stop)!=item['sha256']:raise ValidationError('Protected snapshot differs from reviewed source bytes')
            raw=probe(alias,stage,stop)
            if joined_m4b and alias.suffix in ('.m4b','.m4a') and len(raw.get('chapters') or [])>1:
                raise ValidationError('Existing M4B parts carry their own chapters; they must be arranged individually to preserve every source chapter plan')
            duration,profile=audio_info(raw)
            if manifest.get('profile')==LEGACY_PROFILE and compatibility is not None and compatibility!=profile:
                raise ValidationError('Included files have incompatible recording/audio stream parameters')
            compatibility=profile
            stream=next(s for s in raw['streams'] if s.get('codec_type')=='audio')
            profiles.append((*profile,stream.get('bit_rate'),stream.get('channel_layout')))
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
    if manifest.get('profile')==AUTOMATIC_PROFILE:
        run_owned([shutil.which('ffmpeg'),'-v','error','-xerror','-nostdin','-protocol_whitelist','file','-f','image2','-i',str(cover_copy),'-map','0:v:0','-frames:v','1','-f','null','-'],stage,stop,30)
    return copies,durations,cover_copy,profiles

def create_private(manifest,stage_root,stop,progress=lambda *_:None,artifact_observer=None):
    if artifact_observer is None:
        return _create_private(manifest,stage_root,stop,progress)
    artifact_observer.begin(manifest)
    stage=ordinary(stage_root)/manifest['job_id']/manifest['attempt_id']
    attempt_context={'entered':False}
    try:return _create_private(manifest,stage_root,stop,progress,artifact_observer,attempt_context)
    finally:
        # Failure before entering generated_artifacts created no media producer.
        # Inside it, closed() always records either closed or uncertain first.
        if not attempt_context['entered']:
            error=sys.exc_info()[1]
            try:artifact_observer.closed(stage,producer_closed=True)
            except Exception:
                if error is None:raise


def _create_private(manifest,stage_root,stop,progress=lambda *_:None,artifact_observer=None,attempt_context=None):
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
            with DirectoryBoundary(job,stage,create=True),generated_artifacts(stage,artifact_observer,attempt_context) as generated:
                progress('Checking sources',{})
                copies,durations,cover,profiles=snapshot_manifest(manifest,stage,stop)
                with ProtectedFiles([stage/name for name in copies]+[cover]):
                    for name,item in zip(copies,manifest['sources']):
                        if digest(stage/name,stop)!=item['sha256']:raise ValidationError('Protected snapshot differs from reviewed source bytes')
                    if digest(cover,stop)!=manifest['cover']['sha256']:raise ValidationError('Protected cover differs from reviewed artwork')
                    if manifest.get('profile')==PROFILE:
                        if manifest.get('encoding_policy')!=freeze_policy(manifest['sources']):raise ValidationError('Frozen encoding policy changed')
                        encoding=choose_encoding(profiles)
                    elif manifest.get('profile')==AUTOMATIC_PROFILE:
                        if manifest.get('encoding_policy')!=freeze_automatic_policy(manifest['sources']):raise ValidationError('Frozen automatic encoding policy changed')
                        encoding=choose_automatic_encoding(profiles,single_m4b=len(copies)==1 and Path(copies[0]).suffix.lower()=='.m4b')
                    elif manifest.get('profile')==LEGACY_PROFILE:
                        encoding={'bitrate':160000,'channels':2,'sample_rate':44100,'selection':'legacy fixed profile'}
                    else:raise ValidationError('Unsupported frozen encoding profile')
                    output,validation=_encode_private(manifest,stage,copies,durations,cover,stop,progress,encoding)
                    validation['staging_artifacts']={'attempt_id':attempt,'files':generated}
                    return output,validation


def normalization_filter(encoding):
    return f"aformat=sample_fmts=dbl,aresample={encoding['sample_rate']},aformat=sample_fmts=dbl:channel_layouts={'mono' if encoding['channels']==1 else 'stereo'}"


class ExpandedPcmHash:
    """Expand candidate PCM into canonical doubles without quantizing the proof.

    Bounded chunks preserve every sample and channel; final partial frames fail.
    """
    def __init__(self, channels, kind):
        self.channels=channels;self.kind=kind;self.width={'s16':2,'s24':3,'s32':4,'f32':4}[kind]
        self.pending=b'';self.proof=None
    def feed(self, raw):
        if self.proof is None:self.proof=NativePcmHash(self.channels)
        raw=self.pending+raw;end=len(raw)//self.width*self.width;self.pending=raw[end:];raw=raw[:end]
        expanded=bytearray()
        if self.kind=='s24':
            values=(int.from_bytes(raw[i:i+3],'little',signed=True)/8388608 for i in range(0,len(raw),3))
        else:
            fmt={'s16':'<h','s32':'<i','f32':'<f'}[self.kind];scale={'s16':32768,'s32':2147483648,'f32':1}[self.kind]
            values=(value[0]/scale for value in struct.iter_unpack(fmt,raw))
        for value in values:expanded.extend(struct.pack('<d',value))
        self.proof.feed(expanded)
    def result(self):
        if self.pending or self.proof is None:raise ValidationError('Candidate normalized PCM proof is incomplete')
        return self.proof.result()


def normalized_pcm_evidence(path,stage,stop,duration,encoding,kind=None,aggregate=None):
    proof=NativePcmHash(encoding['channels']) if kind is None else ExpandedPcmHash(encoding['channels'],kind)
    telemetry=proof
    if aggregate is not None:
        if kind is not None:raise ValidationError('Canonical aggregate cannot use a quantized candidate')
        class Fanout:
            def feed(self,raw):proof.feed(raw);aggregate.feed(raw)
        telemetry=Fanout()
    codec,format=('pcm_f64le','f64le') if kind is None else {'s16':('pcm_s16le','s16le'),'s24':('pcm_s24le','s24le'),'s32':('pcm_s32le','s32le'),'f32':('pcm_f32le','f32le')}[kind]
    run_owned([shutil.which('ffmpeg'),'-hide_banner','-v','error','-xerror','-nostdin','-threads','2','-filter_threads','1',
      '-protocol_whitelist','file','-f',INPUT_FORMATS[Path(path).suffix.lower()],'-i',str(path),'-map','0:a:0',
      '-af',normalization_filter(encoding),'-c:a',codec,'-f',format,'pipe:1'],stage,stop,max(300,duration*2),telemetry=telemetry)
    return proof.result()


def choose_normalized_pcm(path,stage,stop,duration,encoding):
    reference=normalized_pcm_evidence(path,stage,stop,duration,encoding)
    # Smallest exact representation, tested before creating any working WAV.
    # Full hashes/counts, not a prefix, duration, or source format label, decide.
    for kind,codec in (('s16','pcm_s16le'),('s24','pcm_s24le'),('s32','pcm_s32le'),('f32','pcm_f32le')):
        if normalized_pcm_evidence(path,stage,stop,duration,encoding,kind)==reference:
            return codec,reference
    return 'pcm_f64le',reference


def choose_normalized_pcm_set(stage,copies,encoding,stop,durations,aggregate=None):
    """Select one exact format for the entire concat-demuxer input set.

    Concat packets inherit the first input's codec configuration. Different PCM
    widths, and especially s32/f32 equal widths, must never be mixed here.
    """
    references=[normalized_pcm_evidence(stage/name,stage,stop,duration,encoding,aggregate=aggregate) for name,duration in zip(copies,durations)]
    for kind,codec in (('s16','pcm_s16le'),('s24','pcm_s24le'),('s32','pcm_s32le'),('f32','pcm_f32le')):
        for name,duration,reference in zip(copies,durations,references):
            if normalized_pcm_evidence(stage/name,stage,stop,duration,encoding,kind)!=reference:break
        else:return codec,references
    return 'pcm_f64le',references


def normalize_sources(stage,copies,encoding,stop,durations):
    required=working_space_required(0,durations,encoding,len(copies))
    if shutil.disk_usage(stage).free<required:raise OSError(errno.ENOSPC,'Insufficient staging space for complete exact normalization and publication; originals retained')
    aggregate=NativePcmHash(encoding['channels'])
    codec,references=choose_normalized_pcm_set(stage,copies,encoding,stop,durations,aggregate)
    result=[];receipts={}
    for index,(name,duration) in enumerate(zip(copies,durations)):
        remaining_pcm=math.ceil(sum(durations[index:])*encoding['sample_rate']*encoding['channels']*8)+(len(copies)-index)*4096
        remaining_required=remaining_pcm+3*output_space_required(0,durations,encoding,len(copies))+64*1024*1024
        if shutil.disk_usage(stage).free<remaining_required:raise OSError(errno.ENOSPC,'Staging space changed before normalization; originals retained')
        output=stage/(f'normalized{index:05}.wav')
        plan_generated(output)
        reference=references[index]
        run_owned([shutil.which('ffmpeg'),'-hide_banner','-v','error','-xerror','-nostdin','-n','-threads','2','-filter_threads','1',
          '-protocol_whitelist','file','-f',INPUT_FORMATS[Path(name).suffix.lower()],'-i',str(stage/name),'-map','0:a:0',
          '-af',normalization_filter(encoding),'-c:a',codec,'-rf64','always','-f','wav',str(output)],stage,stop,max(300,duration*2))
        with VerifiedFile(output) as held:
            actual=native_pcm_evidence(output,stage,stop,duration,encoding)
            if any(actual[key]!=reference[key] for key in reference):
                raise ValidationError('Normalized PCM differs from complete source normalization')
            facts=held.facts();expected=held.sha256()
            if facts['links']!=1:raise ValidationError('Normalized source snapshot has unexpected links')
            receipts[output.name]={'facts':facts,'sha256':expected,'pcm':reference,'codec':codec}
            remember_generated(output,expected,facts['size'])
        result.append(output.name)
    joined=aggregate.result()
    if joined['sample_count']!=sum(reference['sample_count'] for reference in references):raise ValidationError('Joined original normalized sample count changed')
    for receipt in receipts.values():receipt['joined_pcm']=joined
    return result,receipts


def source_chapters(path,stage,stop,duration):
    result=[];previous=0
    for chapter in probe(path,stage,stop).get('chapters',[]):
        try:
            start=float(chapter['start_time']);end=float(chapter['end_time'])
        except (ValueError,TypeError,KeyError):raise ValidationError('Existing M4B chapter boundaries cannot be verified')
        if not all(math.isfinite(value) for value in (start,end)) or start<0 or end<=start or start<previous-.05 or end>duration+.25:
            raise ValidationError('Existing M4B chapters overlap or exceed complete source audio')
        title=chapter.get('tags',{}).get('title','')
        if not isinstance(title,str):raise ValidationError('Existing M4B chapter title is invalid')
        result.append({'start':round(start*1000),'end':round(end*1000),'title':title});previous=end
    return result


def audio_packet_hash(path,stage,stop,duration):
    raw=run_owned([shutil.which('ffmpeg'),'-hide_banner','-v','error','-xerror','-nostdin','-protocol_whitelist','file',
      '-f',INPUT_FORMATS[Path(path).suffix.lower()],'-i',str(path),'-map','0:a:0','-c:a','copy','-f','hash','-hash','sha256','pipe:1'],stage,stop,max(300,duration*2),max_output=4096)
    value=raw.decode('ascii').strip()
    if not value.startswith('SHA256=') or len(value)!=71 or any(c not in '0123456789abcdef' for c in value[7:]):
        raise ValidationError('Compressed audio integrity proof is invalid')
    return value[7:]


class PacketTimingHash:
    """Bounded streaming proof of relative packet timing, order and durations."""
    def __init__(self):
        self.pending=b'';self.hash=hashlib.sha256();self.count=0;self.origin=None
    def feed(self,raw):
        parts=(self.pending+raw).split(b'\n');self.pending=parts.pop()
        if len(self.pending)>4096:raise ValidationError('M4B packet timing line exceeds its bound')
        for line in parts:
            if not line:continue
            values=dict(part.split(b'=',1) for part in line.split(b'|') if b'=' in part)
            try:pts=int(values[b'pts']);dts=int(values[b'dts']);duration=int(values[b'duration'])
            except (KeyError,ValueError):raise ValidationError('M4B packet timing cannot be verified')
            if duration<=0:raise ValidationError('M4B packet duration is invalid')
            try:
                skip=int(values.get(b'skip_samples',b'0'));discard=int(values.get(b'discard_padding',b'0'))
            except ValueError:raise ValidationError('M4B decoder trim semantics cannot be verified')
            if skip<0 or discard<0:raise ValidationError('M4B decoder trim semantics are invalid')
            if self.origin is None:self.origin=pts
            self.hash.update(f'{pts-self.origin},{dts-self.origin},{duration},{skip},{discard}\n'.encode('ascii'));self.count+=1
    def result(self):
        if self.pending or not self.count:raise ValidationError('M4B packet timing proof is incomplete')
        return {'sha256':self.hash.hexdigest(),'packet_count':self.count}


def _copy_presentation(stream, movie):
    """Map positive rational ticks to exact decoded-sample bounds, preserving holds."""
    try:
        if isinstance(stream['sample_rate'], bool):raise ValueError('Boolean sample rate')
        rate_text = str(stream['sample_rate'])
        if not rate_text.isascii() or not rate_text.isdecimal():raise ValueError('Invalid sample rate')
        rate = int(rate_text)
        parts = stream['time_base'].split('/')
        if len(parts) != 2 or not all(p.isascii() and p.isdecimal() for p in parts):raise ValueError('Malformed time base')
        numerator, denominator = (int(p) for p in parts)
        if rate <= 0 or numerator <= 0 or denominator <= 0:raise ValueError('Nonpositive clock')
        scale = Fraction(numerator * rate, denominator)
        if any(isinstance(stream[k], bool) for k in ('start_pts', 'duration_ts')):raise ValueError('Boolean bound')
        tick_values = [str(stream[k]) for k in ('start_pts', 'duration_ts')]
        if not all(v.lstrip('-').isascii() and v.lstrip('-').isdecimal() for v in tick_values):raise ValueError('Noninteger tick bound')
        start_ticks, duration_ticks = (int(v) for v in tick_values)
        if duration_ticks <= 0:raise ValueError('Nonpositive duration')
        start, end = start_ticks * scale, (start_ticks + duration_ticks) * scale
        if start.denominator != 1 or end.denominator != 1:raise ValueError('Fractional decoded-sample boundary')
        movie_start_exact = Fraction(str(movie['start_time'])) * rate
        movie_end_exact = Fraction(str(movie['duration'])) * rate
        if movie_end_exact <= 0:raise ValueError('Nonpositive movie duration')
        movie_start, movie_end = round(movie_start_exact), round(movie_end_exact)
    except (ValueError, TypeError, KeyError, OverflowError, ZeroDivisionError, AttributeError):
        raise ValidationError('M4B presentation bounds cannot be verified')
    if start != 0 or movie_start_exact != 0 or end <= 0 or abs(movie_end - end) > 1:
        raise ValidationError('M4B leading gaps or edit presentation require a verified preservation plan')
    return {'audio_start_sample':int(start), 'audio_end_sample':int(end),
            'movie_start_sample':movie_start, 'movie_end_sample':movie_end}


def copied_audio_evidence(path,stage,stop,duration,*,source_relative=False):
    executable=shutil.which('ffprobe')
    raw=run_owned([executable,'-v','error','-protocol_whitelist','file','-f',INPUT_FORMATS[Path(path).suffix.lower()],
      '-select_streams','a:0','-show_streams','-show_format','-show_data_hash','sha256','-of','json',str(path)],stage,stop,30)
    data=json.loads(raw);streams=data.get('streams',[])
    if len(streams)!=1:raise ValidationError('M4B decoder configuration is ambiguous')
    stream=streams[0]
    keys=('codec_name','profile','sample_rate','channels','channel_layout','time_base','extradata_hash')
    config={key:stream.get(key) for key in keys}
    if not config['extradata_hash'] or not config['time_base']:raise ValidationError('M4B decoder configuration evidence is missing')
    if source_relative:
        # Only the separate byte-exact preservation branch may retain existing
        # edits/gaps. The remux guard below remains unchanged and strict.
        presentation={key:stream.get(key) for key in ('start_pts','duration_ts','start_time','duration')}
        presentation['movie']={key:data.get('format',{}).get(key) for key in ('start_time','duration')}
        if any(presentation[key] is None for key in ('start_pts','duration_ts')):
            raise ValidationError('Source-relative M4B presentation evidence is missing')
    else:presentation=_copy_presentation(stream,data.get('format',{}))
    timing=PacketTimingHash()
    run_owned([executable,'-v','error','-protocol_whitelist','file','-f',INPUT_FORMATS[Path(path).suffix.lower()],
      '-select_streams','a:0','-show_packets','-show_entries','packet=pts,dts,duration:packet_side_data=side_data_type,skip_samples,discard_padding','-of','compact=p=0:nk=0',str(path)],
      stage,stop,max(300,duration*2),telemetry=timing)
    return {'decoder_configuration':config,'relative_packet_timing':timing.result(),'presentation':presentation}


class NativePcmHash:
    """Stream all decoded channels to a bounded digest, never a persistent PCM file."""
    def __init__(self,channels):
        self.frame_bytes=channels*8;self.bytes=0;self.hash=hashlib.sha256()
    def feed(self,raw):self.bytes+=len(raw);self.hash.update(raw)
    def result(self):
        if not self.bytes or self.bytes%self.frame_bytes:raise ValidationError('Native M4B decoded frame proof is incomplete')
        return {'sha256':self.hash.hexdigest(),'sample_count':self.bytes//self.frame_bytes,'bytes':self.bytes,'sample_format':'pcm_f64le'}


def native_pcm_evidence(path,stage,stop,duration,encoding):
    proof=NativePcmHash(encoding['channels'])
    # No resampling or channel selection: hash the decoder's complete native-rate,
    # all-channel output, including the effect of codec priming/discard/edit trims.
    run_owned([shutil.which('ffmpeg'),'-hide_banner','-v','error','-xerror','-nostdin','-threads','2','-filter_threads','1',
      '-protocol_whitelist','file','-f',INPUT_FORMATS[Path(path).suffix.lower()],'-i',str(path),'-map','0:a:0',
      '-c:a','pcm_f64le','-f','f64le','pipe:1'],stage,stop,max(300,duration*2),telemetry=proof)
    return proof.result()|{'sample_rate':encoding['sample_rate'],'channels':encoding['channels'],'channel_layout':encoding.get('channel_layout')}

def verify_normalized_concat(stage,copies,durations,encoding,stop,expected):
    proof=NativePcmHash(encoding['channels'])
    run_owned([shutil.which('ffmpeg'),'-hide_banner','-v','error','-xerror','-nostdin','-threads','2','-filter_threads','1',
      '-protocol_whitelist','file','-format_whitelist','concat,wav','-f','concat','-safe','1','-i',str(stage/'inputs.txt'),
      '-map','0:a:0','-c:a','pcm_f64le','-f','f64le','pipe:1'],stage,stop,max(300,sum(durations)*2),telemetry=proof)
    if proof.result()!=expected:raise ValidationError('Concatenated normalized PCM differs from the complete ordered source proof')


def _encode_private(manifest,stage,copies,durations,cover,stop,progress,encoding):
    original_copies=list(copies);joined=None;codec=None
    with contextlib.ExitStack() as guards:
        if encoding.get('mode')=='normalize':
            copies,receipts=normalize_sources(stage,copies,encoding,stop,durations)
            codecs={receipt['codec'] for receipt in receipts.values()}
            if len(codecs)!=1:raise ValidationError('Normalized concat inputs have incompatible PCM codecs')
            codec=next(iter(codecs));joined=receipts[copies[0]]['joined_pcm']
            for name in copies:
                held=guards.enter_context(VerifiedFile(stage/name))
                if held.facts()!=receipts[name]['facts'] or held.sha256()!=receipts[name]['sha256'] or receipts[name]['joined_pcm']!=joined:
                    raise ValidationError('Normalized snapshot differs from its complete-source receipt')
            write_generated(stage/'inputs.txt',''.join(f"file '{name}'\n" for name in copies))
            guards.enter_context(VerifiedFile(stage/'inputs.txt'))
            # This expected digest came from the ORIGINAL protected sources,
            # never from the possibly misinterpreted concat demuxer's output.
            verify_normalized_concat(stage,copies,durations,encoding,stop,joined)
        # Input/plan leases remain open through final media verification.
        output,validation=_encode_inputs(manifest,stage,copies,durations,cover,stop,progress,encoding,original_copies)
        if joined is not None:
            validation['normalized_joined_pcm']=joined;validation['normalized_pcm_codec']=codec
        return output,validation


def _encode_inputs(manifest,stage,copies,durations,cover,stop,progress,encoding,original_copies):
    required=3*output_space_required(sum(item['size'] for item in manifest['sources']),durations,encoding,len(copies))+64*1024*1024
    if shutil.disk_usage(stage).free<required:raise OSError(errno.ENOSPC,'Staging space changed before output creation; originals retained')
    executable=shutil.which('ffmpeg')
    if not executable:raise ValidationError('Installed ffmpeg is required for audiobook creation')
    if encoding.get('mode')!='normalize':write_generated(stage/'inputs.txt',''.join(f"file '{name}'\n" for name in copies))
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
    if encoding.get('mode')=='copy' and encoding.get('codec')=='aac' and len(original_copies)==1 and Path(original_copies[0]).suffix.lower()=='.m4b':
        return _preserve_single_m4b(manifest,stage,original_copies[0],durations,cover,stop,progress,encoding,tags)
    output=stage/'checked.m4b'
    args=[executable,'-hide_banner','-v','error','-xerror','-nostdin','-n','-threads','2','-filter_threads','1','-protocol_whitelist','file',
      '-format_whitelist','concat,mp3,mov,aac,flac,ogg,wav,asf',
      *(['-f','mov','-i',str(stage/original_copies[0])] if encoding.get('mode')=='copy' else ['-f','concat','-safe','1','-i',str(stage/'inputs.txt')]),'-f','image2','-i',str(cover)]
    chapters=[]
    preserved=source_chapters(stage/original_copies[0],stage,stop,sum(durations)) if encoding.get('mode')=='copy' else []
    if encoding.get('mode')=='copy' and manifest.get('source_chapters')!=preserved:
        raise ValidationError('Existing M4B chapters differ from the frozen complete source plan')
    if preserved:
        chapter_file=stage/'chapters.txt';text=';FFMETADATA1\n';chapters=preserved
        for chapter in chapters:
            text+=f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={chapter['start']}\nEND={chapter['end']}\ntitle={ffmetadata_escape(chapter['title'])}\n"
        write_generated(chapter_file,text)
        args+=['-f','ffmetadata','-i',str(chapter_file),'-map_chapters','2']
    elif manifest.get('chapters') and encoding.get('mode')!='copy':
        if len(manifest['chapters'])!=len(copies):raise ValidationError('Chapter plan must match the reviewed source boundaries')
        chapter_file=stage/'chapters.txt';text=';FFMETADATA1\n';position=0
        for name,duration in zip(manifest['chapters'],durations):
            start=round(position*1000);position+=duration;end=round(position*1000)
            chapters.append({'start':start,'end':end,'title':str(name)})
            text+=f'[CHAPTER]\nTIMEBASE=1/1000\nSTART={start}\nEND={end}\ntitle={ffmetadata_escape(name)}\n'
        write_generated(chapter_file,text)
        args+=['-f','ffmetadata','-i',str(chapter_file),'-map_chapters','2']
    else:args+=['-map_chapters','-1']
    args+=['-map','0:a:0','-map','1:v:0','-map_metadata:g','-1',*(['-c:a','copy'] if encoding.get('mode')=='copy' else ['-af','asetpts=N/SR/TB','-c:a','aac','-b:a',str(encoding['bitrate']),'-ar',str(encoding['sample_rate']),'-ac',str(encoding['channels']),'-threads:a','2']),'-c:v','copy','-disposition:v:0','attached_pic','-movflags','+faststart+disable_chpl']
    for name,value in tags.items():args+=['-metadata',name+'='+value]
    args+=['-progress','pipe:1','-stats_period','1','-nostats','-f','mp4',str(output)]
    progress('Creating audio',{'duration':sum(durations),'source_durations':durations,'source_pcm_frames':[round(d*44100) for d in durations],'source_pcm_rate':44100,'encoding':encoding})
    plan_generated(output)
    run_owned(args,stage,stop,max(300,sum(durations)*2),telemetry=EncodingProgress(sum(durations),lambda value:progress('Creating audio',{'progress':value})))
    chapter_format=None
    sort_title=audiobook_sort_title(review)
    if chapters or sort_title!=review['title']:
        compatible=stage/'compatible.m4b'
        plan_generated(compatible)
        chapter_format=normalize(output,compatible,stop,sort_title=sort_title if sort_title!=review['title'] else None,normalize_chapters=bool(chapters))
        output=compatible
    with VerifiedFile(output) as held_output:
        progress('Checking output',{})
        validation=validate(output,manifest,durations,chapters,stage,stop,encoding)
        if encoding.get('mode')=='copy':
            source_hash=audio_packet_hash(stage/original_copies[0],stage,stop,sum(durations))
            output_hash=audio_packet_hash(output,stage,stop,sum(durations))
            if source_hash!=output_hash:raise ValidationError('Remux changed the complete compressed audio payload')
            source_evidence=copied_audio_evidence(stage/original_copies[0],stage,stop,sum(durations))
            output_evidence=copied_audio_evidence(output,stage,stop,sum(durations))
            if source_evidence!=output_evidence:raise ValidationError('Remux changed the decoder configuration or relative audio packet timing')
            source_pcm=native_pcm_evidence(stage/original_copies[0],stage,stop,sum(durations),encoding)
            output_pcm=native_pcm_evidence(output,stage,stop,sum(durations),encoding)
            if source_pcm!=output_pcm:raise ValidationError('Remux changed full native decoded audio samples or decoder trim effects')
            validation['native_pcm_evidence']=output_pcm
            validation['copied_audio_evidence']=output_evidence
            validation['audio_packet_sha256']=output_hash
            validation['preserved_source_chapters']=chapters
        if chapter_format:
            validation['chapter_format']=chapter_format
            remember_generated(stage/'checked.m4b',chapter_format['input_sha256'],chapter_format['old_file_size'])
            remember_generated(output,validation['sha256'],validation['size'])
        else:remember_generated(output,validation['sha256'],validation['size'])
        for item in manifest['sources']:same_source(item,stop)
        if digest(manifest['cover']['path'],stop)!=manifest['cover']['sha256']:raise ValidationError('Selected cover changed — review required')
        if held_output.sha256()!=validation['sha256'] or held_output.facts()['size']!=validation['size']:
            raise ValidationError('Final output differs from its leased verification artifact')
        return output,validation


def _preserve_single_m4b(manifest,stage,name,durations,cover,stop,progress,encoding,tags):
    """One compressed candidate; no remux or chapter/timescale reconstruction."""
    source=stage/name;output=stage/PRESERVATION_CANDIDATE_NAME;expected=sum(durations)
    sort_title=audiobook_sort_title(manifest['metadata'])
    if sort_title!=manifest['metadata']['title']:tags=tags|{'sort_name':sort_title}
    chapters=source_chapters(source,stage,stop,expected)
    if manifest.get('source_chapters')!=chapters:
        raise ValidationError('Existing M4B chapters differ from the frozen complete source plan')
    cover_bytes=Path(cover).read_bytes()
    if len(cover_bytes)>MAX_IMAGE or hashlib.sha256(cover_bytes).hexdigest()!=manifest['cover']['sha256']:
        raise ValidationError('Protected cover differs from reviewed artwork')
    try:
        with VerifiedFile(source) as held_source,open(source,'rb') as incoming:
            source_facts=held_source.facts()
            def read_at(offset,count):incoming.seek(offset);return incoming.read(count)
            plan=m4b_preservation.plan(source_facts['size'],read_at,tags,cover_bytes)
            if shutil.disk_usage(stage).free<source_facts['size']+len(plan.appended_movie)+16*1024*1024:
                raise OSError(errno.ENOSPC,'Insufficient space for the single metadata candidate; originals retained')
            plan_generated(output)
            progress('Creating audio',{'encoding':encoding,'source_metadata_preservation':True})
            with open(output,'xb') as outgoing:
                receipt=m4b_preservation.stream_candidate(plan,read_at,outgoing.write,stop.is_set)
                outgoing.flush();os.fsync(outgoing.fileno())
            if receipt['source_sha256']!=manifest['sources'][0]['sha256']:
                raise ValidationError('Preservation source differs from frozen bytes')
            with VerifiedFile(output) as held_output,open(output,'rb') as candidate:
                def candidate_read(offset,count):candidate.seek(offset);return candidate.read(count)
                progress('Checking output',{})
                reread=m4b_preservation.verify_candidate(plan,read_at,held_output.facts()['size'],candidate_read,stop.is_set)
                if any(reread[key]!=receipt[key] for key in ('source_sha256','sha256','size')):
                    raise ValidationError('Preservation candidate differs from its creation receipt')
                source_evidence=copied_audio_evidence(source,stage,stop,expected,source_relative=True)
                output_evidence=copied_audio_evidence(output,stage,stop,expected,source_relative=True)
                if source_evidence!=output_evidence:raise ValidationError('Preservation changed decoder, packets or presentation')
                source_pcm=native_pcm_evidence(source,stage,stop,expected,encoding)
                output_pcm=native_pcm_evidence(output,stage,stop,expected,encoding)
                if source_pcm!=output_pcm:raise ValidationError('Preservation changed complete native decoded audio')
                raw=probe(output,stage,stop);duration,profile=audio_info(raw)
                if profile!=(encoding.get('codec','aac'),str(encoding['sample_rate']),encoding['channels']):
                    raise ValidationError('Preserved output audio profile is incorrect')
                actual_chapters=source_chapters(output,stage,stop,expected)
                if actual_chapters!=chapters:raise ValidationError('Preserved source chapter presentation changed')
                actual_tags={key.lower():str(value) for key,value in raw.get('format',{}).get('tags',{}).items()}
                # Demuxers omit empty text items; exact binary metadata bytes
                # were independently checked above, including an empty comment.
                if any(actual_tags.get(key,'')!=str(value) for key,value in tags.items()):
                    raise ValidationError('Preserved output approved metadata differs')
                if held_source.facts()!=source_facts or held_source.sha256()!=receipt['source_sha256']:
                    raise ValidationError('Preservation source identity changed')
                if held_output.sha256()!=receipt['sha256']:raise ValidationError('Preserved candidate identity changed')
                for item in manifest['sources']:same_source(item,stop)
                if digest(manifest['cover']['path'],stop)!=manifest['cover']['sha256']:
                    raise ValidationError('Selected cover changed — review required')
                receipt.update(reread);receipt['pcm_verified']=True
                validation={'profile':manifest.get('profile',LEGACY_PROFILE),'encoding':encoding,'duration':duration,
                  'expected_duration':expected,'sha256':receipt['sha256'],'size':receipt['size'],'chapters':chapters,
                  'preserved_source_chapters':chapters,'source_durations':durations,'source_pcm_frames':[output_pcm['sample_count']],
                  'source_pcm_rate':output_pcm['sample_rate'],'decoded_duration':output_pcm['sample_count']/output_pcm['sample_rate'],
                  'native_pcm_evidence':output_pcm,'copied_audio_evidence':output_evidence,'metadata_preservation':receipt,
                  'checks':'Output checks passed','device':'Apple Books sync not checked','tags':actual_tags}
                remember_generated(output,receipt['sha256'],receipt['size'])
                return output,validation
    except m4b_preservation.Refused as error:raise ValidationError('M4B preservation requires review: '+str(error)) from error


def validate(output,manifest,durations,chapters,stage,stop,encoding=None):
    raw=probe(output,stage,stop)
    duration,profile=audio_info(raw)
    encoding=encoding or {'bitrate':160000,'channels':2,'sample_rate':44100,'selection':'legacy fixed profile'}
    if profile!=(encoding.get('codec','aac'),str(encoding['sample_rate']),encoding['channels']):raise ValidationError('Output audio profile is incorrect')
    if encoding.get('mode')=='copy' and encoding.get('channel_layout'):
        actual_audio=next(stream for stream in raw['streams'] if stream.get('codec_type')=='audio')
        if actual_audio.get('channel_layout')!=encoding['channel_layout']:raise ValidationError('Copied M4B channel layout changed')
    expected=sum(durations);tolerance=max(.25,len(durations)*.1)
    if abs(duration-expected)>tolerance:raise ValidationError(f'Output duration differs from reviewed sources: expected{expected:.3f}s, actual{duration:.3f}s, tolerance{tolerance:.3f}s')
    pictures=[s for s in raw.get('streams',[]) if s.get('codec_type')=='video' and s.get('disposition',{}).get('attached_pic')==1]
    if len(pictures)!=1:raise ValidationError('Output must contain exactly one attached cover')
    if any(s.get('codec_type')=='video' and s not in pictures for s in raw.get('streams',[])):raise ValidationError('Unexpected video stream in audiobook output')
    tags={k.lower():str(v) for k,v in raw.get('format',{}).get('tags',{}).items()}
    review=manifest['metadata']
    expected_tags=[('title',review['title']),('artist',review['canonical_author']),('album_artist',review['canonical_author']),('media_type','2')]
    sort_title=audiobook_sort_title(review)
    if sort_title!=review['title']:expected_tags.append(('sort_name',sort_title))
    if review.get('series'):
        expected_tags += [('grouping',review['series']),('album',' - '.join([review['series'],review.get('number',''),review['title']]))]
        if str(review.get('number','')).isdigit() and 0<int(review['number'])<65536:expected_tags.append(('track',str(int(review['number']))))
    for key,value in expected_tags:
        if tags.get(key)!=value:raise ValidationError('Output metadata check failed: '+key)
    picture=Path(stage)/(uuid.uuid4().hex+('.png' if pictures[0].get('codec_name')=='png' else '.jpg'))
    plan_generated(picture)
    run_owned([shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-protocol_whitelist','file','-i',str(output),'-map','0:v:0','-c:v','copy','-frames:v','1',str(picture)],stage,stop,30)
    if digest(picture,stop)!=manifest['cover']['sha256']:raise ValidationError('Attached cover bytes differ from the reviewed artwork')
    remember_generated(picture,manifest['cover']['sha256'],picture.stat().st_size)
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
