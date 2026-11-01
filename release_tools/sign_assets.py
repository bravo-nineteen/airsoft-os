#!/usr/bin/env python3
"""Sign prebuilt offline release assets without rebuilding the ZIP.

Store the private key outside the repository. Signature is base64 Ed25519.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key


def sign(folder, private_key):
    folder = Path(folder).resolve()
    private_key = Path(private_key).expanduser().resolve()
    if folder in private_key.parents:
        raise ValueError('Signing key must be stored OUTSIDE the assets folder')
    manifest_path = folder / 'aos-manifest.json'
    bundle_path = folder / 'aos-update.zip'
    manifest = manifest_path.read_bytes()
    record = json.loads(manifest)
    digest = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    if record.get('sha256') != digest:
        raise ValueError('Update ZIP does not match manifest SHA-256')
    if record.get('schema') != 1:
        raise ValueError('Unsupported release schema')
    key = load_pem_private_key(private_key.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError('Signing key must be Ed25519')
    signature = base64.b64encode(key.sign(manifest)).decode('ascii') + '\n'
    target = folder / 'aos-manifest.sig'
    target.write_text(signature)
    print('Signed v' + record['version'] + ': ' + str(target))
    print('Upload exactly: aos-update.zip, aos-manifest.json, aos-manifest.sig')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sign AOS release assets offline')
    parser.add_argument('assets_folder')
    parser.add_argument('--signing-key', required=True)
    args = parser.parse_args()
    sign(args.assets_folder, args.signing_key)
