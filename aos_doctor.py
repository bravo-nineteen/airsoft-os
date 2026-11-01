"""AOS system diagnostics. Never changes the OS. CLI: python3 aos_doctor.py"""
import argparse
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def examine(root=ROOT, home=None):
    root=Path(root)
    home=Path(home) if home is not None else Path.home()
    details=[]
    def add(name, ok, detail):
        details.append({'check':name,'ok':bool(ok),'detail':str(detail)})
    v=root/'VERSION'
    add('Application files', (root/'main.py').is_file() and v.is_file(), 'Version '+(v.read_text().strip() if v.is_file() else 'missing'))
    add('AOS logo', (root/'assets'/'aos_logo.jpg').is_file(), 'AOS logo asset')
    add('Python runtime', True, platform.python_version())
    try:
        from PySide6 import QtCore
        add('PySide6', True, QtCore.__version__)
    except ImportError:
        add('PySide6', False, 'Not available in current Python environment')
    add('Desktop session', Path('/usr/share/xsessions/aos-session.desktop').is_file(), 'AOS X session installed')
    add('Openbox', bool(shutil.which('openbox')), 'Window manager executable')
    add('Thunar', bool(shutil.which('thunar')), 'File manager executable')
    add('Network Manager', bool(shutil.which('nmcli')), 'Network Manager command line')
    cfg=home/'.config/aos/github-updates.json'
    if cfg.is_file():
        try:
            d=json.loads(cfg.read_text()); key=Path(d.get('public_key',''))
            add('GitHub config',d.get('repo')=='bravo-nineteen/airsoft-os' and key.is_file(),
                'Configured repo: '+str(d.get('repo','?'))+'; public key present: '+str(key.is_file()))
        except (ValueError, OSError) as exc:add('GitHub config',False,type(exc).__name__)
    else:add('GitHub config',False,'Not yet configured')
    return details

def report_text(items):
    lines=['AOS SYSTEM DIAGNOSTICS','----------------------']
    for x in items:lines.append(('PASS' if x['ok'] else 'CHECK')+'  '+x['check']+' — '+x['detail'])
    return '\n'.join(lines)

def main():
    p=argparse.ArgumentParser();p.add_argument('--json',action='store_true');args=p.parse_args()
    results=examine()
    print(json.dumps({'checks':results},indent=2) if args.json else report_text(results))
    # Missing optional software is not a failure of the report itself.
if __name__=='__main__':main()
