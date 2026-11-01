#!/usr/bin/env python3
"""Administrator-only AOS application updater with transactional backups.

AOS packages are signed ZIPs of app content, not arbitrary scripts. No postinstall
scripts execute and system integration files cannot be replaced by remote bundles.
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import zipfile

APP=Path('/opt/aos')
STATE=Path('/var/lib/aos-updates')
TRUST=Path('/etc/aos/trusted-release-key.pem')
MANIFEST='aos-manifest.json'
SIG='aos-manifest.sig'
BUNDLE='aos-update.zip'
# Only these files may be supplied by a remote release. Never update /etc,
# /usr/local/bin, any privilege policy, installer scripts, or .venv.
FILES={
 'main.py','aos_github.py','aos_updates.py','aos_management.py',
 'aos_network.py','aos_network_gui.py','aos_field_sync.py',
 'aos_live.py','aos_live_gui.py','aos_devices.py','aos_release.py',
 'aos_widgets.py','aos_planning.py','team_ops.py','cyber_native.py',
 'requirements.txt','VERSION',
}
MAX_FILES=180
MAX_BYTES=30*1024*1024

def validate_zip(path):
    seen=set(); total=0
    with zipfile.ZipFile(path) as bundle:
        entries=bundle.infolist()
        if len(entries)>MAX_FILES: raise ValueError('Too many ZIP entries')
        for e in entries:
            n=e.filename
            p=Path(n)
            if n in seen: raise ValueError('Duplicate ZIP entry')
            seen.add(n)
            if n.startswith('/') or '\\' in n or '..' in p.parts or p.is_absolute():
                raise ValueError('Invalid ZIP path')
            if n.endswith('/'):
                if n.rstrip('/') != 'assets': raise ValueError('Unexpected directory')
                continue
            if not (n in FILES or n.startswith('assets/') and len(p.parts)==2
                    and p.suffix.lower() in ('.png','.jpg','.jpeg','.svg','.webp')):
                raise ValueError('Unapproved file: '+n)
            mode=(e.external_attr>>16)&0o170000
            if mode not in (0,0o100000): raise ValueError('ZIP special file refused')
            if e.file_size>MAX_BYTES: raise ValueError('Oversized ZIP entry')
            total+=e.file_size
            if total>MAX_BYTES: raise ValueError('ZIP uncompressed too large')
        if not {'main.py','VERSION'}.issubset(seen):
            raise ValueError('Main application or version missing')
        if bundle.read('VERSION').decode().strip()=='' : raise ValueError('Empty version')
    return entries

def install(folder, app=APP, state=STATE, trusted=TRUST):
    from aos_release import verify
    folder=Path(folder).resolve(); app=Path(app); state=Path(state)
    if not trusted.is_file(): raise FileNotFoundError('Trusted public key missing: '+str(trusted))
    for f in (MANIFEST,SIG,BUNDLE):
        if not (folder/f).is_file(): raise FileNotFoundError(str(folder/f))
    info=verify(folder/BUNDLE,folder/MANIFEST,folder/SIG,trusted)
    validate_zip(folder/BUNDLE)
    with zipfile.ZipFile(folder/BUNDLE) as z:
        content_version=z.read('VERSION').decode().strip()
    if content_version!=info['version']: raise ValueError('Version mismatch')
    state.mkdir(mode=0o700,parents=True,exist_ok=True)
    with open(state/'update.lock','a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        # Cannot preserve a functioning app if there is nothing currently installed.
        if not (app/'main.py').is_file(): raise FileNotFoundError('AOS not installed')
        backups=state/'backups';backups.mkdir(mode=0o700,exist_ok=True)
        stamp=time.strftime('%Y%m%d-%H%M%S')
        backup=backups/(stamp+'-'+info['version'].replace('/','_'))
        if backup.exists(): raise FileExistsError(str(backup))
        with tempfile.TemporaryDirectory(prefix='.aos-prepare-',dir=state) as tmp:
            prepared=Path(tmp)
            with zipfile.ZipFile(folder/BUNDLE) as z:
                for e in z.infolist():
                    if e.is_dir(): continue
                    dest=prepared/e.filename
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    with z.open(e) as source, open(dest,'wb') as target: shutil.copyfileobj(source,target)
            # Snapshot app code and assets, never user databases or venv.
            backup.mkdir(mode=0o700)
            current=[]
            for f in app.iterdir():
                if f.name in FILES or f.name=='assets':
                    if f.is_symlink(): raise ValueError('Unexpected symlink in installed app')
                    target=backup/f.name
                    if f.is_dir(): shutil.copytree(f,target,symlinks=False)
                    else: shutil.copy2(f,target)
                    current.append(f.name)
            (backup/'_backup_meta.json').write_text(json.dumps({'files':current,'version':info['version']}))
            try:
                for f in prepared.iterdir():
                    dest=app/f.name
                    if dest.is_symlink(): raise ValueError('Target is symlink')
                    if f.is_dir():
                        staged=app/('.assets.new.'+str(os.getpid()))
                        if staged.exists(): shutil.rmtree(staged)
                        shutil.copytree(f,staged)
                        old=app/('.assets.old.'+str(os.getpid()))
                        if dest.exists(): os.replace(dest,old)
                        os.replace(staged,dest)
                        if old.exists(): shutil.rmtree(old)
                    else:
                        staged=app/('.'+f.name+'.new.'+str(os.getpid()))
                        shutil.copy2(f,staged)
                        os.chmod(staged,0o644)
                        os.replace(staged,dest)
            except Exception:
                restore(backup,app)
                raise
        return backup

def restore(backup,app=APP):
    backup=Path(backup); app=Path(app)
    meta=json.loads((backup/'_backup_meta.json').read_text())
    for name in meta['files']:
        original=backup/name; target=app/name
        if original.is_dir():
            if target.exists(): shutil.rmtree(target)
            shutil.copytree(original,target)
        else: shutil.copy2(original,target)
    return meta

def rollback(backup,app=APP,state=STATE):
    backup=Path(backup).resolve(); root=(Path(state)/'backups').resolve()
    if root not in backup.parents: raise ValueError('Backup path outside protected backup directory')
    with open(Path(state)/'update.lock','a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return restore(backup,app)

def main():
    p=argparse.ArgumentParser(description='Administrator-authorised AOS updater')
    sub=p.add_subparsers(dest='action',required=True)
    sub.add_parser('install').add_argument('staged_folder')
    sub.add_parser('rollback').add_argument('backup_directory')
    a=p.parse_args()
    if os.geteuid()!=0: p.error('Run with sudo/root')
    if a.action=='install':
        backup=install(a.staged_folder)
        print('Installed verified application update. Restart AOS session to apply.')
        print('Rollback: sudo python3 /opt/aos/aos_apply_update.py rollback',backup)
    else:
        rollback(a.backup_directory);print('Rollback restored. Restart AOS session.')
if __name__=='__main__':main()
