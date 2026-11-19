"""Compare dotenv key names without ever exposing configuration values."""
from __future__ import annotations

from pathlib import Path
import re

from .scanner import Finding, Report

_KEY_LINE = re.compile(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=')


def _read_keys(path: Path) -> tuple[set[str], list[Finding]]:
    keys: set[str] = set()
    findings: list[Finding] = []
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        match = _KEY_LINE.match(line)
        if not match:
            findings.append(Finding(path.name, number, 'MALFORMED_LINE', 'medium',
                                    'Unrecognized dotenv syntax (value intentionally hidden)'))
            continue
        name = match.group(1)
        if name in keys:
            findings.append(Finding(path.name, number, 'DUPLICATE_KEY', 'medium',
                                    f'Duplicate environment variable name: {name}'))
        keys.add(name)
    return keys, findings


def check_env(template: Path, target: Path) -> Report:
    """Compare required variable names; never print or save secret values."""
    template, target = template.expanduser().resolve(), target.expanduser().resolve()
    if not template.is_file():
        raise ValueError(f'Template does not exist: {template}')
    if not target.is_file():
        raise ValueError(f'Target does not exist: {target}')
    source_keys, first = _read_keys(template)
    target_keys, second = _read_keys(target)
    findings = first + second
    for key in sorted(source_keys - target_keys):
        findings.append(Finding(target.name, 0, 'MISSING_KEY', 'high',
                                f'Key required by template is missing: {key}'))
    for key in sorted(target_keys - source_keys):
        findings.append(Finding(target.name, 0, 'EXTRA_KEY', 'low',
                                f'Key not present in template: {key}'))
    return Report('env', 2, 0, sorted(set(findings)))
