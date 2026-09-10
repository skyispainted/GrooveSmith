#!/usr/bin/env bash
cd /mnt/e/projects/audio-jam
rm -f chk.sh chk.txt chk2.sh chk2.txt rb.log seekapi.txt consolecheck.ps1 console.txt pipeline/_seekapi.py 2>/dev/null
git add -A
git commit -q -m "perf: replace per-note coloring with a GPU-composited cursor overlay (transform-only, no reflow/style-recalc on the large SVG); fix seek: original audio is master clock, MIDI follows at v-offset, supports paused-drag via pendingMidiSeek"
echo "COMMIT_EXIT=$?" > /mnt/e/projects/audio-jam/pr.txt
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"
git push origin main >> /mnt/e/projects/audio-jam/pr.txt 2>&1
echo "PUSH_EXIT=$?" >> /mnt/e/projects/audio-jam/pr.txt
git log --oneline -1 >> /mnt/e/projects/audio-jam/pr.txt 2>&1
