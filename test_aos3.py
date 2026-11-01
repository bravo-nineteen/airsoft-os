import base64
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from aos_live import connect,read_state,change,allowed,provision,role_for,make_handler
from aos_devices import validate,simulated
from aos_widgets import get

class AOS3Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=connect(Path(self.tmp.name)/'live.db')
    def tearDown(self):
        self.db.close();self.tmp.cleanup()
    def test_game_lifecycle(self):
        state=read_state(self.db)
        state=change(self.db,'gm','configure',state['revision'],title='Domination',duration=180)
        self.assertEqual(state['remaining'],180)
        state=change(self.db,'gm','start',state['revision'])
        state=change(self.db,'gm','score',state['revision'],team='red',delta=1)
        state=change(self.db,'gm','tick',state['revision'],seconds=30)
        self.assertEqual((state['remaining'],state['red']),(150,1))
        state=change(self.db,'gm','pause',state['revision'])
        self.assertEqual(state['status'],'paused')
    def test_conflict(self):
        state=read_state(self.db)
        change(self.db,'gm','start',state['revision'])
        with self.assertRaises(RuntimeError):change(self.db,'gm','pause',state['revision'])
    def test_invalid_input(self):
        state=read_state(self.db)
        with self.assertRaises(ValueError):change(self.db,'gm','configure',state['revision'],title='X',duration=1)
    def test_roles(self):
        self.assertTrue(allowed('gm','start'))
        self.assertFalse(allowed('leader','score'))
        self.assertFalse(allowed('viewer','reset'))
        tokens=provision(Path(self.tmp.name)/'keys'/'tokens.json')
        self.assertEqual(role_for(tokens['gm'],tokens),'gm')
        self.assertIsNone(role_for('invalid',tokens))
    def test_devices(self):
        self.assertEqual(len(simulated()),2)
        with self.assertRaises(ValueError):validate({'device_id':'bad/../','kind':'gateway','battery':100,'online':True})
    def test_widgets(self):
        self.assertEqual(get('game').label,'Game Status')
        self.assertIsNone(get('unknown'))
    def test_signed_release(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
        from aos_release import verify
        d=Path(self.tmp.name);bundle=d/'a.zip';bundle.write_bytes(b'test bundle')
        manifest=d/'manifest.json';manifest.write_text(json.dumps({'schema':1,'version':'3.0','sha256':hashlib.sha256(bundle.read_bytes()).hexdigest()}))
        private=Ed25519PrivateKey.generate();key=d/'public.pem';key.write_bytes(private.public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo))
        sig=d/'signature.txt';sig.write_text(base64.b64encode(private.sign(manifest.read_bytes())).decode())
        self.assertEqual(verify(bundle,manifest,sig,key)['version'],'3.0')
        bundle.write_bytes(b'tampered')
        with self.assertRaises(ValueError):verify(bundle,manifest,sig,key)

if __name__=='__main__':unittest.main()
