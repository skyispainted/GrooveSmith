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


def transcribe(drums_wav, outdir, device):
    mid = os.path.join(outdir, "drums.mid")
    _run_with_cpu_fallback(
        lambda d: ["adtof", "--audio", drums_wav, "--out", mid, "--device", d],
        device,
    )
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


def to_musicxml(mid, outdir, bpm=None, title=None):
    # Build proper drum-set notation (percussion clef, unpitched notes at standard
    # staff positions, x-noteheads for cymbals/hi-hat) instead of plain pitched notes.
    import drum_notation
    xml = os.path.join(outdir, "drums.musicxml")
    sc = drum_notation.build_drum_score(mid, bpm=bpm, title=title)
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
        log("STAGE 1/4 separation (Demucs htdemucs)")
        drums = separate(args.input, args.outdir, dev)
    log("drums stem: " + drums)

    log("STAGE 2/4 transcription (ADTOF-pytorch)")
    mid = transcribe(drums, args.outdir, dev)

    bpm = estimate_bpm(drums)
    log("estimated bpm = " + str(bpm))

    log("STAGE 3/4 MIDI to MusicXML (music21)")
    xml = to_musicxml(mid, args.outdir, bpm=bpm)

    log("STAGE 4/4 render to SVG/PDF/PNG (verovio + cairosvg)")
    svg, pdf, png = render(xml, args.outdir)

    summary = {
        "device": dev,
        "elapsed_sec": round(time.time() - t0, 1),
        "outputs": {"midi": mid, "musicxml": xml, "svg": svg, "pdf": pdf, "png": png},
    }
    with open(os.path.join(args.outdir, "pipeline_result.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    log("DONE " + json.dumps(summary))


if __name__ == "__main__":
    main()
