"""Native Qt cyber puzzle: standalone offline simulation, no browser or network attacks."""
import random
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QPushButton,QLineEdit,QHBoxLayout,QTextEdit,QComboBox
from PySide6.QtCore import Qt,QTimer

class CyberOperations(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle('AOJ // CYBER OPERATIONS — Native Simulator')
        self.resize(760,540)
        self.setStyleSheet('QDialog{background:#081619;color:#e6eeec} QWidget{color:#e6eeec} QPushButton{background:#24393a;border:1px solid #56746e;padding:10px} QLineEdit,QComboBox,QTextEdit{background:#0b2322;border:1px solid #4c6c63;padding:8px;color:#d2ffdf}')
        self.stage=0;self.seconds=900;self.path=[]
        self.steps=[('ROUTING','Select a safe sequence of nodes from START to SERVER.'),
                    ('TERMINAL','Enter the correct simulated command from the mission briefing.'),
                    ('DATA REROUTE','Choose the correct destination for the classified data packet.')]
        self.layout=QVBoxLayout(self)
        self.title=QLabel();self.title.setStyleSheet('font-size:19px;font-weight:bold;color:#e27670');self.layout.addWidget(self.title)
        self.brief=QLabel();self.brief.setWordWrap(True);self.layout.addWidget(self.brief)
        self.time=QLabel();self.layout.addWidget(self.time)
        self.output=QTextEdit();self.output.setReadOnly(True);self.layout.addWidget(self.output)
        self.controls=QHBoxLayout();self.layout.addLayout(self.controls)
        self.feedback=QLabel();self.layout.addWidget(self.feedback)
        self.reset=QPushButton('RESTART MISSION');self.reset.clicked.connect(self.restart);self.layout.addWidget(self.reset)
        self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(1000)
        self.restart()

    def clear_controls(self):
        while self.controls.count():
            item=self.controls.takeAt(0)
            if item.widget():item.widget().deleteLater()

    def restart(self):
        self.stage=0;self.seconds=900;self.path=[]
        self.command=random.choice(['route --verify','auth --token','sync --secure'])
        self.target=random.choice(['ARCHIVE','RELAY','VAULT'])
        self.render()

    def tick(self):
        if self.seconds>0 and self.stage<3:self.seconds-=1
        self.time.setText(f'TIME REMAINING  {self.seconds//60:02d}:{self.seconds%60:02d}')
        if self.seconds==0 and self.stage<3:
            self.stage=4;self.render()

    def render(self):
        self.clear_controls();self.feedback.setText('')
        if self.stage>=3:
            self.title.setText('MISSION COMPLETE' if self.stage==3 else 'MISSION TIME EXPIRED')
            self.brief.setText('Offline training simulation. Restart to play again.')
            self.output.setPlainText('All three stages completed.' if self.stage==3 else 'The mission was not completed in time.')
            return
        name,desc=self.steps[self.stage]
        self.title.setText(f'CYBER OPERATIONS  //  STAGE {self.stage+1}/3 — {name}')
        self.brief.setText(desc)
        if self.stage==0:
            self.output.setPlainText('NODE GRAPH (SIMULATION)\n\nSTART → ALPHA → BRAVO → SERVER\nSTART → DECOY → SERVER [UNSAFE]\n\nSelect nodes in the correct order.')
            for node in ('ALPHA','BRAVO','DECOY','SERVER'):
                b=QPushButton(node);b.clicked.connect(lambda checked=False,n=node:self.route(n));self.controls.addWidget(b)
        elif self.stage==1:
            self.output.setPlainText('SIMULATED TERMINAL\n\nCommand fragment recovered:\n'+self.command+'\n\nEnter this exact command to authenticate. No real shell commands are executed.')
            self.entry=QLineEdit();self.entry.setPlaceholderText('Type command');self.controls.addWidget(self.entry)
            b=QPushButton('EXECUTE');b.clicked.connect(self.terminal);self.controls.addWidget(b)
        else:
            self.output.setPlainText(f'DATA REROUTE\n\nIntel indicates the approved destination is {self.target}.\nChoose the destination to finish the mission.')
            for name in ('ARCHIVE','RELAY','VAULT'):
                b=QPushButton(name);b.clicked.connect(lambda checked=False,n=name:self.reroute(n));self.controls.addWidget(b)

    def route(self,node):
        expected=['ALPHA','BRAVO','SERVER']
        if node==expected[len(self.path)]:
            self.path.append(node)
            self.feedback.setText('ROUTE VERIFIED: '+' → '.join(self.path))
            if len(self.path)==3:self.stage=1;self.render()
        else:self.path=[];self.feedback.setText('ROUTE REJECTED — START AGAIN')

    def terminal(self):
        if self.entry.text().strip()==self.command:self.stage=2;self.render()
        else:self.feedback.setText('AUTHENTICATION FAILED — CHECK COMMAND')

    def reroute(self,value):
        if value==self.target:self.stage=3;self.render()
        else:self.feedback.setText('INCORRECT DESTINATION — TRY AGAIN')
