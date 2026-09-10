#!/usr/bin/env bash
cd /mnt/e/projects/audio-jam
git add -A
git commit -q -m "fix intermittent demucs failure: serialize jobs with PROC_LOCK (avoid concurrent GPU/CPU runs) + capture real subprocess stderr into logs for diagnosis"
echo "COMMIT_EXIT=$?" > /mnt/e/projects/audio-jam/p.txt
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"
git push origin main >> /mnt/e/projects/audio-jam/p.txt 2>&1
echo "PUSH_EXIT=$?" >> /mnt/e/projects/audio-jam/p.txt
git log --oneline -1 >> /mnt/e/projects/audio-jam/p.txt 2>&1
