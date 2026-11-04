import base64,gzip,hashlib,json,pathlib,struct,sys,time
root=pathlib.Path(__file__).resolve().parent;source=pathlib.Path('C:/Antigravity Projects/Worktrees/Books Arranger/converted-duplicate-20261104');main=pathlib.Path('C:/Antigravity Projects/Studio Illuminati/WIP/Books Arranger')
sys.path.insert(0,str(source));sys.stdout.reconfigure(encoding='utf8');sys.stderr.reconfigure(encoding='utf8')
from native_io import DirectoryBoundary,VerifiedFile,ordinary
previous=json.loads((main/'Docs/Evidence/converted-duplicate_2026-11-04/source-diagnostics-025/diagnostic-selective.json').read_text('utf8'))
target=previous['koontz'][-1]
if pathlib.PureWindowsPath(target['path']).name!='12.mp3' or target['expected_size']!=15490216 or 'strict_decode_error' not in target:raise RuntimeError('Not the exact approved first failed source')
start=time.monotonic();ranges=[];read_bytes=0;output={'path':target['path'],'expected_native':target['native_after'],'prior_visited_extents':sum(s['expected_size'] for s in previous['koontz'])}
try:
    path=ordinary(target['path'])
    with DirectoryBoundary(path.anchor,path.parent),VerifiedFile(path) as file:
        before=file.refresh();output['native_before']=before
        if any(before[k]!=target['native_after'][k] for k in ('identity','dev','ino','size','modified')):raise RuntimeError('Exact approved native source changed')
        def read(at,count,purpose):
            global read_bytes
            if time.monotonic()-start>570:raise TimeoutError('Stop: bounded metadata diagnostic time')
            if at<0 or at+count>before['size'] or read_bytes+count>2097152:raise RuntimeError('Stop: exact approved range byte cap')
            data=file.read_at(at,count)
            if len(data)!=count:raise RuntimeError('Stop: short metadata range read')
            ranges.append([at,count,purpose]);read_bytes+=count;return data
        head=read(0,min(131072,before['size']),'head');tail_start=max(0,before['size']-131072);tail=read(tail_start,before['size']-tail_start,'tail')
        output['head_sha256']=hashlib.sha256(head).hexdigest();output['tail_sha256']=hashlib.sha256(tail).hexdigest()
        at=0
        if head[:3]==b'ID3':
            if len(head)<10 or any(x&128 for x in head[6:10]):raise RuntimeError('Unknown ID3 header shape')
            length=sum(b<<(7*(3-i)) for i,b in enumerate(head[6:10]));at=10+length+(10 if head[3]==4 and head[5]&16 else 0)
            output['leading_id3']={'major':head[3],'revision':head[4],'flags':head[5],'declared_payload':length,'audio_start':at,'contains_iTunSMPB':b'iTunSMPB' in head,'contains_XMP':b'xmp' in head.lower()}
        end=before['size'];output['terminal_id3v1']=tail[-128:-125]==b'TAG'
        if output['terminal_id3v1']:end-=128
        output['terminal_ape_marker']=b'APETAGEX' in tail[-512:]
        if not 0<=at<end:raise RuntimeError('Leading metadata extent invalid')
        count=0;configuration=None;first_position=at;first_length=None
        while at<end:
            if at+4>end:output['frame_error']={'offset':at,'reason':'Partial MPEG frame header'};break
            if at+4<=len(head):raw=head[at:at+4]
            elif at>=tail_start:raw=tail[at-tail_start:at-tail_start+4]
            else:raw=read(at,4,'mpeg-frame-header')
            header=int.from_bytes(raw,'big');version=(header>>19)&3;layer=(header>>17)&3;bitrate_index=(header>>12)&15;rate_index=(header>>10)&3
            if header>>21!=2047 or version==1 or layer!=1 or bitrate_index in (0,15) or rate_index==3:
                sample=read(at,min(64,before['size']-at),'failed-header-metadata')
                output['frame_error']={'offset':at,'reason':'Noncontiguous/unsupported MPEG Layer III header','raw_base64':base64.b64encode(sample).decode()};break
            base_rate=(44100,48000,32000)[rate_index];rate=base_rate//(1 if version==3 else 2 if version==2 else 4);channels=1 if (header>>6)&3==3 else 2
            rates=(0,32,40,48,56,64,80,96,112,128,160,192,224,256,320) if version==3 else (0,8,16,24,32,40,48,56,64,80,96,112,128,144,160)
            length=(144000 if version==3 else 72000)*rates[bitrate_index]//rate+((header>>9)&1)
            current=(version,rate,channels)
            if configuration is None:configuration=current;first_length=length
            if current!=configuration or at+length>end:output['frame_error']={'offset':at,'reason':'Changing configuration or partial audio frame','frame_length':length,'audio_end':end};break
            count+=1;at+=length
        output.update(frame_headers=count,audio_end=end,final_header_position=at,configuration=configuration,headers_contiguous_to_metadata=at==end)
        if first_length and first_position+first_length<=len(head):output['encoder_seek_markers']=[m.decode() for m in (b'Xing',b'Info',b'VBRI',b'LAME') if m in head[first_position:first_position+first_length]]
        after=file.refresh();output['native_after']=after
        if any(before[k]!=after[k] for k in ('identity','dev','ino','size','modified')):raise RuntimeError('Source changed during read-only metadata check')
except BaseException as error:output['stopped']={'class':type(error).__name__,'message':str(error)};raise
finally:
    output['read_bytes']=read_bytes;output['elapsed_seconds']=time.monotonic()-start;output['range_count']=len(ranges)
    compressed=gzip.compress(json.dumps(ranges,separators=(',',':')).encode(),mtime=0);(root/'followup-ranges.json.gz').write_bytes(compressed);output['ranges_sha256']=hashlib.sha256(compressed).hexdigest()
    (root/'followup.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(output,ensure_ascii=True))
