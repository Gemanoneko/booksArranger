"""Owned immutable-source M4B staging and strict validation; no source rewrites."""
import hashlib,json,math,os,shutil,subprocess,time,uuid,threading,contextlib,struct,errno,sys
from pathlib import Path
from fractions import Fraction
from native_io import DirectoryBoundary,publish_no_replace,BoundaryError,ordinary,ProtectedFiles,OwnedProcessJob,VerifiedFile

from encoding_policy import PROFILE, LEGACY_PROFILE, freeze_policy, choose_encoding, AUTOMATIC_PROFILE, freeze_automatic_policy, choose_automatic_encoding
from quicktime_chapters import normalize
from metadata import audiobook_sort_title
import m4b_preservation
import m4b_repair
import mp3_tag_repair
import source_proofs
MAX_IMAGE=8*1024*1024
PRESERVATION_CANDIDATE_NAME='checked.m4b'
INPUT_FORMATS={'.mp3':'mp3','.m4a':'mov','.m4b':'mov','.aac':'aac','.flac':'flac','.ogg':'ogg','.opus':'ogg','.wav':'wav','.wma':'asf','.png':'image2','.jpg':'image2','.jpeg':'image2'}

class Paused(InterruptedError):pass
class ValidationError(ValueError):pass

def digest(path,stop=None,on_bytes=None):
    value=hashlib.sha256()
    with open(path,'rb') as stream:
        while block:=stream.read(1024*1024):
            if stop is not None and stop.is_set():raise Paused('Operation paused; this book will restart')
            value.update(block)
            if on_bytes is not None:on_bytes(len(block))
    return value.hexdigest()


class StepProgress:
    """Measured progress of one pipeline step, sent as {'progress': ...} through the attempt's progress callback.

    Reports are throttled (at most two a second, plus forced boundaries) and only describe work;
    they never decide anything. unit is bytes, seconds (of audio) or files; item/items name the track.
    """
    def __init__(self,report,phase,total,unit,items=None,clock=time.monotonic):
        self.report=report;self.phase=phase;self.total=float(total or 0);self.unit=unit;self.items=items;self.clock=clock;self.sent=None
    def update(self,completed,item=None,force=False):
        if self.report is None or not math.isfinite(self.total) or self.total<=0:return
        now=self.clock()
        if not force and self.sent is not None and now-self.sent<.5:return
        self.sent=now
        completed=min(self.total,max(0.0,float(completed)))
        value={'phase':self.phase,'completed':completed,'total':self.total,'unit':self.unit}
        if self.unit=='files':
            # Whole files only ("2 of 17 files"); the bar still moves within a track by the fraction.
            value.update(completed=float(math.floor(completed)),fraction=completed/self.total)
        if self.items:value.update(item=max(1,min(self.items,int(item or 1))),items=self.items)
        try:self.report(value)
        except Exception:pass  # Progress display only: a failed report never fails the step.


class PcmSeconds:
    """Decoded PCM telemetry counted as audio seconds (bytes / (rate x channels x sample width))."""
    def __init__(self,inner,rate,channels,width,on_seconds):
        self.inner=inner;self.per_second=rate*channels*width;self.on_seconds=on_seconds;self.bytes=0
    def feed(self,raw):
        self.inner.feed(raw);self.bytes+=len(raw)  # The proof itself still raises.
        if self.on_seconds is not None and self.per_second>0:
            try:self.on_seconds(self.bytes/self.per_second)
            except Exception:pass  # Progress display only.

def fingerprint(path):
    with open(path,'rb') as stream:item=os.fstat(stream.fileno())
    return {'size':item.st_size,'modified':str(item.st_mtime_ns)}

def same_source(item,stop,on_bytes=None):
    # A later check in the same attempt skips the re-read only on an identical size/ns mtime/volume/file ID (source_proofs).
    before=source_proofs.stat_of(item['path'])
    if {'size':before.st_size,'modified':str(before.st_mtime_ns)}!={'size':item['size'],'modified':str(item['modified'])}:
        raise ValidationError('Source changed — review required: '+item['path'])
    if source_proofs.unchanged(item['path'],item['sha256'],before):
        if on_bytes is not None:on_bytes(int(item['size']))  # the measured step is satisfied without re-reading
        return
    if digest(item['path'],stop,on_bytes)!=item['sha256']:
        raise ValidationError('Source changed — review required: '+item['path'])
    source_proofs.remember(item['path'],item['sha256'],before,source_proofs.stat_of(item['path']))

def copy_owned(source,destination,expected,stop,on_bytes=None):
    destination=Path(destination)
    plan_generated(destination)
    value=hashlib.sha256()
    with open(source,'rb') as incoming,open(destination,'xb') as outgoing:
        while block:=incoming.read(1024*1024):
            if stop.is_set():raise Paused('Operation paused; this book will restart')
            outgoing.write(block);value.update(block)
            if on_bytes is not None:on_bytes(len(block))
        outgoing.flush();os.fsync(outgoing.fileno())
    if value.hexdigest()!=expected:raise ValidationError('Copied bytes do not match the approved source/output hash')


