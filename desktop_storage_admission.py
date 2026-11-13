"""Fail before a desktop first frame when a copied catalog is not enabled."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))


def main(argv=None):
    from storage_relocation_native import (configure_work_temp,configure_from_environment,
        logical_catalog_location,require_normal_operation,VerificationRequired,close)
    parser=argparse.ArgumentParser()
    parser.add_argument('--database',required=True)
    args=parser.parse_args(argv)
    try:
        configure_work_temp();configure_from_environment()
        database=logical_catalog_location(args.database)
        from catalog_owner import catalog_lock
        with catalog_lock(database,{}):require_normal_operation(database)
        print(json.dumps({'ok':True}));return 0
    except Exception as error:
        print(json.dumps({'ok':False,'error':str(error),
            'code':'verification_required' if isinstance(error,VerificationRequired) else 'storage_admission_refused'}))
        return 1
    finally:close()


if __name__=='__main__':raise SystemExit(main())
