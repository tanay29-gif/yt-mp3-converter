import os
import subprocess
import uuid
import time
from flask import Flask, request, send_file, render_template, jsonify

app = Flask(__name__)

# --- AUTOMATIC ENVIRONMENT DETECTION ---
IS_CLOUD = "RENDER" in os.environ or "PORT" in os.environ
DOWNLOAD_DIR = "/tmp/downloads" if IS_CLOUD else os.path.join(os.getcwd(), "downloads")
ENGINE_PATH = "./audio-converter"

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    data = request.json
    url = data.get('url')
    if not url: return jsonify({"error": "Paste a link!"}), 400

    task_id = str(uuid.uuid4())
    input_template = os.path.join(DOWNLOAD_DIR, f"{task_id}_in.%(ext)s")
    final_mp3 = os.path.join(DOWNLOAD_DIR, f"{task_id}_out.mp3")

    try:
        # 1. DOWNLOAD (Added Mobile User-Agent to prevent IP blocks)
        print(f"[*] Downloading: {url}")
        subprocess.run([
            "yt-dlp", 
            "-f", "bestaudio", 
            "--no-part",
            "--user-agent", "Mozilla/5.0 (Android 14; Mobile; rv:128.0) Gecko/128.0 Firefox/128.0",
            "--match-filter", "duration < 600", # LIMIT TO 10 MINS FOR PUBLIC USE
            "-o", input_template, 
            url
        ], check=True)

        # 2. FIND DOWNLOADED FILE
        downloaded_path = None
        for file in os.listdir(DOWNLOAD_DIR):
            if file.startswith(task_id) and not file.endswith(".mp3"):
                downloaded_path = os.path.join(DOWNLOAD_DIR, file)
                break
        
        if not downloaded_path:
            raise Exception("File not found.")

        # 3. CONVERT (Your Studio-Quality C-Engine)
        print(f"[*] C-Engine Converting: {downloaded_path}")
        subprocess.run([ENGINE_PATH, downloaded_path, final_mp3], check=True, timeout=180)

        # --- THE CLEANUP LOGIC ---
        # This function will run AFTER the file is sent
        def cleanup():
            try:
                if os.path.exists(downloaded_path): os.remove(downloaded_path)
                if os.path.exists(final_mp3): os.remove(final_mp3)
                print(f"[*] Successfully cleaned up task {task_id}")
            except Exception as e:
                print(f"[!] Cleanup Error: {e}")

        # Send file and trigger cleanup on close
        response = send_file(final_mp3, as_attachment=True, download_name="music.mp3")
        response.call_on_close(cleanup)
        return response

    except Exception as e:
        print(f"[!] Error: {str(e)}")
        # Cleanup input if conversion failed
        if 'downloaded_path' in locals() and os.path.exists(downloaded_path):
            os.remove(downloaded_path)
        return jsonify({"error": "Engine failed or Video is unavailable"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)