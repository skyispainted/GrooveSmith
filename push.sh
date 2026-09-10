#!/usr/bin/env bash
cd /mnt/e/projects/audio-jam
rm -f chk.sh chk.txt rb.log consolecheck.ps1 console.txt 2>/dev/null
git add -A
git commit -q -m "remove playback highlight per user request: drop cursor overlay, timemap load, rAF loop, note-coord cache and the highlight toggle; playback path is now minimal (keeps real drum samples, offset, seek, mixing)"
echo "COMMIT_EXIT=$?" > /mnt/e/projects/audio-jam/pr.txt
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"
git push origin main >> /mnt/e/projects/audio-jam/pr.txt 2>&1
echo "PUSH_EXIT=$?" >> /mnt/e/projects/audio-jam/pr.txt
git log --oneline -1 >> /mnt/e/projects/audio-jam/pr.txt 2>&1
