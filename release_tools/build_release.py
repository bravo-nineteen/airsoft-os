#!/usr/bin/env python3
"""Build and Ed25519-sign a release from local code using a private PEM key.
Never check the signing key into GitHub.
"""
import argparse, base64, hashlib, json, sys, zipfile
from pathlib import Path
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from aos_apply_update import FILES,validate_zip

def build(root, destination, signing_key):
    root=Path(root); destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    version=(root/'VERSION').read_text().strip()
    package=destination/'aos-update.zip'
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
        for f in sorted(root.iterdir()):
            if f.is_file() and f.name in FILES: z.write(f,f.name)
        for f in sorted((root/'assets').glob('*')):
            if f.is_file() and f.suffix.lower() in ('.png','.jpg','.jpeg','.webp','.svg'):
                z.write(f,'assets/'+f.name)
    validate_zip(package)
    payload=json.dumps({'schema':1,'version':version,'sha256':hashlib.sha256(package.read_bytes()).hexdigest()},separators=(',',':'),sort_keys=True).encode()
    (destination/'aos-manifest.json').write_bytes(payload)
    key=load_pem_private_key(Path(signing_key).read_bytes(),password=None)
    if not isinstance(key,Ed25519PrivateKey): raise ValueError('Key must be Ed25519 PEM')
    (destination/'aos-manifest.sig').write_text(base64.b64encode(key.sign(payload)).decode()+'\n')
    print('Built and signed v'+version+' at '+str(destination))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('out');p.add_argument('--signing-key',required=True)
    a=p.parse_args();build(a.source,a.out,a.signing_key)
