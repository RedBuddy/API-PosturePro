# Python 3.12.5 base image
FROM python:3.12.5-slim

# Environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=5000

# System dependencies for OpenCV/MediaPipe video I/O
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libglib2.0-0 \
    libgomp1 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer cache)
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . .

# Expose port and run with gunicorn
EXPOSE 5000
CMD ["sh","-c","gunicorn -k gthread --threads 4 -w 1 -t 300 -b 0.0.0.0:${PORT:-5000} main:app"]
