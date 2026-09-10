#!/usr/bin/env python3
"""audio-jam unified pipeline.

audio -> drum stem (Demucs) -> MIDI (ADTOF) -> MusicXML (music21) -> SVG/PDF/PNG (Verovio+cairosvg)

Usage inside container:
    python run_pipeline.py --input /data/input/song.wav --outdir /data/output --device cpu

Device precedence: --device flag > DEVICE env > cpu.
"""
import argparse
import glob
import json
import os
import subprocess
import time


def log(msg):
    print("[audio-jam] " + str(msg), flush=True)


def run(cmd):
    log("run: " + " ".join(cmd))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        tail = "\n".join((proc.stdout or "").splitlines()[-25:])
        log("command failed (exit %d):\n%s" % (proc.returncode, tail))
        raise subprocess.CalledProcessError(proc.returncode, cmd, output=proc.stdout)


def _run_with_cpu_fallback(build_cmd, device):
    """Run a command on the requested device; if it was cuda and failed, retry on cpu.
    build_cmd(dev) -> list[str]."""
    try:
        run(build_cmd(device))
        return device
    except subprocess.CalledProcessError as e:
        if device == "cuda":
            log("cuda run failed (%r); falling back to CPU" % e)
            run(build_cmd("cpu"))
            return "cpu"
        raise


def separate(inp, outdir, device):
    demucs_out = os.path.join(outdir, "demucs")
    _run_with_cpu_fallback(
        lambda d: ["demucs", "-d", d, "-n", "htdemucs", "-o", demucs_out, inp],
        device,
    )
    stem = os.path.splitext(os.path.basename(inp))[0]
    hits = glob.glob(os.path.join(demucs_out, "htdemucs", stem, "drums.wav"))
    if not hits:
        raise RuntimeError("drums stem not produced by demucs")
    return hits[0]


def restore_velocity(drums_wav, mid_path):
    """Write the drum stem's real dynamics back into the MIDI.

    ADTOF's CLI hardcodes velocity=100 for every note (adtof_pytorch/cli.py:125 ->
    post_processing.py:140), so loudness is discarded entirely. A hi-hat that is
    barely audible in the mix comes out exactly as loud as the snare, which reads as
    a metronomic tick rather than music. (Verified: every note in a produced
    drums.mid has velocity exactly 100.)

    No notes are added or removed -- only the loudness dimension is restored, by
    measuring the stem in a short window at each onset. The mapping is calibrated
    against the whole stem (not per piece), so the balance between kick/snare/hat is
    the one actually present in the audio.

    Any failure leaves the previous behaviour (velocity 100) intact rather than
    breaking the pipeline.
    """
    try:
        import numpy as np
        import librosa
        import pretty_midi

        y, sr = librosa.load(drums_wav, sr=None, mono=True)
        pm = pretty_midi.PrettyMIDI(mid_path)
        notes = [n for inst in pm.instruments for n in inst.notes]
        if not notes or y.size == 0:
            return

        pre, post = 0.005, 0.045          # window around each onset
        rms = np.empty(len(notes), dtype=float)
        for i, n in enumerate(notes):
            i0 = max(0, int((float(n.start) - pre) * sr))
            i1 = min(len(y), int((float(n.start) + post) * sr))
            seg = y[i0:i1]
            rms[i] = float(np.sqrt(np.mean(np.square(seg)))) if seg.size else 0.0

        db = 20.0 * np.log10(np.maximum(rms, 1e-7))
        # robust reference: the single loudest hit may be a separation artefact
        ref = float(np.percentile(db, 99))
        RANGE, VLO = 30.0, 20              # dB spanned, and the velocity floor
        frac = np.clip(1.0 - (ref - db) / RANGE, 0.0, 1.0)
        vel = np.round(VLO + (127 - VLO) * frac).astype(int)
        for n, v in zip(notes, vel):
            n.velocity = int(v)
        pm.write(mid_path)
        log("velocity restored: ref=%.1fdB range=%.0fdB -> vel %d..%d (median %d)"
            % (ref, RANGE, int(vel.min()), int(vel.max()), int(np.median(vel))))
    except Exception as e:
        log("velocity restore skipped (%r); leaving velocity=100" % e)


