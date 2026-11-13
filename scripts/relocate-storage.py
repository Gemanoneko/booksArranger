"""Explicit offline Books Arranger storage transaction. Default inspect is read-only."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from storage_relocation_operator import (prepare_source, seal_target, activate_target,
                                         verify_target, enable_target, rollback_unwritten,
                                         recover_unactivated_source)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('inspect', 'prepare'):
        command = commands.add_parser(name)
        command.add_argument('--source-root', required=True)
        command.add_argument('--target-root', required=True)
        command.add_argument('--scope', action='append', required=True)
        command.add_argument('--catalog-relative', required=True)
        command.add_argument('--workspace', required=True)
        if name == 'prepare':
            command.add_argument('--apply', action='store_true', required=True)
            command.add_argument('--plan-sha256', required=True)
            command.add_argument('--catalog-id', required=True)
            command.add_argument('--generation', required=True)
    seal = commands.add_parser('seal')
    for name in ('source-plan', 'source-plan-sha256', 'source-fence', 'source-fence-sha256',
                 'source-original', 'manifest'):
        seal.add_argument('--' + name, required=True)
    seal.add_argument('--apply', action='store_true', required=True)
    for name in ('activate', 'rollback-unwritten'):
        command = commands.add_parser(name)
        command.add_argument('--manifest', required=True)
        command.add_argument('--manifest-sha256', required=True)
        command.add_argument('--apply', action='store_true', required=True)
    recovery = commands.add_parser('recover-source')
    recovery.add_argument('--source-plan', required=True)
    recovery.add_argument('--source-plan-sha256', required=True)
    recovery.add_argument('--apply', action='store_true', required=True)
    verification = commands.add_parser('verify')
    verification.add_argument('--manifest', required=True)
    verification.add_argument('--manifest-sha256', required=True)
    verification.add_argument('--verification-out')
    verification.add_argument('--apply', action='store_true', required=True)
    enable = commands.add_parser('enable')
    enable.add_argument('--manifest', required=True)
    enable.add_argument('--manifest-sha256', required=True)
    enable.add_argument('--verification-path', required=True)
    enable.add_argument('--verification-sha256', required=True)
    enable.add_argument('--apply', action='store_true', required=True)
    args = parser.parse_args(argv)
    if args.command in ('inspect', 'prepare'):
        selected = {} if args.command == 'inspect' else {'expected_plan_sha256': args.plan_sha256,
                    'catalog_id': args.catalog_id, 'generation': args.generation}
        result = prepare_source(args.source_root, args.target_root, args.scope, args.catalog_relative,
                                args.workspace, apply=args.command == 'prepare', **selected)
    elif args.command == 'seal':
        result = seal_target(args.source_plan, args.source_plan_sha256, args.source_fence,
                             args.source_fence_sha256, args.source_original, args.manifest)
    elif args.command == 'activate':result = activate_target(args.manifest, args.manifest_sha256)
    elif args.command == 'rollback-unwritten':result = rollback_unwritten(args.manifest, args.manifest_sha256)
    elif args.command == 'recover-source':result = recover_unactivated_source(args.source_plan, args.source_plan_sha256)
    elif args.command == 'verify':result = verify_target(args.manifest, args.manifest_sha256, args.verification_out)
    else:result = enable_target(args.manifest, args.manifest_sha256, args.verification_path, args.verification_sha256)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    try:raise SystemExit(main())
    except (ValueError, OSError, RuntimeError) as error:
        print(json.dumps({'ok': False, 'error': str(error),
                          'disposition': 'no migration authority granted; preserve phase receipts and originals'}),
                         file=sys.stderr)
        raise SystemExit(2)
