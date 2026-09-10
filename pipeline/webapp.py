#!/usr/bin/env python3
"""GrooveSmith WebUI backend (FastAPI).

Endpoints:
  GET  /                      -> single-page UI
  POST /api/upload            -> accept audio, start async pipeline, return job id
  GET  /api/status/{job_id}   -> job progress/logs/result
  GET  /api/file/{job_id}/{name} -> download a produced artifact (mid/musicxml/pdf/png/svg)
  GET  /api/svg/{job_id}      -> rendered score SVG (inline preview)
  POST /api/import            -> accept a MIDI or MusicXML file, render to SVG, return it

Self-hosted, single-machine: jobs live in memory + a per-job dir under DATA_ROOT.
Pipeline stages are reused from run_pipeline.py.
"""
import os
import shutil
import threading
import time
import traceback
import uuid

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, Response, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import run_pipeline as pl

DATA_ROOT = os.environ.get("DATA_ROOT", "/data")
JOBS_DIR = os.path.join(DATA_ROOT, "jobs")
DEVICE = os.environ.get("DEVICE", "cpu")
os.makedirs(JOBS_DIR, exist_ok=True)

app = FastAPI(title="GrooveSmith")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# in-memory job registry
JOBS = {}
LOCK = threading.Lock()
PROC_LOCK = threading.Lock()  # serialize heavy GPU/CPU processing across jobs

AUDIO_EXT = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
MIDI_EXT = {".mid", ".midi"}
XML_EXT = {".musicxml", ".xml", ".mxl"}

_MIME = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".flac": "audio/flac",
         ".ogg": "audio/ogg", ".m4a": "audio/mp4"}


