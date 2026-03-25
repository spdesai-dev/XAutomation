import os
import sys
import json
import time
import subprocess
import threading
from collections import deque
from flask import Flask, render_template, request, jsonify
from loguru import logger
import config
from spreadsheet import SpreadsheetManager
from ai_generator import generate_dm

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable static file caching
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# ── Global State ──────────────────────────────────────────────────────────────
automation_process = None   # subprocess.Popen instance
is_running = False
current_file = None
session_files = []  # List of dicts: {"original": str, "path": str}
last_message_template = ""

log_messages = deque(maxlen=200)
stats_cache = {
    "total": 0,
    "pending": 0,
    "sent": 0,
    "failed": 0,
    "current_user": "None"
}

# ── Logger ────────────────────────────────────────────────────────────────────
def custom_log_sink(message):
    log_messages.append(message.strip())

logger.remove()
logger.add(custom_log_sink, format="{time:HH:mm:ss} | {level} | {message}")
logger.add("xautomation.log", rotation="1 MB")

# ── Stats helper ──────────────────────────────────────────────────────────────
def update_stats(sm: SpreadsheetManager, current_user="None"):
    global stats_cache
    if not sm or not sm.data:
        return
    total   = len(sm.data)
    pending = sum(1 for r in sm.data if str(r.get('status', '')).lower() == 'pending')
    sent    = sum(1 for r in sm.data if str(r.get('status', '')).lower() == 'sent')
    failed  = sum(1 for r in sm.data if str(r.get('status', '')).lower() == 'failed')
    stats_cache.update({"total": total, "pending": pending, "sent": sent,
                        "failed": failed, "current_user": current_user})

