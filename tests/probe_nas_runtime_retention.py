"""Explicit owned-fixture NAS retention/publication assessment, never discovery."""
import hashlib,json,sys,uuid
from pathlib import Path
import sqlite3

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from catalog_owner import catalog_lock
from runtime_disposition_owners import admit_catalog
from native_io import VerifiedFile,DirectoryBoundary,publish_no_replace,BoundaryError


def main():
    if len(sys.argv)!=3:raise ValueError('Expected explicit owned engineering parent and evidence parent')
    parent=Path(sys.argv[1]).absolute();evidence=Path(sys.argv[2]).absolute()
    if str(parent).casefold()!=str(Path('Z:/Books Arranger/Engineering')).casefold():
        raise ValueError('This assessment is limited to the approved NAS engineering fixture parent')
    tag='retention-publication-'+uuid.uuid4().hex;root=parent/tag;root.mkdir()
    local=evidence/tag;local.mkdir();database=local/'inventory.sqlite3'
    with sqlite3.connect(database) as db:db.execute('CREATE TABLE fixture(value)')
    source=root/'original.bin';source.write_bytes(b'private original retained')
    ads=Path(str(source)+':retained');ads.write_bytes(b'private named stream retained')
    before=(source.read_bytes(),ads.read_bytes())
    with VerifiedFile(source) as held:facts=held.facts()
    refusal=''
    with catalog_lock(database,{'NAS fixture':root}):
        admit_catalog(database)
        try:
            with VerifiedFile(source,delete=True) as held:held.dispose()
        except BoundaryError as error:refusal=str(error)
    assert refusal and (source.read_bytes(),ads.read_bytes())==before
    with VerifiedFile(source) as held:assert held.facts()==facts
    temporary=root/'new-output.part';payload=b'private newly converted output';temporary.write_bytes(payload)
    target=root/'new-output.m4b';sha=hashlib.sha256(payload).hexdigest()
    with DirectoryBoundary(root.anchor,root,rename_destination=True) as boundary:
        publish_no_replace(temporary,target,boundary,expected_sha256=sha,expected_size=len(payload))
    assert not temporary.exists() and target.read_bytes()==payload
    collision=root/'collision.part';collision.write_bytes(b'new collision must remain')
    try:
        with DirectoryBoundary(root.anchor,root,rename_destination=True) as boundary:
            publish_no_replace(collision,target,boundary)
    except FileExistsError:pass
    else:raise AssertionError('Existing destination was not preserved')
    assert target.read_bytes()==payload and collision.read_bytes()==b'new collision must remain'
    report=dict(schema='books-nas-retention-assessment-v1',root=str(root),local=str(local),
                original_retained=True,named_stream_retained=True,original_native_facts_unchanged=True,
                refusal=refusal,new_no_replace_publication=True,existing_destination_preserved=True,
                application_data_journal_before_refusal=list((local/'file-disposition-ledger').glob('*.intent.json'))==[])
    (local/'evidence.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report))


if __name__=='__main__':main()
