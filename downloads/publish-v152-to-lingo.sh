#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$ROOT/downloads/v152-original-parts"
WEB="$HOME/.lingo-bunny/app-v1.3.2/web"
NAME="LingoBunny-V1.5.2-Android-MultiKid-Sync-FINAL.apk"
SHA="71652ca5b25d97ca4faad2116a1ac304cd3391343e5a1e9e73cb4f1955a3bf5e"

if [[ ! -d "$SOURCE" || ! -f "$WEB/index.html" ]]; then
  echo "ERROR: Source pieces or target Lingo Bunny web folder missing" >&2
  exit 1
fi
shopt -s nullglob
files=("$SOURCE"/part-*.bin)
if [[ ${#files[@]} -ne 41 ]]; then
  echo "ERROR: Expected 41 chunks; found ${#files[@]}" >&2
  exit 1
fi
mkdir -p "$WEB/download"
TEMP="$(mktemp "$WEB/download/.v152-XXXXXXXX.apk.part")"
trap 'rm -f "$TEMP"' EXIT
cat "${files[@]}" > "$TEMP"
ACTUAL="$(shasum -a 256 "$TEMP" | awk '{print $1}')"
if [[ "$ACTUAL" != "$SHA" ]]; then
  echo "ERROR: APK SHA256 mismatch: $ACTUAL" >&2
  exit 1
fi
TARGET="$WEB/download/$NAME"
chmod 644 "$TEMP"
mv -f "$TEMP" "$TARGET"
trap - EXIT
URL="https://lingo.bestresources.cn/download/$NAME"
echo "ASSEMBLED_BYTES=$(wc -c < "$TARGET" | tr -d ' ')"
echo "APK_SHA256=$ACTUAL"
echo "PUBLISH_PATH=$TARGET"
echo "PUBLIC_URL=$URL"
STATUS="$(curl --silent --show-error --location --head --max-time 20 --output /dev/null --write-out '%{http_code}' "$URL" || true)"
echo "PUBLIC_HEAD_HTTP=$STATUS"
if [[ "$STATUS" == "200" || "$STATUS" == "206" ]]; then
  echo "RESULT=PUBLIC_DOWNLOAD_READY"
else
  echo "RESULT=FILE_READY_BUT_PUBLIC_ROUTE_NOT_VERIFIED"
  echo "NOTE=No changes were made to the server or learning database"
fi