_ARTIFACTS=threading.local()
@contextlib.contextmanager
def generated_artifacts(stage, observer=None, attempt_context=None):
    if attempt_context is not None:attempt_context['entered']=True
    previous=getattr(_ARTIFACTS,'current',None)
    receipts={};closure={'safe':True}
    _ARTIFACTS.current=(Path(stage),receipts,observer,closure,{})
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
            try:self.callback({'phase':'encoding','completed':seconds,'total':self.total})
            except Exception:pass  # Progress display only: it never fails the media operation.

def run_owned(arguments,directory,stop,deadline=300,max_output=8*1024*1024,telemetry=None,diagnostic=None):
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
    # This point is reached only after normal owned-context exit and successful drain,
    # file closure and bounds. A media nonzero is distinct from ownership/I/O failure.
    if diagnostic is not None:diagnostic(mp3_tag_repair.completed_diagnostic(arguments,process.returncode,raw,error),raw,error)
    if process.returncode:raise ValidationError(error.decode('utf-8','replace')[-2000:] or 'Media operation failed')
    return raw

@contextlib.contextmanager
def owned_stream(arguments,directory,stop,deadline,write=False,read=False):
    """One owned media process streamed by the caller's own thread: its stdin is fed and/or its stdout read here.

    There is no drain thread and no join timeout. A watchdog ends the process on Pause/Stop, the
    deadline or runaway diagnostics, which also releases a blocked read or write, and that cause is
    raised. After the body the input is closed and the exit status checked; a failed cleanup marks
    the producer uncertain, exactly like run_owned.
    """
    directory=Path(directory);token=uuid.uuid4().hex
    stdout=directory/(token+'.stdout');stderr=directory/(token+'.stderr');plan_generated(stderr)
    if not read:plan_generated(stdout)
    with open(stderr,'x+b') as err,(contextlib.nullcontext() if read else open(stdout,'x+b')) as out:
        process=subprocess.Popen(arguments,stdin=subprocess.PIPE if write else subprocess.DEVNULL,stdout=subprocess.PIPE if read else out,stderr=err,
            shell=False,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)|getattr(subprocess,'BELOW_NORMAL_PRIORITY_CLASS',0)|4)
        process._books_suspended=True
        cause=[];finished=threading.Event();started=time.monotonic();failed=None
        def watch():
            while not finished.wait(.1):
                if stop.is_set():cause.append(Paused('Audiobook operation paused; interrupted book restarts'))
                elif time.monotonic()-started>deadline:cause.append(TimeoutError('Owned media operation exceeded its deadline'))
                elif stderr.stat().st_size>1024*1024 or not read and stdout.stat().st_size>8*1024*1024:cause.append(ValidationError('Media diagnostic output exceeded its limit'))
                else:continue
                with contextlib.suppress(OSError):process.terminate()
                return
        with closed_media_job(process):
            watchdog=threading.Thread(target=watch,name='BooksArrangerMediaWatch',daemon=True);watchdog.start()
            try:
                yield process
                if write:process.stdin.close()
                while process.poll() is None:time.sleep(.05)  # the watchdog still enforces stop and deadline
            except BaseException as error:failed=error
            finally:
                finished.set()
                try:
                    if process.poll() is None:
                        process.terminate()
                        try:process.wait(timeout=3)
                        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
                    for pipe in (process.stdin,process.stdout):
                        if pipe is not None:
                            with contextlib.suppress(OSError):pipe.close()
                    watchdog.join(1)
                except BaseException:
                    uncertain_producer();raise
        detail=producer_bytes(err,stderr)
        if cause:raise cause[0] from failed
        if isinstance(failed,OSError) and process.returncode:
            # A closed pipe is the encoder's own failure, never a transient I/O error.
            raise ValidationError(detail.decode('utf-8','replace')[-2000:] or 'Media operation failed') from failed
        if failed is not None:raise failed
    if len(detail)>1024*1024:raise ValidationError('Media diagnostic output exceeded its limit')
    if process.returncode:raise ValidationError(detail.decode('utf-8','replace')[-2000:] or 'Media operation failed')


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
    if len(error_raw)>1024*1024:raise ValidationError('Decode diagnostics exceeded their limit')
    if state['error'] or process.returncode or state['bytes']%4:
        error=ValidationError('Full audio decode failed: '+error_raw.decode('utf-8','replace')[-1000:])
        if process.returncode and not state['error'] and state['bytes']%4==0:error.media_decode_failed=True
        raise error
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
    # Peak on the working drive: the source snapshots plus three output-sized files (the encoded
    # audiobook, its chapter/metadata rewrite and the publication copy when the library shares the
    # drive), plus 64 MiB. Normalized audio is streamed into the encoder, never written to disk.
    return source_bytes+3*output+64*1024*1024


