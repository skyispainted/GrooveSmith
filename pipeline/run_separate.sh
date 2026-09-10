#!/usr/bin/env bash
# Run Demucs separation on the test audio. Device via $DEVICE (cpu default).
set -e
DEV="${DEVICE:-cpu}"
echo "=== validate input wav ==="
python - <<'PY'
import soundfile as sf
info = sf.info("/data/input/test_drums.wav")
print("frames", info.frames, "sr", info.samplerate, "ch", info.channels, "dur", round(info.duration,2))
PY
echo "=== demucs separate (device=$DEV) ==="
START=$(date +%s)
demucs -d "$DEV" -n htdemucs -o /data/output/demucs "/data/input/test_drums.wav" 2>&1 | tail -8
END=$(date +%s)
echo "SEPARATION_SECONDS=$((END-START))"
echo "=== outputs ==="
find /data/output/demucs -name "*.wav" | sort
echo "=== drums stem info ==="
python - <<'PY'
import soundfile as sf, glob, numpy as np
for f in sorted(glob.glob("/data/output/demucs/**/drums.wav", recursive=True)):
    x,sr=sf.read(f)
    print("DRUMS_STEM", f, "sr",sr,"rms",round(float(np.sqrt(np.mean(x**2))),4))
PY