def range_file_response(path, request):
    """Serve a file with HTTP Range support (206) so <audio> can seek reliably."""
    file_size = os.path.getsize(path)
    ext = os.path.splitext(path)[1].lower()
    ctype = _MIME.get(ext, "application/octet-stream")
    range_header = request.headers.get("range") or request.headers.get("Range")
    common = {"accept-ranges": "bytes", "content-type": ctype}

    if not range_header or not range_header.startswith("bytes="):
        return FileResponse(path, media_type=ctype, headers={"accept-ranges": "bytes"})

    try:
        rng = range_header.split("=", 1)[1]
        start_s, end_s = (rng.split("-", 1) + [""])[:2]
        start = int(start_s) if start_s else 0
        end = int(end_s) if end_s else file_size - 1
    except Exception:
        start, end = 0, file_size - 1
    start = max(0, start)
    end = min(end, file_size - 1)
    if start > end:
        start = 0
    length = end - start + 1

    def iterfile():
        with open(path, "rb") as f:
            f.seek(start)
            remaining = length
            chunk = 64 * 1024
            while remaining > 0:
                data = f.read(min(chunk, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "accept-ranges": "bytes",
        "content-range": f"bytes {start}-{end}/{file_size}",
        "content-length": str(length),
    }
    return StreamingResponse(iterfile(), status_code=206, media_type=ctype, headers=headers)


def set_job(job_id, **kw):
    with LOCK:
        JOBS[job_id].update(kw)


def add_log(job_id, line):
    with LOCK:
        JOBS[job_id]["logs"].append(line)


VEROVIO_RESOURCE = os.path.join(os.path.dirname(__import__("verovio").__file__), "data")


def render_svg(xml_path, out_svg, out_timemap=None):
    import verovio
    tk = verovio.toolkit(False)
    tk.setResourcePath(VEROVIO_RESOURCE)
    tk.setOptions({"pageHeight": 60000, "pageWidth": 2100, "scale": 40, "adjustPageHeight": True})
    if not tk.loadFile(xml_path):
        raise RuntimeError("verovio failed to load " + xml_path)
    tk.redoLayout()
    with open(out_svg, "w") as fh:
        fh.write(tk.renderToSVG(1))
    if out_timemap:
        try:
            tm = tk.renderToTimemap()
            if not isinstance(tm, str):
                import json as _json
                tm = _json.dumps(tm)
            with open(out_timemap, "w") as fh:
                fh.write(tm)
        except Exception:
            with open(out_timemap, "w") as fh:
                fh.write("[]")
    return out_svg, 1


def worker(job_id, audio_path):
    jd = os.path.join(JOBS_DIR, job_id)
    # serialize heavy processing: only one job separates/transcribes at a time
    # (prevents GPU OOM / CPU thrash from concurrent demucs runs).
    with PROC_LOCK:
        try:
            set_job(job_id, status="running", progress=5, stage="separation")
            add_log(job_id, "STAGE 1/5 separation (Demucs)")
            drums = pl.separate(audio_path, jd, DEVICE)
            set_job(job_id, progress=45, stage="transcription")
            add_log(job_id, "STAGE 2/5 transcription (ADTOF)")
            mid = pl.transcribe(drums, jd, DEVICE)
            set_job(job_id, progress=70, stage="musicxml")
            add_log(job_id, "STAGE 3/5 MIDI -> MusicXML (music21)")
            bpm = pl.estimate_bpm(drums)
            add_log(job_id, "estimated bpm = " + str(bpm))
            with LOCK:
                j0 = JOBS.get(job_id, {})
                fname = j0.get("filename") or ""
                difficulty = j0.get("difficulty") or "standard"
            title = os.path.splitext(os.path.basename(fname))[0] or None
            add_log(job_id, "difficulty = " + difficulty)
            xml = pl.to_musicxml(mid, jd, bpm=bpm, title=title, difficulty=difficulty)
            set_job(job_id, progress=85, stage="render")
            add_log(job_id, "STAGE 4/5 render (verovio + cairosvg)")
            svg, pdf, png = pl.render(xml, jd)
            timemap = os.path.join(jd, "timemap.json")
            # Render the score to audio so the page can play it through an <audio>
            # element. <midi-player> schedules notes from main-thread timers, which
            # Chrome throttles to ~1/s in a hidden tab, so synthesised playback dies
            # in the background while <audio> keeps going.
            add_log(job_id, "STAGE 5/5 score audio (drum samples)")
            try:
                score = pl.render_score_audio(mid, jd)
            except Exception as e:
                add_log(job_id, "score audio failed: " + repr(e))
                score = None
            add_log(job_id, "done")
            set_job(job_id, status="done", progress=100, stage="done",
                    outputs={"midi": mid, "musicxml": xml, "svg": svg, "pdf": pdf,
                             "png": png, "original": audio_path, "drums": drums,
                             "score": score, "timemap": timemap, "title": title})
        except Exception as e:
            add_log(job_id, "ERROR: " + repr(e))
            add_log(job_id, traceback.format_exc())
            set_job(job_id, status="error", stage="error")


@app.post("/api/upload")
async def upload(file: UploadFile = File(...), difficulty: str = Form("standard")):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in AUDIO_EXT:
        raise HTTPException(400, "unsupported audio type: " + ext)
    if difficulty not in ("simple", "standard", "full"):
        difficulty = "standard"
    job_id = uuid.uuid4().hex[:12]
    jd = os.path.join(JOBS_DIR, job_id)
    os.makedirs(jd, exist_ok=True)
    audio_path = os.path.join(jd, "input" + ext)
    with open(audio_path, "wb") as fh:
        shutil.copyfileobj(file.file, fh)
    with LOCK:
        JOBS[job_id] = {"status": "queued", "progress": 0, "stage": "queued",
                        "logs": [], "outputs": {}, "filename": file.filename,
                        "difficulty": difficulty, "created": time.time()}
    threading.Thread(target=worker, args=(job_id, audio_path), daemon=True).start()
    return {"job_id": job_id}


@app.get("/api/status/{job_id}")
async def status(job_id: str):
    with LOCK:
        j = JOBS.get(job_id)
        if not j:
            raise HTTPException(404, "no such job")
        return dict(j)


@app.get("/api/file/{job_id}/{name}")
async def get_file(job_id: str, name: str):
    with LOCK:
        j = JOBS.get(job_id)
    if not j or j.get("status") != "done":
        raise HTTPException(404, "not ready")
    p = j["outputs"].get(name)
    if not p or not os.path.exists(p):
        raise HTTPException(404, "no such artifact")
    return FileResponse(p, filename=os.path.basename(p))


@app.get("/api/svg/{job_id}")
async def get_svg(job_id: str):
    with LOCK:
        j = JOBS.get(job_id)
    if not j or j.get("status") != "done":
        raise HTTPException(404, "not ready")
    svg = j["outputs"].get("svg")
    if not svg or not os.path.exists(svg):
        raise HTTPException(404, "no svg")
    return Response(open(svg).read(), media_type="image/svg+xml")


@app.get("/api/timemap/{job_id}")
async def get_timemap(job_id: str):
    with LOCK:
        j = JOBS.get(job_id)
    if not j or j.get("status") != "done":
        raise HTTPException(404, "not ready")
    tm = j["outputs"].get("timemap")
    if not tm or not os.path.exists(tm):
        return Response("[]", media_type="application/json")
    return Response(open(tm).read(), media_type="application/json")


@app.get("/api/audio/{job_id}/{kind}")
async def get_audio(job_id: str, kind: str, request: Request):
    """kind = original (uploaded mix) | drums (separated stem) | score (rendered drums)."""
    if kind not in ("original", "drums", "score"):
        raise HTTPException(400, "kind must be original, drums or score")
    with LOCK:
        j = JOBS.get(job_id)
    if not j or j.get("status") != "done":
        raise HTTPException(404, "not ready")
    p = j["outputs"].get(kind)
    if not p or not os.path.exists(p):
        raise HTTPException(404, "no such audio")
    return range_file_response(p, request)


@app.get("/api/midi/{job_id}")
async def get_midi(job_id: str):
    with LOCK:
        j = JOBS.get(job_id)
    if not j or j.get("status") != "done":
        raise HTTPException(404, "not ready")
    p = j["outputs"].get("midi")
    if not p or not os.path.exists(p):
        raise HTTPException(404, "no midi")
    return FileResponse(p, media_type="audio/midi")


IMPORTS = {}


@app.post("/api/import")
async def import_score(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    imp_id = "imp_" + uuid.uuid4().hex[:10]
    jd = os.path.join(JOBS_DIR, imp_id)
    os.makedirs(jd, exist_ok=True)
    src = os.path.join(jd, "src" + ext)
    with open(src, "wb") as fh:
        shutil.copyfileobj(file.file, fh)
    midi_path = None
    imp_title = os.path.splitext(os.path.basename(file.filename or ""))[0] or None
    try:
        if ext in MIDI_EXT:
            xml = pl.to_musicxml(src, jd, title=imp_title)
            midi_path = src
        elif ext in XML_EXT:
            xml = src
            # also produce a MIDI so the imported score can be played
            try:
                from music21 import converte
                m = os.path.join(jd, "from_xml.mid")
                converter.parse(src).write("midi", fp=m)
                midi_path = m
            except Exception:
                midi_path = None
        else:
            raise HTTPException(400, "unsupported score type: " + ext)
        out_svg = os.path.join(jd, "preview.svg")
        out_tm = os.path.join(jd, "timemap.json")
        render_svg(xml, out_svg, out_timemap=out_tm)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, "render failed: " + repr(e))
    with LOCK:
        IMPORTS[imp_id] = {"svg": out_svg, "midi": midi_path, "timemap": out_tm}
    return JSONResponse({"import_id": imp_id, "has_midi": midi_path is not None})


@app.get("/api/import/{imp_id}/svg")
async def import_svg(imp_id: str):
    with LOCK:
        rec = IMPORTS.get(imp_id)
    if not rec:
        raise HTTPException(404, "no such import")
    return Response(open(rec["svg"]).read(), media_type="image/svg+xml")


@app.get("/api/import/{imp_id}/midi")
async def import_midi(imp_id: str):
    with LOCK:
        rec = IMPORTS.get(imp_id)
    if not rec or not rec.get("midi") or not os.path.exists(rec["midi"]):
        raise HTTPException(404, "no midi for this import")
    return FileResponse(rec["midi"], media_type="audio/midi")


@app.get("/api/import/{imp_id}/timemap")
async def import_timemap(imp_id: str):
    with LOCK:
        rec = IMPORTS.get(imp_id)
    if not rec or not rec.get("timemap") or not os.path.exists(rec["timemap"]):
        return Response("[]", media_type="application/json")
    return Response(open(rec["timemap"]).read(), media_type="application/json")


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


HTML_PAGE = open(os.path.join(os.path.dirname(__file__), "index.html")).read()
