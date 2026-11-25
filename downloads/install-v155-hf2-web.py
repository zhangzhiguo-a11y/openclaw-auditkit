#!/usr/bin/env python3
"""Lingo Bunny v1.5.5 HF2: website-only social XHR hotfix. Does not touch SQLite, APK, or backend."""
import hashlib,base64,zlib,os,shutil,tempfile,time,urllib.request
from pathlib import Path

ROOT=Path.home()/'.lingo-bunny'
WEB=ROOT/'app-v1.3.2/web'
FILES={
  'social-v151.js':('224ff4a96dd3f16220e6f8ec46b6aaf6ac1c5eb81f11f33495ad7b646bf392bd','d3664571f97b059eed29ecffe485fa5bf883070465f8652eec44e608e97489df'),
  'index.html':('d83c2da3d36ad0d56e28a45f3cc605076fd301ec434c103900f1bf285acbe335','0cdfd47941d2143aefc4f8b72041094b8aea76f29f07fa3867e88a55b84cbd2e'),
  'sw.js':('161b6f29abf8a878524fa64a5aad427e42388b8e912a6a8bb6829174465b9036','41d6081f25e898319d3bb47c8a8e79f167ac0a51fcebcf8c0b2cc39140528809'),
}
OLD_POST=b"function post(path,payload){\n  var base=(window.LingoSyncConfig&&window.LingoSyncConfig.apiBase)||'';\n  if(typeof window.AndroidBridge!=='undefined')base='https://lingo.bestresources.cn';\n  return fetch(base+path,{method:'POST',mode:'cors',credentials:'omit',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload||{})})\n    .then(function(r){return r.json().catch(function(){return {}}).then(function(j){if(!r.ok){var e=new Error(j.error||('HTTP '+r.status));e.status=r.status;throw e;}return j;});});\n}"
NEW_POST=zlib.decompress(base64.b64decode('eNqVVE1v20YQvftXTHPQkrBMKSmQg1W2cIIGauEmRqwCua65Q2lTapfdXVoRZF4CFEjRXFoUKRK0Nxc5BUaAIilat4f+lvijJ/+FzpKSaDU5tBeCnJ15782bWXY60L91bRMGI4Sx3pMZgpB8qLR1MoF9NDKVKODeZ9t95/K7+GWB1sHOnd1BGyYjn+6oMkNulFTDtU4Hcj5EZiFFl4yCcGOPW6q3OpE8g62dTyDlVCVgIt0IrtyqP5yu869EAJ9bBK0Q7vXvejhnuLK5Ng5SbWBre3uBZXTh0EIgVZIVgshBabUhBY5z7VA5MDiUlsqd1Cpseyx6H6EhxVzRqTNTX8UXiioFwJUAI+0X/kgUeSYT7pCyq8ZttJYWKvGIkJNFQU6I7ZxPM81FOFsD2OcGfMtxMJFK6Em0TUB6d6qSm1qlcthqvTse8VzeoLrw4ICxHgHJNHDTHHUK84ItJYyW4oaRYojvxTErlMBUKhQsrBjZiCZkNzudzENHe6TXoNWFSdBGiapQvbzCZLEvWPfifZCsKIwChRPYMXosLQaLLgOPkO1j2+B9TFzVYo3yYGR61QfZWEfBx2KPsrotQdhrziOdowqYXyDWJiVtZwpcSXByjDTa+Or1brd7+cBvzE2DgmZL87dxSg+8nGDRzSn7yAWagJG3fhU2BuQkazOe1/Okxjr3rVZsVZnyU4yXrYeLtuqGBXc8npW9ZdA3XgU/3b1zO8q5Id88DlmWa2VxgA8cTXNWEk1JrHQdMJyVy3qacKXacVfYD+Nr3W6r1QQ+eL/bDWdz+wPPE/bqQfXKFV1oatM/NkaboMpstfwzQh+hhQpYfzDYAbbeoK8z+Os1nB3++ea3Q38rWRg2jVHdPC1uKprjehUCylrWlKs+VsSXjZyXNDJZQw1nf3x79vuPf3//9Pzo6OL4Ed37i+PHleLuxfHXXtm/4Bcb8l8Jzo9en758eP7qq9MfXhHB1etnz797NzLfox/N/8R98+uL0ycv3gKzqERQbQZdQ7qQMp0G8x/FwcGsXPjdLMbairtvMdZkJ49+Onn+zcnjJyeHL89/+fni+BlbD7DVwmiM1tKf96Pl2+ZuxUvQ4ZKMniW9l/8AH5Ed0w=='))

