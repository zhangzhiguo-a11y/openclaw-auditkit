#!/usr/bin/env python3
from pathlib import Path
import hashlib, os, shutil, time, urllib.request, zipfile

BASE_SHA='59afcf3b2ddb7b6195645640ddc484329b01a90763762dd1c12c4b704e939fa6'
TAIL_SHA='fe67b28cec1ef3983b7454f5d172e673056ec02c56eef8109b48899a863b9f6c'
FINAL_SHA='10a30f37731f30dc922707edb15e385451a3929dbafec7c62f54cf4856a83109'
PREFIX=82927508
TAIL_URLS=[
 'https://raw.githubusercontent.com/zhangzhiguo-a11y/openclaw-auditkit/9191ea2a20c72bfcfc46b73cf4fe0200c8b3c891/downloads/v154/LingoBunny-V1.5.4-tail-from-v153.bin',
 'https://cdn.jsdelivr.net/gh/zhangzhiguo-a11y/openclaw-auditkit@9191ea2a20c72bfcfc46b73cf4fe0200c8b3c891/downloads/v154/LingoBunny-V1.5.4-tail-from-v153.bin',
]

home=Path.home();root=home/'.lingo-bunny'/'app-v1.3.2';web=root/'web';download=web/'download';data_dir=home/'.lingo-bunny'/'data'
base=download/'LingoBunny-V1.5.3-Android-MultiKid-Sync-FINAL.apk'
target=download/'LingoBunny-V1.5.4-Android-MultiKid-Sync-Review-FINAL.apk'
tail=download/'.LingoBunny-V1.5.4-tail.bin'

