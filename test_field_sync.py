"""Run with python3 -m unittest -v test_field_sync.py (no GUI required)."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import aos_field_sync as fs


class FieldSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_root = fs.CACHE_ROOT
        fs.CACHE_ROOT = Path(self.tmp.name)
        self.payload = {'schema': 1, 'events': [{'id': 1, 'name': 'Game', 'date': '2026-11-22', 'venue': 'Field'}],
                        'rosters': [{'event_id': 1, 'member': 'Test', 'callsign': 'Alpha', 'team': 'Task Force', 'status': 'confirmed'}]}

    def tearDown(self):
        fs.CACHE_ROOT = self.old_root
        self.tmp.cleanup()

    def test_cache_roundtrip_and_private_permissions(self):
        path = fs.save_cache('192.0.2.1', 8743, 'a'*64, self.payload)
        self.assertEqual(fs.load_cache('192.0.2.1', 8743, 'a'*64)['snapshot'], self.payload)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(fs.CACHE_ROOT.stat().st_mode & 0o777, 0o700)
        with self.assertRaises(FileNotFoundError):
            fs.load_cache('192.0.2.1', 8743, 'b'*64)

    def test_validation(self):
        for invalid in ({}, {'schema': 1, 'events': [], 'rosters': 'bad'},
                        {'schema': 1, 'events': [4], 'rosters': []}):
            with self.assertRaises(ValueError): fs.validate_snapshot(invalid)

    def test_csv_export(self):
        path = Path(self.tmp.name) / 'roster.csv'
        fs.export_csv(self.payload, 'rosters', path)
        self.assertIn('Task Force', path.read_text(encoding='utf-8-sig'))


if __name__ == '__main__':
    unittest.main()
