"""Installation-owned relative paths, independent of a machine's drive letter."""
import ntpath
from storage_relocation import _relative,_inside,_root,_need

SCHEMA='books-arranger-installation-v2'
PATHS=('application_dir','data_dir','profile_dir','temp_dir','downloads_dir','logs_dir','maintenance_temp_dir','ownership_manifest')
PINS=('storage_relocation','package_ownership','retained_package','retained_profile','ownership_provenance','control_provenance')

def decode(value,anchor):
    if value.get('schema')!=SCHEMA:return dict(value)
    root=_root(str(anchor));result=dict(value)
    for field in PATHS:
        if field in value:result[field]=ntpath.join(root,_relative(value[field]))
    for field in PINS:
        if field in value:result[field]=dict(value[field],manifest=ntpath.join(root,_relative(value[field]['manifest'])))
    return result

def encode(value,anchor):
    root=_root(str(anchor));result=dict(value,schema=SCHEMA)
    def relative(path):
        path=_root(str(path));_need(_inside(path,root) and path!=root,'Managed storage must stay inside the application storage anchor')
        return _relative(ntpath.relpath(path,root))
    for field in PATHS:
        if field in value:result[field]=relative(value[field])
    for field in PINS:
        if field in value:result[field]=dict(value[field],manifest=relative(value[field]['manifest']))
    return result
