#!/usr/bin/env bash
cd /mnt/e/projects/audio-jam
rm -f chk.sh chk.txt rb.log range.sh range.txt range2.sh range2.txt cc.txt 2>/dev/null
git add -A
git commit -q -m "fix progress bar: add HTTP Range (206) support to /api/audio so original song is seekable; lock seekbar during drag until 'seeked' fires so it no longer snaps back / desyncs"
echo "COMMIT_EXIT=$?" > /mnt/e/projects/audio-jam/pr.txt
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"
git push origin main >> /mnt/e/projects/audio-jam/pr.txt 2>&1
echo "PUSH_EXIT=$?" >> /mnt/e/projects/audio-jam/pr.txt
git log --oneline -1 >> /mnt/e/projects/audio-jam/pr.txt 2>&1
