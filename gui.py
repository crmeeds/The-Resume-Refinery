#!/usr/bin/env python3
"""
Resume Optimizer GUI — browser-based interface.
Launch with: python3 gui.py
Your default browser opens automatically.
Press Ctrl+C in the terminal to quit.
"""

import os
import sys
import tempfile
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv, set_key
from flask import Flask, Response, jsonify, request, send_file

# ── Path resolution ──────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

import resume_optimizer as _ro
_ro.BASE_DIR = BASE_DIR
_ro.MASTER_RESUME_PATH = BASE_DIR / "master_resume.md"
_ro.OUTPUT_DIR = BASE_DIR / "output"

from resume_optimizer import analyze_and_optimize, save_resume  # noqa: E402

MASTER_RESUME_PATH = _ro.MASTER_RESUME_PATH
OUTPUT_DIR = _ro.OUTPUT_DIR
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH)

# ── Shared state ─────────────────────────────────────────────────────────────
_state: dict = {"status": "idle", "message": "Ready", "result": "", "job_filename": ""}
_lock = threading.Lock()

# ── Flask app ────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload limit

# ── HTML template ─────────────────────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Resume Optimizer</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f5f7;color:#1d1d1f;min-height:100vh}
  .wrap{max-width:740px;margin:0 auto;padding:36px 20px 60px}
  h1{font-size:28px;font-weight:700;margin-bottom:4px}
  .sub{color:#6e6e73;font-size:14px;margin-bottom:28px}
  .card{background:#fff;border-radius:14px;padding:20px 22px;margin-bottom:12px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
  .card-title{font-size:13px;font-weight:600;color:#6e6e73;text-transform:uppercase;letter-spacing:.5px;margin-bottom:12px}
  .row{display:flex;align-items:center;gap:10px}
  input[type=password]{flex:1;padding:9px 13px;border:1.5px solid #d1d1d6;border-radius:9px;font-size:14px;outline:none;transition:border-color .2s}
  input[type=password]:focus{border-color:#0071e3}
  .file-label{display:flex;align-items:center;gap:10px;flex:1}
  .fname{flex:1;font-size:13px;color:#8e8e93;padding:9px 13px;border:1.5px solid #e5e5ea;border-radius:9px;background:#fafafa;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .fname.ok{color:#1a7f37;border-color:#34c759;background:#f0faf3}
  .hint{font-size:12px;color:#aeaeb2;margin-top:8px}
  .btn{padding:9px 20px;border:none;border-radius:9px;font-size:13px;font-weight:500;cursor:pointer;transition:opacity .15s}
  .btn:disabled{opacity:.4;cursor:not-allowed}
  .btn-outline{background:#e8e8ed;color:#1d1d1f}.btn-outline:hover:not(:disabled){background:#d8d8dd}
  .btn-blue{background:#0071e3;color:#fff}.btn-blue:hover:not(:disabled){background:#0077ed}
  .btn-big{width:100%;padding:15px;font-size:16px;font-weight:600;border-radius:11px;margin-bottom:6px}
  .status{font-size:13px;color:#6e6e73;min-height:20px;margin:6px 0}
  .status.ok{color:#1a7f37}.status.err{color:#d70015}
  .bar-wrap{height:4px;background:#e5e5ea;border-radius:2px;overflow:hidden;display:none;margin-bottom:8px}
  .bar{height:100%;width:40%;background:#0071e3;border-radius:2px;animation:slide 1.4s ease-in-out infinite}
  @keyframes slide{0%{margin-left:-40%}100%{margin-left:110%}}
  .out-card{display:none}
  .output-box{width:100%;height:500px;padding:14px;border:1.5px solid #e5e5ea;border-radius:9px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:13px;resize:vertical;background:#fafafa;color:#1d1d1f;outline:none;line-height:1.6}
  .save-row{display:flex;justify-content:flex-end;margin-top:10px}
</style>
</head>
<body>
<div class="wrap">
  <h1>Resume Optimizer</h1>
  <p class="sub">Tailor your resume to any job posting using Claude AI</p>

  <!-- API Key -->
  <div class="card">
    <div class="card-title">Claude API Key</div>
    <div class="row">
      <input type="password" id="apiKey" placeholder="sk-ant-..." value="__API_KEY__">
    </div>
    <p class="hint">Saved locally in .env — sent only to Anthropic.</p>
  </div>

  <!-- Master Resume -->
  <div class="card">
    <div class="card-title">Master Resume</div>
    <textarea id="masterText" placeholder="Paste your full resume here…" style="width:100%;height:180px;padding:10px 13px;border:1.5px solid #d1d1d6;border-radius:9px;font-size:13px;font-family:inherit;resize:vertical;outline:none;line-height:1.5"></textarea>
  </div>

  <!-- Job Description -->
  <div class="card">
    <div class="card-title">Job Description</div>
    <textarea id="jobText" placeholder="Paste the full job description here…" style="width:100%;height:180px;padding:10px 13px;border:1.5px solid #d1d1d6;border-radius:9px;font-size:13px;font-family:inherit;resize:vertical;outline:none;line-height:1.5"></textarea>
  </div>

  <!-- Run -->
  <button class="btn btn-blue btn-big" id="runBtn" onclick="run()">Optimize Resume</button>
  <div class="status" id="status">Ready — upload your files to get started.</div>
  <div class="bar-wrap" id="barWrap"><div class="bar"></div></div>

  <!-- Output -->
  <div class="card out-card" id="outCard">
    <div class="card-title">Optimized Resume</div>
    <textarea class="output-box" id="output" readonly></textarea>
    <div class="save-row">
      <button class="btn btn-blue" onclick="download()">Save Resume (.txt)</button>
    </div>
  </div>
</div>

<script>
let polling = null;
let timerInterval = null;
let runStart = null;

async function run() {
  const key = document.getElementById('apiKey').value.trim();
  const masterText = document.getElementById('masterText').value.trim();
  const jobText = document.getElementById('jobText').value.trim();
  if (!key) { setStatus('Please enter your Claude API key.', 'err'); return; }
  if (!masterText) { setStatus('Please paste your master resume.', 'err'); return; }
  if (!jobText) { setStatus('Please paste a job description.', 'err'); return; }
  await fetch('/api/save-key', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({key})});
  document.getElementById('runBtn').disabled = true;
  document.getElementById('barWrap').style.display = 'block';
  document.getElementById('outCard').style.display = 'none';
  setStatus('Starting…', '');
  const res = await fetch('/api/run', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({master_text: masterText, job_text: jobText})});
  const data = await res.json();
  if (!data.ok) {
    setStatus(data.error, 'err');
    document.getElementById('runBtn').disabled = false;
    document.getElementById('barWrap').style.display = 'none';
    return;
  }
  polling = setInterval(poll, 2500);
  runStart = Date.now();
  timerInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - runStart) / 1000);
    const m = Math.floor(elapsed / 60);
    const s = String(elapsed % 60).padStart(2, '0');
    setStatus(`Calling Claude AI… (${m}:${s} elapsed)`);
  }, 1000);
}

async function poll() {
  const res = await fetch('/api/status');
  const data = await res.json();
  const cls = data.status === 'done' ? 'ok' : data.status === 'error' ? 'err' : '';
  setStatus(data.message, cls);
  if (data.status === 'done') {
    clearInterval(polling);
    clearInterval(timerInterval); timerInterval = null;
    document.getElementById('barWrap').style.display = 'none';
    document.getElementById('runBtn').disabled = false;
    document.getElementById('output').value = data.result;
    document.getElementById('outCard').style.display = 'block';
  } else if (data.status === 'error') {
    clearInterval(polling);
    clearInterval(timerInterval); timerInterval = null;
    document.getElementById('barWrap').style.display = 'none';
    document.getElementById('runBtn').disabled = false;
  }
}

function download() { window.location.href = '/api/download'; }
function setStatus(msg, cls) {
  const el = document.getElementById('status');
  el.textContent = msg;
  el.className = 'status' + (cls ? ' ' + cls : '');
}

</script>
</body>
</html>"""


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/favicon.ico")
def favicon():
    return "", 204


@app.route("/")
def index():
    api_key = os.getenv("ANTHROPIC_API_KEY", "").replace('"', "&quot;")
    html = HTML.replace("__API_KEY__", api_key)
    return Response(html, content_type="text/html")


@app.route("/api/save-key", methods=["POST"])
def save_key():
    key = (request.json or {}).get("key", "").strip()
    if key:
        os.environ["ANTHROPIC_API_KEY"] = key
        try:
            set_key(str(ENV_PATH), "ANTHROPIC_API_KEY", key)
        except Exception:
            pass
    return jsonify(ok=True)




@app.route("/api/run", methods=["POST"])
def run():
    body = request.json or {}
    master_text = body.get("master_text", "").strip()
    job_text = body.get("job_text", "").strip()
    if not master_text:
        return jsonify(ok=False, error="No resume text provided")
    if not job_text:
        return jsonify(ok=False, error="No job description provided")
    with _lock:
        if _state["status"] == "running":
            return jsonify(ok=False, error="Already running — please wait")
        _state["status"] = "running"
        _state["message"] = "Calling Claude AI…"
        _state["result"] = ""
    threading.Thread(target=_worker, args=(master_text, job_text), daemon=True).start()
    return jsonify(ok=True)


def _worker(master_text: str, job_text: str):
    try:
        result = analyze_and_optimize(job_text, master_text)
        try:
            OUTPUT_DIR.mkdir(exist_ok=True)
            save_resume(result, job_source="job_description.txt")
        except Exception:
            pass
        with _lock:
            _state["status"] = "done"
            _state["message"] = "Done! Review your resume below, then click Save."
            _state["result"] = result
    except Exception as exc:
        with _lock:
            _state["status"] = "error"
            _state["message"] = str(exc)


@app.route("/api/status")
def status():
    with _lock:
        return jsonify(status=_state["status"], message=_state["message"], result=_state["result"])


@app.route("/api/download")
def download():
    with _lock:
        result = _state.get("result", "")
        stem = Path(_state.get("job_filename", "resume.txt")).stem
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    tmp = tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w", encoding="utf-8")
    tmp.write(result)
    tmp.close()
    return send_file(tmp.name, as_attachment=True, download_name=f"{stem}_{ts}.txt")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    PORT = 5050
    url = f"http://localhost:{PORT}"
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    print(f"\nResume Optimizer running at {url}")
    print("Your browser should open automatically.")
    print("Press Ctrl+C to quit.\n")
    app.run(port=PORT, debug=False)
