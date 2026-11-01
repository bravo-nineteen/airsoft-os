"""GUI to view authenticated, certificate-pinned LAN event snapshots."""
import json
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QTableWidget, QTableWidgetItem, QTabWidget, QWidget, QFormLayout, QFileDialog, QMessageBox, QComboBox)
from aos_network import fetch_snapshot
from aos_field_sync import save_cache, load_cache, export_csv, discover_servers

SETTINGS = Path.home() / '.config/aos/network-client.json'


class FetchThread(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, host, port, token, fingerprint):
        super().__init__()
        self.args = (host, port, token, fingerprint)

    def run(self):
        try:
            self.completed.emit(fetch_snapshot(*self.args))
        except Exception as exc:
            self.failed.emit(str(exc))


class DiscoveryThread(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def run(self):
        try:
            self.completed.emit(discover_servers(seconds=4))
        except Exception as exc:
            self.failed.emit(str(exc))


class NetworkViewer(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('AOS 2.2 // FIELD SYNC')
        self.resize(810, 630)
        self.setStyleSheet('QDialog,QWidget{background:#0e191b;color:#eaf0ed}'
                           'QLineEdit,QTableWidget{background:#15272a;color:#f0f5f3;border:1px solid #425a5e;padding:5px}'
                           'QPushButton{background:#253a3d;color:white;padding:9px;border:1px solid #496468}')
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('SECURE FIELD SYNC  /  READ-ONLY  /  OFFLINE CACHE'))
        form = QFormLayout()
        self.host = QLineEdit(); self.host.setPlaceholderText('192.168.1.20')
        self.port = QLineEdit('8743')
        self.fingerprint = QLineEdit(); self.fingerprint.setPlaceholderText('64-character SHA256 certificate fingerprint')
        self.token = QLineEdit(); self.token.setEchoMode(QLineEdit.EchoMode.Password)
        self.token.setPlaceholderText('Server pairing token — not saved')
        for name, field in [('Server IP / hostname', self.host), ('Port', self.port),
                            ('TLS SHA256 fingerprint', self.fingerprint), ('Pairing token', self.token)]:
            form.addRow(name, field)
        layout.addLayout(form)
        self.connect_button = QPushButton('CONNECT AND FETCH EVENT DATA')
        self.connect_button.clicked.connect(self.fetch)
        controls = QHBoxLayout()
        controls.addWidget(self.connect_button)
        self.discover_button = QPushButton('FIND LAN SERVERS')
        self.discover_button.clicked.connect(self.discover)
        controls.addWidget(self.discover_button)
        self.offline_button = QPushButton('OPEN OFFLINE COPY')
        self.offline_button.clicked.connect(self.open_offline)
        controls.addWidget(self.offline_button)
        layout.addLayout(controls)
        self.status = QLabel('No connection. Remote information is never merged into your local database.')
        layout.addWidget(self.status)
        tabs = QTabWidget(); layout.addWidget(tabs)
        self.events = QTableWidget(0, 4); self.events.setHorizontalHeaderLabels(['ID','Event','Date','Venue'])
        self.rosters = QTableWidget(0, 5); self.rosters.setHorizontalHeaderLabels(['Event ID','Member','Callsign','Team','Status'])
        tabs.addTab(self.events, 'Events'); tabs.addTab(self.rosters, 'Rosters')
        exports = QHBoxLayout()
        for name, kind in [('EXPORT EVENTS CSV', 'events'), ('EXPORT ROSTER CSV', 'rosters')]:
            button = QPushButton(name)
            button.clicked.connect(lambda checked=False, k=kind: self.export(k))
            exports.addWidget(button)
        layout.addLayout(exports)
        self.payload = None
        self.discovery_worker = None
        self.worker = None
        try:
            data = json.loads(SETTINGS.read_text())
            self.host.setText(data.get('host', ''))
            self.port.setText(str(data.get('port', 8743)))
            self.fingerprint.setText(data.get('fingerprint', ''))
        except (OSError, ValueError, TypeError):
            pass

    def fetch(self):
        if self.worker and self.worker.isRunning():
            return
        self.connect_button.setEnabled(False)
        self.status.setText('Connecting securely…')
        self.worker = FetchThread(self.host.text(), self.port.text(), self.token.text(), self.fingerprint.text())
        self.worker.completed.connect(self.on_success)
        self.worker.failed.connect(self.on_failure)
        self.worker.finished.connect(lambda: self.connect_button.setEnabled(True))
        self.worker.start()

    def on_success(self, payload):
        self.payload = payload
        self.fill(self.events, payload['events'], ('id','name','date','venue'))
        self.fill(self.rosters, payload['rosters'], ('event_id','member','callsign','team','status'))
        self.status.setText(f"Secure connection verified • {len(payload['events'])} events • "
                            f"{len(payload['rosters'])} roster entries • {payload.get('generated_at','')}")
        SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS.write_text(json.dumps({'host':self.host.text().strip(),
            'port':self.port.text().strip(), 'fingerprint':self.fingerprint.text().strip()}))
        SETTINGS.chmod(0o600)
        try:
            save_cache(self.host.text(), self.port.text(), self.fingerprint.text(), payload)
        except (OSError, ValueError) as exc:
            self.status.setText(self.status.text() + ' • Offline save failed: ' + str(exc)[:90])

    def on_failure(self, error):
        self.status.setText('Connection failed: ' + error[:350])

    def open_offline(self):
        try:
            cached = load_cache(self.host.text(), self.port.text(), self.fingerprint.text())
            payload = cached['snapshot']
            self.payload = payload
            self.fill(self.events, payload['events'], ('id','name','date','venue'))
            self.fill(self.rosters, payload['rosters'], ('event_id','member','callsign','team','status'))
            self.status.setText('OFFLINE COPY • Saved ' + cached.get('saved_at', 'unknown time') +
                                ' • May be outdated; no live connection')
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.status.setText('No valid offline copy for this server: ' + str(exc)[:160])

    def export(self, kind):
        if self.payload is None:
            QMessageBox.information(self, 'Export', 'Connect or open an offline copy first.')
            return
        filename, _ = QFileDialog.getSaveFileName(self, 'Export AOS ' + kind, 'aos-' + kind + '.csv',
                                                  'CSV files (*.csv)')
        if not filename: return
        try:
            export_csv(self.payload, kind, filename)
            self.status.setText('Exported ' + kind + ' to ' + filename)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Export failed', str(exc))

    def discover(self):
        if self.discovery_worker and self.discovery_worker.isRunning(): return
        self.discover_button.setEnabled(False)
        self.status.setText('Listening for AOS servers on this LAN for 4 seconds…')
        self.discovery_worker = DiscoveryThread()
        self.discovery_worker.completed.connect(self.on_discovered)
        self.discovery_worker.failed.connect(lambda error: self.status.setText('Discovery error: ' + error[:180]))
        self.discovery_worker.finished.connect(lambda: self.discover_button.setEnabled(True))
        self.discovery_worker.start()

    def on_discovered(self, servers):
        if not servers:
            self.status.setText('No discoverable servers found. On the host use: python aos_network.py --discoverable')
            return
        choices = [f"{s['host']}:{s['port']}  [{s['fingerprint'][:16]}…]" for s in servers]
        from PySide6.QtWidgets import QInputDialog
        choice, ok = QInputDialog.getItem(self, 'Discovered AOS servers',
                                          'Choose server (verify fingerprint with its operator):',
                                          choices, 0, False)
        if ok:
            server = servers[choices.index(choice)]
            self.host.setText(server['host'])
            self.port.setText(str(server['port']))
            self.fingerprint.setText(server['fingerprint'])
            self.status.setText('Server discovered, NOT authenticated. Confirm its TLS fingerprint with the operator and enter the pairing token.')

    @staticmethod
    def fill(table, records, keys):
        table.setRowCount(min(len(records), 10000))
        for i, record in enumerate(records[:10000]):
            for j, key in enumerate(keys):
                table.setItem(i, j, QTableWidgetItem(str(record.get(key, '') if isinstance(record, dict) else '')))
        table.resizeColumnsToContents()

    def closeEvent(self, event):
        if ((self.worker and self.worker.isRunning()) or
                (self.discovery_worker and self.discovery_worker.isRunning())):
            self.hide()
            event.ignore()
            return
        super().closeEvent(event)
