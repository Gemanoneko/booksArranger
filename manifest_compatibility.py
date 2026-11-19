"""One legacy manifest default, and data-folder locations bridged across recorded storage moves; no routing authority."""


def normalized_output_root(value):
    """Copy a manifest, supplying only its absent legacy output-root default.

    Explicit values (including invalid ones) remain exactly as supplied so the
    existing manifest validators and equality checks can reject them. Never
    synthesize None for a missing or malformed source root.
    """
    if not isinstance(value,dict):raise ValueError('Manifest must be an object')
    result=dict(value)
    if 'output_root' not in result:
        root=value.get('root')
        if not isinstance(root,str) or not root.strip():raise ValueError('Legacy output root requires its actual frozen root')
        result['output_root']=root
    return result


def same_value(left,right):
    """Equal, except that two strings naming the same place in the application data folder are equal across the storage
    moves the selected relocation records (storage_relocation_native.data_location_match; 0.30.0 sort-1).

    A job queued before the 14 Nov move records its reviewed cover under the old data folder; the rebuilt manifest names
    the same cover in the current one. Every other value, the library paths included, must be equal as before.
    """
    if isinstance(left,dict) and isinstance(right,dict):
        return left.keys()==right.keys() and all(same_value(left[key],right[key]) for key in left)
    if isinstance(left,list) and isinstance(right,list):
        return len(left)==len(right) and all(same_value(a,b) for a,b in zip(left,right))
    if isinstance(left,str) and isinstance(right,str) and left!=right:
        from storage_relocation_native import data_location_match
        return data_location_match(left,right)
    return left==right


def equivalent_manifest(left,right,ignore_fields=('job_id',)):
    """Compare every field except explicit exclusions and one absent default.

    Already equal minimal historical/test manifests need no synthesized field.
    A data-folder location recorded before a storage move compares through
    that move's records only (same_value). This comparison does not validate a
    manifest or authorize a new destination.
    """
    if not isinstance(left,dict) or not isinstance(right,dict):return False
    def retained(value):return {key:item for key,item in value.items() if key not in ignore_fields}
    if retained(left)==retained(right):return True
    try:left,right=retained(normalized_output_root(left)),retained(normalized_output_root(right))
    except ValueError:return False
    return left==right or same_value(left,right)
