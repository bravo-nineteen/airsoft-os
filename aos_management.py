"""AOS offline roster/member/event manager. Data stays local in SQLite."""
import csv, sqlite3
from pathlib import Path
from PySide6.QtWidgets import (QDialog,QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLineEdit,QPushButton,QTabWidget,QTableWidget,QTableWidgetItem,QMessageBox,QComboBox,QFileDialog,QLabel)
DB=Path.home()/'.local/share/aos/operations.sqlite3'

def connect():
    DB.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(DB)
    c.execute('PRAGMA foreign_keys=ON')
    c.execute('CREATE TABLE IF NOT EXISTS members (id INTEGER PRIMARY KEY, name TEXT NOT NULL, callsign TEXT, team TEXT, notes TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, name TEXT NOT NULL, date TEXT NOT NULL, venue TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS roster (event_id INTEGER NOT NULL, member_id INTEGER NOT NULL, status TEXT NOT NULL DEFAULT "Confirmed", PRIMARY KEY(event_id,member_id), FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE, FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE CASCADE)')
    c.commit(); return c

class OperationsManager(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle('AOS // EVENT OPERATIONS')
        self.resize(850,600)
        self.setStyleSheet('QDialog{background:#10191b;color:#f1f5f4;font-size:12px} QWidget{color:#f1f5f4;font-size:12px} QLineEdit,QComboBox,QTableWidget{background:#122327;color:#f0f4f2;border:1px solid #496164;padding:5px} QPushButton{background:#24363a;color:#f0f4f2;border:1px solid #5b7477;padding:9px} QPushButton:hover{background:#344b50} QTabWidget::pane{background:#10191b;border:1px solid #42595c} QTabBar::tab{background:#203135;color:#f1f5f4;padding:9px 14px} QTabBar::tab:selected{background:#71302d;color:white} QHeaderView::section{background:#203135;color:#f1f5f4;padding:6px;border:1px solid #42595c} QTableWidget::item{background:#122327;color:#f1f5f4} QTableWidget::item:selected{background:#71302d;color:white}')
        self.conn=connect(); root=QVBoxLayout(self)
        root.addWidget(QLabel('AIRSOFT OS  /  OPERATIONS DATABASE  /  OFFLINE'))
        tabs=QTabWidget();root.addWidget(tabs)
        mw=QWidget();mv=QVBoxLayout(mw);mf=QFormLayout()
        self.name=QLineEdit();self.callsign=QLineEdit();self.team=QComboBox();self.team.setEditable(True);self.team.addItems(['AOJ','Black Talon','Task Force','Other']);self.notes=QLineEdit()
        for k,v in [('Name',self.name),('Callsign',self.callsign),('Team',self.team),('Notes',self.notes)]:mf.addRow(k,v)
        mv.addLayout(mf);add=QPushButton('ADD MEMBER');add.clicked.connect(self.add_member);mv.addWidget(add)
        self.members=QTableWidget();self.members.setColumnCount(5);self.members.setHorizontalHeaderLabels(['ID','Name','Callsign','Team','Notes']);self.members.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);mv.addWidget(self.members)
        row=QHBoxLayout();remove=QPushButton('DELETE SELECTED');remove.clicked.connect(self.delete_member);export=QPushButton('EXPORT MEMBERS CSV');export.clicked.connect(self.export_members);row.addWidget(remove);row.addWidget(export);mv.addLayout(row);tabs.addTab(mw,'Member Profiles')
        ew=QWidget();ev=QVBoxLayout(ew);ef=QFormLayout();self.event_name=QLineEdit();self.event_date=QLineEdit();self.event_date.setPlaceholderText('YYYY-MM-DD');self.venue=QLineEdit()
        for k,v in [('Event name',self.event_name),('Date',self.event_date),('Venue',self.venue)]:ef.addRow(k,v)
        ev.addLayout(ef);add_event=QPushButton('CREATE EVENT');add_event.clicked.connect(self.add_event);ev.addWidget(add_event)
        self.events=QTableWidget();self.events.setColumnCount(4);self.events.setHorizontalHeaderLabels(['ID','Event','Date','Venue']);ev.addWidget(self.events);tabs.addTab(ew,'Events')
        rw=QWidget();rv=QVBoxLayout(rw);rf=QFormLayout();self.event_select=QComboBox();self.member_select=QComboBox();self.status=QComboBox();self.status.addItems(['Confirmed','Pending','Cancelled','Attended']);rf.addRow('Event',self.event_select);rf.addRow('Member',self.member_select);rf.addRow('Status',self.status);rv.addLayout(rf)
        register=QPushButton('ADD / UPDATE ROSTER ENTRY');register.clicked.connect(self.register);rv.addWidget(register)
        self.roster=QTableWidget();self.roster.setColumnCount(5);self.roster.setHorizontalHeaderLabels(['Event','Member','Callsign','Team','Status']);rv.addWidget(self.roster)
        export_roster=QPushButton('EXPORT ROSTER CSV');export_roster.clicked.connect(self.export_roster);rv.addWidget(export_roster);tabs.addTab(rw,'Rosters')
        tabs.currentChanged.connect(lambda _:self.refresh())
        self.refresh()
    def refresh(self):
        self._fill(self.members,self.conn.execute('SELECT id,name,callsign,team,notes FROM members ORDER BY name').fetchall())
        self._fill(self.events,self.conn.execute('SELECT id,name,date,venue FROM events ORDER BY date DESC').fetchall())
        self._fill(self.roster,self.conn.execute('SELECT e.name,m.name,m.callsign,m.team,r.status FROM roster r JOIN members m ON m.id=r.member_id JOIN events e ON e.id=r.event_id ORDER BY e.date DESC,m.name').fetchall())
        self.event_select.clear();self.member_select.clear()
        for id,name in self.conn.execute('SELECT id,name FROM events ORDER BY date DESC'):self.event_select.addItem(name,id)
        for id,name in self.conn.execute('SELECT id,name FROM members ORDER BY name'):self.member_select.addItem(name,id)
    def _fill(self,table,rows):
        table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            for j,value in enumerate(row):table.setItem(i,j,QTableWidgetItem(str(value if value is not None else '')))
        table.resizeColumnsToContents()
    def add_member(self):
        if not self.name.text().strip():return QMessageBox.warning(self,'Member','Name required.')
        self.conn.execute('INSERT INTO members(name,callsign,team,notes) VALUES(?,?,?,?)',(self.name.text().strip(),self.callsign.text().strip(),self.team.currentText().strip(),self.notes.text().strip()));self.conn.commit();self.name.clear();self.callsign.clear();self.notes.clear();self.refresh()
    def delete_member(self):
        row=self.members.currentRow()
        if row<0:return
        id=int(self.members.item(row,0).text())
        if QMessageBox.question(self,'Delete member','Permanently delete this member and their roster entries?')!=QMessageBox.StandardButton.Yes:return
        self.conn.execute('DELETE FROM members WHERE id=?',(id,));self.conn.commit();self.refresh()
    def add_event(self):
        if not self.event_name.text().strip() or not self.event_date.text().strip():return QMessageBox.warning(self,'Event','Event name and date required.')
        self.conn.execute('INSERT INTO events(name,date,venue) VALUES(?,?,?)',(self.event_name.text().strip(),self.event_date.text().strip(),self.venue.text().strip()));self.conn.commit();self.refresh()
    def register(self):
        event=self.event_select.currentData();member=self.member_select.currentData()
        if event is None or member is None:return QMessageBox.warning(self,'Roster','Create an event and member first.')
        self.conn.execute('INSERT INTO roster(event_id,member_id,status) VALUES(?,?,?) ON CONFLICT(event_id,member_id) DO UPDATE SET status=excluded.status',(event,member,self.status.currentText()));self.conn.commit();self.refresh()
    def _export(self,headers,query,default):
        path,_=QFileDialog.getSaveFileName(self,'Export CSV',str(Path.home()/default),'CSV (*.csv)')
        if not path:return
        with open(path,'w',newline='',encoding='utf-8-sig') as f:
            writer=csv.writer(f);writer.writerow(headers);writer.writerows(self.conn.execute(query).fetchall())
    def export_members(self):self._export(['ID','Name','Callsign','Team','Notes'],'SELECT id,name,callsign,team,notes FROM members ORDER BY name','aos_members.csv')
    def export_roster(self):self._export(['Event','Date','Member','Callsign','Team','Status'], 'SELECT e.name,e.date,m.name,m.callsign,m.team,r.status FROM roster r JOIN events e ON e.id=r.event_id JOIN members m ON m.id=r.member_id ORDER BY e.date,m.name','aos_roster.csv')
    def closeEvent(self,event):self.conn.close();super().closeEvent(event)
