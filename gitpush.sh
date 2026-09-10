#!/usr/bin/env bash
cd /mnt/e/projects/audio-jam
git add -A
git commit -q -m "GPU support: Dockerfile.gpu (pytorch CUDA base, apt direct + pip proxy), compose gpu profile with web-gpu; verified RTX 3060, 4min song in ~64s"
echo "COMMIT_EXIT=$?" > /mnt/e/projects/audio-jam/gpush.txt
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"
git push origin main >> /mnt/e/projects/audio-jam/gpush.txt 2>&1
echo "PUSH_EXIT=$?" >> /mnt/e/projects/audio-jam/gpush.txt
git log --oneline -1 >> /mnt/e/projects/audio-jam/gpush.txt 2>&1
