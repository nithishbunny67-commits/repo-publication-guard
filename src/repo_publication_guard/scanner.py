"""Privacy-preserving, dependency-free checks for repositories before publication."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
import re
import subprocess

MAX_BYTES = 2_000_000
SKIP_DIRS = {'.git', '.hg', '.svn', '.venv', 'venv', 'node_modules',
             '__pycache__', '.pytest_cache', '.mypy_cache', '.tox', 'dist', 'build'}

# Targeted signatures only. This is a best-effort preflight, NOT a credential verifier.
SECRET_PATTERNS = (
    ('AWS_ACCESS_KEY', re.compile(r'\b(?:AKIA|ASIA)[0-9A-Z]{16}\b'), 'high'),
    ('GITHUB_TOKEN', re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}\b'), 'high'),
    ('OPENAI_KEY', re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'), 'high'),
    ('GOOGLE_API_KEY', re.compile(r'\bAIza[0-9A-Za-z_-]{35}\b'), 'high'),
    ('SLACK_TOKEN', re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{10,}\b'), 'high'),
    ('PRIVATE_KEY', re.compile(r'-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----'), 'high'),
)
ASSIGNMENT_PATTERN = re.compile(
    r'''(?ix)\b(?:api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|'''
    r'''password|client[_-]?secret)\b\s*[:=]\s*['"]?(?P<value>[A-Za-z0-9_./+=-]{10,})'''
)
PLACEHOLDERS = ('example', 'placeholder', 'replace', 'changeme', 'change_me',
                'your_', 'dummy', 'redacted', 'sample', 'fake', 'not_real', 'not-real')
SEVERITY_ORDER = {'low': 0, 'medium': 1, 'high': 2}


@dataclass(frozen=True, order=True)
class Finding:
    path: str
    line: int
    code: str
    severity: str
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Report:
    mode: str
    files_checked: int
    files_skipped: int
    findings: list[Finding]

    def to_dict(self) -> dict:
        return {
            'schema_version': 1,
            'mode': self.mode,
            'files_checked': self.files_checked,
            'files_skipped': self.files_skipped,
            'finding_count': len(self.findings),
            'findings': [f.to_dict() for f in sorted(self.findings)],
        }


def _git_paths(root: Path, mode: str) -> list[str]:
    command = (['git', '-C', str(root), 'ls-files', '--cached', '-z']
               if mode == 'tracked' else
               ['git', '-C', str(root), 'diff', '--cached', '--name-only',
                '--diff-filter=ACMR', '-z'])
    try:
        proc = subprocess.run(command, capture_output=True, check=True)
    except FileNotFoundError as exc:
        raise ValueError('Git is required for tracked/staged mode') from exc
    except subprocess.CalledProcessError as exc:
        raise ValueError('Not a Git repository; use --mode all') from exc
    return [p.decode('utf-8', errors='surrogateescape')
            for p in proc.stdout.split(b'\0') if p]


def _all_paths(root: Path) -> list[str]:
    names = []
    for p in root.rglob('*'):
        if any(segment in SKIP_DIRS for segment in p.relative_to(root).parts):
            continue
        if p.is_file() and not p.is_symlink():
            names.append(p.relative_to(root).as_posix())
    return names


def _sensitive_path(rel: str) -> bool:
    path = PurePosixPath(rel.lower())
    name = path.name
    if name.startswith('.env'):
        return not (name in {'.env.example', '.env.sample', '.env.template', '.env.dist'}
                    or name.endswith(('.example', '.sample', '.template', '.dist')))
    if name in {'id_rsa', 'id_dsa', 'id_ed25519', 'credentials.json',
                '.pypirc', '.npmrc', 'terraform.tfstate'}:
        return True
    if name.endswith(('.tfstate', '.p12', '.pfx')):
        return True
    if tuple(path.parts[-2:]) == ('.aws', 'credentials'):
        return True
    return False


def _placeholder(text: str) -> bool:
    lower = text.lower()
    return any(word in lower for word in PLACEHOLDERS) or set(lower) == {'x'}


def scan_repository(root: Path, mode: str = 'tracked', max_bytes: int = MAX_BYTES) -> Report:
    """Scan selected files, reporting paths, rule identifiers, and line numbers only.

    Never return actual detected secret values or surrounding source text.
    """
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f'Not a directory: {root}')
    if mode not in {'tracked', 'staged', 'all'}:
        raise ValueError(f'Unknown mode: {mode}')
    selected = _all_paths(root) if mode == 'all' else _git_paths(root, mode)
    findings: list[Finding] = []
    checked = skipped = 0
    for rel in sorted(set(selected)):
        candidate = root / rel
        # Reject symlinked files and paths outside the requested root.
        if candidate.is_symlink() or not candidate.is_file() or not candidate.resolve().is_relative_to(root):
            skipped += 1
            continue
        display_path = candidate.relative_to(root).as_posix()
        if _sensitive_path(display_path):
            findings.append(Finding(display_path, 0, 'SENSITIVE_PATH', 'high',
                                    'A potentially sensitive file is selected for publication'))
        try:
            if candidate.stat().st_size > max_bytes:
                skipped += 1
                continue
            data = candidate.read_bytes()
        except OSError:
            skipped += 1
            continue
        if b'\0' in data:
            skipped += 1
            continue
        checked += 1
        for number, line in enumerate(data.decode('utf-8', errors='replace').splitlines(), 1):
            for code, expression, severity in SECRET_PATTERNS:
                if expression.search(line):
                    findings.append(Finding(display_path, number, code, severity,
                                            'Possible credential; inspect locally and rotate if real'))
            match = ASSIGNMENT_PATTERN.search(line)
            if match and not _placeholder(match.group('value')):
                findings.append(Finding(display_path, number, 'SECRET_ASSIGNMENT', 'medium',
                                        'A credential-like assignment may contain a literal secret'))
    return Report(mode, checked, skipped, sorted(set(findings)))
