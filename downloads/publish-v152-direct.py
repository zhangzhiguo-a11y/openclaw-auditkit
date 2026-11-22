from pathlib import Path
import hashlib
import os
import shutil
import time
import urllib.request

SHA = '71652ca5b25d97ca4faad2116a1ac304cd3391343e5a1e9e73cb4f1955a3bf5e'
SIZE = 84065901
CHUNK_SIZE = 2097152
N = 41
CHUNK_SHAS = """9e73749c29b0b9f6a20bf441d9e1bbafd3dcae3a98e333e9067a6cc86e78948c
c89fbc3c498c2fa6235406582cdd3e7135ba62ff2bf035445ea3c5729745d036
cd37aa3a1c1775b494e8ab3ddcb41d63281ff78d2e3d010085ce52c2a88af6ec
3a1ba2fa071c0669abf85674320668b2394a10f39a323c1eebf57f4bf4de11d2
c0b5c2e7d191609b6bc483a37cbf0e2d81a7852ca9868aaf103106dffb8f5050
4c471df89e1466671c40744f3eeceee16c94dc555110f7058500fbf6e56b8542
ce3a7b7f53389c15575359df6d09086d47bf35bbe9d8abcde4731aadaad54980
78ea10780d3e31d4d181adf094321baa6db14dd613803db33620a226b9ee6c19
4e771e137473ad9deb3ede9cdf502110676a31294383b3ade57881f1f753c31f
77549666e9673c0af3dc6fa61eaca49a7621395842fef30e5c3723a49b84a0ac
a2731b606952d0b2a336791a78f2638b7c5dd9ac97b896bb5a118f0e5b33304c
d06f17871c2b155b7dec8b3aec799bede2284e268f5d04b49217624b6439a93a
846bbc75b9c608750a494efa69d09abf1a8eb20424284de8f319b9766fb420b3
612b239db716808f6f2a0ef9d7aa7128c333c17e663691fef367d493fb9f7974
99d5a1a2ffea28885dd29c75e355c46fd569656ff8a4d59b6a2c033f9bb7d210
69985e674400318eb2170ba3693be03404c006778b32258e6952e7bcf5ad25a8
09d904950317f20fa1ae9ffd5511b98872a35519366683e2a20c40ddb8972a36
02bed3768cbe4d9cdabfa6171aacb9d7f4eabcc377d07adde96d0501e1904e42
490ec4da60effe4d26828c3c4eb2b285784b3e654ead9f4a35c843996db7bd7c
a8cc5cbf5629970eaabb3104c824d0ae34766fab8e6284e8d11fce4c5ad4c977
b1d560315b3a208c71efb794a01d8f6a9e20178c134e0cad8c3fbc278e0b1bb9
0672a17df37c01385fa6ebd579667c7319009e7766991f3f2046fb922827c441
18c4a34ced845d4ae3ac1873e46ee9340a7baab9e851e46e5c6a906b06c33f22
87f07cd052bf55cb2d5933f71f54b707aa428efc9177c9e6a5a7fce291763a94
03ca8fb2657670c05f709c2a3e51df40c239b34a9940d0dfd1caae74496dd341
48eb136b7f1108400731693ce7c2e8d9c1017b59d2b187133641f8cccba8b824
d090d927b21d79471732a74ef18286409e28c409f8ef7c4ee0c536c8f95c22da
2cca11a9e6d3db7095cf7f7e6332f68a1e4984ba017d11b56d172464555bd6d6
236dfc50c260208012252e0aa70e99a69a00ee3a94af9fd929048116394f452c
1249089ac04edbc5b268b702e7f42bb1bf10931d7cb59cb106bf1970aaf48e09
a25ca0e3af58a8699176b17b51202f15cf866ec404cd497a7435af1b7c4793bc
5b0b8c2e78f865cd5ac08e3b17d2c5739bf3df22a2b404f6bc1fcf9ff42ba579
c8236e36dc12dcaf21f9360d2680b2954866742bc068dcf1e4d4d6d8b5d2d857
ec2240b15f66027661543a5fc85bd2e7acbfde608ce75728c152832622c9920c
d44c736169b0691845de47fded1cbaae8e0384429b3c7a429b253e2067c3fb7b
f8768adfbdb4a895823444b9253de15ee336193c346ec40bfaf6ec6b36d91887
b601b15367473bb7c56e044a3e502920b694ae2fb48c59b6c1d72c771ed181cc
de2891b22b3b8ccba73dc02e12cb22001d2ec07d241ffbd2139038ac50c806a2
cf9b2693e43685040d214ffbb1722007544135158a86657cae3e342045a05c6e
cdfce161335cbbbdf601f483805744c941618ee67f8e261ca06ea9108875d8f9
46f001c723c332c75b8a4bbd8ceb7b4802f2eaf125afda3116f10cba46f0773e""".splitlines()
REV = 'c1951ff13237dac4dcf7529c3963699d53245acc'
REPO = 'zhangzhiguo-a11y/openclaw-auditkit'
BASE = f'downloads/v152-original-parts'
NAME = 'LingoBunny-V1.5.2-Android-MultiKid-Sync-FINAL.apk'
HOME = Path.home()
WEB = HOME / '.lingo-bunny/app-v1.3.2/web'
CACHE = HOME / '.lingo-bunny/download-cache/v152-original'
DEST = WEB / 'download' / NAME

