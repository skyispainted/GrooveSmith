#!/usr/bin/env bash
set +e
echo "=== validate MusicXML is well-formed + editable structure ==="
python - <<'PY'
import xml.etree.ElementTree as ET
p="/data/output/drums.musicxml"
tree=ET.parse(p)          # will raise if malformed
root=tree.getroot()
print("WELLFORMED_XML True root=", root.tag)
# count parts, measures, notes, rests
parts=root.findall(".//part")
measures=root.findall(".//measure")
notes=root.findall(".//note")
rests=root.findall(".//rest")
unpitched=root.findall(".//unpitched")
print("parts", len(parts), "measures", len(measures), "notes", len(notes), "rests", len(rests), "unpitched", len(unpitched))
ch=root.findall(".//midi-channel")
print("midi_channel_values", [c.text for c in ch])
# round-trip: re-open in music21 to prove it parses back (editability proxy)
from music21 import converte
s=converter.parse(p)
print("MUSIC21_REPARSE_OK note_events", len(list(s.recurse().notes)))
PY
echo "=== final artifact inventory (the deliverables) ==="
for f in drums.mid drums.musicxml drums.svg drums.pdf drums.png; do
  [ -f /data/output/$f ] && echo "OK  $f  $(stat -c%s /data/output/$f) bytes" || echo "MISSING $f"
done