def sha256(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def download_with_retry(urls,dst):
 last=None
 for url in urls:
  for attempt in range(1,6):
   try:
    req=urllib.request.Request(url,headers={'User-Agent':'LingoBunny-V154-Updater/1.0'})
    with urllib.request.urlopen(req,timeout=45) as r, open(dst,'wb') as out:shutil.copyfileobj(r,out,1024*1024)
    return url
   except Exception as e:
    last=e
    try:dst.unlink()
    except FileNotFoundError:pass
    print(f'download retry {attempt}/5: {type(e).__name__}: {e}')
    time.sleep(min(2*attempt,8))
 raise RuntimeError(f'tail download failed: {last}')

print('=== Lingo Bunny V1.5.4 updater ===')
print('DB_PROTECTED='+str(data_dir/'lingo_bunny.db'))
if not web.is_dir():raise SystemExit('ERROR: web root missing: '+str(web))
download.mkdir(parents=True,exist_ok=True)

candidates=[base]+sorted(download.glob('LingoBunny-V1.5.3*.apk'))
base_ok=None
for p in candidates:
 if p.exists() and p.is_file():
  s=sha256(p);print(f'BASE_CANDIDATE={p.name} SHA256={s}')
  if s==BASE_SHA:base_ok=p;break
if base_ok is None:raise SystemExit('ERROR: exact V1.5.3 base APK not found; no files changed')

used=download_with_retry(TAIL_URLS,tail);ts=sha256(tail);print('TAIL_SOURCE='+used);print('TAIL_SHA256='+ts)
if ts!=TAIL_SHA:
 tail.unlink(missing_ok=True);raise SystemExit('ERROR: tail SHA256 mismatch; no files changed')

tmp=download/'.LingoBunny-V1.5.4-building.apk'
with open(base_ok,'rb') as src, open(tmp,'wb') as out:
 remaining=PREFIX
 while remaining:
  b=src.read(min(1024*1024,remaining))
  if not b:raise SystemExit('ERROR: base APK shorter than expected')
  out.write(b);remaining-=len(b)
 with open(tail,'rb') as tf:shutil.copyfileobj(tf,out,1024*1024)
fs=sha256(tmp);print('FINAL_SHA256='+fs)
if fs!=FINAL_SHA:
 tmp.unlink(missing_ok=True);tail.unlink(missing_ok=True);raise SystemExit('ERROR: rebuilt V1.5.4 SHA mismatch; no web files changed')

with zipfile.ZipFile(tmp,'r') as z:
 bad=z.testzip()
 if bad:raise SystemExit('ERROR: APK zip validation failed at '+bad)
 required={'AndroidManifest.xml','assets/www/index.html','assets/www/v154-data-review.js','assets/www/wish-v152.js','assets/www/sw.js','assets/www/android-release-v152.js','assets/www/manifest.json','assets/www/sync-config.js'}
 if not required.issubset(set(z.namelist())):raise SystemExit('ERROR: V1.5.4 required assets missing')
 idx=z.read('assets/www/index.html').decode('utf-8','replace');fix=z.read('assets/www/v154-data-review.js').decode('utf-8','replace');wish=z.read('assets/www/wish-v152.js').decode('utf-8','replace')
 if 'V1.5.4' not in idx or 'consecutiveCorrectRequired:INTENSIVE_STREAK' not in fix or "syncMergeVersion='1.5.4'" not in fix or "w.status='deleted'" not in wish:raise SystemExit('ERROR: V1.5.4 patch markers missing')

stamp=time.strftime('%Y%m%d-%H%M%S');backup=home/'.lingo-bunny'/'backups'/('web-before-v154-'+stamp);backup.mkdir(parents=True,exist_ok=False)
web_files=[
 ('assets/www/index.html','index.html'),('assets/www/android-release-v152.js','android-release-v152.js'),('assets/www/v154-data-review.js','v154-data-review.js'),('assets/www/sw.js','sw.js'),('assets/www/wish-v152.js','wish-v152.js'),('assets/www/manifest.json','manifest.json'),('assets/www/sync-config.js','sync-config.js')]
for _,dst_name in web_files:
 dst=web/dst_name
 if dst.exists():shutil.copy2(dst,backup/dst_name)

os.chmod(tmp,0o644);os.replace(tmp,target)
with zipfile.ZipFile(target,'r') as z:
 for src_name,dst_name in web_files:
  dst=web/dst_name;t=web/('.'+dst_name+'.v154.tmp');t.write_bytes(z.read(src_name));os.chmod(t,0o644);os.replace(t,dst)
tail.unlink(missing_ok=True)
print('BACKUP='+str(backup));print('APK_PATH='+str(target));print('APK_BYTES='+str(target.stat().st_size))

cors='UNKNOWN'
try:
 req=urllib.request.Request('https://lingo.bestresources.cn/api/profile/load',method='OPTIONS',headers={'Origin':'https://appassets.androidplatform.net','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type','User-Agent':'LingoBunny-V154-Updater/1.0'})
 with urllib.request.urlopen(req,timeout=20) as r:
  allow=r.headers.get('Access-Control-Allow-Origin') or '';methods=r.headers.get('Access-Control-Allow-Methods') or '';cors='OK' if (allow=='*' or 'appassets.androidplatform.net' in allow) and 'POST' in methods.upper() else f'BAD_HEADERS origin={allow!r} methods={methods!r}'
except Exception as e:cors=f'ERROR {type(e).__name__}: {e}'
print('CORS_PREFLIGHT='+cors)
url='https://lingo.bestresources.cn/download/LingoBunny-V1.5.4-Android-MultiKid-Sync-Review-FINAL.apk';print('APK_URL='+url)
try:
 req=urllib.request.Request(url,method='HEAD',headers={'User-Agent':'LingoBunny-V154-Updater/1.0'})
 with urllib.request.urlopen(req,timeout=20) as r:print('PUBLIC_HEAD_HTTP='+str(r.status));print('PUBLIC_CONTENT_LENGTH='+str(r.headers.get('Content-Length') or ''))
except Exception as e:print('PUBLIC_HEAD_HTTP=ERROR '+type(e).__name__+': '+str(e))
print('RESULT=V154_READY')
