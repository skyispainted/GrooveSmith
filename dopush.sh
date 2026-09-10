#!/usr/bin/env bash
cd /mnt/e/projects/audio-jam
rm -f _s.txt
git rm --cached --ignore-unmatch g.sh > /dev/null 2>&1
grep -qxF '/g.sh' .gitignore || echo '/g.sh' >> .gitignore
grep -qxF '/gs.sh' .gitignore || echo '/gs.sh' >> .gitignore
git add -A
git commit -q -m "chore: remove stray helper script from repo, ignore scratch scripts" > /mnt/e/projects/audio-jam/p.txt 2>&1
echo "COMMIT_EXIT=$?" >> /mnt/e/projects/audio-jam/p.txt
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"
git push origin main >> /mnt/e/projects/audio-jam/p.txt 2>&1
echo "PUSH_EXIT=$?" >> /mnt/e/projects/audio-jam/p.txt
git status -sb >> /mnt/e/projects/audio-jam/p.txt 2>&1
git log --oneline -1 >> /mnt/e/projects/audio-jam/p.txt 2>&1
