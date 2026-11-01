import base64, hashlib, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import aos_github

class UpdateTests(unittest.TestCase):
    def test_repo_validation(self):
        self.assertEqual(aos_github.validate_repo('team/aos'), 'team/aos')
        for repo in ('../bad','team/aos/other','team//aos','-team/aos'):
            with self.assertRaises(ValueError): aos_github.validate_repo(repo)
    def test_signed_stage_and_reject_tamper(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); key=Ed25519PrivateKey.generate()
            pub=root/'key.pem'; pub.write_bytes(key.public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo))
            bundle=b'AOS example bundle'; manifest=json.dumps({'schema':1,'version':'3.4','sha256':hashlib.sha256(bundle).hexdigest()}).encode()
            blobs={'aos-update.zip':bundle,'aos-manifest.json':manifest,'aos-manifest.sig':base64.b64encode(key.sign(manifest))}
            config={'repo':'team/aos','channel':'stable','public_key':str(pub)}
            rel={'tag_name':'v3.4','assets':[{'name':name,'browser_download_url':'https://github.com/team/aos/releases/download/v3.4/'+name} for name in blobs]}
            def fake_download(url,path,limit): Path(path).write_bytes(blobs[url.split('/')[-1]])
            with patch.object(aos_github,'release',return_value=rel),patch.object(aos_github,'download',side_effect=fake_download):
                info,folder=aos_github.stage(config,root/'staged')
                self.assertEqual(info['version'],'3.4');self.assertTrue((folder/'aos-update.zip').exists())
                blobs['aos-update.zip']=b'tampered'
                with self.assertRaises(Exception): aos_github.stage(config,root/'other')
    def test_config(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);key=Ed25519PrivateKey.generate()
            pub=root/'key.pem';pub.write_bytes(key.public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo))
            path=root/'config.json';aos_github.configure('team/aos',pub,path=path)
            self.assertEqual(aos_github.settings(path)['repo'],'team/aos')
if __name__=='__main__': unittest.main()