def _mp3_tag_copy(manifest,item,path,stage,stop,duration):
    """Prove a finite non-audio tail repair; retain the original snapshot unchanged."""
    current=getattr(_ARTIFACTS,'current',None)
    if current is None or len(current)<5 or current[0]!=Path(stage):
        raise ValidationError('MP3 repair requires the current owned staging attempt')
    key=(item['path'],item['sha256']);cached=current[4].get(key)
    if cached is not None:
        if digest(stage/cached['name'],stop)!=cached['sha256']:raise ValidationError('Verified MP3 working copy changed')
        return cached
    if Path(path).suffix.lower()!='.mp3' or item['size']>mp3_tag_repair.MAX_BYTES:
        raise ValidationError('Source is outside the finite MP3 tag repair profile')
    data=Path(path).read_bytes()
    try:layout=mp3_tag_repair.plan(data)
    except mp3_tag_repair.UnsupportedProfile as exc:raise ValidationError(str(exc)) from exc
    if layout.source_sha256!=item['sha256']:raise ValidationError('MP3 repair source differs from frozen source')
    candidate=Path(stage)/('tag-repair-'+uuid.uuid4().hex+'.mp3');plan_generated(candidate)
    with candidate.open('xb') as stream:
        stream.write(data[:layout.prefix_size]);stream.flush();os.fsync(stream.fileno())
    candidate_sha=digest(candidate,stop);remember_generated(candidate,candidate_sha,layout.prefix_size)
    ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:raise ValidationError('Installed FFmpeg and FFprobe are required for tag preservation checks')
    def diagnose(args,telemetry=None,allow_nonzero=False):
        completed=[]
        try:
            raw=run_owned(args,stage,stop,max(300,duration*2),64*1024*1024,telemetry,
                diagnostic=lambda token,out,err:completed.append((token,out,err)))
        except ValidationError:
            if not allow_nonzero or not completed or not completed[0][0].data['returncode']:raise
            raw=completed[0][1]
        if not completed:raise ValidationError('No normal owned diagnostic completion')
        token,out,err=completed[0]
        if not allow_nonzero and err:raise ValidationError('Strict repair diagnostic reported errors')
        return raw,token
    prefix=[ffmpeg,'-hide_banner','-v','error','-xerror','-nostdin','-threads','2','-filter_threads','1','-protocol_whitelist','file','-f','mp3','-i']
    with ProtectedFiles([candidate]):
        packets=[]
        for source in (path,candidate):
            raw,_=diagnose([ffprobe,'-v','error','-protocol_whitelist','file','-f','mp3','-select_streams','a:0','-show_packets','-show_entries','packet=pts_time,dts_time,duration_time,pos,size,flags','-of','json',str(source)])
            packets.append(json.loads(raw)['packets'])
        try:packet_proof=mp3_tag_repair.verify_packets(*packets,layout)
        except mp3_tag_repair.UnsupportedProfile as exc:raise ValidationError(str(exc)) from exc
        decoded=[];frame_results=[]
        for source in (path,candidate):
            pcm=NativePcmHash(layout.channels)
            _,token=diagnose(prefix+[str(source),'-map','0:a:0','-c:a','pcm_f64le','-f','f64le','pipe:1'],pcm,True)
            result=pcm.result()
            if result['sample_count']!=layout.samples:
                # A normally completed child can still fail internally or run out of resources.
                # Partial PCM is a failed preservation proof, never evidence of source damage.
                raise ValidationError('MP3 preservation diagnostic is inconclusive: complete native audio could not be verified')
            if source==candidate and token.data['returncode']:raise ValidationError('Repaired MP3 still fails strict decoding')
            decoded.append(result)
            raw,frame_token=diagnose(prefix+[str(source),'-map','0:a:0','-c:a','pcm_s16le','-f','framemd5','-'],allow_nonzero=source==path)
            frame_results.append(raw)
        if decoded[0]!=decoded[1] or frame_results[0]!=frame_results[1]:raise ValidationError('MP3 repair changed decoded samples or frame timing')
        if digest(path,stop)!=item['sha256'] or digest(candidate,stop)!=candidate_sha:raise ValidationError('MP3 repair byte binding changed')
    proof=layout.receipt()|packet_proof|{'decision':'repairable','affected_audio_seconds':0,'native_pcm':decoded[0],
        'decoded_frames_sha256':hashlib.sha256(frame_results[0]).hexdigest(),'working_sha256':candidate_sha}
    write_generated(candidate.with_suffix('.json'),json.dumps(proof,ensure_ascii=False,sort_keys=True))
    cached={'name':candidate.name,'sha256':candidate_sha,'duration':layout.samples/layout.sample_rate,'proof':proof}
    current[4][key]=cached
    return cached


