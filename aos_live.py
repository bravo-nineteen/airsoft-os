"""AOS 3.0 LAN game-state service. Standard-library-only, offline first.

Tokens are provisioned locally. Never exposes shell commands or executable payloads.
"""
import argparse
import csv
import fcntl
import shutil
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import ssl
import threading
import time
from datetime import datetime, timezone
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path.home() / '.local/share/aos'
LIVE_DB = ROOT / 'live.sqlite3'
TOKEN_FILE = ROOT / 'network' / 'live-tokens.json'
ROLES = ('admin', 'gm', 'leader', 'viewer')
MAX_BODY = 8192


def connect(path=LIVE_DB):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS games (id INTEGER PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL, duration INTEGER NOT NULL, remaining INTEGER NOT NULL, red INTEGER NOT NULL, blue INTEGER NOT NULL, revision INTEGER NOT NULL, updated_at TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, time TEXT, actor TEXT, action TEXT, revision INTEGER)')
    if not db.execute('SELECT 1 FROM games WHERE id=1').fetchone():
        db.execute('INSERT INTO games VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)', ('Training Round', 'ready', 900, 900, 0, 0, 0, now()))
    db.commit()
    return db


def now():
    return datetime.now(timezone.utc).isoformat()


def read_state(db):
    row = db.execute('SELECT title,status,duration,remaining,red,blue,revision,updated_at FROM games WHERE id=1').fetchone()
    return dict(zip(('title','status','duration','remaining','red','blue','revision','updated_at'), row))


def change(db, actor, action, expected, **data):
    if action not in ('configure','start','pause','reset','score','tick'):
        raise ValueError('Unsupported action')
    db.execute('BEGIN IMMEDIATE')
    try:
        state = read_state(db)
        if state['revision'] != expected:
            raise RuntimeError('State changed; refresh before editing')
        if action == 'configure':
            title = data.get('title', state['title'])
            duration = data.get('duration', state['duration'])
            if not isinstance(title, str) or not 1 <= len(title) <= 80 or not isinstance(duration, int) or not 30 <= duration <= 14400:
                raise ValueError('Invalid title/duration')
            if state['status'] == 'running': raise ValueError('Pause before configuring')
            state.update(title=title, duration=duration, remaining=duration, status='ready', red=0, blue=0)
        elif action == 'start':
            if state['remaining'] == 0: raise ValueError('Reset finished game')
            state['status'] = 'running'
        elif action == 'pause':
            state['status'] = 'paused'
        elif action == 'reset':
            state.update(status='ready', remaining=state['duration'], red=0, blue=0)
        elif action == 'score':
            team, delta = data.get('team'), data.get('delta')
            if team not in ('red','blue') or type(delta) is not int or delta not in (-1,1): raise ValueError('Invalid score change')
            state[team] = max(0, min(9999, state[team] + delta))
        elif action == 'tick':
            if state['status'] != 'running': raise ValueError('Game not running')
            elapsed = data.get('seconds')
            if type(elapsed) is not int or not 1 <= elapsed <= 14400: raise ValueError('Invalid tick')
            state['remaining'] = max(0, state['remaining'] - elapsed)
            if state['remaining'] == 0: state['status'] = 'finished'
        state['revision'] += 1
        state['updated_at'] = now()
        db.execute('UPDATE games SET title=?,status=?,duration=?,remaining=?,red=?,blue=?,revision=?,updated_at=? WHERE id=1', tuple(state[k] for k in ('title','status','duration','remaining','red','blue','revision','updated_at')))
        db.execute('INSERT INTO audit(time,actor,action,revision) VALUES (?,?,?,?)', (now(), actor, action, state['revision']))
        db.commit()
        return state
    except Exception:
        db.rollback()
        raise


def provision(path=TOKEN_FILE):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    if not path.exists():
        data = {role: secrets.token_urlsafe(32) for role in ROLES}
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f: json.dump(data, f)
    return json.loads(path.read_text())


def role_for(token, tokens):
    if not isinstance(token, str): return None
    for role, expected in tokens.items():
        if hmac.compare_digest(token, expected): return role
    return None


def allowed(role, action):
    if action in ('configure','reset'): return role in ('admin','gm')
    if action in ('start','pause','score'): return role in ('admin','gm')
    return False


