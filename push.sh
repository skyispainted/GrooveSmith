#!/usr/bin/env bash
cd /mnt/e/projects/audio-jam
rm -f svgsize.sh svgsize.txt svgstruct.txt chk.sh chk.txt rb.log consolecheck.ps1 console.txt 2>/dev/null
git add -A
git commit -q -m "perf: reflow-free highlight (cache note SVG coords once, no per-frame getBoundingClientRect), cheaper highlight CSS, and a 播放高亮 on/off toggle to A/B test stutter while keeping real drum samples"
echo "COMMIT_EXIT=$?" > /mnt/e/projects/audio-jam/pr.txt
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"
git push origin main >> /mnt/e/projects/audio-jam/pr.txt 2>&1
echo "PUSH_EXIT=$?" >> /mnt/e/projects/audio-jam/pr.txt
git log --oneline -1 >> /mnt/e/projects/audio-jam/pr.txt 2>&1
