import csv
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from aos_live import connect,read_state,change,GameClock,export_audit,backup_database

class GameReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'game.sqlite3'
        with connect(self.path): pass
    def tearDown(self): self.temp.cleanup()
    def test_local_clock(self):
        clock=GameClock(self.path)
        with connect(self.path) as db:
            state=read_state(db)
            change(db,'gm','start',state['revision'])
        clock.start()
        try:
            time.sleep(1.4)
            with connect(self.path) as db: self.assertLess(read_state(db)['remaining'],900)
        finally: clock.stop()
    def test_single_clock_owner(self):
        a=GameClock(self.path);b=GameClock(self.path)
        a.start();time.sleep(.2);b.start();time.sleep(.2)
        try: self.assertEqual(int(a.owner)+int(b.owner),1)
        finally: a.stop();b.stop()
    def test_export_and_backup(self):
        with connect(self.path) as db:
            state=read_state(db)
            change(db,'gm','score',state['revision'],team='red',delta=1)
        csvpath=Path(self.temp.name)/'audit.csv'
        self.assertEqual(export_audit(self.path,csvpath),1)
        with csvpath.open(encoding='utf-8-sig') as f:
            self.assertEqual(list(csv.DictReader(f))[0]['action'],'score')
        dest=Path(self.temp.name)/'backup.sqlite3'
        backup_database(self.path,dest)
        with sqlite3.connect(dest) as db:
            self.assertEqual(read_state(db)['red'],1)
    def test_backup_same_path_rejected(self):
        with self.assertRaises(ValueError): backup_database(self.path,self.path)

if __name__=='__main__':unittest.main()
