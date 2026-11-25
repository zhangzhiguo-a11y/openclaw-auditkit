#!/usr/bin/env python3
"""Lingo Bunny V1.5.5 HF1: social-only hotfix. Does not edit learning DB."""
from pathlib import Path
import base64,hashlib,os,plistlib,py_compile,shutil,sqlite3,subprocess,tempfile,time,urllib.request,urllib.error,zipfile,zlib,json

ROOT=Path.home()/'.lingo-bunny'
APP=ROOT/'app-v1.3.2'
WEB=APP/'web'
DOWNLOAD=WEB/'download'
MAIN_SERVER=APP/'server.py'
SOCIAL=APP/'lingo_social_api.py'
SOCIAL_DB=ROOT/'data'/'lingo_social.db'
LEARNING_DB=ROOT/'data'/'lingo_bunny.db'
BASE=DOWNLOAD/'LingoBunny-V1.5.5-Android-MultiKid-SafeSync-Review-FINAL.apk'
TARGET=DOWNLOAD/'LingoBunny-V1.5.5-HF1-Android-OnlineFix-FINAL.apk'
BASE_SHA='b1589eb1ec5362852872270cee60360ab5536f3c2d1177aab553e8fe9001c41c'
PREFIX=83972474
PREFIX_SHA='197f19054649451053f223c7a16a917863bc65043d755dfd3826f5a7f0dad809'
TAIL_SHA='6f8590e0a16a9033f11d6fdf94d069f4b2424c255d3ac532039a562cc20a990e'
FINAL_SHA='ad1c6b93ffc84d18941b6df3280f9303a73ce400d841582ce99fa16361ca48c2'
FINAL_BYTES=84075419
PREVIOUS_SOCIAL_SHA='9e6b9527b6d78c45080516b2456f192d58aea0de43700007386d9bd69ca3de38'
NEW_SOCIAL_SHA='0469754a28209bfcf019ad21fca91d8862d1fa7033cec03bad1cfd5f0a1eed42'
SOURCE_COMPRESSED_B64='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'
TAIL_URLS=[
 'https://raw.githubusercontent.com/zhangzhiguo-a11y/openclaw-auditkit/c2ecd09823f45a9881be9f7b802f4876128af3a1/downloads/v155-hf1/LingoBunny-V1.5.5-HF1-tail-from-v155.bin',
 'https://cdn.jsdelivr.net/gh/zhangzhiguo-a11y/openclaw-auditkit@c2ecd09823f45a9881be9f7b802f4876128af3a1/downloads/v155-hf1/LingoBunny-V1.5.5-HF1-tail-from-v155.bin',
]
def sha256(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def fetch(urls,dst):
 last=None
 for url in urls:
  for attempt in range(1,4):
   try:
    req=urllib.request.Request(url,headers={'User-Agent':'LingoBunny-V155-HF1/1.0'})
    with urllib.request.urlopen(req,timeout=35) as r,open(dst,'wb') as o:shutil.copyfileobj(r,o,1024*1024)
    return url
   except Exception as e:
    last=e
    try:dst.unlink()
    except FileNotFoundError:pass
    print('DOWNLOAD_RETRY',attempt,type(e).__name__,str(e)[:130])
    time.sleep(attempt*2)
 raise RuntimeError('Unable to download signed patch: '+str(last))
def launch_label():
 for p in sorted((Path.home()/'Library/LaunchAgents').glob('*.plist')):
  try:
   with p.open('rb') as f:j=plistlib.load(f)
   args=' '.join(str(x) for x in j.get('ProgramArguments',[]))
   if 'lingo-bunny' in args and ('server.py' in args or '8792' in args):return j.get('Label') or 'com.bestresources.lingobunny'
  except Exception:pass
 return 'com.bestresources.lingobunny'
def restart():
 label=launch_label()
 print('LAUNCH_LABEL='+label)
 r=subprocess.run(['launchctl','kickstart','-k',f'gui/{os.getuid()}/{label}'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 if r.returncode:raise RuntimeError('launchctl kickstart: '+r.stdout.strip())
 for _ in range(20):
  try:
   with urllib.request.urlopen('http://127.0.0.1:8792/',timeout=3) as response:
    if response.status==200:return
  except Exception:time.sleep(.5)
 raise RuntimeError('Local server health check failed')
def check_social():
 req=urllib.request.Request('http://127.0.0.1:8792/api/social/online',data=json.dumps({'player_id':'hf1-test-id','secret':'not-a-real-secret'}).encode(),headers={'Content-Type':'application/json'},method='POST')
 try:
  with urllib.request.urlopen(req,timeout=6):pass
 except urllib.error.HTTPError as e:
  if e.code==401:
   data=json.loads(e.read().decode())
   if data.get('error')=='unauthorized':return True
  raise
 return False

print('=== Lingo Bunny V1.5.5 HF1 social-only updater ===')
for p in (APP,WEB,BASE,SOCIAL,MAIN_SERVER,LEARNING_DB):
 if not p.exists():raise SystemExit('ERROR: required path missing: '+str(p))
if sha256(BASE)!=BASE_SHA:raise SystemExit('ERROR: expected V1.5.5 APK not found; no files changed')
server_text=MAIN_SERVER.read_text(encoding='utf-8')
if 'LINGO_V140_SOCIAL_HOOK' not in server_text or 'merge": "v1.5.5-server"' not in server_text:
 raise SystemExit('ERROR: main server differs from V1.5.5; no files changed')
old_social_sha=sha256(SOCIAL)
if old_social_sha not in (PREVIOUS_SOCIAL_SHA,NEW_SOCIAL_SHA):
 raise SystemExit('ERROR: social module differs from known baseline: '+old_social_sha+'; no files changed')
source=zlib.decompress(base64.b64decode(SOURCE_COMPRESSED_B64))
if hashlib.sha256(source).hexdigest()!=NEW_SOCIAL_SHA:raise SystemExit('ERROR: social patch hash mismatch; no files changed')
compile(source.decode('utf-8'),'lingo_social_api.py','exec')
print('SOCIAL_PREFLIGHT=OK')
# APK patch is a signed delta from the exact V1.5.5 APK, not from the learning database.
DOWNLOAD.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(dir=DOWNLOAD,prefix='.hf1-build-') as td:
 td=Path(td);tail=td/'patch.bin';temp_apk=td/'patched.apk'
 source_url=fetch(TAIL_URLS,tail)
 if sha256(tail)!=TAIL_SHA:raise SystemExit('ERROR: signed patch SHA mismatch; no files changed')
 print('TAIL_SOURCE='+source_url)
 with BASE.open('rb') as src,temp_apk.open('wb') as dst:
  remaining=PREFIX;h=hashlib.sha256()
  while remaining:
   b=src.read(min(1024*1024,remaining))
   if not b:raise RuntimeError('base APK truncated')
   dst.write(b);h.update(b);remaining-=len(b)
  if h.hexdigest()!=PREFIX_SHA:raise RuntimeError('base APK common prefix mismatch')
  with tail.open('rb') as f:shutil.copyfileobj(f,dst,1024*1024)
 if temp_apk.stat().st_size!=FINAL_BYTES or sha256(temp_apk)!=FINAL_SHA:
  raise SystemExit('ERROR: final APK SHA mismatch; no files changed')
 with zipfile.ZipFile(temp_apk) as z:
  if z.testzip():raise RuntimeError('APK ZIP CRC failed')
  files={}
  for name in ['index.html','social-v151.js','sw.js']:
   files[name]=z.read('assets/www/'+name)
  if b'v=1.5.5-hf1' not in files['index.html'] or b'learner_key' not in files['social-v151.js'] or b'v1.5.5-hf1-online' not in files['sw.js']:
   raise RuntimeError('APK social patch markers missing')
 print('APK_PREFLIGHT=OK SHA256='+FINAL_SHA)
 # From here only social module, UI shell, and separate APK filename are changed.
 stamp=time.strftime('%Y%m%d-%H%M%S')
 backup=ROOT/'backups'/('v155-hf1-social-before-'+stamp)
 backup.mkdir(parents=True,exist_ok=False)
 shutil.copy2(SOCIAL,backup/'lingo_social_api.py')
 for name in files:
  p=WEB/name
  if p.is_file():shutil.copy2(p,backup/name)
 if SOCIAL_DB.exists():
  with sqlite3.connect(SOCIAL_DB,timeout=15) as c,sqlite3.connect(backup/'lingo_social.db') as dst:c.backup(dst)
 print('BACKUP='+str(backup))
 print('LEARNING_DB_PROTECTED='+str(LEARNING_DB))
 replaced=[]
 try:
  update={SOCIAL:source,**{WEB/k:v for k,v in files.items()}}
  for dest,data in update.items():
   target_tmp=dest.with_name('.'+dest.name+'.hf1.tmp')
   target_tmp.write_bytes(data)
   os.chmod(target_tmp,dest.stat().st_mode & 0o777 if dest.exists() else 0o644)
   os.replace(target_tmp,dest)
   replaced.append(dest)
  os.chmod(temp_apk,0o644)
  os.replace(temp_apk,TARGET)
  restart()
  if not check_social():raise RuntimeError('online endpoint did not return authenticated 401')
 except Exception as error:
  # Code-only rollback; never touch the learning DB or social history.
  for dest in reversed(replaced):
   original=backup/dest.name
   if original.exists():shutil.copy2(original,dest)
  try:restart()
  except Exception as e:print('ROLLBACK_SERVER_WARNING='+str(e))
  raise SystemExit('ERROR: failed and reverted code files: '+str(error))
 print('LOCAL_SERVER_HTTP=200')
 print('LOCAL_SOCIAL_ROUTE=401_EXPECTED')
 print('SOCIAL_PATCH_SHA256='+sha256(SOCIAL))
 print('APK_PATH='+str(TARGET))
 print('APK_BYTES='+str(TARGET.stat().st_size))
 print('APK_SHA256='+sha256(TARGET))
 url='https://lingo.bestresources.cn/download/'+TARGET.name
 print('APK_URL='+url)
 try:
  req=urllib.request.Request(url,method='HEAD',headers={'User-Agent':'LingoBunny-HF1/1.0'})
  with urllib.request.urlopen(req,timeout=12) as r:print('PUBLIC_HEAD_HTTP='+str(r.status))
 except Exception as e:print('PUBLIC_HEAD_HTTP=UNCONFIRMED '+str(e))
 try:
  req=urllib.request.Request('https://lingo.bestresources.cn/api/social/online',data=b'{"player_id":"hf1-test-id","secret":"not-a-real-secret"}',headers={'Content-Type':'application/json','Origin':'https://appassets.androidplatform.net'},method='POST')
  try:
   with urllib.request.urlopen(req,timeout=12) as r:print('PUBLIC_SOCIAL_POST_HTTP='+str(r.status))
  except urllib.error.HTTPError as e:
   print('PUBLIC_SOCIAL_POST_HTTP='+str(e.code)+' (401 expected for dummy credentials)')
 except Exception as e:print('PUBLIC_SOCIAL_POST=UNCONFIRMED '+str(e))
 print('RESULT=V155_HF1_READY')
