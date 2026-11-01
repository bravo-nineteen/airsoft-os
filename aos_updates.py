"""GitHub Release updater front-end (no privileged installation)."""
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit
from aos_github import settings, release, asset_urls, stage

class Worker(QThread):
    finished_text=Signal(str)
    def __init__(self, mode, parent=None): super().__init__(parent); self.mode=mode
    def run(self):
        try:
            data=settings()
            if self.mode=='check':
                r=release(data); asset_urls(r)
                message='GitHub release: '+str(r.get('tag_name'))+'\nSigned package not yet downloaded or verified.'
            else:
                info,path=stage(data,__import__('pathlib').Path.home()/'Downloads'/'AOS-Updates')
                message='Signature and SHA-256 VERIFIED\nVersion: '+info['version']+'\nSaved: '+str(path)+'\n\nAdministrator approval required to install. Run the following on the Toughbook:\n  sudo /opt/aos/.venv/bin/python /opt/aos/aos_apply_update.py install ' + str(path) + ''
        except Exception as exc: message='Update operation failed: '+str(exc)
        self.finished_text.emit(message)

class UpdateChecker(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent); self.setWindowTitle('AOS 3.9 // UPDATE & HEALTH CENTRE'); self.resize(630,370)
        self.setStyleSheet('QDialog,QWidget{background:#10191b;color:#e6f2ee} QTextEdit{background:#112326;color:#e6f2ee;border:1px solid #52696b;padding:8px} QPushButton{background:#273e42;color:#f0f7f5;padding:9px}')
        l=QVBoxLayout(self)
        l.addWidget(QLabel('GITHUB RELEASES / SIGNED UPDATE PACKAGES'))
        l.addWidget(QLabel('Configure repository and trusted signing key in Terminal first.'))
        self.check_btn=QPushButton('CHECK GITHUB RELEASES'); self.check_btn.clicked.connect(lambda:self.run_task('check')); l.addWidget(self.check_btn)
        self.download_btn=QPushButton('DOWNLOAD AND VERIFY (DO NOT INSTALL)'); self.download_btn.clicked.connect(lambda:self.run_task('download')); l.addWidget(self.download_btn)
        self.doctor_btn=QPushButton('RUN LOCAL DIAGNOSTICS')
        self.doctor_btn.clicked.connect(self.run_diagnostics)
        l.addWidget(self.doctor_btn)
        self.output=QTextEdit(); self.output.setReadOnly(True)
        self.output.setPlainText('Run: /opt/aos/.venv/bin/python /opt/aos/aos_github.py configure OWNER/REPO /path/to/trusted-public-key.pem\n\nDownloaded packages are checked against the trusted signing key. Administrator approval is required for installation.')
        l.addWidget(self.output)
        self.worker=None
    def run_diagnostics(self):
        from aos_doctor import examine, report_text
        self.output.setPlainText(report_text(examine()))

    def run_task(self,mode):
        if self.worker and self.worker.isRunning(): return
        self.check_btn.setEnabled(False); self.download_btn.setEnabled(False)
        self.output.setPlainText('Contacting GitHub...')
        self.worker=Worker(mode,self)
        self.worker.finished_text.connect(self.output.setPlainText)
        self.worker.finished.connect(lambda:(self.check_btn.setEnabled(True),self.download_btn.setEnabled(True)))
        self.worker.start()
    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():
            event.ignore(); self.output.append('Wait for the current download/check to finish.')
        else: super().closeEvent(event)
