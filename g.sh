#!/usr/bin/env bash
cd /mnt/e/projects/audio-jam
rm -f chk.sh chk.txt rb.log diff.txt difftest.sh mk.txt r3.txt mksimple.sh pipeline/_mksimple.py pipeline/_r3.py data/simple.* 2>/dev/null
git add -A
git commit -q -m "feat: difficulty parameter (simple/standard/full) controlling quantize grid (8th vs 16th) and which drum pieces are kept/collapsed; UI selector with per-level explanation of what it controls" >/dev/null 2>&1
echo "COMMIT_EXIT=$?" > /mnt/e/projects/audio-jam/g.txt
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"
git push origin main >> /mnt/e/projects/audio-jam/g.txt 2>&1
echo "PUSH_EXIT=$?" >> /mnt/e/projects/audio-jam/g.txt
git log --oneline -1 >> /mnt/e/projects/audio-jam/g.txt 2>&1