def transcribe(drums_wav, outdir, device):
    mid = os.path.join(outdir, "drums.mid")
    _run_with_cpu_fallback(
        lambda d: ["adtof", "--audio", drums_wav, "--out", mid, "--device", d],
        device,
    )
    restore_velocity(drums_wav, mid)
    return mid


def estimate_bpm(drums_wav):
    """Estimate tempo from the drums stem; fall back to None on failure."""
    try:
        import librosa
        y, sr = librosa.load(drums_wav, sr=22050, mono=True)
        tempo_val, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(tempo_val if not hasattr(tempo_val, "__len__") else tempo_val[0])
        # fold into a musically sane range
        while bpm and bpm < 70:
            bpm *= 2
        while bpm and bpm > 180:
            bpm /= 2
        return round(bpm, 2) if bpm and bpm > 0 else None
    except Exception as e:
        log("bpm estimate failed: " + repr(e))
        return None


def to_musicxml(mid, outdir, bpm=None, title=None, difficulty="standard"):
    # Build proper drum-set notation (percussion clef, unpitched notes at standard
    # staff positions, x-noteheads for cymbals/hi-hat) instead of plain pitched notes.
    import drum_notation
    xml = os.path.join(outdir, "drums.musicxml")
    sc = drum_notation.build_drum_score(mid, bpm=bpm, title=title, difficulty=difficulty)
    from music21.musicxml import m21ToXml
    data = m21ToXml.GeneralObjectExporter(sc).parse()
    with open(xml, "wb") as fh:
        fh.write(data)
    return xml


def render(xml, outdir):
    import verovio
    import cairosvg
    res = os.path.join(os.path.dirname(verovio.__file__), "data")
    tk = verovio.toolkit(False)
    tk.setResourcePath(res)
    # tall single page so the whole score + playback highlight live in one SVG
    tk.setOptions({"pageHeight": 60000, "pageWidth": 2100, "scale": 40, "adjustPageHeight": True})
    tk.loadFile(xml)
    tk.redoLayout()
    svg = os.path.join(outdir, "drums.svg")
    with open(svg, "w") as fh:
        fh.write(tk.renderToSVG(1))
    # timemap: [{tstamp(ms), on:[svg element ids], ...}] for playback highlight
    tmap = os.path.join(outdir, "timemap.json")
    try:
        tm = tk.renderToTimemap()
        if not isinstance(tm, str):
            import json as _json
            tm = _json.dumps(tm)
        with open(tmap, "w") as fh:
            fh.write(tm)
    except Exception as e:
        log("timemap failed: " + repr(e))
        with open(tmap, "w") as fh:
            fh.write("[]")
    pdf = os.path.join(outdir, "drums.pdf")
    png = os.path.join(outdir, "drums.png")
    cairosvg.svg2pdf(url=svg, write_to=pdf)
    cairosvg.svg2png(url=svg, write_to=png, output_width=1500)
    return svg, pdf, png


# --- score audio rendering ---------------------------------------------------
# The browser plays the score with <midi-player>, which schedules notes from
# main-thread timers. Chrome throttles those to ~1/s in a HIDDEN tab, so the
# synthesised drums die the moment the tab is backgrounded while the <audio>
# element (original track) keeps going. Rendering the MIDI to a real audio file
# lets the page play the score through an <audio> element as well -- ordinary
# media playback, immune to that throttling, and it picks up the browser's media
# controls for free.
#
# The samples are exactly the ones the browser player uses (static/soundfonts/
# sgm_plus), chosen by the same nearest-velocity-layer rule, so the sound is the
# same as what <midi-player> produced.
_SF_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "static", "soundfonts", "sgm_plus", "percussion")
_SF_VELS = [15, 31, 47, 63, 79, 95, 111, 127]     # instrument.json "velocities"
_SF_MIN_PITCH, _SF_MAX_PITCH = 35, 81              # instrument.json min/maxPitch
_SF_SECONDS = 3.0                                  # instrument.json durationSeconds


