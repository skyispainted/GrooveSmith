#!/usr/bin/env bash
cd /mnt/e/projects/audio-jam
git add -A
git commit -q -m "fix playback jank: drive highlight via requestAnimationFrame (smooth ~60fps), remove smooth-scroll and heavy per-tick DOM work that stuttered audio; throttle+guard scroll on the .stage container"
echo "COMMIT_EXIT=$?" > /mnt/e/projects/audio-jam/pr.txt
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"
git push origin main >> /mnt/e/projects/audio-jam/pr.txt 2>&1
echo "PUSH_EXIT=$?" >> /mnt/e/projects/audio-jam/pr.txt
git log --oneline -1 >> /mnt/e/projects/audio-jam/pr.txt 2>&1
