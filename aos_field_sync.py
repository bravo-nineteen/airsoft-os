"""AOS 2.2: private offline snapshot cache and optional LAN discovery.

Discovery broadcasts *only* a server endpoint and TLS fingerprint. It never
transmits the pairing token or member/roster data. Always verify fingerprint.
"""
import csv
import hashlib
import json
import os
import socket
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

DISCOVERY_PORT = 8744
DISCOVERY_MAGIC = 'AOS_DISCOVERY_V1'
CACHE_ROOT = Path.home() / '.local/share/aos/remote-cache'
MAX_SNAPSHOT_BYTES = 2_000_000


def validate_snapshot(payload):
    if not isinstance(payload, dict) or payload.get('schema') != 1:
        raise ValueError('Unsupported snapshot schema')
    events, rosters = payload.get('events'), payload.get('rosters')
    if not isinstance(events, list) or not isinstance(rosters, list):
        raise ValueError('Invalid events or rosters')
    if len(events) > 500 or len(rosters) > 10000:
        raise ValueError('Too many snapshot records')
    for row in events + rosters:
        if not isinstance(row, dict):
            raise ValueError('Malformed snapshot row')
    raw = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise ValueError('Snapshot too large')
    return raw


def cache_file(host, port, fingerprint):
    key = hashlib.sha256(f'{host.strip().lower()}|{int(port)}|{fingerprint.lower().replace(":", "")}'.encode()).hexdigest()[:24]
    return CACHE_ROOT / (key + '.json')


def save_cache(host, port, fingerprint, payload):
    raw = validate_snapshot(payload)
    CACHE_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(CACHE_ROOT, 0o700)
    target = cache_file(host, port, fingerprint)
    wrapper = {'saved_at': datetime.now(timezone.utc).isoformat(), 'snapshot': payload}
    contents = json.dumps(wrapper, ensure_ascii=False).encode('utf-8')
    fd, temp = tempfile.mkstemp(prefix='.aos-', suffix='.tmp', dir=CACHE_ROOT)
    try:
        with os.fdopen(fd, 'wb') as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, target)
    finally:
        if os.path.exists(temp): os.unlink(temp)
    return target


def load_cache(host, port, fingerprint):
    target = cache_file(host, port, fingerprint)
    if target.stat().st_size > MAX_SNAPSHOT_BYTES + 1024:
        raise ValueError('Cached snapshot too large')
    data = json.loads(target.read_text(encoding='utf-8'))
    validate_snapshot(data['snapshot'])
    return data


def export_csv(payload, kind, path):
    validate_snapshot(payload)
    fields = {'events': ('id', 'name', 'date', 'venue'),
              'rosters': ('event_id', 'member', 'callsign', 'team', 'status')}
    if kind not in fields: raise ValueError('Unknown export type')
    with open(path, 'w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields[kind], extrasaction='ignore')
        writer.writeheader()
        for row in payload[kind]:
            writer.writerow({k: str(row.get(k, '') or '') for k in fields[kind]})


def advertise_server(port, fingerprint, stop_event, discovery_port=DISCOVERY_PORT):
    """Optional broadcast; never include secrets or private data."""
    message = json.dumps({'magic': DISCOVERY_MAGIC, 'port': port,
                          'fingerprint': fingerprint, 'name': 'AOS Field Server'}).encode()
    while not stop_event.is_set():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.sendto(message, ('255.255.255.255', discovery_port))
        except OSError:
            pass
        stop_event.wait(3)


def discover_servers(seconds=4, discovery_port=DISCOVERY_PORT):
    """Passive LAN discovery; caller must authenticate via pinned TLS afterwards."""
    found = {}
    deadline = time.monotonic() + min(max(float(seconds), 0.2), 10.0)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', discovery_port))
        while time.monotonic() < deadline:
            sock.settimeout(min(0.5, max(0.01, deadline - time.monotonic())))
            try: data, address = sock.recvfrom(2048)
            except socket.timeout: continue
            try:
                msg = json.loads(data)
                fp = str(msg.get('fingerprint', '')).lower()
                port = int(msg.get('port', 0))
                if (msg.get('magic') != DISCOVERY_MAGIC or len(fp) != 64 or
                        any(c not in '0123456789abcdef' for c in fp) or
                        not 1 <= port <= 65535): continue
                found[(address[0], port, fp)] = {'host': address[0], 'port': port,
                                                 'fingerprint': fp}
            except (ValueError, TypeError, AttributeError): continue
    return list(found.values())
