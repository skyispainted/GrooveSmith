#!/usr/bin/env bash
O=/mnt/e/projects/audio-jam/chk.txt
F=/mnt/e/projects/audio-jam/pipeline/index.html
: > "$O"
for t in startHlLoop stopHlLoop requestAnimationFrame cancelAnimationFrame "querySelector('.stage')" lastScrollT; do
  echo "$t : $(grep -c -- "$t" "$F")" >> "$O"
done
python3 - << 'PY' >> "$O" 2>&1
import re
s=open("/mnt/e/projects/audio-jam/pipeline/index.html").read()
m=re.search(r"<script>(.*)</script>", s, re.S); js=m.group(1) if m else ""
print("brace",js.count("{")-js.count("}"),"paren",js.count("(")-js.count(")"),"bracket",js.count("[")-js.count("]"))
for bad in ["requestAnimationFram ","cancelAnimationFram ","performance.no ","scrollTo ","getBoundingClientRec "]:
    if bad in s: print("SUSPECT",repr(bad))
print("ok")
PY
