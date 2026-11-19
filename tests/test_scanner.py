import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from repo_publication_guard.cli import main
from repo_publication_guard.scanner import scan_repository


class RepositoryScannerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return path

    def initialize_git(self):
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)

    def test_clean_example_is_not_sensitive(self):
        self.write('.env.example', 'SERVICE_API_KEY=YOUR_API_KEY_HERE\n')
        report = scan_repository(self.root, 'all')
        self.assertEqual(report.findings, [])
        self.assertEqual(report.files_checked, 1)

    def test_real_env_path_is_flagged_without_printing_values(self):
        private = 'a' * 18
        self.write('.env', 'DATABASE_PASSWORD=' + private + '\n')
        report = scan_repository(self.root, 'all')
        self.assertIn('SENSITIVE_PATH', {f.code for f in report.findings})
        self.assertNotIn(private, json.dumps(report.to_dict()))

    def test_fake_aws_pattern_detected_without_leak(self):
        token = 'AKIA' + 'A' * 16
        self.write('config.txt', 'key=' + token + '\n')
        report = scan_repository(self.root, 'all')
        self.assertIn('AWS_ACCESS_KEY', {f.code for f in report.findings})
        self.assertNotIn(token, json.dumps(report.to_dict()))

    def test_fake_github_pattern_detected(self):
        self.write('config.txt', 'key=ghp_' + 'A' * 31 + '\n')
        report = scan_repository(self.root, 'all')
        self.assertIn('GITHUB_TOKEN', {f.code for f in report.findings})

    def test_fake_openai_pattern_detected(self):
        self.write('config.txt', 'key=sk-' + 'A' * 24 + '\n')
        report = scan_repository(self.root, 'all')
        self.assertIn('OPENAI_KEY', {f.code for f in report.findings})

    def test_private_key_header_detected(self):
        self.write('key.txt', '-----BEGIN ' + 'PRIVATE KEY-----' + '\n')
        report = scan_repository(self.root, 'all')
        self.assertIn('PRIVATE_KEY', {f.code for f in report.findings})

    def test_dependency_folders_are_skipped(self):
        self.write('node_modules/creds.txt', 'key=ghp_' + 'A' * 35 + '\n')
        self.assertEqual(scan_repository(self.root, 'all').findings, [])

    def test_binary_files_are_skipped(self):
        (self.root / 'data.bin').write_bytes(b'\x00' + b'hello')
        report = scan_repository(self.root, 'all')
        self.assertEqual(report.files_skipped, 1)
        self.assertEqual(report.files_checked, 0)

    def test_oversize_file_is_skipped(self):
        self.write('big.txt', 'A' * 128)
        report = scan_repository(self.root, 'all', max_bytes=64)
        self.assertEqual(report.files_skipped, 1)

    def test_tracked_mode_ignores_untracked(self):
        self.initialize_git()
        self.write('tracked.txt', 'safe text')
        self.write('untracked.env', 'safe text')
        subprocess.run(['git', '-C', str(self.root), 'add', 'tracked.txt'], check=True)
        report = scan_repository(self.root, 'tracked')
        self.assertEqual(report.files_checked, 1)

    def test_staged_mode_selects_staged_file(self):
        self.initialize_git()
        self.write('staged.txt', 'safe')
        self.write('notstaged.txt', 'also safe')
        subprocess.run(['git', '-C', str(self.root), 'add', 'staged.txt'], check=True)
        report = scan_repository(self.root, 'staged')
        self.assertEqual(report.files_checked, 1)

    def test_symlinked_file_is_not_followed(self):
        outside = Path(self.tmp.name).parent / 'repo-guard-outside-not-created.txt'
        try:
            (self.root / 'linked').symlink_to(outside)
        except OSError as exc:
            # Windows normally requires Developer Mode or the SeCreateSymbolicLinkPrivilege.
            # A missing OS privilege is not a scanner regression; other errors must fail.
            if sys.platform == 'win32' and getattr(exc, 'winerror', None) == 1314:
                self.skipTest('Windows symlink creation privilege is unavailable (WinError 1314)')
            raise
        report = scan_repository(self.root, 'all')
        self.assertEqual(report.files_checked, 0)

    def test_invalid_non_repo_mode_fails(self):
        with self.assertRaises(ValueError):
            scan_repository(self.root, 'tracked')

    def test_cli_no_findings_passes(self):
        self.write('safe.txt', 'Hello world\n')
        self.assertEqual(main(['scan', str(self.root), '--mode', 'all']), 0)

    def test_cli_high_finding_fails(self):
        self.write('.env', 'HELLO=world\n')
        self.assertEqual(main(['scan', str(self.root), '--mode', 'all']), 1)

    def test_cli_errors_distinct_from_findings(self):
        self.assertEqual(main(['scan', str(self.root / 'missing'), '--mode', 'all']), 2)

    def test_medium_threshold_is_configurable(self):
        self.write('config.py', 'password=' + 'lengthysecretliteral' + '\n')
        self.assertEqual(main(['scan', str(self.root), '--mode', 'all', '--fail-on', 'high']), 0)
        self.assertEqual(main(['scan', str(self.root), '--mode', 'all', '--fail-on', 'medium']), 1)


if __name__ == '__main__':
    unittest.main()
