#!/usr/bin/env python3
"""VideoMind - Web interface for video processing pipeline."""

import os
import sys
import threading
import uuid
from datetime import datetime
from queue import Queue, Empty
from urllib.parse import unquote

from flask import Flask, render_template, request, redirect, url_for, Response, send_from_directory, abort

# Allow running from the project directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_OUTPUT_DIR, DEFAULT_WHISPER_MODEL, validate_config

app = Flask(__name__)

OUTPUT_DIR = os.path.abspath(DEFAULT_OUTPUT_DIR)

# In-memory job tracking: {job_id: {"status", "events" Queue, ...}}
jobs = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class JobLogger:
    """Captures print output and pushes it as SSE events."""

    def __init__(self, job_id):
        self.job_id = job_id
        self.queue = jobs[job_id]["events"]

    def emit(self, event_type, data):
        self.queue.put({"event": event_type, "data": data})

    def log(self, msg):
        self.emit("log", msg)

    def step(self, step_name, message):
        import json
        self.emit("step", json.dumps({"step": step_name, "message": message}))

    def done(self):
        self.emit("done", "ok")

    def fail(self, msg):
        self.emit("error_msg", msg)
        self.emit("failed", msg)


def _redirect_print(logger):
    """Context manager that redirects stdout to the job logger."""
    import io

    class LogWriter(io.TextIOBase):
        def write(self, s):
            text = s.rstrip('\n')
            if text:
                logger.log(text)
            return len(s)

    return LogWriter()


def _run_job(job_id):
    """Worker function that runs the full pipeline in a background thread."""
    job = jobs[job_id]
    logger = JobLogger(job_id)
    old_stdout = sys.stdout

    try:
        # Lazy-import pipeline modules (they have heavy deps like whisper, torch)
        from pipeline.downloader import download_audio
        from pipeline.extractor import extract_audio_from_folder
        from pipeline.transcriber import transcribe_audio
        from pipeline.formats import generate_visual_format

        # Redirect prints from pipeline modules to SSE
        sys.stdout = _redirect_print(logger)

        source_type = job["source_type"]
        model = job["model"]
        language = job["lang"]
        output_format = job["format"]
        visual_type = job.get("visual_type", "sketchnote")

        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # Step 1: Get audio
        logger.step("download", "Obtenint audio del video...")

        if source_type == "url":
            videos = download_audio(job["url"], OUTPUT_DIR)
        elif os.path.isfile(job["folder"]):
            from pipeline.extractor import extract_audio_from_file
            result = extract_audio_from_file(job["folder"], OUTPUT_DIR)
            videos = [result] if result else []
        else:
            videos = extract_audio_from_folder(job["folder"], OUTPUT_DIR)

        if not videos:
            logger.fail("No s'ha trobat cap video per processar.")
            job["status"] = "failed"
            return

        logger.log(f"Trobat(s) {len(videos)} video(s).")

        # Step 2-3: Process each video
        for i, video in enumerate(videos):
            title = video["title"]
            audio_path = video["audio_path"]
            video_dir = os.path.dirname(audio_path)

            if len(videos) > 1:
                logger.log(f"\n--- Video {i+1}/{len(videos)}: {title} ---")

            # Step 2: Transcribe
            logger.step("transcribe", f"Transcrivint: {title}...")
            result = transcribe_audio(audio_path, model_name=model, language=language)
            transcript = result["text"]

            if not transcript or len(transcript.strip()) < 20:
                logger.log("Transcripcio massa curta. Saltant mapa conceptual.")
                continue

            logger.log(f"Transcripcio completada ({len(transcript)} caracters).")

            # Step 3: Visual format
            format_labels = {
                "sketchnote": "sketchnote",
                "mindmap": "mapa mental",
                "infografia": "infografia",
            }
            format_label = format_labels.get(visual_type, visual_type)
            logger.step("mindmap", f"Generant {format_label}: {title}...")
            if not validate_config():
                logger.fail("ANTHROPIC_API_KEY no configurada. Revisa el fitxer .env.")
                job["status"] = "failed"
                return
            detected_language = result.get("language", "")
            try:
                generate_visual_format(
                    transcript, video_dir,
                    format_type=visual_type,
                    formats=output_format,
                    language=detected_language,
                )
            except Exception as e:
                logger.fail(f"Error generant {format_label}: {e}")
                job["status"] = "failed"
                return

            logger.log(f"{format_label.capitalize()} generat.")

        job["status"] = "done"
        logger.done()

    except Exception as e:
        logger.fail(f"Error inesperat: {e}")
        job["status"] = "failed"
    finally:
        sys.stdout = old_stdout


