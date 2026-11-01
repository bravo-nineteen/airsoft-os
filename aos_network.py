"""AOS 2.1: TLS certificate-pinned, read-only LAN event snapshots.

No background discovery, no remote command execution, no database writes.
"""
import hashlib
import hmac
import http.client
import json
import os
import secrets
import socket
import sqlite3
import ssl
import subprocess
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DATA = Path.home() / '.local/share/aos'
DB = DATA / 'operations.sqlite3'
NETWORK = DATA / 'network'
MAX_BYTES = 2_000_000


def setup_server():
    NETWORK.mkdir(parents=True, exist_ok=True)
    os.chmod(NETWORK, 0o700)
    cert, key, token_file = NETWORK / 'server.crt', NETWORK / 'server.key', NETWORK / 'access-token'
    if not cert.exists() or not key.exists():
        if cert.exists() != key.exists():
            raise RuntimeError('Only one TLS file exists. Restore both files from backup.')
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:3072', '-sha256', '-nodes',
                        '-keyout', str(key), '-out', str(cert), '-days', '365',
                        '-subj', '/CN=AOS Local Event Server'], check=True)
        os.chmod(key, 0o600)
    if not token_file.exists():
        token_file.write_text(secrets.token_urlsafe(32), encoding='ascii')
        os.chmod(token_file, 0o600)
    fingerprint = hashlib.sha256(ssl.PEM_cert_to_DER_cert(cert.read_text())).hexdigest()
    return cert, key, token_file.read_text().strip(), fingerprint


def snapshot():
    result = {'schema': 1, 'generated_at': datetime.now(timezone.utc).isoformat(),
              'events': [], 'rosters': []}
    if not DB.exists():
        return result
    conn = sqlite3.connect(f'file:{DB}?mode=ro', uri=True, timeout=2)
    try:
        result['events'] = [dict(zip(('id', 'name', 'date', 'venue'), r)) for r in
                            conn.execute('SELECT id,name,date,venue FROM events ORDER BY date DESC LIMIT 500')]
        result['rosters'] = [dict(zip(('event_id','member','callsign','team','status'), r)) for r in
                             conn.execute('SELECT r.event_id,m.name,m.callsign,m.team,r.status '
                                          'FROM roster r JOIN members m ON r.member_id=m.id '
                                          'ORDER BY r.event_id,m.name LIMIT 10000')]
    except sqlite3.OperationalError as exc:
        raise RuntimeError('Event database unavailable or incompatible') from exc
    finally:
        conn.close()
    return result


def serve(bind='0.0.0.0', port=8743, discovery=False):
    cert, key, token, fingerprint = setup_server()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != '/api/v1/snapshot':
                self.send_error(404)
                return
            supplied = self.headers.get('X-AOS-Token', '')
            if not hmac.compare_digest(supplied, token):
                self.send_error(403)
                return
            try:
                payload = json.dumps(snapshot(), ensure_ascii=False).encode('utf-8')
                if len(payload) > MAX_BYTES:
                    raise ValueError('Snapshot too large')
            except Exception:
                self.send_error(503, 'Snapshot unavailable')
                return
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, fmt, *args):
            print('%s - %s' % (self.address_string(), fmt % args))

    server = ThreadingHTTPServer((bind, port), Handler)
    server.daemon_threads = True
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=str(cert), keyfile=str(key))
    server.socket = context.wrap_socket(server.socket, server_side=True)
    print(f'AOS LAN server: https://{bind}:{port}/api/v1/snapshot')
    print('TLS SHA256 fingerprint:', fingerprint)
    print('Pairing token (keep private):', token)
    print('Share the fingerprint and token with trusted terminal operators only.')
    stop = threading.Event()
    beacon = None
    if discovery:
        from aos_field_sync import advertise_server
        beacon = threading.Thread(target=advertise_server, args=(port, fingerprint, stop), daemon=True)
        beacon.start()
        print('LAN discovery enabled (endpoint and fingerprint only; no token).')
    try:
        server.serve_forever()
    finally:
        stop.set()
        if beacon: beacon.join(timeout=2)
        server.server_close()


def fetch_snapshot(host, port, token, fingerprint, timeout=6):
    """Verify the actual TLS certificate on the SAME connection before sending token."""
    host = host.strip()
    fingerprint = fingerprint.lower().replace(':', '').strip()
    if not host or len(host) > 253 or any(c in host for c in '/@?#:'):
        raise ValueError('Enter a hostname or IP address, without a URL or port')
    if not (1 <= int(port) <= 65535):
        raise ValueError('Invalid port')
    if len(fingerprint) != 64 or any(c not in '0123456789abcdef' for c in fingerprint):
        raise ValueError('Enter the 64-character server TLS SHA256 fingerprint')
    if not token.strip():
        raise ValueError('Pairing token required')
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # Explicit fingerprint pinning below.
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    with socket.create_connection((host, int(port)), timeout=timeout) as raw:
        with ctx.wrap_socket(raw, server_hostname=host) as tls:
            tls.settimeout(timeout)
            actual = hashlib.sha256(tls.getpeercert(binary_form=True)).hexdigest()
            if not hmac.compare_digest(actual, fingerprint):
                raise ssl.SSLError('Server certificate fingerprint does not match')
            # No token is transmitted until certificate identity has been checked.
            request = ('GET /api/v1/snapshot HTTP/1.1\r\n'
                       f'Host: {host}\r\n'
                       f'X-AOS-Token: {token.strip()}\r\n'
                       'Accept: application/json\r\nConnection: close\r\n\r\n')
            tls.sendall(request.encode('ascii'))
            response = http.client.HTTPResponse(tls)
            response.begin()
            if response.status != 200:
                raise RuntimeError(f'Server returned HTTP {response.status}')
            if int(response.getheader('Content-Length', '0')) > MAX_BYTES:
                raise RuntimeError('Snapshot too large')
            data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise RuntimeError('Snapshot too large')
            payload = json.loads(data)
            if not isinstance(payload, dict) or payload.get('schema') != 1:
                raise ValueError('Unsupported snapshot format')
            if not isinstance(payload.get('events'), list) or not isinstance(payload.get('rosters'), list):
                raise ValueError('Malformed snapshot')
            return payload


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='AOS secure LAN read-only roster server')
    parser.add_argument('--bind', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8743)
    parser.add_argument('--discoverable', action='store_true', help='Broadcast server address and fingerprint on local LAN')
    args = parser.parse_args()
    serve(args.bind, args.port, args.discoverable)
