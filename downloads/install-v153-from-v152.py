#!/usr/bin/env python3
from pathlib import Path
import hashlib, os, shutil, sys, time, urllib.request, urllib.error, zipfile

BASE_SHA="71652ca5b25d97ca4faad2116a1ac304cd3391343e5a1e9e73cb4f1955a3bf5e"
TAIL_SHA="255245101ab31034edb74dd8fd4cd422d92590b2fba320e55e9b8d300c2bcde1"
FINAL_SHA="59afcf3b2ddb7b6195645640ddc484329b01a90763762dd1c12c4b704e939fa6"
PREFIX=82927508
TAIL_URLS=[
 "https://raw.githubusercontent.com/zhangzhiguo-a11y/openclaw-auditkit/95d1468e7f14de4160faeb8311407a81639c1652/downloads/v153/LingoBunny-V1.5.3-tail-from-v152.bin",
 "https://cdn.jsdelivr.net/gh/zhangzhiguo-a11y/openclaw-auditkit@95d1468e7f14de4160faeb8311407a81639c1652/downloads/v153/LingoBunny-V1.5.3-tail-from-v152.bin",
]

home=Path.home()
root=home/".lingo-bunny"/"app-v1.3.2"
web=root/"web"
download=web/"download"
data_dir=home/".lingo-bunny"/"data"
base=download/"LingoBunny-V1.5.2-Android-MultiKid-Sync-FINAL.apk"
target=download/"LingoBunny-V1.5.3-Android-MultiKid-Sync-FINAL.apk"
tail=download/".LingoBunny-V1.5.3-tail.bin"

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        while True:
            b=f.read(1024*1024)
            if not b: break
            h.update(b)
    return h.hexdigest()

def download_with_retry(urls,dst):
    last=None
    for url in urls:
        for attempt in range(1,6):
            try:
                req=urllib.request.Request(url,headers={"User-Agent":"LingoBunny-V153-Updater/1.0"})
                with urllib.request.urlopen(req,timeout=45) as r, open(dst,"wb") as out:
                    shutil.copyfileobj(r,out,1024*1024)
                return url
            except Exception as e:
                last=e
                try: dst.unlink()
                except FileNotFoundError: pass
                print(f"download retry {attempt}/5: {type(e).__name__}: {e}")
                time.sleep(min(2*attempt,8))
    raise RuntimeError(f"tail download failed: {last}")

print("=== Lingo Bunny V1.5.3 updater ===")
if not web.is_dir():
    raise SystemExit(f"ERROR: web root missing: {web}")
download.mkdir(parents=True,exist_ok=True)

# Never touch the database.
db=data_dir/"lingo_bunny.db"
print("DB_PROTECTED="+str(db))

# Find the exact V1.5.2 base only.
candidates=[base]
if not base.exists():
    candidates += sorted(download.glob("LingoBunny-V1.5.2*.apk"))
base_ok=None
for p in candidates:
    if p.exists() and p.is_file():
        s=sha256(p)
        print(f"BASE_CANDIDATE={p.name} SHA256={s}")
        if s==BASE_SHA:
            base_ok=p
            break
if base_ok is None:
    raise SystemExit("ERROR: exact V1.5.2 base APK not found in web/download; no files changed")

used=download_with_retry(TAIL_URLS,tail)
tail_sha=sha256(tail)
print("TAIL_SOURCE="+used)
print("TAIL_SHA256="+tail_sha)
if tail_sha!=TAIL_SHA:
    tail.unlink(missing_ok=True)
    raise SystemExit("ERROR: tail SHA256 mismatch; no files changed")

tmp=download/".LingoBunny-V1.5.3-building.apk"
with open(base_ok,"rb") as src, open(tmp,"wb") as out:
    remaining=PREFIX
    while remaining:
        b=src.read(min(1024*1024,remaining))
        if not b: raise SystemExit("ERROR: base APK shorter than expected")
        out.write(b); remaining-=len(b)
    with open(tail,"rb") as tf:
        shutil.copyfileobj(tf,out,1024*1024)

