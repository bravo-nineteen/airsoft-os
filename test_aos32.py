import tempfile
import time
import unittest
from pathlib import Path
from aos_live import GameClock, change, connect, read_state

class FailoverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / 'game.sqlite3'
        with connect(self.db) as conn:
            state = read_state(conn)
            change(conn, 'test', 'start', state['revision'])

    def tearDown(self):
        self.tmp.cleanup()

    def test_waiting_clock_takes_over(self):
        first = GameClock(self.db)
        second = GameClock(self.db)
        first.start()
        time.sleep(.35)
        second.start()
        try:
            self.assertTrue(first.owner)
            self.assertFalse(second.owner)
            first.stop()
            deadline = time.monotonic() + 2
            while not second.owner and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertTrue(second.owner)
            with connect(self.db) as conn:
                before = read_state(conn)['remaining']
            time.sleep(1.2)
            with connect(self.db) as conn:
                after = read_state(conn)['remaining']
            self.assertLess(after, before)
        finally:
            first.stop()
            second.stop()

    def test_stopped_waiter_never_takes_over(self):
        first = GameClock(self.db)
        second = GameClock(self.db)
        first.start()
        time.sleep(.2)
        second.start()
        time.sleep(.2)
        second.stop()
        first.stop()
        self.assertFalse(second.owner)

if __name__ == '__main__':
    unittest.main()
