#!/usr/bin/env bash
cd /mnt/e/projects/audio-jam
rm -f align.txt align.sh align2.txt align2.sh c.txt chk.sh chk.txt rb.log 2>/dev/null
git add -A
git commit -q -m "fix highlight desync + reduce stutter: keep score aligned to absolute audio time (no intro trim, so score/MIDI/audio share one timeline), preload drum samples to avoid mid-playback network stalls"
echo "COMMIT_EXIT=$?" > /mnt/e/projects/audio-jam/pr.txt
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"
git push origin main >> /mnt/e/projects/audio-jam/pr.txt 2>&1
echo "PUSH_EXIT=$?" >> /mnt/e/projects/audio-jam/pr.txt
git log --oneline -1 >> /mnt/e/projects/audio-jam/pr.txt 2>&1
