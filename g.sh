#!/usr/bin/env bash
cd /mnt/e/projects/audio-jam
rm -f bc.txt fx.txt c.txt gs.txt rb.log fixcu.py 2>/dev/null
rm -f pipeline/_gridstat.py pipeline/_beamcount.py pipeline/_gen1.py pipeline/_rend.py 2>/dev/null
rm -f data/cmp.* data/inspect.musicxml data/fixed.* 2>/dev/null
git add -A
git commit -q -m "notation: hi-hat/ride continuity pass to fill AI-missed cymbal hits so the top line beams into clean runs (simple/standard on, full stays faithful) -> far fewer isolated notes" >/dev/null 2>&1
echo "COMMIT_EXIT=$?" > /mnt/e/projects/audio-jam/g.txt
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"
git push origin main >> /mnt/e/projects/audio-jam/g.txt 2>&1
echo "PUSH_EXIT=$?" >> /mnt/e/projects/audio-jam/g.txt
git log --oneline -1 >> /mnt/e/projects/audio-jam/g.txt 2>&1
