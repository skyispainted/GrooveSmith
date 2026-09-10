#!/usr/bin/env bash
B=http://localhost:8080
O=/mnt/e/projects/audio-jam/repro.txt
: > "$O"
JOB=$(curl -s -X POST -F "file=@/mnt/e/projects/audio-jam/data/input/song.mp3" $B/api/upload | python3 -c "import sys,json;print(json.load(sys.stdin)['job_id'])")
echo "job=$JOB" >> "$O"
for i in $(seq 1 150); do
  ST=$(curl -s $B/api/status/$JOB | python3 -c "import sys,json;print(json.load(sys.stdin)['status'])" 2>/dev/null)
  [ "$ST" = "done" ] && break; [ "$ST" = "error" ] && break; sleep 3
done
echo "final=$ST" >> "$O"
curl -s $B/api/status/$JOB -o /tmp/j.json
python3 /mnt/e/projects/audio-jam/pipeline/showlog.py /tmp/j.json >> "$O" 2>&1