if not (WEB / 'index.html').is_file():
    raise SystemExit(f'ERROR: Web folder missing: {WEB}')
CACHE.mkdir(parents=True, exist_ok=True)

for i in range(N):
    part = CACHE / f'part-{i:03d}.bin'
    expected = CHUNK_SIZE if i < N - 1 else SIZE - CHUNK_SIZE * (N - 1)
    if part.is_file() and part.stat().st_size == expected and hashlib.sha256(part.read_bytes()).hexdigest() == CHUNK_SHAS[i]:
        print(f'{i + 1:02d}/{N}: cached', flush=True)
        continue
    path = f'{BASE}/part-{i:03d}.bin'
    urls = [
        f'https://raw.githubusercontent.com/{REPO}/{REV}/{path}',
        f'https://cdn.jsdelivr.net/gh/{REPO}@{REV}/{path}',
    ]
    ok = False
    for attempt in range(12):
        url = urls[attempt % len(urls)]
        tmp = CACHE / f'.part-{i:03d}.downloading'
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'LingoBunny-APK-Downloader/1.0', 'Accept': 'application/octet-stream'})
            with urllib.request.urlopen(request, timeout=45) as response, tmp.open('wb') as dst:
                shutil.copyfileobj(response, dst, 256 * 1024)
            got = tmp.stat().st_size
            if got != expected:
                raise OSError(f'expected {expected} bytes but received {got} bytes')
            if hashlib.sha256(tmp.read_bytes()).hexdigest() != CHUNK_SHAS[i]:
                raise OSError('downloaded chunk SHA256 mismatch')
            os.replace(tmp, part)
            print(f'{i + 1:02d}/{N}: downloaded', flush=True)
            ok = True
            break
        except Exception as exc:
            tmp.unlink(missing_ok=True)
            print(f'{i + 1:02d}/{N}: retry {attempt + 1}/12 ({type(exc).__name__}: {exc})', flush=True)
            time.sleep(min(2 + attempt, 12))
    if not ok:
        raise SystemExit(f'ERROR: Could not download part {i:03d}; rerun the same command to resume.')

DEST.parent.mkdir(parents=True, exist_ok=True)
if DEST.exists():
    if DEST.stat().st_size == SIZE and hashlib.sha256(DEST.read_bytes()).hexdigest() == SHA:
        print('RESULT=ALREADY_PUBLISHED_AND_VERIFIED')
        print(f'URL=https://lingo.bestresources.cn/download/{NAME}')
        raise SystemExit(0)
    raise SystemExit(f'ERROR: Destination exists but is different. Will not overwrite: {DEST}')
TEMP = DEST.parent / ('.' + NAME + '.tmp')
h = hashlib.sha256()
with TEMP.open('wb') as out:
    for i in range(N):
        part = CACHE / f'part-{i:03d}.bin'
        with part.open('rb') as inp:
            while True:
                block = inp.read(256 * 1024)
                if not block:
                    break
                h.update(block)
                out.write(block)

actual = h.hexdigest()
if actual != SHA or TEMP.stat().st_size != SIZE:
    TEMP.unlink(missing_ok=True)
    raise SystemExit(f'ERROR: SHA or size mismatch. Got SHA256={actual}. File not published.')
TEMP.chmod(0o644)
os.replace(TEMP, DEST)
print(f'OK: APK_SHA256={actual}', flush=True)
print(f'OK: PUBLISHED={DEST}', flush=True)
print(f'URL=https://lingo.bestresources.cn/download/{NAME}', flush=True)
try:
    req = urllib.request.Request(f'https://lingo.bestresources.cn/download/{NAME}', method='HEAD')
    with urllib.request.urlopen(req, timeout=15) as response:
        status = response.status
        content_type = response.headers.get('Content-Type', '')
        remote_size = response.headers.get('Content-Length', '')
    print(f'PUBLIC_HTTP={status} TYPE={content_type} SIZE={remote_size}', flush=True)
    if status == 200 and (remote_size in ('', str(SIZE))) and not content_type.lower().startswith('text/html'):
        print('RESULT=PUBLIC_DOWNLOAD_READY', flush=True)
    else:
        print('RESULT=PUBLIC_ROUTE_NOT_VERIFIED', flush=True)
except Exception as exc:
    print(f'RESULT=PUBLIC_ROUTE_NOT_VERIFIED: {exc}', flush=True)