def _source_duration(manifest,item,path,stage,stop,duration):
    if m4b_repair.silence_approved(manifest):return duration
    current=getattr(_ARTIFACTS,'current',None)
    if current and len(current)>4 and (item['path'],item['sha256']) in current[4]:
        return _mp3_tag_copy(manifest,item,path,stage,stop,duration)['duration']
    try:return decoded_duration(path,stage,stop,duration)
    except ValidationError as original:
        if Path(path).suffix.lower()!='.mp3' or not getattr(original,'media_decode_failed',False):raise
        try:return _mp3_tag_copy(manifest,item,path,stage,stop,duration)['duration']
        except ValidationError as repair:
            raise original from repair


def check_working_space(manifest, stage, stop):
    if shutil.disk_usage(stage).free<sum(item['size'] for item in manifest['sources'])+64*1024*1024:
        raise OSError(errno.ENOSPC,'Insufficient staging space before source admission; originals retained')
    durations=[];profiles=[]
    for item in manifest['sources']:
        path=ordinary(item['path'])
        if not path.is_relative_to(ordinary(manifest['root'])) or path.suffix.lower() not in INPUT_FORMATS:
            raise ValidationError('Source is outside the supported audiobook boundary')
        with DirectoryBoundary(manifest['root'],path.parent),VerifiedFile(path) as held:
            stat=source_proofs.stat_of(path)
            if held.facts()['size']!=item['size'] or str(held.facts()['modified'])!=str(item['modified']) or not source_proofs.unchanged(path,item['sha256'],stat) and held.sha256()!=item['sha256']:
                raise ValidationError('Source changed before working-space admission')
            source_proofs.remember(path,item['sha256'],stat,source_proofs.stat_of(path))
            raw=probe(path,stage,stop);duration,profile=audio_info(raw)
            stream=next(s for s in raw['streams'] if s.get('codec_type')=='audio')
            profiles.append((*profile,stream.get('bit_rate'),stream.get('channel_layout')))
            durations.append(_source_duration(manifest,item,path,stage,stop,duration))
    if manifest.get('profile')==AUTOMATIC_PROFILE:
        encoding=choose_automatic_encoding(profiles,single_m4b=len(profiles)==1 and Path(manifest['sources'][0]['path']).suffix.lower()=='.m4b')
    elif manifest.get('profile')==PROFILE:encoding=choose_encoding(profiles)
    elif manifest.get('profile')==LEGACY_PROFILE:encoding={'bitrate':160000,'channels':2,'sample_rate':44100}
    else:raise ValidationError('Unsupported frozen encoding profile')
    source_bytes=sum(item['size'] for item in manifest['sources'])
    required=working_space_required(source_bytes,durations,encoding,len(durations))
    if shutil.disk_usage(stage).free<required:
        raise OSError(errno.ENOSPC,f'Insufficient working space; need {required/1024**3:.1f} GB free before snapshotting; originals retained')
    root=ordinary(manifest.get('output_root',manifest['root']));destination=ordinary(manifest['destination'])
    if not destination.is_relative_to(root):raise ValidationError('Destination is outside the audiobook library')
    parent=destination.parent
    while not parent.exists():
        if parent==root:raise ValidationError('Audiobook destination root is unavailable')
        parent=parent.parent
    with DirectoryBoundary(root,parent):
        if shutil.disk_usage(parent).free<output_space_required(source_bytes,durations,encoding,len(durations)):
            raise OSError(errno.ENOSPC,'Insufficient destination space before conversion; originals retained')
    return required


def snapshot_manifest(manifest,stage,stop,report=None):
    sources=manifest['sources']
    # Each track is read four times (check, copy, check, check the copy), then probed and decoded:
    # reads move the track from 0 to 90 %, the decode finishes it.
    step=StepProgress(report,'preparing',len(sources),'files',len(sources))
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
        weight=4*max(1,int(item.get('size') or 0));seen=[0]
        def read(count,index=index,weight=weight,seen=seen):
            seen[0]+=count;step.update(index+.9*min(1,seen[0]/weight),index+1)
        step.update(index,index+1,force=True)
        same_source(item,stop,read)
        alias=stage/(f'source{index:05}'+source.suffix.lower())
        copy_owned(source,alias,item['sha256'],stop,read)
        same_source(item,stop,read)
        # Read bitrate/profile and PCM duration from the same protected, hash-verified bytes.
        with ProtectedFiles([alias]):
            if digest(alias,stop,read)!=item['sha256']:raise ValidationError('Protected snapshot differs from reviewed source bytes')
            raw=probe(alias,stage,stop)
            if joined_m4b and alias.suffix in ('.m4b','.m4a') and len(raw.get('chapters') or [])>1:
                raise ValidationError('Existing M4B parts carry their own chapters; they must be arranged individually to preserve every source chapter plan')
            duration,profile=audio_info(raw)
            if manifest.get('profile')==LEGACY_PROFILE and compatibility is not None and compatibility!=profile:
                raise ValidationError('Included files have incompatible recording/audio stream parameters')
            compatibility=profile
            stream=next(s for s in raw['streams'] if s.get('codec_type')=='audio')
            profiles.append((*profile,stream.get('bit_rate'),stream.get('channel_layout')))
            duration=_source_duration(manifest,item,alias,stage,stop,duration)
        durations.append(duration);copies.append(alias.name)
        step.update(index+1,index+1,force=True)
    return copies,durations,protected_cover(manifest,stage,stop),profiles

