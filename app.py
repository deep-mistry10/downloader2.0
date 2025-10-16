#!/usr/bin/env python3
"""
Cloud-ready Flask Video/Audio Downloader using yt-dlp
Deploy directly to Render, Railway, or Replit.
"""

import os
import uuid
import shutil
import threading
from pathlib import Path
from flask import Flask, request, send_file, redirect, url_for, flash, render_template_string
import yt_dlp

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Temporary download folder
BASE_TEMP = Path("./downloads_temp")
BASE_TEMP.mkdir(exist_ok=True)

# Simple HTML template embedded
INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Video/Audio Downloader</title>
<style>
body{font-family:Arial,sans-serif;background:#f6f7fb;padding:32px;}
.card{max-width:720px;margin:40px auto;background:white;padding:24px;border-radius:12px;box-shadow:0 6px 22px rgba(0,0,0,0.08);}
input,select{width:100%;padding:12px;margin:8px 0 16px 0;border-radius:8px;border:1px solid #ddd;}
button{background:#2563eb;color:white;border:none;padding:12px 18px;border-radius:8px;cursor:pointer;font-weight:600;}
.error{color:#c0392b;margin-bottom:12px;}
.note{font-size:0.9rem;color:#555;margin-top:12px;}
</style>
</head>
<body>
<div class="card">
<h1>Video/Audio Downloader</h1>
{% with messages = get_flashed_messages() %}
{% if messages %}
<div class="error">{{ messages[0] }}</div>
{% endif %}
{% endwith %}
<form method="post" action="{{ url_for('download') }}">
<label>Video or Page URL</label>
<input type="text" name="url" placeholder="https://www.youtube.com/watch?v=..." required>
<label>Format</label>
<select name="kind">
<option value="video">Video (mp4)</option>
<option value="audio">Audio (mp3)</option>
</select>
<button type="submit">Download</button>
</form>
<p class="note">Tip: Some sites may require cookies or login; see yt-dlp docs.</p>
</div>
</body>
</html>
"""

def cleanup_path(path: Path, wait_seconds: int = 30):
    """Delete a file/folder after a delay."""
    import time
    time.sleep(wait_seconds)
    if path.exists():
        try:
            if path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path)
        except:
            pass

@app.route("/", methods=["GET"])
def index():
    return render_template_string(INDEX_HTML)

@app.route("/download", methods=["POST"])
def download():
    url = (request.form.get("url") or "").strip()
    kind = request.form.get("kind", "video")

    if not url or not (url.startswith("http://") or url.startswith("https://")):
        flash("Please enter a valid URL")
        return redirect(url_for("index"))

    # unique folder for this download
    uid = uuid.uuid4().hex
    workdir = BASE_TEMP / uid
    workdir.mkdir(parents=True, exist_ok=True)

    try:
        outtmpl = str(workdir / "%(title).100s.%(ext)s")

        if kind == "audio":
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": outtmpl,
                "noplaylist": True,
                "quiet": True,
                "concurrent_fragment_downloads": 5,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "128",
                }],
                "prefer_ffmpeg": True,
            }
        else:
            ydl_opts = {
                "format": "best[ext=mp4]/best",
                "outtmpl": outtmpl,
                "noplaylist": True,
                "quiet": True,
                "concurrent_fragment_downloads": 5,
                "merge_output_format": None,
                "prefer_ffmpeg": True,
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)

        # get the largest file in folder
        files = sorted(workdir.glob("*"), key=lambda p: p.stat().st_size if p.exists() else 0, reverse=True)
        if not files:
            flash("Download completed but file not found.")
            threading.Thread(target=cleanup_path, args=(workdir, 5), daemon=True).start()
            return redirect(url_for("index"))

        outfile = files[0]
        threading.Thread(target=cleanup_path, args=(workdir, 30), daemon=True).start()
        return send_file(str(outfile), as_attachment=True, download_name=outfile.name)

    except Exception as e:
        flash(f"Error: {e}")
        threading.Thread(target=cleanup_path, args=(workdir, 5), daemon=True).start()
        return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Cloud Video/Audio Downloader on port {port}...")
    app.run(host="0.0.0.0", port=port)
