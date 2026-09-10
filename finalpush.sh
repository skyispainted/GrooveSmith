#!/usr/bin/env bash
cd /mnt/e/projects/audio-jam
O=/mnt/e/projects/audio-jam/gitstate.txt
: > "$O"
git rm --cached --ignore-unmatch push.sh >> "$O" 2>&1
# ensure push.sh is ignored going forward
grep -qxF '/push.sh' .gitignore || echo '/push.sh' >> .gitignore
git add -A
git commit -q -m "chore: drop stray push.sh helper from repo, ignore it" >> "$O" 2>&1
echo "COMMIT_EXIT=$?" >> "$O"
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"
git push origin main >> "$O" 2>&1
echo "PUSH_EXIT=$?" >> "$O"
git status -sb >> "$O" 2>&1
git log --oneline -1 >> "$O" 2>&1
