"""GitHub Releases update retrieval. Downloads are never executed automatically."""
import argparse
import json
import os
import re
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
from aos_release import verify

CONFIG = Path.home() / '.config' / 'aos' / 'github-updates.json'
MAX_MANIFEST = 16_384
MAX_BUNDLE = 150 * 1024 * 1024
REPO_RE = re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')
ASSETS = {'manifest': 'aos-manifest.json', 'signature': 'aos-manifest.sig', 'bundle': 'aos-update.zip'}

def validate_repo(repo):
    if not REPO_RE.fullmatch(repo) or '..' in repo or repo.startswith('-'):
        raise ValueError('Expected GitHub owner/repository')
    return repo

def configure(repo, public_key, channel='stable', path=CONFIG):
    validate_repo(repo)
    if channel not in ('stable', 'beta', 'development'):
        raise ValueError('Unknown channel')
    key = Path(public_key).expanduser().resolve()
    if not key.is_file() or key.stat().st_size > 8192:
        raise ValueError('A local Ed25519 public key PEM is required')
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    if not isinstance(load_pem_public_key(key.read_bytes()), Ed25519PublicKey):
        raise ValueError('Expected Ed25519 public key')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps({'repo': repo, 'channel': channel, 'public_key': str(key)}, indent=2))
    os.chmod(tmp, 0o600)
    tmp.replace(path)
    return path

def settings(path=CONFIG):
    data=json.loads(Path(path).read_text())
    validate_repo(data['repo'])
    if data['channel'] not in ('stable','beta','development'):
        raise ValueError('Invalid channel')
    return data

def get_json(url):
    req=urllib.request.Request(url,headers={'Accept':'application/vnd.github+json','User-Agent':'AOS-Updater/3.6','X-GitHub-Api-Version':'2022-11-28'})
    with urllib.request.urlopen(req, timeout=15) as r:
        data=r.read(512_001)
        if len(data)>512_000: raise ValueError('GitHub response too large')
        return json.loads(data)

def release(data):
    repo=data['repo']; channel=data['channel']
    api='https://api.github.com/repos/'+repo+'/releases'
    if channel=='stable':
        result=get_json(api+'/latest')
        if result.get('draft') or result.get('prerelease'):
            raise ValueError('Not a stable release')
        return result
    for item in get_json(api+'?per_page=30'):
        if item.get('draft'): continue
        if channel=='beta' and item.get('prerelease'): return item
        if channel=='development': return item
    raise ValueError('No release found for selected channel')

def asset_urls(rel):
    assets={x['name']: x['browser_download_url'] for x in rel.get('assets', [])}
    result={}
    for kind,name in ASSETS.items():
        if name not in assets: raise ValueError('Missing release asset: '+name)
        url=assets[name]; p=urlparse(url)
        if p.scheme!='https' or p.hostname!='github.com' or p.username or p.password:
            raise ValueError('Unexpected asset URL')
        result[kind]=url
    return result

def download(url, path, limit):
    req=urllib.request.Request(url,headers={'User-Agent':'AOS-Updater/3.6'})
    total=0
    with urllib.request.urlopen(req, timeout=30) as r, open(path,'wb') as f:
        if urlparse(r.url).scheme!='https': raise ValueError('Insecure redirect')
        while True:
            block=r.read(1024*1024)
            if not block: break
            total+=len(block)
            if total>limit: raise ValueError('Download exceeds size limit')
            f.write(block)

def stage(data, destination):
    rel=release(data)
    urls=asset_urls(rel)
    dest=Path(destination).expanduser().resolve()
    dest.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.aos-stage-',dir=dest) as tmp:
        tmp=Path(tmp)
        for kind,url in urls.items():
            download(url,tmp/ASSETS[kind],MAX_BUNDLE if kind=='bundle' else MAX_MANIFEST)
        verified=verify(tmp/ASSETS['bundle'],tmp/ASSETS['manifest'],tmp/ASSETS['signature'],data['public_key'])
        # Verify release tag and signed manifest version refer to the same release.
        tag=str(rel.get('tag_name','')).removeprefix('v')
        if verified['version']!=tag: raise ValueError('Signed version does not match GitHub tag')
        import shutil
        final=dest/('AOS-'+verified['version'])
        if final.exists(): raise FileExistsError('Already staged: '+str(final))
        shutil.copytree(tmp,final)
        return verified,final

def main():
    p=argparse.ArgumentParser(description='AOS GitHub updater: verify and stage only; no installation')
    sub=p.add_subparsers(dest='action',required=True)
    c=sub.add_parser('configure'); c.add_argument('repo'); c.add_argument('public_key'); c.add_argument('--channel',choices=['stable','beta','development'],default='stable')
    sub.add_parser('check')
    d=sub.add_parser('download'); d.add_argument('--destination',default=str(Path.home()/'Downloads'/'AOS-Updates'))
    a=p.parse_args()
    if a.action=='configure': print('Saved:',configure(a.repo,a.public_key,a.channel))
    elif a.action=='check':
        r=release(settings()); print('Latest:',r.get('tag_name')); print('Assets:', ', '.join(asset_urls(r)))
        print('This is release metadata only; cryptographic verification happens during download.')
    else:
        info,folder=stage(settings(),a.destination)
        print('Verified and staged:',info['version'],folder)
        print('NOT INSTALLED. Review and deploy with an administrator-controlled release process.')
if __name__=='__main__': main()
