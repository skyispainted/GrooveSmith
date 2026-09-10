#!/usr/bin/env bash
cd /mnt/e/projects/audio-jam
rm -f dn.txt r2.txt rb.log verify.txt verify.sh dntest.sh pipeline/_r2.py data/twovoice.* 2>/dev/null
git add -A
git commit -q -m "drum notation: hand/foot two-voice separation (voice1 hands stems-up, voice2 feet stems-down, backup mechanism), corrected staff positions per standard jazz drum notation" >/dev/null 2>&1
echo "COMMIT_EXIT=$?" > /mnt/e/projects/audio-jam/g.txt
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"
git push origin main >> /mnt/e/projects/audio-jam/g.txt 2>&1
echo "PUSH_EXIT=$?" >> /mnt/e/projects/audio-jam/g.txt
git log --oneline -1 >> /mnt/e/projects/audio-jam/g.txt 2>&1
