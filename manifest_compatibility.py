"""One legacy manifest default; no path canonicalization or routing authority."""


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


def equivalent_manifest(left,right,ignore_fields=('job_id',)):
    """Compare every field except explicit exclusions and one absent default.

    Already equal minimal historical/test manifests need no synthesized field.
    This comparison does not validate a manifest or authorize a new destination.
    """
    if not isinstance(left,dict) or not isinstance(right,dict):return False
    def retained(value):return {key:item for key,item in value.items() if key not in ignore_fields}
    if retained(left)==retained(right):return True
    try:return retained(normalized_output_root(left))==retained(normalized_output_root(right))
    except ValueError:return False
