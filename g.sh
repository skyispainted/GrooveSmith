#!/usr/bin/env bash
cd /mnt/e/projects/audio-jam
rm -f v.txt rb.log rend.txt beam.txt beam2.txt insp.txt vtest.sh 2>/dev/null
rm -f pipeline/_inspectxml.py pipeline/_beamtest.py pipeline/_beamtest2.py pipeline/_rend.py pipeline/_r3.py pipeline/_mksimple.py 2>/dev/null
rm -f data/inspect.musicxml data/fixed.* data/simple.* 2>/dev/null
git add -A
git commit -q -m "fix drum notation cleanliness: beams now generate (makeBeams on Measure not Voice, which was throwing), hide feet-voice rests (print-object=no) to remove double-rest clutter, stems locked up/down per voice" >/dev/null 2>&1
echo "COMMIT_EXIT=$?" > /mnt/e/projects/audio-jam/g.txt
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"
git push origin main >> /mnt/e/projects/audio-jam/g.txt 2>&1
echo "PUSH_EXIT=$?" >> /mnt/e/projects/audio-jam/g.txt
git log --oneline -1 >> /mnt/e/projects/audio-jam/g.txt 2>&1
