"""Native offline-first AOJ team operations. UDP LAN is opt-in and unauthenticated: trusted LAN only."""
import json
import socket
import uuid
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel,
                               QPushButton, QTextEdit, QLineEdit, QComboBox, QFormLayout,
                               QMessageBox, QSpinBox, QCheckBox, QListWidget)

DATA = Path.home() / '.config' / 'aoj-os' / 'team_ops.json'
DEFAULT = {
 'unit':'Black Talon Unit', 'callsign':'BT-01', 'host':'127.0.0.1', 'port':47631,
 'event':'AOJ FIELD EVENT', 'schedule':[
  {'time':'09:00','game':'Safety briefing','rules':'Eye protection mandatory. Follow the field marshal.'},
  {'time':'10:00','game':'Team Deathmatch','rules':'Follow the event-specific respawn and hit rules.'},
  {'time':'11:00','game':'Confirmed Kill','rules':'Collect opposing team tags; the Game Master confirms the scoring.'},
  {'time':'13:00','game':'Cyber Operations','rules':'Complete the three native simulation stages to finish the mission.'}],
 'messages':[], 'seen':[]}

def read_data():
    if DATA.exists():
        try:
            value=json.loads(DATA.read_text(encoding='utf-8'))
            if isinstance(value,dict):
                return {**DEFAULT,**value}
        except (OSError,ValueError): pass
    return json.loads(json.dumps(DEFAULT))

def save_data(d):
    DATA.parent.mkdir(parents=True,exist_ok=True)
    DATA.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf-8')

