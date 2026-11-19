from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from repo_publication_guard.envcheck import check_env
from repo_publication_guard.cli import main


class EnvCheckerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.template = self.root / '.env.example'
        self.target = self.root / '.env'

    def test_matching_key_names_are_clean(self):
        self.template.write_text('# Documentation\nA=YOUR_VALUE\nexport B=placeholder\n')
        self.target.write_text('A=something\nB=somethingelse\n')
        self.assertEqual(check_env(self.template, self.target).findings, [])

    def test_missing_and_extra_key_names(self):
        self.template.write_text('A=PLACEHOLDER\nB=PLACEHOLDER\n')
        self.target.write_text('A=secretvalue\nC=morevalue\n')
        report = check_env(self.template, self.target)
        self.assertEqual({f.code for f in report.findings}, {'MISSING_KEY', 'EXTRA_KEY'})
        self.assertNotIn('secretvalue', str(report.to_dict()))

    def test_duplicates_and_malformed_lines(self):
        self.template.write_text('A=placeholder\nA=placeholder\nnot-an-assignment\n')
        self.target.write_text('A=hi\n')
        self.assertEqual({f.code for f in check_env(self.template, self.target).findings},
                         {'DUPLICATE_KEY', 'MALFORMED_LINE'})

    def test_missing_target_raises_clean_error(self):
        self.template.write_text('A=placeholder\n')
        with self.assertRaises(ValueError):
            check_env(self.template, self.target)

    def test_cli_missing_key_is_failing(self):
        self.template.write_text('A=placeholder\n')
        self.target.write_text('B=hiddenvalue\n')
        self.assertEqual(main(['env', '--template', str(self.template),
                               '--file', str(self.target)]), 1)


if __name__ == '__main__':
    unittest.main()
