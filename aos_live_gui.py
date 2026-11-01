"""Native local game console, running against the same SQLite state as LAN server."""
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QSpinBox,QLineEdit,QMessageBox,QFileDialog
from PySide6.QtCore import QTimer
from aos_live import connect,read_state,change,GameClock,LIVE_DB,export_audit,backup_database

class LiveConsole(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle('AOS 3.2 // LIVE OPERATIONS')
        self.resize(530,420)
        root=QVBoxLayout(self)
        self.title=QLineEdit('Training Round')
        self.duration=QSpinBox();self.duration.setRange(1,240);self.duration.setValue(15);self.duration.setSuffix(' minutes')
        row=QHBoxLayout();row.addWidget(QLabel('Round'));row.addWidget(self.title);row.addWidget(self.duration);root.addLayout(row)
        self.info=QLabel();root.addWidget(self.info)
        row=QHBoxLayout()
        for text,action in [('Configure','configure'),('Start','start'),('Pause','pause'),('Reset','reset')]:
            b=QPushButton(text);b.clicked.connect(lambda checked=False,a=action:self.apply(a));row.addWidget(b)
        root.addLayout(row)
        row=QHBoxLayout()
        for text,team,delta in [('RED +','red',1),('RED −','red',-1),('BLUE +','blue',1),('BLUE −','blue',-1)]:
            b=QPushButton(text);b.clicked.connect(lambda checked=False,t=team,d=delta:self.apply('score',team=t,delta=d));row.addWidget(b)
        root.addLayout(row)
        root.addWidget(QLabel('Local Game Master console. LAN terminals can view state with role tokens.'))
        tools=QHBoxLayout()
        audit=QPushButton('Export audit CSV');audit.clicked.connect(self.export_csv);tools.addWidget(audit)
        backup=QPushButton('Back up game database');backup.clicked.connect(self.save_backup);tools.addWidget(backup)
        root.addLayout(tools)
        self.clock=GameClock(LIVE_DB)
        self.clock.start()
        self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(1000)
        self.last_tick=None
        self.refresh()

    def refresh(self):
        with connect() as db:
            state=read_state(db)
        mm,ss=divmod(state['remaining'],60)
        self.info.setText(f"<h2>{mm:02}:{ss:02} · {state['status'].upper()}</h2><h2>RED {state['red']} : {state['blue']} BLUE</h2><p>Revision {state['revision']} · {state['title']}</p>")

    def apply(self,action,**kw):
        if action=='configure':kw.update(title=self.title.text(),duration=self.duration.value()*60)
        try:
            with connect() as db:
                state=read_state(db)
                change(db,'local-gm',action,state['revision'],**kw)
            self.refresh()
        except Exception as exc:QMessageBox.warning(self,'Game control',str(exc))

    def export_csv(self):
        path,_=QFileDialog.getSaveFileName(self,'Export game audit','aos-game-audit.csv','CSV files (*.csv)')
        if path:
            try:
                count=export_audit(LIVE_DB,path)
                QMessageBox.information(self,'Audit exported',f'Exported {count} actions.')
            except Exception as exc: QMessageBox.warning(self,'Export failed',str(exc))

    def save_backup(self):
        path,_=QFileDialog.getSaveFileName(self,'Back up game database','aos-game-backup.sqlite3','SQLite database (*.sqlite3)')
        if path:
            try:
                backup_database(LIVE_DB,path)
                QMessageBox.information(self,'Backup complete','Database backup created.')
            except Exception as exc: QMessageBox.warning(self,'Backup failed',str(exc))

    def closeEvent(self,event):
        self.clock.stop()
        super().closeEvent(event)
