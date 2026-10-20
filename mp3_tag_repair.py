"""Finite ID3v1-tail repair planning; never edits a reviewed source or ignores audio errors."""
import hashlib,json
from dataclasses import dataclass

VERSION='mp3-id3v1-preservation-v1'
MAX_BYTES=64*1024*1024
class UnsupportedProfile(ValueError):pass
def require(value,message):
    if not value:raise UnsupportedProfile(message)
def sha(value):return hashlib.sha256(value).hexdigest()

@dataclass(frozen=True)
class Layout:
    source_sha256:str
    source_size:int
    prefix_size:int
    audio_start:int
    frames:tuple
    sample_rate:int
    channels:int
    audio_sha256:str
    footer_sha256:str
    @property
    def samples(self):return len(self.frames)*1152
    def receipt(self):
        return {'version':VERSION,'source_sha256':self.source_sha256,'source_size':self.source_size,
            'prefix_size':self.prefix_size,'audio_start':self.audio_start,'frame_count':len(self.frames),
            'sample_rate':self.sample_rate,'channels':self.channels,'sample_count':self.samples,
            'audio_bytes_sha256':self.audio_sha256,'removed_bytes':128,'removed_kind':'terminal ID3v1 tag',
            'removed_sha256':self.footer_sha256}

def plan(data):
    require(isinstance(data,bytes) and 132<len(data)<=MAX_BYTES,'Outside bounded MP3 profile')
    end=len(data)-128;require(data[end:end+3]==b'TAG','No exact terminal ID3v1 tag')
    start=0
    if data[:3]==b'ID3':
        require(data[3:6]==b'\x03\x00\x00' and not any(b&128 for b in data[6:10]),'Unsupported leading ID3 shape')
        start=10+sum(b<<(7*(3-i)) for i,b in enumerate(data[6:10]))
        require(10<=start<=8*1024*1024 and start<end,'Leading ID3 extent is invalid')
        require(b'iTunSMPB' not in data[:start],'Gapless metadata needs independent proof')
    frames=[];position=start;configuration=None
    rates=(44100,48000,32000);bitrates=(0,32,40,48,56,64,80,96,112,128,160,192,224,256,320)
    while position<end:
        require(position+4<=end,'Partial MP3 frame header')
        h=int.from_bytes(data[position:position+4],'big');index=(h>>12)&15;rate_index=(h>>10)&3
        require(h>>21==2047 and (h>>19)&3==3 and (h>>17)&3==1 and index not in (0,15) and rate_index!=3,'Noncontiguous/unsupported MPEG audio')
        rate=rates[rate_index];channels=1 if (h>>6)&3==3 else 2
        if configuration is None:configuration=(rate,channels)
        require(configuration==(rate,channels),'Changing MP3 audio configuration')
        length=144000*bitrates[index]//rate+((h>>9)&1)
        require(position+length<=end,'Partial MP3 audio frame')
        frames.append((position,length));position+=length
    require(position==end and len(frames)>=3,'No complete contiguous MP3 frame region')
    first=data[start:start+frames[0][1]]
    require(not any(marker in first for marker in (b'Xing',b'Info',b'VBRI',b'LAME')),'Encoder delay/seek metadata needs independent proof')
    return Layout(sha(data),len(data),end,start,tuple(frames),*configuration,sha(data[start:end]),sha(data[end:]))

def verify_packets(original,candidate,layout):
    require(isinstance(original,list) and isinstance(candidate,list),'Packet evidence missing')
    require(len(candidate)==len(layout.frames),'Decoded packet count differs from audio frames')
    require(original[:len(candidate)]==candidate,'Audio packet timing/flags changed')
    for packet,(position,length) in zip(candidate,layout.frames):
        require(int(packet.get('pos',-1))==position and int(packet.get('size',-1))==length,'Audio packet extent differs')
        require(not packet.get('side_data_list'),'Decoder trim metadata needs independent proof')
        require(all(key in packet for key in ('pts_time','dts_time','duration_time')),'Packet timestamps missing')
    extra=original[len(candidate):]
    require(1<=len(extra)<=2,'Unexpected terminal packet layout')
    position=layout.prefix_size
    for packet in extra:
        size=int(packet.get('size',0));require(int(packet.get('pos',-1))==position and 0<size<=128,'Terminal packet extent differs');position+=size
    require(position==layout.source_size,'Terminal packets are not exactly the tag')
    return {'packet_count':len(candidate),'all_audio_packet_timing_equal':True,'terminal_non_audio_packets':len(extra)}

_INTERNAL=object()
@dataclass(frozen=True,init=False)
class SourceDamageAssessment:
    """Internal typed diagnostic value, not native authority or an importable receipt."""
    _json:str
    def __init__(self,value,seal=None):
        if seal is not _INTERNAL:raise TypeError('Only the internal diagnostic producer creates assessments')
        object.__setattr__(self,'_json',json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')))
    def as_dict(self):return json.loads(self._json)
    @property
    def data(self):return self.as_dict()

def assessment(manifest,item,layout,pcm,diagnostics):
    """Compatibility interface: no source-damage producer is established here.

    Child completion plus partial PCM cannot distinguish corrupt audio from resource,
    decoder or tool failure. Keep this refusing until an independently reviewed,
    source-specific positive damage proof exists; never turn that ambiguity into a hold.
    """
    raise UnsupportedProfile('Damage assessment unavailable: independent source-specific damage proof is required')

@dataclass(frozen=True,init=False)
class CompletedDiagnostic:
    """Normal existing owned-context completion, not a checked native-close receipt."""
    _json:str
    def __init__(self,value,seal=None):
        if seal is not _INTERNAL:raise TypeError('Internal completion only')
        object.__setattr__(self,'_json',json.dumps(value,sort_keys=True,separators=(',',':')))
    @property
    def data(self):return json.loads(self._json)

def completed_diagnostic(arguments,returncode,stdout,stderr):
    """Pipeline calls only after normal owned context exit, drain and output bounds."""
    return CompletedDiagnostic({'context_completed':True,'returncode':returncode,
        'argv':list(arguments),'tool_sha256':sha(__import__('pathlib').Path(arguments[0]).read_bytes()),
        'script_sha256':sha(__import__('pathlib').Path(__file__).read_bytes()),
        'stdout_sha256':sha(stdout),'stderr_sha256':sha(stderr)},_INTERNAL)
