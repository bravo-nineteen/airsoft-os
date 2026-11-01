import tempfile
import unittest
from pathlib import Path
from aos_doctor import examine, report_text
from aos_apply_update import validate_zip

class DoctorTests(unittest.TestCase):
    def test_report_handles_unconfigured_machine(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            result=examine(root=root,home=root)
            self.assertTrue(any(x['check']=='GitHub config' and not x['ok'] for x in result))
            self.assertIn('SYSTEM DIAGNOSTICS',report_text(result))
    def test_report_with_local_version(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'main.py').write_text('# app');(root/'VERSION').write_text('3.7.0')
            report=examine(root=root,home=root)
            self.assertTrue(report[0]['ok'])

if __name__=='__main__':unittest.main()