def _scan_library():
    """Scan the output directory and return a list of processed videos."""
    videos = []
    if not os.path.isdir(OUTPUT_DIR):
        return videos

    for name in sorted(os.listdir(OUTPUT_DIR)):
        video_dir = os.path.join(OUTPUT_DIR, name)
        if not os.path.isdir(video_dir):
            continue

        # Check which files exist
        files = set(os.listdir(video_dir))
        known_outputs = {
            "audio.mp3", "transcript.txt",
            "mindmap.html", "mindmap.md", "mindmap.json",
            "mindmap_tree.html", "mindmap_tree.md", "mindmap_tree.json",
            "infografia.html", "infografia.md", "infografia.json",
        }
        has_any_output = files & known_outputs
        if not has_any_output:
            continue

        # Get modification time for date display
        mtime = max(
            os.path.getmtime(os.path.join(video_dir, f))
            for f in files
            if os.path.isfile(os.path.join(video_dir, f))
        )
        date_str = datetime.fromtimestamp(mtime).strftime("%d/%m/%Y %H:%M")

        videos.append({
            "title": name,
            "date": date_str,
            "has_audio": "audio.mp3" in files,
            "has_transcript": "transcript.txt" in files,
            "has_html": "mindmap.html" in files,
            "has_md": "mindmap.md" in files,
            "has_json": "mindmap.json" in files,
            "has_mindmap_tree": "mindmap_tree.html" in files,
            "has_infografia": "infografia.html" in files,
        })

    # Sort by date, newest first
    videos.sort(key=lambda v: v["date"], reverse=True)
    return videos


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/classify", methods=["POST"])
def classify():
    """Classify an uploaded image's visual format type."""
    import json
    import tempfile
    from pipeline.image_classifier import classify_image

    file = request.files.get("image")
    if not file:
        return json.dumps({"error": "No image uploaded"}), 400

    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "png"
    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
        file.save(tmp)
        tmp_path = tmp.name

    try:
        result = classify_image(tmp_path)
        return json.dumps(result), 200, {"Content-Type": "application/json"}
    finally:
        os.unlink(tmp_path)


@app.route("/process", methods=["POST"])
def process():
    source_type = request.form.get("source_type", "url")
    model = request.form.get("model", DEFAULT_WHISPER_MODEL)
    lang = request.form.get("lang", "auto").strip() or "auto"
    fmt = request.form.get("format", "all")
    visual_type = request.form.get("visual_type", "sketchnote")

    # Validate input
    if source_type == "url":
        url = request.form.get("url", "").strip()
        if not url:
            return render_template("index.html", error="Cal introduir una URL de YouTube.")
        source_val = {"url": url}
    else:
        folder = request.form.get("folder", "").strip()
        if not folder:
            return render_template("index.html", error="Cal introduir la ruta d'una carpeta o fitxer.")
        if not os.path.isdir(folder) and not os.path.isfile(folder):
            return render_template("index.html", error=f"La ruta no existeix: {folder}")
        source_val = {"folder": folder}

    # Create job
    job_id = uuid.uuid4().hex[:12]
    jobs[job_id] = {
        "status": "running",
        "source_type": source_type,
        "model": model,
        "lang": lang,
        "format": fmt,
        "visual_type": visual_type,
        "events": Queue(),
        **source_val,
    }

    # Start worker thread
    t = threading.Thread(target=_run_job, args=(job_id,), daemon=True)
    t.start()

    return redirect(url_for("status", job_id=job_id))


@app.route("/status/<job_id>")
def status(job_id):
    if job_id not in jobs:
        abort(404)
    return render_template("status.html", job_id=job_id)


@app.route("/events/<job_id>")
def events(job_id):
    if job_id not in jobs:
        abort(404)

    def stream():
        q = jobs[job_id]["events"]
        while True:
            try:
                msg = q.get(timeout=30)
                yield f"event: {msg['event']}\ndata: {msg['data']}\n\n"
                # Stop streaming after terminal events
                if msg["event"] in ("done", "failed"):
                    break
            except Empty:
                # Send keepalive comment to prevent timeout
                yield ": keepalive\n\n"

    return Response(stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/library")
def library():
    videos = _scan_library()
    return render_template("library.html", videos=videos)


@app.route("/viewer/<path:title>")
def viewer(title):
    title = unquote(title)
    video_dir = os.path.join(OUTPUT_DIR, title)
    if not os.path.isdir(video_dir):
        abort(404)

    files_present = set(os.listdir(video_dir))
    files = {
        "audio": "audio.mp3" in files_present,
        "transcript": "transcript.txt" in files_present,
        "srt": "transcript.srt" in files_present,
        "html": "mindmap.html" in files_present,
        "md": "mindmap.md" in files_present,
        "json": "mindmap.json" in files_present,
        "mindmap_tree_html": "mindmap_tree.html" in files_present,
        "mindmap_tree_md": "mindmap_tree.md" in files_present,
        "mindmap_tree_json": "mindmap_tree.json" in files_present,
        "infografia_html": "infografia.html" in files_present,
        "infografia_md": "infografia.md" in files_present,
        "infografia_json": "infografia.json" in files_present,
    }

    # Load transcript text
    transcript = ""
    transcript_path = os.path.join(video_dir, "transcript.txt")
    if os.path.isfile(transcript_path):
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript = f.read()

    return render_template("viewer.html", title=title, files=files, transcript=transcript)


@app.route("/output/<path:filepath>")
def serve_output(filepath):
    filepath = unquote(filepath)
    return send_from_directory(OUTPUT_DIR, filepath)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("VideoMind web: http://localhost:5000")
    print(f"Output dir:    {OUTPUT_DIR}")
    app.run(debug=True, host="0.0.0.0", port=5000, threaded=True)