def protected_cover(manifest,stage,stop):
    """The reviewed cover as an owned hash-checked stage copy, probed (and decoded for the automatic profile)."""
    cover=manifest['cover']
    cover_source=ordinary(cover['path'])
    if cover_source.stat().st_size>MAX_IMAGE:raise ValidationError('Selected cover exceeds8 MiB')
    cover_bytes=cover_source.read_bytes()
    extension='.png' if cover_bytes.startswith(b'\x89PNG\r\n\x1a\n') else '.jpg' if cover_bytes.startswith(b'\xff\xd8\xff') else None
    if extension is None:raise ValidationError('Select one usable JPEG or PNG cover')
    cover_copy=stage/('cover'+extension)
    # An in-place attempt that fell back may already own this exact copy in this stage. Reuse the copy, never a skipped
    # gate: the probe, dimension check or decode below may be the very refusal that made it fall back (0.21.0 F1).
    if not (os.path.lexists(cover_copy) and digest(cover_copy,stop)==cover['sha256']):
        copy_owned(cover_source,cover_copy,cover['sha256'],stop)
    image=probe(cover_copy,stage,stop)
    image_streams=[s for s in image.get('streams',[]) if s.get('codec_type')=='video']
    if len(image_streams)!=1 or image_streams[0].get('width',0)*image_streams[0].get('height',0)>16000000:
        raise ValidationError('Selected cover dimensions are invalid or too large')
    if manifest.get('profile')==AUTOMATIC_PROFILE:
        run_owned([shutil.which('ffmpeg'),'-v','error','-xerror','-nostdin','-protocol_whitelist','file','-f','image2','-i',str(cover_copy),'-map','0:v:0','-frames:v','1','-f','null','-'],stage,stop,30)
    return cover_copy

def create_private(manifest,stage_root,stop,progress=lambda *_:None,artifact_observer=None,in_place=None):
    """in_place (0.21.0): an inplace_m4b.Session. An eligible single M4B is then edited in place and returned as an
    inplace_m4b.Edited (held, verified, not yet moved); anything else continues with the copy flow below."""
    if artifact_observer is None:
        return _create_private(manifest,stage_root,stop,progress,in_place=in_place)
    artifact_observer.begin(manifest)
    stage=ordinary(stage_root)/manifest['job_id']/manifest['attempt_id']
    attempt_context={'entered':False}
    try:return _create_private(manifest,stage_root,stop,progress,artifact_observer,attempt_context,in_place)
    finally:
        # Failure before entering generated_artifacts created no media producer.
        # Inside it, closed() always records either closed or uncertain first.
        if not attempt_context['entered']:
            error=sys.exc_info()[1]
            try:artifact_observer.closed(stage,producer_closed=True)
            except Exception:
                if error is None:raise


def _create_private(manifest,stage_root,stop,progress=lambda *_:None,artifact_observer=None,attempt_context=None,in_place=None):
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
                if in_place is not None:
                    import inplace_m4b
                    edited=inplace_m4b.edit(manifest,stage,stop,progress,in_place)
                    if edited is not None:
                        edited.validation['staging_artifacts']={'attempt_id':attempt,'files':generated}
                        return edited,edited.validation
                report=lambda value:progress('Checking sources',{'progress':value})
                copies,durations,cover,profiles=snapshot_manifest(manifest,stage,stop,report)
                with ProtectedFiles([stage/name for name in copies]+[cover]):
                    step=StepProgress(report,'source copies',sum(int(item.get('size') or 0) for item in manifest['sources'])+cover.stat().st_size,'bytes');done=[0]
                    def read(count):done[0]+=count;step.update(done[0])
                    step.update(0,force=True)
                    for name,item in zip(copies,manifest['sources']):
                        if digest(stage/name,stop,read)!=item['sha256']:raise ValidationError('Protected snapshot differs from reviewed source bytes')
                    if digest(cover,stop,read)!=manifest['cover']['sha256']:raise ValidationError('Protected cover differs from reviewed artwork')
                    step.update(done[0],force=True)
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


