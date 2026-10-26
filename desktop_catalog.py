"""Explicit in-place desktop catalog selection; never migrates or rewrites receipts."""
import argparse,json,os,sqlite3,sys
from contextlib import closing
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from scanner import inside
from native_io import DirectoryBoundary,VerifiedFile
from source_cleanup import single_stream

def inspect_folder(folder,mode,roots,install_roots=(),allow_lock=False):
    folder=Path(folder).absolute()
    if mode not in ('existing','new'):raise ValueError('Choose an existing folder or explicitly create a new catalog')
    if any(inside(folder,root) for root in [*roots.values(),*install_roots]):
        raise ValueError('Keep data outside source libraries and installation folders')
    if not folder.exists():
        if mode=='existing':raise ValueError('The selected existing data folder is unavailable')
        # Validate every existing ancestor before the explicit create operation.
        ancestor=folder.parent
        while not ancestor.exists():ancestor=ancestor.parent
        with DirectoryBoundary(ancestor.anchor,ancestor):pass
        return {'mode':'new','folder':str(folder)}
    with DirectoryBoundary(folder.anchor,folder):
        database=folder/'inventory.sqlite3'
        entries=list(folder.iterdir())
        if mode=='new':
            permitted={Path(str(database)+'.lock')} if allow_lock else set()
            if any(entry not in permitted for entry in entries):
                raise ValueError('Choose an empty new folder, or select Existing folder for a recognized catalog')
            return {'mode':'new','folder':str(folder)}
        if not database.exists():raise ValueError('This folder does not contain a recognized Books Arranger catalog')
        with VerifiedFile(database) as held:
            if held.facts()['links']!=1:raise ValueError('Catalog must be an ordinary unique file')
            single_stream(database)
            # Immutable read-only inspection creates neither WAL nor journal files. Futaba's 0.22.1 QA, M-3: immutable also
            # ignores the WAL, and after a hard kill the catalog's last commits live only there (a checkpoint cut short
            # leaves the main file half new, half old), so a healthy catalog read as malformed and was refused. With a
            # WAL beside it, a plain read-only open reads it: never a write to the catalog or the WAL (at most the
            # shared-memory index is rebuilt), and the engine's own open recovers the same state.
            wal=Path(str(database)+'-wal').exists()
            with closing(sqlite3.connect(database.as_uri()+('?mode=ro' if wal else '?mode=ro&immutable=1'),uri=True)) as db:
                tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not {'jobs','queue','files'}.issubset(tables):raise ValueError('This catalog is not a recognized Books Arranger catalog')
                columns={row[1] for row in db.execute('PRAGMA table_info(files)')}
                if not {'root','path','size','modified','kind'}.issubset(columns):raise ValueError('Unsupported catalog schema; folder retained')
                if db.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Catalog integrity check failed; folder retained')
        return {'mode':'existing','folder':str(folder)}

def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument('--folder',required=True);parser.add_argument('--mode',choices=['existing','new'],required=True)
    parser.add_argument('--roots-json');parser.add_argument('--install-root',action='append',default=[])
    args=parser.parse_args(argv)
    if args.roots_json:roots=json.loads(Path(args.roots_json).read_text(encoding='utf-8'))
    else:
        from web_server import DEFAULT_ROOTS
        roots=DEFAULT_ROOTS
    try:result=inspect_folder(args.folder,args.mode,roots,args.install_root)
    except Exception as error:print(json.dumps({'ok':False,'error':str(error)}));return 1
    print(json.dumps({'ok':True,**result}));return 0
if __name__=='__main__':raise SystemExit(main())
