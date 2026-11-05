"""Unified commands for the supported public reference cases."""
from pathlib import Path
import argparse
import json
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import workflow_entry as entry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    doctor = commands.add_parser('doctor')
    doctor.add_argument('--request', type=Path)
    choose = commands.add_parser('choose')
    choose.add_argument('--goal', required=True, choices=sorted(entry.GOALS))
    for name in ('run', 'resume'):
        command = commands.add_parser(name)
        command.add_argument('--request', required=True, type=Path)
        command.add_argument('--run-root', required=True, type=Path)
        if name == 'run':
            command.add_argument('--pause-after-preflight', action='store_true')
    status = commands.add_parser('status')
    status.add_argument('--run-root', required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'doctor':
            result = entry.doctor(entry.request(args.request) if args.request else None)
        elif args.command == 'choose':
            result = entry.choose(args.goal)
        elif args.command == 'status':
            result = entry.status(args.run_root)
        elif args.command == 'run':
            result = entry.run(args.request, args.run_root, args.pause_after_preflight)
        else:
            result = entry.resume(args.request, args.run_root)
    except (OSError, ValueError, KeyError, TypeError) as error:
        # Keep paths/source content out of the diagnostic envelope.
        print(json.dumps({'status': 'REJECTED', 'category': type(error).__name__}))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get('status') not in {'FAILED', 'UNKNOWN', 'NOT_READY'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
