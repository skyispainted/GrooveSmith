#!/usr/bin/env bash
cd /mnt/e/projects/audio-jam
git add -A
git commit -q -m "robustness: auto-fallback to CPU when CUDA separation/transcription fails (handles transient GPU OOM/contention so jobs always complete)"
echo "COMMIT_EXIT=$?" > /mnt/e/projects/audio-jam/p.txt
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"
git push origin main >> /mnt/e/projects/audio-jam/p.txt 2>&1
echo "PUSH_EXIT=$?" >> /mnt/e/projects/audio-jam/p.txt
git log --oneline -1 >> /mnt/e/projects/audio-jam/p.txt 2>&1
