#!/usr/bin/env bash
O=/mnt/e/projects/audio-jam/serve.txt
curl -s http://localhost:8080/ -o /tmp/p.html
{
  echo "bytes=$(stat -c%s /tmp/p.html)"
  echo "startHlLoop=$(grep -c startHlLoop /tmp/p.html)"
  echo "raf=$(grep -c requestAnimationFrame /tmp/p.html)"
  echo "smooth_scroll_removed=$(grep -c 'behavior:.smooth' /tmp/p.html)"
} > "$O" 2>&1