# ── Subprocess log reader ─────────────────────────────────────────────────────
def _read_process_output(proc):
    """Runs in a daemon thread; streams stdout lines from the worker into log_messages."""
    global is_running
    try:
        for line in iter(proc.stdout.readline, ''):
            if line:
                log_messages.append(line.strip())
    except Exception:
        pass
    finally:
        proc.wait()
        is_running = False
        # Refresh stats from the (now updated) spreadsheet file
        if current_file and os.path.exists(current_file):
            try:
                sm = SpreadsheetManager(current_file)
                update_stats(sm, current_user="Idle")
            except Exception:
                pass
        logger.info("Automation process ended.")

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    global current_file, stats_cache, session_files
    
    uploaded_files = request.files.getlist('file')
    if not uploaded_files:
        return jsonify({"error": "No files uploaded"}), 400

    new_loads = 0
    for file in uploaded_files:
        if file.filename == '' or not (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
            continue
            
        temp_filename = "part_" + str(int(time.time())) + "_" + file.filename.replace(" ", "_")
        temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
        file.save(temp_filepath)
        
        session_files.append({"original": file.filename, "path": temp_filepath})
        new_loads += 1

    if not session_files:
        return jsonify({"error": "No valid files uploaded."}), 400

    # CRITICAL FIX: If the user uploads a new file while worker is running,
    # the worker must be stopped so that the merged queue stays synchronized.
    global automation_process, is_running
    if is_running and automation_process is not None:
        try:
            if sys.platform == "win32":
                subprocess.call(["taskkill", "/F", "/T", "/PID", str(automation_process.pid)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                import signal
                os.killpg(os.getpgid(automation_process.pid), signal.SIGTERM)
        except Exception as e:
            logger.error(f"Error stopping process on file upload: {e}")
            
        try:
            automation_process.kill() # Guaranteed fallback kill
        except Exception:
            pass
        
        automation_process = None
        is_running = False
        logger.warning("Automation stopped automatically because new files were uploaded.")

    return _merge_session_files()

def _rebuild_merged_file():
    """Rebuild the merged CSV from current session_files and update current_file.
    Returns the new file path, or None if there are no files.
    This is the single source of truth — always call this right before launching a worker."""
    global current_file, session_files, stats_cache

    all_data = []
    first_sm = None

    for f_info in session_files:
        try:
            sm = SpreadsheetManager(f_info["path"])
            all_data.extend(sm.data)
            if not first_sm:
                first_sm = sm
        except Exception as e:
            logger.error(f"Failed to read {f_info['original']}: {e}")

    if not all_data or first_sm is None:
        current_file = None
        stats_cache.update({"total": 0, "pending": 0, "sent": 0, "failed": 0})
        return None

    master_filename = "merged_session_" + str(int(time.time())) + ".csv"
    master_filepath = os.path.join(app.config['UPLOAD_FOLDER'], master_filename)

    first_sm.data = all_data
    first_sm.file_path = master_filepath
    first_sm.save()

    current_file = master_filepath
    update_stats(first_sm, current_user="Idle")
    logger.info(f"Merged {len(all_data)} rows from {len(session_files)} file(s) into {master_filename}")
    return master_filepath


def _merge_session_files():
    """HTTP-friendly wrapper: rebuilds merged file and returns a jsonify response."""
    _rebuild_merged_file()
    return jsonify({
        "success": True,
        "message": "Session updated.",
        "stats": stats_cache,
        "files": [f["original"] for f in session_files]
    })

@app.route("/api/remove_file", methods=["POST"])
def remove_file():
    global session_files
    data = request.json
    filename = data.get("filename")
    
    if not filename:
        return jsonify({"error": "No filename provided"}), 400
        
    # Find and remove the first occurrence of the filename
    for i, f in enumerate(session_files):
        if f["original"] == filename:
            path_to_delete = f["path"]
            session_files.pop(i)
            try:
                if os.path.exists(path_to_delete):
                    os.remove(path_to_delete)
            except Exception:
                pass
            break
            
    # CRITICAL FIX: If the user removes a file while the worker is running, 
    # the worker (which is running on an old merged snapshot) must be stopped
    # so it doesn't continue generating for the deleted sheet.
    global automation_process, is_running
    if is_running and automation_process is not None:
        try:
            if sys.platform == "win32":
                subprocess.call(["taskkill", "/F", "/T", "/PID", str(automation_process.pid)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                import signal
                os.killpg(os.getpgid(automation_process.pid), signal.SIGTERM)
        except Exception as e:
            logger.error(f"Error stopping process on file removal: {e}")
            
        try:
            automation_process.kill() # Guaranteed fallback kill
        except Exception:
            pass
        
        automation_process = None
        is_running = False
        logger.warning("Automation stopped automatically because a sheet was removed.")
        
    return _merge_session_files()

@app.route("/start", methods=["POST"])
def start_automation():
    global automation_process, is_running, current_file

    if is_running:
        return jsonify({"error": "Automation is already running."}), 400
    if not session_files:
        return jsonify({"error": "No valid spreadsheet uploaded."}), 400

    # Grab lock immediately to prevent race conditions
    is_running = True

    data = request.json or {}
    message_template = data.get("message_template", "")
    use_ai           = bool(data.get("use_ai", False))
    api_key          = data.get("openrouter_api_key", "").strip()
    model            = data.get("openrouter_model", "openai/gpt-oss-120b").strip()
    system_prompt    = data.get("ai_system_prompt", "").strip()
    
    global last_message_template
    last_message_template = message_template

    # If AI is OFF, require a manual template
    if not use_ai and not message_template.strip():
        return jsonify({"error": "Message template cannot be empty."}), 400
    # If AI is ON but no key provided, warn (but don't block — fallback will handle it)
    if use_ai and not api_key:
        logger.warning("AI mode enabled but no API key provided — will use fallback template.")

    python_exe  = sys.executable
    worker_path = os.path.join(os.path.dirname(__file__), "worker.py")

    # REBUILD the merged file fresh from session_files RIGHT NOW.
    # This is the root-cause fix: current_file could be stale (pointing to an old
    # merged CSV that contains rows from deleted sheets). By rebuilding here, we
    # guarantee the worker subprocess only ever sees the current, live data.
    fresh_file = _rebuild_merged_file()
    if not fresh_file:
        is_running = False
        return jsonify({"error": "No valid spreadsheet data found."}), 400

    cmd = [python_exe, worker_path, fresh_file, json.dumps(message_template),
           "--api-key", api_key, "--model", model]
    
    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])

    if use_ai:
        cmd.append("--use-ai")
        # Check if there are any pre-approved messages — if yes, send-only
        # If no approved messages yet, use standard mode (generate + send inline)
        try:
            sm_check = SpreadsheetManager(fresh_file)
            approved = list(sm_check.get_approved_users())
            if approved:
                cmd.append("--send-only")
                logger.info(f"Found {len(approved)} approved messages — using SEND-ONLY mode.")
            else:
                logger.info("No pre-approved messages found — using STANDARD mode (AI generate + send).")
        except Exception:
            pass  # Fall through to standard mode

    try:
        automation_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=os.path.dirname(__file__)
        )
        reader = threading.Thread(target=_read_process_output,
                                  args=(automation_process,), daemon=True)
        reader.start()
        logger.info(f"Automation subprocess started (AI={'ON' if use_ai else 'OFF'}, model={model}).")
        return jsonify({"success": True, "message": "Automation started."})
    except Exception as e:
        is_running = False
        logger.error(f"Failed to start worker process: {e}")
        return jsonify({"error": f"Could not start automation: {e}"}), 500

@app.route("/generate", methods=["POST"])
def generate_messages():
    global automation_process, is_running, current_file

    if is_running:
        return jsonify({"error": "Automation is already running."}), 400
    if not current_file or not os.path.exists(current_file):
        return jsonify({"error": "No valid spreadsheet uploaded."}), 400

    # GRAB LOCK IMMEDIATELY to completely prevent race conditions
    is_running = True

    data = request.json or {}
    message_template = data.get("message_template", "")
    use_ai           = bool(data.get("use_ai", False))
    api_key          = data.get("openrouter_api_key", "").strip()
    model            = data.get("openrouter_model", "openai/gpt-oss-120b").strip()
    system_prompt    = data.get("ai_system_prompt", "").strip()
    
    global last_message_template
    last_message_template = message_template

    if not use_ai:
        return jsonify({"error": "Generate mode requires AI to be enabled."}), 400

    if not api_key:
        logger.warning("AI mode enabled but no API key provided — will use fallback template.")

    python_exe  = sys.executable
    worker_path = os.path.join(os.path.dirname(__file__), "worker.py")

    # REBUILD merged file fresh right before starting subprocess — see start_automation for explanation.
    fresh_file = _rebuild_merged_file()
    if not fresh_file:
        is_running = False
        return jsonify({"error": "No valid spreadsheet data found."}), 400

    cmd = [python_exe, worker_path, fresh_file, json.dumps(message_template),
           "--api-key", api_key, "--model", model, "--use-ai", "--generate-only"]
    
    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])

    try:
        automation_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=os.path.dirname(__file__)
        )
        reader = threading.Thread(target=_read_process_output,
                                  args=(automation_process,), daemon=True)
        reader.start()
        logger.info(f"Generation subprocess started (model={model}).")
        return jsonify({"success": True, "message": "Draft generation started."})
    except Exception as e:
        is_running = False
        logger.error(f"Failed to start generation process: {e}")
        return jsonify({"error": f"Could not start generation: {e}"}), 500

