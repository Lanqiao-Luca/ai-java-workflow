"""Use real temporary files to check allowlist, byte identity and stop behavior."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import os
import runpy
import tempfile
import unittest
from tools.local_evidence import collect, LocalEvidenceError


@unittest.skipUnless(os.name == 'posix', 'POSIX source adapter')
class LocalEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for n, v in (('one.txt', 'CONTROL\nALPHA\n'), ('two.txt', 'BETA\n')):
            (self.root / n).write_text(v)
        self.spec = {'source_id': 'fictional', 'needle': 'ALPHA', 'mode': 'complete',
                     'probe_id': 'one.txt:1', 'max_pages': 2, 'max_bytes': 100, 'max_total_bytes': 200,
                     'files': [{'path': n, 'sha256': hashlib.sha256((self.root / n).read_bytes()).hexdigest()}
                               for n in ('one.txt', 'two.txt')]}

    def collect(self):
        return collect(self.root, self.spec)

    def test_reads_exact_files_with_raw_identity(self):
        (self.root / 'unlisted.txt').write_text('ALPHA private-like-unlisted')
        result = self.collect()
        self.assertEqual(result['coverage']['match_ids'], ['one.txt:2'])
        self.assertEqual({o['path'] for o in result['originals']}, {'one.txt', 'two.txt'})
        self.assertTrue(result['coverage']['coverage_complete'])

    def test_sample_stops_before_second_file(self):
        self.spec['mode'] = 'sample'
        (self.root / 'two.txt').unlink()
        result = self.collect()
        self.assertEqual(result['coverage']['status'], 'SAMPLE_FOUND')
        self.assertEqual(len(result['originals']), 1)

    def test_changed_bytes_cannot_become_valid_zero(self):
        (self.root / 'two.txt').write_text('modified')
        result = self.collect()
        self.assertEqual(result['coverage']['status'], 'STALE')
        self.assertEqual(result['coverage']['absence'], 'unknown')

    def test_missing_file_preserves_unknown(self):
        (self.root / 'two.txt').unlink()
        self.assertEqual(self.collect()['coverage']['status'], 'UNKNOWN')

    def test_denied_read_is_not_zero(self):
        with patch('tools.local_evidence._open_relative', side_effect=PermissionError):
            self.assertEqual(self.collect()['coverage']['status'], 'DENIED')

    def test_path_traversal_absolute_hidden_and_glob_rejected_before_open(self):
        for name in ('../outside', '/etc/passwd', '.hidden', 'dir/../one', 'dir//one', './one'):
            with self.subTest(name=name):
                self.spec['files'][0]['path'] = name
                with self.assertRaises(LocalEvidenceError):
                    self.collect()

    def test_file_and_directory_symlinks_rejected(self):
        (self.root / 'link').symlink_to(self.root / 'one.txt')
        (self.root / 'dir').symlink_to(self.root, target_is_directory=True)
        for name in ('link', 'dir/one.txt'):
            self.spec['files'][0]['path'] = name
            self.assertEqual(self.collect()['coverage']['status'], 'REJECTED')

    def test_fifo_and_directory_do_not_hang_or_count_as_text(self):
        os.mkfifo(self.root / 'fifo')
        for name in ('fifo', 'folder'):
            if name == 'folder':
                (self.root / name).mkdir()
            self.spec['files'][0]['path'] = name
            self.assertEqual(self.collect()['coverage']['status'], 'REJECTED')

    def test_byte_and_page_limits_preserve_partial(self):
        self.spec['max_bytes'] = 2
        self.assertEqual(self.collect()['coverage']['status'], 'PARTIAL')
        self.spec['max_bytes'] = 100
        self.spec['max_pages'] = 1
        self.assertEqual(self.collect()['coverage']['status'], 'PARTIAL')

    def test_zero_requires_visible_control(self):
        self.spec['needle'] = 'MISSING'
        self.assertEqual(self.collect()['coverage']['status'], 'COMPLETE_EMPTY')
        self.spec['probe_id'] = 'not-a-row'
        self.assertEqual(self.collect()['coverage']['status'], 'UNRESOLVED_EMPTY')

    def test_duplicate_allowlist_and_invalid_budget_rejected(self):
        self.spec['files'][1] = deepcopy(self.spec['files'][0])
        with self.assertRaises(LocalEvidenceError):
            self.collect()
        self.spec['max_pages'] = True
        with self.assertRaises(LocalEvidenceError):
            self.collect()

    def test_invalid_utf8_is_not_accepted_observation(self):
        raw = b'\xff'
        (self.root / 'one.txt').write_bytes(raw)
        self.spec['files'][0]['sha256'] = hashlib.sha256(raw).hexdigest()
        self.assertEqual(self.collect()['coverage']['status'], 'REJECTED')

    def test_real_example_executes_all_four_outcomes(self):
        case = Path(__file__).resolve().parents[1] / 'workflows/examples/local-evidence/run.py'
        result = runpy.run_path(str(case))['run_examples']()
        self.assertEqual(len(result), 4)
        self.assertTrue(all(r['source_requests'] == 0 for r in result.values()))


if __name__ == '__main__':
    unittest.main()