def make_handler(db_path, tokens):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, obj):
            data = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.end_headers()
            self.wfile.write(data)

        def _role(self):
            return role_for(self.headers.get('X-AOS-Live-Token', ''), tokens)

        def do_GET(self):
            if urlsplit(self.path).path != '/api/v1/live': return self._send(404, {'error':'not found'})
            if not self._role(): return self._send(403, {'error':'unauthorised'})
            with connect(db_path) as db: state = read_state(db)
            self._send(200, state)

        def do_POST(self):
            if urlsplit(self.path).path != '/api/v1/live': return self._send(404, {'error':'not found'})
            role = self._role()
            if not role: return self._send(403, {'error':'unauthorised'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= MAX_BODY: raise ValueError('Invalid request size')
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict): raise ValueError('Expected object')
                action, revision = body.get('action'), body.get('revision')
                if not allowed(role, action): return self._send(403, {'error':'insufficient permissions'})
                if type(revision) is not int: raise ValueError('revision required')
                with connect(db_path) as db:
                    state = change(db, role, action, revision, **{k:v for k,v in body.items() if k not in ('action','revision')})
                self._send(200, state)
            except (ValueError, TypeError) as exc: self._send(400, {'error':str(exc)})
            except RuntimeError as exc: self._send(409, {'error':str(exc)})
            except Exception: self._send(500, {'error':'internal server error'})

        def log_message(self, fmt, *args): pass
    return Handler


def serve(bind='127.0.0.1', port=8750):
    from aos_network import setup_server
    cert, key, _, fingerprint = setup_server()
    tokens = provision()
    server = ThreadingHTTPServer((bind, port), make_handler(LIVE_DB, tokens))
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(str(cert), str(key))
    server.socket = ctx.wrap_socket(server.socket, server_side=True)
    print('AOS live game server:', bind, port, 'TLS fingerprint:', fingerprint)
    print('Role tokens are stored locally at:', TOKEN_FILE)
    print('For LAN access use --bind 0.0.0.0 on a trusted network; configure firewall appropriately.')
    clock = GameClock(LIVE_DB)
    clock.start()
    try: server.serve_forever()
    finally:
        clock.stop()
        server.server_close()


class GameClock:
    """Single active timer across GUI/server processes, using an OS advisory lock.

    This process must remain running to advance the timer. No silent time
    subtraction is performed while the system is powered off.
    """
    def __init__(self, db_path=LIVE_DB):
        self.db_path = Path(db_path)
        self.stop_event = threading.Event()
        self.thread = None
        self.owner = False

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True, name='aos-game-clock')
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)

    def _run(self):
        """Keep trying for ownership so another process can take over after exit.

        Only the lock holder advances time. A newly elected owner starts a
        fresh monotonic interval: it never charges for time spent disconnected.
        """
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.db_path.with_suffix('.clock.lock')
        with open(lock_path, 'a+b') as lock:
            while not self.stop_event.is_set():
                try:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    self.stop_event.wait(0.25)
                    continue
                self.owner = True
                last = time.monotonic()
                try:
                    while not self.stop_event.wait(0.15):
                        current = time.monotonic()
                        elapsed = int(current - last)
                        if elapsed < 1:
                            continue
                        # Suspend/hibernate and scheduler stalls must not
                        # silently consume an entire round.
                        if elapsed > 5:
                            last = current
                            continue
                        last += elapsed
                        try:
                            with connect(self.db_path) as db:
                                state = read_state(db)
                                if state['status'] == 'running':
                                    change(db, 'server-clock', 'tick',
                                           state['revision'], seconds=elapsed)
                        except (RuntimeError, ValueError, sqlite3.OperationalError):
                            continue
                finally:
                    self.owner = False
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                break


def export_audit(db_path, destination):
    """Export the audit trail to CSV for event review."""
    destination = Path(destination)
    with connect(db_path) as db:
        rows = db.execute('SELECT time,actor,action,revision FROM audit ORDER BY id').fetchall()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('w', newline='', encoding='utf-8-sig') as out:
        writer = csv.writer(out)
        writer.writerow(('time_utc','actor','action','revision'))
        writer.writerows(rows)
    return len(rows)


def backup_database(db_path, destination):
    """Consistent SQLite backup, including transactions from WAL mode."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if Path(db_path).resolve() == destination.resolve():
        raise ValueError('Backup must be stored at a different path')
    with connect(db_path) as source, sqlite3.connect(destination) as target:
        source.backup(target)
    return destination


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--bind',default='127.0.0.1')
    parser.add_argument('--port',type=int,default=8750)
    args=parser.parse_args()
    serve(args.bind,args.port)
