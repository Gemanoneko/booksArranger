"""Restore only this operation's persisted exact security transition."""
import base64

from storage_relocation_operator import NativeItem,Security,need,security_equivalent
from storage_source_finalization import _acl


def _delete_relaxed(acl):
    result=bytearray(acl);offset=8;count=int.from_bytes(acl[4:6],'little')
    everyone=b'\x01\x01\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00'
    for _ in range(count):
        size=int.from_bytes(acl[offset+2:offset+4],'little')
        need(size>=8 and offset+size<=len(acl),'Persisted fence ACE is malformed')
        entry=acl[offset:offset+size];mask=int.from_bytes(entry[4:8],'little')
        if entry[0]==1 and entry[1]==0 and entry[8:]==everyone:
            result[offset+4:offset+8]=(mask&~0x10000).to_bytes(4,'little')
        offset+=size
    need(offset<=len(acl),'Persisted fence ACL is malformed')
    return bytes(result)


def restore_owned_fence(path,identity,original,expected_acl,*,directory=False):
    try:
        expected=base64.b64decode(expected_acl,validate=True)
        need(8<=len(expected)<=65535 and int.from_bytes(expected[2:4],'little')==len(expected),
            'Persisted intended security transition is missing or malformed')
        security=Security()
        need(expected==security.planned_write_fence_acl(original,directory),
            'Persisted security transition is not this operation\'s write fence')
        with NativeItem(path,directory=directory,writable_security=True) as item:
            need(item.facts['identity']==identity,'Name was replaced; permission restoration held')
            current=security.capture(item)
            if security_equivalent(current,original):return True,None
            _,_,raw,_=_acl(security,current)
            need(current['protected'] and current['sddl'].partition('D:')[0]==original['sddl'].partition('D:')[0] and
                bytes(raw) in (expected,_delete_relaxed(expected)) and
                security.has_write_fence(item,current,include_delete=False),
                'Security changed outside this operation; foreign permissions were retained')
            security.restore(item,original)
        return True,None
    except Exception as error:return False,str(error)
