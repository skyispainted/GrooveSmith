#!/usr/bin/env bash
# Download the magenta sgm_plus PERCUSSION soundfont for self-hosting.
# ~376 small mp3s (~9MB). Uses proxy.
set +e
export https_proxy=http://172.20.128.1:20808 http_proxy=http://172.20.128.1:20808
BASE="https://storage.googleapis.com/magentadata/js/soundfonts/sgm_plus"
DEST="/mnt/e/projects/audio-jam/pipeline/static/soundfonts/sgm_plus"
PERC="$DEST/percussion"
mkdir -p "$PERC"
O=/mnt/e/projects/audio-jam/sf_dl.txt
: > "$O"

# top-level soundfont.json but trimmed to only percussion so player won't try other instruments
cat > "$DEST/soundfont.json" << 'JSON'
{
  "name": "sgm_plus",
  "instruments": { "drums": "percussion" }
}
JSON

curl -sL -o "$PERC/instrument.json" --max-time 40 "$BASE/percussion/instrument.json"

ok=0; fail=0; skip=0
for p in $(seq 35 81); do
  for v in 15 31 47 63 79 95 111 127; do
    f="p${p}_v${v}.mp3"
    if [ -s "$PERC/$f" ]; then skip=$((skip+1)); continue; fi
    code=$(curl -sL -o "$PERC/$f" -w '%{http_code}' --max-time 30 "$BASE/percussion/$f")
    if [ "$code" = "200" ] && [ -s "$PERC/$f" ]; then ok=$((ok+1)); else rm -f "$PERC/$f"; fail=$((fail+1)); fi
  done
done
{
  echo "downloaded_ok=$ok skipped=$skip missing(404 combos, normal)=$fail"
  echo "total files: $(ls -1 "$PERC"/*.mp3 2>/dev/null | wc -l)"
  echo "total size: $(du -sh "$DEST" | cut -f1)"
  echo "instrument.json bytes: $(stat -c%s "$PERC/instrument.json")"
} >> "$O" 2>&1
cat "$O"