def render_score_audio(mid_path, outdir, sr=44100):
    """MIDI -> mp3, mixed from the app's drum samples. Returns the mp3 path."""
    import numpy as np
    import pretty_midi
    import soundfile as sf

    if not os.path.isdir(_SF_DIR):
        raise RuntimeError("drum samples not found at " + _SF_DIR)

    pm = pretty_midi.PrettyMIDI(mid_path)
    notes = sorted((float(n.start), int(n.pitch), int(n.velocity))
                   for inst in pm.instruments for n in inst.notes)
    if not notes:
        return None

    total = int((pm.get_end_time() + _SF_SECONDS) * sr) + 1
    mix = np.zeros((total, 2), dtype=np.float32)

    cache = {}
    cut = int(_SF_SECONDS * sr)

    def sample(pitch, vel):
        key = (pitch, vel)
        if key not in cache:
            y, _ = sf.read(os.path.join(_SF_DIR, "p%d_v%d.mp3" % (pitch, vel)),
                           dtype="float32", always_2d=True)
            cache[key] = np.ascontiguousarray(y[:cut])
        return cache[key]

    for start, pitch, vel in notes:
        p = min(_SF_MAX_PITCH, max(_SF_MIN_PITCH, pitch))
        v = min(_SF_VELS, key=lambda L: abs(L - vel))
        s = sample(p, v)
        i0 = int(start * sr)
        i1 = min(total, i0 + len(s))
        if i1 > i0:
            mix[i0:i1] += s[:i1 - i0] * max(0.02, vel / float(v))

    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    if peak > 0:
        mix *= 0.99 / peak

    wav = os.path.join(outdir, "score.wav")
    mp3 = os.path.join(outdir, "score.mp3")
    sf.write(wav, mix, sr)
    # a 4-minute stereo wav is ~40 MB; mp3 brings that to ~5 MB
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-b:a", "192k", mp3])
    try:
        os.remove(wav)
    except OSError:
        pass
    return mp3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--outdir", default="/data/output")
    ap.add_argument("--device", default=os.environ.get("DEVICE", "cpu"))
    ap.add_argument("--skip-separate", action="store_true")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    dev = args.device
    log("device = " + dev)
    t0 = time.time()

    if args.skip_separate:
        drums = args.input
        log("skip separation; input treated as drums stem")
    else:
        log("STAGE 1/5 separation (Demucs htdemucs)")
        drums = separate(args.input, args.outdir, dev)
    log("drums stem: " + drums)

    log("STAGE 2/5 transcription (ADTOF-pytorch)")
    mid = transcribe(drums, args.outdir, dev)

    bpm = estimate_bpm(drums)
    log("estimated bpm = " + str(bpm))

    log("STAGE 3/5 MIDI to MusicXML (music21)")
    xml = to_musicxml(mid, args.outdir, bpm=bpm)

    log("STAGE 4/5 render to SVG/PDF/PNG (verovio + cairosvg)")
    svg, pdf, png = render(xml, args.outdir)

    log("STAGE 5/5 score audio (drum samples -> mp3)")
    score = render_score_audio(mid, args.outdir)

    summary = {
        "device": dev,
        "elapsed_sec": round(time.time() - t0, 1),
        "outputs": {"midi": mid, "musicxml": xml, "svg": svg, "pdf": pdf, "png": png,
                    "score": score},
    }
    with open(os.path.join(args.outdir, "pipeline_result.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    log("DONE " + json.dumps(summary))


if __name__ == "__main__":
    main()
