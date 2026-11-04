import io,pathlib,subprocess,tarfile
root=pathlib.Path(__file__).resolve().parent
source=pathlib.Path('C:/Antigravity Projects/Worktrees/Books Arranger/converted-duplicate-20261104')
target=root/'baseline-d9c0da2'
target.mkdir(exist_ok=False)
data=subprocess.run(['git','-C',str(source),'archive','--format=tar','d9c0da2c0cb47abae4c75e8d722e06268d6ee600','--','*.py','*.json'],stdout=subprocess.PIPE,check=True,timeout=60).stdout
with tarfile.open(fileobj=io.BytesIO(data)) as archive:
    for member in archive.getmembers():
        destination=target/member.name
        if not destination.resolve().is_relative_to(target.resolve()) or member.issym() or member.islnk():raise RuntimeError('Unsafe archive entry')
        if member.isdir():destination.mkdir(parents=True,exist_ok=True)
        elif member.isfile():
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(archive.extractfile(member).read())
(target/'scratch').mkdir(exist_ok=True)
(target/'tests'/'test_automatic_media.py').write_bytes((source/'tests'/'test_automatic_media.py').read_bytes())
driver=(root/'focused.py').read_text().replace(str(source).replace('\\','/'),str(target).replace('\\','/'))
(root/'baseline.py').write_text(driver,encoding='utf-8')
launcher=(root/'owned.mjs').read_text().replace(str(source).replace('\\','/'),str(target).replace('\\','/')).replace("root+'/focused.py'","root+'/baseline.py'")
(root/'baseline-owned.mjs').write_text(launcher,encoding='utf-8')
print('Prepared exact d9c0da2 baseline product with new regression only')
