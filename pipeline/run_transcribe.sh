#!/usr/bin/env bash
# Transcribe the separated drums stem to MIDI using ADTOF-pytorch.
set -e
DEV="${DEVICE:-cpu}"
IN="/data/output/demucs/htdemucs/test_drums/drums.wav"
OUT="/data/output/drums.mid"
echo "=== adtof transcribe (device=$DEV) ==="
START=$(date +%s)
adtof --audio "$IN" --out "$OUT" --device "$DEV" 2>&1 | tail -15
END=$(date +%s)
echo "TRANSCRIBE_SECONDS=$((END-START))"
echo "=== midi analysis ==="
python - <<'PY'
import pretty_midi, collections, os
p="/data/output/drums.mid"
print("exists", os.path.exists(p), "bytes", os.path.getsize(p) if os.path.exists(p) else 0)
pm=pretty_midi.PrettyMIDI(p)
print("duration", round(pm.get_end_time(),2))
for inst in pm.instruments:
    print("instrument is_drum=", inst.is_drum, "program=", inst.program, "n_notes=", len(inst.notes))
    c=collections.Counter(n.pitch for n in inst.notes)
    # GM drum map names
    names={35:"AcousticBassDrum",36:"BassDrum1",38:"AcousticSnare",40:"ElecSnare",42:"ClosedHH",46:"OpenHH",49:"CrashCymbal",51:"RideCymbal",45:"LowTom",47:"MidTom",48:"HiMidTom",50:"HighTom",43:"HighFloorTom",41:"LowFloorTom"}
    for pitch,cnt in sorted(c.items()):
        print(f"  pitch {pitch} ({names.get(pitch,'?')}): {cnt} hits")
    # sample first 8 onsets
    onsets=sorted(n.start for n in inst.notes)[:8]
    print("  first onsets:", [round(x,3) for x in onsets])
    vels=sorted(set(n.velocity for n in inst.notes))
    print("  velocity range:", min(n.velocity for n in inst.notes), "-", max(n.velocity for n in inst.notes))
PY