@app.route("/stop", methods=["POST"])
def stop_automation():
    global automation_process, is_running

    if not is_running or automation_process is None:
        return jsonify({"error": "Automation is not running."}), 400

    try:
        # Kill the entire process tree to also terminate Playwright/Chrome
        if sys.platform == "win32":
            subprocess.call(["taskkill", "/F", "/T", "/PID", str(automation_process.pid)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            import signal, os
            os.killpg(os.getpgid(automation_process.pid), signal.SIGTERM)

        automation_process = None
        is_running = False
        logger.warning("Automation stopped by user.")
        return jsonify({"success": True, "message": "Automation stopped."})
    except Exception as e:
        logger.error(f"Error stopping process: {e}")
        
    try:
        if automation_process: # Ensure automation_process is not None before calling kill
            automation_process.kill() # Guaranteed fallback kill
    except Exception:
        pass

    automation_process = None
    is_running = False
    return jsonify({"error": f"Could not stop: {e}"}), 500 # This line was moved from the try block

@app.route("/api/approvals", methods=["GET"])
def get_approvals():
    global current_file
    if not current_file or not os.path.exists(current_file):
        return jsonify({"approvals": []})
    
    try:
        sm = SpreadsheetManager(current_file)
        approvals = sm.get_pending_approvals()
        return jsonify({"approvals": approvals})
    except Exception as e:
        logger.error(f"Error fetching approvals: {e}")
        return jsonify({"error": f"Failed to fetch approvals: {e}"}), 500

@app.route("/api/approve", methods=["POST"])
def approve_message():
    global current_file
    if not current_file or not os.path.exists(current_file):
        return jsonify({"error": "No active file."}), 400
        
    data = request.json or {}
    index = data.get("index")
    message = data.get("message")
    
    if index is None or message is None:
        return jsonify({"error": "Missing index or message."}), 400
        
    try:
        sm = SpreadsheetManager(current_file)
        sm.update_user_status(index=int(index), status="approved", generated_message=message)
        update_stats(sm, current_user="Idle")
        logger.info(f"Message for row {index} approved.")
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error approving message: {e}")
        return jsonify({"error": f"Error approving message: {e}"}), 500

@app.route("/api/disapprove", methods=["POST"])
def disapprove_message():
    global current_file
    if not current_file or not os.path.exists(current_file):
        return jsonify({"error": "No active file."}), 400
        
    data = request.json or {}
    index = data.get("index")
    feedback = data.get("feedback")
    api_key = data.get("api_key", "").strip()
    model = data.get("model", "openai/gpt-oss-120b").strip()
    fallback_template = data.get("fallback_template", "")
    system_prompt = data.get("ai_system_prompt", "").strip()
    
    if index is None or not feedback:
        return jsonify({"error": "Missing index or feedback."}), 400
        
    try:
        sm = SpreadsheetManager(current_file)
        row = sm.data[int(index)]
        username = row.get("username", "Unknown")
        post_content = row.get("post_content", "")
        
        logger.info(f"Regenerating message for @{username} with feedback...")
        
        # Include feedback in generation and split models
        models = [m.strip() for m in model.split(',') if m.strip()]
        if not models:
            models = ["openai/gpt-oss-120b"]
            
        variations = []
        target_count = 3
        calls_to_make = [models[i % len(models)] for i in range(target_count)]

        for i, mod in enumerate(calls_to_make):
            if i > 0:
                time.sleep(1.2) # Delay for regeneration too
            msg = generate_dm(
                post_content=post_content,
                username=username,
                api_key=api_key,
                model=mod,
                fallback_template=fallback_template,
                system_prompt=system_prompt,
                feedback=feedback,
                variation_index=i
            )
            variations.append(msg)
            
        new_message = json.dumps(variations)
        
        sm.update_user_status(index=int(index), status="pending_approval", generated_message=new_message)
        return jsonify({"success": True, "new_message": new_message})
    except Exception as e:
        logger.error(f"Error regenerating message: {e}")
        return jsonify({"error": f"Error regenerating message: {e}"}), 500

@app.route("/api/test_model", methods=["POST"])
def test_model():
    data = request.json or {}
    api_key = data.get("api_key", "").strip()
    model = data.get("model", "openai/gpt-4o-mini").strip()
    system_prompt = data.get("system_prompt", "").strip()

    if not api_key:
        return jsonify({"success": False, "error": "Missing OpenRouter API Key."}), 400

    try:
        logger.info(f"Testing model {model}...")
        test_msg = generate_dm(
            post_content="This is a test message to verify the AI configuration.",
            username="TestUser",
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            variation_index=0,
            allow_fallback=False
        )
        # Note: generate_dm returns fallback if it fails, and we already improved its logging.
        # To make it explicit for the test, we check if it looks like a fallback or if we can detect the error.
        return jsonify({"success": True, "message": test_msg})
    except Exception as e:
        logger.error(f"Test model failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/status", methods=["GET"])
def get_status():
    global is_running, log_messages, stats_cache, current_file, last_message_template, session_files
    return jsonify({
        "is_running": is_running,
        "logs": list(log_messages),
        "stats": stats_cache,
        "current_file": os.path.basename(current_file) if current_file else None,
        "session_files": [f["original"] for f in session_files],
        "message_template": last_message_template
    })

if __name__ == "__main__":
    logger.info("Starting Flask server on http://localhost:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
