#!/usr/bin/env bash
cd /mnt/e/projects/audio-jam
rm -f st.txt
git add -A
git commit -q -m "feat: alignment offset slider (5ms step) between drum synth and original, playback highlight via verovio timemap, score title from uploaded filename, downloads in sidebar"
echo "COMMIT_EXIT=$?" > /mnt/e/projects/audio-jam/pr.txt
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"
git push origin main >> /mnt/e/projects/audio-jam/pr.txt 2>&1
echo "PUSH_EXIT=$?" >> /mnt/e/projects/audio-jam/pr.txt
git log --oneline -1 >> /mnt/e/projects/audio-jam/pr.txt 2>&1