def digest(data):return hashlib.sha256(data).hexdigest()

print('=== Lingo Bunny V1.5.5 HF2 mobile-web social XHR fix ===')
print('SCOPE=website social transport only; learning DB, social DB and Android APK untouched')
previous={}
for name,(before,after) in FILES.items():
    path=WEB/name
    if not path.is_file():raise SystemExit('ERROR missing '+str(path))
    data=path.read_bytes();sha=digest(data)
    if sha not in (before,after):raise SystemExit('ERROR unexpected '+name+' SHA='+sha+' (no files changed)')
    previous[name]=data
already=all(digest(previous[name])==hashes[1] for name,hashes in FILES.items())
if already:
    print('HF2_ALREADY_APPLIED=YES')
    print('RESULT=V155_HF2_WEB_READY')
    raise SystemExit(0)
if not all(digest(previous[name])==hashes[0] for name,hashes in FILES.items()):
    raise SystemExit('ERROR partial HF2 installation detected; no files changed')

patched={}
social=previous['social-v151.js']
if social.count(OLD_POST)!=1:raise SystemExit('ERROR social function not found')
patched['social-v151.js']=social.replace(OLD_POST,NEW_POST)
idx=previous['index.html']
old_query=b'social-v151.js?v=1.5.5-hf1'
if idx.count(old_query)!=1:raise SystemExit('ERROR HTML script tag not found')
patched['index.html']=idx.replace(old_query,b'social-v151.js?v=1.5.5-hf2-xhr')
sw=previous['sw.js']
if sw.count(b'lingo-bunny-v1.5.5-hf1-online')!=1 or sw.count(old_query)!=1:
    raise SystemExit('ERROR service-worker markers not found')
patched['sw.js']=sw.replace(b'lingo-bunny-v1.5.5-hf1-online',b'lingo-bunny-v1.5.5-hf2-xhr-social').replace(old_query,b'social-v151.js?v=1.5.5-hf2-xhr')
for name,data in patched.items():
    if digest(data)!=FILES[name][1]:raise SystemExit('ERROR patched '+name+' hash mismatch; no files changed')
print('HF2_PATCH_PREFLIGHT=OK')

stamp=time.strftime('%Y%m%d-%H%M%S')
backup=ROOT/'backups'/('v155-hf2-social-web-before-'+stamp)
backup.mkdir(parents=True,exist_ok=False)
for name,content in previous.items():
    (backup/name).write_bytes(content)
print('BACKUP='+str(backup))
replaced=[]
try:
    for name,data in patched.items():
        target=WEB/name
        fd,temp=tempfile.mkstemp(prefix='.'+name+'.',suffix='.hf2',dir=str(WEB))
        try:
            with os.fdopen(fd,'wb') as fh:fh.write(data)
            os.chmod(temp,target.stat().st_mode & 0o777)
            os.replace(temp,target)
        finally:
            if os.path.exists(temp):os.unlink(temp)
        replaced.append(name)
    for name,expected in FILES.items():
        if digest((WEB/name).read_bytes())!=expected[1]:raise RuntimeError('verify failed: '+name)
except Exception as exc:
    for name in reversed(replaced):
        shutil.copy2(backup/name, WEB/name)
    raise SystemExit('ERROR rolled back web files: '+str(exc))
print('WEB_FILES_UPDATED=3')
print('SOCIAL_TRANSPORT=XMLHttpRequest')
print('CLIENT_CACHE_BUSTER=1.5.5-hf2-xhr')
print('LEARNING_DATA_UNCHANGED=YES')
try:
    req=urllib.request.Request('http://127.0.0.1:8792/social-v151.js?v=1.5.5-hf2-xhr',headers={'Cache-Control':'no-cache'})
    with urllib.request.urlopen(req,timeout=8) as res:
        got=res.read()
        print('LOCAL_SOCIAL_JS='+('OK' if res.status==200 and digest(got)==FILES['social-v151.js'][1] else 'MISMATCH'))
except Exception as e:
    print('LOCAL_SOCIAL_JS=UNCONFIRMED '+str(e)[:120])
print('RESULT=V155_HF2_WEB_READY')
