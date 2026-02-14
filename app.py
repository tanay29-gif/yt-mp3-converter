import os
import subprocess
import uuid
import time
from flask import Flask, request, send_file, render_template, jsonify

app = Flask(__name__)

# Environment Detection
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
    # We use a wildcard for extension because yt-dlp might download webm, m4a, or opus
    input_template = os.path.join(DOWNLOAD_DIR, f"{task_id}_in.%(ext)s")
    final_mp3 = os.path.join(DOWNLOAD_DIR, f"{task_id}_out.mp3")

    try:
        # 1. Download best audio
        print(f"[*] Downloading: {url}")
        subprocess.run([
            "yt-dlp", "-f", "bestaudio", "--no-part", 
            "-o", input_template, url
        ], check=True)

        # 2. Identify the downloaded file path
        downloaded_path = None
        for file in os.listdir(DOWNLOAD_DIR):
            if file.startswith(task_id) and not file.endswith(".mp3"):
                downloaded_path = os.path.join(DOWNLOAD_DIR, file)
                break
        
        if not downloaded_path:
            raise Exception("File not found after download.")

        # 3. Use your custom C-Engine for Studio Quality conversion
        print(f"[*] C-Engine Converting: {downloaded_path}")
        # We use a timeout to prevent the process from hanging forever
        subprocess.run([ENGINE_PATH, downloaded_path, final_mp3], check=True, timeout=120)

        # 4. Return the file
        return send_file(final_mp3, as_attachment=True, download_name="studio_quality.mp3")

    except Exception as e:
        print(f"[!] Error: {str(e)}")
        return jsonify({"error": "Engine failed or Video is unavailable"}), 500
    
    finally:
        # Cleanup Logic: Wait 1 second to ensure file is closed, then delete
        time.sleep(1)
        if 'downloaded_path' in locals() and os.path.exists(downloaded_path):
            os.remove(downloaded_path)
        # Note: final_mp3 is usually deleted by a background task, but 
        # for personal use, you can clear the downloads folder manually.

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    # host='0.0.0.0' allows your Android phone to connect via Wi-Fi
    app.run(host='0.0.0.0', port=port, debug=True)