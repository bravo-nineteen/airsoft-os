"""Verify signed AOS update bundles before administrator-managed installation.
No unattended installation or root commands are implemented.
"""
import base64
import hashlib
import json
from pathlib import Path


def verify(bundle, manifest, signature, public_key_pem):
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
    except ImportError as exc:
        raise RuntimeError('Install cryptography to verify signed releases') from exc
    payload=Path(manifest).read_bytes()
    key=load_pem_public_key(Path(public_key_pem).read_bytes())
    if not isinstance(key,Ed25519PublicKey):raise ValueError('Expected Ed25519 public key')
    key.verify(base64.b64decode(Path(signature).read_text().strip(),validate=True),payload)
    info=json.loads(payload)
    if info.get('schema')!=1 or not isinstance(info.get('version'),str):raise ValueError('Invalid manifest')
    if info.get('sha256')!=hashlib.sha256(Path(bundle).read_bytes()).hexdigest():raise ValueError('Bundle hash mismatch')
    return info

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description='Verify a signed AOS release bundle (does not install it)')
    for name in ('bundle','manifest','signature','public_key'):parser.add_argument(name)
    a=parser.parse_args();print(json.dumps(verify(a.bundle,a.manifest,a.signature,a.public_key),indent=2))
