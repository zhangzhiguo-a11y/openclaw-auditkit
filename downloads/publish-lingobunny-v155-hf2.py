#!/usr/bin/env python3
"""Publish the prebuilt, signed HF2 APK to the existing Lingo Bunny download URL.

Scope is exactly one new file under web/download. Do not modify existing HTML,
server code, databases, credentials, or installed APKs.
"""
from pathlib import Path
import hashlib
import os
import shutil
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

APP = Path.home() / '.lingo-bunny' / 'app-v1.3.2'
DOWNLOAD = APP / 'web' / 'download'
BASE = DOWNLOAD / 'LingoBunny-V1.5.5-HF1-Android-OnlineFix-FINAL.apk'
TARGET = DOWNLOAD / 'LingoBunny-V1.5.5-HF2-Android-OnlineFix-FINAL.apk'
BASE_SHA = 'ad1c6b93ffc84d18941b6df3280f9303a73ce400d841582ce99fa16361ca48c2'
PREFIX_BYTES = 83972488
PREFIX_SHA = '9363945c1a8a0a0546ec6c661f44d5a487f4b9bb1496115df3eaf900542445ca'
TAIL_SHA = '215a597c9d8ae62922f59595b51faf727ee46bb4dd0f5eb38c308f9d54b3736b'
TARGET_SHA = 'e1425fcc53a5b855c3e3fa9b093a0ceef317a11e41a04fcbde23bc86a5222e55'
TARGET_BYTES = 84075849
COMMIT = 'eb6f5c07e25435d432d136c719ff236f474d2409'
REPO_FILE = 'downloads/v155-hf2/LingoBunny-V1.5.5-HF2-tail-from-HF1.bin'
URLS = [
    'https://raw.githubusercontent.com/zhangzhiguo-a11y/openclaw-auditkit/' + COMMIT + '/' + REPO_FILE,
    'https://cdn.jsdelivr.net/gh/zhangzhiguo-a11y/openclaw-auditkit@' + COMMIT + '/' + REPO_FILE,
]
PUBLIC_URL = 'https://lingo.bestresources.cn/download/' + TARGET.name


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def download_tail(path):
    errors = []
    for url in URLS:
        for n in range(1, 4):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'LingoBunny-HF2-Publisher/1.0'})
                with urllib.request.urlopen(req, timeout=35) as response, open(path, 'wb') as out:
                    shutil.copyfileobj(response, out)
                if sha(path) == TAIL_SHA:
                    print('TAIL_VERIFIED=OK')
                    return
                errors.append('checksum mismatch: ' + url)
            except Exception as exc:
                errors.append(type(exc).__name__ + ': ' + str(exc)[:100])
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            print('DOWNLOAD_RETRY=' + str(n))
            time.sleep(n)
    raise RuntimeError('Unable to retrieve verified HF2 patch: ' + '; '.join(errors[-3:]))


def verify(apk):
    if apk.stat().st_size != TARGET_BYTES or sha(apk) != TARGET_SHA:
        raise RuntimeError('HF2 APK size or SHA256 mismatch')
    with zipfile.ZipFile(apk) as z:
        if z.testzip():
            raise RuntimeError('HF2 APK ZIP CRC error')
        js = z.read('assets/www/social-v151.js')
        html = z.read('assets/www/index.html')
        sw = z.read('assets/www/sw.js')
        if b'XMLHttpRequest' not in js or b'1.5.5-hf2' not in html or b'1.5.5-hf2' not in sw:
            raise RuntimeError('HF2 APK missing expected social fix markers')
    print('APK_PREFLIGHT=OK SHA256=' + TARGET_SHA)


def check_public():
    req = urllib.request.Request(PUBLIC_URL, method='HEAD', headers={'User-Agent': 'LingoBunny-HF2-Publisher/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            code = response.status
            size = response.headers.get('Content-Length', '')
            print('PUBLIC_HEAD_HTTP=' + str(code))
            print('PUBLIC_CONTENT_LENGTH=' + str(size))
            if code != 200:
                print('PUBLIC_URL_VERIFIED=NO')
            elif size.isdigit() and int(size) == TARGET_BYTES:
                print('PUBLIC_URL_VERIFIED=YES')
            else:
                print('PUBLIC_URL_VERIFIED=RECHECK_CONTENT_LENGTH')
    except Exception as exc:
        print('PUBLIC_HEAD_HTTP=NOT_VERIFIED ' + type(exc).__name__ + ': ' + str(exc))


def main():
    print('=== Lingo Bunny V1.5.5 HF2 public APK publisher ===')
    print('SCOPE=one signed APK under existing web/download; learning data untouched')
    if not DOWNLOAD.is_dir():
        raise RuntimeError('Existing web/download folder not found')
    if TARGET.exists():
        verify(TARGET)
        print('STATUS=ALREADY_PUBLISHED')
    else:
        if not BASE.is_file() or sha(BASE) != BASE_SHA:
            raise RuntimeError('HF1 base APK missing or mismatched; no files changed')
        with tempfile.TemporaryDirectory(prefix='.hf2-publish-', dir=DOWNLOAD) as d:
            tail = Path(d) / 'delta.bin'
            candidate = Path(d) / 'candidate.apk'
            download_tail(tail)
            prefix_hash = hashlib.sha256()
            with BASE.open('rb') as f, candidate.open('wb') as out:
                remaining = PREFIX_BYTES
                while remaining:
                    block = f.read(min(1024 * 1024, remaining))
                    if not block:
                        raise RuntimeError('HF1 base APK too short')
                    prefix_hash.update(block)
                    out.write(block)
                    remaining -= len(block)
                with tail.open('rb') as src:
                    shutil.copyfileobj(src, out, 1024 * 1024)
            if prefix_hash.hexdigest() != PREFIX_SHA:
                raise RuntimeError('HF1 prefix checksum mismatch; no files changed')
            verify(candidate)
            os.chmod(candidate, 0o644)
            os.replace(candidate, TARGET)
        print('STATUS=PUBLISHED')
    print('APK_PATH=' + str(TARGET))
    print('APK_URL=' + PUBLIC_URL)
    print('LEARNING_DATA_UNCHANGED=YES')
    check_public()
    print('RESULT=HF2_PUBLIC_APK_READY')


if __name__ == '__main__':
    main()
