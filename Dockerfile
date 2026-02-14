# 1. Use Python 3.12 on Linux
FROM python:3.12-slim

# 2. Install FFmpeg (required by yt-dlp to probe videos)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 3. Set the working directory inside the cloud server
WORKDIR /app

# 4. Copy your requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy everything else (including your C binary and app.py)
COPY . .

# 6. Make sure your C binary has permission to run in the cloud
RUN chmod +x audio-converter

# 7. Create the downloads folder
RUN mkdir -p downloads

# 8. Start the app using Gunicorn (the professional way to run Flask)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app", "--timeout", "0"]