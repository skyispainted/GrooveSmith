#!/usr/bin/env bash
cd /mnt/e/projects/audio-jam
git add -A
git commit -q -m "fix demucs failure in GPU image: set MKL_THREADING_LAYER=GNU (Intel MKL clashed with libgomp in conda pytorch image, causing exit 1 on both cuda and cpu)"
echo "COMMIT_EXIT=$?" > /mnt/e/projects/audio-jam/p.txt
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"
git push origin main >> /mnt/e/projects/audio-jam/p.txt 2>&1
echo "PUSH_EXIT=$?" >> /mnt/e/projects/audio-jam/p.txt
git log --oneline -1 >> /mnt/e/projects/audio-jam/p.txt 2>&1
