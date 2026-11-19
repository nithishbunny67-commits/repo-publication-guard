"""repo-guard command-line interface."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .envcheck import check_env
from .scanner import Report, SEVERITY_ORDER, scan_repository


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='repo-guard',
        description='Local-first publication safety checks (zero runtime dependencies).'
    )
    sub = parser.add_subparsers(dest='command', required=True)
    scan = sub.add_parser('scan', help='Detect common credential leaks and sensitive file paths')
    scan.add_argument('path', nargs='?', default='.', help='Repository or directory to inspect')
    scan.add_argument('--mode', choices=('tracked', 'staged', 'all'), default='tracked',
                      help='tracked Git files, staged files, or all files (default: tracked)')
    env = sub.add_parser('env', help='Compare .env template key names to a local .env file')
    env.add_argument('--template', default='.env.example')
    env.add_argument('--file', default='.env')
    for command in (scan, env):
        command.add_argument('--format', choices=('text', 'json'), default='text')
        command.add_argument('--fail-on', choices=('low', 'medium', 'high'), default='high',
                             help='Minimum finding severity that fails the command')
    return parser


def _print(report: Report, output_format: str) -> None:
    if output_format == 'json':
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return
    print(f'{report.mode}: {report.files_checked} file(s) checked, '
          f'{report.files_skipped} skipped, {len(report.findings)} finding(s)')
    for item in report.findings:
        location = f'{item.path}:{item.line}' if item.line else item.path
        print(f'[{item.severity}] {location}: {item.code} — {item.message}')
    if not report.findings:
        print('No findings from the configured checks (not a security guarantee).')


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == 'scan':
            report = scan_repository(Path(args.path), mode=args.mode)
        else:
            report = check_env(Path(args.template), Path(args.file))
    except (ValueError, OSError, UnicodeError) as exc:
        print(f'repo-guard: {exc}', file=sys.stderr)
        return 2
    _print(report, args.format)
    return int(any(SEVERITY_ORDER[f.severity] >= SEVERITY_ORDER[args.fail_on]
                   for f in report.findings))


if __name__ == '__main__':
    raise SystemExit(main())