def normalized_pcm_evidence(path,stage,stop,duration,encoding,kind=None,aggregate=None,on_seconds=None):
    proof=NativePcmHash(encoding['channels']) if kind is None else ExpandedPcmHash(encoding['channels'],kind)
    telemetry=proof
    if aggregate is not None:
        if kind is not None:raise ValidationError('Canonical aggregate cannot use a quantized candidate')
        class Fanout:
            def feed(self,raw):proof.feed(raw);aggregate.feed(raw)
        telemetry=Fanout()
    if on_seconds is not None:telemetry=PcmSeconds(telemetry,encoding['sample_rate'],encoding['channels'],{None:8,'s16':2,'s24':3,'s32':4,'f32':4}[kind],on_seconds)
    codec,format=('pcm_f64le','f64le') if kind is None else {'s16':('pcm_s16le','s16le'),'s24':('pcm_s24le','s24le'),'s32':('pcm_s32le','s32le'),'f32':('pcm_f32le','f32le')}[kind]
    run_owned([shutil.which('ffmpeg'),'-hide_banner','-v','error','-xerror','-nostdin','-threads','2','-filter_threads','1',
      '-protocol_whitelist','file','-f',INPUT_FORMATS[Path(path).suffix.lower()],'-i',str(path),'-map','0:a:0',
      '-af',normalization_filter(encoding),'-c:a',codec,'-f',format,'pipe:1'],stage,stop,max(300,duration*2),telemetry=telemetry)
    return proof.result()


def normalized_references(stage,copies,encoding,stop,durations,report=None):
    """Canonical proof of the complete normalized source audio: one f64 decode per track, hashed per track and joined.

    The encoder is later fed this same normalized PCM as a stream (stream_normalized), and every fed
    byte must reproduce these proofs. No uncompressed copy of the book is ever written to disk.
    """
    aggregate=NativePcmHash(encoding['channels']);total=sum(durations);count=len(copies)
    step=StepProgress(report,'checking audio',total,'seconds',count);references=[]
    for index,(name,duration) in enumerate(zip(copies,durations)):
        offset=sum(durations[:index]);step.update(offset,index+1,force=True)
        references.append(normalized_pcm_evidence(stage/name,stage,stop,duration,encoding,aggregate=aggregate,
            on_seconds=lambda seconds,offset=offset,index=index,duration=duration:step.update(offset+min(duration,seconds),index+1)))
    step.update(total,count,force=True)
    joined=aggregate.result()
    if joined['sample_count']!=sum(reference['sample_count'] for reference in references):raise ValidationError('Joined original normalized sample count changed')
    return references,joined


def stream_normalized(write,stage,copies,durations,encoding,stop,references,joined,report=None):
    """Feed the encoder the complete normalized f64 PCM, track by track, re-proving every byte fed.

    Each track's stream must equal its reference proof, and the whole fed stream the joined proof,
    before the encoder's input is closed; any difference stops the encoder and nothing is published.
    The decode is the reference decode (same filter, codec and format), so the bytes are identical.
    """
    aggregate=NativePcmHash(encoding['channels']);total=sum(durations);per_second=encoding['sample_rate']*encoding['channels']*8;fed=0
    step=StepProgress(report,'encoding',total,'seconds');step.update(0,force=True)
    for name,duration,reference in zip(copies,durations,references):
        proof=NativePcmHash(encoding['channels'])
        with owned_stream([shutil.which('ffmpeg'),'-hide_banner','-v','error','-xerror','-nostdin','-threads','2','-filter_threads','1',
              '-protocol_whitelist','file','-f',INPUT_FORMATS[Path(name).suffix.lower()],'-i',str(stage/name),'-map','0:a:0',
              '-af',normalization_filter(encoding),'-c:a','pcm_f64le','-f','f64le','pipe:1'],stage,stop,max(300,duration*2),read=True) as decoder:
            while block:=decoder.stdout.read1(1024*1024):
                proof.feed(block);aggregate.feed(block);write(block);fed+=len(block)
                step.update(fed/per_second)
        if proof.result()!=reference:raise ValidationError('Streamed normalized PCM differs from its complete-source proof')
    if aggregate.result()!=joined:raise ValidationError('Streamed normalized PCM differs from the complete ordered source proof')
    step.update(total,force=True)


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
        # format.start_time is the minimum over every stream, including the attached cover that
        # preservation adds to a coverless source (its 1/90000 clock rounds earlier). The movie
        # start is therefore taken, exactly, over the streams that are not attached pictures.
        listing=json.loads(run_owned([executable,'-v','error','-protocol_whitelist','file','-f',INPUT_FORMATS[Path(path).suffix.lower()],
          '-show_entries','stream=index,start_time:stream_disposition=attached_pic','-of','json',str(path)],stage,stop,30))
        starts=[item.get('start_time') for item in listing.get('streams',[]) if not (item.get('disposition') or {}).get('attached_pic')]
        try:presentation['movie']['start_time']=min(starts,key=Fraction)
        except (ValueError,TypeError,ZeroDivisionError):raise ValidationError('Source-relative M4B presentation evidence is missing')
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