final_sha=sha256(tmp)
print("FINAL_SHA256="+final_sha)
if final_sha!=FINAL_SHA:
    tmp.unlink(missing_ok=True); tail.unlink(missing_ok=True)
    raise SystemExit("ERROR: rebuilt V1.5.3 SHA256 mismatch; no web files changed")

# Validate APK zip before deployment.
with zipfile.ZipFile(tmp,"r") as z:
    bad=z.testzip()
    if bad:
        raise SystemExit("ERROR: APK zip validation failed at "+bad)
    names=set(z.namelist())
    required={
      "assets/www/index.html",
      "assets/www/windows-voice-v135.js",
      "assets/www/android-release-v152.js",
      "AndroidManifest.xml",
    }
    if not required.issubset(names):
        raise SystemExit("ERROR: V1.5.3 required assets missing")
    idx=z.read("assets/www/index.html").decode("utf-8","replace")
    rel=z.read("assets/www/android-release-v152.js").decode("utf-8","replace")
    win=z.read("assets/www/windows-voice-v135.js").decode("utf-8","replace")
    if "v=1.5.3" not in idx or "versionName:'1.5.3'" not in rel or "interimRanked" not in win:
        raise SystemExit("ERROR: V1.5.3 patch markers missing")

# Back up only web files we replace.
stamp=time.strftime("%Y%m%d-%H%M%S")
backup=home/".lingo-bunny"/"backups"/("web-before-v153-"+stamp)
backup.mkdir(parents=True,exist_ok=False)
web_files=[
 ("assets/www/index.html","index.html"),
 ("assets/www/windows-voice-v135.js","windows-voice-v135.js"),
 ("assets/www/android-release-v152.js","android-release-v152.js"),
]
for _,dst_name in web_files:
    dst=web/dst_name
    if dst.exists():
        shutil.copy2(dst,backup/dst_name)

# Publish APK atomically first.
os.chmod(tmp,0o644)
os.replace(tmp,target)

# Extract only three web assets; curriculum/data/app.js remain untouched.
with zipfile.ZipFile(target,"r") as z:
    for src_name,dst_name in web_files:
        dst=web/dst_name
        t=web/("."+dst_name+".v153.tmp")
        t.write_bytes(z.read(src_name))
        os.chmod(t,0o644)
        os.replace(t,dst)

tail.unlink(missing_ok=True)
print("BACKUP="+str(backup))
print("APK_PATH="+str(target))
print("APK_BYTES="+str(target.stat().st_size))

# Verify existing server CORS. V1.3.6+ should already provide this.
cors="UNKNOWN"
try:
    req=urllib.request.Request(
      "https://lingo.bestresources.cn/api/profile/load",
      method="OPTIONS",
      headers={
        "Origin":"https://appassets.androidplatform.net",
        "Access-Control-Request-Method":"POST",
        "Access-Control-Request-Headers":"content-type",
        "User-Agent":"LingoBunny-V153-Updater/1.0",
      })
    with urllib.request.urlopen(req,timeout=20) as r:
        allow=(r.headers.get("Access-Control-Allow-Origin") or "")
        methods=(r.headers.get("Access-Control-Allow-Methods") or "")
        cors="OK" if (allow=="*" or "appassets.androidplatform.net" in allow) and "POST" in methods.upper() else f"BAD_HEADERS origin={allow!r} methods={methods!r}"
except Exception as e:
    cors=f"ERROR {type(e).__name__}: {e}"
print("CORS_PREFLIGHT="+cors)

url="https://lingo.bestresources.cn/download/LingoBunny-V1.5.3-Android-MultiKid-Sync-FINAL.apk"
print("APK_URL="+url)
try:
    req=urllib.request.Request(url,method="HEAD",headers={"User-Agent":"LingoBunny-V153-Updater/1.0"})
    with urllib.request.urlopen(req,timeout=20) as r:
        print("PUBLIC_HEAD_HTTP="+str(r.status))
        print("PUBLIC_CONTENT_LENGTH="+str(r.headers.get("Content-Length") or ""))
except Exception as e:
    print("PUBLIC_HEAD_HTTP=ERROR "+type(e).__name__+": "+str(e))

print("RESULT=V153_READY")
