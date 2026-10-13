"""Retain exact downloaded installer bytes and ordinary cache ancestry until shell closes pipe."""
import hashlib,json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from native_io import DirectoryBoundary,VerifiedFile
from source_cleanup import single_stream

def main(argv=None):
    path,expected=list(sys.argv[1:] if argv is None else argv)
    path=Path(path).absolute()
    if path.suffix.lower()!='.exe':raise ValueError('Update artifact must be the installer executable')
    with DirectoryBoundary(path.anchor,path.parent),VerifiedFile(path) as held:
        if held.facts()['links']!=1:raise RuntimeError('Downloaded update must be unique')
        single_stream(path)
        import base64
        digest=hashlib.sha512()
        for chunk in held.chunks():digest.update(chunk)
        if base64.b64encode(digest.digest()).decode('ascii')!=expected:raise RuntimeError('Downloaded installer checksum changed; check and download again')
        print(json.dumps({'type':'books-update-lease-v1','sha512':expected}),flush=True)
        while os.read(sys.stdin.fileno(),4096):pass
    return 0
if __name__=='__main__':raise SystemExit(main())