def native_pcm_evidence(path,stage,stop,duration,encoding,on_seconds=None):
    proof=NativePcmHash(encoding['channels'])
    # on_seconds only for normalized working files, whose native rate and channels are the encoding's.
    telemetry=proof if on_seconds is None else PcmSeconds(proof,encoding['sample_rate'],encoding['channels'],8,on_seconds)
    # No resampling or channel selection: hash the decoder's complete native-rate,
    # all-channel output, including the effect of codec priming/discard/edit trims.
    run_owned([shutil.which('ffmpeg'),'-hide_banner','-v','error','-xerror','-nostdin','-threads','2','-filter_threads','1',
      '-protocol_whitelist','file','-f',INPUT_FORMATS[Path(path).suffix.lower()],'-i',str(path),'-map','0:a:0',
      '-c:a','pcm_f64le','-f','f64le','pipe:1'],stage,stop,max(300,duration*2),telemetry=telemetry)
    return proof.result()|{'sample_rate':encoding['sample_rate'],'channels':encoding['channels'],'channel_layout':encoding.get('channel_layout')}

def _encode_private(manifest,stage,copies,durations,cover,stop,progress,encoding):
    original_copies=list(copies);joined=None;feed=None
    current=getattr(_ARTIFACTS,'current',None);repairs=[]
    if current is not None and len(current)>4:
        copies=list(copies)
        for index,item in enumerate(manifest['sources']):
            repaired=current[4].get((item['path'],item['sha256']))
            if repaired:
                if digest(stage/repaired['name'],stop)!=repaired['sha256']:raise ValidationError('MP3 working repair changed before encoding')
                copies[index]=repaired['name'];repairs.append(repaired['proof'])
    with ProtectedFiles([stage/name for name in copies if name not in original_copies]):
        for repaired in (current[4].values() if current is not None and len(current)>4 else ()):
            if digest(stage/repaired['name'],stop)!=repaired['sha256']:raise ValidationError('Protected MP3 working repair changed')
        return _encode_repaired_inputs(manifest,stage,copies,durations,cover,stop,progress,encoding,original_copies,repairs)


def _encode_repaired_inputs(manifest,stage,copies,durations,cover,stop,progress,encoding,original_copies,repairs):
    joined=None;feed=None
    if encoding.get('mode')=='normalize':
        # The protected source snapshots are the only inputs; their normalized audio is proven, then
        # streamed into the encoder and proven again byte for byte (no WAV or concat plan on disk).
        report=lambda value:progress('Checking sources',{'progress':value})
        references,joined=normalized_references(stage,copies,encoding,stop,durations,report)
        feed=lambda write,fed_report:stream_normalized(write,stage,copies,durations,encoding,stop,references,joined,fed_report)
    output,validation=_encode_inputs(manifest,stage,copies,durations,cover,stop,progress,encoding,original_copies,feed)
    if joined is not None:
        validation['normalized_joined_pcm']=joined;validation['normalized_pcm_codec']='pcm_f64le'
    if repairs:validation['source_working_repairs']=repairs
    return output,validation


def _encode_inputs(manifest,stage,copies,durations,cover,stop,progress,encoding,original_copies,feed=None):
    required=3*output_space_required(sum(item['size'] for item in manifest['sources']),durations,encoding,len(copies))+64*1024*1024
    if shutil.disk_usage(stage).free<required:raise OSError(errno.ENOSPC,'Staging space changed before output creation; originals retained')
    executable=shutil.which('ffmpeg')
    if not executable:raise ValidationError('Installed ffmpeg is required for audiobook creation')
    if feed is None:write_generated(stage/'inputs.txt',''.join(f"file '{name}'\n" for name in copies))
    review=manifest['metadata'];tags=approved_tags(manifest)
    if encoding.get('mode')=='copy' and encoding.get('codec')=='aac' and len(original_copies)==1 and Path(original_copies[0]).suffix.lower()=='.m4b':
        return _preserve_single_m4b(manifest,stage,original_copies[0],durations,cover,stop,progress,encoding,tags)
    return _encode_tagged(manifest,stage,copies,durations,cover,stop,progress,encoding,original_copies,feed,executable,review,tags)


def approved_tags(manifest):
    """The approved audiobook tags for the reviewed book; one definition for every output path."""
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
    return tags


def preservation_tags(manifest,tags=None):
    """Tags written by metadata preservation (copy flow and in-place edit): approved tags plus the sort title."""
    tags=approved_tags(manifest) if tags is None else tags
    sort_title=audiobook_sort_title(manifest['metadata'])
    return tags|{'sort_name':sort_title} if sort_title!=manifest['metadata']['title'] else tags


