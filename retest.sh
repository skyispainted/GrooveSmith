#!/usr/bin/env bash
B=http://localhost:8080
O=/mnt/e/projects/audio-jam/retest.txt
: > "$O"
JOB=$(curl -s -X POST -F "file=@/mnt/e/projects/audio-jam/data/input/song.mp3" $B/api/upload | python3 -c "import sys,json;print(json.load(sys.stdin)['job_id'])")
echo "job=$JOB" >> "$O"
for i in $(seq 1 200); do
  S=$(curl -s $B/api/status/$JOB)
  ST=$(echo "$S" | python3 -c "import sys,json;print(json.load(sys.stdin)['status'])" 2>/dev/null)
  [ "$ST" = "done" ] && break; [ "$ST" = "error" ] && break; sleep 3
done
echo "final=$ST" >> "$O"
curl -s $B/api/status/$JOB | python3 -c "import sys,json;d=json.load(sys.stdin);print('logs:'); [print(' ',l) for l in d.get('logs',[])]" >> "$O" 2>&1