class TeamOperations(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle('AOJ // TEAM OPERATIONS')
        self.resize(800,620)
        self.data=read_data()
        self.sock=None
        self.setStyleSheet('QDialog{background:#0b1518;color:#e4e9e8} QWidget{color:#e4e9e8;font-size:12px} QLineEdit,QTextEdit,QComboBox,QSpinBox,QListWidget{background:#132427;border:1px solid #456064;padding:5px} QPushButton{background:#27383b;border:1px solid #51676b;padding:7px} QPushButton:hover{background:#40545a}')
        outer=QVBoxLayout(self)
        title=QLabel('AOJ  //  TEAM OPERATIONS   •   NATIVE / OFFLINE-FIRST')
        title.setStyleSheet('font-size:16px;font-weight:bold;color:#e36a62')
        outer.addWidget(title)
        self.tabs=QTabWidget();outer.addWidget(self.tabs)
        self._briefing();self._messages();self._configuration()
        self.status=QLabel('LOCAL MODE — No network connection enabled')
        outer.addWidget(self.status)
        self.timer=QTimer(self);self.timer.timeout.connect(self.poll);self.timer.start(250)
        self.refresh_briefing();self.refresh_messages()

    def _briefing(self):
        w=QWidget();v=QVBoxLayout(w)
        self.event_name=QLabel();self.event_name.setStyleSheet('font-size:17px;font-weight:bold')
        v.addWidget(self.event_name)
        self.games=QListWidget();self.games.currentRowChanged.connect(self.show_rule);v.addWidget(self.games)
        v.addWidget(QLabel('GAME RULES / BRIEFING'))
        self.rules=QTextEdit();self.rules.setReadOnly(True);v.addWidget(self.rules)
        self.tabs.addTab(w,'Event / Game Rules')

    def _messages(self):
        w=QWidget();v=QVBoxLayout(w)
        self.inbox=QTextEdit();self.inbox.setReadOnly(True);v.addWidget(self.inbox)
        v.addWidget(QLabel('Send short text to another unit on the configured LAN endpoint'))
        self.destination=QComboBox();self.destination.addItems(['ALL','Black Talon Unit','Task Force Unit','AOJ Command'])
        v.addWidget(self.destination)
        self.compose=QLineEdit();self.compose.setPlaceholderText('Message (maximum 200 characters)')
        self.compose.setMaxLength(200);v.addWidget(self.compose)
        send=QPushButton('SEND / SAVE MESSAGE');send.clicked.connect(self.send_message);v.addWidget(send)
        self.tabs.addTab(w,'Messages')

    def _configuration(self):
        w=QWidget();v=QVBoxLayout(w);form=QFormLayout()
        self.unit=QComboBox();self.unit.addItems(['Black Talon Unit','Task Force Unit','AOJ Command','The Syndicate','The Horde'])
        self.unit.setCurrentText(self.data['unit']);form.addRow('Unit',self.unit)
        self.callsign=QLineEdit(self.data['callsign']);form.addRow('Callsign',self.callsign)
        self.host=QLineEdit(self.data['host']);form.addRow('Destination IPv4',self.host)
        self.port=QSpinBox();self.port.setRange(1024,65535);self.port.setValue(int(self.data['port']))
        form.addRow('UDP port',self.port)
        self.lan=QCheckBox('Enable LAN receive/send (trusted local network only)')
        form.addRow(self.lan)
        v.addLayout(form)
        save=QPushButton('SAVE SETTINGS');save.clicked.connect(self.save_settings);v.addWidget(save)
        v.addWidget(QLabel('Event schedule is stored locally as JSON and remains available offline.'))
        v.addWidget(QLabel('Edit ~/.config/aoj-os/team_ops.json to change games and rules.'))
        v.addWidget(QLabel('LAN messages are NOT encrypted or authenticated. Do not use on untrusted networks.'))
        v.addWidget(QLabel('Heltec V3 / LoRa hardware integration is not implemented in this release.'))
        v.addStretch();self.tabs.addTab(w,'Unit / Network')

    def refresh_briefing(self):
        self.event_name.setText(f"{self.data['event']}   /   {self.data['unit']}")
        row=self.games.currentRow();self.games.clear()
        for game in self.data['schedule']:
            self.games.addItem(f"{game['time']}   {game['game']}")
        if self.games.count(): self.games.setCurrentRow(max(0,row))

    def show_rule(self,row):
        schedule=self.data.get('schedule',[])
        self.rules.setPlainText(schedule[row].get('rules','') if 0<=row<len(schedule) else '')

    def refresh_messages(self):
        lines=[]
        for m in self.data['messages'][-70:]:
            lines.append(f"[{m['time']}] {m['sender']} → {m['to']}: {m['text']}")
        self.inbox.setPlainText('\n\n'.join(lines) or 'No messages yet.')
        self.inbox.moveCursor(self.inbox.textCursor().MoveOperation.End)

    def save_settings(self):
        self.data.update(unit=self.unit.currentText(),callsign=self.callsign.text().strip()[:30],
                         host=self.host.text().strip(),port=self.port.value())
        save_data(self.data);self.refresh_briefing()
        if self.lan.isChecked(): self.start_lan()
        else: self.stop_lan()

    def start_lan(self):
        self.stop_lan()
        try:
            self.sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            self.sock.setblocking(False)
            self.sock.bind(('0.0.0.0',self.data['port']))
            self.status.setText(f"LAN LISTENING UDP {self.data['port']} — Unauthenticated test transport")
        except OSError as e:
            self.stop_lan();QMessageBox.warning(self,'Network',str(e))
            self.lan.setChecked(False)

    def stop_lan(self):
        if self.sock:self.sock.close();self.sock=None
        self.status.setText('LOCAL MODE — No network connection enabled')

    def send_message(self):
        value=self.compose.text().strip()
        if not value:return
        packet=dict(version=1,id=str(uuid.uuid4()),time=datetime.now().strftime('%H:%M:%S'),
                    sender=self.data['unit'],to=self.destination.currentText(),text=value)
        self.data['messages'].append(packet);self.data['messages']=self.data['messages'][-200:]
        self.data['seen'].append(packet['id']);self.data['seen']=self.data['seen'][-500:]
        save_data(self.data);self.refresh_messages();self.compose.clear()
        if self.sock:
            try:self.sock.sendto(json.dumps(packet).encode('utf-8'),(self.data['host'],self.data['port']))
            except OSError as e:self.status.setText(f'SEND FAILED: {e}')

    def poll(self):
        if not self.sock:return
        for _ in range(10):
            try:raw,source=self.sock.recvfrom(2048)
            except BlockingIOError:break
            except OSError:break
            try:
                packet=json.loads(raw.decode('utf-8'))
                if (packet.get('version')!=1 or not isinstance(packet.get('id'),str)
                    or packet['id'] in self.data['seen'] or not isinstance(packet.get('text'),str)
                    or len(packet['text'])>200 or packet.get('to') not in ('ALL',self.data['unit'])):continue
                if not isinstance(packet.get('sender'),str):continue
                self.data['messages'].append({k:str(packet.get(k,''))[:200] for k in ('id','time','sender','to','text')})
                self.data['messages']=self.data['messages'][-200:]
                self.data['seen'].append(packet['id']);self.data['seen']=self.data['seen'][-500:]
                save_data(self.data);self.refresh_messages()
            except (UnicodeError,ValueError,TypeError,KeyError):continue

    def closeEvent(self,event):
        self.stop_lan();super().closeEvent(event)