def _encode_tagged(manifest,stage,copies,durations,cover,stop,progress,encoding,original_copies,feed,executable,review,tags):
    output=stage/'checked.m4b'
    if feed is not None:source_input=['-protocol_whitelist','pipe','-format_whitelist','f64le','-f','f64le','-ar',str(encoding['sample_rate']),'-ac',str(encoding['channels']),'-i','pipe:0']
    else:source_input=['-protocol_whitelist','file','-format_whitelist','concat,mp3,mov,aac,flac,ogg,wav,asf',
      *(['-f','mov','-i',str(stage/original_copies[0])] if encoding.get('mode')=='copy' else ['-f','concat','-safe','1','-i',str(stage/'inputs.txt')])]
    args=[executable,'-hide_banner','-v','error','-xerror','-nostdin','-n','-threads','2','-filter_threads','1',*source_input,'-f','image2','-i',str(cover)]
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
    args+=(['-nostats'] if feed is not None else ['-progress','pipe:1','-stats_period','1','-nostats'])+['-f','mp4',str(output)]
    progress('Creating audio',{'duration':sum(durations),'source_durations':durations,'source_pcm_frames':[round(d*44100) for d in durations],'source_pcm_rate':44100,'encoding':encoding})
    plan_generated(output)
    if feed is not None:
        # Progress is the audio fed so far; the encoder trails it by at most a pipe buffer.
        with owned_stream(args,stage,stop,max(300,sum(durations)*2),write=True) as encoder:
            feed(encoder.stdin.write,lambda value:progress('Creating audio',{'progress':value}))
    else:run_owned(args,stage,stop,max(300,sum(durations)*2),telemetry=EncodingProgress(sum(durations),lambda value:progress('Creating audio',{'progress':value})))
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
    tags=preservation_tags(manifest,tags)
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
            plan=m4b_preservation.plan(source_facts['size'],read_at,tags,cover_bytes,m4b_repair.approved_repairs(manifest))
            repair_note=m4b_repair.confirm(manifest,plan)
            if shutil.disk_usage(stage).free<source_facts['size']+plan.tail_padding+len(plan.appended_media)+len(plan.appended_movie)+16*1024*1024:
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
                if m4b_repair.silenced(plan):
                    output_evidence,output_pcm,silence_proof=m4b_repair.prove_silenced_tail(source,output,plan,stage,stop,expected,encoding,
                        evidence=copied_audio_evidence,run=run_owned)
                    repair_note=repair_note|{'silence_proof':silence_proof}
                else:
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
                if repair_note:validation['damage_repair']=repair_note
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
    expected_tags=([('title',review['title'])] if review.get('title') else [])+[('artist',review['canonical_author']),('album_artist',review['canonical_author']),('media_type','2')]
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

def publish(output,manifest,validation,stop,journal,revision_guard,review_lock=None,report=None):
    destination=ordinary(manifest['destination']);root=ordinary(manifest.get('output_root',manifest['root']))
    if destination.suffix.lower()!='.m4b':raise ValidationError('Only a reviewed M4B destination can be published')
    if any(os.path.normcase(str(destination))==os.path.normcase(item['path']) for item in manifest['sources']):raise ValidationError('Output must be distinct from every source')
    # Measured: every source is re-checked, the audiobook is copied, then every source is re-checked again.
    step=StepProgress(report,'publishing',2*sum(int(item.get('size') or 0) for item in manifest['sources'])+int(validation.get('size') or 0),'bytes');done=[0]
    def read(count):done[0]+=count;step.update(done[0])
    step.update(0,force=True)
    for item in manifest['sources']:same_source(item,stop,read)
    if not revision_guard():raise ValidationError('Candidate review changed — review required')
    with DirectoryBoundary(root,destination.parent,create=True) as boundary:
        if destination.exists():raise FileExistsError('An audiobook already exists at this path; nothing was overwritten')
        if shutil.disk_usage(destination.parent).free<validation['size']+16*1024*1024:raise ValidationError('Insufficient destination space')
        temporary=destination.parent/('.books-arranger-'+manifest['job_id']+'-'+manifest.get('attempt_id',str(uuid.uuid4()))+'.partial')
        journal('copying',{'temporary':str(temporary),'destination':str(destination),'validation':validation,'parent_identity':boundary.identities})
        copy_owned(output,temporary,validation['sha256'],stop,read)
        if stop.is_set():raise Paused('Publication paused; owned temporary retained for recovery')
        for item in manifest['sources']:same_source(item,stop,read)
        step.update(done[0],force=True)
        if digest(manifest['cover']['path'],stop)!=manifest['cover']['sha256']:raise ValidationError('Cover changed — review required')
        with review_lock if review_lock is not None else contextlib.nullcontext():
            if not revision_guard():raise ValidationError('Candidate review changed — review required')
            boundary.revalidate()
            journal('publishing',{'temporary':str(temporary),'destination':str(destination),'validation':validation,'parent_identity':boundary.identities})
            publish_no_replace(temporary,destination,boundary,validation['sha256'],validation['size'])
        if digest(destination)!=validation['sha256']:raise ValidationError('Published output hash did not match the checked artifact')
        journal('completed',{'destination':str(destination),'validation':validation})
    return str(destination)
