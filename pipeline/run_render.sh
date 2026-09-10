#!/usr/bin/env bash
set +e
echo "=== install music21 + verovio (pypi, no proxy) ==="
pip install --timeout 120 --retries 5 "music21==9.1.0" verovio >/tmp/m.log 2>&1 && echo INSTALL_OK || { echo INSTALL_FAIL; tail -20 /tmp/m.log; }
echo "=== MIDI -> MusicXML via music21 ==="
python - <<'PY'
from music21 import converter, environment
import os
mid="/data/output/drums.mid"
s=converter.parse(mid)
xml="/data/output/drums.musicxml"
s.write("musicxml", fp=xml)
print("MUSICXML_WRITTEN", os.path.exists(xml), "bytes", os.path.getsize(xml))
# report structure
parts=s.parts if hasattr(s,'parts') else []
print("n_parts", len(parts))
notes=list(s.recurse().notes)
print("n_note_events", len(notes))
# is it recognized as percussion / unpitched?
from music21 import percussion, note
unp=[n for n in s.recurse().notes if isinstance(n, (percussion.PercussionChord,)) or 'Unpitched' in type(n).__name__]
print("unpitched_events", len(unp))
PY
echo "=== MusicXML head ==="
head -30 /data/output/drums.musicxml
echo "=== Verovio: MusicXML -> SVG (headless, no display) ==="
python - <<'PY'
import verovio, os
tk=verovio.toolkit()
ok=tk.loadFile("/data/output/drums.musicxml")
print("verovio_load", ok)
tk.setOptions({"pageHeight":2000,"pageWidth":1500,"scale":40})
tk.redoLayout()
n=tk.getPageCount()
print("pages", n)
svg=tk.renderToSVG(1)
open("/data/output/drums.svg","w").write(svg)
print("SVG_WRITTEN", os.path.getsize("/data/output/drums.svg"))
PY
ls -la /data/output/
