#!/usr/bin/env bash
O=/mnt/e/projects/audio-jam/joblog.txt
: > "$O"
echo "=== job 21ca3ab106ba logs ===" >> "$O"
curl -s http://localhost:8080/api/status/21ca3ab106ba -o /tmp/j.json
python3 /mnt/e/projects/audio-jam/pipeline/showlog.py /tmp/j.json >> "$O" 2>&1
echo "=== web-gpu container logs (tail 80) ===" >> "$O"
cd /mnt/e/projects/audio-jam && docker compose logs web-gpu --tail 80 >> "$O" 2>&1
